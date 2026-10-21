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
    assert manifest['schema'] == 2, 'Unknown selected-stage schema'
    assert manifest['style_contract']['native_canvas'] == [256, 224]
    assert manifest['style_contract']['master_canvas'] == [1024, 896]
    records = manifest['stages']
    assert [record['id'] for record in records] == [0, 1, 2]
    selected = []
    for record in records:
        artifacts = {}
        for role in ('master', 'provenance', 'raw_source'):
            descriptor = record[role]
            path = (root / descriptor['file']).resolve()
            assert path.is_relative_to(directory.resolve()), (role, path)
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            assert digest == descriptor['sha256'], (role, path, digest)
            artifacts[role] = path
        provenance = json.loads(artifacts['provenance'].read_text(encoding='utf-8'))
        assert provenance['mode'] == 'built-in imagegen', record['id']
        with Image.open(artifacts['master']) as source:
            assert source.mode == 'RGB' and source.size == (1024, 896), record['id']
            native = source.resize((256, 224), Image.Resampling.NEAREST)
            assert source.tobytes() == native.resize(source.size, Image.Resampling.NEAREST).tobytes(), record['id']
            assert len(native.getcolors(91) or []) in range(3, 91), record['id']
        selected.append({**record, 'image': native, 'manifest_sha256':
                         hashlib.sha256(manifest_path.read_bytes()).hexdigest()})
    return selected
