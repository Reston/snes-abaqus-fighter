"""Audit the packaged technical baseline; this does not certify public polish."""
from pathlib import Path
import hashlib
import json
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'docs/release-audit.json'
checks = []


def check(condition, label, details=None):
    if not condition:
        raise AssertionError((label, details))
    checks.append({'check': label, 'passed': True, 'details': details})


def sha(data):
    return hashlib.sha256(data).hexdigest()


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

        suites = {}
        reports = ['test-report.json', 'character-test-report.json',
                   'presentation-test-report.json', 'input-test-report.json']
        for name in reports:
            report = json.loads((ROOT / 'docs' / name).read_text())
            check(report['rom_sha256'] == manifest['sha256'] and
                  report.get('status', 'passed') == 'passed' and
                  report['passed'] == len(report['checks']) > 0 and
                  all(item['passed'] for item in report['checks']),
                  'exact-ROM suite is complete: ' + name, report['passed'])
            suites[name] = report['passed']
        result['native_suite_checks'] = sum(suites.values())
        result['suites'] = suites

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
            check(all(name in package.namelist() for name in
                      ['Play.cmd', 'LICENSE', 'CREDITS.md', 'emulator/LICENSE',
                       'licenses/PVSnesLib.txt', 'licenses/SNESMod.txt', 'licenses/Snes9x.txt']),
                  'offline launcher and license notices are present')
            for name in ['gameplay', 'characters', 'presentation', 'inputs']:
                check(json.loads(package.read(f'qa/{name}.json'))['rom_sha256'] == manifest['sha256'],
                      'packaged exact-ROM evidence: ' + name)
            check(json.loads(package.read('qa/compatibility.json')) == compatibility and
                  package.read('COMPATIBILITY.md') == (ROOT / 'docs/COMPATIBILITY.md').read_bytes(),
                  'packaged independent-engine smoke evidence and scope')
        check((ROOT / 'dist/release-sha256.txt').read_text().split()[0] == sha(archive.read_bytes()),
              'offline archive matches its published checksum')
        result['status'] = 'passed'
        result['remaining_release_gates'] = 'docs/PUBLIC-RELEASE.md'
    except BaseException as error:
        result['error'] = repr(error)
        raise
    finally:
        result['audit_checks'] = len(checks)
        REPORT.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in
                      ['status', 'version', 'rom_sha256', 'native_suite_checks',
                       'audit_checks', 'public_release_certified']}))


if __name__ == '__main__':
    main()
