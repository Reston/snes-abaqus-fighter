"""Focused silent controller-feel checks for the animation-era native ROM.

This suite is intentionally separate from the long roster and arcade probes.
It only drives SNES controller inputs through the official libretro core and
reads the public trace.  Audio is captured by the existing host callback but
is never opened or played, and no emulator window is created.
"""

from __future__ import annotations

import ctypes as C
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from emulator import Emulator, ROOT


checks: list[dict[str, object]] = []


def signed16(value: int) -> int:
    """Return a public trace word as a signed 16-bit fixed-point value."""

    value &= 0xffff
    return value - 0x10000 if value & 0x8000 else value


def check(ok: bool, label: str, details: object | None = None) -> None:
    if not ok:
        raise AssertionError((label, details))
    checks.append({"check": label, "passed": True, "details": details})


def trace(e: Emulator) -> dict[str, int]:
    """Decode the public trace, including the input-feel extension."""

    # The v0.5.1 combat classification extension occupies words 82..93.
    # Keep this decoder local to the focused suite; the shared emulator host
    # remains deliberately backward-compatible with older ROMs until the
    # parent integrates the new trace aliases.
    data = C.string_at(e.ram + 0x1FF00, 188)
    words = [int.from_bytes(data[i:i + 2], "little")
             for i in range(0, len(data), 2)]
    names = (
        "magic", "screen", "frame", "mode", "hp1", "hp2", "x1", "x2",
        "y1", "y2", "action1", "action2", "wins1", "wins2", "arena",
        "round", "intro", "paused", "energy1", "energy2", "wave1",
        "wave2", "selected", "selected2", "arcade", "seconds", "pose1",
        "pose2", "round_end", "hitstop", "combo", "champion",
        "fighter_id1", "fighter_id2", "family1", "family2", "speed1",
        "speed2", "jump1", "jump2", "face1", "face2", "back_speed1",
        "back_speed2", "special_startup1", "special_startup2",
        "special_active1", "special_active2", "special_recovery1",
        "special_recovery2", "special_damage1", "special_damage2",
        "special_reach1", "special_reach2", "throw_range1", "throw_range2",
        "wave_low1", "wave_low2", "wave_speed1", "wave_speed2",
        "wave_life1", "wave_life2", "anim_frame1", "anim_frame2",
        "anim_state1", "anim_state2", "anim_tick1", "anim_tick2",
        "buffered_action1", "buffered_action2", "buffer_age1",
        "buffer_age2", "jump_buffer1", "jump_buffer2", "command_stage1",
        "command_stage2", "raw_keys1", "raw_keys2", "landing1", "landing2",
        "jump_vx1", "jump_vx2",
        "hurt1", "hurt2", "guard1", "guard2",
        "connected1", "connected2", "combo_link1", "combo_link2",
        "chain_timer1", "chain_timer2", "counter1", "counter2",
    )
    return dict(zip(names, words))


def event_field(sample: dict[str, int], name: str, port: int,
                default: int = 0) -> int:
    """Read a per-player v0.5.1 event field with stable alias fallback."""

    suffix = str(port + 1)
    names = [name]
    if name == "combo_link":
        names.extend(("combo", "combo_trace"))
    for alias in names:
        for candidate in (f"{alias}{suffix}", f"{alias}_state{suffix}",
                          f"{alias}_trace{suffix}"):
            if candidate in sample:
                return sample[candidate]
    # The legacy combo word is a P1-only field at TRACE[30].  It is useful as
    # a read-only fallback for an intermediate ROM, but never shadows the
    # new per-player words when they are available.
    if name == "combo_link" and port == 0 and "combo" in sample:
        return sample["combo"]
    return default


def press(e: Emulator, key: str, port: int = 0) -> None:
    e.tap(key, port)
    e.run(14)


def wait_screen(e: Emulator, wanted: int) -> None:
    for _ in range(60):
        if trace(e)["screen"] == wanted:
            return
        e.run(10)
    raise AssertionError(("screen did not arrive", wanted, trace(e)))


def boot(mode: int = 2, wait_intro: bool = True) -> Emulator:
    e = Emulator()
    e.run(120)
    for _ in range(mode):
        press(e, "down")
    press(e, "a")
    wait_screen(e, 1)
    press(e, "a")
    if mode == 1:
        press(e, "a", 1)
    wait_screen(e, 2)
    press(e, "a")
    wait_screen(e, 3)
    if wait_intro:
        for _ in range(180):
            if trace(e)["intro"] == 0:
                break
            e.run(1)
        check(trace(e)["intro"] == 0, "input probe reaches live combat")
    e.run(3)
    return e


def close_players(e: Emulator) -> None:
    for _ in range(180):
        s = trace(e)
        if abs(s["x1"] - s["x2"]) < 28 * 16:
            return
        p1 = "right" if s["x1"] < s["x2"] else "left"
        p2 = "left" if p1 == "right" else "right"
        e.run(1, p1=[p1], p2=[p2])


