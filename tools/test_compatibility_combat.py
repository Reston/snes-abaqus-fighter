"""Bounded independent-engine combat compatibility gate.

This suite complements the native matchup sweep with the pinned
bsnes2014 Accuracy Libretro core. It drives the release menus and fighters
through controller callbacks only, reads the public trace, and keeps all
video/PCM data in memory except for two optional smoke captures under the
ignored compatibility cache. It does not write emulated memory, create
savestates, open a frontend, or play audio.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_compatibility as compatibility  # noqa: E402
import test_matchups as matchups  # noqa: E402


ROOT = compatibility.ROOT
REPORT_PATH = ROOT / "docs" / "compatibility-combat-test-report.json"
CAPTURE_ROOT = ROOT / ".tools" / "compat" / "combat-captures"
FIGHTERS = 12
STAGES = 3
LIVE_FRAMES = 600
SMOKE_FRAMES = 120
PULSE_FRAMES = 3
POLICIES = tuple(matchups.POLICIES)
Probe = compatibility.Probe


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def signed16(value: int) -> int:
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def press(core: Probe, key: str, port: int = 0) -> None:
    """Use a sustained controller pulse for the menu's edge sampler."""

    if port == 0:
        core.run(PULSE_FRAMES, p1=[key])
    else:
        core.run(PULSE_FRAMES, p2=[key])
    core.run(PULSE_FRAMES)
    core.run(20)


