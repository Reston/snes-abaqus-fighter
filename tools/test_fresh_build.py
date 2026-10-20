"""Rebuild a committed source export with freshly extracted pinned tools.

Only verified download archives may be copied from the local cache. No
extracted SDK, Python environment, build directory or emulator state is reused.
The fresh Build.cmd --assets run must reproduce the current tested cartridge.
Temporary source exports and logs stay under ignored build/fresh-build/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'docs/fresh-build-test-report.json'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def command(args: list[str], cwd: Path = ROOT, env: dict | None = None) -> str:
    result = subprocess.run(args, cwd=cwd, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, errors='replace', env=env)
    if result.returncode:
        raise RuntimeError((args, result.returncode,
                            result.stdout[-3000:], result.stderr[-3000:]))
    return result.stdout.strip()


def canonical_symbols(data: bytes) -> str:
    text = data.decode('utf-8').replace('\\', '/')
    match = re.search(r'for "(.+)/dist/abaqus-after-hours\.sfc"', text)
    if not match:
        raise AssertionError('linker symbols do not identify the output path')
    return text.replace(match.group(1), '<SOURCE>').replace('\r\n', '\n')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-ref', default='HEAD')
    args = parser.parse_args()
    started = time.monotonic()
    result: dict = {
        'status': 'failed',
        'scope': 'committed source export, fresh tool extraction, full asset rebuild',
        'host_contract': {'gui_opened': False, 'emulator_launched': False,
                          'pre_extracted_tools_reused': False,
                          'build_intermediates_reused': False},
    }
    try:
        commit = command(['git', 'rev-parse', '--verify', '--end-of-options',
                          args.source_ref + '^{commit}'])
        result['source_commit'] = commit
        result['source_tree'] = command(['git', 'rev-parse', commit + '^{tree}'])
        expected = json.loads((ROOT / 'dist/manifest.json').read_text())
        original_rom = (ROOT / 'dist' / expected['rom']).read_bytes()
        if sha(original_rom) != expected['sha256']:
            raise AssertionError('current cartridge and manifest disagree')
        result['rom_sha256'] = expected['sha256']

        container = ROOT / 'build/fresh-build'
        container.mkdir(parents=True, exist_ok=True)
        run_root = Path(tempfile.mkdtemp(prefix=commit[:8] + '-', dir=container))
        archive = run_root / 'source.zip'
        source = run_root / 'source'
        source.mkdir()
        result['work_directory'] = str(run_root.relative_to(ROOT)).replace('\\', '/')
        command(['git', 'archive', '--format=zip', '--output=' + str(archive), commit])
        with zipfile.ZipFile(archive) as package:
            for item in package.infolist():
                target = (source / item.filename).resolve()
                if not target.is_relative_to(source.resolve()):
                    raise AssertionError(('source archive escapes export', item.filename))
                parts = Path(item.filename).parts
                if any(part.lower() in ('.tools', 'build', '.git') for part in parts):
                    raise AssertionError(('source contains a tool/build cache', item.filename))
                mode = item.external_attr >> 16
                kind = stat.S_IFMT(mode)
                if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise AssertionError(('source contains a non-regular entry', item.filename))
            generated_before = {
                name: package.read(name) for name in package.namelist()
                if name.startswith('assets/generated/') and not name.endswith('/')
            }
            original_symbols = package.read('dist/abaqus-after-hours.sym')
            committed_manifest = json.loads(package.read('dist/manifest.json'))
            if committed_manifest['sha256'] != expected['sha256']:
                raise AssertionError('commit does not contain the current cartridge; commit build inputs first')
            package.extractall(source)
        result['source_archive_sha256'] = sha(archive.read_bytes())

        pins = re.findall(r"Get-PinnedArchive\s+'([^']+)'\s+'([^']+)'\s+'([A-F0-9]{64})'",
                          (source / 'tools/setup.ps1').read_text())
        if len(pins) != 4:
            raise AssertionError(('expected four pinned bootstrap archives', len(pins)))
        cache = source / '.tools'
        cache.mkdir()
        reused = []
        for url, name, digest in pins:
            prior = ROOT / '.tools' / name
            if prior.exists():
                if sha(prior.read_bytes()).upper() != digest:
                    raise AssertionError(('parent cache archive pin mismatch', name))
                shutil.copyfile(prior, cache / name)
                reused.append(name)
        result['cached_archives_reused'] = reused
        log = run_root / 'build.log'
        build_env = os.environ.copy()
        removed = []
        for name in list(build_env):
            if name.upper() in ('PVSNESLIB_HOME', 'PYTHONHOME', 'PYTHONPATH',
                                'PYTHONUSERBASE', 'VIRTUAL_ENV', 'CONDA_PREFIX'):
                removed.append(name)
                del build_env[name]
        # Pin the only SDK override honored by build.py to this fresh export.
        sdk = cache / 'sdk/pvsneslib'
        build_env['PVSNESLIB_HOME'] = str(sdk)
        build_env['PYTHONNOUSERSITE'] = '1'
        result['build_environment'] = {
            'removed_overrides': sorted(removed),
            'selected_sdk': str(sdk.relative_to(source)).replace('\\', '/'),
            'python_user_site_disabled': True,
        }
        with log.open('w', encoding='utf-8') as output:
            build = subprocess.run(['cmd', '/d', '/c', r'call .\Build.cmd --assets'],
                                   cwd=source, stdin=subprocess.DEVNULL,
                                   stdout=output, stderr=subprocess.STDOUT,
                                   env=build_env)
        result['build_exit_code'] = build.returncode
        result['build_log'] = str(log.relative_to(ROOT)).replace('\\', '/')
        if build.returncode:
            raise AssertionError(('fresh build failed', log.read_text()[-4000:]))
        sdk_digest = hashlib.sha256()
        sdk_files = 0
        for path in sorted(sdk.rglob('*')):
            if path.is_file():
                sdk_digest.update(path.relative_to(sdk).as_posix().encode('utf-8'))
                sdk_digest.update(b'\0')
                sdk_digest.update(path.read_bytes())
                sdk_files += 1
        if not sdk_files:
            raise AssertionError('fresh SDK directory is empty')
        result['build_environment']['sdk_files'] = sdk_files
        result['build_environment']['sdk_tree_sha256'] = sdk_digest.hexdigest()

        result['bootstrap_archives'] = []
        for url, name, digest in pins:
            actual = sha((cache / name).read_bytes())
            if actual.upper() != digest:
                raise AssertionError(('fresh bootstrap archive pin mismatch', name))
            result['bootstrap_archives'].append({'name': name, 'url': url, 'sha256': actual})
        python = cache / 'python/python.exe'
        result['python_environment'] = json.loads(command([
            str(python), '-c',
            'import json,platform,PIL;print(json.dumps(dict(python=platform.python_version(),pillow=PIL.__version__)))',
        ], cwd=source, env=build_env))
        rebuilt = (source / 'dist' / expected['rom']).read_bytes()
        rebuilt_manifest = json.loads((source / 'dist/manifest.json').read_text())
        result['rebuilt_rom_sha256'] = sha(rebuilt)
        if rebuilt != original_rom or rebuilt_manifest != expected:
            raise AssertionError(('fresh cartridge differs', result['rebuilt_rom_sha256'], expected['sha256']))

        compared = []
        for name, before in generated_before.items():
            after = (source / name).read_bytes()
            text = Path(name).suffix in ('.asm', '.h', '.json')
            left = before.replace(b'\r\n', b'\n') if text else before
            right = after.replace(b'\r\n', b'\n') if text else after
            if left != right:
                raise AssertionError(('fresh generated asset differs', name))
            compared.append({'file': name, 'sha256': sha(right),
                             'comparison': 'LF-normalized text' if text else 'exact bytes'})
        result['generated_assets'] = compared
        result['generated_assets_verified'] = len(compared)
        result['symbols_equal_after_source_path_normalization'] = (
            canonical_symbols(original_symbols) ==
            canonical_symbols((source / 'dist/abaqus-after-hours.sym').read_bytes()))
        if not result['symbols_equal_after_source_path_normalization']:
            raise AssertionError('linker symbol layout differs beyond source paths')
        result['status'] = 'passed'
    except Exception as error:
        result['error'] = repr(error)
        raise
    finally:
        result['elapsed_seconds'] = round(time.monotonic() - started, 3)
        REPORT.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in
                      ('status', 'source_commit', 'rom_sha256',
                       'generated_assets_verified', 'elapsed_seconds')}))


if __name__ == '__main__':
    main()
