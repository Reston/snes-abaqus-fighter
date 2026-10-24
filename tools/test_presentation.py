"""Silent, headless presentation checks for the native menus and arenas.

This suite drives the actual cartridge through the official Snes9x libretro
core.  It checks title/select/arena state transitions, the four-by-three roster
navigation contract, selected portrait updates, and all three fight stages.
Frames are captured from the core's video callback for human review; no window
or audio device is opened and the host never writes emulated memory.

Run after the 4 MiB 64-frame animation native build with::

    python tools/test_presentation.py
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


TITLE, SELECT, ARENA, FIGHT = 0, 1, 2, 3
NAMES = (
    "DAMIAN", "IVO", "CRISTOBAL", "COTE", "NEGGER", "DAVID",
    "FERNANDO", "CRISTIAN", "MAMARIAGA", "RESTON", "ROXANA", "LARS",
)
STAGES = ("las-condes", "el-castillo", "la-oficina")
PORTRAIT_VRAM_WORD = 0x4A00
PORTRAIT_VRAM_BYTE = PORTRAIT_VRAM_WORD * 2
PORTRAIT_BYTES = 64 * 80 // 2
BG2_MAP_WORD = 0x5800
BG2_MAP_BYTE = BG2_MAP_WORD * 2
PORTRAIT_MAP_X = 23
PORTRAIT_MAP_Y = 6
PORTRAIT_TILE_BASE = 160
PORTRAIT_MAP_PALETTE = 1
UI_TILE_VRAM_WORD = 0x4000
UI_TILE_VRAM_BYTE = UI_TILE_VRAM_WORD * 2
OPAQUE_FONT_BASE = 256
TRANSPARENT_FONT_MAX = 127
ARENA_ROW_X = 8
ARENA_ROW_Y = 40
ARENA_ROW_W = 240
ARENA_ROW_H = 56
ARENA_THUMB_X = 18
ARENA_THUMB_Y_INSET = 2
ARENA_THUMB_W = 104
ARENA_THUMB_H = 52
checks: list[dict[str, object]] = []


def check(ok: bool, label: str, details: object | None = None) -> None:
    if not ok:
        raise AssertionError((label, details))
    checks.append({"check": label, "passed": True, "details": details})


def state(e: Emulator) -> dict[str, int]:
    return e.state()


def press(e: Emulator, key: str, port: int = 0) -> None:
    e.tap(key, port)
    e.run(20)


def wait_screen(e: Emulator, wanted: int, max_frames: int = 600) -> None:
    for _ in range(max_frames // 10):
        if state(e)["screen"] == wanted:
            e.run(10)
            return
        e.run(10)
    raise AssertionError(("screen did not arrive", wanted, state(e)))


def frame_digest(e: Emulator) -> str:
    check(e.frame is not None, "video callback produced a native frame")
    return hashlib.sha256(e.frame.tobytes()).hexdigest()


def capture(e: Emulator, name: str) -> Path:
    check(e.frame is not None, "capture has a native video frame", name)
    check(e.frame.size == (256, 224), "capture uses the SNES 256x224 frame", {
        "name": name, "size": e.frame.size,
    })
    check(len(e.frame.getcolors(256 * 224) or []) > 12,
          "capture is a populated presentation frame", name)
    path = ROOT / "docs/screenshots/presentation" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    e.frame.save(path)
    return path


def vram_bytes(e: Emulator) -> bytes:
    """Read the core's VRAM callback without modifying emulated memory."""

    pointer = e.core.retro_get_memory_data(3)
    size = e.core.retro_get_memory_size(3)
    return C.string_at(pointer, size)


def verify_animation_artifact() -> dict[str, object]:
    """Keep presentation captures tied to the current 64-frame art package."""

    path = ROOT / "assets/generated/character-manifest.json"
    entries = json.loads(path.read_text())
    check(len(entries) == 12, "presentation build keeps twelve fighter manifests", {
        "count": len(entries),
    })
    proof: list[dict[str, object]] = []
    for fighter, entry in enumerate(entries):
        check(int(entry.get("frame_count", 0)) == 64,
              "presentation package records 64 fighter frames", {
                  "fighter": fighter, "frame_count": entry.get("frame_count"),
              })
        framing = entry.get("portrait_framing")
        check(isinstance(framing, dict),
              "presentation manifest records portrait framing metadata", {
                  "fighter": fighter, "has_framing": isinstance(framing, dict),
              })
        if isinstance(framing, dict):
            check(framing.get("head_clipped") is False and
                  framing.get("shared_composition") is True,
                  "portrait framing keeps the complete shared head composition", {
                      "fighter": fighter,
                      "head_clipped": framing.get("head_clipped"),
                      "shared_composition": framing.get("shared_composition"),
                  })
            check(framing.get("target_sizes") == [[32, 40], [64, 80]],
                  "portrait framing records both native target sizes", {
                      "fighter": fighter, "target_sizes": framing.get("target_sizes"),
                  })
            for key in ("crop_box", "head_anchor_box", "render"):
                check(key in framing, "portrait framing includes " + key, {
                    "fighter": fighter, "key": key,
                })
        preview = ROOT / "assets/generated" / f"fighter{fighter:02}.png"
        check(preview.exists(), "presentation package includes fighter preview", {
            "fighter": fighter, "path": str(preview),
        })
        if preview.exists():
            image = Image.open(preview)
            check(image.mode == "RGBA" and image.size == (6144, 80),
                  "presentation package uses the 64-frame native preview strip", {
                      "fighter": fighter, "mode": image.mode, "size": image.size,
                  })
        proof.append({"fighter": fighter, "frame_count": entry.get("frame_count"),
                      "preview": str(preview), "portrait_framing": framing})
    return {"fighters": proof, "frame_count": 64}


