"""Publish a completed generated asset directory with rollback and recovery.

Encoding uses a private build directory. A short OS lock serializes directory
publication; no lock is held during the expensive encoder. The journal lets
the next build recover the previous complete directory after an interrupted
two-rename publication. Prior outputs and failed candidates remain under build.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import tempfile
import uuid


def locations(root):
    root = Path(root).resolve()
    build = root / 'build'
    build.mkdir(exist_ok=True)
    target = root / 'assets/generated'
    if build.resolve() != build or target.resolve() != target:
        raise ValueError('asset publication requires ordinary workspace directories')
    if target.exists() and not target.is_dir():
        raise ValueError('generated assets must be a directory')
    return root, build, target


def candidate_path(root, path, prefix):
    root, build, target = locations(root)
    path = Path(path).absolute()
    if path.parent != build or not path.name.startswith(prefix) or path.resolve() != path:
        raise ValueError('asset publication path is outside its reserved workspace directory')
    return path


@contextmanager
def workspace_lock(root, name):
    root, build, _ = locations(root)
    if name not in ('asset-publication.lock', 'native-build.lock'):
        raise ValueError('unknown workspace build lock')
    path = build / name
    if path.resolve() != path:
        raise ValueError('asset publication lock must stay in the workspace')
    with path.open('a+b') as handle:
        if not handle.tell():
            handle.write(b'\0')
            handle.flush()
        handle.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def publication_lock(root):
    return workspace_lock(root, 'asset-publication.lock')


def journal_path(root):
    _, build, _ = locations(root)
    path = build / 'asset-publication.json'
    if path.resolve() != path:
        raise ValueError('asset publication journal must stay in the workspace')
    return path


def recover(root):
    """Caller holds the short publication lock."""
    root, _, target = locations(root)
    journal = journal_path(root)
    if not journal.exists():
        return
    data = json.loads(journal.read_bytes())
    stage = candidate_path(root, root / data['stage'], 'assets-stage-')
    backup = candidate_path(root, root / data['backup'], 'assets-prior-')
    if not target.exists() and backup.is_dir():
        os.replace(backup, target)
    elif not target.exists() and stage.is_dir():
        validate_stage(root, stage)
        os.replace(stage, target)
    if not target.is_dir():
        raise RuntimeError('asset publication journal has no complete directory to recover')
    journal.unlink()


def ensure_complete(root):
    with publication_lock(root):
        recover(root)


def begin(root):
    root, build, _ = locations(root)
    ensure_complete(root)
    return Path(tempfile.mkdtemp(prefix='assets-stage-', dir=build)).resolve()


def validate_stage(root, stage):
    stage = candidate_path(root, stage, 'assets-stage-')
    if not stage.is_dir():
        raise ValueError('asset candidate directory is missing')
    files = list(stage.iterdir())
    if any(not p.is_file() or p.is_symlink() or not p.stat().st_size for p in files):
        raise ValueError('asset candidate contains an empty or unsupported output')
    for name in ('data.asm', 'assets.h', 'soundbank.asm', 'soundbank.h', 'soundbank.bnk', 'stage-depth.json'):
        if not (stage / name).is_file():
            raise ValueError('asset candidate is incomplete: ' + name)
    for script in ('data.asm', 'soundbank.asm'):
        references = re.findall(r'(?m)^\s*\.incbin\s+"([^"]+)"', (stage / script).read_text())
        if not references:
            raise ValueError('asset candidate has no linked binary references: ' + script)
        for reference in references:
            path = Path(reference)
            if path.parts[:2] != ('assets', 'generated') or len(path.parts) != 3 or not (stage / path.name).is_file():
                raise ValueError('asset candidate has an invalid binary reference: ' + reference)
    return len(files)


def publish(root, stage):
    root, build, target = locations(root)
    stage = candidate_path(root, stage, 'assets-stage-')
    total = validate_stage(root, stage)
    backup = candidate_path(root, build / ('assets-prior-' + uuid.uuid4().hex), 'assets-prior-')
    with publication_lock(root):
        recover(root)
        journal = journal_path(root)
        temporary = build / ('asset-journal-' + uuid.uuid4().hex + '.tmp')
        data = {'stage': stage.relative_to(root).as_posix(), 'backup': backup.relative_to(root).as_posix()}
        with temporary.open('xb') as handle:
            handle.write((json.dumps(data) + '\n').encode())
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, journal)
        had_target = target.exists()
        try:
            if had_target:
                os.replace(target, backup)
            os.replace(stage, target)
        except BaseException:
            if not target.exists() and backup.is_dir():
                os.replace(backup, target)
            if target.exists() or not had_target:
                journal.unlink(missing_ok=True)
            raise
        journal.unlink()
    return {'files': total, 'previous_outputs': backup.relative_to(root).as_posix() if had_target else None}
