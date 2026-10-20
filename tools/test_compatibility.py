"""Independent-engine smoke and neutral 600-frame cadence test.

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
import zipfile
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ROM_PATH = ROOT / "dist" / "abaqus-after-hours.sfc"
MANIFEST_PATH = ROOT / "dist" / "manifest.json"
COMPAT_ROOT = ROOT / ".tools" / "compat"
CORE_ARCHIVE = COMPAT_ROOT / "bsnes2014_accuracy_libretro.dll.zip"
CORE_PATH = COMPAT_ROOT / "bsnes2014-accuracy" / "bsnes2014_accuracy_libretro.dll"
CAPTURE_ROOT = ROOT / "docs" / "screenshots" / "compatibility"
REPORT_PATH = ROOT / "docs" / "compatibility-test-report.json"

CORE_URL = (
    "https://buildbot.libretro.com/nightly/windows/x86_64/latest/"
    "bsnes2014_accuracy_libretro.dll.zip"
)
CORE_ARCHIVE_SHA256 = "CB1211AE6B6838ED60BEB7CC8AE5AD8074327733F1042CCC8BABA32A62C6D18C"
CORE_DLL_SHA256 = "F2AAC1DDB314A001467A26B56604020F0A29C3A4DD1658B072884ACE75343CF4"
ROM_BYTES = 4 * 1024 * 1024
TRACE_OFFSET = 0x1FF00
TRACE_WORDS = 114
TRACE_BYTES = TRACE_WORDS * 2
SCOPE = "independent-engine smoke, neutral600frame cadence"

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
            if self.pixel_format == 1:  # XRGB8888
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
        data = C.string_at(self.ram + TRACE_OFFSET, TRACE_BYTES)
        words = [
            int.from_bytes(data[offset:offset + 2], "little")
            for offset in range(0, TRACE_BYTES, 2)
        ]
        return dict(zip(TRACE_NAMES, words))

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
