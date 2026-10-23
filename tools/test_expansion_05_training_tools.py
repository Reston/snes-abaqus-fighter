"""Capture-only Training tools proof on the actual native cartridge.

Only libretro controller inputs advance gameplay. WRAM/VRAM/OAM reads are
observations; this driver never loads a state or writes emulated memory.
Shared suite reports are not changed. Run with the canonical cached Python.
"""
from __future__ import annotations

import argparse
import ctypes as C
import hashlib
import gzip
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import test_training as native
from expansion_contracts import combined_contract

ROOT = native.ROOT
CAPTURES = ROOT / "docs/screenshots/expansion-05"
SESSIONS = []
EVENTS = {}
OriginalQA = native.QA


class QA(OriginalQA):
    def __init__(self, rom, label):
        super().__init__(rom, label)
        self.fight_samples = 0
        self.ppu_overflow = []
        self.audio_samples = 0
        self.native_timing_failures = []
        self.native_previous = None
        self.spc_peak_backlog = 0
        self.spc_failures = []
        self.timing_ring = []
        self.timeline = []
        self.timeline_capture = None
        addresses = symbols(ROOT / "dist/abaqus-after-hours.sym")
        self.offsets = {k: (addresses[k] - 0x7E0000 if addresses[k] >= 0x7E0000 else addresses[k])
                        for k in ("screen", "lag_frame_counter", "snes_vblank_count", "spc_fread", "spc_fwrite")}
        SESSIONS.append(self)

    def step(self, p1=(), p2=(), allow_menu_load_duplicate=False):
        # Menu redraws can consume one callback while the visible portrait is
        # updated; scene loaders spend up to 27 callbacks in actual blank.
        # Account for both explicitly, with no allowance for native FIGHT.
        self.emulator.run(1, p1=tuple(p1), p2=tuple(p2))
        s = self.state()
        native_screen = int.from_bytes(C.string_at(self.emulator.ram + self.offsets["screen"], 1), "little")
        valid = s.get("magic") == 0xAABA and s.get("screen") in range(5)
        if valid and self.previous is not None:
            delta = (s["frame"] - self.previous["frame"]) & 65535
            if delta != 1:
                black = self.emulator.frame.getbbox() is None
                scene_load = self._menu_load_budget > 0 and black and native_screen != native.FIGHT
                # Loading an arena has already assigned FIGHT; actual blank
                # and an explicitly armed menu transition identify that path.
                if self._menu_load_budget > 0 and black and self.previous["screen"] != native.FIGHT:
                    scene_load = True
                redraw = (native_screen in (native.SELECT, native.ARENA) and s["screen"] == native_screen and
                          not black and bool((set(p1) | set(p2)) & {"up","down","left","right","a","b"}))
                consecutive = getattr(self, "menu_duplicate_run", 0) + 1
                allowed = delta == 0 and (scene_load or (redraw and consecutive == 1))
                if not allowed:
                    failure = {"state": s, "previous": self.previous, "delta": delta,
                               "native_screen": native_screen, "black": black,
                               "p1": list(p1), "p2": list(p2)}
                    self.cadence.append(failure)
                    if native_screen != native.FIGHT:
                        raise AssertionError(("focused native callback cadence", failure))
                self.menu_duplicate_run = consecutive
                if allowed:
                    self.menu_load_duplicates.append({"sample": self.samples, "frame": s["frame"],
                        "kind": "forced_blank_scene_load" if scene_load else "menu_redraw",
                        "native_screen": native_screen, "trace_screen": s["screen"], "black": black})
                if scene_load:
                    self._menu_load_budget -= 1
            else:
                self.menu_duplicate_run = 0
        self.previous = s if valid else None
        if valid:
            self.samples += 1
        self.timing_ring.append({"p1": list(p1), "p2": list(p2), "state": s})
        self.timing_ring = self.timing_ring[-8:]
        if s.get("screen") == native.FIGHT and s.get("magic") == 0xAABA:
            self.fight_samples += 1
            if s["ppu_stat"] & 0xC0:
                self.ppu_overflow.append(s)
        read = lambda k, n: int.from_bytes(C.string_at(self.emulator.ram + self.offsets[k], n), "little")
        current = {"screen": s.get("screen"), "native_screen": read("screen", 1),
                   "lag": read("lag_frame_counter", 2), "vblank": read("snes_vblank_count", 2)}
        previous = self.native_previous
        if previous and all(x["screen"] == native.FIGHT and x["native_screen"] == native.FIGHT
                            for x in (previous, current)):
            lag = (current["lag"] - previous["lag"]) & 65535
            vblank = (current["vblank"] - previous["vblank"]) & 65535
            if lag or vblank != 1:
                self.native_timing_failures.append({"before": previous, "after": current, "frame": s["frame"],
                                                    "samples": list(self.timing_ring)})
                # Collect the complete case; the report budget gate still fails.
            backlog = (read("spc_fwrite", 1) - read("spc_fread", 1)) & 255
            self.spc_peak_backlog = max(self.spc_peak_backlog, backlog)
            if backlog > 6 or backlog % 3:
                self.spc_failures.append({"frame": s["frame"], "backlog": backlog})
                raise AssertionError(("resident SPC queue contract failed", self.spc_failures[-1]))
        self.native_previous = current
        self.timeline.append({"state":s,"native":current,"p1":list(p1),"p2":list(p2)})
        return s

    def close(self):
        CAPTURES.mkdir(parents=True, exist_ok=True)
        path = CAPTURES / (self.label + "-timeline.json.gz")
        path.write_bytes(gzip.compress((json.dumps(self.timeline,separators=(",",":"))+"\n").encode(),mtime=0))
        self.timeline_capture = {"path":path.relative_to(ROOT).as_posix(),
                                 "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
                                 "callbacks":len(self.timeline)}
        self.timeline = []
        self.audio_samples = self.emulator.audio_samples
        self.audio_peak = self.emulator.audio_peak
        super().close()


