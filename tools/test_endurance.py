"""Long, controller-only endurance gate for the native v0.7 cartridge.

Each mode uses one uninterrupted libretro core session for the complete
native NTSC hour.  Roster/stage changes are driven through the game's own
pause, result, title and select menus; the host never reboots the core during
the measured session.  This matters because the cartridge frame counter,
ambient clock and SPC state must survive 16-bit wrap and long live combat.

``longrun_host.py`` samples video/audio callbacks without displaying or
playing them and checks the read-only WRAM trace/OAM shadow on every measured
tick.  The worker never writes emulated memory and never uses a savestate.

Run ``python tools/test_endurance.py --benchmark`` first.  The benchmark is a
strict 1,000-frame cadence/state gate (coverage is intentionally partial), and
the full gate requires its exact-ROM, exact-harness marker before running one
isolated worker per mode.  Per-mode checkpoints live under ignored ``build/``;
the authoritative report is written only after all three uninterrupted
sessions pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from longrun_host import LongRunHost, ROOT


HOUR_SECONDS = 3600.0
BENCHMARK_FRAMES = 1_000
PROGRESS_INTERVAL = 6_000
ROSTER_INTERVAL = 24_000
TRAINING_RESET_INTERVAL = 8_192
ARCADE_POLICY_INTERVAL = 8_192
ARCADE_POLICY_WINDOW = 2_048
MAX_DOWN_STATE_TICKS = 300
MAX_SPC_BACKLOG = 32
MAX_SPC_GROWTH_STREAK = 8
MAX_SPC_STABLE_NO_AUDIO_STREAK = 120
VIDEO_FPS_EPSILON = 1e-6
SCREEN_TITLE, SCREEN_SELECT, SCREEN_ARENA, SCREEN_FIGHT, SCREEN_RESULT = range(5)
STAGE_NAMES = ("las-condes", "el-castillo", "la-oficina")
ROM_MANIFEST = ROOT / "dist/manifest.json"
BENCHMARK_PATH = ROOT / "build/endurance-benchmark.json"
MODE_REPORT = ROOT / "build/endurance-mode{mode}.json"
AUTHORITATIVE_REPORT = ROOT / "docs/endurance-test-report.json"
CORE_ARCHIVE = ROOT / ".tools/core.zip"
CORE_MEMBER = "snes9x_libretro.dll"
CORE_ARCHIVE_SHA256 = "f3e88ae8540840c838dbcd57715134809894c9fd31d389e613409923ac23ea4e"
CORE_MEMBER_SHA256 = "f00db5bd97bbe0e80761e590449eb14716bd9ab5785a1b50725c55e10505c343"


def screen_ready(current: dict[str, int], wanted: int) -> bool:
    """Require both trace and native screen state before sending menu input."""

    return current["screen"] == wanted and current["native_screen"] == wanted


def harness_identity() -> str:
    digest = hashlib.sha256()
    for path in (ROOT / "tools/longrun_host.py", ROOT / "tools/test_endurance.py"):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def rom_identity() -> tuple[str, int]:
    manifest = json.loads(ROM_MANIFEST.read_text())
    rom_path = ROOT / "dist/abaqus-after-hours.sfc"
    digest = hashlib.sha256(rom_path.read_bytes()).hexdigest()
    if digest != manifest.get("sha256"):
        raise AssertionError(("ROM manifest hash mismatch", digest, manifest.get("sha256")))
    if int(manifest.get("bytes", 0)) != 4 * 1024 * 1024:
        raise AssertionError(("unexpected endurance ROM size", manifest))
    return digest, int(manifest["bytes"])


def core_identity() -> dict[str, object]:
    """Pin the loaded DLL to the checked-in core archive/member bytes."""

    if not CORE_ARCHIVE.exists():
        raise AssertionError(("missing pinned libretro core archive", str(CORE_ARCHIVE)))
    archive_sha = hashlib.sha256(CORE_ARCHIVE.read_bytes()).hexdigest()
    if archive_sha != CORE_ARCHIVE_SHA256:
        raise AssertionError(("core archive hash mismatch", archive_sha,
                              CORE_ARCHIVE_SHA256))
    with zipfile.ZipFile(CORE_ARCHIVE) as archive:
        try:
            member = archive.read(CORE_MEMBER)
        except KeyError as exc:
            raise AssertionError(("core archive missing pinned member", CORE_MEMBER)) from exc
    member_sha = hashlib.sha256(member).hexdigest()
    if member_sha != CORE_MEMBER_SHA256:
        raise AssertionError(("core archive member hash mismatch", member_sha,
                              CORE_MEMBER_SHA256))
    dll = ROOT / ".tools/core/snes9x_libretro.dll"
    dll_sha = hashlib.sha256(dll.read_bytes()).hexdigest()
    if dll_sha != member_sha:
        raise AssertionError(("loaded core DLL differs from archive member", dll_sha,
                              member_sha))
    return {"archive": str(CORE_ARCHIVE.relative_to(ROOT)),
            "archive_sha256": archive_sha, "member": CORE_MEMBER,
            "member_sha256": member_sha, "dll": str(dll.relative_to(ROOT)),
            "dll_sha256": dll_sha}


def wait_screen(host: LongRunHost, wanted: int, maximum: int = 720) -> dict[str, int]:
    for _ in range(maximum // 10):
        current = host.state()
        if screen_ready(current, wanted):
            return current
        host.run(10)
    raise AssertionError(("endurance menu transition stalled", wanted, host.state()))


def boot(host: LongRunHost, mode: int, fighter: int, fighter2: int,
         stage: int) -> dict[str, int]:
    host.run(120)
    if not screen_ready(host.state(), SCREEN_TITLE):
        raise AssertionError(("cold boot did not reach title", host.state()))
    for _ in range(mode):
        host.tap("down")
    host.tap("a")
    wait_screen(host, SCREEN_SELECT)
    for _ in range(fighter):
        host.tap("right")
    host.tap("a")
    if mode in (1, 2):
        port = 0 if mode == 2 else 1
        for _ in range((fighter2 - host.state()["selected2"]) % 12):
            host.tap("right", port)
        host.tap("a", port)
    wait_screen(host, SCREEN_ARENA)
    for _ in range(stage):
        host.tap("down")
    host.tap("a")
    wait_screen(host, SCREEN_FIGHT)
    for _ in range(240):
        current = host.state()
        if current["intro"] == 0:
            host.run(3)
            return host.state()
        host.run(1)
    raise AssertionError(("fight intro stalled", host.state()))


def oam_entries(raw: bytes) -> list[dict[str, int]]:
    entries = []
    for index in range(128):
        offset = index * 4
        x, y, tile_low, attr = raw[offset:offset + 4]
        high = raw[512 + index // 4]
        pair = (index & 3) * 2
        x9 = (high >> pair) & 1
        entries.append({
            "x": x | (x9 << 8),
            "x9": x9,
            "x_signed": x - 256 if x9 and x >= 0x80 else x | (x9 << 8),
            "y": y,
            "tile": tile_low | ((attr & 1) << 8),
            "attr": attr,
            "size": (high >> (pair + 1)) & 1,
        })
    return entries


def verify_oam_layout(entries: list[dict[str, int]], side: int,
                      current: dict[str, int], frame: int) -> None:
    """Check the native 6x5 metasprite contract on every live sample."""

    rows = [entries[row * 6:(row + 1) * 6] for row in range(5)]
    if any(len(row) != 6 for row in rows):
        raise AssertionError(("actor OAM row width changed", frame, side))
    for row_index, row in enumerate(rows):
        if any(abs(row[col + 1]["x_signed"] - row[col]["x_signed"]) != 16
               for col in range(5)):
            raise AssertionError(("actor OAM columns are not contiguous", frame,
                                  side, row))
        if len({piece["y"] for piece in row}) != 1:
            raise AssertionError(("actor OAM row has inconsistent Y", frame, side, row))
        if any(row[col + 1]["tile"] - row[col]["tile"] != 2
               for col in range(5)):
            raise AssertionError(("actor OAM tile columns are not contiguous", frame,
                                  side, row))
    tops = [row[0]["tile"] for row in rows]
    if any(tops[row + 1] - tops[row] != 32 for row in range(4)):
        raise AssertionError(("actor OAM tile rows are not contiguous", frame, side,
                              tops))
    expected_flip = 0 if current[f"face{side + 1}"] else 0x40
    if any((piece["attr"] & 0x40) != expected_flip for piece in entries):
        raise AssertionError(("actor OAM facing attribute disagrees with trace", frame,
                              side, current[f"face{side + 1}"], entries))
    if any(((piece["attr"] >> 1) & 7) != side for piece in entries):
        raise AssertionError(("actor OAM palette bank changed", frame, side, entries))
    if any(piece["size"] != 1 for piece in entries):
        raise AssertionError(("actor OAM lost 16x16 size", frame, side, entries))
    if side == 1 and any(not (piece["tile"] & 0x100)
                         for row in rows[3:] for piece in row):
        raise AssertionError(("P2 bottom OAM rows lost tile high bit", frame, entries))
    floor = max(piece["y"] for piece in entries) + 16
    if not 0 <= floor <= 224:
        raise AssertionError(("actor OAM floor is outside native screen", frame, side,
                              floor))


def wrap_delta(current: int, previous: int) -> int:
    return (int(current) - int(previous)) & 0xFFFF


def keys_for(mode: int, tick: int, state: dict[str, int],
             arcade_progression: bool = False) -> tuple[list[str], list[str]]:
    """Deterministic combat coverage without writing state or relying on RNG."""

    distance = abs(state["x1"] - state["x2"])
    forward = "right" if state["x1"] < state["x2"] else "left"
    back = "left" if forward == "right" else "right"

    # Arcade needs to exercise the complete native ladder during an hour-long
    # session.  Reserve a bounded window in each interval for the same
    # controller-only close/guard/throw policy used by the gameplay suite;
    # the broader six-button macro below still owns the remaining coverage.
    # This keeps champion progression an observed menu route instead of a
    # host-side state shortcut.
    if (mode == 0 and (arcade_progression or
                      tick % ARCADE_POLICY_INTERVAL < ARCADE_POLICY_WINDOW)):
        distance_px = distance // 16
        if state["intro"] or state["round_end"] or state["hitstop"]:
            return [], []
        if state["action1"]:
            return [forward], []
        if state["action2"] and distance_px < 55:
            return ([back, "down"] if 4 <= state["action2"] <= 6
                    else [back]), []
        if distance_px > 25:
            return [forward], []
        # Match the gameplay probe's real release after every L attempt.
        # A failed throw must not leave the edge held indefinitely.
        return ([forward] if state["raw_keys1"] & 0x20 else [forward, "l"]), []

    # A dedicated close-range throw window is needed in Training, where the
    # second controller is intentionally inert.  The old macro stopped at a
    # 50-pixel gap, outside several profiles' strict throw ranges.  Reserve
    # the complete tail of the cycle for a controller-only approach and a
    # separated L edge.  The window must be long enough to close a fresh
    # match's gap; an eight-tick pulse could end before the fighter reached
    # even the largest profile's throw range and falsely report no throws.
    phase = tick % 512
    if mode != 0 and phase >= 448:
        if state["intro"] or state["round_end"] or state["hitstop"]:
            return [], []
        throw_limit = max(1, int(state["throw_range1"]) * 16 - 1)
        if distance >= throw_limit:
            # Keep P2 stationary while P1 closes; moving both controllers
            # back made the old fixture chase a receding target indefinitely.
            return [forward], []
        if (state["action1"] == 0 and state["hurt1"] == 0 and
                state["y1"] == 0 and state["down_state1"] == 0):
            # L is edge-triggered.  Keep a real release gap between attempts,
            # while holding forward so the strict dynamic range remains true.
            if (phase - 448) % 8 == 0:
                return [forward, "l"], []
            return [forward], []
        return [], []

    if distance > 50 * 16:
        # The long-run macros must reach real contact even after a fresh
        # roster/stage boot.  Training's second pad is ignored by the native
        # mode, so P1 closes the gap on its own there.
        if state["x1"] < state["x2"]:
            return ["right"], [] if mode == 2 else ["left"]
        return ["left"], [] if mode == 2 else ["right"]
    p1: list[str] = []
    p2: list[str] = []
    # Keep a release gap between every edge-triggered button.  The previous
    # long-run macro left Y/X and L/R phases adjacent, which could exercise
    # only the first edge and make the input-count report overstate coverage.
    # Every normal maps to its native action value: Y=1, X=2, L=3, B=4,
    # A=5, R=6.  The two directional sequences below are real QCF and uppercut
    # motions; they are deliberately separate from the six normal edges.
    if phase < 20:
        p1 = ["right"]
        p2 = ["left"]
    elif phase < 28:
        p1 = ["left"]
        p2 = ["right"]
    elif phase < 36:
        p1 = ["y"]
        p2 = ["b"]
    elif phase < 44:
        p1 = ["x"]
        p2 = ["a"]
    elif phase < 52:
        p1 = ["l"]
        p2 = ["r"]
    elif phase < 60:
        p1 = ["b"]
        p2 = ["x"]
    elif phase < 68:
        p1 = ["a"]
        p2 = ["y"]
    elif phase < 76:
        p1 = ["r"]
        p2 = ["l"]
    elif phase < 84:
        p1 = ["up", "right", "y"]
        p2 = ["up", "left", "x"]
    elif phase < 92:
        p1 = ["up", "right", "x"]
        p2 = ["up", "left", "y"]
    elif phase < 100:
        p1 = ["down"]
        p2 = ["down"]
    elif phase < 108:
        p1 = ["down", "y"]
        p2 = ["down", "y"]
    elif phase < 116:
        p1 = ["down", "right"]
        p2 = ["down", "left"]
    elif phase < 124:
        p1 = ["right", "y"]
        p2 = ["left", "y"]
    elif phase < 132:
        p1 = []
        p2 = []
    elif phase < 140:
        p1 = ["down", "l"]
        p2 = ["down", "l"]
    elif phase < 148:
        p1 = []
        p2 = []
    elif phase < 164:
        p1 = ["l"]
        p2 = ["l"]
    elif phase < 180:
        p1 = ["right" if state["x1"] < state["x2"] else "left", "l"]
        p2 = ["left" if state["x1"] < state["x2"] else "right", "l"]
    elif phase < 196:
        p1 = ["down", "b"]
        p2 = ["down", "a"]
    elif phase < 212:
        p1 = ["up"]
        p2 = ["up"]
    elif phase < 228:
        p1 = ["right"]
        p2 = ["left"]
    elif phase < 260:
        p1 = ["left"]
        p2 = ["right"]
    elif phase < 276:
        p1 = ["down", "right"]
        p2 = ["down", "left"]
    elif phase < 284:
        p1 = ["right", "y"]
        p2 = ["left", "y"]
    elif phase < 308:
        p1 = ["right"]
        p2 = ["left"]
    elif phase < 340:
        p1 = ["left"]
        p2 = ["right"]
    elif phase < 356:
        p1 = ["down", "r"]
        p2 = ["down", "b"]
    elif phase < 372:
        p1 = ["up", "left", "b"]
        p2 = ["up", "right", "a"]
    elif phase < 404:
        p1 = ["right"]
        p2 = ["left"]
    elif phase < 420:
        p1 = ["left"]
        p2 = ["right"]
    elif phase < 436:
        p1 = ["y"]
        p2 = ["x"]
    elif phase < 452:
        p1 = ["x"]
        p2 = ["y"]
    elif phase < 468:
        p1 = ["b"]
        p2 = ["a"]
    elif phase < 484:
        p1 = ["a"]
        p2 = ["b"]
    elif phase < 500:
        p1 = ["r"]
        p2 = ["l"]
    else:
        p1 = ["right"]
        p2 = ["left"]
    if mode == 2:
        # Training intentionally ignores controller two, but feeding it a
        # varied pad value proves that the inert path remains inert.
        p2 = ["left", "down", "x"] if (tick // 48) & 1 else ["right"]
    return p1, p2


def legacy_cadence_repro_keys(mode: int, tick: int,
                              state: dict[str, int]) -> tuple[list[str], list[str]]:
    """The original 650-tick defect macro, retained as a diagnostic fixture.

    This is intentionally not used by the endurance policy.  It preserves the
    exact controller sequence that reproduced e44's live trace-frame repeat at
    tick 636, so a candidate runtime fix can be compared without conflating it
    with the broader six-button coverage macro above.
    """

    distance = abs(state["x1"] - state["x2"])
    if distance > 50 * 16:
        if state["x1"] < state["x2"]:
            return ["right"], [] if mode == 2 else ["left"]
        return ["left"], [] if mode == 2 else ["right"]
    phase = tick % 384
    p1: list[str] = []
    p2: list[str] = []
    if phase < 24:
        p1 += ["right"]
        p2 += ["left"]
    elif phase < 48:
        p1 += ["left"]
        p2 += ["right"]
    elif phase < 66:
        p1 += ["down", "x"]
        p2 += ["down", "x"]
    elif phase < 84:
        p1 += ["down", "l"]
        p2 += ["down", "l"]
    elif phase < 102:
        p1 += ["up", "right", "y"]
        p2 += ["up", "left", "b"]
    elif phase < 126:
        p1 += ["left", "y"]
        p2 += ["right", "b"]
    elif phase < 150:
        p1 += ["down", "right", "y"]
        p2 += ["down", "left", "y"]
    elif phase < 174:
        p1 += ["right", "l"]
        p2 += ["left", "l"]
    elif phase < 198:
        p1 += ["down", "b"]
        p2 += ["down", "a"]
    elif phase < 222:
        p1 += ["left"]
        p2 += ["right", "y"]
    elif phase < 246:
        p1 += ["down", "x"]
        p2 += ["left"]
    elif phase < 270:
        p1 += ["right", "a"]
        p2 += ["down", "right", "b"]
    elif phase < 294:
        p1 += ["up", "left", "b"]
        p2 += ["up", "right", "y"]
    elif phase < 318:
        p1 += ["down", "l"]
        p2 += ["down", "x"]
    elif phase < 342:
        p1 += ["left", "a"]
        p2 += ["right", "l"]
    else:
        p1 += ["right"]
        p2 += ["left"]
    if mode == 2:
        p2 = ["left", "down", "x"] if (tick // 48) & 1 else ["right"]
    return p1, p2


class EnduranceRun:
    def __init__(self, mode: int, target: int, benchmark: bool = False,
                 coverage_required: bool = True):
        self.mode = mode
        self.target = target
        self.benchmark = benchmark
        self.coverage_required = coverage_required
        self.total_frames = 0
        self.live_frames = 0
        self.live_segments = 0
        self.last_live = False
        self.previous: dict[str, int] | None = None
        self.nonfight_streak = 0
        self.max_nonfight_streak = 0
        self.max_down_tick = 0
        self.max_pending_throw = 0
        self.max_down_state_duration = [0, 0]
        # The wake transition intentionally hands an input captured during
        # DOWN_WAKE to the normal buffer with age 7 (wakeAge + 1).  That
        # value is one tick older than the ordinary six-tick buffer contract,
        # but it is valid only for the single DOWN_WAKE -> FREE handoff and
        # must not become a general stale-input escape hatch.
        self.wake_handoff_active = [False, False]
        self.wake_handoff_count = 0
        self.down_state_duration = [0, 0]
        self.max_oam_visible = 0
        self.max_oam_sprites = 0
        self.max_x = 0
        self.min_x = 0xFFFF
        self.cadence_failures: list[dict[str, int]] = []
        self.native_timing_failures: list[dict[str, int]] = []
        self.ambient_failures: list[dict[str, int]] = []
        self.overflow_frames: list[dict[str, int]] = []
        self.frame_wraps = 0
        self.ambient_wraps = 0
        self.lag_counter_wraps = 0
        self.vblank_counter_wraps = 0
        self.lag_counter_increments = 0
        self.stable_fight_lag_increments = 0
        self.nonfight_lag_increments = 0
        self.vblank_flag_samples = 0
        self.max_spc_backlog = 0
        self.spc_backlog_nonzero_samples = 0
        self.spc_drain_events = 0
        self.spc_drain_bytes = 0
        self.spc_growth_streak = 0
        self.max_spc_growth_streak = 0
        self.spc_stable_nonzero_streak = 0
        self.max_spc_stable_nonzero_streak = 0
        self.spc_no_audio_streak = 0
        self.max_spc_no_audio_streak = 0
        self.spc_fifo_failures: list[dict[str, int | str]] = []
        self.last_audio_nonzero_batches = 0
        self.last_spc_fread = 0
        self.last_spc_fwrite = 0
        self.spc_read_advance_bytes = 0
        self.spc_write_advance_bytes = 0
        self.spc_read_pointer_wraps = 0
        self.spc_write_pointer_wraps = 0
        self.last_lag_counter = 0
        self.last_vblank_counter = 0
        self.native_screen_mismatch_samples = 0
        self.native_screen_mismatch_segments = 0
        self.native_screen_mismatch_streak = 0
        self.max_native_screen_mismatch_streak = 0
        self.native_screen_final = None
        self.video_samples = 0
        self.audio_samples = 0
        self.audio_nonzero_batches = 0
        self.input_counts: dict[str, int] = {}
        self.trace_magic_samples = 0
        self.events = {
            "attack": 0, "air": 0, "throw": 0, "guard": 0, "special": 0,
            "wake": 0, "down": 0, "round_change": 0, "result": 0,
            "pause": 0, "reset": 0, "result_continue": 0,
            "arcade_ladder": 0, "champion": 0, "champion_restart": 0,
            "menu_roster": 0, "real_contact": 0, "damage": 0,
        }
        self.normal_action_starts = {str(action): 0 for action in range(1, 7)}
        self.rosters: list[dict[str, object]] = []
        self.stages: set[int] = set()

    def inspect(self, host: LongRunHost, current: dict[str, int],
                p1: list[str], p2: list[str]) -> None:
        self.total_frames += 1
        if current.get("magic") != 0xAABA:
            raise AssertionError(("trace magic mismatch", self.total_frames, current))
        self.trace_magic_samples += 1
        self.native_screen_final = current["native_screen"]
        native_mismatch = current["native_screen"] != current["screen"]
        if native_mismatch:
            self.native_screen_mismatch_samples += 1
            self.native_screen_mismatch_segments += int(
                self.native_screen_mismatch_streak == 0)
            self.native_screen_mismatch_streak += 1
            self.max_native_screen_mismatch_streak = max(
                self.max_native_screen_mismatch_streak,
                self.native_screen_mismatch_streak)
        else:
            self.native_screen_mismatch_streak = 0
        self.last_lag_counter = current["lag_frame_counter"]
        self.last_vblank_counter = current["snes_vblank_count"]
        self.vblank_flag_samples += int(bool(current["vblank_flag"]))
        for key in p1 + p2:
            self.input_counts[key] = self.input_counts.get(key, 0) + 1
        live = (current["screen"] == SCREEN_FIGHT and
                current["native_screen"] == SCREEN_FIGHT and
                current["intro"] == 0 and
                current["round_end"] == 0 and not current["paused"])
        if live:
            self.live_frames += 1
            self.live_segments += int(not self.last_live)
            self.nonfight_streak = 0
            self.stages.add(int(current["arena"]))
            self.max_x = max(self.max_x, current["x1"], current["x2"])
            self.min_x = min(self.min_x, current["x1"], current["x2"])
        else:
            self.nonfight_streak += 1
            self.max_nonfight_streak = max(self.max_nonfight_streak,
                                           self.nonfight_streak)

        # The resident SPC pump exposes only its read/write cursors.  Keep
        # this host-side evidence read-only: the modulo-256 difference is the
        # queued command count, while decreases prove that commands drain.
        spc_backlog = current["spc_backlog"]
        if not 0 <= spc_backlog < 256:
            raise AssertionError(("SPC FIFO backlog out of bounds",
                                  self.total_frames, current))
        self.last_spc_fread = current["spc_fread"]
        self.last_spc_fwrite = current["spc_fwrite"]
        self.max_spc_backlog = max(self.max_spc_backlog, spc_backlog)
        self.spc_backlog_nonzero_samples += int(spc_backlog > 0)
        stable_fight_now = (current["screen"] == SCREEN_FIGHT and
                            current["native_screen"] == SCREEN_FIGHT)
        if self.previous is not None:
            previous_fread = self.previous["spc_fread"]
            previous_fwrite = self.previous["spc_fwrite"]
            self.spc_read_advance_bytes += (
                current["spc_fread"] - previous_fread) & 0xFF
            self.spc_write_advance_bytes += (
                current["spc_fwrite"] - previous_fwrite) & 0xFF
            self.spc_read_pointer_wraps += int(
                current["spc_fread"] < previous_fread)
            self.spc_write_pointer_wraps += int(
                current["spc_fwrite"] < previous_fwrite)
            previous_spc = self.previous["spc_backlog"]
            if spc_backlog < previous_spc:
                self.spc_drain_events += 1
                self.spc_drain_bytes += previous_spc - spc_backlog
            if spc_backlog > previous_spc:
                self.spc_growth_streak += 1
                self.max_spc_growth_streak = max(
                    self.max_spc_growth_streak, self.spc_growth_streak)
            else:
                self.spc_growth_streak = 0
            if stable_fight_now and spc_backlog > 0:
                if spc_backlog == previous_spc:
                    self.spc_stable_nonzero_streak += 1
                else:
                    self.spc_stable_nonzero_streak = 0
                self.max_spc_stable_nonzero_streak = max(
                    self.max_spc_stable_nonzero_streak,
                    self.spc_stable_nonzero_streak)
                if (host.audio_nonzero_batches == self.last_audio_nonzero_batches):
                    self.spc_no_audio_streak += 1
                else:
                    self.spc_no_audio_streak = 0
                self.max_spc_no_audio_streak = max(
                    self.max_spc_no_audio_streak, self.spc_no_audio_streak)
            else:
                self.spc_stable_nonzero_streak = 0
                self.spc_no_audio_streak = 0
        self.last_audio_nonzero_batches = host.audio_nonzero_batches
        if spc_backlog > MAX_SPC_BACKLOG:
            self.spc_fifo_failures.append({
                "kind": "backlog", "at": self.total_frames,
                "backlog": spc_backlog,
                "fread": current["spc_fread"],
                "fwrite": current["spc_fwrite"],
            })
        if self.spc_growth_streak > MAX_SPC_GROWTH_STREAK:
            self.spc_fifo_failures.append({
                "kind": "growth", "at": self.total_frames,
                "streak": self.spc_growth_streak,
                "backlog": spc_backlog,
            })
        if self.spc_no_audio_streak > MAX_SPC_STABLE_NO_AUDIO_STREAK:
            self.spc_fifo_failures.append({
                "kind": "stuck_without_pcm", "at": self.total_frames,
                "streak": self.spc_no_audio_streak,
                "backlog": spc_backlog,
            })

        if self.previous is not None:
            frame_delta = wrap_delta(current["frame"], self.previous["frame"])
            if current["frame"] < self.previous["frame"]:
                self.frame_wraps += 1
            lag_delta = wrap_delta(current["lag_frame_counter"],
                                   self.previous["lag_frame_counter"])
            if current["lag_frame_counter"] < self.previous["lag_frame_counter"]:
                self.lag_counter_wraps += 1
            if lag_delta:
                self.lag_counter_increments += lag_delta
            vblank_delta = wrap_delta(current["snes_vblank_count"],
                                      self.previous["snes_vblank_count"])
            if current["snes_vblank_count"] < self.previous["snes_vblank_count"]:
                self.vblank_counter_wraps += 1
            stable_fight = (current["screen"] == SCREEN_FIGHT and
                            self.previous["screen"] == SCREEN_FIGHT and
                            current["native_screen"] == SCREEN_FIGHT and
                            self.previous["native_screen"] == SCREEN_FIGHT)
            if stable_fight:
                self.stable_fight_lag_increments += lag_delta
                if lag_delta != 0 or vblank_delta != 1:
                    self.native_timing_failures.append({
                        "at": self.total_frames,
                        "lag_delta": lag_delta,
                        "previous_lag_frame_counter": self.previous["lag_frame_counter"],
                        "lag_frame_counter": current["lag_frame_counter"],
                        "vblank_delta": vblank_delta,
                        "previous_snes_vblank_count": self.previous["snes_vblank_count"],
                        "snes_vblank_count": current["snes_vblank_count"],
                        "vblank_flag": current["vblank_flag"],
                        "frame_delta": frame_delta,
                        "frame": current["frame"],
                        "previous_frame": self.previous["frame"],
                        "round_end": current["round_end"],
                        "hitstop": current["hitstop"],
                    })
            else:
                self.nonfight_lag_increments += lag_delta
            # The main-loop counter advances through intro, hitstop, pause
            # and round-end presentation too.  Only screen loads leave the
            # FIGHT scene, so every adjacent FIGHT trace must be unit cadence;
            # restricting this to live combat would hide a stall exactly when
            # the renderer is busiest.
            if (current["screen"] == SCREEN_FIGHT and
                    self.previous["screen"] == SCREEN_FIGHT and
                    current["native_screen"] == SCREEN_FIGHT and
                    self.previous["native_screen"] == SCREEN_FIGHT and
                    frame_delta != 1):
                self.cadence_failures.append({
                    "at": self.total_frames, "delta": frame_delta,
                    "frame": current["frame"], "paused": current["paused"],
                    "intro": current["intro"], "round_end": current["round_end"],
                    "hitstop": current["hitstop"],
                    "previous_lag_frame_counter": self.previous["lag_frame_counter"],
                    "lag_frame_counter": current["lag_frame_counter"],
                    "lag_delta": lag_delta,
                    "previous_snes_vblank_count": self.previous["snes_vblank_count"],
                    "snes_vblank_count": current["snes_vblank_count"],
                    "vblank_delta": vblank_delta,
                    "vblank_flag": current["vblank_flag"],
                    "native_screen": current["native_screen"],
                    "previous_native_screen": self.previous["native_screen"],
                })
            gameplay_now = (live and not current["paused"] and
                            not current["hitstop"])
            gameplay_before = (self.last_live and not self.previous["paused"] and
                               not self.previous["hitstop"])
            if gameplay_now and gameplay_before:
                if current["ambient_clock"] < self.previous["ambient_clock"]:
                    self.ambient_wraps += 1
                ambient_delta = wrap_delta(current["ambient_clock"],
                                           self.previous["ambient_clock"])
                if ambient_delta != 1 and "select" not in p1:
                    self.ambient_failures.append({
                        "at": self.total_frames, "delta": ambient_delta,
                        "clock": current["ambient_clock"],
                    })
            if current["round"] != self.previous["round"]:
                self.events["round_change"] += 1
            if current["paused"] and not self.previous["paused"]:
                self.events["pause"] += 1
            if current["screen"] == SCREEN_RESULT and self.previous["screen"] != SCREEN_RESULT:
                self.events["result"] += 1
            for side in (1, 2):
                previous_action = self.previous[f"action{side}"]
                action = current[f"action{side}"]
                if 1 <= action <= 6 and action != previous_action:
                    self.normal_action_starts[str(action)] += 1
                if current[f"connected{side}"] == 2 and \
                        self.previous[f"connected{side}"] != 2:
                    self.events["real_contact"] += 1
                if current[f"hp{side}"] < self.previous[f"hp{side}"]:
                    self.events["damage"] += 1

        if current["ppu_stat"] & 0xC0:
            self.overflow_frames.append({
                "at": self.total_frames, "status": current["ppu_stat"] & 0xFF,
            })
        self._check_bounds(host, current, live)
        for side in (1, 2):
            if current[f"action{side}"]:
                self.events["attack"] += 1
            if current[f"y{side}"]:
                self.events["air"] += 1
            if current[f"action{side}"] == 9:
                self.events["throw"] += 1
            if current[f"guard{side}"]:
                self.events["guard"] += 1
            if current[f"wave{side}"]:
                self.events["special"] += 1
            if current[f"action{side}"] == 7 and \
                    (self.previous is None or self.previous[f"action{side}"] != 7):
                self.events["special"] += 1
            if current[f"down_state{side}"]:
                self.events["down"] += 1
            if current[f"down_state{side}"] >= 4 or current[f"wake_age{side}"]:
                self.events["wake"] += 1
            self.max_down_tick = max(self.max_down_tick,
                                     current[f"down_tick{side}"])
            if (current["paused"] or current["screen"] != SCREEN_FIGHT or
                    current["round_end"] or current[f"hp{side}"] == 0):
                self.down_state_duration[side - 1] = 0
            elif current[f"down_state{side}"]:
                self.down_state_duration[side - 1] += 1
                self.max_down_state_duration[side - 1] = max(
                    self.max_down_state_duration[side - 1],
                    self.down_state_duration[side - 1])
            else:
                self.down_state_duration[side - 1] = 0
            if self.down_state_duration[side - 1] > MAX_DOWN_STATE_TICKS:
                raise AssertionError(("down-state softlock", self.total_frames,
                                      side, current))
            self.max_pending_throw = max(
                self.max_pending_throw, current[f"pending_throw_damage{side}"])
        self.last_live = live
        self.previous = current

    def _check_bounds(self, host: LongRunHost, current: dict[str, int], live: bool):
        for side in (1, 2):
            if not 0 <= current[f"hp{side}"] <= 128:
                raise AssertionError(("HP out of bounds", self.total_frames, current))
            if not 0 <= current[f"energy{side}"] <= 96:
                raise AssertionError(("energy out of bounds", self.total_frames, current))
            if not 0 <= current[f"fighter_id{side}"] < 12:
                raise AssertionError(("fighter id out of bounds", self.total_frames, current))
            if current[f"family{side}"] not in range(4):
                raise AssertionError(("special family out of bounds", self.total_frames, current))
            if current[f"down_state{side}"] not in range(6):
                raise AssertionError(("down state out of bounds", self.total_frames, current))
            if current["native_screen"] not in range(5):
                raise AssertionError(("native screen out of bounds", self.total_frames,
                                      current["native_screen"], current))
            if current[f"face{side}"] not in (0, 1):
                raise AssertionError(("facing out of bounds", self.total_frames, current))
            buffer_age = current[f"buffer_age{side}"]
            jump_buffer = current[f"jump_buffer{side}"]
            previous_down = (self.previous[f"down_state{side}"]
                             if self.previous is not None else None)
            wake_handoff = (previous_down == 5 and
                            current[f"down_state{side}"] == 0 and
                            current[f"invuln{side}"] == 4 and
                            (buffer_age == 7 or jump_buffer == 7))
            just_woke = False
            if wake_handoff:
                self.wake_handoff_active[side - 1] = True
                self.wake_handoff_count += 1
                just_woke = True
            if self.wake_handoff_active[side - 1]:
                # The handoff may remain frozen in hitstop.  Once a normal
                # simulation tick is available, the copied input must have
                # aged back into the ordinary six-tick window (or be gone).
                if just_woke:
                    # The first FREE trace is the handoff itself; its age 7
                    # is expected before the next controls tick can consume
                    # or decrement the copied input.
                    if buffer_age > 7 or jump_buffer > 7:
                        raise AssertionError(("wake handoff buffer exceeded",
                                              self.total_frames, side, current))
                elif current["hitstop"]:
                    if buffer_age > 7 or jump_buffer > 7:
                        raise AssertionError(("wake handoff buffer exceeded during hitstop",
                                              self.total_frames, side, current))
                elif buffer_age <= 6 and jump_buffer <= 6:
                    self.wake_handoff_active[side - 1] = False
                else:
                    raise AssertionError(("wake handoff buffer did not settle",
                                          self.total_frames, side, current))
            elif buffer_age > 6 or jump_buffer > 6:
                raise AssertionError(("input buffer out of bounds", self.total_frames, current))
        if current["x1"] > 0xFFFF or current["x2"] > 0xFFFF:
            raise AssertionError(("position out of fixed-point bounds", self.total_frames, current))
        if live:
            for side in (1, 2):
                position = current[f"x{side}"]
                if not 24 * 16 <= position <= 232 * 16:
                    raise AssertionError(("actor escaped stage clamp", self.total_frames,
                                          side, position, current))
        if not live:
            return
        raw = host.oam_memory()
        entries = oam_entries(raw)
        for side, base in ((0, 0), (1, 32)):
            actor = entries[base:base + 30]
            if any(piece["size"] != 1 or piece["tile"] >= 512
                   for piece in actor):
                raise AssertionError(("corrupt actor OAM entry", self.total_frames,
                                      side, actor))
            visible = sum(piece["y"] < 224 for piece in actor)
            self.max_oam_visible = max(self.max_oam_visible, visible)
            self.max_oam_sprites = max(self.max_oam_sprites, visible)
            if visible != 30:
                raise AssertionError(("live actor lost an OAM piece", self.total_frames,
                                      side, visible))
            verify_oam_layout(actor, side, current, self.total_frames)

    def result(self, host: LongRunHost, elapsed: float) -> dict[str, object]:
        required = {
            "attack": self.events["attack"] > 0,
            "air": self.events["air"] > 0,
            "throw": self.events["throw"] > 0,
            "guard": self.events["guard"] > 0,
            "special": self.events["special"] > 0,
            "down": self.events["down"] > 0,
            "wake": self.events["wake"] > 0,
            "round_progress": (self.events["round_change"] > 0 or
                                self.events["result"] > 0 or
                                self.events["reset"] > 0),
            "three_stages": len(self.stages) >= 3,
            "six_normal_actions": all(self.normal_action_starts[str(action)] > 0
                                       for action in range(1, 7)),
            "real_damage": self.events["real_contact"] > 0 and self.events["damage"] > 0,
        }
        if self.mode == 0:
            required.update({
                "arcade_ladder": self.events["arcade_ladder"] > 0,
                "champion": self.events["champion"] > 0,
                "champion_restart": self.events["champion_restart"] > 0,
            })
        else:
            required["menu_roster"] = self.events["menu_roster"] > 0
        if self.mode == 2:
            required["training_reset"] = self.events["reset"] > 0
        if self.coverage_required:
            missing = [name for name, seen in required.items() if not seen]
            if missing:
                raise AssertionError(("endurance coverage missing", self.mode, missing,
                                      self.events))
        if self.cadence_failures:
            raise AssertionError(("nonunit live frame cadence", self.cadence_failures[:3]))
        if self.native_timing_failures:
            raise AssertionError(("stable FIGHT native timing failure",
                                  self.native_timing_failures[:3]))
        if self.spc_fifo_failures:
            raise AssertionError(("resident SPC FIFO did not drain",
                                  self.spc_fifo_failures[:3]))
        if self.ambient_failures:
            raise AssertionError(("ambient clock stalled during live combat",
                                  self.ambient_failures[:3]))
        if self.overflow_frames:
            raise AssertionError(("PPU OBJ overflow during endurance", self.overflow_frames[:3]))
        if self.max_nonfight_streak > 720:
            raise AssertionError(("scene transition/softlock exceeded allowance",
                                  self.max_nonfight_streak))
        if self.max_native_screen_mismatch_streak > 720:
            raise AssertionError(("native force-blank transition exceeded allowance",
                                  self.max_native_screen_mismatch_streak))
        if self.live_frames == 0:
            raise AssertionError(("no live combat frames observed", self.mode))
        if host.video_samples == 0 or host.video_size != (256, 224):
            raise AssertionError(("native video callback geometry missing",
                                  self.mode, host.video_samples, host.video_size))
        if host.video_nonblank == 0:
            raise AssertionError(("native video callback stayed blank", self.mode))
        if host.audio_samples == 0 or host.audio_nonzero_batches == 0:
            raise AssertionError(("native PCM callback stayed silent", self.mode,
                                  host.audio_samples, host.audio_nonzero_batches))
        live_fraction = self.live_frames / max(1, self.total_frames)
        return {
            "mode": self.mode, "mode_name": ("arcade", "local_vs", "training")[self.mode],
            "status": "passed", "frames": self.total_frames,
            "target_live_frames": self.target,
            "coverage_required": self.coverage_required,
            "live_frames": self.live_frames, "live_segments": self.live_segments,
            "elapsed_seconds": round(elapsed, 3),
            "rosters": self.rosters, "stages": sorted(self.stages),
            "events": self.events, "required_coverage": required,
            "normal_action_starts": self.normal_action_starts,
            "live_fraction": round(live_fraction, 6),
            "native_frame_wraps": self.frame_wraps,
            "ambient_clock_wraps": self.ambient_wraps,
            "lag_frame_counter_last": self.last_lag_counter,
            "lag_frame_counter_wraps": self.lag_counter_wraps,
            "lag_frame_counter_increments": self.lag_counter_increments,
            "stable_fight_lag_increments": self.stable_fight_lag_increments,
            "nonfight_lag_increments": self.nonfight_lag_increments,
            "cadence_failures": self.cadence_failures[:8],
            "native_timing_failures": self.native_timing_failures[:8],
            "ambient_failures": self.ambient_failures[:8],
            "ppu_overflow_frames": self.overflow_frames[:8],
            "max_spc_backlog": self.max_spc_backlog,
            "spc_backlog_nonzero_samples": self.spc_backlog_nonzero_samples,
            "spc_drain_events": self.spc_drain_events,
            "spc_drain_bytes": self.spc_drain_bytes,
            "max_spc_growth_streak": self.max_spc_growth_streak,
            "max_spc_stable_nonzero_streak": self.max_spc_stable_nonzero_streak,
            "max_spc_no_audio_streak": self.max_spc_no_audio_streak,
            "spc_fifo_failures": self.spc_fifo_failures[:8],
            "spc_fread": self.last_spc_fread,
            "spc_fwrite": self.last_spc_fwrite,
            "spc_read_advance_bytes": self.spc_read_advance_bytes,
            "spc_write_advance_bytes": self.spc_write_advance_bytes,
            "spc_read_pointer_wraps": self.spc_read_pointer_wraps,
            "spc_write_pointer_wraps": self.spc_write_pointer_wraps,
            "spc_fifo_thresholds": {
                "max_backlog": MAX_SPC_BACKLOG,
                "max_growth_streak": MAX_SPC_GROWTH_STREAK,
                "max_stable_no_audio_streak": MAX_SPC_STABLE_NO_AUDIO_STREAK,
            },
            "snes_vblank_count_last": self.last_vblank_counter,
            "snes_vblank_counter_wraps": self.vblank_counter_wraps,
            "vblank_flag_samples": self.vblank_flag_samples,
            "native_screen_final": self.native_screen_final,
            "native_screen_mismatch_samples": self.native_screen_mismatch_samples,
            "native_screen_mismatch_segments": self.native_screen_mismatch_segments,
            "max_native_screen_mismatch_streak": self.max_native_screen_mismatch_streak,
            "input_counts": self.input_counts,
            "max_nonfight_streak": self.max_nonfight_streak,
            "max_down_tick": self.max_down_tick,
            "max_down_state_duration": self.max_down_state_duration,
            "max_pending_throw_damage": self.max_pending_throw,
            "wake_buffer_handoffs": self.wake_handoff_count,
            "max_oam_visible_actor_pieces": self.max_oam_visible,
            "max_oam_sprites": self.max_oam_sprites,
            "position_bounds": {"min": self.min_x, "max": self.max_x},
            "video_samples": host.video_samples,
            "video_nonblank_samples": host.video_nonblank,
            "video_geometry": list(host.video_size),
            "audio_samples": host.audio_samples,
            "audio_nonzero_batches": host.audio_nonzero_batches,
            "audio_peak_sampled": host.audio_peak,
            "trace_magic_samples": self.trace_magic_samples,
            "video_fps": host.video_fps,
            "audio_sample_rate": host.audio_sample_rate,
            "rom_sha256": rom_identity()[0],
        }


def tracked_step(host: LongRunHost, runner: EnduranceRun,
                 p1=(), p2=()) -> dict[str, int]:
    """Advance exactly one core tick and feed it to the endurance checker."""

    current = host.run(1, p1=p1, p2=p2)
    runner.inspect(host, current, list(p1), list(p2))
    return current


def tracked_pulse(host: LongRunHost, runner: EnduranceRun, key: str,
                  port: int = 0, settle: int = 12) -> dict[str, int]:
    """Hold a menu edge for three frames with a poll-safe release gap.

    The native menu samples edge-triggered buttons through the controller
    poll callback.  Three neutral frames before and after the hold make the
    pulse deterministic without changing gameplay input timing.
    """

    for _ in range(3):
        tracked_step(host, runner)
    for _ in range(3):
        tracked_step(host, runner,
                     p1=[key] if port == 0 else [],
                     p2=[key] if port == 1 else [])
    current = host.state()
    for _ in range(3):
        current = tracked_step(host, runner)
    for _ in range(settle):
        current = tracked_step(host, runner)
    return current


def tracked_wait_screen(host: LongRunHost, runner: EnduranceRun,
                        wanted: int, maximum: int = 720) -> dict[str, int]:
    for _ in range(maximum):
        current = host.state()
        if screen_ready(current, wanted):
            return current
        current = tracked_step(host, runner)
    raise AssertionError(("uninterrupted menu transition stalled", wanted,
                          host.state()))


def tracked_wait_live(host: LongRunHost, runner: EnduranceRun,
                      maximum: int = 240) -> dict[str, int]:
    for _ in range(maximum):
        current = host.state()
        if (screen_ready(current, SCREEN_FIGHT) and current["intro"] == 0):
            return current
        current = tracked_step(host, runner)
    raise AssertionError(("uninterrupted fight intro stalled", host.state()))


def assert_loaded_state(current: dict[str, int], mode: int, fighter: int,
                        fighter2: int, stage: int, route: str) -> None:
    """Check the requested menu choice against the cartridge's live trace."""

    expected_p2 = (fighter2 if mode in (1, 2) else (fighter + 1 +
                   int(current["arcade"])) % 12)
    if (not screen_ready(current, SCREEN_FIGHT) or current["intro"] != 0):
        raise AssertionError(("requested menu route did not reach live fight",
                              route, current))
    if current["fighter_id1"] != fighter or current["fighter_id2"] != expected_p2:
        raise AssertionError(("live trace fighter IDs disagree with menu choice",
                              route, {"requested": [fighter, expected_p2],
                                      "actual": [current["fighter_id1"],
                                                 current["fighter_id2"]],
                                      "state": current}))
    if current["arena"] != stage:
        raise AssertionError(("live trace arena disagrees with menu choice",
                              route, {"requested": stage, "actual": current["arena"],
                                      "state": current}))


