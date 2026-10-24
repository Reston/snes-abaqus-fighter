"""Content-based asset reuse; fresh exports always regenerate from source.

This is a local performance cache, not release evidence. Its source graph is
discovered without importing encoders; C/gameplay edits do not re-encode art.
Every cache hit also hashes the published generated files.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid
from PIL import __version__ as pillow_version
from asset_transaction import locations

TEXT = {'.py', '.json', '.asm', '.h', '.c', '.ps1', '.md', '.txt', '.csv', '.svg'}
TOOL = '.tools/sdk/pvsneslib/devkitsnes/tools/smconv.exe'


def digest(path):
    raw = Path(path).read_bytes()
    if Path(path).suffix.lower() in TEXT:
        raw = raw.replace(b'\r\n', b'\n')
    return hashlib.sha256(raw).hexdigest()


def encoder_dependencies(root):
    root = Path(root).resolve()
    pending, found = [root / 'tools/make_assets.py'], set()
    while pending:
        path = pending.pop()
        if path in found:
            continue
        if path.resolve() != path or not path.is_file():
            raise ValueError('asset encoder dependency is missing or outside the ordinary source tree: ' + str(path))
        found.add(path)
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        for node in ast.walk(tree):
            names = [n.name for n in node.names] if isinstance(node, ast.Import) else (
                [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            for name in names:
                parts = name.split('.')
                if parts[0] == 'tools':
                    parts = parts[1:]
                if parts:
                    candidate = root / 'tools' / (parts[0] + '.py')
                    if candidate.is_file():
                        pending.append(candidate)
    return found


def inputs(root):
    root = Path(root).resolve()
    paths = encoder_dependencies(root)
    paths.update((root / 'tools').glob('*.ps1'))
    for path in (root / 'assets').rglob('*'):
        if path.relative_to(root / 'assets').parts[0].lower() == 'generated':
            continue
        if path.is_dir():
            if path.resolve() != path:
                raise ValueError('authored asset directories must stay in the ordinary source tree')
            continue
        if not path.is_file():
            continue
        if not path.resolve().is_relative_to(root):
            raise ValueError('asset source leaves the workspace: ' + str(path))
        paths.add(path)
    files = {p.relative_to(root).as_posix(): digest(p) for p in sorted(paths)}
    files[TOOL] = digest(root / TOOL)
    return {'files': files, 'python': list(sys.version_info[:3]), 'pillow': pillow_version, 'platform': os.name}


def outputs(root, directory=None):
    root, build, target = locations(root)
    directory = Path(directory) if directory is not None else target
    if directory.resolve() != directory or not (directory == target or
            directory.parent == build and directory.name.startswith('assets-stage-')):
        raise ValueError('asset cache output directory is outside the publication workspace')
    result = {}
    for path in sorted(directory.iterdir()):
        if path.is_file():
            if path.resolve() != path:
                raise ValueError('generated asset cache cannot follow redirected files')
            result['assets/generated/' + path.name] = digest(path)
    return result


def status(root):
    root, build, _ = locations(root)
    path = build / 'asset-cache-v1.json'
    if path.resolve() != path:
        raise ValueError('asset cache must stay in the workspace')
    try:
        cached = json.loads(path.read_bytes())
    except (OSError, ValueError):
        return False, 'no complete local asset cache'
    if not isinstance(cached, dict) or cached.get('schema') != 1:
        return False, 'asset cache schema differs'
    try:
        actual_inputs = inputs(root)
    except OSError:
        return False, 'art or encoder inputs are missing'
    if cached.get('inputs') != actual_inputs:
        return False, 'art or encoder inputs changed'
    try:
        actual_outputs = outputs(root)
    except OSError:
        return False, 'generated outputs are missing'
    if cached.get('outputs') != actual_outputs:
        return False, 'generated outputs changed'
    return True, 'inputs and outputs match'


def save(root, source_inputs, generated_outputs):
    """Save the exact source/output pair captured before publication.

    A competing publisher can only make this stamp miss on the next build;
    it cannot accidentally label another directory's bytes as these inputs.
    """
    _, build, _ = locations(root)
    path = build / 'asset-cache-v1.json'
    if path.resolve() != path:
        raise ValueError('asset cache must stay in the workspace')
    temporary = build / ('asset-cache-' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('xb') as handle:
            handle.write((json.dumps({'schema': 1, 'inputs': source_inputs, 'outputs': generated_outputs}, sort_keys=True) + '\n').encode())
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        return False
    return True
