"""Silent, headless integration checks for the individualized SNES roster.

This is deliberately separate from ``test_rom.py``.  It launches only the
official libretro core through :class:`emulator.Emulator`, drives the two
SNES controllers, reads the emulator's video/WRAM trace, and captures audio
samples without sending them to an audio device.  The host never writes game
memory.

Run after a native build with::

    python tools/test_characters.py

The script is intended to be useful while the user has another game in the
foreground: it never opens a window, plays audio, or takes focus.  It checks
the 4 MiB eight-bank animation cartridge and preserves the 16 logical combat
pose trace for gameplay assertions.
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
ANIMATION_FRAME_COUNT = 64
ANIMATION_BANK_COUNT = 8
BANK_BYTES = POSE_BYTES * 8
ANIMATION_BANK_SUFFIXES = ("", "b", "c", "d", "e", "f", "g", "h")
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
_BANK_CACHE: dict[tuple[int, int], bytes] = {}
_FRAME_LOOKUP: dict[int, dict[bytes, int]] = {}


def check(ok: bool, label: str, details: object | None = None) -> None:
    if not ok:
        raise AssertionError((label, details))
    checks.append({"check": label, "passed": True, "details": details})


def signed16(value: int) -> int:
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def raw_trace_words(e: Emulator, count: int = 114) -> list[int]:
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
        # Animation and input-feel fields are deliberately read directly from
        # the public trace window here.  This keeps this suite compatible with
        # an emulator.py host that predates the animation aliases and avoids
        # writing any emulated memory.
        "anim_frame1": raw[62], "anim_frame2": raw[63],
        "animation_frame1": raw[62], "animation_frame2": raw[63],
        "anim_state1": raw[64], "anim_state2": raw[65],
        "anim_tick1": raw[66], "anim_tick2": raw[67],
        "buffered_action1": raw[68], "buffered_action2": raw[69],
        "buffer_age1": raw[70], "buffer_age2": raw[71],
        "jump_buffer1": raw[72], "jump_buffer2": raw[73],
        "command_stage1": raw[74], "command_stage2": raw[75],
        "raw_keys1": raw[76], "raw_keys2": raw[77],
        "landing1": raw[78], "landing2": raw[79],
        # v0.6 airborne/throw/knockdown telemetry.  Keep the stable 0..93
        # offsets untouched; these aliases are read-only and optional until
        # the next native ROM is released.
        "down_state1": raw[94], "down_state2": raw[95],
        "down_tick1": raw[96], "down_tick2": raw[97],
        "invuln1": raw[98], "invuln2": raw[99],
        "pending_throw_damage1": raw[100], "pending_throw_damage2": raw[101],
        "throw_owner1": raw[102], "throw_owner2": raw[103],
        "air_action1": raw[104], "air_action2": raw[105],
        "throw_victim1": raw[106], "throw_victim2": raw[107],
        "wake_action1": raw[108], "wake_action2": raw[109],
        "wake_age1": raw[110], "wake_age2": raw[111],
        "wake_jump1": raw[112], "wake_jump2": raw[113],
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


def boot(mode: int, fighter: int, stage: int = 0, fighter2: int | None = None,
         quiet_frames: int = 3, rom=None) -> Emulator:
    """Boot a fresh match using only menu controller input.

    mode follows the cartridge menu: 0 arcade, 1 local versus, 2 training.
    """

    e = Emulator(rom)
    e.run(120)
    for _ in range(mode):
        press(e, "down")
    press(e, "a")
    wait_screen(e, 1)
    for _ in range(fighter):
        press(e, "right")
    press(e, "a")
    if mode in (1, 2):
        # Preserve the adjacent Training fixture unless an opponent is
        # requested explicitly; both choices use the native second cursor.
        target = fighter2 if fighter2 is not None else (
            (fighter + 1) % len(NAMES) if mode == 2 else 1)
        port = 0 if mode == 2 else 1
        for _ in range((target - state(e)["selected2"]) % len(NAMES)):
            press(e, "right", port)
        press(e, "a", port)
    wait_screen(e, 2)
    for _ in range(stage):
        press(e, "down")
    press(e, "a")
    wait_screen(e, 3)
    if mode == 0:
        e.run(3, p1=["a"]); e.run(3)
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
    e.run(quiet_frames)
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
# Keeping the logical labels separate from the 16 legacy gameplay poses lets
# the tests verify actual VRAM animation without changing the long-standing
# action trace.  Frames 48..63 are the airborne/throw/knockdown atlas.
ANIMATION_FRAME_NAMES = tuple("legacy-" + name for name in POSE_NAMES) + (
    "idle-guard", "idle-inhale", "idle-exhale", "idle-return",
    "walk-forward-contact", "walk-forward-pass", "walk-forward-under",
    "walk-forward-opposite", "walk-back-contact", "walk-back-pass",
    "walk-back-under", "walk-back-opposite", "crouch-transition",
    "jump-anticipation", "jump-extension", "landing-compression",
    "attack-ready", "attack-jab-retract", "attack-cross-windup",
    "attack-cross-retract", "attack-kick-windup", "attack-kick-retract",
    "attack-sweep-windup", "attack-sweep-recovery", "block-impact",
    "hurt-recovery", "special-charge", "cast-recovery",
    "uppercut-anticipation", "uppercut-recovery", "victory-transition",
    "knockout-fall",
    "upright-neutral", "air-punch-anticipation", "air-punch-active",
    "air-punch-recovery", "air-kick-anticipation", "air-kick-active",
    "air-kick-recovery", "compact-apex-guard", "thrower-grip",
    "thrower-release", "victim-lift", "victim-impact",
    "knockdown-launch", "knockdown-fall", "grounded-getup",
    "wakeup-guard",
)
NON_KO_POSES = tuple(index for index, name in enumerate(POSE_NAMES)
                     if name != "knockout")
# Standing-height comparisons deliberately cover only upright support and
# attack silhouettes.  Frame 44 is uppercut anticipation with the body
# crouched; frame 45 is the airborne/recovery transition.  Both remain under
# the strict canvas, scale, and shared-baseline checks above.
COMPARABLE_STANDING_FRAMES = (
    16, 17, 18, 19,
    20, 21, 22, 23, 24, 25, 26, 27,
    32, 33, 34, 35, 36, 37,
    42, 43, 48, 56, 57, 63,
)
# Air, victim and knockdown frames intentionally do not share the standing
# support line: their feet are in flight, impact, or a bounded get-up state.
# Keep baseline checks strict for every upright/support pose while allowing
# those explicit physical roles to move within the 96x80 canvas.
SUPPORT_BASELINE_FRAMES = tuple(range(0, 47)) + (48, 56, 57, 62, 63)
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
                return [value] * ANIMATION_FRAME_COUNT, key
    raise AssertionError((
        "character manifest must record one physical global scale per fighter",
        entry.get("id"), sorted(entry),
    ))


def _native_pose_boxes(fighter: int) -> tuple[Image.Image, list[tuple[int, int, int, int]]]:
    """Decode the generated 64-frame native animation sheet into boxes."""

    path = ROOT / f"assets/generated/fighter{fighter:02}.png"
    check(path.exists(), "native pose preview exists", {"fighter": fighter, "path": str(path)})
    source_image = Image.open(path)
    check(source_image.mode == "RGBA",
          "native animation preview preserves RGBA transparency", {
              "fighter": fighter, "mode": source_image.mode,
          })
    image = source_image.convert("RGBA")
    check(image.size == (POSE_WIDTH * ANIMATION_FRAME_COUNT, POSE_HEIGHT),
          "native animation preview uses the 64-frame 96x80 contract", {
              "fighter": fighter, "size": image.size,
          })
    boxes: list[tuple[int, int, int, int]] = []
    for pose in range(ANIMATION_FRAME_COUNT):
        crop = image.crop((pose * POSE_WIDTH, 0,
                           (pose + 1) * POSE_WIDTH, POSE_HEIGHT))
        box = crop.getchannel("A").getbbox()
        check(box is not None, "native pose has opaque pixels", {
            "fighter": fighter, "pose": ANIMATION_FRAME_NAMES[pose],
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
    actual_frame = uploaded_frame_id(e, fighter, side)
    if actual_frame is None:
        actual_frame = trace_animation_frame(state(e), side)
    if actual_frame is None or not 0 <= actual_frame < ANIMATION_FRAME_COUNT:
        actual_frame = 0
    alpha = native.crop((actual_frame * POSE_WIDTH, 0,
                         (actual_frame + 1) * POSE_WIDTH, POSE_HEIGHT)).getchannel("A")
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

    expected_box = boxes[actual_frame]
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
    return {"frame": actual_frame, "expected": expected_screen,
            "observed": observed, "changed_pixels": len(changed),
            "opaque_pixels": len(alpha_pixels)}


def verify_native_proportions() -> dict[str, object]:
    """Check shared-scale source geometry before any emulator is launched.

    The old pipeline fit each pose independently to a 64x80 frame, making a
    jab or kick visibly taller or shorter than idle.  This review intentionally
    checks the generated native image and manifest rather than a duplicated
    source constant: all sixty-four frames must advertise the same physical
    scale, stay inside the 96x80 canvas, and keep one support-floor baseline
    for every upright/support role.  Air and knockdown roles are checked for
    bounds and distinct source/native hashes instead of being forced onto the
    standing baseline.
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
        check(int(entry.get("frame_count", 0)) == ANIMATION_FRAME_COUNT,
              "manifest records all sixty-four native animation frames", {
                  "fighter": fighter, "frame_count": entry.get("frame_count"),
              })
        scales, scale_source = _manifest_scales(entry)
        check(len(scales) == ANIMATION_FRAME_COUNT,
              "fighter records one scale for every animation frame", {
            "fighter": fighter, "count": len(scales), "source": scale_source,
        })
        scale_span = max(scales) - min(scales)
        check(scale_span <= 1e-6, "all sixty-four frames use one uniform physical scale", {
            "fighter": fighter, "scale": scales[0], "span": scale_span,
        })

        _, boxes = _native_pose_boxes(fighter)
        metadata_frames = entry.get("frames")
        check(isinstance(metadata_frames, list) and
              len(metadata_frames) == ANIMATION_FRAME_COUNT,
              "manifest contains complete metadata for all 64 frames", {
                  "fighter": fighter,
                  "count": len(metadata_frames) if isinstance(metadata_frames, list) else None,
              })
        frame_hashes: list[str] = []
        if isinstance(metadata_frames, list):
            for pose, item in enumerate(metadata_frames):
                check(isinstance(item, dict), "frame metadata record is an object", {
                    "fighter": fighter, "frame": pose,
                })
                if not isinstance(item, dict):
                    continue
                global_index = item.get("global_index", item.get("globalindex"))
                check(int(global_index if global_index is not None else -1) == pose,
                      "frame metadata preserves stable global index", {
                          "fighter": fighter, "frame": pose,
                          "global_index": global_index,
                      })
                expected_kind = ("legacy" if pose < 16 else
                                 "motion" if pose < 32 else
                                 "actions" if pose < 48 else "airborne")
                if 20<=pose<28 and entry.get('walking_revision'):
                    expected_kind='walking-v2'
                source_kind = item.get("source_kind", item.get("source_role"))
                check(source_kind == expected_kind,
                      "frame metadata preserves its source role", {
                          "fighter": fighter, "frame": pose,
                          "expected": expected_kind, "actual": source_kind,
                      })
                source_file = item.get("source_file", item.get("sourcefile"))
                source_hash = item.get("source_hash", item.get("sourcehash"))
                native_hash = item.get("native_hash", item.get("hash"))
                pixel_hash = item.get("pixels_sha256", native_hash)
                check(isinstance(source_file, str) and bool(source_file) and
                      isinstance(source_hash, str) and len(source_hash) == 64,
                      "frame metadata retains source file and hash", {
                          "fighter": fighter, "frame": pose,
                          "source_file": source_file, "source_hash": source_hash,
                      })
                check(isinstance(native_hash, str) and len(native_hash) == 64 and
                      isinstance(pixel_hash, str) and len(pixel_hash) == 64,
                      "frame metadata retains native pixel hashes", {
                          "fighter": fighter, "frame": pose,
                          "native_hash": native_hash, "pixels_sha256": pixel_hash,
                      })
                if isinstance(native_hash, str):
                    frame_hashes.append(native_hash)
                native_box = item.get("native_box", item.get("nativebox"))
                check(native_box == list(boxes[pose]),
                      "frame metadata bounds match the native preview", {
                          "fighter": fighter, "frame": pose,
                          "metadata": native_box, "preview": boxes[pose],
                      })

        # The authored source ranges must include the new airborne atlas while
        # retaining the original 0..47 source split.
        sources = entry.get("animation_sources")
        check(isinstance(sources, list) and len(sources) >= 3,
              "manifest records motion, action, and airborne sources", {
                  "fighter": fighter, "sources": sources,
              })
        if isinstance(sources, list):
            ranges = [tuple(item.get("frame_range", ())) for item in sources
                      if isinstance(item, dict)]
            check((16, 31) in ranges and (32, 47) in ranges and (48, 63) in ranges,
                  "manifest keeps stable old ranges and adds airborne 48-63", {
                      "fighter": fighter, "ranges": ranges,
                  })

        # Palette bytes are a compatibility boundary.  Compare the emitted
        # OBJ binary to the manifest's fifteen-color palette so a new atlas
        # cannot silently reorder or recolor the established base palette.
        palette = entry.get("palette")
        palette_path = ROOT / "assets/generated" / f"fighter{fighter:02}_pal.bin"
        check(isinstance(palette, list) and len(palette) == 16 and
              palette_path.exists(), "fighter palette metadata and binary exist", {
                  "fighter": fighter, "palette": palette_path.name,
              })
        if isinstance(palette, list) and len(palette) == 16 and palette_path.exists():
            expected_palette = bytearray()
            for color in palette:
                if isinstance(color, list) and len(color) >= 3:
                    red, green, blue = [int(value) for value in color[:3]]
                    snes = (red >> 3) | ((green >> 3) << 5) | ((blue >> 3) << 10)
                    expected_palette.extend(snes.to_bytes(2, "little"))
            actual_palette = palette_path.read_bytes()[:len(expected_palette)]
            check(bytes(expected_palette) == actual_palette,
                  "native OBJ palette bytes match manifest ordering", {
                      "fighter": fighter, "bytes": len(actual_palette),
                  })
        for pose, box in enumerate(boxes):
            left, top, right, bottom = box
            check(left > 0 and top >= 0 and right < POSE_WIDTH and bottom <= POSE_HEIGHT,
                  "native animation frame stays inside its 96x80 canvas", {
                      "fighter": fighter, "pose": ANIMATION_FRAME_NAMES[pose], "box": box,
                  })

        baselines = [boxes[pose][3] for pose in SUPPORT_BASELINE_FRAMES]
        check(max(baselines) - min(baselines) <= 1,
              "upright/support animation frames share a support-floor baseline", {
                  "fighter": fighter, "frames": SUPPORT_BASELINE_FRAMES,
                  "baselines": baselines,
              })
        baseline_y = entry.get("baseline_y")
        if isinstance(baseline_y, (int, float)):
            check(abs(float(baseline_y) - baselines[0]) <= 1,
                  "manifest baseline matches rendered animation support line", {
                      "fighter": fighter, "manifest": baseline_y,
                      "native": baselines[0],
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
        # The drawn animation atlases must preserve the same body scale while
        # adding motion.  Their hands/feet may change the outer silhouette,
        # but the visible body cannot collapse to a separately fitted sprite.
        for frame in COMPARABLE_STANDING_FRAMES:
            height = boxes[frame][3] - boxes[frame][1]
            check(idle_height * 0.65 <= height <= idle_height + 12,
                  "drawn animation preserves comparable fighter height", {
                      "fighter": fighter, "frame": ANIMATION_FRAME_NAMES[frame],
                      "idle_height": idle_height, "frame_height": height,
                  })
        if len(frame_hashes) == ANIMATION_FRAME_COUNT:
            for start, end, minimum, role in (
                    (16, 20, 3, "breathing"), (20, 24, 3, "forward walk"),
                    (24, 28, 3, "backward walk"), (48, 52, 3, "air punch"),
                    (52, 56, 3, "air kick"), (56, 60, 3, "throw"),
                    (60, 64, 3, "knockdown/recovery")):
                check(len(set(frame_hashes[start:end])) >= minimum,
                      "native " + role + " frames remain visibly distinct", {
                          "fighter": fighter, "frames": [start, end],
                          "unique": len(set(frame_hashes[start:end])),
                      })
        results[f"{fighter:02}"] = {
            "scale": scales[0], "scale_source": scale_source,
            "idle_box": boxes[0], "jab_box": boxes[5],
            "kick_box": boxes[7], "cast_box": boxes[12],
            "animation_frames": len(boxes), "baseline": baselines[0],
        }
    return results


def expected_bank(fighter: int, bank: int) -> bytes:
    if not 0 <= bank < ANIMATION_BANK_COUNT:
        raise AssertionError(("invalid animation bank", fighter, bank))
    cache_key = (fighter, bank)
    if cache_key in _BANK_CACHE:
        return _BANK_CACHE[cache_key]
    suffix = ANIMATION_BANK_SUFFIXES[bank]
    data = (ROOT / f"assets/generated/fighter{fighter:02}{suffix}.bin").read_bytes()
    check(len(data) == BANK_BYTES, "fighter bank has 8 complete poses", {
        "fighter": fighter, "bank": bank, "bytes": len(data),
    })
    _BANK_CACHE[cache_key] = data
    return data


def actor_payload(e: Emulator, side: int) -> bytes:
    """Compact one actor's 10 native rows, removing the padded VRAM tail."""

    image = vram(e)
    base = VRAM_ACTOR_BASE + side * VRAM_ACTOR_STRIDE
    return b"".join(
        image[base + row * VRAM_ROW_STRIDE:
              base + row * VRAM_ROW_STRIDE + VRAM_ROW_BYTES]
        for row in range(POSE_HEIGHT // 8)
    )


def uploaded_frame_id(e: Emulator, fighter: int, side: int) -> int | None:
    """Identify the exact uploaded animation frame from native VRAM bytes."""

    lookup = _FRAME_LOOKUP.get(fighter)
    if lookup is None:
        lookup = {}
        for bank in range(ANIMATION_BANK_COUNT):
            data = expected_bank(fighter, bank)
            for pose in range(8):
                frame = bank * 8 + pose
                payload = data[pose * POSE_BYTES:(pose + 1) * POSE_BYTES]
                lookup[payload] = frame
        _FRAME_LOOKUP[fighter] = lookup
    return lookup.get(actor_payload(e, side))


def trace_animation_frame(sample: dict[str, int], side: int) -> int | None:
    """Read the actual visual frame, accepting future host aliases."""

    suffix = str(side + 1)
    for key in (f"animation_frame{suffix}", f"anim_frame{suffix}",
                f"frame_anim{suffix}", f"visual_frame{suffix}"):
        value = sample.get(key)
        if value is not None and 0 <= int(value) < ANIMATION_FRAME_COUNT:
            return int(value)
    return None


def animation_group_for_pose(pose: int) -> set[int]:
    """Frames that are valid visual transitions for a legacy logical pose."""

    groups = {
        0: {0, 16, 17, 18, 19, 28, 32, 34, 36, 38},
        1: {1, 20, 21, 22, 23},
        2: {2, 24, 25, 26, 27},
        3: {3, 28},
        4: {4, 29, 30, 31, 54, 55},
        5: {5, 32, 33, 34, 35},
        6: {6, 32, 33, 34, 35},
        7: {7, 32, 36, 37, 38, 39},
        8: {8, 28, 38, 39},
        9: {9, 40, 63},
        10: {10, 14, 41, 58, 59, 60, 61, 62},
        11: {11, 46},
        12: {12, 42, 43},
        13: {13, 44, 45},
        # The logical KO pose may settle on the native head-left floor frame
        # after a knockdown; keep both legacy KO art and the v0.6 floor frame.
        14: {14, 47, 59},
        15: {15, 32, 33, 34, 35, 48, 56, 57},
    }
    return groups.get(pose, {pose})


AIR_PUNCH_FRAMES = set(range(49, 52))
AIR_KICK_FRAMES = set(range(52, 55))
THROW_FRAMES = set(range(56, 60))
KNOCKDOWN_FRAMES = set(range(60, 64))


def observed_animation_frames(e: Emulator, fighter: int, side: int,
                              frames: int = 48) -> set[int]:
    """Collect exact native VRAM frame IDs while a controller action runs."""

    seen: set[int] = set()
    for _ in range(frames):
        actual = uploaded_frame_id(e, fighter, side)
        if actual is not None:
            seen.add(actual)
            check(actor_rows(e, fighter, side, actual // 8, actual),
                  "observed animation frame has all ten native VRAM rows", {
                      "fighter": fighter, "side": side, "frame": actual,
                  })
        e.run(1)
    return seen


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
    """Wait for the one-actor-per-vblank queue and return visual bank.

    The logical combat pose remains 0..15, while the renderer can stream one
    of the 48 animation frames.  The exact compact VRAM payload is therefore
    authoritative for the bank returned here; TRACE[62/63] is used as a
    cross-check when the new host aliases are present.
    """

    for _ in range(max_frames):
        s = state(e)
        pose = s["pose1" if side == 0 else "pose2"]
        actual = uploaded_frame_id(e, fighter, side)
        if actual is not None:
            bank = actual // 8
            # TRACE[62/63] is written before the alternating one-actor
            # vblank upload.  During a fast transition it can name a later
            # visual frame while VRAM still contains the previous one.  Keep
            # the exact native VRAM payload authoritative here; stream_pose
            # checks the trace against the expected logical animation group
            # when a controller transition has a known target.
            return s, bank
        bank = 0 if pose < 8 else 1
        if actor_rows(e, fighter, side, bank, pose):
            return s, bank
        e.run(1)
    s = state(e)
    pose = s["pose1" if side == 0 else "pose2"]
    actual = uploaded_frame_id(e, fighter, side)
    bank = actual // 8 if actual is not None else (0 if pose < 8 else 1)
    return s, bank


def stream_pose(e: Emulator, fighter: int, side: int, expected_pose: int,
                label: str, max_frames: int = 48,
                hold: tuple[str, ...] = ()) -> dict[str, int]:
    """Wait for a logical pose and compare its complete animated VRAM frame."""

    state_key = "pose1" if side == 0 else "pose2"
    for _ in range(max_frames):
        sample = state(e)
        pose = sample[state_key]
        actual = uploaded_frame_id(e, fighter, side)
        traced = trace_animation_frame(sample, side)
        allowed = animation_group_for_pose(expected_pose)
        if pose == expected_pose and actual is not None and actual in allowed:
            check(traced is None or traced in allowed,
                  label + " trace stays in the expected animation group", {
                      "fighter": fighter, "side": side,
                      "trace": traced, "vram": actual,
                  })
            check(True, label + " streams its complete native pose", {
                "fighter": fighter, "side": side, "pose": pose,
                "frame": actual, "bank": actual // 8,
            })
            return {"pose": pose, "frame": actual, "bank": actual // 8}
        bank = 0 if pose < 8 else 1
        if pose == expected_pose and actor_rows(e, fighter, side, bank, pose):
            check(True, label + " streams its complete legacy native pose", {
                "fighter": fighter, "side": side, "pose": pose, "bank": bank,
            })
            return {"pose": pose, "frame": pose, "bank": bank}
        e.run(1, p1=list(hold) if side == 0 else [],
              p2=list(hold) if side == 1 else [])
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


def save_animation_gif(fighter: int, label: str,
                       images: list[Image.Image]) -> Path:
    """Save callback-captured PPU frames at their native 60 Hz cadence."""

    check(len(images) >= 4, "animation capture contains native PPU frames", {
        "fighter": fighter, "label": label, "frames": len(images),
    })
    folder = ROOT / "docs/screenshots/characters"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{fighter:02}-{label}.gif"
    # Three source PPU frames span 50 ms at 60 Hz.  A flat 50 ms per frame
    # would play the review at one third speed and obscure the real cadence.
    durations = (20, 20, 10) * ((len(images) + 2) // 3)
    images[0].save(path, save_all=True, append_images=images[1:],
                   duration=list(durations[:len(images)]), loop=0,
                   optimize=False)
    return path


def capture_animation_gif(e: Emulator, fighter: int, label: str,
                          inputs: tuple[str, ...] = (),
                          frames: int = 24, side: int = 0) -> Path:
    """Save source-actual PPU frames for a human animation review."""

    images: list[Image.Image] = []
    for _ in range(frames):
        if e.frame is not None:
            images.append(e.frame.copy())
        e.run(1, p1=list(inputs) if side == 0 else [],
              p2=list(inputs) if side == 1 else [])
    return save_animation_gif(fighter, label, images)


def observe_animation_loop(e: Emulator, fighter: int, side: int,
                           label: str, inputs: tuple[str, ...],
                           expected: set[int], frames: int = 32,
                           gif_label: str | None = None,
                           minimum_distinct: int = 3) -> dict[str, object]:
    """Observe distinct uploaded frames and a stable floor while moving."""

    visual_frames: list[int] = []
    expected_frames: list[int] = []
    floors: list[int] = []
    reached_expected = False
    for _ in range(frames):
        actual = uploaded_frame_id(e, fighter, side)
        if actual is not None:
            visual_frames.append(actual)
            if actual in expected:
                reached_expected = True
                expected_frames.append(actual)
            elif reached_expected:
                check(False, label + " uses the correct animation frame set", {
                    "fighter": fighter, "side": side, "frame": actual,
                })
        raw = oam_memory(e)
        entries = _oam_actor_entries(raw, side)
        floors.append(max(entry["y"] for entry in entries) + 16)
        e.run(1, p1=list(inputs) if side == 0 else [],
              p2=list(inputs) if side == 1 else [])
    check(len(set(expected_frames)) >= minimum_distinct,
          label + f" exposes at least {minimum_distinct} distinct native animation frames", {
              "fighter": fighter, "side": side,
              "frames": sorted(set(expected_frames)),
          })
    check(max(floors) - min(floors) <= 1,
          label + " keeps a stable support floor while animating", {
              "fighter": fighter, "side": side,
              "floor_min": min(floors), "floor_max": max(floors),
          })
    gif_path = None
    if gif_label is not None and side == 0:
        # Re-run the exact input window for the review capture.  The GIF is
        # generated from actual callback frames, never from source art.
        gif_path = str(capture_animation_gif(e, fighter, gif_label, inputs, frames))
    return {"frames": sorted(set(expected_frames)),
            "floor": [min(floors), max(floors)], "gif": gif_path}


def trigger_special(e: Emulator, expected_family: int,
                    fighter: int | None = None) -> tuple[
                        dict[str, int], list[dict[str, int]], set[int]]:
    """Try the controller-only special motions and return observed samples.

    The primary motion is the game's documented down + punch shortcut.  The
    remaining quarter-circle and uppercut variants make this diagnostic if a
    character family chooses a different six-button route while preserving
    the public controller contract.
    """

    macros = (
        (("down",), ("down", 'y')),
        (("down",), ("down", "a")),
        (("down", "right"), ("down", "right", 'y')),
        (("down",), ("down", 'x')),
    )
    best: tuple[dict[str, int], list[dict[str, int]]] | None = None
    visual_frames: set[int] = set()
    before = state(e)
    for held, pressed in macros:
        # The libretro input callback is sampled at the core's frame boundary;
        # a one-frame edge can fall between polls on some Snes9x cadence
        # phases.  Hold the setup and button long enough for a real pad
        # sample, matching a player's sustained SNES input without changing
        # the game's edge-triggered move rules.
        e.run(4, p1=list(held))
        # Keep the sustained 18-frame button window, but inspect each native
        # PPU frame while it is held.  Rush specials expose their bank-1
        # active frame only briefly before the recovery frame in bank 4.
        samples: list[dict[str, int]] = []
        for _ in range(18):
            e.run(1, p1=list(pressed))
            sample = state(e)
            samples.append(sample)
            if fighter is not None:
                actual = uploaded_frame_id(e, fighter, 0)
                if actual is not None:
                    visual_frames.add(actual)
        manifested_at: int | None = None
        for _ in range(40):
            sample = state(e)
            samples.append(sample)
            if fighter is not None:
                actual = uploaded_frame_id(e, fighter, 0)
                if actual is not None:
                    visual_frames.add(actual)
            # Leave the emulator on the special pose so the following VRAM
            # assertion observes the one-actor-per-vblank upload, rather than
            # waiting until the animation has already returned to idle.
            displacement = abs(signed16(sample["x1"]) - signed16(before["x1"]))
            rising = signed16(sample["y1"]) < 0
            manifested = sample["wave1"] or (
                expected_family == 1 and sample["pose1"] >= 8 and displacement >= 8
            ) or (
                expected_family == 3 and sample["pose1"] >= 8 and rising
            )
            if manifested:
                # The renderer uploads one actor per vblank.  Keep sampling
                # a few frames after the trace-visible manifestation so the
                # exact active/cast bank can settle into VRAM before the
                # caller records its native frame ID.
                if manifested_at is None:
                    manifested_at = len(samples)
                elif len(samples) - manifested_at >= 4:
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
            return before, samples, visual_frames
        best = (before, samples)
        e.run(36)
    assert best is not None
    return best[0], best[1], visual_frames


def assert_special_family(e: Emulator, fighter: int) -> dict[str, object]:
    expected = SPECIAL_FAMILY[fighter]
    before, samples, visual_frames = trigger_special(e, expected, fighter)
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
        "visual_frames": sorted(visual_frames),
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
            e, 1, p1=["down", 'y'], p2=guard_keys
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
            e, 0, p1=[], p2=["down", 'y']
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
        banks = [expected_bank(fighter, bank)
                 for bank in range(ANIMATION_BANK_COUNT)]
        digests.append(hashlib.sha256(b"".join(banks)).hexdigest())
        check(len(banks) == ANIMATION_BANK_COUNT,
              "fighter has eight complete animation banks", {
                  "fighter": fighter, "banks": ANIMATION_BANK_COUNT,
              })
    check(len(set(digests)) == len(NAMES), "all twelve fighters have distinct native animation assets", {
        "unique_assets": len(set(digests)),
    })


def verify_p1_fighter(fighter: int) -> dict[str, object]:
    # Capture the first live frame before the slow idle loop can leave the
    # legacy frame-0 bank.  This keeps all six legacy native banks observable through
    # real controller transitions while later captures remain banner-free.
    e = boot(2, fighter, fighter % 3, quiet_frames=0)
    try:
        s0, bank0 = wait_for_uploaded_pose(e, fighter, 0)
        actual0 = uploaded_frame_id(e, fighter, 0)
        seen_banks: set[int] = set()
        if actual0 is not None:
            seen_banks.add(actual0 // 8)
        check(s0["selected"] == fighter, "menu selects requested fighter", {
            "fighter": fighter, "selected": s0["selected"],
        })
        check(actual0 in {0, 16, 17, 18, 19, 32} or bank0 in {0, 2},
              "idle frame uses a valid legacy or breathing animation bank", {
            "fighter": fighter, "pose": s0["pose1"], "frame": actual0,
            "bank": bank0,
        })
        check(actual0 is not None or actor_rows(e, fighter, 0, bank0, s0["pose1"]),
              "all ten idle sprite rows reach actor VRAM", {
            "fighter": fighter,
        })
        idle_oam = verify_oam_geometry(e, 0, "idle")
        idle_render = verify_rendered_actor(e, fighter, 0, idle_oam)
        e.run(3)
        idle_path = capture(e, fighter, "idle")
        idle_loop = observe_animation_loop(
            # Weighted breathing uses a complete 96-tick cycle; observe all
            # four approved frames through their unequal planted holds.
            e, fighter, 0, "idle breathing", (), {16, 17, 18, 19},
            frames=100, gif_label="idle-animation", minimum_distinct=4,
        )
        seen_banks.update(frame // 8 for frame in idle_loop["frames"])

        # The crouch, jump, and all six normal buttons must each upload the
        # exact native pose selected by the controller.  This catches a
        # renderer that only validates idle/special banks while a normal move
        # still points at a stale 64x80 or wrong-bank frame.
        e.run(3, p1=["down"])
        crouch_stream = stream_pose(e, fighter, 0, 3, "crouch", hold=("down",))
        seen_banks.add(crouch_stream["bank"])
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
        walk_forward = observe_animation_loop(
            e, fighter, 0, "forward walk", ("right",), set(range(20, 28)),
            frames=24, gif_label="walk-animation",
        )
        seen_banks.update(frame // 8 for frame in walk_forward["frames"])
        walk_back = observe_animation_loop(
            e, fighter, 0, "backward walk", ("left",), set(range(20, 28)),
            frames=24,
        )
        seen_banks.update(frame // 8 for frame in walk_back["frames"])

        e.run(3, p1=["up"])
        jump_stream = stream_pose(e, fighter, 0, 4, "jump", hold=("up",))
        seen_banks.add(jump_stream["bank"])
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
            ("y", 1, 5), ("x", 3, 6),
            ("b", 4, 7), ("a", 5, 7),
        ):
            # A one-frame edge can land between the libretro poll callbacks
            # at this point in the long roster stream.  Hold the physical
            # button for three frames, then release it while the action's
            # native startup/recovery remains edge-triggered.
            e.run(3, p1=[key])
            check(state(e)["action1"] == action,
                  "normal button starts action " + key.upper(), {
                      "fighter": fighter, "action": state(e)["action1"],
                  })
            normal_streams[key] = stream_pose(
                e, fighter, 0, pose, "normal " + key.upper(), hold=(key,))
            seen_banks.add(normal_streams[key]["bank"])
            # Observe extension and recovery as well as the first pose.
            # Weighted anticipation may occupy a transition bank at entry.
            native_frames = observed_animation_frames(e, fighter, 0, frames=50)
            seen_banks.update(frame // 8 for frame in native_frames)

        # Hold the transition across the libretro poll phase; the engine still
        # consumes only the edge and keeps the uppercut action active.
        e.run(3, p1=["down", 'x'])
        check(state(e)["action1"] == 8, "down plus heavy starts the uppercut", {
            "fighter": fighter, "action": state(e)["action1"],
        })
        uppercut_stream = stream_pose(e, fighter, 0, 13, "uppercut",
                                      hold=("down", 'x'))
        seen_banks.add(uppercut_stream["bank"])
        e.run(70)
        attack_gif = capture_animation_gif(e, fighter, "attack-animation", ("y",), 24)

        # Drive P1 all the way to the gameplay clamp so the left edge
        # exercises signed X9 coordinates and the native flip/palette bits.
        # Backward speed is profile-specific, so a fixed short duration can
        # stop well inside the screen for slower fighters such as Ivo.
        for _ in range(260):
            if signed16(state(e)["x1"]) <= 24 * 16:
                break
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
        seen_banks.update(frame // 8 for frame in special["visual_frames"])
        s_special, bank1 = wait_for_uploaded_pose(e, fighter, 0)
        special_frame = uploaded_frame_id(e, fighter, 0)
        if special_frame is not None:
            seen_banks.add(special_frame // 8)
        # The special family must reach a second-bank key pose at least once.
        check(s_special["pose1"] >= 8 or bank1 >= 1, "special reaches a non-idle animation bank", {
            "fighter": fighter, "pose": s_special["pose1"],
            "frame": special_frame, "bank": bank1,
        })
        check(special_frame is not None or actor_rows(e, fighter, 0, bank1, s_special["pose1"]),
              "all ten special sprite rows reach the native animation bank", {
                  "fighter": fighter, "bank": bank1,
              })
        capture(e, fighter, "special")

        check(set(range(6)).issubset(seen_banks),
              "controller transitions stream all six legacy animation banks", {
                  "fighter": fighter, "seen_banks": sorted(seen_banks),
              })

        profile_speed = side_field(s0, 0, "speed", "profile_speed", "profileSpeed")
        profile_jump = side_field(s0, 0, "jump", "jump_strength", "jumpStrength")
        return {
            "name": NAMES[fighter], "movement_delta": delta,
            "movement_samples": movement, "jump_height": jump_height,
            "speed_trace": profile_speed, "jump_trace": profile_jump,
            "special": special, "idle_screenshot": str(idle_path),
            "idle_render": idle_render,
            "idle_animation": idle_loop, "walk_forward": walk_forward,
            "walk_backward": walk_back, "attack_gif": str(attack_gif),
            "animation_banks": sorted(seen_banks),
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
        actual0 = uploaded_frame_id(e, fighter, 1)
        check(s0["selected2"] == fighter, "controller two selects requested fighter", {
            "fighter": fighter, "selected2": s0["selected2"],
        })
        check(actual0 is not None or actor_rows(e, fighter, 1, bank0, s0["pose2"]),
              "player two receives this fighter's native idle rows", {
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
        p2_frame = uploaded_frame_id(e, fighter, 1)
        check(p2_frame in set(range(20, 28)) or p2_frame in (1, 2),
              "player two walk streams an exact flipped animation frame", {
                  "fighter": fighter, "frame": p2_frame,
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
                "idle_frame": actual0, "walk_frame": p2_frame,
                "idle_floor": idle_oam["floor"], "idle_render": idle_render}
    finally:
        e.close()


def _drive_side(e: Emulator, side: int, keys: tuple[str, ...] | list[str],
                frames: int = 1) -> None:
    kwargs = {"p1" if side == 0 else "p2": list(keys)}
    e.run(frames, **kwargs)


def _wait_grounded(e: Emulator, side: int, max_frames: int = 100) -> None:
    key = "y1" if side == 0 else "y2"
    for _ in range(max_frames):
        if signed16(state(e)[key]) == 0:
            return
        _drive_side(e, side, ())
    raise AssertionError(("fighter did not return to the floor", side, state(e)))


def _air_normal(e: Emulator, fighter: int, side: int, key: str,
                expected: set[int], capture_gif: bool = False) -> dict[str, object]:
    """Capture one airborne normal's anticipation, active, and recovery art."""

    suffix = str(side + 1)
    y_key = f"y{suffix}"
    face_key = f"face{suffix}"
    action_index = {"y": 1, "x": 3, "b": 4, "a": 5}[key]
    before = state(e)
    face = before[face_key]
    _drive_side(e, side, ("up",), 3)
    airborne = False
    for _ in range(20):
        sample = state(e)
        if signed16(sample[y_key]) < 0:
            airborne = True
            break
        _drive_side(e, side, ())
    check(airborne, f"P{suffix} {key.upper()} jump reaches airborne state", {
        "fighter": fighter, "side": side, "trace": state(e),
    })

    seen: set[int] = set()
    latch_samples: list[dict[str, int]] = []
    captured: list[Image.Image] = []

    def observe(sample: dict[str, int]) -> None:
        if capture_gif and e.frame is not None:
            captured.append(e.frame.copy())
        actual = uploaded_frame_id(e, fighter, side)
        if actual is not None:
            seen.add(actual)
            if actual in expected:
                check(actor_rows(e, fighter, side, actual // 8, actual),
                      f"P{suffix} {key.upper()} air frame has exact native rows", {
                          "fighter": fighter, "side": side, "frame": actual,
                      })
        air_action = side_field(sample, side, "air_action", "airAction")
        if air_action:
            latch_samples.append(sample)
        if signed16(sample[y_key]) < 0 and air_action:
            check(sample[face_key] == face,
                  f"P{suffix} {key.upper()} air normal keeps takeoff facing", {
                      "fighter": fighter, "side": side, "face": sample[face_key],
                  })

    # Sustain the edge long enough for every libretro poll phase, while
    # observing each uploaded frame.  A three-frame hold can begin on the
    # final poll and otherwise hide the short anticipation drawing 49/52.
    for _ in range(6):
        _drive_side(e, side, (key,))
        observe(state(e))
    _drive_side(e, side, ())
    for _ in range(48):
        sample = state(e)
        observe(sample)
        _drive_side(e, side, ())
    check(expected.issubset(seen),
          f"P{suffix} {key.upper()} streams air anticipation/active/recovery", {
              "fighter": fighter, "side": side, "expected": sorted(expected),
              "seen": sorted(seen),
          })
    # The native latch is intentionally a boolean: the action itself remains
    # available in TRACE[10/11], while this field answers whether an airborne
    # normal is currently latched.  Do not infer a strength ID from it.
    check(any(side_field(sample, side, "air_action", "airAction") == 1
              for sample in latch_samples),
          f"P{suffix} {key.upper()} exposes its airborne action latch", {
              "fighter": fighter, "side": side, "air_action": 1,
              "samples": latch_samples[:4],
          })
    _wait_grounded(e, side)
    landed = state(e)
    check(landed[f"action{suffix}"] == 0 and
          (side_field(landed, side, "air_action", "airAction") or 0) == 0,
          f"P{suffix} {key.upper()} air attack finishes on landing", landed)
    gif_path = None
    if captured:
        gif_path = str(save_animation_gif(
            fighter, f"p{side + 1}-air-{key}", captured))
    return {"key": key, "action": action_index, "frames": sorted(seen),
            "latch_samples": len(latch_samples), "facing": face,
            "gif": gif_path}


def _close_for_throw(e: Emulator) -> int:
    """Bring both idle actors inside the strict throw range."""

    for _ in range(220):
        sample = state(e)
        distance = abs(signed16(sample["x2"]) - signed16(sample["x1"]))
        # canHit() uses a strict '< throwRange' comparison.  Closing against
        # a generic 26px threshold leaves Cristobal and other 25px profiles
        # exactly on the rejected edge, especially for left-facing P2.
        limit = min(sample["throw_range1"], sample["throw_range2"]) * 16
        if distance < limit:
            return distance
        if sample["x1"] < sample["x2"]:
            e.run(1, p1=["right"], p2=["left"])
        else:
            e.run(1, p1=["left"], p2=["right"])
    raise AssertionError(("fighters did not reach throw range", state(e)))


def _throw_sequence(e: Emulator, fighter: int, attacker: int,
                    capture_gif: bool = False) -> dict[str, object]:
    """Observe distinct thrower/victim frames and delayed ground damage."""

    distance = _close_for_throw(e)
    before = state(e)
    attacker_suffix = str(attacker + 1)
    victim = 1 - attacker
    victim_suffix = str(victim + 1)
    forward = "right" if before[f"face{attacker_suffix}"] else "left"
    _drive_side(e, attacker, (forward, 'x'), 3)
    frames_attacker: set[int] = set()
    frames_victim: set[int] = set()
    down_states: list[int] = []
    hp_before = before[f"hp{victim_suffix}"]
    hp_drop_state: int | None = None
    pending_samples: list[dict[str, int]] = []
    captured: list[Image.Image] = []
    for _ in range(120):
        sample = state(e)
        if capture_gif and e.frame is not None:
            captured.append(e.frame.copy())
        actual_attacker = uploaded_frame_id(e, fighter, attacker)
        actual_victim = uploaded_frame_id(e, fighter, victim)
        if actual_attacker is not None:
            frames_attacker.add(actual_attacker)
        if actual_victim is not None:
            frames_victim.add(actual_victim)
        down = sample[f"down_state{victim_suffix}"]
        down_states.append(down)
        if sample[f"hp{victim_suffix}"] < hp_before and hp_drop_state is None:
            hp_drop_state = down
        if (sample[f"pending_throw_damage{victim_suffix}"] or
                sample[f"pending_throw_damage{attacker_suffix}"]):
            pending_samples.append(sample)
        if down == 0 and frames_victim and len(down_states) > 12:
            break
        _drive_side(e, attacker, ())
    check(frames_attacker & THROW_FRAMES,
          f"P{attacker_suffix} thrower streams distinct grip/release frames", {
              "fighter": fighter, "frames": sorted(frames_attacker),
          })
    check(frames_victim & {58, 59},
          f"P{victim_suffix} victim streams lifted/impact frames", {
              "fighter": fighter, "frames": sorted(frames_victim),
          })
    check(frames_victim & KNOCKDOWN_FRAMES,
          f"P{victim_suffix} victim streams bounded knockdown/get-up frames", {
              "fighter": fighter, "frames": sorted(frames_victim),
          })
    check(any(state_value in (1, 2, 3, 4, 5) for state_value in down_states),
          f"P{victim_suffix} enters a bounded downed/wake state", {
              "fighter": fighter, "states": down_states,
          })
    check(set(down_states).issubset({0, 1, 2, 3, 4, 5}),
          f"P{victim_suffix} downed state stays within the public enum", {
              "fighter": fighter, "states": sorted(set(down_states)),
          })
    if hp_drop_state is not None:
        check(hp_drop_state >= 3,
              f"P{victim_suffix} throw damage waits for ground impact", {
                  "fighter": fighter, "down_state_at_damage": hp_drop_state,
              })
    check(pending_samples and any(
        sample[f"throw_owner{victim_suffix}"] == attacker or
        sample[f"throw_owner{attacker_suffix}"] == attacker
        for sample in pending_samples),
          f"P{victim_suffix} exposes delayed throw owner/damage telemetry", {
              "fighter": fighter,
              "pending": pending_samples[:5],
          })
    check(any(sample[f"throw_victim{attacker_suffix}"] == victim
              for sample in pending_samples),
          f"P{attacker_suffix} exposes the distinct throw victim role", {
              "fighter": fighter, "victim": victim,
              "pending": pending_samples[:5],
          })
    gif_path = None
    if captured:
        gif_path = str(save_animation_gif(
            fighter, f"p{attacker + 1}-throw-sequence", captured))
    return {"attacker": attacker, "victim": victim, "distance_12_4": distance,
            "attacker_frames": sorted(frames_attacker),
            "victim_frames": sorted(frames_victim),
            "down_states": down_states, "damage_state": hp_drop_state,
            "gif": gif_path}


def verify_airborne_and_throw(fighter: int) -> dict[str, object]:
    """Exercise all four air normals in both facings and both throw roles."""

    e = boot(1, fighter, fighter % 3, fighter)
    try:
        air_results: dict[str, object] = {}
        for side in (0, 1):
            for key in ("y", "x"):
                air_results[f"p{side + 1}-{key}"] = _air_normal(
                    e, fighter, side, key, AIR_PUNCH_FRAMES,
                    capture_gif=(key == "y" and (side == 0 or fighter == 0)))
            for key in ("b", "a"):
                air_results[f"p{side + 1}-{key}"] = _air_normal(
                    e, fighter, side, key, AIR_KICK_FRAMES,
                    capture_gif=(key == "b" and (side == 0 or fighter == 0)))
        # Every fighter gets a source-actual PPU throw capture for the review
        # set; the separate P2 representative below keeps the flipped OAM
        # block covered without doubling the full twelve-fighter run.
        throw_results = [_throw_sequence(e, fighter, 0, capture_gif=True)]
    finally:
        e.close()

    # A fresh round makes P2 the thrower, preserving an independent victim
    # sequence and proving the flipped G/H art in the other OAM block.
    e = boot(1, fighter, fighter % 3, fighter)
    try:
        throw_results.append(_throw_sequence(e, fighter, 1, capture_gif=(fighter == 0)))
    finally:
        e.close()
    return {"air_normals": air_results, "throws": throw_results}


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
        "airborne_throw": {},
        "guard_checks": {},
        "player_two_specials": {},
    }
    try:
        manifest = json.loads((ROOT / "dist/manifest.json").read_text())
        report["rom_sha256"] = manifest["sha256"]
        report["rom_bytes"] = manifest.get("bytes")
        check(manifest.get("bytes") == 4 * 1024 * 1024,
              "release manifest records the 4 MiB FastROM animation image", {
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

        # Every fighter's G/H banks are exercised through controller-driven
        # air normals in both facings, followed by distinct thrower/victim
        # sequences.  The exact payload checks remain in uploaded_frame_id and
        # actor_rows; this result only records the observed native frame IDs.
        airborne_results: dict[str, object] = {}
        for fighter in range(len(NAMES)):
            airborne_results[f"{fighter:02}"] = verify_airborne_and_throw(fighter)
        report["airborne_throw"] = airborne_results

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
