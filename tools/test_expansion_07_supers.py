"""Controller-only, silent native super proof. Never writes WRAM or loads states.

The linked private arrays are read as telemetry; every meter, position, contact,
guard, jump, interruption, pause and reset is earned through actual controllers.
This driver owns only expansion-07-report.json and expansion-07 screenshots.
"""
from __future__ import annotations

import ctypes as C
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from emulator import ROOT
from expansion_contracts import BASE, combined_contract
from release_evidence import EXPECTED_NATIVE_CORE
from test_characters import boot, uploaded_frame_id, vram

NAMES = ["KERNEL OVERDRIVE", "COMPOUND INTEREST", "ATOMIC CASCADE",
         "FINAL BALANCE", "MACRO COLLAPSE", "FINAL AUDIT", "LEGACY ROLLOUT",
         "ZERO RISK", "MERGE STORM", "CLOUD NINE", "CLOSING BELL", "ABSOLUTE ZERO"]
# Independent expected outcomes: uncontested close hits must deliver these
# actual HP steps, not merely advertise a different profile or move name.
HITS = [[10, 10, 12], [15, 19], [9, 9, 14], [13, 21], [15, 21], [8, 8, 18],
        [10, 10, 13], [12, 22], [8, 8, 13], [14, 22], [7, 7, 17], [16, 22]]
START = [12, 18, 8, 14, 20, 9, 14, 13, 8, 16, 7, 22]
ACTIVE_END = [80, 76, 31, 36, 85, 35, 96, 34, 72, 84, 28, 90]
END = [106, 108, 55, 68, 117, 63, 120, 68, 94, 114, 54, 118]
DIRECT = {2, 3, 5, 7, 10}
STATE = ("superActive", "superRequest", "superPhase", "superNext",
         "superContactEnd", "superWaveDamage", "superWaveReach")
checks: list[dict] = []
captures: list[str] = []
timing = {"frames": 0, "cadence_failures": [], "overflow_failures": []}
SYMBOLS: dict[str, int] = {}


def check(ok, label, detail=None):
    if not ok:
        raise AssertionError((label, detail))
    checks.append({"check": label, "details": detail})


def symbols(data):
    return {n: int(a, 16) for a, n in
            re.findall(r"^([0-9a-fA-F]{8}) (\S+)$", data, re.M)}


def read(e, name, size=2):
    address = SYMBOLS[name]
    if address < 0x20000:
        offset = address
    else:
        offset = address - 0x7E0000
    assert 0 <= offset < 0x20000
    return list(C.string_at(e.ram + offset, size))


def sample(e):
    s = e.state()
    for name in STATE:
        s[name] = read(e, name)
    raw = read(e, "fighters", 128)
    s["ticks"] = [raw[17], raw[81]]
    s["ends"] = [raw[62], raw[126]]
    s["active_ends"] = [raw[63], raw[127]]
    s["stat77"] = int.from_bytes(C.string_at(e.ram + 0x1FF00 + 228, 2), "little")
    return s


def step(e, p1=(), p2=(), monitor=True):
    old = e.state()["frame"]
    e.run(1, p1=p1, p2=p2)
    s = sample(e)
    if monitor:
        timing["frames"] += 1
        delta = (s["frame"] - old) & 65535
        if delta != 1:
            timing["cadence_failures"].append({"frame": s["frame"], "delta": delta,
                                               "phase": s["superPhase"], "keys": [p1, p2]})
        if s["stat77"] & 0xC0:
            timing["overflow_failures"].append({"frame": s["frame"], "stat77": s["stat77"]})
    return s


def run(e, frames, p1=(), p2=(), monitor=True):
    s = sample(e)
    for _ in range(frames):
        s = step(e, p1, p2, monitor)
    return s


def full(e):
    # Idle passive regeneration: no memory injection, cheats or save states.
    for _ in range(1800):
        s = sample(e)
        if s["energy1"] == 96 and s["energy2"] == 96:
            run(e, 3)
            return
        e.run(1)
    raise AssertionError(("meter did not naturally reach full", sample(e)))


