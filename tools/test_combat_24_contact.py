"""Focused all-six-feature v0.24 contact proof, using real silent controllers.

Partial --fighters runs are build-only diagnostics. A full-roster focused run
still does not certify the release or replace the parent's frozen-ROM gates.
Geometry is checked against current native art, never regenerated on disk here.
"""
from __future__ import annotations
import argparse
from collections import deque
import ctypes as C
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from contact_geometry import generate, world, overlap, overlays, sha
from test_endurance import LongRunHost, EnduranceRun, boot, core_identity
from test_champion import host_contract
from PIL import Image, ImageDraw

checks = []
native = []
DATA = None
SYMS = {}
FRAME_OWNERS = {
    'attack-v1': {5, 6, 7, 8, 9, 10, 12, 13, 15, *range(32, 46), 47},
    'jump-v1': {29, 30, 31, *range(49, 56)},
    'super-v1': {1, 2, 4},
}


def dependency_hashes():
    # Include the transitive helper inventory conservatively. Other workers
    # may edit test_rom/test_inputs during diagnostics; record both snapshots.
    paths = list((ROOT/'src').rglob('*')) + list((ROOT/'tools').glob('*.py'))
    paths += [ROOT/p for p in ('dist/abaqus-after-hours.sfc', 'dist/abaqus-after-hours.sym',
                              'dist/manifest.json', 'build/contact_geometry_data.h')]
    return {p.relative_to(ROOT).as_posix(): sha(p.read_bytes())
            for p in sorted(paths) if p.is_file()}


def check(ok, label, detail=None):
    checks.append({'passed': bool(ok), 'check': label, 'detail': detail})
    if not ok:
        raise AssertionError((label, detail))


def signed(v):
    return v - 65536 if v & 32768 else v


def sym(raw):
    return {n: int(a, 16) for a, n in re.findall(r'^([0-9a-fA-F]{8}) (\S+)$', raw, re.M)}


def read(host, name, count):
    return C.string_at(host.ram + (SYMS[name] & 0x1ffff), count)


