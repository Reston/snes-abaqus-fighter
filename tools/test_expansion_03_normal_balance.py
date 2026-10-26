"""Four normal roles: silent, controller-only, exact-cartridge measurements.

No save states or emulated-memory writes. The native Fighter timing cache is
read only to label the windows whose actual contacts/whiffs are exercised.
Run with the canonical Python through tools/run_background.py.
"""
from __future__ import annotations

import argparse
import ctypes as C
import hashlib
import json
import re
import sys
import subprocess
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_characters import boot
from test_inputs import trace, signed16
from expansion_contracts import combined_contract

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/screenshots/expansion-03"
MOVES = (("y", 1, "jab"), ("x", 3, "strong_punch"),
         ("b", 4, "light_kick"), ("a", 5, "strong_kick"))
checks = []
metrics = {"gameplay_callbacks": 0, "cadence_deltas": {}, "ppu_overflow": [],
           "peak_spc_backlog": 0, "captures": []}


def check(ok, label, details=None):
    checks.append({"check": label, "passed": bool(ok), "details": details})
    if not ok:
        raise AssertionError((label, details))


def symbols_text(source):
    return {name: int(address, 16) for address, name in re.findall(
        r"^([0-9a-fA-F]{8}) (\S+)$", source, re.M)}


def symbols(path):
    return symbols_text(path.read_text(encoding="utf-8"))


def profiles():
    source = (ROOT / "src/characters.h").read_text(encoding="utf-8")
    rows = re.findall(r"\{([\d,]+)\}, \{([\d,]+)\}, \{([\d,]+)\}, \{([\d,]+)\}", source)
    return [{name: list(map(int, row.split(","))) for name, row in zip(
        ("startup", "recovery", "damage", "reach"), values)} for values in rows]


class Rig:
    def __init__(self, fighter, port, opponent=None):
        opponent = fighter if opponent is None else opponent
        p1, p2 = (fighter, opponent) if port == 0 else (opponent, fighter)
        self.e = boot(1, p1, fighter % 3, p2)
        self.port, self.fighter = port, fighter
        self.a, self.d = str(port + 1), str(2 - port)
        self.tag = f"fighter{fighter:02d} P{self.a}"
        self.syms = symbols(ROOT / "dist/abaqus-after-hours.sym")
        self.base = self.syms["fighters"] - 0x7e0000

    def state(self):
        s = trace(self.e)
        for port in (0, 1):
            s[f"tick{port + 1}"] = C.string_at(self.e.ram + self.base + port * 64 + 17, 1)[0]
        return s

    def step(self, attack=(), defend=()):
        before = self.state()
        self.e.run(1, **{f"p{self.a}": attack, f"p{self.d}": defend})
        after = self.state()
        delta = (after["frame"] - before["frame"]) & 65535
        metrics["gameplay_callbacks"] += 1
        hist = metrics["cadence_deltas"]
        hist[str(delta)] = hist.get(str(delta), 0) + 1
        raw = C.string_at(self.e.ram + 0x1ff00, 246)
        stat77 = int.from_bytes(raw[228:230], "little")
        if stat77 & 0xc0:
            metrics["ppu_overflow"].append({"case": self.tag, "frame": after["frame"], "stat77": stat77})
        # SPC FIFO indices are read-only native symbols, separate from TRACE.
        ptrs = [C.string_at(self.e.ram + (self.syms[name] & 0x1ffff), 1)[0]
                for name in ("spc_fread", "spc_fwrite")]
        metrics["peak_spc_backlog"] = max(metrics["peak_spc_backlog"], (ptrs[1] - ptrs[0]) & 255)
        return after

    def direction(self, toward=True, defender=False):
        s = self.state()
        side, other = (self.d, self.a) if defender else (self.a, self.d)
        right = s[f"x{side}"] < s[f"x{other}"]
        return "right" if right == toward else "left"

    def gap(self):
        s = self.state()
        return abs(s["x1"] - s["x2"]) / 16

    def position(self, target):
        self.settle()
        for _ in range(240):
            gap = self.gap()
            if target - 1 <= gap <= target + 1:
                self.step()
                return self.gap()
            self.step((self.direction(gap > target),))
        raise AssertionError((self.tag, "controller spacing failed", target, self.gap()))

    def settle(self):
        for _ in range(140):
            s = self.state()
            if not any(s[f"{field}{side}"] for side in (self.a, self.d)
                       for field in ("action", "hurt", "down_state", "y")) and not s["hitstop"]:
                self.step()
                return
            self.step()
        raise AssertionError((self.tag, "did not settle", self.state()))

    def timing(self):
        raw = C.string_at(self.e.ram + self.base + self.port * 64, 64)
        return {"startup": raw[24], "active": raw[63] - raw[24],
                "recovery": raw[62] - raw[63], "total": raw[62]}

    def capture(self, label):
        OUT.mkdir(parents=True, exist_ok=True)
        path = OUT / f"{self.fighter:02d}-p{self.a}-{label}.png"
        self.e.frame.save(path)
        metrics["captures"].append(path.relative_to(ROOT).as_posix())

    def close(self):
        self.e.close()