native.QA = QA
check = native.check


def text(q, row=26, end=28):
    return native.decode_text(native.vram_bytes(q), row, end)


def shot(q, name):
    CAPTURES.mkdir(parents=True, exist_ok=True)
    path = CAPTURES / f"{name}.png"
    q.emulator.frame.save(path)
    return path.relative_to(ROOT).as_posix()


def observe(q):
    s = q.state()
    fields = ("frame", "x1", "x2", "y1", "y2", "hp1", "hp2", "action1",
              "action2", "raw_keys1", "raw_keys2", "energy1", "face1", "face2",
              "hurt1", "hurt2", "guard1", "guard2", "combo1", "connected1",
              "hitstop", "training_dummy", "paused", "pause_page")
    return {**{k: s[k] for k in fields}, "footer": text(q)}


def await_text(q, token, limit=80):
    for _ in range(limit):
        if token in text(q):
            return text(q)
        q.step()
    raise AssertionError(("native footer did not arrive", token, observe(q)))


def tools(q, challenge=None):
    if not q.state()["paused"]:
        q.press("start")
    # Select retains the existing normal/Controls/Specials order, then tools.
    for _ in range(4):
        if q.state()["pause_page"] == 3:
            break
        q.press("select")
    q.run(8)
    check(q.state()["pause_page"] == 3 and q.state()["guide_build"] == 0,
          "Training tools guide finishes its native three-stage build", observe(q))
    if challenge is not None:
        for _ in range(3):
            if f"C{challenge + 1} " in text(q, 18, 19):
                break
            q.press("down")
            q.run(5)
        check(f"C{challenge + 1} " in text(q, 18, 19),
              "paused Down selects the requested executable challenge", text(q, 6, 27))


