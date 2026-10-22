"""Load reviewed stage masters and their original image-generation provenance."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image


def load_stage_sources(root: Path) -> list[dict]:
    directory = root / 'assets/art/stages'
    manifest_path = directory / 'stages.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if not (manifest['schema'] == 2):
        raise AssertionError('Unknown selected-stage schema')
    if not (manifest['style_contract']['native_canvas'] == [256, 224]):
        raise AssertionError()
    if not (manifest['style_contract']['master_canvas'] == [1024, 896]):
        raise AssertionError()
    records = manifest['stages']
    if not ([record['id'] for record in records] == [0, 1, 2]):
        raise AssertionError()
    selected = []
    for record in records:
        artifacts = {}
        for role in ('master', 'provenance', 'raw_source'):
            descriptor = record[role]
            path = (root / descriptor['file']).resolve()
            if not (path.is_relative_to(directory.resolve())):
                raise AssertionError((role, path))
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if not (digest == descriptor['sha256']):
                raise AssertionError((role, path, digest))
            artifacts[role] = path
        provenance = json.loads(artifacts['provenance'].read_text(encoding='utf-8'))
        if not (provenance['mode'] == 'built-in imagegen'):
            raise AssertionError(record['id'])
        with Image.open(artifacts['master']) as source:
            if not (source.mode == 'RGB' and source.size == (1024, 896)):
                raise AssertionError(record['id'])
            native = source.resize((256, 224), Image.Resampling.NEAREST)
            if not (source.tobytes() == native.resize(source.size, Image.Resampling.NEAREST).tobytes()):
                raise AssertionError(record['id'])
            if not (len(native.getcolors(91) or []) in range(3, 91)):
                raise AssertionError(record['id'])
        selected.append({**record, 'image': native, 'manifest_sha256':
                         hashlib.sha256(manifest_path.read_bytes()).hexdigest()})
    return selected
