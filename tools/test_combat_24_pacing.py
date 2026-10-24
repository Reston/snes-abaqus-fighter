"""Focused combined-ROM pacing/recoil proof: real pads, read-only telemetry.

Run with .tools/python/python.exe tools/run_background.py --log build/pacing.log
-- .tools/python/python.exe tools/test_combat_24_pacing.py. Shared suites and
their reports are deliberately not written by this feature driver.
"""
from __future__ import annotations

import argparse
import ctypes as C
import hashlib
import json
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import test_expansion_03_normal_balance as balance
from test_characters import boot
from test_characters import uploaded_frame_id
from test_champion import host_contract
from test_inputs import trace, signed16
from release_evidence import EXPECTED_NATIVE_CORE
from expansion_contracts import combined_contract
from contact_geometry import generate as generate_geometry, world
import test_expansion_06_cpu_personality as cpu
import test_expansion_07_supers as supers

BASE = 'f75005d'
JUMP_VY_OVERRIDES = {1: -96, 4: -86, 6: -86, 9: -105}
FRAME_OWNERS = {
    'attack-v1': {5, 6, 7, 8, 9, 10, 12, 13, 15, *range(32, 46), 47},
    'jump-v1': {29, 30, 31, *range(49, 56)},
    'super-v1': {1, 2, 4},
}
OUT = ROOT / 'docs/screenshots/combat-24-pacing'
ROM = ROOT / 'dist/abaqus-after-hours.sfc'
SYM = ROOT / 'dist/abaqus-after-hours.sym'
CHECKS = []
CHECK_INDEX = {}
METRICS = balance.metrics
FAILURES = {'cadence': [], 'ppu': [], 'spc': [], 'assertions': []}
HARNESS = ('tools/test_combat_24_pacing.py', 'tools/test_characters.py', 'tools/test_inputs.py',
           'tools/emulator.py', 'tools/run_background.py', 'tools/test_champion.py',
           'tools/test_presentation.py', 'tools/release_evidence.py', 'tools/expansion_contracts.py',
           'tools/v024_contracts.py', 'tools/test_expansion_03_normal_balance.py',
           'tools/contact_geometry.py',
           'tools/test_expansion_06_cpu_personality.py', 'tools/test_expansion_07_supers.py')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source_hashes():
    return {p.relative_to(ROOT).as_posix(): sha(p.read_bytes())
            for p in sorted((ROOT / 'src').rglob('*')) if p.is_file()}


def git(path):
    return subprocess.check_output(['git', 'show', BASE + ':' + path], cwd=ROOT)


def require(ok, label, detail=None):
    # Retain one representative per invariant and count all executions. Native
    # controller traces live in their cases; repeated passing samples should
    # not turn the committed focused report into hundreds of megabytes.
    if ok and label in CHECK_INDEX:
        CHECK_INDEX[label]['executions'] += 1
    else:
        row = {'check': label, 'passed': bool(ok), 'details': detail, 'executions': 1}
        CHECKS.append(row)
        CHECK_INDEX[label] = row
    if not ok:
        FAILURES['assertions'].append({'check': label, 'details': detail})
        raise AssertionError((label, detail))


class Rig(balance.Rig):
    def __init__(self, fighter, port, opponent=None, mode=1):
        opponent = fighter if opponent is None else opponent
        p1, p2 = (fighter, opponent) if port == 0 else (opponent, fighter)
        self.e = boot(mode, p1, fighter % 3, p2, rom=ROM)
        self.port, self.fighter = port, fighter
        self.a, self.d = str(port + 1), str(2 - port)
        self.tag = f'fighter{fighter:02d} P{self.a}'
        self.syms = balance.symbols(SYM)
        self.base = self.syms['fighters'] - 0x7e0000

    def read(self, name, count=1):
        return list(C.string_at(self.e.ram + (self.syms[name] & 0x1ffff), count))

    def step(self, attack=(), defend=()):
        before = self.state()['frame']
        audio = self.e.audio_samples
        s = super().step(attack, defend)
        if self.e.audio_samples <= audio:
            raise AssertionError(('native PCM callback missing', self.tag, s))
        delta = (s['frame'] - before) & 65535
        if delta != 1:
            FAILURES['cadence'].append([self.tag, s['frame'], delta])
            raise AssertionError(('native cadence', self.tag, s))
        if METRICS['ppu_overflow']:
            FAILURES['ppu'] = METRICS['ppu_overflow']
            raise AssertionError(('PPU overflow', self.tag, s))
        if METRICS['peak_spc_backlog'] > 6:
            FAILURES['spc'].append([self.tag, s['frame'], METRICS['peak_spc_backlog']])
            raise AssertionError(('SPC FIFO', self.tag, s))
        return s

    def capture(self, label):
        OUT.mkdir(parents=True, exist_ok=True)
        path = OUT / f'{self.fighter:02d}-p{self.a}-{label}.png'
        self.e.frame.save(path)
        METRICS['captures'].append(path.relative_to(ROOT).as_posix())


balance.Rig = Rig
balance.check = require


def recoil(r, key, blocked=False, capture=None):
    r.position(26)
    guard = ('down', r.direction(False, True)) if blocked else ()
    before = r.state()
    frames = []
    s = r.step((key,), guard)
    for _ in range(45):
        frames.append(r.e.frame.copy())
        if s[f'connected{r.a}']:
            break
        s = r.step((), guard)
    require(s[f'connected{r.a}'] == (1 if blocked else 2), r.tag + ' recoil starts on real contact', [key, blocked])
    contact = s
    expected = 1 if contact[f'x{r.d}'] > contact[f'x{r.a}'] else -1
    rows = []
    while s['hitstop'] or s[f'hurt{r.d}']:
        old = s
        s = r.step((), guard)
        frames.append(r.e.frame.copy())
        if not old['hitstop']:
            rows.append({'dx': s[f'x{r.d}'] - old[f'x{r.d}'], 'hurt': s[f'hurt{r.d}'],
                         'guard': s[f'guard{r.d}'], 'frame': s[f'anim_frame{r.d}']})
    require(all(row['dx'] * expected >= 0 for row in rows), r.tag + ' recoil never reverses', rows)
    movement = [abs(row['dx']) for row in rows]
    total = abs(s[f'x{r.d}'] - before[f'x{r.d}']) / 16
    if capture:
        OUT.mkdir(parents=True, exist_ok=True)
        path = OUT / f'damian-{capture}.gif'
        # Every native frame retained; 17 ms GIF units are an approximation.
        frames[0].save(path, save_all=True, append_images=frames[1:], duration=17, loop=0, optimize=False)
        METRICS['captures'].append(path.relative_to(ROOT).as_posix())
    r.settle()
    return {'distance_pixels': total, 'live_deltas_12_4': movement,
            'rows': rows, 'contact': {k: contact[k] for k in
             ('hitstop', f'hurt{r.d}', f'guard{r.d}', f'hp{r.d}', f'tick{r.a}')},
            'damage': before[f'hp{r.d}'] - contact[f'hp{r.d}']}


