"""Run and bind the canonical six native suites to the frozen source inventory."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emulator import ROOT
from play_flow_media import inventory as media_inventory
from candidate_sources import snapshot
from collate_pacing_floor_25 import SIX, count
from collate_combat_24 import failure_arrays
from release_evidence import EXPECTED_NATIVE_CORE
from test_champion import host_contract
from test_stage_pipeline_26 import host_guards

CHECKS = []


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok, label, details=None):
    CHECKS.append({'check': label, 'passed': bool(ok), 'details': details})
    if not ok:
        raise RuntimeError((label, details))


def main():
    started = time.monotonic()
    sources = snapshot(ROOT)
    manifest = json.loads((ROOT / 'dist/manifest.json').read_bytes())
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    artifacts = {n: sha(ROOT / 'dist' / n) for n in ('abaqus-after-hours.sfc', 'abaqus-after-hours.sym', 'manifest.json')}
    report = {'status': 'failed', 'version': manifest['version'], 'rom_sha256': manifest['sha256'],
              'source_commit': commit, 'source_sha256': sources, 'checks': CHECKS,
              'host_contract': host_contract(), 'native_execution': True, 'controller_only': True,
              'memory_writes': False, 'save_states': False, 'suite_reports': {}}
    try:
        require(manifest['version'] == '0.26.0' and artifacts['abaqus-after-hours.sfc'] == manifest['sha256'], 'suite runner loads the exact current cartridge')
        core = ROOT / '.tools/core/snes9x_libretro.dll'
        require(sha(core).lower() == EXPECTED_NATIVE_CORE['dll_sha256'].lower(), 'suite runner hashes the actual pinned expanded native core')
        report['core_sha256'] = sha(core)
        report['source_guard_runs'] = host_guards('test_candidate_sources.py')
        report['media_guard_runs'] = host_guards('test_play_flow_media.py')
        report['collation_guard_runs'] = host_guards('test_play_flow_collation.py')
        environment = dict(os.environ, ABAQUS_HEADLESS='1')
        run = subprocess.run(['cmd', '/d', '/c', str(ROOT / 'Test.cmd')], cwd=ROOT,
                             stdin=subprocess.DEVNULL, capture_output=True, env=environment,
                             creationflags=0x08000000 if os.name == 'nt' else 0)
        log = ROOT / 'build/v026-canonical-native-suites.log'
        log.write_bytes(run.stdout + run.stderr)
        report['command'] = ['cmd', '/d', '/c', 'Test.cmd']
        report['exit_code'] = run.returncode
        report['retained_log'] = log.relative_to(ROOT).as_posix()
        report['retained_log_sha256'] = sha(log)
        require(run.returncode == 0, 'all six canonical native programs exit successfully', run.returncode)
        for name in SIX:
            path = ROOT / 'docs' / name
            data = json.loads(path.read_bytes())
            require(data.get('status', 'passed' if name == 'test-report.json' else None) == 'passed' and data.get('rom_sha256') == manifest['sha256'],
                    'native suite is passed and bound to this cartridge', name)
            failure_arrays(data, name)
            report['suite_reports'][name] = {'sha256': sha(path), 'checks': count(data)}
        require(snapshot(ROOT) == sources, 'all native suite source/command inputs remain fixed')
        require(artifacts == {n: sha(ROOT / 'dist' / n) for n in artifacts}, 'cartridge symbols and manifest stay fixed through every suite')
        require(sha(core) == report['core_sha256'], 'expanded native core stays fixed during all suites')
        require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == commit, 'suite source commit remains the frozen execution commit')
        report['native_six_suite_checks'] = sum(row['checks'] for row in report['suite_reports'].values())
        report['captures'] = media_inventory(ROOT, 'native-suite')
        report['status'] = 'passed'
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        report['check_count'] = len(CHECKS)
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
        (ROOT / 'docs/play-flow-v026-native-suite-report.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
        print(json.dumps({k: report[k] for k in ('status', 'check_count', 'elapsed_seconds')}), flush=True)


if __name__ == '__main__':
    main()
