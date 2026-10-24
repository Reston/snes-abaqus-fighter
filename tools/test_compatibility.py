"""Independent-engine smoke, stage dynamics, and neutral cadence test.

The pinned path is deliberately fixed to the official Libretro
bsnes2014 Accuracy Windows x64 core.  This host drives only the standard
Libretro controller callbacks, captures video and PCM in memory, and reads
the cartridge's public WRAM trace.  It never writes emulated memory, creates
a save state, opens an audio device, or creates a frontend window.
"""

from __future__ import annotations

import ctypes as C
import hashlib
import json
import sys
import zipfile
from pathlib import Path

from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parent))
from stage_test_contract import depth_manifest


ROOT = Path(__file__).resolve().parents[1]
ROM_PATH = ROOT / "dist" / "abaqus-after-hours.sfc"
MANIFEST_PATH = ROOT / "dist" / "manifest.json"
COMPAT_ROOT = ROOT / ".tools" / "compat"
CORE_ARCHIVE = COMPAT_ROOT / "bsnes2014_accuracy_libretro.dll.zip"
CORE_PATH = COMPAT_ROOT / "bsnes2014-accuracy" / "bsnes2014_accuracy_libretro.dll"
CAPTURE_ROOT = ROOT / "docs" / "screenshots" / "compatibility"
REPORT_PATH = ROOT / "docs" / "compatibility-test-report.json"
STAGE_MANIFEST_PATH = ROOT / "assets" / "generated" / "stage-dynamics.json"

CORE_URL = (
    "https://buildbot.libretro.com/nightly/windows/x86_64/latest/"
    "bsnes2014_accuracy_libretro.dll.zip"
)
CORE_ARCHIVE_SHA256 = "CB1211AE6B6838ED60BEB7CC8AE5AD8074327733F1042CCC8BABA32A62C6D18C"
CORE_DLL_SHA256 = "F2AAC1DDB314A001467A26B56604020F0A29C3A4DD1658B072884ACE75343CF4"
ROM_BYTES = 4 * 1024 * 1024
TRACE_OFFSET = 0x1FF00
TRACE_WORDS = 119
TRACE_BYTES = TRACE_WORDS * 2
PHASE_COUNT = 4
PHASE_PERIOD_FRAMES = 16
STAGE_COUNT = 3
SCOPE = (
    "independent-engine smoke, stage ambient/effects freeze, "
    "synchronized low-wave, neutral600frame cadence"
)

BUTTONS = {
    "b": 0,
    "y": 1,
    "select": 2,
    "start": 3,
    "up": 4,
    "down": 5,
    "left": 6,
    "right": 7,
    "a": 8,
    "x": 9,
    "l": 10,
    "r": 11,
}

TRACE_NAMES = (
    "magic", "screen", "frame", "mode", "hp1", "hp2", "x1", "x2",
    "y1", "y2", "action1", "action2", "wins1", "wins2", "arena",
    "round", "intro", "paused", "energy1", "energy2", "wave1", "wave2",
    "selected", "selected2", "arcade", "seconds", "pose1", "pose2",
    "round_end", "hitstop", "combo", "champion", "fighter_id1",
    "fighter_id2", "family1", "family2", "speed1", "speed2", "jump1",
    "jump2", "face1", "face2", "back_speed1", "back_speed2",
    "special_startup1", "special_startup2", "special_active1",
    "special_active2", "special_recovery1", "special_recovery2",
    "special_damage1", "special_damage2", "special_reach1", "special_reach2",
    "throw_range1", "throw_range2", "wave_low1", "wave_low2", "wave_speed1",
    "wave_speed2", "wave_life1", "wave_life2", "anim_frame1", "anim_frame2",
    "anim_state1", "anim_state2", "anim_tick1", "anim_tick2",
    "buffered_action1", "buffered_action2", "buffer_age1", "buffer_age2",
    "jump_buffer1", "jump_buffer2", "command_stage1", "command_stage2",
    "raw_keys1", "raw_keys2", "landing1", "landing2", "jump_vx1", "jump_vx2",
    "hurt1", "hurt2", "guard1", "guard2", "connected1", "connected2",
    "combo_link1", "combo_link2", "chain_timer1", "chain_timer2", "counter1",
    "counter2", "down_state1", "down_state2", "down_tick1", "down_tick2",
    "invuln1", "invuln2", "pending_throw_damage1", "pending_throw_damage2",
    "throw_owner1", "throw_owner2", "air_action1", "air_action2",
    "throw_victim1", "throw_victim2", "wake_action1", "wake_action2",
    "wake_age1", "wake_age2", "wake_jump1", "wake_jump2",
    "ppu_stat", "ambient_phase", "ambient_clock", "ambient_pending_phase",
    "ambient_phase_age",
)


class GameInfo(C.Structure):
    _fields_ = [
        ("path", C.c_char_p),
        ("data", C.c_void_p),
        ("size", C.c_size_t),
        ("meta", C.c_char_p),
    ]


class SystemInfo(C.Structure):
    _fields_ = [
        ("library_name", C.c_char_p),
        ("library_version", C.c_char_p),
        ("valid_extensions", C.c_char_p),
        ("need_fullpath", C.c_bool),
        ("block_extract", C.c_bool),
    ]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def signed16(value: int) -> int:
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


TRACE_DEFAULTS = {
    "ppu_stat": 114,
    "ambient_phase": 115,
    "ambient_clock": 116,
    "ambient_pending_phase": 117,
    "ambient_phase_age": 118,
}


def normalize_patch_cells(value: object) -> list[int]:
    """Normalize manifest BG1 map cells to 32x32 word indices."""

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