class Rig:
    def __init__(self, fighter, port=0, case='contact'):
        self.fighter, self.port = fighter, port
        self.a, self.d = str(port+1), str(2-port)
        self.host = LongRunHost(video_interval=30)
        boot(self.host, 1, fighter, fighter, fighter % 3)
        self.runner = EnduranceRun(1, 1, coverage_required=False)
        self.started = time.monotonic()
        self.tag = f'{fighter:02d}/P{self.a}/{case}'
        self.old_vram = self.vram()
        self.transfers = 0
        self.max_changed_bytes = 0
        self.trajectory = hashlib.sha256()
        self.controller_runs = []
        self.history = deque(maxlen=16)
        self.first_native_failure = None
        self.step()

    def state(self):
        s = self.host.state()
        raw = read(self.host, 'fighters', 128)
        for p in (0, 1):
            f = raw[p*64:(p+1)*64]
            for name, offset in (('tick', 17), ('startup', 24), ('duck', 21), ('end', 62), ('active_end', 63)):
                s[f'{name}{p+1}'] = f[offset]
        for name in ('superActive', 'superPhase', 'superContactEnd'):
            s[name] = list(read(self.host, name, 2))
        s['recoil_latches'] = read(self.host, 'rearKickRecoil', 1)[0]
        s['native_frame'] = int.from_bytes(read(self.host, 'frame', 2), 'little')
        return s

    def vram(self):
        ptr = self.host.core.retro_get_memory_data(3)
        return C.string_at(ptr+0xc000, 0x2800)

    def step(self, attack=(), defend=(), physical=None):
        self.last_before = self.state()
        keys = [list(attack), list(defend)] if not self.port else [list(defend), list(attack)]
        if physical is not None:
            keys = [list(physical[0]), list(physical[1])]
        self.last_keys = keys
        if self.controller_runs and self.controller_runs[-1]['keys'] == keys:
            self.controller_runs[-1]['callbacks'] += 1
        else:
            self.controller_runs.append({'at_callback': self.runner.total_frames+1, 'callbacks': 1, 'keys': keys})
        self.host.run(1, p1=keys[0], p2=keys[1])
        s = self.host.state()
        self.runner.inspect(self.host, s, keys[0], keys[1])
        current = self.vram()
        changed = [sum(x != y for x, y in zip(self.old_vram[p*5120:(p+1)*5120],
                                             current[p*5120:(p+1)*5120])) for p in (0, 1)]
        check_budget = sum(bool(v) for v in changed) <= 1 and sum(changed) <= 3840
        if not check_budget:
            check(False, 'At most one 3840-byte actor changes per vblank', {'case': self.tag, 'changed': changed})
        self.transfers += bool(sum(changed))
        self.max_changed_bytes = max(self.max_changed_bytes, sum(changed))
        self.old_vram = current
        detailed = self.state()
        self.history.append({'callback': self.runner.total_frames, 'keys': keys,
                             'before': self.last_before, 'after': detailed})
        if self.first_native_failure is None and any((self.runner.cadence_failures,
                                                      self.runner.native_timing_failures,
                                                      self.runner.ambient_failures,
                                                      self.runner.overflow_frames,
                                                      self.runner.spc_fifo_failures)):
            self.first_native_failure = list(self.history)
        self.trajectory.update(json.dumps({'keys': keys, 'state': detailed}, sort_keys=True,
                                          separators=(',', ':')).encode())
        return detailed

    def run(self, frames, attack=(), defend=()):
        s = self.state()
        for _ in range(frames):
            s = self.step(attack, defend)
        return s

    def direction(self, toward=True, defender=False):
        s = self.state()
        a, d = (self.d, self.a) if defender else (self.a, self.d)
        right = s[f'x{a}'] < s[f'x{d}']
        return 'right' if right == toward else 'left'

    def settle(self):
        for _ in range(180):
            s = self.state()
            if not any(s[f'{key}{p}'] for p in (1, 2) for key in ('action', 'hurt', 'down_state', 'y', 'landing', 'invuln')) and not s['hitstop']:
                return self.run(2)
            self.step()
        raise AssertionError(('did not settle', self.tag, self.state()))

    def position(self, gap):
        self.settle()
        for _ in range(300):
            s = self.state()
            actual = abs(s['x1']-s['x2']) / 16
            if abs(actual-gap) < 1.35:
                return self.run(2)
            self.step((self.direction(actual > gap),))
        raise AssertionError(('position', self.tag, gap, self.state()))

    def attack(self, keys, defender=(), limit=95):
        before = self.state()
        s = self.step(keys, defender)
        rows = [s]
        for _ in range(limit):
            if s[f'connected{self.a}']:
                return before, s, rows
            if len(rows) > 4 and not s[f'action{self.a}'] and not s[f'y{self.a}']:
                break
            s = self.step((), defender)
            rows.append(s)
        return before, s, rows

    def close(self):
        row = {'frames': self.runner.total_frames, 'live_frames': self.runner.live_frames,
               'cadence_failures': self.runner.cadence_failures, 'native_timing_failures': self.runner.native_timing_failures,
               'ambient_failures': self.runner.ambient_failures, 'ppu_overflow_frames': self.runner.overflow_frames,
               'spc_fifo_failures': self.runner.spc_fifo_failures}
        row.update(case=self.tag, actor_update_callbacks=self.transfers,
                   max_changed_actor_bytes=self.max_changed_bytes, audio_samples=self.host.audio_samples,
                   native_fps=self.host.video_fps, max_spc_backlog=self.runner.max_spc_backlog)
        row.update(stable_fight_lag_increments=self.runner.stable_fight_lag_increments,
                   max_oam_visible=self.runner.max_oam_visible,
                   max_oam_sprites=self.runner.max_oam_sprites,
                   native_screen_mismatch_samples=self.runner.native_screen_mismatch_samples)
        row.update(boot={'mode': 1, 'fighter1': self.fighter, 'fighter2': self.fighter,
                         'stage': self.fighter % 3}, controller_runs=self.controller_runs,
                   first_native_failure=self.first_native_failure)
        row['trajectory_sha256'] = self.trajectory.hexdigest()
        native.append(row)
        pending_error = sys.exc_info()[1]
        try:
            self.runner.result(self.host, time.monotonic()-self.started)
        except Exception as error:
            row['native_budget_error'] = repr(error)
            if pending_error is None:
                raise
        finally:
            self.host.close()
        if pending_error is not None:
            row['case_error'] = repr(pending_error)
            return
        check(not any(row[k] for k in ('cadence_failures', 'native_timing_failures', 'ambient_failures',
                                      'ppu_overflow_frames', 'spc_fifo_failures')), 'Strict native budgets', row['case'])


