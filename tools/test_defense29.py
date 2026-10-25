"""Controller-only defensive-option proof. No WRAM writes or save states.

Run with project Python through run_background.py, affinity mask 12.
--measure records the integration parent's actual throw/down clocks first.
"""
from __future__ import annotations

import argparse
import ctypes as C
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from PIL import Image
from emulator import Emulator
import test_characters as characters
import test_inputs as inputs
import test_compatibility as compatibility
import test_expansion_03_normal_balance as balance
import test_presentation as presentation
from release_evidence import EXPECTED_NATIVE_CORE
from test_champion import host_contract
from candidate_sources import snapshot

OUT = ROOT / 'build/defense29'
CHECKS = {}
HEALTH = {}
SYMS = {}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(ok, label, details=None):
    row = CHECKS.setdefault(label, {'check': label, 'passed': True, 'executions': 0})
    row['executions'] += 1
    if not ok:
        row.update(passed=False, details=details)
        raise AssertionError((label, details))


def symbols(path):
    return {name: int(address, 16) & 0x1ffff for address, name in re.findall(
        r'^([0-9A-Fa-f]{8}) (\S+)$', path.read_text(), re.M)}


def read(e, name, size=1):
    return int.from_bytes(C.string_at(e.ram + SYMS[name], size), 'little')


class Host:
    def __init__(self, core, rom=None):
        self.core_name = core
        if core == 'accuracy':
            prior = compatibility.ROM_PATH
            compatibility.ROM_PATH = Path(rom or ROOT / 'dist/abaqus-after-hours.sfc')
            try:
                self.host = compatibility.Probe()
            finally:
                compatibility.ROM_PATH = prior
        else:
            self.host = Emulator(rom, core_options=inputs.MENU_CORE_OPTIONS)
        self.ram, self.core = self.host.ram, self.host.core
        self.stream = []
        self.health = HEALTH.setdefault(core, {'callbacks': 0, 'max_spc_backlog': 0,
                                               'actor_page_changes': [0, 0], 'failures': []})

    @property
    def frame(self):
        frame = self.host.frame_image if self.core_name == 'accuracy' else self.host.frame
        return frame.resize((256, 224), Image.Resampling.NEAREST).convert('RGB')

    def state(self):
        return inputs.trace(self)

    def run(self, count=1, p1=(), p2=()):
        for _ in range(count):
            before = self.state()
            watch = (read(self, 'screen') == 3 and before['screen'] == 3 and not before['intro'])
            if watch:
                counters = [read(self, n, 2) for n in ('frame', 'snes_vblank_count', 'lag_frame_counter')]
                samples = self.host.audio_samples
                vram = self.core.retro_get_memory_data(3)
                pages = [C.string_at(vram + offset, 0x1400) for offset in (0xc000, 0xd400)]
            self.host.run(1, p1, p2)
            after = self.state()
            if watch and read(self, 'screen') == 3 and after['screen'] == 3 and not after['intro']:
                current = [read(self, n, 2) for n in ('frame', 'snes_vblank_count', 'lag_frame_counter')]
                delta = [(a - b) & 65535 for a, b in zip(current, counters)]
                event = {'core': self.core_name, 'before': counters, 'after': current,
                         'delta': delta, 'trace': [before['frame'], after['frame']]}
                if delta != [1, 1, 0] or (after['frame'] - before['frame']) & 65535 != 1:
                    self.health['failures'].append(event)
                require(delta == [1, 1, 0] and (after['frame'] - before['frame']) & 65535 == 1,
                        'strict native frame/vblank/SDK cadence', event)
                require(self.host.audio_samples > samples, 'silent PCM callbacks advance')
                stat = int.from_bytes(C.string_at(self.ram + 0x1ff00 + 228, 2), 'little')
                require(stat & 0xc0 == 0, 'native OBJ range/time limits', stat)
                backlog = (read(self, 'spc_fwrite') - read(self, 'spc_fread')) & 255
                self.health['max_spc_backlog'] = max(self.health['max_spc_backlog'], backlog)
                require(backlog <= 6, 'resident SPC FIFO bound', backlog)
                changed = [C.string_at(vram + offset, 0x1400) != old
                           for offset, old in zip((0xc000, 0xd400), pages)]
                require(sum(changed) <= 1, 'at most one actor VRAM page changes per vblank', changed)
                for port in range(2):
                    self.health['actor_page_changes'][port] += int(changed[port])
                self.health['callbacks'] += 1
            raw = C.string_at(self.ram + SYMS['fighters'], 128)
            private = C.string_at(self.ram + SYMS['v29DefenseState'], 16)
            wave_rng = C.string_at(self.ram + SYMS['waves'], 32) + C.string_at(self.ram + SYMS['randomseed'], 2)
            self.stream.append([list(p1), list(p2), after, raw.hex(), private.hex(), wave_rng.hex()])
        return self.state()

    def tap(self, key, port=0):
        self.run(3, **{'p1' if port == 0 else 'p2': [key]})
        return self.run(3)

    def close(self):
        self.host.close()


