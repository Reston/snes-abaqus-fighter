"""Silent controller-only native CPU personality evidence; never writes WRAM.

The fixed encounter script is independent of the CPU policy table. Decisions,
contacts, visible recovery opportunities and PPU/cadence are observed from the
cartridge. A second all-roster Hard run also injects ignored P2 gameplay input.
"""
from __future__ import annotations

import argparse
from collections import Counter
import ctypes as C
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emulator import Emulator, ROOT
import test_inputs as legacy
from release_evidence import EXPECTED_NATIVE_CORE

NAMES = ("Damian", "Ivo", "Cristobal", "Cote", "Negger", "David",
         "Fernando", "Cristian", "Mamariaga", "Reston", "Roxana", "Lars")
ATTACKS = 0xC0C0
CHECKS = []
SYMBOLS = {}


def require(ok, label, detail=None):
    if not ok:
        raise AssertionError((label, detail))
    CHECKS.append({"check": label, "passed": True, "details": detail})


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state(e):
    s = e.state()
    # Read current native action clocks, not reconstructed/future move data.
    f = C.string_at(e.ram + SYMBOLS["fighters"], 128)
    s.update(tick1=f[17], tick2=f[81], active_end1=f[63], active_end2=f[127], action_end2=f[126])
    s["ppu"] = int.from_bytes(C.string_at(e.ram + 0x1FF00 + 228, 2), "little")
    return s


def compact(s):
    return {k: s[k] for k in (
        "frame", "hp1", "hp2", "x1", "x2", "y1", "y2", "face2",
        "action1", "action2", "tick1", "tick2", "active_end1",
        "raw_keys1", "raw_keys2", "hurt1", "hurt2", "guard2",
        "connected2", "down_state1", "down_state2", "hitstop", "round_end", "paused")}


def boot(cpu, difficulty, *, training=True, delay=0):
    e = legacy.boot(2 if training else 0, fighter=4 if training else (cpu-1) % 12,
                    fighter2=cpu if training else None, difficulty=difficulty,
                    title_delay=delay)
    if training:
        e.tap("start")
        e.tap("up")  # Stand -> CPU; ordinary pause dummy selector.
        e.tap("start")
    require(e.state()["fighter_id2"] == cpu and not e.state()["paused"],
            "controller menus select CPU " + NAMES[cpu], {"difficulty": difficulty})
    return e


def p1_script(s, tick):
    """Repeated neutral, pressure, guard, recovery bait and jump-in encounters."""
    forward = "right" if s["x1"] < s["x2"] else "left"
    back = "left" if forward == "right" else "right"
    distance = abs(s["x1"] - s["x2"]) // 16
    phase = tick % 900
    if phase < 100:
        return []
    if phase < 260:
        return [forward] if distance > 26 else (["x"] if tick % 35 < 3 else [])
    if phase < 400:
        return [back, "down"] if tick % 80 < 40 else [back]
    if phase < 580:
        return [forward] if distance > 28 else (["down", "a"] if tick % 43 < 3 else [])
    if phase < 760:
        if tick % 60 < 3:
            return [forward, "up"]
        if tick % 60 in (18, 19, 20):
            return ["a"]
        return [forward] if not s["y1"] and distance > 50 else []
    # Strong punches at 40..50px create honest punishable whiffs/recovery.
    if distance > 48:
        return [forward]
    if tick % 40 < 3:
        return ["x"]
    return [back] if distance < 40 else []


