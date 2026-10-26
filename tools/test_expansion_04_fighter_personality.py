"""Controller-only Snes9x proof of twelve native intro/victory presentations.

No savestates or emulated memory writes. Video is captured, PCM acknowledged
silently. Optional --baseline-rom compares gameplay outcomes with the base ROM.
Run after tools/build.py; writes only this feature's report/screenshots.
"""
from __future__ import annotations

import argparse
import ctypes as C
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emulator import Emulator, ROOT
from expansion_contracts import combined_contract

OUT = ROOT / 'docs/screenshots/expansion-04'
REPORT = ROOT / 'docs/expansion-04-report.json'
BASE = '610537d'
NAMES = ('DAMIAN', 'IVO', 'CRISTOBAL', 'COTE', 'NEGGER', 'DAVID',
         'FERNANDO', 'CRISTIAN', 'MADARIAGA', 'RESTON', 'ROXANA', 'LARS')
TITLES = ('Kernel salute', 'Capital guard', 'Atomic one-two', 'Balance check',
          'Macro brace', 'Audit rise', 'Legacy seal', 'Risk reversal',
          'Merge pulse', 'Cloud horizon', 'Close-out flourish', 'Nordic stamp')
INTROS = ((42,43,35,32), (40,28,40,43), (34,6,35,32), (28,44,45,35),
          (34,42,40,32), (44,45,46,32), (40,42,43,35), (40,34,35,32),
          (28,42,43,32), (42,43,45,32), (35,45,46,32), (44,28,42,35))
VICTORIES = ((43,42,45,46,11,46,11), (40,28,42,43,46,11,46),
             (34,6,35,45,11,46,11), (28,44,45,35,46,11,46),
             (34,42,43,40,46,11,11), (44,45,13,45,46,11,46),
             (40,42,43,35,45,46,11), (40,34,6,35,45,11,46),
             (28,42,43,35,46,11,46), (42,43,35,45,46,11,11),
             (35,45,46,11,46,45,11), (44,28,42,43,45,46,11))
INTRO_SAMPLES = (14, 26, 38, 50)
VICTORY_SAMPLES = (8, 28, 48, 72, 96, 124, 156)
SUFFIXES = ('', 'b', 'c', 'd', 'e', 'f', 'g', 'h')
checks = []


def check(ok, label, details=None):
    checks.append({'check': label, 'passed': bool(ok), 'details': details})
    if not ok:
        raise AssertionError((label, details))


def symbols(text):
    return {name: int(addr, 16) for addr, name in
            re.findall(r'^([0-9a-fA-F]{8}) ([^\s]+)$', text, re.M)}


SYMS = symbols((ROOT / 'dist/abaqus-after-hours.sym').read_text(encoding='utf-8'))


def ram(e, name, size=1):
    address = SYMS[name]
    offset = address - 0x7E0000 if address >= 0x7E0000 else address
    return int.from_bytes(C.string_at(e.ram + offset, size), 'little')


def trace(e, word):
    return int.from_bytes(C.string_at(e.ram + 0x1FF00 + word * 2, 2), 'little')


def actor_payloads(e):
    raw = C.string_at(e.core.retro_get_memory_data(3), 65536)
    return [b''.join(raw[0xC000 + side*0x1400 + r*512:
                             0xC000 + side*0x1400 + r*512 + 384]
                     for r in range(10)) for side in (0, 1)]