def move_cursor(host: LongRunHost, runner: EnduranceRun,
                current: int, desired: int, port: int = 0) -> None:
    # The roster is a 4x3 grid: vertical edges move four slots. A forward-only
    # sweep can issue 22 deliberate cursor pulses for two fighters and spend
    # longer than the softlock allowance in a healthy menu. Use its real grid
    # controls, retaining every per-transition timeout and loaded-ID check.
    routes = (
        (), ("right",), ("right", "right"), ("down", "left"),
        ("down",), ("down", "right"), ("down", "right", "right"),
        ("up", "left"), ("up",), ("up", "right"),
        ("left", "left"), ("left",),
    )
    for key in routes[(int(desired) - int(current)) % 12]:
        tracked_pulse(host, runner, key, port)


def move_arena_cursor(host: LongRunHost, runner: EnduranceRun,
                      current: int, desired: int) -> None:
    """Move the three-entry arena cursor with the menu's down edge."""

    steps = (int(desired) - int(current)) % 3
    for _ in range(steps):
        tracked_pulse(host, runner, "down")


def select_from_menu(host: LongRunHost, runner: EnduranceRun, mode: int,
                     fighter: int, fighter2: int, stage: int) -> dict[str, int]:
    """Complete the native select/arena flow without closing the core."""

    current = tracked_wait_screen(host, runner, SCREEN_SELECT)
    move_cursor(host, runner, current["selected"], fighter)
    tracked_pulse(host, runner, "a")
    if mode in (1, 2):
        current = tracked_wait_screen(host, runner, SCREEN_SELECT)
        port = 0 if mode == 2 else 1
        move_cursor(host, runner, current["selected2"], fighter2, port=port)
        tracked_pulse(host, runner, "a", port=port)
    current = tracked_wait_screen(host, runner, SCREEN_ARENA)
    move_arena_cursor(host, runner, current["arena"], stage)
    tracked_pulse(host, runner, "a")
    return tracked_wait_live(host, runner)


