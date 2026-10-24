"""Session-best Training combos survive retries, without counting blocked hits."""
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emulator import ROOT
import test_confirm_26 as confirm
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


def best(e):
    value = native.read(e, 'stageDepthTable', 7)
    return (value >> 32) & 255, (value >> 40) & 65535


def tools(r):
    inputs.press(r.e, 'start', r.fighter % 2)
    for _ in range(3):
        inputs.press(r.e, 'select')
    r.e.run(10)
    require(native.read(r.e, 'paused') == 1 and native.read(r.e, 'pausePage') == 3,
            'best combo is reached on the existing Tools page')


def case(fighter, independent):
    r = confirm.Rig(fighter, independent)
    try:
        require(best(r.e) == (0, 0), 'new Training session starts with no invented best', [fighter, independent])
        initial = confirm.opener(r, 'y')
        single = 128 - initial['hp2']
        # Reset before the contact/actor work lets the deferred footer catch up.
        inputs.press(r.e, 'select')
        r.e.run(10)
        require(best(r.e) == (1, single) and native.read(r.e, 'trainingHits') == 0,
                'immediate live retry preserves the earned pending hit but clears current totals', [fighter, best(r.e), single])
        confirm.opener(r, 'y')
        s = r.step(('x',))
        for _ in range(100):
            if s['action1'] == 3 and s['connected1']:
                break
            s = r.step()
        damage = 128 - s['hp2']
        require(s['connected1'] == 2 and s['combo_link1'] == 2 and damage > single,
                'larger record comes from an actual two-hit confirm', [fighter, s])
        r.settle()
        r.e.run(100)
        require(best(r.e) == (2, damage), 'deferred UI records the actual higher-damage combo', [fighter, best(r.e), damage])
        tools(r)
        label = f'BEST 02H {damage:03}D'
        start = len(presentation.checks)
        presentation.verify_opaque_text_rows(r.e, [(19, (32 - len(label)) // 2, label)], 'session best')
        require(all(c['passed'] for c in presentation.checks[start:]), 'native Tools pixels display the actual best hits and damage')
        if fighter == 0 and not independent:
            r.e.frame.save(ROOT / 'docs/screenshots/play-flow-v026/training-best-combo.png')
        inputs.press(r.e, 'x', 1)
        r.e.run(10)
        require(best(r.e) == (2, damage) and native.read(r.e, 'trainingHits') == 0 and native.read(r.e, 'trainingDamage', 2) == 0,
                'either-pad X retries preserve the record while clearing the new attempt')
        inputs.press(r.e, 'start')
        confirm.opener(r, 'y')
        r.settle()
        r.e.run(100)
        require(best(r.e) == (2, damage), 'a later single hit cannot replace the better two-hit record')
        tools(r)
        inputs.press(r.e, 'down')
        inputs.press(r.e, 'x')
        r.e.run(10)
        require(native.read(r.e, 'trainingDummy') == 4 and best(r.e) == (2, damage),
                'changing and restarting another drill keeps the same session record')
        inputs.press(r.e, 'b', 1)
        r.e.run(35)
        require(inputs.native_screen(r.e) == 1 and best(r.e) == (0, 0),
                'returning to character select begins a fresh Training session')
        return {'fighter': fighter, 'independent': independent, 'single_damage': single,
                'best_hits': 2, 'best_damage': damage, 'reset_before_publication': True,
                'live_reset_retains_best': True, 'guide_retry_retains_best': True,
                'new_session_clears_best': True, 'passed': True}
    finally:
        r.close()


def main():
    start = time.monotonic()
    sources = source_hashes()
    manifest = json.loads((ROOT / 'dist/manifest.json').read_bytes())
    report = {'status': 'failed', 'version': manifest['version'], 'rom_sha256': manifest['sha256'],
              'source_sha256': sources, 'checks': CHECKS, 'native_health': native.HEALTH,
              'host_contract': host_contract(), 'controller_only': True, 'memory_writes': False,
              'save_states': False, 'cases': []}
    try:
        require(hashlib.sha256((ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()).hexdigest() == manifest['sha256'], 'best proof loads the exact current cartridge')
        require(hashlib.sha256((ROOT / '.tools/core/snes9x_libretro.dll').read_bytes()).hexdigest().lower() == native.EXPECTED_NATIVE_CORE['dll_sha256'].lower(), 'best proof hashes the pinned native core')
        report['independent_core'] = native.compatibility.verify_manifest_and_pinned_core()
        for fighter in range(12):
            report['cases'].append(case(fighter, False))
        for fighter in (0, 5, 11):
            report['cases'].append(case(fighter, True))
        require(not native.HEALTH['failures'], 'session best has no native cadence OBJ FIFO or PCM failures')
        require(source_hashes() == sources, 'best-combo inputs remain fixed')
        report['status'] = 'passed'
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        report['check_count'] = len(CHECKS)
        report['native_check_count'] = len(native.CHECKS)
        report['native_failed_checks'] = [r for r in native.CHECKS if not r['passed']]
        report['elapsed_seconds'] = round(time.monotonic() - start, 3)
        (ROOT / 'docs/play-flow-v026-best-report.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
        print(json.dumps({k: report[k] for k in ('status', 'check_count', 'elapsed_seconds')}), flush=True)


if __name__ == '__main__':
    main()