def ui_row(e: Emulator, row: int) -> list[int]:
    """Decode one BG2 interface tile-map row from native VRAM."""

    memory = vram_bytes(e)
    offset = BG2_MAP_BYTE + row * 32 * 2
    return [int.from_bytes(memory[offset + x * 2:offset + x * 2 + 2], "little")
            for x in range(32)]


def map_row(memory: bytes, row: int) -> list[int]:
    """Decode one BG2 map row from an already captured VRAM image."""

    offset = BG2_MAP_BYTE + row * 32 * 2
    return [int.from_bytes(memory[offset + x * 2:offset + x * 2 + 2], "little")
            for x in range(32)]


def map_tile(memory: bytes, x: int, y: int) -> int:
    return int.from_bytes(memory[BG2_MAP_BYTE + (y * 32 + x) * 2:
                                 BG2_MAP_BYTE + (y * 32 + x + 1) * 2],
                          "little")


def snes_rgb(value: int) -> tuple[int, int, int]:
    """Convert a BGR555 color using the same expansion as libretro video."""

    def channel(shift: int) -> int:
        component = (value >> shift) & 0x1F
        return (component << 3) | (component >> 2)

    return channel(0), channel(5), channel(10)


def _tile_indices(tile_data: bytes) -> list[int]:
    """Decode one already-sized SNES 4bpp tile."""

    indices: list[int] = []
    for y in range(8):
        planes = (
            tile_data[y * 2], tile_data[y * 2 + 1],
            tile_data[16 + y * 2], tile_data[16 + y * 2 + 1],
        )
        for x in range(8):
            bit = 7 - x
            indices.append(sum(((planes[plane] >> bit) & 1) << plane
                               for plane in range(4)))
    return indices


def tile_indices(tile_data: bytes) -> list[int]:
    """Decode one SNES 4bpp tile into its 64 palette indices."""

    check(len(tile_data) == 32, "UI 4bpp tile has 32 native bytes", len(tile_data))
    return _tile_indices(tile_data)


def decode_tile_block(tile_data: bytes, palette: bytes,
                      width_tiles: int, height_tiles: int) -> Image.Image:
    """Decode a native 4bpp tile block with its exact SNES palette.

    The portrait DMA uses a fighter-specific palette at CGRAM 16, so it must
    be decoded independently of ``ui_pal.bin``.  This also gives the rendered
    PPU crop a source-actual RGB reference instead of comparing it to the
    pre-quantized PNG preview.
    """

    expected_bytes = width_tiles * height_tiles * 32
    check(len(tile_data) == expected_bytes,
          "native portrait tile block has the expected byte count", {
              "bytes": len(tile_data), "expected": expected_bytes,
          })
    check(len(palette) >= 32,
          "native portrait palette contains sixteen colors", len(palette))
    colors = [snes_rgb(int.from_bytes(palette[i:i + 2], "little"))
              for i in range(0, 32, 2)]
    image = Image.new("RGB", (width_tiles * 8, height_tiles * 8))
    # Tiles are row-major in the generated block.  Build scanlines explicitly
    # because PIL's flat buffer is pixel-major rather than tile-major.
    rows: list[tuple[int, int, int]] = []
    for y in range(height_tiles * 8):
        tile_y, inner_y = divmod(y, 8)
        for tile_x in range(width_tiles):
            tile_number = tile_y * width_tiles + tile_x
            tile = tile_data[tile_number * 32:(tile_number + 1) * 32]
            indices = _tile_indices(tile)
            row_start = inner_y * 8
            rows.extend(colors[index] for index in
                        indices[row_start:row_start + 8])
    image.putdata(rows)
    return image


def tile_rgb(tile_data: bytes, palette: bytes) -> Image.Image:
    """Decode a UI tile to RGB for a source-actual PPU crop comparison."""

    check(len(palette) >= 32, "UI palette contains the first 16 colors", len(palette))
    colors = [snes_rgb(int.from_bytes(palette[i:i + 2], "little"))
              for i in range(0, 32, 2)]
    image = Image.new("RGB", (8, 8))
    image.putdata([colors[index] for index in tile_indices(tile_data)])
    return image


def image_delta(actual: Image.Image, expected: Image.Image) -> dict[str, float | int]:
    """Return tolerant RGB error metrics without depending on NumPy."""

    check(actual.size == expected.size, "presentation comparison sizes match", {
        "actual": actual.size, "expected": expected.size,
    })
    deltas = [abs(a - b) for ap, ep in zip(actual.convert("RGB").getdata(),
                                            expected.convert("RGB").getdata())
              for a, b in zip(ap, ep)]
    pixel_deltas = [max(abs(a - b) for a, b in zip(ap, ep))
                    for ap, ep in zip(actual.convert("RGB").getdata(),
                                      expected.convert("RGB").getdata())]
    return {
        "mean_channel_delta": sum(deltas) / len(deltas),
        "max_channel_delta": max(deltas, default=0),
        "pixels_over_16": sum(delta > 16 for delta in pixel_deltas),
        "pixels": len(pixel_deltas),
    }


def centered_start(text: str) -> int:
    return (32 - len(text)) // 2


def verify_menu_font_bank(e: Emulator, rows: list[tuple[int, int, str]],
                          label: str) -> None:
    """Menus keep their original transparent ASCII glyph bank (0..127)."""

    memory = vram_bytes(e)
    for row, x, text in rows:
        values = map_row(memory, row)
        for offset, character in enumerate(text):
            tile = values[x + offset] & 0x03FF
            check(tile == ord(character) and tile <= TRANSPARENT_FONT_MAX,
                  "menu text stays in the original ASCII glyph bank", {
                      "label": label, "row": row, "x": x + offset,
                      "character": character, "tile": tile,
                  })