def roster_transition(host: LongRunHost, runner: EnduranceRun, mode: int,
                      fighter: int, fighter2: int, stage: int) -> dict[str, int]:
    """Use START+B roster navigation from a live match, never a host reboot."""

    current = host.state()
    if not screen_ready(current, SCREEN_FIGHT) or current["paused"]:
        raise AssertionError(("roster transition requires live fight", current))
    tracked_pulse(host, runner, "start")
    if host.state()["paused"] != 1:
        raise AssertionError(("three-frame pause pulse did not pause", host.state()))
    tracked_pulse(host, runner, "b")
    if not screen_ready(host.state(), SCREEN_SELECT):
        raise AssertionError(("pause B did not open roster select", host.state()))
    current = select_from_menu(host, runner, mode, fighter, fighter2, stage)
    assert_loaded_state(current, mode, fighter, fighter2, stage, "pause-b-select")
    runner.events["menu_roster"] += 1
    runner.rosters.append({"fighter1": fighter, "fighter2": fighter2,
                           "stage": stage, "route": "pause-b-select"})
    runner.stages.add(stage)
    return current


def training_reset(host: LongRunHost, runner: EnduranceRun) -> dict[str, int]:
    """Reset Training through Select while preserving the active core session."""

    before = host.state()
    if not screen_ready(before, SCREEN_FIGHT) or before["paused"]:
        return before
    tracked_pulse(host, runner, "select")
    for _ in range(16):
        tracked_step(host, runner)
    after = host.state()
    runner.events["reset"] += 1
    if after["hp1"] != 128 or after["hp2"] != 128:
        raise AssertionError(("training reset did not restore HP", before, after))
    return after