class Rig(balance.Rig):
    def __init__(self, fighter, port, core='snes9x', mode=1, rom=None, stage=None):
        self.port, self.fighter, self.core_name = port, fighter, core
        self.a, self.d = str(port + 1), str(2 - port)
        self.tag = f'{core} fighter{fighter:02} attacker P{self.a}'
        prior = characters.Emulator
        characters.Emulator = lambda rom=None: Host(core, rom)
        try:
            self.e = characters.boot(mode, fighter, fighter % 3 if stage is None else stage,
                                     fighter, rom=rom)
        finally:
            characters.Emulator = prior
        self.syms, self.base = SYMS, SYMS['fighters']
        if mode == 2:
            self.e.tap('start')
            self.e.tap('x')
            self.e.tap('start')
            require(read(self.e, 'trainingDummy') == 5 and not self.state()['paused'],
                    'Training enables the actual second controller')

    def step(self, attack=(), defend=()):
        self.e.run(1, **{f'p{self.a}': attack, f'p{self.d}': defend})
        return self.state()

    def reset(self):
        self.e.tap('select', 0)
        self.e.run(8)
        s = self.state()
        require(s['hp1'] == s['hp2'] == 128 and not s['down_state1'] and not s['down_state2'],
                'controller Training reset restores the round', self.tag)
        return s

    def grab(self, defender=()):
        self.approach_throw()
        return self.start_throw(defender)

    def approach_throw(self):
        self.settle()
        # A fast actor can skip a one-pixel target band near the 22px body
        # separation floor. Prove strict native range directly instead.
        reach = min(self.state()['throw_range1'], self.state()['throw_range2'])
        target = min(23, reach - .5)
        for _ in range(240):
            if self.gap() <= target:
                self.step()
                if self.gap() < reach:
                    return
            self.step((self.direction(),))
        raise AssertionError(('could not walk into strict native throw range', self.tag, reach, self.gap()))

    def start_throw(self, defender=()):
        s = self.step((self.direction(), 'x'), defender)
        if self.core_name == 'accuracy' and not s[f'action{self.a}']:
            s = self.step((self.direction(), 'x'), defender)
        require(s[f'action{self.a}'] == 9, 'toward plus X selects the original throw', [self.tag, s])
        for _ in range(30):
            if s[f'down_state{self.d}'] == 1:
                return s
            s = self.step((), defender)
        raise AssertionError(('grab did not connect', self.tag, s))

    def stream(self, label):
        raw = (json.dumps(self.e.stream, separators=(',', ':')) + '\n').encode()
        path = OUT / f'{self.core_name}-{self.fighter:02}-p{self.a}-{label}.json.gz'
        path.write_bytes(gzip.compress(raw, mtime=0))
        return {'callbacks': len(self.e.stream), 'unmasked_stream_sha256': sha(raw),
                'path': path.relative_to(ROOT).as_posix(), 'gzip_sha256': sha(path.read_bytes())}


def command(r):
    return (r.direction(True, True), 'x')


def tech_edge(r):
    keys = command(r)
    before = r.state()
    s = r.step((), keys)
    if r.core_name == 'accuracy' and s[f'down_state{r.d}'] == 1:
        s = r.step((), keys)
    return before, s


def wait_for(r, predicate, label, limit=180, attack=(), defend=()):
    s = r.state()
    for _ in range(limit):
        if predicate(s):
            return s
        s = r.step(attack, defend)
    raise AssertionError((label, r.tag, s))


def finish_stop(r, defend=()):
    return wait_for(r, lambda s: not s['hitstop'], 'hitstop finishes', defend=defend)


def timer(r):
    return C.string_at(r.e.ram + SYMS['v29DefenseState'], 16)[int(r.d) - 1]


def verify_tech(r, before, label, late=True, observe_tail=True):
    s = r.state()
    event = dict(s)
    require(s['hp1'] == before['hp1'] and s['hp2'] == before['hp2'],
            'earned tech deals no damage to either player', [r.tag, label, s])
    require(s['down_state1'] == s['down_state2'] == s['pending_throw_damage1'] ==
            s['pending_throw_damage2'] == s['y1'] == s['y2'] == 0 and
            s['throw_owner1'] == s['throw_owner2'] == s['throw_victim1'] == s['throw_victim2'] == 255,
            'earned tech atomically cancels both throw links and landing damage', [r.tag, label, s])
    require(s['guard1'] == s['guard2'] == s['connected1'] == s['connected2'] == 1 and
            s['hurt1'] == s['hurt2'] == 6 and s['hitstop'] == 3,
            'earned tech retains equal six-live-tick recovery and three-video-tick hitstop', [r.tag, label, s])
    if late:
        require(abs(s['x1'] - s['x2']) == 40 * 16 and
                all(24 * 16 <= s[f'x{p}'] <= 232 * 16 for p in (1, 2)),
                'late tech separates fairly by forty pixels inside both walls', [r.tag, label, s])
        require(s['face1'] == (s['x1'] < s['x2']) and s['face2'] == (s['x2'] < s['x1']),
                'late tech restores both geometric facings without crossing', [r.tag, label, s])
    require(read(r.e, 'impactBannerCounter') == 3, 'only earned tech requests the native THROW TECH cue')
    for _ in range(8):
        r.step()
    start = len(presentation.checks)
    presentation.verify_opaque_text_rows(r.e, [(9, 10, 'THROW TECH!')], r.tag + ' ' + label)
    require(all(row['passed'] for row in presentation.checks[start:]),
            'earned tech is readable in actual opaque native PPU glyphs', [r.tag, label])
    if r.fighter == 0 and label in ('tick-5', 'corner-right'):
        path = ROOT / f'docs/screenshots/defense29/{r.core_name}-p{r.a}-{label}.png'
        path.parent.mkdir(parents=True, exist_ok=True)
        r.e.frame.save(path)
    for _ in range(110 if observe_tail else 0):
        s = r.step()
        require(s['hp1'] == before['hp1'] and s['hp2'] == before['hp2'],
                'a successful tech can never apply delayed landing damage', [r.tag, label, s])
    return {'label': label, 'event': event}


