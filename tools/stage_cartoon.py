"""Source-aware ambient phase design for the reviewed cartoon stage masters.

The stage encoder owns the map redirect and native validation.  This module
only chooses eight cells that are meaningful in the selected master and
creates four palette-preserving tile phases from the *actual* encoded tiles.
No RGB pixels or BG palette entries are introduced at runtime: every phase
uses an index already present in its source tile/palette bank.
"""
from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image

from stage_assets import _decode_tile, _encode_tile, _tile


PHASE_COUNT = 4
MAP_WIDTH = 32
BYTES_PER_TILE = 32


# The coordinates are deliberately expressed in map cells, while the source
# tile and palette are resolved from the map supplied to the function.  This
# keeps the animation attached to a real feature after a source-master
# re-quantization and prevents an old tile-number assumption from silently
# repainting another part of a stage.
_FEATURES: dict[str, list[dict]] = {
    "stage0": [
        {"x": 28, "y": 6, "role": "tree_leaf_shimmer", "patterns": [
            [(2, 2), (3, 2), (3, 3), (4, 3)], [(1, 3), (2, 3), (2, 4), (3, 4)], [(3, 2), (4, 2), (4, 3), (5, 3)]
        ]},
        {"x": 29, "y": 6, "role": "tree_leaf_shimmer", "patterns": [
            [(0, 2), (1, 2), (1, 3), (2, 3)], [(0, 3), (1, 3), (1, 4), (2, 4)], [(1, 2), (2, 2), (2, 3), (3, 3)]
        ]},
        {"x": 28, "y": 7, "role": "tree_leaf_shimmer", "patterns": [
            [(2, 3), (3, 3), (3, 4), (4, 4)], [(1, 4), (2, 4), (2, 5), (3, 5)], [(3, 3), (4, 3), (4, 4), (5, 4)]
        ]},
        {"x": 29, "y": 7, "role": "tree_leaf_shimmer", "patterns": [
            [(0, 3), (1, 3), (1, 4), (2, 4)], [(0, 4), (1, 4), (1, 5), (2, 5)], [(1, 3), (2, 3), (2, 4), (3, 4)]
        ]},
        # The canopy panes are above the fighter floor and read as glass
        # highlights in the v2 master; keeping the shimmer here avoids
        # painting the unobstructed lower fighting plane.
        {"x": 16, "y": 8, "role": "glass_reflection", "patterns": [
            [(4, 2), (5, 2), (6, 2), (7, 2), (5, 3)], [(2, 3), (3, 3), (4, 3), (5, 3), (3, 4)],
            [(0, 4), (1, 4), (2, 4), (3, 4), (1, 5)]
        ]},
        {"x": 17, "y": 8, "role": "glass_reflection", "patterns": [
            [(0, 3), (1, 3), (2, 3), (3, 3), (2, 4)], [(0, 4), (1, 4), (2, 4), (3, 4), (1, 5)],
            [(0, 5), (1, 5), (2, 5), (3, 5), (1, 6)]
        ]},
        {"x": 16, "y": 9, "role": "glass_reflection", "patterns": [
            [(4, 2), (5, 2), (6, 2), (7, 2), (5, 3)], [(2, 3), (3, 3), (4, 3), (5, 3), (3, 4)],
            [(0, 4), (1, 4), (2, 4), (3, 4), (1, 5)]
        ]},
        {"x": 17, "y": 9, "role": "glass_reflection", "patterns": [
            [(0, 3), (1, 3), (2, 3), (3, 3), (2, 4)], [(0, 4), (1, 4), (2, 4), (3, 4), (1, 5)],
            [(0, 5), (1, 5), (2, 5), (3, 5), (1, 6)]
        ]},
    ],
    "stage1": [
        {"x": 4, "y": 10, "role": "stringlight_pulse", "patterns": [
            [(5, 2), (6, 2), (5, 3)], [(4, 3), (5, 3), (6, 3)],
            [(5, 2), (6, 2), (6, 3)]
        ]},
        {"x": 8, "y": 10, "role": "stringlight_pulse", "patterns": [
            [(3, 2), (4, 2), (4, 3)], [(2, 3), (3, 3), (4, 3)],
            [(3, 2), (4, 2), (3, 3)]
        ]},
        {"x": 16, "y": 14, "role": "party_gesture", "patterns": [
            [(5, 2), (6, 2), (5, 3), (6, 3)], [(4, 1), (5, 1), (5, 2), (6, 2)], [(6, 2), (7, 2), (6, 3), (7, 3)]
        ]},
        {"x": 17, "y": 14, "role": "party_gesture", "patterns": [
            [(0, 2), (1, 2), (0, 3), (1, 3)], [(0, 1), (1, 1), (0, 2), (1, 2)], [(1, 2), (2, 2), (1, 3), (2, 3)]
        ]},
        {"x": 16, "y": 15, "role": "party_gesture", "patterns": [
            [(5, 2), (6, 2), (5, 3), (6, 3)], [(4, 1), (5, 1), (5, 2), (6, 2)], [(6, 2), (7, 2), (6, 3), (7, 3)]
        ]},
        {"x": 17, "y": 15, "role": "party_gesture", "patterns": [
            [(1, 2), (2, 2), (1, 3), (2, 3)], [(1, 1), (2, 1), (2, 2), (3, 2)], [(2, 2), (3, 2), (2, 3), (3, 3)]
        ]},
        # The right building's warm window begins at row 13 in the v2
        # master; the old row-10 roof cells were only nearby pixels.
        {"x": 27, "y": 13, "role": "window_light_pulse", "patterns": [
            [(2, 2), (3, 2)], [(1, 1), (2, 1)], [(2, 2), (3, 2)]
        ]},
        {"x": 28, "y": 13, "role": "window_light_pulse", "patterns": [
            [(2, 2), (3, 2)], [(1, 1), (2, 1)], [(2, 2), (3, 2)]
        ]},
    ],
    "stage2": [
        {"x": 7, "y": 13, "role": "monitor_left_cursor", "patterns": [
            [], [], []
        ]},
        {"x": 8, "y": 13, "role": "monitor_left_cursor", "patterns": [
            [], [], []
        ]},
        {"x": 7, "y": 14, "role": "monitor_left_cursor", "patterns": [
            [(1, 2), (2, 2), (3, 2), (4, 2), (2, 3)],
            [(3, 2), (4, 2), (5, 2), (6, 2), (4, 3)],
            [(4, 2), (5, 2), (6, 2), (7, 2), (6, 3)]
        ]},
        {"x": 8, "y": 14, "role": "monitor_left_cursor", "patterns": [
            [(0, 2), (1, 2)], [(1, 2), (2, 2), (2, 3)], [(2, 2), (3, 2), (3, 3)]
        ]},
        {"x": 19, "y": 13, "role": "monitor_right_cursor", "patterns": [
            [], [], []
        ]},
        {"x": 20, "y": 13, "role": "monitor_right_cursor", "patterns": [
            [], [], []
        ]},
        {"x": 19, "y": 14, "role": "monitor_right_cursor", "patterns": [
            [(1, 2), (2, 2), (3, 2), (4, 2), (2, 3)],
            [(3, 2), (4, 2), (5, 2), (6, 2), (4, 3)],
            [(4, 2), (5, 2), (6, 2), (7, 2), (6, 3)]
        ]},
        {"x": 20, "y": 14, "role": "monitor_right_cursor", "patterns": [
            [(0, 2), (1, 2)], [(1, 2), (2, 2), (2, 3)], [(2, 2), (3, 2), (3, 3)]
        ]},
    ],
}


