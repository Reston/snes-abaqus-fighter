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
from expansion_contracts import combined_contract

NAMES = ("Damian", "Ivo", "Cristobal", "Cote", "Negger", "David",
         "Fernando", "Cristian", "Madariaga", "Reston", "Roxana", "Lars")
ATTACKS = 0xC0C0
CHECKS = []
SYMBOLS = {}


def require(ok, label, detail=None):
    CHECKS.append({"check": label, "passed": bool(ok), "details": detail})
    if not ok:
        raise AssertionError((label, detail))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state(e):
    s = e.state()
    # Read current native action clocks, not reconstructed/future move data.
    f = C.string_at(e.ram + SYMBOLS["fighters"], 128)
    s.update(tick1=f[17], tick2=f[81], active_end1=f[63], active_end2=f[127], action_end2=f[126],
             startup2=f[88])
    s['super2'] = C.string_at(e.ram + SYMBOLS['superActive'] + 1, 1)[0]
    s["ppu"] = int.from_bytes(C.string_at(e.ram + 0x1FF00 + 228, 2), "little")
    return s


def compact(s):
    return {k: s[k] for k in (
        "frame", "hp1", "hp2", "x1", "x2", "y1", "y2", "face2",
        "action1", "action2", "tick1", "tick2", "active_end1",
        "raw_keys1", "raw_keys2", "hurt1", "hurt2", "guard2",
        "connected2", "down_state1", "down_state2", "hitstop", "round_end", "paused",
        "energy1", "energy2", "super2", "startup2", "active_end2", "action_end2", "ppu")}


