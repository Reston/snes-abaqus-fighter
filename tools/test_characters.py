"""Silent, headless integration checks for the individualized SNES roster.

This is deliberately separate from ``test_rom.py``.  It launches only the
official libretro core through :class:`emulator.Emulator`, drives the two
SNES controllers, reads the emulator's video/WRAM trace, and captures audio
samples without sending them to an audio device.  The host never writes game
memory.

Run after a native build with::

    python tools/test_characters.py

The script is intended to be useful while the user has another game in the
foreground: it never opens a window, plays audio, or takes focus.
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


NAMES = (
    "DAMIAN", "IVO", "CRISTOBAL", "COTE", "NEGGER", "DAVID",
    "FERNANDO", "CRISTIAN", "MAMARIAGA", "RESTON", "ROXANA", "LARS",
)

# This is a behavioral contract for the upgraded roster, not a lookup into the
# game binary.  The test obtains the family from the read-only WRAM trace and
# compares what the game reports with this design contract.
SPECIAL_FAMILY = (0, 0, 1, 1, 2, 3, 2, 3, 2, 0, 3, 2)
FAMILY_NAMES = ("projectile", "rush", "groundwave", "rising")

# A pose is a 96x80 actor frame (3,840 bytes).  The six 16x16 OBJ columns are
# stored as twelve 8x8 tiles per row.  Eight poses are kept in each
# LoROM-friendly bank; each physical VRAM row occupies a 16-tile page (512
# bytes), with the final four tiles left as padding for predictable OAM IDs.
POSE_WIDTH = 96
POSE_HEIGHT = 80
POSE_BYTES = POSE_WIDTH * POSE_HEIGHT // 2
BANK_BYTES = POSE_BYTES * 8
VRAM_ACTOR_BASE = 0xC000
VRAM_ACTOR_STRIDE = 0x1400
VRAM_ROW_STRIDE = 0x200
VRAM_ROW_BYTES = 0x180
VRAM_PAGE_BYTES = 0x200
OAM_ENTRY_BYTES = 4
OAM_HIGH_BYTES = 32
ACTOR_SPRITE_COLUMNS = 6
ACTOR_SPRITE_ROWS = 5
ACTOR_SPRITES = ACTOR_SPRITE_COLUMNS * ACTOR_SPRITE_ROWS
ACTOR_OAM_SLOTS = 32
OAM_ACTOR_BASE = (0, ACTOR_OAM_SLOTS)

checks: list[dict[str, object]] = []


def check(ok: bool, label: str, details: object | None = None) -> None:
    if not ok:
        raise AssertionError((label, details))
    checks.append({"check": label, "passed": True, "details": details})


def signed16(value: int) -> int:
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def raw_trace_words(e: Emulator, count: int = 64) -> list[int]:
    """Return trace words without mutating the emulated WRAM.

    The first 32 words predate the individualized roster.  The optional words
    are decoded here as a fallback so the test remains compatible with an
    Emulator.state() implementation from before the trace extension landed.
    """

    data = C.string_at(e.ram + 0x1FF00, count * 2)
    return [int.from_bytes(data[i:i + 2], "little") for i in range(0, len(data), 2)]


def state(e: Emulator) -> dict[str, int]:
    """Read the public state plus the agreed roster trace extension."""

    result = dict(e.state())
    raw = raw_trace_words(e)
    # These aliases mirror the agreed TRACE[32..41] contract.  setdefault is
    # intentional: a future Emulator.state() may expose nicer names directly.
    extension = {
        "fighter_id1": raw[32], "fighter_id2": raw[33],
        "family1": raw[34], "family2": raw[35],
        "speed1": raw[36], "speed2": raw[37],
        "jump1": raw[38], "jump2": raw[39],
        "face1": raw[40], "face2": raw[41],
        "back_speed1": raw[42], "back_speed2": raw[43],
        "special_startup1": raw[44], "special_startup2": raw[45],
        "special_active1": raw[46], "special_active2": raw[47],
        "special_recovery1": raw[48], "special_recovery2": raw[49],
        "special_damage1": raw[50], "special_damage2": raw[51],
        "special_reach1": raw[52], "special_reach2": raw[53],
        "throw_range1": raw[54], "throw_range2": raw[55],
        "wave_low1": raw[56], "wave_low2": raw[57],
        "wave_speed1": raw[58], "wave_speed2": raw[59],
        "wave_life1": raw[60], "wave_life2": raw[61],
    }
    for key, value in extension.items():
        result.setdefault(key, value)
    return result


def side_field(s: dict[str, int], side: int, *names: str) -> int | None:
    """Find a per-side trace field while accepting old/new naming styles."""

    suffix = str(side + 1)
    zero_suffix = str(side)
    candidates: list[str] = []
    for name in names:
        candidates.extend((f"{name}{suffix}", f"{name}_{suffix}",
                           f"{name}{zero_suffix}", f"{name}_{zero_suffix}"))
    for key in candidates:
        if key in s:
            return int(s[key])
    return None


def wait_screen(e: Emulator, wanted: int, max_frames: int = 600) -> None:
    for _ in range(max_frames // 10):
        if state(e)["screen"] == wanted:
            e.run(10)
            return
        e.run(10)
    raise AssertionError(("screen did not arrive", wanted, state(e)))


def press(e: Emulator, key: str, port: int = 0) -> None:
    e.tap(key, port)
    e.run(20)


def boot(mode: int, fighter: int, stage: int = 0, fighter2: int = 1) -> Emulator:
    """Boot a fresh match using only menu controller input.

    mode follows the cartridge menu: 0 arcade, 1 local versus, 2 training.
    """

    e = Emulator()
    e.run(120)
    for _ in range(mode):
        press(e, "down")
    press(e, "a")
    wait_screen(e, 1)
    for _ in range(fighter):
        press(e, "right")
    press(e, "a")
    if mode == 1:
        # The cartridge initializes P2's cursor to roster slot 1 (Ivo), so
        # menu-right counts are relative to that cursor rather than slot 0.
        for _ in range((fighter2 - 1) % len(NAMES)):
            press(e, "right", 1)
        press(e, "a", 1)
    wait_screen(e, 2)
    for _ in range(stage):
        press(e, "down")
    press(e, "a")
    wait_screen(e, 3)
    # Let the 110-frame intro finish while the CPU is still inert.  The first
    # live frame can still carry the FIGHT banner's dirty-tile upload, so give
    # the renderer three quiet frames before the first VRAM check or capture.
    for _ in range(160):
        if state(e)["intro"] == 0:
            break
        e.run(1)
    check(state(e)["intro"] == 0, "match intro completes", {
        "mode": mode, "fighter": fighter, "fighter2": fighter2,
    })
    e.run(3)
    return e


def vram(e: Emulator) -> bytes:
    ptr = e.core.retro_get_memory_data(3)
    size = e.core.retro_get_memory_size(3)
    return C.string_at(ptr, size)


def _symbol_wram_offset(name: str) -> int | None:
    """Resolve a linker symbol into an offset in libretro's WRAM window.

    PVSnesLib's ``.sym`` file records WRAM symbols as 24-bit SNES addresses
    (normally ``$7Exxxx``).  Keeping this lookup in the test host means the
    test can inspect the native OAM staging buffer without adding a gameplay
    trace field or writing any emulated memory.  A fixed fallback covers the
    current SDK's stable OAM declaration while still preferring the symbol
    emitted by a future linker layout.
    """

    candidates = [ROOT / "dist/abaqus-after-hours.sym", ROOT / "build/abaqus-after-hours.sym"]
    pattern = re.compile(r"^\s*([0-9a-fA-F]{6,8})\s+" + re.escape(name) + r"\s*$")
    for path in candidates:
        if not path.exists():
            continue
        for line in path.read_text(errors="replace").splitlines():
            match = pattern.match(line)
            if not match:
                continue
            address = int(match.group(1), 16)
            if 0x7E0000 <= address < 0x800000:
                return address - 0x7E0000
            if address < 0x20000:
                return address
    return None


def oam_memory(e: Emulator) -> bytes:
    """Read the native 512-byte OAM table plus its 32-byte high table."""

    offset = _symbol_wram_offset("oamMemory")
    if offset is None:
        # PVSnesLib's standard sprite RAM section currently starts at $7E9010.
        # This is only a read-only compatibility fallback; the symbol remains
        # authoritative whenever the linker emits one.
        offset = 0x9010
    return C.string_at(e.ram + offset, 128 * OAM_ENTRY_BYTES + OAM_HIGH_BYTES)


def oam_entry(raw: bytes, index: int) -> dict[str, int]:
    """Decode one SNES OAM entry, including its ninth tile-number bit."""

    offset = index * OAM_ENTRY_BYTES
    x, y, tile_low, attr = raw[offset:offset + OAM_ENTRY_BYTES]
    high = raw[512 + index // 4]
    pair = (index & 3) * 2
    x9 = (high >> pair) & 1
    size = (high >> (pair + 1)) & 1
    # The ninth tile bit lives in OAM attribute bit 0.  The adjacent high-table
    # bit is the 16x16 size flag, which must remain separate from tile IDs.
    tile = tile_low | ((attr & 1) << 8)
    raw_x = x | (x9 << 8)
    # OAM stores a 9-bit unsigned coordinate, but the left-edge probe can
    # straddle the 0/255 byte wrap: -24 is low byte $E8 with X9 set, while a
    # right-edge coordinate such as 264 is low byte $08 with X9 set.  Keep the
    # raw value for the X9 assertion and expose the unwrapped screen coordinate
    # for row spacing/geometry checks.
    signed_x = x - 256 if x9 and x >= 0x80 else raw_x
    return {"x": raw_x, "x_signed": signed_x, "y": y, "tile": tile,
            "attr": attr, "x9": x9, "size": size}


def _oam_actor_entries(raw: bytes, side: int) -> list[dict[str, int]]:
    base = OAM_ACTOR_BASE[side]
    return [oam_entry(raw, base + index) for index in range(ACTOR_SPRITES)]


def verify_oam_geometry(e: Emulator, side: int, label: str,
                        expected_floor: int | None = None) -> dict[str, object]:
    """Validate the 6x5 native metasprite layout and floor support.

    The old 64x80 renderer could silently overlap P2's OAM block and clip
    bottom rows.  This assertion reads only the cartridge's WRAM OAM buffer and
    checks the geometry that the PPU will actually scan: six columns at 16px,
    five rows at 16px, fixed tile strides, palette/flip attributes, and a
    stable bottom edge.  P2 rows 3 and 4 deliberately cross tile bit 8 because
    its VRAM page begins at tile 160.
    """

    raw = oam_memory(e)
    entries = _oam_actor_entries(raw, side)
    check(len(entries) == ACTOR_SPRITES, "native OAM exposes thirty actor sprites", {
        "side": side, "label": label, "count": len(entries),
    })

    # All actor entries should be visible at the centered boot position.  The
    # x9 bit is allowed to be set for a later edge probe, but coordinates must
    # remain within the signed 9-bit SNES sprite range.
    check(all(entry["x"] <= 0x1FF and entry["y"] < 0xF0 for entry in entries),
          "actor OAM entries stay in the visible geometry range", {
              "side": side, "label": label,
              "x": [entry["x"] for entry in entries],
              "y": [entry["y"] for entry in entries],
          })

    rows = [entries[row * ACTOR_SPRITE_COLUMNS:(row + 1) * ACTOR_SPRITE_COLUMNS]
            for row in range(ACTOR_SPRITE_ROWS)]
    x_values = [[entry["x_signed"] for entry in row] for row in rows]
    y_values = [[entry["y"] for entry in row] for row in rows]
    for row, values in enumerate(x_values):
        check(all(abs(values[col + 1] - values[col]) == 16
                  for col in range(ACTOR_SPRITE_COLUMNS - 1)),
              "actor OAM columns advance by sixteen pixels", {
                  "side": side, "label": label, "row": row, "x": values,
              })
    row_tops = [values[0] for values in y_values]
    check(all(row_tops[row + 1] - row_tops[row] == 16
              for row in range(ACTOR_SPRITE_ROWS - 1)),
          "actor OAM rows advance by sixteen pixels", {
              "side": side, "label": label, "row_tops": row_tops,
          })
    check(all(len(set(values)) == 1 for values in y_values),
          "actor OAM rows share a common y origin", {
              "side": side, "label": label, "y": y_values,
          })

    tile_rows = [[entry["tile"] for entry in row] for row in rows]
    for row, values in enumerate(tile_rows):
        check(all(values[col + 1] - values[col] == 2
                  for col in range(ACTOR_SPRITE_COLUMNS - 1)),
              "actor OAM columns use two-tile 16px steps", {
                  "side": side, "label": label, "row": row, "tiles": values,
              })
    tile_tops = [values[0] for values in tile_rows]
    check(all(tile_tops[row + 1] - tile_tops[row] == 32
              for row in range(ACTOR_SPRITE_ROWS - 1)),
          "actor OAM rows use the sixteen-tile page stride", {
              "side": side, "label": label, "tile_tops": tile_tops,
          })

    expected_flip = 0 if side == 0 else 0x40
    check(all((entry["attr"] & 0x40) == expected_flip for entry in entries),
          "actor OAM preserves the horizontal orientation", {
              "side": side, "label": label, "expected_flip": expected_flip,
              "attributes": sorted(set(entry["attr"] & 0x40 for entry in entries)),
          })
    check(all(((entry["attr"] >> 1) & 7) == side for entry in entries),
          "actor OAM keeps each fighter palette separate", {
              "side": side, "label": label,
              "palettes": sorted(set((entry["attr"] >> 1) & 7 for entry in entries)),
          })
    check(all(entry["size"] == 1 for entry in entries),
          "actor OAM marks every piece as a 16x16 sprite", {
              "side": side, "label": label,
              "size_bits": sorted(set(entry["size"] for entry in entries)),
          })

    if side == 1:
        bottom_tiles = [tile for row in tile_rows[3:5] for tile in row]
        check(all(tile & 0x100 for tile in bottom_tiles),
              "P2 bottom actor rows preserve the ninth tile bit", {
                  "side": side, "label": label, "tiles": bottom_tiles,
              })

    floor = max(row_tops) + 16
    if expected_floor is not None:
        check(abs(floor - expected_floor) <= 1,
              "actor keeps a stable support-floor baseline", {
                  "side": side, "label": label, "floor": floor,
                  "expected_floor": expected_floor,
              })
    return {"floor": floor, "x": x_values, "y": y_values,
            "tiles": tile_rows, "flip": expected_flip}


POSE_NAMES = (
    "idle", "walk-forward", "walk-back", "crouch", "jump", "jab",
    "cross", "kick", "sweep", "block", "hurt", "victory", "cast",
    "uppercut", "knockout", "rush",
)
NON_KO_POSES = tuple(index for index, name in enumerate(POSE_NAMES)
                     if name != "knockout")
SCALE_KEYS = ("physical_scale", "global_scale", "uniform_scale", "scale")


def _numeric_scale(value: object) -> float | None:
    """Accept the scalar or {x,y} form used by different asset manifests."""

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, dict):
        for key in ("x", "value", "pixels_per_source", "source_to_native"):
            candidate = value.get(key)
            if isinstance(candidate, (int, float)) and not isinstance(candidate, bool):
                return float(candidate)
    return None


def _manifest_scales(entry: dict[str, object]) -> tuple[list[float], str]:
    """Extract the physical scale contract, including per-frame annotations."""

    frames = entry.get("frames")
    frame_scales: list[float] = []
    if isinstance(frames, list):
        for frame in frames:
            if not isinstance(frame, dict):
                continue
            for key in SCALE_KEYS:
                if key in frame:
                    value = _numeric_scale(frame[key])
                    if value is not None:
                        frame_scales.append(value)
                        break
    if frame_scales:
        return frame_scales, "frames"

    for key in SCALE_KEYS:
        if key in entry:
            value = _numeric_scale(entry[key])
            if value is not None:
                return [value] * len(POSE_NAMES), key
    raise AssertionError((
        "character manifest must record one physical global scale per fighter",
        entry.get("id"), sorted(entry),
    ))


def _native_pose_boxes(fighter: int) -> tuple[Image.Image, list[tuple[int, int, int, int]]]:
    """Decode the actual generated native pose sheet into per-pose boxes."""

    path = ROOT / f"assets/generated/fighter{fighter:02}.png"
    check(path.exists(), "native pose preview exists", {"fighter": fighter, "path": str(path)})
    image = Image.open(path).convert("RGBA")
    check(image.size == (POSE_WIDTH * len(POSE_NAMES), POSE_HEIGHT),
          "native pose preview uses the 96x80 frame contract", {
              "fighter": fighter, "size": image.size,
          })
    boxes: list[tuple[int, int, int, int]] = []
    for pose in range(len(POSE_NAMES)):
        crop = image.crop((pose * POSE_WIDTH, 0,
                           (pose + 1) * POSE_WIDTH, POSE_HEIGHT))
        box = crop.getchannel("A").getbbox()
        check(box is not None, "native pose has opaque pixels", {
            "fighter": fighter, "pose": POSE_NAMES[pose],
        })
        boxes.append(box)
    return image, boxes


def verify_rendered_actor(e: Emulator, fighter: int, side: int,
                          geometry: dict[str, object]) -> dict[str, object]:
    """Confirm that the PPU output contains the native actor silhouette.

    OAM flags alone can report a 16x16 sprite while OBJSEL is configured with
    the wrong large-size mode, which makes the cartridge render blank or
    expand every piece to 32x32.  Compare the captured RGB frame against the
    generated stage plate at the actor's opaque native pixels.  The stage
    plate and Snes9x output differ by the expected <=8-level SNES palette
    rounding; a larger difference in the native silhouette is therefore a
    rendered actor pixel.  The bounds check also rejects a large-size bleed
    outside the 96x80 actor canvas.
    """

    check(e.frame is not None, "actor render probe has a video frame", {
        "fighter": fighter, "side": side,
    })
    stage_index = int(state(e).get("arena", 0))
    stage_path = ROOT / f"assets/generated/stage{stage_index}.png"
    check(stage_path.exists(), "render probe has the native stage plate", {
        "fighter": fighter, "stage": stage_index, "path": str(stage_path),
    })
    stage = Image.open(stage_path).convert("RGB")
    frame = e.frame.convert("RGB")
    native, boxes = _native_pose_boxes(fighter)
    alpha = native.crop((0, 0, POSE_WIDTH, POSE_HEIGHT)).getchannel("A")
    alpha_pixels = [(x, y) for y in range(POSE_HEIGHT) for x in range(POSE_WIDTH)
                    if alpha.getpixel((x, y))]
    x_rows = geometry["x"]
    y_rows = geometry["y"]
    assert isinstance(x_rows, list) and isinstance(y_rows, list)
    frame_left = min(int(x) for row in x_rows for x in row)
    frame_top = min(int(y) for row in y_rows for y in row)
    changed: list[tuple[int, int]] = []
    for source_x, source_y in alpha_pixels:
        screen_x = frame_left + (POSE_WIDTH - 1 - source_x if side else source_x)
        screen_y = frame_top + source_y
        if not (0 <= screen_x < 256 and 0 <= screen_y < 224):
            continue
        actual = frame.getpixel((screen_x, screen_y))
        plate = stage.getpixel((screen_x, screen_y))
        if max(abs(actual[channel] - plate[channel]) for channel in range(3)) > 16:
            changed.append((screen_x, screen_y))

    expected_box = boxes[0]
    if side:
        expected_box = (POSE_WIDTH - expected_box[2], expected_box[1],
                        POSE_WIDTH - expected_box[0], expected_box[3])
    expected_screen = (frame_left + expected_box[0], frame_top + expected_box[1],
                       frame_left + expected_box[2], frame_top + expected_box[3])
    minimum = max(24, len(alpha_pixels) // 20)
    check(len(changed) >= minimum,
          "captured PPU frame contains the native actor pixels", {
              "fighter": fighter, "side": side, "changed_pixels": len(changed),
              "opaque_pixels": len(alpha_pixels), "minimum": minimum,
          })
    if changed:
        observed = (min(x for x, _ in changed), min(y for _, y in changed),
                    max(x for x, _ in changed) + 1, max(y for _, y in changed) + 1)
        check(all(abs(observed[index] - expected_screen[index]) <= 8
                  for index in range(4)),
              "captured actor bounds stay on the native 96x80 canvas", {
                  "fighter": fighter, "side": side,
                  "expected": expected_screen, "observed": observed,
              })
    else:
        observed = None
    return {"expected": expected_screen, "observed": observed,
            "changed_pixels": len(changed), "opaque_pixels": len(alpha_pixels)}


def verify_native_proportions() -> dict[str, object]:
    """Check shared-scale source geometry before any emulator is launched.

    The old pipeline fit each pose independently to a 64x80 frame, making a
    jab or kick visibly taller or shorter than idle.  This review intentionally
    checks the generated native image and manifest rather than a duplicated
    source constant: all sixteen frames must advertise the same physical
    scale, stay inside the 96x80 canvas, and share one support-floor baseline.
    """

    manifest_path = ROOT / "assets/generated/character-manifest.json"
    entries = json.loads(manifest_path.read_text())
    check(len(entries) == len(NAMES), "character manifest contains all twelve fighters", {
        "count": len(entries),
    })
    results: dict[str, object] = {}
    for fighter, entry in enumerate(entries):
        check(int(entry.get("id", -1)) == fighter, "manifest roster order is stable", {
            "fighter": fighter, "id": entry.get("id"),
        })
        scales, scale_source = _manifest_scales(entry)
        check(len(scales) == len(POSE_NAMES), "fighter records one scale for every pose", {
            "fighter": fighter, "count": len(scales), "source": scale_source,
        })
        scale_span = max(scales) - min(scales)
        check(scale_span <= 1e-6, "all sixteen poses use one uniform physical scale", {
            "fighter": fighter, "scale": scales[0], "span": scale_span,
        })

        _, boxes = _native_pose_boxes(fighter)
        for pose, box in enumerate(boxes):
            left, top, right, bottom = box
            check(left > 0 and top >= 0 and right < POSE_WIDTH and bottom <= POSE_HEIGHT,
                  "native pose stays inside its 96x80 canvas", {
                      "fighter": fighter, "pose": POSE_NAMES[pose], "box": box,
                  })

        baselines = [boxes[pose][3] for pose in NON_KO_POSES]
        check(max(baselines) - min(baselines) <= 1,
              "non-knockout poses share a support-floor baseline", {
                  "fighter": fighter, "baselines": baselines,
              })
        standing_height = entry.get("standing_height")
        idle_height = boxes[0][3] - boxes[0][1]
        if isinstance(standing_height, (int, float)):
            check(abs(idle_height - float(standing_height)) <= 2,
                  "manifest standing height matches native idle geometry", {
                      "fighter": fighter, "manifest": standing_height,
                      "idle_pixels": idle_height,
                  })

        # These representative frames are the ones most likely to expose a
        # per-pose fit: jab reaches forward, kick extends vertically, and cast
        # raises both arms.  Their torso/standing geometry must remain close to
        # idle even when the outer silhouette grows.
        for pose in (5, 7, 12):
            height = boxes[pose][3] - boxes[pose][1]
            # A raised arm or a kick can change the silhouette's top edge by
            # several pixels.  The meaningful invariant is that the native
            # body was not independently shrunk to fit that pose: keep a
            # broad but explicit 65% lower bound and reject an unexpected
            # over-sized frame as well.
            check(idle_height * 0.65 <= height <= idle_height + 12,
                  "attack pose keeps a comparable body height to idle", {
                      "fighter": fighter, "pose": POSE_NAMES[pose],
                      "idle_height": idle_height, "pose_height": height,
                  })
        results[f"{fighter:02}"] = {
            "scale": scales[0], "scale_source": scale_source,
            "idle_box": boxes[0], "jab_box": boxes[5],
            "kick_box": boxes[7], "cast_box": boxes[12],
            "baseline": baselines[0],
        }
    return results


def expected_bank(fighter: int, bank: int) -> bytes:
    suffix = "" if bank == 0 else "b"
    data = (ROOT / f"assets/generated/fighter{fighter:02}{suffix}.bin").read_bytes()
    check(len(data) == BANK_BYTES, "fighter bank has 8 complete poses", {
        "fighter": fighter, "bank": bank, "bytes": len(data),
    })
    return data


def actor_rows(e: Emulator, fighter: int, side: int, bank: int,
               pose: int | None = None) -> bool:
    """Compare every uploaded row in the selected actor slot to the ROM asset."""

    data = expected_bank(fighter, bank)
    pose_in_bank = (pose if pose is not None else bank * 8) & 7
    data = data[pose_in_bank * POSE_BYTES:(pose_in_bank + 1) * POSE_BYTES]
    image = vram(e)
    base = VRAM_ACTOR_BASE + side * VRAM_ACTOR_STRIDE
    return all(
        image[base + row * VRAM_ROW_STRIDE:base + row * VRAM_ROW_STRIDE + VRAM_ROW_BYTES]
        == data[row * VRAM_ROW_BYTES:(row + 1) * VRAM_ROW_BYTES]
        for row in range(10)
    )


def wait_for_uploaded_pose(e: Emulator, fighter: int, side: int = 0,
                           max_frames: int = 24) -> tuple[dict[str, int], int]:
    """Wait for the one-actor-per-vblank queue and return pose/bank."""

    for _ in range(max_frames):
        s = state(e)
        pose = s["pose1" if side == 0 else "pose2"]
        bank = 0 if pose < 8 else 1
        if actor_rows(e, fighter, side, bank, pose):
            return s, bank
        e.run(1)
    s = state(e)
    pose = s["pose1" if side == 0 else "pose2"]
    bank = 0 if pose < 8 else 1
    return s, bank


def stream_pose(e: Emulator, fighter: int, side: int, expected_pose: int,
                label: str, max_frames: int = 48) -> dict[str, int]:
    """Wait for one controller-driven pose and compare its complete VRAM page."""

    state_key = "pose1" if side == 0 else "pose2"
    for _ in range(max_frames):
        sample = state(e)
        pose = sample[state_key]
        bank = 0 if pose < 8 else 1
        if pose == expected_pose and actor_rows(e, fighter, side, bank, pose):
            check(True, label + " streams its complete native pose", {
                "fighter": fighter, "side": side, "pose": pose, "bank": bank,
            })
            return {"pose": pose, "bank": bank}
        e.run(1)
    raise AssertionError((label + " did not stream its expected native pose", {
        "fighter": fighter, "side": side, "expected_pose": expected_pose,
        "last": state(e),
    }))


def capture(e: Emulator, fighter: int, label: str) -> Path:
    folder = ROOT / "docs/screenshots/characters"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (f"{fighter:02}.png" if label == "idle" else f"{fighter:02}-{label}.png")
    if e.frame is None:
        e.run(1)
    e.frame.save(path)
    return path


def trigger_special(e: Emulator, expected_family: int) -> tuple[dict[str, int], list[dict[str, int]]]:
    """Try the controller-only special motions and return observed samples.

    The primary motion is the game's documented down + punch shortcut.  The
    remaining quarter-circle and uppercut variants make this diagnostic if a
    character family chooses a different six-button route while preserving
    the public controller contract.
    """

    macros = (
        (("down",), ("down", "x")),
        (("down",), ("down", "a")),
        (("down", "right"), ("down", "right", "x")),
        (("down",), ("down", "l")),
    )
    best: tuple[dict[str, int], list[dict[str, int]]] | None = None
    before = state(e)
    for held, pressed in macros:
        # The libretro input callback is sampled at the core's frame boundary;
        # a one-frame edge can fall between polls on some Snes9x cadence
        # phases.  Hold the setup and button long enough for a real pad
        # sample, matching a player's sustained SNES input without changing
        # the game's edge-triggered move rules.
        e.run(4, p1=list(held))
        e.run(18, p1=list(pressed))
        samples: list[dict[str, int]] = []
        for _ in range(40):
            sample = state(e)
            samples.append(sample)
            # Leave the emulator on the special pose so the following VRAM
            # assertion observes the one-actor-per-vblank upload, rather than
            # waiting until the animation has already returned to idle.
            displacement = abs(signed16(sample["x1"]) - signed16(before["x1"]))
            rising = signed16(sample["y1"]) < 0
            if sample["wave1"] or (
                expected_family == 1 and sample["pose1"] >= 8 and displacement >= 8
            ) or (
                expected_family == 3 and sample["pose1"] >= 8 and rising
            ):
                break
            e.run(1)
        # A trace-visible action, projectile, vertical movement, or rush
        # displacement is stronger evidence than merely pressing a button.
        changed = any(
            s["action1"] or s["wave1"] or signed16(s["y1"]) < 0
            or abs(signed16(s["x1"]) - signed16(before["x1"])) >= 8
            for s in samples
        )
        if changed:
            return before, samples
        best = (before, samples)
        e.run(36)
    assert best is not None
    return best


def assert_special_family(e: Emulator, fighter: int) -> dict[str, object]:
    expected = SPECIAL_FAMILY[fighter]
    before, samples = trigger_special(e, expected)
    observed = [state(e)] + samples
    values = [side_field(s, 0, "family", "special_family", "specialFamily")
              for s in observed]
    values = [v for v in values if v is not None and v < len(FAMILY_NAMES)]
    check(bool(values), "fighter exposes a special family in read-only trace", {
        "fighter": fighter, "expected": expected,
        "trace_keys": sorted(k for k in observed[-1] if "family" in k.lower()),
    })
    check(all(v == expected for v in values), "fighter reports its contracted special family", {
        "fighter": fighter, "expected": expected, "observed": values,
    })

    # The family must manifest in emulated gameplay.  This deliberately uses
    # only public trace values, never game memory writes or source constants.
    action = any(s["action1"] for s in samples)
    projectile = any(s["wave1"] for s in samples)
    rise = any(signed16(s["y1"]) < 0 for s in samples)
    rush = any(abs(signed16(s["x1"]) - signed16(before["x1"])) >= 8 for s in samples)
    low_wave = [side_field(s, 0, "wave_low", "waveLow", "low") for s in samples]
    low_wave = [v for v in low_wave if v is not None]
    if expected == 0:
        manifested = projectile and (not low_wave or any(v == 0 for v in low_wave))
    elif expected == 1:
        manifested = rush and not rise
    elif expected == 2:
        manifested = projectile and (not low_wave or any(v == 1 for v in low_wave))
    else:
        manifested = rise
    check(manifested, "special family produces an observable combat event", {
        "fighter": fighter, "family": FAMILY_NAMES[expected],
        "action": action, "projectile": projectile, "rush": rush, "rise": rise,
    })
    return {
        "expected": FAMILY_NAMES[expected], "observed": values,
        "action": action, "projectile": projectile, "rush": rush, "rise": rise,
    }


def close_p1_to_guard_range(e: Emulator) -> int:
    """Put P1 at 35--40 pixels from an idle P2 using only the controller."""

    for _ in range(260):
        s = state(e)
        distance = abs(signed16(s["x2"]) - signed16(s["x1"]))
        if 35 * 16 <= distance <= 40 * 16:
            return distance
        e.run(1, p1=["right"] if distance > 40 * 16 else ["left"])
    raise AssertionError(("P1 could not close to the guard range", state(e)))


def close_p2_to_attack_range(e: Emulator) -> int:
    """Put a left-facing P2 at 35--40 pixels from a passive P1."""

    for _ in range(260):
        s = state(e)
        distance = abs(signed16(s["x2"]) - signed16(s["x1"]))
        if 35 * 16 <= distance <= 40 * 16:
            return distance
        e.run(1, p2=["left"] if distance > 40 * 16 else ["right"])
    raise AssertionError(("P2 could not close to the attack range", state(e)))


def wait_for_hp_change(e: Emulator, side: int, p1=(), p2=(), max_frames: int = 120) -> tuple[int, int, dict[str, int]]:
    """Hold the guard/controller inputs until a real hit is recorded."""

    key = "hp1" if side == 0 else "hp2"
    before = state(e)
    initial = before[key]
    for frame in range(1, max_frames + 1):
        e.run(1, p1=list(p1), p2=list(p2))
        sample = state(e)
        if sample[key] != initial:
            return initial, sample[key], {"frame": frame, **sample}
    raise AssertionError(("special did not reach the guarded/passive target", {
        "side": side, "initial_hp": initial, "last": state(e),
    }))


def verify_guard_case(fighter: int, guard: str, blocked: bool) -> dict[str, object]:
    """Check a real special interaction against a controller-held guard.

    P2 is local-versus and receives no CPU decisions.  Standing guard is the
    character's back direction (right while P2 faces left); crouch guard adds
    down and therefore does not walk backward.  A blocked special may deal
    one chip point, while an unblocked special must deal meaningful damage.
    """

    e = boot(1, fighter, 0, 1)
    try:
        distance = close_p1_to_guard_range(e)
        guard_keys = ["right"] if guard == "standing" else ["down", "right"]
        before = state(e)
        face1 = side_field(before, 0, "face", "facing", "direction")
        face2 = side_field(before, 1, "face", "facing", "direction")
        if face1 is not None:
            check(face1 == 1, "P1 faces the left-facing P2 before the special", {
                "fighter": fighter, "face1": face1, "face2": face2,
            })
        if face2 is not None:
            check(face2 == 0, "P2 remains left-facing for the guard check", {
                "fighter": fighter, "face2": face2,
            })
        family = side_field(before, 0, "family", "special_family", "specialFamily")
        check(family == SPECIAL_FAMILY[fighter], "guard probe sees the contracted special family", {
            "fighter": fighter, "family": family,
        })

        initial_hp, final_hp, hit = wait_for_hp_change(
            e, 1, p1=["down", "x"], p2=guard_keys
        )
        delta = initial_hp - final_hp
        if blocked:
            check(0 < delta <= 1, "held standing/crouch guard limits special to chip damage", {
                "fighter": fighter, "family": FAMILY_NAMES[SPECIAL_FAMILY[fighter]],
                "guard": guard, "hp_delta": delta,
            })
        else:
            check(delta >= 10, "special breaks the intended guard and deals real damage", {
                "fighter": fighter, "family": FAMILY_NAMES[SPECIAL_FAMILY[fighter]],
                "guard": guard, "hp_delta": delta,
            })
        return {
            "fighter": NAMES[fighter], "family": FAMILY_NAMES[SPECIAL_FAMILY[fighter]],
            "guard": guard, "expected_blocked": blocked, "distance_12_4": distance,
            "initial_hp2": initial_hp, "final_hp2": final_hp, "damage": delta,
            "hit_frame": hit["frame"],
        }
    finally:
        e.close()


def verify_p2_special_hit(fighter: int) -> dict[str, object]:
    """Ensure each representative special also works when P2 faces left."""

    e = boot(1, 1, 0, fighter)
    try:
        distance = close_p2_to_attack_range(e)
        before = state(e)
        face2 = side_field(before, 1, "face", "facing", "direction")
        if face2 is not None:
            check(face2 == 0, "P2 representative starts left-facing", {
                "fighter": fighter, "face2": face2,
            })
        family = side_field(before, 1, "family", "special_family", "specialFamily")
        check(family == SPECIAL_FAMILY[fighter], "P2 representative reports its special family", {
            "fighter": fighter, "family": family,
        })

        initial_hp, final_hp, hit = wait_for_hp_change(
            e, 0, p1=[], p2=["down", "x"]
        )
        delta = initial_hp - final_hp
        check(delta >= 10, "left-facing P2 special reaches passive P1", {
            "fighter": fighter, "family": FAMILY_NAMES[SPECIAL_FAMILY[fighter]],
            "hp_delta": delta,
        })
        return {
            "fighter": NAMES[fighter], "family": FAMILY_NAMES[SPECIAL_FAMILY[fighter]],
            "distance_12_4": distance, "initial_hp1": initial_hp,
            "final_hp1": final_hp, "damage": delta, "hit_frame": hit["frame"],
            "face2": face2,
        }
    finally:
        e.close()


def verify_asset_identity() -> None:
    digests: list[str] = []
    for fighter in range(len(NAMES)):
        a = expected_bank(fighter, 0)
        b = expected_bank(fighter, 1)
        digests.append(hashlib.sha256(a + b).hexdigest())
        check(a != b, "fighter has distinct pose banks", {"fighter": fighter})
    check(len(set(digests)) == len(NAMES), "all twelve fighters have distinct native animation assets", {
        "unique_assets": len(set(digests)),
    })


def verify_p1_fighter(fighter: int) -> dict[str, object]:
    e = boot(2, fighter, fighter % 3)
    try:
        s0, bank0 = wait_for_uploaded_pose(e, fighter, 0)
        check(s0["selected"] == fighter, "menu selects requested fighter", {
            "fighter": fighter, "selected": s0["selected"],
        })
        check(s0["pose1"] < 8 and bank0 == 0, "idle frame uses the first pose bank", {
            "fighter": fighter, "pose": s0["pose1"], "bank": bank0,
        })
        check(actor_rows(e, fighter, 0, 0), "all ten idle sprite rows reach actor VRAM", {
            "fighter": fighter,
        })
        idle_oam = verify_oam_geometry(e, 0, "idle")
        idle_render = verify_rendered_actor(e, fighter, 0, idle_oam)
        idle_path = capture(e, fighter, "idle")

        # The crouch, jump, and all six normal buttons must each upload the
        # exact native pose selected by the controller.  This catches a
        # renderer that only validates idle/special banks while a normal move
        # still points at a stale 64x80 or wrong-bank frame.
        e.run(3, p1=["down"])
        crouch_stream = stream_pose(e, fighter, 0, 3, "crouch")
        e.run(4)

        x0 = signed16(s0["x1"])
        movement = []
        for _ in range(8):
            e.run(1, p1=["right"])
            movement.append(signed16(state(e)["x1"]) - x0)
        s_move = state(e)
        delta = signed16(s_move["x1"]) - x0
        check(delta > 0, "controller one moves the fighter forward", {
            "fighter": fighter, "delta_12_4": delta,
        })
        check(s_move["pose1"] in (1, 2), "forward movement uses a walk pose", {
            "fighter": fighter, "pose": s_move["pose1"],
        })

        e.run(3, p1=["up"])
        jump_stream = stream_pose(e, fighter, 0, 4, "jump")
        jump_samples = []
        for _ in range(8):
            jump_samples.append(state(e))
            e.run(1)
        jump_height = min(signed16(s["y1"]) for s in jump_samples)
        check(jump_height < 0, "controller one jump leaves the floor", {
            "fighter": fighter, "min_y_12_4": jump_height,
        })
        for _ in range(90):
            e.run(1)
            if signed16(state(e)["y1"]) == 0:
                break
        # A grounded return must put the complete metasprite back on exactly
        # the same support line as idle.  This catches per-pose y fitting and
        # a stale OAM row that a VRAM-only comparison cannot see.
        landed_oam = verify_oam_geometry(e, 0, "landed", idle_oam["floor"])

        normal_streams: dict[str, dict[str, int]] = {}
        for key, action, pose in (
            ("y", 1, 5), ("x", 2, 6), ("l", 3, 6),
            ("b", 4, 7), ("a", 5, 7), ("r", 6, 7),
        ):
            e.run(1, p1=[key])
            check(state(e)["action1"] == action,
                  "normal button starts action " + key.upper(), {
                      "fighter": fighter, "action": state(e)["action1"],
                  })
            normal_streams[key] = stream_pose(
                e, fighter, 0, pose, "normal " + key.upper())
            e.run(50)

        e.run(1, p1=["down", "l"])
        check(state(e)["action1"] == 8, "down plus heavy starts the uppercut", {
            "fighter": fighter, "action": state(e)["action1"],
        })
        uppercut_stream = stream_pose(e, fighter, 0, 13, "uppercut")
        e.run(70)

        # Drive P1 to the gameplay clamp so the left edge exercises signed X9
        # coordinates and the native flip/palette bits, still through input.
        for _ in range(90):
            e.run(1, p1=["left"])
        edge_oam = verify_oam_geometry(e, 0, "left-edge")
        edge_entries = _oam_actor_entries(oam_memory(e), 0)
        check(any(entry["x9"] for entry in edge_entries),
              "left screen edge preserves signed OAM X9 pixels", {
                  "fighter": fighter,
                  "x9_entries": [index for index, entry in enumerate(edge_entries)
                                 if entry["x9"]],
              })

        special = assert_special_family(e, fighter)
        s_special, bank1 = wait_for_uploaded_pose(e, fighter, 0)
        # The special family must reach a second-bank key pose at least once.
        check(s_special["pose1"] >= 8 or bank1 == 1, "special reaches a second-bank pose", {
            "fighter": fighter, "pose": s_special["pose1"], "bank": bank1,
        })
        check(actor_rows(e, fighter, 0, 1, s_special["pose1"]), "all ten special sprite rows reach the second actor bank", {
            "fighter": fighter,
        })
        capture(e, fighter, "special")

        profile_speed = side_field(s0, 0, "speed", "profile_speed", "profileSpeed")
        profile_jump = side_field(s0, 0, "jump", "jump_strength", "jumpStrength")
        return {
            "name": NAMES[fighter], "movement_delta": delta,
            "movement_samples": movement, "jump_height": jump_height,
            "speed_trace": profile_speed, "jump_trace": profile_jump,
            "special": special, "idle_screenshot": str(idle_path),
            "idle_render": idle_render,
            "crouch_stream": crouch_stream, "jump_stream": jump_stream,
            "normal_streams": normal_streams, "uppercut_stream": uppercut_stream,
            "idle_floor": idle_oam["floor"], "landed_floor": landed_oam["floor"],
            "edge_floor": edge_oam["floor"],
        }
    finally:
        e.close()


def verify_p2_orientation(fighter: int) -> dict[str, object]:
    """Exercise the same native asset in player two's flipped actor slot."""

    e = boot(1, 0, 0, fighter)
    try:
        s0, bank0 = wait_for_uploaded_pose(e, fighter, 1)
        check(s0["selected2"] == fighter, "controller two selects requested fighter", {
            "fighter": fighter, "selected2": s0["selected2"],
        })
        check(actor_rows(e, fighter, 1, 0), "player two receives this fighter's native idle rows", {
            "fighter": fighter,
        })
        idle_oam = verify_oam_geometry(e, 1, "idle")
        idle_render = verify_rendered_actor(e, fighter, 1, idle_oam)
        face = side_field(s0, 1, "face", "facing", "direction")
        if face is not None:
            check(face == 0, "player two starts facing left for horizontal flip", {
                "fighter": fighter, "face2": face,
            })

        x0 = signed16(s0["x2"])
        e.run(1, p2=["left"])
        walk_samples = [state(e)]
        for _ in range(6):
            e.run(1, p2=["left"])
            walk_samples.append(state(e))
        s_walk = state(e)
        x_delta = signed16(s_walk["x2"]) - x0
        check(x_delta < 0, "controller two moves its flipped fighter toward player one", {
            "fighter": fighter, "delta_12_4": x_delta,
        })
        check(s_walk["pose2"] in (1, 2), "player two flipped actor uses a walk pose", {
            "fighter": fighter, "pose2": s_walk["pose2"],
        })

        e.run(3, p2=["up"])
        y_samples = []
        for _ in range(8):
            y_samples.append(state(e))
            e.run(1)
        min_y = min(signed16(s["y2"]) for s in y_samples)
        check(min_y < 0, "controller two can jump the flipped fighter", {
            "fighter": fighter, "min_y_12_4": min_y,
        })
        s_end = state(e)
        face_end = side_field(s_end, 1, "face", "facing", "direction")
        if face_end is not None:
            check(face_end == 0, "player two keeps left-facing flip while moving left", {
                "fighter": fighter, "face2": face_end,
            })
        return {"name": NAMES[fighter], "movement_delta": x_delta,
                "jump_height": min_y, "face2": face_end, "bank": bank0,
                "idle_floor": idle_oam["floor"], "idle_render": idle_render}
    finally:
        e.close()