def result_transition(host: LongRunHost, runner: EnduranceRun, mode: int,
                      fighter: int, fighter2: int, stage: int) -> dict[str, int]:
    """Continue a native result screen, including Arcade champion -> title."""

    result = host.state()
    if not screen_ready(result, SCREEN_RESULT):
        return result
    champion = mode == 0 and result["champion"] == 1
    won_ladder = mode == 0 and not champion and result["wins1"] == 2
    tracked_pulse(host, runner, "a")
    if champion:
        runner.events["champion"] += 1
        tracked_wait_screen(host, runner, SCREEN_TITLE)
        # showTitle preserves Arcade mode; A starts the normal title -> select
        # route and lets this single core session exercise the champion return.
        tracked_pulse(host, runner, "a")
        tracked_wait_screen(host, runner, SCREEN_SELECT)
        current = select_from_menu(host, runner, mode, fighter, fighter2, stage)
        assert_loaded_state(current, mode, fighter, fighter2, stage,
                            "champion-title")
        runner.events["champion_restart"] += 1
        runner.rosters.append({"fighter1": fighter, "fighter2": fighter2,
                               "stage": stage, "route": "champion-title"})
        runner.stages.add(stage)
        return current
    if won_ladder:
        runner.events["arcade_ladder"] += 1
    else:
        runner.events["result_continue"] += 1
    return tracked_wait_live(host, runner)


