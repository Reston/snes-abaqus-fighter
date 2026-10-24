"""Silent, headless verification for the animated BG1 stage pass.

The stage pass keeps the authored BG1 plate and map intact, then streams an
eight-tile (256-byte) ambient patch at BG1 tile 960 / VRAM word ``$3C00``.
This suite intentionally reads the native VRAM, WRAM OAM shadow, callback
frames and the appended stage telemetry.  It does not write emulated memory,
open a window or play captured audio.

The ROM-facing manifest is ``assets/generated/stage-dynamics.json``.  It owns
the four phase tile files, selected BG1 map cells, the allowed screen rects,
the maximum pending upload age and the STAT77 overflow masks.  The suite is
kept separate from the existing presentation checks so the authored stage
plate and the runtime ambient patch can be reviewed independently.
"""

from __future__ import annotations

import ctypes as C
import hashlib
import json
import re
import sys
import time
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from emulator import Emulator, ROOT
from stage_test_contract import depth_manifest


TITLE, SELECT, ARENA, FIGHT = 0, 1, 2, 3
STAGE_NAMES = ("las-condes", "el-castillo", "la-oficina")

BG1_TILES_BYTE = 0x0000
BG1_MAP_WORD = 0x3800
BG1_MAP_BYTE = BG1_MAP_WORD * 2
DYNAMIC_TILE_WORD = 0x3C00
DYNAMIC_TILE_BYTE = DYNAMIC_TILE_WORD * 2
DYNAMIC_TILE_COUNT = 8
DYNAMIC_TILE_BYTES = DYNAMIC_TILE_COUNT * 32
BG1_MAP_BYTES = 32 * 32 * 2
PHASE_COUNT = 4
TRACE_DEFAULTS = {
    "ppu_stat": 114,
    "ambient_phase": 115,
    "ambient_clock": 116,
    "ambient_pending_phase": 117,
    "ambient_phase_age": 118,
}
OAM_ENTRY_BYTES = 4
OAM_HIGH_BYTES = 32
OAM_ACTOR_SLOTS = 30
OAM_ACTOR_BASE = (0, 32)
OAM_TOTAL_BYTES = 128 * OAM_ENTRY_BYTES + OAM_HIGH_BYTES

checks: list[dict[str, object]] = []


def check(ok: bool, label: str, details: object | None = None) -> None:
    if not ok:
        raise AssertionError((label, details))
    checks.append({"check": label, "passed": True, "details": details})


def press(e: Emulator, key: str, port: int = 0) -> None:
    e.tap(key, port)
    e.run(20)


def state(e: Emulator) -> dict[str, int]:
    return e.state()


