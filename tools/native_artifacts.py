"""Validate and publish the cartridge/symbol/manifest trio with recovery.

The caller holds native-build.lock. The cartridge is replaced last, as one
already-validated file. A journal restores prior metadata after interruption,
or recognizes a complete new trio. Other files in dist remain untouched.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import uuid

NAMES = ('abaqus-after-hours.sym', 'manifest.json', 'abaqus-after-hours.sfc')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def locations(root):
    root = Path(root).resolve()
    build, dist = root / 'build', root / 'dist'
    build.mkdir(exist_ok=True)
    dist.mkdir(exist_ok=True)
    if build.resolve() != build or dist.resolve() != dist:
        raise ValueError('native build outputs must stay in ordinary workspace directories')
    for name in NAMES:
        if (dist / name).resolve() != dist / name:
            raise ValueError('native artifact cannot be a redirected file: ' + name)
    return root, build, dist


def private_path(root, path, prefix):
    _, build, _ = locations(root)
    path = Path(path).absolute()
    if path.parent != build or not path.name.startswith(prefix) or path.resolve() != path:
        raise ValueError('native candidate/backup leaves its reserved build directory')
    return path


def begin(root):
    _, build, _ = locations(root)
    return Path(tempfile.mkdtemp(prefix='native-stage-', dir=build)).resolve()


def validate(root, stage):
    stage = private_path(root, stage, 'native-stage-')
    if any(not (stage / n).is_file() or (stage / n).is_symlink() for n in NAMES):
        raise ValueError('native candidate lacks the cartridge, symbols or manifest')
    raw = (stage / NAMES[2]).read_bytes()
    if len(raw) != 4194304 or raw[0x7fd5] != 0x30 or raw[0x7fd7] != 0x0c or raw[0x7fd9] != 1:
        raise ValueError('native candidate must be a 4 MiB NTSC FastROM LoROM')
    checksum = int.from_bytes(raw[0x7fde:0x7fe0], 'little')
    complement = int.from_bytes(raw[0x7fdc:0x7fde], 'little')
    if checksum != (sum(raw) & 65535) or (checksum ^ complement) != 65535:
        raise ValueError('native candidate checksum differs')
    manifest = json.loads((stage / 'manifest.json').read_bytes())
    version = manifest.get('version') if isinstance(manifest, dict) else None
    if not isinstance(version, str) or not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('native candidate has no numeric manifest version')
    if (manifest.get('rom') != NAMES[2] or manifest.get('bytes') != len(raw) or
            manifest.get('sha256') != sha(raw) or manifest.get('checksum') != f'{checksum:04X}' or
            manifest.get('mapping') != '4 MiB FastROM LoROM' or manifest.get('region') != 'NTSC 60 Hz'):
        raise ValueError('native candidate manifest differs from the cartridge')
    symbols = (stage / NAMES[0]).read_text()
    if 'no$snes symbolic information' not in symbols or not re.search(r'(?m)^[0-9a-fA-F]{8} \S+$', symbols):
        raise ValueError('native candidate has no linked symbol table')
    return {name: sha((stage / name).read_bytes()) for name in NAMES}


def journal_path(root):
    _, build, _ = locations(root)
    path = build / 'native-publication.json'
    if path.resolve() != path:
        raise ValueError('native journal must stay in the workspace')
    return path


def atomic_write(path, raw, build):
    temporary = build / ('native-write-' + uuid.uuid4().hex + '.tmp')
    with temporary.open('xb') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def restore(root, record):
    _, build, dist = locations(root)
    backup = private_path(root, root / record['backup'], 'native-prior-')
    previous = record['previous']
    if not isinstance(previous, dict) or not set(previous) <= set(NAMES):
        raise ValueError('invalid prior native artifact inventory')
    # Validate every backup before changing any current artifact.
    for name, digest in previous.items():
        if sha((backup / name).read_bytes()) != digest:
            raise ValueError('native artifact recovery backup differs: ' + name)
    for name in NAMES:
        target = dist / name
        if name in previous:
            if target.is_file() and sha(target.read_bytes()) == previous[name]:
                continue
            atomic_write(target, (backup / name).read_bytes(), build)
        else:
            target.unlink(missing_ok=True)


def recover(root):
    root, _, dist = locations(root)
    journal = journal_path(root)
    if not journal.exists():
        return
    record = json.loads(journal.read_bytes())
    expected = record['new']
    if not isinstance(expected, dict) or set(expected) != set(NAMES):
        raise ValueError('invalid interrupted native artifact inventory')
    complete = all((dist / n).is_file() and sha((dist / n).read_bytes()) == h for n, h in expected.items())
    if not complete:
        restore(root, record)
    journal.unlink()


def publish(root, stage):
    root, build, dist = locations(root)
    stage = private_path(root, stage, 'native-stage-')
    expected = validate(root, stage)
    recover(root)
    if all((dist / n).is_file() and sha((dist / n).read_bytes()) == h for n, h in expected.items()):
        return None
    backup = private_path(root, build / ('native-prior-' + uuid.uuid4().hex), 'native-prior-')
    backup.mkdir()
    prior = {}
    for name in NAMES:
        target = dist / name
        if target.is_file():
            raw = target.read_bytes()
            (backup / name).write_bytes(raw)
            prior[name] = sha(raw)
    record = {'backup': backup.relative_to(root).as_posix(), 'previous': prior, 'new': expected}
    journal = journal_path(root)
    atomic_write(journal, (json.dumps(record) + '\n').encode(), build)
    try:
        for name in NAMES:
            os.replace(stage / name, dist / name)
    except BaseException:
        restore(root, record)
        journal.unlink()
        raise
    journal.unlink()
    return backup.relative_to(root).as_posix()