def run_mode(mode: int, target: int, benchmark: bool = False,
             coverage_required: bool = True) -> dict[str, object]:
    started = time.monotonic()
    core_info = core_identity()
    runner = EnduranceRun(mode, target, benchmark, coverage_required)
    host: LongRunHost | None = None
    fighter = (mode * 3) % 12
    fighter2 = (fighter + 1) % 12
    stage = mode % 3
    next_roster = ROSTER_INTERVAL
    next_reset = TRAINING_RESET_INTERVAL
    report: dict[str, object] | None = None
    progression_frames = 0
    try:
        # The measured session starts after the one-time native boot and then
        # keeps this exact core alive until target native ticks are observed.
        host = LongRunHost(video_interval=120)
        boot(host, mode, fighter, fighter2, stage)
        initial = host.state()
        assert_loaded_state(initial, mode, fighter, fighter2, stage, "initial")
        runner.rosters.append({"fighter1": fighter, "fighter2": fighter2,
                               "stage": stage, "route": "initial"})
        runner.stages.add(stage)
        runner.previous = None
        runner.last_live = False
        # The full gate measures one native live-combat hour.  Menu/intro,
        # pause and round-result frames remain in the same session and are
        # reported separately, so they may extend total emulated frames past
        # the live target.  The short benchmark retains its fixed total-frame
        # contract for quick cadence feedback.
        def reached_target() -> bool:
            return (runner.total_frames >= target if benchmark else
                    runner.live_frames >= target)

        while not reached_target():
            current = host.state()
            # setScreenOff()/loadBackground can make the native screen leave
            # FIGHT before the trace is republished.  Do not feed combat or
            # menu edges during that force-blank interval; the next tracked
            # tick will publish the new screen and remain subject to the
            # strict cadence checks once both views agree again.
            if current["screen"] != current["native_screen"]:
                tracked_step(host, runner)
                continue
            if current["screen"] == SCREEN_RESULT:
                fighter = (fighter + 2) % 12
                fighter2 = (fighter + 3) % 12
                stage = (stage + 1) % 3
                result_transition(host, runner, mode, fighter, fighter2, stage)
                continue
            if (mode in (1, 2) and runner.total_frames >= next_roster and
                    screen_ready(current, SCREEN_FIGHT) and not current["paused"]):
                fighter = (fighter + 2) % 12
                fighter2 = (fighter + 3) % 12
                stage = (stage + 1) % 3
                roster_transition(host, runner, mode, fighter, fighter2, stage)
                next_roster += ROSTER_INTERVAL
                continue
            if (mode == 2 and runner.total_frames >= next_reset and
                    screen_ready(current, SCREEN_FIGHT) and not current["paused"]):
                training_reset(host, runner)
                next_reset += TRAINING_RESET_INTERVAL
                continue
            # Complete one observed ladder before the mixed macro. Interleaving
            # short progression windows with broad attack coverage can lose
            # every match against a changed CPU and omit the champion route.
            # The remainder of the same full-hour session still has to meet
            # every original combat/normal/guard/special/three-stage check.
            progression = mode == 0 and not benchmark and runner.events["champion_restart"] == 0
            p1, p2 = keys_for(mode, runner.total_frames, current, progression)
            progression_frames += int(progression)
            tracked_step(host, runner, p1, p2)
            if runner.total_frames and runner.total_frames % PROGRESS_INTERVAL == 0:
                print(json.dumps({
                    "mode": mode, "frames": runner.total_frames,
                    "target": target, "live": runner.live_frames,
                    "pid": os.getpid(), "core_frames": host.frames,
                }), flush=True)
        elapsed = time.monotonic() - started
        report = runner.result(host, elapsed)
        report["benchmark"] = benchmark
        report["core_frames_including_boot"] = host.frames
        report["core"] = core_info
        report["uninterrupted_session"] = True
        report["initial_ladder_policy_frames"] = progression_frames
        return report
    finally:
        if host is not None:
            host.close()
            if report is not None:
                report["core_boots"] = host.boot_count
                report["core_unloads"] = host.unload_count
                report["core_reboots"] = max(0, host.boot_count - 1)


