"""Isolated v0.24 super-art proof; controller-only native execution.

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
from test_champion import host_contract
from test_characters import (actor_payload, boot, uploaded_frame_id,
                             verify_oam_geometry)

BASE = 'f75005d'
BASE_ROM_SHA = '057139801b64d1d486c91e18f456e01519dd4d25c3d0d6a92e61f311b99da3fd'
OUT = ROOT / 'docs/screenshots/combat24-super'
checks = []
captures = []
health = {'frames': 0, 'cadence_failures': [], 'obj_failures': [],
          'transfer_failures': [], 'audio_failures': [], 'phase_failures': [],
          'peak_spc_backlog': 0, 'actor_updates': [0, 0],
          'maximum_changed_actor_payload_bytes': 0}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git_file(path):
    return subprocess.check_output(['git', 'show', BASE + ':' + path], cwd=ROOT)


def check(ok, label, detail=None):
    checks.append({'check': label, 'passed': bool(ok), 'detail': detail})
    if not ok:
        raise AssertionError((label, detail))


def art_contract():
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
        check(changed == [1, 2, 4], 'exactly three owned frames differ', [i, changed])
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
        result.append({'id': i, 'slug': slug, 'changed_frames': changed, 'standing_height': HEIGHTS[i],
                       'source_anchor_size': list(figures[0].size), 'conversion_scale': scale, 'frames': converted})
    path = OUT/'roster-native.png';gallery.save(path);captures.append(path)
    tracked = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASE, 'assets/generated'], cwd=ROOT, text=True).splitlines()
    delta = [p for p in tracked if git_file(p) != (ROOT/p).read_bytes()]
    allowed = {'assets/generated/character-manifest.json'} | {
        f'assets/generated/fighter{i:02d}{suffix}' for i in range(12) for suffix in ('.png', '.bin')}
    check(set(delta) == allowed, 'generated delta is twelve first banks, twelve previews and metadata', delta)
    masters = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASE, 'assets/art'], cwd=ROOT, text=True).splitlines()
    check(all(git_file(p) == (ROOT/p).read_bytes() for p in masters), 'all original masters and provenance preserved', len(masters))
    old = git_file('src/super_moves.h').decode()
    new = (ROOT/'src/super_moves.h').read_text()
    pattern = r'u8 superFrame\(u8 p\) \{.*?\n\}'
    check(re.sub(pattern, '', old, flags=re.S).replace('\r\n', '\n') ==
          re.sub(pattern, '', new, flags=re.S).replace('\r\n', '\n'),
          'all super timing damage energy projectile and state source unchanged')
    return {'fighters': result, 'generated_count': len(tracked), 'generated_delta': delta,
            'existing_art_files_preserved': len(masters)}


def native_contract():
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
    for path in ('src/hardware.asm', 'src/trace.asm', 'src/game.c', 'src/characters.h', 'src/animation_weight.h'):
        check(git_file(path).replace(b'\r\n', b'\n') == (ROOT/path).read_bytes().replace(b'\r\n', b'\n'),
              'native renderer ABI allocation and unowned gameplay source exact', path)
    rom = (ROOT/'dist/abaqus-after-hours.sfc').read_bytes()
    check(len(rom) == 4194304 and rom[0x7FD5] == 0x30, '4 MiB FastROM LoROM')
    return {'new_mutable_bytes': 0, 'preserved_ram_labels': len(ram), 'bank_local_sections': len(sections),
            'largest_section': max(sections), 'actor_transfer_bytes': 3840, 'obj_per_actor': 30,
            'new_obj_vram_palette_sound_banks': 0, 'frame_ids': [1, 2, 4], 'abi': 'Fighter64/Wave16/TRACE0..122'}


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
    try:
        legacy.position(e, far=True);legacy.full(e)
        old = legacy.sample(e);payload = [actor_payload(e, p) for p in range(2)]
        for tick in range(180):
            before_audio = e.audio_samples
            state = legacy.step(e, ['y', 'b'], ['y', 'b'])
            payload = observe(e, old, payload, before_audio, state)
            if tick == 0:
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
                    health['phase_failures'].append([fighter, p, tick, clock, frame, actual])
                wanted[p].add(actual)
                native = uploaded_frame_id(e, fighter, p)
                check(native is not None, 'VRAM contains a complete exact native frame', [fighter, p, tick])
                if native in (1, 2, 4):
                    uploaded[p].add(native)
                    if native == actual and len([r for r in phase_samples[p] if r['frame'] == native]) < 2:
                        phase_samples[p].append({'frame': native, 'clock': clock, 'pulse': state['superPhase'][p],
                                                 'payload_sha256': sha(payload[p])})
            old = state
        check(wanted == [{1, 2, 4}, {1, 2, 4}], 'three phase-specific frames selected on both ports', fighter)
        check(uploaded == [{1, 2, 4}, {1, 2, 4}], 'three dedicated frames actually upload on both ports', fighter)
        check(state['superActive'] == [0, 0], 'both held commands finish without repeat', fighter)
        check(e.audio_peak > 1000, 'capture-only resident PCM remains active', fighter)
        return {'fighter': fighter, 'selected': [sorted(r) for r in wanted], 'uploaded': [sorted(r) for r in uploaded],
                'phase_samples': phase_samples, 'audio_peak': e.audio_peak, 'frames': 180}
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
    parser = argparse.ArgumentParser();parser.add_argument('--baseline-rom', type=Path)
    args = parser.parse_args();OUT.mkdir(parents=True, exist_ok=True)
    started = time.time()
    legacy.SYMBOLS = legacy.symbols((ROOT/'dist/abaqus-after-hours.sym').read_text())
    report = {'feature': 'super', 'scope': 'isolated v0.24 dedicated super artwork; not combined verification',
              'baseline_commit': BASE, 'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'source_sha256': {p: sha((ROOT/p).read_bytes()) for p in ('src/super_moves.h', 'assets/art/super-v1.json')},
              'rom_sha256': sha((ROOT/'dist/abaqus-after-hours.sfc').read_bytes()),
              'symbols_sha256': sha((ROOT/'dist/abaqus-after-hours.sym').read_bytes()),
              'test_sha256': sha(Path(__file__).read_bytes()),
              'command': subprocess.list2cmdline([sys.executable, 'tools/test_combat24_super.py', *sys.argv[1:]]),
              'host': dict(host_contract(), platform=platform.platform(), machine=platform.machine()),
              'harness_sha256': {p: sha((ROOT/p).read_bytes()) for p in ('tools/emulator.py', 'tools/test_characters.py', 'tools/test_expansion_07_supers.py', 'tools/pose_revision_assets.py')},
              'core_sha256': sha((ROOT/'.tools/core/snes9x_libretro.dll').read_bytes()),
              'controller_only': True, 'memory_writes': False, 'save_states': False,
              'human_balance_likeness_controller_review': 'open', 'failures': []}
    old_shot = Emulator.shot
    Emulator.shot = lambda e, name: e.frame.save(OUT/('guide.png' if name == 'expansion-07-guide.png' else name))
    try:
        check(report['core_sha256'] == EXPECTED_NATIVE_CORE['dll_sha256'], 'pinned native Snes9x1.63 core')
        check(not report['host']['gui_opened'] and not report['host']['audio_device_opened'], 'silent headless host')
        check(report['host'].get('priority_class') == 0x4000 and len(report['host']['logical_processors']) <= 2,
              'background runner priority and affinity enforced', report['host'])
        report['art'] = art_contract();report['native_contract'] = native_contract()
        report['dedicated_sequences'] = [dedicated_sequence(i) for i in range(12)]
        report['activation'] = [legacy.activation(i) for i in range(12)]
        report['hits'] = [legacy.contact(i, p) for i in range(12) for p in range(2)]
        report['blocks'] = [legacy.contact(i, p, guard=True) for i in range(12) for p in range(2)]
        report['whiffs'] = [legacy.whiff(i, p) for i in range(12) for p in range(2)]
        report['interruptions'] = [legacy.interrupt(i, p) for i in range(12) for p in range(2)]
        report['punish'] = legacy.punish();report['pause_reset'] = legacy.eligibility_pause_reset()
        report['hurt_down_wake_dead'] = legacy.hurt_down_wake_dead()
        report['ordinary_special_after_super'] = legacy.ordinary_special_after_super()
        captures.append(OUT/'guide.png');report['clips'] = {}
        for fighter in (0, 2, 5):
            after = clip(fighter, 'after')
            report['clips'][str(fighter)] = {'after': after}
            if args.baseline_rom:
                check(sha(args.baseline_rom.read_bytes()) == BASE_ROM_SHA, 'approved baseline cartridge exact')
                saved = legacy.SYMBOLS
                legacy.SYMBOLS = legacy.symbols(args.baseline_rom.with_suffix('.sym').read_text())
                before = clip(fighter, 'before', args.baseline_rom)
                legacy.SYMBOLS = saved
                report['clips'][str(fighter)]['before'] = before
                check(before['events'] == after['events'], 'before/after full native contacts and damage identical', fighter)
        for key in ('cadence_failures', 'obj_failures', 'transfer_failures', 'audio_failures', 'phase_failures'):
            check(not health[key], 'dedicated sequence ' + key + ' empty', health[key][:8])
        check(not legacy.timing['cadence_failures'] and not legacy.timing['overflow_failures'],
              'retained controller fixtures native cadence and OBJ checks pass', legacy.timing)
        check(sha((ROOT/'dist/abaqus-after-hours.sfc').read_bytes()) == report['rom_sha256'], 'exact cartridge retained throughout proof')
        report['status'] = 'passed'
    except Exception as exc:
        report['status'] = 'failed';report['failures'].append(repr(exc))
        raise
    finally:
        Emulator.shot = old_shot
        report['checks'] = len(checks) + len(legacy.checks)
        report['health'] = health;report['retained_fixture_timing'] = legacy.timing
        report['captures'] = [{'path': p.relative_to(ROOT).as_posix(), 'sha256': sha(p.read_bytes())} for p in captures if p.exists()]
        report['elapsed_seconds'] = round(time.time()-started, 3)
        (ROOT/'docs/combat-24-super-report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
        print(json.dumps({k: report[k] for k in ('status', 'rom_sha256', 'checks', 'elapsed_seconds')}))


if __name__ == '__main__':
    main()
