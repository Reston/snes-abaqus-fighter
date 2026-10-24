"""Canonical source inventory shared by native candidate evidence producers."""
import hashlib
from pathlib import Path

SUFFIXES = {'.py', '.ps1', '.c', '.h', '.asm'}
COMMANDS = ('Build.cmd', 'Test.cmd', 'Play.cmd')


def snapshot(root):
    root = Path(root).resolve()
    paths = []
    for folder in ('src', 'tools'):
        directory = root / folder
        if not directory.is_dir():
            raise ValueError('candidate source directory is missing: ' + folder)
        paths.extend(p for p in directory.rglob('*') if p.is_file() and p.suffix.lower() in SUFFIXES)
    for name in COMMANDS:
        path = root / name
        if not path.is_file():
            raise ValueError('candidate command is missing: ' + name)
        paths.append(path)
    result = {}
    for path in sorted(paths):
        if not path.resolve().is_relative_to(root):
            raise ValueError('candidate source leaves the workspace: ' + str(path))
        raw = path.read_bytes().replace(b'\r\n', b'\n')
        result[path.relative_to(root).as_posix()] = hashlib.sha256(raw).hexdigest()
    return result