def failed_escape(r, before, label, defend=()):
    s = wait_for(r, lambda s: s[f'down_state{r.d}'] == 3, 'unteched throw reaches floor', defend=defend)
    expected = before[f'pending_throw_damage{r.d}']
    require(s[f'hp{r.d}'] == before[f'hp{r.d}'] - expected and s[f'hp{r.a}'] == before[f'hp{r.a}'],
            'ineligible escapes retain the exact original delayed throw damage', [r.tag, label, expected, s])
    require(read(r.e, 'impactBannerCounter') != 3,
            'ineligible input cannot advertise THROW TECH', [r.tag, label, s])
    return {'label': label, 'damage': expected, 'landing': s}


def await_wake(r, close=False, defend=()):
    for _ in range(170):
        s = r.state()
        if s[f'down_state{r.d}'] == 5:
            return s
        keys = (r.direction(),) if close and r.gap() > 18 else ()
        r.step(keys, defend)
    raise AssertionError(('wake did not arrive', r.tag, r.state()))


def recovery(r, kind):
    r.reset()
    r.grab()
    s = await_wake(r, close=True)
    if kind in ('buffer-attack', 'buffer-jump'):
        key = 'y' if kind == 'buffer-attack' else 'up'
        s = r.step((), (key,))
        if r.core_name == 'accuracy' and not (s[f'wake_action{r.d}'] if key == 'y' else s[f'wake_jump{r.d}']):
            s = r.step((), (key,))
        require(s[f'wake_action{r.d}'] == 1 if key == 'y' else s[f'wake_jump{r.d}'] > 0,
                'fresh wake edge enters the established attack or jump buffer', [r.tag, kind, s])
        r.step()
    guard = (r.direction(False, True),) if kind == 'guard' else ()
    for _ in range(8):
        if s[f'down_state{r.d}'] == 0:
            break
        s = r.step((r.direction(),) if r.gap() > 18 else (), guard)
    require(s[f'down_state{r.d}'] == 0, 'wake reaches the original free transition')
    require(timer(r) == 10 and s[f'invuln{r.d}'] == 4,
            'recovery starts ten throw-protection ticks while retaining four invulnerability units', [r.tag, kind, s])
    if kind.startswith('buffer-'):
        s = r.step()
        require(s[f'action{r.d}'] == 1 if kind == 'buffer-attack' else s[f'y{r.d}'] != 0,
                'released buffered wake attack or jump executes on the first free control tick', [r.tag, kind, s])
        return {'kind': kind, 'event': s, 'throw_timer': timer(r)}
    if kind == 'protected-throw':
        r.step((r.direction(),))
        r.step((r.direction(),))
        s = r.step((r.direction(), 'x'))
        if r.core_name == 'accuracy' and not s[f'action{r.a}']:
            s = r.step((r.direction(), 'x'))
        require(s[f'action{r.a}'] == 9, 'wake pressure still uses the original throw command', [r.tag, s])
        s = wait_for(r, lambda s: s[f'tick{r.a}'] == 4, 'throw reaches active tick')
        require(s[f'invuln{r.d}'] == 0 and 0 < timer(r) <= 5 and
                abs(s['x1'] - s['x2']) < s[f'throw_range{r.a}'] * 16,
                'repeated grab overlaps a truly throwable target after general invulnerability expires', [r.tag, s, timer(r)])
        require(s[f'down_state{r.d}'] == 0 and s[f'connected{r.a}'] == 0,
                'short wake protection rejects only the repeated grab', [r.tag, s])
        event = s
        r.e.tap('start')
        frozen = timer(r)
        r.e.run(20)
        require(timer(r) == frozen and r.state()['paused'], 'pause freezes active throw-only wake protection')
        if r.fighter == 0:
            r.e.tap('select')
            r.e.run(8)
            presentation.verify_opaque_text_rows(r.e, [(20, 3, 'TECH: TOWARD + X ON GRAB'),
                                                       (23, 3, 'WAKE: BRIEF THROW PROTECTION')], r.tag + ' defense guide')
            path = ROOT / f'docs/screenshots/defense29/{r.core_name}-p{r.a}-guide.png'
            path.parent.mkdir(parents=True, exist_ok=True)
            r.e.frame.save(path)
        r.e.tap('start')
        r.settle()
        require(timer(r) == 0, 'throw protection expires after its bounded live ticks')
        next_grab = r.grab()
        require(next_grab[f'down_state{r.d}'] == 1,
                'ordinary throws work again after wake protection expires', [r.tag, next_grab])
        return {'kind': kind, 'event': event, 'next_grab': next_grab}
    hp = s[f'hp{r.d}']
    s = r.step(('y',), guard)
    if r.core_name == 'accuracy' and not s[f'action{r.a}']:
        s = r.step(('y',), guard)
    s = wait_for(r, lambda s: s[f'connected{r.a}'] != 0, 'ordinary wake strike contacts', limit=18, defend=guard)
    require(s[f'invuln{r.d}'] == 0 and timer(r) > 0,
            'ordinary wake strike contacts during the throw-only protection interval', [r.tag, kind, s, timer(r)])
    require(s[f'connected{r.a}'] == (1 if guard else 2) and
            (s[f'hp{r.d}'] == hp if guard else s[f'hp{r.d}'] < hp),
            'ordinary strike damage and held guard retain their established rules', [r.tag, kind, hp, s])
    return {'kind': kind, 'event': s, 'throw_timer': timer(r)}