def verify_select_card_render(e: Emulator) -> dict[str, object]:
    """Ensure every 32x40 roster card is rendered at its authored bounds.

    The native VRAM portrait assertion proves the large profile block, while
    this comparison catches a card crop or one-pixel shift that can make a
    head appear cut off even when the source asset is correct.
    """

    expected_path = ROOT / "assets/generated/select.png"
    check(expected_path.exists(), "generated select plate exists", str(expected_path))
    expected_plate = Image.open(expected_path).convert("RGB")
    check(expected_plate.size == (256, 224), "generated select plate is native size",
          expected_plate.size)
    check(e.frame is not None, "select card comparison has a native frame")
    assert e.frame is not None
    metrics: dict[str, object] = {}
    for fighter in range(12):
        col, row = fighter % 4, fighter // 4
        x, y = 8 + col * 40 + 4, 48 + row * 48 + 4
        # Cursor lines are one native pixel at the card's outer boundary
        # (x=8/47, y=48/95); the portrait inset starts four pixels inside, so
        # the full authored 32x40 crop is safe to compare and catches a face
        # or hair edge clipped by a bad portrait composition.
        crop = (x, y, x + 32, y + 40)
        actual = e.frame.crop(crop)
        expected = expected_plate.crop(crop)
        delta = image_delta(actual, expected)
        check(delta["mean_channel_delta"] <= 8.0 and
              delta["pixels_over_16"] <= 32,
              "roster card portrait stays inside its authored crop", {
                  "rect": list(crop),
                  **delta,
              })
        metrics[f"{fighter:02}"] = {"rect": list(crop), **delta}
    return metrics


def verify_fight_font_bank(e: Emulator, current: dict[str, int]) -> dict[str, object]:
    """Verify live HUD strings use opaque glyphs and cannot reveal BG1."""

    p1 = NAMES[current["fighter_id1"]]
    p2 = NAMES[current["fighter_id2"]]
    if current["mode"] == 2:
        versus = "TRAINING"
    elif current["mode"] == 1:
        versus = "P1 VS P2"
    else:
        versus = "P1 VS CPU"
    rows = [
        (0, 1, p1), (0, 20, p2), (1, 15, "KO"),
        (2, 13, "ROUND"), (2, 19, str(current["round"])),
        (4, 12, versus),
    ]
    return verify_opaque_text_rows(e, rows, "live fight")


def verify_round_marker_tiles(e: Emulator) -> None:
    """Keep the two native round-marker glyphs filled on the HUD panel."""

    memory = vram_bytes(e)
    row_two = map_row(memory, 2)
    check(all((row_two[x] & 0x03FF) in (147, 148)
              for x in (1, 2, 29, 30)),
          "HUD round markers retain their native tile IDs", {
              "row2": {str(x): row_two[x] for x in (1, 2, 29, 30)},
          })
    for tile in (147, 148):
        native_tile = memory[UI_TILE_VRAM_BYTE + tile * 32:
                             UI_TILE_VRAM_BYTE + (tile + 1) * 32]
        indices = tile_indices(native_tile)
        check(all(index >= 1 for index in indices),
              "round marker tile has an opaque panel background", {
                  "tile": tile, "min_palette_index": min(indices),
              })


def verify_opaque_text_rows(e: Emulator, rows: list[tuple[int, int, str]],
                            label: str) -> dict[str, object]:
    """Assert map, native tile pixels, and final PPU pixels for UI text.

    Opaque glyph tiles are the project-owned copies at 256..383.  Checking
    both the tile bank and the composed frame makes this regression catch the
    original symptom: transparent ASCII glyphs showed the stage through the
    HUD/result letters.
    """

    memory = vram_bytes(e)
    palette = (ROOT / "assets/generated/ui_pal.bin").read_bytes()
    check(e.frame is not None, "opaque UI text comparison has a native frame", label)
    assert e.frame is not None
    seen: set[int] = set()
    details: list[dict[str, object]] = []
    for row, x, text in rows:
        values = map_row(memory, row)
        for offset, character in enumerate(text):
            cell_x = x + offset
            tile = values[cell_x] & 0x03FF
            expected_tile = OPAQUE_FONT_BASE + ord(character)
            check(tile == expected_tile,
                  "combat/result text uses opaque glyph bank 256..383", {
                      "label": label, "row": row, "x": cell_x,
                      "character": character, "tile": tile,
                      "expected": expected_tile,
                  })
            if tile not in seen:
                seen.add(tile)
                offset_bytes = UI_TILE_VRAM_BYTE + tile * 32
                native_tile = memory[offset_bytes:offset_bytes + 32]
                indices = tile_indices(native_tile)
                check(all(index >= 1 for index in indices),
                      "opaque glyph tile has no transparent palette-zero pixels", {
                          "label": label, "tile": tile,
                          "min_palette_index": min(indices),
                      })
            offset_bytes = UI_TILE_VRAM_BYTE + tile * 32
            palette_index = (values[cell_x] >> 10) & 7
            expected_palette = 1 if label == "live fight" and (row == 0 or (row == 1 and cell_x in (15, 16))) else 0
            # The timer digits are white; the two fighter names and KO use
            # the gold accent bank, whose panel remains fully opaque.
            if row == 0 and cell_x in (15, 16):expected_palette = 0
            check(palette_index == expected_palette,
                  "native HUD/result glyph uses its intended palette", {
                      "label": label, "row": row, "x": cell_x,
                      "actual": palette_index, "expected": expected_palette})
            expected = tile_rgb(memory[offset_bytes:offset_bytes + 32],
                                palette[palette_index * 32:(palette_index + 1) * 32])
            actual = e.frame.crop((cell_x * 8, row * 8,
                                  cell_x * 8 + 8, row * 8 + 8))
            delta = image_delta(actual, expected)
            check(delta["mean_channel_delta"] <= 3.0 and
                  delta["pixels_over_16"] == 0,
                  "opaque UI glyph composes over the panel without stage bleed", {
                      "label": label, "row": row, "x": cell_x,
                      "character": character, "tile": tile, **delta,
                  })
            details.append({"row": row, "x": cell_x,
                            "character": character, "tile": tile, **delta})
    return {"label": label, "tiles": len(seen), "cells": details}