def motion(fighter, port):
    r = Rig(fighter, port)
    try:
        s = r.state()
        out = {}
        for toward, label, field in ((True, 'walk', 'speed'), (False, 'retreat', 'back_speed')):
            before = s[f'x{r.a}']
            keys = (r.direction(toward),)
            for _ in range(24):
                s = r.step(keys)
            distance = abs(s[f'x{r.a}'] - before)
            require(distance == 24 * s[f'{field}{r.a}'], r.tag + ' movement matches native per-tick speed', label)
            out[label] = {'ticks': 24, 'distance_12_4': distance, 'speed_12_4': s[f'{field}{r.a}']}
        return out
    finally:
        r.close()


def wave(fighter, port):
    r = Rig(fighter, port)
    try:
        if r.state()[f'family{r.a}'] not in (0, 2):
            return {'family': 'direct', 'wave': False}
        # Opposite corners plus a continuously airborne defender avoid contact
        # without injecting a wave or changing either native hurt rectangle.
        for _ in range(200):
            r.step(('left' if port == 0 else 'right',), ('right' if port == 0 else 'left',))
        r.step()
        s = r.step(('down', 'y'), ('up',))
        for _ in range(40):
            if s[f'wave{r.a}']:
                break
            s = r.step((), ('up',))
        require(s[f'wave{r.a}'] == 1, r.tag + ' special creates an ordinary projectile')
        raw = r.read('waves', 32)[port * 16:(port + 1) * 16]
        speed, life = raw[8], raw[6]
        x = int.from_bytes(bytes(raw[:2]), 'little', signed=True)
        initial = {'x_12_4': x, 'remaining_life': life, 'speed_12_4': speed}
        samples = []
        for _ in range(30):
            s = r.step((), ('up',))
            raw = r.read('waves', 32)[port * 16:(port + 1) * 16]
            if not raw[4]:
                break
            now = int.from_bytes(bytes(raw[:2]), 'little', signed=True)
            samples.append(abs(now - x)); x = now
        require(len(samples) >= 20 and set(samples) == {speed}, r.tag + ' projectile travels at the measured slower speed', samples)
        return {**initial, 'measured_steps': len(samples), 'step_deltas': sorted(set(samples))}
    finally:
        r.close()


def special_timing(fighter, port):
    r = Rig(fighter, port)
    try:
        r.position(150)
        initial = r.state()
        s = r.step(('down', 'y'))
        require(s[f'action{r.a}'] == 7, r.tag + ' slow-special proof begins with paid ordinary command')
        timing = r.timing()
        require(timing['startup'] == s[f'special_startup{r.a}'] and
                timing['active'] == s[f'special_active{r.a}'] and
                timing['recovery'] == s[f'special_recovery{r.a}'],
                r.tag + ' ordinary special exposes exact native startup/active/recovery', timing)
        xs = [s[f'x{r.a}'] - initial[f'x{r.a}']]
        vertical = []
        while s[f'action{r.a}']:
            if initial[f'family{r.a}'] == 3:
                raw = r.read('fighters', 128)[port * 64:(port + 1) * 64]
                vertical.append({'tick': raw[17], 'y_12_4': signed16(s[f'y{r.a}']),
                                 'vy_12_4': int.from_bytes(bytes(raw[4:6]), 'little', signed=True)})
            s = r.step(); xs.append(s[f'x{r.a}'] - initial[f'x{r.a}'])
        if initial[f'family{r.a}'] == 1:
            speed = 48 if fighter == 2 else 42
            old_ticks = 13 if fighter == 2 else 15
            require(xs[:3] == [0, 0, 0] and abs(xs[-1]) == speed * old_ticks,
                    r.tag + ' rush adds stationary telegraph and preserves total travel', xs)
        if vertical:
            preparation = [row for row in vertical if row['tick'] < timing['startup']]
            launch = [row for row in vertical if row['tick'] == timing['startup']]
            require(preparation and all(row['y_12_4'] == row['vy_12_4'] == 0 for row in preparation),
                    r.tag + ' rising special keeps its readable preparation grounded', preparation)
            require(len(launch) == 1 and launch[0]['y_12_4'] == -1 and
                    launch[0]['vy_12_4'] == {5: -86, 7: -80, 10: -97}[fighter],
                    r.tag + ' rising special launches at active contact with preserved velocity', launch)
        return {**timing, 'horizontal_travel_12_4': abs(xs[-1]), 'first_three_x_deltas': xs[:3],
                'rising_launch_samples': vertical}
    finally:
        r.close()


def geometry_contract():
    header, data = generate_geometry(ROOT)
    require(header == (ROOT/'build/contact_geometry_data.h').read_bytes(),
            'pacing range oracle derives from the current native pixels')
    syms = balance.symbols(SYM)
    rom = ROM.read_bytes()
    def linked(name, size):
        address = syms[name]
        offset = ((address >> 16) & 127) * 32768 + (address & 32767)
        return rom[offset:offset+size]
    table = bytes(v for fighter in data['poses'] for pose in fighter for rect in pose for v in rect)
    require(linked('contactPoses', len(table)) == table and
            linked('contactGeometryDigest', 32).hex() == data['digest'],
            'exact cartridge contains the independently derived contact table and digest')
    return data