def _map_word(base_map: bytes, x: int, y: int) -> int:
    if len(base_map) != MAP_WIDTH * MAP_WIDTH * 2:
        raise ValueError("stage map must contain 1024 16-bit words")
    return struct.unpack_from("<H", base_map, (y * MAP_WIDTH + x) * 2)[0]


def _luma15(palette: bytes, bank: int, index: int) -> int:
    # background() emits six banks in palette order while its map words use
    # BG palette numbers 2..7, leaving banks 0/1 reserved for the HUD and
    # effects.  Accept direct 0..5 too for isolated encoder fixtures.
    palette_bank = bank - 2 if 2 <= bank <= 7 else bank
    if not 0 <= palette_bank < 6:
        raise ValueError(f"stage map palette bank is outside the six authored banks: {bank}")
    offset = (palette_bank * 16 + index) * 2
    raw = struct.unpack_from("<H", palette, offset)[0]
    # SNES BGR15.  The weights favor green just enough to keep the ordering
    # useful for foliage, warm bulbs and the cool monitor banks.
    red = raw & 31
    green = (raw >> 5) & 31
    blue = (raw >> 10) & 31
    return red * 3 + green * 4 + blue * 2


def _ordered_values(tile: bytes, palette: bytes, bank: int) -> list[int]:
    values = set(value for row in _decode_tile(tile) for value in row)
    if len(values) < 2:
        # A flat source tile is unusual for a selected feature.  Use the
        # source palette bank only as a deterministic fallback, still never
        # introducing a color outside the authored stage palette.
        values.update(range(1, 16))
    return sorted(values, key=lambda value: (_luma15(palette, bank, value), value))