def defense_case(core, fighter, port):
    r = Rig(fighter, port, core, mode=2)
    row = {'core': core, 'fighter': fighter, 'attacker_port': port, 'events': []}
    try:
        for tick in (1, 3, 5):
            r.reset()
            before = r.grab()
            finish_stop(r)
            # Accuracy's autojoy read can straddle the frontend callback.
            # Its selected interior case holds across both callbacks; exact
            # first/last-tick boundaries are asserted on expanded Snes9x.
            delivery_tick = min(tick, 4) if core == 'accuracy' else tick
            for _ in range(delivery_tick - 1):
                r.step()
            tech_edge(r)
            row['events'].append(verify_tech(r, before, f'tick-{delivery_tick}'))
        # A sixth-tick edge cannot rewind the launch or its landing damage.
        r.reset()
        before = r.grab()
        finish_stop(r)
        for _ in range(5):
            r.step()
        s = r.step((), command(r))
        require(s[f'down_state{r.d}'] == 2, 'sixth live-tick input is too late and preserves launch')
        row['events'].append(failed_escape(r, before, 'late'))
        for label, held in (('early-hitstop', False), ('held-hitstop', True), ('wrong-direction', False),
                            ('down-is-uppercut', False)):
            r.reset()
            before = r.grab()
            if label in ('early-hitstop', 'held-hitstop'):
                keys = command(r)
                frozen_tick = before[f'down_tick{r.d}']
                s = r.step((), keys)
                require(s[f'down_tick{r.d}'] == frozen_tick and s[f'down_state{r.d}'] == 1,
                        'hitstop freezes the escape clock and cannot resolve a tech', [r.tag, label, s])
                finish_stop(r, keys if held else ())
                for _ in range(6):
                    r.step((), keys if held else ())
            else:
                finish_stop(r)
                keys = (r.direction(False, True), 'x') if label == 'wrong-direction' else (*command(r), 'down')
                r.step((), keys)
                for _ in range(5):
                    r.step()
            row['events'].append(failed_escape(r, before, label, keys if held else ()))
        # Existing simultaneous throw resolution keeps its original outcome.
        r.reset()
        r.approach_throw()
        before = r.state()
        s = r.step((r.direction(), 'x'), command(r))
        if core == 'accuracy' and not s[f'action{r.a}']:
            s = r.step((r.direction(), 'x'), command(r))
        s = wait_for(r, lambda s: s['guard1'] and s['guard2'] and s['hurt1'] and s['hurt2'],
                     'mutual throws tech', limit=20)
        row['events'].append(verify_tech(r, before, 'simultaneous', late=False))
        # Held X from before the grab must not manufacture a fresh edge.
        r.reset()
        r.e.run(38, **{f'p{r.d}': ['x']})
        for _ in range(170):
            if r.gap() < min(r.state()['throw_range1'], r.state()['throw_range2']) - 2:
                break
            r.step((r.direction(),), ('x',))
        before = r.start_throw(('x',))
        keys = command(r)
        finish_stop(r, keys)
        for _ in range(6):
            r.step((), keys)
        row['events'].append(failed_escape(r, before, 'held-before-grab', keys))
        for kind in ('protected-throw', 'strike', 'guard', 'buffer-attack', 'buffer-jump'):
            row['events'].append(recovery(r, kind))
        for wall in ('left', 'right'):
            r.reset()
            r.e.run(280, p1=[wall], p2=[wall])
            r.settle()
            before = r.start_throw()
            require((min(before['x1'], before['x2']) <= 46 * 16 if wall == 'left' else
                     max(before['x1'], before['x2']) >= 210 * 16),
                    'corner fixture reaches the actual wall through both pads', [r.tag, wall, before])
            finish_stop(r)
            r.step()
            tech_edge(r)
            row['events'].append(verify_tech(r, before, f'corner-{wall}'))
        r.reset()
        r.position(24)
        if (r.state()['x1'] + r.state()['x2']) / 32 > 150:
            r.e.run(65, p1=['left'], p2=['left'])
        else:
            r.e.run(65, p1=['right'], p2=['right'])
        r.step()
        before = r.state()
        takeoff = (r.direction(), 'up')
        s = r.step(takeoff)
        if core == 'accuracy' and not s[f'y{r.a}']:
            s = r.step(takeoff)
        require(s[f'y{r.a}'] != 0, 'crossing fixture launches a real diagonal jump')
        r.e.run(85)
        s = r.state()
        require((s['x1'] < s['x2']) != (before['x1'] < before['x2']) and not s['y1'] and not s['y2'],
                'crossing fixture lands on the opposite side through ordinary jump physics', [r.tag, before, s])
        before = r.grab()
        finish_stop(r)
        r.step()
        tech_edge(r)
        row['events'].append(verify_tech(r, before, 'crossed-owner-side'))
        # Air and out-of-range commands retain the ordinary heavy punch.
        for airborne in (False, True):
            r.reset()
            if airborne:
                s = r.step((), ('up',))
                if core == 'accuracy' and not s[f'y{r.d}']:
                    s = r.step((), ('up',))
                require(s[f'y{r.d}'] != 0 and s[f'down_state{r.d}'] == 0,
                        'air rejection fixture is genuinely airborne through a controller jump', [r.tag, s])
            s = r.step((), command(r))
            if core == 'accuracy' and s[f'action{r.d}'] != 3:
                s = r.step((), command(r))
            require(s[f'action{r.d}'] == 3 and not s['down_state1'] and not s['down_state2'] and
                    read(r.e, 'impactBannerCounter') != 3,
                    'airborne or distant Toward+X retains its normal action without a fabricated tech', [r.tag, airborne, s])
        # Pause freezes ownership and wake timers. Start owns the resume sample.
        r.reset()
        r.grab()
        finish_stop(r)
        r.step()
        r.e.run(1, **{f'p{r.d}': ['start']})
        if core == 'accuracy' and not r.state()['paused']:
            r.e.run(1, **{f'p{r.d}': ['start']})
        require(r.state()['paused'] == 1, 'controller pauses before the freeze measurement')
        frozen = C.string_at(r.e.ram + SYMS['fighters'], 128)
        private = C.string_at(r.e.ram + SYMS['v29DefenseState'], 16)
        r.e.run(24, **{f'p{r.d}': [r.direction(True, True)]})
        # Native capture samples keys on pause; compare the actual down/link/physics clocks.
        current = C.string_at(r.e.ram + SYMS['fighters'], 128)
        offsets = tuple(range(8)) + tuple(range(48, 58))
        require(all(current[p * 64 + i] == frozen[p * 64 + i] for p in (0, 1) for i in offsets) and
                C.string_at(r.e.ram + SYMS['v29DefenseState'], 16) == private,
                'pause freezes lift physics ownership damage wake buffers and defense clocks', r.tag)
        s = r.step((), ('start', *command(r)))
        if core == 'accuracy' and s['paused']:
            s = r.step((), ('start', *command(r)))
        require(not s['paused'] and s[f'down_state{r.d}'] == 1,
                'Start owns the resume sample over a throw-tech command', [r.tag, s])
        r.step()
        before = r.state()
        tech_edge(r)
        row['events'].append(verify_tech(r, before, 'pause-resume-fresh'))
        r.reset()
        r.grab()
        r.reset()
        s = r.state()
        require(s['pending_throw_damage1'] == s['pending_throw_damage2'] == 0 and
                s['throw_owner1'] == s['throw_owner2'] == s['throw_victim1'] == s['throw_victim2'] == 255,
                'live Training reset cancels an actual linked grab and its deferred damage')
        r.grab()
        await_wake(r)
        wait_for(r, lambda s: s[f'down_state{r.d}'] == 0, 'wake timer reset fixture')
        require(timer(r) == 10, 'reset fixture has actual active wake protection')
        r.reset()
        require(C.string_at(r.e.ram + SYMS['v29DefenseState'], 16) == bytes(16),
                'Training reset clears only this feature reservation without stale protection')
        row['stream'] = r.stream('defenses')
        return row
    finally:
        r.stream('latest-diagnostic')
        r.close()