def active_frame(s, p):
    """Independent audit of the current native ACTIVE selectors."""
    if s['superActive'][int(p)-1]:
        return 2
    action = s[f'action{p}']
    if s[f'air_action{p}']:
        return 50 if action <= 3 else 53
    if action == 1:
        return 5
    if action <= 3:
        return 6
    if action <= 6:
        return 8 if s[f'duck{p}'] else 7
    if action == 8:
        return 13
    if action == 9:
        return 57
    return {1: 15, 3: 13}.get(s[f'family{p}'], 12)


def collision_snapshot(r, previous, current, frame, rear=False):
    """Undo only the documented post-contact writes; never expand geometry.

    Collision uses the defender's pre-animation body selection. Immediate
    recoil changes x after collision; knockdown can then change y/facing.
    """
    d, a = r.d, r.a
    latch = (current['recoil_latches'] >> ((int(d)-1)*4)) & 15
    check((latch & 3) in (1, 2), 'Real contact latches a geometric recoil side', [r.tag, latch])
    direction = 1 if (latch & 3) == 2 else -1
    impulse = 16 if current[f'guard{d}'] else (64 if latch & 4 else 32)
    dx = current[f'x{d}'] - direction * impulse
    dy = signed(current[f'y{d}'])
    if current[f'down_state{d}'] and not previous[f'down_state{d}'] and dy == -1:
        dy = 0
    clamp_reconstructed = current[f'x{d}'] in (24*16, 232*16)
    if clamp_reconstructed:
        # A clamped post-hit coordinate loses part of the impulse. These
        # fixtures have an unhurt grounded defender: recover its actual pad
        # movement from the previous callback, then apply the ordinary clamp.
        check(not any(previous[f'{key}{d}'] for key in ('action', 'hurt', 'y', 'down_state')),
              'Clamped reconstruction has a neutral grounded defender', r.tag)
        keys = r.last_keys[int(d)-1]
        dx = previous[f'x{d}']
        face = int(dx < previous[f'x{a}'])
        if 'down' not in keys:
            forward, back = ('right', 'left') if face else ('left', 'right')
            if forward in keys and back not in keys:
                dx += (1 if face else -1)*previous[f'speed{d}']
            elif back in keys and forward not in keys:
                dx -= (1 if face else -1)*previous[f'back_speed{d}']
        dx = min(232*16, max(24*16, dx))
        # Stay outside the separation ambiguity; never guess a wider box.
        check(abs(dx-current[f'x{a}']) >= 22*16+12 or
              abs(dy-signed(current[f'y{a}'])) >= 50*16,
              'Clamped collision reconstruction excludes body-separation ambiguity', [r.tag, previous, current])
    body_frame = previous[f'anim_frame{d}']
    if not previous[f'hurt{d}']:
        if previous[f'action{d}'] and current[f'action{d}']:
            if current[f'startup{d}'] <= current[f'tick{d}'] < current[f'active_end{d}']:
                body_frame = active_frame(current, d)
        elif current[f'duck{d}']:
            body_frame = 3
    ax, ay = current[f'x{a}'], signed(current[f'y{a}'])
    strike = world(DATA['poses'][r.fighter][frame][3 if rear else 2], ax, ay, current[f'face{a}'])
    hurt = [world(rect, dx, dy, previous[f'face{d}']) for rect in DATA['poses'][r.fighter][body_frame][:2]]
    check(any(overlap(strike, rect) for rect in hurt), 'Real native contact overlaps its evaluated pose bands',
          {'case': r.tag, 'frame': frame, 'body_frame': body_frame, 'strike': strike, 'hurt': hurt,
           'impulse_12_4': impulse, 'latch': latch})
    side = dx-ax
    check(not side or direction == (1 if side > 0 else -1),
          'Recoil follows contact side, including locked-facing cross-ups', [r.tag, side, latch])
    return {'attack_frame': frame, 'body_frame': body_frame, 'strike_12_4': strike,
            'hurt_12_4': hurt, 'recoil_impulse_12_4': impulse, 'recoil_latch': latch,
            'collision_xy_12_4': [[ax, ay], [dx, dy]], 'clamp_reconstructed': clamp_reconstructed}