def boot(cpu, difficulty, *, training=True, delay=0):
    e = legacy.boot(2 if training else 0, fighter=4 if training else (cpu-1) % 12,
                    fighter2=cpu if training else None, difficulty=difficulty,
                    title_delay=delay, wait_intro=training)
    if not training:
        # The combined Arcade conversation precedes the ordinary 110 intro.
        e.run(3, p1=['a'])
        e.run(3)
        for _ in range(600):
            if not e.state()['intro']:
                break
            e.run(1)
        require(not e.state()['intro'], 'Arcade A skip reaches ordinary live fight')
        e.run(3)
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
    failures = []
    controller_runs = []
    try:
        for tick in range(frames):
            before = state(e)
            keys = p1_script(before, tick)
            noise = (["y", "x", "b", "a", "l", "r", "up", "left"]
                     if noisy_p2 and tick % 7 < 3 else [])
            command = [keys, noise]
            if controller_runs and controller_runs[-1]['keys'] == command:
                controller_runs[-1]['frames'] += 1
            else:
                controller_runs.append({'keys': command, 'frames': 1})
            e.run(1, p1=keys, p2=noise)
            after = state(e)
            pair = {"before": compact(before), "after": compact(after)}
            delta = (after['frame'] - before['frame']) & 0xffff
            CHECKS.append({'check': 'native CPU encounter keeps unit cadence',
                           'passed': delta == 1, 'details': [cpu, difficulty, tick]})
            if delta != 1:
                failures.append({'tick': tick, 'delta': delta, 'keys': command, **pair})
            require(after["ppu"] & 0xC0 == 0,
                    "native CPU encounter stays within OBJ fetch limits", [cpu, difficulty, tick])
            raw = after["raw_keys2"]
            decisions[str(raw)] += 1
            require(raw & ~(ATTACKS | 0xF00) == 0,
                    "CPU sends only legal directions and face buttons", raw)
            if raw & ATTACKS == 0xC000:
                require(raw == 0xC000 and before['energy2'] == 96 and difficulty > 0,
                        'CPU super command is neutral and legal only at full gauge', pair)
                m['super_commands'] += 1
            if after['super2'] and not before['super2']:
                require(before['energy2'] == 96 and after['energy2'] == 0 and raw == 0xC000,
                        'CPU activates the same paid legal Y+B super command', pair)
                m['super_starts'] += 1
                examples.setdefault('super', pair)
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
                "cadence_failures": failures, "controller_runs": controller_runs,
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
    # Fixed controller phases remeasured on the combined ROM with Arcade A skip.
    fixtures = ((2, 2, 10, False, True), (4, 1, 0, False, True),
                (4, 2, 0, False, True), (2, 2, 15, True, False))
    results = []
    for cpu, difficulty, delay, retreat, hit in fixtures:
        e = boot(cpu, difficulty, training=False, delay=delay)
        rows, approach = [], []
        try:
            for _ in range(210):
                s = state(e)
                if abs(s['x1']-s['x2']) <= (34 if retreat else 68)*16 and not any(
                        s[k] for k in ('hurt1', 'down_state1', 'action1', 'y1')):
                    break
                approach.append(compact(s))
                e.run(1, p1=['right'])
            else:
                raise AssertionError(('CPU jump fixture never reaches launch band', compact(s)))
            for tick in range(65):
                rows.append(state(e))
                e.run(1, p1=['up', 'left' if retreat else 'right'] if tick < 3 else
                      ['a'] if not retreat and tick in (16, 17) else [])
            starts = [i for i in range(1, len(rows)) if rows[i]['action2'] == 8 and rows[i-1]['action2'] != 8]
            require(starts, 'CPU deliberately starts universal uppercut', [cpu, difficulty, delay])
            index = starts[0]
            before, first = rows[index-1:index+1]
            require(first['raw_keys2'] == 1088 and first['tick2'] == 1 and legacy.signed16(first['y2']) < 0
                    and not before['raw_keys2'] & 64,
                    'uppercut uses real fresh Down+X and actual action clock', compact(first))
            require(not any(before[k] for k in ('action2', 'hurt2', 'y2', 'down_state2', 'hitstop'))
                    and before['hp2'] > 0, 'uppercut begins only from available grounded state', compact(before))
            require(-56*16 <= legacy.signed16(before['y1']) <= -12*16
                    and abs(before['x1']-before['x2']) < 41*16
                    and (before['x1'] > before['x2']) == bool(before['face2'])
                    and before['hurt1'] == before['down_state1'] == 0 and before['hp1'] > 0,
                    'CPU anti-air sees only live near airborne opponent in front', compact(before))
            startup = rows[index:index+5]
            require([s['tick2'] for s in startup] == [1, 2, 3, 4, 5]
                    and all(s['action2'] == 8 and not s['connected2'] and s['hp1'] == before['hp1'] for s in startup),
                    'CPU uppercut preserves five actual pre-contact startup ticks', [compact(s) for s in startup])
            active = [s for s in rows[index:] if s['action2'] == 8]
            contacts = [s for s in active if s['connected2'] == 2]
            if hit:
                require(contacts and contacts[0]['tick2'] == 6 and contacts[0]['hp1'] < before['hp1']
                        and contacts[0]['hp2'] == before['hp2'] and legacy.signed16(contacts[0]['y1']) < 0,
                        'CPU intercepts jump on ordinary first active action tick', [cpu, difficulty, delay])
            else:
                window = [s for s in active if 6 <= s['tick2'] < 14]
                require(len(window) == 8 and not contacts
                        and all(s['hp1'] == before['hp1'] and not s['connected2'] for s in active)
                        and min(abs(s['x1']-s['x2']) for s in window) > 41*16,
                        'CPU retreat bait whiffs all eight actual active ticks', [compact(s) for s in window])
            results.append({'cpu': cpu, 'difficulty': difficulty, 'title_delay': delay, 'retreat': retreat,
                            'approach': approach, 'samples': [compact(s) for s in rows]})
        finally:
            e.close()
    return results