def position(e, distance=28, far=False):
    for _ in range(280):
        s = sample(e)
        gap = abs(s["x2"] - s["x1"]) / 16
        if far:
            if s["x1"] == 24 * 16 and s["x2"] == 232 * 16:
                break
            e.run(1, p1=["left"], p2=["right"])
        else:
            if gap <= distance:
                break
            e.run(1, p1=["right"], p2=["left"])
    else:
        raise AssertionError(("controller movement did not reach fixture", sample(e)))
    run(e, 3)


def fire(e, port, extra=()):
    before = sample(e)
    keys = ["y", "b", *extra]
    s = step(e, keys if port == 0 else (), keys if port == 1 else ())
    check(before[f"energy{port+1}"] == 96 and s[f"energy{port+1}"] == 0,
          "fresh neutral chord pays exactly 96 immediately", {"port": port, "id": before[f"fighter_id{port+1}"]})
    check(s["superActive"][port] == 1 and s[f"action{port+1}"] == 7,
          "super takes priority using the existing special action ID")
    check(s["ticks"][port] == 1 and s["superPhase"][port] == 0,
          "activation exposes real startup before any pulse")
    return s


def activation(fighter):
    e = boot(1, fighter, fighter2=fighter)
    try:
        before = sample(e)
        s = run(e, 3, ["y", "b"], ["y", "b"])
        check(s["superActive"] == [0, 0] and s["action1"] == s["action2"] == 0,
              "insufficient-gauge chord cannot become a normal or special", fighter)
        check(s["energy1"] >= before["energy1"] and s["energy2"] >= before["energy2"],
              "insufficient gauge never spends any energy", fighter)
        s = run(e, 620, ["y", "b"], ["y", "b"])
        check(s["energy1"] == s["energy2"] == 96 and s["superActive"] == [0, 0],
              "held chord cannot auto-fire when regeneration fills the gauge", fighter)
        run(e, 3)
        s = run(e, 3, ["down", "y", "b"], ["down", "y", "b"])
        check(s["energy1"] == s["energy2"] == 96 and s["action1"] == s["action2"] == 0,
              "directional chord cannot accidentally buy a quick special", fighter)
        run(e, 3)
        s = run(e, 3, ["l", "r"], ["l", "r"])
        check(s["action1"] == s["action2"] == 0 and s["superActive"] == [0, 0],
              "shoulders remain non-attacking", fighter)
        run(e, 3)
        # Test each half-chord order on each physical controller.
        for first, second in ((['y'], ['b']), (['b'], ['y'])):
            run(e, 3, first, second)
            s = run(e, 100, ["y", "b"], ["y", "b"])
            check(s["superActive"] == [0, 0] and s["energy1"] == s["energy2"] == 96,
                  "adding either held half-chord cannot arm a super on either port", [fighter, first, second])
            run(e, 3)
        run(e, 3)
        before = sample(e)
        # Extra face edges cannot beat the explicit super chord.
        keys = ["y", "b", "x", "a"] if fighter == 0 else ["y", "b"]
        s = step(e, keys, keys)
        check(s["superActive"] == [1, 1] and s["energy1"] == s["energy2"] == 0,
              "both ports activate and pay full gauge on the same tick", fighter)
        check(s["action1"] == s["action2"] == 7 and s["ticks"] == [1, 1],
              "both ports choose super before ordinary face attacks", fighter)
        check(s["ends"] == [END[fighter]] * 2 and s["active_ends"] == [ACTIVE_END[fighter]] * 2,
              "native clocks expose bounded active and recovery durations", fighter)
        starts = [1, 1]
        previous = [1, 1]
        completed = [None, None]
        lows = [set(), set()]
        for elapsed in range(210):
            s = step(e, ["y", "b"], ["y", "b"])
            for port in range(2):
                if s["superActive"][port] and not previous[port]:
                    starts[port] += 1
                if previous[port] and not s["superActive"][port]:
                    completed[port] = elapsed + 2
                if s[f"wave{port+1}"]:
                    lows[port].add(s[f"wave_low{port+1}"])
            previous = s["superActive"]
        check(starts == [1, 1] and s["superActive"] == [0, 0],
              "held chords produce one bounded sequence on each port", fighter)
        check(all(t is not None and t <= END[fighter] for t in completed),
              "serialized sequences finish inside their maximum clock budget", [fighter, completed])
        check(s["energy1"] < 96 and s["energy2"] < 96,
              "super cannot refund enough meter for unlimited repeats", fighter)
        return {"fighter": fighter, "name": NAMES[fighter], "start_energy": [before["energy1"], before["energy2"]],
                "full_cost": [96, 96], "maximum_duration": END[fighter], "observed_duration": completed, "starts": starts,
                "observed_wave_heights": [sorted(x) for x in lows]}
    finally:
        e.close()