def cutoff(fighter, frame, defender_frames=(16, 17, 18, 19)):
    strike = world(DATA['poses'][fighter][frame][2])
    limits = []
    for n in defender_frames:
        for rect in DATA['poses'][fighter][n][:2]:
            body = world(rect, face=0)
            if strike[1] < body[3] and strike[3] > body[1]:
                limits.append((strike[2]-body[0])/16)
    check(bool(limits), 'Visible attack has a plausible body band', [fighter, frame])
    return min(limits), max(limits)


def ordinary(fighter, port):
    r = Rig(fighter, port, 'ordinary')
    cases = []
    try:
        for keys, frame, label in ((('y',), 5, 'jab'), (('x',), 6, 'strong-punch'),
                                   (('b',), 7, 'kick'), (('a',), 7, 'strong-kick'),
                                   (('down', 'b'), 8, 'low')):
            lo, hi = cutoff(fighter, frame)
            s = r.position(hi+3)
            hp = s[f'hp{r.d}']
            before, after, rows = r.attack(keys)
            check(after[f'hp{r.d}'] == hp and not any(x[f'connected{r.a}'] for x in rows),
                  'Pixels separated beyond distal boundary do not hit', [r.tag, label, hi, abs(before['x1']-before['x2'])/16])
            r.position(max(25, lo-3))
            before, after, rows = r.attack(keys)
            check(after[f'connected{r.a}'] == 2 and after[f'hp{r.d}'] < before[f'hp{r.d}'],
                  'Visible distal overlap causes real damage', [r.tag, label, lo, after])
            check(after[f'tick{r.a}'] >= after[f'startup{r.a}'] and after[f'tick{r.a}'] < after[f'active_end{r.a}'],
                  'Contact occurs only in the active phase', [r.tag, label])
            check(after[f'anim_frame{r.a}'] == frame, 'Contact selector matches native active animation frame', [r.tag, label, frame])
            collision = collision_snapshot(r, r.last_before, after, frame)
            check(collision['recoil_impulse_12_4'] == (32 if label in ('jab', 'kick', 'low') else 64),
                  'Ordinary light/strong contact uses its exact immediate recoil', [r.tag, label, collision])
            cases.append({'move': label, 'idle_band_boundary_range_px': [lo, hi],
                          'inside_gap_12_4': abs(before['x1']-before['x2']),
                          'contact_tick': after[f'tick{r.a}'], 'damage': before[f'hp{r.d}']-after[f'hp{r.d}'],
                          'collision': collision})
        # Remote heavy/uppercut attempts must not connect through blank space.
        r.position(100)
        hp = r.state()[f'hp{r.d}']
        for keys in (('x',), ('a',), ('down', 'a'), ('down', 'x')):
            r.settle()
            _, after, rows = r.attack(keys)
            check(after[f'hp{r.d}'] == hp and not any(x[f'connected{r.a}'] for x in rows),
                  'No phantom remote strike', [r.tag, keys])
        r.position(26)
        # Crouch high/low guard must be classified by the unchanged guard rule.
        guard = ('down', r.direction(False, True))
        _, after, _ = r.attack(('down', 'b'), guard)
        check(after[f'connected{r.a}'] == 1 and after[f'guard{r.d}'], 'Low contact remains crouch-blockable', r.tag)
        guard_collision = collision_snapshot(r, r.last_before, after, 8)
        check(guard_collision['recoil_impulse_12_4'] == 16, 'Guard contact uses exact immediate recoil', r.tag)
        r.settle()
        r.position(26)
        _, after, _ = r.attack(('down', 'b'), (r.direction(False, True),))
        check(after[f'connected{r.a}'] == 2 and not after[f'guard{r.d}'], 'Standing guard does not block a visible low strike', [r.tag, after])
        return {'fighter': fighter, 'port': port, 'cases': cases, 'guard_collision': guard_collision}
    finally:
        r.close()


