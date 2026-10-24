"""All-roster special-command hints, exact portraits and both native cores."""
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
from test_play_flow_26 import source_hashes
from test_champion import host_contract

# The retained v0.25 roster's four ordinary-special families, independently
# enumerated here. No fighter profile is changed by the display pass.
FAMILIES = (0, 0, 1, 1, 2, 3, 2, 3, 2, 0, 3, 2)
LABELS = ('WAVE SHOT', 'RUSH', 'LOW WAVE', 'RISING')
CHECKS = []


def require(ok, label, details=None):
    CHECKS.append({'check': label, 'passed': bool(ok), 'details': details})
    if not ok:
        raise AssertionError((label, details))


def case(independent):
    original = inputs.Emulator
    try:
        inputs.Emulator = lambda **kwargs: native.Rig(independent)
        e = inputs.menu_title()
    finally:
        inputs.Emulator = original
    rows = []
    try:
        inputs.menu_select(e, 1)
        for player in (0, 1):
            field = 'selected2' if player else 'selected'
            for _ in range(12):
                if native.read(e, field) == 0:
                    break
                inputs.menu_press(e, ['left'], player)
            for fighter in range(12):
                require(native.read(e, field) == fighter, 'hint belongs to the actual hovered fighter and controller', [independent, player, fighter])
                start = len(presentation.checks)
                presentation.verify_menu_font_bank(e, [(19, 22, 'SPECIAL'), (20, 22, LABELS[FAMILIES[fighter]]),
                    (22, 22, 'DOWN+Y'), (23, 22, '32 ENERGY'), (25, 22, 'SUPER Y+B')], 'roster move hints')
                presentation.verify_large_portrait(e, fighter)
                require(all(c['passed'] for c in presentation.checks[start:]), 'native hint pixels and the exact approved portrait pass together')
                # Explicitly reject old longer-family letters surviving a hover.
                tile_row = presentation.map_row(presentation.vram_bytes(e), 20)
                require(all((tile_row[x] & 1023) == 0 for x in range(22 + len(LABELS[FAMILIES[fighter]]), 32)),
                        'shorter move families clear the previous longer label', [independent, player, fighter])
                if not independent and player == 0 and fighter in (0, 2, 4, 5):
                    e.frame.save(ROOT / f'docs/screenshots/play-flow-v026/roster-family-{FAMILIES[fighter]}.png')
                rows.append({'fighter': fighter, 'player': player, 'family': FAMILIES[fighter], 'passed': True})
                if fighter < 11:
                    inputs.menu_press(e, ['right'], player)
            inputs.menu_press(e, ['a'], player)
        inputs.menu_press(e, ['a'], 1)
        e.run(160)
        s = inputs.trace(e)
        require(s['fighter_id1'] == s['fighter_id2'] == 11 and s['family1'] == s['family2'] == FAMILIES[11],
                'hinted roster choices load the matching native special family', [independent, s])
        return {'independent': independent, 'roster': rows, 'passed': True}
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
        require(hashlib.sha256((ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()).hexdigest() == manifest['sha256'], 'roster proof loads the exact current cartridge')
        require(hashlib.sha256((ROOT / '.tools/core/snes9x_libretro.dll').read_bytes()).hexdigest().lower() == native.EXPECTED_NATIVE_CORE['dll_sha256'].lower(), 'roster proof hashes the pinned native core')
        report['independent_core'] = native.compatibility.verify_manifest_and_pinned_core()
        for independent in (False, True):
            report['cases'].append(case(independent))
        require(not native.HEALTH['failures'], 'roster-to-fight transition keeps native cadence OBJ FIFO and PCM health')
        require(source_hashes() == sources, 'roster proof runtime and producers remain fixed')
        report['status'] = 'passed'
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        report['check_count'] = len(CHECKS)
        report['native_check_count'] = len(native.CHECKS)
        report['native_failed_checks'] = [r for r in native.CHECKS if not r['passed']]
        report['presentation_checks'] = len(presentation.checks)
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
        (ROOT / 'docs/play-flow-v026-roster-report.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
        print(json.dumps({k: report[k] for k in ('status', 'check_count', 'elapsed_seconds')}), flush=True)


if __name__ == '__main__':
    main()