def normal_ranges(fighter, port, geometry):
    """Bracket the raster boundary; legacy profile reach is no longer an oracle."""
    r = Rig(fighter, port)
    result = {}
    try:
        for key, action, role in balance.MOVES:
            tag = f'{r.tag} {role}'
            r.position(110)
            hp = r.state()[f'hp{r.d}']
            s = r.step((key,))
            require(s[f'action{r.a}'] == action, tag+' uses the face-button action')
            timing = r.timing(); ticks = [s[f'tick{r.a}']]
            while s[f'action{r.a}']:
                press = ('x',) if key == 'y' and s[f'tick{r.a}'] == timing['startup'] else ()
                s = r.step(press)
                if s[f'action{r.a}']:
                    require(s[f'action{r.a}'] == action, tag+' whiff retains its commitment')
                    ticks.append(s[f'tick{r.a}'])
            require(ticks == list(range(1, timing['total'])) and s[f'hp{r.d}'] == hp,
                    tag+' completes every native whiff tick', {**timing, 'ticks': ticks})
            frame = 5 if action == 1 else 6 if action == 3 else 7
            strike = world(geometry['poses'][fighter][frame][2])
            limits = []
            for idle in range(16, 20):
                bands = [world(rect, face=0) for rect in geometry['poses'][fighter][idle][:2]]
                limits.append(max((strike[2]-body[0])/16 for body in bands
                                  if strike[1] < body[3] and strike[3] > body[1]))
            lo, hi = min(limits), max(limits)
            outside = r.position(hi+3)
            hp = r.state()[f'hp{r.d}']; s = r.step((key,)); connected = 0
            for _ in range(timing['total']+8):
                connected = max(connected, s[f'connected{r.a}'])
                s = r.step()
            require(outside > hi and not connected and s[f'hp{r.d}'] == hp,
                    tag+' whiffs beyond all idle pose bands', [outside, lo, hi])
            inside = r.position(max(25, lo-3))
            before = r.state(); s = r.step((key,))
            for _ in range(timing['total']+8):
                if s[f'connected{r.a}']:
                    break
                s = r.step()
            damage = before[f'hp{r.d}']-s[f'hp{r.d}']
            require(s[f'connected{r.a}'] == 2 and s[f'tick{r.a}'] == timing['startup'] and
                    s[f'anim_frame{r.a}'] == frame and
                    damage > 0 and not s[f'guard{r.d}'] and not s[f'down_state{r.d}'],
                    tag+' first active tick causes real raster-overlap damage', [inside, s])
            result[role] = {**timing, 'attack_frame': frame, 'idle_pose_cutoff_pixels': [lo, hi],
                            'outside_whiff_gap': outside, 'inside_hit_gap': inside, 'damage': damage,
                            'first_contact_tick': s[f'tick{r.a}']}
            r.settle()
        lp, sp, lk, sk = (result[name] for _, _, name in balance.MOVES)
        require(lp['startup'] < lk['startup'] < sk['startup'] <= sp['startup'],
                r.tag+' speed roles remain distinct', result)
        require(lp['damage'] < lk['damage'] < sk['damage'] < sp['damage'],
                r.tag+' damage roles remain distinct', result)
        require(lp['total'] < lk['total'] < sk['total'] <= sp['total']+1,
                r.tag+' stronger normals require longer commitment', result)
        return result
    finally:
        r.close()


def block_and_punish(fighter, port):
    """Keep the original risk/punish proof against legal standing guards.

    These four neutral normals are high/mid. Final-art Fernando's jab ends
    exactly at his crouch band's top (row 29), so Down+Back correctly ducks
    it at every spacing. Standing Back proves actual blocked contact and
    the original timing/punish outcomes; Down+B retains its separate low test.
    """
    r = Rig(fighter, port)
    result = {}
    try:
        for key, action, role in balance.MOVES:
            for punish in (False, True):
                r.position(26)
                guard = (r.direction(False, True),)
                attacker_guard = (r.direction(False),)
                hp = r.state()[f'hp{r.a}']
                defender_hp = r.state()[f'hp{r.d}']
                s = r.step((key,), guard)
                for _ in range(40):
                    if s[f'connected{r.a}']:
                        break
                    s = r.step((), guard)
                require(s[f'connected{r.a}'] == 1 and s[f'guard{r.d}'] == 1,
                        f'{r.tag} {role} is honestly blocked', s)
                contact = s
                frozen = s['hitstop']
                # A blocked hit cannot confirm into a special, even if pressed
                # during hitstop. Preserve the original command and clocks.
                s = r.step(('down', 'y'), guard)
                while s['hitstop']:
                    s = r.step(attacker_guard, guard)
                s = r.step(attacker_guard, guard)
                require(s[f'action{r.a}'] == action and s[f'energy{r.a}'] >= contact[f'energy{r.a}'],
                        f'{r.tag} {role} cannot special-cancel blocked contact', s)
                live = 1
                attacker_free = defender_free = None
                jab_sent = False
                response = None
                for _ in range(70):
                    if not s[f'action{r.a}'] and attacker_free is None:
                        attacker_free = live
                    if not s[f'hurt{r.d}'] and defender_free is None:
                        defender_free = live
                    dk = guard
                    if punish and not jab_sent and not s[f'hurt{r.d}']:
                        dk = ('y', r.direction(False, True))
                        jab_sent = True
                    s = r.step(attacker_guard, dk)
                    live += int(not s['hitstop'])
                    if punish and jab_sent and s[f'connected{r.d}']:
                        response = s
                        break
                    if not punish and attacker_free is not None and defender_free is not None:
                        break
                if not punish:
                    advantage = defender_free - attacker_free
                    require((-4 <= advantage <= -2 if role == 'jab' else
                             -4 <= advantage <= -2 if role == 'light_kick' else advantage <= -10),
                            f'{r.tag} {role} has the intended measured block risk',
                            {'advantage': advantage, 'attacker_free': attacker_free,
                             'defender_free': defender_free})
                    result[role] = {'block_advantage_first_active': advantage,
                                    'attacker_recovers_after': attacker_free,
                                    'defender_recovers_after': defender_free,
                                    'captured_hitstop': frozen,
                                    'blocked_contact_chip': defender_hp - contact[f'hp{r.d}'],
                                    'guard_command': 'standing relative Back'}
                else:
                    if role == 'jab':
                        advantage = result[role]['block_advantage_first_active']
                        jab_startup = balance.profiles()[fighter]['startup'][0]
                        expected_hit = jab_startup < -advantage
                        require(response is not None and (s[f'hp{r.a}'] < hp) == expected_hit,
                                r.tag + ' jab response follows its actual startup and block disadvantage', response)
                    if role in ('strong_punch', 'strong_kick'):
                        require(response is not None and response[f'connected{r.d}'] == 2 and s[f'hp{r.a}'] < hp,
                                f'{r.tag} blocked {role} is actually jab-punishable', response)
                    result[role]['immediate_jab_response'] = (
                        'hit' if response and response[f'connected{r.d}'] == 2 else
                        'blocked' if response else 'whiff')
                r.settle()
        return result
    finally:
        r.close()


