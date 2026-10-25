"""Earn both office bonuses with controllers on the real cartridge, silently.

No emulated-memory writes, save states, fixtures, GUI or audio playback.
Default Snes9x coverage: every hero through both bonuses, hero0 to Champion.
Accuracy may select a smaller explicit roster while retaining earned routes.
Use --combined only after the parent freezes the six-feature v0.29 candidate;
its preservation oracle is parent-owned v029_contracts.validate, not old reports.
"""
from __future__ import annotations
import argparse
import ctypes as C
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from PIL import Image
from emulator import Emulator
from test_classic_menu import AccuracyMenu
from test_training import core_identity
from test_compatibility import verify_manifest_and_pinned_core
from test_champion import host_contract
from candidate_sources import snapshot
from v024_contracts import symbols
import test_presentation as presentation
import asset_cache

BASE = 'c7510c30e129465bcca0b32e2142daec60546d0f'
BONUS_OUTPUTS = {'assets/generated/bonus29-assets.json'} | {
    f'assets/generated/bonus29_{name}{suffix}' for name in ('printer', 'inbox')
    for suffix in ('.bin', '_pal.bin', '.png')}
CHECKS = {}
HEALTH = {'bonus_callbacks': 0, 'fight_callbacks': 0, 'max_spc_backlog': 0,
          'max_changed_actor_pages_per_bonus_callback': 0, 'failures': []}
MEDIA = []


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(ok, label, details=None):
    row = CHECKS.setdefault(label, {'check': label, 'passed': True, 'executions': 0})
    row['executions'] += 1
    if not ok:
        row.update(passed=False, details=details)
        raise AssertionError((label, details))


def preservation(syms, combined=False):
    # This feature-specific budget remains mandatory in both preservation modes.
    # Assert all four labels explicitly; a missing linked asset must not pass an
    # empty symbol scan. Parent validation owns the combined inventory policy.
    sections = []
    for name in ('bonus29_printer', 'bonus29_printer_pal', 'bonus29_inbox', 'bonus29_inbox_pal'):
        require(name in syms and name + '_end' in syms, 'Every bonus target/palette has linked bounds', name)
        start, end = syms[name], syms[name + '_end']
        size = 32 if name.endswith('_pal') else 3840
        require(end - start == size and start >> 16 == (end - 1) >> 16,
                'Each bonus asset section stays within one LoROM bank', [name, hex(start), hex(end)])
        require((ROOT / 'assets/generated' / (name + '.bin')).stat().st_size == size,
                'Native bonus target/palette retains its exact upload budget', [name, size])
        sections.append({'name': name, 'start': start, 'end': end, 'bytes': size})
    require(sum(row['bytes'] for row in sections) == 7744, 'Bonus asset ROM budget remains 7744 bytes')
    if combined:
        from v029_contracts import validate
        result = validate(ROOT)
        generated = result['generated']
        require(generated['baseline_count'] == 226 and generated['current_count'] == 237,
                'Combined candidate has the parent-reviewed exact 237 generated files', generated['current_count'])
        added = {row['path'] for row in generated['added']}
        require(len(added) == 11 and BONUS_OUTPUTS <= added,
                'Combined inventory includes all seven bonus outputs alongside four arena outputs', sorted(added))
        return {'mode': 'combined', 'validator': 'v029_contracts.validate',
                'contract': result, 'bonus_outputs': sorted(BONUS_OUTPUTS), 'bonus_asset_sections': sections}
    changed = []; count = 0
    archived = subprocess.check_output(['git', 'archive', BASE, 'assets/generated', 'src/hardware.asm', 'src/trace.asm'], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archived)) as archive:
        for item in archive:
            if not item.isfile():
                continue
            before = archive.extractfile(item).read(); after = (ROOT / item.name).read_bytes()
            if Path(item.name).suffix in ('.h', '.asm', '.json'):
                before = before.replace(b'\r\n', b'\n'); after = after.replace(b'\r\n', b'\n')
            count += item.name.startswith('assets/generated/')
            if before != after:
                changed.append(item.name)
    require(count == 226 and set(changed) == {'assets/generated/assets.h', 'assets/generated/data.asm'},
            'All 224 prior generated art/audio/metadata payloads and hardware/trace assembly stay exact', changed)
    old = symbols(subprocess.check_output(['git', 'show', BASE + ':dist/abaqus-after-hours.sym'], cwd=ROOT).decode())
    ram = lambda value: value < 0x2000 or 0x7e0000 <= value < 0x800000
    prior = {name: value for name, value in old.items() if ram(value)}
    markers = {'SECTIONEND_globram.data', 'RAM_USAGE_SLOT_3_BANK_127_END'}
    moved = {name: [value, syms.get(name)] for name, value in prior.items() if syms.get(name) != value}
    added = {name: value for name, value in syms.items() if ram(value) and name not in prior}
    expected = {'v29DefenseState', 'v29BonusState', 'v29AutoState', 'v29RandomState', 'v29AudioState', 'v29ArenaState'}
    require(set(moved) == markers and all(new == old + 176 for old, new in moved.values()),
            'Only the two RAM end markers grow by the parent-reserved 176 bytes', moved)
    require(set(added) == expected, 'No mutable variable outside the six parent reservations', added)
    for name, address in syms.items():
        if name.startswith('bonus29_') and name.endswith('_end'):
            start = syms[name[:-4]]
            require(address - start in (32, 3840) and (start >> 16) == ((address - 1) >> 16),
                    'Each bonus asset section stays within one LoROM bank', [name, hex(start), hex(address)])
    known = set(subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASE, 'assets/generated'], cwd=ROOT, text=True).splitlines())
    current = {p.relative_to(ROOT).as_posix() for p in (ROOT / 'assets/generated').iterdir() if p.is_file() and p.name != 'soundbank.h'}
    extra = current - known
    expected_extra = {'assets/generated/bonus29-assets.json'} | {
        f'assets/generated/bonus29_{name}{suffix}' for name in ('printer', 'inbox') for suffix in ('.bin', '_pal.bin', '.png')}
    require(extra == expected_extra and not known - current, 'Exactly seven bonus outputs append to the 226-file inventory', sorted(extra))
    return {'baseline': BASE, 'old_generated': count, 'preserved_old_payloads': count - len(changed),
            'changed_declarations': changed, 'new_outputs': sorted(extra), 'old_variable_addresses_preserved': len(prior) - 2,
            'ram_markers': moved, 'parent_reservations': added, 'hardware_trace_exact': True}