def _replacement(current: int, target: int, alternate: int,
                 ordered: Iterable[int]) -> int:
    if current != target:
        return target
    if current != alternate:
        return alternate
    for candidate in ordered:
        if candidate != current:
            return candidate
    raise ValueError("ambient feature has no alternate palette index")


def _variant(source: bytes, positions: list[tuple[int, int]], target: int,
             alternate: int, ordered: list[int]) -> tuple[bytes, int]:
    pixels = _decode_tile(source)
    changed = 0
    for x, y in positions:
        if not 0 <= x < 8 or not 0 <= y < 8:
            raise ValueError(f"ambient feature pixel outside tile: {(x, y)}")
        value = _replacement(pixels[y][x], target, alternate, ordered)
        if value != pixels[y][x]:
            changed += 1
            pixels[y][x] = value
    if not changed:
        raise ValueError("ambient feature phase did not change its source tile")
    return _encode_tile(pixels), changed


def _target_policy(role: str, ordered: list[int], phase: int) -> tuple[int, int]:
    if len(ordered) < 2:
        raise ValueError(f"{role} needs at least two palette candidates")
    if role.startswith("monitor_"):
        # A dark cursor/progress segment traverses the lower monitor bezel,
        # below the FAST/11/8.1 lettering.  Alternating a second dark shade
        # keeps the movement readable without painting text rows.
        target = ordered[0] if phase != 2 else ordered[1]
        alternate = ordered[-1] if target == ordered[0] else ordered[0]
        return target, alternate
    if role in {"tree_leaf_shimmer", "glass_reflection"}:
        target = ordered[-1] if phase != 2 else ordered[-2]
        alternate = ordered[-2] if target == ordered[-1] else ordered[-1]
        return target, alternate
    # Bulbs, party gesture and window light use a restrained warm pulse.
    target = ordered[-2] if phase != 2 else ordered[-1]
    alternate = ordered[-1] if target == ordered[-2] else ordered[-2]
    return target, alternate