def main() -> int:
    started = time.time()
    report: dict[str, object] = {
        "emulator": "Official Snes9x 1.63 x64 libretro core",
        "rom_sha256": None,
        "rom_bytes": None,
        "checks": checks,
        "proportions": {},
        "characters": {},
        "player_two": {},
        "guard_checks": {},
        "player_two_specials": {},
    }
    try:
        manifest = json.loads((ROOT / "dist/manifest.json").read_text())
        report["rom_sha256"] = manifest["sha256"]
        report["rom_bytes"] = manifest.get("bytes")
        check(manifest.get("bytes") == 2 * 1024 * 1024,
              "release manifest records the 2 MiB FastROM image", {
                  "bytes": manifest.get("bytes"),
                  "mapping": manifest.get("mapping"),
              })
        report["proportions"] = verify_native_proportions()
        verify_asset_identity()

        character_results: dict[str, object] = {}
        for fighter in range(len(NAMES)):
            character_results[f"{fighter:02}"] = verify_p1_fighter(fighter)
        report["characters"] = character_results

        p2_results: dict[str, object] = {}
        for fighter in range(len(NAMES)):
            p2_results[f"{fighter:02}"] = verify_p2_orientation(fighter)
        report["player_two"] = p2_results

        # Verify the frame-level guard rules against actual HP changes.  These
        # probes deliberately use local-versus P2 input so no CPU behaviour or
        # hidden test hook can satisfy the assertion.  The representative
        # roster members cover every special family and both directional
        # guard exceptions:
        #   projectile/rush: standing guard blocks;
        #   groundwave: standing guard loses, crouch guard blocks;
        #   rising: standing guard blocks, crouch guard loses.
        guard_cases = (
            (0, "standing", True),
            (2, "standing", True),
            (4, "standing", False),
            (4, "crouching", True),
            (10, "standing", True),
            (10, "crouching", False),
        )
        guard_results: dict[str, object] = {}
        for fighter, guard, blocked in guard_cases:
            key = f"{fighter:02}-{guard}"
            guard_results[key] = verify_guard_case(fighter, guard, blocked)
        report["guard_checks"] = guard_results

        # Exercise the same four representatives as player two.  P2 starts
        # facing left, so this catches flipped movement and projectile/hitbox
        # direction errors that a P1-only probe would miss.
        p2_special_results: dict[str, object] = {}
        for fighter in (0, 2, 4, 10):
            p2_special_results[f"{fighter:02}"] = verify_p2_special_hit(fighter)
        report["player_two_specials"] = p2_special_results

        movement = [int(v["movement_delta"]) for v in character_results.values()]
        check(len(set(movement)) >= 3, "roster has at least three observed movement profiles", {
            "movement_deltas": movement,
        })
        report["passed"] = len(checks)
        report["elapsed_seconds"] = round(time.time() - started, 2)
        report["status"] = "passed"
    except Exception as exc:
        report["passed"] = len(checks)
        report["elapsed_seconds"] = round(time.time() - started, 2)
        report["status"] = "failed"
        report["error"] = repr(exc)
        raise
    finally:
        path = ROOT / "docs/character-test-report.json"
        path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "status": report["status"], "passed": report.get("passed", 0),
        "seconds": report["elapsed_seconds"],
        "report": "docs/character-test-report.json",
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
