"""Focused silent controller-feel checks for the animation-era native ROM.

This suite is intentionally separate from the long roster and arcade probes.
It only drives SNES controller inputs through the official libretro core and
reads the public trace.  Audio is captured by the existing host callback but
is never opened or played, and no emulator window is created.
"""

from __future__ import annotations

import ctypes as C
from functools import lru_cache
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from emulator import Emulator, ROOT
from contact_geometry import generate as generate_contact_geometry, world, overlap


checks: list[dict[str, object]] = []
BG2_MAP_BYTE = 0x5800 * 2
HEALTH_TILE = 129
ENERGY_TILE = 138
P1_STATUS_ATTR = 0x2000
P2_STATUS_ATTR = 0x6000
MENU_CORE_OPTIONS = {"snes9x_up_down_allowed": "enabled"}
DELIBERATE_PACING=tuple(map(int,json.loads((ROOT/'dist/manifest.json').read_bytes())['version'].split('.'))) >= (0,25,0)
PLAY_FLOW=tuple(map(int,json.loads((ROOT/'dist/manifest.json').read_bytes())['version'].split('.'))) >= (0,26,0)
CLASSIC_MENUS=tuple(map(int,json.loads((ROOT/'dist/manifest.json').read_bytes())['version'].split('.'))) >= (0,27,0)
_screen_address: int | None = None


def native_screen(e: Emulator) -> int:
    """Read the real scene byte while a loader has not yet published TRACE."""
    global _screen_address
    if _screen_address is None:
        symbols = (ROOT / "dist/abaqus-after-hours.sym").read_text(encoding="utf-8")
        match = re.search(r"^([0-9a-fA-F]{8}) screen$", symbols, re.MULTILINE)
        if match is None:
            raise AssertionError("missing native screen symbol")
        _screen_address = int(match.group(1), 16) - 0x7e0000
    return C.string_at(e.ram + _screen_address, 1)[0]


def signed16(value: int) -> int:
    """Return a public trace word as a signed 16-bit fixed-point value."""

    value &= 0xffff
    return value - 0x10000 if value & 0x8000 else value


@lru_cache(maxsize=1)
def contact_poses():
    """Independently regenerate final-pixel rectangles for fixture brackets.

    These only establish physical overlap; controller-created contact,
    direction, timing, damage and guard assertions remain mandatory.
    """

    return generate_contact_geometry()[1]["poses"]


def body_regions(sample: dict[str, int], side: str):
    pose = contact_poses()[sample[f"fighter_id{side}"]][sample[f"anim_frame{side}"]]
    return [world(rect, sample[f"x{side}"], signed16(sample[f"y{side}"]),
                  sample[f"face{side}"]) for rect in pose[:2]]


def check(ok: bool, label: str, details: object | None = None) -> None:
    if not ok:
        raise AssertionError((label, details))
    checks.append({"check": label, "passed": True, "details": details})


def trace(e: Emulator) -> dict[str, int]:
    """Decode the public trace, including the input-feel extension."""

    # The v0.6 airborne/throw/knockdown extension occupies words 94..113
    # after the v0.5.1 combat classification words 82..93.
    # Keep this decoder local to the focused suite; the shared emulator host
    # remains deliberately backward-compatible with older ROMs until the
    # parent integrates the new trace aliases.
    data = C.string_at(e.ram + 0x1FF00, 228)
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
        "down_state1", "down_state2", "down_tick1", "down_tick2",
        "invuln1", "invuln2", "pending_throw_damage1", "pending_throw_damage2",
        "throw_owner1", "throw_owner2", "air_action1", "air_action2",
        "throw_victim1", "throw_victim2", "wake_action1", "wake_action2",
        "wake_age1", "wake_age2", "wake_jump1", "wake_jump2",
    )
    return dict(zip(names, words))


def vram_bytes(e: Emulator) -> bytes:
    """Read native VRAM without writing to the emulated machine."""

    pointer = e.core.retro_get_memory_data(3)
    size = e.core.retro_get_memory_size(3)
    return C.string_at(pointer, size)


def bg2_tile(memory: bytes, x: int, y: int) -> int:
    """Decode one 16-bit BG2 map entry from the native VRAM snapshot."""

    offset = BG2_MAP_BYTE + (y * 32 + x) * 2
    return int.from_bytes(memory[offset:offset + 2], "little")


def status_bar_expected(value: int, count: int, base: int,
                        attributes: int, scale_health: bool) -> list[int]:
    """Build the native eight-pixel status glyph sequence."""

    remaining = (value * 88) // 128 if scale_health else value
    return [attributes + base + min(8, max(0, remaining - index * 8))
            for index in range(count)]


def check_status_bars(e: Emulator, sample: dict[str, int], label: str) -> dict[str, object]:
    """Compare mirrored BG2 health/energy bars to the public trace values."""

    memory = vram_bytes(e)
    health_p1 = status_bar_expected(sample["hp1"], 11, HEALTH_TILE,
                                     P1_STATUS_ATTR | (0x0400 if sample["hp1"] <= 32 else 0), True)
    health_p2 = status_bar_expected(sample["hp2"], 11, HEALTH_TILE,
                                     P2_STATUS_ATTR | (0x0400 if sample["hp2"] <= 32 else 0), True)
    energy_p1 = status_bar_expected(sample["energy1"], 12, ENERGY_TILE,
                                    P1_STATUS_ATTR, False)
    energy_p2 = status_bar_expected(sample["energy2"], 12, ENERGY_TILE,
                                    P2_STATUS_ATTR, False)
    actual_health_p1 = [bg2_tile(memory, 1 + index, 1)
                        for index in range(11)]
    actual_health_p2 = [bg2_tile(memory, 30 - index, 1)
                        for index in range(11)]
    actual_energy_p1 = [bg2_tile(memory, 1 + index, 3)
                        for index in range(12)]
    actual_energy_p2 = [bg2_tile(memory, 30 - index, 3)
                        for index in range(12)]
    check(actual_health_p1 == health_p1 and actual_health_p2 == health_p2,
          "native mirrored health bars match trace HP after " + label, {
              "sample": sample, "p1": actual_health_p1,
              "expected_p1": health_p1, "p2": actual_health_p2,
              "expected_p2": health_p2,
          })
    check(actual_energy_p1 == energy_p1 and actual_energy_p2 == energy_p2,
          "native mirrored energy bars match trace meter after " + label, {
              "sample": sample, "p1": actual_energy_p1,
              "expected_p1": energy_p1, "p2": actual_energy_p2,
              "expected_p2": energy_p2,
          })
    return {
        "label": label, "hp": [sample["hp1"], sample["hp2"]],
        "energy": [sample["energy1"], sample["energy2"]],
        "health_p1": actual_health_p1, "health_p2": actual_health_p2,
        "energy_p1": actual_energy_p1, "energy_p2": actual_energy_p2,
    }


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


@lru_cache(maxsize=1)
def menu_preview_symbols() -> dict[str, int] | None:
    """Bind the v0.28 gesture wait to actual linked native state/counters."""
    version = tuple(map(int, json.loads((ROOT/'dist/manifest.json').read_bytes())['version'].split('.')))
    if version < (0, 28, 0):
        return None
    linked = {name: int(address, 16) & 0x1ffff for address, name in re.findall(
        r"^([0-9a-fA-F]{8}) (\S+)$",
        (ROOT/'dist/abaqus-after-hours.sym').read_text(), re.MULTILINE)}
    required = {'menuPreviewConfirm', 'selectPlayer', 'mode', 'frame',
                'snes_vblank_count', 'lag_frame_counter'}
    check(required <= linked.keys(), "preview fixture has linked gesture and health symbols",
          sorted(required - linked.keys()))
    return {name: linked[name] for name in required}


def menu_press(e: Emulator, keys: list[str], port: int = 0,
               hold: int = 12, release: int = 4) -> None:
    """Send one settled controller edge without opening a frontend.

    Scene loaders publish TRACE after loading graphics and eleven audio cues.
    Preserve the original edge/hold, then bound publication separately using
    the actual native scene byte. Short direction/SOCD holds remain unchanged.
    """

    kwargs = {"p1" if port == 0 else "p2": keys}
    before = native_screen(e)
    preview = menu_preview_symbols() if before == 1 else None
    def read(name, size=1):
        return int.from_bytes(C.string_at(e.ram + preview[name], size), "little")
    role = read("selectPlayer") if preview else None
    target = 1 if preview and role == 0 and read("mode") != 0 else 2
    first = preview_first = completed = None
    callbacks = 0
    def advance(held):
        nonlocal first, preview_first, completed, callbacks
        scene = native_screen(e)
        counters = [read(name, 2) for name in ("frame", "snes_vblank_count", "lag_frame_counter")] if preview else []
        e.run(1, **held)
        callbacks += 1
        after = native_screen(e)
        if after != before and first is None:
            first = callbacks
        if preview:
            phase = read("menuPreviewConfirm")
            if phase and preview_first is None:
                preview_first = callbacks
                check(phase == 1 and callbacks <= 2,
                      "roster confirm accepts the edge within two callbacks",
                      {"callback": callbacks, "phase": phase, "role": role})
            if preview_first is not None:
                if scene == after == 1:
                    current = [read(name, 2) for name in ("frame", "snes_vblank_count", "lag_frame_counter")]
                    delta = [(a-b) & 65535 for a, b in zip(current, counters)]
                    check(delta == [1, 1, 0], "roster gesture keeps native frame/VBlank/SDK cadence", delta)
                    stat = int.from_bytes(C.string_at(e.ram + 0x1ff00 + 114*2, 2), "little")
                    check(not stat & 0xc0, "roster gesture has no OBJ overflow", stat)
                if not phase and (after != 1 or read("selectPlayer") != role) and completed is None:
                    completed = callbacks
    for _ in range(hold):
        advance(kwargs)
    if preview_first is not None:
        for _ in range(release):
            advance({})
        # Wait only for the observed roster gesture, never for live gameplay.
        while completed is None and callbacks < preview_first + 18:
            advance({})
        check(completed == preview_first + 18 and native_screen(e) == target
              and read("menuPreviewConfirm") == 0 and (target != 1 or read("selectPlayer") == 1),
              "18-tick roster gesture publishes exactly the next selection step",
              {"accepted": preview_first, "completed": completed, "target": target,
               "scene": native_screen(e), "role": read("selectPlayer")})
    else:
        e.run(release)
    destination = native_screen(e)
    if destination != before:
        bound = preview_first + 18 if preview_first is not None else 2
        check(first is not None and first <= bound,
              "menu edge changes the actual scene within two callbacks" if preview_first is None else
              "roster scene change respects the measured gesture bound",
              {"from": before, "to": destination, "first_callback": first, "bound": bound})
        for settled in range(37):
            if trace(e)["screen"] == destination:
                break
            e.run(1)
        check(trace(e)["screen"] == destination and native_screen(e) == destination,
              "scene loader publishes the selected destination within 36 callbacks",
              {"destination": destination, "settle_callbacks": settled,
               "trace": trace(e)["screen"], "native": native_screen(e)})


def menu_title() -> Emulator:
    """Boot the title with the core option that exposes native SOCD input."""

    e = Emulator(core_options=MENU_CORE_OPTIONS)
    e.run(120)
    check(trace(e)["screen"] == 0, "menu regression boots at the title", trace(e))
    return e


def menu_select(e: Emulator, mode: int = 1) -> None:
    """Open the roster for any native mode."""

    for _ in range(mode):
        menu_press(e, ["down"])
    menu_press(e, ["a"])
    wait_screen(e, 1)


def menu_arena(e: Emulator, mode: int = 1) -> None:
    """Confirm each mode's fighter choices and settle on the arena screen."""

    menu_select(e, mode)
    if mode in (1, 2):
        menu_press(e, ["a"])
        wait_screen(e, 1)
        menu_press(e, ["a"])
    else:
        menu_press(e, ["a"])
    wait_screen(e, 2)


def menu_result() -> Emulator:
    """Reach a result card through controller-only local-versus play."""

    e = Emulator(core_options=MENU_CORE_OPTIONS)
    e.run(120)
    menu_press(e, ["down"])
    menu_press(e, ["a"])
    wait_screen(e, 1)
    menu_press(e, ["a"])
    wait_screen(e, 1)
    menu_press(e, ["a"])
    wait_screen(e, 2)
    menu_press(e, ["a"])
    wait_screen(e, 3)
    for _ in range(180):
        if trace(e)["intro"] == 0:
            break
        e.run(1)
    check(trace(e)["intro"] == 0,
          "menu result probe reaches live local combat", trace(e))
    for _ in range(2200):
        sample = trace(e)
        if sample["screen"] == 4:
            return e
        if sample["intro"] or sample["round_end"] or sample["paused"]:
            e.run(1)
            continue
        if sample["action1"] or sample["hurt1"] or sample["down_state1"]:
            e.run(6)
        elif abs(signed16(sample["x1"])-signed16(sample["x2"])) > 30 * 16:
            forward = "right" if sample["x1"] < sample["x2"] else "left"
            e.run(8, p1=[forward])
        else:
            e.run(3, p1=["x"])
            e.run(40)
    last = trace(e)
    e.close()
    raise AssertionError(("menu result probe did not reach a result card", last))


def check_training_menu_regressions() -> dict[str, object]:
    """Training's second roster keeps shared-pad SOCD and one-action priority."""

    results = {}
    for port in (0, 1):
        e = menu_title()
        try:
            menu_select(e, 2)
            # START wins over B/A, but this single held edge may only enter
            # the DUMMY roster, never skip it or start a fight.
            menu_press(e, ["start", "b", "a"])
            initial = trace(e)
            check(initial["screen"] == 1 and initial["selected2"] == 1,
                  "Training first START/B/A edge enters only the DUMMY roster", initial)
            menu_press(e, ["right"], port=port, hold=4, release=0)
            right = trace(e)
            check(right["selected"] == 0 and right["selected2"] == 2,
                  "either pad moves Training's DUMMY cursor without moving P1", {
                      "port": port, "state": right,
                  })
            # An opposite edge on the other participating pad must be
            # neutral while RIGHT remains held on the original pad.
            e.run(4, p1=["right"] if port == 0 else ["left"],
                  p2=["left"] if port == 0 else ["right"])
            e.run(4)
            check(trace(e)["selected2"] == right["selected2"],
                  "Training DUMMY neutralizes held opposites across both pads", {
                      "port": port, "state": trace(e),
                  })
            menu_press(e, ["up", "down"], port=port)
            check(trace(e)["selected2"] == right["selected2"],
                  "Training DUMMY neutralizes same-pad vertical SOCD", trace(e))
            # Split B and A across the merged pads. Back must return to P1
            # once, without letting the A edge re-enter DUMMY in that sample.
            e.run(12, p1=["b"] if port == 0 else ["a"],
                  p2=["a"] if port == 0 else ["b"])
            e.run(4)
            back = trace(e)
            check(back["screen"] == 1,
                  "Training DUMMY B wins over A and stays on the roster", back)
            menu_press(e, ["right"])
            moved = trace(e)
            check(moved["selected"] == 1 and moved["selected2"] == 2,
                  "Training DUMMY Back performs one action and restores P1 control", moved)
            menu_press(e, ["a"])
            check(trace(e)["screen"] == 1 and trace(e)["selected2"] == 2,
                  "Training re-confirm opens DUMMY with the adjacent default", trace(e))
            menu_press(e, ["start", "b", "a"], port=port)
            confirmed = trace(e)
            check(confirmed["screen"] == 2,
                  "Training DUMMY START wins over B/A and advances only to ARENA", confirmed)
            results[f"pad{port + 1}"] = {
                "first_confirm": initial, "dummy_right": right,
                "back": back, "p1_after_back": moved, "second_confirm": confirmed,
            }
        finally:
            e.close()
    return results