def cartoon_stage_animation(name: str, base_gfx: bytes, base_map: bytes,
                            palette: bytes, source_image: Image.Image) -> dict:
    """Return source-aware cells/phases for one selected cartoon stage.

    ``source_image`` is the 256x224 nearest-reduced master selected by
    ``stage_sources``.  It is used for provenance and size validation; the
    native phase edits themselves are made from the quantized tiles so every
    result is guaranteed to be representable by the existing BG1 palette.
    """
    if name not in _FEATURES:
        raise ValueError(f"unknown cartoon stage: {name}")
    if not isinstance(source_image, Image.Image) or source_image.size != (256, 224):
        raise ValueError("cartoon stage source must be the selected 256x224 image")
    if source_image.mode != "RGB":
        source_image = source_image.convert("RGB")
    if len(palette) != 192:
        raise ValueError("stage palette must contain six 16-color banks")

    features = _FEATURES[name]
    if len(features) != 8:
        raise ValueError(f"{name} cartoon animation needs exactly eight cells")
    cells = [{key: value for key, value in feature.items() if key != "patterns"}
             for feature in features]
    phases: list[list[bytes]] = [[_tile(base_gfx, _map_word(base_map, c["x"], c["y"]) & 0x3FF)
                                  for c in cells]]
    design_cells = []
    changed_by_phase = [[0] * len(cells) for _ in range(PHASE_COUNT)]

    for slot, feature in enumerate(features):
        x, y = feature["x"], feature["y"]
        map_word = _map_word(base_map, x, y)
        source_tile_index = map_word & 0x3FF
        bank = (map_word >> 10) & 7
        source = phases[0][slot]
        ordered = _ordered_values(source, palette, bank)
        phase_tiles = [source]
        phase_details = []
        for phase in range(1, PHASE_COUNT):
            positions = feature["patterns"][phase - 1]
            if not positions:
                # The eight-cell map contract reserves a compact monitor
                # region, but only the four lower cells carry the moving
                # cursor. Keeping the upper four source-identical avoids
                # turning a small UI cue into scattered monitor noise.
                phase_tiles.append(source)
                phase_details.append({
                    "phase": phase,
                    "pixels": [],
                    "target_palette": None,
                    "alternate_palette": None,
                    "changed_pixels": 0,
                })
                continue
            target, alternate = _target_policy(feature["role"], ordered, phase)
            tile, changed = _variant(source, positions, target, alternate, ordered)
            phase_tiles.append(tile)
            changed_by_phase[phase][slot] = changed
            phase_details.append({
                "phase": phase,
                "pixels": [list(point) for point in positions],
                "target_palette": target,
                "alternate_palette": alternate,
                "changed_pixels": changed,
            })
        phases[0][slot] = source
        for phase in range(1, PHASE_COUNT):
            if len(phases) <= phase:
                phases.append([b"" for _ in cells])
            phases[phase][slot] = phase_tiles[phase]
        design_cells.append({
            "slot": slot,
            "x": x,
            "y": y,
            "native_rect": [x * 8, y * 8, x * 8 + 7, y * 8 + 7],
            "role": feature["role"],
            "source_tile": source_tile_index,
            "source_palette": bank,
            "source_tile_sha256": hashlib.sha256(source).hexdigest(),
            "ordered_palette_indices": ordered,
            "phase_edits": phase_details,
        })

    if len(phases) != PHASE_COUNT or any(len(phase) != 8 for phase in phases):
        raise ValueError("cartoon stage phase construction did not produce 4x8 tiles")
    for phase in phases:
        if any(len(tile) != BYTES_PER_TILE for tile in phase):
            raise ValueError("cartoon stage phase contains a non-4bpp tile")
    if any(phases[phase] == phases[0] for phase in range(1, PHASE_COUNT)):
        raise ValueError(f"{name} cartoon phase is byte-identical to phase zero")
    if len({b"".join(phase) for phase in phases}) != PHASE_COUNT:
        raise ValueError(f"{name} cartoon phases are not all distinct")

    source_hash = hashlib.sha256(source_image.tobytes()).hexdigest()
    feature_design = {
        "version": "0.22.0",
        "source_image_sha256": source_hash,
        "source_image_size": [source_image.width, source_image.height],
        "phase_count": PHASE_COUNT,
        "phase_semantics": [
            "source-identical neutral",
            "feature highlight enters",
            "feature highlight crosses",
            "feature returns",
        ],
        "selection": "eight map cells derived from the selected base map; no BG palette writes",
        "cells": design_cells,
        "changed_pixels_by_phase": [
            sum(changed_by_phase[phase]) for phase in range(PHASE_COUNT)
        ],
    }
    return {"cells": cells, "phases": phases, "feature_design": feature_design}


def regenerate_selected_ambient(root):
    """Rebuild only the three owned ambient binaries and dynamics manifest.

    Recover the authored map from the retained source words, then use the same
    encoder as make_assets. No fighter/menu/audio asset generation is needed.
    """
    import json
    from stage_assets import build_stage_animation
    from stage_sources import load_stage_sources
    out = root / "assets/generated"
    path = out / "stage-dynamics.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for source, previous in zip(load_stage_sources(root), manifest["stages"]):
        name = "stage" + str(source["id"])
        base_map = bytearray((out / (name + "_map.bin")).read_bytes())
        for cell in previous["cells"]:
            struct.pack_into("<H", base_map, (cell["y"] * 32 + cell["x"]) * 2,
                             cell["map_word_before"])
        gfx = (out / (name + "_tiles.bin")).read_bytes()
        palette = (out / (name + "_pal.bin")).read_bytes()
        motion = cartoon_stage_animation(name, gfx, bytes(base_map), palette, source["image"])
        dynamic = build_stage_animation(name, gfx, bytes(base_map), palette,
                                        cells=motion["cells"], phases=motion["phases"])
        if dynamic["map"] != (out / (name + "_map.bin")).read_bytes():
            raise ValueError("ambient-only generation changed a map")
        record = dynamic["manifest"]
        record["art_source"] = previous["art_source"]
        record["feature_design"] = motion["feature_design"]
        manifest["stages"][source["id"]] = record
        (out / (name + "_ambient.bin")).write_bytes(dynamic["ambient"])
    path.write_bytes((json.dumps(manifest, indent=2) + "\n").encode("utf-8"))


if __name__ == "__main__":
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regenerate", action="store_true", required=True)
    parser.parse_args()
    regenerate_selected_ambient(Path(__file__).resolve().parents[1])


__all__ = ["cartoon_stage_animation"]
