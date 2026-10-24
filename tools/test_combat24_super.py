"""Focused combined-ROM v0.24 super-art proof; controller-only native execution.

Run with canonical .tools Python through tools/run_background.py after an
asset build. Reuses the retained super gameplay fixtures without changing
their assertions or writing their reports. Owns only combat-24-super-report
and screenshots/combat24-super. No WRAM writes, save states, GUI or speakers.
"""
from pathlib import Path
import argparse
import ctypes as C
import hashlib
import io
import json
import platform
import re
import subprocess
import sys
import time

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import test_expansion_07_supers as legacy
from emulator import Emulator
from fighter_assets import HEIGHTS, SLUGS, extract_atlas
from release_evidence import EXPECTED_NATIVE_CORE
from expansion_contracts import combined_contract
from test_champion import host_contract
from test_characters import (actor_payload, boot, uploaded_frame_id,
                             verify_oam_geometry)

BASE = 'f75005d'
BASE_ROM_SHA = '057139801b64d1d486c91e18f456e01519dd4d25c3d0d6a92e61f311b99da3fd'
FRAME_OWNERS = {
    'attack-v1': {5, 6, 7, 8, 9, 10, 12, 13, 15, *range(32, 46), 47},
    'jump-v1': {29, 30, 31, *range(49, 56)},
    'super-v1': {1, 2, 4},
}
HARNESS = ('tools/test_combat24_super.py', 'tools/emulator.py', 'tools/test_characters.py',
           'tools/test_inputs.py', 'tools/test_expansion_07_supers.py', 'tools/pose_revision_assets.py',
           'tools/fighter_assets.py', 'tools/test_champion.py', 'tools/test_presentation.py',
           'tools/release_evidence.py', 'tools/run_background.py', 'tools/expansion_contracts.py',
           'tools/v024_contracts.py')
OUT = ROOT / 'docs/screenshots/combat24-super'
checks = []
captures = []
baseline_git = None
health = {'frames': 0, 'cadence_failures': [], 'obj_failures': [],
          'transfer_failures': [], 'audio_failures': [], 'phase_failures': [],
          'peak_spc_backlog': 0, 'actor_updates': [0, 0],
          'maximum_changed_actor_payload_bytes': 0}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_hashes():
    return {p.relative_to(ROOT).as_posix(): sha(p.read_bytes())
            for p in sorted((ROOT/'src').rglob('*')) if p.is_file()}