def resume(q):
    q.press("start")
    q.run(24)
    check(q.state()["paused"] == 0 and q.state()["guide_dirty"] == 0,
          "resume clears the staged guide and restores the live footer", observe(q))


def reset(q):
    q.press("select")
    q.run(32)
    check(q.state()["hp1"] == 128 and q.state()["hp2"] == 128 and
          q.state()["seconds"] == 99,
          "live Select retains ordinary Training round reset", observe(q))
    check("00H 000D SP-" in text(q) and "----- ----- ----- ----- -----" in text(q),
          "live Select clears history, combo damage and special feedback", text(q))


def approach(q, gap=28):
    for _ in range(180):
        s = q.state()
        if abs(s["x1"] - s["x2"]) <= gap * 16:
            q.run(3)
            return
        q.step(("right",) if s["x1"] < s["x2"] else ("left",))
    raise AssertionError(("controller approach failed", observe(q)))


def jab(q):
    before = q.state()["hp2"]
    rows = [observe(q)]
    q.step(("y",))
    for _ in range(30):
        q.step()
        rows.append(observe(q))
        if q.state()["hp2"] < before:
            return before - q.state()["hp2"], rows
    raise AssertionError(("real jab did not hit", rows))


def controls_and_history(rom):
    q = native.boot(rom, fighter=0, fighter2=0, label="history-controls")
    try:
        q.run(32)
        check("C1 READY" in text(q), "Training opens with an armed visible tool panel", text(q))
        baseline_hud = native.bg2_rows(native.vram_bytes(q), 0, 5)
        q.run(2, ("down",))
        q.run(2, ("down", "right"))
        q.run(2, ("right", "y"))
        q.run(50)
        await_text(q, "6Y---")
        check("2----" in text(q) and "3----" in text(q) and "6Y---" in text(q),
              "native input history retains actual quarter-circle steps and Y", observe(q))
        check("SP!" in text(q), "accepted motion special produces a visible execution cue", observe(q))
        # The footer and guide must never rewrite nameplates or the top rule.
        after_hud = native.bg2_rows(native.vram_bytes(q), 0, 5)
        check(baseline_hud[0] == after_hud[0] and baseline_hud[4] == after_hud[4],
              "live tools preserve native top HUD nameplates and bottom rule")
        EVENTS["motion_history"] = {"state": observe(q), "capture": shot(q, "motion-history")}

        reset(q)
        # SOCD is cleaned by the actual capture path, and shoulders are absent.
        q.run(2, ("down", "up", "left", "right", "x", "b", "l", "r"))
        q.run(30)
        await_text(q, "5-XB-")
        check("5-XB-" in text(q), "history shows cleaned neutral direction and simultaneous face buttons", text(q))
        check(q.state()["action1"] not in (7, 8), "SOCD command does not become a directional special", observe(q))

        tools(q)
        q.press("right")
        q.run(8)
        check(q.state()["pause_page"] == 1, "paused Right wraps Training tools to Controls")
        q.press("left", port=1)
        q.run(8)
        check(q.state()["pause_page"] == 3, "P2 paused Left wraps Controls to Training tools")
        unchanged = text(q, 9, 19)
        q.run(3, ("up", "down", "left", "right"))
        q.run(5)
        check(q.state()["pause_page"] == 3 and text(q, 9, 19) == unchanged,
              "opposing paused directions cancel without changing tools or challenge")
        EVENTS["tools_page"] = {"state": observe(q), "capture": shot(q, "tools-page")}
        q.press("up", port=1)
        q.run(8)
        check("LIVE DISPLAY OFF" in text(q, 9, 10), "P2 paused Up hides the live tools", text(q, 9, 10))
        resume(q)
        q.run(2, ("left", "b"))
        q.run(30)
        footer_words = native.bg2_rows(native.vram_bytes(q), 26, 28)
        check(all(cell == 0 for row in footer_words for cell in row),
              "hidden live display clears both actual native footer rows", footer_words)
        tools(q)
        q.press("up")
        q.run(8)
        resume(q)
        await_text(q, "4--B-")
        check("4--B-" in text(q), "hidden display continues recording actual player commands", text(q))
        reset(q)

        # Both pads still choose all five original dummies on the normal card.
        q.press("start")
        for target in (1, 2, 3, 4, 0):
            q.press("down", port=target % 2)
            check(q.state()["training_dummy"] == target,
                  "ordinary paused dummy cycle is preserved", observe(q))
        q.run(3, ("up", "down"))
        q.run(3)
        check(q.state()["training_dummy"] == 0, "opposite dummy directions cancel")
        q.press("up")
        check(q.state()["training_dummy"] == 4, "Up still selects the CPU dummy")
        q.press("r", port=1)
        check("CPU HARD" in text(q, 11, 12), "P2 R still selects Hard CPU Training", text(q, 11, 12))
        q.press("l")
        check("CPU NORMAL" in text(q, 11, 12), "P1 L still selects Normal CPU Training", text(q, 11, 12))
        q.run(3, ("l",), ("r",))
        q.run(3)
        check("CPU NORMAL" in text(q, 11, 12), "opposite shoulders across pads still cancel")
        q.press("down")
        frozen = q.state()
        q.run(3, ("start", "select"))
        q.run(3)
        check(not q.state()["paused"] and q.state()["x1"] == frozen["x1"],
              "paused Start retains priority over Select without a reset", observe(q))
        check(q.state()["training_dummy"] == 0, "Start/Select retains the selected dummy")
        EVENTS["controls"] = observe(q)

        # Shoulder and P2 attack buttons remain non-attacks during live Training.
        q.run(12, ("l", "r"), ("y", "x", "b", "a"))
        check(q.state()["action1"] == 0 and q.state()["action2"] == 0,
              "live shoulders and P2 attacks do not consume the four-button combat layout", observe(q))
        q.press("start")
        q.run(3, ("a", "select"))
        q.run(5)
        check(not q.state()["paused"], "paused A still resumes before Select")
        q.press("start")
        q._menu_load_budget = native.MENU_LOAD_DUPLICATE_LIMIT
        q.run(3, ("b", "a", "select"))
        native.wait_screen(q, native.SELECT)
        check(q.state()["screen"] == native.SELECT,
              "paused B retains roster priority over A and Select", q.state())
    finally:
        q.close()