def airfront(fighter, port):
    r = Rig(fighter, port, 'airfront')
    result = []
    try:
        for key in ('y', 'a'):
            r.position(30)
            before = r.state()
            s = r.step(('up',))
            previous_y = 0
            sent = False
            for _ in range(90):
                y = signed(s[f'y{r.a}'])
                descending = y > previous_y
                keys = ()
                if y < 0 and descending and y >= (-38 if key == 'y' else -48)*16 and not sent:
                    keys = (key,)
                    sent = True
                previous_y = y
                s = r.step(keys)
                if sent and s[f'connected{r.a}']:
                    break
                if sent and not s[f'y{r.a}'] and not s[f'action{r.a}']:
                    break
            check(sent and s[f'connected{r.a}'] == 2 and signed(s[f'y{r.a}']) < 0,
                  'Descending visible air attack connects in front', [r.tag, key, s])
            frame = 50 if key == 'y' else 53
            check(s[f'anim_frame{r.a}'] == frame, 'Air contact uses current active pose', [r.tag, key, frame])
            collision = collision_snapshot(r, r.last_before, s, frame)
            result.append({'key': key, 'contact': s, 'collision': collision})
            r.settle()
        r.position(29)
        before = r.state()
        s = r.step((), ('up',))
        for _ in range(25):
            if signed(s[f'y{r.d}']) < -26*16:
                break
            s = r.step()
        check(signed(s[f'y{r.d}']) < -26*16, 'Jump fixture lifts the entire hurt region', r.tag)
        before, after, rows = r.attack(('down', 'b'))
        check(after[f'hp{r.d}'] == before[f'hp{r.d}'] and not any(x[f'connected{r.a}'] for x in rows),
              'Low foot passes beneath a jumping body without phantom contact', [r.tag, rows])
        return {'fighter': fighter, 'port': port, 'cases': result, 'jump_over_low': True}
    finally:
        r.close()


def crossups(fighter, port):
    r = Rig(fighter, port, 'crossups')
    result = []
    try:
        for key in ('a', 'x'):
            r.position(24)
            before = r.state()
            original = before[f'face{r.a}']
            forward = r.direction()
            sign = 1 if original else -1
            s = r.step(('up', forward), (r.direction(True, True),))
            sent = False
            contact = None
            for _ in range(90):
                crossed = (s[f'x{r.a}']-s[f'x{r.d}'])*sign > 0
                keys = ()
                if crossed and signed(s[f'y{r.a}']) >= -48*16 and not sent:
                    keys = (key,)
                    sent = True
                s = r.step(keys, (r.direction(True, True),))
                if sent and s[f'connected{r.a}']:
                    contact = s
                    break
                if sent and not s[f'action{r.a}'] and not s[f'y{r.a}']:
                    break
            if key == 'a':
                check(contact is not None and signed(s[f'y{r.a}']) < 0 and s[f'face{r.a}'] == original,
                      'Air A connects behind locked facing', [r.tag, s])
                collision = collision_snapshot(r, r.last_before, s, 53, rear=True)
                (ax, _), (dx, _) = collision['collision_xy_12_4']
                check((ax-dx)*sign > 0 and abs(ax-dx) <= 26*16,
                      'Pre-contact cross-up stays inside original 16px plus 10px body cap', [r.tag, collision])
                check(not s[f'down_state{r.d}'], 'Cross-up does not invent knockdown', r.tag)
            else:
                check(sent and contact is None and s[f'hp{r.d}'] == before[f'hp{r.d}'],
                      'Air X cannot hit behind locked facing', r.tag)
            result.append({'key': key, 'sent': sent, 'contact': contact,
                           'collision': collision if key == 'a' else None})
            r.settle()
        return {'fighter': fighter, 'port': port, 'cases': result}
    finally:
        r.close()