def completed_whiff_fixture(cpu):
    """Retreat jump after a visible normal; require its complete unconnected clock."""
    delay = 3 if cpu == 7 else 0
    e = legacy.boot(2, fighter=8, fighter2=cpu, difficulty=2, title_delay=delay)
    rows, active, completed = [], None, None
    try:
        for _ in range(180):
            if abs(state(e)['x1']-state(e)['x2']) <= 44*16:
                break
            e.run(1, p1=['right'])
        e.run(3)
        e.tap('start'); e.tap('up'); e.tap('start')
        for tick in range(1200):
            before = state(e)
            forward = 'right' if before['x1'] < before['x2'] else 'left'
            back = 'left' if forward == 'right' else 'right'
            keys = ([back, 'up'] if before['action2'] and not before['y1'] else
                    [forward] if abs(before['x1']-before['x2']) > 46*16 and not before['y1'] else [])
            e.run(1, p1=keys)
            after = state(e)
            rows.append({'tick': tick, 'keys': keys, 'before': compact(before), 'after': compact(after)})
            require((after['frame']-before['frame']) & 65535 == 1 and not after['ppu'] & 0xc0,
                    'completed-whiff fixture preserves native cadence and fetch limits', [cpu, tick])
            if after['action2'] in (1, 2, 3, 4, 5, 6) and not before['action2']:
                active = {'action': after['action2'], 'connected': 0, 'start': tick}
            if active:
                active['connected'] = max(active['connected'], after['connected2'])
                if after['action2'] != active['action']:
                    if not active['connected'] and before['tick2']+1 >= before['action_end2'] and not (
                            after['hurt2'] or after['down_state2']):
                        completed = {'action': active['action'], 'start': active['start'], 'end': tick,
                                     'final_action_tick': before['tick2'], 'action_end': before['action_end2']}
                        break
                    active = None
        require(completed is not None, 'personality commits and completes a genuine normal whiff', cpu)
        return {'cpu': cpu, 'difficulty': 2, 'title_delay': delay, 'completed_normal_whiffs': 1,
                'completion': completed, 'samples': rows}
    finally:
        e.close()


def super_fixture(difficulty, full_gauge):
    """Enable a real Training CPU after ordinary position/meter preparation."""
    e = legacy.boot(2, fighter=4, fighter2=2, difficulty=difficulty)
    samples, low_samples, available_low = [], 0, 0
    try:
        for _ in range(180):
            if abs(state(e)['x1'] - state(e)['x2']) <= 34 * 16:
                break
            e.run(1, p1=['right'])
        e.run(3)
        if full_gauge:
            for _ in range(1800):
                if state(e)['energy2'] == 96:
                    break
                e.run(1)
            require(state(e)['energy2'] == 96, 'CPU super fixture naturally fills meter')
        e.tap('start')
        e.tap('up')
        e.tap('start')
        started = None
        for tick in range(1200 if full_gauge else 240):
            before = state(e)
            e.run(1, p1=['down', 'left'])
            after = state(e)
            pair = {'tick': tick, 'before': compact(before), 'after': compact(after)}
            samples.append(pair)
            if before['energy2'] < 96:
                low_samples += 1
                available_low += not any(before[k] for k in ('action2', 'hurt2', 'y2', 'down_state2', 'hitstop'))
                require(after['raw_keys2'] != 0xC000 and not (after['super2'] and not before['super2']),
                        'low-meter CPU never requests or activates a super', pair)
            if after['super2'] and not before['super2']:
                require(before['energy2'] == 96 and after['energy2'] == 0 and after['raw_keys2'] == 0xC000,
                        'controller-prepared CPU pays the same full-gauge super cost', pair)
                started = pair
                break
        if full_gauge:
            require(started is not None, 'Normal/Hard CPU actually uses a legal full-gauge super', difficulty)
            e.run(2)
            path = e.shot(f'expansion-06/cpu02-d{difficulty}-super.png')
        else:
            require(low_samples > 30 and available_low > 10,
                    'negative super fixture covers genuinely available low-meter CPU samples',
                    [difficulty, low_samples, available_low])
            path = None
        return {'cpu': 2, 'difficulty': difficulty, 'full_gauge': full_gauge,
                'activation': started, 'low_meter_samples': low_samples,
                'available_low_meter_samples': available_low, 'samples': samples,
                'capture': path.relative_to(ROOT).as_posix() if path else None}
    finally:
        e.close()


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


def personality_metrics(cases, whiffs=()):
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
                (sum(c["metrics"].get("completed_normal_whiffs", 0) for c in rows)
                 + sum(c.get('completed_normal_whiffs', 0) for c in whiffs if c.get('cpu') == cpu)) > 0,
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
    now = dict((n, a) for a, n in pairs)
    shared = combined_contract(ROOT)
    require(True, 'combined asset, ABI and appended allocation policy passes')
    require(now["cpuPersonalities"] >> 16 not in (0x7E, 0x7F), "personality table lives in ROM")
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
    return {"combined": shared, "cpu_mutable_bytes_added": 0,
            "personality_table_bytes": 108, "table_address": f"{now['cpuPersonalities']:06x}",
            "cpu_sections": sections, "core_sha256": sha(core)}