def arcade_copy(name: str) -> list[str]:
    """Authored story copy oracle; native VRAM/PPU still prove its delivery."""
    source = (ROOT / "src/arcade_story.h").read_text(encoding="utf-8")
    match = re.search(r"\b" + re.escape(name) + r"\[[^]]+\]\s*=\s*\{(.*?)\};", source, re.S)
    if match is None:
        raise AssertionError(("missing authored story copy", name))
    return [json.loads('"' + text + '"') for text in re.findall(r'"((?:\\.|[^"\\])*)"', match.group(1))]


def verify_result_font_bank(e: Emulator, current: dict[str, int]) -> dict[str, object]:
    """Verify the result card's title, score, quote, and action rows."""

    winner = NAMES[current["fighter_id1"] if current["wins1"] >= current["wins2"]
                  else current["fighter_id2"]]
    quotes = (
        "IT WORKS ON MY MACHINE.", "COMPOUNDING THE COMBO.",
        "ATOMIC. CONSISTENT. VICTORY.", "THE BALANCE IS IN MY FAVOR.",
        "THAT WAS A MACRO MOVE.", "YOUR GUARD FAILED THE AUDIT.",
        "LEGACY NEVER GOES DOWN.", "RISK: UNDER CONTROL.",
        "MERGED WITHOUT CONFLICTS.", "DEPLOYED TO THE TOP.",
        "THE BOOKS ARE NOW CLOSED.", "COLD CODE. WARM VICTORY.",
    )
    winner_id = current["fighter_id1"] if current["wins1"] >= current["wins2"] \
        else current["fighter_id2"]
    score = f"P1  {current['wins1']} - {current['wins2']}  P2"
    if current["champion"]:
        rows = [
            (2, centered_start("OFFICE CHAMPION"), "OFFICE CHAMPION"),
            (18, 21, winner),
            (19, 21, f"P1 {current['wins1']}-{current['wins2']} P2"),
            (20, 22, "ALL 11"), (21, 21, "DEFEATED"),
            *[(22 + line, centered_start(text), text) for line, text in
              enumerate(arcade_copy("arcadeStoryEndings")[winner_id * 3:winner_id * 3 + 3])],
            (25, centered_start("A/START: TITLE"), "A/START: TITLE"),
            (27, centered_start("B: CHARACTER SELECT"), "B: CHARACTER SELECT"),
        ]
        return verify_opaque_text_rows(e, rows, "champion ending")
    elif current["mode"] == 1:
        title, action, context = "MATCH COMPLETE", "A/START: REMATCH", "LOCAL 1V1"
    else:
        won = current["wins1"] > current["wins2"]
        title = "SHIFT COMPLETE" if won else "SHIFT OVER"
        action = "A/START: NEXT CHALLENGER" if won else "A/START: CONTINUE"
        context = "ARCADE SHIFT"
        quotes = arcade_copy("arcadeStoryWinnerQuotes")
    rows = [
        (5, centered_start(title), title),
        (9, 15, winner),
        (11, 15, ("PLAYER 1 WINS" if current["wins1"] > current["wins2"] else "PLAYER 2 WINS")
         if current["mode"] == 1 else "WINS THE MATCH"),
        (13, 16, "ROUND WINS"),
        (14, 15, score),
        (17, 15, context),
        (21, centered_start(quotes[winner_id]), quotes[winner_id]),
        (24, centered_start(action), action),
        (26, centered_start("B: CHARACTER SELECT"), "B: CHARACTER SELECT"),
    ]
    if current["mode"] == 1:
        rows.append((23, centered_start("EITHER PLAYER"), "EITHER PLAYER"))
    return verify_opaque_text_rows(e, rows, "result card")


def verify_arena_cursor(e: Emulator, arena: int) -> dict[str, object]:
    """Verify the full 240x56 cursor frame follows the three arena rows."""

    memory = vram_bytes(e)
    top = 5 + arena * 7
    expected: dict[tuple[int, int], tuple[int, int]] = {}
    for x in range(1, 31):
        expected[(x, top)] = (154, 0x2000)
        expected[(x, top + 6)] = (154, 0xA000)
    expected[(1, top)] = (149, 0x2000)
    expected[(30, top)] = (150, 0x2000)
    expected[(1, top + 6)] = (151, 0x2000)
    expected[(30, top + 6)] = (152, 0x2000)
    for y in range(top + 1, top + 6):
        expected[(1, y)] = (153, 0x2000)
        expected[(30, y)] = (153, 0x6000)
    for (x, y), (tile, attributes) in expected.items():
        entry = map_tile(memory, x, y)
        check((entry & 0x03FF) == tile and (entry & 0xF000) == attributes,
              "arena cursor follows the native 240x56 row contract", {
                  "arena": arena, "x": x, "y": y,
                  "entry": hex(entry), "tile": tile,
                  "attributes": hex(attributes),
              })
    cursor_tiles = {149, 150, 151, 152, 153, 154}
    stray: list[tuple[int, int, int]] = []
    for y in range(32):
        if top <= y <= top + 6:
            continue
        for x in range(32):
            tile = map_tile(memory, x, y) & 0x03FF
            if tile in cursor_tiles:
                stray.append((x, y, tile))
    check(not stray, "arena cursor has no tiles in another selection row", {
        "arena": arena, "stray": stray,
    })
    return {"arena": arena, "top_tile_row": top, "cursor_cells": len(expected)}