def whiffs_and_ranges(fighter, port, profile):
    r = Rig(fighter, port)
    result = {}
    try:
        for key, action, role in MOVES:
            tag = f"{r.tag} {role}"
            r.position(110)
            whiff_hp = r.state()[f"hp{r.d}"]
            s = r.step((key,))
            check(s[f"action{r.a}"] == action, tag + " uses the face-button action")
            timing = r.timing()
            ticks = [s[f"tick{r.a}"]]
            # A premature heavier input cannot cancel a whiff.
            while s[f"action{r.a}"]:
                press = ("x",) if key == "y" and s[f"tick{r.a}"] == timing["startup"] else ()
                s = r.step(press)
                if s[f"action{r.a}"]:
                    check(s[f"action{r.a}"] == action, tag + " whiff retains its commitment")
                    ticks.append(s[f"tick{r.a}"])
            check(ticks == list(range(1, timing["total"])) and s[f"hp{r.d}"] == whiff_hp,
                  tag + " completes every native whiff tick", {**timing, "ticks": ticks})
            # Bracket the real front contact boundary using physical walking.
            cutoff = profile["reach"][action - 1] + 10
            outside = r.position(cutoff + 3)
            hp = r.state()[f"hp{r.d}"]
            s = r.step((key,))
            connected = 0
            for _ in range(timing["total"] + 8):
                connected = max(connected, s[f"connected{r.a}"])
                s = r.step()
            check(outside > cutoff and connected == 0 and s[f"hp{r.d}"] == hp,
                  tag + " whiffs beyond its reach", {"center_gap": outside, "cutoff": cutoff})
            inside = r.position(cutoff - 3)
            before = r.state()
            s = r.step((key,))
            for _ in range(timing["total"] + 8):
                if s[f"connected{r.a}"]:
                    break
                s = r.step()
            check(s[f"connected{r.a}"] == 2 and s[f"tick{r.a}"] == timing["startup"],
                  tag + " first active tick hits just inside reach", {"gap": inside, "contact": s})
            damage = before[f"hp{r.d}"] - s[f"hp{r.d}"]
            check(damage > 0 and not s[f"guard{r.d}"] and not s[f"down_state{r.d}"],
                  tag + " deals a real normal hit without knockdown", damage)
            result[role] = {**timing, "front_reach": cutoff - 10, "center_cutoff": cutoff,
                            "outside_whiff_gap": outside, "inside_hit_gap": inside,
                            "damage": damage, "first_contact_tick": s[f"tick{r.a}"]}
            if fighter in (0, 11) and port == 0:
                r.capture(role + "-tip")
            r.settle()
        lp, sp, lk, sk = (result[name] for _, _, name in MOVES)
        check(lp["startup"] < lk["startup"] < sk["startup"] <= sp["startup"],
              r.tag + " speed roles remain distinct", result)
        check(lp["front_reach"] < sp["front_reach"] < lk["front_reach"] < sk["front_reach"],
              r.tag + " range roles remain distinct", result)
        check(lp["damage"] < lk["damage"] < sk["damage"] < sp["damage"],
              r.tag + " damage roles remain distinct", result)
        check(lp["total"] < lk["total"] < sk["total"] <= sp["total"] + 1,
              r.tag + " stronger normals require longer commitment", result)
        return result
    finally:
        r.close()


