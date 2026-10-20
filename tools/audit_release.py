"""Audit the packaged technical baseline; this does not certify public polish."""
from pathlib import Path
import hashlib
import json
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from PIL import Image
from release_evidence import (EXTRA_REPORTS, training_report_path,
                               validate_release_evidence)

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'docs/release-audit.json'
checks = []


def check(condition, label, details=None):
    if not condition:
        raise AssertionError((label, details))
    checks.append({'check': label, 'passed': True, 'details': details})


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_value(value):
    # Evidence checks use sets for complete matrix/coverage comparisons.
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    raise TypeError(f'Unsupported audit detail: {type(value).__name__}')


def main():
    result = {'scope': 'packaged technical baseline',
              'public_release_certified': False, 'status': 'failed',
              'checks': checks}
    try:
        manifest = json.loads((ROOT / 'dist/manifest.json').read_text())
        rom = (ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()
        result.update(version=manifest['version'], rom_sha256=sha(rom))
        check(sha(rom) == manifest['sha256'], 'cartridge matches manifest')
        check(len(rom) == manifest['bytes'] == 4 * 1024 * 1024,
              'native cartridge is the current 4 MiB target')
        check(rom[0x7fd5] == 0x30, 'header identifies FastROM LoROM')
        checksum = int.from_bytes(rom[0x7fde:0x7fe0], 'little')
        complement = int.from_bytes(rom[0x7fdc:0x7fde], 'little')
        check(checksum == sum(rom) & 0xffff and checksum ^ complement == 0xffff,
              'SNES checksum and complement are valid')

        # Release-scale evidence is intentionally separate from the bounded
        # Test.cmd smoke suites.  Use the same validator as package.py so the
        # audit and the ZIP gate enforce identical current-ROM, source-freeze,
        # endurance, independent-combat and full-matchup contracts.
        result['release_evidence'] = validate_release_evidence(ROOT, sha(rom), check)
        training_source = training_report_path(ROOT)

        suites = {}
        reports = ['test-report.json', 'character-test-report.json',
                   'presentation-test-report.json', 'input-test-report.json',
                   'stage-test-report.json']
        for name in reports:
            report = json.loads((ROOT / 'docs' / name).read_text())
            check(report['rom_sha256'] == manifest['sha256'] and
                  report.get('status', 'passed') == 'passed' and
                  report['passed'] == len(report['checks']) > 0 and
                  all(item['passed'] for item in report['checks']),
                  'exact-ROM suite is complete: ' + name, report['passed'])
            suites[name] = report['passed']
        training_report = json.loads(training_source.read_text())
        check(training_report['rom_sha256'] == manifest['sha256'] and
              training_report['suite'] == 'training' and
              training_report['status'] == 'passed' and
              training_report['passed'] == len(training_report['checks']) > 0 and
              all(item['passed'] for item in training_report['checks']),
              'exact-ROM suite is complete: training-test-report.json',
              training_report['passed'])
        suites['training-test-report.json'] = training_report['passed']
        result['native_suite_checks'] = sum(suites.values())
        result['suites'] = suites

        stage_report = json.loads((ROOT / 'docs/stage-test-report.json').read_text())
        stages = stage_report['stages']
        check(set(stages) == {'las-condes', 'el-castillo', 'la-oficina'},
              'stage evidence covers all three locations')
        for name, stage in stages.items():
            waves, stress = stage['two_waves'], stage['oam_stress']
            check(set(stage['phase_results']) == {'0', '1', '2', '3'} and
                  waves['wave1_frames'] > 0 and waves['wave2_frames'] > 0 and
                  waves['max_tiles'] <= 34 and waves['max_sprites'] <= 32 and
                  all((status & 0xc0) == 0 for status in waves['ppu_stat']) and
                  stress['frames'] == 600 and stress['max_tiles'] <= 34 and
                  stress['max_scanline'] <= 32 and
                  all((status & 0xc0) == 0 for status in stress['statuses']),
                  'ambient phases and measured OBJ budget: ' + name)

        compatibility = json.loads((ROOT / 'docs/compatibility-test-report.json').read_text())
        cadence = compatibility['checks']['cadence']
        check(compatibility['status'] == 'passed' and compatibility['pinned_core'] and
              compatibility['rom']['sha256'] == manifest['sha256'],
              'independent-engine smoke matches the current cartridge')
        check(cadence['observed_deltas'] == 600 and cadence['delta_min'] == 1 and
              cadence['delta_max'] == 1 and cadence['non_one_deltas'] == 0,
              'independent-engine neutral cadence is 600 unit steps')
        result['independent_engine_smoke'] = {
            'scope': compatibility['scope'], 'core': compatibility['core'],
            'cadence': cadence,
        }
        independent_stages = compatibility['checks']['stage_ambient_and_freeze']
        check(independent_stages['passed'] and set(independent_stages['stages']) == set(stages),
              'independent engine covers all three ambient stage loops')
        for name, stage in independent_stages['stages'].items():
            plate, phases = stage['static_plate_color'], stage['ambient_phases']
            check(plate['passed'] and plate['sample_count'] >= 10000 and
                  plate['match_ratio_le_8'] >= 0.99 and
                  phases['phase_count'] == 4 and phases['ppu_patch_distinct'] == 4,
                  'independent PPU colors and four visible phases: ' + name)
        low_wave = compatibility['checks']['synchronized_low_wave']
        check(low_wave['passed'] and low_wave['synchronized_frames_in_600'] > 0 and
              low_wave['observed_deltas'] == 600 and low_wave['non_one_deltas'] == 0 and
              all((status & 0xc0) == 0 for status in low_wave['stat77_values']),
              'independent low-wave combat cadence and PPU overflow check')

        entries = json.loads((ROOT / 'assets/generated/character-manifest.json').read_text())
        check(len(entries) == 12, 'all twelve fighters have manifests')
        source_count = 0
        frame_counts = []
        native_digests = []
        for fighter, entry in enumerate(entries):
            sources = [entry['source_legacy']] + entry['animation_sources']
            for source in sources:
                path = ROOT / source['file']
                check(sha(path.read_bytes()) == source['sha256'],
                      'source provenance hash: ' + source['file'])
                source_count += 1
            count = entry['frame_count']
            frames = entry['frames']
            check(entry['id'] == fighter and count >= 48 and count % 8 == 0 and
                  len(frames) == count, 'complete frame contract', fighter)
            scales = [item['physical_scale'] for item in frames]
            check(max(scales) - min(scales) < 1e-9,
                  'one physical scale across the fighter', fighter)
            with Image.open(ROOT / f'assets/generated/fighter{fighter:02}.png') as preview:
                check(preview.mode == 'RGBA' and preview.size == (96 * count, 80),
                      'native preview matches frame contract', fighter)
            banks = []
            for bank in range(count // 8):
                suffix = '' if bank == 0 else chr(ord('a') + bank)
                data = (ROOT / f'assets/generated/fighter{fighter:02}{suffix}.bin').read_bytes()
                check(len(data) == 30720, 'complete LoROM-safe fighter bank',
                      {'fighter': fighter, 'bank': bank})
                banks.append(data)
            native_digests.append(sha(b''.join(banks)))
            frame_counts.append(count)
        check(len(set(native_digests)) == 12, 'twelve distinct native fighter sets')
        result['roster'] = {'fighters': 12, 'frames': sum(frame_counts),
                            'source_atlases_verified': source_count}

        archive = ROOT / f"dist/Abaqus-After-Hours-v{manifest['version']}-Windows.zip"
        with zipfile.ZipFile(archive) as package:
            check(package.testzip() is None, 'offline package CRC check')
            check(package.read('abaqus-after-hours.sfc') == rom and
                  json.loads(package.read('manifest.json')) == manifest,
                  'offline package contains the exact cartridge')
            check(package.read('emulator/snes9x.conf') ==
                  (ROOT / 'tools/snes9x.conf').read_bytes(),
                  'offline package contains the current controls/display defaults')
            for report_name in ('compatibility-test-report.json',
                                'compatibility-combat-test-report.json'):
                check(package.read(report_name) ==
                      (ROOT / 'docs' / report_name).read_bytes(),
                      'offline compatibility guide report link: ' + report_name)
            check(all(name in package.namelist() for name in
                      ['Play.cmd', 'LICENSE', 'CREDITS.md', 'emulator/LICENSE',
                       'licenses/PVSnesLib.txt', 'licenses/SNESMod.txt', 'licenses/Snes9x.txt']),
                  'offline launcher and license notices are present')
            native_package_sources = {
                'gameplay': ROOT / 'docs/test-report.json',
                'characters': ROOT / 'docs/character-test-report.json',
                'presentation': ROOT / 'docs/presentation-test-report.json',
                'inputs': ROOT / 'docs/input-test-report.json',
                'stages': ROOT / 'docs/stage-test-report.json',
                'training': training_source,
            }
            for name, source in native_package_sources.items():
                packaged = package.read(f'qa/{name}.json')
                check(packaged == source.read_bytes() and
                      json.loads(packaged)['rom_sha256'] == manifest['sha256'],
                      'packaged exact-ROM evidence and byte identity: ' + name)
            check(package.read('qa/stage-dynamics.json') ==
                  (ROOT / 'assets/generated/stage-dynamics.json').read_bytes() and
                  package.read('OBJ-BUDGET.md') == (ROOT / 'docs/OBJ-BUDGET.md').read_bytes(),
                  'packaged stage animation contract and OBJ budget evidence')
            check(json.loads(package.read('qa/compatibility.json')) == compatibility and
                  package.read('COMPATIBILITY.md') == (ROOT / 'docs/COMPATIBILITY.md').read_bytes(),
                  'packaged independent-engine smoke evidence and scope')
            for key, relative in EXTRA_REPORTS.items():
                archive_name = {
                    'matchups': 'qa/matchups.json',
                    'independent_combat': 'qa/independent-combat.json',
                    'endurance': 'qa/endurance.json',
                    'fresh_build': 'qa/fresh-build.json',
                }[key]
                check(package.read(archive_name) == (ROOT / relative).read_bytes() and
                      json.loads(package.read(archive_name)).get('status') == 'passed',
                      'packaged release evidence: ' + key)
        check((ROOT / 'dist/release-sha256.txt').read_text().split()[0] == sha(archive.read_bytes()),
              'offline archive matches its published checksum')
        result['status'] = 'passed'
        result['remaining_release_gates'] = 'docs/PUBLIC-RELEASE.md'
    except BaseException as error:
        result['error'] = repr(error)
        raise
    finally:
        result['audit_checks'] = len(checks)
        REPORT.write_text(json.dumps(result, indent=2, default=json_value) + '\n')
    print(json.dumps({key: result[key] for key in
                      ['status', 'version', 'rom_sha256', 'native_suite_checks',
                       'audit_checks', 'public_release_certified']}))


if __name__ == '__main__':
    main()