def encounter(cpu, difficulty, frames, *, noisy_p2=False, capture=False):
    e = boot(cpu, difficulty)
    decisions, starts, responses = Counter(), Counter(), Counter()
    m = Counter()
    examples = {}
    digest = hashlib.sha256()
    video = hashlib.sha256()
    active = None
    try:
        for tick in range(frames):
            before = state(e)
            keys = p1_script(before, tick)
            noise = (["y", "x", "b", "a", "l", "r", "up", "left"]
                     if noisy_p2 and tick % 7 < 3 else [])
            e.run(1, p1=keys, p2=noise)
            after = state(e)
            pair = {"before": compact(before), "after": compact(after)}
            require((after["frame"] - before["frame"]) & 0xFFFF == 1,
                    "native CPU encounter keeps unit cadence", [cpu, difficulty, tick])
            require(after["ppu"] & 0xC0 == 0,
                    "native CPU encounter stays within OBJ fetch limits", [cpu, difficulty, tick])
            raw = after["raw_keys2"]
            decisions[str(raw)] += 1
            require(raw & ~(ATTACKS | 0xF00) == 0,
                    "CPU sends only legal directions and face buttons", raw)
            eligible = (before["hp1"] > 0 and before["hp2"] > 0 and
                        not any(before[k] for k in ("action2", "hurt2", "y2", "down_state2", "hitstop")))
            if not eligible:
                m["unavailable_samples"] += 1
                require(not raw & ATTACKS,
                        "CPU never buffers an attack while unavailable", pair)
            else:
                m["available_samples"] += 1
                distance = abs(before["x1"] - before["x2"]) // 16
                forward, back = (256, 512) if before["face2"] else (512, 256)
                if 25 <= distance <= 46 and not before["action1"] and not before["down_state1"]:
                    m["neutral_spacing_samples"] += 1
                    m["neutral_approach"] += bool(raw & forward)
                    m["neutral_retreat"] += bool(raw & back)
                    m["neutral_hold"] += raw == 0
                if (before["action1"] and before["tick1"] >= before["active_end1"] and
                        not before["hurt1"] and not before["y1"] and distance <= 46):
                    m["visible_recovery_samples"] += 1
                    if raw & ATTACKS:
                        m["recovery_answers"] += 1
                        responses[str(raw)] += 1
                        examples.setdefault("recovery_answer", pair)
                    else:
                        m["declined_recovery_samples"] += 1
                if before["action1"] and distance < 64:
                    m["enemy_attack_samples"] += 1
                    m["guard_decisions"] += bool(raw & back)
            if after["action2"] and after["action2"] != before["action2"]:
                starts[str(after["action2"])] += 1
                m["attack_starts"] += 1
                active = {"action": after["action2"], "connected": 0}
                examples.setdefault("start", pair)
            if active:
                active["connected"] = max(active["connected"], after["connected2"])
                if after["action2"] != active["action"]:
                    if not active["connected"]:
                        m["whiffs_or_interrupted"] += 1
                        examples.setdefault("whiff", pair)
                        if (before["tick2"]+1 >= before["action_end2"] and
                                not after["hurt2"] and not after["down_state2"] and active["action"] <= 6):
                            m["completed_normal_whiffs"] += 1
                            examples.setdefault("completed_whiff", pair)
                    active = None
            if after["connected2"] > 0 and before["connected2"] == 0:
                contact = "hit" if after["connected2"] == 2 else "blocked"
                m[contact] += 1
                examples.setdefault(contact, pair)
                if capture and contact not in examples.get("screenshots", {}):
                    path = e.shot(f"expansion-06/cpu{cpu:02}-{contact}.png")
                    examples.setdefault("screenshots", {})[contact] = path.relative_to(ROOT).as_posix()
            if after["hp2"] < before["hp2"]:
                m["cpu_guard_contacts" if after["guard2"] else "cpu_took_hits"] += 1
                examples.setdefault("cpu_guard" if after["guard2"] else "cpu_hurt", pair)
            if after["action2"] == 8 and before["action2"] != 8:
                m["anti_air_starts"] += 1
                examples.setdefault("anti_air", pair)
            digest.update(json.dumps(compact(after), sort_keys=True, separators=(",", ":")).encode())
            if tick % 30 == 0:
                video.update(e.frame.tobytes())
        require(m["attack_starts"] > 3 and m["available_samples"] > 100,
                "CPU actively fights in a genuine encounter", {"cpu": cpu, "difficulty": difficulty, "metrics": dict(m)})
        return {"cpu": cpu, "name": NAMES[cpu], "difficulty": difficulty,
                "frames": frames, "metrics": dict(m), "decisions": dict(decisions),
                "action_starts": dict(starts), "recovery_commands": dict(responses),
                "trace_sha256": digest.hexdigest(), "sampled_video_sha256": video.hexdigest(),
                "examples": examples}
    finally:
        e.close()


def recovery_fixture(cpu, difficulty, delay=0):
    """A controller whiff against Stand; enable CPU during visible recovery."""
    e = legacy.boot(2, fighter=2, fighter2=cpu, difficulty=difficulty, title_delay=delay)
    rows = []
    try:
        for _ in range(180):
            s = state(e)
            if abs(s["x1"]-s["x2"]) < 43*16:
                break
            e.run(1, p1=["right"])
        e.run(3)
        e.run(3, p1=["y"])
        for _ in range(30):
            s = state(e)
            if s["action1"] and s["tick1"] >= s["active_end1"]:
                break
            e.run(1)
        require(s["action1"] == 1 and s["connected1"] == 0 and s["hp2"] == 128,
                "recovery fixture starts with a genuine controller whiff", compact(s))
        e.tap("start")
        e.tap("up")
        require(e.state()["paused"] == 1, "recovery fixture enables CPU through pause")
        for tick in range(28):
            before = state(e)
            e.run(1, p1=["start"] if tick < 3 else [])
            after = state(e)
            rows.append({"before": compact(before), "after": compact(after)})
        opportunities = [
            p for p in rows if p["before"]["action1"] and not p["before"]["action2"]
            and p["before"]["tick1"] >= p["before"]["active_end1"]
            and not p["before"]["hurt2"] and not p["before"]["hitstop"] and not p["before"]["paused"]]
        answers = [p for p in opportunities if p["after"]["raw_keys2"] & ATTACKS]
        require(opportunities, "recovery fixture observes available visible recovery", [cpu, difficulty, delay])
        return {"cpu": cpu, "difficulty": difficulty, "title_delay": delay,
                "opportunities": len(opportunities), "answers": len(answers),
                "commands": dict(Counter(str(p["after"]["raw_keys2"]) for p in answers)),
                "samples": rows}
    finally:
        e.close()


