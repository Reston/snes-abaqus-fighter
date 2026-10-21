"""Native, palette-preserving ambient animation for the three BG1 stages.

Stage masters remain the source of truth.  This module only derives four
small phases from already encoded 4bpp tiles, redirects eight map cells to
the unused BG1 tile slots immediately before BG2, and records every native
coordinate and source hash for review.
"""
from __future__ import annotations

import hashlib
import struct

PHASE_COUNT = 4
BYTES_PER_TILE = 32
TILE_INDEX_BASE = 960
TILE_COUNT = 8
BYTES_PER_PHASE = TILE_COUNT * BYTES_PER_TILE
AMBIENT_VRAM_WORD = 0x3C00
PHASE_TICKS = 16
MAX_PHASE_AGE = 15
PHASE_CAPTURE_FRAMES = 128
TRACE_FIELDS = {
    "status": 114,
    "uploaded_phase": 115,
    "ambient_clock": 116,
    "pending_phase": 117,
    "pending_age": 118,
}
MAP_WIDTH = 32
MAP_HEIGHT = 32
MAP_BYTES = MAP_WIDTH * MAP_HEIGHT * 2

STAGE_RECORDS = {
    "stage0": (0, "las-condes"),
    "stage1": (1, "el-castillo"),
    "stage2": (2, "la-oficina"),
}