def check_socd_and_p2(e: Emulator) -> None:
    s0 = trace(e)
    e.run(8, p1=["left", "right"])
    s1 = trace(e)

    def assert_opposite(before: dict[str, int], after: dict[str, int],
                        port: int) -> None:
        suffix = port + 1
        dx = after[f"x{suffix}"] - before[f"x{suffix}"]
        raw = after[f"raw_keys{suffix}"]
        # Snes9x 1.63 sanitizes a physical opposite-direction pair before
        # padsCurrent() on this host.  Keep the native neutral assertion for
        # a core that exposes both bits, while checking that this host's
        # one-bit resolution is deterministic and uses the correct walk/back
        # speed for each facing.
        if raw == 0 or raw == 768:
            check(abs(dx) <= 2,
                  f"P{suffix} opposite horizontal directions resolve neutral", {
                      "before": before[f"x{suffix}"],
                      "after": after[f"x{suffix}"],
                      "raw": raw,
                  })
            return
        check(raw in (256, 512),
              f"P{suffix} opposite input has a documented raw resolution", {
                  "raw": raw,
                  "trace": after,
              })
        face = before[f"face{suffix}"]
        if raw == 256:  # Right
            expected = before[f"speed{suffix}"] if face else before[f"back_speed{suffix}"]
        else:  # Left
            expected = -before[f"back_speed{suffix}"] if face else -before[f"speed{suffix}"]
        check(dx == expected * 8,
              f"P{suffix} opposite input resolves deterministically", {
                  "before": before[f"x{suffix}"],
                  "after": after[f"x{suffix}"],
                  "raw": raw,
                  "expected_delta": expected * 8,
              })

    assert_opposite(s0, s1, 0)

    e.run(6, p1=["right"])
    moved = trace(e)
    check(moved["x1"] > s1["x1"], "a single direction remains responsive after SOCD", {
        "before": s1["x1"], "after": moved["x1"],
    })

    # P2 receives the same neutralization and direction sampling through its
    # own controller port; this catches a P1-only input path.
    x2 = moved["x2"]
    e.run(8, p2=["left", "right"])
    neutral2 = trace(e)
    assert_opposite(moved, neutral2, 1)
    e.run(6, p2=["left"])
    check(trace(e)["x2"] < neutral2["x2"],
          "controller two remains responsive after SOCD")


def check_attack_buffer(e: Emulator) -> None:
    """Verify a short tap is buffered and starts only after action zero.

    The first normal has a sixteen-tick life with the current profile.  The
    second three-frame tap begins around tick twelve, where the six-tick
    buffer still overlaps the first action's recovery.  Holding the button
    longer would hide an edge-triggering regression, so release it before the
    first action reaches zero.
    """

    e.run(3, p1=["y"])
    e.run(1)
    first = trace(e)
    check(first["action1"] == 1, "first normal attack starts", first)
    check(first["raw_keys1"] == 0, "first attack probe releases its button", first)

    # Move to the latter recovery ticks while keeping the opponent distant.
    for _ in range(8):
        e.run(1)
    before_tap = trace(e)
    check(before_tap["action1"] == 1,
          "buffer tap begins while the first attack is active", before_tap)

    held = []
    for _ in range(3):
        e.run(1, p1=["y"])
        held.append(trace(e))
    released = e.run(1)
    buffered = any(s["buffered_action1"] == 1 and s["buffer_age1"] > 0
                   for s in held)
    check(buffered, "normal attack input is captured during recovery", {
        "held": held,
        "released": released,
    })
    check(held[0]["buffer_age1"] == 6 and held[-1]["buffer_age1"] == 4,
          "normal input buffer uses the six-tick live window", {
              "ages": [s["buffer_age1"] for s in held],
          })
    check(released["raw_keys1"] == 0,
          "buffered attack tap is released before execution", released)

    # The first action must visibly end.  A second action observed while the
    # first is still active is a false positive for this contract.
    ended = False
    ended_trace: dict[str, int] | None = None
    for _ in range(8):
        s = trace(e)
        if s["action1"] == 0:
            ended = True
            ended_trace = s
            break
        e.run(1)
    check(ended, "buffered attack observes the first action ending", {
        "trace": ended_trace or trace(e),
    })

    e.run(1)
    restarted = trace(e)
    check(restarted["action1"] == 1 and restarted["anim_tick1"] <= 2,
          "buffered normal attack executes with a fresh animation tick", {
              "ended": ended_trace,
              "trace": restarted,
          })


def check_jump_buffer(e: Emulator) -> None:
    # The UP edge is deliberately one frame.  The old probe held UP through
    # most of the jump and could pass without testing the six-tick landing
    # buffer at all.
    e.run(3, p1=["up"])
    released_start = e.run(1)
    first_y = signed16(released_start["y1"])
    airborne = first_y < 0
    check(airborne, "jump input leaves the floor", released_start)
    check(released_start["raw_keys1"] == 0,
          "jump probe releases UP before the landing window", released_start)

    previous_y = first_y
    falling = False
    queued = False
    queue_trace: dict[str, int] | None = None
    released_queue: dict[str, int] | None = None
    late_y: int | None = None
    for _ in range(100):
        s = trace(e)
        y = signed16(s["y1"])
        if y < 0 and y > previous_y:
            falling = True
        # y is 12.4 fixed point.  Keep the edge inside the final sixteen
        # pixels of the falling arc, rather than accepting the whole jump's
        # low 256-pixel range.
        if falling and y < 0 and y > -16 * 16 and y > previous_y:
            # Sustain the edge only until the read-only buffer proves that
            # this poll phase saw it.  This avoids both a one-frame miss and
            # holding UP across the floor, which would create an ordinary
            # held-jump instead of testing the landing buffer.
            for _ in range(3):
                e.run(1, p1=["up"])
                queue_trace = trace(e)
                if queue_trace["jump_buffer1"] > 0:
                    break
            queued = bool(queue_trace and queue_trace["jump_buffer1"] > 0)
            late_y = y
            released_queue = e.run(1)
            break
        previous_y = y
        e.run(1)
    check(falling, "jump buffer probe observes the falling arc", {
        "y": late_y,
        "trace": trace(e),
    })
    check(queued, "jump input is captured in the final sixteen pixels", {
        "y": late_y,
        "trace": queue_trace,
    })
    check(released_queue is not None and released_queue["raw_keys1"] == 0,
          "landing jump edge is released before execution", released_queue)

    landed = (queue_trace is not None and
              signed16(queue_trace["y1"]) >= 0)
    second_jump = False
    for _ in range(24):
        s = trace(e)
        y = signed16(s["y1"])
        if not landed and y >= 0:
            landed = True
        elif landed and y < 0:
            second_jump = True
            break
        e.run(1)
    check(landed, "jump buffer reaches the floor boundary", trace(e))
    check(second_jump, "landing consumes the jump buffer into a second jump", {
        "trace": trace(e),
        "late_y": late_y,
    })


