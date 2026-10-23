"""Earn Arcade stories/endings on the exact native ROM, using controllers only.

Default: twelve complete eleven-opponent ladders. No ROM fixture, memory writes,
save states, GUI, audio playback, or shared suite report changes. Source tables
are the authored copy oracle; actual VRAM and PPU glyph pixels prove delivery.
"""
from __future__ import annotations

import argparse
import ctypes as C
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emulator import Emulator, ROOT
from expansion_contracts import combined_contract
import test_presentation as p
from test_champion import host_contract, verify_background

BASE = "610537d"
OUT = ROOT / "docs/screenshots/expansion-09"
CHECKS: list[dict] = []
SYMBOLS: dict[str, int] = {}
TEXT: dict[str, list[str]] = {}
RIVALS = [9, 3, 8, 1, 6, 10, 4, 11, 2, 0, 5, 7]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def check(ok, label, details=None):
    CHECKS.append({"check": label, "passed": bool(ok), "details": details})
    if not ok:
        raise AssertionError((label, details))


def symbols(raw):
    return {name: int(address, 16) for address, name in
            re.findall(r"^([0-9a-f]{8}) (\S+)$", raw.decode("utf-8"), re.M)}


def read(e, name, width=2):
    address = SYMBOLS[name]
    if address >> 16 == 0x7E:
        address &= 0xFFFF
    elif address >> 16 == 0x7F:
        address = 0x10000 + (address & 0xFFFF)
    return int.from_bytes(C.string_at(e.ram + address, width), "little")


def trace_word(e, index):
    return int.from_bytes(C.string_at(e.ram + 0x1FF00 + index * 2, 2), "little")


def press(e, key, port=0):
    e.tap(key, port)
    e.run(8)


def wait(e, screen, limit=900):
    for _ in range(limit):
        if e.state()["screen"] == screen:
            e.run(8)
            return
        e.run(1)
    raise AssertionError(("screen did not arrive", screen, e.state()))


def boot(hero=0, mode=0, difficulty=0):
    e = Emulator()
    e.run(100)
    if difficulty == 0:
        press(e, "l")
    elif difficulty == 2:
        press(e, "r")
    for _ in range(mode):
        press(e, "down")
    press(e, "a"); wait(e, 1)
    for _ in range(hero):
        press(e, "right")
    press(e, "a")
    if mode:
        press(e, "a")
    wait(e, 2)
    press(e, "a"); wait(e, 3)
    return e


def capture(e, name):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    e.frame.save(path)
    return path.relative_to(ROOT).as_posix()


def rows(e, expected, label):
    """Compare full opaque map text and the actual PPU line to native glyphs."""
    memory = p.vram_bytes(e)
    palette = (ROOT / "assets/generated/ui_pal.bin").read_bytes()[:32]
    cells, largest, wrong, transparent = 0, 0, [], set()
    for y, x, text in expected:
        for offset, character in enumerate(text):
            cell_x = x + offset
            entry = p.map_tile(memory, cell_x, y)
            tile = entry & 1023
            if tile != ord(character) + 256 or ((entry >> 10) & 7) != 0:
                wrong.append([y, cell_x, character, hex(entry)])
            encoded = memory[0x8000 + tile * 32:0x8000 + (tile + 1) * 32]
            if not all(p.tile_indices(encoded)):
                transparent.add(tile)
            expected_tile = p.tile_rgb(encoded, palette)
            actual = e.frame.crop((cell_x * 8, y * 8, cell_x * 8 + 8, y * 8 + 8))
            delta = p.image_delta(actual, expected_tile)
            largest = max(largest, delta["max_channel_delta"])
            if delta["pixels_over_16"]:
                wrong.append([y, cell_x, "PPU pixels", delta])
            cells += 1
    check(not wrong and not transparent and largest <= 3,
          label + ": native map, opaque glyph and PPU pixels", {
              "cells": cells, "maximum_channel_delta": largest,
              "wrong": wrong[:5], "transparent_tiles": sorted(transparent)})
    return {"text": [text for _, _, text in expected], "cells": cells,
            "max_channel_delta": largest}