def lookahead_fixture(cpu):
    """Two fresh boots differ only in a newly pressed, previously unseen X."""
    branches = []
    for attack in (False, True):
        e = boot(cpu, 2)
        try:
            rows = [compact(state(e))]
            for _ in range(4):
                e.run(1, p1=["x"] if attack else [])
                rows.append(compact(state(e)))
            branches.append(rows)
        finally:
            e.close()
    neutral, pressed = branches
    require(neutral[0] == pressed[0], "lookahead branches share the same native opening", cpu)
    first = next(i for i in range(1, 5) if neutral[i]["raw_keys1"] != pressed[i]["raw_keys1"])
    require(neutral[first]["raw_keys2"] == pressed[first]["raw_keys2"],
            "CPU decision cannot read a newly pressed opponent button", {"cpu": cpu, "samples": [neutral[first], pressed[first]]})
    return {"cpu": cpu, "first_input_frame": first, "neutral": neutral[first], "pressed": pressed[first]}


def anti_air_fixtures():
    fixtures = ((2, 2, 4, False, True), (4, 1, 5, False, True),
                (4, 2, 0, False, True), (2, 2, 9, True, False))
    results = []
    for cpu, difficulty, delay, retreat, hit in fixtures:
        case = legacy._cpu_jump_in(cpu, difficulty, delay, retreat=retreat, kick=not retreat)
        results.append(legacy._cpu_uppercut_start(case, hit=hit))
    return results


def guard_fixture(cpu, difficulty=1):
    """Enable CPU facing an already visible low wave; every roster member."""
    e = legacy.boot(2, fighter=4, fighter2=cpu, difficulty=difficulty)
    rows = []
    try:
        e.run(3, p1=["down", "y"])
        for _ in range(30):
            if e.state()["wave1"]:
                break
            e.run(1)
        require(e.state()["wave1"] == 1 and e.state()["hp2"] == 128,
                "guard fixture creates real approaching low wave", cpu)
        e.run(12)  # Let it enter the existing 96px visible reaction band.
        e.tap("start")
        e.tap("up")
        for tick in range(180):
            e.run(1, p1=["start"] if tick < 3 else [])
            s = state(e)
            if s["hp2"] < 128:
                rows.append(compact(s))
                if len(rows) > 12:
                    break
        require(rows and rows[0]["guard2"] and all(s["hp2"] >= 127 for s in rows),
                "each personality preserves real low-wave guard and chip", {"cpu": cpu, "samples": rows})
        require(any(s["raw_keys2"] & 1024 for s in rows),
                "guarded low wave uses a real crouch-back controller decision", cpu)
        return {"cpu": cpu, "difficulty": difficulty, "samples": rows}
    finally:
        e.close()


def ko_fixture(victim):
    e = boot(2, 0 if victim==2 else 2, training=False)
    dead = []
    try:
        for tick in range(4000):
            s = state(e)
            forward = "right" if s["x1"] < s["x2"] else "left"
            keys = [forward]
            if victim==2 and tick % 24 < 3 and abs(s["x1"]-s["x2"]) < 34*16:
                keys = [forward, "x"]
            e.run(1, p1=keys)
            after = state(e)
            if after[f"hp{victim}"] == 0:
                dead.append(compact(after))
                for _ in range(15):
                    e.run(1, p1=["up", "y"])
                    dead.append(compact(state(e)))
                break
        require(len(dead) == 16, "controller encounter reaches genuine KO", {"victim": victim, "last": compact(state(e))})
        require(all(s["raw_keys2"] == 0 for s in dead[1:]),
                "CPU emits no decisions after either fighter's KO", {"victim": victim, "samples": dead})
        return {"victim": victim, "samples": dead}
    finally:
        e.close()