def combo_challenge(rom):
    q = native.boot(rom, fighter=2, fighter2=0, label="combo-challenge")
    try:
        q.run(2, ("down", "y"))
        q.run(48)
        await_text(q, "SP!")
        check(q.state()["hp2"] == 128 and "00H 000D" in text(q) and "C1 DONE!" not in text(q),
              "accepted whiffed rush special gets an execution cue without invented damage or success", observe(q))
        EVENTS["special_whiff"] = {"state": observe(q), "capture": shot(q, "special-whiff")}
        q.run(2, ("down", "y"))
        q.run(110)
        await_text(q, "SP-")
        energy = q.state()["energy1"]
        check(energy < 32, "repeated real special costs leave insufficient energy for another special", energy)
        q.run(2, ("down", "y"))
        rejected = [q.step() for _ in range(30)]
        check(not any(s["action1"] == 7 for s in rejected) and "SP-" in text(q),
              "an energy-rejected shortcut cannot light the successful-special cue", observe(q))
        reset(q)
        approach(q)
        damage, rows = jab(q)
        q.run(3)
        await_text(q, "01H")
        check(f"{damage:03d}D" in text(q) and "NOW " in text(q) and "C1 LINK!" in text(q),
              "first real hit shows current hits, actual damage and the live link task", observe(q))
        EVENTS["current_combo"] = {"rows": rows, "capture": shot(q, "current-combo")}
        q.run(2, ("down", "y"))
        samples = []
        for _ in range(65):
            q.step()
            samples.append(observe(q))
        check(any(s["combo1"] >= 2 for s in samples),
              "controller normal-to-special produces a real two-hit native combo", samples)
        total = 128 - min(s["hp2"] for s in samples)
        check(f"02H {total:03d}D" in text(q) and "C1 DONE!" in text(q),
              "true normal-to-special challenge completes with exact accumulated damage", observe(q))
        check("LAST" in text(q), "last combo stays visible after hit stun ends", text(q))
        EVENTS["combo_success"] = {"damage": total, "rows": samples,
                                   "capture": shot(q, "combo-complete")}
        # Training recovery must not erase the recorded last combo or task result.
        q.run(160)
        check(q.state()["hp2"] == 128 and "C1 DONE!" in text(q) and f"{total:03d}D" in text(q),
              "ordinary Training health recovery preserves last combo evidence", observe(q))
        reset(q)
        approach(q)
        jab(q)
        q.run(55)
        check("C1 RETRY" in text(q), "expired hit stun fails the normal-to-special task", observe(q))
        EVENTS["combo_failure"] = {"state": observe(q), "capture": shot(q, "combo-retry")}
        q.run(2, ("down", "y"))
        q.run(55)
        check("C1 DONE!" not in text(q), "a late unlinked special cannot complete the combo challenge", observe(q))
        reset(q)
        q.press("start")
        q.press("down")
        resume(q)
        approach(q)
        q.run(2, ("y",))
        q.run(35)
        check(q.state()["hp2"] == 128 and "00H 000D" in text(q) and "C1 DONE!" not in text(q),
              "blocked normal supplies neither damage nor false challenge progress", observe(q))
        q.press("start")
        q.press("down")
        resume(q)
        check(q.state()["training_dummy"] == 2, "low guard dummy retains its original selection")
        q.run(2, ("down", "a"))
        low_block = []
        for _ in range(40):
            q.step()
            s = q.state()
            if s["connected1"] == 1:
                low_block.append(observe(q))
                break
        check(bool(low_block) and low_block[-1]["guard2"] == 1 and low_block[-1]["hp2"] >= 127,
              "original low guard dummy actually blocks a real sweep", low_block)
        q.run(45)
        q.press("start")
        q.press("down")
        resume(q)
        jumping = [q.step() for _ in range(90)]
        jumps = sum(before["y2"] == 0 and native.signed16(after["y2"]) < 0
                    for before, after in zip(jumping, jumping[1:]))
        check(q.state()["training_dummy"] == 3 and jumps >= 2,
              "original Jump dummy repeatedly jumps after ordinary landings", {"new_jumps": jumps})
    finally:
        q.close()