def trades_throws(fighter):
    r = Rig(fighter, case='trades-throws')
    try:
        check(all(0 < r.state()[f'throw_range{p}'] <= 96 for p in (1, 2)),
              'Native throw ranges fit the conservative canvas rejection', fighter)
        r.position(29)
        before = r.state()
        s = r.step(physical=(('y',), ('y',)))
        for _ in range(25):
            if s['hp1'] < before['hp1'] or s['hp2'] < before['hp2']:
                break
            s = r.step()
        check(s['hp1'] == s['hp2'] < before['hp1'] and s['connected1'] == s['connected2'] == 2,
              'Both mirrored candidates resolve as one symmetric trade', [fighter, s])
        trade = s
        r.settle()
        r.position(min(r.state()['throw_range1'], r.state()['throw_range2'])-2)
        before = r.state()
        s = r.step(physical=((r.direction(), 'x'), (r.direction(True, True), 'x')))
        r.run(28)
        s = r.state()
        check(s['hp1'] == before['hp1'] and s['hp2'] == before['hp2'] and not s['down_state1'] and not s['down_state2'],
              'Mutual throws tech without one-sided damage', fighter)
        throws = []
        for port in (0, 1):
            r.port, r.a, r.d = port, str(port+1), str(2-port)
            r.position(r.state()[f'throw_range{r.a}']-2)
            before, s, _ = r.attack((r.direction(), 'x'), limit=5)
            check(s[f'action{r.a}'] == 9 or s[f'down_state{r.d}'], 'Strict close throw is accepted on each port', [fighter, port, s])
            r.run(70)
            check(r.state()[f'hp{r.d}'] < before[f'hp{r.d}'], 'Throw applies delayed impact damage', [fighter, port])
            throws.append({'port': port, 'initial_gap': abs(before['x1']-before['x2']), 'range': before[f'throw_range{r.a}']})
            r.settle()
            r.position(r.state()[f'throw_range{r.a}']+4)
            _, s, _ = r.attack((r.direction(), 'x'), limit=1)
            check(s[f'action{r.a}'] != 9, 'Outside strict range falls back to ordinary strong punch', [fighter, port])
            r.settle()
        return {'fighter': fighter, 'trade': trade, 'throws': throws}
    finally:
        r.close()


def specials(fighter, port):
    r = Rig(fighter, port, 'specials-supers')
    try:
        r.position(44 if r.state()[f'family{r.a}'] == 1 else 27)
        while r.state()[f'energy{r.a}'] < 32:
            r.step()
        before, s, rows = r.attack(('down', 'y'), limit=140)
        if s[f'hp{r.d}'] == before[f'hp{r.d}']:
            for _ in range(120):
                s = r.step()
                if s[f'hp{r.d}'] < before[f'hp{r.d}']:
                    break
        check(s[f'hp{r.d}'] < before[f'hp{r.d}'], 'Visible ordinary special connects on each port', [fighter, port, s])
        ordinary_damage = before[f'hp{r.d}'] - s[f'hp{r.d}']
        r.settle()
        r.position(40 if s[f'family{r.a}'] == 1 else 27)
        while r.state()[f'energy{r.a}'] < 96:
            r.step()
        before, s, rows = r.attack(('y', 'b'), limit=140)
        for _ in range(140):
            if s[f'hp{r.d}'] < before[f'hp{r.d}']:
                break
            s = r.step()
        check(any(x['superActive'][port] for x in rows) and s[f'hp{r.d}'] < before[f'hp{r.d}'],
              'Direct/volley super connects through the same geometry path', [fighter, port, s])
        return {'fighter': fighter, 'port': port, 'family': before[f'family{r.a}'], 'ordinary_damage': ordinary_damage,
                'observed_super_damage': before[f'hp{r.d}']-s[f'hp{r.d}']}
    finally:
        r.close()


def static_contract():
    old = sym(subprocess.check_output(['git', 'show', '3f51120:dist/abaqus-after-hours.sym'], cwd=ROOT).decode())
    ram = {n: a for n, a in old.items() if a < 0x2000 or 0x7e0000 <= a < 0x800000}
    moved = {n: [a, SYMS.get(n)] for n, a in ram.items() if SYMS.get(n) != a}
    check(not moved, 'Every prior RAM/direct-page symbol retains its address', moved)
    added = {n: a for n, a in SYMS.items() if n not in old and (a < 0x2000 or 0x7e0000 <= a < 0x800000)}
    check(not added, 'Contact geometry adds no mutable RAM symbols', added)
    rom = (ROOT/'dist/abaqus-after-hours.sfc').read_bytes()
    def rom_data(name, size):
        address = SYMS[name]
        check(address >> 16 not in (0x7e, 0x7f) and (address & 65535) + size <= 65536,
              'Read-only geometry fits one LoROM bank', [name, hex(address), size])
        offset = ((address >> 16) & 127) * 32768 + (address & 32767)
        return rom[offset:offset+size]
    table = bytes(v for poses in DATA['poses'] for pose in poses for rect in pose for v in rect)
    check(rom_data('contactPoses', len(table)) == table, 'Exact cartridge contains refreshed raster geometry')
    check(rom_data('contactGeometryDigest', 32).hex() == DATA['digest'], 'Exact cartridge identifies its geometry inputs')
    from expansion_contracts import combined_contract
    composition = combined_contract(ROOT)
    from v024_contracts import active_scopes
    check(active_scopes(ROOT) == FRAME_OWNERS, 'All three disjoint art scopes are integrated')
    check((ROOT/'assets/generated/stage-depth.json').is_file(), 'Combined scope includes rebuilt stage depth')
    changed = composition['assets']['changed_generated']
    for poses in DATA['poses']:
        for pose in poses:
            for rect in pose[:3]:
                check(0 < rect[0] < rect[2] < 96 and 0 < rect[1] < rect[3] <= 78,
                      'Derived rectangle has bounded positive area')
                a = world(rect)
                b = world(rect, face=0)
                check(a[0] == -b[2] and a[2] == -b[0], 'Mirror transform is exact about actor center')
                check(not overlap(a, [a[2], a[1], a[2]+16, a[3]]) and
                      overlap(a, [a[2]-1, a[1], a[2]+16, a[3]]), 'Touching edges miss; one fixed-point unit overlaps')
    return {'prior_ram_labels': len(ram), 'added_ram': added, 'changed_generated': changed,
            'rom_geometry_bytes': len(table)+32, 'geometry_address': hex(SYMS['contactPoses']),
            'composition': composition}