def check_menu_regressions() -> dict[str, object]:
    """Exercise native menu SOCD and confirm/back priority at every screen."""

    results: dict[str, object] = {"training": check_training_menu_regressions()}

    # Title: keep DOWN held while adding UP.  cleanDirections(raw) must make
    # that new opposite edge neutral, so the following confirm selects Local
    # Versus (menu row 1), rather than returning to Arcade row 0.
    e = menu_title()
    try:
        menu_press(e, ["down"], hold=4, release=0)
        e.run(4, p1=["down", "up"])
        e.run(4)
        menu_press(e, ["a"])
        title_state = trace(e)
        check(title_state["screen"] == 1 and title_state["mode"] == 1,
              "title held-opposite direction stays neutral before confirm",
              title_state)
        results["title_socd"] = title_state
    finally:
        e.close()

    # P1 roster: opposite directions on the same pad must not move the
    # selection after the first RIGHT edge has been held.
    e = menu_title()
    try:
        menu_select(e, 0)
        initial = trace(e)
        menu_press(e, ["right"], hold=4, release=0)
        after_right = trace(e)
        e.run(4, p1=["right", "left"])
        e.run(4)
        after_mixed = trace(e)
        check(after_right["selected"] == (initial["selected"] + 1) % 12,
              "P1 roster accepts one clean RIGHT edge", {
                  "initial": initial, "after_right": after_right,
              })
        check(after_mixed["selected"] == after_right["selected"],
              "P1 roster neutralizes held opposite directions", {
                  "after_right": after_right, "after_mixed": after_mixed,
              })
        results["roster_p1_socd"] = {
            "initial": initial["selected"],
            "after_right": after_right["selected"],
            "after_mixed": after_mixed["selected"],
        }
    finally:
        e.close()

    # P2 roster merges the two pads by contract, so test the same held
    # opposite sequence on port 2 while selectPlayer is active.
    e = menu_title()
    try:
        menu_select(e, 1)
        menu_press(e, ["a"])
        wait_screen(e, 1)
        initial = trace(e)
        menu_press(e, ["right"], port=1, hold=4, release=0)
        after_right = trace(e)
        e.run(4, p2=["right", "left"])
        e.run(4)
        after_mixed = trace(e)
        check(after_right["selected2"] == (initial["selected2"] + 1) % 12,
              "P2 roster accepts one clean RIGHT edge", {
                  "initial": initial, "after_right": after_right,
              })
        check(after_mixed["selected2"] == after_right["selected2"],
              "P2 roster neutralizes held opposite directions", {
                  "after_right": after_right, "after_mixed": after_mixed,
              })
        results["roster_p2_socd"] = {
            "initial": initial["selected2"],
            "after_right": after_right["selected2"],
            "after_mixed": after_mixed["selected2"],
        }
    finally:
        e.close()

    e = menu_title()
    try:
        menu_arena(e, 1)
        before = trace(e)
        menu_press(e, ["down"], hold=4, release=0)
        after_down = trace(e)
        e.run(4, p1=["down", "up"])
        e.run(4)
        after_mixed = trace(e)
        check(after_down["arena"] == (before["arena"] + 1) % 3,
              "ARENA accepts one clean DOWN edge", {
                  "before": before, "after_down": after_down,
              })
        check(after_mixed["arena"] == after_down["arena"],
              "ARENA neutralizes held opposite directions", {
                  "after_down": after_down, "after_mixed": after_mixed,
              })
        results["arena_socd"] = {
            "before": before["arena"],
            "after_down": after_down["arena"],
            "after_mixed": after_mixed["arena"],
        }
    finally:
        e.close()

    # Confirm has priority over Back.  These cases are intentionally distinct
    # because the old sequential menu branches could briefly load another
    # screen and then consume the same edge again.
    e = menu_title()
    try:
        menu_arena(e, 1)
        before = trace(e)
        menu_press(e, ["b", "start"])
        after = trace(e)
        check(after["screen"] == 3,
              "ARENA START confirm wins over simultaneous B back", {
                  "before": before, "after": after,
              })
        results["arena_confirm_priority"] = {
            "before_screen": before["screen"], "after_screen": after["screen"],
        }
    finally:
        e.close()

    e = menu_title()
    try:
        menu_select(e, 1)
        menu_press(e, ["a"])
        wait_screen(e, 1)
        before = trace(e)
        menu_press(e, ["b", "a"])
        after = trace(e)
        check(after["screen"] == 1,
              "P2 roster B back wins over simultaneous A confirm", {
                  "before": before, "after": after,
              })
        results["roster_p2_back_priority"] = {
            "before_screen": before["screen"], "after_screen": after["screen"],
        }
    finally:
        e.close()

    e = menu_title()
    try:
        menu_arena(e, 1)
        before = trace(e)
        menu_press(e, ["b", "a"])
        after = trace(e)
        check(after["screen"] == 1,
              "ARENA B back wins over simultaneous A confirm", {
                  "before": before, "after": after,
              })
        results["arena_back_priority"] = {
            "before_screen": before["screen"], "after_screen": after["screen"],
        }
    finally:
        e.close()

    e = menu_title()
    try:
        menu_select(e, 1)
        menu_press(e, ["a"])
        wait_screen(e, 1)
        before = trace(e)
        menu_press(e, ["b", "start"])
        after = trace(e)
        check(after["screen"] == 2,
              "P2 roster START confirm wins over simultaneous B back", {
                  "before": before, "after": after,
              })
        results["roster_p2_confirm_priority"] = {
            "before_screen": before["screen"], "after_screen": after["screen"],
        }
    finally:
        e.close()

    e = menu_result()
    try:
        before = trace(e)
        menu_press(e, ["b", "start"])
        after = trace(e)
        check(after["screen"] == 3,
              "RESULT START rematch wins over simultaneous B back", {
                  "before": before, "after": after,
              })
        results["result_confirm_priority"] = {
            "before_screen": before["screen"], "after_screen": after["screen"],
        }
    finally:
        e.close()

    e = menu_result()
    try:
        before = trace(e)
        menu_press(e, ["b", "a"])
        after = trace(e)
        check(after["screen"] == 1,
              "RESULT B back wins over simultaneous A confirm", {
                  "before": before, "after": after,
              })
        results["result_back_priority"] = {
            "before_screen": before["screen"], "after_screen": after["screen"],
        }
    finally:
        e.close()

    return results


def boot(mode: int = 2, wait_intro: bool = True,
         fighter: int = 0, fighter2: int | None = None,
         difficulty: int | None = None, title_delay: int = 0,
         core_options: dict[str, str] | None = None) -> Emulator:
    e = Emulator(core_options=core_options)
    e.run(120)
    if title_delay:
        # This is only used by deterministic CPU probes to align the native
        # frame modulo with an AI decision phase.  The default remains the
        # established boot cadence used by all legacy controller checks.
        e.run(title_delay)
    if difficulty is not None:
        check(difficulty in (0, 1, 2), "CPU probe difficulty is valid", difficulty)
        if difficulty < 1:
            press(e, "l")
        elif difficulty > 1:
            press(e, "r")
    for _ in range(mode):
        press(e, "down")
    press(e, "a")
    wait_screen(e, 1)
    for _ in range(fighter):
        press(e, "right")
    press(e, "a")
    if mode in (1, 2):
        target = fighter2 if fighter2 is not None else (
            (fighter + 1) % 12 if mode == 2 else 1)
        port = 0 if mode == 2 else 1
        for _ in range((target - trace(e)["selected2"]) % 12):
            press(e, "right", port)
        press(e, "a", port)
    wait_screen(e, 2)
    press(e, "a")
    wait_screen(e, 3)
    if wait_intro:
        if mode == 0:
            e.run(3, p1=["a"]); e.run(3)
        for _ in range(180):
            if trace(e)["intro"] == 0:
                break
            e.run(1)
        check(trace(e)["intro"] == 0, "input probe reaches live combat")
    e.run(3)
    return e


def close_players(e: Emulator) -> None:
    for _ in range(260):
        s = trace(e)
        if abs(s["x1"] - s["x2"]) < min(28, s["throw_range1"], s["throw_range2"]) * 16:
            return
        p1 = "right" if s["x1"] < s["x2"] else "left"
        p2 = "left" if p1 == "right" else "right"
        e.run(1, p1=[p1], p2=[p2])


@lru_cache(maxsize=1)
def _fighter_base() -> int:
    raw=(ROOT/'dist/abaqus-after-hours.sym').read_text(encoding='utf-8')
    return int(re.search(r'^([0-9a-fA-F]{8}) fighters$',raw,re.M)[1],16)&0x1ffff


def _action_clock(e: Emulator, port: int = 0) -> tuple[int,int]:
    """Observe current tick/end from the preserved Fighter64 ABI, read only."""
    raw=C.string_at(e.ram+_fighter_base()+port*64,64)
    return raw[17],raw[62]


def _stress_press(e: Emulator, key: str, port: int = 0) -> None:
    """Use the release stress probe's 20-frame menu tap cadence."""

    e.tap(key, port)
    e.run(20)