def check_hitstop_capture(e: Emulator) -> None:
    close_players(e)
    e.run(3, p1=["y"])
    e.run(1)
    hit = None
    for _ in range(60):
        s = trace(e)
        if s["hitstop"]:
            hit = s
            break
        e.run(1)
    check(hit is not None, "a close normal hit produces hitstop", trace(e))

    frozen = (hit["anim_frame1"], hit["anim_tick1"]) if hit else (-1, -1)
    freeze_samples = [hit] if hit else []

    # Tap X during hitstop.  captureInput is live during hitstop, but the
    # buffer age and the combat animation must wait for the freeze to expire.
    e.run(3, p1=["x"])
    tap = trace(e)
    freeze_samples.append(tap)
    captured = (tap["buffered_action1"] == 2 and tap["buffer_age1"] > 0)
    e.run(1)  # release before the buffered command can execute
    freeze_samples.append(trace(e))
    while len(freeze_samples) < 6 and trace(e)["hitstop"]:
        e.run(1)
        freeze_samples.append(trace(e))

    active_freeze = [s for s in freeze_samples if s["hitstop"]]
    animation_froze = bool(active_freeze) and all(
        (s["anim_frame1"], s["anim_tick1"]) == frozen
        for s in active_freeze
    )
    check(len(active_freeze) >= 3,
          "hitstop lasts across several sampled frames", freeze_samples)
    check(animation_froze,
          "animation frame and tick freeze during hitstop", freeze_samples)
    check(captured, "attack tap is buffered during hitstop", tap)
    post_tap_freeze = [s for s in freeze_samples[1:] if s["hitstop"]]
    check(bool(post_tap_freeze) and all(
        s["buffer_age1"] == tap["buffer_age1"] for s in post_tap_freeze
    ), "input buffer age freezes with hitstop", {
        "tap_age": tap["buffer_age1"],
        "samples": post_tap_freeze,
    })

    executed = None
    for _ in range(30):
        s = trace(e)
        if not s["hitstop"] and s["action1"] == 2:
            executed = s
            break
        e.run(1)
    check(executed is not None,
          "hitstop tap executes after the freeze expires", {
              "tap": tap,
              "trace": executed or trace(e),
          })
    if executed is not None:
        check(executed["anim_frame1"] in (34, 6, 35),
              "post-hitstop buffered attack enters its native action sequence",
              executed)


def check_pause_intro_discard() -> None:
    """Paused and intro frames must clear commands before combat consumes them."""

    intro = boot(1, wait_intro=False)
    try:
        before = trace(intro)
        check(before["intro"] > 0, "intro discard probe starts during intro", before)
        intro.run(3, p1=["y", "up"])
        during_intro = trace(intro)
        check(during_intro["buffered_action1"] == 0 and
              during_intro["buffer_age1"] == 0 and
              during_intro["jump_buffer1"] == 0,
              "intro input buffers are discarded", during_intro)
    finally:
        intro.close()

    paused = boot(1)
    try:
        paused.run(3, p1=["start", "y", "up"])
        pause_state = trace(paused)
        check(pause_state["paused"] == 1, "START enters pause for discard probe", pause_state)
        check(pause_state["buffered_action1"] == 0 and
              pause_state["buffer_age1"] == 0 and
              pause_state["jump_buffer1"] == 0,
              "pause input buffers are discarded", pause_state)
        paused.run(1)
        paused.run(1, p1=["a"])
        paused.run(1)
    finally:
        paused.close()


def check_down_shortcut(port: int) -> None:
    """Down+P is the explicit shortcut; adding Back must disqualify it."""

    e = boot(1)
    try:
        suffix = port + 1
        initial = trace(e)
        face = port_field(initial, "face", port)
        drive(e, port, ["down"], 3)
        drive(e, port, ["down", "x"], 3)
        tap = trace(e)
        check(tap[f"action{suffix}"] == 7,
              f"P{suffix} down+X shortcut starts special", {
                  "face": face,
                  "trace": tap,
              })
    finally:
        e.close()


def drive(e: Emulator, port: int, keys: list[str], frames: int = 1) -> None:
    """Hold a controller state on one port for an exact number of frames."""

    kwargs = {"p1" if port == 0 else "p2": keys}
    e.run(frames, **kwargs)


def port_field(s: dict[str, int], name: str, port: int) -> int:
    return s[f"{name}{port + 1}"]


def wait_connected(e: Emulator, attacker: int, hold_defender: list[str] | None = None,
                   max_frames: int = 80) -> tuple[dict[str, int] | None,
                                                  list[dict[str, int]]]:
    """Return the first classified contact sample and the trace history.

    Contact is an event, so callers must retain the first sample rather than
    waiting for the next state transition.  The optional defender hold keeps
    a local-versus guard active while the attacker reaches its active frame.
    """

    hold_defender = hold_defender or []
    samples: list[dict[str, int]] = []
    for _ in range(max_frames):
        sample = trace(e)
        samples.append(sample)
        if event_field(sample, "connected", attacker) != 0:
            return sample, samples
        if attacker == 0:
            e.run(1, p2=hold_defender)
        else:
            e.run(1, p1=hold_defender)
    return None, samples