def verify_arena_plate(e: Emulator, arena: int) -> dict[str, object]:
    """Compare the rendered thumbnail/card interior with the generated plate."""

    expected_path = ROOT / "assets/generated/arenas.png"
    check(expected_path.exists(), "generated arena plate exists", str(expected_path))
    expected_plate = Image.open(expected_path).convert("RGB")
    check(expected_plate.size == (256, 224), "generated arena plate is native size",
          expected_plate.size)
    check(e.frame is not None, "arena plate comparison has a native frame", arena)
    assert e.frame is not None
    y = ARENA_ROW_Y + arena * ARENA_ROW_H
    thumb_y = y + ARENA_THUMB_Y_INSET
    thumb_rect = (ARENA_THUMB_X, thumb_y,
                  ARENA_THUMB_X + ARENA_THUMB_W,
                  thumb_y + ARENA_THUMB_H)
    check(ARENA_ROW_X + 8 <= ARENA_THUMB_X and
          ARENA_THUMB_X + ARENA_THUMB_W <=
          ARENA_ROW_X + ARENA_ROW_W - 8 and
          y < thumb_y and thumb_y + ARENA_THUMB_H <= y + ARENA_ROW_H - 2,
          "arena thumbnail stays inside the cursor frame", {
              "arena": arena, "row": [ARENA_ROW_X, y, ARENA_ROW_W, ARENA_ROW_H],
              "thumbnail": list(thumb_rect),
          })
    actual_thumb = e.frame.crop(thumb_rect)
    expected_thumb = expected_plate.crop(thumb_rect)
    thumb_delta = image_delta(actual_thumb, expected_thumb)
    check(thumb_delta["mean_channel_delta"] <= 8.0 and
          thumb_delta["pixels_over_16"] <= thumb_delta["pixels"] * 0.08,
          "arena thumbnail uses the focused 104x52 native landmark view", {
              "arena": arena, "rect": list(thumb_rect), **thumb_delta,
          })
    # Exclude the cursor's one-pixel top/bottom rules; the interior is the
    # authored thumbnail, divider and location label.
    actual = e.frame.crop((16, y + 1, 240, y + 55))
    expected = expected_plate.crop((16, y + 1, 240, y + 55))
    delta = image_delta(actual, expected)
    check(delta["mean_channel_delta"] <= 8.0 and
          delta["pixels_over_16"] <= delta["pixels"] * 0.08,
          "arena row keeps its generated thumbnail/card layout", {
              "arena": arena, "rect": [16, y + 1, 240, y + 55], **delta,
          })
    return {"arena": arena, "rect": [16, y + 1, 240, y + 55],
            "thumbnail": list(thumb_rect), "thumbnail_delta": thumb_delta,
            **delta}


def verify_footer_blank(e: Emulator, label: str) -> None:
    """Rows 26/27 are permanent breathing room after combat UI settles."""

    rows = {str(row): ui_row(e, row) for row in (26, 27)}
    if state(e)["mode"] == 2:
        for row, values in rows.items():
            check(all((entry & 0x03ff) == 0 or
                      (256 <= (entry & 0x03ff) <= 383 and (entry & 0xf000) == 0x2000)
                      for entry in values),
                  "Training footer stays in native opaque tool glyphs after " + label, rows)
            if any(entry & 0x03ff for entry in values):
                text = "".join(chr((entry & 0x03ff) - 256) if 256 <= (entry & 0x03ff) <= 383 else " "
                               for entry in values)
                check(text.startswith("IN" if row == "26" else ("NOW ", "LAST")),
                      "Training footer shows the input/status row after " + label, text)
        return
    check(all((entry & 0x03FF) == 0 for values in rows.values()
              for entry in values),
          "combat footer rows 26-27 remain blank after " + label, rows)


def verify_result_score(e: Emulator, winner_side: int) -> dict[str, object]:
    """The result line reports the trace's actual best-of-three score."""

    current = state(e)
    check(current["screen"] == 4, "local match reaches the native result screen", current)
    expected_wins = (2, 0) if winner_side == 0 else (0, 2)
    check((current["wins1"], current["wins2"]) == expected_wins,
          "result trace exposes the truthful best-of-three score", current)
    row = ui_row(e, 14)
    digits = [entry & 0x03FF for entry in row]
    expected = [
        OPAQUE_FONT_BASE + ord("0") + current["wins1"],
        OPAQUE_FONT_BASE + ord("0") + current["wins2"],
    ]
    check(digits[19] == expected[0] and digits[23] == expected[1],
          "result row 14 writes opaque score digits at native source positions", {
              "wins1": current["wins1"], "wins2": current["wins2"],
              "x19": digits[19], "x23": digits[23],
              "expected": expected,
              "row14": digits,
          })
    return {"wins1": current["wins1"], "wins2": current["wins2"],
            "row14": digits}