def damian_sample(label):
    r = Rig(0, 0)
    try:
        result = {}
        for key, name, blocked in (('y', 'light', False), ('x', 'strong', False), ('x', 'guard', True)):
            result[name] = recoil(r, key, blocked, label + '-' + name)
    finally:
        r.close()
    return {'motion': motion(0, 0), 'projectile': wave(0, 0), 'recoil': result}


def crossup(fighter, port):
    r = Rig(fighter, port)
    try:
        result = {}
        for key in ('a', 'x'):
            r.position(24)
            hp = r.state()[f'hp{r.d}']
            original = r.state()[f'face{r.a}']
            sign = 1 if original else -1
            s = r.step(('up', r.direction()), (r.direction(True, True),))
            air_speed = abs(signed16(s[f'jump_vx{r.a}']))
            start = balance.profiles()[fighter]['startup'][4 if key == 'a' else 2] - 3
            # Reston's low arc always remains inside body separation height.
            # Commit startup before crossing; waiting until after crossing
            # would consume his remaining airtime at the slower chase speed.
            anticipatory_gap = (start - 1) * (air_speed + s[f'speed{r.d}'] - 24) + air_speed + s[f'speed{r.d}'] - 1
            sent = False
            for _ in range(90):
                crossed = (s[f'x{r.a}'] - s[f'x{r.d}']) * sign > 0
                keys = ()
                anticipatory = fighter == 9 and not crossed and (s[f'x{r.d}'] - s[f'x{r.a}']) * sign <= anticipatory_gap
                if (anticipatory or (crossed and signed16(s[f'y{r.a}']) >= -48 * 16)) and not sent:
                    keys = (key,); sent = True
                s = r.step(keys, (r.direction(True, True),))
                if sent and s[f'connected{r.a}']:
                    break
                if sent and not s[f'action{r.a}'] and not s[f'y{r.a}']:
                    break
            if key == 'x':
                require(sent and s[f'hp{r.d}'] == hp and not s[f'connected{r.a}'], r.tag + ' air strong punch cannot hit behind')
            else:
                gap = abs(s[f'x{r.a}'] - s[f'x{r.d}']) / 16
                # canHit's rear center reach is 16+10 pixels. Initial strong
                # recoil moves four more pixels away on that very contact tick.
                require(s[f'action{r.a}'] == 5 and s[f'air_action{r.a}'] == 1 and
                        s[f'face{r.a}'] == original and signed16(s[f'y{r.a}']) < 0 and
                        (s[f'x{r.a}'] - s[f'x{r.d}']) * sign > 0 and gap - 4 <= 26 and
                        s[f'connected{r.a}'] == 2 and not s[f'down_state{r.d}'], r.tag + ' real rear kick retains original contact reach', s)
                oldx = s[f'x{r.d}']; steps = []; landed = False
                while s['hitstop'] or s[f'hurt{r.d}']:
                    prior = s
                    s = r.step()
                    if not prior['hitstop']:
                        delta = s[f'x{r.d}'] - prior[f'x{r.d}']
                        require(delta * sign <= 0, r.tag + ' rear recoil keeps contact side through landing', [delta, s])
                        steps.append(delta)
                        landed |= not s[f'y{r.a}']
                result = {'post_impulse_gap': gap, 'contact_gap_before_impulse': gap - 4,
                          'contact_tick': r.timing()['startup'], 'recoil_steps': steps,
                          'recoil_pixels': abs(s[f'x{r.d}'] - oldx) / 16, 'attacker_landed_during_recoil': landed,
                          'startup_before_crossing': fighter == 9}
            r.settle()
        return result
    finally:
        r.close()


def trades_and_corner(fighter, port):
    r = Rig(fighter, port)
    try:
        r.position(26)
        s = r.step(('y',), ('y',))
        for _ in range(20):
            if s['connected1'] and s['connected2']:
                break
            s = r.step()
        require(s['connected1'] == s['connected2'] == 2 and s['hp1'] < 128 and s['hp2'] < 128,
                r.tag + ' simultaneous jab snapshots both deal damage', s)
        contact = s
        signs = [1 if s['x1'] > s['x2'] else -1, 1 if s['x2'] > s['x1'] else -1]
        drift = []
        while s['hitstop'] or s['hurt1'] or s['hurt2']:
            old = s; s = r.step()
            if not old['hitstop']:
                dx = [s[f'x{p+1}'] - old[f'x{p+1}'] for p in range(2)]
                require(all(dx[p] * signs[p] >= 0 for p in range(2)), r.tag + ' both trade latches recoil apart', dx)
                drift.append(dx)
        r.settle()
        outward = 'right' if port == 0 else 'left'
        for _ in range(270):
            r.step((outward,), (outward,))
        r.position(26)
        s = r.step(('x',))
        for _ in range(30):
            if s[f'connected{r.a}']:
                break
            s = r.step()
        wall = (232 if port == 0 else 24) * 16
        require(s[f'connected{r.a}'] == 2 and s[f'x{r.d}'] == wall, r.tag + ' strong initial recoil clamps to real wall', s)
        corner_ticks = 0
        while s['hitstop'] or s[f'hurt{r.d}']:
            s = r.step(); corner_ticks += 1
            require(s[f'x{r.d}'] == wall, r.tag + ' every strong hurt tick remains corner-clamped', s[f'x{r.d}'])
        return {'trade_hp': [contact['hp1'], contact['hp2']], 'trade_drift_12_4': drift, 'corner_ticks': corner_ticks}
    finally:
        r.close()