def personality_metrics(cases):
    results = []
    for difficulty in (0, 1, 2):
        group = [c for c in cases if c["difficulty"] == difficulty]
        aggressive = [group[i] for i in (2, 3, 8)]
        defensive = [group[i] for i in (1, 4, 6, 11)]
        def rate(rows, field):
            return sum(c["metrics"].get(field, 0) for c in rows) / sum(
                c["metrics"].get("neutral_spacing_samples", 0) for c in rows)
        advance_a, advance_d = rate(aggressive, "neutral_approach"), rate(defensive, "neutral_approach")
        retreat_a, retreat_d = rate(aggressive, "neutral_retreat"), rate(defensive, "neutral_retreat")
        require(advance_a > advance_d * 1.5 and retreat_d > retreat_a + .1,
                "aggressive and defensive habits are observable at each difficulty",
                {"difficulty": difficulty, "advance": [advance_a, advance_d], "retreat": [retreat_a, retreat_d]})
        require(len({c["trace_sha256"] for c in group}) == 12,
                "all twelve produce individual recorded decision encounters", difficulty)
        results.append({"difficulty": difficulty, "aggressive_advance_rate": advance_a,
                        "defensive_advance_rate": advance_d, "aggressive_retreat_rate": retreat_a,
                        "defensive_retreat_rate": retreat_d})
    for cpu in range(12):
        rows = [c for c in cases if c["cpu"]==cpu]
        require(sum(c["metrics"].get("hit", 0) for c in rows)>0 and
                sum(c["metrics"].get("blocked", 0) for c in rows)>0 and
                sum(c["metrics"].get("completed_normal_whiffs", 0) for c in rows)>0,
                "each personality has native hit, blocked attack and completed whiff evidence", cpu)
    aa = [sum(c["metrics"].get("anti_air_starts", 0) for c in cases if c["difficulty"]==d) for d in (0, 1, 2)]
    require(aa[0] == 0 and aa[2] > aa[1] > 0, "difficulty preserves fallible anti-air distinction", aa)
    return results


def counter_metrics(recovery):
    hard = [c for c in recovery if c["difficulty"] == 2 and c["cpu"] in (2, 5, 7)]
    results = {}
    for group, ids in (("pressure", (2,)), ("counter", (5, 7))):
        rows = [c for c in hard if c["cpu"] in ids]
        opportunities = sum(c["opportunities"] for c in rows)
        answers = sum(c["answers"] for c in rows)
        results[group] = {"available_recovery_ticks": opportunities, "answers": answers,
                          "answer_rate": answers / opportunities}
    require(results["counter"]["answer_rate"] > results["pressure"]["answer_rate"] * 1.5,
            "counter specialists answer visible recovery more often than pressure specialist", results)
    return results