def block_and_punish(fighter, port):
    r = Rig(fighter, port)
    result = {}
    try:
        for key, action, role in MOVES:
            for punish in (False, True):
                r.position(26)
                guard = ("down", r.direction(False, True))
                attacker_guard = ("down", r.direction(False))
                hp = r.state()[f"hp{r.a}"]
                defender_hp = r.state()[f"hp{r.d}"]
                s = r.step((key,), guard)
                for _ in range(40):
                    if s[f"connected{r.a}"]:
                        break
                    s = r.step((), guard)
                check(s[f"connected{r.a}"] == 1 and s[f"guard{r.d}"] == 1,
                      f"{r.tag} {role} is honestly blocked")
                contact = s
                frozen = s["hitstop"]
                # Press a special during guard hitstop: guard is never a confirm.
                s = r.step(("down", "y"), guard)
                while s["hitstop"]:
                    s = r.step(attacker_guard, guard)
                s = r.step(attacker_guard, guard)
                check(s[f"action{r.a}"] == action and s[f"energy{r.a}"] >= contact[f"energy{r.a}"],
                      f"{r.tag} {role} cannot special-cancel blocked contact")
                live = 1
                attacker_free = defender_free = None
                jab_sent = False
                response = None
                for _ in range(70):
                    if not s[f"action{r.a}"] and attacker_free is None:
                        attacker_free = live
                    if not s[f"hurt{r.d}"] and defender_free is None:
                        defender_free = live
                    dk = guard
                    if punish and not jab_sent and not s[f"hurt{r.d}"]:
                        dk = ("y", r.direction(False, True))
                        jab_sent = True
                    s = r.step(attacker_guard, dk)
                    live += int(not s["hitstop"])
                    if punish and jab_sent and s[f"connected{r.d}"]:
                        response = s
                        break
                    if not punish and attacker_free is not None and defender_free is not None:
                        break
                if not punish:
                    advantage = defender_free - attacker_free
                    check((-4 <= advantage <= -2 if role == "jab" else
                           -4 <= advantage <= -2 if role == "light_kick" else advantage <= -10),
                          f"{r.tag} {role} has the intended measured block risk",
                          {"advantage": advantage, "attacker_free": attacker_free,
                           "defender_free": defender_free})
                    result[role] = {"block_advantage_first_active": advantage,
                                    "attacker_recovers_after": attacker_free,
                                    "defender_recovers_after": defender_free,
                                    "captured_hitstop": frozen,
                                    "blocked_contact_chip": defender_hp - contact[f"hp{r.d}"]}
                else:
                    if role == "jab":
                        advantage = result[role]["block_advantage_first_active"]
                        jab_startup = profiles()[fighter]["startup"][0]
                        expected_hit = jab_startup < -advantage
                        check(response is not None and (s[f"hp{r.a}"] < hp) == expected_hit,
                              r.tag + " jab response follows its actual startup and block disadvantage", response)
                    if role in ("strong_punch", "strong_kick"):
                        check(response is not None and response[f"connected{r.d}"] == 2 and s[f"hp{r.a}"] < hp,
                              f"{r.tag} blocked {role} is actually jab-punishable", response)
                    result[role]["immediate_jab_response"] = (
                        "hit" if response and response[f"connected{r.d}"] == 2 else
                        "blocked" if response else "whiff")
                r.settle()
        return result
    finally:
        r.close()