def oam(e):
    raw = C.string_at(e.ram + SYMS['oamMemory'] - 0x7E0000, 544)
    entries = []
    for i in range(128):
        x, y, tile, attr = raw[i*4:i*4+4]
        high = (raw[512+i//4] >> ((i&3)*2)) & 3
        entries.append((x + ((high&1)<<8), y, tile+((attr&1)<<8),
                        attr, 16 if high&2 else 8))
    return entries


def payloads(fighter):
    result = []
    for suffix in SUFFIXES:
        raw = (ROOT / f'assets/generated/fighter{fighter:02}{suffix}.bin').read_bytes()
        result.extend(raw[n:n+3840] for n in range(0, len(raw), 3840))
    return result


def tap(e, key, port=0):
    e.run(3, **{f'p{port+1}': [key]})
    e.run(7)


def boot(fighter, stage=0, mode=1, rom=None):
    e = Emulator(rom=rom)
    e.run(120)
    for _ in range(mode):
        tap(e, 'down')
    tap(e, 'a')
    for _ in range(fighter):
        tap(e, 'right')
    tap(e, 'a')
    if mode:
        target = e.state()['selected2']
        for _ in range((fighter-target)%12):
            tap(e, 'right', int(mode == 1))
        tap(e, 'a', int(mode == 1))
    for _ in range(stage):
        tap(e, 'down')
    e.run(3, p1=['a'])
    for _ in range(120):
        s = e.state()
        if s['screen'] == 3 and ram(e, 'screen') == 3 and s['intro']:
            return e
        e.run(1)
    raise AssertionError(('controller menu route failed', e.state()))


class Monitor:
    def __init__(self):
        self.previous = None
        self.upload_failures = []
        self.cadence_failures = []
        self.overflow_failures = []
        self.maximum_actors_changed = 0
        self.maximum_objects = 0
        self.maximum_scanline_objects = 0
        self.maximum_scanline_tiles = 0
        self.samples = 0
        self.strict_cadence_samples = 0
        self.max_spc_backlog = 0

    def sample(self, e, strict=False):
        s = e.state()
        pages = actor_payloads(e)
        self.samples += 1
        if self.previous:
            old_s, old_pages, old_lag = self.previous
            changed = sum(a != b for a, b in zip(pages, old_pages))
            self.maximum_actors_changed = max(self.maximum_actors_changed, changed)
            if changed > 1:
                self.upload_failures.append(s['frame'])
            if strict:
                self.strict_cadence_samples += 1
                delta = (s['frame'] - old_s['frame']) & 65535
                lag = (ram(e, 'lag_frame_counter', 2)-old_lag) & 65535
                if delta != 1 or lag:
                    self.cadence_failures.append({'frame': s['frame'], 'delta': delta, 'lag': lag})
        self.previous = (s, pages, ram(e, 'lag_frame_counter', 2))
        if trace(e, 114) & 0xC0:
            self.overflow_failures.append(s['frame'])
        entries = [entry for entry in oam(e) if entry[0] < 256 and entry[1] < 224]
        self.maximum_objects = max(self.maximum_objects, len(entries))
        for line in range(121, 218):
            row = [entry for entry in entries if entry[1] <= line < entry[1]+entry[4]]
            self.maximum_scanline_objects = max(self.maximum_scanline_objects, len(row))
            self.maximum_scanline_tiles = max(self.maximum_scanline_tiles,
                                              sum(entry[4]//8 for entry in row))
        self.max_spc_backlog = max(self.max_spc_backlog,
                                  (ram(e, 'spc_fwrite')-ram(e, 'spc_fread'))&255)
        return s, pages

    def verify(self, label):
        check(not self.upload_failures, label+' at most one actor page changes per video frame', self.upload_failures)
        check(not self.cadence_failures, label+' stable native ticks have exact cadence and no lag', self.cadence_failures[:8])
        check(not self.overflow_failures, label+' native PPU has no OBJ range/time overflow', self.overflow_failures[:8])
        check(self.maximum_scanline_objects <= 32 and self.maximum_scanline_tiles <= 34,
              label+' staged OAM stays within scanline/fetch budgets', self.summary())
        check(self.max_spc_backlog <= 6, label+' existing SPC FIFO stays bounded', self.max_spc_backlog)

    def summary(self):
        return {key: value for key, value in vars(self).items() if key != 'previous'}


def crop_actor(e, side):
    s = e.state()
    x = s[f'x{side+1}']//16
    y = s[f'y{side+1}']
    if y >= 32768:
        y -= 65536
    return e.frame.crop((x-48, 121+y//16, x+48, 201+y//16)).copy()


def screenshot(e, fighter, label):
    path = OUT / f'{fighter:02}-{NAMES[fighter].lower()}-{label}.png'
    e.frame.save(path)
    return path.relative_to(ROOT).as_posix()


def verify_intro(e, fighter, monitor):
    native = payloads(fighter)
    seen, captures, accents = {}, {}, [set(), set()]
    frozen = ('hp1', 'hp2', 'x1', 'x2', 'y1', 'y2', 'energy1', 'energy2',
              'action1', 'action2', 'seconds', 'wave1', 'wave2')
    origin = {key: e.state()[key] for key in frozen}
    violations = []
    while e.state()['intro']:
        e.run(1)
        s, pages = monitor.sample(e, strict=2 < 110-e.state()['intro'] < 108)
        tick = 110-s['intro']
        if any(s[key] != origin[key] for key in frozen):
            violations.append(s)
        if tick in INTRO_SAMPLES:
            beat = INTRO_SAMPLES.index(tick)
            expected = INTROS[fighter][beat]
            for side in (0, 1):
                check(s[f'anim_frame{side+1}'] == expected and pages[side] == native[expected],
                      f'{NAMES[fighter]} P{side+1} intro beat {beat} is the exact approved native pose', expected)
            seen[beat] = expected
            captures[beat] = crop_actor(e, 0)
            if beat == 1:
                screenshot(e, fighter, 'intro')
        entry = oam(e)[69]
        if entry[0] < 256 and entry[1] < 224:
            side = 0 if tick < 32 else 1
            accents[side].add(entry[:4])
    check(not violations, NAMES[fighter]+' intro never alters combat state', len(violations))
    check(len(seen) == 4, NAMES[fighter]+' exposes all four intro beats')
    check(all(accents), NAMES[fighter]+' both intro sides receive a native signature accent',
          [len(items) for items in accents])
    for _ in range(8):
        e.run(1)
        monitor.sample(e)
    check(oam(e)[69][0] >= 256, NAMES[fighter]+' cosmetic accent ends before live combat')
    return seen, captures


def win_round(e, side, monitor):
    # Walk only when out of normal-kick range, then release direction before
    # pressing A. Every HP loss therefore comes from ordinary controller play.
    for tick in range(1600):
        s = e.state()
        if s['round_end']:
            check(s[f'hp{2-side}'] == 0 and s[f'wins{side+1}'] >= 1,
                  f'P{side+1} wins through actual native damage')
            return tick
        gap = abs(s['x1']-s['x2'])
        if gap > 40*16:
            keys = ['right' if s[f'x{side+1}'] < s[f'x{2-side}'] else 'left']
        else:
            keys = ['a'] if tick % 40 < 4 else []
        e.run(1, **{f'p{side+1}': keys})
        monitor.sample(e)
    raise AssertionError(('ordinary controller KO did not arrive', side, e.state()))


def verify_victory(e, fighter, side, monitor):
    native = payloads(fighter)
    captures, seen, accents = {}, {}, set()
    frozen_keys = ('hp1','hp2','x1','x2','y1','y2','energy1','energy2','seconds','wins1','wins2')
    frozen = tuple(e.state()[key] for key in frozen_keys)
    bad_state, loser_frames, loser_errors = [], set(), []
    start = e.state()['round_end']
    for _ in range(start-1):
        e.run(1)
        s, pages = monitor.sample(e, strict=4 < 180-e.state()['round_end'] < 176)
        tick = 180-s['round_end']
        if tuple(s[key] for key in frozen_keys) != frozen:
            bad_state.append(s['frame'])
        loser_frames.add(s[f'anim_frame{2-side}'])
        loser = 2-side
        clock = s[f'anim_tick{loser}']
        expected_loser = ((59 if s[f'down_tick{loser}'] < 5 else 14)
                          if s[f'down_state{loser}'] == 3 else
                          47 if clock <= 8 else 59 if clock <= 16 else 14)
        if s[f'anim_frame{loser}'] != expected_loser:
            loser_errors.append({'tick': tick, 'frame': s[f'anim_frame{loser}'],
                                 'expected': expected_loser, 'clock': clock,
                                 'down_state': s[f'down_state{loser}'], 'down_tick': s[f'down_tick{loser}']})
        if tick in VICTORY_SAMPLES:
            beat = VICTORY_SAMPLES.index(tick)
            expected = VICTORIES[fighter][beat]
            check(s[f'anim_frame{side+1}'] == expected and pages[side] == native[expected],
                  f'{NAMES[fighter]} P{side+1} victory beat {beat} is the exact approved native pose', expected)
            captures[beat] = crop_actor(e, side)
            seen[beat] = expected
            if beat == 4:
                screenshot(e, fighter, 'victory')
        entry = oam(e)[69]
        if 32 <= tick < 64 and entry[0] < 256 and entry[1] < 224:
            accents.add(entry[:4])
    check(not bad_state, NAMES[fighter]+' victory leaves outcome, positions, health and clock frozen', bad_state)
    check(len(seen) == 7 and len(set(seen.values())) >= 4,
          NAMES[fighter]+' plays seven victory beats with at least four distinct approved poses')
    check(not loser_errors, NAMES[fighter]+' KO loser follows exact weighted fall/impact/prone sequencing',
          {'observed': sorted(loser_frames), 'errors': loser_errors[:8]})
    check(len(accents) >= 2, NAMES[fighter]+' victory has a moving native signature accent', len(accents))
    e.run(1)
    check(e.state()['intro'] == 110 and not e.state()['round_end'],
          NAMES[fighter]+' roundEnd lasts exactly 180 native ticks and resets normally')
    return seen, captures


def pause_probe(mode, during_victory=False):
    e = boot(0, mode=mode)
    try:
        while e.state()['intro'] > 84:
            e.run(1)
        if during_victory:
            e.run(100)
            win_round(e, 0, Monitor())
            e.run(42)
        tap(e, 'start')
        check(e.state()['paused'] == 1, 'Start pauses presentation')
        snapshot = e.state()
        pages = actor_payloads(e)
        effect = oam(e)[69]
        e.run(24, p1=['y','x'], p2=['l','r'])
        frozen = e.state()
        check(all(frozen[k] == snapshot[k] for k in
                  ('intro','round_end','hp1','hp2','x1','x2','anim_frame1','anim_frame2'))
              and pages == actor_payloads(e) and effect == oam(e)[69],
              'Paused intro/victory freezes exact poses, signature accent and countdown',
              {'mode': mode, 'victory': during_victory})
        e.run(3)
        e.run(3, p1=['start','select'])
        e.run(3)
        check(not e.state()['paused'] and e.state()['round'] == snapshot['round'],
              'Start plus Select resumes without a Training reset')
        if snapshot['intro']:
            check(e.state()['intro'] > 0, 'Start plus Select preserves the paused intro')
        if mode == 2:
            # CPU Training's shoulders still own the existing level. They do
            # not drive gestures or attacks, including while intro is paused.
            tap(e, 'start')
            for _ in range(4):
                tap(e, 'down')
            check(trace(e,121) == 4, 'Existing paused dummy selector reaches CPU Training')
            level = ram(e, 'difficulty')
            tap(e, 'r', 1)
            check(ram(e, 'difficulty') == (level+1)%3,
                  'P2 R still changes the existing CPU Training level')
            e.run(3, p1=['l'], p2=['r'])
            e.run(3)
            check(ram(e, 'difficulty') == (level+1)%3,
                  'Opposite held Training shoulders still cancel across ports')
            tap(e, 'l')
            check(ram(e, 'difficulty') == level,
                  'P1 L still restores the existing CPU Training level')
            tap(e, 'start')
            tap(e, 'select')
            check(not e.state()['intro'] and not e.state()['round_end']
                  and e.state()['hp1'] == 128 and e.state()['hp2'] == 128,
                  'Live Training Select skips presentation through the existing reset path')
        tap(e, 'start')
        tap(e, 'select')
        e.run(8)
        check(trace(e,119) == 1 and trace(e,120) == 0,
              'Existing Controls guide builds normally during presentation pause')
        e.run(3, p1=['a','b'])
        for _ in range(120):
            if e.state()['screen'] == 1 and ram(e, 'screen') == 1:
                break
            e.run(1)
        check(e.state()['screen'] == 1, 'Pause B returns to roster normally')
    finally:
        e.close()


def contact_sheet(rows, beats, label):
    width, height = 220+beats*104, 40+len(rows)*108
    sheet = Image.new('RGB', (width, height), '#101829')
    draw = ImageDraw.Draw(sheet)
    draw.text((12,12), 'NATIVE SNES PPU / '+label+' / chronological beats, original 1:1 crops', fill='#ffdb45')
    for fighter, images in enumerate(rows):
        y = 40+fighter*108
        draw.text((12,y+23), NAMES[fighter], fill='#ffdb45')
        draw.text((12,y+42), TITLES[fighter], fill='white')
        for beat, image in sorted(images.items()):
            sheet.paste(image, (220+beat*104, y+20))
            draw.text((224+beat*104,y+4), str(beat+1), fill='white')
    path = OUT / (label.lower()+'-all12.png')
    sheet.save(path)
    return path.relative_to(ROOT).as_posix()


def static_audit():
    combined = combined_contract(ROOT)
    check(True, 'Strict combined asset/source/native preservation policy passes')
    check(SYMS['personalityIntroFrames'] >= 0x7f0448 and
          SYMS['personalityVictoryFrames'] == SYMS['personalityIntroFrames']+48,
          'Personality tables retain 132 contiguous bytes inside combined appended data')
    assets = subprocess.check_output(['git','diff',BASE,'--name-only','--','assets/generated'], cwd=ROOT).decode().splitlines()
    fighter_assets = [path for path in assets if re.search(
        r'/(fighter|portrait|character-manifest)', path)]
    check(not fighter_assets, 'Every approved fighter bank, palette, portrait and native strip is unchanged', fighter_assets)
    sections = []
    for name, address in SYMS.items():
        if name.startswith('SECTIONSTART_.personality'):
            end = SYMS[name.replace('SECTIONSTART_', 'SECTIONEND_', 1)]
            check(address >> 16 == end >> 16 and address & 65535 >= 0x8000,
                  'Native personality function fits one 32 KiB LoROM bank', name)
            sections.append({'name':name,'start':f'{address:06X}','end':f'{end:06X}','bytes':end-address})
    return {'combined_contract': combined, 'personality_new_mutable_bytes':0,
            'all_generated_changes_from_base':assets,
            'initialized_constant_bytes':132, 'native_sections':sections}


def paired_behavior(baseline_rom):
    # The same physical input at every sampled tick must give the same
    # simulation/outcome. Animation and cosmetic effect state are excluded.
    keys = ('hp1','hp2','x1','x2','y1','y2','energy1','energy2','action1','action2',
            'intro','round_end','wins1','wins2','seconds','round','hitstop')
    def record(rom):
        e = boot(5, mode=1, rom=rom)
        result = []
        try:
            while e.state()['intro'] > 106:
                e.run(1)
            for tick in range(1000):
                s = e.state()
                controls = []
                if not s['intro'] and not s['round_end']:
                    controls = ['right'] if abs(s['x1']-s['x2']) > 40*16 else (
                        ['a'] if tick%40 < 4 else [])
                e.run(1, p1=controls)
                result.append(tuple(e.state()[key] for key in keys))
            return result
        finally:
            e.close()
    base = record(baseline_rom)
    candidate = record(None)
    mismatch = next((i for i,(a,b) in enumerate(zip(base,candidate)) if a != b), None)
    check(mismatch is None, '1,000 paired controller ticks preserve intro, combat and round outcomes', mismatch)
    return {'baseline_sha256':hashlib.sha256(baseline_rom.read_bytes()).hexdigest(),
            'paired_ticks':len(base),'fields':keys,'first_mismatch':mismatch}


def progression_probes():
    e = boot(0)
    try:
        e.run(120)
        # An untouched healthy timeout is a real DRAW, without either side
        # receiving a victory flourish or a medal.
        for _ in range(6100):
            if e.state()['round_end']:
                break
            e.run(1)
        check(e.state()['round_end'] == 180 and e.state()['hp1'] == 128
              and e.state()['hp2'] == 128 and e.state()['seconds'] == 0,
              'Controller-neutral healthy timeout still resolves at the normal duration')
        e.run(48)
        check(e.state()['wins1'] == 0 and e.state()['wins2'] == 0
              and e.state()['anim_frame1'] in (10,41)
              and e.state()['anim_frame2'] in (10,41) and oam(e)[69][0] >= 256,
              'DRAW keeps the native non-winner poses and has no winner accent')
    finally:
        e.close()
    e = boot(0)
    try:
        e.run(120)
        win_round(e,0,Monitor())
        e.run(180+120)
        win_round(e,0,Monitor())
        e.run(180)
        for _ in range(120):
            if e.state()['screen'] == 4 and ram(e,'screen') == 4:
                break
            e.run(1)
        check(e.state()['screen'] == 4 and e.state()['wins1'] == 2,
              'A real two-round victory reaches the ordinary result screen')
        check(all(entry[0] >= 256 or entry[1] >= 224 for entry in oam(e)),
              'Result transition clears actors and borrowed signature sprite')
        tap(e,'a')
        for _ in range(120):
            if e.state()['screen'] == 3 and ram(e,'screen') == 3:
                break
            e.run(1)
        check(e.state()['screen'] == 3 and e.state()['intro'] > 0,
              'Result A starts a fresh match with the individual intro')
    finally:
        e.close()


def bank_audit():
    sdk = Path(os.environ.get('PVSNESLIB_HOME', ROOT/'.tools/sdk/pvsneslib'))
    folder = ROOT/'build/v022-personality'
    folder.mkdir(parents=True, exist_ok=True)
    output = folder/'bank-audit.sfc'
    result = subprocess.run([str(sdk/'devkitsnes/bin/wlalink.exe'),'-d','-s','-v','-A','-c',
                             '-L',str(sdk/'pvsneslib/lib/LoROM_FastROM'),
                             str(ROOT/'build/linkfile'),str(output)],
                            cwd=ROOT,capture_output=True,text=True,check=True)
    log = result.stdout+result.stderr
    (folder/'banks.log').write_text(log,encoding='utf-8',newline='\n')
    check(output.read_bytes() == (ROOT/'dist/abaqus-after-hours.sfc').read_bytes(),
          'Verbose native bank audit reproduces the exact tested cartridge')
    free = [(int(bank),int(count)) for bank,count in
            re.findall(r'ROM bank (\d+) \((\d+) bytes',log)]
    total = re.search(r'ROM: (\d+) bytes',log)
    check(len(free) == 128 and total is not None, 'All 128 native ROM bank allocations were inspected')
    return {'rom_free_bytes':int(total[1]),
            'completely_free_banks':[bank for bank,count in free if count == 32768],
            'free_bytes_by_bank':dict(free)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline-rom', type=Path)
    args = parser.parse_args()
    start = time.monotonic()
    OUT.mkdir(parents=True, exist_ok=True)
    report = {'status':'failed', 'rom_sha256':hashlib.sha256((ROOT/'dist/abaqus-after-hours.sfc').read_bytes()).hexdigest(),
              'symbols_sha256':hashlib.sha256((ROOT/'dist/abaqus-after-hours.sym').read_bytes()).hexdigest(),
              'version':json.loads((ROOT/'dist/manifest.json').read_text(encoding='utf-8'))['version'],
              'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'native_source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                                      for name in ('src/game.c','src/fighter_personality.h', 'src/animation_weight.h',
                                                   'tools/expansion_contracts.py', 'tools/emulator.py')},
              'core_sha256':hashlib.sha256((ROOT/'.tools/core/snes9x_libretro.dll').read_bytes()).hexdigest(),
              'host_contract':{'headless':True,'controller_only':True,'save_states':False,
                               'memory_writes':False,'audio_playback':False},
              'checks':checks,'roster':[]}
    intro_rows, victory_rows = [], []
    try:
        report['static_audit'] = static_audit()
        check(len(set(INTROS)) == 12 and len(set(VICTORIES)) == 12,
              'Every fighter has different intro and victory frame choreography')
        for fighter in range(12):
            e = boot(fighter, fighter%3)
            monitor = Monitor()
            try:
                intro, images = verify_intro(e, fighter, monitor)
                intro_rows.append(images)
                # Observe idle combat too: the presentation must never leave
                # an accent or override the live animation/attack dispatcher.
                for _ in range(120):
                    e.run(1)
                    monitor.sample(e, strict=True)
                side = fighter%2
                ticks = win_round(e, side, monitor)
                victory, images = verify_victory(e, fighter, side, monitor)
                victory_rows.append(images)
                monitor.verify(NAMES[fighter])
                report['roster'].append({'id':fighter,'name':NAMES[fighter],'gesture':TITLES[fighter],
                                         'winner_side':side+1,'intro_frames':list(intro.values()),
                                         'victory_frames':list(victory.values()),'controller_ko_ticks':ticks,
                                         'native_budget':monitor.summary()})
                print(NAMES[fighter]+' native intro/victory verified', flush=True)
            finally:
                e.close()
        report['contact_sheets'] = [contact_sheet(intro_rows,4,'INTRO'),
                                     contact_sheet(victory_rows,7,'VICTORY')]
        pause_probe(1)
        pause_probe(1, during_victory=True)
        pause_probe(2)
        progression_probes()
        if args.baseline_rom:
            report['paired_baseline'] = paired_behavior(args.baseline_rom)
        report['linker_budget'] = bank_audit()
        report['captures'] = [{'file':path.relative_to(ROOT).as_posix(),
                               'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
                              for path in sorted(OUT.glob('*.png'))]
        report['status'] = 'passed'
    finally:
        report['passed'] = sum(item['passed'] for item in checks)
        report['seconds'] = round(time.monotonic()-start,3)
        REPORT.write_text(json.dumps(report,indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({'status':report['status'],'passed':report['passed'],
                      'rom_sha256':report['rom_sha256'],'seconds':report['seconds']}),flush=True)


if __name__ == '__main__':
    main()