def verify_large_portrait(e: Emulator, fighter: int,
                          map_x: int = PORTRAIT_MAP_X,
                          map_y: int = PORTRAIT_MAP_Y) -> dict[str, object]:
    """Verify the selected 64x80 portrait transfer and its BG2 map anchor.

    The profile image is a native 8x10 tile block at VRAM word $4A00.  A
    whole-block comparison catches stale portraits that can look plausible in
    a generic frame digest, while the map check proves the renderer points
    BG2 at tile 160 with palette 1 at the requested screen's anchor.
    """

    memory = vram_bytes(e)
    expected_path = ROOT / "assets/generated" / f"portrait{fighter:02}_tiles.bin"
    check(expected_path.exists(), "native large portrait asset exists", {
        "fighter": fighter, "path": str(expected_path),
    })
    expected = expected_path.read_bytes()
    check(len(expected) == PORTRAIT_BYTES,
          "large portrait asset is an 8x10 tile block", {
              "fighter": fighter, "bytes": len(expected),
          })
    actual = memory[PORTRAIT_VRAM_BYTE:PORTRAIT_VRAM_BYTE + PORTRAIT_BYTES]
    check(actual == expected, "large portrait reaches BG2 VRAM exactly", {
        "fighter": fighter, "vram_word": hex(PORTRAIT_VRAM_WORD),
        "sha256": hashlib.sha256(actual).hexdigest(),
    })

    map_offset = BG2_MAP_BYTE + (map_y * 32 + map_x) * 2
    entry = int.from_bytes(memory[map_offset:map_offset + 2], "little")
    tile = entry & 0x03FF
    palette = (entry >> 10) & 0x07
    check(tile == PORTRAIT_TILE_BASE and palette == PORTRAIT_MAP_PALETTE,
          "profile map anchor selects tile 160 with palette 1", {
              "fighter": fighter, "x": map_x, "y": map_y,
              "entry": hex(entry), "tile": tile, "palette": palette,
          })
    palette_path = ROOT / "assets/generated" / f"portrait{fighter:02}_pal.bin"
    check(palette_path.exists(), "native large portrait palette exists", {
        "fighter": fighter, "path": str(palette_path),
    })
    expected_palette = palette_path.read_bytes()
    expected_image = decode_tile_block(expected, expected_palette, 8, 10)
    check(e.frame is not None, "large portrait has a rendered native frame", fighter)
    assert e.frame is not None
    crop = (map_x * 8, map_y * 8, map_x * 8 + 64, map_y * 8 + 80)
    actual_image = e.frame.crop(crop)
    rendered = image_delta(actual_image, expected_image)
    check(rendered["mean_channel_delta"] <= 3.0 and
          rendered["max_channel_delta"] <= 3 and
          rendered["pixels_over_16"] == 0,
          "large portrait crop matches decoded native PPU pixels", {
              "fighter": fighter, "crop": list(crop), **rendered,
          })
    return {"asset": str(expected_path), "sha256": hashlib.sha256(actual).hexdigest(),
            "map_entry": entry, "tile": tile, "palette": palette,
            "rendered": rendered}


def optional_portrait_trace(e: Emulator, selected: int) -> None:
    """Validate optional trace aliases when the native UI exposes one."""

    values: list[tuple[str, int]] = []
    current = state(e)
    for key in (
        "portrait_id", "portrait", "hover_portrait", "select_portrait",
        "selected_portrait", "portrait_slot",
    ):
        if key in current:
            values.append((key, int(current[key])))
    for key, value in values:
        check(value == selected, "selection trace exposes the hovered portrait", {
            "field": key, "selected": selected, "value": value,
        })


def title_and_select() -> dict[str, object]:
    e = Emulator()
    try:
        e.run(120)
        check(state(e)["screen"] == TITLE, "cold boot reaches the redesigned home screen")
        version = json.loads((ROOT / "dist/manifest.json").read_bytes())["version"]
        verify_menu_font_bank(e, [
            (20, 9, "ARCADE SHIFT"),
            (22, 9, "LOCAL 1V1 / 2P"),
            (24, 9, "TRAINING"),
            (25, 3, "L/R LEVEL"),
            (25, 18, "NORMAL"),
            (27, 24, "V" + version),
        ], "title")
        title_path = capture(e, "title.png")
        initial_title = frame_digest(e)
        press(e, "r")
        check(state(e)["screen"] == TITLE, "title difficulty cycling keeps the home screen")
        check(frame_digest(e) != initial_title, "title difficulty state changes the rendered menu")
        press(e, "a")
        wait_screen(e, SELECT)

        check(state(e)["selected"] == 0, "roster opens on the first fighter")
        verify_menu_font_bank(e, [
            (4, 23, "PLAYER 1"),
            (17, 22, NAMES[0]),
            (27, centered_start("D-PAD SELECT A/START OK B BACK"),
             "D-PAD SELECT A/START OK B BACK"),
        ], "fighter select")
        select_card_render = verify_select_card_render(e)
        select_digests: dict[int, str] = {0: frame_digest(e)}
        portrait_paths: dict[str, str] = {"00": str(capture(e, "select-00.png"))}
        portrait_vram: dict[str, dict[str, object]] = {
            "00": verify_large_portrait(e, 0),
        }
        optional_portrait_trace(e, 0)

        # Horizontal movement covers every card and its wrap.  The expected
        # 4x3 visual grid is then exercised with +/-4 vertical steps.
        for expected in range(1, 12):
            press(e, "right")
            check(state(e)["selected"] == expected,
                  "roster horizontal navigation reaches slot " + str(expected + 1), {
                      "selected": state(e)["selected"],
                  })
            select_digests[expected] = frame_digest(e)
            portrait_paths[f"{expected:02}"] = str(capture(e, f"select-{expected:02}.png"))
            portrait_vram[f"{expected:02}"] = verify_large_portrait(e, expected)
            optional_portrait_trace(e, expected)
        press(e, "right")
        check(state(e)["selected"] == 0, "roster horizontal navigation wraps")

        press(e, "down")
        check(state(e)["selected"] == 4, "roster down moves one four-card row")
        select_digests[4] = frame_digest(e)
        press(e, "down")
        check(state(e)["selected"] == 8, "roster down reaches the third four-card row")
        press(e, "down")
        check(state(e)["selected"] == 0, "roster down wraps after the third row")
        press(e, "up")
        check(state(e)["selected"] == 8, "roster up wraps to the third row")
        press(e, "up")
        check(state(e)["selected"] == 4, "roster up moves one four-card row")
        press(e, "up")
        check(state(e)["selected"] == 0, "roster up returns to the first row")

        check(len(portrait_vram) == 12,
              "every fighter hover refreshes its exact large portrait block", {
                  "fighters": len(portrait_vram),
              })
        check(len(set(select_digests.values())) == len(select_digests),
              "each fighter hover has a distinct rendered large-profile state", {
                  "fighters": len(select_digests),
              })

        press(e, "a")
        wait_screen(e, ARENA)
        check(state(e)["arena"] == 0, "arena select opens on Las Condes")
        arena_paths: dict[str, str] = {}
        arena_digests: list[str] = []
        arena_renders: dict[str, dict[str, object]] = {}
        for index, stage in enumerate(STAGES):
            if index:
                press(e, "down")
            check(state(e)["arena"] == index, "arena cursor reaches row " + str(index + 1), {
                "arena": state(e)["arena"],
            })
            arena_digests.append(frame_digest(e))
            verify_arena_cursor(e, index)
            arena_plate = verify_arena_plate(e, index)
            verify_opaque_text_rows(e, [
                (27, centered_start("UP/DOWN A/START OK B BACK"),
                 "UP/DOWN A/START OK B BACK"),
            ], "arena footer")
            arena_renders[stage] = arena_plate
            arena_paths[stage] = str(capture(e, f"arena-{index}.png"))
        press(e, "down")
        check(state(e)["arena"] == 0, "arena cursor wraps after the third row")
        return {
            "title": str(title_path), "portraits": portrait_paths,
            "portrait_vram": portrait_vram,
            "select_card_render": select_card_render,
            "arena_select": arena_paths, "arena_digests": arena_digests,
            "arena_renders": arena_renders,
            "arena_contract": {
                "row_x": ARENA_ROW_X, "row_y": ARENA_ROW_Y,
                "row_width": ARENA_ROW_W, "row_height": ARENA_ROW_H,
                "thumbnail_x": ARENA_THUMB_X,
                "thumbnail_y_inset": ARENA_THUMB_Y_INSET,
                "thumbnail_width": ARENA_THUMB_W,
                "thumbnail_height": ARENA_THUMB_H,
            },
        }
    finally:
        e.close()


