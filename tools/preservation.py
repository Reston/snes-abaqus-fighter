"""Recompute generated-asset preservation from committed Git objects."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

PROTECTED = {'src/hardware.asm', 'src/trace.asm'}
TEXT_TYPES = {'.asm', '.h', '.json'}
# Policy is separate from the report: it cannot authorize its own differences.
POLICIES = {
    '0.16.0': {
        'baseline_commit': 'e9d4313af3fff74ca9857f8a6fb0d704464fac8f',
        'baseline_version': '0.15.0',
        'baseline_rom_sha256': '2c447156b7c1f12d94e1c76dde3423928ad026933076c952806abda7d6281d44',
        'allowed_changed': [],
        'allowed_added': [],
    },
    '0.15.0': {
        'baseline_commit': '2f2df2909ee7cf100b5dc4c8ef0f5aefb46a9891',
        'baseline_version': '0.14.0',
        'baseline_rom_sha256': '3de317b43f72bea76cfc2f1a1ebd5c67dd57913b8d9fddfb50a7a846a02ddeaa',
        'allowed_changed': [],
        'allowed_added': [],
    },
    '0.14.0': {
        'baseline_commit': '54173e352b7195daf634dce63112a280d0fd94cf',
        'baseline_version': '0.13.0',
        'baseline_rom_sha256': 'eefa712718d52aa536258773596e78cee3f4cfc83b1cd4144e3de1110d2273b4',
        'allowed_changed': [],
        'allowed_added': [],
    },
    '0.13.0': {
        'baseline_commit': 'ff62dcd3bb7b34c49fbfbfc402f0d8ce96347cb1',
        'baseline_version': '0.12.0',
        'baseline_rom_sha256': '33502fba12bf2cf02e6244174449c678ad1dd704afc754e7819f815489c6fa83',
        'allowed_changed': ['assets/generated/soundbank.asm', 'assets/generated/soundbank.bnk'],
        'allowed_added': ['assets/generated/music4.it'],
    },
}


def git(root: Path, *args: str) -> bytes:
    result = subprocess.run(['git', *args], cwd=root, stdin=subprocess.DEVNULL,
                            capture_output=True)
    if result.returncode:
        raise ValueError(('Cannot resolve preservation Git input', args,
                          result.stderr.decode(errors='replace')[-1000:]))
    return result.stdout


def resolve(root: Path, ref: str) -> str:
    return git(root, 'rev-parse', '--verify', '--end-of-options', ref+'^{commit}').decode().strip()


def normalize(path: str, value: bytes) -> bytes:
    return value.replace(b'\r\n', b'\n') if Path(path).suffix in TEXT_TYPES else value


def committed_files(root: Path, commit: str) -> dict[str, bytes]:
    archive = git(root, 'archive', '--format=tar', commit, 'assets/generated', *sorted(PROTECTED))
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        return {member.name: source.extractfile(member).read()
                for member in source if member.isfile()}


def build_report(root: Path, baseline_ref: str, source_ref: str,
                 allowed_changed: list[str], allowed_added: list[str]) -> dict:
    baseline, freeze = resolve(root, baseline_ref), resolve(root, source_ref)
    if baseline == freeze:
        raise ValueError('Preservation baseline must precede the source freeze')
    git(root, 'merge-base', '--is-ancestor', baseline, freeze)
    manifest = json.loads((root/'dist/manifest.json').read_bytes())
    committed = json.loads(git(root, 'show', freeze+':dist/manifest.json'))
    if committed != manifest:
        raise ValueError('Preservation source freeze must contain the current manifest')
    prior = json.loads(git(root, 'show', baseline+':dist/manifest.json'))
    before, frozen = committed_files(root, baseline), committed_files(root, freeze)
    if set(before) - set(frozen):
        raise ValueError(('Preservation baseline files were removed', sorted(set(before)-set(frozen))))
    current = {}
    for name, data in frozen.items():
        raw = (root/name).read_bytes()
        if normalize(name, raw) != normalize(name, data):
            raise ValueError(('Current preservation input differs from source freeze', name))
        current[name] = raw
    records, changed = [], set()
    for name, old in sorted(before.items()):
        same = normalize(name, old) == normalize(name, current[name])
        if not same:
            changed.add(name)
        records.append({'path': name, 'sha256': hashlib.sha256(current[name]).hexdigest(),
                        'source_blob_sha256': hashlib.sha256(old).hexdigest(),
                        'comparison': 'LF-normalized text' if Path(name).suffix in TEXT_TYPES else 'exact bytes',
                        'preserved': same})
    added = [{'path': name, 'sha256': hashlib.sha256(current[name]).hexdigest()}
             for name in sorted(set(frozen)-set(before))]
    if changed & PROTECTED:
        raise ValueError(('Protected hardware/trace assembly changed', sorted(changed & PROTECTED)))
    if (len(allowed_changed) != len(set(allowed_changed)) or
            len(allowed_added) != len(set(allowed_added)) or
            changed != set(allowed_changed) or {row['path'] for row in added} != set(allowed_added)):
        raise ValueError(('Asset differences do not match approved changes', sorted(changed), added))
    generated = [row for row in records if row['path'].startswith('assets/generated/')]
    return {'version': manifest['version'], 'rom_sha256': manifest['sha256'], 'status': 'passed',
            'baseline_commit': baseline, 'baseline_version': prior['version'], 'source_freeze': freeze,
            'generated_assets_total': len([name for name in frozen if name.startswith('assets/generated/')]),
            'existing_assets_preserved': sum(row['preserved'] for row in generated),
            'generated_assets_modified': len(changed), 'generated_assets_added': len(added),
            'native_assembly_preserved': len(PROTECTED),
            'scope': 'Generated assets and protected hardware/trace ASM; binary bytes exact, text LF-normalized.',
            'allowed_changed': sorted(changed), 'allowed_added': sorted(allowed_added),
            'files': records, 'added': added}


def validate_report(root: Path, report: dict, manifest: dict, source_freeze: str) -> None:
    policy = POLICIES.get(manifest['version'])
    if policy is None:
        raise ValueError('No approved preservation baseline for candidate '+manifest['version'])
    prior = json.loads(git(root, 'show', policy['baseline_commit']+':dist/manifest.json'))
    if (prior.get('version') != policy['baseline_version'] or
            prior.get('sha256') != policy['baseline_rom_sha256']):
        raise ValueError('Approved preservation baseline manifest identity differs')
    expected = build_report(root, policy['baseline_commit'], source_freeze,
                            policy['allowed_changed'], policy['allowed_added'])
    if report != expected:
        raise ValueError('Preservation report differs from recomputed committed baseline evidence')