def _stress_wait_screen(e: Emulator, wanted: int,
                        max_frames: int = 600) -> None:
    """Match the roster stress harness's settled menu transition."""

    for _ in range(max_frames // 10):
        if trace(e)["screen"] == wanted:
            e.run(10)
            return
        e.run(10)
    raise AssertionError(("stress boot did not reach screen", wanted, trace(e)))


def _stress_boot(mode: int, fighter: int = 0, fighter2: int | None = None,
                 quiet_frames: int = 3, difficulty: int | None = None,
                 title_delay: int = 0) -> Emulator:
    """Boot with the exact cadence used by build/stress64.py/stress_two.py."""

    e = Emulator()
    e.run(120)
    if title_delay:
        e.run(title_delay)
    if difficulty is not None:
        check(difficulty in (0, 1, 2), "CPU stress difficulty is valid", difficulty)
        if difficulty < 1:
            _stress_press(e, "l")
        elif difficulty > 1:
            _stress_press(e, "r")
    for _ in range(mode):
        _stress_press(e, "down")
    _stress_press(e, "a")
    _stress_wait_screen(e, 1)
    for _ in range(fighter):
        _stress_press(e, "right")
    _stress_press(e, "a")
    if mode in (1, 2):
        target = fighter2 if fighter2 is not None else (
            (fighter + 1) % 12 if mode == 2 else 1)
        port = 0 if mode == 2 else 1
        for _ in range((target - trace(e)["selected2"]) % 12):
            _stress_press(e, "right", port)
        _stress_press(e, "a", port)
    _stress_wait_screen(e, 2)
    _stress_press(e, "a")
    _stress_wait_screen(e, 3)
    for _ in range(160):
        if trace(e)["intro"] == 0:
            break
        e.run(1)
    check(trace(e)["intro"] == 0, "stress boot reaches live combat", {
        "mode": mode, "fighter": fighter, "fighter2": fighter2,
    })
    e.run(quiet_frames)
    return e


def _cadence_boot(cadence: str, mode: int, fighter: int = 0,
                  fighter2: int | None = None, difficulty: int | None = None,
                  title_delay: int = 0) -> Emulator:
    """Select one of the two intentionally distinct stress boot cadences."""

    if cadence == "original":
        return boot(mode, fighter=fighter, fighter2=fighter2,
                    difficulty=difficulty, title_delay=title_delay)
    return _stress_boot(mode, fighter=fighter, fighter2=fighter2,
                        difficulty=difficulty, title_delay=title_delay)


def _run_transition_stress(cadence: str, fighter: int) -> dict[str, object]:
    """Run one four-family stress case without normalizing its phase."""

    e = _cadence_boot(cadence, 2, fighter=fighter)
    try:
        if fighter == 4 or DELIBERATE_PACING:
            # Slower travel must not turn transition coverage into a long
            # out-of-range walk. Establish genuine close spacing first;
            # every original 600 measured ticks and all bank/state checks stay.
            close_players(e)
            e.run(3)
        start = trace(e)["frame"]
        drops: list[dict[str, int]] = []
        banks: set[int] = set()
        down_states: set[int] = set()
        deliberate=DELIBERATE_PACING
        plan={'stage':0,'held':0,'started':False,'seen':False,'completed':[]}
        for index in range(600):
            phase = index % 150
            if deliberate:
                keys=_deliberate_transition_keys(trace(e),plan)
            elif phase < 38:
                keys = ["right"]
            elif phase < 44:
                keys = ["right", 'x']
            elif phase < 50:
                keys = ["up", "x"]
            elif phase < 80:
                # Repeated real edges let the sweep begin after the longer
                # throw commitment, rather than losing one early held edge.
                keys = ["down", 'a']
            elif phase < 110:
                keys = ["down", 'y']
            else:
                keys = []
            old = trace(e)["frame"]
            e.run(1, p1=keys)
            current = trace(e)
            delta = (current["frame"] - old) & 0xFFFF
            if delta != 1:
                drops.append({
                    "index": index, "delta": delta,
                    "frame": current["frame"],
                    "anim_frame1": current["anim_frame1"],
                    "anim_frame2": current["anim_frame2"],
                    "action1": current["action1"],
                    "down_state2": current["down_state2"],
                })
            banks.add(current["anim_frame1"] // 8)
            banks.add(current["anim_frame2"] // 8)
            down_states.add(current["down_state2"])
        result = {
            "boot_cadence": cadence,
            "fighter": fighter,
            "emulated_frames": 600,
            "game_ticks": (trace(e)["frame"] - start) & 0xFFFF,
            "nonunit_steps": drops,
            "banks": sorted(banks),
            "down_states": sorted(down_states),
            "controller_policy": "v025 observed completion before fresh command" if deliberate else "historical held sweep",
            "completed_commands": plan['completed'] if deliberate else None,
        }
        check(result["game_ticks"] == 600 and not drops,
              cadence + " transition stress advances exactly 600 native ticks",
              result)
        check(set(banks) == set(range(8)),
              cadence + " transition stress visits all eight animation banks",
              result)
        check(set(down_states) == set(range(6)),
              cadence + " transition stress visits every down-state", result)
        if deliberate:
            check(plan['completed']==list(range(6)),cadence+' retimed stress completes all six intended controller commands',result)
        return result
    finally:
        e.close()


def _deliberate_transition_keys(s: dict[str,int], plan: dict) -> list[str]:
    """A host-side command schedule, never an emulated-memory mutation.

    Slower commitments need real release gaps. Cover standalone X, close
    throw, sweep, jab, jump and special instead of letting one early held
    edge expire during the previous move. All 600 cadence/bank/state
    assertions remain in the original probe.
    """
    index=plan['stage']
    if index>=6:return []
    forward='right' if s['x1']<s['x2'] else 'left'
    actions=(3,9,6,1,0,7)
    keys=(['x'],[forward,'x'],['down','a'],['y'],['up'],['down','y'])[index]
    quiet=not any(s[k] for k in ('action1','hurt1','hurt2','down_state1','down_state2','y1','y2','hitstop'))
    if not plan['started']:
        if not quiet:return []
        if index in (1,2) and abs(s['x1']-s['x2'])>min(24,s['throw_range1']-1)*16:
            return [forward]
        plan.update(started=True,held=0,seen=False)
    if (s['y1']!=0 if index==4 else s['action1']==actions[index]):plan['seen']=True
    if plan['held']<3:
        plan['held']+=1
        return keys
    if plan['seen'] and quiet:
        plan['completed'].append(index)
        plan.update(stage=index+1,held=0,started=False,seen=False)
    return []


def check_transition_stress() -> dict[str, object]:
    """Run the fixed 600-tick two-actor transition cadence probe.

    The four representatives exercise every special family and the complete
    animation/knockdown path under the same controller schedule used by the
    release stress probe.  Every libretro step must advance exactly one native
    frame; the run must also visit all eight animation banks and every public
    down-state.  Inputs stay controller-only and deliberately match the
    gameplay cadence rather than being widened to hide a missed tick.
    """

    representatives = (0, 2, 4, 10)
    results: dict[str, object] = {}
    for cadence in ("original", "settled"):
        for fighter in representatives:
            results[f"{cadence}-{fighter:02}"] = _run_transition_stress(
                cadence, fighter)
    return results


def _run_combo_cadence_stress(cadence: str) -> dict[str, object]:
    """Keep the confirmed Y->X combo/UI path live for 600 native ticks."""

    e = _cadence_boot(cadence, 2, fighter=0)
    try:
        initial = trace(e)
        start = initial["frame"]
        drops: list[dict[str, int]] = []
        maximum_combo = 0
        phase, age = "approach", 0
        for index in range(600):
            sample = trace(e)
            keys: list[str] = []
            if phase == "approach" and not sample["action1"] and not sample["hurt2"]:
                if abs(sample["x1"] - sample["x2"]) > 28 * 16:
                    keys = ["right" if sample["x1"] < sample["x2"] else "left"]
                else:
                    phase, age = "jab", 0
            if phase == "jab":
                if sample["action1"] == 1 and sample["connected1"] == 2:
                    phase, age = "confirm", 0
                elif age < 3:
                    keys = ["y"]
                elif age > 40:
                    phase = "approach"
            if phase == "confirm":
                if age < 3:
                    keys = ["x"]
                else:
                    phase = "recover"
            elif phase == "recover" and not sample["action1"] and not sample["hurt2"]:
                phase = "approach"
            old = sample["frame"]
            e.run(1, p1=keys)
            current = trace(e)
            age += 1
            combo = event_field(current, "combo_link", 0)
            maximum_combo = max(maximum_combo, combo)
            delta = (current["frame"] - old) & 0xFFFF
            if delta != 1:
                drops.append({
                    "index": index, "delta": delta,
                    "frame": current["frame"],
                    "combo": combo,
                    "hp2": current["hp2"],
                })
        result = {
            "boot_cadence": cadence, "emulated_frames": 600,
            "game_ticks": (trace(e)["frame"] - start) & 0xFFFF,
            "nonunit_steps": drops, "max_combo": maximum_combo,
            "final_hp": [current["hp1"], current["hp2"]],
        }
        check(result["game_ticks"] == 600 and not drops,
              cadence + " combo cadence stress advances 600 native ticks",
              result)
        check(maximum_combo >= 2,
              cadence + " combo cadence stress confirms a Y-to-X chain", result)
        return result
    finally:
        e.close()


def check_combo_cadence_stress() -> dict[str, object]:
    """Run the combo cadence probe under both documented boot phases."""

    return {
        cadence: _run_combo_cadence_stress(cadence)
        for cadence in ("original", "settled")
    }


def _run_two_controller_stress(cadence: str, scenario: str) -> dict[str, object]:
    """Run one simultaneous two-controller scenario at its native phase."""

    e = _cadence_boot(cadence, 1, fighter=0, fighter2=0)
    try:
        start = trace(e)["frame"]
        initial = trace(e)
        drops: list[dict[str, int]] = []
        impact_frames = 0
        air_action_frames = [0, 0]
        air_frames = [0, 0]
        air_x_drift = [0, 0]
        final: dict[str, int] = {}
        for index in range(600):
            sample = trace(e)
            phase = index % 80
            if scenario == "air":
                p1 = (["up"] if phase < 3 else
                      ["x"] if phase < 10 else
                      ['a'] if 25 <= phase < 29 else [])
                p2 = (["up"] if phase < 3 else
                      ["y"] if phase < 10 else
                      ["a"] if 25 <= phase < 29 else [])
            else:
                p1: list[str] = []
                p2: list[str] = []
                if phase < 20 and abs(sample["x1"] - sample["x2"]) > 26 * 16:
                    p1 = ["right" if sample["x1"] < sample["x2"] else "left"]
                    p2 = ["left" if sample["x1"] < sample["x2"] else "right"]
                if 20 <= phase < 24:
                    p1 = p2 = ["y"]
            old = sample["frame"]
            e.run(1, p1=p1, p2=p2)
            current = trace(e)
            delta = (current["frame"] - old) & 0xFFFF
            if delta != 1:
                drops.append({
                    "index": index, "delta": delta,
                    "frame": current["frame"],
                    "action1": current["action1"],
                    "action2": current["action2"],
                    "hp1": current["hp1"], "hp2": current["hp2"],
                })
            if current["hitstop"]:
                impact_frames += 1
            if scenario == "air":
                for port in range(2):
                    suffix = str(port + 1)
                    if current[f"air_action{suffix}"]:
                        air_action_frames[port] += 1
                        if signed16(current[f"y{suffix}"]) < 0:
                            air_frames[port] += 1
                            air_x_drift[port] = max(
                                air_x_drift[port],
                                abs(current[f"x{suffix}"] - initial[f"x{suffix}"]),
                            )
            final = current
        result = {
            "boot_cadence": cadence, "scenario": scenario,
            "emulated_frames": 600,
            "game_ticks": (trace(e)["frame"] - start) & 0xFFFF,
            "nonunit_steps": drops, "impact_frames": impact_frames,
            "final_hp": [final.get("hp1"), final.get("hp2")],
        }
        if scenario == "air":
            result.update({
                "air_action_frames": air_action_frames,
                "air_frames": air_frames,
                "air_x_drift": air_x_drift,
            })
        check(result["game_ticks"] == 600 and not drops,
              cadence + " two-controller " + scenario +
              " stress advances 600 native ticks", result)
        if scenario == "air":
            check(all(value > 0 for value in air_action_frames) and
                  all(value > 0 for value in air_frames),
                  cadence + " two-controller air stress executes both air normals",
                  result)
            check(air_x_drift == [0, 0],
                  cadence + " two-controller air normals preserve takeoff X",
                  result)
            check(result["final_hp"] == [128, 128],
                  cadence + " two-controller air stress leaves both HP intact",
                  result)
        else:
            check(impact_frames > 0,
                  cadence + " two-controller trades stress reaches combat hitstop",
                  result)
        return result
    finally:
        e.close()


def check_two_controller_stress() -> dict[str, object]:
    """Run simultaneous air-normal and close-trade cadence scenarios."""

    results: dict[str, object] = {}
    for cadence in ("original", "settled"):
        for scenario in ("air", "trades"):
            results[f"{cadence}-{scenario}"] = _run_two_controller_stress(
                cadence, scenario)
    return results


def _pcm_values(data: bytes) -> list[int]:
    """Decode captured little-endian signed PCM samples."""

    usable = len(data) & ~1
    return [int.from_bytes(data[index:index + 2], "little", signed=True)
            for index in range(0, usable, 2)]


def _pcm_metrics(data: bytes) -> dict[str, int | bool]:
    values = _pcm_values(data)
    peak = max((abs(value) for value in values), default=0)
    return {
        "bytes": len(data), "samples": len(values),
        "nonzero": sum(value != 0 for value in values),
        "peak": peak, "clipped": peak >= 32767,
    }


def _pcm_prefix_alignment(left: bytes, right: bytes,
                          window: int = 4096,
                          max_shift_bytes: int = 128) -> dict[str, int | float]:
    """Find a sample-aligned matching prefix for two fresh audio captures."""

    best = {"shift_bytes": 0, "compared_bytes": 0,
            "equal_bytes": 0, "ratio": 0.0}
    for shift in range(-max_shift_bytes, max_shift_bytes + 1, 2):
        left_start = max(0, shift)
        right_start = max(0, -shift)
        compared = min(len(left) - left_start, len(right) - right_start, window)
        if compared <= 0:
            continue
        equal = sum(left[left_start + index] == right[right_start + index]
                    for index in range(compared))
        ratio = equal / compared
        if ratio > float(best["ratio"]):
            best = {"shift_bytes": shift, "compared_bytes": compared,
                    "equal_bytes": equal, "ratio": ratio}
    return best


def _audio_branch(cue: str, triggered: bool) -> tuple[bytes, bytes]:
    """Capture one fresh branch while only one Snes9x core is alive.

    The libretro Snes9x DLL keeps core/audio callback state globally, so two
    Emulator instances cannot be advanced concurrently.  Sequential fresh
    boots preserve the paired comparison without routing one branch's PCM to
    the other branch or invalidating teardown.
    """

    e = _cadence_boot("original", 2, fighter=0)
    try:
        close_players(e)
        e.pcm = bytearray()
        e.run(12)
        prefix = bytes(e.pcm)
        e.pcm = bytearray()
        if cue == "normal-contact":
            if triggered:
                e.run(4, p1=["y"])
            else:
                e.run(4)
        elif cue == "special":
            if triggered:
                e.run(3, p1=["down"])
                e.run(3, p1=["down", 'y'])
                e.run(2)
            else:
                e.run(8)
        else:
            raise AssertionError(("unknown audio cue", cue))
        return prefix, bytes(e.pcm)
    finally:
        e.close()


def _audio_pair(cue: str) -> dict[str, object]:
    """Compare a cue window with a fresh, otherwise identical silent input."""

    quiet_prefix, quiet_window = _audio_branch(cue, False)
    triggered_prefix, triggered_window = _audio_branch(cue, True)
    alignment = _pcm_prefix_alignment(quiet_prefix, triggered_prefix)
    check(float(alignment["ratio"]) >= 0.99 and
          int(alignment["compared_bytes"]) >= 1024,
          cue + " audio pre-trigger PCM prefix matches or phase-aligns", {
              "cue": cue, "alignment": alignment,
          })

    quiet_metrics = _pcm_metrics(quiet_window)
    triggered_metrics = _pcm_metrics(triggered_window)
    compared = min(len(quiet_window), len(triggered_window))
    differing = sum(quiet_window[index] != triggered_window[index]
                    for index in range(compared))
    check(differing > 0,
          cue + " cue window differs from its no-input control", {
              "cue": cue, "differing_bytes": differing,
              "compared_bytes": compared,
          })
    check(triggered_metrics["nonzero"] > 0 and
          triggered_metrics["peak"] > 0,
          cue + " cue window contains captured PCM", {
              "cue": cue, "metrics": triggered_metrics,
          })
    check(not quiet_metrics["clipped"] and not triggered_metrics["clipped"],
          cue + " cue audio stays below signed-PCM clipping", {
              "cue": cue, "quiet": quiet_metrics,
              "triggered": triggered_metrics,
          })
    return {
        "cue": cue, "prefix": alignment,
        "quiet_window": quiet_metrics,
        "triggered_window": triggered_metrics,
        "differing_bytes": differing,
    }


def check_resident_sfx_audio() -> dict[str, object]:
    """Prove resident normal/contact and special cues reach the PCM callback."""

    return {
        "normal_contact": _audio_pair("normal-contact"),
        "special": _audio_pair("special"),
    }


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

    The first normal has a fourteen-tick life with the current profile. The
    second three-frame tap begins around tick ten, where the six-tick
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
    for _ in range(60):
        tick,end=_action_clock(e)
        if tick>=end-4:break
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
    for _ in range(3):
        e.run(1, p1=["x"])
        freeze_samples.append(trace(e))
    tap = trace(e)
    captured = (tap["buffered_action1"] == 3 and tap["buffer_age1"] > 0)
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
        if not s["hitstop"] and s["action1"] == 3:
            executed = s
            break
        e.run(1)
    check(executed is not None,
          "hitstop tap executes after the freeze expires", {
              "tap": tap,
              "trace": executed or trace(e),
          })
    if executed is not None:
        check(executed["anim_frame1"] in (32, 34, 6, 35),
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
        drive(e, port, ["down", 'y'], 3)
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


def confirm_heavy(e: Emulator, first: dict[str, int],
                  hold_defender: list[str] | None = None
                  ) -> tuple[dict[str, int] | None, list[dict[str, int]]]:
    """React to real jab contact with a fresh X edge during its hitstop.

    Observe new damage rather than the jab's still-latched connected flag.
    Guard input remains sampled throughout; no future input is inspected.
    """

    check(first["connected1"] == 2 and first["hitstop"] > 0,
          "strong confirm follows an observed real jab hitstop", first)
    rows = []
    for index in range(50):
        e.run(1, p1=["x"] if index < 3 else [],
              p2=hold_defender or [])
        current = trace(e)
        rows.append(current)
        if current["hp2"] < first["hp2"]:
            return current, rows
    return None, rows


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


def check_motion_step_timeout_both_ports() -> list[dict[str, object]]:
    """A slow complete motion works when each progress step beats its timeout."""
    cases = []
    for port in (0, 1):
        suffix = str(port + 1)
        for gap in (8, 12):
            e = boot(1)
            try:
                before = trace(e)
                forward = "right" if before[f"face{suffix}"] else "left"
                started = e.frames
                steps = []
                for keys, frames in ((["down"], 3), ([], gap),
                                     (["down", forward], 1), ([], gap),
                                     ([forward], 1), ([forward, "x"], 3)):
                    drive(e, port, keys, frames)
                    now = trace(e)
                    steps.append({"elapsed_frames": e.frames - started, "keys": keys,
                                  "stage": now[f"command_stage{suffix}"],
                                  "action": now[f"action{suffix}"],
                                  "energy": now[f"energy{suffix}"]})
                case = {"port": port, "gap_between_steps": gap, "steps": steps}
                if gap == 8:
                    check(steps[4]["stage"] == 3 and steps[4]["elapsed_frames"] > 12,
                          f"P{suffix} QCF timeout refreshes on progress, not from the first Down", case)
                    check(steps[-1]["action"] == 7 and
                          before[f"energy{suffix}"] - steps[-1]["energy"] >= 28,
                          f"P{suffix} spaced QCF creates a real energy-spending special", case)
                else:
                    check(steps[1]["stage"] == 0 and steps[4]["stage"] == 0,
                          f"P{suffix} twelve neutral ticks expire an unfinished motion step", case)
                    check(steps[-1]["action"] != 7 and
                          steps[-1]["energy"] >= before[f"energy{suffix}"],
                          f"P{suffix} expired QCF falls back to a normal without a special cost", case)
                cases.append(case)
            finally:
                e.close()
    return cases


def _throw_victim_to_wake(e: Emulator, victim: int) -> dict[str, int]:
    """Create a local throw and return the victim's first wake sample."""

    attacker = 1 - victim
    _close_for_throw(e)
    before = trace(e)
    attacker_suffix = str(attacker + 1)
    victim_suffix = str(victim + 1)
    forward = "right" if before[f"face{attacker_suffix}"] else "left"
    drive(e, attacker, [forward, 'x'], 3)
    for _ in range(180):
        sample = trace(e)
        if sample[f"down_state{victim_suffix}"] == 5:
            return sample
        drive(e, attacker, [])
    raise AssertionError(("throw probe did not reach wake", victim, trace(e)))


def _wait_wake_free(e: Emulator, victim: int) -> dict[str, int]:
    """Release a wake victim and return its first free sample."""

    suffix = str(victim + 1)
    for _ in range(16):
        sample = trace(e)
        if sample[f"down_state{suffix}"] == 0:
            return sample
        drive(e, victim, [])
    raise AssertionError(("wake did not become free", victim, trace(e)))


def check_wake_motion_both_ports() -> None:
    """Wake directions cannot leak into a later special, in either port.

    Wake still accepts its explicit attack/jump edges (covered by the existing
    wake regression).  A fresh QCF entered after wake must remain valid.
    """

    for victim in (0, 1):
        suffix = str(victim + 1)

        # A direction-only QCF entered during wake must be discarded.  The
        # fresh X edge after wake should start normal action 3 and retain meter.
        e = boot(1)
        try:
            wake = _throw_victim_to_wake(e, victim)
            forward = "right" if wake[f"face{suffix}"] else "left"
            for keys in (["down"], ["down"], ["down", forward], [forward]):
                drive(e, victim, keys)
            drive(e, victim, [])
            free = _wait_wake_free(e, victim)
            energy = free[f"energy{suffix}"]
            drive(e, victim, ["x"])
            post = trace(e)
            check(post[f"action{suffix}"] == 3 and
                  post[f"energy{suffix}"] == energy,
                  f"P{suffix} wake-only QCF directions do not turn fresh X into a special", {
                      "wake": wake,
                      "free": free,
                      "post": post,
                  })
        finally:
            e.close()

        # A new, complete QCF after wake must still produce the character
        # special, proving the wake cleanup does not disable later motion.
        e = boot(1)
        try:
            _throw_victim_to_wake(e, victim)
            free = _wait_wake_free(e, victim)
            forward = "right" if free[f"face{suffix}"] else "left"
            for keys in (["down"], ["down", forward], [forward]):
                drive(e, victim, keys, 3)
            motion = trace(e)
            check(motion[f"command_stage{suffix}"] == 3,
                  f"P{suffix} fresh post-wake QCF reaches forward stage", {
                      "free": free,
                      "motion": motion,
                  })
            energy = motion[f"energy{suffix}"]
            drive(e, victim, [forward, "x"], 3)
            special = trace(e)
            check((special[f"action{suffix}"] == 7 or
                   special[f"wave{suffix}"]) and
                  special[f"energy{suffix}"] < energy,
                  f"P{suffix} fresh post-wake QCF still creates a special", {
                      "motion": motion,
                      "special": special,
                  })
        finally:
            e.close()


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
    # inside startup+active+5 and a fresh strong punch may cancel it.
    e = boot(1)
    try:
        close_players(e)
        drive(e, 0, ["y"], 3)
        drive(e, 0, [])
        hit, live = wait_for_hitstop_end(e)
        e.run(1)
        drive(e, 0, ["x"], 3)
        early = trace(e)
        check(early["action1"] == 3,
              "early hit-confirm cancels into a strong punch", {
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
        for _ in range(60):
            tick,end=_action_clock(e)
            if tick>=end-2:break
            e.run(1)
        late_before = trace(e)
        check(late_before["action1"] == 1,
              "late cancel probe remains in the first attack recovery", {
                  "hitstop": hit, "trace": late_before,
              })
        held = []
        # One callback is a real fresh edge and is released before the
        # tuned fourteen-tick jab finishes, so restart cannot be a hold.
        for _ in range(1):
            drive(e, 0, ["x"])
            held.append(trace(e))
        check(held[0]["action1"] == 1 and held[0]["buffered_action1"] == 3,
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
            check(restarted["action1"] == 3 and restarted["anim_tick1"] <= 2,
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


def check_guard_timing() -> dict[str, object]:
    """Guard impact keeps chip low, pushback light, and stun finite."""

    e = boot(1)
    status_bar_results: list[dict[str, object]] = []
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
            return {"status_bars": status_bar_results}
        blocked_samples = [sample for sample in samples
                           if sample["pose2"] == 9]
        blocked_dx = blocked_hit["x2"] - (blocked_previous or start)["x2"]
        check(blocked_hit["hp2"] >= start["hp2"] - 1,
              "guarded light punch deals at most one point of chip", {
                  "start_hp": start["hp2"], "impact": blocked_hit,
              })
        guard_min,guard_max=(15,17) if DELIBERATE_PACING else (8,14)
        check(guard_min <= len(blocked_samples) <= guard_max,
              "guard stun lasts the reviewed live window plus contact pause", {
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

            # The health DMA is intentionally deferred into hitstop.  Read
            # the live trace only after that queue has settled, then verify
            # both native mirrored bars against the exact BG2 map entries.
            e.run(8)
            settled = trace(e)
            status_bar_results.append(check_status_bars(
                e, settled, "the real hit"))

            # Spend meter through the public down+X shortcut in the same
            # round.  Wait for a grounded, neutral control tick so this edge
            # cannot be confused with the previous normal's recovery.
            for _ in range(80):
                ready = trace(e)
                if (ready["action1"] == 0 and ready["hurt1"] == 0 and
                        ready["hitstop"] == 0 and signed16(ready["y1"]) == 0):
                    break
                e.run(1)
            special_before = trace(e)
            drive(e, 0, ["down"], 3)
            drive(e, 0, ["down", 'y'], 3)
            special_spent: dict[str, int] | None = None
            for _ in range(80):
                special_sample = trace(e)
                if special_sample["energy1"] < special_before["energy1"]:
                    special_spent = special_sample
                    break
                e.run(1)
            check(special_spent is not None,
                  "public special input spends player one's meter", {
                      "before": special_before,
                      "after": special_spent or trace(e),
                  })
            if special_spent is not None:
                # Allow periodic HUD refresh and any impact hitstop DMA to
                # complete before comparing the current trace to VRAM.
                e.run(18)
                status_bar_results.append(check_status_bars(
                    e, trace(e), "the special meter spend"))
    finally:
        e.close()

    return {"status_bars": status_bar_results}


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


def counter_banner_row(e: Emulator, attacker: int) -> list[int]:
    """Read the exact BG2 row-9 banner cells for one attacker side."""

    memory = vram_bytes(e)
    origin = 20 if attacker else 2
    return [bg2_tile(memory, origin + index, 9) for index in range(8)]


def check_counter_banner() -> dict[str, object]:
    """Verify a real counter event, cadence, and native COUNTER! banner."""

    expected = [(256 + ord(character)) | 0x2000 for character in "COUNTER!"]
    results: dict[str, object] = {}
    for attacker in (0, 1):
        defender = 1 - attacker
        e = boot(1)
        try:
            close_players(e)
            initial = trace(e)
            initial_frame = initial["frame"]
            # P1's Y jab beats P2's slower R heavy, then mirror the exact
            # edge-triggered fixture on port two.  Holding both for one native
            # tick gives captureInput an unambiguous edge on each port.
            if attacker == 0:
                e.run(1, p1=["y"], p2=['a'])
            else:
                e.run(1, p1=['a'], p2=["y"])
            samples = [trace(e)]
            rows = [counter_banner_row(e, attacker)]
            previous_frame = initial_frame
            deltas = [(samples[0]["frame"] - previous_frame) & 0xffff]
            counter_index: int | None = None

            # Keep every native frame through contact plus the five-tick
            # frozen window.  The first banner DMA is intentionally deferred
            # into hitstop, so VRAM is sampled on every frame here.
            for _ in range(28):
                previous = samples[-1]
                e.run(1)
                sample = trace(e)
                samples.append(sample)
                rows.append(counter_banner_row(e, attacker))
                deltas.append((sample["frame"] - previous["frame"]) & 0xffff)
                if counter_index is None and \
                        event_field(sample, "counter", attacker) == 1 and \
                        event_field(sample, "connected", attacker) == 2 and \
                        sample[f"hp{defender + 1}"] < initial[f"hp{defender + 1}"]:
                    counter_index = len(samples) - 1

            evidence = {
                "initial": initial,
                "counter_index": counter_index,
                "samples": [{
                    "frame": sample["frame"],
                    "hitstop": sample["hitstop"],
                    "counter": event_field(sample, "counter", attacker),
                    "connected": event_field(sample, "connected", attacker),
                    "hp1": sample["hp1"], "hp2": sample["hp2"],
                } for sample in samples[:12]],
                "banner_rows": rows[:12],
                "expected": expected,
                "deltas": deltas[:12],
            }
            prefix = f"P{attacker + 1} counter"
            check(counter_index is not None,
                  f"{prefix} produces a real counter contact and damage",
                  evidence)
            if counter_index is None:
                results[f"p{attacker + 1}"] = evidence
                continue

            contact = samples[counter_index]
            counter_end = min(counter_index + 5, len(samples) - 1)
            banner_indices = [index for index, row in enumerate(rows)
                              if row == expected]
            first_banner = min(banner_indices) if banner_indices else None
            check(all(delta == 1 for delta in deltas[:counter_end + 1]),
                  f"{prefix} keeps one native frame cadence through hitstop",
                  {"contact_index": counter_index,
                   "deltas": deltas[:counter_end + 1],
                   "contact": contact})
            check(first_banner is not None and
                  counter_index <= first_banner <= counter_index + 3,
                  f"{prefix} shows COUNTER! within three frozen ticks",
                  {"contact_index": counter_index,
                   "first_banner": first_banner,
                   "contact_hitstop": contact["hitstop"],
                   "rows": rows[counter_index:counter_end + 1]})
            check(first_banner is not None and
                  all(rows[index] == expected
                      for index in range(first_banner, counter_end + 1)),
                  f"{prefix} keeps the exact side-correct COUNTER! row",
                  {"first_banner": first_banner,
                   "rows": rows[first_banner:counter_end + 1],
                   "expected": expected})
            results[f"p{attacker + 1}"] = {
                **evidence,
                "first_banner": first_banner,
                "counter_hitstop": contact["hitstop"],
                "banner_origin_x": 20 if attacker else 2,
            }
        finally:
            e.close()
    return results


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
        check(cancel["action1"] == 3,
              "real hit confirmation cancels into a strong punch", {
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
        check(blocked_cancel["action1"] != 3,
              "blocked jab cannot hit-confirm cancel into medium", {
                  "event": blocked, "trace": blocked_cancel,
              })
        check(event_field(blocked_cancel, "combo_link", 0) == 0 and
              event_field(blocked_cancel, "counter", 0) == 0,
              "blocked contact does not start a combo or counter", blocked_cancel)
    finally:
        e.close()


def check_held_back_combo_and_block_string() -> None:
    """Keep true links real while a hurt defender holds back, and keep a
    continuous guard string blocked after the first impact.

    Holding back is sampled during hitstun in the SNES input path.  It must
    not turn the next confirmed hit into a block merely because the defender
    is still holding the guard direction.  The companion probe keeps guard
    held across two separate normals and requires both contacts to remain
    blocked, preserving the normal block-string behavior.
    """

    e = boot(1)
    try:
        close_players(e)
        start_normal(e, 0, "y")
        first, history = wait_connected(e, 0)
        check(first is not None and event_field(first or {}, "connected", 0) == 2,
              "held-back combo starts from a real jab", {
                  "event": first, "history": history,
              })
        if first is not None:
            defender_back = ["right" if first["face2"] == 0 else "left"]
            # Keep the defender's back direction held through hitstop and the
            # next attack's active window.  The first hit's hurt timer must
            # still be live when the second contact is observed.
            second, second_history = confirm_heavy(e, first, defender_back)
            check(second is not None and
                  event_field(second or {}, "connected", 0) == 2 and
                  event_field(second or {}, "guard", 1) == 0 and
                  event_field(second or {}, "hurt", 1) > 0 and
                  event_field(second or {}, "combo_link", 0) >= 2,
                  "held-back defender stays a real hit during hurt continuity", {
                      "first": first, "second": second,
                      "history": second_history,
                  })
    finally:
        e.close()

    e = boot(1)
    try:
        close_players(e)
        guard = ["down", "right"]
        start_normal(e, 0, "y", guard)
        first, first_history = wait_connected(e, 0, guard)
        check(first is not None and event_field(first or {}, "connected", 0) == 1,
              "continuous block string starts with blocked contact", {
                  "event": first, "history": first_history,
              })
        if first is not None:
            initial_hp = first["hp2"]
            # Release the first attack's recovery while keeping the guard
            # direction sampled, then issue a second normal into the same
            # standing guard.
            for _ in range(40):
                sample = trace(e)
                if sample["action1"] == 0 and sample["hurt1"] == 0:
                    break
                e.run(1, p2=guard)
            start_normal(e, 0, "x", guard)
            second, second_history = wait_connected(e, 0, guard)
            check(second is not None and
                  event_field(second or {}, "connected", 0) == 1 and
                  event_field(second or {}, "guard", 1) > 0 and
                  second["hp2"] >= initial_hp - 1,
                  "continuous guard string keeps the second contact blocked", {
                      "first": first, "second": second,
                      "history": second_history,
                  })
    finally:
        e.close()


def check_stale_prehit_buffer() -> None:
    """A defender's pre-hit command clears while fresh hitstop input remains."""

    e = boot(1)
    try:
        close_players(e)
        # P1 starts a slow strong kick.  X is buffered during its startup,
        # then P2's faster jab lands while P1 is still the defender.  This
        # exercises the contract's defender-side stale-buffer clearing path.
        e.run(1, p1=["a"], p2=["y"])
        prehit: list[dict[str, int]] = []
        for _ in range(3):
            e.run(1, p1=["x"])
            prehit.append(trace(e))
        e.run(1, p1=[])
        check(any(s["buffered_action1"] == 3 and
                  event_field(s, "hurt", 1) == 0 for s in prehit),
              "defender pre-hit strong input is visibly buffered", prehit)

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
        check(any(s["buffered_action1"] == 3 and s["buffer_age1"] > 0
                  for s in hitstop_taps),
              "new hitstop strong tap is captured after stale input clears", {
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
    second, _ = confirm_heavy(e, first)
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
        drive(e, 0, [forward, 'x'], 3)
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
        drive(e, 1, [forward, 'x'], 3)
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
        drive(e, 0, [forward, 'x'], 3)
        no_throw = trace(e)
        check(no_throw["action1"] != 9,
              "P1 heavy input outside throw range falls back to a normal", {
                  "outside": outside, "trace": no_throw,
              })
    finally:
        e.close()


def _airborne_normal_probe(e: Emulator, port: int, key: str) -> dict[str, object]:
    """Trigger one airborne normal and retain its public action latch."""

    suffix = str(port + 1)
    y_key = f"y{suffix}"
    face_key = f"face{suffix}"
    action_key = f"air_action{suffix}"
    drive(e, port, ["up"], 3)
    takeoff = None
    for _ in range(20):
        sample = trace(e)
        if signed16(sample[y_key]) < 0:
            takeoff = sample
            break
        drive(e, port, [])
    check(takeoff is not None, f"P{suffix} airborne {key.upper()} starts above the floor", {
        "key": key, "trace": trace(e),
    })
    if takeoff is None:
        return {"key": key, "air_action": 0, "airborne": False}
    face = takeoff[face_key]
    drive(e, port, [key], 3)
    samples: list[dict[str, int]] = []
    for _ in range(36):
        sample = trace(e)
        samples.append(sample)
        if sample[action_key] and signed16(sample[y_key]) < 0:
            check(sample[face_key] == face,
                  f"P{suffix} airborne {key.upper()} preserves facing", sample)
        drive(e, port, [])
    latched = [sample[action_key] for sample in samples if sample[action_key]]
    check(bool(latched), f"P{suffix} airborne {key.upper()} exposes an action latch", {
        "key": key, "samples": samples,
    })
    for _ in range(100):
        sample = trace(e)
        if signed16(sample[y_key]) == 0:
            break
        drive(e, port, [])
    landed = trace(e)
    check(landed[f"action{suffix}"] == 0 and landed[action_key] == 0,
          f"P{suffix} airborne {key.upper()} completes on landing", landed)
    return {"key": key, "air_action": latched[0] if latched else 0,
            "latch_values": sorted(set(latched)),
            "airborne": any(signed16(sample[y_key]) < 0 for sample in samples)}


def check_air_normals_both_sides() -> None:
    """All four airborne normals work for right- and left-facing players."""

    e = boot(1)
    try:
        results: dict[str, object] = {}
        for port in (0, 1):
            for key in ("y", "x", "b", "a"):
                results[f"p{port + 1}-{key}"] = _airborne_normal_probe(e, port, key)
        check(len(results) == 8, "both controller directions cover four airborne normals", results)
    finally:
        e.close()


def check_air_contact_window() -> None:
    """Air contact is classified on the active drawing and ends on landing."""

    # Keep one punch and one kick in separate fresh local-versus rounds so the
    # first connected edge remains unambiguous.  The trace's animation frame
    # is the source of truth; a persistent connected=2 value during recovery
    # must not be mistaken for a second active hit.
    cases = ((0, "y", 50), (1, "b", 53))
    for port, key, active_frame in cases:
        e = boot(1)
        try:
            close_players(e)
            suffix = str(port + 1)
            y_key = f"y{suffix}"
            face_key = f"face{suffix}"
            drive(e, port, ["up"], 3)
            for _ in range(12):
                if signed16(trace(e)[y_key]) < 0:
                    break
                drive(e, port, [])
            takeoff = trace(e)
            check(signed16(takeoff[y_key]) < 0,
                  f"P{suffix} air-contact probe reaches ascent", takeoff)
            takeoff_face = takeoff[face_key]
            if DELIBERATE_PACING:
                # The longer arc puts an early ascent punch over the head.
                # Earn a descending jump-in at the same unchanged hit region.
                previous_y = signed16(takeoff[y_key])
                for _ in range(90):
                    drive(e, port, [])
                    current_y = signed16(trace(e)[y_key])
                    if previous_y < current_y and -42 * 16 <= current_y < 0:
                        break
                    previous_y = current_y
                check(current_y < 0, "slower air-contact setup stays airborne")
            drive(e, port, [key], 6)
            previous_connected = 0
            contact = None
            samples: list[dict[str, int]] = []
            for _ in range(48):
                sample = trace(e)
                samples.append(sample)
                connected = event_field(sample, "connected", port)
                if contact is None and connected == 2 and previous_connected != 2:
                    contact = sample
                previous_connected = connected
                drive(e, port, [])
            check(contact is not None,
                  f"P{suffix} airborne {key.upper()} reaches a real contact", {
                      "port": port, "key": key, "samples": samples,
                  })
            if contact is not None:
                check(contact[f"anim_frame{suffix}"] == active_frame,
                      f"P{suffix} airborne contact occurs on active frame {active_frame}",
                      contact)
                check(contact[face_key] == takeoff_face,
                      f"P{suffix} airborne contact keeps takeoff facing", contact)
            landed = None
            for _ in range(80):
                sample = trace(e)
                if signed16(sample[y_key]) == 0:
                    landed = sample
                    break
                drive(e, port, [])
            check(landed is not None and landed[f"action{suffix}"] == 0 and
                  landed[f"air_action{suffix}"] == 0,
                  f"P{suffix} airborne action clears on landing", landed or trace(e))
        finally:
            e.close()


def _close_for_throw(e: Emulator) -> None:
    for _ in range(180):
        sample = trace(e)
        # The engine's throw contact is strict '< throwRange'.  Use the
        # smaller live profile range so mirrored P2 probes cannot settle at
        # an exactly-equal 25px edge and accidentally start a normal.
        limit = min(sample["throw_range1"], sample["throw_range2"]) * 16
        if abs(sample["x1"] - sample["x2"]) < limit:
            return
        if sample["x1"] < sample["x2"]:
            e.run(1, p1=["right"], p2=["left"])
        else:
            e.run(1, p1=["left"], p2=["right"])
    raise AssertionError(("throw probe could not close players", trace(e)))


def _observe_throw(e: Emulator, attacker: int) -> dict[str, object]:
    """Return the complete delayed throw/downed trace for one attacker."""

    _close_for_throw(e)
    before = trace(e)
    victim = 1 - attacker
    a_suffix = str(attacker + 1)
    v_suffix = str(victim + 1)
    forward = "right" if before[f"face{a_suffix}"] else "left"
    drive(e, attacker, [forward, 'x'], 3)
    samples: list[dict[str, int]] = []
    first_down = None
    damage_state = None
    damage_hp = None
    saw_floor = False
    saw_wake = False
    initial_hp = before[f"hp{v_suffix}"]
    for _ in range(140):
        sample = trace(e)
        samples.append(sample)
        if first_down is None and sample[f"down_state{v_suffix}"]:
            first_down = sample
        if sample[f"down_state{v_suffix}"] == 3:
            saw_floor = True
        if sample[f"down_state{v_suffix}"] == 5:
            saw_wake = True
        if damage_state is None and sample[f"hp{v_suffix}"] < initial_hp:
            damage_state = sample[f"down_state{v_suffix}"]
            damage_hp = sample[f"hp{v_suffix}"]
        # Keep a normal held through floor/get-up/wake.  The native contact
        # path must reject it while the defender is down, proving no OTG
        # damage without writing game memory or using a test hook.
        attacker_keys = ["y"] if sample[f"down_state{v_suffix}"] in (3, 4, 5) else []
        if first_down is not None and saw_wake and sample[f"down_state{v_suffix}"] == 0:
            break
        drive(e, attacker, attacker_keys)
    check(first_down is not None, f"P{v_suffix} enters a downed state after P{a_suffix} throw", {
        "attacker": attacker, "samples": samples,
    })
    check(all(0 <= sample[f"down_state{v_suffix}"] <= 5 for sample in samples),
          "throw down-state telemetry stays within 0..5", {
              "attacker": attacker,
              "states": sorted(set(sample[f"down_state{v_suffix}"] for sample in samples)),
          })
    states = {sample[f"down_state{v_suffix}"] for sample in samples}
    check({1, 2, 3, 4, 5}.issubset(states),
          "throw visits lift, flight, floor, get-up, and wake states", {
              "attacker": attacker, "states": sorted(states),
          })
    if damage_state is not None:
        check(damage_state >= 3, "throw damage waits until victim ground impact", {
            "attacker": attacker, "damage_state": damage_state,
        })
    check(saw_floor, "throw reaches a grounded floor state before wake", {
        "attacker": attacker, "states": sorted(states),
    })
    if damage_hp is not None:
        check(all(sample[f"hp{v_suffix}"] == damage_hp
                  for sample in samples
                  if sample[f"down_state{v_suffix}"] in (3, 4, 5)
                  and sample[f"hp{v_suffix}"] <= damage_hp),
              "downed victim rejects subsequent OTG damage", {
                  "attacker": attacker, "damage_hp": damage_hp,
              })
    pending = [sample for sample in samples
               if sample[f"pending_throw_damage{v_suffix}"] or
               sample[f"pending_throw_damage{a_suffix}"]]
    check(pending and any(
        sample[f"throw_owner{v_suffix}"] == attacker or
        sample[f"throw_owner{a_suffix}"] == attacker for sample in pending),
          "throw telemetry exposes delayed damage and its owner", {
              "attacker": attacker, "pending": pending[:5],
          })
    check(any(sample[f"throw_victim{a_suffix}"] == victim for sample in pending),
          "throw telemetry identifies the distinct victim role", {
              "attacker": attacker, "victim": victim,
              "pending": pending[:5],
          })
    return {"attacker": attacker, "victim": victim, "samples": samples,
            "first_down": first_down, "damage_state": damage_state,
            "damage_hp": damage_hp}


def check_throw_knockdown_wake() -> None:
    """Verify distinct throw roles, bounded wake, no OTG, pause, and reset."""

    e = boot(1)
    try:
        result = _observe_throw(e, 0)
    finally:
        e.close()

    # Use a fresh throw for the timing-sensitive part.  The complete probe
    # above deliberately runs through wake; this one pauses on the floor and
    # captures a fresh UP edge during the six-tick wake state.
    e = boot(1)
    try:
        _close_for_throw(e)
        before = trace(e)
        forward = "right" if before["face1"] else "left"
        drive(e, 0, [forward, 'x'], 3)
        paused_checked = False
        queued = False
        queued_trace: dict[str, int] | None = None
        wake_pause_checked = False
        woke = False
        woke_trace: dict[str, int] | None = None
        for _ in range(160):
            sample = trace(e)
            down = sample["down_state2"]
            if down == 3 and not paused_checked:
                # START is edge sampled by the SNES core.  A one-frame tap
                # can land in the same hitstop poll that produced FLOOR;
                # use the established three-frame pulse so the pause edge
                # is observed without advancing the paused simulation.
                e.run(3, p1=["start"])
                paused = trace(e)
                e.run(20)
                still = trace(e)
                check(paused["paused"] == 1 and
                      still["down_state2"] == paused["down_state2"] and
                      still["down_tick2"] == paused["down_tick2"],
                      "pause freezes downed-state timing", {
                          "paused": paused, "still": still,
                      })
                e.run(3, p1=["start"])
                paused_checked = True
            elif down == 5 and not queued:
                e.run(1, p2=["up"])
                queued_trace = trace(e)
                queued = queued_trace["wake_jump2"] > 0
                e.run(1, p2=[])
            elif down == 5 and queued and not wake_pause_checked:
                e.run(3, p1=["start"])
                wake_paused = trace(e)
                e.run(20)
                wake_still = trace(e)
                check(wake_paused["paused"] == 1 and
                      wake_still["down_state2"] == wake_paused["down_state2"] and
                      wake_still["down_tick2"] == wake_paused["down_tick2"] and
                      wake_still["wake_jump2"] == wake_paused["wake_jump2"],
                      "pause freezes wake timing and buffered jump age", {
                          "paused": wake_paused, "still": wake_still,
                      })
                e.run(3, p1=["start"])
                wake_pause_checked = True
            elif down == 0 and queued:
                woke = signed16(sample["y2"]) < 0
                if woke:
                    woke_trace = sample
                if woke:
                    break
            e.run(1)
        check(paused_checked, "pause probe reaches the downed floor state", trace(e))
        check(queued, "wake-up jump edge is captured during the wake state", {
            "queued": queued_trace,
        })
        check(wake_pause_checked, "pause probe freezes a queued wake edge", trace(e))
        check(woke, "wake-up buffer becomes actionable after get-up", trace(e))
        if woke_trace is not None:
            invuln = [woke_trace["invuln2"]]
            for _ in range(3):
                e.run(1)
                invuln.append(trace(e)["invuln2"])
            check(invuln == [4, 3, 2, 1],
                  "wake transition grants exactly four free invulnerability ticks", {
                      "trace": woke_trace, "invuln": invuln,
                  })
    finally:
        e.close()

    e = boot(1)
    try:
        mirrored = _observe_throw(e, 1)
        check(mirrored["victim"] == 0 and mirrored["first_down"] is not None,
              "P2 mirrored throw produces an independent victim sequence", mirrored)
    finally:
        e.close()

    # Training reset must clear an active downed state and delayed throw data.
    e = boot(2)
    try:
        _close_for_throw(e)
        before = trace(e)
        drive(e, 0, ["right", 'x'], 3)
        down = None
        for _ in range(80):
            sample = trace(e)
            if sample["down_state2"]:
                down = sample
                break
            e.run(1)
        check(down is not None, "Training probe reaches a downed victim", down)
        e.run(3, p1=["select"])
        e.run(12)
        reset = trace(e)
        check(reset["down_state1"] == 0 and reset["down_state2"] == 0 and
              reset["pending_throw_damage1"] == 0 and
              reset["pending_throw_damage2"] == 0 and
              reset["throw_owner1"] == 255 and reset["throw_owner2"] == 255 and
              reset["throw_victim1"] == 255 and reset["throw_victim2"] == 255,
              "Training reset clears knockdown and delayed throw state", {
                  "before": before, "down": down, "reset": reset,
              })
    finally:
        e.close()


def check_simultaneous_throw_tech() -> None:
    """Attempt the symmetric throw edge and reject one-sided damage."""

    e = boot(1)
    try:
        _close_for_throw(e)
        initial = trace(e)
        f1 = "right" if initial["face1"] else "left"
        f2 = "right" if initial["face2"] else "left"
        for _ in range(4):
            e.run(1, p1=[f1, 'x'], p2=[f2, 'x'])
        e.run(20)
        after = trace(e)
        check(after["hp1"] == initial["hp1"] and after["hp2"] == initial["hp2"] and
              after["down_state1"] == 0 and after["down_state2"] == 0,
              "simultaneous throw inputs resolve without one-sided damage", {
                  "initial": initial, "after": after,
              })
    finally:
        e.close()

    # A throw and a normal on the same contact frame resolve in favor of the
    # throw.  This is a separate case from symmetric throw tech: it must show
    # one concrete action-9/down-state outcome rather than merely no damage.
    e = boot(1)
    try:
        _close_for_throw(e)
        initial = trace(e)
        f1 = "right" if initial["face1"] else "left"
        for _ in range(4):
            e.run(1, p1=[f1, 'x'], p2=["y"])
        resolved = trace(e)
        check(resolved["down_state2"] in (1, 2, 3, 4, 5) and
              resolved["hp1"] == initial["hp1"],
              "grounded throw beats a simultaneous normal", {
                  "initial": initial, "resolved": resolved,
              })
    finally:
        e.close()

    # A rush-family special remains a grounded, moving action.  This catches
    # the close-contact path accidentally treating its down+P edge as a throw
    # or losing horizontal motion at the floor.
    e = boot(1, fighter=2, fighter2=1)
    try:
        _close_for_throw(e)
        initial = trace(e)
        drive(e, 0, ["down", 'y'], 3)
        samples = []
        for _ in range(18):
            sample = trace(e)
            samples.append(sample)
            e.run(1)
        check(any(sample["action1"] == 7 and signed16(sample["y1"]) == 0
                  for sample in samples),
              "rush special starts from the grounded state", {
                  "initial": initial, "samples": samples,
              })
        check(max(sample["x1"] for sample in samples) - initial["x1"] >= 8,
              "grounded rush special carries horizontal motion", {
                  "initial_x": initial["x1"],
                  "samples": samples,
              })
    finally:
        e.close()


def check_throw_startup_escape() -> dict[str, object]:
    """A jump begun on throw startup makes the target ineligible.

    Both controller edges are sampled on the same frame: P1 commits the
    forward+L throw input while P2 presses UP.  The thrower may remain in its
    native action-9 startup/recovery sequence, but the airborne target must
    stay free and unharmed.  This exercises the compiler-safe ``enemy->y``
    gate in both action selection and contact resolution.
    """

    e = boot(1)
    try:
        _close_for_throw(e)
        initial = trace(e)
        forward = "right" if initial["face1"] else "left"
        initial_hp = (initial["hp1"], initial["hp2"])

        # Keep both edges live for the poll window; the P2 UP edge starts the
        # jump before the contact snapshot can accept a grounded throw.
        e.run(3, p1=[forward, 'x'], p2=["up"])
        samples: list[dict[str, int]] = []
        for _ in range(64 if DELIBERATE_PACING else 48):
            sample = trace(e)
            samples.append(sample)
            e.run(1)

        throw_active = [sample for sample in samples if sample["action1"] == 9]
        airborne_throw = [sample for sample in throw_active
                          if signed16(sample["y2"]) < 0 and
                          sample["down_state2"] == 0]
        grounded_free = [sample for sample in samples
                         if signed16(sample["y2"]) == 0 and
                         sample["down_state2"] == 0 and
                         sample["action1"] == 0]
        check(bool(throw_active),
              "P1 commits the native throw action while P2 jumps", {
                  "initial": initial, "samples": samples,
              })
        check(bool(airborne_throw),
              "airborne P2 cannot be grabbed during P1 throw startup", {
                  "initial": initial, "airborne_throw": airborne_throw,
              })
        check(all(sample["down_state2"] == 0 for sample in samples) and
              not any(sample["connected1"] == 2 for sample in samples),
              "escaped throw leaves P2 in DOWN_FREE without throw contact", {
                  "states": sorted(set(sample["down_state2"] for sample in samples)),
                  "contacts": sorted(set(sample["connected1"] for sample in samples)),
              })
        check(all((sample["hp1"], sample["hp2"]) == initial_hp
                  for sample in samples),
              "escaped throw causes no damage to either fighter", {
                  "initial_hp": initial_hp,
                  "hp": sorted(set((sample["hp1"], sample["hp2"])
                                   for sample in samples)),
              })
        check(bool(grounded_free),
              "escaped throw returns both fighters to grounded free state", {
                  "last": samples[-1],
              })
        return {
            "initial": initial,
            "throw_frames": len(throw_active),
            "airborne_throw_frames": len(airborne_throw),
            "grounded_free": bool(grounded_free),
        }
    finally:
        e.close()


def check_projectile_interrupts_throw() -> dict[str, object]:
    """A live projectile cancels a pending throw without delayed damage.

    This uses the deterministic late-special contact from the native input
    path: P2 (Ivo, the default local-versus opponent) reaches four ticks before
    its actual projectile release while P1 closes with heavy punch. The contact resolver
    must release the victim's pending throw before LIFT becomes observable,
    then let the victim finish its bounded flight.  The wave may hurt P1, but
    the cancelled throw must never damage P2 at the later ground impact.
    """

    e = boot(1)
    try:
        close_players(e)
        drive(e, 1, ["down"], 3)
        drive(e, 1, ["down", 'y'], 3)

        # Ivo's projectile startup is long enough for a late throw edge to
        # overlap it.  Keep the controller released between samples so this
        # probe observes the engine's actual action/tick schedule.
        startup: list[dict[str, int]] = []
        ready: dict[str, int] | None = None
        for _ in range(20):
            sample = trace(e)
            startup.append(sample)
            if (sample["action2"] == 7 and
                    sample["anim_tick2"] == sample["special_startup2"] - 4):
                ready = sample
                break
            drive(e, 1, [])
        check(ready is not None,
              "P2 projectile reaches the late startup tick for throw interruption", {
                  "startup": startup,
                  "trace": ready or trace(e),
              })
        if ready is None:
            return {"status": "unreached", "startup": startup}

        before = ready
        forward = "right" if before["face1"] else "left"
        samples: list[dict[str, int]] = []
        # The five-tick heavy edge is long enough for Snes9x's poll phase but
        # remains a controller-only contact attempt, not a state mutation.
        for _ in range(5):
            drive(e, 0, [forward, 'x'])
            samples.append(trace(e))

        # Keep collecting until the released victim returns to FREE, proving
        # both that FLIGHT is bounded and that no delayed throw damage appears
        # after the wave/throw contact snapshot.
        free: dict[str, int] | None = None
        for _ in range(120):
            sample = trace(e)
            samples.append(sample)
            if sample["down_state2"] == 0:
                free = sample
                break
            drive(e, 0, [])

        flight = [sample for sample in samples if sample["down_state2"] == 2]
        released = [sample for sample in flight
                    if sample["pending_throw_damage2"] == 0 and
                    sample["throw_owner2"] == 255]
        check(bool(flight),
              "projectile contact releases the victim into bounded FLIGHT", {
                  "before": before, "samples": samples,
              })
        check(bool(released),
              "projectile cancellation clears pending throw ownership", {
                  "before": before, "flight": flight,
              })
        check(any(sample["hp1"] < before["hp1"] and
                  sample["action1"] == 0 for sample in released),
              "projectile still resolves its hit on the thrower", {
                  "before": before, "released": released,
              })
        check(all(sample["hp2"] == before["hp2"] for sample in samples),
              "cancelled throw never applies delayed victim damage", {
                  "before_hp2": before["hp2"],
                  "states": sorted(set(sample["down_state2"] for sample in samples)),
                  "samples": samples,
              })
        check(free is not None,
              "projectile-released victim returns to FREE within a bounded flight", {
                  "free": free, "last": samples[-1] if samples else trace(e),
              })
        return {
            "before": {key: before[key] for key in
                       ("frame", "hp1", "hp2", "action2", "anim_tick2")},
            "states": sorted(set(sample["down_state2"] for sample in samples)),
            "flight_samples": len(flight),
            "free_frame": free["frame"] if free is not None else None,
        }
    finally:
        e.close()


def check_attack_knockdowns() -> None:
    """Real sweep, uppercut, and rising hits enter the down-state machine."""

    cases = (
        (0, ["down", 'a'], "crouching heavy sweep"),
        (0, ["down", 'x'], "uppercut"),
        (5, ["down", 'y'], "rising special"),
    )
    for fighter, keys, label in cases:
        e = boot(1, fighter=fighter, fighter2=1)
        try:
            close_players(e)
            initial = trace(e)
            drive(e, 0, keys, 3)
            samples: list[dict[str, int]] = []
            for _ in range(100):
                sample = trace(e)
                samples.append(sample)
                if sample["down_state2"]:
                    break
                e.run(1)
            check(any(event_field(sample, "connected", 0) == 2
                      for sample in samples) or
                  any(sample["down_state2"] for sample in samples),
                  label + " produces a real contact", {
                      "fighter": fighter, "initial": initial,
                      "samples": samples,
                  })
            check(any(sample["down_state2"] in (1, 2, 3, 4, 5)
                      for sample in samples),
                  label + " real hit enters bounded knockdown", {
                      "fighter": fighter, "states": sorted(
                          set(sample["down_state2"] for sample in samples)),
                  })
        finally:
            e.close()

    # A guarded sweep is a blocked contact and must never launch the defender.
    e = boot(1, fighter=0, fighter2=1)
    try:
        close_players(e)
        drive(e, 0, ["down", 'a'], 3)
        guarded: list[dict[str, int]] = []
        for _ in range(40):
            # Keep the defender stationary at close range while crouch
            # guarding; a back-only hold can walk out of the sweep's reach
            # before its active tick and turn this into a movement test.
            e.run(1, p2=["down", "right"])
            sample = trace(e)
            guarded.append(sample)
            if sample["connected1"] == 1:
                break
        check(any(sample["connected1"] == 1 for sample in guarded),
              "crouch-guarded sweep produces blocked contact", guarded)
        check(not any(sample["down_state2"] for sample in guarded),
              "blocked sweep does not cause knockdown", guarded)
    finally:
        e.close()


def check_down_floor_input_guard() -> dict[str, object]:
    """Downed input cannot act, jump, or re-hit at a close floor position.

    Lars's long heavy reach makes the OTG portion non-vacuous: after his
    uppercut launches P2, P1 waits until its action is free, then holds Down+A
    while P2 is still down.  The actual active frame must overlap a downed
    state with physical strike/body overlap without changing P2 HP.
    """

    e = boot(1, fighter=11, fighter2=0)
    try:
        if DELIBERATE_PACING:
            # Earn a corner position through both physical pads. This keeps
            # launch drift inside real sweep reach; no geometry is widened.
            e.run(200,p2=['right'])
            for _ in range(500):
                s=trace(e)
                if s['x2']-s['x1']<32*16:break
                e.run(1,p1=['right'])
        else:
            close_players(e)
        initial = trace(e)
        launch_face: int | None = None
        impact_hp: int | None = None
        heavy_at: int | None = None
        samples: list[dict[str, int]] = []
        active: list[dict[str, int]] = []
        floor: list[dict[str, int]] = []
        rise: list[dict[str, int]] = []
        states: set[int] = set()
        violations: list[dict[str, object]] = []

        drive(e, 0, ["down", 'x'], 3)
        for index in range(120):
            sample = trace(e)
            down = sample["down_state2"]
            states.add(down)
            if down:
                samples.append(sample)
                if launch_face is None:
                    launch_face = sample["face2"]
                    impact_hp = sample["hp2"]
                if sample["hp2"] != impact_hp:
                    violations.append({"kind": "hp", "sample": sample})
                if sample["action2"] != 0 or sample["jump_buffer2"] != 0:
                    violations.append({"kind": "victim_input", "sample": sample})
                down_y = signed16(sample["y2"])
                if (down in (1, 2) and down_y >= 0) or (down in (3, 4, 5) and
                                                        down_y != 0):
                    violations.append({"kind": "down_y", "sample": sample})
                if down in (1, 2, 3) and sample["face2"] != launch_face:
                    violations.append({"kind": "launch_face", "sample": sample})
                if down == 3:
                    floor.append(sample)
                if down == 4:
                    rise.append(sample)
                if heavy_at is not None and sample["action1"] == 6 and sample["anim_frame1"] == 8:
                    strike = world(contact_poses()[11][8][2], sample["x1"],
                                   signed16(sample["y1"]), sample["face1"])
                    body = body_regions(sample, "2")
                    active.append({
                        "frame": sample["frame"],
                        "down_state2": down,
                        "distance": abs(sample["x1"] - sample["x2"]),
                        "hp2": sample["hp2"],
                        "strike": strike, "body": body,
                        "physical_overlap": any(overlap(strike, band) for band in body),
                    })
            approach = []
            if heavy_at is None and down and sample["y1"] == 0 and sample["action1"] == 0:
                if DELIBERATE_PACING and abs(sample['x1']-sample['x2']) > 32*16:
                    approach = ['right' if sample['x1']<sample['x2'] else 'left']
                else:
                    heavy_at = index
            p1 = ['down', 'a'] if heavy_at is not None and heavy_at <= index < heavy_at + 4 else approach
            p2 = ["up", "y"] if launch_face is not None else []
            e.run(1, p1=p1, p2=p2)

        check(bool(samples),
              "close launcher produces a trace-visible down-state sequence", {
                  "initial": initial, "states": sorted(states),
              })
        check({2, 3, 4, 5}.issubset(states),
              "downed control probe reaches flight, floor, rise, and wake", {
                  "states": sorted(states),
              })
        check(bool(floor),
              "downed victim reaches a grounded FLOOR state", {
                  "states": sorted(states), "floor": floor[:3],
              })
        if floor:
            check(any(any(overlap(
                          world(contact_poses()[11][8][2], sample["x1"], 0, sample["face1"]),
                          band) for band in body_regions(sample, "2")) for sample in floor),
                  "FLOOR input probe has physical overlap with Lars's sweep strike", {
                      "floor": floor[:4],
                  })
        check(not violations,
              "held UP+Y cannot act, jump, re-hit, or flip a downed victim", {
                  "violations": violations[:8],
                  "sample_count": len(samples),
              })
        check(bool(active),
              "attacker's actual heavy active frame overlaps a downed victim", {
                  "active": active,
                  "states": sorted(states),
              })
        check(any(sample["physical_overlap"] for sample in active),
              "downed victim physically overlaps the actual active heavy strike", {
                  "active": active,
              })
        check(impact_hp is not None and all(sample["hp2"] == impact_hp
                                            for sample in active),
              "downed victim takes no OTG damage from the active heavy", {
                  "impact_hp": impact_hp, "active": active,
              })
        check(bool(rise),
              "downed victim reaches RISE before wake", {
                  "states": sorted(states),
              })
        if rise and launch_face is not None:
            expected_face = 1 if rise[0]["x2"] < rise[0]["x1"] else 0
            check(rise[0]["face2"] == expected_face and
                  rise[0]["face2"] != launch_face,
                  "victim facing updates only when RISE begins", {
                      "launch_face": launch_face,
                      "rise": rise[0],
                      "expected_face": expected_face,
                  })
        return {
            "states": sorted(states), "launch_face": launch_face,
            "impact_hp": impact_hp, "floor_frames": len(floor),
            "active": active, "rise_frame": rise[0]["frame"] if rise else None,
        }
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
        for _ in range(70):
            sample = trace(e)
            y = signed16(sample["y1"])
            lower,upper=(-19,-15) if DELIBERATE_PACING else (-24,-20)
            if (y < 0 and y > previous_y and
                    lower * 16 <= y <= upper * 16):
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


def _cross_up_contact_case(port: int, key: str = "a", *, guard: str = "",
                           delay: int = 0, front: bool = False,
                           corner: bool = False, trade: bool = False) -> dict[str, object]:
    """Boot mirrored local play and supply only real controller edges.

    Guard is applied just before startup ends: holding back throughout the
    flight walks out of the short rear box and would only prove a whiff.
    The low-guard arc starts slightly farther away so the active kick actually
    overlaps the shorter crouching body before it leaves the rear box.
    """

    from test_stages import oam_entry, oam_memory

    e = boot(1, fighter=0, fighter2=0)
    a, d = str(port + 1), str(2 - port)
    sign = 1 if port == 0 else -1
    forward, back = ("right", "left") if port == 0 else ("left", "right")
    label = f"P{a} air {key.upper()} " + (
        "front corner" if corner else "front" if front else
        f"rear {guard or 'neutral'} delay{delay}") + (" trade" if trade else "")
    fields = ("frame", "x1", "x2", "y1", "y2", "face1", "face2",
              "fighter_id1", "fighter_id2",
              "action1", "action2", "anim_tick1", "anim_tick2", "anim_frame1",
              "anim_frame2", "air_action1", "air_action2", "connected1",
              "connected2", "hp1", "hp2", "hurt1", "hurt2", "guard1", "guard2",
              "hitstop", "down_state1", "down_state2", "raw_keys1", "raw_keys2")

    def sample() -> dict[str, int]:
        state = trace(e)
        return {name: state[name] for name in fields}

    try:
        if corner:
            # The front kick's victim is at the outward wall. Both pad holds
            # reach it naturally; the contact and every hurt tick must clamp.
            e.run(320 if DELIBERATE_PACING else 180, p1=[forward], p2=[forward])
        approach_gap = (44 if guard=='low' else 40) if DELIBERATE_PACING else (40 if front and not corner else 36 if guard == "low" else 24)
        for _ in range(180):
            state = trace(e)
            if abs(state["x1"] - state["x2"]) <= approach_gap * 16:
                break
            drive(e, port, [forward])
        e.run(3)
        initial = sample()
        check(initial[f"face{a}"] == (1 if port == 0 else 0) and
              initial[f"hp{d}"] == 128, label + " starts healthy facing forward", initial)
        drive(e, port, ["up"] if front or trade else ["up", forward])
        rows = [sample()]
        attack_sent = False
        trade_sent = False
        trade_age = 0
        countdown = delay
        contact_index = None
        effect = None
        for index in range(84):
            state = rows[-1]
            crossed = (state[f"x{a}"] - state[f"x{d}"]) * sign > 0
            attacker_keys: list[str] = []
            defender_keys: list[str] = []
            if not attack_sent and not trade and ((front and index >= 1) or (not front and crossed)):
                if countdown == 0:
                    attacker_keys = [key]
                    attack_sent = True
                else:
                    countdown -= 1
            if contact_index is None and crossed and state[f"anim_tick{a}"] >= (9 if DELIBERATE_PACING else 6):
                if guard == "old":
                    defender_keys = [forward]
                elif guard in ("new", "low"):
                    defender_keys = [back] + (["down"] if guard == "low" else [])
            # Ground A has three extra startup ticks. During the observed
            # descent supply its edge first, then air A three ticks later.
            # The front neutral-jump bracket keeps both drawn kicks in range
            # without locking a grounded normal away from a crossed target.
            if trade:
                if not trade_sent:
                    descending = (len(rows) > 1 and
                                  signed16(state[f"y{a}"]) > signed16(rows[-2][f"y{a}"]))
                    if descending and signed16(state[f"y{a}"]) >= -53 * 16:
                        defender_keys = ["a"]
                        trade_sent = True
                else:
                    trade_age += 1
                    if trade_age == 3:
                        attacker_keys = [key]
                        attack_sent = True
            e.run(1, **{f"p{a}": attacker_keys, f"p{d}": defender_keys})
            rows.append(sample())
            if contact_index is None and rows[-1][f"connected{a}"]:
                contact_index = len(rows) - 1
                effect = oam_entry(oam_memory(e), 69)

        action = {"y": 1, "x": 3, "b": 4, "a": 5}[key]
        active_frame = 50 if action < 4 else 53
        active = [row for row in rows if row[f"action{a}"] == action and
                  row[f"anim_frame{a}"] == active_frame]
        evidence = {"initial": initial, "active": active, "rows": rows}
        # A trade cancels both actions before the frame is rendered. The
        # previous startup tick plus both contacts is the observable evidence;
        # requiring frame 53 here would change the game's trade semantics.
        trade_startup = (trade and contact_index is not None and
                         rows[contact_index - 1][f"anim_tick{a}"] == (9 if DELIBERATE_PACING else 6))
        check(attack_sent and (bool(active) or trade_startup),
              label + " exercises an active airborne normal", evidence)
        airborne = [row for row in rows if signed16(row[f"y{a}"]) < 0]
        check(all(row[f"face{a}"] == initial[f"face{a}"] for row in airborne),
              label + " locks takeoff facing throughout flight", airborne)
        check(all(24 * 16 <= row[f"x{side}"] <= 232 * 16
                  for row in rows for side in (1, 2)), label + " stays inside both walls", rows)
        check(all(row[f"down_state{d}"] == 0 for row in rows),
              label + " never changes the medium-kick knockdown contract", rows)

        # Reflect the ordinary visible strike behind the locked facing to
        # bracket a directional rejection. A distant or vertically separated
        # target would make that rejection vacuous. Actual rear A contact is
        # checked separately against its dedicated short rear rectangle.
        if not front and not trade:
            geometry = []
            for row in active:
                gap = (row[f"x{a}"] - row[f"x{d}"]) * sign
                strike = world(contact_poses()[0][active_frame][2], row[f"x{a}"],
                               signed16(row[f"y{a}"]), 1-row[f"face{a}"])
                if gap > 0 and any(overlap(strike, body) for body in body_regions(row, d)):
                    geometry.append(row)
            check(bool(geometry), label + " has rear active overlap inside the reflected visible front strike", evidence)

        should_hit = key == "a" and delay == 0
        if should_hit:
            check(contact_index is not None, label + " produces contact", evidence)
            assert contact_index is not None
            contact = rows[contact_index]
            previous = rows[contact_index - 1]
            blocked = guard == "new"
            away = sign if front else -sign
            recoil = 16 if blocked else 64
            physical = dict(previous)
            physical[f"x{a}"] = contact[f"x{a}"] - ((-sign if front else sign) * 64 if trade else 0)
            physical[f"y{a}"] = contact[f"y{a}"]
            physical[f"x{d}"] = (contact[f"x{d}"] + away*12 if corner else
                                   contact[f"x{d}"] - away*recoil)
            if corner and DELIBERATE_PACING:
                # Slower walking leaves a different 12.4 remainder at the
                # wall. Reconstruct the stationary victim BEFORE the clamp,
                # from the previous sample and the unchanged body separator.
                separate=(abs(previous[f'x{a}']-previous[f'x{d}'])<22*16 and
                          abs(signed16(contact[f'y{a}']))<50*16)
                physical[f'x{d}']=previous[f'x{d}']+away*(12 if separate else 0)
            physical[f"y{d}"] = contact[f"y{d}"]
            if guard == "low":
                physical[f"anim_frame{d}"] = 3
            if trade:
                physical[f"anim_frame{d}"] = 7
                physical[f"anim_frame{a}"] = 53
                ground_strike = world(contact_poses()[0][7][2], physical[f"x{d}"],
                                      0, physical[f"face{d}"])
                check(any(overlap(ground_strike, body) for body in body_regions(physical, a)),
                      label + " simultaneous grounded strike overlaps the active airborne body", {
                          "physical": physical, "strike": ground_strike,
                          "body": body_regions(physical, a)})
            strike = world(contact_poses()[0][53][2 if front else 3],
                           physical[f"x{a}"], signed16(physical[f"y{a}"]),
                           physical[f"face{a}"])
            center_gap = abs(physical[f"x{a}"] - physical[f"x{d}"])
            check(any(overlap(strike, body) for body in body_regions(physical, d)),
                  label + " real controller contact overlaps the visible strike and pose body", {
                      "physical": physical, "strike": strike,
                      "body": body_regions(physical, d)})
            check((trade_startup or contact[f"anim_frame{a}"] == 53) and signed16(contact[f"y{a}"]) < 0,
                  label + " contacts during the airkick active window", contact)
            if not front:
                check(center_gap <= 26 * 16, label + " uses at most 16px rear reach plus 10px body", center_gap)
            elif not corner:
                check(center_gap > 26 * 16,
                      label + " exercises front contact outside the rear-center cap", center_gap)
            check(contact[f"connected{a}"] == (1 if blocked else 2) and
                  contact[f"hp{d}"] == (127 if blocked else 113) and
                  contact[f"guard{d}"] == int(blocked) and
                  contact["hitstop"] == ((5 if blocked else 10) if DELIBERATE_PACING else (3 if blocked else 6)),
                  label + " preserves exact damage, guard classification and hitstop", contact)
            if guard:
                # Public raw pad bits prove these are actual old/new-back and
                # crouch-back samples rather than neutral defender hits.
                guard_keys = (0x100 if port == 0 else 0x200) if guard == "old" else (
                    0x200 if port == 0 else 0x100)
                if guard == "low":
                    guard_keys |= 0x400
                check(contact[f"raw_keys{d}"] == guard_keys,
                      label + " samples the intended real defender guard input", contact)
            check((contact[f"x{d}"] - previous[f"x{d}"]) * away >= (0 if corner else 1),
                  label + " immediate recoil points away from the attacker", {
                      "previous": previous, "contact": contact})
            # Effects are constructed before the final corner clamp. In a
            # trade the second snapshot contact owns the single effect slot.
            fx_victim = "1" if trade else d
            fx_direction = (-1 if front else 1) if trade else away
            fx_center = ((contact[f"x{fx_victim}"] + away * (64 + 12)) >> 4
                         if corner else contact[f"x{fx_victim}"] >> 4)
            if corner and DELIBERATE_PACING:
                fx_center=(physical[f'x{d}']+away*64)>>4
            expected_fx = (fx_center + (-12 if fx_direction > 0 else 6) - 8) & 511
            check(effect is not None and effect["x"] == expected_fx,
                  label + " native impact effect appears on the contact side", {"effect": effect, "expected_x": expected_fx})
            frozen = rows[contact_index + 1:contact_index + 1 + contact["hitstop"]]
            check(len(frozen) == contact["hitstop"] and
                  all(all(row[name] == contact[name] for name in
                          ("x1", "x2", "y1", "y2", "hurt1", "hurt2", "anim_tick1", "anim_tick2"))
                      for row in frozen), label + " hitstop freezes contact physics and animation", frozen)
            drift = [(before, after) for before, after in zip(rows[contact_index:], rows[contact_index + 1:])
                     if before["hitstop"] == 0 and before[f"hurt{d}"] > 0 and not before[f"guard{d}"]]
            if not blocked:
                def eased_step(remaining):
                    return 2 * (16 if remaining >= 12 else 12 if remaining >= 8
                                else 8 if remaining >= 4 else 4)
                check(bool(drift) and all((after[f"x{d}"] - before[f"x{d}"]) * away ==
                                         (0 if corner else eased_step(after[f"hurt{d}"]))
                                         for before, after in drift),
                      label + " every hurt tick recoils away through landing/action cancellation", drift)
                if trade:
                    check(contact["hp1"] == 113 and contact["hp2"] == 113 and
                          contact["connected1"] == 2 and contact["connected2"] == 2,
                          label + " preserves both simultaneous snapshot contacts", contact)
            if corner:
                wall = (232 if away > 0 else 24) * 16
                check(all(row[f"x{d}"] == wall for row in rows[contact_index:] if row[f"hurt{d}"]),
                      label + " contact and hurt drift clamp at the actual wall", rows[contact_index:])
        else:
            check(contact_index is None and all(row[f"hp{d}"] == 128 for row in rows),
                  label + " remains a directional/range whiff", evidence)
            if key == "a":
                check(all(abs(row[f"x{a}"] - row[f"x{d}"]) > 26 * 16 for row in active),
                      label + " rejects rear centers beyond 26px during active ticks", active)
        landed = rows[-1]
        expected_face = 1 if landed[f"x{a}"] < landed[f"x{d}"] else 0
        check(landed[f"y{a}"] == 0 and landed[f"action{a}"] == 0 and
              landed[f"air_action{a}"] == 0 and landed[f"face{a}"] == expected_face,
              label + " clears air action and restores positional facing after landing", landed)
        return {"label": label, "contact": rows[contact_index] if contact_index is not None else None,
                "effect": effect, "active": active, "landed": landed}
    finally:
        e.close()


def _grounded_cross_up_whiff(port: int, key: str) -> dict[str, object]:
    """Lock a grounded normal before the other controller jumps behind it."""

    e = boot(1, fighter=0, fighter2=0)
    jumper, attacker = str(port + 1), str(2 - port)
    sign = 1 if port == 0 else -1
    forward = "right" if port == 0 else "left"
    action = 5 if key == "a" else 3
    try:
        for _ in range(180):
            s = trace(e)
            if abs(s["x1"] - s["x2"]) <= 24 * 16:
                break
            drive(e, port, [forward])
        e.run(3)
        drive(e, port, ["up", forward])
        sent = False
        rows = []
        for _ in range(64):
            s = trace(e)
            relative = (s[f"x{jumper}"] - s[f"x{attacker}"]) * sign
            keys = []
            if not sent and -64 <= relative < 0:
                keys = [key]
                sent = True
            drive(e, 1 - port, keys)
            rows.append(trace(e))
        active_frame = 7 if key == "a" else 6
        rear_overlap = []
        for s in rows:
            if (s[f"action{attacker}"] != action or
                    s[f"anim_frame{attacker}"] != active_frame or
                    (s[f"x{jumper}"] - s[f"x{attacker}"]) * sign <= 0):
                continue
            strike = world(contact_poses()[0][active_frame][2],
                           s[f"x{attacker}"], signed16(s[f"y{attacker}"]),
                           1-s[f"face{attacker}"])
            if any(overlap(strike, body) for body in body_regions(s, jumper)):
                rear_overlap.append(s)
        label = f"P{attacker} grounded backward {key.upper()}"
        check(sent and bool(rear_overlap), label + " has reflected visible rear active overlap", rear_overlap or rows)
        check(all(s[f"face{attacker}"] == (0 if port == 0 else 1) and
                  s[f"air_action{attacker}"] == 0 for s in rear_overlap),
              label + " stays grounded with locked directional facing", rear_overlap)
        check(all(s[f"hp{jumper}"] == 128 and s[f"connected{attacker}"] == 0 for s in rows),
              label + " cannot use the airborne medium-kick exception", rear_overlap)
        return {"label": label, "overlap": rear_overlap}
    finally:
        e.close()


def check_cross_up_contacts() -> dict[str, object]:
    """Mirrored attacks, relative-back guard, short rear reach and recoil."""

    results: dict[str, object] = {}
    for port in (0, 1):
        cases = [("rear", {}), ("old-back", {"guard": "old"}),
                 ("new-back", {"guard": "new"}), ("low-back", {"guard": "low"}),
                 ("front", {"front": True}), ("far-rear", {"delay": 3 if DELIBERATE_PACING else 1}),
                 ("corner", {"front": True, "corner": True}),
                 ("trade", {"trade": True, "front": True})]
        for name, options in cases:
            results[f"p{port + 1}-{name}"] = _cross_up_contact_case(port, **options)
        for key in ("y", "x", "b"):
            # The short air jab's drawn fist needs one more falling tick to
            # overlap the standing body vertically in the mirrored bracket.
            results[f"p{port + 1}-rear-{key}"] = _cross_up_contact_case(
                port, key, delay=(3 if DELIBERATE_PACING else 1) if key == "y" else 0)
        for key in ("a", "x"):
            results[f"p{2 - port}-ground-{key}"] = _grounded_cross_up_whiff(port, key)
    return results


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


# CPU coverage deliberately stays bounded.  The arcade menu is the only
# supported way to select a CPU difficulty; the probes below use the roster
# relationship in the cartridge (CPU id = P1 id + 1) and never write RAM.
CPU_REPRESENTATIVES = (0, 2, 4, 5)
CPU_FAMILIES = {0: 0, 2: 1, 4: 2, 5: 3}


def _cpu_summary(sample: dict[str, int]) -> dict[str, int]:
    """Keep CPU report evidence compact while retaining the causal fields."""

    names = (
        "frame", "fighter_id1", "fighter_id2", "family2", "hp1", "hp2",
        "x1", "x2", "y1", "y2", "action1", "action2", "anim_frame1",
        "anim_frame2", "anim_tick1", "anim_tick2", "anim_state2", "raw_keys2",
        "wave1", "wave2", "guard2", "hurt2", "connected1", "down_state2",
        "down_tick2", "wake_jump2", "invuln2",
    )
    return {name: sample[name] for name in names if name in sample}


def _cpu_boot(cpu_id: int, difficulty: int, target_phase: int | None = None) -> tuple[Emulator, dict[str, int]]:
    """Boot arcade with one CPU representative, optionally phase-aligned."""

    fighter = (cpu_id - 1) % 12
    if target_phase is None:
        e = boot(0, fighter=fighter, difficulty=difficulty)
        return e, trace(e)

    calibration = boot(0, fighter=fighter, difficulty=difficulty)
    initial = trace(calibration)
    calibration.close()
    phase = (initial["frame"] + cpu_id * 13) % 97
    delay = (target_phase - phase) % 97
    e = boot(0, fighter=fighter, difficulty=difficulty,
             title_delay=delay)
    return e, trace(e)


def _cpu_live_segment(cpu_id: int, difficulty: int,
                      limit: int = 180) -> dict[str, object]:
    """Collect a live AI segment and stop before a round-end transition."""

    e, initial = _cpu_boot(cpu_id, difficulty)
    ticks = 0
    ended = False
    drops: list[dict[str, int]] = []
    down_violations: list[dict[str, int]] = []
    try:
        check(initial["mode"] == 0 and initial["screen"] == 3 and
              initial["intro"] == 0,
              "arcade CPU segment starts in live combat", _cpu_summary(initial))
        check(initial["fighter_id2"] == cpu_id and
              initial["family2"] == CPU_FAMILIES[cpu_id],
              "arcade CPU segment selects the requested fighter family", {
                  "requested": cpu_id, "sample": _cpu_summary(initial),
              })
        attempt = 0
        while ticks < limit:
            index = attempt
            attempt += 1
            before = trace(e)
            e.run(1, p1=["left", "down"])
            current = trace(e)
            # A KO/round transition is outside the live AI cadence window.
            if current["round_end"] or current["hp1"] == 0 or current["screen"] != 3:
                ended = True
                break
            delta = (current["frame"] - before["frame"]) & 0xffff
            if delta != 1:
                drops.append({
                    "index": index, "delta": delta,
                    "frame": current["frame"],
                    "action2": current["action2"],
                    "down_state2": current["down_state2"],
                })
            if current["down_state2"] and current["action2"]:
                down_violations.append({
                    "index": index, "frame": current["frame"],
                    "action2": current["action2"],
                    "down_state2": current["down_state2"],
                })
            ticks += 1
        return {
            "ticks": ticks, "drops": drops,
            "down_violations": down_violations,
            "ended": ended,
            "start_frame": initial["frame"],
            "end": _cpu_summary(trace(e)),
        }
    finally:
        e.close()


def check_cpu_matrix() -> dict[str, object]:
    """Run 600 live native ticks for every CPU family and difficulty."""

    results: dict[str, object] = {}
    for difficulty in (0, 1, 2):
        for cpu_id in CPU_REPRESENTATIVES:
            remaining = 600
            segments: list[dict[str, object]] = []
            # Start with the full 600-tick live window.  If the CPU actually
            # ends the round, reboot only then and count the remaining live
            # ticks in a new round; fixed-size restarts would repeatedly reuse
            # the same opening PRNG phase and hide cadence problems.
            for _ in range(8):
                if remaining <= 0:
                    break
                segment = _cpu_live_segment(cpu_id, difficulty, remaining)
                segments.append(segment)
                remaining -= int(segment["ticks"])
                if int(segment["ticks"]) == 0 or not segment["ended"]:
                    break
            key = f"d{difficulty}-cpu{cpu_id:02}"
            total = 600 - remaining
            result = {
                "difficulty": difficulty, "cpu_id": cpu_id,
                "family": CPU_FAMILIES[cpu_id],
                "ticks": total, "segments": segments,
                "nonunit_steps": [drop for segment in segments
                                   for drop in segment["drops"]],
                "down_violations": [violation for segment in segments
                                     for violation in segment["down_violations"]],
            }
            check(total == 600 and not result["nonunit_steps"],
                  f"CPU d{difficulty} fighter {cpu_id} advances 600 live ticks",
                  {**result, "segments": [
                      {**segment, "end": segment["end"]}
                      for segment in segments
                  ]})
            check(not result["down_violations"],
                  f"CPU d{difficulty} fighter {cpu_id} has no active downed state",
                  result)
            results[key] = result
    return results


def _capture_cpu_special(cpu_id: int, difficulty: int,
                         target_phase: int, keys_fn, limit: int = 100,
                         require_active: bool = True) -> dict[str, object]:
    """Capture one CPU special from controller-only spacing inputs."""

    e, initial = _cpu_boot(cpu_id, difficulty, target_phase)
    samples: list[dict[str, int]] = []
    try:
        for index in range(limit):
            sample = trace(e)
            samples.append(sample)
            e.run(1, p1=keys_fn(index, sample))
        family = CPU_FAMILIES[cpu_id]
        active = [sample for sample in samples if sample["action2"] == 7]
        if require_active:
            check(bool(active),
                  f"CPU d{difficulty} fighter {cpu_id} manifests its special", {
                      "initial": _cpu_summary(initial),
                      "active": [_cpu_summary(sample) for sample in active[:8]],
                  })
            check(all(sample["family2"] == family for sample in active),
                  f"CPU fighter {cpu_id} special reports its family",
                  [_cpu_summary(sample) for sample in active[:8]])
        else:
            check(all(sample["family2"] == family for sample in samples),
                  f"CPU fighter {cpu_id} far-window trace keeps its family",
                  [_cpu_summary(sample) for sample in samples[:8]])
        return {"initial": initial, "active": active,
                "wave": [sample for sample in samples if sample["wave2"]],
                "samples": samples}
    finally:
        e.close()


def _capture_cpu_approach(difficulty: int) -> dict[str, object]:
    """Bring a CPU into the documented 29..46px neutral approach interval."""

    e, initial = _cpu_boot(2, difficulty)
    try:
        for index in range(240):
            sample = trace(e)
            distance = abs(sample["x1"] - sample["x2"]) / 16
            if 29 <= distance <= 46 and not sample["action2"] and not sample["y2"]:
                after: list[dict[str, int]] = []
                e.run(1)
                after.append(trace(e))
                # A personality may choose a normal on this decision tick.
                # Find an actual neutral approach decision, rather than
                # requiring every tick in the band to override its tempo.
                if abs(after[0]["x1"]-after[0]["x2"]) < abs(sample["x1"]-sample["x2"]):
                    for _ in range(2):
                        e.run(1)
                        after.append(trace(e))
                    return {"initial": initial, "start": sample,
                            "after": after, "index": index}
                continue
            forward = "right" if sample["x1"] < sample["x2"] else "left"
            back = "left" if sample["x1"] < sample["x2"] else "right"
            # Hold the measured band while a normal finishes; continuously
            # walking forward can cross the CPU before its neutral decision.
            e.run(1, p1=[forward] if distance > 46 else
                  ([back] if distance < 29 else [back, "down"]))
    finally:
        e.close()
    raise AssertionError(("CPU approach never enters 29..46px spacing",
                          {"difficulty": difficulty,
                           "initial": _cpu_summary(initial)}))


def check_cpu_special_spacing() -> dict[str, object]:
    """Exercise all four CPU families in their intended distance bands."""

    results: dict[str, object] = {}
    for difficulty in (0, 1, 2):
        # A rush or rising strike must never be selected from the wave band.
        # Keep this short window entirely beyond 95px so the negative result
        # proves the distance gate rather than a missing target condition.
        for cpu_id in (2, 5):
            far = _capture_cpu_special(
                cpu_id, difficulty, 0,
                lambda _index, _sample: ["left", "down"], 12,
                require_active=False)
            far_samples = far["samples"]
            far_distances = [abs(sample["x1"] - sample["x2"]) / 16
                             for sample in far_samples]
            check(bool(far_samples) and min(far_distances) > 95,
                  f"CPU d{difficulty} fighter {cpu_id} far-window stays beyond 95px",
                  {"distances_px": far_distances,
                   "samples": [_cpu_summary(sample)
                               for sample in far_samples[:8]]})
            check(not any(sample["action2"] == 7 for sample in far_samples),
                  f"CPU d{difficulty} fighter {cpu_id} never rushes/rises from far range",
                  [_cpu_summary(sample) for sample in far_samples])
            results[f"d{difficulty}-cpu{cpu_id:02}-far"] = {
                "family": CPU_FAMILIES[cpu_id],
                "min_distance_px": min(far_distances),
                "active_frames": sum(sample["action2"] == 7
                                      for sample in far_samples),
            }

        # Projectile and groundwave are only allowed from far spacing.  P1 is
        # held at the left clamp while the CPU approaches from the right.
        for cpu_id in (0, 4):
            captured = _capture_cpu_special(
                cpu_id, difficulty, 0,
                lambda _index, _sample: ["left", "down"], 70)
            active = captured["active"]
            first = active[0]
            check(abs(first["x1"] - first["x2"]) >= 95 * 16,
                  f"CPU d{difficulty} fighter {cpu_id} far special stays beyond 95px",
                  _cpu_summary(first))
            check(bool(captured["wave"]),
                  f"CPU d{difficulty} fighter {cpu_id} produces a live wave",
                  {"wave": [_cpu_summary(sample)
                            for sample in captured["wave"][:8]]})
            results[f"d{difficulty}-cpu{cpu_id:02}"] = {
                "family": CPU_FAMILIES[cpu_id],
                "first_distance_px": abs(first["x1"] - first["x2"]) / 16,
                "wave_frames": len(captured["wave"]),
            }

        # Rush begins only after the CPU has approached into its bounded
        # 45..90px band.  Raw X is fixed point; the minimum displacement is
        # intentionally modest so it catches a missing lunge without tying
        # the test to a particular sprite upload cadence.
        rush = _capture_cpu_special(
            2, difficulty, 58,
            lambda _index, sample: (
                ["down"] if sample["action2"] == 7 else
                ["right"] if abs(sample["x1"] - sample["x2"]) > 64 * 16 else
                ["left"] if abs(sample["x1"] - sample["x2"]) < 56 * 16
                else ["down"]), 240)
        first = rush["active"][0]
        samples = rush["samples"]
        active_index = next(index for index, sample in enumerate(samples)
                            if sample["action2"] == 7)
        end_index = next((index for index in range(active_index, len(samples))
                          if samples[index]["action2"] != 7), len(samples))
        rush_active = samples[active_index:end_index]
        # cpuKeys samples positions before updateFighter advances the actor.
        # The first visible action-7 trace is therefore one update late; use
        # the preceding decision sample for the spacing band.
        decision = samples[max(0, active_index - 1)]
        last_active = [sample for sample in rush_active
                       if sample["anim_tick2"] <=
                       sample["special_startup2"] + sample["special_active2"]][-1]
        decision_distance_px = abs(decision["x1"] - decision["x2"]) / 16
        displacement = abs(last_active["x2"] - decision["x2"])
        check(45 <= decision_distance_px < 95,
              f"CPU d{difficulty} rush starts in its near spacing band",
              {"decision": _cpu_summary(decision),
               "first_active": _cpu_summary(first),
               "distance_px": decision_distance_px})
        check(displacement >= 45 and displacement < 95 * 16,
              f"CPU d{difficulty} rush has bounded forward travel", {
                  "decision": _cpu_summary(decision),
                  "first": _cpu_summary(first),
                  "last": _cpu_summary(last_active),
                  "displacement_fixed": displacement,
                  "travel_px": displacement / 16,
              })
        results[f"d{difficulty}-cpu02"] = {
            "family": 1, "start_distance_px": decision_distance_px,
            "decision_distance_px": decision_distance_px,
            "displacement_fixed": displacement,
            "travel_px": displacement / 16,
        }

        approach = _capture_cpu_approach(difficulty)
        approach_start = approach["start"]
        approach_after = approach["after"]
        approach_distance = abs(approach_start["x1"] -
                                approach_start["x2"]) / 16
        check(29 <= approach_distance <= 46,
              f"CPU d{difficulty} enters the 29..46px approach interval",
              _cpu_summary(approach_start))
        check(bool(approach_after) and
              abs(approach_after[0]["x1"] - approach_after[0]["x2"]) <
              abs(approach_start["x1"] - approach_start["x2"]),
              f"CPU d{difficulty} closes the 29..46px approach gap", {
                  "start": _cpu_summary(approach_start),
                  "after": [_cpu_summary(sample)
                            for sample in approach_after],
              })
        results[f"d{difficulty}-approach"] = {
            "start_distance_px": approach_distance,
            "after_distance_px": [abs(sample["x1"] - sample["x2"]) / 16
                                   for sample in approach_after],
            "ticks_to_interval": approach["index"],
        }

        # Rising is sampled while P1 is airborne and inside the CPU's close
        # anti-air band.  The fresh jump edge is controller-only.
        # The slower approach can exceed the former 38-tick jump deadline.
        # Repeated real close jumps give every difficulty a visible target
        # across its ordinary 97-tick signature cadence, including intervening
        # fallible jabs/universal uppercuts. No future decision is inspected.
        def rising_keys(index, sample):
            forward = "right" if sample["x1"] < sample["x2"] else "left"
            if abs(sample["x1"] - sample["x2"]) / 16 > 40:
                return [forward]
            if DELIBERATE_PACING:
                # Fresh jump edges across the signature's established phase,
                # rather than a held UP that only creates one long arc.
                if 92 <= (sample['frame']+5*13)%97 <= 94:
                    return ['up']
                # Guard between attempts so an intervening normal
                # cannot KO the fixture before a later signature window.
                return ['left' if sample['x1'] < sample['x2'] else 'right', 'down']
            return ["up"]
        rising_phase=(12,4,16)[difficulty] if DELIBERATE_PACING else (16 if difficulty==1 else 0)
        rising = _capture_cpu_special(5, difficulty, rising_phase,
                                      rising_keys, 900 if DELIBERATE_PACING else 400)
        rising_active = rising["active"]
        airborne = [sample for sample in rising_active
                     if signed16(sample["y1"]) < 0]
        first = rising_active[0]
        check(bool(airborne),
              f"CPU d{difficulty} rising special reacts to an airborne target",
              {"first": _cpu_summary(first),
               "airborne": [_cpu_summary(sample) for sample in airborne[:8]]})
        check(abs(first["x1"] - first["x2"]) <=
              (first["special_reach2"] + 10) * 16,
              f"CPU d{difficulty} rising special stays in its anti-air range",
              _cpu_summary(first))
        results[f"d{difficulty}-cpu05"] = {
            "family": 3,
            "airborne_frames": len(airborne),
            "start_distance_px": abs(first["x1"] - first["x2"]) / 16,
        }
    return results


def check_cpu_natural_wave_specials() -> dict[str, object]:
    """Ensure wave/projectile CPUs use their signature move in neutral.

    This deliberately uses the ordinary arcade boot phase and neutral P1
    input.  It must not phase-align the global CPU cadence: a live action-7
    trace and its launched wave are the observable contract.  Action recovery
    may overlap the wave lifetime, so this check does not reject that normal
    overlap or attempt to count casts from it.
    """

    # The family IDs are projectile=0 and groundwave=2 in characters.h.  The
    # trace exposes wave_low2, where 0 is a projectile and 1 is a low wave.
    wave_cpus = (
        (0, 0), (1, 0), (4, 1), (6, 1),
        (8, 1), (9, 0), (11, 1),
    )
    results: dict[str, object] = {}
    for difficulty in (0, 1, 2):
        for cpu_id, expected_low in wave_cpus:
            e, initial = _cpu_boot(cpu_id, difficulty, None)
            samples: list[dict[str, int]] = []
            try:
                # Keep this window fixed and controller-only.  A round should
                # remain live for the opening neutral exchange; treating an
                # early result transition as a failure makes the regression
                # explainable instead of silently testing a menu/result page.
                for _ in range(180):
                    samples.append(trace(e))
                    e.run(1)
            finally:
                e.close()

            live = [sample for sample in samples
                    if sample["screen"] == 3 and not sample["round_end"]]
            actions = [sample for sample in live if sample["action2"] == 7]
            waves = [sample for sample in live if sample["wave2"]]
            correct_waves = [sample for sample in waves
                             if sample["wave_low2"] == expected_low]
            evidence = {
                "initial": _cpu_summary(initial),
                "live_ticks": len(live),
                "action7_frames": len(actions),
                "wave_frames": len(waves),
                "wave_low": sorted(set(sample["wave_low2"]
                                        for sample in waves)),
                "expected_low": expected_low,
                "action7": [_cpu_summary(sample) for sample in actions[:4]],
                "wave": [_cpu_summary(sample) for sample in waves[:4]],
            }
            prefix = f"CPU d{difficulty} fighter {cpu_id} natural wave"
            check(len(live) == 180,
                  f"{prefix} keeps the 180-tick live opening", evidence)
            check(bool(actions),
                  f"{prefix} emits a special without phase alignment",
                  evidence)
            check(bool(waves) and len(correct_waves) == len(waves),
                  f"{prefix} launches the correct wave family", evidence)
            results[f"d{difficulty}-cpu{cpu_id:02}"] = evidence
    return results


def check_cpu_lowwave_guard() -> dict[str, object]:
    """Normal/Hard CPU crouch-blocks a genuine incoming low wave."""

    results: dict[str, object] = {}
    for difficulty in (1, 2):
        e = boot(0, fighter=4, difficulty=difficulty)
        samples: list[dict[str, int]] = []
        try:
            drive(e, 0, ["down"], 3)
            drive(e, 0, ["down", 'y'], 3)
            for _ in range(80):
                sample = trace(e)
                samples.append(sample)
                e.run(1)
        finally:
            e.close()
        wave = [sample for sample in samples if sample["wave1"]]
        impact = [sample for sample in samples
                  if sample["hp2"] < 128 and sample["guard2"]]
        check(bool(wave), f"CPU d{difficulty} sees a genuine incoming low wave", {
            "wave": [_cpu_summary(sample) for sample in wave[:8]],
        })
        check(bool(impact) and all(sample["hp2"] >= 127 for sample in impact),
              f"CPU d{difficulty} low-wave guard takes at most one chip", {
                  "impact": [_cpu_summary(sample) for sample in impact[:8]],
              })
        back = 512 if impact and impact[0]["face2"] else 256
        guarded = [sample for sample in impact
                   if sample["raw_keys2"] & 1024 and sample["raw_keys2"] & back]
        check(bool(guarded),
              f"CPU d{difficulty} low-wave guard holds DOWN plus back",
              [_cpu_summary(sample) for sample in guarded[:8]])
        check(any(sample["anim_frame2"] == 3 and sample["anim_state2"] == 6
                  for sample in guarded),
              f"CPU d{difficulty} low-wave guard renders the crouched posture",
              [_cpu_summary(sample) for sample in guarded[:8]])
        results[f"difficulty-{difficulty}"] = {
            "wave_frames": len(wave),
            "impact": [_cpu_summary(sample) for sample in impact[:8]],
            "chip": 128 - min((sample["hp2"] for sample in impact), default=128),
        }
    return results


def check_cpu_wake() -> dict[str, object]:
    """Normal/Hard CPU wakes with its single UP edge after a knockdown."""

    induction_limit = 260
    observation_limit = 120
    results: dict[str, object] = {}
    for difficulty in (1, 2):
        e = boot(0, fighter=1, difficulty=difficulty)
        samples: list[dict[str, int]] = []
        down_seen = False
        down_index: int | None = None
        wake_index: int | None = None
        attack_pulses = 0
        scene_violations: list[dict[str, int]] = []
        try:
            close_players(e)
            # Induce exactly one knockdown within the historical bounded
            # window.  Once the victim enters any down state, stop all P1
            # attacks so a second hit or KO cannot hide wake behavior.
            for index in range(induction_limit):
                current = trace(e)
                distance = abs(current["x1"] - current["x2"])
                forward = "right" if current["x1"] < current["x2"] else "left"
                # Reclose after guarded recoil instead of attacking empty
                # space while the four-button CPU retreats from contact.
                keys = [forward] if distance > 28 * 16 else []
                if (index % 32 < 4 and distance < 45 * 16 and
                        not down_seen and current["action1"] == 0 and
                        current["down_state1"] == 0):
                    keys = ["down", "x"]
                    attack_pulses += 1
                e.run(1, p1=keys)
                sample = trace(e)
                if sample["screen"] != 3 or sample["round_end"] or \
                        sample["hp1"] == 0 or sample["hp2"] == 0:
                    scene_violations.append({
                        "phase": 0, "index": index,
                        "screen": sample["screen"],
                        "round_end": sample["round_end"],
                        "hp1": sample["hp1"], "hp2": sample["hp2"],
                    })
                if sample["down_state2"]:
                    down_seen = True
                    down_index = index
                    samples.append(sample)
                    break

            # Observe lift, flight, floor, get-up and wake separately.  This
            # phase sends no input, leaving the CPU's single wake edge as the
            # only source of the jump buffer.
            if down_seen:
                for observation in range(observation_limit):
                    sample = trace(e)
                    samples.append(sample)
                    if sample["screen"] != 3 or sample["round_end"] or \
                            sample["hp1"] == 0 or sample["hp2"] == 0:
                        scene_violations.append({
                            "phase": 1, "index": observation,
                            "screen": sample["screen"],
                            "round_end": sample["round_end"],
                            "hp1": sample["hp1"], "hp2": sample["hp2"],
                        })
                    if (wake_index is None and sample["down_state2"] == 5
                            and sample["down_tick2"] == 1):
                        wake_index = observation
                    if sample["down_state2"] == 0 and \
                            signed16(sample["y2"]) < 0:
                        break
                    e.run(1)
        finally:
            e.close()
        wake_edge = [sample for sample in samples
                     if sample["down_state2"] == 5 and sample["down_tick2"] == 1]
        airborne = [sample for sample in samples if signed16(sample["y2"]) < 0]
        check(down_seen, f"CPU d{difficulty} enters a real downed state",
              [_cpu_summary(sample) for sample in samples[:8]])
        check(not scene_violations,
              f"CPU d{difficulty} wake fixture stays in live non-KO FIGHT",
              {"violations": scene_violations,
               "down_index": down_index, "wake_index": wake_index})
        check(any(sample["raw_keys2"] & 2048 for sample in wake_edge),
              f"CPU d{difficulty} samples a single UP wake edge",
              [_cpu_summary(sample) for sample in wake_edge])
        check(any(sample["wake_jump2"] > 0 for sample in wake_edge),
              f"CPU d{difficulty} buffers the wake jump",
              [_cpu_summary(sample) for sample in wake_edge])
        check(bool(airborne), f"CPU d{difficulty} leaves wake airborne",
              [_cpu_summary(sample) for sample in airborne[:8]])
        results[f"difficulty-{difficulty}"] = {
            "wake_edge": [_cpu_summary(sample) for sample in wake_edge],
            "airborne": [_cpu_summary(sample) for sample in airborne[:8]],
            "down_seen": down_seen,
            "down_index": down_index,
            "wake_index": wake_index,
            "induction_limit": induction_limit,
            "observation_limit": observation_limit,
            "attack_pulses_before_down": attack_pulses,
            "scene_violations": scene_violations,
        }
    return results


def _cpu_jump_in(cpu_id: int, difficulty: int, title_delay: int = 0, *,
                 retreat: bool = False, kick: bool = True) -> dict[str, object]:
    """Replay a jump from native arcade menus, never memory or a save state.

    Fixed title delays select reproducible PRNG/cadence opportunities. Walk
    to the launch band, then lock ordinary forward/backward jump momentum.
    The optional medium kick is deliberately later than the early reactions.
    """

    e = boot(0, fighter=(cpu_id - 1) % 12, difficulty=difficulty,
             title_delay=title_delay)
    approach: list[dict[str, int]] = []
    samples: list[dict[str, int]] = []
    launch_range = 34 if retreat else (56 if DELIBERATE_PACING and cpu_id==4 else 68)
    try:
        for _ in range(210):
            sample = trace(e)
            if (abs(sample["x1"] - sample["x2"]) <= launch_range * 16 and
                    not sample["hurt1"] and not sample["down_state1"] and
                    not sample["action1"] and not sample["y1"] and
                    (not DELIBERATE_PACING or cpu_id!=4 or not sample['action2'])):
                break
            approach.append(sample)
            e.run(1, p1=["right"])
        else:
            raise AssertionError(("CPU jump fixture never reaches launch band",
                                  _cpu_summary(trace(e))))
        for tick in range(65):
            samples.append(trace(e))
            keys = (["up", "left" if retreat else "right"] if tick < 3
                    else ["a"] if kick and tick in (16, 17) else [])
            e.run(1, p1=keys)
    finally:
        e.close()
    return {"cpu_id": cpu_id, "difficulty": difficulty,
            "title_delay": title_delay, "retreat": retreat,
            "approach": approach, "samples": samples}


def _cpu_uppercut_start(case: dict[str, object], *, hit: bool) -> dict[str, object]:
    """Require a fresh Down+X edge, its full startup, and native contact/whiff."""

    samples = case["samples"]
    label = (f"CPU d{case['difficulty']} fighter {case['cpu_id']} "
             f"delay{case['title_delay']} {'retreat' if case['retreat'] else 'jump-in'}")
    starts = [index for index in range(1, len(samples))
              if samples[index]["action2"] == 8 and
              samples[index - 1]["action2"] != 8]
    check(bool(starts), label + " deliberately starts the universal uppercut",
          [_cpu_summary(sample) for sample in samples])
    index = starts[0]
    before, first = samples[index - 1:index + 1]
    check(first["raw_keys2"] == 1088 and first["anim_tick2"] == 1 and
          signed16(first["y2"]) < 0 and before["raw_keys2"] & 64 == 0,
          label + " starts action 8 from a real fresh DOWN+X edge", {
              "before": _cpu_summary(before), "first": _cpu_summary(first)})
    check(before["action2"] == before["hurt2"] == before["y2"] ==
          before["down_state2"] == before["hitstop"] == 0 and before["hp2"] > 0,
          label + " commits only from an ordinary available grounded startup",
          _cpu_summary(before))
    check(-56 * 16 <= signed16(before["y1"]) <= -12 * 16 and
          abs(before["x1"] - before["x2"]) < 41 * 16 and
          (before["x1"] > before["x2"]) == bool(before["face2"]) and
          before["hurt1"] == before["down_state1"] == 0 and before["hp1"] > 0,
          label + " reacts to a live visible near airborne target in front",
          _cpu_summary(before))
    startup = samples[index:index + 5]
    check([sample["anim_tick2"] for sample in startup] == [1, 2, 3, 4, 5] and
          all(sample["action2"] == 8 and sample["connected2"] == 0 and
              sample["hp1"] == before["hp1"] for sample in startup),
          label + " preserves all five pre-contact startup ticks",
          [_cpu_summary(sample) for sample in startup])
    active = [sample for sample in samples[index:] if sample["action2"] == 8]
    contacts = [sample for sample in active if sample["connected2"] == 2]
    if hit:
        check(bool(contacts) and contacts[0]["anim_tick2"] == 6 and
              contacts[0]["hp1"] < before["hp1"] and
              contacts[0]["hp2"] == before["hp2"] and
              signed16(contacts[0]["y1"]) < 0,
              label + " intercepts the jump on its ordinary first active tick", {
                  "decision": _cpu_summary(before),
                  "contact": _cpu_summary(contacts[0]) if contacts else None})
    else:
        active_window = [sample for sample in active
                         if 6 <= sample["anim_tick2"] < 14]
        check(len(active_window) == 8 and not contacts and
              all(sample["hp1"] == before["hp1"] and sample["connected2"] == 0
                  for sample in active) and
              min(abs(sample["x1"] - sample["x2"])
                  for sample in active_window) > 41 * 16,
              label + " can commit and whiff all eight active ticks", {
                  "decision": _cpu_summary(before),
                  "active": [_cpu_summary(sample) for sample in active_window]})
    return {"cpu_id": case["cpu_id"], "difficulty": case["difficulty"],
            "title_delay": case["title_delay"], "start_index": index,
            "decision": _cpu_summary(before), "first": _cpu_summary(first),
            "contact": _cpu_summary(contacts[0]) if contacts else None}


def _cpu_anti_air_ko(victim: int) -> dict[str, object]:
    """Reach genuine KOs on both sides with walk/throw/uppercut controller play."""

    e = boot(0, fighter=1, difficulty=2)
    samples: list[dict[str, int]] = []
    try:
        for tick in range(1800 if victim == 2 else 900):
            before = trace(e)
            if before["round_end"] or before["screen"] != 3:
                break
            forward = "right" if before["x1"] < before["x2"] else "left"
            keys = [forward]
            if victim == 2:
                # Reclose after recoil and throw only from observed range.
                # A fixed 16-tick spam schedule can feed jabs while X is still
                # recovering. Finish with a real airborne uppercut, preserving
                # the zero-HP flight and CPU-inertness assertions below.
                keys = []
                if not before["hitstop"] and not before["action1"]:
                    distance = abs(before["x1"] - before["x2"])
                    if before["hp2"] <= 24 and distance < 38 * 16:
                        keys = ["down", "x"]
                    elif distance > (before["throw_range1"] - 2) * 16:
                        keys = [forward]
                    else:
                        keys = [forward, "x"]
                if before["raw_keys1"] & 64 and "x" in keys:
                    keys = [forward]  # release before the next fresh edge
            e.run(1, p1=keys)
            sample = trace(e)
            if sample[f"hp{victim}"] == 0:
                samples.append(sample)
                for _ in range(12):
                    e.run(1, p1=["up"])
                    samples.append(trace(e))
                break
    finally:
        e.close()
    check(len(samples) == 13 and all(sample[f"hp{victim}"] == 0
                                    for sample in samples),
          f"CPU anti-air negative reaches a real P{victim} KO",
          [_cpu_summary(sample) for sample in samples])
    check(all(sample["raw_keys2"] == 0 and sample["action2"] != 8
              for sample in samples[1:]),
          f"CPU issues no uppercut or buffered attack after P{victim} KO",
          [_cpu_summary(sample) for sample in samples])
    if victim == 2:
        check(samples[0]["round_end"] == 0 and samples[0]["down_state2"] == 2 and
              signed16(samples[0]["y1"]) < 0,
              "zero-HP CPU stays inert during committed flight with airborne P1",
              _cpu_summary(samples[0]))
    return {"victim": victim, "samples": [_cpu_summary(sample) for sample in samples]}


def check_cpu_anti_air() -> dict[str, object]:
    """Bound strategic uppercuts with useful hits, misses and state exclusions.

    These title delays were measured on the current readable-combat cartridge.
    Each positive requires a deliberate action-8 start and real first-active contact.
    Existing rising-special, wave defense, approach and wake fixtures still
    run separately with their original assertions.
    """

    preview_menus = menu_preview_symbols() is not None
    fixtures = ((0, 1, 1), (0, 2, 0), (2, 2, 13), (4, 1, 6),
                (4, 2, 5), (5, 1, 8), (5, 2, 5))
    if DELIBERATE_PACING:
        fixtures=((0,1,1),(0,2,18),(2,2,13),(4,1,14),
                  (6,2,1),(5,1,7),(5,2,9))
    if PLAY_FLOW:
        # Current roster hints change menu elapsed time. Fixed measured
        # controller-only phases retain every original reaction assertion.
        fixtures=((0,1,2),(0,2,19),(2,2,1),(4,1,3),
                  (6,2,2),(5,1,7),(5,2,10))
    if CLASSIC_MENUS:
        # Faster roster transitions change the native frame at the opening.
        # Measured controller-only delays retain the same hit/startup checks.
        fixtures=((0,1,0),(0,2,7),(2,2,0),(4,1,5),
                  (6,2,0),(5,1,1),(5,2,5))
    if preview_menus:
        # Measured on the linked 18-tick standing-preview menu path. Only
        # title-controller timing changes; every original 65-sample reaction,
        # first-active contact and grounded/visible eligibility check remains.
        fixtures=((0,1,42),(0,2,6),(2,2,4),(4,1,3),
                  (6,2,0),(5,1,1),(5,2,39))
    cases = [_cpu_jump_in(cpu, difficulty, delay)
             for cpu, difficulty, delay in fixtures]
    hits = [_cpu_uppercut_start(case, hit=True) for case in cases]
    retreat = _cpu_jump_in(2, 2, 15 if preview_menus else 23 if CLASSIC_MENUS else 25 if PLAY_FLOW else 24 if DELIBERATE_PACING else 13, retreat=True, kick=False)
    whiff = _cpu_uppercut_start(retreat, hit=False)

    # Equal menu frame counts align Normal's title+20 with Hard/Easy's
    # difficulty-button tap. The same visible opening does not assure a
    # reaction: Hard intercepts here, Normal misses its sampled opportunity.
    comparison_cpu,comparison_delay=(5,39) if preview_menus else (5,5) if CLASSIC_MENUS else (5,10) if PLAY_FLOW else (5,9) if DELIBERATE_PACING else (4,5)
    easy = _cpu_jump_in(comparison_cpu, 0, comparison_delay)
    normal = _cpu_jump_in(comparison_cpu, 1, comparison_delay+20)
    hard = cases[6 if DELIBERATE_PACING else 4]
    opening = ("frame", "x1", "x2", "y1", "y2", "action1", "action2", "hp1", "hp2")
    check(all(tuple(case["samples"][0][name] for name in opening) ==
              tuple(hard["samples"][0][name] for name in opening)
              for case in (easy, normal)),
          "CPU anti-air difficulty comparison has the same native opening",
          [_cpu_summary(case["samples"][0]) for case in (easy, normal, hard)])
    for case, label in ((easy, "Easy"), (normal, "Normal sampled miss")):
        check(not any(sample["raw_keys2"] == 1088 or sample["action2"] == 8
                      for sample in case["samples"]),
              label + " keeps the measured jump-in without a universal uppercut",
              [_cpu_summary(sample) for sample in case["samples"]])
    # The four-button CPU chooses from four normals instead of six. In the
    # equal-opening comparison above Normal is occupied by a strong normal;
    # this separately measured phase retains a genuinely free sampled miss.
    decline_delay=0 if CLASSIC_MENUS else 29 if DELIBERATE_PACING else 0
    normal_decline = _cpu_jump_in(comparison_cpu, 1, decline_delay)
    check(not any(sample["action2"] == 8 for sample in normal_decline["samples"]),
          "Normal's available-window fixture genuinely declines the uppercut")
    opportunities = [sample for sample in normal_decline["samples"]
                     if -56 * 16 <= signed16(sample["y1"]) <= -12 * 16 and
                     abs(sample["x1"] - sample["x2"]) < 41 * 16 and
                     sample["action2"] == sample["hurt2"] == sample["y2"] == 0]
    check(bool(opportunities), "Normal can decline an available near jump-in",
          [_cpu_summary(sample) for sample in opportunities])

    empty_jump = _cpu_jump_in(comparison_cpu, 2, comparison_delay, kick=False)
    empty_hit = _cpu_uppercut_start(empty_jump, hit=True)
    check(empty_jump["samples"][:17] == hard["samples"][:17] and
          empty_hit["start_index"] < 16 and
          all(sample["action1"] == 0 for sample in empty_jump["samples"][:17]),
          "CPU can intercept an empty jump before any attack-button input",
          empty_hit)

    # A rush CPU occupied by a normal can be crossed and genuinely hurt by
    # the jump kick. Its locked facing exposes a real behind-target window;
    # free grounded CPUs turn normally before choosing their input.
    busy = _cpu_jump_in(2, 1, 21 if CLASSIC_MENUS else 0)
    crossed = _cpu_jump_in(2, 2, 0 if preview_menus else 1 if CLASSIC_MENUS else 4)
    cases.extend((retreat, easy, normal, normal_decline, empty_jump, busy, crossed))
    negatives: dict[str, list[tuple[dict[str, int], dict[str, int]]]] = {
        name: [] for name in ("grounded", "far", "behind-locked", "unavailable",
                             "hurt", "target-hurt-or-down", "hitstop")}
    for case in cases:
        rows = case["approach"] + case["samples"]
        pairs = list(zip(rows, rows[1:]))
        check(all((after["frame"] - before["frame"]) & 0xffff == 1
                  for before, after in pairs),
              f"CPU anti-air d{case['difficulty']} fighter {case['cpu_id']} keeps native cadence")
        for before, after in pairs:
            airborne = signed16(before["y1"]) < 0
            unavailable = bool(before["action2"] or before["y2"] or before["down_state2"])
            behind = ((before["x1"] > before["x2"] and not before["face2"]) or
                      (before["x1"] < before["x2"] and before["face2"]))
            flags = {
                "grounded": not airborne,
                "far": airborne and abs(before["x1"] - before["x2"]) >= 41 * 16,
                "behind-locked": airborne and behind and (unavailable or before["hurt2"]),
                "unavailable": unavailable,
                "hurt": bool(before["hurt2"]),
                "target-hurt-or-down": bool(before["hurt1"] or before["down_state1"]),
                "hitstop": bool(before["hitstop"]),
            }
            for name, applies in flags.items():
                if applies:
                    negatives[name].append((before, after))
    negative_counts = {}
    for name, pairs in negatives.items():
        violations = [(before, after) for before, after in pairs
                      if after["raw_keys2"] == 1088]
        check(bool(pairs) and not violations,
              "CPU anti-air does not issue DOWN+X for " + name, {
                  "observed_ticks": len(pairs),
                  "example": _cpu_summary(pairs[0][0]) if pairs else None,
                  "violations": [[_cpu_summary(s) for s in pair] for pair in violations[:4]]})
        negative_counts[name] = len(pairs)
    return {"hits": hits, "retreat_whiff": whiff, "empty_jump": empty_hit,
            "normal_declined_title_delay": decline_delay,
            "normal_declined_ticks": len(opportunities),
            "normal_declined_opportunities": [_cpu_summary(sample) for sample in opportunities],
            "negative_ticks": negative_counts,
            "ko": [_cpu_anti_air_ko(victim) for victim in (1, 2)]}


def check_cpu_regressions() -> dict[str, object]:
    """Run the bounded CPU 0.6.1 matrix and its behavior fixtures."""

    return {
        "matrix": check_cpu_matrix(),
        "special_spacing": check_cpu_special_spacing(),
        "natural_wave_specials": check_cpu_natural_wave_specials(),
        "lowwave_guard": check_cpu_lowwave_guard(),
        "wake": check_cpu_wake(),
        "anti_air": check_cpu_anti_air(),
    }


def check_pause_transition_cadence() -> dict[str, object]:
    """Pause-card construction must preserve native cadence on either pad.

    The long-session roster route exposed a missed frame on the first Start
    edge. Check every callback around pause/resume in each mode, including
    the expensive card-construction tick rather than only the settled screen.
    """
    results = {}
    for mode in (0, 1, 2):
        for port in (0, 1):
            e = boot(mode)
            key = f"mode{mode}-pad{port + 1}"
            phases = []
            try:
                previous = trace(e)
                for wanted in (1, 0):
                    deltas = []
                    for tick in range(18):
                        held = ["start"] if tick < 3 else []
                        e.run(1, **({"p1": held} if port == 0 else {"p2": held}))
                        current = trace(e)
                        deltas.append((current["frame"] - previous["frame"]) & 0xffff)
                        previous = current
                    check(all(delta == 1 for delta in deltas),
                          "pause/resume card keeps unit native cadence", {
                              "case": key, "wanted_paused": wanted, "deltas": deltas,
                          })
                    check(current["screen"] == 3 and current["paused"] == wanted,
                          "either controller pauses and resumes the active mode", {
                              "case": key, "wanted_paused": wanted,
                              "screen": current["screen"], "paused": current["paused"],
                          })
                    phases.append({"paused": wanted, "frames": len(deltas),
                                   "deltas": deltas})
                results[key] = phases
            finally:
                e.close()
    return results


def main() -> int:
    started = time.monotonic()
    report: dict[str, object] = {
        "emulator": "Official Snes9x 1.63 x64 libretro core",
        "suite": "input-feel",
        "status": "failed",
        "rom_sha256": None,
        "rom_bytes": None,
        "checks": checks,
        "transition_stress": {},
        "combo_cadence_stress": {},
        "two_controller_stress": {},
        "resident_sfx_audio": {},
        "status_bars": {},
        "counter_banner": {},
        "throw_interrupt": {},
        "throw_startup_escape": {},
        "down_floor_guard": {},
        "cpu_regressions": {},
        "menu_regressions": {},
        "cross_up_contacts": {},
    }
    try:
        manifest = json.loads((ROOT / "dist/manifest.json").read_text())
        report["rom_sha256"] = manifest["sha256"]
        report["rom_bytes"] = manifest.get("bytes")
        check(manifest.get("bytes") == 4 * 1024 * 1024,
              "input-feel probe uses the 4 MiB animation ROM", manifest)

        report["transition_stress"] = check_transition_stress()
        report["combo_cadence_stress"] = check_combo_cadence_stress()
        report["two_controller_stress"] = check_two_controller_stress()
        report["resident_sfx_audio"] = check_resident_sfx_audio()

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
        report["pause_transition_cadence"] = check_pause_transition_cadence()
        check_training_inertness()
        check_training_reset()
        report["menu_regressions"] = check_menu_regressions()
        report["status_bars"] = check_guard_timing()
        report["counter_banner"] = check_counter_banner()
        check_contact_classification()
        check_held_back_combo_and_block_string()
        check_stale_prehit_buffer()
        check_combo_lifecycle()
        check_mirrored_throw_range()
        check_air_normals_both_sides()
        check_air_contact_window()
        check_attack_knockdowns()
        report["down_floor_guard"] = check_down_floor_input_guard()
        check_throw_knockdown_wake()
        check_simultaneous_throw_tech()
        report["throw_startup_escape"] = check_throw_startup_escape()
        report["throw_interrupt"] = check_projectile_interrupts_throw()
        report["cpu_regressions"] = check_cpu_regressions()

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
        report["cross_up_contacts"] = check_cross_up_contacts()
        check_neutral_jump_unsteered()
        check_jump_velocity(0, "right")
        check_jump_velocity(1, "left")
        check_down_shortcut(0)
        check_down_shortcut(1)
        check_qcf_both_facings()
        report["motion_step_timeout"] = check_motion_step_timeout_both_ports()
        check_wake_motion_both_ports()
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