def centered(y, text):
    return (y, (32 - len(text)) // 2, text)


def story(e):
    s = e.state()
    hero, opponent = s["fighter_id1"], s["fighter_id2"]
    rival = RIVALS[hero] == opponent
    opener = TEXT["arcadeStoryRivalOpeners" if rival else "arcadeStoryOpeners"][hero]
    reply = TEXT["arcadeStoryRivalReplies" if rival else "arcadeStoryReplies"][opponent]
    expected = [(9, 2, p.NAMES[hero]), (10, 2, opener),
                (12, 2, p.NAMES[opponent]), (13, 2, reply),
                centered(26, "P1 A: FIGHT   AUTO: 6 SECONDS"),
                centered(27, "START PAUSE > SELECT GUIDE")]
    if rival:
        expected.append(centered(11, "FRIENDLY RIVALS"))
    check(s["mode"] == 0 and s["intro"] == 110 and read(e, "arcadeStoryTicks") > 0,
          "matchup exchange holds the existing Arcade intro", {"hero": hero, "opponent": opponent})
    result = rows(e, expected, f"{p.NAMES[hero]} vs {p.NAMES[opponent]}")
    result.update({"hero": hero, "opponent": opponent, "rivals": rival})
    return result


def skip_story(e):
    e.run(2)
    press(e, "a")
    check(read(e, "arcadeStoryTicks") == 0 and e.state()["intro"] > 0,
          "fresh P1 A advances conversation into ordinary countdown")
    for _ in range(160):
        if not e.state()["intro"]:
            break
        e.run(1)
    e.run(8)
    s = e.state()
    check(s["intro"] == 0 and s["action1"] == 0 and not s["buffered_action1"],
          "skip does not become an opening attack or buffered command", s)


def play_cpu(e, limit=16000, policy="close"):
    """Read-only feedback controls ordinary close/guard/throw gameplay."""
    before = e.frames
    rounds_seen = set()
    for _ in range(limit):
        s = e.state()
        if s["screen"] == 4:
            e.run(8)
            return e.frames - before
        forward = "right" if s["x1"] < s["x2"] else "left"
        back = "left" if forward == "right" else "right"
        distance = abs(s["x1"] - s["x2"]) // 16
        if s["intro"] and s["round"] > 1 and s["round"] not in rounds_seen:
            check(read(e, "arcadeStoryTicks") == 0,
                  "later rounds retain ordinary intro without repeating story")
            rounds_seen.add(s["round"])
        if s["intro"] or s["round_end"] or s["hitstop"]:
            e.run(1)
        elif policy == "jump-in" and s["y1"] >= 32768:
            # Easy still has ordinary real guard/movement/attack decisions.
            # Cross ground waves with a visible jump, then press airborne A.
            air_keys = [forward]
            if not s["action1"] and distance < 62 and s["y1"] < 65536-16:
                air_keys.append("a")
            e.run(1, p1=air_keys)
        elif s["action1"]:
            e.run(1, p1=[forward])
        elif policy == "jump-in" and (distance > 38 or (s["wave2"] and s["wave_low2"])):
            e.run(1, p1=[forward,"up"])
        elif s["action2"] and distance < 55:
            e.run(1, p1=[back, "down"] if 4 <= s["action2"] <= 6 else [back])
        elif distance >= s["throw_range1"] - 2:
            e.run(1, p1=[forward])
        else:
            e.run(1, p1=[forward, "x"])
            e.run(1, p1=[forward])
    raise AssertionError(("CPU match did not finish", e.state()))


def result_quote(e):
    s = e.state()
    winner = s["fighter_id1"] if s["wins1"] == 2 else s["fighter_id2"]
    expected = [centered(21, TEXT["arcadeStoryWinnerQuotes"][winner]),
                centered(24, "A/START: NEXT CHALLENGER" if s["wins1"] == 2 else "A/START: CONTINUE"),
                centered(26, "B: CHARACTER SELECT")]
    return rows(e, expected, "Arcade result " + p.NAMES[winner])


def transition_controls():
    e = boot()
    try:
        report = {"initial": story(e)}
        frame_before, timer = e.state()["frame"], read(e, "arcadeStoryTicks")
        lag_before = read(e, "lag_frame_counter")
        e.run(120, p1=["down", "y", "up", "x"])
        s = e.state()
        check(s["frame"] - frame_before == 120 and read(e, "arcadeStoryTicks") == timer - 120,
              "conversation updates at one native tick per video frame")
        check(s["hp1"] == 128 and s["hp2"] == 128 and s["intro"] == 110 and
              s["x1"] == 66 * 16 and s["x2"] == 190 * 16 and not s["buffered_action1"],
              "story rejects combat, movement, motion and jump buffers", s)
        timer = read(e, "arcadeStoryTicks")
        e.run(3, p1=["a", "start"]); e.run(8)
        check(e.state()["paused"] == 1 and read(e, "arcadeStoryTicks") == timer,
              "Start+A pauses without advancing the exchange")
        e.run(80)
        check(read(e, "arcadeStoryTicks") == timer, "paused conversation timer stays frozen")
        press(e, "select", 1); e.run(12)
        check(trace_word(e, 119) == 1, "P2 Select opens ordinary Controls guide during story pause")
        press(e, "start", 1)
        report["after_guide"] = story(e)
        press(e, "start"); press(e, "a")
        report["after_a_resume"] = story(e)
        check(not e.state()["paused"], "pause A resumes the exchange without skipping it")
        timer = read(e, "arcadeStoryTicks")
        press(e, "a", 1)
        check(read(e, "arcadeStoryTicks") > 0 and read(e, "arcadeStoryTicks") < timer,
              "P2 A does not control Arcade story advance")
        e.run(10)
        timer = read(e, "arcadeStoryTicks")
        for _ in range(timer + 12):
            e.run(1)
            if not read(e, "arcadeStoryTicks"):
                break
        e.run(8)
        check(read(e, "arcadeStoryTicks") == 0 and 80 < e.state()["intro"] < 110,
              "six-second automatic advance enters countdown without input")
        report["lag_counter_delta_including_pause"] = (read(e, "lag_frame_counter") - lag_before) & 65535
        check(report["lag_counter_delta_including_pause"] == 0,
              "story pause, guide, resume and automatic exit add no native lag ticks")
        report["auto_advance"] = capture(e, "auto-countdown.png")
        e.run(140)
        before = e.state()["frame"]
        lag = read(e, "lag_frame_counter")
        e.run(600)
        check((e.state()["frame"] - before) & 65535 == 600 and read(e, "lag_frame_counter") == lag,
              "post-story live combat retains 600/600 cadence and native lag counter")
        report["live_cadence"] = 600
        press(e, "start"); press(e, "b"); wait(e, 1)
        check(e.state()["screen"] == 1, "ordinary paused B returns from Arcade to roster")
    finally:
        e.close()
    for mode in (1, 2):
        e = boot(mode=mode)
        try:
            check(read(e, "arcadeStoryTicks") == 0,
                  "Versus/Training start without Arcade story", mode)
            e.run(180)
            check(e.state()["intro"] == 0, "Versus/Training ordinary intro timing remains", mode)
            if mode == 2:
                press(e, "start")
                for _ in range(4):
                    press(e, "down")
                initial = read(e, "difficulty", 1)
                press(e, "r", 1)
                check(read(e, "difficulty", 1) == (initial + 1) % 3,
                      "P2 shoulder still changes paused Training CPU level")
                press(e, "start"); press(e, "select")
                check(e.state()["hp1"] == 128 and e.state()["intro"] == 0 and not read(e, "arcadeStoryTicks"),
                      "Training Select reset remains live and never starts story")
        finally:
            e.close()
    e = boot(difficulty=2)
    try:
        story(e); skip_story(e)
        for _ in range(2000):
            if e.state()["screen"] == 4:
                break
            e.run(10)
        s = e.state()
        check(s["screen"] == 4 and s["wins2"] == 2 and not s["champion"],
              "ordinary CPU combat earns a real loss without champion", s)
        report["loss"] = result_quote(e)
        report["loss"]["capture"] = capture(e, "cpu-winner-continue.png")
        e.run(3, p1=["start", "a", "b"]); e.run(12)
        check(e.state()["screen"] == 3 and e.state()["arcade"] == 0 and e.state()["fighter_id2"] == 1,
              "result Start wins simultaneous A/B and Continue retains the opponent")
        story(e)
        press(e, "start"); press(e, "b"); wait(e, 1)
        check(e.state()["screen"] == 1, "paused B still leaves a repeated conversation")
    finally:
        e.close()
    return report


def ladder(hero):
    e = boot(hero)
    report = {"hero": hero, "matches": []}
    try:
        for index in range(11):
            exchange = story(e)
            if index == 0 or exchange["rivals"]:
                exchange["capture"] = capture(e, f"{hero:02}-vs-{exchange['opponent']:02}.png")
            check(e.state()["arcade"] == index and e.state()["arena"] == index % 3 and
                  e.state()["fighter_id2"] == (hero + 1 + index) % 12,
                  "Arcade opponent and three-stage order are unchanged", {"hero": hero, "index": index})
            skip_story(e)
            attempts = []
            for attempt in range(16):
                policy = "close" if attempt == 0 else "jump-in"
                frames = play_cpu(e, policy=policy)
                current = e.state()
                check(current["screen"] == 4 and current["arcade"] == index,
                      "controller combat reaches the expected Arcade result")
                check(bool(current["champion"]) == (index == 10 and current["wins1"] == 2),
                      "only a real eleventh match win awards champion")
                attempts.append({"wins1": current["wins1"], "wins2": current["wins2"], "frames": frames, "controller_policy": policy})
                if current["wins1"] == 2:
                    break
                result_quote(e)
                press(e, "a"); wait(e, 3)
                check(e.state()["arcade"] == index and e.state()["fighter_id2"] == exchange["opponent"],
                      "loss Continue repeats the same opponent")
                story(e); skip_story(e)
            check(current["wins1"] == 2, "controller policy earns the Arcade match", attempts)
            item = {"opponent": exchange["opponent"], "arena": current["arena"],
                    "story": exchange, "attempts": attempts}
            if index < 10:
                item["quote"] = result_quote(e)
                if index == 0:
                    item["capture"] = capture(e, f"{hero:02}-winner.png")
                press(e, "start" if index & 1 else "a"); wait(e, 3)
            report["matches"].append(item)
            print(f"{p.NAMES[hero]} {index + 1}/11: {attempts}", flush=True)
        ending = TEXT["arcadeStoryEndings"][hero * 3:hero * 3 + 3]
        report["ending"] = rows(e, [centered(22 + i, line) for i, line in enumerate(ending)] +
                                 [centered(25, "A/START: TITLE"), centered(27, "B: CHARACTER SELECT")],
                                 "earned champion " + p.NAMES[hero])
        check(read(e, "musicIndex", 1) == 4, "earned ending retains champion music")
        report["background"] = verify_background(e)
        p.verify_large_portrait(e, hero, 21, 7)
        report["ending_capture"] = capture(e, f"{hero:02}-champion.png")
        picture = e.frame.tobytes()
        e.run(60)
        check(e.state()["champion"] == 1 and picture == e.frame.tobytes(),
              "individual ending waits stably for its normal menu action")
        key = ("a", "start", "b")[hero % 3]
        press(e, key)
        wait(e, 1 if key == "b" else 0)
        check(e.state()["screen"] == (1 if key == "b" else 0),
              "earned champion exit uses ordinary title/roster route", key)
        report["exit"] = {"key": key, "screen": e.state()["screen"]}
        report["frames"] = e.frames
        return report
    finally:
        e.close()


def storage_and_preservation():
    code = (ROOT / "src/arcade_story.h").read_text(encoding="utf-8")
    for name, body in re.findall(r"const char \* const (\w+)\[\d+\]=\{(.*?)\n\};", code, re.S):
        TEXT[name] = re.findall(r'"([^"\n]*)"', body)
        expected = 36 if name.endswith("Endings") else 12
        width = 30 if name.endswith(("WinnerQuotes", "Endings")) else 28
        check(len(TEXT[name]) == expected and all(0 < len(line) <= width for line in TEXT[name]),
              "all twelve authored text sets fit native panel width", {"table": name, "count": len(TEXT[name]), "width": width})
    raw = (ROOT / "dist/abaqus-after-hours.sfc").read_bytes()

    def rom_offset(address):
        return ((address >> 16) & 127) * 32768 + (address & 65535) - 0x8000

    for name, lines in TEXT.items():
        check(SYMBOLS[name] >> 16 not in (0x7E, 0x7F) and SYMBOLS[name] & 65535 >= 0x8000,
              "story text table occupies cartridge ROM", name)
        offset = rom_offset(SYMBOLS[name])
        encoded = []
        for i in range(len(lines)):
            pointer = int.from_bytes(raw[offset + i * 4:offset + i * 4 + 4], "little")
            start = rom_offset(pointer)
            encoded.append(raw[start:raw.index(b"\0", start)].decode("ascii"))
        check(encoded == lines, "actual linked text and far pointers preserve every authored line", name)
    contract = combined_contract(ROOT)
    check(True, "combined strict asset/native preservation passes", {
        "changes": contract["assets"]["changed_generated"],
        "native": contract["native"]})
    check(SYMBOLS["arcadeStoryTicks"] == SYMBOLS["stageVictoryPhase"] + 1,
          "two-byte story timer follows sixteen stage-depth bytes", hex(SYMBOLS["arcadeStoryTicks"]))
    sections, start, banks, story_sizes = [], None, set(), {}
    for address, name in re.findall(r"^([0-9a-f]{8}) (\S+)$", (ROOT / "dist/abaqus-after-hours.sym").read_text(encoding="utf-8"), re.M):
        if name.startswith("SECTIONSTART_"):
            start = (int(address, 16), name[13:])
        elif name.startswith("SECTIONEND_") and start:
            end = int(address, 16)
            if start[0] & 65535 >= 0x8000 and start[0] >> 16 not in (0x7E, 0x7F):
                check(end - start[0] <= 32768 and ((end - 1) >> 16) == start[0] >> 16,
                      "linked native section stays within one LoROM bank", start[1])
                sections.append(end - start[0])
                banks.add((start[0] >> 16) & 127)
                if "arcadeStory" in name:
                    story_sizes[start[1].split("text_")[0]] = end - start[0]
            start = None
    return {"combined_contract": contract, "new_mutable_bytes": 2,
            "timer_address": hex(SYMBOLS["arcadeStoryTicks"]),
            "rom_text_lines": sum(map(len, TEXT.values())), "maximum_linked_section_bytes": max(sections),
            "story_function_bytes": story_sizes,
            "rom_banks_without_named_sections": [bank for bank in range(128) if bank not in banks]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--heroes", default=",".join(map(str, range(12))))
    parser.add_argument("--report", default="docs/expansion-09-report.json")
    args = parser.parse_args()
    started = time.monotonic()
    global SYMBOLS
    SYMBOLS = symbols((ROOT / "dist/abaqus-after-hours.sym").read_bytes())
    manifest = json.loads((ROOT / "dist/manifest.json").read_text(encoding="utf-8"))
    report = {"status": "failed", "suite": "expansion-09-arcade-story", "scope": "focused native controller and PPU proof; no shared six-suite or release claim",
              "rom_sha256": sha((ROOT / "dist/abaqus-after-hours.sfc").read_bytes()), "checksum": manifest["checksum"],
              "host": host_contract(), "controller_only": True, "memory_writes": 0, "save_states": 0,
              "core_sha256": sha((ROOT / ".tools/core/snes9x_libretro.dll").read_bytes()),
              "source_sha256": {name: sha((ROOT / name).read_bytes()) for name in
                  ("src/game.c", "src/arcade_story.h", "tools/test_expansion_09_arcade_story.py",
                   "tools/expansion_contracts.py", "tools/test_presentation.py", "tools/test_champion.py", "tools/emulator.py")},
              "checks": CHECKS, "ladders": []}
    try:
        check(report["rom_sha256"] == manifest["sha256"], "exact cartridge matches its build manifest")
        report["preservation"] = storage_and_preservation()
        report["controls"] = transition_controls()
        for hero in map(int, args.heroes.split(",")):
            report["ladders"].append(ladder(hero))
            (ROOT / args.report).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
        report["coverage"] = {
            "heroes": sorted(item["hero"] for item in report["ladders"]),
            "earned_champions": len(report["ladders"]),
            "arcade_matches_won": sum(len(item["matches"]) for item in report["ladders"]),
            "reciprocal_rival_exchanges": sum(match["story"]["rivals"] for item in report["ladders"] for match in item["matches"]),
            "controller_video_frames": sum(item["frames"] for item in report["ladders"]),
            "champion_exit_keys": [item["exit"]["key"] for item in report["ladders"]]}
        if len(report["ladders"]) == 12:
            check(report["coverage"]["heroes"] == list(range(12)) and
                  report["coverage"]["arcade_matches_won"] == 132 and
                  report["coverage"]["reciprocal_rival_exchanges"] == 12,
                  "all twelve earned endings cover all 132 matchups and six reciprocal rivalries")
        report["status"] = "passed"
    except Exception as error:
        report["error"] = repr(error)
        raise
    finally:
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        report["passed"] = sum(item["passed"] for item in CHECKS)
        (ROOT / args.report).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({key: report[key] for key in ("status", "passed", "rom_sha256", "elapsed_seconds")}))


if __name__ == "__main__":
    main()