def knockout(fighter, port):
    r = Rig(fighter, port)
    try:
        hits = []
        for _ in range(14):
            r.position(26)
            s = r.step(('x',))
            for _ in range(35):
                if s[f'connected{r.a}']:
                    break
                s = r.step()
            require(s[f'connected{r.a}'] == 2, r.tag + ' KO probe uses real strong hit')
            hits.append(s[f'hp{r.d}'])
            if s[f'hp{r.d}'] == 0:
                require(s['round_end'] > 0 and s[f'hp{r.a}'] == 128, r.tag + ' real KO enters winner countdown', s)
                for _ in range(12):
                    s = r.step()
                return {'hp_steps': hits, 'round_end': s['round_end'], 'winner': port}
            r.settle()
        raise AssertionError(('KO not reached', fighter, port, hits))
    finally:
        r.close()


def cpu_checks(fighter):
    cpu.SYMBOLS = {n: a & 0x1ffff for n, a in balance.symbols(SYM).items()}
    cpu.require = require
    runs = []
    for difficulty in (0, 1, 2):
        a = cpu.encounter(fighter, difficulty, 1800)
        require(not a['cadence_failures'], 'CPU encounter advances every native video tick', [fighter, difficulty, a['cadence_failures']])
        if difficulty == 2:
            b = cpu.encounter(fighter, difficulty, 1800, noisy_p2=True)
            require(not b['cadence_failures'] and a['trace_sha256'] == b['trace_sha256'] and
                    a['sampled_video_sha256'] == b['sampled_video_sha256'],
                    'CPU ignores P2 gameplay input with identical native trace/video', fighter)
            a['ignored_p2_trace_sha256'] = b['trace_sha256']
        # Keep observations and controller script; shared policy tables are not
        # used as an oracle for what a particular encounter must decide.
        runs.append(a)
    return {'encounters': runs, 'lookahead': cpu.lookahead_fixture(fighter)}


def guarded_super_contact(fighter, port):
    """Hold close 28px spacing between legal rising-super guard windows.

    Continuous Back retreats during charge/gaps and can evade a finisher.
    Keep every legacy contact assertion and change only the supplied pads.
    This owner-local policy has no dependency on another producer's driver.
    """
    if fighter not in (5, 7, 10):
        return supers.contact(fighter, port, guard=True)
    original_step = supers.step
    defender = 1 - port
    back = 'right' if defender == 1 else 'left'
    rows = []

    def timed_guard_step(e, p1=(), p2=(), monitor=True):
        before = supers.sample(e)
        supplied = list((p1, p2)[defender])
        next_tick = before['ticks'][port] + int(not before['hitstop'])
        contact_now = (before['superPhase'][port] > 0 and
                       next_tick < before['superContactEnd'][port])
        new_pulse = (before['superPhase'][port] < len(supers.HITS[fighter]) and
                     next_tick >= before['superNext'][port])
        window = bool(before['superActive'][port] and (contact_now or new_pulse))
        if not window:
            if defender == 0:
                p1 = ()
            else:
                p2 = ()
        state = original_step(e, p1, p2, monitor)
        if supplied:
            rows.append({'clock_before': before['ticks'][port], 'phase_before': before['superPhase'][port],
                         'next_clock': next_tick, 'next_pulse': before['superNext'][port],
                         'contact_end': before['superContactEnd'][port], 'pulse_window': window,
                         'super_active_before': before['superActive'][port],
                         'supplied_defense': supplied, 'controller_keys': [list(p1), list(p2)],
                         'defender_x_before': before[f'x{defender+1}'],
                         'defender_x_after': state[f'x{defender+1}']})
        return state

    supers.step = timed_guard_step
    try:
        result = supers.contact(fighter, port, guard=True)
    finally:
        supers.step = original_step
    require(rows and all(row['supplied_defense'] == [back] and
                         row['controller_keys'][defender] == ([back] if row['pulse_window'] else [])
                         for row in rows),
            'rising guard uses relative back only in committed pulse windows', [fighter, port])
    startup = [row for row in rows if row['super_active_before'] and
               row['phase_before'] == 0 and not row['pulse_window']]
    require(startup and all(row['defender_x_before'] == row['defender_x_after'] for row in startup),
            'neutral rising-super startup guard fixture holds defender position', [fighter, port])
    result['controller_policy'] = 'standing relative back during pulse windows; neutral startup gaps recovery'
    result['guard_controller_rows'] = rows
    return result


def super_checks(fighter):
    supers.SYMBOLS = balance.symbols(SYM)
    supers.check = require
    result = {'chord': supers.activation(fighter), 'ports': []}
    for port in (0, 1):
        result['ports'].append({'port': port + 1,
                               'hits': supers.contact(fighter, port),
                               'guard': guarded_super_contact(fighter, port),
                               'interrupt': supers.interrupt(fighter, port)})
    require(not supers.timing['cadence_failures'] and not supers.timing['overflow_failures'],
            'super contacts preserve native cadence and OBJ limits', supers.timing)
    return result