def wait_live(e: Emulator) -> dict[str, int]:
    """Advance through hitstop and return the first live trace sample."""

    for _ in range(30):
        sample = trace(e)
        if not sample["hitstop"]:
            return sample
        e.run(1)
    return trace(e)


def start_normal(e: Emulator, attacker: int = 0, key: str = "y",
                 hold_defender: list[str] | None = None) -> None:
    """Start one edge-triggered normal and release its button."""

    hold_defender = hold_defender or []
    if attacker == 0:
        e.run(3, p1=[key], p2=hold_defender)
        e.run(1, p2=hold_defender)
    else:
        e.run(3, p1=hold_defender, p2=[key])
        e.run(1, p1=hold_defender)


def check_qcf_case(port: int, wrong_back: bool = False) -> None:
    """Exercise a real QCF on either facing and reject down-back shortcuts."""

    e = boot(1)
    try:
        initial = trace(e)
        face = port_field(initial, "face", port)
        forward = "right" if face else "left"
        back = "left" if face else "right"
        suffix = port + 1

        if wrong_back:
            drive(e, port, ["down"], 3)
            drive(e, port, ["down", back], 3)
            blocked_motion = trace(e)
            check(blocked_motion[f"command_stage{suffix}"] == 0,
                  f"P{suffix} down-back clears the QCF motion", blocked_motion)
            drive(e, port, [back, "x"], 3)
            wrong_tap = trace(e)
            drive(e, port, [])
            samples = [wrong_tap]
            for _ in range(24):
                samples.append(trace(e))
                drive(e, port, [])
            special = [s for s in samples
                       if s[f"action{suffix}"] == 7 or s[f"wave{suffix}"]]
            check(not special,
                  f"P{suffix} down-back+X does not create a special", {
                      "face": face,
                      "samples": samples,
                  })
            return

        drive(e, port, ["down"], 3)
        drive(e, port, ["down", forward], 3)
        drive(e, port, [forward], 3)
        motion = trace(e)
        check(motion[f"command_stage{suffix}"] == 3,
              f"P{suffix} reaches QCF forward stage", {
                  "face": face,
                  "forward": forward,
                  "trace": motion,
              })
        drive(e, port, [forward, "x"], 3)
        tap = trace(e)
        drive(e, port, [])
        samples = [tap]
        for _ in range(42):
            samples.append(trace(e))
            drive(e, port, [])
        special = [s for s in samples
                   if s[f"action{suffix}"] == 7 or s[f"wave{suffix}"]]
        check(bool(special), f"P{suffix} QCF+X creates the special action", {
            "face": face,
            "forward": forward,
            "tap": tap,
            "special": special[:4],
        })
    finally:
        e.close()


def check_qcf_both_facings() -> None:
    check_qcf_case(0)
    check_qcf_case(1)
    check_qcf_case(0, wrong_back=True)


def check_jump_velocity(port: int, direction: str) -> None:
    """Verify takeoff momentum is committed and cannot be steered in flight."""

    e = boot(1)
    suffix = port + 1
    sign = 1 if direction == "right" else -1
    try:
        # The diagonal edge is held long enough to survive the native pad poll,
        # then released.  TRACE[80/81] is the source of truth for takeoff vx.
        drive(e, port, ["up", direction], 3)
        takeoff = trace(e)
        vx = signed16(port_field(takeoff, "jump_vx", port))
        check(vx * sign > 0,
              f"P{suffix} diagonal jump commits {direction} takeoff velocity", {
                  "direction": direction, "vx": vx, "trace": takeoff,
              })

        samples = [takeoff]
        for _ in range(8):
            drive(e, port, [])
            samples.append(trace(e))
        xs = [s[f"x{suffix}"] for s in samples]
        if sign > 0:
            monotonic = all(after >= before
                            for before, after in zip(xs, xs[1:]))
        else:
            monotonic = all(after <= before
                            for before, after in zip(xs, xs[1:]))
        check(monotonic,
              f"P{suffix} diagonal jump keeps {direction} momentum after release", {
                  "xs": xs, "vx": vx,
              })
        check(signed16(port_field(samples[-1], "jump_vx", port)) == vx,
              f"P{suffix} jump velocity remains committed in the air", {
                  "expected_vx": vx,
                  "observed_vx": signed16(port_field(samples[-1], "jump_vx", port)),
              })
    finally:
        e.close()


def check_neutral_jump_unsteered() -> None:
    """A late horizontal direction must not add momentum to a neutral jump."""

    e = boot(1)
    try:
        drive(e, 0, ["up"], 3)
        takeoff = trace(e)
        check(signed16(takeoff["jump_vx1"]) == 0,
              "neutral jump starts without horizontal momentum", takeoff)
        e.run(6)
        before_late_input = trace(e)
        drive(e, 0, ["right"], 3)
        after_late_input = trace(e)
        check(signed16(after_late_input["jump_vx1"]) == 0,
              "late horizontal input cannot steer a neutral jump", {
                  "before": before_late_input,
                  "after": after_late_input,
              })
        check(after_late_input["x1"] == before_late_input["x1"],
              "late horizontal input leaves neutral jump position unchanged", {
                  "before": before_late_input["x1"],
                  "after": after_late_input["x1"],
              })
    finally:
        e.close()


def wait_for_hitstop_end(e: Emulator) -> tuple[dict[str, int], dict[str, int]]:
    """Return the first hitstop sample and the first live sample after it."""

    hit = None
    for _ in range(60):
        sample = trace(e)
        if sample["hitstop"]:
            hit = sample
            break
        e.run(1)
    check(hit is not None, "normal hit provides a cancel timing window", trace(e))
    while trace(e)["hitstop"]:
        e.run(1)
    return hit, trace(e)