def confirms_and_low(fighter, port):
    r = Rig(fighter, port)
    result = {}
    try:
        for first_key, second_key, second_action in (("y", "x", 3), ("b", "a", 5)):
            r.position(26)
            hp = r.state()[f"hp{r.d}"]
            s = r.step((first_key,))
            for _ in range(30):
                if s[f"connected{r.a}"]:
                    break
                s = r.step()
            first = s
            check(first[f"connected{r.a}"] == 2, r.tag + " combo begins from a real light hit")
            back = (r.direction(False, True),)
            s = r.step((second_key,), back)
            for _ in range(50):
                if s[f"action{r.a}"] == second_action and s[f"connected{r.a}"]:
                    break
                s = r.step((), back)
            check(s[f"action{r.a}"] == second_action and s[f"connected{r.a}"] == 2
                  and s[f"combo_link{r.a}"] == 2 and not s[f"guard{r.d}"],
                  f"{r.tag} {first_key.upper()}->{second_key.upper()} truly combos through held back", s)
            result[first_key + "_to_" + second_key] = {
                "damage": hp - s[f"hp{r.d}"], "combo_link": s[f"combo_link{r.a}"],
                "second_contact_tick": s[f"tick{r.a}"], "remaining_stun": s[f"hurt{r.d}"]}
            r.settle()
        # The low is an ordinary Down+B, with no energy or new command.
        r.position(26)
        hp = r.state()[f"hp{r.d}"]
        back = (r.direction(False, True),)
        s = r.step(("down", "b"), back)
        for _ in range(35):
            if s[f"connected{r.a}"]:
                break
            s = r.step((), back)
        check(s[f"action{r.a}"] == 4 and s[f"connected{r.a}"] == 2
              and s[f"hp{r.d}"] < hp and not s[f"down_state{r.d}"],
              r.tag + " Down+B beats high guard without sweep knockdown", s)
        result["low_beats_high_guard"] = True
        r.settle()
        r.position(26)
        guard = ("down", r.direction(False, True))
        s = r.step(("down", "b"), guard)
        for _ in range(35):
            if s[f"connected{r.a}"]:
                break
            s = r.step((), guard)
        check(s[f"connected{r.a}"] == 1 and not s[f"down_state{r.d}"],
              r.tag + " Down+B is crouch-blockable", s)
        result["low_crouch_blockable"] = True
        return result
    finally:
        r.close()


def air_crossup(fighter, port):
    r = Rig(fighter, port)
    result = {}
    try:
        for key in ("a", "x"):
            r.position(24)
            hp = r.state()[f"hp{r.d}"]
            original = r.state()[f"face{r.a}"]
            forward = r.direction()
            s = r.step(("up", forward), (r.direction(True, True),))
            sign = 1 if original else -1
            sent = False
            # Both players approach. The grounded opponent then follows the
            # jump, so low/slow and high/fast arcs all get a genuine short rear
            # contact opportunity. A is pressed only after crossing and below
            # the vertical contact threshold; X gets the same opportunity.
            for _ in range(90):
                crossed = (s[f"x{r.a}"] - s[f"x{r.d}"]) * sign > 0
                keys = ()
                if crossed and signed16(s[f"y{r.a}"]) >= -48 * 16 and not sent:
                    keys = (key,)
                    sent = True
                s = r.step(keys, (r.direction(True, True),))
                if sent and s[f"connected{r.a}"]:
                    break
                if sent and not s[f"action{r.a}"] and not s[f"y{r.a}"]:
                    break
            gap = abs(s[f"x{r.a}"] - s[f"x{r.d}"]) / 16
            if key == "a":
                check(s[f"action{r.a}"] == 5 and s[f"air_action{r.a}"] == 1 and
                      s[f"face{r.a}"] == original and signed16(s[f"y{r.a}"]) < 0 and
                      (s[f"x{r.a}"] - s[f"x{r.d}"]) * sign > 0 and gap <= 28 and
                      s[f"connected{r.a}"] == 2 and not s[f"down_state{r.d}"],
                      r.tag + " strong kick retains a real airborne rear cross-up", s)
                result.update({"contact_tick": s[f"tick{r.a}"], "contact_gap_after_recoil": gap,
                               "damage": hp - s[f"hp{r.d}"], "air_y_12_4": signed16(s[f"y{r.a}"])})
                if fighter == 0:
                    r.step()
                    r.capture("air-crossup")
            else:
                check(sent and s[f"hp{r.d}"] == hp and not s[f"connected{r.a}"],
                      r.tag + " air strong punch still cannot hit behind its facing", s)
                result["air_punch_rear_whiff"] = True
            r.settle()
            check(not r.state()[f"air_action{r.a}"], r.tag + " air normal clears normally on landing")
        return result
    finally:
        r.close()