def contact(fighter, port, guard=False, capture=False):
    e = boot(1, fighter, fighter2=fighter)
    images = []
    try:
        position(e)
        full(e)
        defender = 1 - port
        hpkey = f"hp{defender+1}"
        hp = sample(e)[hpkey]
        # All projectile supers are mids/lows, so crouch guard covers both.
        # Rising contact retains ordinary standing guard / anti-air semantics.
        back = "right" if defender == 1 else "left"
        guardkeys = [back] + ([] if fighter in DIRECT else ["down"])
        frames, uploaded, events, guard_frames, down, ys = set(), set(), [], 0, set(), []
        guarded_phases = set()
        old_hitstop = 0
        for tick in range(220):
            attackkeys = ["y", "b"] if tick < 3 else []
            defkeys = guardkeys if guard else []
            s = step(e, attackkeys if port == 0 else defkeys,
                     attackkeys if port == 1 else defkeys)
            if tick == 0:
                check(s["superActive"][port] and s[f"energy{port+1}"] == 0,
                      "contact fixture activates via paid controller chord", [fighter, port, guard])
            if s[hpkey] != hp:
                events.append({"frame": tick, "damage": hp - s[hpkey], "phase": s["superPhase"][port],
                               "guard": s[f"guard{defender+1}"], "tick": s["ticks"][port]})
                hp = s[hpkey]
            if s["superActive"][port]:
                frames.add(s[f"anim_frame{port+1}"])
                ys.append(s[f"y{port+1}"])
                if tick % 3 == 0:
                    frame_id = uploaded_frame_id(e, fighter, port)
                    check(frame_id is not None, "super actor VRAM is an exact approved native frame", [fighter, port, tick])
                    uploaded.add(frame_id)
            if s[f"guard{defender+1}"]:
                guard_frames += 1
                if s["hitstop"] > old_hitstop:
                    guarded_phases.add(s["superPhase"][port])
            old_hitstop = s["hitstop"]
            down.add(s[f"down_state{defender+1}"])
            if capture and tick % 3 == 0 and e.frame is not None:
                images.append(e.frame.copy())
        if guard:
            check(guarded_phases == set(range(1, len(HITS[fighter]) + 1)),
                  "every super pulse makes a real guarded contact", [fighter, port, sorted(guarded_phases)])
            check(guard_frames > 0 and all(v["guard"] for v in events),
                  "defender really guards the native super contacts", [fighter, port, events])
            check(sum(v["damage"] for v in events) <= 3,
                  "blocked super produces only ordinary bounded chip", [fighter, port, events])
            check(not (down - {0}), "blocked final hit never knocks down", [fighter, port])
        else:
            check([v["damage"] for v in events] == HITS[fighter],
                  "all named super pulses cause the distinct tuned HP sequence", [fighter, port, events])
            check(0 < 128 - hp <= 38,
                  "uncontested total super damage is capped below one third health", [fighter, port, hp])
            if fighter in DIRECT:
                check(bool(down - {0}), "direct finisher causes real knockdown after the earlier strikes", [fighter, port])
        check(s["superActive"][port] == 0 and s[f"action{port+1}"] == 0,
              "startup active recovery sequence returns to neutral", [fighter, port])
        check(e.audio_samples > 10000 and e.audio_peak > 1000,
              "resident sound path produces real non-silent captured PCM", [fighter, port])
        if images:
            path = ROOT / "docs/screenshots" / f"expansion-07-{fighter:02d}-{'block' if guard else 'hit'}.gif"
            path.parent.mkdir(parents=True, exist_ok=True)
            images[0].save(path, save_all=True, append_images=images[1:], duration=50, loop=0)
            captures.append(path.relative_to(ROOT).as_posix())
        return {"fighter": fighter, "port": port, "guard": guard, "events": events,
                "damage": 128 - hp, "frames": sorted(frames), "uploaded_frames": sorted(uploaded),
                "down_states": sorted(down), "guarded_phases": sorted(guarded_phases),
                "left_ground": any(y != 0 for y in ys)}
    finally:
        e.close()