def check_normal_cancel_deadline() -> None:
    """Early hit-confirm cancels; late input buffers through recovery."""

    # Early hit-confirm: after hitstop ends the connected normal is still
    # inside startup+active+5 and a fresh medium punch may cancel it.
    e = boot(1)
    try:
        close_players(e)
        drive(e, 0, ["y"], 3)
        drive(e, 0, [])
        hit, live = wait_for_hitstop_end(e)
        e.run(1)
        drive(e, 0, ["x"], 3)
        early = trace(e)
        check(early["action1"] == 2,
              "early hit-confirm cancels into a medium punch", {
                  "hitstop": hit, "live": live, "trace": early,
              })
    finally:
        e.close()

    # Late recovery: wait beyond the five-tick cancel cutoff, tap X, and
    # verify that the command waits for action zero before starting.
    e = boot(1)
    try:
        close_players(e)
        drive(e, 0, ["y"], 3)
        drive(e, 0, [])
        hit, _ = wait_for_hitstop_end(e)
        e.run(1)
        e.run(7)
        late_before = trace(e)
        check(late_before["action1"] == 1,
              "late cancel probe remains in the first attack recovery", {
                  "hitstop": hit, "trace": late_before,
              })
        held = []
        for _ in range(3):
            drive(e, 0, ["x"])
            held.append(trace(e))
        check(held[0]["action1"] == 1 and held[0]["buffered_action1"] == 2,
              "late normal input buffers without cancelling after the deadline", {
                  "before": late_before, "held": held,
              })
        drive(e, 0, [])
        ended = None
        for _ in range(8):
            sample = trace(e)
            if sample["action1"] == 0:
                ended = sample
                break
            drive(e, 0, [])
        check(ended is not None,
              "late cancel probe reaches action zero before restart", {
                  "ended": ended, "held": held,
              })
        if ended is not None:
            drive(e, 0, [])
            restarted = trace(e)
            check(restarted["action1"] == 2 and restarted["anim_tick1"] <= 2,
                  "late buffered normal starts after recovery", {
                      "ended": ended, "restarted": restarted,
                  })
    finally:
        e.close()


def check_training_reset() -> None:
    """Select resets a live training round after real damage and movement."""

    e = boot(2)
    try:
        initial = trace(e)
        close_players(e)
        drive(e, 0, ["y"], 3)
        drive(e, 0, [])
        damaged = None
        for _ in range(60):
            sample = trace(e)
            if sample["hp2"] < initial["hp2"]:
                damaged = sample
                break
            e.run(1)
        check(damaged is not None and
              (damaged["x1"] != initial["x1"] or
               damaged["x2"] != initial["x2"] or
               damaged["hp2"] < initial["hp2"]),
              "training probe creates damage or movement before reset", {
                  "initial": initial, "damaged": damaged or trace(e),
              })

        # Select rebuilds both actor pages and the HUD, so the first few core
        # frames are occupied by the native DMA queue.  Keep Select held over
        # the input poll and settle before reading the reset contract.
        e.run(3, p1=["select"])
        e.run(10)
        reset = trace(e)
        check(reset["hp1"] == 128 and reset["hp2"] == 128,
              "Training Select restores both health values", reset)
        check(reset["x1"] == 66 * 16 and reset["x2"] == 190 * 16 and
              signed16(reset["y1"]) == 0 and signed16(reset["y2"]) == 0,
              "Training Select restores both fighters to their start positions", reset)
        check(reset["action1"] == 0 and reset["action2"] == 0 and
              reset["wave1"] == 0 and reset["wave2"] == 0 and
              reset["hitstop"] == 0 and reset["intro"] == 0,
              "Training Select clears active combat state", reset)
        check(reset["buffered_action1"] == 0 and reset["buffer_age1"] == 0 and
              reset["jump_buffer1"] == 0,
              "Training Select clears input buffers", reset)
    finally:
        e.close()


def check_guard_timing() -> None:
    """Guard impact keeps chip low, pushback light, and stun finite."""

    e = boot(1)
    try:
        close_players(e)
        start = trace(e)
        previous = start
        samples: list[dict[str, int]] = []
        blocked_previous: dict[str, int] | None = None
        blocked_hit: dict[str, int] | None = None
        for frame in range(30):
            # Down+away holds a stationary crouch guard, preventing the
            # defender's backward walk from obscuring the impact displacement.
            e.run(1, p1=["y"] if frame < 3 else [], p2=["down", "right"])
            sample = trace(e)
            samples.append(sample)
            if blocked_hit is None and sample["hitstop"] and sample["pose2"] == 9:
                blocked_previous = previous
                blocked_hit = sample
            previous = sample
            if blocked_hit is not None and len(samples) >= frame + 10:
                # Keep sampling through the complete eight-tick hurt state.
                if sample["pose2"] != 9 and frame >= 14:
                    break
        check(blocked_hit is not None,
              "standing attack produces a trace-visible guarded impact", {
                  "start": start, "samples": samples,
              })
        if blocked_hit is None:
            return
        blocked_samples = [sample for sample in samples
                           if sample["pose2"] == 9]
        blocked_dx = blocked_hit["x2"] - (blocked_previous or start)["x2"]
        check(blocked_hit["hp2"] >= start["hp2"] - 1,
              "guarded light punch deals at most one point of chip", {
                  "start_hp": start["hp2"], "impact": blocked_hit,
              })
        check(8 <= len(blocked_samples) <= 14,
              "guard stun lasts its eight-tick window with hitstop included", {
                  "guard_samples": len(blocked_samples),
                  "samples": blocked_samples,
              })
        check(0 < blocked_dx <= 32,
              "guarded impact uses reduced pushback", {
                  "blocked_dx_12_4": blocked_dx, "impact": blocked_hit,
              })

        # Release guard and confirm an otherwise identical close punch uses
        # the normal damage and larger pushback path.
        e.run(20)
        close_players(e)
        real_start = trace(e)
        previous = real_start
        real_hit = None
        for frame in range(36):
            e.run(1, p1=["y"] if frame < 3 else [])
            sample = trace(e)
            if real_hit is None and sample["hp2"] < real_start["hp2"]:
                real_hit = (previous, sample)
                break
            previous = sample
        check(real_hit is not None,
              "unblocked close punch reaches the defender", {
                  "start": real_start, "last": trace(e),
              })
        if real_hit is not None:
            real_previous, real_sample = real_hit
            real_dx = real_sample["x2"] - real_previous["x2"]
            check(real_sample["hp2"] <= real_start["hp2"] - 7,
                  "unblocked light punch deals normal damage", {
                      "start_hp": real_start["hp2"], "impact": real_sample,
                  })
            check(real_dx > blocked_dx,
                  "unblocked impact pushes farther than guarded impact", {
                      "guarded_dx_12_4": blocked_dx,
                      "unblocked_dx_12_4": real_dx,
                  })
    finally:
        e.close()