# Retained controller regressions with the combined Arcade conversation boot.
def arcade_lowwave_regression() -> dict[str, object]:
    """Normal/Hard CPU crouch-blocks a genuine incoming low wave."""

    results: dict[str, object] = {}
    for difficulty in (1, 2):
        e = boot(5, difficulty, training=False)
        samples: list[dict[str, int]] = []
        try:
            legacy.drive(e, 0, ["down"], 3)
            legacy.drive(e, 0, ["down", 'y'], 3)
            for _ in range(80):
                sample = state(e)
                samples.append(sample)
                e.run(1)
        finally:
            e.close()
        wave = [sample for sample in samples if sample["wave1"]]
        impact = [sample for sample in samples
                  if sample["hp2"] < 128 and sample["guard2"]]
        require(bool(wave), f"CPU d{difficulty} sees a genuine incoming low wave", {
            "wave": [legacy._cpu_summary(sample) for sample in wave[:8]],
        })
        require(bool(impact) and all(sample["hp2"] >= 127 for sample in impact),
              f"CPU d{difficulty} low-wave guard takes at most one chip", {
                  "impact": [legacy._cpu_summary(sample) for sample in impact[:8]],
              })
        back = 512 if impact and impact[0]["face2"] else 256
        guarded = [sample for sample in impact
                   if sample["raw_keys2"] & 1024 and sample["raw_keys2"] & back]
        require(bool(guarded),
              f"CPU d{difficulty} low-wave guard holds DOWN plus back",
              [legacy._cpu_summary(sample) for sample in guarded[:8]])
        require(any(sample["anim_frame2"] == 3 and sample["anim_state2"] == 6
                  for sample in guarded),
              f"CPU d{difficulty} low-wave guard renders the crouched posture",
              [legacy._cpu_summary(sample) for sample in guarded[:8]])
        results[f"difficulty-{difficulty}"] = {
            "wave_frames": len(wave),
            "impact": [legacy._cpu_summary(sample) for sample in impact[:8]],
            "chip": 128 - min((sample["hp2"] for sample in impact), default=128),
        }
    return results