def audit():
    global SYMBOLS
    raw = (ROOT / "dist/abaqus-after-hours.sym").read_text(encoding="utf-8")
    pairs = [(int(a, 16), n) for a, n in re.findall(r"^([0-9a-f]{8}) (\S+)$", raw, re.M)]
    SYMBOLS = {n: a & 0x1FFFF for a, n in pairs if a >> 16 in (0x7E, 0x7F)}
    baseline = subprocess.check_output(["git", "show", "610537d:dist/abaqus-after-hours.sym"], cwd=ROOT).decode()
    base_ram = {n: int(a, 16) for a, n in re.findall(r"^([0-9a-f]{8}) (\S+)$", baseline, re.M)
                if int(a, 16) >> 16 in (0x7E, 0x7F) or int(a, 16) < 0x2000}
    now = dict((n, a) for a, n in pairs)
    drift = [n for n, a in base_ram.items() if now.get(n) != a]
    require(not drift, "all existing WRAM/direct-page symbols retain addresses", drift)
    require(now["cpuPersonalities"] >> 16 not in (0x7E, 0x7F), "personality table lives in ROM")
    require(not subprocess.check_output(["git", "diff", "--name-only", "610537d", "--", "assets"], cwd=ROOT).strip(),
            "all approved art, palettes, generated assets and audio are byte-preserved")
    rom = ROOT / "dist/abaqus-after-hours.sfc"
    data = rom.read_bytes()
    require(len(data) == 4194304 and data[0x7FD5] == 0x30, "4 MiB NTSC FastROM LoROM contract")
    core = ROOT / ".tools/core/snes9x_libretro.dll"
    require(sha(core) == EXPECTED_NATIVE_CORE["dll_sha256"], "pinned native Snes9x core")
    sections = []
    section_starts = {n[len("SECTIONSTART_"):]: a for a, n in pairs if n.startswith("SECTIONSTART_")}
    for a, n in pairs:
        if n.startswith("SECTIONEND_"):
            key = n[len("SECTIONEND_"):]
            if key in section_starts and "cpu" in key.lower():
                start = section_starts[key]
                require((start & 0x7FFF) + a-start <= 32768,
                        "CPU code fits one 32 KiB LoROM bank", [key, start, a])
                sections.append({"section": key, "start": f"{start:06x}", "bytes": a-start})
    return {"preserved_ram_symbols": len(base_ram), "mutable_bytes_added": 0,
            "personality_table_bytes": 108, "table_address": f"{now['cpuPersonalities']:06x}",
            "cpu_sections": sections, "core_sha256": sha(core)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--frames", type=int, default=1800)
    parser.add_argument("--report", type=Path, default=ROOT / "docs/expansion-06-report.json")
    args = parser.parse_args()
    start = time.time()
    hardware = audit()
    cases = []
    for difficulty in (0, 1, 2):
        for cpu in range(12):
            case = encounter(cpu, difficulty, args.frames, capture=cpu in (2, 7) and difficulty==2)
            cases.append(case)
            print(json.dumps({"cpu": cpu, "difficulty": difficulty, "metrics": case["metrics"]}), flush=True)
    replay = []
    metrics = personality_metrics(cases)
    recovery, no_lookahead, anti_air, guards, ko, regressions = [], [], [], [], [], {}
    counters = {}
    if not args.quick:
        for cpu in range(12):
            again = encounter(cpu, 2, args.frames, noisy_p2=True)
            first = cases[24+cpu]
            require(again["trace_sha256"] == first["trace_sha256"] and
                    again["sampled_video_sha256"] == first["sampled_video_sha256"],
                    "all-roster deterministic replay ignores P2 gameplay input", cpu)
            replay.append({"cpu": cpu, "trace_sha256": again["trace_sha256"],
                           "sampled_video_sha256": again["sampled_video_sha256"]})
        for difficulty in (0, 1, 2):
            for cpu in range(12):
                recovery.append(recovery_fixture(cpu, difficulty))
        for cpu in (2, 5, 7):
            for delay in (3, 6, 9, 12, 15):
                recovery.append(recovery_fixture(cpu, 2, delay))
        require(any(c["answers"] for c in recovery if c["cpu"] in (5, 7)),
                "counter specialists answer real recovery in controlled encounters")
        require(any(c["answers"] == 0 for c in recovery if c["difficulty"]==2),
                "Hard can decline an available punish opportunity")
        counters = counter_metrics(recovery)
        no_lookahead = [lookahead_fixture(cpu) for cpu in range(12)]
        anti_air = anti_air_fixtures()
        guards = [guard_fixture(cpu, d) for d in (1, 2) for cpu in range(12)]
        ko = [ko_fixture(victim) for victim in (1, 2)]
        regressions = {"lowwave_guard": legacy.check_cpu_lowwave_guard(), "wake": legacy.check_cpu_wake()}
    report = {"status": "passed", "scope": "focused CPU feature evidence; no six-suite or release claim",
              "rom_sha256": sha(ROOT / "dist/abaqus-after-hours.sfc"),
              "harness_sha256": {p: sha(ROOT/p) for p in (
                  "tools/test_expansion_06_cpu_personality.py", "tools/emulator.py", "tools/test_inputs.py")},
              "source_sha256": sha(ROOT / "src/cpu_personality.h"),
              "headless": True, "audio": "capture callbacks only; no playback device", "memory_writes": False,
              "hardware": hardware, "elapsed_seconds": round(time.time()-start, 3),
              "cases": cases, "p2_noise_replays": replay,
              "personality_metrics": metrics, "controlled_recovery": recovery,
              "counter_metrics": counters,
              "no_input_lookahead": no_lookahead, "anti_air": anti_air, "ko": ko,
              "all_roster_low_guard": guards,
              "preserved_regressions": regressions, "legacy_focused_checks": len(legacy.checks),
              "screenshots": [{"path": p.relative_to(ROOT).as_posix(), "sha256": sha(p),
                               "native_dimensions": [256, 224]} for p in sorted(
                                   (ROOT / "docs/screenshots/expansion-06").glob("*.png"))],
              "checks": len(CHECKS), "summary_checks": [c for c in CHECKS if "native CPU encounter" not in c["check"]
                                                            and "CPU sends only" not in c["check"]
                                                            and "CPU never buffers" not in c["check"]]}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": "passed", "rom_sha256": report["rom_sha256"], "checks": len(CHECKS),
                      "elapsed_seconds": report["elapsed_seconds"]}), flush=True)


if __name__ == "__main__":
    main()