def stage_patch_rects(record: dict[str, object]) -> list[tuple[int, int, int, int]]:
    """Return native 256x224 screen rectangles affected by the ambient patch."""

    configured = record.get("screen_rects", record.get("patch_rects", []))
    rects: list[tuple[int, int, int, int]] = []
    if isinstance(configured, list):
        for item in configured:
            if isinstance(item, (list, tuple)) and len(item) == 4:
                rects.append(tuple(int(value) for value in item))
    if rects:
        return rects

    cells = normalize_patch_cells(record.get(
        "patch_cells", record.get("map_cells",
                                    record.get("dynamic_cells", record.get("cells", [])))))
    return [((cell % 32) * 8, (cell // 32) * 8,
             (cell % 32 + 1) * 8, (cell // 32 + 1) * 8)
            for cell in cells]


def stage_phase_probe_rects(record: dict[str, object]) -> list[tuple[int, int, int, int]]:
    """Use manifest changed-pixel bounds to avoid actor/effect pixels in freezes."""

    cells = record.get("cells", [])
    high_slots: set[int] | None = None
    if isinstance(cells, list):
        selected: set[int] = set()
        for cell in cells:
            if not isinstance(cell, dict) or "slot" not in cell:
                continue
            try:
                slot = int(cell["slot"])
                native_y = int(cell.get("native_y", int(cell.get("y", 0)) * 8))
            except (TypeError, ValueError):
                continue
            # Keep only the unobscured high patch for actual video matching:
            # y48 tree, y80 lights, and y104 monitors.  Ground reflection
            # cells are intentionally excluded because actor/effect OBJ can
            # cover them during a freeze.
            if native_y <= 104:
                selected.add(slot)
        if selected:
            high_slots = selected

    rects: list[tuple[int, int, int, int]] = []
    phases = record.get("phases", [])
    if isinstance(phases, list):
        for phase in phases[1:]:
            if not isinstance(phase, dict):
                continue
            cells = phase.get("cells", [])
            if not isinstance(cells, list):
                continue
            for cell in cells:
                if not isinstance(cell, dict):
                    continue
                if high_slots is not None:
                    try:
                        if int(cell.get("slot", -1)) not in high_slots:
                            continue
                    except (TypeError, ValueError):
                        continue
                bounds = cell.get("pixel_bounds")
                if not isinstance(bounds, dict):
                    continue
                try:
                    left = int(bounds["left"])
                    top = int(bounds["top"])
                    right = int(bounds["right"]) + 1
                    bottom = int(bounds["bottom"]) + 1
                except (KeyError, TypeError, ValueError):
                    continue
                if 0 <= left < right <= 256 and 0 <= top < bottom <= 224:
                    rects.append((left, top, right, bottom))
    return rects or stage_patch_rects(record)


def stage_slug(record: dict[str, object], stage_id: int) -> str:
    default = ("las-condes", "el-castillo", "la-oficina")[stage_id]
    value = record.get("slug", record.get("name", default))
    return str(value).lower().replace(" ", "-")


def load_stage_dynamics() -> tuple[dict[str, object], dict[str, int], dict[int, dict[str, object]]]:
    """Validate the generated stage contract before starting the core."""

    depth=depth_manifest(ROOT)
    if depth is not None:
        return depth, dict(TRACE_DEFAULTS), {row['id']:row for row in depth['stages']}
    require(STAGE_MANIFEST_PATH.exists(),
            f"missing stage dynamics manifest: {STAGE_MANIFEST_PATH}")
    manifest = json.loads(STAGE_MANIFEST_PATH.read_text(encoding="utf-8"))
    require(int(manifest.get("phase_count", PHASE_COUNT)) == PHASE_COUNT,
            "stage dynamics manifest must declare four ambient phases")
    require(int(manifest.get("tile_count", 0)) == 8,
            "stage dynamics manifest must declare eight streamed tiles")
    require(int(manifest.get("bytes_per_phase", 0)) == 256,
            "stage dynamics manifest must declare 256 bytes per phase")
    require(int(manifest.get("ambient_vram_word", 0)) == 0x3C00,
            "stage dynamics must upload at BG1 VRAM word $3C00")
    phase_period = manifest.get(
        "phase_period_frames",
        manifest.get("clock_frames_per_phase",
                     manifest.get("phase_period",
                                  manifest.get("phase_ticks",
                                              manifest.get("clock_frames", PHASE_PERIOD_FRAMES)))))
    require(int(phase_period) == PHASE_PERIOD_FRAMES,
            f"stage ambient clock must hold each phase for {PHASE_PERIOD_FRAMES} live frames")
    trace_map = dict(TRACE_DEFAULTS)
    configured_trace = manifest.get("trace", {})
    if isinstance(configured_trace, dict):
        aliases = {
            "ppu_stat": ("ppu_stat", "status"),
            "ambient_phase": ("ambient_phase", "uploaded_phase"),
            "ambient_clock": ("ambient_clock",),
            "ambient_pending_phase": ("ambient_pending_phase", "pending_phase"),
            "ambient_phase_age": ("ambient_phase_age", "pending_age"),
        }
        for name, keys in aliases.items():
            for key in keys:
                if key in configured_trace:
                    trace_map[name] = int(configured_trace[key])
                    break
    require(trace_map == TRACE_DEFAULTS,
            f"stage telemetry must use trace words 114..118: {trace_map!r}")

    raw_stages = manifest.get("stages")
    require(isinstance(raw_stages, list) and len(raw_stages) == STAGE_COUNT,
            "stage dynamics manifest must contain exactly three stages")
    records: dict[int, dict[str, object]] = {}
    assert isinstance(raw_stages, list)
    for raw in raw_stages:
        require(isinstance(raw, dict), "stage dynamics entries must be objects")
        assert isinstance(raw, dict)
        stage_id = int(raw.get("id", raw.get("stage_id", raw.get("record_id", -1))))
        require(0 <= stage_id < STAGE_COUNT,
                f"stage dynamics id is outside 0..{STAGE_COUNT - 1}: {stage_id}")
        require(stage_id not in records,
                f"stage dynamics repeats stage id {stage_id}")
        phases = raw.get("phases", raw.get("phase_assets", []))
        require(isinstance(phases, list) and len(phases) == PHASE_COUNT,
                f"stage {stage_id} must declare four phase assets")
        require(int(raw.get("tile_count", 0)) == 8 and
                int(raw.get("bytes_per_phase", 0)) == 256 and
                int(raw.get("ambient_vram_word", 0)) == 0x3C00,
                f"stage {stage_id} has an invalid native ambient upload contract")
        phase_hashes = [item.get("sha256") for item in phases
                        if isinstance(item, dict)]
        require(len(phase_hashes) == PHASE_COUNT and
                len(set(phase_hashes)) == PHASE_COUNT,
                f"stage {stage_id} phase assets are not four distinct blocks")
        cells = raw.get("cells", [])
        require(isinstance(cells, list) and len(cells) == 8,
                f"stage {stage_id} must declare eight ambient map cells")
        rects = stage_patch_rects(raw)
        require(bool(rects), f"stage {stage_id} must declare ambient screen rects or map cells")
        require(all(0 <= left < right <= 256 and 0 <= top < bottom <= 224
                    for left, top, right, bottom in rects),
                f"stage {stage_id} has an invalid 256x224 ambient screen rect")
        records[stage_id] = raw
    require(set(records) == set(range(STAGE_COUNT)),
            f"stage dynamics ids are not exactly 0, 1, 2: {sorted(records)}")
    return manifest, trace_map, records


def patch_digest(image: Image.Image | None,
                 rects: list[tuple[int, int, int, int]]) -> str:
    """Hash only the authored ambient patch in the actual video callback."""

    require(image is not None, "independent core produced no PPU frame")
    require(bool(rects), "ambient patch has no screen rectangles")
    assert image is not None
    rgb = image.convert("RGB")
    # Libretro may expose the native 256-wide picture or a 2x horizontal
    # callback.  Manifest rectangles are always expressed in native pixels.
    x_scale = rgb.width / 256.0
    chunks: list[bytes] = []
    for left, top, right, bottom in rects:
        x0 = max(0, min(rgb.width, int(round(left * x_scale))))
        x1 = max(0, min(rgb.width, int(round(right * x_scale))))
        y0 = max(0, min(rgb.height, int(top)))
        y1 = max(0, min(rgb.height, int(bottom)))
        require(x0 < x1 and y0 < y1, "ambient patch rectangle is outside the PPU frame")
        chunks.append(rgb.crop((x0, y0, x1, y1)).tobytes())
    return hashlib.sha256(b"".join(chunks)).hexdigest()


def camera_aligned_patch_match(before: Image.Image | None,
                               after: Image.Image | None,
                               rects: list[tuple[int, int, int, int]]) -> int | None:
    """Find one global native-pixel alignment for all ambient patch rects."""

    require(before is not None and after is not None,
            "independent core produced no PPU frame for camera normalization")
    require(before.size == after.size, "camera normalization received different PPU sizes")
    assert before is not None and after is not None
    before_rgb = before.convert("RGB")
    after_rgb = after.convert("RGB")
    x_scale = before_rgb.width / 256.0
    # Directional impacts include one-pixel steps; the full delta stays <=4.
    for shift in range(-4, 5):
        matched = True
        for left, top, right, bottom in rects:
            bx0 = int(round(left * x_scale))
            bx1 = int(round(right * x_scale))
            by0, by1 = int(top), int(bottom)
            ax0 = int(round((left + shift) * x_scale))
            ax1 = int(round((right + shift) * x_scale))
            if ax0 < 0 or ax1 > after_rgb.width:
                matched = False
                break
            if before_rgb.crop((bx0, by0, bx1, by1)).tobytes() != \
                    after_rgb.crop((ax0, by0, ax1, by1)).tobytes():
                matched = False
                break
        if matched:
            return shift
    return None


def static_plate_color_agreement(core: "Probe", stage_id: int,
                                 record: dict[str, object]) -> dict[str, object]:
    """Compare the unobscured upper stage plate with its native RGB master.

    The generated stage PNG is the decoded native 256x224 plate.  The
    independent core currently duplicates each native pixel horizontally in a
    512-wide callback, so compare the mean of the callback pixels covering
    each native x coordinate.  The y40..100 band stays above the fighters and
    interface; all eight authored ambient cells are excluded even when they
    are below that band.  SNES RGB quantization is accepted up to eight levels
    per channel, with a sixteen-level guard for a small residual mismatch.
    """

    master_path = ROOT / "assets" / "generated" / f"stage{stage_id}.png"
    require(master_path.exists(), f"missing generated stage master: {master_path}")
    expected = Image.open(master_path).convert("RGB")
    require(expected.size == (256, 224),
            f"stage {stage_id} master is not native 256x224: {expected.size}")
    require(core.frame_image is not None,
            f"stage {stage_id} produced no video frame for static plate check")
    observed = core.frame_image.convert("RGB")
    require(observed.height >= 101 and observed.width >= 256,
            f"stage {stage_id} callback is too small for static plate check: {observed.size}")
    x_scale = observed.width / 256.0
    dynamic: list[tuple[int, int, int, int]] = []
    cells = record.get("cells", [])
    if isinstance(cells, list):
        for cell in cells:
            if not isinstance(cell, dict):
                continue
            try:
                left_value = cell.get("native_x")
                top_value = cell.get("native_y")
                if left_value is None:
                    left_value = int(cell["x"]) * 8
                if top_value is None:
                    top_value = int(cell["y"]) * 8
                left = int(left_value)
                top = int(top_value)
            except (KeyError, TypeError, ValueError):
                continue
            dynamic.append((left, top, left + 8, top + 8))

    def in_dynamic(x: int, y: int) -> bool:
        return any(left <= x < right and top <= y < bottom
                   for left, top, right, bottom in dynamic)

    count = 0
    within8 = 0
    within16 = 0
    max_delta = 0
    total_delta = 0
    for y in range(40, 101):
        for x in range(256):
            if in_dynamic(x, y):
                continue
            x0 = max(0, min(observed.width - 1, int(round(x * x_scale))))
            x1 = max(x0 + 1, min(observed.width, int(round((x + 1) * x_scale))))
            pixels = [observed.getpixel((sample_x, y))
                      for sample_x in range(x0, x1)]
            actual = tuple(sum(pixel[channel] for pixel in pixels) // len(pixels)
                           for channel in range(3))
            wanted = expected.getpixel((x, y))
            delta = max(abs(actual[channel] - wanted[channel]) for channel in range(3))
            total_delta += delta
            max_delta = max(max_delta, delta)
            count += 1
            within8 += delta <= 8
            within16 += delta <= 16
    require(count >= 10000,
            f"stage {stage_id} static plate sample is too small: {count}")
    ratio8 = within8 / count
    ratio16 = within16 / count
    require(ratio8 >= 0.99,
            f"stage {stage_id} static plate RGB agreement below 99% at <=8: "
            f"{within8}/{count} ({ratio8:.4f})")
    require(ratio16 == 1.0,
            f"stage {stage_id} static plate has >16 RGB error: "
            f"{within16}/{count} ({ratio16:.4f})")
    return {
        "master": str(master_path.relative_to(ROOT)).replace("\\", "/"),
        "region_native": [0, 40, 256, 101],
        "excluded_dynamic_cells": len(dynamic),
        "sample_count": count,
        "within_8": within8,
        "within_16": within16,
        "match_ratio_le_8": ratio8,
        "match_ratio_le_16": ratio16,
        "max_channel_delta": max_delta,
        "mean_max_channel_delta": total_delta / count,
        "callback_width": observed.width,
        "horizontal_scale": x_scale,
        "passed": True,
    }


def verify_manifest_and_pinned_core() -> dict[str, object]:
    """Verify every release input before loading the independent DLL."""

    require(MANIFEST_PATH.exists(), f"missing ROM manifest: {MANIFEST_PATH}")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    require(ROM_PATH.exists(), f"missing ROM: {ROM_PATH}")
    actual_rom_hash = sha256(ROM_PATH)
    require(manifest.get("bytes") == ROM_BYTES,
            f"manifest ROM size is not {ROM_BYTES}: {manifest.get('bytes')!r}")
    manifest_hash = str(manifest.get("sha256", "")).upper()
    require(len(manifest_hash) == 64,
            "manifest does not contain a 64-character ROM SHA256")
    require(ROM_PATH.stat().st_size == ROM_BYTES,
            f"ROM size is not {ROM_BYTES}: {ROM_PATH.stat().st_size}")
    require(actual_rom_hash == manifest_hash,
            "manifest ROM SHA256 does not match the current ROM bytes")

    require(CORE_ARCHIVE.exists(), f"missing pinned core archive: {CORE_ARCHIVE}")
    actual_archive_hash = sha256(CORE_ARCHIVE)
    require(actual_archive_hash == CORE_ARCHIVE_SHA256,
            "pinned bsnes2014 archive hash mismatch; the rolling official URL "
            "changed or the cache is stale")
    with zipfile.ZipFile(CORE_ARCHIVE) as archive:
        names = [item.filename for item in archive.infolist() if not item.is_dir()]
    require(names == ["bsnes2014_accuracy_libretro.dll"],
            f"unexpected files in pinned core archive: {names!r}")

    require(CORE_PATH.exists(), f"missing extracted core DLL: {CORE_PATH}")
    actual_dll_hash = sha256(CORE_PATH)
    require(actual_dll_hash == CORE_DLL_SHA256,
            "pinned bsnes2014 DLL hash mismatch; run tools/setup-compat.ps1")
    return {
        "rom_sha256": actual_rom_hash.lower(),
        "manifest_sha256": manifest_hash.lower(),
        "rom_bytes": ROM_BYTES,
        "archive_sha256": actual_archive_hash,
        "dll_sha256": actual_dll_hash,
    }


class Probe:
    """Minimal callback-only Libretro host for the pinned core."""

    active = None

    def __init__(self) -> None:
        if Probe.active is not None:
            raise RuntimeError("only one independent core instance is supported")
        self.core = C.CDLL(str(CORE_PATH))
        self.closed = False
        self.loaded = False
        self.held = [set(), set()]
        self.pixel_format = 0
        self.frame_image: Image.Image | None = None
        self.width = 0
        self.height = 0
        self.pitch = 0
        self.raw_prefix = b""
        self.last_raw = b""
        self.video_format_history: list[dict[str, int]] = []
        self.video_callbacks = 0
        self.audio_samples = 0
        self.audio_energy = 0
        self.audio_peak = 0
        self.directory = str(COMPAT_ROOT).encode("utf-8")

        ENV = C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p)
        VIDEO = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t)
        AUDIO = C.CFUNCTYPE(None, C.c_int16, C.c_int16)
        BATCH = C.CFUNCTYPE(C.c_size_t, C.POINTER(C.c_int16), C.c_size_t)
        POLL = C.CFUNCTYPE(None)
        INPUT = C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint)

        def environment(command: int, data: C.c_void_p) -> bool:
            command &= 0xFFFF
            if command == 10 and data:  # SET_PIXEL_FORMAT
                self.pixel_format = C.cast(data, C.POINTER(C.c_uint))[0]
                return True
            if command == 2 and data:  # GET_OVERSCAN
                C.cast(data, C.POINTER(C.c_bool))[0] = False
                return True
            if command == 3 and data:  # GET_CAN_DUPE
                C.cast(data, C.POINTER(C.c_bool))[0] = True
                return True
            if command == 17 and data:  # GET_VARIABLE_UPDATE
                C.cast(data, C.POINTER(C.c_bool))[0] = False
                return True
            if command == 24 and data:  # GET_INPUT_DEVICE_CAPABILITIES
                C.cast(data, C.POINTER(C.c_uint))[0] = 0
                return True
            if command in (9, 30, 31) and data:  # private system/core/save paths
                C.cast(data, C.POINTER(C.c_char_p))[0] = self.directory
                return True
            if command == 15:  # GET_VARIABLE: use the core defaults
                return False
            return command in (1, 6, 11, 16, 18, 35, 37, 39, 44, 52, 53, 63)

        def video(data: C.c_void_p, width: int, height: int, pitch: int) -> None:
            if not data or not width or not height:
                return
            raw = C.string_at(data, pitch * height)
            self.raw_prefix = raw[:64]
            self.last_raw = raw
            self.video_format_history.append({
                "pixel_format": int(self.pixel_format),
                "width": int(width),
                "height": int(height),
                "pitch": int(pitch),
            })
            # bsnes2014 Accuracy reports RETRO_PIXEL_FORMAT_0RGB1555 but
            # this Windows build supplies four bytes per callback pixel.  The
            # callback stride is authoritative: decoding it as a 16-bit
            # buffer produces alternating vertical stripes.  On the actual
            # pinned DLL the four bytes are little-endian B,G,R,X.
            if pitch >= int(width) * 4:
                image = Image.frombytes("RGB", (width, height), raw,
                                        "raw", "BGRX", pitch)
            elif self.pixel_format == 1:  # XRGB8888
                image = Image.frombytes("RGB", (width, height), raw,
                                        "raw", "BGRX", pitch)
            elif self.pixel_format == 2:  # RGB565
                image = Image.frombytes("RGB", (width, height), raw,
                                        "raw", "BGR;16", pitch)
            else:  # 0RGB1555
                image = Image.frombytes("RGB", (width, height), raw,
                                        "raw", "BGR;15", pitch)
            self.frame_image = image
            self.width = int(width)
            self.height = int(height)
            self.pitch = int(pitch)
            self.video_callbacks += 1

        def audio_sample(left: int, right: int) -> None:
            left = int(left)
            right = int(right)
            self.audio_peak = max(self.audio_peak, abs(left), abs(right))
            self.audio_energy += left * left + right * right
            self.audio_samples += 2

        def audio_batch(data: C.POINTER(C.c_int16), frames: int) -> int:
            if data and frames:
                values = C.cast(data, C.POINTER(C.c_int16 * (frames * 2))).contents
                for value in values:
                    integer = int(value)
                    self.audio_peak = max(self.audio_peak, abs(integer))
                    self.audio_energy += integer * integer
                self.audio_samples += int(frames) * 2
            return int(frames)

        def input_state(port: int, device: int, index: int, button: int) -> int:
            return int(port < 2 and button in self.held[port])

        self.callbacks = [
            ENV(environment), VIDEO(video), AUDIO(audio_sample),
            BATCH(audio_batch), POLL(lambda: None), INPUT(input_state),
        ]
        for name, callback in zip(
            ("environment", "video_refresh", "audio_sample",
             "audio_sample_batch", "input_poll", "input_state"),
            self.callbacks,
        ):
            getattr(self.core, "retro_set_" + name)(callback)

        self.core.retro_get_system_info.argtypes = [C.POINTER(SystemInfo)]
        self.core.retro_get_system_info.restype = None
        info = SystemInfo()
        self.core.retro_get_system_info(C.byref(info))
        self.library_name = (info.library_name or b"").decode("utf-8", "replace")
        self.library_version = (info.library_version or b"").decode("utf-8", "replace")
        self.core.retro_init()

        self.core.retro_load_game.argtypes = [C.POINTER(GameInfo)]
        self.core.retro_load_game.restype = C.c_bool
        self.core.retro_get_memory_data.argtypes = [C.c_uint]
        self.core.retro_get_memory_data.restype = C.c_void_p
        self.core.retro_get_memory_size.argtypes = [C.c_uint]
        self.core.retro_get_memory_size.restype = C.c_size_t
        rom = C.create_string_buffer(ROM_PATH.read_bytes())
        self.rom = rom
        game = GameInfo(str(ROM_PATH).encode(), C.cast(rom, C.c_void_p),
                        len(rom) - 1, None)
        require(self.core.retro_load_game(C.byref(game)),
                "bsnes2014 Accuracy rejected the frozen ROM")
        self.loaded = True
        self.core.retro_set_controller_port_device.argtypes = [C.c_uint, C.c_uint]
        self.core.retro_set_controller_port_device(0, 1)
        self.core.retro_set_controller_port_device(1, 1)
        self.ram = self.core.retro_get_memory_data(2)
        self.ram_size = int(self.core.retro_get_memory_size(2))
        require(self.ram and self.ram_size >= TRACE_OFFSET + TRACE_BYTES,
                f"independent core WRAM trace unavailable: {self.ram_size} bytes")
        Probe.active = self

    def run(self, count: int = 1, p1=(), p2=()) -> dict[str, int]:
        require(not self.closed, "cannot run a closed core")
        self.held = [{BUTTONS[key] for key in p1}, {BUTTONS[key] for key in p2}]
        for _ in range(count):
            self.core.retro_run()
        return self.state()

    def state(self) -> dict[str, int]:
        require(not self.closed, "cannot read a closed core")
        words = self.trace_words()
        return dict(zip(TRACE_NAMES, words))

    def trace_words(self, count: int = TRACE_WORDS) -> list[int]:
        require(not self.closed, "cannot read a closed core")
        data = C.string_at(self.ram + TRACE_OFFSET, count * 2)
        words = [
            int.from_bytes(data[offset:offset + 2], "little")
            for offset in range(0, count * 2, 2)
        ]
        return words

    def frame_signature(self) -> dict[str, object]:
        require(self.frame_image is not None, "independent core produced no video")
        rgb = self.frame_image.tobytes()
        sampled = rgb[::max(1, len(rgb) // 4096)]
        distinct = len({sampled[i:i + 3] for i in range(0, len(sampled) - 2, 3)})
        nonzero = sum(1 for value in rgb if value)
        signature = {
            "width": self.width,
            "height": self.height,
            "pitch": self.pitch,
            "sha256_rgb": hashlib.sha256(rgb).hexdigest(),
            "distinct_sampled_rgb": distinct,
            "nonzero_bytes": nonzero,
            "nonblank": bool(nonzero and distinct > 1),
        }
        require(signature["nonblank"], "independent core produced a blank PPU frame")
        return signature

    def video_contract(self) -> dict[str, object]:
        """Describe the callback layout and the host's channel conversion."""

        require(self.video_callbacks > 0, "independent core produced no video callbacks")
        bytes_per_pixel = self.pitch / self.width if self.width else 0
        if self.pitch >= self.width * 4:
            decoded_packing = "BGRX-8888 (stride-authoritative)"
        elif self.pixel_format == 2:
            decoded_packing = "RGB565 little-endian"
        elif self.pixel_format == 0:
            decoded_packing = "0RGB1555 little-endian"
        else:
            decoded_packing = "XRGB8888"
        return {
            "pixel_format_enum": self.pixel_format,
            "width": self.width,
            "height": self.height,
            "pitch": self.pitch,
            "bytes_per_pixel": bytes_per_pixel,
            "callbacks": self.video_callbacks,
            "decoded_packing": decoded_packing,
            "raw_prefix_hex": self.raw_prefix.hex(),
        }

    def capture(self, name: str) -> str:
        require(self.frame_image is not None, f"no PPU frame for {name}")
        CAPTURE_ROOT.mkdir(parents=True, exist_ok=True)
        path = CAPTURE_ROOT / f"{name}.png"
        self.frame_image.save(path)
        return str(path.relative_to(ROOT)).replace("\\", "/")

    def close(self) -> None:
        if self.closed:
            return
        try:
            if self.loaded:
                self.core.retro_unload_game()
            self.core.retro_deinit()
        finally:
            self.closed = True
            if Probe.active is self:
                Probe.active = None


def press(core: Probe, key: str, port: int = 0) -> None:
    if port == 0:
        core.run(3, p1=[key])
    else:
        core.run(3, p2=[key])
    core.run(3)
    core.run(20)


def wait_screen(core: Probe, wanted: int, limit: int = 600) -> dict[str, int]:
    for _ in range(limit // 10):
        state = core.state()
        if state["screen"] == wanted:
            return state
        core.run(10)
    raise AssertionError(f"screen {wanted} did not arrive: {core.state()}")


def traced_state(core: Probe, trace_map: dict[str, int]) -> dict[str, int]:
    current = core.state()
    words = core.trace_words(max(TRACE_WORDS, max(trace_map.values(), default=0) + 1))
    for name, index in trace_map.items():
        current[name] = words[index]
    return current


def capture_stage_frame(core: Probe, name: str) -> str:
    require(core.frame_image is not None, f"no PPU frame for {name}")
    return core.capture(name)


def boot_match(core: Probe, stage_id: int, trace_map: dict[str, int],
               rects: list[tuple[int, int, int, int]],
               low_wave_pair: bool = False) -> dict[str, object]:
    """Enter local versus and return the settled live fight plus intro evidence."""

    core.run(120)
    title = core.state()
    require(title["magic"] == 0xAABA and title["screen"] == 0,
            f"stage boot title state is wrong: {title}")
    # Title menu item 1 is local versus, which gives both ports real controls.
    press(core, "down")
    press(core, "a")
    select = wait_screen(core, 1)
    if low_wave_pair:
        # Negger (4) and Fernando (6) are the authored low-wave pair.
        press(core, "down")
        press(core, "a")
        # The second fighter is confirmed by port 1; keeping the input on
        # port 0 leaves the selection screen active and eventually times out.
        press(core, "down", 1)
        press(core, "right", 1)
        press(core, "a", 1)
    else:
        press(core, "a")
        press(core, "a", 1)
    arena = wait_screen(core, 2)
    require(arena["arena"] == 0,
            f"stage arena did not start at 0: {arena}")
    for _ in range(stage_id):
        press(core, "down")
    press(core, "a")
    fight = wait_screen(core, 3)
    require(fight["arena"] == stage_id,
            f"stage selection did not reach {stage_id}: {fight}")

    intro_samples: list[dict[str, object]] = []
    for _ in range(16):
        current = traced_state(core, trace_map)
        if current["intro"] == 0:
            break
        intro_samples.append({
            "clock": current["ambient_clock"],
            "phase": current["ambient_phase"],
            "pending": current["ambient_pending_phase"],
            "age": current["ambient_phase_age"],
            "ppu": patch_digest(core.frame_image, rects),
        })
        core.run(1)
    require(len(intro_samples) >= 4,
            f"stage intro was too short for a freeze sample: {intro_samples}")
    # The first frame may finish the initial upload.  The settled tail must
    # remain unchanged while intro countdown is still active.
    intro_tail = intro_samples[-4:]
    require(len({(item["clock"], item["phase"], item["pending"], item["age"])
                 for item in intro_tail}) == 1,
            f"ambient trace advanced during intro: {intro_tail}")
    require(len({item["ppu"] for item in intro_tail}) == 1,
            f"ambient PPU patch changed during intro: {intro_tail}")
    while core.state()["intro"]:
        core.run(1)
    live = traced_state(core, trace_map)
    require(live["screen"] == 3 and live["intro"] == 0,
            f"live fight state is wrong after intro: {live}")
    if low_wave_pair:
        require(live["selected"] == 4 and live["selected2"] == 6 and
                live["family1"] == 2 and live["family2"] == 2,
                f"low-wave control fixture selected the wrong fighters: {live}")
    return {
        "title": title,
        "select": select,
        "arena": arena,
        "fight": live,
        "intro_samples": intro_tail,
    }


def verify_stage_phases(core: Probe, stage_id: int,
                        record: dict[str, object],
                        trace_map: dict[str, int]) -> dict[str, object]:
    rects = stage_phase_probe_rects(record)
    max_frames = int(record.get("phase_capture_frames", 160))
    require(max_frames >= PHASE_COUNT * PHASE_PERIOD_FRAMES,
            f"stage {stage_id} phase capture window is too short")
    phase_observations: dict[int, dict[str, object]] = {}
    previous_clock: int | None = None
    for _ in range(max_frames):
        current = traced_state(core, trace_map)
        require(0 <= current["ambient_phase"] < PHASE_COUNT,
                f"stage {stage_id} uploaded phase is outside 0..3: {current}")
        if previous_clock is not None:
            clock_delta = (current["ambient_clock"] - previous_clock) & 0xFFFF
            require(clock_delta in (0, 1),
                    f"stage {stage_id} ambient clock jumped by {clock_delta}")
        previous_clock = current["ambient_clock"]
        phase = current["ambient_phase"]
        if phase not in phase_observations:
            # The Accuracy core presents the frame callback before the native
            # vblank DMA that publishes the trace phase.  Advance one neutral
            # callback frame so the observed phase and PPU image refer to the
            # same completed upload.
            core.run(1)
            current = traced_state(core, trace_map)
            require(current["ambient_phase"] == phase,
                    f"stage {stage_id} phase changed during upload observation: {current}")
            previous_clock = current["ambient_clock"]
            image = core.frame_image.copy() if core.frame_image is not None else None
            digest = patch_digest(image, rects)
            capture = capture_stage_frame(core, f"stage{stage_id}-ambient-phase{phase}")
            phase_observations[phase] = {
                "phase": phase,
                "clock": current["ambient_clock"],
                "pending": current["ambient_pending_phase"],
                "age": current["ambient_phase_age"],
                "ppu_patch_sha256": digest,
                "capture": capture,
            }
        if len(phase_observations) == PHASE_COUNT:
            break
        core.run(1)
    require(set(phase_observations) == set(range(PHASE_COUNT)),
            f"stage {stage_id} did not expose all four uploaded phases: "
            f"{sorted(phase_observations)}")
    phase_digests = [phase_observations[index]["ppu_patch_sha256"]
                     for index in range(PHASE_COUNT)]
    require(len(set(phase_digests)) == PHASE_COUNT,
            f"stage {stage_id} ambient phases are not distinct in actual PPU pixels: "
            f"{phase_observations}")
    return {
        "stage_id": stage_id,
        "screen_rects": stage_patch_rects(record),
        "ppu_probe_rects": rects,
        "phase_count": PHASE_COUNT,
        "phase_period_frames": PHASE_PERIOD_FRAMES,
        "phases": phase_observations,
        "ppu_patch_distinct": len(set(phase_digests)),
    }


def verify_pause_freeze(core: Probe, trace_map: dict[str, int],
                        rects: list[tuple[int, int, int, int]]) -> dict[str, object]:
    core.run(3, p1=["start"])
    core.run(3)
    paused = traced_state(core, trace_map)
    require(paused["paused"] != 0, f"pause did not enter native paused state: {paused}")
    before = {
        "clock": paused["ambient_clock"],
        "phase": paused["ambient_phase"],
        "pending": paused["ambient_pending_phase"],
        "age": paused["ambient_phase_age"],
        "ppu_patch_sha256": patch_digest(core.frame_image, rects),
    }
    core.run(12)
    after = traced_state(core, trace_map)
    after_digest = patch_digest(core.frame_image, rects)
    require((after["ambient_clock"], after["ambient_phase"],
             after["ambient_pending_phase"], after["ambient_phase_age"]) ==
            (before["clock"], before["phase"], before["pending"], before["age"]),
            f"ambient trace advanced while paused: before={before}, after={after}")
    require(after_digest == before["ppu_patch_sha256"],
            f"actual PPU ambient patch changed while paused: {before} -> {after_digest}")
    core.run(3, p1=["start"])
    core.run(3)
    released = traced_state(core, trace_map)
    require(released["paused"] == 0,
            f"pause did not release through the native controller: {released}")
    return {"before": before, "after": after, "released": released}


def close_players(core: Probe) -> None:
    for _ in range(180):
        current = core.state()
        if abs(current["x1"] - current["x2"]) < 28 * 16:
            return
        p1 = "right" if current["x1"] < current["x2"] else "left"
        p2 = "left" if p1 == "right" else "right"
        core.run(1, p1=[p1], p2=[p2])
    raise AssertionError(f"controllers could not close fighters: {core.state()}")


def verify_hitstop_freeze(core: Probe, trace_map: dict[str, int],
                          rects: list[tuple[int, int, int, int]]) -> dict[str, object]:
    close_players(core)
    core.run(3, p1=["y"])
    core.run(1)
    hit = None
    for _ in range(100):
        current = traced_state(core, trace_map)
        if current["hitstop"]:
            hit = current
            break
        core.run(1)
    require(hit is not None, "controls-only hitstop fixture did not produce contact")
    assert hit is not None
    before_frame = core.frame_image.copy() if core.frame_image is not None else None
    before_digest = patch_digest(before_frame, rects)
    before_clock = hit["ambient_clock"]
    before_phase = hit["ambient_phase"]
    held = 0
    alignments: list[int] = []
    while traced_state(core, trace_map)["hitstop"] and held < 20:
        core.run(1)
        current = traced_state(core, trace_map)
        require(current["ambient_clock"] == before_clock and
                current["ambient_phase"] == before_phase,
                f"ambient trace advanced during hitstop: {current}")
        after_frame = core.frame_image.copy() if core.frame_image is not None else None
        after_digest = patch_digest(after_frame, rects)
        alignment = camera_aligned_patch_match(before_frame, after_frame, rects)
        require(alignment is not None,
                f"actual PPU ambient patch changed during hitstop after camera "
                f"normalization: before={before_digest}, after={after_digest}, "
                f"trace={current}")
        assert alignment is not None
        alignments.append(alignment)
        held += 1
    require(held >= 2, f"hitstop freeze was too short to inspect: {held}")
    return {"hitstop": hit, "held_ticks": held,
            "ppu_patch_sha256": before_digest,
            "camera_alignments_native_px": sorted(set(alignments))}


def verify_round_end_freeze(core: Probe, trace_map: dict[str, int],
                            rects: list[tuple[int, int, int, int]]) -> dict[str, object]:
    # Repeated real Y-button attacks are sufficient to reach a round end with
    # the local-versus fixture.  No WRAM or save-state shortcut is permitted.
    attempts = 0
    ko_deltas: list[int] = []

    def step(p1=(), p2=()) -> dict[str, int]:
        before = core.state()["frame"]
        core.run(1, p1=p1, p2=p2)
        sample = traced_state(core, trace_map)
        delta = (sample["frame"] - before) & 0xFFFF
        ko_deltas.append(delta)
        require(delta == 1, f"KO/reaction cadence must remain unit-only: {sample}, delta={delta}")
        require(sample["ppu_stat"] & 0xC0 == 0,
                f"KO/reaction exceeded native OBJ fetch budget: {sample}")
        return sample

    current = traced_state(core, trace_map)
    while attempts < 80 and not current["round_end"]:
        for _ in range(180):
            if abs(current["x1"] - current["x2"]) < 28 * 16 or current["round_end"]:
                break
            toward = "right" if current["x1"] < current["x2"] else "left"
            current = step([toward], ["left" if toward == "right" else "right"])
        require(current["round_end"] or abs(current["x1"] - current["x2"]) < 28 * 16,
                f"controllers could not close fighters before KO: {current}")
        for offset in range(23):
            if current["round_end"]:
                break
            current = step(["y"] if offset < 3 else [])
        attempts += 1
    current = traced_state(core, trace_map)
    require(current["round_end"] == 180 and current["hp2"] == 0 and
            current["hp1"] > 0 and current["wins1"] == 1,
            f"controls-only round-end fixture did not reach a KO: {current}")
    ko = dict(current)
    # Feature 08 is deferred: the original ambient phase, pending slot and
    # actual PPU patch must freeze for the entire round end, including a KO.
    reaction = []
    phases = {current["ambient_phase"]}
    images = {patch_digest(core.frame_image, rects)}
    frozen = {key: current[key] for key in
              ("ambient_clock", "ambient_phase", "ambient_pending_phase", "ambient_phase_age")}
    # Intro/victory gestures and winner lettering can cover an ambient cell.
    # Prove the ambient trace frozen from the first KO sample, then compare
    # actual PPU patches after those foreground sequences have settled.
    while current["round_end"] > 20:
        current = step()
        require(all(current[key] == value for key, value in frozen.items()),
                f"ambient state changed during round end: {current}")
    before_frame = core.frame_image.copy() if core.frame_image is not None else None
    before = {
        "round_end": current["round_end"], "clock": current["ambient_clock"],
        "phase": current["ambient_phase"], "pending": current["ambient_pending_phase"],
        "age": current["ambient_phase_age"], "ppu_patch_sha256": patch_digest(before_frame, rects),
    }
    frozen_frames = 0
    alignments: list[int] = []
    for _ in range(8):
        after = step()
        require(after["ambient_clock"] == before["clock"] and
                after["ambient_phase"] == before["phase"] and
                after["ambient_pending_phase"] == before["pending"] and
                after["ambient_phase_age"] == before["age"],
                f"ambient trace advanced during deferred-stage round end: {after}")
        after_frame = core.frame_image.copy() if core.frame_image is not None else None
        alignment = camera_aligned_patch_match(before_frame, after_frame, rects)
        require(alignment is not None,
                "actual PPU ambient patch changed during round end")
        alignments.append(alignment)
        frozen_frames += 1
    return {"attempts": attempts, "ko": ko, "frozen_frames": frozen_frames, "before": before,
            "cadence": {"frames": len(ko_deltas), "deltas": sorted(set(ko_deltas))},
            "victory_reaction": {"samples": reaction, "phases": sorted(phases),
                                 "distinct_ppu_patches": len(images)},
            "camera_alignments_native_px": alignments}


def boot_low_wave_match(core: Probe, trace_map: dict[str, int],
                        rects: list[tuple[int, int, int, int]]) -> dict[str, int]:
    result = boot_match(core, 0, trace_map, rects, low_wave_pair=True)
    live = result["fight"]
    assert isinstance(live, dict)
    return live


def verify_synchronized_low_wave(trace_map: dict[str, int],
                                 rects: list[tuple[int, int, int, int]]) -> dict[str, object]:
    core = Probe()
    try:
        live = boot_low_wave_match(core, trace_map, rects)
        core.run(3, p1=["down", "y"], p2=["down", "y"])
        core.run(3)
        synchronized: list[dict[str, int]] = []
        for _ in range(80):
            current = traced_state(core, trace_map)
            if (current["wave1"] and current["wave2"] and
                    current["wave_low1"] and current["wave_low2"]):
                synchronized.append(current)
                break
            core.run(1)
        require(synchronized, "controls-only fixture did not synchronize two low waves")

        previous_frame = core.state()["frame"]
        deltas: list[int] = []
        stat_values: set[int] = set()
        stat_overflow_values: set[int] = set()
        sync_frames = 0
        for offset in range(600):
            # Reissue the same real controller command at a conservative cadence
            # so both specials can be observed without any emulated-memory write.
            controls = ["down", "y"] if offset % 96 == 0 else []
            current = core.run(1, p1=controls, p2=controls)
            delta = (current["frame"] - previous_frame) & 0xFFFF
            deltas.append(delta)
            previous_frame = current["frame"]
            raw_stat = current["ppu_stat"] & 0xFF
            stat_values.add(raw_stat)
            overflow_bits = raw_stat & 0xC0
            stat_overflow_values.add(overflow_bits)
            # STAT77 low revision bits are core/PPU-defined (the pinned
            # Accuracy callback reports 0x11 on some frames).  The native
            # safety contract is the range/time overflow bits 7 and 6.
            require(overflow_bits == 0,
                    f"STAT77 trace word 114 reports OAM range/time overflow "
                    f"during low-wave cadence: {current}")
            if (current["wave1"] and current["wave2"] and
                    current["wave_low1"] and current["wave_low2"]):
                sync_frames += 1
        require(all(delta == 1 for delta in deltas),
                f"low-wave cadence contains non-one frame deltas: {sorted(set(deltas))}")
        return {
            "fighters": {
                "p1": live["fighter_id1"], "p2": live["fighter_id2"],
                "family1": live["family1"], "family2": live["family2"],
            },
            "synchronized_initial_frames": len(synchronized),
            "synchronized_frames_in_600": sync_frames,
            "stat77_values": sorted(stat_values),
            "stat77_overflow_bits": sorted(stat_overflow_values),
            "stat77_overflow_mask": "0xC0",
            "requested_frames": 600,
            "observed_deltas": len(deltas),
            "delta_min": min(deltas),
            "delta_max": max(deltas),
            "non_one_deltas": sum(delta != 1 for delta in deltas),
            "passed": True,
        }
    finally:
        core.close()


def stage_state(label: str, state: dict[str, int], frame: dict[str, object],
                capture: str) -> dict[str, object]:
    fields: dict[str, object] = {
        "screen": state["screen"],
        "frame": frame,
        "capture": capture,
    }
    if label == "select":
        fields["selected"] = state["selected"]
    elif label == "arena":
        fields["arena"] = state["arena"]
    elif label == "fight":
        fields.update({
            "intro": state["intro"],
            "fighter_id1": state["fighter_id1"],
            "fighter_id2": state["fighter_id2"],
            "hp1": state["hp1"],
            "hp2": state["hp2"],
        })
    return fields


def run_stage_engine_check(stage_id: int, record: dict[str, object],
                           trace_map: dict[str, int]) -> dict[str, object]:
    if depth_manifest(ROOT) is not None:
        # The depth driver decodes both real SNES tile planes and verifies
        # each camera/impact offset, immutable maps, freeze and live budgets.
        # Use a separate capture directory from the six-suite execution.
        import test_combat_24_stage08 as depth
        depth.OUT=CAPTURE_ROOT/'depth-v1';depth.OUT.mkdir(parents=True,exist_ok=True)
        result=depth.stage_case(stage_id,independent=True)
        result['stage_contract']='whole-scenery-fixed-floor'
        result['passed']=True
        return result
    rects = stage_phase_probe_rects(record)
    core = Probe()
    try:
        boot = boot_match(core, stage_id, trace_map, rects)
        # Let the native FIGHT! banner and the first interface settle before
        # comparing the upper, unobscured stage plate.  This still uses only
        # neutral controller frames and leaves ambient cells excluded below.
        core.run(40)
        plate = static_plate_color_agreement(core, stage_id, record)
        phases = verify_stage_phases(core, stage_id, record, trace_map)
        pause = verify_pause_freeze(core, trace_map, rects)
        result: dict[str, object] = {
            "stage_id": stage_id,
            "slug": stage_slug(record, stage_id),
            "boot": boot,
            "static_plate_color": plate,
            "ambient_phases": phases,
            "pause_freeze": pause,
        }
        result["hitstop_freeze"] = verify_hitstop_freeze(core, trace_map, rects)
        result["round_end_freeze"] = verify_round_end_freeze(core, trace_map, rects)
        return result
    finally:
        core.close()


def main() -> int:
    report: dict[str, object] = {
        "status": "failed",
        "scope": SCOPE,
        "pinned_core": True,
        "source_url": CORE_URL,
        "rom": {"sha256": None, "bytes": ROM_BYTES},
        "core": {
            "archive_sha256": CORE_ARCHIVE_SHA256,
            "dll_sha256": CORE_DLL_SHA256,
            "library_name": None,
            "library_version": None,
        },
        "checks": {},
        "errors": [],
        "host_contract": {
            "emulated_memory_writes": 0,
            "savestate_calls": 0,
            "audio_device_opened": False,
            "frontend_window_created": False,
            "pcm_callback_capture_only": True,
        },
    }
    core: Probe | None = None
    try:
        pinned_inputs = verify_manifest_and_pinned_core()
        report["checks"]["pinned_inputs"] = pinned_inputs
        report["rom"]["sha256"] = pinned_inputs["rom_sha256"]
        stage_manifest, trace_map, stage_records = load_stage_dynamics()
        report["stage_dynamics"] = {
            "manifest": str(STAGE_MANIFEST_PATH.relative_to(ROOT)).replace("\\", "/"),
            "manifest_sha256": sha256(STAGE_MANIFEST_PATH),
            "phase_count": PHASE_COUNT,
            "phase_period_frames": PHASE_PERIOD_FRAMES,
            "trace": trace_map,
            "stage_count": STAGE_COUNT,
        }
        core = Probe()
        require(core.library_name == "bsnes2014",
                f"unexpected independent core name: {core.library_name!r}")
        require(core.library_version == "v094 (Accuracy) 3c1394e",
                f"unexpected independent core version: {core.library_version!r}")
        report["core"].update({
            "library_name": core.library_name,
            "library_version": core.library_version,
            "system_ram_bytes": core.ram_size,
            "trace_offset": "0x1FF00",
            "trace_words": TRACE_WORDS,
        })

        title = core.run(120)
        report["core"]["video"] = core.video_contract()
        title_frame = core.frame_signature()
        title_capture = core.capture("title")
        require(title["magic"] == 0xAABA and title["screen"] == 0,
                f"title state is wrong: magic={title['magic']}, screen={title['screen']}")
        report["checks"]["title"] = stage_state("title", title, title_frame, title_capture)

        press(core, "down")
        press(core, "a")
        select = wait_screen(core, 1)
        select_frame = core.frame_signature()
        select_capture = core.capture("select")
        require(select["screen"] == 1 and select["selected"] == 0,
                f"select state is wrong: screen={select['screen']}, selected={select['selected']}")
        report["checks"]["select"] = stage_state("select", select, select_frame, select_capture)

        press(core, "a")
        press(core, "a", 1)
        arena = wait_screen(core, 2)
        arena_frame = core.frame_signature()
        arena_capture = core.capture("arena")
        require(arena["screen"] == 2 and arena["arena"] == 0,
                f"arena state is wrong: screen={arena['screen']}, arena={arena['arena']}")
        report["checks"]["arena"] = stage_state("arena", arena, arena_frame, arena_capture)

        press(core, "a")
        wait_screen(core, 3)
        for _ in range(240):
            if core.state()["intro"] == 0:
                break
            core.run(1)
        fight = core.state()
        fight_frame = core.frame_signature()
        fight_capture = core.capture("fight")
        require(fight["screen"] == 3 and fight["intro"] == 0,
                f"live fight state is wrong: screen={fight['screen']}, intro={fight['intro']}")
        report["checks"]["fight"] = stage_state("fight", fight, fight_frame, fight_capture)

        stage_digests = [
            report["checks"][name]["frame"]["sha256_rgb"]
            for name in ("title", "select", "arena", "fight")
        ]
        require(len(set(stage_digests)) == 4,
                "title/select/arena/fight PPU frames are not all distinct")
        report["checks"]["ppu_distinct"] = {
            "passed": True,
            "stage_count": 4,
            "distinct_sha256_rgb": len(set(stage_digests)),
        }

        before_right = core.state()
        core.run(20, p1=["right"])
        after_right = core.state()
        require(after_right["x1"] != before_right["x1"],
                f"right input did not move P1: {before_right['x1']} -> {after_right['x1']}")
        core.run(3, p1=["up"])
        after_jump = core.state()
        jump_y = signed16(after_jump["y1"])
        require(jump_y < 0, f"up input did not produce negative jump Y: {jump_y}")
        report["checks"]["controller"] = {
            "right_x_before": before_right["x1"],
            "right_x_after": after_right["x1"],
            "jump_y_signed": jump_y,
            "passed": True,
        }

        previous_frame = core.state()["frame"]
        deltas: list[int] = []
        for _ in range(600):
            current = core.run(1)
            delta = (current["frame"] - previous_frame) & 0xFFFF
            deltas.append(delta)
            previous_frame = current["frame"]
        require(all(delta == 1 for delta in deltas),
                f"neutral cadence contains non-one frame deltas: {sorted(set(deltas))}")
        report["checks"]["cadence"] = {
            "requested_frames": 600,
            "observed_deltas": len(deltas),
            "delta_min": min(deltas),
            "delta_max": max(deltas),
            "non_one_deltas": sum(delta != 1 for delta in deltas),
            "passed": True,
        }

        require(core.audio_energy > 0, "PCM callback captured zero energy")
        require(0 < core.audio_peak < 32767,
                f"PCM peak is outside unclipped 16-bit range: {core.audio_peak}")
        report["checks"]["audio"] = {
            "samples": core.audio_samples,
            "energy": core.audio_energy,
            "peak": core.audio_peak,
            "passed": True,
        }
        core.close()
        core = None

        stage_results: dict[str, object] = {}
        for stage_id in range(STAGE_COUNT):
            record = stage_records[stage_id]
            stage_results[stage_slug(record, stage_id)] = run_stage_engine_check(
                stage_id, record, trace_map)
        report["checks"]["stage_ambient_and_freeze"] = {
            "manifest_phase_count": int(stage_manifest.get("phase_count", PHASE_COUNT)),
            "stages": stage_results,
            "passed": True,
        }
        report["checks"]["synchronized_low_wave"] = verify_synchronized_low_wave(
            trace_map, stage_phase_probe_rects(stage_records[0]))
        report["status"] = "passed"
    except Exception as exc:
        report["errors"].append(repr(exc))
        report["error_type"] = type(exc).__name__
    finally:
        if core is not None:
            try:
                core.close()
            except Exception as exc:
                report["errors"].append(f"close: {exc!r}")
        if report["errors"]:
            report["status"] = "failed"
        REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({
            "status": report["status"],
            "scope": SCOPE,
            "report": str(REPORT_PATH.relative_to(ROOT)).replace("\\", "/"),
            "error": report["errors"][0] if report["errors"] else None,
        }))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