class Rig:
    def __init__(self, core, syms, captures):
        # Snes9x's default frontend rejects simultaneous opposites. This
        # documented frontend option lets the native cancellation see both.
        self.host = AccuracyMenu() if core == 'accuracy' else Emulator(core_options={'snes9x_up_down_allowed': 'enabled'})
        self.syms = syms; self.core = core; self.captures = captures
        self.callbacks = 0; self.bonus_upload_rows = 0
        self.meter_verified = False

    def read(self, name, size=1):
        return int.from_bytes(C.string_at(self.host.ram + (self.syms[name] & 0x1ffff), size), 'little')

    def bonus(self):
        raw = C.string_at(self.host.ram + (self.syms['v29BonusState'] & 0x1ffff), 64)
        result = dict(zip(('seen', 'variant', 'result', 'paused', 'seconds', 'subtick', 'progress', 'target',
                          'action', 'tick', 'connected', 'pose', 'old_pose', 'walk', 'flash', 'face'), raw))
        result.update({name: int.from_bytes(raw[offset:offset + 2], 'little', signed=True)
                       for name, offset in (('x', 16), ('y', 18), ('vy', 20))})
        result.update(result_ticks=raw[22], goal=raw[23], stage=raw[24], hits=raw[25], buttons=raw[26], armed=raw[27])
        return result

    def state(self):
        return self.host.state()

    def counters(self):
        return [self.read(name, 2) for name in ('frame', 'snes_vblank_count', 'lag_frame_counter')]

    def actor_pages(self):
        pointer = self.host.core.retro_get_memory_data(3)
        return [C.string_at(pointer + offset, 5120) for offset in (0xc000, 0xd400)]

    def run(self, count=1, p1=(), p2=()):
        for _ in range(count):
            before = self.read('screen'); trace_before = self.state(); counters = self.counters()
            pages = self.actor_pages() if before == trace_before['screen'] == 5 else None
            samples = self.host.audio_samples
            self.host.run(1, p1=p1, p2=p2); self.callbacks += 1
            after = self.read('screen'); state = self.state()
            steady_bonus = before == after == trace_before['screen'] == state['screen'] == 5
            steady_fight = before == after == trace_before['screen'] == state['screen'] == 3 and not trace_before['intro'] and not state['intro']
            if steady_bonus or steady_fight:
                delta = [(a - b) & 65535 for a, b in zip(self.counters(), counters)]
                HEALTH['bonus_callbacks' if steady_bonus else 'fight_callbacks'] += 1
                if delta != [1, 1, 0]:
                    HEALTH['failures'].append({'screen': before, 'callback': self.callbacks, 'delta': delta, 'bonus': self.bonus()})
                require(delta == [1, 1, 0], 'Every steady native callback advances one game tick/vblank with zero SDK lag', HEALTH['failures'][-1:] or None)
                stat = int.from_bytes(C.string_at(self.host.ram + 0x1ff00 + 228, 2), 'little')
                require(not (stat & 0xc0), 'STAT77 reports neither OBJ range nor time overflow', stat)
                require(self.host.audio_samples > samples, 'PCM advances on every steady native callback')
                backlog = (self.read('spc_fwrite') - self.read('spc_fread')) & 255
                HEALTH['max_spc_backlog'] = max(HEALTH['max_spc_backlog'], backlog)
                require(backlog <= 6, 'Resident SPC FIFO stays at six or fewer queued bytes', backlog)
                if steady_fight and not self.meter_verified and self.read('hudEnergy', 2) == 0x6060 and not self.read('hudDirty'):
                    memory = presentation.vram_bytes(self.host)
                    cells = [presentation.map_tile(memory, x + i, 4) for x in (1, 22) for i in range(9)]
                    expected = [(ord(character) + 256) | 0x2400 for _ in range(2) for character in 'SUPER Y+B']
                    require(cells == expected, 'Both full-meter hints preserve their exact opaque glyphs and gold attributes')
                    self.meter_verified = True
                if steady_bonus:
                    updated = self.actor_pages()
                    changed = sum(a != b for a, b in zip(pages, updated))
                    HEALTH['max_changed_actor_pages_per_bonus_callback'] = max(HEALTH['max_changed_actor_pages_per_bonus_callback'], changed)
                    require(changed <= 1 and pages[1] == updated[1],
                            'Only one actor page can change per bonus callback; target never receives live DMA')
        return self.state()

    def until(self, predicate, limit=600, label='Expected native state arrives'):
        for _ in range(limit):
            if predicate():
                return
            self.run()
        raise AssertionError((label, self.state(), self.bonus()))

    def pulse(self, key, port=0, settle=8):
        self.run(3, **({'p1': [key]} if port == 0 else {'p2': [key]})); self.run(settle)

    def capture(self, name):
        path = self.captures / self.core / (name + '.png'); path.parent.mkdir(parents=True, exist_ok=True)
        self.host.frame.save(path)
        MEDIA.append({'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path.read_bytes())})

    def text(self, y, text):
        x = (32 - len(text)) // 2
        memory = presentation.vram_bytes(self.host)
        wrong = []
        for offset, character in enumerate(text):
            entry = presentation.map_tile(memory, x + offset, y)
            if entry != (ord(character) + 256) | 0x2000:
                wrong.append([offset, character, hex(entry)])
            tile = memory[0x8000 + (ord(character) + 256) * 32:0x8000 + (ord(character) + 257) * 32]
            expected = presentation.tile_rgb(tile, (ROOT / 'assets/generated/ui_pal.bin').read_bytes()[:32])
            actual = self.host.frame.crop(((x + offset) * 8, y * 8, (x + offset + 1) * 8, y * 8 + 8))
            delta = presentation.image_delta(actual, expected)
            if delta['max_channel_delta'] > 3:
                wrong.append([offset, 'PPU', delta])
        require(not wrong, 'Actual native glyph map and rendered PPU text match the bonus instructions/result', [text, wrong[:3]])

    def boot(self, hero=0, mode=0):
        self.run(120); self.pulse('l')  # ordinary Easy menu preference
        for _ in range(mode):
            self.pulse('down')
        self.pulse('a'); self.until(lambda: self.read('screen') == 1)
        for _ in range(hero):
            self.pulse('right')
        self.pulse('a', settle=25)
        if mode:
            self.pulse('a', settle=25)
        self.until(lambda: self.read('screen') == 2)
        self.pulse('a'); self.until(lambda: self.read('screen') == self.state()['screen'] == 3)

    def live(self):
        if self.read('arcadeStoryTicks', 2):
            self.pulse('a', settle=2)
        self.until(lambda: self.read('intro') == 0, 500)
        self.run(5)

    def play(self, lose=False, policy='close'):
        self.live()
        for _ in range(16000):
            if self.read('screen') == 4:
                self.until(lambda: self.state()['screen'] == 4); self.run(8)
                return {'wins': [self.state()['wins1'], self.state()['wins2']], 'arcade': self.read('arcade'), 'controller_policy': policy}
            s = self.state()
            forward = 'right' if s['x1'] < s['x2'] else 'left'
            back = 'left' if forward == 'right' else 'right'
            distance = abs(s['x1'] - s['x2']) // 16
            if s['intro'] or s['round_end'] or s['hitstop']:
                self.run()
            elif lose:
                self.run(p1=[forward])
            elif s['action1']:
                self.run(p1=[forward])
            elif policy == 'jump-in' and s['y1'] >= 32768:
                self.run(3, p1=[forward, 'a'] if distance < 62 and s['y1'] < 65536 - 16 else [forward])
            elif policy == 'jump-in' and (distance > 38 or (s['wave2'] and s['wave_low2'])):
                self.run(3, p1=[forward, 'up'])
            elif s['action2'] and distance < 55:
                self.run(p1=[back, 'down'] if 4 <= s['action2'] <= 6 else [back])
            # At the observed 32px spacing, a short-range hero must try X
            # rather than walk forever. Native input chooses a legal throw
            # only strictly inside its cap, otherwise the ordinary strong
            # punch; retain exact fixed-point boundary and all tick limits.
            elif abs(s['x1'] - s['x2']) > max(s['throw_range1'], 32) * 16:
                self.run(p1=[forward])
            else:
                self.run(3, p1=[forward, 'x']); self.run(p1=[forward])
        raise AssertionError(('Bounded ordinary CPU match did not finish', self.state()))

    def verify_target(self, variant):
        memory = presentation.vram_bytes(self.host)
        name = 'bonus29_inbox' if variant else 'bonus29_printer'
        target = (ROOT / 'assets/generated' / (name + '.bin')).read_bytes()
        actual = b''.join(memory[0xd400 + row * 512:0xd400 + row * 512 + 384] for row in range(10))
        require(actual == target, 'Original imagegen target fills only the reused actor1 VRAM page', name)
        map_bytes = (ROOT / 'assets/generated/stage2_map.bin').read_bytes()
        require(memory[0x7000:0x8000] == map_bytes,
                'BONUS preserves the complete approved office map including the old ambient address')
        gfx = (ROOT / 'assets/generated/stage2_tiles.bin').read_bytes()
        require(memory[:len(gfx)] == gfx, 'BONUS preserves every detailed office scenery/floor tile')
        # The target is initially isolated from the hero. Its actual rendered
        # silhouette must match the decoded native sprite over the office.
        palette = (ROOT / 'assets/generated' / (name + '_pal.bin')).read_bytes()
        target_pixels = []
        for ty in range(10):
            for tx in range(12):
                block = target[(ty * 12 + tx) * 32:(ty * 12 + tx + 1) * 32]
                ids = presentation.tile_indices(block)
                for pixel, value in enumerate(ids):
                    if value:
                        rgb = presentation.snes_rgb(int.from_bytes(palette[value * 2:value * 2 + 2], 'little'))
                        x, y = tx * 8 + pixel % 8, ty * 8 + pixel // 8
                        actual = self.host.frame.getpixel((154 + x, 121 + y))
                        target_pixels.append(max(abs(a - b) for a, b in zip(rgb, actual)))
        require(len(target_pixels) > 2500 and max(target_pixels) <= 3,
                'Actual PPU shows the complete original printer/inbox silhouette and palette', [name, len(target_pixels), max(target_pixels)])

    def bonus_route(self, hero, variant, outcome):
        self.until(lambda: self.read('screen') == self.state()['screen'] == 5)
        self.run(6)
        b = self.bonus(); seen = 1 if variant == 0 else 3
        require(b['seen'] == seen and b['variant'] == variant and b['result'] == 0,
                'Only earned milestones 3/7 start the proper automatic bonus', b)
        require(self.read('arcade') == (6 if variant else 2), 'BONUS retains the just-won ladder index until its single handoff')
        self.verify_target(variant)
        require(b['action'] == 0 and b['progress'] == 0 and b['armed'] == 1,
                'Held result confirmation cannot become an automatic opening bonus attack')
        self.text(0, 'OFFICE BONUS'); self.text(1, 'INBOX OVERLOAD' if variant else 'PRINTER JAM')
        self.text(26, 'MOVE + Y/X PUNCH B/A KICK'); self.text(27, 'START PAUSE  SELECT SKIP')
        if hero in (0, 11) or self.core == 'accuracy':
            self.capture(f'hero{hero:02}-bonus{variant + 1}-start')
        # Whiff and held edge: B must be a light kick, never a menu-back route.
        # Accuracy's callback can precede the next native pad-scan phase.
        # Use the same three-callback held pulse as the existing native suites;
        # all per-callback frame/vblank/lag/OBJ/SPC assertions stay strict.
        self.run(); self.run(3, p1=['b'])
        require(self.bonus()['action'] == 4 and self.read('screen') == 5,
                'B is a live light kick in BONUS')
        self.run(36, p1=['b'])
        require(self.bonus()['progress'] == 0 and self.bonus()['action'] == 0,
                'An out-of-range miss earns nothing and a held face button does not auto-repeat')
        self.run()
        # Real jump physics/approved airborne poses and opposite movement.
        original_x = self.bonus()['x']
        self.run(8, p1=['left', 'right'])
        require(self.bonus()['x'] == original_x, 'Opposing horizontal directions cancel in BONUS')
        self.run(3, p1=['up'])
        require(self.bonus()['y'] < 0, 'The selected hero can jump through ordinary controller input')
        self.until(lambda: self.bonus()['y'] == 0, 150)
        # Pause priority, both ports, held controls, and resume-edge disposal.
        self.run(3, p1=['start', 'select', 'a'])
        require(self.bonus()['paused'] == 1 and self.bonus()['result'] == 0, 'Start owns simultaneous skip/attack')
        self.run(8)
        self.text(10, 'BONUS PAUSED')
        frozen = self.bonus()
        self.run(45, p1=['right', 'a', 'b', 'x', 'y', 'up'], p2=['right', 'b'])
        require(self.bonus() == frozen, 'Pause freezes timer, target, actor, action and progress despite held inputs')
        if hero == 0:
            self.capture(f'hero00-bonus{variant + 1}-paused')
        self.run(3, p2=['start']); self.run(2)
        require(not self.bonus()['paused'] and self.bonus()['action'] == 0, 'P2 Start resumes without converting held attacks into an action')
        self.run(3, p2=['x', 'a', 'b', 'y'])
        require(self.bonus()['action'] == 0, 'P2 face attacks do not drive the solo bonus hero')
        if outcome == 'skip':
            self.pulse('start', settle=2)
            self.pulse('select', port=hero % 2, settle=4)
            require(self.bonus()['result'] == 3 and not self.bonus()['paused'], 'Fresh Select skips even a paused optional challenge without touching the ladder')
        elif outcome == 'timeout':
            self.until(lambda: self.bonus()['result'] != 0, 1000)
            require(self.bonus()['result'] == 2 and self.bonus()['seconds'] == 0,
                    'A complete native countdown times out safely')
        else:
            buttons = ['y', 'b', 'x', 'a']
            used = set(); attempts = 0
            for _ in range(1100):
                b = self.bonus()
                if b['result']:
                    break
                delta = b['target'] - b['x'] // 16
                if b['action']:
                    self.run()
                elif abs(delta) > 48:
                    self.run(p1=['right' if delta > 0 else 'left'])
                else:
                    # All four are exercised once, then strong attacks finish.
                    key = buttons[attempts] if attempts < 4 else ('x' if attempts % 2 else 'a')
                    used.add(key); attempts += 1
                    self.run(3, p1=[key]); self.run()
            require(self.bonus()['result'] == 1 and self.bonus()['progress'] == self.bonus()['goal'],
                    'Movement and real four-button attacks clear the challenge before timeout', self.bonus())
            require(used == {'a', 'b', 'x', 'y'} and self.bonus()['buttons'] == 15 and self.bonus()['stage'] == 2,
                    'All four attacks and both rolling-target relocations are playable', [used, self.bonus()])
        self.run(8)
        result = self.bonus()
        self.text(10, ('INBOX ZERO!' if variant else 'JAM CLEARED!') if outcome == 'success' else
                  ('TIME! THE SHIFT GOES ON' if outcome == 'timeout' else 'SKIPPED - ONWARD!'))
        if hero in (0, 1, 2, 11) or self.core == 'accuracy':
            self.capture(f'hero{hero:02}-bonus{variant + 1}-{outcome}')
        pending_arcade = 7 if variant else 3
        if hero == 0:
            self.pulse('start', settle=2)
            left = self.bonus()['result_ticks']
            self.run(30, p1=['a', 'b', 'x', 'y'])
            require(self.bonus()['result_ticks'] == left and self.read('screen') == 5,
                    'Bonus result can be paused and face buttons cannot dismiss it or return to roster')
            self.pulse('start', port=1, settle=2)
        # Held A/B cannot dismiss or attack through the automatic result.
        self.until(lambda: self.read('screen') == 3, 130)
        self.until(lambda: self.state()['screen'] == 3)
        require(self.read('arcade') == pending_arcade and self.state()['fighter_id2'] == (hero + 1 + pending_arcade) % 12,
                'Success/timeout/skip automatically loads exactly the correct next ladder opponent', self.state())
        require(self.bonus()['seen'] == seen, 'Earned bonus markers survive normal combat handoff')
        self.live(); self.run(12)
        memory = presentation.vram_bytes(self.host)
        fighter = self.state()['fighter_id2']
        suffixes = ('', 'b', 'c', 'd', 'e', 'f', 'g', 'h')
        approved = {raw[pos:pos + 3840] for suffix in suffixes
                    for raw in [(ROOT / f'assets/generated/fighter{fighter:02}{suffix}.bin').read_bytes()]
                    for pos in range(0, 30720, 3840)}
        actual = b''.join(memory[0xd400 + row * 512:0xd400 + row * 512 + 384] for row in range(10))
        require(actual in approved, 'Next combat restores actor1 from approved opponent art, replacing the bonus target')
        return {'variant': variant, 'outcome': outcome, 'result': result,
                'next_arcade': pending_arcade, 'next_opponent': self.state()['fighter_id2']}

    def close(self):
        self.host.close()


def traversal(args, syms, outcome='success'):
    cases = []
    for hero in args.fighters:
        rig = Rig(args.core, syms, args.captures)
        try:
            rig.boot(hero)
            result = {'hero': hero, 'matches': [], 'bonuses': [], 'champion': False}
            end = 11 if hero == args.champion_hero else args.through
            shift = 0
            while shift < end:
                require(rig.read('arcade') == shift and rig.state()['fighter_id2'] == (hero + 1 + shift) % 12,
                        'Every real Arcade opponent remains in original order', [hero, shift, rig.state()])
                if hero == args.champion_hero and shift in (2, 3, 6):
                    lost = rig.play(lose=True)
                    require(lost['wins'][1] == 2 and rig.read('resultWin') == 0,
                            'Controller-only losses are earned before both milestones and after the first bonus')
                    seen = rig.bonus()['seen']; rig.pulse('a'); rig.until(lambda: rig.read('screen') == 3)
                    require(rig.read('arcade') == shift and rig.bonus()['seen'] == seen,
                            'Continue retries the same opponent without repeating the earned bonus')
                attempts = []
                for attempt in range(16):
                    policy = 'close' if attempt == 0 else 'jump-in'
                    match = rig.play(policy=policy); attempts.append(match)
                    print(json.dumps({'core': args.core, 'hero': hero, 'shift': shift + 1,
                                      'attempt': attempt + 1, **match}), flush=True)
                    if match['wins'][0] == 2:
                        break
                    require(rig.read('screen') == 4 and rig.read('arcade') == shift,
                            'Loss never advances a bonus milestone or the ladder')
                    rig.pulse('a'); rig.until(lambda: rig.read('screen') == 3)
                require(attempts[-1]['wins'][0] == 2, 'Player earns each milestone with actual two-round Arcade wins', [hero, shift, attempts])
                result['matches'].append({'shift': shift + 1, 'opponent': rig.state()['fighter_id2'], 'attempts': attempts})
                if shift == 10:
                    require(rig.read('champion') == 1 and rig.read('screen') == 4 and rig.bonus()['seen'] == 3,
                            'All eleven opponents and the earned Champion ending survive both optional bonuses')
                    rig.text(2, 'OFFICE CHAMPION')
                    rig.capture(f'hero{hero:02}-champion'); result['champion'] = True; break
                rig.run(3)
                # Keep the confirmation held across the forced-blank loader.
                rig.run(3, p1=['a'])
                rig.until(lambda: rig.read('screen') in (3, 5))
                if shift in (2, 6):
                    variant = int(shift == 6)
                    rig.run(24, p1=['a'])
                    require(rig.bonus()['action'] == 0 and rig.bonus()['progress'] == 0 and rig.bonus()['armed'] == 0,
                            'Result confirmation held through BONUS entry cannot attack or earn progress')
                    result['bonuses'].append(rig.bonus_route(hero, variant, outcome))
                else:
                    require(rig.read('screen') == 3, 'No bonus interrupts other Arcade result handoffs')
                    rig.until(lambda: rig.state()['screen'] == 3)
                shift += 1
                print(json.dumps({'core': args.core, 'hero': hero, 'earned_shift': shift,
                                  'bonus_count': len(result['bonuses'])}), flush=True)
            require(0 < rig.host.audio_peak < 32767, 'Captured native PCM stays active and unclipped', rig.host.audio_peak)
            result.update(callbacks=rig.callbacks, audio_peak=rig.host.audio_peak)
            cases.append(result)
        finally:
            rig.close()
    return cases


def other_modes(args, syms):
    rows = []
    for mode in (1, 2):
        rig = Rig(args.core, syms, args.captures)
        try:
            rig.boot(0, mode); rig.live()
            for _ in range(90):
                rig.run(p1=['right', 'b'], p2=['left', 'b'])
                require(rig.read('screen') == 3 and rig.bonus()['seen'] == 0,
                        'Local and Training stay entirely in their native fight mode')
            if mode == 1:
                result = rig.play()
                require(result['wins'][0] == 2, 'An ordinary Local match earns its native result')
                rig.pulse('a', port=1)
                rig.until(lambda: rig.read('screen') == 3)
                require(rig.bonus()['seen'] == 0, 'A P2 Local rematch never opens an Arcade bonus')
            rows.append({'mode': mode, 'native_live_callbacks': 90})
        finally:
            rig.close()
    return rows


def coverage(args, cases):
    require([case['hero'] for case in cases] == args.fighters,
            'Every requested current-ROM hero completes its real earned route')
    both = []; champions = []
    for case in cases:
        end = 11 if case['hero'] == args.champion_hero else args.through
        require(len(case['matches']) == end,
                'Each hero earns every requested ladder win without fixture shortcuts', [case['hero'], end])
        variants = [bonus['variant'] for bonus in case['bonuses']]
        require(variants == ([0, 1] if end >= 7 else [0]) and
                all(bonus['outcome'] == args.outcome for bonus in case['bonuses']),
                'Every requested current-ROM milestone proves its actual success/timeout/skip outcome',
                [case['hero'], variants, args.outcome])
        require(case['champion'] == (end == 11), 'Requested Champion route proves the earned ending', case['hero'])
        if variants == [0, 1]:
            both.append(case['hero'])
        if case['champion']:
            champions.append(case['hero'])
    return {'current_rom_only': True, 'historical_reports_used': False,
            'heroes': args.fighters, 'both_bonus_heroes': both, 'champion_heroes': champions,
            'all_twelve_both_bonuses': set(both) == set(range(12)), 'outcome': args.outcome,
            'earned_wins': sum(len(case['matches']) for case in cases),
            'bonus_rounds': sum(len(case['bonuses']) for case in cases)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core', choices=('snes9x', 'accuracy'), required=True)
    parser.add_argument('--combined', action='store_true',
                        help='Use parent v029_contracts.validate for the frozen six-feature v0.29 candidate')
    parser.add_argument('--fighters', default=','.join(map(str, range(12))))
    parser.add_argument('--through', type=int, choices=(3, 7), default=7)
    parser.add_argument('--champion-hero', type=int, default=0)
    parser.add_argument('--outcome', choices=('success', 'timeout', 'skip'), default='success')
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--captures', type=Path, default=ROOT / 'docs/screenshots/bonus-v029')
    args = parser.parse_args(); args.fighters = list(map(int, args.fighters.split(',')))
    if not args.fighters or len(set(args.fighters)) != len(args.fighters) or any(hero not in range(12) for hero in args.fighters):
        parser.error('--fighters must contain distinct hero IDs from 0 through 11')
    if args.champion_hero not in range(-1, 12):
        parser.error('--champion-hero must be -1 (disabled) or a hero ID from 0 through 11')
    args.captures = args.captures.resolve(); args.report = args.report.resolve()
    sources = snapshot(ROOT); producers = asset_cache.inputs(ROOT)
    syms = symbols((ROOT / 'dist/abaqus-after-hours.sym').read_text())
    manifest = json.loads((ROOT / 'dist/manifest.json').read_bytes())
    report = {'status': 'failed',
              'scope': 'combined v0.29 office bonus focused proof' if args.combined else 'isolated topic2 office bonus implementation',
              'preservation_mode': 'combined' if args.combined else 'isolated', 'version': manifest['version'], 'core': args.core,
              'source_inventory_sha256': sha(json.dumps(sources, sort_keys=True).encode()),
              'harness_sha256': sources['tools/test_bonus29.py'], 'root': str(ROOT),
              'requested_route': {'heroes': args.fighters, 'through': args.through,
                                  'champion_hero': args.champion_hero, 'outcome': args.outcome},
              'rom_sha256': manifest['sha256'], 'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'sources': sources, 'producer_inputs': producers, 'host': host_contract(),
              'memory_writes': False, 'save_states': False, 'combined_verification_claimed': False,
              'command': [sys.executable, *sys.argv]}
    started = time.monotonic()
    try:
        require(sha((ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()) == manifest['sha256'], 'Exact tested ROM matches its manifest')
        require(report['host']['logical_processors'] == [4, 5] and report['host']['priority_class'] == 0x4000,
                'Native jobs stay silently below normal on assigned CPU4/5', report['host'])
        report['core_identity'] = verify_manifest_and_pinned_core() if args.core == 'accuracy' else core_identity()
        report['preservation'] = preservation(syms, combined=args.combined)
        report['cases'] = traversal(args, syms, args.outcome)
        report['coverage'] = coverage(args, report['cases'])
        report['other_modes'] = other_modes(args, syms)
        require(snapshot(ROOT) == sources and asset_cache.inputs(ROOT) == producers,
                'Source, harness, encoder, art and dependency bytes stay frozen during proof')
        require(sha((ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()) == report['rom_sha256'], 'ROM bytes stay frozen during proof')
        require(not HEALTH['failures'] and HEALTH['bonus_callbacks'] > 0, 'All focused native cadence/health assertions pass', HEALTH)
        report['status'] = 'passed'
    except BaseException as error:
        report['error'] = repr(error)
        raise
    finally:
        report.update(health=HEALTH, checks=list(CHECKS.values()), passed=sum(x['executions'] for x in CHECKS.values() if x['passed']),
                      media=MEDIA, seconds=round(time.monotonic() - started, 3))
        args.report.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.report.with_suffix('.tmp'); temporary.write_bytes((json.dumps(report, indent=2) + '\n').encode())
        temporary.replace(args.report)
        print(json.dumps({k: report[k] for k in ('status', 'core', 'passed', 'seconds')}), flush=True)


if __name__ == '__main__':
    main()
