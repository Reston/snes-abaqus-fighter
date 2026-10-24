"""Headless Windows launcher validation; never installs or opens an emulator."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emulator import ROOT
from candidate_sources import snapshot

CHECKS = []


def require(ok, label, details=None):
    CHECKS.append({'check': label, 'passed': bool(ok), 'details': details})
    if not ok:
        raise RuntimeError((label, details))


def invoke(script, *args):
    return subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                           '-File', str(script), *args], cwd=ROOT, capture_output=True, text=True,
                          creationflags=0x08000000 if os.name == 'nt' else 0)


def main():
    started = time.monotonic()
    sources = snapshot(ROOT)
    manifest = json.loads((ROOT / 'dist/manifest.json').read_bytes())
    rom = (ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()
    report = {'status': 'failed', 'version': manifest['version'], 'rom_sha256': manifest['sha256'],
              'source_sha256': sources, 'host_only': True, 'native_execution': False,
              'gui_opened': False, 'setup_invoked': False, 'checks': CHECKS, 'cases': []}
    try:
        require(hashlib.sha256(rom).hexdigest() == manifest['sha256'], 'launcher proof begins with the exact current cartridge')
        actual = invoke(ROOT / 'tools/play.ps1', '-ValidateOnly')
        require(actual.returncode == 0, 'actual launcher validates without provisioning or opening a window', actual.stderr)
        data = json.loads(actual.stdout)
        require(data['Version'] == manifest['version'] and data['Sha256'] == manifest['sha256'] and
                Path(data['RomPath']).resolve() == (ROOT / 'dist/abaqus-after-hours.sfc').resolve(),
                'actual launcher identifies this checkout cartridge, not another worktree', data)
        with tempfile.TemporaryDirectory(prefix='launcher-test-', dir=ROOT / 'build') as directory:
            fixture = Path(directory).resolve()
            if not fixture.is_relative_to((ROOT / 'build').resolve()):
                raise ValueError('launcher fixture cleanup must stay under workspace build')
            for name in ('tools', 'src', 'dist'):
                (fixture / name).mkdir()
            for name in ('play.ps1', 'validate_cartridge.ps1'):
                shutil.copyfile(ROOT / 'tools' / name, fixture / 'tools' / name)
            (fixture / 'tools/setup.ps1').write_text("throw 'Setup must not run during validation'\n")
            (fixture / 'src/version.h').write_text('#define ABAQUS_GAME_VERSION "' + manifest['version'] + '"\n')
            for scenario in ('valid', 'wrong-sha', 'stale-version', 'truncated-rom', 'missing-manifest', 'malformed-manifest'):
                value = dict(manifest)
                payload = rom
                if scenario == 'wrong-sha':
                    value['sha256'] = '0' * 64
                elif scenario == 'stale-version':
                    value['version'] = '0.25.0'
                elif scenario == 'truncated-rom':
                    payload = rom[:-1]
                (fixture / 'dist/abaqus-after-hours.sfc').write_bytes(payload)
                metadata = fixture / 'dist/manifest.json'
                metadata.write_text(json.dumps(value))
                if scenario == 'missing-manifest':
                    metadata.unlink()
                elif scenario == 'malformed-manifest':
                    metadata.write_bytes(b'{')
                before = {p.relative_to(fixture).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in fixture.rglob('*') if p.is_file()}
                result = invoke(fixture / 'tools/play.ps1', '-ValidateOnly')
                require((result.returncode == 0) == (scenario == 'valid'),
                        'launcher accepts only the complete current cartridge', [scenario, result.returncode, result.stderr[-400:]])
                require(not (fixture / '.tools').exists(), 'validation never installs or creates emulator files', scenario)
                after = {p.relative_to(fixture).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in fixture.rglob('*') if p.is_file()}
                require(before == after, 'validating or rejecting a cartridge does not rewrite user files', scenario)
                report['cases'].append({'scenario': scenario, 'accepted': result.returncode == 0, 'passed': True})
        require(snapshot(ROOT) == sources, 'launcher commands and source inputs stay fixed during proof')
        report['status'] = 'passed'
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        report['check_count'] = len(CHECKS)
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
        (ROOT / 'docs/play-flow-v026-launcher-report.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
        print(json.dumps({k: report[k] for k in ('status', 'check_count', 'elapsed_seconds')}), flush=True)


if __name__ == '__main__':
    main()