def measure(core, fighter, port, label='baseline', rom=None):
    r = Rig(fighter, port, core, rom=rom)
    try:
        s = r.grab()
        start_hp = s[f'hp{r.d}']
        row = {'core': core, 'fighter': fighter, 'port': port,
               'grab': s, 'states': [], 'damage_callback': None}
        previous = None
        for callback in range(160):
            state = (s[f'down_state{r.d}'], s[f'down_tick{r.d}'], s[f'invuln{r.d}'])
            row['states'].append({'callback': callback, 'state': list(state), 'hitstop': s['hitstop'],
                                  'hp': s[f'hp{r.d}'], 'pending': s[f'pending_throw_damage{r.d}']})
            if s[f'hp{r.d}'] < start_hp and row['damage_callback'] is None:
                row['damage_callback'] = callback
            if state[0] == 0 and previous is not None and previous[0] != 0:
                row['recovery_callback'] = callback
            if 'recovery_callback' in row and state[2] == 0:
                break
            previous = state
            s = r.step()
        require(row['damage_callback'] is not None and 'recovery_callback' in row,
                'measure a real linked throw through damage and complete recovery', row)
        row['stream'] = r.stream(label)
        return row
    finally:
        r.close()


def cpu_case(core, level, delay):
    r = Rig(0, 0, core, mode=2)
    row = {'core': core, 'difficulty': level, 'paused_delay': delay, 'observations': []}
    try:
        r.position(24)
        r.e.tap('start')
        r.e.tap('up')
        require(read(r.e, 'trainingDummy') == 4, 'CPU proof selects the actual Training CPU through the pause card')
        for _ in range((level - read(r.e, 'difficulty')) % 3):
            r.e.tap('r')
        r.e.run(delay)
        r.e.run(1, p1=['start'])
        if r.state()['paused']:
            r.e.run(1, p1=['start'])
        r.step()
        before = r.start_throw()
        for _ in range(20):
            s = r.state()
            row['observations'].append({k: s[k] for k in ('frame', 'hitstop', 'down_state2', 'down_tick2',
                                                         'raw_keys2', 'hp1', 'hp2', 'guard1', 'guard2')})
            if s['down_state2'] == 0 or s['down_state2'] == 2:
                break
            r.step()
        escaped = s['down_state2'] == 0
        if escaped:
            require(any(o['down_tick2'] == 2 and o['hitstop'] == 0 for o in row['observations'][:-1]),
                    'CPU waits for two visible live lift ticks before its only attempt', row)
            verify_tech(r, before, f'cpu-{level}-{delay}', observe_tail=False)
        else:
            failed_escape(r, before, f'cpu-{level}-{delay}')
        require(all(o['raw_keys2'] == 0 for o in row['observations']
                    if o['down_state2'] == 1 and (o['down_tick2'] < 2 or o['hitstop'])),
                'CPU cannot escape instantly or queue a hitstop escape', row)
        row['escaped'] = escaped
        row['stream'] = r.stream(f'cpu-{level}-{delay}')
        return row
    finally:
        r.stream('latest-cpu-diagnostic')
        r.close()