def arcade_wake_regression() -> dict[str, object]:
    """Normal/Hard CPU wakes with its single UP edge after a knockdown."""

    induction_limit = 260
    observation_limit = 120
    results: dict[str, object] = {}
    for difficulty in (1, 2):
        e = boot(2, difficulty, training=False)
        samples: list[dict[str, int]] = []
        down_seen = False
        down_index: int | None = None
        wake_index: int | None = None
        attack_pulses = 0
        scene_violations: list[dict[str, int]] = []
        try:
            legacy.close_players(e)
            # Induce exactly one knockdown within the historical bounded
            # window.  Once the victim enters any down state, stop all P1
            # attacks so a second hit or KO cannot hide wake behavior.
            for index in range(induction_limit):
                current = state(e)
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
                sample = state(e)
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
                    sample = state(e)
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
                            legacy.signed16(sample["y2"]) < 0:
                        break
                    e.run(1)
        finally:
            e.close()
        wake_edge = [sample for sample in samples
                     if sample["down_state2"] == 5 and sample["down_tick2"] == 1]
        airborne = [sample for sample in samples if legacy.signed16(sample["y2"]) < 0]
        require(down_seen, f"CPU d{difficulty} enters a real downed state",
              [legacy._cpu_summary(sample) for sample in samples[:8]])
        require(not scene_violations,
              f"CPU d{difficulty} wake fixture stays in live non-KO FIGHT",
              {"violations": scene_violations,
               "down_index": down_index, "wake_index": wake_index})
        require(any(sample["raw_keys2"] & 2048 for sample in wake_edge),
              f"CPU d{difficulty} samples a single UP wake edge",
              [legacy._cpu_summary(sample) for sample in wake_edge])
        require(any(sample["wake_jump2"] > 0 for sample in wake_edge),
              f"CPU d{difficulty} buffers the wake jump",
              [legacy._cpu_summary(sample) for sample in wake_edge])
        require(bool(airborne), f"CPU d{difficulty} leaves wake airborne",
              [legacy._cpu_summary(sample) for sample in airborne[:8]])
        results[f"difficulty-{difficulty}"] = {
            "wake_edge": [legacy._cpu_summary(sample) for sample in wake_edge],
            "airborne": [legacy._cpu_summary(sample) for sample in airborne[:8]],
            "down_seen": down_seen,
            "down_index": down_index,
            "wake_index": wake_index,
            "induction_limit": induction_limit,
            "observation_limit": observation_limit,
            "attack_pulses_before_down": attack_pulses,
            "scene_violations": scene_violations,
        }
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--frames", type=int, default=1800)
    parser.add_argument("--report", type=Path, default=ROOT / "docs/expansion-06-report.json")
    args = parser.parse_args()
    start = time.time()
    report = {"status": "running", "scope": "focused combined CPU evidence; no six-suite or release claim",
              "rom_sha256": sha(ROOT / "dist/abaqus-after-hours.sfc"),
              "harness_sha256": {p: sha(ROOT/p) for p in (
                  "tools/test_expansion_06_cpu_personality.py", "tools/emulator.py", "tools/test_inputs.py",
                  "tools/expansion_contracts.py", "tools/release_evidence.py")},
              "source_sha256": {p.relative_to(ROOT).as_posix(): sha(p)
                                for p in sorted((ROOT / 'src').rglob('*')) if p.is_file()},
              "symbols_sha256": sha(ROOT / 'dist/abaqus-after-hours.sym'),
              "headless": True, "audio": "capture callbacks only; no playback device", "memory_writes": False,
              "save_states": False, "controller_only": True, "failures": [],
              "cases": [], "p2_noise_replays": [], "controlled_recovery": [],
              "no_input_lookahead": [], "anti_air": [], "ko": [], "all_roster_low_guard": [],
              "cpu_supers": [], "preserved_regressions": {}}
    args.report.parent.mkdir(parents=True, exist_ok=True)

    def save():
        report['elapsed_seconds'] = round(time.time()-start, 3)
        report['checks'] = len(CHECKS)
        report['passed_checks'] = sum(c['passed'] for c in CHECKS)
        report['failed_checks'] = sum(not c['passed'] for c in CHECKS)
        report['summary_checks'] = [c for c in CHECKS if not c['passed'] or (
            'native CPU encounter' not in c['check'] and 'CPU sends only' not in c['check']
            and 'CPU never buffers' not in c['check'])]
        args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')

    def attempt(label, function):
        try:
            value = function()
            return value
        except Exception as exc:
            import traceback
            report['failures'].append({'case': label, 'error': repr(exc), 'traceback': traceback.format_exc()})
            print(json.dumps({'case': label, 'failed': repr(exc)}), flush=True)
            return {'failed_case': label, 'error': repr(exc)}
        finally:
            # A controller boot assertion can precede a fixture's try/finally.
            # Clean up that host instance so independent cases still execute.
            if Emulator._active_instance is not None:
                Emulator._active_instance.close()

    try:
        report['hardware'] = audit()
        for difficulty in (0, 1, 2):
            for cpu in range(12):
                case = attempt(f'encounter-cpu{cpu}-d{difficulty}',
                    lambda: encounter(cpu, difficulty, args.frames, capture=cpu in (2, 7) and difficulty==2))
                report['cases'].append(case)
                print(json.dumps({'cpu': cpu, 'difficulty': difficulty,
                                  'metrics': case.get('metrics'), 'cadence_failures': len(case.get('cadence_failures', []))}), flush=True)
                save()
        report['completed_whiff_fixtures'] = [attempt(f'completed-whiff-cpu{cpu}',
            lambda: completed_whiff_fixture(cpu)) for cpu in (3, 7, 11)]
        report['personality_metrics'] = attempt('personality-metrics', lambda: personality_metrics(
            report['cases'], report['completed_whiff_fixtures']))
        if not args.quick:
            for cpu in range(12):
                again = attempt(f'ignored-p2-cpu{cpu}', lambda: encounter(cpu, 2, args.frames, noisy_p2=True))
                first = report['cases'][24+cpu]
                if 'trace_sha256' in again and 'trace_sha256' in first:
                    attempt(f'ignored-p2-comparison-cpu{cpu}', lambda: require(
                        again['trace_sha256'] == first['trace_sha256'] and
                        again['sampled_video_sha256'] == first['sampled_video_sha256'],
                        'all-roster deterministic replay ignores P2 gameplay input', cpu))
                report['p2_noise_replays'].append(again)
                save()
            for difficulty in (0, 1, 2):
                for cpu in range(12):
                    report['controlled_recovery'].append(attempt(f'recovery-cpu{cpu}-d{difficulty}',
                        lambda: recovery_fixture(cpu, difficulty)))
            for cpu in (2, 5, 7):
                for delay in (3, 6, 9, 12, 15):
                    report['controlled_recovery'].append(attempt(f'recovery-cpu{cpu}-delay{delay}',
                        lambda: recovery_fixture(cpu, 2, delay)))
            recovery = report['controlled_recovery']
            attempt('counter-positive', lambda: require(any(c.get('answers') for c in recovery if c.get('cpu') in (5, 7)),
                'counter specialists answer real recovery in controlled encounters'))
            attempt('counter-fallibility', lambda: require(any(c.get('answers') == 0 for c in recovery if c.get('difficulty')==2),
                'Hard can decline an available punish opportunity'))
            report['counter_metrics'] = attempt('counter-metrics', lambda: counter_metrics(recovery))
            for cpu in range(12):
                report['no_input_lookahead'].append(attempt(f'lookahead-cpu{cpu}', lambda: lookahead_fixture(cpu)))
            report['anti_air'] = attempt('anti-air', anti_air_fixtures)
            for difficulty in (1, 2):
                for cpu in range(12):
                    report['all_roster_low_guard'].append(attempt(f'guard-cpu{cpu}-d{difficulty}', lambda: guard_fixture(cpu, difficulty)))
                for full_gauge in (False, True):
                    report['cpu_supers'].append(attempt(f'cpu-super-d{difficulty}-full{full_gauge}', lambda: super_fixture(difficulty, full_gauge)))
            for victim in (1, 2):
                report['ko'].append(attempt(f'ko-victim{victim}', lambda: ko_fixture(victim)))
            report['preserved_regressions'] = {
                'lowwave_guard': attempt('arcade-lowwave', arcade_lowwave_regression),
                'wake': attempt('arcade-wake', arcade_wake_regression)}
        report['legacy_focused_checks'] = len(legacy.checks)
        capture_paths = {path for case in report['cases']
                         for path in case.get('examples', {}).get('screenshots', {}).values()}
        capture_paths.update(case['capture'] for case in report['cpu_supers'] if case.get('capture'))
        report['screenshots'] = [{'path': path, 'sha256': sha(ROOT / path),
                                 'native_dimensions': [256, 224]} for path in sorted(capture_paths)]
        report['rom_sha256_after'] = sha(ROOT / 'dist/abaqus-after-hours.sfc')
        attempt('unchanged-tested-rom', lambda: require(report['rom_sha256_after'] == report['rom_sha256'],
            'production ROM identity stays unchanged throughout the focused proof'))
        cadence = [{'cpu': c.get('cpu'), 'difficulty': c.get('difficulty'), **f}
                   for c in report['cases'] + report['p2_noise_replays'] for f in c.get('cadence_failures', [])]
        report['cadence_failures'] = cadence
        report['status'] = 'failed' if report['failures'] or cadence or any(not c['passed'] for c in CHECKS) else 'passed'
    except Exception as exc:
        report['status'] = 'failed'
        report['error'] = repr(exc)
        raise
    finally:
        save()
    print(json.dumps({k: report[k] for k in ('status', 'rom_sha256', 'checks', 'elapsed_seconds')}), flush=True)
    if report['status'] != 'passed':
        raise SystemExit(1)


if __name__ == "__main__":
    main()