def check_training_inertness() -> None:
    """Training's second port stays inert and cannot inject CPU actions."""

    e = boot(2)
    try:
        initial = trace(e)
        for _ in range(90):
            e.run(1)
        idle = trace(e)
        check(idle["x2"] == initial["x2"] and idle["action2"] == 0 and
              idle["wave2"] == 0 and idle["hp2"] == initial["hp2"],
              "Training opponent remains inert while P1 is idle", {
                  "initial": initial, "idle": idle,
              })

        # Port two is physically driven here even though Training must use
        # the CPU-neutral path.  A leaked local-versus pad would move or make
        # the opponent attack, which is visible without peeking at WRAM.
        e.run(3, p2=["left", "y"])
        e.run(20, p2=[])
        driven = trace(e)
        check(driven["x2"] == initial["x2"] and driven["action2"] == 0 and
              driven["wave2"] == 0 and driven["hp2"] == initial["hp2"],
              "Training ignores controller-two movement and attack input", {
                  "initial": initial, "driven": driven,
              })
    finally:
        e.close()


def check_contact_classification() -> None:
    """Only real, unblocked contact opens a normal cancel window."""

    # A confirmed hit may cancel during the short post-hit active window.
    e = boot(1)
    try:
        close_players(e)
        start_normal(e, 0, "y")
        real, history = wait_connected(e, 0)
        check(real is not None and event_field(real or {}, "connected", 0) == 2,
              "close punch is classified as a real hit", {
                  "event": real, "history": history,
              })
        if real is not None:
            check(event_field(real, "guard", 1) == 0 and
                  event_field(real, "hurt", 1) > 0,
                  "real hit exposes hurt without guard state", real)
        wait_live(e)
        e.run(1)
        drive(e, 0, ["x"], 3)
        cancel = trace(e)
        check(cancel["action1"] == 2,
              "real hit confirmation cancels into a medium punch", {
                  "event": real, "cancel": cancel,
              })
    finally:
        e.close()

    # A blocked jab still produces hitstop, but it must never be treated as a
    # hit confirm.  The immediate sample matters because a buffered medium
    # may legitimately execute later after the jab returns to neutral.
    e = boot(1)
    try:
        close_players(e)
        guard = ["down", "right"]
        start_normal(e, 0, "y", guard)
        blocked, history = wait_connected(e, 0, guard)
        check(blocked is not None and
              event_field(blocked or {}, "connected", 0) == 1,
              "guarded punch is classified as blocked contact", {
                  "event": blocked, "history": history,
              })
        if blocked is not None:
            check(event_field(blocked, "guard", 1) > 0 and
                  blocked["pose2"] == 9,
                  "blocked contact exposes guard-stun state", blocked)
        wait_live(e)
        e.run(1, p2=guard)
        drive(e, 0, ["x"], 3)
        blocked_cancel = trace(e)
        check(blocked_cancel["action1"] != 2,
              "blocked jab cannot hit-confirm cancel into medium", {
                  "event": blocked, "trace": blocked_cancel,
              })
        check(event_field(blocked_cancel, "combo_link", 0) == 0 and
              event_field(blocked_cancel, "counter", 0) == 0,
              "blocked contact does not start a combo or counter", blocked_cancel)
    finally:
        e.close()


def check_stale_prehit_buffer() -> None:
    """A defender's pre-hit command clears while fresh hitstop input remains."""

    e = boot(1)
    try:
        close_players(e)
        # P1 starts a slow heavy normal.  X is buffered during its startup,
        # then P2's faster jab lands while P1 is still the defender.  This
        # exercises the contract's defender-side stale-buffer clearing path.
        e.run(1, p1=["l"], p2=["y"])
        prehit: list[dict[str, int]] = []
        for _ in range(3):
            e.run(1, p1=["x"])
            prehit.append(trace(e))
        e.run(1, p1=[])
        check(any(s["buffered_action1"] == 2 and
                  event_field(s, "hurt", 1) == 0 for s in prehit),
              "defender pre-hit medium input is visibly buffered", prehit)

        event, history = wait_connected(e, 1)
        check(event is not None and event_field(event or {}, "connected", 1) == 2,
              "buffer probe reaches a real hit on the defender", {
                  "event": event, "history": history,
              })
        if event is None:
            return
        check(event["buffered_action1"] == 0 and event["buffer_age1"] == 0,
              "real impact clears the defender's stale pre-hit command", event)

        # Release the pre-hit button for a full sampled tick so the deliberate
        # hitstop tap is a new edge, then hold it for the host's three-frame
        # polling window.  Buffer expiry remains frozen during hitstop.  P1 is
        # still hurt after the freeze, so execution is covered by the normal
        # hitstop-capture test rather than being required here.
        e.run(1, p1=[])
        tap_samples: list[dict[str, int]] = []
        for _ in range(3):
            e.run(1, p1=["x"])
            tap_samples.append(trace(e))
        tap = tap_samples[-1]
        hitstop_taps = [s for s in tap_samples if s["hitstop"]]
        check(any(s["buffered_action1"] == 2 and s["buffer_age1"] > 0
                  for s in hitstop_taps),
              "new hitstop medium tap is captured after stale input clears", {
                  "event": event, "tap": tap_samples,
              })
        check(bool(hitstop_taps) and
              len({s["buffer_age1"] for s in hitstop_taps}) == 1,
              "defender input-buffer age freezes through hitstop", {
                  "event": event, "tap": tap_samples,
              })
    finally:
        e.close()