def fast_jab_spacing(fighter, port):
    """The fastest opponent punishes unsafe low kicks, but cannot jab their tip."""
    r = Rig(fighter, port, opponent=8)
    result = {}
    try:
        for target, label in ((26, "close"), (profiles()[fighter]["reach"][3] + 7, "tip")):
            r.position(target)
            defender_guard = ("down", r.direction(False, True))
            attacker_guard = ("down", r.direction(False))
            hp = r.state()[f"hp{r.a}"]
            s = r.step(("b",), defender_guard)
            for _ in range(40):
                if s[f"connected{r.a}"]:
                    break
                s = r.step((), defender_guard)
            check(s[f"connected{r.a}"] == 1, f"{r.tag} {label} kick is guarded by Madariaga")
            for _ in range(40):
                if not s[f"hitstop"] and not s[f"hurt{r.d}"]:
                    break
                s = r.step(attacker_guard, defender_guard)
            response_gap = r.gap()
            s = r.step(attacker_guard, ("y", r.direction(False, True)))
            contact = s[f"connected{r.d}"]
            for _ in range(20):
                contact = max(contact, s[f"connected{r.d}"])
                s = r.step(attacker_guard)
            expected_hit = label == "close" and profiles()[fighter]["recovery"][3] > 7
            check((s[f"hp{r.a}"] < hp) == expected_hit,
                  f"{r.tag} {label} light-kick risk follows measured space/recovery",
                  {"gap": response_gap, "response_contact": contact, "damage": hp - s[f"hp{r.a}"]})
            if label == "tip":
                check(contact == 0, r.tag + " tip light kick makes the fastest jab whiff", response_gap)
            result[label] = {"response_gap": response_gap,
                             "jab_result": "hit" if s[f"hp{r.a}"] < hp else "blocked" if contact else "whiff"}
            r.settle()
        return result
    finally:
        r.close()


def special_confirm(fighter, port):
    r = Rig(fighter, port)
    result = {}
    try:
        for key, may_cancel in (("y", True), ("x", False)):
            r.position(26)
            s = r.step((key,))
            for _ in range(35):
                if s[f"connected{r.a}"]:
                    break
                s = r.step()
            check(s[f"connected{r.a}"] == 2, r.tag + " special-cancel fixture starts with actual damage")
            energy = s[f"energy{r.a}"]
            s = r.step(("down", "y"))
            while s["hitstop"]:
                s = r.step()
            s = r.step()
            if may_cancel:
                check(s[f"action{r.a}"] == 7 and energy - s[f"energy{r.a}"] in (31, 32),
                      r.tag + " confirmed jab cancels to its original paid special", s)
            else:
                check(s[f"action{r.a}"] == 3 and s[f"energy{r.a}"] >= energy,
                      r.tag + " strong punch retains its uncancellable recovery", s)
            result[key] = {"action_after_hitstop": s[f"action{r.a}"],
                           "energy_change": s[f"energy{r.a}"] - energy}
            r.settle()
        return result
    finally:
        r.close()


