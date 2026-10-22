"""Thin silent libretro host for the endurance gate.

The canonical host intentionally materializes every callback frame as a PIL
image.  That is useful for visual assertions but makes an hour-scale soak
needlessly expensive.  This host keeps the same official Snes9x libretro
core, controller ABI and read-only WRAM access while sampling video and PCM
instead of retaining every callback.  It never writes emulated memory and it
never opens a window or plays audio.
"""

from __future__ import annotations

import ctypes as C
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUTTONS = {
    "b": 0, "y": 1, "select": 2, "start": 3, "up": 4, "down": 5,
    "left": 6, "right": 7, "a": 8, "x": 9, "l": 10, "r": 11,
}
OAM_BYTES = 128 * 4 + 32


class GameInfo(C.Structure):
    _fields_ = [
        ("path", C.c_char_p), ("data", C.c_void_p),
        ("size", C.c_size_t), ("meta", C.c_char_p),
    ]


class GameGeometry(C.Structure):
    _fields_ = [
        ("base_width", C.c_uint), ("base_height", C.c_uint),
        ("max_width", C.c_uint), ("max_height", C.c_uint),
        ("aspect_ratio", C.c_float),
    ]


class SystemTiming(C.Structure):
    _fields_ = [("fps", C.c_double), ("sample_rate", C.c_double)]


class SystemAvInfo(C.Structure):
    _fields_ = [("geometry", GameGeometry), ("timing", SystemTiming)]


