"""Retain controller-captured baseline/current recoil clips for human review."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    current = json.loads((ROOT/'dist/manifest.json').read_bytes())
    baseline = sha(subprocess.check_output(
        ['git', 'show', 'f75005d:dist/abaqus-after-hours.sfc'], cwd=ROOT))
    result = {'status': 'passed', 'version': current['version'],
              'rom_sha256': current['sha256'], 'baseline_rom_sha256': baseline,
              'scope': 'Limited native recoil review clips; full-roster proof is separate',
              'producer': 'tools/copy_combat_24_pacing_samples.py',
              'producer_sha256': sha(Path(__file__).read_bytes().replace(b'\r\n', b'\n')),
              'samples': {}}
    destination = ROOT/'docs/screenshots/combat-24-pacing'
    destination.mkdir(parents=True, exist_ok=True)
    for label, expected in (('before', baseline), ('after', current['sha256'])):
        report_path = ROOT/f'build/v024-recoil-{label}.json'
        report = json.loads(report_path.read_bytes())
        if (report['status'] != 'diagnostic_passed' or report['rom_sha256'] != expected or
                report['rom_sha256_after'] != expected or report['changed_harness_inputs'] or
                report['host_contract']['gui_opened'] or report['host_contract']['audio_device_opened']):
            raise ValueError('Invalid or unstable native sample: ' + label)
        expected_names = {f'damian-{label}-{kind}.gif' for kind in ('light', 'strong', 'guard')}
        if {Path(row['path']).name for row in report['captures']} != expected_names:
            raise ValueError('Incomplete recoil sample inventory: ' + label)
        captures = []
        for row in report['captures']:
            source = (ROOT/row['path']).resolve()
            if not source.is_relative_to((ROOT/'build').resolve()) or sha(source.read_bytes()) != row['sha256']:
                raise ValueError('Sample bytes or source path differ: ' + row['path'])
            target = destination/source.name
            shutil.copyfile(source, target)
            captures.append({'path': target.relative_to(ROOT).as_posix(),
                             'sha256': sha(target.read_bytes()),
                             'evidence_scope': 'historical approved baseline' if label == 'before' else 'current ROM'})
        result['samples'][label] = {
            'rom_sha256': expected, 'source_commit': report['source_commit'],
            'command': report['command'], 'host_contract': report['host_contract'],
            'source_sha256': report['source_sha256'], 'harness_sha256': report['harness_sha256'],
            'source_only_report': report_path.relative_to(ROOT).as_posix(),
            'original_report_sha256': sha(report_path.read_bytes()),
            'measurements': report['damian'], 'captures': captures}
    (ROOT/'docs/combat-24-pacing-samples.json').write_bytes((json.dumps(result, indent=2)+'\n').encode())
    print(json.dumps({'status': 'passed', 'rom_sha256': current['sha256'], 'native_clips': 6}))


if __name__ == '__main__':
    main()