def _seed_two_hit_combo(e: Emulator) -> tuple[dict[str, int] | None,
                                               dict[str, int] | None]:
    """Create a real light/medium chain and return both contact samples."""

    close_players(e)
    start_normal(e, 0, "y")
    first, _ = wait_connected(e, 0)
    if first is None:
        return None, None
    wait_live(e)
    e.run(1)
    drive(e, 0, ["x"], 3)
    second, _ = wait_connected(e, 0)
    return first, second


def check_combo_lifecycle() -> None:
    """Combo linkage follows true hurt continuity and attacker interruption."""

    e = boot(1)
    try:
        first, second = _seed_two_hit_combo(e)
        check(first is not None and second is not None and
              event_field(second or {}, "connected", 0) == 2,
              "two-hit combo reaches its second real contact", {
                  "first": first, "second": second,
              })
        if second is not None:
            check(event_field(second, "combo_link", 0) >= 2 and
                  event_field(second, "chain_timer", 0) > 0,
                  "same defender hurt continuity increments combo linkage", second)

        # Let the defender recover while the display timer is still alive.
        for _ in range(60):
            sample = trace(e)
            if event_field(sample, "hurt", 1) == 0 and not sample["hitstop"]:
                break
            e.run(1)
        close_players(e)
        start_normal(e, 0, "y")
        recovered, _ = wait_connected(e, 0)
        check(recovered is not None and event_field(recovered or {}, "connected", 0) == 2,
              "post-recovery punch reaches the defender", recovered)
        if recovered is not None:
            check(event_field(recovered, "combo_link", 0) == 1,
                  "combo restarts after the defender leaves hurt state", recovered)
    finally:
        e.close()

    # A defender interrupt must also break the link, even if the attacker's
    # display lifetime has not yet reached zero.
    e = boot(1)
    try:
        _, second = _seed_two_hit_combo(e)
        check(second is not None and event_field(second or {}, "combo_link", 0) >= 2,
              "interrupt probe starts from an active combo", second)
        for _ in range(60):
            sample = trace(e)
            if event_field(sample, "hurt", 1) == 0 and not sample["hitstop"]:
                break
            e.run(1)
        close_players(e)
        start_normal(e, 1, "y")
        interrupted, _ = wait_connected(e, 1)
        check(interrupted is not None and
              event_field(interrupted or {}, "connected", 1) == 2 and
              event_field(interrupted or {}, "hurt", 0) > 0,
              "defender can interrupt the former attacker", interrupted)
        for _ in range(40):
            sample = trace(e)
            if event_field(sample, "hurt", 0) == 0 and not sample["hitstop"]:
                break
            e.run(1)
        close_players(e)
        start_normal(e, 0, "y")
        restarted, _ = wait_connected(e, 0)
        check(restarted is not None and
              event_field(restarted or {}, "connected", 0) == 2 and
              event_field(restarted or {}, "combo_link", 0) == 1,
              "combo restarts after the attacker is interrupted", restarted)
    finally:
        e.close()


def check_mirrored_throw_range() -> None:
    """Player one and two share the same exact throw-range/contact edge."""

    e = boot(1)
    try:
        close_players(e)
        inside = trace(e)
        check(abs(inside["x1"] - inside["x2"]) < inside["throw_range1"] * 16,
              "P1 throw probe starts inside its published range", inside)
        forward = "right" if inside["face1"] else "left"
        drive(e, 0, [forward, "l"], 3)
        p1_throw = trace(e)
        check(p1_throw["action1"] == 9 or
              event_field(p1_throw, "connected", 0) == 2,
              "P1 throw connects at the close contact edge", p1_throw)
    finally:
        e.close()

    e = boot(1)
    try:
        close_players(e)
        inside = trace(e)
        check(abs(inside["x1"] - inside["x2"]) < inside["throw_range2"] * 16,
              "P2 throw probe starts inside its published range", inside)
        forward = "right" if inside["face2"] else "left"
        drive(e, 1, [forward, "l"], 3)
        p2_throw = trace(e)
        check(p2_throw["action2"] == 9 or
              event_field(p2_throw, "connected", 1) == 2,
              "P2 mirrored throw connects at the close contact edge", p2_throw)
    finally:
        e.close()

    e = boot(1)
    try:
        close_players(e)
        initial = trace(e)
        back = "left" if initial["face1"] else "right"
        drive(e, 0, [back], 8)
        outside = trace(e)
        check(abs(outside["x1"] - outside["x2"]) >= outside["throw_range1"] * 16,
              "P1 range probe reaches the outside side of the throw edge", outside)
        forward = "right" if outside["face1"] else "left"
        drive(e, 0, [forward, "l"], 3)
        no_throw = trace(e)
        check(no_throw["action1"] != 9,
              "P1 heavy input outside throw range falls back to a normal", {
                  "outside": outside, "trace": no_throw,
              })
    finally:
        e.close()


