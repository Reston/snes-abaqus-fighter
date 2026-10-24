"""Read-only timing guide proof, including the actual uninterrupted whiff clocks."""
import ctypes as C
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emulator import ROOT
import test_inputs as inputs
import test_music_26 as native
import test_presentation as presentation
import test_training as training
from test_play_flow_26 import source_hashes
from test_champion import host_contract

CHECKS = []
MOVES = (('y', 1), ('x', 3), ('b', 4), ('a', 5))


def require(ok, label, details=None):
    CHECKS.append({'check': label, 'passed': bool(ok), 'details': details})
    if not ok:
        raise AssertionError((label, details))


def centered(y, text):
    return y, (32 - len(text)) // 2, text


def page(e, player, timings):
    vr = presentation.vram_bytes(e)
    require(training.decode_text(vr, 9, 10)[3:5] == f'P{player + 1}',
            'normal guide identifies its actual controller port', player)
    rows = [centered(6, 'NORMAL TIMING 2/2'), (11, 18, 'S  A  R'),
            centered(17, 'S STARTUP A ACTIVE R RECOVERY'),
            centered(18, 'GROUNDED STANDING NORMALS'),
            centered(19, 'HITSTOP ADDS A CONTACT PAUSE'),
            centered(21, 'TICKS AT NORMAL VIDEO RATE'),
            centered(22, 'UP: P2 NORMALS' if not player else 'UP: SPECIAL MOVES')]
    for row, timing in enumerate(timings, 12):
        for x, value in zip((18, 21, 24), timing):
            text = f'{value:02}'
            require(training.decode_text(vr, row, row + 1)[x:x + 2] == text,
                    'displayed normal timing matches the native match cache', [player, row, x, value])
            rows.append((row, x, text))
    start = len(presentation.checks)
    presentation.verify_opaque_text_rows(e, rows, 'actual normal timing guide')
    require(all(c['passed'] for c in presentation.checks[start:]),
            'normal timing guide glyph pixels use the opaque current PPU font', player)


def case(fighter, independent):
    original = inputs.Emulator
    try:
        inputs.Emulator = lambda **kwargs: native.Rig(independent)
        e = inputs.boot(1, fighter=fighter, fighter2=(fighter + 1) % 12)
    finally:
        inputs.Emulator = original
    try:
        inputs.press(e, 'start')
        inputs.press(e, 'select')
        inputs.press(e, 'select')
        e.run(8)
        frozen = native.physics(e)
        timings = []
        for player in (0, 1):
            inputs.press(e, 'up', player)
            e.run(10)
            require(native.read(e, 'stageDepthTable', 4) >> 24 == player + 1,
                    'either pad cycles from specials to P1 and P2 normal timing', [fighter, player, independent])
            values = []
            for _, action in MOVES:
                index = player * 16 + action
                start = C.string_at(e.ram + native.SYMS['matchStartup'] + index, 1)[0]
                active_end = C.string_at(e.ram + native.SYMS['matchActiveEnd'] + index, 1)[0]
                end = C.string_at(e.ram + native.SYMS['matchActionEnd'] + index, 1)[0]
                values.append((start, active_end - start, end - active_end))
            page(e, player, values)
            require(native.physics(e) == frozen, 'browsing both timing tables keeps the fight frozen')
            if fighter == 0 and not independent:
                e.frame.save(ROOT / f'docs/screenshots/play-flow-v026/normal-timing-p{player + 1}.png')
            timings.append(values)
        inputs.press(e, 'up')
        e.run(10)
        require(native.read(e, 'stageDepthTable', 4) >> 24 == 0,
                'third Up returns to the existing special-move page')
        text = training.decode_text(presentation.vram_bytes(e), 23, 24)
        require('UP: P1 NORMAL TIMING' in text, 'special page advertises its timing-table shortcut')
        # Start owns a simultaneous Up and resumes; no phantom table change.
        e.run(3, p1=['start'], p2=['up'])
        e.run(3)
        require(native.read(e, 'paused') == 0 and native.read(e, 'stageDepthTable', 4) >> 24 == 0,
                'Start retains priority over normal-table browsing')
        clocks = []
        for player in (0, 1):
            for (key, action), expected in zip(MOVES, timings[player]):
                e.run(5)
                for _ in range(6):
                    s = e.run(1, **{'p1' if player == 0 else 'p2': [key]})
                    if s[f'action{player + 1}'] == action:
                        break
                raw = C.string_at(e.ram + native.SYMS['fighters'] + player * 64, 64)
                actual = (raw[24], raw[63] - raw[24], raw[62] - raw[63])
                require(actual == expected, 'the real accepted ground action has exactly the displayed timing',
                        [fighter, player, key, expected, actual])
                ticks = []
                for _ in range(120):
                    if not s[f'action{player + 1}']:
                        break
                    raw = C.string_at(e.ram + native.SYMS['fighters'] + player * 64, 64)
                    ticks.append(raw[17])
                    s = e.run(1)
                require(ticks == list(range(1, sum(expected))) and s['hp1'] == s['hp2'] == 128,
                        'uninterrupted whiff visits every displayed tick without damage or contact',
                        [fighter, player, key, expected, ticks])
                clocks.append({'port': player, 'key': key, 'timing': actual, 'ticks': len(ticks)})
        inputs.press(e, 'start')
        require(native.read(e, 'stageDepthTable', 4) >> 24 == 0,
                'a new pause resets the timing view without a new state allocation')
        return {'fighter': fighter, 'opponent': (fighter + 1) % 12, 'independent': independent,
                'native_ground_actions': clocks, 'passed': True}
    finally:
        e.close()


def main():
    start = time.monotonic()
    sources = source_hashes()
    manifest = json.loads((ROOT / 'dist/manifest.json').read_bytes())
    report = {'status': 'failed', 'version': manifest['version'], 'rom_sha256': manifest['sha256'],
              'source_sha256': sources, 'checks': CHECKS, 'native_health': native.HEALTH,
              'host_contract': host_contract(), 'controller_only': True, 'memory_writes': False,
              'save_states': False, 'cases': []}
    try:
        require(hashlib.sha256((ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()).hexdigest() == manifest['sha256'],
                'normal-guide proof loads the exact current cartridge')
        require(hashlib.sha256((ROOT / '.tools/core/snes9x_libretro.dll').read_bytes()).hexdigest().lower() == native.EXPECTED_NATIVE_CORE['dll_sha256'].lower(),
                'normal-guide proof hashes the actual pinned Snes9x core')
        report['independent_core'] = native.compatibility.verify_manifest_and_pinned_core()
        for independent in (False, True):
            for fighter in range(12):
                report['cases'].append(case(fighter, independent))
        require(not native.HEALTH['failures'], 'normal tables retain strict native health on both cores')
        require(source_hashes() == sources, 'normal-guide inputs remain fixed during execution')
        report['status'] = 'passed'
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        report['check_count'] = len(CHECKS)
        report['native_check_count'] = len(native.CHECKS)
        report['native_failed_checks'] = [c for c in native.CHECKS if not c['passed']]
        report['elapsed_seconds'] = round(time.monotonic() - start, 3)
        (ROOT / 'docs/play-flow-v026-normal-guide-report.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
        print(json.dumps({k: report[k] for k in ('status', 'check_count', 'elapsed_seconds')}), flush=True)


if __name__ == '__main__':
    main()
