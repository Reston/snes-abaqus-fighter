"""Reject false preservation claims, including under python -O."""
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import package
import preservation


def rejected(action, label):
    try:
        action()
    except (package.PackageError, ValueError):
        return
    raise RuntimeError('Accepted invalid preservation evidence: '+label)


def main():
    manifest = json.loads((ROOT/'dist/manifest.json').read_bytes())
    report = json.loads((ROOT/'docs/champion-preservation-report.json').read_bytes())
    freeze = json.loads((ROOT/'docs/fresh-build-test-report.json').read_bytes())['source_commit']
    validate = lambda data: package.validate_preservation(data, ROOT, manifest, freeze)
    validate(report)
    for malformed in (None, [], 'invalid', 0):
        rejected(lambda: validate(malformed), 'non-object report')
    mutations = []
    for field, value in [('baseline_commit', '0'*40), ('baseline_commit', freeze),
                         ('baseline_version', '0.0.0'),
                         ('allowed_changed', [] if report['allowed_changed'] else ['unapproved.bin']),
                         ('allowed_added', [] if report['allowed_added'] else ['unapproved.bin']),
                         ('source_freeze', report['baseline_commit'])]:
        mutations.append((dict(report, **{field:value}), field))
    for field, value in [('source_blob_sha256', '0'*64), ('sha256', '0'*64),
                         ('comparison', 'exact bytes')]:
        altered = copy.deepcopy(report)
        row = next(row for row in altered['files'] if row['path'].endswith('/soundbank.asm'))
        row[field] = value
        mutations.append((altered, field))
    if report['allowed_changed']:
        altered = copy.deepcopy(report)
        for row in altered['files']:
            if row['path'] in altered['allowed_changed']:
                row['preserved'] = True
        altered.update(existing_assets_preserved=report['existing_assets_preserved']+len(report['allowed_changed']),
                       generated_assets_modified=0, allowed_changed=[])
        mutations.append((altered, 'known changes falsely marked preserved with matching counts'))
    altered = copy.deepcopy(report)
    altered['files'][0]['preserved'] = False
    altered['existing_assets_preserved'] -= 1
    altered['generated_assets_modified'] += 1
    altered['allowed_changed'].append(altered['files'][0]['path'])
    mutations.append((altered, 'report authorizes its own extra difference'))
    for altered, label in mutations:
        rejected(lambda: validate(altered), label)
    policy = preservation.POLICIES[manifest['version']]
    rejected(lambda: preservation.build_report(ROOT, freeze, freeze, [], []), 'same-commit baseline')
    rejected(lambda: preservation.build_report(ROOT, freeze, policy['baseline_commit'], [], []),
             'baseline is not an ancestor of source freeze')
    original = policy['baseline_version']
    try:
        policy['baseline_version'] = 'invalid'
        rejected(lambda: validate(report), 'baseline manifest must match approved version')
    finally:
        policy['baseline_version'] = original
    if (preservation.normalize('asset.asm', b'a\r\nb') != b'a\nb' or
            preservation.normalize('asset.bin', b'a\r\nb') != b'a\r\nb'):
        raise RuntimeError('Text/binary comparison contract changed')
    print('Preservation baseline, manifest, ancestry and mutation checks passed ('+str(len(mutations))+')')


if __name__ == '__main__':
    main()
