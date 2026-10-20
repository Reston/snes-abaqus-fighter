"""Silent, headless integration checks for the individualized SNES roster.

This is deliberately separate from ``test_rom.py``.  It launches only the
official libretro core through :class:`emulator.Emulator`, drives the two
SNES controllers, reads the emulator's video/WRAM trace, and captures audio
samples without sending them to an audio device.  The host never writes game
memory.

Run after a native build with::

    python tools/test_characters.py

The script is intended to be useful while the user has another game in the
foreground: it never opens a window, plays audio, or takes focus.
"""

from __future__ import annotations

import ctypes as C
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from emulator import Emulator, ROOT


NAMES = (
    "DAMIAN", "IVO", "CRISTOBAL", "COTE", "NEGGER", "DAVID",
    "FERNANDO", "CRISTIAN", "MAMARIAGA", "RESTON", "ROXANA", "LARS",
)

# This is a behavioral contract for the upgraded roster, not a lookup into the
# game binary.  The test obtains the family from the read-only WRAM trace and
# compares what the game reports with this design contract.
SPECIAL_FAMILY = (0, 0, 1, 1, 2, 3, 2, 3, 2, 0, 3, 2)
FAMILY_NAMES = ("projectile", "rush", "groundwave", "rising")

# A pose is a 64x80 actor frame (2,560 bytes).  Eight poses are kept in each
# LoROM-friendly bank, and the renderer interleaves ten 256-byte rows in VRAM.
POSE_BYTES = 2560
BANK_BYTES = POSE_BYTES * 8
VRAM_ACTOR_BASE = 0xC000
VRAM_ACTOR_STRIDE = 0x100
VRAM_ROW_STRIDE = 0x200
VRAM_ROW_BYTES = 0x100

checks: list[dict[str, object]] = []


def check(ok: bool, label: str, details: object | None = None) -> None:
    if not ok:
        raise AssertionError((label, details))
    checks.append({"check": label, "passed": True, "details": details})


def signed16(value: int) -> int:
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def raw_trace_words(e: Emulator, count: int = 64) -> list[int]:
    """Return trace words without mutating the emulated WRAM.

    The first 32 words predate the individualized roster.  The optional words
    are decoded here as a fallback so the test remains compatible with an
    Emulator.state() implementation from before the trace extension landed.
    """

    data = C.string_at(e.ram + 0x1FF00, count * 2)
    return [int.from_bytes(data[i:i + 2], "little") for i in range(0, len(data), 2)]


def state(e: Emulator) -> dict[str, int]:
    """Read the public state plus the agreed roster trace extension."""

    result = dict(e.state())
    raw = raw_trace_words(e)
    # These aliases mirror the agreed TRACE[32..41] contract.  setdefault is
    # intentional: a future Emulator.state() may expose nicer names directly.
    extension = {
        "fighter_id1": raw[32], "fighter_id2": raw[33],
        "family1": raw[34], "family2": raw[35],
        "speed1": raw[36], "speed2": raw[37],
        "jump1": raw[38], "jump2": raw[39],
        "face1": raw[40], "face2": raw[41],
        "back_speed1": raw[42], "back_speed2": raw[43],
        "special_startup1": raw[44], "special_startup2": raw[45],
        "special_active1": raw[46], "special_active2": raw[47],
        "special_recovery1": raw[48], "special_recovery2": raw[49],
        "special_damage1": raw[50], "special_damage2": raw[51],
        "special_reach1": raw[52], "special_reach2": raw[53],
        "throw_range1": raw[54], "throw_range2": raw[55],
        "wave_low1": raw[56], "wave_low2": raw[57],
        "wave_speed1": raw[58], "wave_speed2": raw[59],
        "wave_life1": raw[60], "wave_life2": raw[61],
    }
    for key, value in extension.items():
        result.setdefault(key, value)
    return result


def side_field(s: dict[str, int], side: int, *names: str) -> int | None:
    """Find a per-side trace field while accepting old/new naming styles."""

    suffix = str(side + 1)
    zero_suffix = str(side)
    candidates: list[str] = []
    for name in names:
        candidates.extend((f"{name}{suffix}", f"{name}_{suffix}",
                           f"{name}{zero_suffix}", f"{name}_{zero_suffix}"))
    for key in candidates:
        if key in s:
            return int(s[key])
    return None