def whiff(fighter, port):
    e = boot(1, fighter, fighter2=fighter)
    try:
        position(e, far=True)
        full(e)
        fire(e, port)
        s = run(e, 220, ['y', 'b'] if port == 0 else [], ['y', 'b'] if port == 1 else [])
        check(s[f"hp{2-port}"] == 128 and s["superActive"] == [0, 0] and not s[f"wave{port+1}"],
              "out-of-range super whiffs, expires and spends gauge", [fighter, port])
        check(s[f"energy{port+1}"] < 16, "whiff cannot refund its full gauge cost", [fighter, port])
        return {"fighter": fighter, "port": port, "distance": 208, "hp": s[f"hp{2-port}"],
                "remaining_energy": s[f"energy{port+1}"]}
    finally:
        e.close()


def interrupt(fighter, port):
    e = boot(1, fighter, fighter2=fighter)
    try:
        position(e)
        full(e)
        target = port + 1
        maximum = 0
        observed = False
        for tick in range(100):
            chord = ["y", "b"] if tick < 3 else []
            normal = ["y"] if tick < 3 else []
            s = step(e, chord if port == 0 else normal, chord if port == 1 else normal)
            maximum = max(maximum, s["superPhase"][port])
            if tick == 0:
                check(s[f"energy{target}"] == 0 and s["superActive"][port],
                      "interruptible startup still pays full cost", [fighter, port])
            if s[f"hp{target}"] < 128:
                observed = True
        check(observed and maximum == 0 and not s["superActive"][port],
              "a real light punch interrupts startup before any super pulse", [fighter, port, maximum])
        check(s[f"hp{2-port}"] == 128 and not s[f"wave{target}"],
              "interrupted super cannot leak later damage or projectiles", [fighter, port])
        return {"fighter": fighter, "port": port, "max_phase": maximum, "hp": s[f"hp{target}"]}
    finally:
        e.close()


def punish():
    e = boot(1, 2, fighter2=2)
    try:
        position(e, distance=80)
        full(e)
        fire(e, 0)
        for _ in range(80):
            s = sample(e)
            if s["ticks"][0] >= ACTIVE_END[2]:
                break
            step(e)
        check(s["hp2"] == 128, "Atomic Cascade missed before the recovery punish")
        for _ in range(40):
            s = sample(e)
            # Feature03's shorter Cristobal jab needs a genuine close punish.
            if abs(s["x2"] - s["x1"]) <= 32 * 16:
                break
            step(e, p2=["left"])
        before = sample(e)
        check(before["superActive"][0] and before["ticks"][0] >= ACTIVE_END[2],
              "opponent enters range during committed super recovery", before["ticks"])
        found = None
        for tick in range(24):
            prior = sample(e)
            s = step(e, p2=["y"] if tick < 3 else [])
            if s["hp1"] < 128:
                found = {"before_contact": prior, "after_contact": s}
                break
        check(found is not None and found['after_contact']["counter2"] == 0
              and found['before_contact']['superActive'][0]
              and ACTIVE_END[2] <= found['before_contact']['ticks'][0] + 1 < END[2],
              "controller approach and light punch punish recovery without a startup counter")
        return {"recovery_tick": before["ticks"][0], "punish_hp": found['after_contact']["hp1"],
                "contact": found}
    finally:
        e.close()