def clocks_and_dma(fighter):
    r = Rig(fighter, 0)
    def video_ram():
        return C.string_at(r.e.core.retro_get_memory_data(3), 65536)
    try:
        seconds, tick = r.state()['seconds'], r.read('secondTick')[0]
        actor_changes = [0, 0]; peak = 0
        before = video_ram()
        for index in range(120):
            keys = ('left',) if index < 40 else ('right',) if index < 80 else ()
            r.step(keys, ('right',) if index < 40 else ('left',) if index < 80 else ())
            after = video_ram()
            changed = []
            for port, start in enumerate((0xc000, 0xd400)):
                offsets = [i for i, (a, b) in enumerate(zip(before[start:start+0x1400], after[start:start+0x1400])) if a != b]
                if offsets:
                    changed.append(port); actor_changes[port] += 1
                    peak = max(peak, len(offsets))
                    require(len(offsets) <= 3840 and all(i % 512 < 384 for i in offsets),
                            'actor writes stay inside five 384-byte rows with native padding', [fighter, port, len(offsets)])
                    require(uploaded_frame_id(r.e, fighter, port) is not None,
                            'uploaded actor matches an exact current native pose', [fighter, port])
            require(len(changed) <= 1, 'at most one actor changes VRAM per vblank', [fighter, index, changed])
            before = after
        require(r.state()['seconds'] == seconds - (tick + 120) // 60 and r.read('secondTick')[0] == (tick + 120) % 60,
                'normal match clock still counts sixty live native ticks per second', fighter)
        require(min(actor_changes) > 0, 'DMA sample actually uploads both actors', [fighter, actor_changes])
        s = r.step(('start',))
        paused_seconds, paused_tick = s['seconds'], r.read('secondTick')[0]
        for _ in range(60):
            s = r.step()
        require(s['paused'] and s['seconds'] == paused_seconds and r.read('secondTick')[0] == paused_tick,
                'pause freezes combat clock while native rendering and PCM continue', fighter)
        s = r.step((), ('start',))
        require(not s['paused'], 'P2 Start resumes the real paused match', fighter)
        return {'live_ticks': 120, 'paused_ticks': 60, 'actor_upload_samples': actor_changes, 'peak_changed_actor_bytes': peak}
    finally:
        r.close()


def rear_trade(fighter, port):
    # Both jump through one another with locked takeoff facing. Equal native
    # air clocks allow two short rear boxes to trade on one atomic snapshot.
    attempts = []
    for gap in (24, 28, 32):
        r = Rig(fighter, port)
        try:
            r.position(gap)
            face = r.state()[f'face{r.a}']; sign = 1 if face else -1
            s = r.step(('up', r.direction()), ('up', r.direction(True, True)))
            air_speed = abs(signed16(s[f'jump_vx{r.a}']))
            air_start = balance.profiles()[fighter]['startup'][4] - 3
            # While they face one another, native separation removes 24
            # fixed-point units from each tick's closing distance. Schedule
            # startup so its first active snapshot is just after crossing.
            threshold = (air_start - 1) * (2 * air_speed - 24) + 2 * air_speed - 1
            sent = False; contact = None
            for _ in range(100):
                ak, dk = (), ()
                crossed = (s[f'x{r.a}'] - s[f'x{r.d}']) * sign > 0
                if not crossed and (s[f'x{r.d}'] - s[f'x{r.a}']) * sign <= threshold and not sent:
                    ak = dk = ('a',); sent = True
                s = r.step(ak, dk)
                if s['hp1'] < 128 or s['hp2'] < 128:
                    contact = s; break
                if sent and not s[f'y{r.a}']:
                    break
            attempts.append({'gap': gap, 'hp': [s['hp1'], s['hp2']], 'action': [s['action1'], s['action2']]})
            if not contact or s['connected1'] != 2 or s['connected2'] != 2:
                continue
            require((s[f'x{r.a}'] - s[f'x{r.d}']) * sign > 0 and s[f'face{r.a}'] == face,
                    r.tag + ' rear trade occurs behind locked takeoff facing', s)
            # Recoil points opposite each attacker's locked facing, while
            # existing airborne momentum carries each victim further away.
            grounded = []
            while s['hitstop'] or s[f'hurt{r.d}']:
                old = s; s = r.step()
                if not old['hitstop']:
                    dx = s[f'x{r.d}'] - old[f'x{r.d}']
                    require(dx * sign <= 0, r.tag + ' simultaneous rear-trade victim keeps snapshotted recoil', dx)
                    grounded.append(dx)
            return {'fixture_attempts': attempts, 'hp': [contact['hp1'], contact['hp2']], 'rear_victim_recoil_12_4': grounded}
        finally:
            r.close()
    require(False, 'controller rear trade must be reproducible', [fighter, port, attempts])


def preservation():
    shared = combined_contract(ROOT)
    assets, native = shared['assets'], shared['native']
    require(assets['baseline_commit'] == native['baseline_commit'] == BASE,
            'independent combined policy uses the approved v0.23.1 baseline')
    require(assets['generated_count'] == 226,
            'combined generated inventory contains exactly 226 files', assets['generated_count'])
    require(assets['frame_ownership'] == {k: sorted(v) for k, v in FRAME_OWNERS.items()} and
            sum(map(len, FRAME_OWNERS.values())) == len(set().union(*FRAME_OWNERS.values())) == 37,
            'three disjoint feature sets own 37 poses and preserve the other 27')
    require(len(assets['fighters']) == 12 and all(r['preserved_frames'] >= 27 for r in assets['fighters']),
            'every fighter preserves all 27 unowned poses with exact portraits palettes scales and old sources')
    require(native['prior_ram_labels'] == native['unchanged_prior_ram_labels'] == 1318 and
            not native['documented_relocations'] and not native['appended_ram_symbols'],
            'all 1318 prior RAM labels remain unchanged with no added mutable RAM', native)
    now = balance.symbols(SYM)
    # Shared policy audits hardware's bounded hit-reaction section and TRACE;
    # sibling-owned animation, superFrame, version and game hooks may differ.
    path = 'src/knockdown.h'
    require(git(path).replace(b'\r\n', b'\n') == (ROOT / path).read_bytes().replace(b'\r\n', b'\n'),
            path + ' remains byte-identical after newline normalization')
    sections = []
    for name, address in now.items():
        if not name.startswith('SECTIONSTART_') or address < 0x800000:
            continue
        end = now.get(name.replace('SECTIONSTART_', 'SECTIONEND_'))
        if end is not None and end > address:
            sections.append([address, end, name])
    require(all(a >> 16 == (b - 1) >> 16 and b - a <= 32768 for a, b, _ in sections), 'all linked native sections fit 32 KiB LoROM banks')
    require(len(ROM.read_bytes()) == 4194304 and ROM.read_bytes()[0x7fd5] == 0x30, 'native 4 MiB FastROM LoROM cartridge')
    return {'combined': shared, 'sections': len(sections), 'pacing_new_mutable_bytes': 0,
            'recoil_storage': 'existing rearKickRecoil byte: one nibble per port; direction bits0..1, strong bit2, direct-super link bit3'}


