"""Read-only contact/super composition repro; not final six-feature evidence.

Fresh counters per controller-only session preserve attribution. Failed legacy
fixtures remain failed observations; a closer fixture is a separate experiment.
Run silently with canonical Python through tools/run_background.py.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import test_combat24_super as dedicated
legacy = dedicated.legacy
from contact_geometry import generate, world, overlap
from test_champion import host_contract
from test_endurance import core_identity
from PIL import Image, ImageDraw

native_samples = []
original_step = legacy.step


def direct_counters(e):
    return {name: int.from_bytes(bytes(legacy.read(e, name, 1 if name == 'vblank_flag' else 2)), 'little')
            for name in ('frame', 'snes_vblank_count', 'lag_frame_counter', 'vblank_flag')}


def instrumented_step(e, p1=(), p2=(), monitor=True):
    before = direct_counters(e)
    trace_before = e.state()['frame']
    state = original_step(e, p1, p2, monitor)
    after = direct_counters(e)
    native_samples.append({'before': before, 'after': after,
                           'trace': [trace_before, state['frame']],
                           'pause_trace_native': [state['paused'], legacy.read(e, 'paused', 1)[0]],
                           'raw_keys_trace': [state['raw_keys1'], state['raw_keys2']],
                           'raw_keys_native': [int.from_bytes(bytes(legacy.read(e, 'fighters', 128)[p*64+32:p*64+34]), 'little') for p in (0, 1)],
                           'delta': {k: (after[k]-before[k]) & 65535 for k in before},
                           'phase': state['superPhase'], 'ticks': state['ticks'], 'keys': [p1, p2]})
    return state


legacy.step = instrumented_step


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def reset_counters():
    native_samples.clear()
    for counters in (dedicated.health, legacy.timing):
        for key, value in counters.items():
            counters[key] = [0, 0] if key == 'actor_updates' else ([] if isinstance(value, list) else 0)


def signed(v):
    return v - 65536 if v & 32768 else v


def rising(fighter, port, distance, guard, data):
    e = legacy.boot(1, fighter, fighter2=fighter)
    rows, events, guarded = [], [], set()
    try:
        legacy.position(e, distance=distance)
        legacy.full(e)
        initial = legacy.sample(e)
        hp = initial[f'hp{2-port}']
        previous = initial
        for callback in range(160):
            keys = ['y', 'b'] if callback < 3 else []
            back = 'right' if port == 0 else 'left'
            next_tick = previous['ticks'][port] + int(not previous['hitstop'])
            contact_now = (previous['superPhase'][port] > 0 and next_tick < previous['superContactEnd'][port])
            new_pulse = (previous['superPhase'][port] < len(legacy.HITS[fighter]) and
                         next_tick >= previous['superNext'][port])
            # Back only for the telegraphed pulse windows; holding it through
            # startup is a retreat experiment and changes neutral spacing.
            defense = [back] if guard and (contact_now or new_pulse) and callback else []
            s = legacy.step(e, keys if port == 0 else defense, keys if port else defense)
            p, d = str(port+1), str(2-port)
            if s[f'hp{d}'] != hp:
                events.append({'callback': callback, 'damage': hp-s[f'hp{d}'],
                               'tick': s['ticks'][port], 'phase': s['superPhase'][port]})
                hp = s[f'hp{d}']
            if s[f'guard{d}'] and s['hitstop'] > previous['hitstop']:
                guarded.add(s['superPhase'][port])
            if s['superActive'][port]:
                # Collision precedes animateFighter. For this neutral defender,
                # its prior selected hurt/idle pose is the evaluated body pose.
                frame = 2 if s['ticks'][port] < s['superContactEnd'][port] else 1
                body_frame = previous[f'anim_frame{d}']
                observed_xy = [[signed(s[f'x{q}']), signed(s[f'y{q}'])] for q in ('1', '2')]
                collision_xy = copy.deepcopy(observed_xy)
                collision_face = [s['face1'], s['face2']]
                impact = s['hitstop'] > previous['hitstop'] and s[f'connected{p}'] > 0
                impulse = 0
                if impact:
                    # hurtWithRecoil immediately shifts x AFTER the overlap;
                    # a real final hit also changes facing/y in knockdown.
                    # Undo those documented writes for the evaluated snapshot.
                    direction = 1 if s[f'face{p}'] else -1
                    impulse = 16 if s[f'guard{d}'] else 32
                    if 'beginRecoil' in legacy.SYMBOLS:
                        latch = legacy.read(e, 'rearKickRecoil', 1)[0] >> ((1-port)*4) & 15
                        if (latch & 3) not in (1, 2):
                            raise AssertionError(('impact has no latched recoil direction', fighter, port, latch))
                        direction = 1 if latch & 3 == 2 else -1
                        impulse = 16 if s[f'guard{d}'] else (64 if latch & 4 else 32)
                    collision_xy[1-port][0] -= direction * impulse
                    collision_face[1-port] = previous[f'face{d}']
                    if s[f'down_state{d}'] and not previous[f'down_state{d}'] and s[f'y{d}'] == 65535:
                        collision_xy[1-port][1] = 0
                strike = world(data['poses'][fighter][frame][2], signed(s[f'x{p}']),
                               signed(s[f'y{p}']), s[f'face{p}'])
                hurt = [world(r, *collision_xy[1-port], collision_face[1-port])
                        for r in data['poses'][fighter][body_frame][:2]]
                rows.append({'callback': callback, 'frame': s['frame'], 'tick': s['ticks'][port],
                             'phase': s['superPhase'][port], 'contact_end': s['superContactEnd'][port],
                             'observed_xy_12_4': observed_xy, 'collision_xy_12_4': collision_xy,
                             'collision_face': collision_face, 'post_impact_reconstructed': impact,
                             'impact_recoil_12_4': impulse,
                             'face': [s['face1'], s['face2']],
                             'selected': [s['anim_frame1'], s['anim_frame2']],
                             'uploaded': [dedicated.uploaded_frame_id(e, fighter, q) for q in (0, 1)],
                             'body_frame_before_animation': body_frame,
                             'strike_12_4': strike, 'hurt_12_4': hurt,
                             'spatial_overlap': any(overlap(strike, r) for r in hurt),
                             'hurt': [s['hurt1'], s['hurt2']], 'connected': s[f'connected{p}'],
                             'hitstop': s['hitstop'], 'hp': [s['hp1'], s['hp2']],
                             'keys': [keys if port == 0 else defense, keys if port else defense],
                             'raw_keys': [s['raw_keys1'], s['raw_keys2']]})
            previous = s
        expected = legacy.HITS[fighter]
        ok = guarded == set(range(1, len(expected)+1)) if guard else [v['damage'] for v in events] == expected
        return {'fighter': fighter, 'port': port, 'requested_gap_px': distance,
                'actual_gap_12_4': abs(initial['x1']-initial['x2']), 'guard': guard,
                'guard_policy': 'standing back during pulse windows; neutral between',
                'events': events, 'guarded_phases': sorted(guarded), 'all_pulses_connect': ok,
                'expected_hit_damage': expected, 'rows': rows}
    finally:
        e.close()


def pulse_overlay(cases, path):
    """Offline collision-snapshot pixels; never adds runtime debug drawing."""
    panels = []
    for case in cases:
        result = case['result']
        if case['kind'] != 'rising-pulses' or result['port'] or result['guard']:
            continue
        sheet = Image.open(ROOT/f"assets/generated/fighter{case['fighter']:02d}.png").convert('RGBA')
        for phase in range(1, len(result['expected_hit_damage'])+1):
            event = next((e for e in result['events'] if e['phase'] == phase), None)
            row = next((r for r in result['rows'] if r['callback'] == event['callback']), None) if event else None
            if row is None:
                row = next((r for r in result['rows'] if r['phase'] == phase and
                            r['tick'] < r['contact_end']), None)
            if row is None:
                continue
            im = Image.new('RGB', (384, 192), '#141c2c')
            draw = ImageDraw.Draw(im)
            center = sum(xy[0] for xy in row['collision_xy_12_4'])/32
            ox, oy = 192-center, 160
            for p, frame in ((0, 2), (1, row['body_frame_before_animation'])):
                pose = sheet.crop((frame*96, 0, (frame+1)*96, 80))
                if not row['collision_face'][p]:
                    pose = pose.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                x, y = row['collision_xy_12_4'][p]
                im.paste(pose, (round(ox+x/16-48), round(oy+y/16-78)), pose)
            for rect, color in [(r, '#60d0ef') for r in row['hurt_12_4']] + [(row['strike_12_4'], '#ffb04b')]:
                l, t, r, b = rect
                draw.rectangle((ox+l/16, oy+t/16, ox+r/16, oy+b/16), outline=color)
            draw.text((8, 5), f"ID{case['fighter']:02d} gap{result['requested_gap_px']} phase{phase} tick{row['tick']}", fill='white')
            draw.text((8, 20), f"HP event: {event['damage'] if event else 'MISS'} | overlap {row['spatial_overlap']}", fill='white')
            draw.text((8, 176), 'orange=strike  cyan=body | collision pose before animation', fill='white')
            panels.append(im)
    gallery = Image.new('RGB', (768, 192*((len(panels)+1)//2)), '#141c2c')
    for n, im in enumerate(panels):
        gallery.paste(im, ((n % 2)*384, (n//2)*192))
    path.parent.mkdir(parents=True, exist_ok=True)
    gallery.save(path)
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': digest(path.read_bytes()),
            'meaning': 'read-only native-derived logical collision snapshots, not PPU screenshots'}


def input_phase_probe(fighter, width=1):
    """Keep the failed immediate-pause fixture intact; observe the next polls."""
    e = legacy.boot(1, fighter, fighter2=fighter, stage=fighter % 3)
    try:
        legacy.position(e, far=True)
        legacy.full(e)
        for _ in range(5):
            legacy.step(e, ['y', 'b'], ['y', 'b'])
        states = [legacy.step(e, ['start']) for _ in range(width)]
        states += [legacy.step(e) for _ in range(3)]
        return {'fighter': fighter, 'pause_after_input_callbacks': [s['paused'] for s in states],
                'start_held_callbacks': width,
                'ticks': [s['ticks'] for s in states],
                'meaning': 'observation only; original one-callback pause assertion is not changed'}
    finally:
        e.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--rom', type=Path, default=ROOT/'dist/abaqus-after-hours.sfc')
    parser.add_argument('--runtime-source', help='commit used to build an explicitly retained ROM')
    parser.add_argument('--phase-probe', type=int, nargs='*', default=[])
    parser.add_argument('--phase-width', type=int, choices=(1, 3), default=1)
    parser.add_argument('--dedicated', type=int, nargs='*', default=[0, 2, 5, 7, 10])
    parser.add_argument('--rising', type=int, nargs='*', default=[5, 7, 10])
    parser.add_argument('--gaps', type=int, nargs='+', default=[28, 22])
    parser.add_argument('--guards', action='store_true')
    parser.add_argument('--fairness', action='store_true', help='retain legacy remote-whiff/startup-interrupt/recovery-punish checks')
    parser.add_argument('--expect-legacy-david-miss', action='store_true',
                        help='require the reproduced David target28 neutral miss [8,8]; all other fixtures remain strict')
    parser.add_argument('--core', choices=('snes9x', 'accuracy'), default='snes9x')
    parser.add_argument('--overlays', type=Path)
    args = parser.parse_args()
    args.rom = args.rom.resolve()
    if args.overlays:
        args.overlays = args.overlays.resolve()
    if args.core == 'accuracy':
        import test_characters
        import test_compatibility as compat
        compat.ROM_PATH = args.rom
        if digest(compat.CORE_PATH.read_bytes()).upper() != compat.CORE_DLL_SHA256:
            raise AssertionError('Accuracy DLL differs from pinned member')
        if digest(compat.CORE_ARCHIVE.read_bytes()).upper() != compat.CORE_ARCHIVE_SHA256:
            raise AssertionError('Accuracy archive differs from pinned download')
        class AccuracyHost(compat.Probe):
            def __init__(self, rom=None):
                if rom is not None:
                    raise ValueError('Accuracy composition uses the current exact ROM')
                super().__init__()
            @property
            def frame(self):
                return self.frame_image
            def tap(self, key, port=0):
                self.run(3, **({'p1': [key]} if port == 0 else {'p2': [key]}))
                return self.run(3)
            def state(self):
                # Preserve all public names expected by the shared helpers.
                return dedicated.Emulator.state(self)
        test_characters.Emulator = AccuracyHost
    elif args.rom != (ROOT/'dist/abaqus-after-hours.sfc').resolve():
        import test_characters
        class RetainedHost(dedicated.Emulator):
            def __init__(self, rom=None):
                super().__init__(rom or args.rom)
        test_characters.Emulator = RetainedHost
    started = time.monotonic()
    _, data = generate()
    legacy.SYMBOLS = legacy.symbols(args.rom.with_suffix('.sym').read_text())
    report = {'status': 'failed', 'scope': 'interim-contact-plus-dedicated-super-composition',
              'final_art_timing_rerun_required': True,
              'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
              'built_runtime_source_commit': args.runtime_source,
              'source_diff_sha256': digest(subprocess.check_output(['git', 'diff', 'HEAD', '--', 'src', 'tools'], cwd=ROOT)),
              'rom_sha256': digest(args.rom.read_bytes()), 'rom': str(args.rom),
              'geometry_digest': data['digest'], 'command': subprocess.list2cmdline([sys.executable, *sys.argv]),
              'harness_sha256': digest(Path(__file__).read_bytes().replace(b'\r\n', b'\n')),
              'host': host_contract(), 'core': core_identity(), 'cases': [], 'failures': []}
    if args.core == 'accuracy':
        report['core'] = {'name': 'bsnes2014 Accuracy', 'dll_sha256': digest(compat.CORE_PATH.read_bytes()),
                          'archive_sha256': digest(compat.CORE_ARCHIVE.read_bytes())}
    try:
        for fighter in args.dedicated:
            reset_counters()
            result = dedicated.dedicated_sequence(fighter)
            case = {'kind': 'dedicated-simultaneous', 'fighter': fighter, 'result': result,
                    'health': copy.deepcopy(dedicated.health), 'timing': copy.deepcopy(legacy.timing),
                    'native_counters': copy.deepcopy(native_samples)}
            report['cases'].append(case)
            print(json.dumps({'dedicated': fighter, 'cadence': legacy.timing['cadence_failures']}), flush=True)
        for fighter in args.rising:
            for port in (0, 1):
                for gap in args.gaps:
                    for guard in ([False, True] if args.guards else [False]):
                        reset_counters()
                        result = rising(fighter, port, gap, guard, data)
                        report['cases'].append({'kind': 'rising-pulses', 'fighter': fighter,
                                                'result': result, 'timing': copy.deepcopy(legacy.timing),
                                                'native_counters': copy.deepcopy(native_samples)})
                        known_miss = args.expect_legacy_david_miss and fighter == 5 and gap == 28 and not guard
                        expected = ([e['damage'] for e in result['events']] == [8, 8] and
                                    [e['phase'] for e in result['events']] == [1, 2]) if known_miss else result['all_pulses_connect']
                        if not expected:
                            report['failures'].append({'kind': 'pulse-miss', 'fighter': fighter, 'port': port,
                                                       'gap': gap, 'guard': guard, 'events': result['events']})
                        print(json.dumps({k: result[k] for k in ('fighter', 'port', 'requested_gap_px', 'guard',
                                                               'events', 'all_pulses_connect')}), flush=True)
        if args.fairness:
            for fighter in args.rising:
                for port in (0, 1):
                    for label, fn in (('remote-whiff', legacy.whiff), ('startup-interrupt', legacy.interrupt)):
                        reset_counters()
                        result = fn(fighter, port)
                        report['cases'].append({'kind': label, 'fighter': fighter, 'result': result,
                                                'timing': copy.deepcopy(legacy.timing),
                                                'native_counters': copy.deepcopy(native_samples)})
            reset_counters()
            result = legacy.punish()
            report['cases'].append({'kind': 'recovery-punish', 'fighter': 2, 'result': result,
                                    'timing': copy.deepcopy(legacy.timing),
                                    'native_counters': copy.deepcopy(native_samples)})
        for fighter in args.phase_probe:
            reset_counters()
            result = input_phase_probe(fighter, args.phase_width)
            report['cases'].append({'kind': 'input-phase-diagnostic', 'fighter': fighter, 'result': result,
                                    'timing': copy.deepcopy(legacy.timing),
                                    'native_counters': copy.deepcopy(native_samples)})
        if args.overlays:
            report['overlay'] = pulse_overlay(report['cases'], args.overlays)
        for case in report['cases']:
            bad = [s for s in case['native_counters'] if s['delta']['frame'] != 1 or
                   s['delta']['snes_vblank_count'] != 1 or s['delta']['lag_frame_counter'] != 0]
            if bad:
                report['failures'].append({'kind': 'native-runtime-counters',
                                           'case': [case['kind'], case['fighter']], 'details': bad})
            for group in ('health', 'timing'):
                for key, value in case.get(group, {}).items():
                    if key.endswith('failures') and value:
                        report['failures'].append({'kind': key, 'case': [case['kind'], case['fighter']], 'details': value})
        if report['failures']:
            raise AssertionError(report['failures'])
        report['status'] = 'passed'
        report['legacy_david_target28_negative_required'] = args.expect_legacy_david_miss
    except Exception as error:
        report['error'] = repr(error)
        report['interrupted_case'] = {'native_counters': copy.deepcopy(native_samples),
                                      'timing': copy.deepcopy(legacy.timing),
                                      'health': copy.deepcopy(dedicated.health)}
        raise
    finally:
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps({k: report[k] for k in ('status', 'rom_sha256', 'elapsed_seconds')}), flush=True)


if __name__ == '__main__':
    main()