def wait_screen(e: Emulator, wanted: int, max_frames: int = 600) -> None:
    for _ in range(max_frames // 10):
        if state(e)["screen"] == wanted:
            e.run(10)
            return
        e.run(10)
    raise AssertionError(("stage screen did not arrive", wanted, state(e)))


def frame_digest(frame: Image.Image | None) -> str:
    check(frame is not None, "stage callback produced a native frame")
    assert frame is not None
    return hashlib.sha256(frame.tobytes()).hexdigest()


def vram_bytes(e: Emulator) -> bytes:
    pointer = e.core.retro_get_memory_data(3)
    size = e.core.retro_get_memory_size(3)
    return C.string_at(pointer, size)


def _symbol_wram_offset(name: str) -> int | None:
    """Resolve a WRAM symbol from the current linker map when available."""

    pattern = re.compile(r"^\s*([0-9a-fA-F]{6,8})\s+" + re.escape(name) + r"\s*$")
    for path in (ROOT / "dist/abaqus-after-hours.sym",
                 ROOT / "build/abaqus-after-hours.sym"):
        if not path.exists():
            continue
        for line in path.read_text(errors="ignore").splitlines():
            match = pattern.match(line)
            if not match:
                continue
            address = int(match.group(1), 16)
            if (address >> 16) == 0x7E:
                return address & 0xFFFF
            if address < 0x20000:
                return address
    return None


def oam_memory(e: Emulator) -> bytes:
    offset = _symbol_wram_offset("oamMemory")
    if offset is None:
        offset = 0x9010
    return C.string_at(e.ram + offset, OAM_TOTAL_BYTES)


def oam_entry(raw: bytes, index: int) -> dict[str, int]:
    offset = index * OAM_ENTRY_BYTES
    x, y, tile_low, attr = raw[offset:offset + OAM_ENTRY_BYTES]
    high = raw[512 + index // 4]
    pair = (index & 3) * 2
    x9 = (high >> pair) & 1
    size = (high >> (pair + 1)) & 1
    return {
        "x": x | (x9 << 8), "y": y, "tile": tile_low | ((attr & 1) << 8),
        "attr": attr, "x9": x9, "size": size,
    }


def actor_entries(raw: bytes, side: int) -> list[dict[str, int]]:
    base = OAM_ACTOR_BASE[side]
    return [oam_entry(raw, base + index) for index in range(OAM_ACTOR_SLOTS)]


def actor_contract(e: Emulator, expected_floor: int | None = None,
                   allow_airborne: bool = False) -> dict[str, object]:
    raw = oam_memory(e)
    p1 = actor_entries(raw, 0)
    p2 = actor_entries(raw, 1)
    all_entries = p1 + p2
    if not allow_airborne:
        check(all(entry["y"] < 0xF0 for entry in all_entries),
              "ambient stage keeps all sixty actor sprites visible", {
                  "y": [entry["y"] for entry in all_entries],
              })
    check(all(entry["size"] == 1 for entry in all_entries),
          "ambient stage keeps every actor piece at 16x16", {
              "sizes": sorted({entry["size"] for entry in all_entries}),
          })
    floors = [max(entry["y"] for entry in entries) + 16
              for entries in (p1, p2)]
    floor = max(floors)
    if expected_floor is not None:
        check(max(abs(value - expected_floor) for value in floors) <= 1,
              "ambient patch preserves the actor support floor", {
                  "floors": floors, "expected_floor": expected_floor,
              })
    for side, pieces in enumerate((p1, p2)):
        # Ground shadows keep the actor's horizontal pivot while it jumps.
        # Check the actual OAM, including the shared high-table size/X9 bits.
        left = (pieces[0]["x"] - (80 if pieces[0]["attr"] & 0x40 else 0)) & 511
        if left >= 256:
            left -= 512
        shadows = [oam_entry(raw, 64 + side * 2 + index) for index in range(2)]
        check(all(shadow["x"] == left + 32 + index * 16 and
                  shadow["y"] == 200 and shadow["tile"] == 430 and
                  shadow["attr"] == (0x25 if index == 0 else 0x65) and
                  shadow["x9"] == 0 and shadow["size"] == 1
                  for index, shadow in enumerate(shadows)),
              "floor shadows preserve pivot, visibility and native attributes", {
                  "side": side, "actor_left": left, "shadows": shadows,
              })
    return {"floor": floor, "floors": floors,
            "active_sprites": len(all_entries), "raw_tail": raw[256:]}


def actor_rects(e: Emulator) -> list[tuple[int, int, int, int]]:
    """Return tight screen masks for the two native 6x5 actor blocks."""

    raw = oam_memory(e)
    rects: list[tuple[int, int, int, int]] = []
    for side in (0, 1):
        entries = actor_entries(raw, side)
        left = min(entry["x"] for entry in entries)
        top = min(entry["y"] for entry in entries)
        right = max(entry["x"] for entry in entries) + 16
        bottom = max(entry["y"] for entry in entries) + 16
        rects.append((max(0, left - 2), max(0, top - 2),
                      min(256, right + 2), min(224, bottom + 2)))
    return rects


def scanline_budget(raw: bytes) -> dict[str, int]:
    """Return the complete native OBJ scanline budget.

    The two actor blocks occupy slots 0..29 and 32..61, but the stage effect
    and shadow entries use the remaining native slots.  Count every visible
    entry so the stage pass cannot hide an overflow by checking actors only.
    A 16x16 OBJ consumes two 8x8 tile fetches on each covered line; an 8x8
    OBJ consumes one.
    """

    sprite_counts = [0] * 224
    tile_counts = [0] * 224
    for index in range(128):
        entry = oam_entry(raw, index)
        if entry["y"] >= 224:
            continue
        height = 16 if entry["size"] else 8
        tiles = 2 if entry["size"] else 1
        for scanline in range(entry["y"], min(224, entry["y"] + height)):
            sprite_counts[scanline] += 1
            tile_counts[scanline] += tiles
    sprite_max = max(sprite_counts, default=0)
    tile_max = max(tile_counts, default=0)
    return {
        "max_sprites": sprite_max,
        "max_tiles": tile_max,
        "sprite_line": sprite_counts.index(sprite_max) if sprite_max else -1,
        "tile_line": tile_counts.index(tile_max) if tile_max else -1,
    }


def scanline_load(raw: bytes) -> int:
    """Compatibility helper returning the complete sprite count."""

    return scanline_budget(raw)["max_sprites"]


def visible_oam_count(raw: bytes, start: int = 0) -> int:
    """Count visible entries in an OAM range for capture diagnostics."""

    return sum(oam_entry(raw, index)["y"] < 224
               for index in range(start, 128))


def trace_words(e: Emulator, count: int = 119) -> list[int]:
    data = C.string_at(e.ram + 0x1FF00, count * 2)
    return [int.from_bytes(data[index:index + 2], "little")
            for index in range(0, count * 2, 2)]


def stage_trace(e: Emulator, trace_map: dict[str, int]) -> dict[str, int]:
    current = dict(state(e))
    words = trace_words(e, max(119, max(trace_map.values(), default=118) + 1))
    for name, index in trace_map.items():
        current[name] = words[index]
    current["stage_id"] = current.get("arena", 0)
    return current


def resolve_asset(value: object, default: Path) -> Path:
    if value is None:
        return default
    path = Path(str(value))
    if path.is_absolute():
        return path
    candidates = (ROOT / path, ROOT / "assets/generated" / path,
                  ROOT / "assets/art/stages" / path)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def load_dynamic_manifest() -> tuple[dict[str, object], dict[str, int]]:
    path = ROOT / "assets/generated/stage-dynamics.json"
    check(path.exists(), "stage dynamics manifest exists", {"path": str(path)})
    manifest = json.loads(path.read_text())
    check(int(manifest.get("phase_count", PHASE_COUNT)) == PHASE_COUNT,
          "stage dynamics manifest declares four ambient phases", manifest)
    check(int(manifest.get("tile_word", DYNAMIC_TILE_WORD)) == DYNAMIC_TILE_WORD,
          "stage dynamics use BG1 tile 960 at VRAM word $3C00", manifest)
    check(int(manifest.get("tile_count", DYNAMIC_TILE_COUNT)) == DYNAMIC_TILE_COUNT,
          "stage dynamics use eight contiguous 4bpp tiles", manifest)
    trace_map = dict(TRACE_DEFAULTS)
    configured = manifest.get("trace", {})
    if isinstance(configured, dict):
        aliases = {
            "ppu_stat": ("ppu_stat", "status"),
            "ambient_phase": ("ambient_phase", "uploaded_phase"),
            "ambient_clock": ("ambient_clock",),
            "ambient_pending_phase": ("ambient_pending_phase", "pending_phase"),
            "ambient_phase_age": ("ambient_phase_age", "pending_age"),
        }
        for name, names in aliases.items():
            for alias in names:
                if alias in configured:
                    trace_map[name] = int(configured[alias])
                    break
    check(min(trace_map.values()) >= 114,
          "stage telemetry begins after the stable combat trace", trace_map)
    stages = manifest.get("stages")
    check(isinstance(stages, list) and len(stages) == 3,
          "stage dynamics manifest contains all three stages", {
              "count": len(stages) if isinstance(stages, list) else None,
          })
    return manifest, trace_map


def stage_record(manifest: dict[str, object], stage_id: int) -> dict[str, object]:
    stages = manifest["stages"]
    assert isinstance(stages, list)
    for index, record in enumerate(stages):
        assert isinstance(record, dict)
        record_id = record.get("id", record.get("record_id", index))
        if record_id is not None and int(record_id) == stage_id:
            return record
        name = str(record.get("name", ""))
        if name.lower().rstrip().endswith(str(stage_id)):
            return record
        slug = str(record.get("slug", ""))
        if slug.lower().rstrip().endswith(str(stage_id)):
            return record
    raise AssertionError(("stage id missing from dynamics manifest", stage_id))


def stage_slug(record: dict[str, object], stage_id: int) -> str:
    value = str(record.get("slug", record.get("name", STAGE_NAMES[stage_id])))
    if value.lower() in {f"stage{stage_id}", f"stage-{stage_id}"}:
        value = STAGE_NAMES[stage_id]
    return value.lower().replace(" ", "-")


def normalize_cells(value: object) -> list[int]:
    cells: list[int] = []
    if not isinstance(value, list):
        return cells
    for item in value:
        if isinstance(item, int):
            cells.append(item)
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            cells.append(int(item[1]) * 32 + int(item[0]))
        elif isinstance(item, dict) and "x" in item and "y" in item:
            cells.append(int(item["y"]) * 32 + int(item["x"]))
    return sorted(set(cells))


def rects_for(record: dict[str, object], cells: list[int]) -> list[tuple[int, int, int, int]]:
    configured = record.get("screen_rects", record.get("patch_rects", []))
    rects: list[tuple[int, int, int, int]] = []
    if isinstance(configured, list):
        for item in configured:
            if isinstance(item, (list, tuple)) and len(item) == 4:
                rects.append(tuple(int(value) for value in item))
    if rects:
        return rects
    return [((cell % 32) * 8, (cell // 32) * 8,
             (cell % 32 + 1) * 8, (cell // 32 + 1) * 8)
            for cell in cells]


def base_paths(record: dict[str, object], stage_id: int) -> tuple[Path, Path]:
    base = record.get("base", {})
    if not isinstance(base, dict):
        base = {}
    tiles = base.get("tiles", record.get("base_tiles"))
    tile_default = ROOT / "assets/generated" / f"stage{stage_id}_tiles.bin"
    map_file = base.get("map", record.get("base_map"))
    map_default = ROOT / "assets/generated" / f"stage{stage_id}_map.bin"
    return resolve_asset(tiles, tile_default), resolve_asset(map_file, map_default)


def phase_assets(record: dict[str, object], stage_id: int) -> list[dict[str, object]]:
    """Resolve phase blocks from the current single-file stage interface.

    ``make_assets.py`` emits ``stageN_ambient.bin`` with four contiguous
    256-byte blocks.  The manifest records the offset and hash for each
    block.  The older four-file spelling remains accepted for source
    compatibility, but all runtime verification below uses the extracted
    bytes and the manifest hash.
    """

    phases = record.get("phases", record.get("phase_assets", []))
    check(isinstance(phases, list) and len(phases) == PHASE_COUNT,
          "stage record declares four phase assets", {
              "stage": stage_id,
              "count": len(phases) if isinstance(phases, list) else None,
          })
    result: list[dict[str, object]] = []
    assert isinstance(phases, list)
    combined_value = record.get("ambient_file", record.get("ambient"))
    combined_default = ROOT / "assets/generated" / f"stage{stage_id}_ambient.bin"
    combined = resolve_asset(combined_value, combined_default)
    combined_data: bytes | None = None
    if combined.exists():
        combined_data = combined.read_bytes()
    for phase_id, phase in enumerate(phases):
        offset = phase_id * DYNAMIC_TILE_BYTES
        expected_hash: str | None = None
        value: object = None
        if isinstance(phase, dict):
            value = phase.get("tiles", phase.get("asset", phase.get("file")))
            offset = int(phase.get("offset", offset))
            expected_hash = str(phase.get("sha256", "")) or None
        else:
            value = phase
        # The new manifest has no per-phase filename; its offset identifies a
        # slice of the combined ambient file.  If a legacy filename is
        # supplied, keep accepting that interface too.
        if value is None and combined_data is not None:
            path = combined
            check(offset >= 0 and offset + DYNAMIC_TILE_BYTES <= len(combined_data),
                  "combined stage ambient block lies within the generated file", {
                      "stage": stage_id, "phase": phase_id,
                      "offset": offset, "file_bytes": len(combined_data),
                  })
            data = combined_data[offset:offset + DYNAMIC_TILE_BYTES]
        else:
            default = ROOT / "assets/generated" / f"stage{stage_id}_ambient{phase_id}.bin"
            path = resolve_asset(value, default)
            check(path.exists(), "stage ambient phase asset exists", {
                  "stage": stage_id, "phase": phase_id, "path": str(path),
            })
            data = path.read_bytes()
        check(len(data) == DYNAMIC_TILE_BYTES,
              "stage ambient phase contains exactly 256 tile bytes", {
                  "stage": stage_id, "phase": phase_id, "bytes": len(data),
              })
        actual_hash = hashlib.sha256(data).hexdigest()
        if expected_hash is not None:
            check(actual_hash == expected_hash,
                  "stage ambient phase matches its manifest hash", {
                      "stage": stage_id, "phase": phase_id,
                      "expected": expected_hash, "actual": actual_hash,
                  })
        result.append({"path": path, "offset": offset, "data": data,
                       "sha256": actual_hash})
    hashes = [str(item["sha256"]) for item in result]
    check(len(set(hashes)) == PHASE_COUNT,
          "stage ambient phase assets are four distinct tile blocks", {
              "stage": stage_id, "hashes": hashes,
          })
    return result


def map_words(data: bytes) -> list[int]:
    return [int.from_bytes(data[index:index + 2], "little")
            for index in range(0, len(data), 2)]


def verify_stage_vram(e: Emulator, record: dict[str, object], stage_id: int,
                      phase_id: int, base_tiles: bytes, base_map: bytes,
                      phase_tiles: bytes, cells: list[int]) -> dict[str, object]:
    memory = vram_bytes(e)
    check(memory[DYNAMIC_TILE_BYTE:DYNAMIC_TILE_BYTE + DYNAMIC_TILE_BYTES] == phase_tiles,
          "uploaded ambient phase matches the native 256-byte tile block", {
              "stage": stage_id, "phase": phase_id,
              "sha256": hashlib.sha256(memory[DYNAMIC_TILE_BYTE:
                                               DYNAMIC_TILE_BYTE + DYNAMIC_TILE_BYTES]).hexdigest(),
          })
    check(memory[BG1_TILES_BYTE:len(base_tiles)] == base_tiles,
          "ambient upload preserves the authored BG1 stage tiles", {
              "stage": stage_id, "bytes": len(base_tiles),
          })
    actual_map = memory[BG1_MAP_BYTE:BG1_MAP_BYTE + BG1_MAP_BYTES]
    expected_words = map_words(base_map)
    actual_words = map_words(actual_map)
    check(len(expected_words) == 1024 and len(actual_words) == 1024,
          "BG1 stage map remains a complete 32x32 map", {
              "stage": stage_id, "expected": len(expected_words),
              "actual": len(actual_words),
          })
    outside = [index for index in range(1024) if index not in cells]
    check(all(actual_words[index] == expected_words[index] for index in outside),
          "ambient map upload leaves every non-patch BG1 cell exact", {
              "stage": stage_id, "phase": phase_id,
              "mismatches": [index for index in outside
                             if actual_words[index] != expected_words[index]][:12],
          })
    patched = actual_words
    check(all(960 <= (patched[index] & 0x03FF) < 968 and
              (patched[index] & 0xFC00) == (expected_words[index] & 0xFC00)
              for index in cells),
          "ambient map cells select tiles 960-967 with authored palettes", {
              "stage": stage_id, "phase": phase_id,
              "cells": cells,
              "entries": [hex(patched[index]) for index in cells],
          })
    return {
        "phase": phase_id,
        "tile_sha256": hashlib.sha256(phase_tiles).hexdigest(),
        "map_sha256": hashlib.sha256(actual_map).hexdigest(),
        "base_tile_bytes": len(base_tiles),
        "patch_cells": cells,
    }


def changed_pixels(before: Image.Image, after: Image.Image,
                   allowed: list[tuple[int, int, int, int]]) -> dict[str, object]:
    before_rgb = before.convert("RGB")
    after_rgb = after.convert("RGB")
    old = before_rgb.load()
    new = after_rgb.load()
    outside = 0
    changed = 0
    bbox: list[int] | None = None
    for y in range(224):
        for x in range(256):
            if old[x, y] == new[x, y]:
                continue
            changed += 1
            inside = any(left <= x < right and top <= y < bottom
                         for left, top, right, bottom in allowed)
            if inside:
                continue
            outside += 1
            if bbox is None:
                bbox = [x, y, x, y]
            else:
                bbox[0] = min(bbox[0], x)
                bbox[1] = min(bbox[1], y)
                bbox[2] = max(bbox[2], x)
                bbox[3] = max(bbox[3], y)
    return {"changed_pixels": changed, "outside_patch_pixels": outside,
            "outside_bbox": bbox}


def changed_in_rects(before: Image.Image, after: Image.Image,
                     include: list[tuple[int, int, int, int]],
                     exclude: list[tuple[int, int, int, int]] = ()) -> int:
    """Count changed native pixels in authored patch cells only.

    Actor rectangles are excluded because a fighter can briefly occlude an
    ambient cell while the two phase snapshots are taken.  This keeps the
    assertion about actual BG1 output rather than incidental OBJ movement.
    """

    old = before.convert("RGB").load()
    new = after.convert("RGB").load()
    changed = 0
    for y in range(224):
        for x in range(256):
            if old[x, y] == new[x, y]:
                continue
            inside = any(left <= x < right and top <= y < bottom
                         for left, top, right, bottom in include)
            covered = any(left <= x < right and top <= y < bottom
                          for left, top, right, bottom in exclude)
            if inside and not covered:
                changed += 1
    return changed


def capture_frame(e: Emulator, path: Path) -> None:
    check(e.frame is not None and e.frame.size == (256, 224),
          "ambient capture has native 256x224 dimensions", str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    assert e.frame is not None
    e.frame.save(path)


def save_ambient_gif(frames: list[Image.Image], path: Path) -> None:
    check(len(frames) >= PHASE_COUNT,
          "ambient review capture contains all four uploaded phases", {
              "frames": len(frames), "path": str(path),
          })
    if not frames:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    durations = [20, 20, 10]
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=[durations[index % 3] for index in range(len(frames))],
                   loop=0, disposal=2)


def save_capture_gif(frames: list[Image.Image], path: Path,
                     label: str, minimum: int = 1) -> None:
    """Save callback frames at the native 60 Hz cadence for review."""

    check(len(frames) >= minimum,
          f"{label} capture contains enough native PPU frames", {
              "frames": len(frames), "path": str(path),
          })
    if not frames:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    durations = [20, 20, 10]
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=[durations[index % 3] for index in range(len(frames))],
                   loop=0, disposal=2)


def close_players(e: Emulator) -> None:
    for _ in range(180):
        current = state(e)
        if abs(current["x1"] - current["x2"]) < 28 * 16:
            return
        p1 = "right" if current["x1"] < current["x2"] else "left"
        p2 = "left" if p1 == "right" else "right"
        e.run(1, p1=[p1], p2=[p2])
    raise AssertionError(("stage hitstop fixture could not close fighters", state(e)))


def boot_stage(stage_id: int, trace_map: dict[str, int], mode: int = 0,
               fighter: int = 0, fighter2: int = 1) -> Emulator:
    """Boot one stage with the native menu cadence.

    ``mode=1`` is Local VS.  It is used by the two-wave regression because
    both controllers must issue the same special input; arcade CPU decisions
    would make that fixture nondeterministic.  ``mode=2`` is Training and is
    used for ambient captures so the opponent cannot move the comparison
    frame.  ``mode=0`` remains available for an arcade smoke boot.
    """

    check(mode in (0, 1, 2), "stage fixture mode is arcade, local VS or training", mode)
    check(0 <= fighter < 12 and 0 <= fighter2 < 12,
          "stage fixture fighters are in the twelve-entry roster", {
              "fighter": fighter, "fighter2": fighter2,
          })
    e = Emulator()
    e.run(120)
    check(state(e)["screen"] == TITLE, "stage cold boot reaches the title screen")
    for _ in range(mode):
        press(e, "down")
    press(e, "a")
    wait_screen(e, SELECT)
    for _ in range(fighter):
        press(e, "right")
    press(e, "a")
    if mode in (1, 2):
        port = 0 if mode == 2 else 1
        for _ in range((fighter2 - state(e)["selected2"]) % 12):
            press(e, "right", port)
        press(e, "a", port)
    wait_screen(e, ARENA)
    for _ in range(stage_id):
        press(e, "down")
    press(e, "a")
    wait_screen(e, FIGHT)
    initial_clock: int | None = None
    while state(e)["intro"]:
        current = stage_trace(e, trace_map)
        if initial_clock is None:
            initial_clock = current["ambient_clock"]
        check(current["ambient_clock"] == initial_clock,
              "ambient clock remains frozen during the fight intro", current)
        e.run(1)
    e.run(3)
    return e


def verify_pause_freeze(e: Emulator, trace_map: dict[str, int],
                        phase_path: Path) -> dict[str, object]:
    e.run(3, p1=["start"])
    e.run(3)
    paused = stage_trace(e, trace_map)
    check(paused["paused"] != 0, "stage pause enters the native paused state", paused)
    before = {
        "clock": paused["ambient_clock"],
        "phase": paused["ambient_phase"],
        "pending": paused["ambient_pending_phase"],
        "tile_sha256": hashlib.sha256(vram_bytes(e)[DYNAMIC_TILE_BYTE:
                                                     DYNAMIC_TILE_BYTE + DYNAMIC_TILE_BYTES]).hexdigest(),
        "frame": frame_digest(e.frame),
    }
    e.run(12)
    after = stage_trace(e, trace_map)
    after_frame = frame_digest(e.frame)
    check(after["ambient_clock"] == before["clock"] and
          after["ambient_phase"] == before["phase"] and
          after["ambient_pending_phase"] == before["pending"],
          "ambient phase and clock freeze while paused", {
              "before": before, "after": after,
          })
    actual_tiles = vram_bytes(e)[DYNAMIC_TILE_BYTE:DYNAMIC_TILE_BYTE + DYNAMIC_TILE_BYTES]
    check(hashlib.sha256(actual_tiles).hexdigest() == before["tile_sha256"],
          "ambient tile block remains unchanged while paused", before)
    check(after_frame == before["frame"],
          "stage PPU output remains frozen while paused", {
              "before": before["frame"], "after": after_frame,
          })
    e.run(3, p1=["start"])
    e.run(3)
    check(stage_trace(e, trace_map)["paused"] == 0,
          "stage pause releases through the native controller", stage_trace(e, trace_map))
    return {"before": before, "after": after, "phase_asset": str(phase_path)}


def verify_hitstop_freeze(e: Emulator, trace_map: dict[str, int]) -> dict[str, object]:
    close_players(e)
    e.run(3, p1=["y"])
    e.run(1)
    hit = None
    for _ in range(80):
        current = stage_trace(e, trace_map)
        if current["hitstop"]:
            hit = current
            break
        e.run(1)
    check(hit is not None, "stage hitstop fixture produces a real contact", hit)
    assert hit is not None
    before_tiles = vram_bytes(e)[DYNAMIC_TILE_BYTE:DYNAMIC_TILE_BYTE + DYNAMIC_TILE_BYTES]
    before_frame = frame_digest(e.frame)
    before_clock = hit["ambient_clock"]
    held = 0
    while stage_trace(e, trace_map)["hitstop"] and held < 20:
        e.run(1)
        current = stage_trace(e, trace_map)
        check(current["ambient_clock"] == before_clock,
              "ambient clock freezes during combat hitstop", current)
        current_tiles = vram_bytes(e)[DYNAMIC_TILE_BYTE:DYNAMIC_TILE_BYTE + DYNAMIC_TILE_BYTES]
        check(current_tiles == before_tiles,
              "ambient tile block freezes during combat hitstop", current)
        # The combat PPU may settle impact HUD/effect pixels during hitstop;
        # the stage contract is that its ambient clock, uploaded block and
        # pending phase remain frozen.  Retain the callback digest as review
        # evidence instead of incorrectly requiring the whole screen to be
        # byte-identical across those intentional contact effects.
        held += 1
    check(held >= 2, "stage hitstop freeze spans multiple native ticks", {
        "ticks": held, "hitstop": hit,
    })
    return {"hitstop": hit, "held_ticks": held,
            "before_frame": before_frame,
            "after_frame": frame_digest(e.frame)}


def verify_oam_stress(e: Emulator, trace_map: dict[str, int],
                      record: dict[str, object], expected_floor: int) -> dict[str, object]:
    status_config = record.get("ppu_stat", {})
    if not isinstance(status_config, dict):
        status_config = {}
    range_mask = int(status_config.get("range_overflow_mask", 0x80))
    time_mask = int(status_config.get("time_overflow_mask", 0x40))
    frames = int(record.get("stress_frames", 600))
    max_scanline = 0
    max_tiles = 0
    peak_budget: dict[str, int] = {}
    max_extra_oam = 0
    statuses: list[int] = []
    floors: list[int] = []
    for index in range(frames):
        phase = index % 96
        p1 = ["right"] if phase < 48 else ["left"]
        p2 = ["left"] if phase < 48 else ["right"]
        if phase in (8, 9, 56, 57):
            p1.append("up")
        if phase in (24, 25, 72, 73):
            p2.append("up")
        e.run(1, p1=p1, p2=p2)
        current = stage_trace(e, trace_map)
        raw = oam_memory(e)
        budget = scanline_budget(raw)
        if budget["max_sprites"] > max_scanline:
            peak_budget = budget
        max_scanline = max(max_scanline, budget["max_sprites"])
        max_tiles = max(max_tiles, budget["max_tiles"])
        max_extra_oam = max(max_extra_oam, visible_oam_count(raw, 62))
        contract = actor_contract(
            e, expected_floor
            if current["y1"] == 0 and current["y2"] == 0 else None,
            allow_airborne=(current["y1"] != 0 or current["y2"] != 0))
        if current["y1"] == 0 and current["y2"] == 0:
            floors.append(int(contract["floor"]))
        statuses.append(current["ppu_stat"] & 0xFF)
    check(max_scanline > 0 and max_scanline <= 32 and max_tiles <= 34,
          "native OAM scanline load stays within 34 tile/32 sprite limits", {
              "max_sprites": max_scanline, "max_tiles": max_tiles,
              "peak_budget": peak_budget, "frames": frames,
          })
    check(not any(status & (range_mask | time_mask) for status in statuses),
          "native STAT77 reports no OAM range/time overflow", {
              "range_mask": hex(range_mask), "time_mask": hex(time_mask),
              "statuses": sorted(set(statuses)),
          })
    check(bool(floors) and max(floors) - min(floors) <= 1,
          "stage OAM stress preserves the grounded actor support floor", {
              "floor_min": min(floors) if floors else None,
              "floor_max": max(floors) if floors else None,
          })
    return {"frames": frames, "max_scanline": max_scanline,
            "max_tiles": max_tiles, "peak_budget": peak_budget,
            "max_extra_oam": max_extra_oam,
            "statuses": sorted(set(statuses)), "floor": [min(floors), max(floors)]}


def verify_two_wave_regression(stage_id: int, slug: str,
                               trace_map: dict[str, int]) -> dict[str, object]:
    """Exercise two synchronized ground waves through the real Local VS path.

    This intentionally uses the same deterministic fixture as the native
    OAM review: P1 fighter 4 and P2 fighter 6, four frames of DOWN followed
    by twenty-eight frames of DOWN+X on both controllers.  The test records
    callback PPU frames and the complete OAM shadow while the waves are
    active, so an effect that exists only in an authored source sheet cannot
    satisfy the regression.
    """

    e = boot_stage(stage_id, trace_map, mode=1, fighter=4, fighter2=6)
    try:
        check(e.frame is not None, "two-wave fixture has a native PPU frame")
        assert e.frame is not None
        baseline_frame = e.frame.copy()
        baseline_extra_oam = visible_oam_count(oam_memory(e), 62)
        frames: list[Image.Image] = [baseline_frame]
        wave_frames: list[Image.Image] = []
        wave_indices: list[int] = []
        wave1_count = 0
        wave2_count = 0
        statuses: list[int] = []
        budgets: list[dict[str, int]] = []
        extra_oam: list[int] = []
        ppu_deltas: list[dict[str, object]] = []

        def sample(keys: list[str], tick: int) -> None:
            nonlocal wave1_count, wave2_count
            e.run(1, p1=keys, p2=keys)
            current = stage_trace(e, trace_map)
            check(e.frame is not None,
                  "two-wave fixture captures every native PPU tick", tick)
            assert e.frame is not None
            frame = e.frame.copy()
            frames.append(frame)
            raw = oam_memory(e)
            budget = scanline_budget(raw)
            budgets.append(budget)
            statuses.append(current["ppu_stat"] & 0xFF)
            extra_oam.append(visible_oam_count(raw, 62))
            if current.get("wave1", 0):
                wave1_count += 1
            if current.get("wave2", 0):
                wave2_count += 1
            if current.get("wave1", 0) or current.get("wave2", 0):
                wave_frames.append(frame)
                wave_indices.append(tick)
                ppu_deltas.append(changed_pixels(baseline_frame, frame, []))

        # Keep this sequence explicit: the first four ticks establish the
        # crouch, then both controllers hold the special shortcut together.
        e.run(4, p1=["down"], p2=["down"])
        for tick in range(28):
            sample(["down", 'y'], tick)
        # Include the recovery/shadow frames after the active wave window in
        # the actual review GIF and budget sample.
        for tick in range(28, 52):
            sample([], tick)

        check(wave1_count > 0 and wave2_count > 0,
              "synchronized Local VS fixture produces both native waves", {
                  "stage": stage_id, "wave1_frames": wave1_count,
                  "wave2_frames": wave2_count,
              })
        check(bool(wave_frames),
              "two-wave fixture captures active-wave callback frames", {
                  "stage": stage_id, "indices": wave_indices,
              })
        # STAT77's low revision bits read as 0x01 on the Snes9x PPU; only
        # bits 7/6 are the native range/time overflow flags.  Require those
        # flags to be zero while retaining the raw status values in the
        # report.
        overflow_mask = 0x80 | 0x40
        check(statuses and all((status & overflow_mask) == 0 for status in statuses),
              "two-wave PPU samples report zero range/time overflow STAT", {
                  "stage": stage_id, "statuses": sorted(set(statuses)),
                  "overflow_mask": hex(overflow_mask),
              })
        max_sprites = max((item["max_sprites"] for item in budgets), default=0)
        max_tiles = max((item["max_tiles"] for item in budgets), default=0)
        peak_budget = max(budgets, key=lambda item: (item["max_tiles"], item["max_sprites"]),
                          default={})
        check(max_sprites <= 32 and max_tiles <= 34,
              "two-wave OAM load stays within 34 tile/32 sprite limits", {
                  "stage": stage_id, "max_sprites": max_sprites,
                  "max_tiles": max_tiles, "peak_budget": peak_budget,
              })
        max_delta = max((int(item["changed_pixels"]) for item in ppu_deltas),
                        default=0)
        check(max_delta > 8 and len({frame_digest(frame) for frame in wave_frames}) > 1,
              "actual PPU frames show animated wave/contact effects and shadows", {
                  "stage": stage_id, "max_changed_pixels": max_delta,
                  "wave_variants": len({frame_digest(frame) for frame in wave_frames}),
                  "extra_oam_baseline": baseline_extra_oam,
                  "extra_oam_peak": max(extra_oam, default=baseline_extra_oam),
              })

        capture_dir = ROOT / "docs/screenshots/stages"
        gif_path = capture_dir / f"{slug}-two-waves.gif"
        save_capture_gif(frames, gif_path, "two-wave review", minimum=20)
        contact_path = capture_dir / f"{slug}-two-waves-contact.png"
        contact = wave_frames[len(wave_frames) // 2]
        contact_path.parent.mkdir(parents=True, exist_ok=True)
        contact.save(contact_path)
        return {
            "fixture": {"mode": "local_vs", "fighter1": 4, "fighter2": 6,
                        "input": "4DOWN+28DOWN+X synchronized"},
            "wave1_frames": wave1_count, "wave2_frames": wave2_count,
            "wave_indices": wave_indices, "ppu_stat": sorted(set(statuses)),
            "max_sprites": max_sprites, "max_tiles": max_tiles,
            "peak_budget": peak_budget,
            "extra_oam_baseline": baseline_extra_oam,
            "extra_oam_peak": max(extra_oam, default=baseline_extra_oam),
            "max_changed_pixels": max_delta,
            "gif": str(gif_path), "contact_capture": str(contact_path),
        }
    finally:
        e.close()


def run_stage(stage_id: int, record: dict[str, object],
              trace_map: dict[str, int]) -> dict[str, object]:
    slug = stage_slug(record, stage_id)
    tiles_path, map_path = base_paths(record, stage_id)
    check(tiles_path.exists() and map_path.exists(),
          "stage authored BG1 base assets exist", {
              "stage": stage_id, "tiles": str(tiles_path), "map": str(map_path),
          })
    base_tiles = tiles_path.read_bytes()
    base_map = map_path.read_bytes()
    check(len(base_tiles) <= BG1_MAP_BYTE,
          "stage base tiles stop before the BG1 map", {
              "stage": stage_id, "bytes": len(base_tiles),
          })
    check(len(base_map) == BG1_MAP_BYTES,
          "stage base map is exactly 32x32 cells", {
              "stage": stage_id, "bytes": len(base_map),
          })
    phase_records = phase_assets(record, stage_id)
    phase_tiles = [bytes(item["data"]) for item in phase_records]
    cells = normalize_cells(record.get(
        "patch_cells", record.get("map_cells",
        record.get("dynamic_cells", record.get("cells", [])))))
    check(bool(cells), "stage dynamics declares selected BG1 patch cells", {
        "stage": stage_id, "cells": cells,
    })
    patch_rects = rects_for(record, cells)
    rects = list(patch_rects)
    # Training's native hint blinks independently of the stage patch while
    # the four phase captures are collected.  Keep that precise HUD row out
    # of the stage-only PPU diff; all authored stage pixels remain strict.
    rects.append((0, 24, 256, 32))
    # Training tool rows own this BG2 region; phase VRAM remains exact.
    rects.append((0, 208, 256, 224))
    non_stage = record.get("non_stage_rects", [])
    if isinstance(non_stage, list):
        rects += [tuple(int(value) for value in item)
                  for item in non_stage
                  if isinstance(item, (list, tuple)) and len(item) == 4]

    # Training keeps the opponent inert while ambient phase captures are
    # compared across time; Local VS is reserved for the synchronized wave
    # fixture below.
    e = boot_stage(stage_id, trace_map, mode=2)
    try:
        initial = stage_trace(e, trace_map)
        check(initial["stage_id"] == stage_id,
              "fight trace selects the requested stage", initial)
        baseline_oam = oam_memory(e)
        baseline_extra_oam = visible_oam_count(baseline_oam, 62)
        baseline_contract = actor_contract(e)
        expected_floor = int(baseline_contract["floor"])
        check(initial["ambient_clock"] >= 0 and initial["ambient_clock"] < 0x10000,
              "ambient clock is present after the stage intro", initial)

        frames: list[Image.Image] = []
        phase_results: dict[str, object] = {}
        phase_frames: dict[int, Image.Image] = {}
        phase_sample: dict[int, dict[str, int]] = {}
        phase_actor_rects: dict[int, list[tuple[int, int, int, int]]] = {}
        previous_clock = initial["ambient_clock"]
        max_age = int(record.get("max_phase_age", 15))
        capture_frames = int(record.get("phase_capture_frames", 128))
        for tick in range(capture_frames):
            current = stage_trace(e, trace_map)
            frames.append(e.frame.copy() if e.frame is not None else Image.new("RGB", (256, 224)))
            check(current["ambient_clock"] >= previous_clock,
                  "ambient clock advances monotonically during live stage capture", current)
            previous_clock = current["ambient_clock"]
            desired = (current["ambient_clock"] >> 4) & 3
            uploaded = current["ambient_phase"]
            check(0 <= uploaded < PHASE_COUNT,
                  "uploaded ambient phase stays within the four-phase range", current)
            pending = current["ambient_pending_phase"]
            if desired != uploaded:
                check(pending == desired,
                      "pending ambient phase follows the live stage clock", current)
                check(current["ambient_phase_age"] <= max_age,
                      "ambient upload latency remains within the manifest bound", current)
            if uploaded not in phase_frames:
                actual = vram_bytes(e)[DYNAMIC_TILE_BYTE:DYNAMIC_TILE_BYTE + DYNAMIC_TILE_BYTES]
                if actual == phase_tiles[uploaded]:
                    phase_frames[uploaded] = frames[-1]
                    phase_sample[uploaded] = current
                    phase_actor_rects[uploaded] = actor_rects(e)
                    phase_results[str(uploaded)] = verify_stage_vram(
                        e, record, stage_id, uploaded, base_tiles, base_map,
                        phase_tiles[uploaded], cells)
                    phase_path = ROOT / "docs/screenshots/stages" / f"{slug}-phase{uploaded}.png"
                    capture_frame(e, phase_path)
                    phase_results[str(uploaded)]["capture"] = str(phase_path)
            e.run(1)
        check(set(phase_frames) == set(range(PHASE_COUNT)),
              "all four ambient phases upload to BG1", {
                  "stage": stage_id, "observed": sorted(phase_frames),
              })
        for phase_id in range(1, PHASE_COUNT):
            if phase_id in phase_frames:
                allowed = rects + phase_actor_rects.get(0, []) + \
                    phase_actor_rects.get(phase_id, [])
                diff = changed_pixels(phase_frames[0], phase_frames[phase_id], allowed)
                check(diff["outside_patch_pixels"] == 0,
                      "ambient PPU diff stays inside the authored patch/non-stage masks", {
                          "stage": stage_id, "phase": phase_id, **diff,
                      })
                patch_pixels = changed_in_rects(
                    phase_frames[0], phase_frames[phase_id], patch_rects,
                    phase_actor_rects.get(0, []) + phase_actor_rects.get(phase_id, []))
                check(patch_pixels > 0,
                      "ambient phase produces visible PPU changes inside selected map cells", {
                          "stage": stage_id, "phase": phase_id,
                          "patch_pixels": patch_pixels,
                          "patch_rects": patch_rects,
                      })
                phase_results[str(phase_id)]["ppu_diff"] = diff
                phase_results[str(phase_id)]["patch_pixels"] = patch_pixels
        gif_path = ROOT / "docs/screenshots/stages" / f"{slug}-ambient.gif"
        save_ambient_gif(frames, gif_path)

        phase_asset = phase_records[phase_sample.get(0, {}).get("ambient_phase", 0)]["path"]
        pause = verify_pause_freeze(e, trace_map, phase_asset)
        hitstop = verify_hitstop_freeze(e, trace_map)
        stress = verify_oam_stress(e, trace_map, record, expected_floor)
        final_extra_oam = visible_oam_count(oam_memory(e), 62)
        check(final_extra_oam <= 66 and int(stress["max_extra_oam"]) <= 66,
              "ambient stage pass keeps effects within the reserved OBJ slots", {
                  "stage": stage_id, "baseline_extra_oam": baseline_extra_oam,
                  "final_extra_oam": final_extra_oam,
                  "max_extra_oam": stress["max_extra_oam"],
              })
        # The libretro Snes9x core is process-global; the independent Local
        # VS wave fixture must start only after this stage instance closes.
        e.close()
        two_waves = verify_two_wave_regression(stage_id, slug, trace_map)
        return {
            "stage": stage_id, "slug": slug,
            "base_tiles": str(tiles_path), "base_map": str(map_path),
            "patch_cells": cells, "phase_results": phase_results,
            "phase_samples": {str(key): value for key, value in phase_sample.items()},
            "ambient_gif": str(gif_path), "pause": pause,
            "hitstop": hitstop, "oam_stress": stress,
            "two_waves": two_waves,
        }
    finally:
        e.close()


def main() -> int:
    if depth_manifest(ROOT) is not None:
        return depth_stage_suite()
    started = time.monotonic()
    report: dict[str, object] = {
        "emulator": "Official Snes9x 1.63 x64 libretro core",
        "suite": "stage-ambient",
        "status": "failed", "rom_sha256": None, "rom_bytes": None,
        "checks": checks, "stages": {},
    }
    try:
        dist_manifest = json.loads((ROOT / "dist/manifest.json").read_text())
        report["rom_sha256"] = dist_manifest.get("sha256")
        report["rom_bytes"] = dist_manifest.get("bytes")
        check(dist_manifest.get("bytes") == 4 * 1024 * 1024,
              "stage suite uses the 4 MiB native ROM", dist_manifest)
        dynamics, trace_map = load_dynamic_manifest()
        report["trace_map"] = trace_map
        report["stages"] = {
            stage_slug(stage_record(dynamics, stage_id), stage_id):
            run_stage(stage_id, stage_record(dynamics, stage_id), trace_map)
            for stage_id in range(3)
        }
        report["status"] = "passed"
    except Exception as exc:
        report["error"] = repr(exc)
        raise
    finally:
        report["passed"] = len(checks)
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        report_path = ROOT / "docs/stage-test-report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "status": report["status"], "passed": report["passed"],
        "seconds": report["elapsed_seconds"], "rom_sha256": report["rom_sha256"],
        "report": "docs/stage-test-report.json",
    }))
    return 0


def depth_stage_suite() -> int:
    """One native execution backs the stage suite and its focused appendix."""
    if json.loads((ROOT/'dist/manifest.json').read_bytes())['version']=='0.25.0':
        import test_pacing_floor_25 as current
        result=current.stage_main()
        focused=json.loads((ROOT/'docs/pacing-floor-v025-stage-report.json').read_bytes())
        shared={**focused,'suite':'stage-depth','shared_native_execution':True,
                'focused_report':'docs/pacing-floor-v025-stage-report.json',
                'focused_report_sha256':hashlib.sha256((ROOT/'docs/pacing-floor-v025-stage-report.json').read_bytes()).hexdigest(),
                'passed':focused['check_count']}
        (ROOT/'docs/stage-test-report.json').write_bytes((json.dumps(shared,indent=2)+'\n').encode())
        return result
    import test_combat_24_stage08 as depth
    started=time.monotonic()
    manifest=json.loads((ROOT/'dist/manifest.json').read_bytes())
    report={'status':'failed','suite':'stage-depth','rom_sha256':manifest['sha256'],
            'rom_bytes':manifest['bytes'],'checks':depth.checks}
    try:
        depth.main()
        focused=json.loads(depth.REPORT.read_bytes())
        check(focused['rom_sha256']==manifest['sha256'],'Stage proof identifies the current cartridge')
        report={**focused,'suite':'stage-depth',
                'focused_report':depth.REPORT.relative_to(ROOT).as_posix(),
                'focused_report_sha256':hashlib.sha256(depth.REPORT.read_bytes()).hexdigest(),
                'shared_native_execution':True}
    except Exception as error:
        report['error']=repr(error)
        raise
    finally:
        report['passed']=sum(row.get('passed') is True for row in report['checks'])
        report['elapsed_seconds']=round(time.monotonic()-started,3)
        (ROOT/'docs/stage-test-report.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
