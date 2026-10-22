"""Capture read-only diagnostics around the unchanged mode2 endurance policy.

Run through tools/run_background.py. Alternate ROM/symbol paths permit a
bounded negative control without replacing the current cartridge. All native
cadence, timing, SPC, PPU, ambient and coverage assertions remain authoritative;
failure diagnostics are written even when the original runner rejects a ROM.
"""
from __future__ import annotations

import argparse
from collections import deque
import ctypes as C
import hashlib
import json
import re
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_endurance as endurance


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path,
                        default=endurance.ROOT / "dist/abaqus-after-hours.sfc")
    parser.add_argument("--symbols", type=Path,
                        default=endurance.ROOT / "dist/abaqus-after-hours.sym")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--frames", type=int, default=216356)
    parser.add_argument("--checkpoint", action="store_true",
                        help="omit full-hour coverage requirements, retaining all strict checks")
    parser.add_argument("--watch-at", type=int, action="append",
                        help="capture callbacks around this measured tick (repeatable)")
    args = parser.parse_args()
    watched_points = args.watch_at or (137337, 174198, 175243)
    if args.frames <= 0:
        parser.error("--frames must be positive")
    raw = args.rom.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    symbols = {}
    for address, name in re.findall(r"^([0-9a-fA-F]{6,8})\s+(\S+)\s*$",
                                    args.symbols.read_text(), re.M):
        value = int(address, 16)
        if value >> 16 == 0x7E:
            symbols[name] = value & 0xFFFF
        elif value >> 16 == 0x7F:
            symbols[name] = 0x10000 | (value & 0xFFFF)
        elif value < 0x20000:
            symbols[name] = value

    class DiagnosticHost(endurance.LongRunHost):
        def __init__(self, *positional, **keywords):
            keywords["rom"] = args.rom
            super().__init__(*positional, **keywords)

        def _symbol_offset(self, symbol, fallback):
            # Alternate cartridges must use their own symbol file, never a
            # fallback offset or symbols belonging to the current build.
            return symbols[symbol]

    runners = []

    class DiagnosticRun(endurance.EnduranceRun):
        def __init__(self, *positional, **keywords):
            super().__init__(*positional, **keywords)
            self.ring = deque(maxlen=16)
            self.windows = []
            self.until = -1
            self.recovery_count = 0
            self.recoveries = []
            self.full_health_refreshes = []
            runners.append(self)

        def inspect(self, host, current, p1, p2):
            before = (len(self.cadence_failures), len(self.native_timing_failures))
            super().inspect(host, current, p1, p2)
            sample = {"at": self.total_frames, "core_callback": host.frames,
                      "p1": p1, "p2": p2, "state": dict(current),
                      "native": {name: C.string_at(host.ram + symbols[name], size).hex()
                                 for name, size in (("fighters", 128), ("frame", 2),
                                                    ("hudHp", 2), ("hudEnergy", 2),
                                                    ("hudSeconds", 1), ("hudDirty", 1),
                                                    ("actorUploadDirty", 1),
                                                    ("impactHudPending", 1))}}
            previous = self.ring[-1] if self.ring else None
            if previous:
                old = bytes.fromhex(previous["native"]["fighters"])
                new = bytes.fromhex(sample["native"]["fighters"])
                recovered = [p for p in range(2) if old[p * 64 + 14] < new[p * 64 + 14] == 128]
                if recovered:
                    self.recovery_count += len(recovered)
                    if len(self.recoveries) < 48:
                        self.recoveries.append({"players": recovered, "before": previous, "after": sample})
                # Preserve evidence of timer-driven energy refreshes even
                # when neither HP value changes. Observation only: no new gate.
                if (current["frame"] % 120 == 0 and current["frame"] & 15 and
                        len(self.full_health_refreshes) < 16):
                    old_energy = bytes.fromhex(previous["native"]["hudEnergy"])
                    new_energy = bytes.fromhex(sample["native"]["hudEnergy"])
                    players = [p for p in range(2) if old[p * 64 + 14] == new[p * 64 + 14] == 128
                               and old_energy[p] != new_energy[p] == new[p * 64 + 15]]
                    if players:
                        self.full_health_refreshes.append({"players": players, "before": previous, "after": sample})
            self.ring.append(sample)
            failed = before != (len(self.cadence_failures), len(self.native_timing_failures))
            watched = any(abs(self.total_frames - point) <= 4
                          for point in watched_points)
            if failed and len(self.windows) < 32:
                self.windows.append({"failure_at": self.total_frames,
                                     "samples": list(self.ring)})
                self.until = self.total_frames + 8
            elif self.total_frames <= self.until and self.windows:
                self.windows[-1]["samples"].append(sample)
            if watched:
                self.windows.append({"parent_regression_at": self.total_frames,
                                     "samples": [sample]})

    # Adapt only cartridge identity and observation. The original run_mode,
    # controller routes, inspect(), result() and every threshold run unchanged.
    endurance.LongRunHost = DiagnosticHost
    endurance.EnduranceRun = DiagnosticRun
    endurance.rom_identity = lambda: (digest, len(raw))
    report = {"status": "failed", "rom": str(args.rom.resolve()),
              "symbols": str(args.symbols.resolve()), "rom_sha256": digest,
              "checksum": f"{int.from_bytes(raw[0x7fde:0x7fe0], 'little'):04X}",
              "harness_sha256": endurance.harness_identity(),
              "diagnostic_harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "controller_only": True, "memory_writes": False,
              "savestates": False, "gui": False, "audio_device": False}
    started = time.monotonic()
    try:
        report["endurance"] = endurance.run_mode(
            2, args.frames, benchmark=False, coverage_required=not args.checkpoint)
        report["status"] = "passed"
    except Exception as exc:
        report["error"] = repr(exc)
    finally:
        if runners:
            runner = runners[0]
            report["observed"] = {
                "frames": runner.total_frames, "live_frames": runner.live_frames,
                "training_cpu_live_frames": runner.training_cpu_live_frames,
                "cadence_failures": runner.cadence_failures,
                "native_timing_failures": runner.native_timing_failures,
                "ambient_failures": runner.ambient_failures,
                "ppu_overflow_frames": runner.overflow_frames,
                "spc_fifo_failures": runner.spc_fifo_failures,
                "recovery_count": runner.recovery_count,
                "recoveries": runner.recoveries,
                "full_health_refreshes": runner.full_health_refreshes,
                "windows": runner.windows, "last_samples": list(runner.ring)}
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({key: report[key] for key in
                          ("status", "rom_sha256", "elapsed_seconds")}), flush=True)
    return int(report["status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