class LongRunHost:
    """One active Snes9x core with low-overhead callback sampling."""

    _active = None

    def __init__(self, rom: Path | None = None, video_interval: int = 120):
        if LongRunHost._active is not None:
            raise RuntimeError("only one endurance core may be active per process")
        self.closed = False
        self.boot_count = 0
        self.unload_count = 0
        self.frames = 0
        self.video_interval = max(1, int(video_interval))
        self.video_samples = 0
        self.video_nonblank = 0
        self.video_digest = None
        self.video_size = (0, 0)
        self.audio_batches = 0
        self.audio_samples = 0
        self.audio_nonzero_batches = 0
        self.audio_peak = 0
        self.audio_prefix = bytearray()
        self.held = [set(), set()]
        self.pixel_format = 0
        self._cached_oam_offset = None
        self._cached_vblank_offsets = None
        self._cached_native_screen_offset = None
        self._cached_spc_offsets = None
        self.directory = str(ROOT / ".tools/core").encode()
        self.core = C.CDLL(str(ROOT / ".tools/core/snes9x_libretro.dll"))

        ENV = C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p)
        VIDEO = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t)
        AUDIO = C.CFUNCTYPE(None, C.c_int16, C.c_int16)
        BATCH = C.CFUNCTYPE(C.c_size_t, C.POINTER(C.c_int16), C.c_size_t)
        POLL = C.CFUNCTYPE(None)
        INPUT = C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint)

        def env(cmd, data):
            cmd &= 0xFFFF
            if cmd == 10:
                self.pixel_format = C.cast(data, C.POINTER(C.c_uint))[0]
                return True
            if cmd == 3:
                C.cast(data, C.POINTER(C.c_bool))[0] = True
                return True
            if cmd in (9, 31, 30):
                C.cast(data, C.POINTER(C.c_char_p))[0] = self.directory
                return True
            if cmd == 15:
                return False
            if cmd == 17:
                C.cast(data, C.POINTER(C.c_bool))[0] = False
                return True
            if cmd == 47:
                C.cast(data, C.POINTER(C.c_int))[0] = 3
                return True
            if cmd == 39:
                C.cast(data, C.POINTER(C.c_uint))[0] = 0
                return True
            if cmd == 52:
                C.cast(data, C.POINTER(C.c_uint))[0] = 0
                return True
            return cmd in (1, 6, 11, 16, 18, 35, 37, 44, 53, 63)

        def video(data, width, height, pitch):
            if not data or self.frames % self.video_interval:
                return
            raw = C.string_at(data, pitch * height)
            self.video_samples += 1
            self.video_size = (int(width), int(height))
            self.video_digest = hashlib.sha256(raw).hexdigest()
            if any(raw):
                self.video_nonblank += 1

        def audio_sample(left, right):
            self.audio_batches += 1
            self.audio_samples += 1
            self.audio_peak = max(self.audio_peak, abs(int(left)), abs(int(right)))
            if left or right:
                self.audio_nonzero_batches += 1

        def batch(data, frame_count):
            self.audio_batches += 1
            self.audio_samples += int(frame_count)
            # Keep only bounded evidence.  The callback still acknowledges
            # every native batch, but never copies a full-hour PCM stream.
            if self.audio_batches <= 2 or self.audio_batches % 120 == 0:
                count = min(int(frame_count), 64)
                raw = C.string_at(data, count * 4)
                if len(self.audio_prefix) < 4096:
                    self.audio_prefix.extend(raw[:4096 - len(self.audio_prefix)])
                if any(raw):
                    self.audio_nonzero_batches += 1
                samples = C.cast(data, C.POINTER(C.c_int16))
                for index in range(min(count * 2, 128)):
                    self.audio_peak = max(self.audio_peak, abs(int(samples[index])))
            return frame_count

        def poll():
            return None

        def input_state(port, device, index, button):
            return int(port < 2 and button in self.held[port])

        self.callbacks = [
            ENV(env), VIDEO(video), AUDIO(audio_sample), BATCH(batch),
            POLL(poll), INPUT(input_state),
        ]
        for name, callback in zip(
                ("environment", "video_refresh", "audio_sample",
                 "audio_sample_batch", "input_poll", "input_state"),
                self.callbacks):
            getattr(self.core, "retro_set_" + name)(callback)
        self.core.retro_init()
        self.core.retro_load_game.argtypes = [C.POINTER(GameInfo)]
        self.core.retro_load_game.restype = C.c_bool
        self.core.retro_get_memory_data.argtypes = [C.c_uint]
        self.core.retro_get_memory_data.restype = C.c_void_p
        self.core.retro_get_memory_size.argtypes = [C.c_uint]
        self.core.retro_get_memory_size.restype = C.c_size_t
        self.rompath = Path(rom or ROOT / "dist/abaqus-after-hours.sfc")
        self.rom = C.create_string_buffer(self.rompath.read_bytes())
        info = GameInfo(str(self.rompath).encode(), C.cast(self.rom, C.c_void_p),
                        len(self.rom) - 1, None)
        if not self.core.retro_load_game(C.byref(info)):
            raise RuntimeError("Snes9x rejected the endurance ROM")
        self.boot_count = 1
        self.core.retro_get_system_av_info.argtypes = [C.POINTER(SystemAvInfo)]
        self.core.retro_get_system_av_info.restype = None
        av_info = SystemAvInfo()
        self.core.retro_get_system_av_info(C.byref(av_info))
        self.video_fps = float(av_info.timing.fps)
        self.audio_sample_rate = float(av_info.timing.sample_rate)
        self.core.retro_set_controller_port_device(0, 1)
        self.core.retro_set_controller_port_device(1, 1)
        self.ram = self.core.retro_get_memory_data(2)
        if self.core.retro_get_memory_size(2) != 131072:
            raise RuntimeError("unexpected WRAM size")
        LongRunHost._active = self

    def run(self, count: int = 1, p1=(), p2=()):
        if self.closed:
            raise RuntimeError("endurance core is closed")
        self.held = [{BUTTONS[key] for key in p1},
                     {BUTTONS[key] for key in p2}]
        for _ in range(int(count)):
            self.core.retro_run()
            self.frames += 1
        return self.state()

    def tap(self, key: str, port: int = 0, settle: int = 14):
        self.run(3, **({"p1": [key]} if port == 0 else {"p2": [key]}))
        return self.run(settle)

    def trace_words(self, count: int = 119) -> list[int]:
        raw = C.string_at(self.ram + 0x1FF00, count * 2)
        return [int.from_bytes(raw[index:index + 2], "little")
                for index in range(0, count * 2, 2)]

    def state(self) -> dict[str, int]:
        # Stable combat trace words 0..113 plus v0.7 stage words 114..118.
        data = C.string_at(self.ram + 0x1FF00, 246)
        values = [int.from_bytes(data[index:index + 2], "little")
                  for index in range(0, len(data), 2)]
        names = [
            "magic", "screen", "frame", "mode", "hp1", "hp2", "x1", "x2",
            "y1", "y2", "action1", "action2", "wins1", "wins2", "arena",
            "round", "intro", "paused", "energy1", "energy2", "wave1",
            "wave2", "selected", "selected2", "arcade", "seconds", "pose1",
            "pose2", "round_end", "hitstop", "combo", "champion",
        ]
        result = dict(zip(names, values[:32]))
        extension = [
            "fighter_id1", "fighter_id2", "family1", "family2", "speed1",
            "speed2", "jump1", "jump2", "face1", "face2", "back_speed1",
            "back_speed2", "special_startup1", "special_startup2",
            "special_active1", "special_active2", "special_recovery1",
            "special_recovery2", "special_damage1", "special_damage2",
            "special_reach1", "special_reach2", "throw_range1",
            "throw_range2", "wave_low1", "wave_low2", "wave_speed1",
            "wave_speed2", "wave_life1", "wave_life2",
        ]
        result.update(dict(zip(extension, values[32:62])))
        animation = [
            "anim_frame1", "anim_frame2", "anim_state1", "anim_state2",
            "anim_tick1", "anim_tick2", "buffered_action1", "buffered_action2",
            "buffer_age1", "buffer_age2", "jump_buffer1", "jump_buffer2",
            "command_stage1", "command_stage2", "raw_keys1", "raw_keys2",
            "landing1", "landing2", "jump_vx1", "jump_vx2",
        ]
        result.update(dict(zip(animation, values[62:82])))
        contact = [
            "hurt1", "hurt2", "guard1", "guard2", "connected1", "connected2",
            "combo1", "combo2", "combo_display1", "combo_display2",
            "counter1", "counter2",
        ]
        result.update(dict(zip(contact, values[82:94])))
        recovery = [
            "down_state1", "down_state2", "down_tick1", "down_tick2",
            "invuln1", "invuln2", "pending_throw_damage1",
            "pending_throw_damage2", "throw_owner1", "throw_owner2",
            "air_action1", "air_action2", "throw_victim1", "throw_victim2",
            "wake_action1", "wake_action2", "wake_age1", "wake_age2",
            "wake_jump1", "wake_jump2",
        ]
        result.update(dict(zip(recovery, values[94:114])))
        result.update({
            "ppu_stat": values[114], "ambient_phase": values[115],
            "ambient_clock": values[116], "ambient_pending_phase": values[117],
            "ambient_phase_age": values[118],
            "pause_page": values[119], "guide_build": values[120],
            "training_dummy": values[121], "guide_dirty": values[122],
        })
        result["native_screen"] = self.native_screen()
        result.update(self.vblank_state())
        result.update(self.spc_fifo_state())
        return result

    def native_screen(self) -> int:
        """Read the live screen enum before its trace publication catches up."""

        if self._cached_native_screen_offset is None:
            self._cached_native_screen_offset = self._symbol_offset("screen", 0x2960)
        return C.string_at(self.ram + self._cached_native_screen_offset, 1)[0]

    def vblank_state(self) -> dict[str, int]:
        """Read the native low-RAM VBlank diagnostics without writing state.

        PVSnesLib keeps these counters outside the gameplay trace.  They are
        useful when a repeated trace frame needs to be classified as a
        missed ``WaitForVBlank`` versus a publication-order problem.  The
        offsets are resolved from the current ROM's symbols once and retain
        the documented low-RAM fallbacks for stripped symbol files.
        """

        if self._cached_vblank_offsets is None:
            self._cached_vblank_offsets = {
                "vblank_flag": self._symbol_offset("vblank_flag", 0x30),
                "lag_frame_counter": self._symbol_offset(
                    "lag_frame_counter", 0x35),
                "snes_vblank_count": self._symbol_offset(
                    "snes_vblank_count", 0x37),
            }
        offsets = self._cached_vblank_offsets
        flag = C.string_at(self.ram + offsets["vblank_flag"], 1)[0]
        lag = int.from_bytes(
            C.string_at(self.ram + offsets["lag_frame_counter"], 2), "little")
        count = int.from_bytes(
            C.string_at(self.ram + offsets["snes_vblank_count"], 2), "little")
        return {"vblank_flag": flag, "lag_frame_counter": lag,
                "snes_vblank_count": count}

    def oam_memory(self) -> bytes:
        if self._cached_oam_offset is None:
            self._cached_oam_offset = self._oam_offset()
        offset = self._cached_oam_offset
        return C.string_at(self.ram + offset, OAM_BYTES)

    def spc_fifo_state(self) -> dict[str, int]:
        """Read the resident SPC command FIFO cursors without touching WRAM."""

        if self._cached_spc_offsets is None:
            self._cached_spc_offsets = {
                "spc_fread": self._symbol_offset("spc_fread", 0x44),
                "spc_fwrite": self._symbol_offset("spc_fwrite", 0x45),
            }
        offsets = self._cached_spc_offsets
        fread = C.string_at(self.ram + offsets["spc_fread"], 1)[0]
        fwrite = C.string_at(self.ram + offsets["spc_fwrite"], 1)[0]
        return {
            "spc_fread": fread,
            "spc_fwrite": fwrite,
            "spc_backlog": (fwrite - fread) & 0xFF,
        }

    def _oam_offset(self) -> int:
        return self._symbol_offset("oamMemory", 0x9010)

    def _symbol_offset(self, symbol: str, fallback: int) -> int:
        pattern = re.compile(
            r"^\s*([0-9a-fA-F]{6,8})\s+" + re.escape(symbol) + r"\s*$")
        for path in (ROOT / "dist/abaqus-after-hours.sym",
                     ROOT / "build/abaqus-after-hours.sym"):
            if not path.exists():
                continue
            for line in path.read_text(errors="ignore").splitlines():
                match = pattern.match(line)
                if not match:
                    continue
                address = int(match.group(1), 16)
                if address >> 16 == 0x7E:
                    return address & 0xFFFF
                if address < 0x20000:
                    return address
        return fallback

    def close(self):
        if self.closed:
            return
        self.core.retro_unload_game()
        self.core.retro_deinit()
        self.unload_count += 1
        self.closed = True
        if LongRunHost._active is self:
            LongRunHost._active = None