def eligibility_pause_reset():
    e = boot(2, 0, fighter2=1)
    try:
        full(e)
        run(e, 6, ["up"])
        s = run(e, 15, ["y", "b"])
        check(not s["superActive"][0] and s["energy1"] == 96,
              "airborne fresh chord cannot activate or spend energy")
        s = run(e, 70, ["y", "b"])
        check(s["y1"] == 0 and not s["superActive"][0],
              "airborne rejected chord cannot auto-activate after landing")
        run(e, 3)
        # Start retains priority over every face button, including the chord.
        s = run(e, 3, ["start", "y", "b"])
        check(s["paused"] and s["energy1"] == 96 and not s["superActive"][0],
              "Start plus chord pauses without attacking or taking B's roster route")
        run(e, 3)
        s = run(e, 3, ["start", "y", "b"])
        check(not s["paused"] and not s["superActive"][0] and s["energy1"] == 96,
              "resume sample cannot smuggle a held chord into combat")
        run(e, 3)
        fire(e, 0)
        run(e, 13)
        before = sample(e)
        check(before["superActive"][0] and before["wave1"], "reset fixture owns a controller-created super wave")
        run(e, 3, ["start", "select"])
        frozen = sample(e)
        run(e, 40)
        s = sample(e)
        check(s["paused"] and s["ticks"] == frozen["ticks"] and s["superPhase"] == frozen["superPhase"]
              and s["wave_life1"] == frozen["wave_life1"],
              "Start plus Select pauses and freezes the real super and wave")
        run(e, 3, ["start", "select"])
        s = sample(e)
        check(not s["paused"] and s["superActive"][0] and s["energy1"] < 64,
              "Start plus Select resumes without resetting Training")
        run(e, 3)
        s = run(e, 3, ["select"])
        check(all(s[n] == [0, 0] for n in STATE),
              "live Training Select clears every private super byte", {n: s[n] for n in STATE})
        check(s["energy1"] == s["energy2"] == 64 and s["hp1"] == s["hp2"] == 128
              and not s["wave1"] and not s["wave2"] and s["action1"] == s["action2"] == 0,
              "Training reset restores ordinary meter health actions and waves")
        # Existing three-stage guide, read from actual VRAM after publication.
        run(e, 3)
        run(e, 3, ["start"])
        run(e, 3)
        run(e, 3, ["select"])
        run(e, 3)
        run(e, 3, ["select"])
        run(e, 16)
        memory = vram(e)
        def text(x, y, count):
            p = 0xB000 + (y * 32 + x) * 2
            return "".join(chr(int.from_bytes(memory[p+i*2:p+i*2+2], "little") & 0x7F) for i in range(count))
        command = "SUPER: Y+B NEUTRAL FULL 96"
        check(text(3, 7, len(command)) == command, "native move guide teaches the command and full cost",
              text(3, 7, len(command)))
        empty = memory[0x8000+(256+32)*32:0x8000+(257+32)*32]
        for char in sorted(set(command) - {" "}):
            pos = 0x8000 + (256+ord(char))*32
            check(memory[pos:pos+32] != empty,
                  "every command character has a visible native glyph", char)
        check(text(6, 16, len(NAMES[0])) == NAMES[0] and text(6, 21, len(NAMES[1])) == NAMES[1],
              "native move guide names both fighters' distinct supers")
        e.shot("expansion-07-guide.png")
        captures.append("docs/screenshots/expansion-07-guide.png")
        # P2 is deliberately ignored as gameplay input in Training.
        run(e, 3, ["start"])
        run(e, 3)
        full(e)
        s = run(e, 30, p2=["y", "b"])
        check(s["superActive"][1] == 0 and s["energy2"] == 96,
              "Training preserves ignored physical P2 attack input")
        return {"pause_freeze_tick": frozen["ticks"][0], "reset": "all 14 bytes zero",
                "guide": "docs/screenshots/expansion-07-guide.png"}
    finally:
        e.close()