def capture_comparison(directory):
    from test_characters import boot as image_boot, state
    directory.mkdir(parents=True, exist_ok=True)
    baseline = ROOT/'build/contact-baseline-v0231.sfc'
    baseline.write_bytes(subprocess.check_output(['git', 'show', 'f75005d:dist/abaqus-after-hours.sfc'], cwd=ROOT))
    paths = []
    for label in ('jab-visible-tip', 'air-crossup'):
        runs = []
        for rom in (baseline, ROOT/'dist/abaqus-after-hours.sfc'):
            e = image_boot(1, 0, fighter2=0, rom=rom)
            try:
                for _ in range(180):
                    s = state(e)
                    if abs(s['x1']-s['x2']) <= (44 if label == 'jab-visible-tip' else 24)*16:
                        break
                    e.run(1, p1=('right',))
                e.run(3)
                frames = []
                if label == 'jab-visible-tip':
                    e.run(1, p1=('y',))
                    for _ in range(48):
                        frames.append(e.frame.copy())
                        e.run(1)
                else:
                    e.run(1, p1=('up', 'right'))
                    sent = False
                    for _ in range(80):
                        s = state(e)
                        keys = ()
                        if s['x1'] > s['x2'] and not sent:
                            keys = ('a',)
                            sent = True
                        frames.append(e.frame.copy())
                        e.run(1, p1=keys)
                runs.append(frames)
            finally:
                e.close()
        pairs = []
        for left, right in zip(*runs):
            im = Image.new('RGB', (512, 240), (25, 30, 42))
            im.paste(left, (0, 16));im.paste(right, (256, 16))
            d = ImageDraw.Draw(im)
            d.text((4, 2), 'historical v0.23.1', fill='white')
            d.text((260, 2), 'combined v0.24', fill='white')
            pairs.append(im)
        path = directory/(label+'-before-after.gif')
        pairs[0].save(path, save_all=True, append_images=pairs[1:], loop=0, duration=[20, 20, 10]*27, optimize=False)
        paths.append({'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path.read_bytes()),
                      'baseline_rom_sha256': sha(baseline.read_bytes()),
                      'candidate_rom_sha256': sha((ROOT/'dist/abaqus-after-hours.sfc').read_bytes()),
                      'playback': 'GIF durations approximate native 60.0988 Hz; native ROM is authoritative'})
    return paths


