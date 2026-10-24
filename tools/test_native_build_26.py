"""Real staged native builds and host-only publication fault verification."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emulator import ROOT
from play_flow_media import inventory as media_inventory
from test_play_flow_26 import source_hashes
from test_stage_pipeline_26 import host_guards
import native_artifacts

CHECKS = []


def require(ok, label, details=None):
    CHECKS.append({'check': label, 'passed': bool(ok), 'details': details})
    if not ok:
        raise RuntimeError((label, details))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    started = time.monotonic()
    run = subprocess.run([sys.executable, str(ROOT / 'tools/build.py')], cwd=ROOT,
                         capture_output=True, text=True, check=False)
    require(run.returncode == 0, 'canonical staged native build succeeds', run.stdout[-1000:] + run.stderr[-500:])
    return {'elapsed_seconds': round(time.monotonic() - started, 3), 'exit_code': run.returncode,
            'output': run.stdout + run.stderr}


def main():
    started = time.monotonic()
    sources = source_hashes()
    manifest = json.loads((ROOT / 'dist/manifest.json').read_bytes())
    report = {'status': 'failed', 'version': manifest['version'], 'rom_sha256': manifest['sha256'],
              'source_sha256': sources, 'host_only': True, 'native_execution': False,
              'memory_writes': False, 'save_states': False, 'checks': CHECKS}
    try:
        require(sha(ROOT / 'dist/abaqus-after-hours.sfc') == manifest['sha256'], 'before cartridge matches its manifest')
        report['native_artifact_guard_runs'] = host_guards('test_native_artifacts.py')
        report['builds'] = [build()]
        require(sha(ROOT / 'dist/abaqus-after-hours.sfc') == manifest['sha256'] and
                json.loads((ROOT / 'dist/manifest.json').read_bytes()) == manifest,
                'staged publication retains the exact real cartridge and manifest')
        require(not native_artifacts.journal_path(ROOT).exists(), 'completed build leaves no pending native publication')
        first = {n: sha(ROOT / 'dist' / n) for n in native_artifacts.NAMES}
        stamps = {n: (ROOT / 'dist' / n).stat().st_mtime_ns for n in native_artifacts.NAMES}
        report['builds'].append(build())
        require('Using unchanged generated assets: inputs and outputs match' in report['builds'][1]['output'],
                'warm native build uses the unchanged asset fast path')
        require(first == {n: sha(ROOT / 'dist' / n) for n in native_artifacts.NAMES},
                'consecutive native builds reproduce all three published files byte-for-byte')
        require(stamps == {n: (ROOT / 'dist' / n).stat().st_mtime_ns for n in native_artifacts.NAMES},
                'identical native outputs do not replace the existing files')
        require(source_hashes() == sources, 'native build/proof inputs stay fixed throughout compilation')
        report['published_files'] = first
        report['cartridge_reproduced'] = True
        report['identical_outputs_not_replaced'] = True
        report['captures'] = media_inventory(ROOT, 'native-build')
        report['status'] = 'passed'
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        report['check_count'] = len(CHECKS)
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
        (ROOT / 'docs/play-flow-v026-native-build-report.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
        print(json.dumps({k: report[k] for k in ('status', 'check_count', 'elapsed_seconds')}), flush=True)


if __name__ == '__main__':
    main()