def run_benchmark() -> dict[str, object]:
    rom_sha, rom_bytes = rom_identity()
    core_info = core_identity()
    started = time.monotonic()
    modes = {}
    for mode in range(3):
        modes[str(mode)] = run_mode(mode, BENCHMARK_FRAMES, benchmark=True,
                                    coverage_required=False)
    result = {
        "status": "passed", "rom_sha256": rom_sha, "rom_bytes": rom_bytes,
        "frames_per_mode": BENCHMARK_FRAMES, "modes": modes,
        "benchmark_contract": {
            "strict_live_cadence": True,
            "strict_stable_fight_native_timing": True,
            "strict_resident_spc_fifo": True,
            "strict_ambient_cadence": True,
            "strict_trace_bounds": True,
            "strict_oam_bounds": True,
            "strict_video_geometry": True,
            "strict_video_fps": True,
            "strict_pcm_callback": True,
            "strict_trace_magic": True,
            "coverage_complete": False,
        },
        "core": core_info,
        "harness_sha256": harness_identity(),
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
    BENCHMARK_PATH.parent.mkdir(parents=True, exist_ok=True)
    BENCHMARK_PATH.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)
    return result


def run_legacy_cadence_repro() -> dict[str, object]:
    """Replay the preserved e44 live-cadence fixture without full coverage."""

    rom_sha, _ = rom_identity()
    host = LongRunHost(video_interval=1)
    failures: list[dict[str, object]] = []
    try:
        boot(host, 0, 0, 1, 0)
        previous: dict[str, int] | None = None
        for tick in range(650):
            before = host.state()
            p1, p2 = legacy_cadence_repro_keys(0, tick, before)
            after = host.run(1, p1=p1, p2=p2)
            delta = None if previous is None else wrap_delta(after["frame"], previous["frame"])
            if delta not in (None, 1):
                failure = {"tick": tick, "delta": delta, "p1": p1, "p2": p2,
                           "before": before, "after": after}
                failures.append(failure)
                break
            previous = after
        result = {"status": "passed" if not failures else "failed",
                  "rom_sha256": rom_sha, "ticks": 650,
                  "failures": failures, "host_frames": host.frames,
                  "video_samples": host.video_samples}
    finally:
        host.close()
    path = ROOT / "build/endurance-cadence-repro-current.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)
    if failures:
        raise AssertionError(("legacy cadence reproduction failed", failures[0]))
    return result