def hurt_down_wake_dead():
    e = boot(1, 0, fighter2=0)
    result = {}
    try:
        position(e)
        full(e)
        run(e, 3, p2=["y"])
        for _ in range(20):
            s = sample(e)
            if s["hurt1"]:
                break
            step(e)
        check(s["hurt1"] > 0 and s["energy1"] == 96, "hurt fixture retains a naturally full gauge")
        s = run(e, 3, ["y", "b"])
        check(not s["superActive"][0] and s["energy1"] == 96,
              "fresh full-gauge chord cannot activate during real hitstun")
        run(e, 80, ["y", "b"])
        s = sample(e)
        check(not s["superActive"][0] and s["energy1"] == 96,
              "rejected hurt chord cannot become a delayed super")
        run(e, 3)
        position(e)
        run(e, 3, p2=["down", "x"])
        for _ in range(30):
            s = sample(e)
            if s["down_state1"]:
                break
            step(e)
        check(s["down_state1"] > 0 and s["energy1"] == 96,
              "ordinary controller uppercut creates the downed eligibility fixture")
        s = run(e, 3, ["y", "b"])
        check(not s["superActive"][0] and s["energy1"] == 96,
              "fresh full-gauge chord cannot activate while downed")
        run(e, 3)
        for _ in range(140):
            s = sample(e)
            if s["down_state1"] == 5:
                break
            step(e)
        check(s["down_state1"] == 5, "controller knockdown reaches native wake")
        s = run(e, 3, ["y", "b"])
        check(not s["superActive"][0] and s["energy1"] == 96 and s["superRequest"][0] == 0,
              "wake chord cannot queue a super through the ordinary wake buffer")
        s = run(e, 80, ["y", "b"])
        check(s["down_state1"] == 0 and s["invuln1"] == 0 and not s["superActive"][0],
              "held wake chord remains rejected through get-up and invulnerability")
        run(e, 3)
        fire(e, 0)
        result["hurt_down_wake"] = "rejects without spending; fresh grounded command works after wake"
    finally:
        e.close()
    e = boot(1, 3, fighter2=3)
    try:
        full(e)
        dead = None
        for _ in range(12):
            position(e)
            for tick in range(85):
                s = step(e, p2=["x"] if tick < 3 else [])
                if not s["hp1"]:
                    dead = s
                    break
            if dead:
                break
        check(dead is not None and dead["round_end"] > 0 and dead["energy1"] == 96,
              "controller strong punches produce an actual KO with full victim gauge")
        s = run(e, 3, ["y", "b"])
        check(s["hp1"] == 0 and s["energy1"] == 96 and not s["superActive"][0],
              "dead full-gauge fighter cannot activate or spend energy")
        result["dead"] = "rejects after actual controller KO"
    finally:
        e.close()
    return result


def ordinary_special_after_super():
    e = boot(1, 0, fighter2=0)
    try:
        position(e)
        full(e)
        fire(e, 0)
        run(e, 150)
        for _ in range(600):
            if sample(e)["energy1"] >= 32:
                break
            step(e)
        position(e)
        before = sample(e)
        hp = before["hp2"]
        events = []
        for tick in range(80):
            s = step(e, ["down", "y"] if tick < 3 else [])
            if tick == 0:
                check(s["action1"] == 7 and not s["superActive"][0]
                      and 31 <= before["energy1"] - s["energy1"] <= 32,
                      "ordinary quick special still uses its existing 32-energy command")
            if s["hp2"] != hp:
                events.append(hp - s["hp2"])
                hp = s["hp2"]
        # Damian's ordinary profile is 15 plus the retained power adjustment
        # (3-2), so the existing cartridge damage is 16, not the super's 12.
        check(events == [16] and s["superWaveDamage"] == [0, 0],
              "ordinary special after a super retains normal damage and clears projectile tags", events)
        return {"command": "Down+Y", "cost": 32, "damage": events}
    finally:
        e.close()


