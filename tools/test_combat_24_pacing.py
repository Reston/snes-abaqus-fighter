"""Isolated pacing/recoil proof: real native pads, read-only telemetry, no GUI.

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
import test_expansion_06_cpu_personality as cpu
import test_expansion_07_supers as supers

BASE = '3f51120'
OUT = ROOT / 'docs/screenshots/combat-24-pacing'
ROM = ROOT / 'dist/abaqus-after-hours.sfc'
SYM = ROOT / 'dist/abaqus-after-hours.sym'
CHECKS = []
CHECK_INDEX = {}
METRICS = balance.metrics
FAILURES = {'cadence': [], 'ppu': [], 'spc': [], 'assertions': []}


def sha(data):
    return hashlib.sha256(data).hexdigest()


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
        while s[f'action{r.a}']:
            s = r.step(); xs.append(s[f'x{r.a}'] - initial[f'x{r.a}'])
        if initial[f'family{r.a}'] == 1:
            speed = 48 if fighter == 2 else 42
            old_ticks = 13 if fighter == 2 else 15
            require(xs[:3] == [0, 0, 0] and abs(xs[-1]) == speed * old_ticks,
                    r.tag + ' rush adds stationary telegraph and preserves total travel', xs)
        return {**timing, 'horizontal_travel_12_4': abs(xs[-1]), 'first_three_x_deltas': xs[:3]}
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
            sent = False
            for _ in range(90):
                crossed = (s[f'x{r.a}'] - s[f'x{r.d}']) * sign > 0
                keys = ()
                if crossed and signed16(s[f'y{r.a}']) >= -48 * 16 and not sent:
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
                          'recoil_pixels': abs(s[f'x{r.d}'] - oldx) / 16, 'attacker_landed_during_recoil': landed}
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


def super_checks(fighter):
    supers.SYMBOLS = balance.symbols(SYM)
    supers.check = require
    result = {'chord': supers.activation(fighter), 'ports': []}
    for port in (0, 1):
        result['ports'].append({'port': port + 1,
                               'hits': supers.contact(fighter, port),
                               'guard': supers.contact(fighter, port, guard=True),
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
                            'uploaded actor matches an exact preserved native pose', [fighter, port])
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
    now = balance.symbols(SYM)
    old = balance.symbols_text(git('dist/abaqus-after-hours.sym').decode())
    ram = {n: a for n, a in old.items() if a < 0x2000 or 0x7e0000 <= a < 0x800000}
    moved = {n: [a, now.get(n)] for n, a in ram.items() if now.get(n) != a}
    added = {n: a for n, a in now.items() if n not in old and (a < 0x2000 or 0x7e0000 <= a < 0x800000)}
    require(not moved and not added, 'no mutable RAM addresses or allocation change', {'moved': moved, 'added': added})
    files = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASE, 'assets/generated'], cwd=ROOT).decode().splitlines()
    delta = [p for p in files if git(p) != (ROOT / p).read_bytes()]
    require(len(files) == 219 and not delta, 'all 219 generated assets retain exact baseline bytes', delta)
    for path in ('src/hardware.asm', 'src/trace.asm', 'src/knockdown.h', 'src/super_moves.h', 'src/version.h'):
        require(git(path) == (ROOT / path).read_bytes(), path + ' remains byte-identical')
    sections = []
    for name, address in now.items():
        if not name.startswith('SECTIONSTART_') or address < 0x800000:
            continue
        end = now.get(name.replace('SECTIONSTART_', 'SECTIONEND_'))
        if end is not None and end > address:
            sections.append([address, end, name])
    require(all(a >> 16 == (b - 1) >> 16 and b - a <= 32768 for a, b, _ in sections), 'all linked native sections fit 32 KiB LoROM banks')
    require(len(ROM.read_bytes()) == 4194304 and ROM.read_bytes()[0x7fd5] == 0x30, 'native 4 MiB FastROM LoROM cartridge')
    return {'prior_ram_labels': len(ram), 'moved': moved, 'added': added, 'generated_count': len(files), 'generated_delta': delta, 'sections': len(sections)}


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
        require(all(a[0][i] == b[0][i] for i in (2, 3, 4, 5, 6, 7, 9, 11, 12, 15)) and a[3:] == b[3:],
                'jump velocities/gravity, damage, reach, throws and family preserved', fighter)
        require(all(b[0][i] == round(a[0][i] * .82) for i in (0, 1)), 'movement speed is rounded to 82 percent', fighter)
        require(b[1] == [v + (3 if i in (2, 4, 5) else 0) for i, v in enumerate(a[1])] and
                b[2] == [v + (4 if i in (2, 4, 5) else 0) for i, v in enumerate(a[2])],
                'ground heavy timing changes are exact and fast light timing preserved', fighter)
        require(b[0][8] == a[0][8] + 3 and b[0][10] == a[0][10] + 5,
                'ordinary special gains three startup and five recovery ticks', fighter)
        row = {'fighter': fighter, 'walk_12_4': [a[0][0], b[0][0]], 'retreat_12_4': [a[0][1], b[0][1]]}
        if a[0][7] in (0, 2):
            old_range, new_range = a[0][13] * a[0][14], b[0][13] * b[0][14]
            require(abs(old_range - new_range) <= b[0][13] and b[0][13] == round(a[0][13] * .82),
                    'projectile lifetime preserves nominal travel within one slower step', [fighter, old_range, new_range])
            row['projectile'] = {'speed_12_4': [a[0][13], b[0][13]], 'life_ticks': [a[0][14], b[0][14]],
                                 'nominal_range_12_4': [old_range, new_range]}
        else:
            require(a[0][13:15] == b[0][13:15], 'direct special speed/life preserved', fighter)
        result.append(row)
    symbols = balance.symbols(SYM)
    address = symbols['hitStunByDamage']
    offset = ((address >> 16) & 127) * 32768 + (address & 32767)
    table = ROM.read_bytes()[offset:offset + 256]
    require(table == bytes(12 + damage // 3 for damage in range(256)),
            'all 256 compiled 65816 applyHitReaction damage/stun entries remain exact')
    return result


def main():
    global ROM, SYM
    p = argparse.ArgumentParser()
    p.add_argument('--sample', choices=('before', 'after'))
    p.add_argument('--fighters', default=','.join(map(str, range(12))))
    p.add_argument('--report', default='docs/combat-24-pacing-report.json')
    p.add_argument('--baseline', action='store_true')
    args = p.parse_args()
    if args.baseline:
        ROM, SYM = ROOT / 'build/pacing-baseline.sfc', ROOT / 'build/pacing-baseline.sym'
    report = {'status': 'failed', 'scope': 'isolated-pacing-recoil', 'combined_pass_claimed': False,
              'rom_path': str(ROM), 'rom_sha256': sha(ROM.read_bytes()), 'symbols_sha256': sha(SYM.read_bytes()),
              'base_commit': BASE, 'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
              'command': subprocess.list2cmdline([sys.executable, *sys.argv]),
              'host_contract': {**host_contract(), 'platform': platform.platform(), 'memory_writes': False, 'save_states': False},
              'harness_sha256': sha(Path(__file__).read_bytes()), 'checks': CHECKS, 'metrics': METRICS, 'failure_arrays': FAILURES, 'roster': []}
    start = time.monotonic()
    try:
        core = sha((ROOT / '.tools/core/snes9x_libretro.dll').read_bytes())
        require(core == EXPECTED_NATIVE_CORE['dll_sha256'], 'pinned native Snes9x core', core)
        report['core_sha256'] = core
        if args.sample:
            report['damian'] = damian_sample(args.sample)
        else:
            report['preservation'] = preservation()
            report['profiles'] = profile_audit()
            for fighter in map(int, args.fighters.split(',')):
                for port in (0, 1):
                    row = {'fighter': fighter, 'port': port + 1}
                    report['roster'].append(row)
                    row['motion'] = motion(fighter, port)
                    row['wave'] = wave(fighter, port)
                    row['special_timing'] = special_timing(fighter, port)
                    row['normals'] = balance.whiffs_and_ranges(fighter, port, balance.profiles()[fighter])
                    row['confirms'] = balance.confirms_and_low(fighter, port)
                    row['blocks'] = balance.block_and_punish(fighter, port)
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
        report['status'] = 'passed'
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        report['source_sha256'] = {path: sha((ROOT / path).read_bytes()) for path in
                                   ('src/game.c', 'src/characters.h', 'src/cpu_personality.h', 'tools/test_combat_24_pacing.py')}
        if (ROOT / 'src/pacing_recoil.h').exists():
            report['source_sha256']['src/pacing_recoil.h'] = sha((ROOT / 'src/pacing_recoil.h').read_bytes())
        report['dependency_sha256'] = {path: sha((ROOT / path).read_bytes()) for path in
                ('tools/test_characters.py', 'tools/test_inputs.py', 'tools/emulator.py', 'tools/run_background.py',
                 'tools/test_expansion_03_normal_balance.py', 'tools/test_expansion_06_cpu_personality.py',
                 'tools/test_expansion_07_supers.py', 'src/hardware.asm', 'src/trace.asm')}
        report['super_metrics'] = supers.timing
        report['captures'] = [{'path': p.relative_to(ROOT).as_posix(), 'sha256': sha(p.read_bytes())}
                              for p in sorted(OUT.glob('*'))]
        report['elapsed_seconds'] = round(time.monotonic() - start, 3)
        report['passed'] = sum(c['executions'] for c in CHECKS if c['passed'])
        path = ROOT / args.report
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
        print(json.dumps({k: report.get(k) for k in ('status', 'passed', 'rom_sha256', 'elapsed_seconds', 'error')}))


if __name__ == '__main__':
    main()