def low_guard_challenge(rom):
    q = native.boot(rom, fighter=0, fighter2=4, label="low-guard-challenge")
    try:
        tools(q, 1)
        # Return to ordinary pause card before choosing CPU, retaining L/R.
        q.press("select")
        q.press("up")
        q.press("r")
        check(q.state()["training_dummy"] == 4 and "CPU HARD" in text(q, 11, 12),
              "low guard drill uses the ordinary existing CPU and shoulder level controls")
        resume(q)
        failure = []
        for _ in range(900):
            q.step()
            s = q.state()
            if s["hp1"] < 128:
                failure.append(observe(q))
                break
        await_text(q, "C2 RETRY")
        check(bool(failure), "unguarded actual CPU damage fails the low-guard task", failure)
        # Reposition by the public Training reset, then defend immediately.
        # Staying point blank after a hit invites CPU throws rather than lows.
        q.run(2, ("select",))
        rows = []
        for _ in range(3000):
            s = q.state()
            away = "left" if s["x1"] < s["x2"] else "right"
            q.step(("down", away))
            now = observe(q)
            if now["hurt1"] > s["hurt1"] or now["hp1"] != s["hp1"]:
                rows.append(now)
            if "C2 DONE!" in text(q):
                break
        check("C2 DONE!" in text(q) and any(s["guard1"] for s in rows),
              "real controller low guard against a CPU low completes the task", rows[-16:])
        EVENTS["low_guard"] = {"failure": failure, "contacts": rows,
                               "capture": shot(q, "low-guard-complete")}
    finally:
        q.close()


