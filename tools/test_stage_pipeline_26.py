"""Host-only one-pass stage generation and exact-cartridge reproduction proof."""
import ast
import hashlib
import json
from pathlib import Path
import runpy
import re
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emulator import ROOT
from test_play_flow_26 import source_hashes
from v025_contracts import canonical
import stage_depth_assets as stages
import menu_assets

CHECKS = []


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(ok, label, details=None):
    CHECKS.append({'check': label, 'passed': bool(ok), 'details': details})
    if not ok:
        raise RuntimeError((label, details))


def inventory():
    return {p.relative_to(ROOT).as_posix(): sha(canonical(p.name, p.read_bytes()))
            for p in sorted((ROOT / 'assets/generated').iterdir()) if p.is_file() and p.name != 'soundbank.h'}


def host_guards(filename):
    source = ROOT / 'tools' / filename
    parsed = ast.parse(source.read_text())
    expected = sum(isinstance(n, ast.FunctionDef) and n.name.startswith('test_')
                   for cls in parsed.body if isinstance(cls, ast.ClassDef) for n in cls.body)
    runs = []
    for optimized in (False, True):
        command = [sys.executable] + (['-O'] if optimized else []) + [str(source)]
        run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        output = run.stdout + run.stderr
        count = re.search(r'Ran (\d+) tests?', output)
        total = int(count[1]) if count else 0
        require(expected > 0 and run.returncode == 0 and total == expected and output.rstrip().endswith('OK'),
                filename + ' guards pass in the requested interpreter mode', [optimized, total, run.returncode, output[-500:]])
        runs.append({'optimized': optimized, 'tests': total, 'exit_code': run.returncode, 'output': output})
    return runs


def main():
    started = time.monotonic()
    sources = source_hashes()
    manifest = json.loads((ROOT / 'dist/manifest.json').read_bytes())
    original = stages.build_stage
    calls = []
    before = inventory()
    report = {'status': 'failed', 'version': manifest['version'], 'rom_sha256': manifest['sha256'],
              'source_sha256': sources, 'host_only': True, 'native_execution': False,
              'memory_writes': False, 'save_states': False, 'checks': CHECKS,
              'stage_encoder_calls': calls, 'generated_files': before}

    def counted(root, record, palette):
        calls.append(record['id'])
        return original(root, record, palette)

    try:
        require(len(before) == 226, 'generation proof begins with the complete expected inventory')
        require(sha((ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()) == manifest['sha256'], 'before cartridge matches its manifest')
        menu_writer = menu_assets.make_menu_images

        def interrupted(*args, **kwargs):
            raise RuntimeError('injected mid-generation failure')

        menu_assets.make_menu_images = interrupted
        failed_as_expected = False
        try:
            runpy.run_path(str(ROOT / 'tools/make_assets.py'), run_name='__main__')
        except RuntimeError as error:
            failed_as_expected = str(error) == 'injected mid-generation failure'
        finally:
            menu_assets.make_menu_images = menu_writer
        require(failed_as_expected and inventory() == before, 'an interrupted real generation leaves the entire live asset set intact')
        report['generation_failure_preserved_live_assets'] = True
        stages.build_stage = counted
        try:
            context = runpy.run_path(str(ROOT / 'tools/make_assets.py'), run_name='__main__')
        finally:
            stages.build_stage = original
        require(calls == [0, 1, 2], 'the full asset pipeline encodes each current stage exactly once', calls)
        require(inventory() == before, 'all 226 generated outputs remain identical after one-pass regeneration')
        prepared = context['native_stage_data']
        record, palette = prepared['records'][0], prepared['ui_palette']
        mutations = ('workspace', 'palette', 'source', 'missing-stage')
        for name in mutations:
            changed = dict(prepared)
            if name == 'workspace':
                changed['root'] = ROOT / 'build/another-root'
            elif name == 'palette':
                changed['ui_palette'] = palette[:16]
            elif name == 'source':
                changed['records'] = prepared['records'][1:]
            else:
                changed['payloads'] = {k: v for k, v in prepared['payloads'].items() if k != 2}
            rejected = False
            try:
                stages.stage_payload(ROOT, record, palette, changed)
            except ValueError:
                rejected = True
            require(rejected, 'prepared snapshot rejects a mismatched ' + name)
        report['rejected_snapshot_mutations'] = list(mutations)
        built = subprocess.run([sys.executable, str(ROOT / 'tools/build.py')], cwd=ROOT,
                               capture_output=True, text=True, check=False)
        require(built.returncode == 0, 'canonical native build accepts the regenerated assets', built.stdout[-500:] + built.stderr[-500:])
        require(sha((ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()) == manifest['sha256'] and
                json.loads((ROOT / 'dist/manifest.json').read_bytes()) == manifest,
                'regenerated assets reproduce the exact cartridge and manifest')
        require(inventory() == before, 'native text canonicalization preserves the same complete output inventory')
        require(source_hashes() == sources, 'all generation and proof source inputs stay fixed')
        report['cartridge_reproduced'] = True
        require('Using unchanged generated assets: inputs and outputs match' in built.stdout,
                'ordinary native build reuses the newly verified assets without another encoder pass')
        report['ordinary_build_reused_assets'] = True
        report['publication_guard_runs'] = host_guards('test_asset_transaction.py')
        report['cache_guard_runs'] = host_guards('test_asset_cache.py')
        report['status'] = 'passed'
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        stages.build_stage = original
        report['check_count'] = len(CHECKS)
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
        (ROOT / 'docs/play-flow-v026-build-report.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
        print(json.dumps({k: report[k] for k in ('status', 'check_count', 'elapsed_seconds')}), flush=True)


if __name__ == '__main__':
    main()