def ko_case(core, port, fighter=0):
    r = Rig(fighter, port, core)
    row = {'core': core, 'fighter': fighter, 'port': port, 'throws': 0}
    try:
        for _ in range(10):
            r.settle()
            r.e.run(12)
            before = r.grab()
            row['throws'] += 1
            lethal = before[f'hp{r.d}'] <= before[f'pending_throw_damage{r.d}']
            if lethal:
                finish_stop(r)
                for _ in range(5):
                    r.step()
                keys = command(r)
                r.step((), keys)
                s = wait_for(r, lambda s: s['round_end'] != 0, 'lethal throw reaches its earned KO', defend=keys)
                require(s[f'hp{r.d}'] == 0 and s[f'hp{r.a}'] == 128 and s[f'down_state{r.d}'] == 3 and
                        read(r.e, 'impactBannerCounter') != 3,
                        'late or held input cannot undo lethal landing damage or revive a KO', [r.tag, s])
                for _ in range(6):
                    s = r.step((), keys)
                require(s[f'hp{r.d}'] == 0 and s['round_end'] > 0,
                        'round-end input cannot fabricate a post-KO tech', [r.tag, s])
                row['ko'] = s
                row['stream'] = r.stream('ko')
                return row
            wait_for(r, lambda s: s[f'down_state{r.d}'] == 3, 'KO setup throw lands')
        raise AssertionError(('KO setup did not finish', row, r.state()))
    finally:
        r.stream('latest-ko-diagnostic')
        r.close()


def unaffected(fighter, port, phase):
    r = Rig(fighter, port, rom=OUT / 'baseline/abaqus-after-hours.sfc' if phase == 'before' else None)
    try:
        # Forced-blank loader callbacks can straddle the frontend boundary;
        # old 0x55 core-fill bytes are not initialized combat state. Retain
        # that complete route separately, then compare every LIVE byte and
        # game-frame value without masks, time offsets or omitted live ticks.
        boot_stream = r.stream(f'boot-unaffected-{phase}')
        r.e.stream = []
        r.position(112)
        for _ in range(12):
            r.step((r.direction(),))
        for _ in range(18):
            r.step((r.direction(False),))
        r.step(('up', r.direction()))
        r.e.run(90)
        for key in ('y', 'x', 'b', 'a'):
            r.position(112)
            r.step((key,))
            r.e.run(65)
        r.position(24)
        r.step(('y',))
        r.e.run(70)
        # Hash complete, unmasked traces, Fighter/Wave/RNG and native pads,
        # throughout ordinary live play. The complete loader is also retained.
        row = r.stream(f'unaffected-{phase}')
        row['boot_stream'] = boot_stream
        return r.e.stream, row
    finally:
        r.close()