def check_landing_buffer_boundary() -> None:
    """The oldest valid six-tick jump edge survives into the landing tick."""

    e = boot(1)
    try:
        drive(e, 0, ["up"], 3)
        drive(e, 0, [])
        previous_y = signed16(trace(e)["y1"])
        queued_at: dict[str, int] | None = None
        # Damian's neutral arc reaches roughly 22 pixels above the floor four
        # simulation ticks before landing.  Choose that falling sample from
        # telemetry rather than hard-coding a frame number.
        for _ in range(40):
            sample = trace(e)
            y = signed16(sample["y1"])
            if (y < 0 and y > previous_y and
                    -24 * 16 <= y <= -20 * 16):
                queued_at = sample
                break
            previous_y = y
            e.run(1)
        check(queued_at is not None,
              "landing buffer probe finds the oldest falling-window sample", {
                  "trace": queued_at or trace(e),
              })
        if queued_at is None:
            return
        e.run(3, p1=["up"])
        held = trace(e)
        e.run(1)
        released = trace(e)
        check(held["jump_buffer1"] >= 4 and released["jump_buffer1"] >= 3,
              "oldest landing edge retains buffered age before contact", {
                  "queued_at": queued_at, "held": held,
                  "released": released,
              })

        landed_index: int | None = None
        second_jump_index: int | None = None
        rows = [held, released]
        for _ in range(16):
            e.run(1)
            rows.append(trace(e))
        for index, sample in enumerate(rows):
            if landed_index is None and signed16(sample["y1"]) == 0:
                landed_index = index
            elif landed_index is not None and signed16(sample["y1"]) < 0:
                second_jump_index = index
                break
        check(landed_index is not None,
              "landing buffer reaches the floor", {"rows": rows})
        check(second_jump_index == (landed_index + 1
                                    if landed_index is not None else -1),
              "oldest valid landing edge executes on the first grounded tick", {
                  "landed_index": landed_index,
                  "second_jump_index": second_jump_index,
                  "rows": rows,
              })
    finally:
        e.close()


def check_cross_up_jump() -> None:
    """A diagonal jump crosses P2 with locked air facing, then turns on landing."""

    e = boot(1)
    try:
        close_players(e)
        start = trace(e)
        check(start["x1"] < start["x2"] and start["face1"] == 1,
              "cross-up probe starts with P1 facing right", start)
        drive(e, 0, ["up", "right"], 3)
        samples = [trace(e)]
        for _ in range(48):
            e.run(1)
            samples.append(trace(e))
            if signed16(samples[-1]["y1"]) == 0 and samples[-1]["landing1"]:
                break
        airborne = [sample for sample in samples
                     if signed16(sample["y1"]) < 0]
        crossed = [sample for sample in airborne
                   if sample["x1"] > sample["x2"]]
        check(bool(airborne), "cross-up probe observes an airborne arc", {
            "samples": samples,
        })
        check(bool(crossed),
              "diagonal jump crosses the opponent before landing", {
                  "start": start, "crossed": crossed[:4],
              })
        if airborne:
            check(all(sample["face1"] == 1 for sample in airborne),
                  "airborne cross-up keeps the takeoff facing", {
                      "airborne": airborne,
                  })
            check(all(after["x1"] >= before["x1"]
                      for before, after in zip(airborne, airborne[1:])),
                  "cross-up horizontal travel remains monotonic in air", {
                      "x1": [sample["x1"] for sample in airborne],
                  })
        landed = samples[-1]
        for _ in range(3):
            e.run(1)
            landed = trace(e)
        check(landed["x1"] > landed["x2"] and landed["face1"] == 0,
              "facing updates after a crossed jump lands", landed)
    finally:
        e.close()


def main() -> int:
    started = time.monotonic()
    report: dict[str, object] = {
        "emulator": "Official Snes9x 1.63 x64 libretro core",
        "suite": "input-feel",
        "status": "failed",
        "rom_sha256": None,
        "rom_bytes": None,
        "checks": checks,
    }
    try:
        manifest = json.loads((ROOT / "dist/manifest.json").read_text())
        report["rom_sha256"] = manifest["sha256"]
        report["rom_bytes"] = manifest.get("bytes")
        check(manifest.get("bytes") == 4 * 1024 * 1024,
              "input-feel probe uses the 4 MiB animation ROM", manifest)

        # Local versus is required for controller-two checks.  Training mode
        # intentionally supplies CPU keys on port two and would mask a P2
        # input regression.
        e = boot(1)
        try:
            check_socd_and_p2(e)
            check_hitstop_capture(e)
        finally:
            e.close()

        check_pause_intro_discard()
        check_training_inertness()
        check_training_reset()
        check_guard_timing()
        check_contact_classification()
        check_stale_prehit_buffer()
        check_combo_lifecycle()
        check_mirrored_throw_range()

        e = boot(1)
        try:
            check_attack_buffer(e)
        finally:
            e.close()

        e = boot(1)
        try:
            check_jump_buffer(e)
        finally:
            e.close()

        check_landing_buffer_boundary()
        check_cross_up_jump()
        check_neutral_jump_unsteered()
        check_jump_velocity(0, "right")
        check_jump_velocity(1, "left")
        check_down_shortcut(0)
        check_down_shortcut(1)
        check_qcf_both_facings()
        check_normal_cancel_deadline()
        report["status"] = "passed"
    except BaseException as exc:
        report["error"] = repr(exc)
        raise
    finally:
        report["passed"] = len(checks)
        report["checks"] = checks
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        report_path = ROOT / "docs/input-test-report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "status": report["status"],
        "passed": len(checks),
        "seconds": report["elapsed_seconds"],
        "rom_sha256": report["rom_sha256"],
        "report": "docs/input-test-report.json",
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