def boot_fight(mode: int = 1, stage: int = 0) -> Emulator:
    """Enter one native fight screen without opening a frontend window."""

    e = Emulator()
    e.run(120)
    for _ in range(mode):
        press(e, "down")
    press(e, "a")
    wait_screen(e, SELECT)
    press(e, "a")
    if mode in (1, 2):
        check(state(e)["screen"] == SELECT,
              "first fighter confirm leaves the second roster visible", state(e))
        heading = "DUMMY" if mode == 2 else "PLAYER 2"
        verify_menu_font_bank(e, [(4, 23, heading)], "second roster heading")
        verify_large_portrait(e, state(e)["selected2"])
        press(e, "a", 0 if mode == 2 else 1)
    wait_screen(e, ARENA)
    for _ in range(stage):
        press(e, "down")
    press(e, "a")
    wait_screen(e, FIGHT)
    for _ in range(180):
        if state(e)["intro"] == 0:
            break
        e.run(1)
    check(state(e)["intro"] == 0, "presentation fight reaches live combat", {
        "mode": mode, "stage": stage,
    })
    e.run(3)
    return e


def footer_lifecycle() -> None:
    """Check footer clearing after intro, Training reset, and pause."""

    e = boot_fight(1)
    try:
        verify_footer_blank(e, "the intro")
        e.run(3, p1=["start"])
        paused = state(e)
        check(paused["paused"] == 1, "START opens the native pause panel", paused)
        e.run(12)
        verify_footer_blank(e, "pause")
    finally:
        e.close()

    e = boot_fight(2)
    try:
        e.run(3, p1=["select"])
        e.run(12)
        reset = state(e)
        check(reset["intro"] == 0 and reset["action1"] == 0 and
              reset["action2"] == 0,
              "Training Select reset returns to an idle live round", reset)
        verify_footer_blank(e, "Training reset")
    finally:
        e.close()


def result_score_capture(winner_side: int = 0) -> dict[str, object]:
    """Win two local rounds and inspect the score line on the result screen."""

    e = boot_fight(1)
    try:
        # This uses state-driven approach and strong hits, also covered by the
        # gameplay suite. The other player is passive in local-versus, so no
        # AI state is involved in the result score or winner assertion.
        for _ in range(520):
            current = state(e)
            if current["screen"] == 4:
                break
            if current["intro"] or current["round_end"] or current["paused"]:
                e.run(1)
                continue
            x_attacker = current["x1" if winner_side == 0 else "x2"]
            x_defender = current["x2" if winner_side == 0 else "x1"]
            forward = "right" if x_attacker < x_defender else "left"
            port = "p1" if winner_side == 0 else "p2"
            action = current["action1" if winner_side == 0 else "action2"]
            if abs(x_attacker - x_defender) > 30 * 16:
                e.run(8, **{port: [forward]})
            elif action:
                e.run(6)
            else:
                e.run(3, **{port: ["x"]}); e.run(40)
        # The second win enters the native 180-tick round-end presentation;
        # the attack cadence above may finish exactly on that transition.
        for _ in range(220):
            if state(e)["screen"] == 4:
                break
            e.run(1)
        # The trace is published after the scene change; allow the PPU and
        # public trace to settle before comparing the actual result card.
        e.run(15)
        score = verify_result_score(e, winner_side)
        score["opaque_text"] = verify_result_font_bank(e, state(e))
        winner_id = state(e)["fighter_id1" if winner_side == 0 else "fighter_id2"]
        score["portrait"] = verify_large_portrait(e, winner_id, 4, 9)
        path = capture(e, "result-score.png" if winner_side == 0 else "result-score-p2.png")
        score["capture"] = str(path)
        press(e, "start")
        wait_screen(e, FIGHT)
        reset = state(e)
        check(reset["wins1"] == 0 and reset["wins2"] == 0 and reset["round"] == 1,
              "the advertised START rematch resets both players' scores", reset)
        return score
    finally:
        e.close()