def git_bytes(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def static_contract():
    current_text = (ROOT / 'dist/abaqus-after-hours.sym').read_text()
    baseline_text = (OUT / 'baseline/abaqus-after-hours.sym').read_text()
    full = lambda text: {name: int(address, 16) for address, name in re.findall(
        r'^([0-9A-Fa-f]{8}) (\S+)$', text, re.M)}
    old, new = full(baseline_text), full(current_text)
    ram = lambda address: address < 0x2000 or 0x7e0000 <= address < 0x800000
    prior_ram = {name: address for name, address in old.items() if ram(address)}
    drift = {name: [address, new.get(name)] for name, address in prior_ram.items() if new.get(name) != address}
    require(not drift, 'all prior variable data and SDK WRAM symbols retain their exact addresses', drift)
    added_ram = {name: address for name, address in new.items() if ram(address) and name not in old}
    require(not added_ram, 'no mutable definition or RAM label is added outside the parent reservation', added_ram)
    allowed = {'src/game.c', 'src/cpu_personality.h', 'src/pause_guide.h'}
    preserved = {}
    for line in git_bytes('ls-tree', '-r', '29fee83', 'src').decode().splitlines():
        _, _, blob, name = line.split(None, 3)
        if name in allowed:
            continue
        raw = (ROOT / name).read_bytes().replace(b'\r\n', b'\n')
        actual = hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest()
        require(actual == blob, 'unowned native source including profiles and hardware/trace ASM stays exact', name)
        preserved[name] = sha(raw)
    assets = {}
    for line in git_bytes('ls-tree', '-r', '29fee83', 'assets/generated').decode().splitlines():
        _, _, blob, name = line.split(None, 3)
        raw = (ROOT / name).read_bytes()
        actual = hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest()
        require(actual == blob, 'all tracked generated assets stay byte-identical', name)
        assets[name] = sha(raw)
    require(len(assets) == 226, 'the complete tracked generated inventory remains 226 files', len(assets))
    sections = []
    for name, start in new.items():
        if not name.startswith('SECTIONSTART_') or start >> 16 in (0x7e, 0x7f) or start < 0x800000:
            continue
        end = new.get(name.replace('SECTIONSTART_', 'SECTIONEND_', 1))
        if end is None:
            continue
        # SECTIONEND is exclusive; a section ending exactly at xx:10000
        # occupies the preceding bank's final byte, not the following bank.
        require(start >> 16 == (end - 1 if end > start else end) >> 16 and
                (start & 65535) >= 0x8000 and 0 <= end - start <= 32768,
                'every linked ROM section stays inside one 32KiB LoROM bank', [name, start, end])
        sections.append({'section': name.removeprefix('SECTIONSTART_'), 'start': f'{start:06X}',
                         'end': f'{end:06X}', 'bytes': end - start})
    stack = {name: int(size) for name, size in re.findall(r'^\.define __(defense29\w+)_locals (\d+)$',
                                                        (ROOT / 'build/game.asm').read_text(), re.M)}
    return {'prior_wram_symbols': len(prior_ram), 'wram_drift': drift, 'added_ram_symbols': added_ram,
            'feature_stack_local_bytes': stack, 'preserved_sources': preserved,
            'tracked_generated_assets': assets, 'extra_generated_header_sha256': sha((ROOT / 'assets/generated/soundbank.h').read_bytes()),
            'rom_sections': sections, 'reservation_address': f'{new["v29DefenseState"]:06X}',
            'reservation_bytes': 16, 'used_bytes': [0, 1], 'new_mutable_definitions': 0,
            'new_obj_slots': 0, 'new_dma_bytes': 0, 'max_actor_upload_bytes': 3840,
            'unsafe_bg1_map_dma_added': False, 'hardware_trace_asm_changes': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--measure', action='store_true')
    parser.add_argument('--fighter', type=int, default=None)
    parser.add_argument('--section', choices=('all', 'defense', 'cpu', 'ko', 'preservation'), default='all')
    parser.add_argument('--core', choices=('both', 'snes9x', 'accuracy'), default='both')
    args = parser.parse_args()
    global SYMS
    SYMS = symbols(ROOT / 'dist/abaqus-after-hours.sym')
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    sources = snapshot(ROOT)
    artifact_names = ('dist/abaqus-after-hours.sfc', 'dist/abaqus-after-hours.sym', 'dist/manifest.json',
                      'build/defense29/baseline/abaqus-after-hours.sfc',
                      'build/defense29/baseline/abaqus-after-hours.sym')
    artifacts = {name: sha((ROOT / name).read_bytes()) for name in artifact_names}
    report = {'status': 'failed', 'rom_sha256': sha((ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()),
              'controller_only': True, 'memory_writes': False, 'save_states': False,
              'checks': CHECKS, 'native_health': HEALTH, 'cases': [], 'cpu_cases': [], 'ko_cases': [],
              'unaffected_cases': [], 'throw_preservation': [], 'source_sha256': sources,
              'artifact_sha256': artifacts, 'host_contract': host_contract(),
              'command': [sys.executable, *sys.argv], 'base_commit': '29fee83',
              'source_commit': git_bytes('rev-parse', 'HEAD').decode().strip(),
              'source_snapshot_sha256': sha(json.dumps(sources, sort_keys=True, separators=(',', ':')).encode()),
              'harness_sha256': sha(Path(__file__).read_bytes())}
    try:
        require(sha((ROOT / '.tools/core/snes9x_libretro.dll').read_bytes()) == EXPECTED_NATIVE_CORE['dll_sha256'].lower(),
                'pinned Snes9x core hash')
        require(sha(compatibility.CORE_PATH.read_bytes()) == compatibility.CORE_DLL_SHA256.lower(),
                'pinned Accuracy core hash')
        dependencies = [ROOT / '.tools/core/snes9x_libretro.dll', compatibility.CORE_PATH,
                        ROOT / '.tools/python/python.exe',
                        ROOT / '.tools/sdk/pvsneslib/devkitsnes/tools/816-opt.exe',
                        ROOT / '.tools/sdk/pvsneslib/devkitsnes/bin/816-tcc.exe',
                        ROOT / '.tools/sdk/pvsneslib/devkitsnes/bin/wla-65816.exe',
                        ROOT / '.tools/sdk/pvsneslib/devkitsnes/bin/wlalink.exe',
                        ROOT / '.tools/sdk/pvsneslib/devkitsnes/include/hdr.asm.in']
        dependencies.extend((ROOT / '.tools/sdk/pvsneslib/pvsneslib/lib/LoROM_FastROM').glob('*.obj'))
        dependencies.extend((ROOT / '.tools/sdk/pvsneslib/pvsneslib/include').rglob('*.h'))
        dependencies.extend((ROOT / '.tools/sdk/pvsneslib/devkitsnes/include').rglob('*.h'))
        report['dependencies_sha256'] = {path.relative_to(ROOT).as_posix(): sha(path.read_bytes()) for path in dependencies}
        if args.measure:
            for core, fighters in [('snes9x', range(12) if args.fighter is None else [args.fighter]),
                                   ('accuracy', [0])]:
                for fighter in fighters:
                    for port in (0, 1):
                        report['cases'].append(measure(core, fighter, port))
                    print(json.dumps({'core': core, 'fighter': fighter, 'status': 'measured'}), flush=True)
        else:
            report['static_contract'] = static_contract()
            baseline = json.loads((OUT / 'baseline-measurement.json').read_bytes())
            report['baseline'] = {'rom_sha256': baseline['rom_sha256'],
                'measurement_sha256': sha((OUT / 'baseline-measurement.json').read_bytes()),
                'callbacks': baseline['native_health'],
                'cases': [{k: r[k] for k in ('core', 'fighter', 'port', 'damage_callback', 'recovery_callback', 'stream')}
                          for r in baseline['cases']]}
            if args.section in ('all', 'defense'):
                for core, fighters in [('snes9x', range(12) if args.fighter is None else [args.fighter]),
                                       ('accuracy', (0, 1, 8, 11) if args.fighter is None else [args.fighter])]:
                    if args.core != 'both' and args.core != core:
                        continue
                    for fighter in fighters:
                        for port in (0, 1):
                            report['cases'].append(defense_case(core, fighter, port))
                        print(json.dumps({'core': core, 'fighter': fighter, 'status': 'passed'}), flush=True)
            if args.section in ('all', 'cpu'):
                for core in ('snes9x', 'accuracy'):
                    if args.core != 'both' and args.core != core:
                        continue
                    for level in ((0, 1, 2) if core == 'snes9x' else (2,)):
                        cases = [cpu_case(core, level, delay) for delay in range(4)]
                        require(sum(row['escaped'] for row in cases) == (0, 1, 2)[level],
                                'CPU policy earns bounded fallible phase-sampled escapes', [core, level, cases])
                        report['cpu_cases'].extend(cases)
                        print(json.dumps({'core': core, 'cpu_level': level, 'status': 'passed'}), flush=True)
            if args.section in ('all', 'ko'):
                for core in ('snes9x', 'accuracy'):
                    if args.core != 'both' and args.core != core:
                        continue
                    fighters = ((range(12) if core == 'snes9x' else (0, 1, 8, 11))
                                if args.fighter is None else (args.fighter,))
                    for fighter in fighters:
                        for port in (0, 1):
                            report['ko_cases'].append(ko_case(core, port, fighter))
                        print(json.dumps({'core': core, 'ko_fighter': fighter, 'roles': 'passed'}), flush=True)
            if args.section in ('all', 'preservation'):
                for fighter in (range(12) if args.fighter is None else [args.fighter]):
                    for port in (0, 1):
                        before, old = unaffected(fighter, port, 'before')
                        after, new = unaffected(fighter, port, 'after')
                        difference = next((i for i, (a, b) in enumerate(zip(before, after)) if a != b), None)
                        require(before == after,
                                'ordinary movement jump and four normals preserve every unmasked live native state byte',
                                {'fighter': fighter, 'port': port, 'first_difference': difference,
                                 'before': before[difference] if difference is not None else len(before),
                                 'after': after[difference] if difference is not None else len(after)})
                        report['unaffected_cases'].append({'fighter': fighter, 'port': port, 'before': old, 'after': new,
                                                           'complete_unmasked_equality': True})
                        current = measure('snes9x', fighter, port, label='candidate-throw')
                        prior = next(r for r in baseline['cases'] if (r['core'], r['fighter'], r['port']) == ('snes9x', fighter, port))
                        reference = measure('snes9x', fighter, port, label='baseline-replay',
                                            rom=OUT / 'baseline/abaqus-after-hours.sfc')
                        require(reference['states'] == prior['states'],
                                'frozen final harness reproduces the pre-implementation baseline throw measurement', [fighter, port])
                        require(current['states'] == reference['states'],
                                'unteched throw damage launch floor rise wake and invulnerability stay exact', [fighter, port])
                        entry = {k: current[k] for k in ('fighter', 'port', 'damage_callback', 'recovery_callback', 'stream')}
                        entry['baseline_replay'] = reference['stream']
                        report['throw_preservation'].append(entry)
                    print(json.dumps({'fighter': fighter, 'unaffected_and_throw_preservation': 'passed'}), flush=True)
            require(snapshot(ROOT) == sources, 'producer harness and all native sources stay fixed during the proof')
            require(all(sha((ROOT / name).read_bytes()) == digest for name, digest in artifacts.items()),
                    'tested ROM symbols and manifest stay fixed during the proof')
            require(all(sha((ROOT / name).read_bytes()) == digest for name, digest in report['dependencies_sha256'].items()),
                    'pinned core Python and compiler dependency bytes stay fixed during the proof')
            require(all(sha((ROOT / name).read_bytes()) == digest for name, digest in
                        report['static_contract']['tracked_generated_assets'].items()),
                    'all 226 generated asset bytes stay fixed during the proof')
            report['captures'] = [{'path': p.relative_to(ROOT).as_posix(), 'sha256': sha(p.read_bytes())}
                                  for p in sorted((ROOT / 'docs/screenshots/defense29').glob('*.png'))]
        report['status'] = 'passed'
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
        report['check_executions'] = sum(c['executions'] for c in CHECKS.values())
        path = (OUT / 'baseline-measurement.json' if args.measure else
                OUT / f'diagnostic-{args.section}.json' if args.fighter is not None or args.section != 'all' or args.core != 'both'
                else ROOT / 'docs/defense29-report.json')
        temporary = path.with_suffix(path.suffix + '.tmp')
        temporary.write_bytes((json.dumps(report, indent=2) + '\n').encode())
        temporary.replace(path)
        print(json.dumps({k: report[k] for k in ('status', 'check_executions', 'elapsed_seconds')}), flush=True)


if __name__ == '__main__':
    main()