def wait_screen(e: Emulator, wanted: int, max_frames: int = 600) -> None:
    for _ in range(max_frames // 10):
        if state(e)["screen"] == wanted:
            e.run(10)
            return
        e.run(10)
    raise AssertionError(("screen did not arrive", wanted, state(e)))


def press(e: Emulator, key: str, port: int = 0) -> None:
    e.tap(key, port)
    e.run(20)


def boot(mode: int, fighter: int, stage: int = 0, fighter2: int = 1) -> Emulator:
    """Boot a fresh match using only menu controller input.

    mode follows the cartridge menu: 0 arcade, 1 local versus, 2 training.
    """

    e = Emulator()
    e.run(120)
    for _ in range(mode):
        press(e, "down")
    press(e, "a")
    wait_screen(e, 1)
    for _ in range(fighter):
        press(e, "right")
    press(e, "a")
    if mode == 1:
        # The cartridge initializes P2's cursor to roster slot 1 (Ivo), so
        # menu-right counts are relative to that cursor rather than slot 0.
        for _ in range((fighter2 - 1) % len(NAMES)):
            press(e, "right", 1)
        press(e, "a", 1)
    wait_screen(e, 2)
    for _ in range(stage):
        press(e, "down")
    press(e, "a")
    wait_screen(e, 3)
    # Let the 110-frame intro finish while the CPU is still inert.  The first
    # live frame can still carry the FIGHT banner's dirty-tile upload, so give
    # the renderer three quiet frames before the first VRAM check or capture.
    for _ in range(160):
        if state(e)["intro"] == 0:
            break
        e.run(1)
    check(state(e)["intro"] == 0, "match intro completes", {
        "mode": mode, "fighter": fighter, "fighter2": fighter2,
    })
    e.run(3)
    return e


def vram(e: Emulator) -> bytes:
    ptr = e.core.retro_get_memory_data(3)
    size = e.core.retro_get_memory_size(3)
    return C.string_at(ptr, size)


def expected_bank(fighter: int, bank: int) -> bytes:
    suffix = "" if bank == 0 else "b"
    data = (ROOT / f"assets/generated/fighter{fighter:02}{suffix}.bin").read_bytes()
    check(len(data) == BANK_BYTES, "fighter bank has 8 complete poses", {
        "fighter": fighter, "bank": bank, "bytes": len(data),
    })
    return data


def actor_rows(e: Emulator, fighter: int, side: int, bank: int,
               pose: int | None = None) -> bool:
    """Compare every uploaded row in the selected actor slot to the ROM asset."""

    data = expected_bank(fighter, bank)
    pose_in_bank = (pose if pose is not None else bank * 8) & 7
    data = data[pose_in_bank * POSE_BYTES:(pose_in_bank + 1) * POSE_BYTES]
    image = vram(e)
    base = VRAM_ACTOR_BASE + side * VRAM_ACTOR_STRIDE
    return all(
        image[base + row * VRAM_ROW_STRIDE:base + row * VRAM_ROW_STRIDE + VRAM_ROW_BYTES]
        == data[row * VRAM_ROW_BYTES:(row + 1) * VRAM_ROW_BYTES]
        for row in range(10)
    )


def wait_for_uploaded_pose(e: Emulator, fighter: int, side: int = 0,
                           max_frames: int = 24) -> tuple[dict[str, int], int]:
    """Wait for the one-actor-per-vblank queue and return pose/bank."""

    for _ in range(max_frames):
        s = state(e)
        pose = s["pose1" if side == 0 else "pose2"]
        bank = 0 if pose < 8 else 1
        if actor_rows(e, fighter, side, bank, pose):
            return s, bank
        e.run(1)
    s = state(e)
    pose = s["pose1" if side == 0 else "pose2"]
    bank = 0 if pose < 8 else 1
    return s, bank


def capture(e: Emulator, fighter: int, label: str) -> Path:
    folder = ROOT / "docs/screenshots/characters"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (f"{fighter:02}.png" if label == "idle" else f"{fighter:02}-{label}.png")
    if e.frame is None:
        e.run(1)
    e.frame.save(path)
    return path


def trigger_special(e: Emulator, expected_family: int) -> tuple[dict[str, int], list[dict[str, int]]]:
    """Try the controller-only special motions and return observed samples.

    The primary motion is the game's documented down + punch shortcut.  The
    remaining quarter-circle and uppercut variants make this diagnostic if a
    character family chooses a different six-button route while preserving
    the public controller contract.
    """

    macros = (
        (("down",), ("down", "x")),
        (("down",), ("down", "a")),
        (("down", "right"), ("down", "right", "x")),
        (("down",), ("down", "l")),
    )
    best: tuple[dict[str, int], list[dict[str, int]]] | None = None
    before = state(e)
    for held, pressed in macros:
        # The libretro input callback is sampled at the core's frame boundary;
        # a one-frame edge can fall between polls on some Snes9x cadence
        # phases.  Hold the setup and button long enough for a real pad
        # sample, matching a player's sustained SNES input without changing
        # the game's edge-triggered move rules.
        e.run(4, p1=list(held))
        e.run(18, p1=list(pressed))
        samples: list[dict[str, int]] = []
        for _ in range(40):
            sample = state(e)
            samples.append(sample)
            # Leave the emulator on the special pose so the following VRAM
            # assertion observes the one-actor-per-vblank upload, rather than
            # waiting until the animation has already returned to idle.
            displacement = abs(signed16(sample["x1"]) - signed16(before["x1"]))
            rising = signed16(sample["y1"]) < 0
            if sample["wave1"] or (
                expected_family == 1 and sample["pose1"] >= 8 and displacement >= 8
            ) or (
                expected_family == 3 and sample["pose1"] >= 8 and rising
            ):
                break
            e.run(1)
        # A trace-visible action, projectile, vertical movement, or rush
        # displacement is stronger evidence than merely pressing a button.
        changed = any(
            s["action1"] or s["wave1"] or signed16(s["y1"]) < 0
            or abs(signed16(s["x1"]) - signed16(before["x1"])) >= 8
            for s in samples
        )
        if changed:
            return before, samples
        best = (before, samples)
        e.run(36)
    assert best is not None
    return best


def assert_special_family(e: Emulator, fighter: int) -> dict[str, object]:
    expected = SPECIAL_FAMILY[fighter]
    before, samples = trigger_special(e, expected)
    observed = [state(e)] + samples
    values = [side_field(s, 0, "family", "special_family", "specialFamily")
              for s in observed]
    values = [v for v in values if v is not None and v < len(FAMILY_NAMES)]
    check(bool(values), "fighter exposes a special family in read-only trace", {
        "fighter": fighter, "expected": expected,
        "trace_keys": sorted(k for k in observed[-1] if "family" in k.lower()),
    })
    check(all(v == expected for v in values), "fighter reports its contracted special family", {
        "fighter": fighter, "expected": expected, "observed": values,
    })

    # The family must manifest in emulated gameplay.  This deliberately uses
    # only public trace values, never game memory writes or source constants.
    action = any(s["action1"] for s in samples)
    projectile = any(s["wave1"] for s in samples)
    rise = any(signed16(s["y1"]) < 0 for s in samples)
    rush = any(abs(signed16(s["x1"]) - signed16(before["x1"])) >= 8 for s in samples)
    low_wave = [side_field(s, 0, "wave_low", "waveLow", "low") for s in samples]
    low_wave = [v for v in low_wave if v is not None]
    if expected == 0:
        manifested = projectile and (not low_wave or any(v == 0 for v in low_wave))
    elif expected == 1:
        manifested = rush and not rise
    elif expected == 2:
        manifested = projectile and (not low_wave or any(v == 1 for v in low_wave))
    else:
        manifested = rise
    check(manifested, "special family produces an observable combat event", {
        "fighter": fighter, "family": FAMILY_NAMES[expected],
        "action": action, "projectile": projectile, "rush": rush, "rise": rise,
    })
    return {
        "expected": FAMILY_NAMES[expected], "observed": values,
        "action": action, "projectile": projectile, "rush": rush, "rise": rise,
    }


def close_p1_to_guard_range(e: Emulator) -> int:
    """Put P1 at 35--40 pixels from an idle P2 using only the controller."""

    for _ in range(260):
        s = state(e)
        distance = abs(signed16(s["x2"]) - signed16(s["x1"]))
        if 35 * 16 <= distance <= 40 * 16:
            return distance
        e.run(1, p1=["right"] if distance > 40 * 16 else ["left"])
    raise AssertionError(("P1 could not close to the guard range", state(e)))


def close_p2_to_attack_range(e: Emulator) -> int:
    """Put a left-facing P2 at 35--40 pixels from a passive P1."""

    for _ in range(260):
        s = state(e)
        distance = abs(signed16(s["x2"]) - signed16(s["x1"]))
        if 35 * 16 <= distance <= 40 * 16:
            return distance
        e.run(1, p2=["left"] if distance > 40 * 16 else ["right"])
    raise AssertionError(("P2 could not close to the attack range", state(e)))


def wait_for_hp_change(e: Emulator, side: int, p1=(), p2=(), max_frames: int = 120) -> tuple[int, int, dict[str, int]]:
    """Hold the guard/controller inputs until a real hit is recorded."""

    key = "hp1" if side == 0 else "hp2"
    before = state(e)
    initial = before[key]
    for frame in range(1, max_frames + 1):
        e.run(1, p1=list(p1), p2=list(p2))
        sample = state(e)
        if sample[key] != initial:
            return initial, sample[key], {"frame": frame, **sample}
    raise AssertionError(("special did not reach the guarded/passive target", {
        "side": side, "initial_hp": initial, "last": state(e),
    }))


def verify_guard_case(fighter: int, guard: str, blocked: bool) -> dict[str, object]:
    """Check a real special interaction against a controller-held guard.

    P2 is local-versus and receives no CPU decisions.  Standing guard is the
    character's back direction (right while P2 faces left); crouch guard adds
    down and therefore does not walk backward.  A blocked special may deal
    one chip point, while an unblocked special must deal meaningful damage.
    """

    e = boot(1, fighter, 0, 1)
    try:
        distance = close_p1_to_guard_range(e)
        guard_keys = ["right"] if guard == "standing" else ["down", "right"]
        before = state(e)
        face1 = side_field(before, 0, "face", "facing", "direction")
        face2 = side_field(before, 1, "face", "facing", "direction")
        if face1 is not None:
            check(face1 == 1, "P1 faces the left-facing P2 before the special", {
                "fighter": fighter, "face1": face1, "face2": face2,
            })
        if face2 is not None:
            check(face2 == 0, "P2 remains left-facing for the guard check", {
                "fighter": fighter, "face2": face2,
            })
        family = side_field(before, 0, "family", "special_family", "specialFamily")
        check(family == SPECIAL_FAMILY[fighter], "guard probe sees the contracted special family", {
            "fighter": fighter, "family": family,
        })

        initial_hp, final_hp, hit = wait_for_hp_change(
            e, 1, p1=["down", "x"], p2=guard_keys
        )
        delta = initial_hp - final_hp
        if blocked:
            check(0 < delta <= 1, "held standing/crouch guard limits special to chip damage", {
                "fighter": fighter, "family": FAMILY_NAMES[SPECIAL_FAMILY[fighter]],
                "guard": guard, "hp_delta": delta,
            })
        else:
            check(delta >= 10, "special breaks the intended guard and deals real damage", {
                "fighter": fighter, "family": FAMILY_NAMES[SPECIAL_FAMILY[fighter]],
                "guard": guard, "hp_delta": delta,
            })
        return {
            "fighter": NAMES[fighter], "family": FAMILY_NAMES[SPECIAL_FAMILY[fighter]],
            "guard": guard, "expected_blocked": blocked, "distance_12_4": distance,
            "initial_hp2": initial_hp, "final_hp2": final_hp, "damage": delta,
            "hit_frame": hit["frame"],
        }
    finally:
        e.close()


def verify_p2_special_hit(fighter: int) -> dict[str, object]:
    """Ensure each representative special also works when P2 faces left."""

    e = boot(1, 1, 0, fighter)
    try:
        distance = close_p2_to_attack_range(e)
        before = state(e)
        face2 = side_field(before, 1, "face", "facing", "direction")
        if face2 is not None:
            check(face2 == 0, "P2 representative starts left-facing", {
                "fighter": fighter, "face2": face2,
            })
        family = side_field(before, 1, "family", "special_family", "specialFamily")
        check(family == SPECIAL_FAMILY[fighter], "P2 representative reports its special family", {
            "fighter": fighter, "family": family,
        })

        initial_hp, final_hp, hit = wait_for_hp_change(
            e, 0, p1=[], p2=["down", "x"]
        )
        delta = initial_hp - final_hp
        check(delta >= 10, "left-facing P2 special reaches passive P1", {
            "fighter": fighter, "family": FAMILY_NAMES[SPECIAL_FAMILY[fighter]],
            "hp_delta": delta,
        })
        return {
            "fighter": NAMES[fighter], "family": FAMILY_NAMES[SPECIAL_FAMILY[fighter]],
            "distance_12_4": distance, "initial_hp1": initial_hp,
            "final_hp1": final_hp, "damage": delta, "hit_frame": hit["frame"],
            "face2": face2,
        }
    finally:
        e.close()


def verify_asset_identity() -> None:
    digests: list[str] = []
    for fighter in range(len(NAMES)):
        a = expected_bank(fighter, 0)
        b = expected_bank(fighter, 1)
        digests.append(hashlib.sha256(a + b).hexdigest())
        check(a != b, "fighter has distinct pose banks", {"fighter": fighter})
    check(len(set(digests)) == len(NAMES), "all twelve fighters have distinct native animation assets", {
        "unique_assets": len(set(digests)),
    })


def verify_p1_fighter(fighter: int) -> dict[str, object]:
    e = boot(2, fighter, fighter % 3)
    try:
        s0, bank0 = wait_for_uploaded_pose(e, fighter, 0)
        check(s0["selected"] == fighter, "menu selects requested fighter", {
            "fighter": fighter, "selected": s0["selected"],
        })
        check(s0["pose1"] < 8 and bank0 == 0, "idle frame uses the first pose bank", {
            "fighter": fighter, "pose": s0["pose1"], "bank": bank0,
        })
        check(actor_rows(e, fighter, 0, 0), "all ten idle sprite rows reach actor VRAM", {
            "fighter": fighter,
        })
        idle_path = capture(e, fighter, "idle")

        x0 = signed16(s0["x1"])
        movement = []
        for _ in range(8):
            e.run(1, p1=["right"])
            movement.append(signed16(state(e)["x1"]) - x0)
        s_move = state(e)
        delta = signed16(s_move["x1"]) - x0
        check(delta > 0, "controller one moves the fighter forward", {
            "fighter": fighter, "delta_12_4": delta,
        })
        check(s_move["pose1"] in (1, 2), "forward movement uses a walk pose", {
            "fighter": fighter, "pose": s_move["pose1"],
        })

        e.run(3, p1=["up"])
        jump_samples = []
        for _ in range(8):
            jump_samples.append(state(e))
            e.run(1)
        jump_height = min(signed16(s["y1"]) for s in jump_samples)
        check(jump_height < 0, "controller one jump leaves the floor", {
            "fighter": fighter, "min_y_12_4": jump_height,
        })
        for _ in range(90):
            e.run(1)
            if signed16(state(e)["y1"]) == 0:
                break

        special = assert_special_family(e, fighter)
        s_special, bank1 = wait_for_uploaded_pose(e, fighter, 0)
        # The special family must reach a second-bank key pose at least once.
        check(s_special["pose1"] >= 8 or bank1 == 1, "special reaches a second-bank pose", {
            "fighter": fighter, "pose": s_special["pose1"], "bank": bank1,
        })
        check(actor_rows(e, fighter, 0, 1, s_special["pose1"]), "all ten special sprite rows reach the second actor bank", {
            "fighter": fighter,
        })
        capture(e, fighter, "special")

        profile_speed = side_field(s0, 0, "speed", "profile_speed", "profileSpeed")
        profile_jump = side_field(s0, 0, "jump", "jump_strength", "jumpStrength")
        return {
            "name": NAMES[fighter], "movement_delta": delta,
            "movement_samples": movement, "jump_height": jump_height,
            "speed_trace": profile_speed, "jump_trace": profile_jump,
            "special": special, "idle_screenshot": str(idle_path),
        }
    finally:
        e.close()


def verify_p2_orientation(fighter: int) -> dict[str, object]:
    """Exercise the same native asset in player two's flipped actor slot."""

    e = boot(1, 0, 0, fighter)
    try:
        s0, bank0 = wait_for_uploaded_pose(e, fighter, 1)
        check(s0["selected2"] == fighter, "controller two selects requested fighter", {
            "fighter": fighter, "selected2": s0["selected2"],
        })
        check(actor_rows(e, fighter, 1, 0), "player two receives this fighter's native idle rows", {
            "fighter": fighter,
        })
        face = side_field(s0, 1, "face", "facing", "direction")
        if face is not None:
            check(face == 0, "player two starts facing left for horizontal flip", {
                "fighter": fighter, "face2": face,
            })

        x0 = signed16(s0["x2"])
        e.run(1, p2=["left"])
        walk_samples = [state(e)]
        for _ in range(6):
            e.run(1, p2=["left"])
            walk_samples.append(state(e))
        s_walk = state(e)
        x_delta = signed16(s_walk["x2"]) - x0
        check(x_delta < 0, "controller two moves its flipped fighter toward player one", {
            "fighter": fighter, "delta_12_4": x_delta,
        })
        check(s_walk["pose2"] in (1, 2), "player two flipped actor uses a walk pose", {
            "fighter": fighter, "pose2": s_walk["pose2"],
        })

        e.run(3, p2=["up"])
        y_samples = []
        for _ in range(8):
            y_samples.append(state(e))
            e.run(1)
        min_y = min(signed16(s["y2"]) for s in y_samples)
        check(min_y < 0, "controller two can jump the flipped fighter", {
            "fighter": fighter, "min_y_12_4": min_y,
        })
        s_end = state(e)
        face_end = side_field(s_end, 1, "face", "facing", "direction")
        if face_end is not None:
            check(face_end == 0, "player two keeps left-facing flip while moving left", {
                "fighter": fighter, "face2": face_end,
            })
        return {"name": NAMES[fighter], "movement_delta": x_delta,
                "jump_height": min_y, "face2": face_end, "bank": bank0}
    finally:
        e.close()


def main() -> int:
    started = time.time()
    report: dict[str, object] = {
        "emulator": "Official Snes9x 1.63 x64 libretro core",
        "rom_sha256": None,
        "checks": checks,
        "characters": {},
        "player_two": {},
        "guard_checks": {},
        "player_two_specials": {},
    }
    try:
        manifest = json.loads((ROOT / "dist/manifest.json").read_text())
        report["rom_sha256"] = manifest["sha256"]
        verify_asset_identity()

        character_results: dict[str, object] = {}
        for fighter in range(len(NAMES)):
            character_results[f"{fighter:02}"] = verify_p1_fighter(fighter)
        report["characters"] = character_results

        p2_results: dict[str, object] = {}
        for fighter in range(len(NAMES)):
            p2_results[f"{fighter:02}"] = verify_p2_orientation(fighter)
        report["player_two"] = p2_results

        # Verify the frame-level guard rules against actual HP changes.  These
        # probes deliberately use local-versus P2 input so no CPU behaviour or
        # hidden test hook can satisfy the assertion.  The representative
        # roster members cover every special family and both directional
        # guard exceptions:
        #   projectile/rush: standing guard blocks;
        #   groundwave: standing guard loses, crouch guard blocks;
        #   rising: standing guard blocks, crouch guard loses.
        guard_cases = (
            (0, "standing", True),
            (2, "standing", True),
            (4, "standing", False),
            (4, "crouching", True),
            (10, "standing", True),
            (10, "crouching", False),
        )
        guard_results: dict[str, object] = {}
        for fighter, guard, blocked in guard_cases:
            key = f"{fighter:02}-{guard}"
            guard_results[key] = verify_guard_case(fighter, guard, blocked)
        report["guard_checks"] = guard_results

        # Exercise the same four representatives as player two.  P2 starts
        # facing left, so this catches flipped movement and projectile/hitbox
        # direction errors that a P1-only probe would miss.
        p2_special_results: dict[str, object] = {}
        for fighter in (0, 2, 4, 10):
            p2_special_results[f"{fighter:02}"] = verify_p2_special_hit(fighter)
        report["player_two_specials"] = p2_special_results

        movement = [int(v["movement_delta"]) for v in character_results.values()]
        check(len(set(movement)) >= 3, "roster has at least three observed movement profiles", {
            "movement_deltas": movement,
        })
        report["passed"] = len(checks)
        report["elapsed_seconds"] = round(time.time() - started, 2)
        report["status"] = "passed"
    except Exception as exc:
        report["passed"] = len(checks)
        report["elapsed_seconds"] = round(time.time() - started, 2)
        report["status"] = "failed"
        report["error"] = repr(exc)
        raise
    finally:
        path = ROOT / "docs/character-test-report.json"
        path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "status": report["status"], "passed": report.get("passed", 0),
        "seconds": report["elapsed_seconds"],
        "report": "docs/character-test-report.json",
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