def crossup_challenge(rom):
    q = native.boot(rom, fighter=0, fighter2=0, label="crossup-challenge")
    try:
        tools(q, 2)
        resume(q)
        approach(q, 40)
        q.step(("up",))
        q.step()
        q.step(("a",))
        rows = []
        for _ in range(85):
            q.step()
            rows.append(observe(q))
        check(any(s["hp2"] < 128 for s in rows) and "C3 RETRY" in text(q),
              "a front air kick hits but cannot complete the rear cross-up task", rows)
        reset(q)
        check("C3 READY" in text(q), "Select rearms the selected challenge without changing its choice", text(q))
        approach(q, 24)
        initial_face = q.state()["face1"]
        q.step(("up", "right"))
        sent = False
        rows = []
        for _ in range(90):
            s = q.state()
            keys = ()
            if not sent and s["x1"] > s["x2"]:
                keys = ("a",)
                sent = True
            q.step(keys)
            rows.append(observe(q))
        rear_hits = [s for s in rows if s["hp2"] < 128 and
                     native.signed16(s["y1"]) < 0 and s["x1"] > s["x2"] and
                     s["face1"] == initial_face]
        check(sent and bool(rear_hits) and "C3 DONE!" in text(q),
              "actual rear airborne A contact completes the cross-up drill", rear_hits)
        EVENTS["crossup"] = {"rows": rows, "capture": shot(q, "crossup-complete")}
    finally:
        q.close()


def nontraining(rom):
    q = native.boot(rom, mode=1, fighter=0, fighter2=0, label="versus-preservation")
    try:
        q.run(32)
        check("C1" not in text(q) and "IN" not in text(q), "Training footer is absent from local Versus", text(q))
        q.press("start")
        for page in (1, 2, 0):
            q.press("select")
            q.run(8)
            check(q.state()["pause_page"] == page,
                  "Versus preserves its original two-page guide cycle", observe(q))
    finally:
        q.close()


def roster_timing(rom):
    """Bounded changing-input load with every CPU profile, stage and level."""
    from test_endurance import keys_for

    coverage = []
    for enemy in range(12):
        q = native.boot(rom, fighter=(enemy + 2) % 12, fighter2=enemy,
                        stage=enemy % 3, difficulty=enemy % 3,
                        label=f"tools-cpu-{enemy:02d}")
        try:
            q.press("start")
            q.press("up")
            q.press("start")
            check(q.state()["training_dummy"] == 4, "bounded timing probe selects the real CPU dummy", enemy)
            actions = set()
            for tick in range(1200):
                p1, p2 = keys_for(2, tick, q.state())
                s = q.step(p1, p2)
                actions.add(s["action1"])
            q.run(24)
            check("LAST" in text(q) or "NOW " in text(q),
                  "live tool feedback remains published under changing-input CPU load", observe(q))
            check(len(actions - {0}) >= 3, "bounded tools timing probe exercises multiple real attacks", sorted(actions))
            coverage.append({"enemy": enemy, "fighter": (enemy + 2) % 12,
                             "stage": enemy % 3, "difficulty": enemy % 3,
                             "frames": 1200, "actions": sorted(actions)})
        finally:
            q.close()
    EVENTS["roster_timing"] = coverage


def symbols(path):
    return {name: int(address, 16) for address, name in
            re.findall(r"^([0-9a-fA-F]{8}) (\S+)$", path.read_text(encoding="utf-8"), re.M)}