def wait_screen(core: Probe, wanted: int, limit: int = 600) -> None:
    for _ in range(limit // 10):
        if core.state()["screen"] == wanted:
            core.run(10)
            return
        core.run(10)
    raise AssertionError(f"screen {wanted} did not arrive: {core.state()}")


def boot_match(core: Probe, fighter1: int, fighter2: int,
               stage: int) -> dict[str, int]:
    """Enter local VS with real controller callbacks and verify selections."""

    core.run(120)
    title = core.state()
    require(title["magic"] == 0xAABA and title["screen"] == 0,
            f"cold boot did not reach title: {title}")
    press(core, "down")
    press(core, "a")
    wait_screen(core, 1)
    for _ in range(fighter1):
        press(core, "right")
    press(core, "a")
    # Local VS initializes P2's cursor at roster slot 1.
    for _ in range((fighter2 - 1) % FIGHTERS):
        press(core, "right", 1)
    press(core, "a", 1)
    wait_screen(core, 2)
    for _ in range(stage):
        press(core, "down")
    press(core, "a")
    wait_screen(core, 3)
    for _ in range(180):
        if core.state()["intro"] == 0:
            break
        core.run(1)
    settled = core.state()
    require(settled["screen"] == 3 and settled["intro"] == 0,
            f"match intro did not complete: {settled}")
    require(settled["selected"] == fighter1 and
            settled["selected2"] == fighter2,
            f"roster selection mismatch: wanted {fighter1}/{fighter2}, got {settled}")
    require(settled["fighter_id1"] == fighter1 and
            settled["fighter_id2"] == fighter2,
            f"loaded fighter mismatch: wanted {fighter1}/{fighter2}, got {settled}")
    require(settled["arena"] == stage,
            f"loaded stage mismatch: wanted {stage}, got {settled['arena']}")
    core.run(3)
    return core.state()


def state_position(state: dict[str, int], side: int) -> tuple[int, int]:
    suffix = str(side + 1)
    return signed16(state[f"x{suffix}"]), signed16(state[f"y{suffix}"])


def check_fighter_trace(state: dict[str, int], side: int,
                        expected_id: int) -> None:
    """Check public fighter telemetry without peeking at source tables."""

    suffix = str(side + 1)
    fighter_id = int(state[f"fighter_id{suffix}"])
    require(fighter_id == expected_id,
            f"P{suffix} fighter id changed {fighter_id} != {expected_id}")
    family = int(state[f"family{suffix}"])
    require(family in range(4), f"P{suffix} special family escaped 0..3: {family}")
    require(int(state[f"face{suffix}"]) in (0, 1),
            f"P{suffix} facing escaped 0/1: {state[f'face{suffix}']}")
    require(int(state[f"hp{suffix}"]) in range(129),
            f"P{suffix} HP escaped 0..128: {state[f'hp{suffix}']}")
    require(int(state[f"energy{suffix}"]) in range(97),
            f"P{suffix} energy escaped 0..96: {state[f'energy{suffix}']}")
    require(int(state[f"action{suffix}"]) in range(10),
            f"P{suffix} action escaped 0..9: {state[f'action{suffix}']}")
    require(int(state[f"pose{suffix}"]) in range(16),
            f"P{suffix} legacy pose escaped 0..15: {state[f'pose{suffix}']}")
    require(int(state[f"anim_frame{suffix}"]) in range(64),
            f"P{suffix} animation frame escaped 0..63: {state[f'anim_frame{suffix}']}")
    require(int(state[f"anim_state{suffix}"]) in range(15),
            f"P{suffix} animation state escaped 0..14: {state[f'anim_state{suffix}']}")
    require(int(state[f"buffered_action{suffix}"]) in range(10),
            f"P{suffix} buffered action escaped 0..9: {state[f'buffered_action{suffix}']}")
    require(int(state[f"buffer_age{suffix}"]) in range(256),
            f"P{suffix} buffer age escaped u8: {state[f'buffer_age{suffix}']}")
    require(int(state[f"jump_buffer{suffix}"]) in range(256),
            f"P{suffix} jump buffer escaped u8: {state[f'jump_buffer{suffix}']}")
    require(int(state[f"landing{suffix}"]) in range(4),
            f"P{suffix} landing escaped 0..3: {state[f'landing{suffix}']}")
    require(int(state[f"raw_keys{suffix}"]) in range(65536),
            f"P{suffix} raw keys escaped u16: {state[f'raw_keys{suffix}']}")
    require(int(state[f"hurt{suffix}"]) in range(256),
            f"P{suffix} hurt escaped u8: {state[f'hurt{suffix}']}")
    require(int(state[f"guard{suffix}"]) in (0, 1),
            f"P{suffix} guard escaped 0/1: {state[f'guard{suffix}']}")
    require(int(state[f"connected{suffix}"]) in (0, 1, 2),
            f"P{suffix} connected escaped 0/1/2: {state[f'connected{suffix}']}")
    require(int(state[f"combo_link{suffix}"]) in range(256),
            f"P{suffix} combo escaped u8: {state[f'combo_link{suffix}']}")
    require(int(state[f"chain_timer{suffix}"]) in range(256),
            f"P{suffix} combo timer escaped u8: {state[f'chain_timer{suffix}']}")
    require(int(state[f"counter{suffix}"]) in (0, 1),
            f"P{suffix} counter escaped 0/1: {state[f'counter{suffix}']}")
    down = int(state[f"down_state{suffix}"])
    require(down in range(6), f"P{suffix} down state escaped 0..5: {down}")
    require(int(state[f"down_tick{suffix}"]) in range(256),
            f"P{suffix} down tick escaped u8: {state[f'down_tick{suffix}']}")
    require(int(state[f"invuln{suffix}"]) in range(256),
            f"P{suffix} invulnerability escaped u8: {state[f'invuln{suffix}']}")
    require(int(state[f"pending_throw_damage{suffix}"]) in range(256),
            f"P{suffix} pending throw damage escaped u8: {state[f'pending_throw_damage{suffix}']}")
    require(int(state[f"throw_owner{suffix}"]) in (0, 1, 255),
            f"P{suffix} throw owner escaped 0/1/255: {state[f'throw_owner{suffix}']}")
    require(int(state[f"throw_victim{suffix}"]) in (0, 1, 255),
            f"P{suffix} throw victim escaped 0/1/255: {state[f'throw_victim{suffix}']}")
    require(int(state[f"air_action{suffix}"]) in (0, 1),
            f"P{suffix} air action escaped 0/1: {state[f'air_action{suffix}']}")
    require(int(state[f"wake_action{suffix}"]) in range(10),
            f"P{suffix} wake action escaped 0..9: {state[f'wake_action{suffix}']}")
    require(int(state[f"wake_age{suffix}"]) in range(256),
            f"P{suffix} wake age escaped u8: {state[f'wake_age{suffix}']}")
    require(int(state[f"wake_jump{suffix}"]) in range(256),
            f"P{suffix} wake jump escaped u8: {state[f'wake_jump{suffix}']}")
    x, y = state_position(state, side)
    require(0 <= x <= 4096, f"P{suffix} X left native stage bounds: {x}")
    require(-4096 <= y <= 512, f"P{suffix} Y left native stage bounds: {y}")
    jump_vx = signed16(int(state[f"jump_vx{suffix}"]))
    require(-4096 <= jump_vx <= 4096,
            f"P{suffix} jump horizontal velocity escaped bounds: {jump_vx}")


def check_global_trace(state: dict[str, int], fighter1: int,
                       fighter2: int, stage: int) -> None:
    require(state["magic"] == 0xAABA, f"trace magic changed: {state['magic']}")
    require(state["screen"] == 3, f"fight left live screen: {state['screen']}")
    require(state["arena"] == stage, f"fight arena changed: {state['arena']} != {stage}")
    require(int(state["round_end"]) in range(181),
            f"round-end timer escaped 0..180: {state['round_end']}")
    require(int(state["hitstop"]) in range(6),
            f"hitstop escaped 0..5: {state['hitstop']}")
    require(int(state["seconds"]) in range(100),
            f"round timer escaped 0..99: {state['seconds']}")
    require(int(state["wins1"]) in range(3) and int(state["wins2"]) in range(3),
            f"round wins escaped 0..2: {state['wins1']}/{state['wins2']}")
    require(int(state["wave1"]) in (0, 1) and int(state["wave2"]) in (0, 1),
            f"wave active escaped 0/1: {state['wave1']}/{state['wave2']}")
    require(int(state["wave_low1"]) in (0, 1) and int(state["wave_low2"]) in (0, 1),
            f"wave low escaped 0/1: {state['wave_low1']}/{state['wave_low2']}")
    require(int(state["wave_speed1"]) in range(256) and
            int(state["wave_speed2"]) in range(256),
            f"wave speed escaped u8: {state['wave_speed1']}/{state['wave_speed2']}")
    require(int(state["wave_life1"]) in range(256) and
            int(state["wave_life2"]) in range(256),
            f"wave life escaped u8: {state['wave_life1']}/{state['wave_life2']}")
    require((int(state["ppu_stat"]) & 0xC0) == 0,
            f"PPU OAM range/time overflow bits set: {state['ppu_stat']:#x}")
    check_fighter_trace(state, 0, fighter1)
    check_fighter_trace(state, 1, fighter2)


def close_down_episode(episodes: list[list[int]], active: list[int],
                       side: int) -> None:
    if active[side]:
        episodes[side].append(active[side])
        active[side] = 0


def run_case(fighter1: int, fighter2: int, stage: int, policy_name: str,
             frames: int, capture: bool = False) -> dict[str, object]:
    policy: Callable[[dict[str, int], int], list[str]] = matchups.POLICY_FUNCTIONS[policy_name]
    core = Probe()
    started = time.perf_counter()
    try:
        initial = boot_match(core, fighter1, fighter2, stage)
        check_global_trace(initial, fighter1, fighter2, stage)
        first_signature = core.frame_signature()
        capture_paths: list[str] = []
        if capture:
            CAPTURE_ROOT.mkdir(parents=True, exist_ok=True)
            path = CAPTURE_ROOT / f"f{fighter1:02d}-f{fighter2:02d}-s{stage}-{policy_name}.png"
            require(core.frame_image is not None, "smoke capture has no native frame")
            core.frame_image.save(path)
            capture_paths.append(str(path.relative_to(ROOT)).replace("\\", "/"))

        previous = initial
        previous_callbacks = core.video_callbacks
        action_counts = [Counter(), Counter()]
        animation_counts = [Counter(), Counter()]
        input_counts = [Counter(), Counter()]
        family_values = [set(), set()]
        damage_dealt = [0, 0]
        damage_events = [0, 0]
        hp_min = [int(initial["hp1"]), int(initial["hp2"])]
        x_min = [state_position(initial, 0)[0], state_position(initial, 1)[0]]
        x_max = list(x_min)
        y_min = [state_position(initial, 0)[1], state_position(initial, 1)[1]]
        y_max = list(y_min)
        down_episodes: list[list[int]] = [[], []]
        down_active = [0, 0]
        down_seen = [False, False]
        wake_seen = [False, False]
        air_seen = [False, False]
        throw_seen = [False, False]
        landing_seen = [False, False]
        special_seen = [False, False]
        deltas: list[int] = []
        callback_deltas: list[int] = []
        last_frame = int(initial["frame"])
        pulse_keys: list[list[str]] = [[], []]
        pulse_left = 0

        for offset in range(frames):
            if pulse_left == 0:
                pulse_keys = [list(policy(previous, 0)), list(policy(previous, 1))]
                pulse_left = PULSE_FRAMES
            pulse_left -= 1
            for side, keys in enumerate(pulse_keys):
                input_counts[side].update(matchups.input_categories(keys, previous, side))

            current = core.run(1, p1=pulse_keys[0], p2=pulse_keys[1])
            callback_delta = core.video_callbacks - previous_callbacks
            callback_deltas.append(callback_delta)
            require(callback_delta == 1,
                    f"video callback cadence was {callback_delta} at offset {offset}")
            frame_delta = (int(current["frame"]) - last_frame) & 0xFFFF
            deltas.append(frame_delta)
            require(frame_delta == 1,
                    f"trace frame cadence was {frame_delta} at offset {offset}")
            check_global_trace(current, fighter1, fighter2, stage)

            for side in (0, 1):
                suffix = str(side + 1)
                action = int(current[f"action{suffix}"])
                anim_frame = int(current[f"anim_frame{suffix}"])
                action_counts[side][str(action)] += 1
                animation_counts[side][str(anim_frame)] += 1
                family_values[side].add(int(current[f"family{suffix}"]))
                if action == 7:
                    special_seen[side] = True
                if int(current[f"air_action{suffix}"]):
                    air_seen[side] = True
                if int(current[f"throw_owner{suffix}"]) != 255 or int(current[f"throw_victim{suffix}"]) != 255:
                    throw_seen[side] = True
                if int(current[f"landing{suffix}"]):
                    landing_seen[side] = True
                hp_key = f"hp{suffix}"
                hp_drop = int(previous[hp_key]) - int(current[hp_key])
                if hp_drop > 0:
                    damage_dealt[1 - side] += hp_drop
                    damage_events[1 - side] += 1
                hp_min[side] = min(hp_min[side], int(current[hp_key]))
                x, y = state_position(current, side)
                x_min[side] = min(x_min[side], x)
                x_max[side] = max(x_max[side], x)
                y_min[side] = min(y_min[side], y)
                y_max[side] = max(y_max[side], y)
                down_state = int(current[f"down_state{suffix}"])
                if down_state:
                    down_seen[side] = True
                    down_active[side] += 1
                    require(down_active[side] <= 240,
                            f"P{suffix} down sequence soft-locked at {down_active[side]} frames")
                else:
                    close_down_episode(down_episodes, down_active, side)
                if down_state == 5 or int(current[f"wake_action{suffix}"]) or int(current[f"wake_age{suffix}"]):
                    wake_seen[side] = True

            previous = current
            previous_callbacks = core.video_callbacks
            last_frame = int(current["frame"])

        for side in (0, 1):
            close_down_episode(down_episodes, down_active, side)
        require(all(delta == 1 for delta in deltas),
                f"non-one trace deltas: {sorted(set(deltas))}")
        require(all(delta == 1 for delta in callback_deltas),
                f"non-one video callback deltas: {sorted(set(callback_deltas))}")
        non_idle_actions = [
            any(int(action) > 0 for action in counter)
            for counter in action_counts
        ]
        require(any(non_idle_actions),
                f"policy realized no actions for either fighter: {action_counts}")
        require(len(animation_counts[0]) >= 2 and len(animation_counts[1]) >= 2,
                f"policy realized no animation change: {animation_counts}")
        require(core.audio_energy > 0 and 0 < core.audio_peak < 32767,
                f"PCM callback unhealthy: samples={core.audio_samples}, energy={core.audio_energy}, peak={core.audio_peak}")
        return {
            "fighter1": fighter1,
            "fighter2": fighter2,
            "stage": stage,
            "policy": policy_name,
            "frames": frames,
            "elapsed_seconds": time.perf_counter() - started,
            "initial": {
                "fighter_id1": initial["fighter_id1"],
                "fighter_id2": initial["fighter_id2"],
                "arena": initial["arena"],
                "frame_signature": first_signature,
            },
            "cadence": {
                "trace_frames": len(deltas),
                "trace_delta_min": min(deltas),
                "trace_delta_max": max(deltas),
                "trace_non_one_deltas": sum(delta != 1 for delta in deltas),
                "video_callbacks": len(callback_deltas),
                "video_delta_min": min(callback_deltas),
                "video_delta_max": max(callback_deltas),
                "video_non_one_deltas": sum(delta != 1 for delta in callback_deltas),
                "passed": True,
            },
            "actions": {
                "counts": [dict(sorted(counter.items(), key=lambda item: int(item[0]))) for counter in action_counts],
                "animation_frame_counts": [dict(sorted(counter.items(), key=lambda item: int(item[0]))) for counter in animation_counts],
                "input_mix": [dict(sorted(counter.items())) for counter in input_counts],
                "special_family_values": [sorted(values) for values in family_values],
                "special_seen": special_seen,
                "air_action_seen": air_seen,
            },
            "damage": {
                "dealt": damage_dealt,
                "events": damage_events,
                "minimum_hp": hp_min,
                "total": sum(damage_dealt),
            },
            "position": {"x_min": x_min, "x_max": x_max, "y_min": y_min, "y_max": y_max},
            "down_wake": {
                "down_seen": down_seen,
                "wake_seen": wake_seen,
                "episodes": down_episodes,
                "max_episode": [max(episodes or [0]) for episodes in down_episodes],
            },
            "throws": {"throw_seen": throw_seen, "landing_seen": landing_seen},
            "audio": {"samples": core.audio_samples, "energy": core.audio_energy, "peak": core.audio_peak},
            "captures": capture_paths,
            "passed": True,
        }
    finally:
        core.close()


def case_matrix() -> list[tuple[int, int, int, str]]:
    neighbors = [(fighter, (fighter + 1) % FIGHTERS) for fighter in range(FIGHTERS)]
    pairs = neighbors + [(fighter2, fighter1) for fighter1, fighter2 in neighbors]
    cases: list[tuple[int, int, int, str]] = []
    for pair_index, (fighter1, fighter2) in enumerate(pairs):
        for policy_index, policy_name in enumerate(POLICIES):
            case_index = pair_index * len(POLICIES) + policy_index
            cases.append((fighter1, fighter2, case_index % STAGES, policy_name))
    return cases


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="run two short silent smoke cases")
    parser.add_argument("--limit", type=int, default=None, help="run only the first N matrix cases")
    parser.add_argument("--frames", type=int, default=LIVE_FRAMES, help=f"live frames per case (default {LIVE_FRAMES})")
    parser.add_argument("--no-capture", action="store_true", help="disable the two ignored smoke captures")
    args = parser.parse_args()
    require(args.frames > 0, "--frames must be positive")
    if args.limit is not None:
        require(args.limit > 0, "--limit must be positive")
    return args


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    report: dict[str, object] = {
        "status": "failed",
        "scope": "independent bsnes2014 Accuracy bounded combat compatibility",
        "pinned_core": True,
        "rom": {"sha256": None, "bytes": compatibility.ROM_BYTES},
        "matrix": {
            "fighters": FIGHTERS,
            "stages": STAGES,
            "policies": list(POLICIES),
            "pulse_frames": PULSE_FRAMES,
            "full_case_count": len(case_matrix()),
            "requested_frames_per_case": SMOKE_FRAMES if args.smoke else args.frames,
        },
        "cases": [],
        "errors": [],
        "limitations": [
            "This is a bounded controller-only independent-core gate, not the full 144-pair matchup matrix.",
            "It does not prove every native frame or every VRAM/OAM row; the roster/presentation suites own those checks.",
            "Damage and down/wake events are recorded when realized by deterministic policies; no event is forced through memory writes.",
        ],
        "host_contract": {
            "emulated_memory_writes": 0,
            "savestate_calls": 0,
            "audio_device_opened": False,
            "frontend_window_created": False,
            "pcm_callback_capture_only": True,
        },
    }
    try:
        pinned = compatibility.verify_manifest_and_pinned_core()
        report["rom"]["sha256"] = pinned["rom_sha256"]
        report["core"] = {
            "archive_sha256": pinned["archive_sha256"],
            "dll_sha256": pinned["dll_sha256"],
        }
        cases = case_matrix()
        if args.smoke:
            cases = cases[:2]
            frames = SMOKE_FRAMES
        else:
            frames = args.frames
            if args.limit is not None:
                cases = cases[:args.limit]
        report["matrix"]["selected_case_count"] = len(cases)
        report["matrix"]["selected_frames"] = len(cases) * frames
        signatures: list[str] = []
        for index, (fighter1, fighter2, stage, policy_name) in enumerate(cases):
            result = run_case(
                fighter1, fighter2, stage, policy_name, frames,
                capture=(args.smoke and not args.no_capture),
            )
            report["cases"].append(result)
            signatures.append(str(result["initial"]["frame_signature"]["sha256_rgb"]))
            print(json.dumps({
                "case": index + 1,
                "total": len(cases),
                "fighter1": fighter1,
                "fighter2": fighter2,
                "stage": stage,
                "policy": policy_name,
                "frames": frames,
                "elapsed_seconds": result["elapsed_seconds"],
                "status": "passed",
            }))
        if args.smoke:
            require(len(set(signatures)) == len(signatures),
                    "smoke native fighter/stage output signatures were not distinct")
            report["smoke_output"] = {
                "distinct_frame_signatures": len(set(signatures)),
                "captures": [capture for result in report["cases"] for capture in result["captures"]],
                "passed": True,
            }
        report["status"] = "passed"
    except Exception as exc:
        report["errors"].append(repr(exc))
        report["error_type"] = type(exc).__name__
        print(json.dumps({"status": "failed", "error": repr(exc)}))
    finally:
        report["elapsed_seconds"] = time.perf_counter() - started
        REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({
            "status": report["status"],
            "report": str(REPORT_PATH.relative_to(ROOT)).replace("\\", "/"),
            "cases_completed": len(report["cases"]),
            "elapsed_seconds": report["elapsed_seconds"],
            "error": report["errors"][0] if report["errors"] else None,
        }))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