def contracts():
    shared = combined_contract(ROOT)
    check(True, "combined assets, native ABI and bounded appended allocations satisfy shared policy")
    check(all(SYMBOLS[name] == SYMBOLS[STATE[0]] + 2 * i for i, name in enumerate(STATE))
          and SYMBOLS["superWaveReach"] + 2 == SYMBOLS["superActive"] + 14,
          "seven bounded per-port arrays append exactly 14 mutable bytes")
    # Audit bank-local linked sections, including functions and asset streams.
    starts = {n[13:]: a for n, a in SYMBOLS.items() if n.startswith("SECTIONSTART_")}
    ends = {n[11:]: a for n, a in SYMBOLS.items() if n.startswith("SECTIONEND_")}
    sections = []
    intervals = []
    for n, a in starts.items():
        b = ends.get(n)
        if b is None or 0x7E0000 <= a < 0x800000 or a < 0x8000:
            continue
        size = b - a
        check(size <= 32768 and (a >> 16) == ((b - 1) >> 16),
              "linked ROM section fits one 32 KiB LoROM bank", {"name": n, "bytes": size})
        sections.append(size)
        offset = ((a >> 16) & 127) * 32768 + (a & 32767)
        intervals.append((offset, offset + size))
    merged = []
    for a, b in sorted(intervals):
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return {"combined": shared, "super_mutable_bytes_added": 14,
            "bank_local_sections": len(sections), "largest_section_bytes": max(sections),
            "unoccupied_bytes_outside_linked_sections": 4194304 - sum(b-a for a, b in merged)}


def main():
    global SYMBOLS
    started = time.time()
    SYMBOLS = symbols((ROOT / "dist/abaqus-after-hours.sym").read_text(encoding="utf-8"))
    report = {"feature": 7, "base": BASE, "command": "fresh simultaneous neutral grounded Y+B",
              "rom_sha256": hashlib.sha256((ROOT / "dist/abaqus-after-hours.sfc").read_bytes()).hexdigest(),
              "test_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "harness_sha256": {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in (
                  "tools/expansion_contracts.py", "tools/emulator.py", "tools/test_characters.py")},
              "source_sha256": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted((ROOT / 'src').rglob('*')) if p.is_file()},
              "symbols_sha256": hashlib.sha256((ROOT / 'dist/abaqus-after-hours.sym').read_bytes()).hexdigest(),
              "core_sha256": hashlib.sha256((ROOT / ".tools/core/snes9x_libretro.dll").read_bytes()).hexdigest(),
              "controller_only": True, "memory_writes": False, "save_states": False,
              "audio": "capture callbacks only; no device or GUI"}
    try:
        check(report['core_sha256'] == EXPECTED_NATIVE_CORE['dll_sha256'], 'pinned native Snes9x core')
        report["contracts"] = contracts()
        report["activation"] = [activation(i) for i in range(12)]
        report["hits"] = [contact(i, p, capture=(p == 0 and i in {0, 2, 5, 8, 11})) for i in range(12) for p in range(2)]
        report["blocks"] = [contact(i, p, guard=True, capture=(i == 3 and p == 1)) for i in range(12) for p in range(2)]
        report["whiffs"] = [whiff(i, p) for i in range(12) for p in range(2)]
        report["interruptions"] = [interrupt(i, p) for i in range(12) for p in range(2)]
        report["punish"] = punish()
        report["pause_reset"] = eligibility_pause_reset()
        report["hurt_down_wake_dead"] = hurt_down_wake_dead()
        report["ordinary_special_after_super"] = ordinary_special_after_super()
        check(not timing["cadence_failures"], "all monitored native frames advance exactly once per video callback", timing)
        check(not timing["overflow_failures"], "all monitored native pictures keep STAT77 OBJ overflow clear", timing)
        report['rom_sha256_after'] = hashlib.sha256((ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()).hexdigest()
        check(report['rom_sha256_after'] == report['rom_sha256'],
              'production ROM identity stays unchanged throughout the focused proof')
        report["status"] = "passed"
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = repr(exc)
        raise
    finally:
        report['captures'] = [{'path': path, 'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}
                              for path in captures]
        report["checks"] = len(checks)
        report["timing"] = timing
        report["elapsed_seconds"] = round(time.time() - started, 3)
        (ROOT / "docs/expansion-07-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({k: report[k] for k in ("status", "rom_sha256", "checks", "elapsed_seconds")}))


if __name__ == "__main__":
    main()