def git_file(path):
    global baseline_git
    if baseline_git is None:
        baseline_git = subprocess.Popen(['git', 'cat-file', '--batch'], cwd=ROOT,
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    baseline_git.stdin.write((BASE + ':' + path + '\n').encode())
    baseline_git.stdin.flush()
    header = baseline_git.stdout.readline().split()
    if len(header) != 3 or header[1] != b'blob':
        raise AssertionError(('baseline blob unavailable', path, header))
    raw = baseline_git.stdout.read(int(header[2]))
    if baseline_git.stdout.read(1) != b'\n':
        raise AssertionError(('baseline blob framing', path))
    return raw


def check(ok, label, detail=None):
    checks.append({'check': label, 'passed': bool(ok), 'detail': detail})
    if not ok:
        raise AssertionError((label, detail))


def combined_preservation():
    shared = combined_contract(ROOT)
    assets, native = shared['assets'], shared['native']
    check(assets['baseline_commit'] == native['baseline_commit'] == BASE,
          'independent combined policy uses approved v0.23.1 baseline')
    check(assets['generated_count'] == 226, 'combined generated inventory contains exactly 226 files')
    check(assets['frame_ownership'] == {k: sorted(v) for k, v in FRAME_OWNERS.items()} and
          sum(map(len, FRAME_OWNERS.values())) == len(set().union(*FRAME_OWNERS.values())) == 37,
          'three disjoint feature sets own 37 poses and preserve the other 27')
    check(len(assets['fighters']) == 12 and all(r['preserved_frames'] >= 27 for r in assets['fighters']),
          'all 27 unowned poses portraits palettes scales and original source masters remain exact')
    check(native['prior_ram_labels'] == native['unchanged_prior_ram_labels'] == 1318 and
          not native['documented_relocations'] and not native['appended_ram_symbols'],
          'all 1318 prior RAM labels unchanged with no additional mutable RAM', native)
    return shared


def art_contract(shared):
    index = json.loads((ROOT / 'assets/art/super-v1.json').read_bytes())
    manifest = json.loads((ROOT / 'assets/generated/character-manifest.json').read_bytes())
    rows = manifest['fighters'] if isinstance(manifest, dict) else manifest
    result = []
    gallery = Image.new('RGB', (384 * 2, 104 * 6), '#141c2c')
    draw = ImageDraw.Draw(gallery)
    for i, slug in enumerate(SLUGS):
        stem = f'assets/generated/fighter{i:02d}'
        old = Image.open(io.BytesIO(git_file(stem + '.png'))).convert('RGBA')
        new = Image.open(ROOT / (stem + '.png')).convert('RGBA')
        changed = [n for n in range(64) if old.crop((n*96, 0, (n+1)*96, 80)).tobytes() !=
                   new.crop((n*96, 0, (n+1)*96, 80)).tobytes()]
        owned_changed = sorted(set(changed) & FRAME_OWNERS['super-v1'])
        check(owned_changed == [1, 2, 4], 'exactly three super-owned frames differ', [i, owned_changed])
        check(set(changed) <= set().union(*FRAME_OWNERS.values()),
              'other changes are limited to approved attack and jump ownership', [i, changed])
        check(git_file(stem + '_pal.bin') == (ROOT / (stem + '_pal.bin')).read_bytes(),
              'approved fifteen-color OBJ palette is exact', i)
        for suffix, ext in (('', '.png'), ('-large', '.png'), ('_tiles', '.bin'), ('_pal', '.bin')):
            path = f'assets/generated/portrait{i:02d}{suffix}{ext}'
            check(git_file(path) == (ROOT/path).read_bytes(), 'portrait remains byte-identical', path)
        entry = next(r for r in index['fighters'] if r['id'] == i)
        prov = ROOT / entry['provenance']
        check(sha(prov.read_bytes()) == entry['provenance_sha256'], 'index pins provenance', i)
        record = json.loads(prov.read_bytes())
        check(sha((ROOT/record['reference']).read_bytes()) == record['reference_sha256'], 'reference pinned', i)
        check(record['palette_sha256'] == sha((ROOT/(stem+'_pal.bin')).read_bytes()), 'palette pinned', i)
        check(record['height_target'] == HEIGHTS[i], 'approved physical height target', i)
        source = record['sources'][0]
        check(source['frames'] == [None, 1, 2, 4, None, None, None, None], 'disjoint phase mapping', i)
        check(sha((ROOT/source['file']).read_bytes()) == source['sha256'] == record['raw_output_sha256'],
              'selected source is exact retained built-in raw output', i)
        figures, details = extract_atlas(ROOT/source['file'], pose_names=source['poses'], expected_count=8)
        scale = HEIGHTS[i] / figures[0].height
        converted = []
        for pose, n in ((1, 1), (2, 2), (3, 4)):
            meta = rows[i]['frames'][n]
            check(meta['conversion_scale'] == scale, 'one neutral-anchored isotropic conversion', [i, n])
            expected = [round(figures[pose].width*scale), round(figures[pose].height*scale)]
            box = new.crop((n*96, 0, (n+1)*96, 80)).getchannel('A').getbbox()
            check(box[3] == 78 and box[0] > 0 and box[2] < 96 and expected[0] <= 94 and expected[1] <= 77,
                  'safe canvas and grounded sole baseline', [i, n, box, expected])
            check(meta['native_size'] == expected, 'native dimensions use shared source scale', [i, n])
            converted.append({'frame': n, 'size': expected, 'source_box': details[pose]['source_box'],
                              'native_hash': meta['native_hash']})
        check(len({m['native_hash'] for m in converted}) == 3, 'three individual phase drawings', i)
        x, y = (i % 2) * 384, (i // 2) * 104
        draw.text((x+6, y+3), f'{i:02d} {slug.upper()} | anchor / charge1 / contact2 / recovery4', fill='white')
        for col, n in enumerate((0, 1, 2, 4)):
            gallery.paste(new.crop((n*96, 0, (n+1)*96, 80)), (x+col*96, y+22),
                          new.crop((n*96, 0, (n+1)*96, 80)))
        result.append({'id': i, 'slug': slug, 'changed_frames': changed, 'super_changed_frames': owned_changed,
                       'standing_height': HEIGHTS[i],
                       'source_anchor_size': list(figures[0].size), 'conversion_scale': scale, 'frames': converted})
    path = OUT/'roster-native.png';gallery.save(path);captures.append(path)
    old = git_file('src/super_moves.h').decode()
    new = (ROOT/'src/super_moves.h').read_text()
    pattern = r'u8 superFrame\(u8 p\) \{.*?\n\}'
    check(re.sub(pattern, '', old, flags=re.S).replace('\r\n', '\n') ==
          re.sub(pattern, '', new, flags=re.S).replace('\r\n', '\n'),
          'all super timing damage energy projectile and state source unchanged')
    return {'fighters': result, 'generated_count': shared['assets']['generated_count'],
            'generated_delta': shared['assets']['changed_generated'],
            'generated_additions': shared['assets']['added_generated'],
            'existing_art_and_reference_files_preserved': shared['assets']['protected_source_count']}


def native_contract(shared):
    old = legacy.symbols(git_file('dist/abaqus-after-hours.sym').decode())
    current = legacy.SYMBOLS
    ram = {n: a for n, a in old.items() if a < 0x2000 or 0x7E0000 <= a < 0x800000}
    moved = {n: [a, current.get(n)] for n, a in ram.items() if current.get(n) != a}
    check(not moved, 'all baseline WRAM/direct-page symbol addresses preserved', moved)
    sections = []
    for n, a in current.items():
        if not n.startswith('SECTIONSTART_') or a < 0x8000 or 0x7E0000 <= a < 0x800000:
            continue
        b = current.get('SECTIONEND_' + n[13:])
        if b is None:
            continue
        check(0 < b-a <= 32768 and a >> 16 == (b-1) >> 16, 'section fits one LoROM bank', [n, b-a])
        sections.append(b-a)
    check(shared['native']['abi_and_transfer_assembly_preserved'],
          'native transfer and trace ABI preserved under combined hit-reaction policy')
    rom = (ROOT/'dist/abaqus-after-hours.sfc').read_bytes()
    check(len(rom) == 4194304 and rom[0x7FD5] == 0x30, '4 MiB FastROM LoROM')
    return {'new_mutable_bytes': 0, 'preserved_ram_labels': len(ram), 'bank_local_sections': len(sections),
            'largest_section': max(sections), 'actor_transfer_bytes': 3840, 'obj_per_actor': 30,
            'super_new_obj_vram_palette_sound_banks': 0, 'frame_ids': [1, 2, 4], 'abi': 'Fighter64/Wave16/TRACE0..122'}


def observe(e, old, old_payload, before_audio, state):
    health['frames'] += 1
    if (state['frame'] - old['frame']) & 65535 != 1:
        health['cadence_failures'].append([old['frame'], state['frame']])
    if state['stat77'] & 0xC0:
        health['obj_failures'].append([state['frame'], state['stat77']])
    payload = [actor_payload(e, p) for p in range(2)]
    changed = [p for p in range(2) if old_payload[p] != payload[p]]
    for p in changed:
        health['actor_updates'][p] += 1
        health['maximum_changed_actor_payload_bytes'] = max(health['maximum_changed_actor_payload_bytes'], len(payload[p]))
    if len(changed) > 1:
        health['transfer_failures'].append([state['frame'], changed])
    if e.audio_samples <= before_audio:
        health['audio_failures'].append({'kind': 'missing_pcm', 'frame': state['frame']})
    read = legacy.read(e, 'spc_fread', 1)[0];write = legacy.read(e, 'spc_fwrite', 1)[0]
    backlog = (write-read) & 255
    health['peak_spc_backlog'] = max(health['peak_spc_backlog'], backlog)
    if backlog > 32:
        health['audio_failures'].append({'kind': 'fifo', 'frame': state['frame'], 'bytes': backlog})
    return payload


def dedicated_sequence(fighter):
    e = boot(1, fighter, fighter2=fighter, stage=fighter % 3)
    wanted = [set(), set()];uploaded = [set(), set()];phase_samples = [[], []]
    pauses = []
    def advance(p1=(), p2=()):
        nonlocal old, payload
        before_audio = e.audio_samples
        state = legacy.step(e, p1, p2)
        payload = observe(e, old, payload, before_audio, state)
        old = state
        return state
    try:
        legacy.position(e, far=True);legacy.full(e)
        old = legacy.sample(e);payload = [actor_payload(e, p) for p in range(2)]
        for elapsed in range(180):
            state = advance(['y', 'b'], ['y', 'b'])
            if elapsed == 0:
                check(state['energy1'] == state['energy2'] == 0 and state['superActive'] == [1, 1],
                      'fresh neutral Y+B costs96 on both ports', fighter)
                for port in range(2):verify_oam_geometry(e, port, f'super-{fighter}-{port}')
            for p in range(2):
                if not state['superActive'][p]:
                    continue
                clock = state['ticks'][p]
                frame = 1 if clock < legacy.START[fighter] else (
                    4 if clock >= state['active_ends'][p] else (2 if clock < state['superContactEnd'][p] else 1))
                actual = state[f'anim_frame{p+1}']
                if frame != actual:
                    health['phase_failures'].append([fighter, p, elapsed, clock, frame, actual])
                wanted[p].add(actual)
                native = uploaded_frame_id(e, fighter, p)
                check(native is not None, 'VRAM contains a complete exact native frame', [fighter, p, elapsed])
                if native in (1, 2, 4):
                    uploaded[p].add(native)
                    if native == actual and len([r for r in phase_samples[p] if r['frame'] == native]) < 2:
                        phase_samples[p].append({'frame': native, 'clock': clock, 'pulse': state['superPhase'][p],
                                                 'payload_sha256': sha(payload[p])})
            if elapsed in (4, legacy.START[fighter]+3):
                port = 0 if elapsed == 4 else 1
                frozen = advance(['start'] if port == 0 else (), ['start'] if port == 1 else ())
                check(frozen['paused'] == 1, 'either native port can pause a dedicated super', [fighter, port])
                fields = ('ticks', 'superActive', 'superPhase', 'superNext', 'superContactEnd',
                          'anim_frame1', 'anim_frame2', 'wave_life1', 'wave_life2', 'x1', 'x2', 'y1', 'y2')
                for _ in range(8):
                    paused = advance()
                    check(all(paused[k] == frozen[k] for k in fields), 'pause freezes both super sequences and uploads', [fighter, port])
                resumed = advance(['start'] if port == 0 else (), ['start'] if port == 1 else ())
                check(not resumed['paused'] and resumed['superActive'] == [1, 1],
                      'same port resumes both committed supers', [fighter, port])
                advance();pauses.append(port)
        check(wanted == [{1, 2, 4}, {1, 2, 4}], 'three phase-specific frames selected on both ports', fighter)
        check(uploaded == [{1, 2, 4}, {1, 2, 4}], 'three dedicated frames actually upload on both ports', fighter)
        check(state['superActive'] == [0, 0], 'both held commands finish without repeat', fighter)
        check(e.audio_peak > 1000, 'capture-only resident PCM remains active', fighter)
        return {'fighter': fighter, 'selected': [sorted(r) for r in wanted], 'uploaded': [sorted(r) for r in uploaded],
                'phase_samples': phase_samples, 'audio_peak': e.audio_peak, 'ordinary_ticks': 180,
                'pause_resume_ports': pauses}
    finally:
        e.close()


def guarded_contact(fighter, port):
    """Keep a rising defender in place between legal standing-guard windows."""
    if fighter not in (5, 7, 10):
        return legacy.contact(fighter, port, guard=True)
    original_step = legacy.step
    defender = 1 - port
    back = 'right' if defender == 1 else 'left'
    rows = []

    def timed_guard_step(e, p1=(), p2=(), monitor=True):
        before = legacy.sample(e)
        supplied = list((p1, p2)[defender])
        next_tick = before['ticks'][port] + int(not before['hitstop'])
        contact_now = (before['superPhase'][port] > 0 and
                       next_tick < before['superContactEnd'][port])
        new_pulse = (before['superPhase'][port] < len(legacy.HITS[fighter]) and
                     next_tick >= before['superNext'][port])
        window = bool(before['superActive'][port] and (contact_now or new_pulse))
        if not window:
            if defender == 0:
                p1 = ()
            else:
                p2 = ()
        state = original_step(e, p1, p2, monitor)
        if supplied:
            rows.append({'clock_before': before['ticks'][port], 'phase_before': before['superPhase'][port],
                         'next_clock': next_tick, 'next_pulse': before['superNext'][port],
                         'contact_end': before['superContactEnd'][port], 'pulse_window': window,
                         'super_active_before': before['superActive'][port],
                         'supplied_defense': supplied, 'controller_keys': [list(p1), list(p2)],
                         'defender_x_before': before[f'x{defender+1}'],
                         'defender_x_after': state[f'x{defender+1}']})
        return state

    legacy.step = timed_guard_step
    try:
        result = legacy.contact(fighter, port, guard=True)
    finally:
        legacy.step = original_step
    check(rows and all(row['supplied_defense'] == [back] and
                       row['controller_keys'][defender] == ([back] if row['pulse_window'] else [])
                       for row in rows),
          'rising guard uses relative back only in committed pulse windows', [fighter, port])
    startup = [row for row in rows if row['super_active_before'] and
               row['phase_before'] == 0 and not row['pulse_window']]
    check(startup and all(row['defender_x_before'] == row['defender_x_after'] for row in startup),
          'neutral rising-super startup guard fixture holds defender position', [fighter, port])
    result['controller_policy'] = 'standing relative back during pulse windows; neutral startup gaps recovery'
    result['guard_controller_rows'] = rows
    return result

def training_reset(fighter):
    e = boot(2, fighter, fighter2=fighter)
    try:
        legacy.full(e);legacy.fire(e, 0);legacy.run(e, 2)
        legacy.run(e, 3, p2=['start']);frozen = legacy.sample(e)
        check(frozen['paused'] and frozen['superActive'][0], 'P2 pauses each Training signature startup', fighter)
        paused = legacy.run(e, 8)
        check(paused['ticks'] == frozen['ticks'] and paused['superPhase'] == frozen['superPhase'],
              'each Training super clock freezes', fighter)
        legacy.run(e, 3, p2=['start']);legacy.run(e, 3)
        reset = legacy.run(e, 3, p1=['select'])
        check(all(reset[n] == [0, 0] for n in legacy.STATE) and not reset['wave1'] and not reset['wave2'],
              'Training reset clears every signature state and projectile', fighter)
        later = legacy.run(e, 24)
        check(not later['superActive'][0] and later['action1'] == 0 and later['hp1'] == later['hp2'] == 128,
              'reset cannot leak later super frames or damage', fighter)
        return {'fighter': fighter, 'activation_port': 0, 'pause_port': 1, 'reset_port': 0, 'state': 'all14 private bytes zero'}
    finally:
        e.close()


def clip(fighter, phase, rom=None):
    old_boot = legacy.boot;old_step = legacy.step
    images = []
    legacy.boot = lambda *a, **kw: boot(*a, rom=rom, **kw)
    def step(e, *a, **kw):
        state = old_step(e, *a, **kw)
        if (state['superActive'][0] or images) and state['frame'] % 3 == 0:
            images.append(e.frame.copy())
        return state
    legacy.step = step
    try:
        result = legacy.contact(fighter, 0, capture=False)
        path = OUT/f'{fighter:02d}-{phase}.gif'
        images[0].save(path, save_all=True, append_images=images[1:], duration=50, loop=0)
        captures.append(path)
        return result
    finally:
        legacy.boot = old_boot;legacy.step = old_step


def main():
    global OUT
    parser = argparse.ArgumentParser();parser.add_argument('--baseline-rom', type=Path)
    parser.add_argument('--fighters', default=','.join(map(str, range(12))))
    parser.add_argument('--report', type=Path, default=ROOT/'docs/combat-24-super-report.json')
    args = parser.parse_args()
    try:
        fighters = list(map(int, args.fighters.split(',')))
    except ValueError:
        parser.error('--fighters must list distinct roster IDs 0..11')
    if not fighters or len(set(fighters)) != len(fighters) or any(i not in range(12) for i in fighters):
        parser.error('--fighters must list distinct roster IDs 0..11')
    partial = set(fighters) != set(range(12))
    report_path = (ROOT/args.report).resolve()
    if partial:
        if not report_path.is_relative_to((ROOT/'build').resolve()):
            parser.error('partial rosters require --report under build; they are diagnostic only')
        OUT = report_path.parent/(report_path.stem+'-captures')
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.time()
    legacy.SYMBOLS = legacy.symbols((ROOT/'dist/abaqus-after-hours.sym').read_text())
    report = {'feature': 'super', 'scope': 'combined-ROM focused dedicated super artwork and retained gameplay fixtures',
              'combined_pass_claimed': False, 'combined_focused_coverage_complete': False,
              'historical_evidence': 'Prior isolated reports and GIFs are historical; this report counts only the current cartridge run. Optional baseline clips are historical comparisons.',
              'baseline_commit': BASE, 'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'source_sha256': source_hashes(),
              'art_index_sha256': sha((ROOT/'assets/art/super-v1.json').read_bytes()),
              'rom_sha256': sha((ROOT/'dist/abaqus-after-hours.sfc').read_bytes()),
              'symbols_sha256': sha((ROOT/'dist/abaqus-after-hours.sym').read_bytes()),
              'test_sha256': sha(Path(__file__).read_bytes()),
              'command': subprocess.list2cmdline([sys.executable, 'tools/test_combat24_super.py', *sys.argv[1:]]),
              'host': dict(host_contract(), platform=platform.platform(), machine=platform.machine()),
              'harness_sha256': {p: sha((ROOT/p).read_bytes()) for p in HARNESS},
              'core_sha256': sha((ROOT/'.tools/core/snes9x_libretro.dll').read_bytes()),
              'controller_only': True, 'memory_writes': False, 'save_states': False,
              'selected_fighters': fighters, 'diagnostic_only': partial,
              'human_balance_likeness_controller_review': 'open', 'failures': []}
    old_shot = Emulator.shot
    Emulator.shot = lambda e, name: e.frame.save(OUT/('guide.png' if name == 'expansion-07-guide.png' else name))
    try:
        check(report['core_sha256'] == EXPECTED_NATIVE_CORE['dll_sha256'], 'pinned native Snes9x1.63 core')
        check(not report['host']['gui_opened'] and not report['host']['audio_device_opened'], 'silent headless host')
        check(report['host'].get('priority_class') == 0x4000 and len(report['host']['logical_processors']) <= 2,
              'background runner priority and affinity enforced', report['host'])
        report['combined_contract'] = combined_preservation()
        report['art'] = art_contract(report['combined_contract'])
        report['native_contract'] = native_contract(report['combined_contract'])
        report['dedicated_sequences'] = [dedicated_sequence(i) for i in fighters]
        report['training_resets'] = [training_reset(i) for i in fighters]
        report['activation'] = [legacy.activation(i) for i in fighters]
        report['hits'] = [legacy.contact(i, p) for i in fighters for p in range(2)]
        report['blocks'] = [guarded_contact(i, p) for i in fighters for p in range(2)]
        report['whiffs'] = [legacy.whiff(i, p) for i in fighters for p in range(2)]
        report['interruptions'] = [legacy.interrupt(i, p) for i in fighters for p in range(2)]
        if not partial:
            report['punish'] = legacy.punish();report['pause_reset'] = legacy.eligibility_pause_reset()
            report['pause_reset']['guide'] = (OUT/'guide.png').relative_to(ROOT).as_posix()
            report['hurt_down_wake_dead'] = legacy.hurt_down_wake_dead()
            report['ordinary_special_after_super'] = legacy.ordinary_special_after_super()
            captures.append(OUT/'guide.png')
        else:
            report['skipped_global_fixtures'] = ['punish', 'pause_reset', 'hurt_down_wake_dead',
                                                 'ordinary_special_after_super', 'clips']
        report['clips'] = {}
        for fighter in (() if partial else (0, 2, 5)):
            after = clip(fighter, 'after')
            report['clips'][str(fighter)] = {'after': after}
            if args.baseline_rom:
                check(sha(args.baseline_rom.read_bytes()) == BASE_ROM_SHA, 'approved baseline cartridge exact')
                saved = legacy.SYMBOLS
                saved_timing = {k: v.copy() if isinstance(v, list) else v for k, v in legacy.timing.items()}
                saved_checks = len(legacy.checks)
                legacy.SYMBOLS = legacy.symbols(args.baseline_rom.with_suffix('.sym').read_text())
                before = clip(fighter, 'before', args.baseline_rom)
                legacy.SYMBOLS = saved
                before['evidence_scope'] = 'historical approved v0.23.1 baseline comparison; excluded from current native check and timing counts'
                before['observed_native_frames'] = legacy.timing['frames']-saved_timing['frames']
                before['checks'] = len(legacy.checks)-saved_checks
                before['cadence_failures'] = legacy.timing['cadence_failures'][len(saved_timing['cadence_failures']):]
                before['overflow_failures'] = legacy.timing['overflow_failures'][len(saved_timing['overflow_failures']):]
                check(not before['cadence_failures'] and not before['overflow_failures'], 'baseline clip native health', fighter)
                legacy.timing.clear();legacy.timing.update(saved_timing)
                del legacy.checks[saved_checks:]
                report['clips'][str(fighter)]['before'] = before
                check(before['events'] == after['events'], 'before/after full native contacts and damage identical', fighter)
        for key in ('cadence_failures', 'obj_failures', 'transfer_failures', 'audio_failures', 'phase_failures'):
            check(not health[key], 'dedicated sequence ' + key + ' empty', health[key][:8])
        check(not legacy.timing['cadence_failures'] and not legacy.timing['overflow_failures'],
              'retained controller fixtures native cadence and OBJ checks pass', legacy.timing)
        check(sha((ROOT/'dist/abaqus-after-hours.sfc').read_bytes()) == report['rom_sha256'], 'exact cartridge retained throughout proof')
        check(sha((ROOT/'dist/abaqus-after-hours.sym').read_bytes()) == report['symbols_sha256'],
              'exact symbols retained throughout proof')
        check(source_hashes() == report['source_sha256'] and
              {p: sha((ROOT/p).read_bytes()) for p in HARNESS} == report['harness_sha256'] and
              sha((ROOT/'assets/art/super-v1.json').read_bytes()) == report['art_index_sha256'],
              'production source art index and harness inputs retained throughout proof')
        report['combined_focused_coverage_complete'] = not partial
        report['status'] = 'diagnostic_passed' if partial else 'passed'
    except Exception as exc:
        report['status'] = 'failed';report['failures'].append(repr(exc))
        raise
    finally:
        Emulator.shot = old_shot
        if baseline_git is not None:
            baseline_git.stdin.close();baseline_git.wait(timeout=10)
        report['checks'] = len(checks) + len(legacy.checks)
        report['own_check_inventory'] = checks
        report['retained_fixture_check_count'] = len(legacy.checks)
        report['health'] = health;report['retained_fixture_timing'] = legacy.timing
        report['rom_sha256_after'] = sha((ROOT/'dist/abaqus-after-hours.sfc').read_bytes())
        report['symbols_sha256_after'] = sha((ROOT/'dist/abaqus-after-hours.sym').read_bytes())
        report['source_sha256_after'] = source_hashes()
        report['captures'] = [{'path': p.relative_to(ROOT).as_posix(), 'sha256': sha(p.read_bytes()),
                               'evidence_scope': 'historical baseline' if p.stem.endswith('-before') else 'current invocation'}
                              for p in captures if p.exists()]
        report['elapsed_seconds'] = round(time.time()-started, 3)
        report['harness_sha256_after'] = {p: sha((ROOT/p).read_bytes()) for p in HARNESS}
        report['changed_harness_inputs'] = [p for p in HARNESS if
                                           report['harness_sha256'][p] != report['harness_sha256_after'][p]]
        if report['changed_harness_inputs']:
            report['diagnostic_provenance_issue'] = {
                'changed_harness_inputs': report['changed_harness_inputs'],
                'meaning': 'Concurrent harness edits invalidate stable-input evidence; this alone is not a ROM defect.'}
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
        print(json.dumps({k: report[k] for k in ('status', 'rom_sha256', 'checks', 'elapsed_seconds')}))


if __name__ == '__main__':
    main()