def _decode_tile(data: bytes) -> list[list[int]]:
    if len(data) != BYTES_PER_TILE:
        raise ValueError(f"4bpp tile must be {BYTES_PER_TILE} bytes, got {len(data)}")
    pixels = []
    for y in range(8):
        row = []
        for x in range(8):
            value = 0
            for bit in range(4):
                value |= ((data[(bit // 2) * 16 + y * 2 + bit % 2] >> (7 - x)) & 1) << bit
            row.append(value)
        pixels.append(row)
    return pixels


def _encode_tile(pixels: list[list[int]]) -> bytes:
    if len(pixels) != 8 or any(len(row) != 8 for row in pixels):
        raise ValueError("tile pixels must be an 8x8 matrix")
    out = bytearray(BYTES_PER_TILE)
    for y, row in enumerate(pixels):
        for x, value in enumerate(row):
            if not 0 <= value <= 15:
                raise ValueError(f"4bpp palette index out of range: {value}")
            for bit in range(4):
                out[(bit // 2) * 16 + y * 2 + bit % 2] |= ((value >> bit) & 1) << (7 - x)
    return bytes(out)


def _tile(base_gfx: bytes, index: int) -> bytes:
    start = index * BYTES_PER_TILE
    end = start + BYTES_PER_TILE
    if start < 0 or end > len(base_gfx) or len(base_gfx) % BYTES_PER_TILE:
        raise ValueError(f"source tile {index} is outside the encoded stage graphics")
    return base_gfx[start:end]


def _changed_pixels(before: bytes, after: bytes) -> list[tuple[int, int]]:
    left = _decode_tile(before)
    right = _decode_tile(after)
    return [(x, y) for y in range(8) for x in range(8) if left[y][x] != right[y][x]]


def _bounds(points: list[tuple[int, int]]) -> dict[str, int] | None:
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return {"left": min(xs), "top": min(ys), "right": max(xs), "bottom": max(ys)}


def _apply_edits(source: bytes, edits: list[tuple[int, int, int]]) -> bytes:
    pixels = _decode_tile(source)
    for x, y, value in edits:
        if not 0 <= x < 8 or not 0 <= y < 8:
            raise ValueError(f"ambient edit outside tile: {(x, y)}")
        if not 0 <= value <= 15:
            raise ValueError(f"ambient palette index out of range: {value}")
        pixels[y][x] = value
    return _encode_tile(pixels)


def _stage_cells(name: str) -> list[dict[str, int | str]]:
    if name == "stage0":
        return [
            {"x": 28, "y": 6, "source_tile": 220, "palette": 5, "role": "tree_leaf_shimmer"},
            {"x": 29, "y": 6, "source_tile": 221, "palette": 5, "role": "tree_leaf_shimmer"},
            {"x": 28, "y": 7, "source_tile": 252, "palette": 5, "role": "tree_leaf_shimmer"},
            {"x": 29, "y": 7, "source_tile": 253, "palette": 5, "role": "tree_leaf_shimmer"},
            {"x": 16, "y": 21, "source_tile": 687, "palette": 7, "role": "glass_reflection"},
            {"x": 17, "y": 21, "source_tile": 688, "palette": 7, "role": "glass_reflection"},
            {"x": 16, "y": 22, "source_tile": 719, "palette": 2, "role": "glass_reflection"},
            {"x": 17, "y": 22, "source_tile": 720, "palette": 7, "role": "glass_reflection"},
        ]
    if name == "stage1":
        return [
            {"x": 5, "y": 10, "source_tile": 315, "palette": 4, "role": "stringlight"},
            {"x": 9, "y": 10, "source_tile": 319, "palette": 3, "role": "stringlight"},
            {"x": 16, "y": 14, "source_tile": 454, "palette": 3, "role": "party_gesture"},
            {"x": 17, "y": 14, "source_tile": 455, "palette": 4, "role": "party_gesture"},
            {"x": 16, "y": 15, "source_tile": 486, "palette": 4, "role": "party_gesture"},
            {"x": 17, "y": 15, "source_tile": 487, "palette": 4, "role": "party_gesture"},
            {"x": 27, "y": 10, "source_tile": 337, "palette": 5, "role": "window_light"},
            {"x": 28, "y": 10, "source_tile": 338, "palette": 5, "role": "window_light"},
        ]
    if name == "stage2":
        return [
            {"x": 7, "y": 13, "source_tile": 415, "palette": 7, "role": "monitor_left"},
            {"x": 8, "y": 13, "source_tile": 416, "palette": 7, "role": "monitor_left"},
            {"x": 7, "y": 14, "source_tile": 447, "palette": 7, "role": "monitor_left"},
            {"x": 8, "y": 14, "source_tile": 448, "palette": 7, "role": "monitor_left"},
            {"x": 19, "y": 13, "source_tile": 427, "palette": 7, "role": "monitor_right"},
            {"x": 20, "y": 13, "source_tile": 428, "palette": 7, "role": "monitor_right"},
            {"x": 19, "y": 14, "source_tile": 459, "palette": 7, "role": "monitor_right"},
            {"x": 20, "y": 14, "source_tile": 460, "palette": 7, "role": "monitor_right"},
        ]
    raise ValueError(f"unknown stage animation: {name}")


def _stage_edits(name: str) -> list[list[tuple[int, int, int, int]]]:
    """Return four phase edit lists as (slot, x, y, palette_index)."""
    if name == "stage0":
        return [
            [],
            # One connected 2x2 red-leaf highlight moves one native pixel
            # across the cluster before returning to the neutral canopy.
            [(0, 2, 2, 9), (0, 3, 2, 9), (1, 0, 2, 9), (1, 1, 2, 9),
             (2, 2, 3, 9), (2, 3, 3, 9), (3, 0, 3, 9), (3, 1, 3, 9),
             # A connected three-pixel reflection stripe starts at the left.
             (4, 5, 2, 1), (4, 6, 2, 1), (4, 7, 2, 1),
             (5, 0, 3, 1), (5, 1, 3, 1), (5, 2, 3, 1),
             (6, 5, 2, 1), (6, 6, 2, 1), (6, 7, 2, 1),
             (7, 0, 3, 1), (7, 1, 3, 1), (7, 2, 3, 1)],
            # The leaf cluster sways in the opposite direction; the glass
            # streak advances diagonally by one row and two columns.
            [(0, 1, 3, 9), (0, 2, 3, 9), (1, 0, 3, 9), (1, 1, 3, 9),
             (2, 1, 4, 9), (2, 2, 4, 9), (3, 0, 4, 9), (3, 1, 4, 9),
             (4, 3, 3, 1), (4, 4, 3, 1), (4, 5, 3, 1),
             (5, 0, 4, 1), (5, 1, 4, 1), (5, 2, 4, 1),
             (6, 3, 3, 1), (6, 4, 3, 1), (6, 5, 3, 1),
             (7, 0, 4, 1), (7, 1, 4, 1), (7, 2, 4, 1)],
            # Return the leaf shimmer toward center while the reflection
            # finishes its short diagonal sweep.
            [(0, 1, 2, 9), (0, 2, 2, 9), (1, 0, 2, 9), (1, 1, 2, 9),
             (2, 1, 3, 9), (2, 2, 3, 9), (3, 0, 3, 9), (3, 1, 3, 9),
             (4, 1, 4, 1), (4, 2, 4, 1), (4, 3, 4, 1),
             (5, 0, 5, 1), (5, 1, 5, 1), (5, 2, 5, 1),
             (6, 1, 4, 1), (6, 2, 4, 1), (6, 3, 4, 1),
             (7, 0, 5, 1), (7, 1, 5, 1), (7, 2, 5, 1)],
        ]
    if name == "stage1":
        return [
            [],
            # Each bulb gets a center plus two warm neighbors, then the
            # pulse contracts.  The gesture is a connected amber cup/hand
            # moving one row upward across the dark central guest.
            [(0, 1, 6, 1), (0, 4, 6, 1), (1, 0, 1, 1), (1, 2, 2, 1),
             (2, 5, 2, 1), (2, 6, 2, 1), (2, 7, 2, 1),
             (3, 0, 2, 1), (3, 1, 2, 1),
             (4, 5, 2, 1), (4, 6, 2, 1),
             (5, 1, 2, 1), (5, 2, 2, 1),
             (6, 2, 2, 2), (7, 5, 2, 2)],
            [(0, 1, 5, 1), (0, 2, 5, 1), (0, 3, 5, 1), (0, 4, 5, 1),
             (1, 0, 0, 1), (1, 1, 0, 1), (1, 2, 0, 1), (1, 3, 1, 1),
             (2, 6, 1, 1), (2, 7, 1, 1),
             (3, 0, 1, 1), (3, 1, 1, 1), (3, 2, 1, 1),
             (4, 4, 1, 1), (4, 5, 1, 1),
             (5, 2, 1, 1), (5, 3, 1, 1),
             (6, 3, 3, 3), (7, 1, 3, 3)],
            [(0, 1, 6, 1), (0, 4, 6, 1), (1, 0, 1, 1), (1, 2, 2, 1),
             (2, 5, 2, 1), (2, 6, 2, 1), (2, 7, 2, 1),
             (3, 0, 2, 1), (3, 1, 2, 1),
             (4, 5, 2, 1), (4, 6, 2, 1),
             (5, 1, 2, 1), (5, 2, 2, 1),
             (6, 2, 4, 2), (7, 4, 4, 2)],
        ]
    if name == "stage2":
        return [
            [],
            # A two-pixel monitor cursor/progress segment travels beneath
            # the 11/8.1 Mbps lettering; only the lower two monitor tiles
            # change, so every digit remains byte-identical.
            [(2, 0, 1, 3), (2, 1, 1, 3), (2, 0, 2, 3), (2, 1, 2, 3),
             (6, 0, 1, 3), (6, 1, 1, 3), (6, 0, 2, 3), (6, 1, 2, 3)],
            [(2, 5, 1, 3), (2, 6, 1, 3), (2, 5, 2, 3), (2, 6, 2, 3),
             (6, 5, 1, 3), (6, 6, 1, 3), (6, 5, 2, 3), (6, 6, 2, 3)],
            [(3, 2, 1, 3), (3, 3, 1, 3), (3, 2, 2, 3), (3, 3, 2, 3),
             (7, 2, 1, 3), (7, 3, 1, 3), (7, 2, 2, 3), (7, 3, 2, 3)],
        ]
    raise ValueError(f"unknown stage animation: {name}")


def build_stage_animation(name: str, base_gfx: bytes, base_map: bytes,
                          palette: bytes, cells: list[dict] | None = None,
                          phases: list[list[bytes]] | None = None) -> dict:
    """Build four 8-tile phases and a map with eight dynamic tile entries.

    ``base_gfx`` and ``base_map`` are never modified.  Supplying explicit
    ``cells`` and ``phases`` is supported for isolated QA and for source-aware
    stage variants.  Custom cells may contain only ``x``, ``y`` and ``role``;
    their source tile and palette are derived from ``base_map``.  If either
    value is supplied it must agree with that map.  Custom cells must provide
    explicit phases so the legacy edit table cannot accidentally paint a new
    stage with coordinates from an older master.
    """
    if len(base_gfx) % BYTES_PER_TILE or len(base_gfx) > 0x7000:
        raise ValueError("stage graphics must be whole tiles and fit the 896-tile region")
    if len(base_map) != MAP_BYTES:
        raise ValueError(f"stage map must be {MAP_BYTES} bytes")
    if len(palette) != 192:
        raise ValueError("stage palette must contain six 16-color banks")
    try:
        record_id, slug = STAGE_RECORDS[name]
    except KeyError as exc:
        raise ValueError(f"unknown stage animation: {name}") from exc
    custom_cells = cells is not None
    cells = list(_stage_cells(name) if cells is None else cells)
    if len(cells) != TILE_COUNT:
        raise ValueError(f"{name} requires exactly {TILE_COUNT} dynamic cells")
    normalized_cells = []
    for slot, cell in enumerate(cells):
        x, y = int(cell["x"]), int(cell["y"])
        if not 0 <= x < MAP_WIDTH or not 0 <= y < MAP_HEIGHT:
            raise ValueError(f"map cell outside 32x32 stage map: {(x, y)}")
        raw = struct.unpack_from('<H', base_map, (y * MAP_WIDTH + x) * 2)[0]
        map_tile = raw & 0x3FF
        source_palette = (raw >> 10) & 7
        if "source_tile" in cell and map_tile != int(cell["source_tile"]):
            raise ValueError(f"{name} cell {(x, y)} expected tile {cell['source_tile']}, got {map_tile}")
        if "palette" in cell and source_palette != int(cell["palette"]):
            raise ValueError(f"{name} cell {(x, y)} expected palette {cell['palette']}, got {source_palette}")
        normalized_cells.append({
            **cell,
            "x": x,
            "y": y,
            "source_tile": map_tile,
            "palette": source_palette,
        })
        if TILE_INDEX_BASE + slot >= 1024:
            raise ValueError("dynamic tile index exceeds BG1 map tile field")
    cells = normalized_cells

    source_tiles = [_tile(base_gfx, int(cell["source_tile"])) for cell in cells]
    if phases is None:
        if custom_cells:
            raise ValueError("custom stage cells require explicit four-phase tile data")
        edits = _stage_edits(name)
        phases = []
        for phase_index in range(PHASE_COUNT):
            edits_by_slot: dict[int, list[tuple[int, int, int]]] = {}
            for slot, x, y, value in edits[phase_index]:
                edits_by_slot.setdefault(slot, []).append((x, y, value))
            phases.append([
                _apply_edits(source, edits_by_slot.get(slot, []))
                for slot, source in enumerate(source_tiles)
            ])
    if len(phases) != PHASE_COUNT or any(len(phase) != TILE_COUNT for phase in phases):
        raise ValueError("stage animation must contain four phases of eight tiles")
    normalized = []
    for phase_index, phase in enumerate(phases):
        phase_bytes = []
        for slot, tile_bytes in enumerate(phase):
            tile_bytes = bytes(tile_bytes)
            if len(tile_bytes) != BYTES_PER_TILE:
                raise ValueError(f"{name} phase {phase_index} slot {slot} is not one 4bpp tile")
            if phase_index == 0 and tile_bytes != source_tiles[slot]:
                raise ValueError(f"{name} phase 0 slot {slot} is not byte-identical to its source tile")
            _decode_tile(tile_bytes)
            phase_bytes.append(tile_bytes)
        normalized.append(b''.join(phase_bytes))
    ambient = b''.join(normalized)

    redirected = bytearray(base_map)
    cell_manifest = []
    for slot, cell in enumerate(cells):
        x, y = int(cell["x"]), int(cell["y"])
        offset = (y * MAP_WIDTH + x) * 2
        before = struct.unpack_from('<H', base_map, offset)[0]
        after = (before & 0xFC00) | (TILE_INDEX_BASE + slot)
        struct.pack_into('<H', redirected, offset, after)
        cell_manifest.append({
            "slot": slot,
            "x": x,
            "y": y,
            "native_x": x * 8,
            "native_y": y * 8,
            "role": str(cell.get("role", "ambient")),
            "source_tile": int(cell["source_tile"]),
            "dynamic_tile": TILE_INDEX_BASE + slot,
            "palette": (before >> 10) & 7,
            "map_word_before": before,
            "map_word_after": after,
            "source_sha256": hashlib.sha256(source_tiles[slot]).hexdigest(),
        })

    phase_manifest = []
    for phase_index, phase_bytes in enumerate(normalized):
        all_points = []
        cell_phases = []
        for slot, source in enumerate(source_tiles):
            changed = _changed_pixels(source, phases[phase_index][slot])
            native = [(cells[slot]["x"] * 8 + x, cells[slot]["y"] * 8 + y) for x, y in changed]
            all_points.extend(native)
            cell_phases.append({
                "slot": slot,
                "changed_pixels": len(changed),
                "pixel_bounds": _bounds(native),
            })
        phase_manifest.append({
            "index": phase_index,
            "offset": phase_index * BYTES_PER_PHASE,
            "bytes": BYTES_PER_PHASE,
            "sha256": hashlib.sha256(phase_bytes).hexdigest(),
            "changed_pixels": len(all_points),
            "pixel_bounds": _bounds(all_points),
            "cells": cell_phases,
        })
    manifest = {
        "version": "0.1.0",
        "record_id": record_id,
        "name": name,
        "slug": slug,
        "phase_count": PHASE_COUNT,
        "phase_ticks": PHASE_TICKS,
        "max_phase_age": MAX_PHASE_AGE,
        "phase_capture_frames": PHASE_CAPTURE_FRAMES,
        "tile_count": TILE_COUNT,
        "bytes_per_tile": BYTES_PER_TILE,
        "bytes_per_phase": BYTES_PER_PHASE,
        "ambient_bytes": len(ambient),
        "ambient_vram_word": AMBIENT_VRAM_WORD,
        "ambient_file": f"assets/generated/{name}_ambient.bin",
        "trace": TRACE_FIELDS.copy(),
        "tile_index_base": TILE_INDEX_BASE,
        "source": {
            "gfx_sha256": hashlib.sha256(base_gfx).hexdigest(),
            "map_sha256": hashlib.sha256(base_map).hexdigest(),
            "palette_sha256": hashlib.sha256(palette).hexdigest(),
            "palette_write": False,
        },
        "ambient_sha256": hashlib.sha256(ambient).hexdigest(),
        "phase_offsets": [record["offset"] for record in phase_manifest],
        "phase_sha256": [record["sha256"] for record in phase_manifest],
        "cells": cell_manifest,
        "phases": phase_manifest,
    }
    return {"map": bytes(redirected), "ambient": ambient, "manifest": manifest}


__all__ = ["build_stage_animation"]
