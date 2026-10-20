"""Controller-only ordered local-versus matchup sweep.

This is a bounded balance and engine-stability probe.  It boots every ordered
12-by-12 local-versus pairing through the native menus, distributes the work
across all three stages, and drives two deterministic controller policies:
grounded range/normal/special pressure and a jump/guard/throw mix.  Outcomes
are read only from the public WRAM trace.  The host never writes emulated
memory, creates a save state, opens a frontend window, or sends audio to a
device.

The sweep records evidence for follow-up balance work; it does not establish
human balance or full combat correctness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emulator import Emulator, ROOT  # noqa: E402


ROM_PATH = ROOT / "dist" / "abaqus-after-hours.sfc"
MANIFEST_PATH = ROOT / "dist" / "manifest.json"
REPORT_PATH = ROOT / "docs" / "matchup-test-report.json"
ROM_BYTES = 4 * 1024 * 1024
FIGHTERS = 12
STAGES = 3
LIVE_FRAMES = 600
DOWN_SOFTLOCK_FRAMES = 240
STALL_WARNING_FRAMES = 180
POLICIES = ("ground_combo_special", "jump_guard_throw_mix")


class MatchupFailure(RuntimeError):
    """A hard engine or controller-path failure with a minimal repro."""

    def __init__(self, kind: str, message: str, frame: int,
                 state: dict[str, int], p1: list[str], p2: list[str]) -> None:
        super().__init__(message)
        self.kind = kind
        self.frame = frame
        self.state = state
        self.p1 = p1
        self.p2 = p2


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().lower()


def signed16(value: int) -> int:
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def press(e: Emulator, key: str, port: int = 0) -> None:
    e.tap(key, port)
    e.run(20)


def wait_screen(e: Emulator, wanted: int, limit: int = 600) -> None:
    for _ in range(limit // 10):
        if e.state()["screen"] == wanted:
            e.run(10)
            return
        e.run(10)
    raise AssertionError(f"screen {wanted} did not arrive: {e.state()}")


def boot_match(fighter1: int, fighter2: int, stage: int) -> Emulator:
    """Enter local VS with only real controller callbacks."""

    e = Emulator()
    try:
        e.run(120)
        require(e.state()["screen"] == 0, "cold boot did not reach title")
        # Title item 1 is local versus.
        press(e, "down")
        press(e, "a")
        wait_screen(e, 1)
        for _ in range(fighter1):
            press(e, "right")
        press(e, "a")
        # Local VS initializes P2's cursor at roster slot 1.
        for _ in range((fighter2 - 1) % FIGHTERS):
            press(e, "right", 1)
        press(e, "a", 1)
        wait_screen(e, 2)
        for _ in range(stage):
            press(e, "down")
        press(e, "a")
        wait_screen(e, 3)
        for _ in range(160):
            if e.state()["intro"] == 0:
                break
            e.run(1)
        require(e.state()["intro"] == 0, "match intro did not complete")
        e.run(3)
        return e
    except Exception:
        e.close()
        raise


def x_position(state: dict[str, int], side: int) -> int:
    return signed16(state[f"x{side + 1}"])


def y_position(state: dict[str, int], side: int) -> int:
    return signed16(state[f"y{side + 1}"])


def direction_toward(state: dict[str, int], side: int) -> str:
    dx = x_position(state, 1) - x_position(state, 0)
    if side == 0:
        return "right" if dx > 0 else "left"
    return "left" if dx > 0 else "right"


def forward_key(state: dict[str, int], side: int) -> str:
    return "right" if state[f"face{side + 1}"] else "left"


def back_key(state: dict[str, int], side: int) -> str:
    return "left" if state[f"face{side + 1}"] else "right"


def grounded(state: dict[str, int], side: int) -> bool:
    return (state[f"down_state{side + 1}"] == 0 and
            y_position(state, side) == 0 and
            state[f"hitstop"] == 0 and
            state[f"round_end"] == 0 and
            state[f"paused"] == 0)


def range_close_keys(state: dict[str, int], side: int,
                     threshold: int = 24 * 16) -> list[str] | None:
    distance = abs(x_position(state, 1) - x_position(state, 0))
    if distance > threshold:
        return [direction_toward(state, side)]
    return None


def ground_combo_special(state: dict[str, int], side: int) -> list[str]:
    """Close distance, then alternate normals, throws, and specials."""

    if not grounded(state, side):
        return []
    closing = range_close_keys(state, side)
    if closing is not None:
        return closing
    phase = (state["frame"] + side * 19) % 120
    forward = forward_key(state, side)
    if phase < 4:
        return ["down", "x"]
    if 30 <= phase < 34:
        return ["y"]
    if 62 <= phase < 66:
        return [forward, "l"]
    if 92 <= phase < 96:
        return ["x"]
    return []


def jump_guard_throw_mix(state: dict[str, int], side: int) -> list[str]:
    """Mix jumping, directional guard, throws, normals, and specials."""

    if state[f"round_end"] or state[f"paused"] or state[f"hitstop"]:
        return []
    closing = range_close_keys(state, side, threshold=28 * 16)
    if closing is not None:
        return closing
    phase = (state["frame"] + side * 37) % 144
    forward = forward_key(state, side)
    back = back_key(state, side)
    if state[f"down_state{side + 1}"]:
        return []
    if phase < 5 and y_position(state, side) == 0:
        return ["up"]
    if 8 <= phase < 14 and y_position(state, side) < 0:
        return ["y"]
    if 38 <= phase < 58 and y_position(state, side) == 0:
        return [back, "down"]
    if 70 <= phase < 75 and y_position(state, side) == 0:
        return [forward, "l"]
    if 98 <= phase < 103 and y_position(state, side) == 0:
        return ["down", "x"]
    if 122 <= phase < 126 and y_position(state, side) == 0:
        return ["y"]
    return []


POLICY_FUNCTIONS: dict[str, Callable[[dict[str, int], int], list[str]]] = {
    "ground_combo_special": ground_combo_special,
    "jump_guard_throw_mix": jump_guard_throw_mix,
}


def input_categories(keys: list[str], state: dict[str, int], side: int) -> list[str]:
    """Classify the controller sample for the matchup report."""

    categories: list[str] = []
    if not keys:
        return ["idle"]
    if "left" in keys or "right" in keys:
        categories.append("move")
    if "up" in keys:
        categories.append("jump")
    if "l" in keys:
        categories.append("throw")
    if "down" in keys and "x" in keys:
        categories.append("special")
    if (back_key(state, side) in keys and
            not any(key in keys for key in ("y", "x", "a", "b", "l"))):
        categories.append("guard")
    if any(key in keys for key in ("y", "x", "a", "b")) and "special" not in categories:
        categories.append("normal")
    return categories or ["other"]


def update_down(down: dict[str, object], side: int, value: int,
               frame: int) -> None:
    key = str(side + 1)
    active = int(value) != 0
    if active and down["start"][key] is None:
        down["start"][key] = frame
    if not active and down["start"][key] is not None:
        start = int(down["start"][key])
        down["durations"][key].append(frame - start)
        down["start"][key] = None


def finalize_down(down: dict[str, object], frame: int) -> None:
    for side in (0, 1):
        key = str(side + 1)
        if down["start"][key] is not None:
            down["durations"][key].append(frame - int(down["start"][key]))
            down["start"][key] = None


def matchup_once(fighter1: int, fighter2: int, stage: int,
                 policy_name: str, frames: int = LIVE_FRAMES) -> dict[str, object]:
    policy = POLICY_FUNCTIONS[policy_name]
    e = boot_match(fighter1, fighter2, stage)
    try:
        initial = e.state()
        previous = initial
        previous_frame = initial["frame"]
        previous_host_frame = e.frames
        state_digest = hashlib.sha256()
        action_counts = [Counter(), Counter()]
        input_counts = [Counter(), Counter()]
        family_values = [set(), set()]
        special_events = [0, 0]
        wave_events = [0, 0]
        damage_dealt = [0, 0]
        damage_events = [0, 0]
        hp_min = [initial["hp1"], initial["hp2"]]
        x_min = [x_position(initial, 0), x_position(initial, 1)]
        x_max = list(x_min)
        y_min = [y_position(initial, 0), y_position(initial, 1)]
        y_max = list(y_min)
        distance_min = abs(x_min[1] - x_min[0])
        distance_max = distance_min
        down: dict[str, object] = {
            "start": {"1": None, "2": None},
            "durations": {"1": [], "2": []},
        }
        deltas: list[int] = []
        host_deltas: list[int] = []
        round_outcomes: list[dict[str, object]] = []
        wins_seen = [initial["wins1"], initial["wins2"]]
        idle_run = 0
        max_idle = 0
        warnings: list[str] = []
        last_meaningful_frame = initial["frame"]

        for offset in range(frames):
            current_frame = previous["frame"]
            p1 = policy(previous, 0)
            p2 = policy(previous, 1)
            for side, keys in enumerate((p1, p2)):
                input_counts[side].update(input_categories(keys, previous, side))
            current = e.run(1, p1=p1, p2=p2)
            frame = current["frame"]
            delta = (frame - previous_frame) & 0xFFFF
            deltas.append(delta)
            host_delta = e.frames - previous_host_frame
            host_deltas.append(host_delta)
            if host_delta != 1:
                raise MatchupFailure(
                    "host_frame_cadence",
                    f"host callback frame delta was {host_delta}, expected 1",
                    offset, current, p1, p2)
            if current["screen"] != 3:
                raise MatchupFailure(
                    "screen_exit", "live local-versus screen exited unexpectedly",
                    offset, current, p1, p2)
            if delta != 1:
                raise MatchupFailure(
                    "trace_frame_cadence",
                    f"trace frame delta was {delta}, expected 1 including freezes",
                    offset, current, p1, p2)
            for side in (0, 1):
                suffix = str(side + 1)
                action = int(current[f"action{suffix}"])
                action_counts[side][str(action)] += 1
                family_values[side].add(int(current[f"family{suffix}"]))
                hp_key = f"hp{suffix}"
                hp_drop = previous[hp_key] - current[hp_key]
                if hp_drop > 0:
                    damage_dealt[1 - side] += hp_drop
                    damage_events[1 - side] += 1
                hp_min[side] = min(hp_min[side], current[hp_key])
                x = x_position(current, side)
                y = y_position(current, side)
                x_min[side] = min(x_min[side], x)
                x_max[side] = max(x_max[side], x)
                y_min[side] = min(y_min[side], y)
                y_max[side] = max(y_max[side], y)
                update_down(down, side, current[f"down_state{suffix}"], offset + 1)
                if current[f"down_state{suffix}"] not in range(6):
                    raise MatchupFailure(
                        "down_state", "public down-state enum escaped 0..5",
                        offset, current, p1, p2)
                if current[f"wave{suffix}"] and not previous[f"wave{suffix}"]:
                    wave_events[side] += 1
                if action == 7 and previous[f"action{suffix}"] != 7:
                    special_events[side] += 1
            distance = abs(x_position(current, 1) - x_position(current, 0))
            distance_min = min(distance_min, distance)
            distance_max = max(distance_max, distance)
            round_changed = [current[f"wins{side + 1}"] > wins_seen[side]
                             for side in (0, 1)]
            if any(round_changed):
                winner = 0 if round_changed[0] and not round_changed[1] else 1
                round_outcomes.append({
                    "frame": frame,
                    "winner_side": winner,
                    "wins": [current["wins1"], current["wins2"]],
                    "hp": [current["hp1"], current["hp2"]],
                })
                wins_seen = [current["wins1"], current["wins2"]]
            meaningful = (
                current["hp1"] != previous["hp1"] or
                current["hp2"] != previous["hp2"] or
                current["action1"] or current["action2"] or
                current["wave1"] or current["wave2"] or
                current["down_state1"] or current["down_state2"] or
                current["x1"] != previous["x1"] or
                current["x2"] != previous["x2"] or
                current["y1"] != previous["y1"] or
                current["y2"] != previous["y2"] or
                current["round_end"]
            )
            if meaningful:
                last_meaningful_frame = frame
                idle_run = 0
            else:
                idle_run += 1
                max_idle = max(max_idle, idle_run)
            for side in (0, 1):
                key = str(side + 1)
                if down["start"][key] is not None:
                    duration = offset + 1 - int(down["start"][key])
                    if duration > DOWN_SOFTLOCK_FRAMES:
                        raise MatchupFailure(
                            "down_softlock",
                            f"P{key} remained down for {duration} frames",
                            offset, current, p1, p2)
            # Hash the public trace and the exact controls at every native
            # callback frame so replay evidence is independent of screenshots.
            state_digest.update(json.dumps({
                "frame": frame,
                "p1": p1,
                "p2": p2,
                "trace": current,
            }, sort_keys=True, separators=(",", ":")).encode("utf-8"))
            previous = current
            previous_frame = frame
            previous_host_frame = e.frames

        finalize_down(down, frames)
        if max_idle >= STALL_WARNING_FRAMES:
            warnings.append(f"idle/stall window reached {max_idle} frames")
        if not round_outcomes:
            warnings.append("no round outcome in bounded live window")
        max_down = [max((down["durations"][str(side + 1)] or [0]))
                    for side in (0, 1)]
        return {
            "fighter1": fighter1,
            "fighter2": fighter2,
            "stage": stage,
            "policy": policy_name,
            "frames": frames,
            "cadence": {
                "observed_frames": len(deltas),
                "trace_delta_min": min(deltas),
                "trace_delta_max": max(deltas),
                "trace_non_one_deltas": sum(delta != 1 for delta in deltas),
                "host_delta_min": min(host_deltas),
                "host_delta_max": max(host_deltas),
                "host_non_one_deltas": sum(delta != 1 for delta in host_deltas),
                "passed": True,
            },
            "damage": {
                "dealt": damage_dealt,
                "events": damage_events,
                "minimum_hp": hp_min,
                "total": sum(damage_dealt),
            },
            "actions": {
                "counts": [dict(sorted(counter.items(), key=lambda item: int(item[0])))
                           for counter in action_counts],
                "issued_input_mix": [dict(sorted(counter.items()))
                                     for counter in input_counts],
                "input_mix_semantics": (
                    "controller keys issued by the deterministic policy; not realized "
                    "native actions"
                ),
                "special_family_values": [sorted(values) for values in family_values],
                "special_events": special_events,
                "wave_events": wave_events,
            },
            "round_outcomes": round_outcomes,
            "position": {
                "x_min": x_min,
                "x_max": x_max,
                "y_min": y_min,
                "y_max": y_max,
                "distance_min": distance_min,
                "distance_max": distance_max,
            },
            "down_durations": {
                "episodes": down["durations"],
                "max": max_down,
                "total": [sum(down["durations"][str(side + 1)])
                          for side in (0, 1)],
            },
            "stalls": {
                "max_idle_frames": max_idle,
                "last_meaningful_frame": last_meaningful_frame,
                "warnings": warnings,
            },
            "trace_sha256": state_digest.hexdigest(),
            "passed": True,
        }
    finally:
        e.close()


def verify_inputs() -> dict[str, object]:
    require(ROM_PATH.exists(), f"missing ROM: {ROM_PATH}")
    require(MANIFEST_PATH.exists(), f"missing ROM manifest: {MANIFEST_PATH}")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    actual = sha256(ROM_PATH)
    expected = str(manifest.get("sha256", "")).lower()
    require(ROM_PATH.stat().st_size == ROM_BYTES,
            f"ROM size is not {ROM_BYTES}: {ROM_PATH.stat().st_size}")
    require(manifest.get("bytes") == ROM_BYTES,
            f"manifest ROM size is not {ROM_BYTES}: {manifest.get('bytes')!r}")
    require(len(expected) == 64 and actual == expected,
            f"ROM hash does not match manifest: actual={actual} manifest={expected}")
    return {
        "sha256": actual,
        "manifest_sha256": expected,
        "bytes": ROM_BYTES,
    }


def stage_for(fighter1: int, fighter2: int, policy_index: int) -> int:
    return (fighter1 + fighter2 + policy_index) % STAGES


def selected_replays() -> list[tuple[int, int, int]]:
    return [(0, 1, 0), (1, 0, 0), (4, 6, 1), (6, 4, 1)]


def balance_summary(results: list[dict[str, object]]) -> dict[str, object]:
    """Report bounded statistical outliers without calling them balance facts."""

    by_policy: dict[str, list[dict[str, object]]] = {
        policy: [result for result in results if result["policy"] == policy]
        for policy in POLICIES
    }
    summary: dict[str, object] = {
        "method": "Tukey-style 1.5 IQR bounds over bounded total damage",
        "human_balance_claim": False,
        "policies": {},
        "warnings": [],
    }
    for policy, policy_results in by_policy.items():
        if not policy_results:
            continue
        values = sorted(int(result["damage"]["total"]) for result in policy_results)
        q1 = values[len(values) // 4]
        q3 = values[(len(values) * 3) // 4]
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outliers = [
            {
                "fighter1": result["fighter1"],
                "fighter2": result["fighter2"],
                "stage": result["stage"],
                "damage_total": result["damage"]["total"],
                "reason": "total damage outside bounded IQR range",
            }
            for result in policy_results
            if result["damage"]["total"] < lower or result["damage"]["total"] > upper
        ]
        no_outcome = sum(not result["round_outcomes"] for result in policy_results)
        summary["policies"][policy] = {
            "matchups": len(policy_results),
            "damage_total": {
                "min": values[0],
                "q1": q1,
                "median": values[len(values) // 2],
                "q3": q3,
                "max": values[-1],
                "iqr": iqr,
                "lower_bound": lower,
                "upper_bound": upper,
            },
            "round_outcome_matches": len(policy_results) - no_outcome,
            "no_outcome_matches": no_outcome,
            "no_outcome_rate": no_outcome / len(policy_results),
            "outliers": outliers,
        }
        summary["warnings"].extend({
            "policy": policy,
            **outlier,
        } for outlier in outliers)
        if no_outcome / len(policy_results) > 0.5:
            summary["warnings"].append({
                "policy": policy,
                "reason": "more than half of bounded windows had no round outcome",
                "matches": no_outcome,
            })
    return summary


def run_sweep(limit: int | None, frames: int, smoke: bool) -> dict[str, object]:
    pairs = [(fighter1, fighter2)
             for fighter1 in range(FIGHTERS)
             for fighter2 in range(FIGHTERS)]
    if limit is not None:
        pairs = pairs[:limit]
    if smoke:
        pairs = pairs[:2]
    total = len(pairs) * len(POLICIES)
    report: dict[str, object] = {
        "status": "failed",
        "scope": "controller-only ordered 12x12 local-VS matchup sweep",
        "rom": None,
        "matchup_count_requested": total,
        "frames_per_matchup": frames,
        "ordered_pair_count": len(pairs),
        "full_ordered_matrix": len(pairs) == FIGHTERS * FIGHTERS,
        "policies": list(POLICIES),
        "cadence_contract": (
            "host callback and read-only TRACE frame deltas must both be exactly 1 "
            "for every measured local-VS frame, including hitstop, round-end, and pause"
        ),
        "stages": {str(stage): 0 for stage in range(STAGES)},
        "results": [],
        "warnings": [],
        "replays": [],
        "host_contract": {
            "controller_only": True,
            "emulated_memory_writes": 0,
            "savestate_calls": 0,
            "frontend_window_created": False,
            "audio_device_opened": False,
            "trace_read_only": True,
        },
    }
    report["rom"] = verify_inputs()
    completed = 0
    active_case: dict[str, object] | None = None
    empty_case = {
        "fighter1": None,
        "fighter2": None,
        "stage": None,
        "policy": None,
        "policy_index": None,
        "core_load_index": None,
        "replay": None,
        "replay_run": None,
    }
    try:
        for fighter1, fighter2 in pairs:
            for policy_index, policy_name in enumerate(POLICIES):
                stage = stage_for(fighter1, fighter2, policy_index)
                active_case = {
                    "fighter1": fighter1,
                    "fighter2": fighter2,
                    "stage": stage,
                    "policy": policy_name,
                    "policy_index": policy_index,
                    "core_load_index": completed + 1,
                    "replay": False,
                }
                result = matchup_once(fighter1, fighter2, stage, policy_name, frames)
                report["results"].append(result)
                report["stages"][str(stage)] += 1
                report["warnings"].extend({
                    "fighter1": fighter1,
                    "fighter2": fighter2,
                    "stage": stage,
                    "policy": policy_name,
                    "message": warning,
                } for warning in result["stalls"]["warnings"])
                completed += 1
        for fighter1, fighter2, policy_index in selected_replays():
            if (fighter1, fighter2) not in pairs:
                continue
            policy_name = POLICIES[policy_index]
            stage = stage_for(fighter1, fighter2, policy_index)
            active_case = {
                "fighter1": fighter1,
                "fighter2": fighter2,
                "stage": stage,
                "policy": policy_name,
                "policy_index": policy_index,
                "core_load_index": completed + 1,
                "replay": True,
                "replay_run": 1,
            }
            first = matchup_once(fighter1, fighter2, stage, policy_name, frames)
            active_case["core_load_index"] = completed + 2
            active_case["replay_run"] = 2
            second = matchup_once(fighter1, fighter2, stage, policy_name, frames)
            same_hash = first["trace_sha256"] == second["trace_sha256"]
            if not same_hash:
                raise MatchupFailure(
                    "replay_mismatch", "deterministic replay trace hash changed",
                    0, {}, [], [])
            report["replays"].append({
                "fighter1": fighter1,
                "fighter2": fighter2,
                "stage": stage,
                "policy": policy_name,
                "trace_sha256": first["trace_sha256"],
                "same_trace_sha256": same_hash,
                "passed": True,
            })
        report["sidesymmetry"] = {
            "ordered_pairs": len(pairs),
            "mirrored_ordered_pairs": sum(
                (fighter2, fighter1) in pairs
                for fighter1, fighter2 in pairs if fighter1 != fighter2),
            "self_matchups": sum(fighter1 == fighter2 for fighter1, fighter2 in pairs),
            "passed": True,
        }
        report["balance_summary"] = balance_summary(report["results"])
        report["completed_matchups"] = completed
        report["status"] = "passed"
    except MatchupFailure as failure:
        report["completed_matchups"] = completed
        report["first_failure"] = {
            "kind": failure.kind,
            "message": str(failure),
            "frame_offset": failure.frame,
            "state": failure.state,
            "p1": failure.p1,
            "p2": failure.p2,
            **empty_case,
            **(active_case or {}),
        }
        report["status"] = "failed"
    except Exception as exc:
        report["completed_matchups"] = completed
        report["first_failure"] = {
            "kind": type(exc).__name__,
            "message": str(exc),
            **empty_case,
            **(active_case or {}),
        }
        report["status"] = "failed"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None,
                        help="limit ordered pairs for a bounded rehearsal")
    parser.add_argument("--frames", type=int, default=LIVE_FRAMES,
                        help=f"live frames per matchup (default {LIVE_FRAMES})")
    parser.add_argument("--smoke", action="store_true",
                        help="run two ordered pairs instead of the full matrix")
    args = parser.parse_args()
    require(args.frames > 0, "--frames must be positive")
    report = run_sweep(args.limit, args.frames, args.smoke)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "completed_matchups": report.get("completed_matchups", 0),
        "report": str(REPORT_PATH.relative_to(ROOT)).replace("\\", "/"),
        "first_failure": report.get("first_failure"),
    }))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
