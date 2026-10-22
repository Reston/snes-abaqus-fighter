"""Silent controller-only stress of simultaneous contacts on the current ROM.

Mirror matches make both contacts occur on the same simulation tick.  The
existing endurance checker still enforces cadence, native timing, bounds,
ambient, PPU and SPC rules on every measured callback.  General endurance
coverage is intentionally partial; this diagnostic is not a live-hour gate.

Run through tools/run_background.py, with an explicit ignored report path.
It never replaces the six-suite or release reports and never opens a window,
audio device or save state, or writes emulated memory.
"""

from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_endurance as endurance
from make_crossup_review import process_contract


ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "uppercut": {"keys": ("down", "l"), "action": 8, "knockdown": True},
    "sweep": {"keys": ("down", "r"), "action": 6, "knockdown": True},
    "special-contact": {"keys": ("down", "x"), "action": 7, "knockdown": False},
    "wave-clash": {"keys": ("down", "x"), "action": 7, "knockdown": False},
}
WAVE_FIGHTERS = (0, 1, 4, 6, 8, 9, 11)
FAILURE_FIELDS = (
    "cadence_failures", "native_timing_failures", "ambient_failures",
    "ppu_overflow_frames", "spc_fifo_failures",
)


def require(condition: object, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def ready(state: dict[str, int], side: int, needs_energy: bool) -> bool:
    return (
        state[f"hp{side}"] > 0
        and state[f"y{side}"] == 0
        and all(state[key + str(side)] == 0 for key in
                ("action", "hurt", "down_state", "invuln", "landing"))
        and (not needs_energy or state[f"energy{side}"] >= 32)
    )


def run_case(fighter: int, stage: int, pattern: str, target: int) -> dict:
    policy = PATTERNS[pattern]
    runner = endurance.EnduranceRun(1, target, benchmark=False, coverage_required=False)
    host = endurance.LongRunHost(video_interval=120)
    row = {"fighter1": fighter, "fighter2": fighter, "stage": stage,
           "pattern": pattern, "status": "failed"}
    recent: deque[dict] = deque(maxlen=24)
    starts, contacts, knockdowns, clashes, commands = [0, 0], 0, 0, 0, 0
    draws, draw_resets, pending_draw = 0, 0, None
    minimum_hp = [128, 128]
    samples: list[dict] = []
    began = time.monotonic()
    try:
        endurance.boot(host, 1, fighter, fighter, stage)
        endurance.assert_loaded_state(host.state(), 1, fighter, fighter, stage,
                                      "simultaneous-contact-budget")
        runner.rosters.append({"fighter1": fighter, "fighter2": fighter,
                               "stage": stage, "route": "cold-boot"})
        runner.stages.add(stage)
        while runner.live_frames < target:
            require(runner.total_frames < target * 8 + 1200,
                    "Diagnostic exhausted callback budget before live-frame target")
            old = host.state()
            if endurance.screen_ready(old, endurance.SCREEN_RESULT):
                endurance.result_transition(host, runner, 1, fighter, fighter, stage)
                continue
            p1, p2 = (), ()
            stable = (endurance.screen_ready(old, endurance.SCREEN_FIGHT)
                      and not any(old[key] for key in
                                  ("paused", "intro", "round_end", "hitstop")))
            if stable and all(ready(old, side, policy["action"] == 7) for side in (1, 2)):
                gap = abs(old["x2"] - old["x1"])
                # Rush moves advance during startup. At point-blank range
                # matching rushes can cross before their active window.
                rush = pattern == "special-contact" and old["family1"] == 1
                spacing = 64 if rush else 30
                if pattern != "wave-clash" and gap > spacing * 16:
                    p1 = ("right",) if old["x1"] < old["x2"] else ("left",)
                    p2 = ("left",) if old["x1"] < old["x2"] else ("right",)
                elif rush and gap < (spacing - 3) * 16:
                    p1 = ("left",) if old["x1"] < old["x2"] else ("right",)
                    p2 = ("right",) if old["x1"] < old["x2"] else ("left",)
                elif not old["wave1"] and not old["wave2"]:
                    p1 = p2 = policy["keys"]
                    commands += 1
            current = endurance.tracked_step(host, runner, p1, p2)
            recent.append({"at": runner.total_frames, "p1": list(p1), "p2": list(p2),
                           "before": old, "after": current})
            for side in (1, 2):
                minimum_hp[side - 1] = min(minimum_hp[side - 1], current[f"hp{side}"])
                starts[side - 1] += int(current[f"action{side}"] == policy["action"]
                                        and old[f"action{side}"] != policy["action"])
            if (not old["round_end"] and current["round_end"]
                    and current["hp1"] == current["hp2"] == 0):
                draws += 1
                pending_draw = current["round"]
            if pending_draw is not None:
                require(current["wins1"] == current["wins2"] == 0
                        and current["round"] == pending_draw
                        and current["screen"] == endurance.SCREEN_FIGHT,
                        "Double KO must award no win and repeat the same round")
                if not current["round_end"] and current["intro"]:
                    require(current["hp1"] == current["hp2"] == 128,
                            "Double-KO round restart must restore both fighters")
                    draw_resets += 1
                    pending_draw = None
            trade = all(current[f"hp{side}"] < old[f"hp{side}"] for side in (1, 2))
            double_down = trade and current["down_state1"] == current["down_state2"] == 2
            # Both waves vanish while they still have life, with no damage or
            # scene transition. Their ordinary expiration cannot satisfy this.
            clash = (pattern == "wave-clash" and stable
                     and all(old[f"wave{side}"] and old[f"wave_life{side}"] > 1
                             and not current[f"wave{side}"] for side in (1, 2))
                     and all(current[f"hp{side}"] == old[f"hp{side}"] for side in (1, 2))
                     and not current["round_end"])
            contacts += int(trade)
            knockdowns += int(double_down)
            clashes += int(clash)
            if (trade or clash) and len(samples) < 8:
                samples.append({"at": runner.total_frames, "before": old, "after": current})
        row["native"] = runner.result(host, time.monotonic() - began)
        require(min(starts) >= 2, "Coverage missing: both players must start the requested move twice")
        require((clashes if pattern == "wave-clash" else contacts) >= 2,
                "Coverage missing: at least two simultaneous contacts or wave clashes")
        if policy["knockdown"]:
            require(knockdowns >= 2, "Coverage missing: at least two simultaneous double knockdowns")
        if pattern == "wave-clash":
            require(minimum_hp == [128, 128], "Wave-clash setup must not damage either fighter")
        row["status"] = "passed"
    except Exception as error:
        row["error"] = repr(error)
    finally:
        row.update(action_starts=starts, command_frames=commands,
                   simultaneous_contacts=contacts, simultaneous_double_knockdowns=knockdowns,
                   wave_clashes=clashes, contact_samples=samples,
                   double_kos=draws, draw_round_restarts=draw_resets, minimum_hp=minimum_hp,
                   frames=runner.total_frames, live_frames=runner.live_frames,
                   cadence_failures=runner.cadence_failures,
                   native_timing_failures=runner.native_timing_failures,
                   ambient_failures=runner.ambient_failures,
                   ppu_overflow_frames=runner.overflow_frames,
                   spc_fifo_failures=runner.spc_fifo_failures,
                   failure_states=runner.failure_states,
                   elapsed_seconds=round(time.monotonic() - began, 3))
        if row["status"] != "passed":
            row["last_callbacks"] = list(recent)
        host.close()
        row.update(core_boots=host.boot_count, core_unloads=host.unload_count,
                   max_active_emulators=1)
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fighter", type=int, choices=range(12))
    parser.add_argument("--stage", type=int, choices=range(3))
    parser.add_argument("--pattern", choices=PATTERNS)
    parser.add_argument("--live-frames", type=int, default=1200)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    require(args.live_frames >= 600, "At least 600 live frames are required")
    if args.pattern == "wave-clash" and args.fighter is not None:
        require(args.fighter in WAVE_FIGHTERS, "Wave clash requires a projectile or groundwave fighter")
    report_path = args.report.resolve()
    require(report_path.is_relative_to(ROOT / "build"), "Diagnostic reports must stay in ignored build/")
    manifest = json.loads((ROOT / "dist/manifest.json").read_bytes())
    identity, size = endurance.rom_identity()
    report = {
        "suite": "focused-simultaneous-contact-budget", "status": "running",
        "version": manifest["version"], "rom_sha256": identity, "rom_bytes": size,
        "core": endurance.core_identity(), "host_contract": process_contract(),
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "harness_sha256": {
            path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (Path(__file__).resolve(), ROOT / "tools/test_endurance.py",
                         ROOT / "tools/longrun_host.py", ROOT / "tools/make_crossup_review.py",
                         ROOT / "tools/test_champion.py")
        },
        "policy": "Mirror matches; 30px contacts, 61..64px rush setup, initial distance for wave clashes; wait for recovery/energy.",
        "coverage": "Each case requires both players to start the move twice and at least two same-frame contacts/clashes.",
        "scope": "Bounded diagnostic with strict native timing/bounds/SPC/PPU checks; not a release suite or live hour.",
        "cases": [],
    }
    patterns = (args.pattern,) if args.pattern else tuple(PATTERNS)
    fighters = (args.fighter,) if args.fighter is not None else range(12)
    stages = (args.stage,) if args.stage is not None else range(3)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        for pattern in patterns:
            for fighter in fighters:
                if pattern == "wave-clash" and fighter not in WAVE_FIGHTERS:
                    continue
                for stage in stages:
                    require(endurance.rom_identity()[0] == identity, "Candidate changed during stress")
                    row = run_case(fighter, stage, pattern, args.live_frames)
                    report["cases"].append(row)
                    report_path.write_bytes((json.dumps(report, indent=2) + "\n").encode())
                    print(json.dumps({key: row[key] for key in
                          ("fighter1", "stage", "pattern", "status", "live_frames",
                           "simultaneous_contacts", "simultaneous_double_knockdowns", "wave_clashes")}), flush=True)
                    require(row["status"] == "passed", f"Contact stress failed: {fighter}/{stage}/{pattern}: {row.get('error')}")
        require(endurance.rom_identity()[0] == identity, "Candidate changed before report")
        report["status"] = "passed"
    except Exception as error:
        report.update(status="failed", error=repr(error))
    finally:
        report_path.write_bytes((json.dumps(report, indent=2) + "\n").encode())
    print(json.dumps({"status": report["status"], "cases": len(report["cases"]),
                      "rom_sha256": identity, "report": str(report_path)}), flush=True)
    return int(report["status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