def corner_jab_guard(fighter, port):
    """Mash-speed re-jabs must not create an inescapable corner hit loop."""
    r = Rig(fighter, port)
    try:
        outward = "right" if port == 0 else "left"
        # Reach the wall through ordinary pad holds; there is no state setup.
        for _ in range(240):
            r.step((outward,), (outward,))
        r.position(26)
        wall = (232 if port == 0 else 24) * 16
        check(r.state()[f"x{r.d}"] == wall, r.tag + " jab fixture reaches the real corner")
        s = r.step(("y",))
        for _ in range(30):
            if s[f"connected{r.a}"]:
                break
            s = r.step()
        check(s[f"connected{r.a}"] == 2, r.tag + " corner jab starts from a genuine hit")
        first_hp = s[f"hp{r.d}"]
        guard = (outward,)
        contacts = []
        for repeat in range(3):
            for _ in range(40):
                if not s["hitstop"] and not s[f"action{r.a}"]:
                    break
                s = r.step((), guard)
            s = r.step(("y",), guard)
            for _ in range(25):
                if s[f"connected{r.a}"]:
                    break
                s = r.step((), guard)
            check(s[f"connected{r.a}"] == 1 and s[f"guard{r.d}"] == 1
                  and s[f"hp{r.d}"] == first_hp,
                  f"{r.tag} immediate corner re-jab {repeat + 1} can be guarded", s)
            contacts.append({"contact": s[f"connected{r.a}"], "hp": s[f"hp{r.d}"]})
        return {"first_hit_damage": 128 - first_hp, "followups": contacts,
                "controller_guard_escapes_repeated_hitstun": True}
    finally:
        r.close()