def fight_stage_captures() -> dict[str, str]:
    captures: dict[str, str] = {}
    digests: dict[str, str] = {}
    for stage_index, stage in enumerate(STAGES):
        e = Emulator()
        try:
            e.run(120)
            press(e, "a")
            wait_screen(e, SELECT)
            press(e, "a")
            wait_screen(e, ARENA)
            for _ in range(stage_index):
                press(e, "down")
            press(e, "a")
            wait_screen(e, FIGHT)
            # P1 A skips the optional Arcade conversation, then normal intro.
            e.run(3, p1=["a"]); e.run(3)
            for _ in range(160):
                if state(e)["intro"] == 0:
                    break
                e.run(1)
            check(state(e)["intro"] == 0, "stage fight intro completes", {
                "stage": stage,
            })
            e.run(3)
            verify_footer_blank(e, "the stage intro")
            verify_fight_font_bank(e, state(e))
            verify_round_marker_tiles(e)
            path = capture(e, f"stage-{stage_index}.png")
            captures[stage] = str(path)
            digests[stage] = frame_digest(e)
        finally:
            e.close()
    check(len(captures) == 3, "all three stage captures are saved", captures)
    check(len(set(digests.values())) == 3,
          "the three stage fights render distinct native architecture plates", digests)
    return captures


def training_selection_capture() -> dict[str, object]:
    """Verify the visible DUMMY identity independently from live match state."""
    e = Emulator()
    try:
        e.run(120)
        press(e, "down"); press(e, "down"); press(e, "a")
        wait_screen(e, SELECT)
        press(e, "right"); press(e, "right"); press(e, "a")
        wait_screen(e, SELECT)
        check(state(e)["selected"] == 2 and state(e)["selected2"] == 3,
              "Training opens DUMMY after the chosen player with an adjacent cursor", state(e))
        press(e, "up", 1); press(e, "left", 1)
        check(state(e)["selected"] == 2 and state(e)["selected2"] == 10,
              "P2 can choose a nonadjacent dummy without changing PLAYER 1", state(e))
        verify_menu_font_bank(e, [(4, 23, "DUMMY"), (17, 22, "ROXANA")],
                              "Training arbitrary dummy")
        arbitrary = {"state": state(e), "portrait": verify_large_portrait(e, 10),
                     "capture": str(capture(e, "training-dummy.png"))}
        press(e, "down")
        check(state(e)["selected2"] == state(e)["selected"] == 2,
              "P1 can choose the same fighter for a visible mirror selection", state(e))
        verify_menu_font_bank(e, [(4, 23, "DUMMY"), (17, 22, "CRISTOBAL")],
                              "Training mirror dummy")
        mirror = {"state": state(e), "portrait": verify_large_portrait(e, 2),
                  "capture": str(capture(e, "training-mirror.png"))}
        press(e, "b", 1)
        verify_menu_font_bank(e, [(4, 23, "PLAYER 1"), (17, 22, "CRISTOBAL")],
                              "Training Back to PLAYER 1")
        returned = verify_large_portrait(e, 2)
        return {"arbitrary": arbitrary, "mirror": mirror, "back_portrait": returned}
    finally:
        e.close()


def timeout_draw_capture() -> dict[str, object]:
    """A full-health tied timeout must never claim a double knockout."""
    e = boot_fight(1)
    try:
        for _ in range(6200):
            current = state(e)
            if current["seconds"] == 0 and current["round_end"] > 100:
                break
            e.run(1)
        e.run(5)
        current = state(e)
        check(current["seconds"] == 0 and current["round_end"] > 100 and
              current["hp1"] == current["hp2"] > 0 and
              current["wins1"] == current["wins2"] == 0,
              "neutral local match reaches a healthy tied timeout", current)
        text = verify_opaque_text_rows(e, [
            (10, centered_start("TIME OVER"), "TIME OVER"),
            (12, centered_start("DRAW"), "DRAW"),
        ], "first tied timeout banner")
        path = capture(e, "timeout-draw.png")
        return {"state": current, "opaque_text": text, "capture": str(path)}
    finally:
        e.close()


def main() -> int:
    started = time.time()
    report: dict[str, object] = {
        "emulator": "Official Snes9x 1.63 x64 libretro core",
        "rom_sha256": None, "rom_bytes": None, "status": "failed",
        "checks": checks, "captures": {},
    }
    try:
        manifest = json.loads((ROOT / "dist/manifest.json").read_text())
        report["rom_sha256"] = manifest.get("sha256")
        report["rom_bytes"] = manifest.get("bytes")
        check(manifest.get("bytes") == 4 * 1024 * 1024,
              "presentation build uses the 4 MiB animation ROM", manifest)
        report["animation_artifact"] = verify_animation_artifact()
        footer_lifecycle()
        report["captures"] = {
            "menus": title_and_select(),
            "training_selection": training_selection_capture(),
            "stages": fight_stage_captures(),
            "result": result_score_capture(),
            "result_p2": result_score_capture(1),
            "timeout_draw": timeout_draw_capture(),
        }
        report["status"] = "passed"
    except Exception as exc:
        report["error"] = repr(exc)
        raise
    finally:
        report["passed"] = len(checks)
        report["elapsed_seconds"] = round(time.time() - started, 2)
        (ROOT / "docs/presentation-test-report.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
    print(json.dumps({"status": report["status"], "passed": report["passed"],
                      "seconds": report["elapsed_seconds"],
                      "report": "docs/presentation-test-report.json"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