def full_gate() -> int:
    rom_sha, rom_bytes = rom_identity()
    core_info = core_identity()
    if not BENCHMARK_PATH.exists():
        raise RuntimeError("run --benchmark before the endurance gate")
    benchmark = json.loads(BENCHMARK_PATH.read_text())
    if (benchmark.get("rom_sha256") != rom_sha or
            int(benchmark.get("rom_bytes", 0)) != rom_bytes or
            benchmark.get("harness_sha256") != harness_identity() or
            benchmark.get("status") != "passed" or
            benchmark.get("benchmark_contract", {}).get("strict_live_cadence") is not True or
            benchmark.get("benchmark_contract", {}).get("strict_stable_fight_native_timing") is not True or
            benchmark.get("benchmark_contract", {}).get("strict_resident_spc_fifo") is not True or
            benchmark.get("benchmark_contract", {}).get("strict_ambient_cadence") is not True or
            benchmark.get("benchmark_contract", {}).get("strict_trace_bounds") is not True or
            benchmark.get("benchmark_contract", {}).get("strict_oam_bounds") is not True or
            benchmark.get("benchmark_contract", {}).get("strict_video_geometry") is not True or
            benchmark.get("benchmark_contract", {}).get("strict_video_fps") is not True or
            benchmark.get("benchmark_contract", {}).get("strict_pcm_callback") is not True or
            benchmark.get("benchmark_contract", {}).get("strict_trace_magic") is not True or
            benchmark.get("core") != core_info):
        raise RuntimeError("endurance benchmark is missing or belongs to another ROM")
    started = time.monotonic()
    # Query the core's declared NTSC timing rather than assuming exactly 60
    # Hz.  216,000 frames is short of one wall-clock hour at 60.0988 fps.
    timing_host = LongRunHost(video_interval=120)
    native_fps = timing_host.video_fps
    timing_host.close()
    target_frames = int(math.ceil(native_fps * HOUR_SECONDS))
    processes: dict[int, subprocess.Popen] = {}
    for mode in range(3):
        command = [sys.executable, str(Path(__file__).resolve()), "--mode", str(mode),
                   "--frames", str(target_frames), "--worker"]
        # Each worker is a separate process, so the libretro DLL remains
        # single-instance within each process while all three mode hours can
        # progress independently.  stdout/stderr stay inherited for sparse
        # PID-tagged progress and immediate failure diagnostics.
        processes[mode] = subprocess.Popen(command, cwd=ROOT)
    reports = {}
    for mode, process in processes.items():
        returncode = process.wait()
        path = Path(str(MODE_REPORT).format(mode=mode))
        if returncode or not path.exists():
            raise RuntimeError(("endurance mode failed", mode, returncode,
                                str(path)))
        report = json.loads(path.read_text())
        worker_fps = float(report.get("video_fps", 0.0))
        if (not math.isfinite(worker_fps) or
                abs(worker_fps - native_fps) > VIDEO_FPS_EPSILON):
            raise RuntimeError(("endurance worker video FPS differs from native timing",
                                mode, worker_fps, native_fps,
                                VIDEO_FPS_EPSILON, report))
        if (report.get("status") != "passed" or
                report.get("rom_sha256") != rom_sha or
                report.get("uninterrupted_session") is not True or
                int(report.get("core_boots", 0)) != 1 or
                int(report.get("core_unloads", 0)) != 1 or
                int(report.get("core_reboots", -1)) != 0 or
                int(report.get("target_live_frames", 0)) != target_frames or
                int(report.get("live_frames", 0)) < target_frames or
                int(report.get("native_frame_wraps", 0)) < 3 or
                len(report.get("stages", [])) < 3):
            raise RuntimeError(("endurance mode report failed", mode, report))
        reports[str(mode)] = report
    aggregate = {
        "suite": "endurance", "status": "passed", "rom_sha256": rom_sha,
        "rom_bytes": rom_bytes, "target_live_frames_per_mode": target_frames,
        "native_fps": native_fps, "hours_per_mode": target_frames / native_fps / HOUR_SECONDS,
        "benchmark_contract": dict(benchmark["benchmark_contract"]),
        "contract_flags": {
            "strict_live_cadence": True,
            "strict_stable_fight_native_timing": True,
            "strict_resident_spc_fifo": True,
            "strict_ambient_cadence": True,
            "strict_trace_bounds": True,
            "strict_oam_bounds": True,
            "strict_video_geometry": True,
            "strict_video_fps": True,
            "strict_pcm_callback": True,
            "strict_trace_magic": True,
            "worker_video_fps_match": True,
            "video_fps_epsilon": VIDEO_FPS_EPSILON,
        },
        "harness_sha256": harness_identity(),
        "core": core_info,
        "modes": reports,
        "total_frames_per_mode": {mode: report["frames"]
                                  for mode, report in reports.items()},
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
    AUTHORITATIVE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    AUTHORITATIVE_REPORT.write_text(json.dumps(aggregate, indent=2) + "\n")
    print(json.dumps({"status": "passed", "report": str(AUTHORITATIVE_REPORT),
                      "rom_sha256": rom_sha}), flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--cadence-repro", action="store_true")
    parser.add_argument("--checkpoint", action="store_true",
                        help="run strict partial coverage without full-hour route requirements")
    parser.add_argument("--mode", type=int, choices=(0, 1, 2))
    parser.add_argument("--frames", type=int, default=0)
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    if args.benchmark:
        run_benchmark()
        return 0
    if args.cadence_repro:
        run_legacy_cadence_repro()
        return 0
    if args.mode is not None:
        target = args.frames
        if target <= 0:
            timing_host = LongRunHost(video_interval=120)
            target = int(math.ceil(timing_host.video_fps * HOUR_SECONDS))
            timing_host.close()
        report = run_mode(args.mode, target, benchmark=target <= BENCHMARK_FRAMES,
                          coverage_required=not args.checkpoint and target > BENCHMARK_FRAMES)
        path = Path(str(MODE_REPORT).format(mode=args.mode))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({"status": report["status"], "mode": args.mode,
                          "frames": report["frames"], "report": str(path)}), flush=True)
        return 0
    return full_gate()


if __name__ == "__main__":
    raise SystemExit(main())

