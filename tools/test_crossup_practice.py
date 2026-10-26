"""Verify practical rear medium-kick setups for all twelve native fighters.

This supplements the six suites. It drives both controllers without memory
writes/save states, using each fighter's existing movement and attack timing.
The default report stays under ignored build/; --rom supports a negative
regression fixture without replacing the current cartridge.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import test_matchups
from emulator import Emulator
from make_crossup_review import process_contract
from release_evidence import EXPECTED_NATIVE_CORE
from test_inputs import signed16, trace

NAMES = ('Damian', 'Ivo', 'Cristobal', 'Cote', 'Negger', 'David',
         'Fernando', 'Cristian', 'Madariaga', 'Reston', 'Roxana', 'Lars')
# These are reproducible controller setups, not new profile or balance values.
# Understep means the defender walks toward the jump until centers cross.
RECIPES = {fighter: ('neutral', 24) for fighter in range(12)}
RECIPES.update({1: ('understep', 24), 3: ('understep', 36),
                4: ('understep', 48), 6: ('understep', 36), 9: ('understep', 24)})


def require(condition, label, details=None):
    if not condition:
        raise RuntimeError((label, details))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def practice_case(fighter, port, stage):
    recipe, gap = RECIPES[fighter]
    opponent = (fighter+1) % 12
    ids = (fighter, opponent) if port == 0 else (opponent, fighter)
    e = test_matchups.boot_match(*ids, stage)
    attacker, defender = str(port+1), str(2-port)
    sign = 1 if port == 0 else -1
    forward = 'right' if port == 0 else 'left'
    toward_jumper = 'left' if port == 0 else 'right'
    try:
        for _ in range(180):
            initial = trace(e)
            if abs(initial['x1']-initial['x2']) <= gap*16:
                break
            e.run(1, **{'p'+attacker: [forward]})
        e.run(3)
        initial = trace(e)
        require(initial['fighter_id'+attacker] == fighter and
                initial['fighter_id'+defender] == opponent and initial['arena'] == stage and
                initial['hp1'] == initial['hp2'] == 128,
                'Correct healthy roster pairing and arena', initial)
        e.run(1, **{'p'+attacker: ['up', forward]})
        rows = [trace(e)]
        sent = crossed = False
        for _ in range(84):
            state = rows[-1]
            relative = (state['x'+defender]-state['x'+attacker])*sign
            crossed = crossed or relative < 0
            keys = []
            cue = relative <= 8*16 if recipe == 'understep' else crossed
            if not sent and cue and signed16(state['y'+attacker]) < 0:
                keys = ['a']
                sent = True
            under = [toward_jumper] if recipe == 'understep' and not crossed else []
            e.run(1, **{'p'+attacker: keys, 'p'+defender: under})
            rows.append(trace(e))
        airborne = [state for state in rows if signed16(state['y'+attacker]) < 0]
        contacts = [index for index, state in enumerate(rows) if state['connected'+attacker]]
        require(sent and crossed and airborne and contacts,
                'Practical controller setup must produce a crossing and contact', rows)
        index = contacts[0]
        contact = rows[index]
        require(contact['connected'+attacker] == 2 and contact['air_action'+attacker] == 1 and
                contact['action'+attacker] == 5 and signed16(contact['y'+attacker]) < 0 and
                0 < (contact['x'+attacker]-contact['x'+defender])*sign <= 26*16+32 and
                contact['hp'+attacker] == 128 and contact['hp'+defender] < 128 and
                contact['guard'+defender] == 0 and contact['hitstop'] == 5,
                'First contact is a rear airborne medium kick with normal hitstop', contact)
        require(all(state['face'+attacker] == int(port == 0) for state in airborne),
                'Takeoff facing stays locked until landing', airborne)
        frozen = rows[index+1:index+6]
        fields = ('x1', 'x2', 'y1', 'y2', 'hurt1', 'hurt2', 'anim_tick1', 'anim_tick2')
        require(len(frozen) == 5 and all(all(state[key] == contact[key] for key in fields)
                                       for state in frozen),
                'Five contact hitstop ticks freeze physics and animation', frozen)
        drift = [(before, after) for before, after in zip(rows[index:], rows[index+1:])
                 if before['hurt'+defender] and not before['guard'+defender] and not before['hitstop']]
        # A close understep can also receive the existing 12/16px body push.
        # Check the combined movement: both contributions must point away.
        require(drift and all((after['x'+defender]-before['x'+defender])*(-sign) in (9, 21)
                             for before, after in drift),
                'Hurt recoil and close body separation both push away', drift)
        require(all((after['frame']-before['frame']) & 0xffff == 1
                    for before, after in zip(rows, rows[1:])),
                'Every measured callback advances native telemetry once')
        landed = rows[-1]
        require(landed['y'+attacker] == landed['air_action'+attacker] == landed['action'+attacker] == 0 and
                landed['face'+attacker] == int(landed['x'+attacker] < landed['x'+defender]) and
                all(state['down_state'+defender] == 0 for state in rows),
                'Landing clears the air action and restores positional facing', landed)
        return {'fighter': fighter, 'name': NAMES[fighter], 'opponent': opponent,
                'port': port, 'stage': stage, 'recipe': recipe,
                'starting_gap_px': abs(initial['x1']-initial['x2'])/16,
                'contact': contact, 'damage': 128-contact['hp'+defender],
                'hurt_drift_ticks': len(drift),
                'hurt_ticks_after_attacker_landing': sum(before['y'+attacker] == 0 for before, _ in drift),
                'landed': landed, 'passed': True}
    finally:
        e.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, default=ROOT/'dist/abaqus-after-hours.sfc')
    parser.add_argument('--report', type=Path, default=ROOT/'build/crossup-practice-report.json')
    for name, count in (('fighter', 12), ('port', 2), ('stage', 3)):
        parser.add_argument('--'+name, type=int, choices=range(count))
    args = parser.parse_args()
    host = process_contract()
    rom = args.rom.resolve()
    manifest = json.loads((ROOT/'dist/manifest.json').read_bytes())
    core = ROOT/'.tools/core/snes9x_libretro.dll'
    require(sha(core) == EXPECTED_NATIVE_CORE['dll_sha256'], 'Pinned expanded Snes9x core')
    test_matchups.Emulator = lambda: Emulator(rom=rom)
    report = {'status': 'running', 'scope': 'supplemental real-controller cross-up practice coverage; no human balance approval',
              'rom_sha256': sha(rom), 'rom_bytes': rom.stat().st_size,
              'version': manifest['version'] if sha(rom) == manifest['sha256'] else 'regression-fixture',
              'core_sha256': sha(core), 'host_contract': host, 'cases': [],
              'harness_sha256': {name: sha(ROOT/name) for name in (
                  'tools/test_crossup_practice.py', 'tools/test_matchups.py', 'tools/test_inputs.py',
                  'tools/emulator.py', 'tools/make_crossup_review.py')},
              'recipes': {str(key): {'route': value[0], 'approach_gap_px': value[1]}
                          for key, value in RECIPES.items()}}
    started = time.monotonic()
    try:
        for fighter in ([args.fighter] if args.fighter is not None else range(12)):
            for port in ([args.port] if args.port is not None else (0, 1)):
                for stage in ([args.stage] if args.stage is not None else range(3)):
                    result = practice_case(fighter, port, stage)
                    report['cases'].append(result)
                    print(json.dumps({key: result[key] for key in ('fighter', 'port', 'stage', 'recipe', 'damage', 'passed')}), flush=True)
        report['status'] = 'passed'
    except Exception as error:
        report['status'] = 'failed'
        report['failure'] = str(error)
    report['elapsed_seconds'] = round(time.monotonic()-started, 3)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_bytes((json.dumps(report, indent=2)+'\n').encode())
    print(json.dumps({'status': report['status'], 'cases': len(report['cases']),
                      'report': str(args.report), 'failure': report.get('failure')}), flush=True)
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