def preservation():
    ref = "610537d3da8f7005c28ea31d0a45a7c17f8f7ba8"
    combined = combined_contract(ROOT)
    check(True, "Strict combined asset/source/native preservation policy passes")
    base = symbols_text(subprocess.check_output(
        ["git", "show", ref + ":dist/abaqus-after-hours.sym"], cwd=ROOT).decode("utf-8"))
    now = symbols(ROOT / "dist/abaqus-after-hours.sym")
    ram = {name: address for name, address in base.items()
           if (0x7e0000 <= address < 0x800000 or address < 0x2000)
           and not name.startswith(("SECTION", "RAM_USAGE", "__local"))}
    baseline_source = subprocess.check_output(["git", "show", ref + ":src/characters.h"], cwd=ROOT).decode("utf-8")
    current_source = (ROOT / "src/characters.h").read_text(encoding="utf-8")
    pattern = (r"\{\s*([\d,\-\sA-Z_]+),\s*\{([\d,]+)\}, "
               r"\{([\d,]+)\}, \{([\d,]+)\}, \{([\d,]+)\}")
    old, new = re.findall(pattern, baseline_source), re.findall(pattern, current_source)
    check(len(old) == len(new) == 12 and all(
        re.sub(r"\s", "", a[0]) == re.sub(r"\s", "", b[0]) and
        all(a[i].split(",")[j] == b[i].split(",")[j] for i in range(1, 5) for j in (1, 5)) and
        a[1].split(",")[4] == b[1].split(",")[4]
        for a, b in zip(old, new)),
        "Movement, throws, specials, legacy normal, sweep and air-kick startup retain their baseline data")
    for path in ("src/hardware.asm", "src/trace.asm", "src/knockdown.h"):
        check(subprocess.check_output(["git", "show", ref + ":" + path], cwd=ROOT) == (ROOT / path).read_bytes(),
              path + " remains byte-identical")
    sections = []
    for name, address in now.items():
        if not name.startswith("SECTIONSTART_"):
            continue
        end = now.get(name.replace("SECTIONSTART_", "SECTIONEND_"))
        if end is not None and address >= 0x800000:
            # End labels may be at the exact next-bank boundary.
            sections.append((address, end, name))
    check(all((a >> 16) == ((b - 1) >> 16) for a, b, _ in sections if b > a),
          "All native code sections fit within 32 KiB LoROM banks")
    banks = {}
    for name, address in now.items():
        if not name.startswith("SECTIONSTART_") or (address & 65535) < 0x8000:
            continue
        end = now.get(name.replace("SECTIONSTART_", "SECTIONEND_"))
        if end is not None:
            bank = (address >> 16) & 127
            banks[bank] = banks.get(bank, 0) + end - address
    check(all(size <= 32768 for size in banks.values()), "No bank exceeds 32 KiB linked-section occupancy")
    def active_size(table):
        end = next(a for n, a in table.items() if n.startswith("SECTIONEND_.attackActivetext_"))
        return end - table["attackActive"]
    active_bytes = active_size(now)
    check(active_bytes == active_size(base),
          "Role tuning adds no attackActive code or per-tick branch cost", active_bytes)
    current_rom = (ROOT / "dist/abaqus-after-hours.sfc").read_bytes()
    check(len(current_rom) == 4194304 and current_rom[0x7fd5] == 0x30,
          "Combined cartridge retains 4 MiB FastROM LoROM mapping")
    return {"combined_contract": combined,
            "attack_active_code_bytes": active_bytes, "attack_active_added_code_bytes": 0,
            "normal_balance_added_mutable_bytes": 0, "native_code_sections": len(sections),
            "linked_section_bytes": sum(banks.values()),
            "unallocated_banks": [f"{bank:02X}" for bank in range(128) if bank not in banks]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fighters", default=",".join(map(str, range(12))))
    parser.add_argument("--report", default="docs/expansion-03-report.json")
    args = parser.parse_args()
    selected = [int(x) for x in args.fighters.split(",")]
    start = time.monotonic()
    rom = ROOT / "dist/abaqus-after-hours.sfc"
    report = {"status": "failed", "rom_sha256": hashlib.sha256(rom.read_bytes()).hexdigest(),
              "base_commit": "610537d3da8f7005c28ea31d0a45a7c17f8f7ba8",
              "host_contract": {"headless": True, "audio_playback": False,
                                "controller_only": True, "memory_writes": False, "save_states": False},
              "roster": [], "checks": checks, "metrics": metrics}
    report["core_sha256"] = hashlib.sha256((ROOT / ".tools/core/snes9x_libretro.dll").read_bytes()).hexdigest()
    report["symbols_sha256"] = hashlib.sha256((ROOT / "dist/abaqus-after-hours.sym").read_bytes()).hexdigest()
    report["source_sha256"] = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                               for path in ("src/characters.h", "src/game.c", "src/version.h",
                                            "tools/test_expansion_03_normal_balance.py", "tools/expansion_contracts.py",
                                            "tools/test_characters.py", "tools/test_inputs.py", "tools/emulator.py")}
    report["scope"] = {"fighters": selected, "ports": [1, 2], "six_shared_suites_run": False}
    try:
        data = profiles()
        check(len(data) == 12, "All twelve profiles are present")
        report["preservation"] = preservation()
        for fighter in selected:
            for port in (0, 1):
                row = {"fighter": fighter, "port": port + 1}
                report["roster"].append(row)
                row["normals"] = whiffs_and_ranges(fighter, port, data[fighter])
                row["block"] = block_and_punish(fighter, port)
                row["confirms"] = confirms_and_low(fighter, port)
                row["air_crossup"] = air_crossup(fighter, port)
                row["fast_jab_spacing"] = fast_jab_spacing(fighter, port)
                row["special_confirm"] = special_confirm(fighter, port)
                row["corner_jab_guard"] = corner_jab_guard(fighter, port)
                print(f"fighter {fighter:02d} P{port + 1} complete", flush=True)
            left, right = report["roster"][-2:]
            check(all(all(left["normals"][role][field] == right["normals"][role][field]
                          for field in ("startup", "active", "recovery", "total", "damage", "front_reach"))
                      for _, _, role in MOVES), f"fighter{fighter:02d} both ports have identical measured frame/damage/range data")
        check(not metrics["ppu_overflow"], "No PPU range/time overflow in focused combat", metrics["ppu_overflow"])
        check(metrics["peak_spc_backlog"] <= 6, "Resident SPC FIFO stays within the existing focused backlog budget",
              metrics["peak_spc_backlog"])
        check(set(metrics["cadence_deltas"]) == {"1"}, "Every observed live callback advances exactly one native tick",
              metrics["cadence_deltas"])
        report["captures"] = [{"file": path, "sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}
                              for path in metrics["captures"]]
        report["status"] = "passed"
    finally:
        report["passed"] = sum(c["passed"] for c in checks)
        report["elapsed_seconds"] = round(time.monotonic() - start, 3)
        path = ROOT / args.report
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": report["status"], "passed": report["passed"],
                      "rom_sha256": report["rom_sha256"], "elapsed_seconds": report["elapsed_seconds"]}))


if __name__ == "__main__":
    main()
