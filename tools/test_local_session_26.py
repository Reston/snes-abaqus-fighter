"""Earn local session scores through real two-round matches and rematches."""
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emulator import ROOT
from play_flow_media import inventory as media_inventory
import test_inputs as inputs
import test_music_26 as native
import test_presentation as presentation
from test_play_flow_26 import source_hashes
from test_champion import host_contract

CHECKS = []


def require(ok, label, details=None):
    CHECKS.append({'check': label, 'passed': bool(ok), 'details': details})
    if not ok:
        raise AssertionError((label, details))


def score(e):
    raw = native.read(e, 'stageDepthTable', 9)
    return (raw >> 56) & 255, (raw >> 64) & 255


def earn(e, winner, prior):
    side, other = str(winner + 1), str(2 - winner)
    watched_round = False
    for callbacks in range(14000):
        if inputs.native_screen(e) == 4:
            e.run(16)
            s = inputs.trace(e)
            require(s['wins' + side] == 2 and s['wins' + other] == 0,
                    'the result follows an earned two-round victory', [winner, s])
            return callbacks
        s = inputs.trace(e)
        if s['round_end'] and s['wins' + side] == 1 and not watched_round:
            require(score(e) == prior, 'one round never counts as a session match win', [winner, prior, score(e)])
            watched_round = True
        keys = []
        if not (s['intro'] or s['round_end'] or s['hitstop'] or s['action' + side] or s['hurt' + side] or s['down_state' + side]):
            delta = inputs.signed16(s['x' + other]) - inputs.signed16(s['x' + side])
            keys = ['right' if delta > 0 else 'left'] if abs(delta) > 29 * 16 else ['x']
        e.run(1, **{'p1' if winner == 0 else 'p2': keys})
        if keys == ['x']:
            e.run(1)
    raise AssertionError(('local session victory did not finish', winner, inputs.trace(e)))


def case(fighter, independent):
    original = inputs.Emulator
    try:
        inputs.Emulator = lambda **kwargs: native.Rig(independent)
        e = inputs.boot(1, fighter=fighter, fighter2=fighter)
    finally:
        inputs.Emulator = original
    try:
        require(score(e) == (0, 0), 'a new character selection starts a fresh local session', [fighter, independent])
        expected = [0, 0]
        matches = []
        for index, winner in enumerate((0, 1, 0)):
            callbacks = earn(e, winner, tuple(expected))
            expected[winner] += 1
            require(score(e) == tuple(expected), 'exactly one session win is awarded to the actual match winner', [fighter, winner, expected, score(e)])
            label = f'P1 {expected[0]:02} - {expected[1]:02} P2'
            start = len(presentation.checks)
            presentation.verify_opaque_text_rows(e, [(17, 15, 'SESSION WINS'), (19, 15, label)], 'earned local session score')
            require(all(c['passed'] for c in presentation.checks[start:]), 'native result text distinguishes session wins from round wins')
            e.run(90)
            require(score(e) == tuple(expected), 'waiting on the result never awards duplicate session wins')
            matches.append({'winner': winner, 'score': list(expected), 'earned_callbacks': callbacks})
            if index < 2:
                inputs.press(e, 'a' if index == 0 else 'start', index % 2)
                e.run(30)
                s = inputs.trace(e)
                require(inputs.native_screen(e) == 3 and score(e) == tuple(expected) and s['wins1'] == s['wins2'] == 0,
                        'either-pad rematch keeps session wins and resets only the round score')
                require(s['fighter_id1'] == s['fighter_id2'] == fighter and s['round'] == 1,
                        'the rivalry retains both fighters across rematches')
        if fighter == 0 and not independent:
            e.frame.save(ROOT / 'docs/screenshots/play-flow-v026/local-session-2-1.png')
        inputs.press(e, 'b', 1)
        e.run(35)
        require(inputs.native_screen(e) == 1 and score(e) == (0, 0), 'P2 returning to character select ends and clears the session')
        return {'fighter': fighter, 'independent': independent, 'matches': matches, 'passed': True}
    finally:
        e.close()


def main():
    started = time.monotonic()
    sources = source_hashes()
    manifest = json.loads((ROOT / 'dist/manifest.json').read_bytes())
    report = {'status': 'failed', 'version': manifest['version'], 'rom_sha256': manifest['sha256'],
              'source_sha256': sources, 'checks': CHECKS, 'native_health': native.HEALTH,
              'host_contract': host_contract(), 'controller_only': True, 'memory_writes': False,
              'save_states': False, 'cases': []}
    try:
        require(hashlib.sha256((ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()).hexdigest() == manifest['sha256'], 'session proof loads the exact current cartridge')
        require(hashlib.sha256((ROOT / '.tools/core/snes9x_libretro.dll').read_bytes()).hexdigest().lower() == native.EXPECTED_NATIVE_CORE['dll_sha256'].lower(), 'session proof hashes the pinned native core')
        report['independent_core'] = native.compatibility.verify_manifest_and_pinned_core()
        for fighter in range(12):
            report['cases'].append(case(fighter, False))
            print(json.dumps({'fighter': fighter, 'status': 'passed'}), flush=True)
        report['cases'].append(case(0, True))
        require(not native.HEALTH['failures'], 'local sessions retain strict native cadence OBJ FIFO and PCM health')
        require(source_hashes() == sources, 'session runtime and producer inputs stay fixed')
        report['captures'] = media_inventory(ROOT, 'session')
        report['status'] = 'passed'
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        report['check_count'] = len(CHECKS)
        report['native_check_count'] = len(native.CHECKS)
        report['native_failed_checks'] = [r for r in native.CHECKS if not r['passed']]
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
        (ROOT / 'docs/play-flow-v026-session-report.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
        print(json.dumps({k: report[k] for k in ('status', 'check_count', 'elapsed_seconds')}), flush=True)


if __name__ == '__main__':
    main()