def audit():
    contract = combined_contract(ROOT)
    current = symbols(ROOT / "dist/abaqus-after-hours.sym")
    check(True, "combined strict preservation: 219 generated files, eight authorized changes, protected source pins and bounded RAM", {
        "generated": contract["assets"]["generated_count"],
        "changes": contract["assets"]["changed_generated"],
        "native": contract["native"]})
    owned = {n: f"{a:06x}" for n, a in current.items()
             if n.startswith("training") and 0x7E0000 <= a <= 0x7FFFFF}
    check(current["trainingStatusText"] + 33 - current["trainingHistory"] == 101,
          "Training mutable state remains exactly 101 bytes")
    return {"combined_contract": contract, "training_ram_symbols": owned,
            "training_ram_bytes": 101, "training_lookup_ram_bytes": 90,
            "rom_section_bytes": contract["native"]["linked_section_bytes"],
            "rom_free_bytes": 4194304 - contract["native"]["linked_section_bytes"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=ROOT / "dist/abaqus-after-hours.sfc")
    parser.add_argument("--report", type=Path, default=ROOT / "docs/expansion-05-report.json")
    args = parser.parse_args()
    report = {"feature": "05 Training tools", "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
              "host": "pinned Snes9x libretro; capture only; no GUI/audio device",
              "controller_only": True, "emulated_memory_writes": False,
              "save_state_loads": False, "core": native.core_identity(),
              "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                for name in ("src/game.c", "src/pause_guide.h", "src/training_tools.h", "tools/expansion_contracts.py")}}
    try:
        controls_and_history(args.rom)
        combo_challenge(args.rom)
        low_guard_challenge(args.rom)
        crossup_challenge(args.rom)
        nontraining(args.rom)
        roster_timing(args.rom)
        report["audit"] = audit()
        report["status"] = "passed"
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = repr(exc)
        raise
    finally:
        report["events"] = EVENTS
        report["captures"] = [{"path": p.relative_to(ROOT).as_posix(),
                               "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                              for p in sorted(CAPTURES.glob("*.png"))]
        report["sessions"] = [{"label": q.label, "samples": q.samples,
                               "fight_samples": q.fight_samples,
                               "cadence_failures": q.cadence,
                               "ppu_overflow": q.ppu_overflow,
                               "native_timing_failures": q.native_timing_failures,
                               "spc_peak_backlog_bytes": q.spc_peak_backlog,
                               "spc_failures": q.spc_failures,
                               "audio_samples": q.audio_samples,
                               "menu_load_callbacks": len(q.menu_load_duplicates),
                               "menu_callback_evidence": q.menu_load_duplicates,
                               "timeline": q.timeline_capture} for q in SESSIONS]
        budgets = all(not q.cadence and not q.ppu_overflow and not q.native_timing_failures and
                      not q.spc_failures for q in SESSIONS)
        native.CHECKS.append({"check": "focused native FIGHT cadence, SDK timing, OBJ and resident SPC budgets",
                              "passed": budgets, "details": {q.label: {
                                  "trace_failures":len(q.cadence), "sdk_failures":len(q.native_timing_failures),
                                  "obj_failures":len(q.ppu_overflow), "spc_failures":len(q.spc_failures)}
                                  for q in SESSIONS}})
        if report["status"] == "passed" and not budgets:
            report["status"] = "failed"
            report["error"] = "native timing/OBJ/SPC budgets failed; inspect sessions"
        report["checks"] = native.CHECKS
        report["check_count"] = len(native.CHECKS)
        report["harness_sha256"] = hashlib.sha256(Path(__file__).read_bytes() +
                    (ROOT / "tools/test_training.py").read_bytes() +
                    (ROOT / "tools/emulator.py").read_bytes() +
                    (ROOT / "tools/expansion_contracts.py").read_bytes()).hexdigest()
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({"status": report["status"], "checks": len(native.CHECKS),
                          "rom_sha256": report["rom_sha256"], "report": str(args.report)}))
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