def profile_audit():
    pattern = (r'\{\s*([\d,\-\sA-Z_]+),\s*\{([\d,]+)\}, '
               r'\{([\d,]+)\}, \{([\d,]+)\}, \{([\d,]+)\}')
    def parse(source):
        families = {'SPECIAL_PROJECTILE': 0, 'SPECIAL_RUSH': 1, 'SPECIAL_GROUNDWAVE': 2, 'SPECIAL_RISING': 3}
        rows = []
        for row in re.findall(pattern, source):
            fields = [families[x.strip()] if x.strip() in families else int(x) for x in row[0].split(',')]
            rows.append([fields, *[list(map(int, x.split(','))) for x in row[1:]]])
        return rows
    old, new = parse(git('src/characters.h').decode()), parse((ROOT / 'src/characters.h').read_text())
    require(len(old) == len(new) == 12, 'profile audit sees exactly twelve fighters')
    result = []
    for fighter, (a, b) in enumerate(zip(old, new)):
        require(b[0][2] == JUMP_VY_OVERRIDES.get(fighter, a[0][2]),
                'only four approved jump launch overrides differ from the baseline',
                [fighter, a[0][2], b[0][2]])
        require(all(a[0][i] == b[0][i] for i in (3, 4, 5, 6, 7, 9, 11, 12, 15)) and a[3:] == b[3:],
                'gravity uppercut special launch damage reach throws and family preserved', fighter)
        require(all(b[0][i] == round(a[0][i] * .82) for i in (0, 1)), 'movement speed is rounded to 82 percent', fighter)
        require(b[1] == [v + (3 if i in (2, 4, 5) else 0) for i, v in enumerate(a[1])] and
                b[2] == [v + (4 if i in (2, 4, 5) else 0) for i, v in enumerate(a[2])],
                'ground heavy timing changes are exact and fast light timing preserved', fighter)
        require(b[0][8] == a[0][8] + 3 and b[0][10] == a[0][10] + 5,
                'ordinary special gains three startup and five recovery ticks', fighter)
        row = {'fighter': fighter, 'walk_12_4': [a[0][0], b[0][0]], 'retreat_12_4': [a[0][1], b[0][1]],
               'jump_vy': [a[0][2], b[0][2]], 'approved_jump_override': fighter in JUMP_VY_OVERRIDES}
        if a[0][7] in (0, 2):
            old_range, new_range = a[0][13] * a[0][14], b[0][13] * b[0][14]
            require(abs(old_range - new_range) <= b[0][13] and b[0][13] == round(a[0][13] * .82),
                    'projectile lifetime preserves nominal travel within one slower step', [fighter, old_range, new_range])
            row['projectile'] = {'speed_12_4': [a[0][13], b[0][13]], 'life_ticks': [a[0][14], b[0][14]],
                                 'nominal_range_12_4': [old_range, new_range]}
        else:
            require(a[0][13:15] == b[0][13:15], 'direct special speed/life preserved', fighter)
        result.append(row)
    pacing = (ROOT / 'src/pacing_recoil.h').read_text(encoding='utf-8')
    air = re.search(r'u8 pacingAirSpeed\(u8 id\)\s*\{(.*?)\n\}', pacing, re.S)
    require(air is not None, 'old horizontal jump launch has a dedicated pacingAirSpeed hook')
    air_speeds = {int(i): int(v) for i, v in re.findall(r'case\s+(\d+):\s*return\s+(\d+);', air[1])}
    default = re.search(r'default:\s*return\s+(\d+);', air[1])
    require(set(air_speeds) == set(range(11)) and default is not None,
            'horizontal launch switch explicitly covers the twelve fighters')
    air_speeds[11] = int(default[1])
    require(all(air_speeds[i] == row[0][0] + 8 for i, row in enumerate(old)),
            'all twelve horizontal jump launches preserve old walk speed plus eight', air_speeds)
    game = (ROOT / 'src/game.c').read_text(encoding='utf-8')
    require(re.search(r'if\(keys&KEY_RIGHT\)f->vx=pacingAirSpeed\(f->id\);\s*'
                      r'else if\(keys&KEY_LEFT\)f->vx=-pacingAirSpeed\(f->id\);', game) is not None,
            'both horizontal takeoff directions use the preserved air speed')
    require(re.search(r'if\(f->airAction && \(a==3 \|\| a>=5\)\)\s*\{\s*'
                      r'f->actionStartup-=3;f->actionActiveEnd-=3;f->actionEnd-=7;', game) is not None,
            'airborne heavy startup active and recovery restore original timing')
    symbols = balance.symbols(SYM)
    address = symbols['hitStunByDamage']
    offset = ((address >> 16) & 127) * 32768 + (address & 32767)
    table = ROM.read_bytes()[offset:offset + 256]
    require(table == bytes(12 + damage // 3 for damage in range(256)),
            'all 256 compiled 65816 applyHitReaction damage/stun entries remain exact')
    return result


def main():
    global ROM, SYM, OUT
    p = argparse.ArgumentParser()
    p.add_argument('--sample', choices=('before', 'after'))
    p.add_argument('--fighters', default=','.join(map(str, range(12))))
    p.add_argument('--report', default='docs/combat-24-pacing-report.json')
    p.add_argument('--baseline', action='store_true')
    args = p.parse_args()
    fighters = list(map(int, args.fighters.split(',')))
    if not fighters or len(set(fighters)) != len(fighters) or any(i not in range(12) for i in fighters):
        p.error('--fighters must list distinct roster IDs 0..11')
    if args.baseline and not args.sample:
        p.error('--baseline is historical sample media only; it cannot supply combined evidence')
    partial = bool(args.sample) or set(fighters) != set(range(12))
    if partial:
        report_path = (ROOT/args.report).resolve()
        if not report_path.is_relative_to((ROOT/'build').resolve()):
            p.error('samples and partial rosters require --report under build; they are diagnostic only')
        OUT = report_path.parent/(report_path.stem+'-captures')
    if args.baseline:
        ROM, SYM = ROOT / 'build/pacing-baseline.sfc', ROOT / 'build/pacing-baseline.sym'
    report = {'status': 'failed', 'scope': 'historical baseline sample' if args.baseline else (
                  'limited pacing sample' if args.sample else 'combined-ROM focused pacing/recoil'),
              'combined_pass_claimed': False, 'combined_focused_coverage_complete': False,
              'diagnostic_only': partial, 'selected_fighters': fighters,
              'historical_evidence': 'Prior isolated reports and GIFs are historical; only captures produced by this invocation are current.',
              'rom_path': str(ROM), 'rom_sha256': sha(ROM.read_bytes()), 'symbols_sha256': sha(SYM.read_bytes()),
              'base_commit': BASE, 'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
              'command': subprocess.list2cmdline([sys.executable, *sys.argv]),
              'host_contract': {**host_contract(), 'platform': platform.platform(), 'memory_writes': False, 'save_states': False},
              'test_sha256': sha(Path(__file__).read_bytes()),
              'source_sha256': source_hashes(),
              'harness_sha256': {path: sha((ROOT / path).read_bytes()) for path in HARNESS},
              'checks': CHECKS, 'metrics': METRICS, 'failure_arrays': FAILURES, 'roster': []}
    start = time.monotonic()
    try:
        require(not report['host_contract']['gui_opened'] and not report['host_contract']['audio_device_opened'],
                'silent headless host')
        require(report['host_contract'].get('priority_class') == 0x4000 and
                len(report['host_contract']['logical_processors']) <= 2,
                'background runner priority and affinity enforced', report['host_contract'])
        core = sha((ROOT / '.tools/core/snes9x_libretro.dll').read_bytes())
        require(core == EXPECTED_NATIVE_CORE['dll_sha256'], 'pinned native Snes9x core', core)
        report['core_sha256'] = core
        if args.sample:
            report['damian'] = damian_sample(args.sample)
        else:
            report['preservation'] = preservation()
            report['profiles'] = profile_audit()
            geometry = geometry_contract()
            report['contact_geometry_digest'] = geometry['digest']
            for fighter in fighters:
                for port in (0, 1):
                    row = {'fighter': fighter, 'port': port + 1}
                    report['roster'].append(row)
                    row['motion'] = motion(fighter, port)
                    row['wave'] = wave(fighter, port)
                    row['special_timing'] = special_timing(fighter, port)
                    row['normals'] = normal_ranges(fighter, port, geometry)
                    row['confirms'] = balance.confirms_and_low(fighter, port)
                    row['blocks'] = block_and_punish(fighter, port)
                    row['corner'] = balance.corner_jab_guard(fighter, port)
                    row['air_crossup'] = crossup(fighter, port)
                    row['special_confirm'] = balance.special_confirm(fighter, port)
                    row['trades_and_corner'] = trades_and_corner(fighter, port)
                    row['rear_trade'] = rear_trade(fighter, port)
                    row['ko'] = knockout(fighter, port)
                    r = Rig(fighter, port)
                    try:
                        row['recoil'] = {name: recoil(r, key, blocked) for key, name, blocked in
                                         (('y', 'light', False), ('x', 'strong', False), ('x', 'guard', True))}
                    finally:
                        r.close()
                    d = row['recoil']
                    require(d['strong']['distance_pixels'] > d['light']['distance_pixels'] > d['guard']['distance_pixels'],
                            'strong/light/guard recoil separate visibly', [fighter, port, d])
                    for name in d:
                        dx = d[name]['live_deltas_12_4']
                        require(dx == sorted(dx, reverse=True), 'recoil eases monotonically', [fighter, port, name, dx])
                    print(f'fighter {fighter:02d} P{port+1} complete', flush=True)
                row['supers'] = super_checks(fighter)
                row['cpu'] = cpu_checks(fighter)
                row['clocks_and_dma'] = clocks_and_dma(fighter)
                print(f'fighter {fighter:02d} super/CPU complete', flush=True)
            report['combined_focused_coverage_complete'] = set(fighters) == set(range(12))
        require(sha(ROM.read_bytes()) == report['rom_sha256'] and sha(SYM.read_bytes()) == report['symbols_sha256'],
                'exact ROM and symbols retained throughout focused proof')
        require(source_hashes() == report['source_sha256'] and
                {path: sha((ROOT / path).read_bytes()) for path in HARNESS} == report['harness_sha256'],
                'production source and harness inputs retained throughout focused proof')
        report['status'] = 'diagnostic_passed' if partial else 'passed'
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        report['rom_sha256_after'] = sha(ROM.read_bytes())
        report['symbols_sha256_after'] = sha(SYM.read_bytes())
        report['source_sha256_after'] = source_hashes()
        report['harness_sha256_after'] = {path: sha((ROOT/path).read_bytes()) for path in HARNESS}
        report['changed_harness_inputs'] = [path for path in HARNESS if
                                           report['harness_sha256'][path] != report['harness_sha256_after'][path]]
        if report['changed_harness_inputs']:
            report['diagnostic_provenance_issue'] = {
                'changed_harness_inputs': report['changed_harness_inputs'],
                'meaning': 'Concurrent harness edits invalidate stable-input evidence; this alone is not a ROM defect.'}
        report['dependency_sha256'] = report['harness_sha256']
        report['super_metrics'] = supers.timing
        report['captures'] = [{'path': path, 'sha256': sha((ROOT / path).read_bytes()),
                               'evidence_scope': 'historical baseline' if args.baseline else 'current invocation'}
                              for path in sorted(set(METRICS['captures']))]
        report['elapsed_seconds'] = round(time.monotonic() - start, 3)
        report['check_inventory'] = CHECKS
        report['checks'] = sum(c['executions'] for c in CHECKS)
        report['passed'] = sum(c['executions'] for c in CHECKS if c['passed'])
        path = ROOT / args.report
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
        print(json.dumps({k: report.get(k) for k in ('status', 'passed', 'rom_sha256', 'elapsed_seconds', 'error')}))


if __name__ == '__main__':
    main()