def main():
    global DATA, SYMS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fighters', type=int, nargs='+', default=list(range(12)))
    parser.add_argument('--report', type=Path, default=ROOT/'docs/combat-24-contact-report.json')
    parser.add_argument('--captures', action='store_true')
    args = parser.parse_args()
    if any(f not in range(12) for f in args.fighters) or len(set(args.fighters)) != len(args.fighters):
        parser.error('--fighters must contain unique IDs in 0..11')
    full_roster = set(args.fighters) == set(range(12))
    if not full_roster:
        if args.report == parser.get_default('report'):
            args.report = ROOT/'build/v024-contact-diagnostic.json'
        if not args.report.resolve().is_relative_to((ROOT/'build').resolve()):
            parser.error('partial --fighters reports must stay under build/')
    start = time.monotonic()
    dependencies = dependency_hashes()
    report = {'status': 'failed', 'scope': 'all-six-feature-combined-contact',
              'evidence_kind': 'full-roster-focused' if full_roster else 'bounded-diagnostic',
              'full_roster': full_roster, 'final_certification': False,
              'frozen_combined_rerun_required': True,
              'requested_fighters': args.fighters, 'required_fighters': list(range(12)), 'required_ports': [0, 1],
              'completed_fighters': [], 'rom_sha256': sha((ROOT/'dist/abaqus-after-hours.sfc').read_bytes()),
              'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
              'source_diff_sha256': sha(subprocess.check_output(['git', 'diff', 'HEAD', '--', 'src', 'tools'], cwd=ROOT)),
              'command': subprocess.list2cmdline([sys.executable, *sys.argv]), 'host': host_contract(),
              'dependencies_start': dependencies,
              'harness_sha256': sha(Path(__file__).read_bytes().replace(b'\r\n', b'\n')),
              'coverage_contract': {
                  'controller_only': True, 'memory_writes': False, 'savestates': False,
                  'native_checks': ['unit trace frame cadence', 'native screen and SDK vblank/lag counters',
                                    'OBJ scanlines and PPU overflow', 'one 3840-byte actor DMA per vblank',
                                    'resident SPC FIFO and captured PCM', 'native NTSC video callbacks'],
                  'geometry_checks': ['current encoded art/preview/manifest', 'half-open exact boundary math',
                                      'mirrored body bands', 'pre-contact recoil reconstruction',
                                      'ground light/strong/high/low', 'air front/rear cross-up',
                                      'simultaneous trades', 'strict throws', 'ordinary specials and supers'],
                  'frame_owners': {k: sorted(v) for k, v in FRAME_OWNERS.items()},
                  'unchanged_recoil_impulses_12_4': {'light': 32, 'strong': 64, 'guard': 16},
              },
              'ordinary': [], 'airfront': [], 'crossups': [], 'trades_throws': [], 'specials_supers': [], 'native': native}
    try:
        report['core'] = core_identity()
        header, DATA = generate()
        report['geometry_digest'] = DATA['digest']
        report['geometry_dependencies'] = DATA['dependencies']
        check((ROOT/'build/contact_geometry_data.h').read_bytes() == header, 'Geometry header is current')
        SYMS = sym((ROOT/'dist/abaqus-after-hours.sym').read_text())
        report['preservation'] = static_contract()
        for fighter in args.fighters:
            for port in (0, 1):
                report['ordinary'].append(ordinary(fighter, port))
                report['airfront'].append(airfront(fighter, port))
                report['crossups'].append(crossups(fighter, port))
                report['specials_supers'].append(specials(fighter, port))
            report['trades_throws'].append(trades_throws(fighter))
            report['completed_fighters'].append(fighter)
            print(json.dumps({'completed_fighter': fighter, 'checks': len(checks)}), flush=True)
        if args.captures:
            directory = ROOT/('docs/screenshots/combat-24-contact' if full_roster else 'build/v024-contact-captures')
            overlays(ROOT, DATA, directory)
            report['captures'] = capture_comparison(directory)
        report['status'] = 'passed' if full_roster else 'diagnostic-passed'
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        report['dependencies_end'] = dependency_hashes()
        report['changed_dependencies'] = {p: [dependencies.get(p), report['dependencies_end'].get(p)]
                                          for p in dependencies.keys() | report['dependencies_end'].keys()
                                          if dependencies.get(p) != report['dependencies_end'].get(p)}
        report['dependencies_stable'] = not report['changed_dependencies']
        if full_roster and report['changed_dependencies'] and report['status'] == 'passed':
            report['status'] = 'stale-dependencies'
        report['elapsed_seconds'] = round(time.monotonic()-start, 3)
        report['checks'] = checks
        report['passed_checks'] = sum(c['passed'] for c in checks)
        for field in ('cadence_failures', 'native_timing_failures', 'ambient_failures', 'ppu_overflow_frames', 'spc_fifo_failures'):
            report[field] = [dict(case=row['case'], failure=f) for row in native for f in row[field]]
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps({k: report[k] for k in ('status', 'rom_sha256', 'passed_checks', 'elapsed_seconds')}))
    if report['status'] not in ('passed', 'diagnostic-passed'):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
