"""Controller-only ordinary-special timing regression; silent pinned native cores.

Baseline --observe retains failures. Only behavioral comparison collapses its
repeated logical frames; candidate cadence/SDK/OBJ/DMA/SPC checks stay strict.
Run through the canonical run_background.py with job-local affinity 768.
"""
from __future__ import annotations
import argparse
import ctypes as C
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from test_contact_24_timing import TimingHost, AccuracyHost, symbols, read, static_contract
from test_endurance import EnduranceRun, core_identity
from test_champion import host_contract
import test_compatibility as compat

MOVES = [('jab', ('y',), 1), ('cross', ('x',), 3),
         ('light-kick', ('b',), 4), ('strong-kick', ('a',), 5),
         ('sweep', ('down', 'a'), 6), ('uppercut', ('down', 'x'), 8),
         ('special', ('down', 'y'), 7)]
BASE = '22495b9a945a5c7903bc7e9972e2d0f2d2a34c5a'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(ok, detail):
    if not ok:
        raise AssertionError(detail)


def boot(host, fighter, stage):
    """Exact test_characters.boot(1, f, stage, f) callback/menu schedule."""
    def press(key, port=0):
        host.run(3, **({'p1': [key]} if port == 0 else {'p2': [key]}))
        host.run(23)

    def screen(wanted):
        for _ in range(60):
            if host.state()['screen'] == wanted:
                host.run(10)
                return
            host.run(10)
        raise AssertionError(('boot screen', wanted, host.state()))

    host.run(120)
    press('down'); press('a'); screen(1)
    for _ in range(fighter):
        press('right')
    press('a')
    for _ in range((fighter-host.state()['selected2']) % 12):
        press('right', 1)
    press('a', 1); screen(2)
    for _ in range(stage):
        press('down')
    press('a'); screen(3)
    for _ in range(160):
        if not host.state()['intro']:
            break
        host.run(1)
    require(not host.state()['intro'], 'intro did not finish')
    host.run(3)


def snapshot(host):
    s = host.state()
    s['native_frame'] = int.from_bytes(read(host, 'frame', 2), 'little')
    s['fighters_hex'] = read(host, 'fighters', 128).hex()
    s['waves_hex'] = read(host, 'waves', 32).hex()
    s['trace_hex'] = C.string_at(host.ram+0x1ff00, 246).hex()
    s['recoil'] = read(host, 'rearKickRecoil', 1)[0]
    s['supers_hex'] = b''.join(read(host, n, 2) for n in (
        'superActive', 'superRequest', 'superPhase', 'superNext',
        'superContactEnd', 'superWaveDamage', 'superWaveReach')).hex()
    return s


def run_case(args, fighter, stage, phase, port, spacing):
    host = (AccuracyHost if args.core == 'accuracy' else TimingHost)(args.rom, symbols(args.symbols))
    rows, failures, events = [], [], []
    runner = EnduranceRun(1, 1, coverage_required=False)
    old_vram = None
    maximum_changed_bytes = 0
    try:
        boot(host, fighter, stage)
        previous = snapshot(host)

        def step(p1=(), p2=(), label=''):
            nonlocal previous, old_vram, maximum_changed_bytes
            pcm_before = host.audio_samples
            host.run(1, p1=p1, p2=p2)
            s = snapshot(host)
            runner.inspect(host, s, list(p1), list(p2))
            delta = {n: (s[n]-previous[n]) & 65535 for n in (
                'frame', 'native_frame', 'lag_frame_counter', 'snes_vblank_count')}
            if delta != dict(frame=1, native_frame=1, lag_frame_counter=0, snes_vblank_count=1):
                failures.append(dict(kind='direct_cadence', callback=len(rows)+1,
                    label=label, before_frame=previous['frame'], frame=s['frame'],
                    deltas=delta, ticks=[int(s['fighters_hex'][34:36], 16), int(s['fighters_hex'][162:164], 16)],
                    hp=[s['hp1'], s['hp2']], hitstop=s['hitstop']))
            if host.audio_samples <= pcm_before:
                failures.append(dict(kind='pcm_callback', callback=len(rows)+1))
            vram = C.string_at(host.core.retro_get_memory_data(3)+0xc000, 10240)
            pages = [vram[p*5120:(p+1)*5120] for p in (0, 1)]
            if old_vram is not None:
                changed = [sum(a != b for a, b in zip(old_vram[p], pages[p])) if old_vram[p] != pages[p] else 0 for p in (0, 1)]
                maximum_changed_bytes = max(maximum_changed_bytes, sum(changed))
                if sum(bool(n) for n in changed) > 1 or sum(changed) > 3840:
                    failures.append(dict(kind='actor_dma', callback=len(rows)+1, changed=changed))
            old_vram = pages
            rows.append(dict(callback=len(rows)+1, label=label, keys=[list(p1), list(p2)],
                **{n: s[n] for n in ('frame', 'native_frame', 'lag_frame_counter', 'snes_vblank_count',
                    'fighters_hex', 'waves_hex', 'trace_hex', 'recoil', 'supers_hex')}))
            previous = s
            return s

        def run(n, p1=(), p2=(), label=''):
            # Give each held input its declared logical duration. Retain
            # every physical callback and SDK failure, including repeats.
            # This permits identical input edges on compared logical ticks.
            completed = 0
            for _ in range(n+16):
                if completed >= n:
                    return
                frame_before = previous['frame']
                s = step(p1, p2, label)
                completed += (s['frame']-frame_before) & 65535
            raise AssertionError(('logical segment did not finish', label, n))

        def settle():
            for _ in range(240):
                s = host.state()
                if not s['hitstop'] and not any(s[f'{n}{p}'] for n in ('action', 'hurt', 'y', 'down_state') for p in (1, 2)):
                    run(6, label='settle')
                    return
                step(label='settle')
            raise AssertionError(('settle', fighter, host.state()))

        def position(target):
            settle()
            for _ in range(360):
                s = host.state()
                distance = abs(s['x1']-s['x2'])/16
                if abs(distance-target) < 1.8:
                    run(2+phase, label='position-phase')
                    events.append(dict(label='position', target=target, x=[s['x1'], s['x2']], faces=[s['face1'], s['face2']]))
                    return
                toward = 'right' if s[f'x{port+1}'] < s[f'x{2-port}'] else 'left'
                key = toward if distance > target else ('left' if toward == 'right' else 'right')
                keys = [(), ()]
                if distance < target and ((key == 'left' and s[f'x{port+1}'] <= 24*16) or (key == 'right' and s[f'x{port+1}'] >= 232*16)):
                    keys[1-port] = (toward,)
                else:
                    keys[port] = (key,)
                step(*keys, label='position')
            raise AssertionError(('spacing', fighter, target, distance))

        def command(label, keys, action, wait=75):
            before = host.state()
            start = len(rows)
            # Offsets 0/1/2 exercise simultaneous and staggered commands.
            # Each pad holds its command for exactly three logical ticks;
            # approach_port also chooses which pad leads the offset.
            # Short jabs can legally cancel the lagging actor in the very
            # callback that accepts its input, before action publication.
            # Keep normal trade fixtures simultaneous, and stagger the
            # longer ordinary-special/super startups under investigation.
            offset = phase if action == 7 else 0
            first, second = [(), ()], [(), ()]
            first[port] = keys; second[1-port] = keys
            run(offset, *first, label)
            run(3-offset, keys, keys, label)
            run(offset, *second, label)
            run(wait, label=label)
            command_rows = rows[start:]
            for p in (0, 1):
                require(any(bytes.fromhex(r['fighters_hex'])[p*64+16] == action for r in command_rows), ('missing command', fighter, label, p))
            after = host.state()
            events.append(dict(label=label, before_hp=[before['hp1'], before['hp2']],
                after_hp=[after['hp1'], after['hp2']], callbacks=len(command_rows)))

        run(120, ('left',), ('right',), 'separate')
        for label, keys, action in MOVES:
            command(label, keys, action)
        if spacing == 'close':
            # Actual mirror trades on both approach directions. No WRAM,
            # states, resets, or invulnerability modifications.
            for label, keys, action in [('close-jab', ('y',), 1), ('close-cross', ('x',), 3),
                                        ('close-kick', ('a',), 5), ('close-special', ('down', 'y'), 7)]:
                position(29)
                command(label, keys, action, 100)
        settle()
        # Recharge through real native time so both supers use the ordinary
        # energy/chord path after the seven-move special fixture.
        for _ in range(1600):
            s = host.state()
            if s['energy1'] == 96 and s['energy2'] == 96 and not (s['wave1'] or s['wave2']):
                break
            step(label='recharge')
        else:
            raise AssertionError(('super recharge failed', fighter, host.state()))
        position(29 if spacing == 'close' else 180)
        command('super', ('y', 'b'), 7, 170)
        require(any(bytes.fromhex(r['supers_hex'])[p] for r in rows if r['label'] == 'super' for p in (0, 1)), 'super not accepted')
        arrays = {n: getattr(runner, n) for n in ('cadence_failures', 'native_timing_failures',
            'ambient_failures', 'overflow_frames', 'spc_fifo_failures')}
        failures.extend(dict(kind=n, evidence=v) for n, v in arrays.items() if v)
        require(host.audio_samples > 0 and host.audio_peak > 0 and host.audio_peak < 32767, 'PCM health')
        return dict(fighter=fighter, stage=stage, phase=phase, approach_port=port, spacing=spacing,
            status='failed' if failures else 'passed', failures=failures, events=events, rows=rows,
            callbacks=len(rows), max_changed_actor_bytes=maximum_changed_bytes,
            peak_spc_backlog=runner.max_spc_backlog, pcm_samples=host.audio_samples,
            pcm_peak=host.audio_peak, sdk_lag_increments=runner.lag_counter_increments)
    finally:
        host.close()


def compare(before, after):
    result = []
    for old, new in zip(before['cases'], after['cases'], strict=True):
        identity = ('fighter', 'stage', 'phase', 'approach_port', 'spacing')
        require(all(old[n] == new[n] for n in identity), 'case identities differ')
        with gzip.open(old['stream'], 'rt') as f:
            a = json.load(f)
        with gzip.open(new['stream'], 'rt') as f:
            b = json.load(f)
        # Last callback for a repeated baseline trace, as in the existing
        # contact timing proof. Keep all original failures and raw streams.
        aa = {r['frame']: r for r in a}
        bb = {r['frame']: r for r in b}
        common = sorted(aa.keys() & bb.keys())
        differences = []
        for tick in common:
            fields = ['fighters_hex', 'waves_hex', 'recoil', 'supers_hex']
            diff = {n: [aa[tick][n], bb[tick][n]] for n in fields if aa[tick][n] != bb[tick][n]}
            if diff:
                differences.append(dict(frame=tick, fields=diff))
        result.append(dict(**{n: new[n] for n in identity}, logical_ticks=len(common),
            baseline_repeats=len(a)-len(aa), candidate_repeats=len(b)-len(bb),
            differences=differences))
    return dict(status='failed' if any(r['differences'] or r['candidate_repeats'] for r in result) else 'passed',
        logical_ticks=sum(r['logical_ticks'] for r in result),
        baseline_repeats=sum(r['baseline_repeats'] for r in result), cases=result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, default=ROOT/'dist/abaqus-after-hours.sfc')
    parser.add_argument('--symbols', type=Path, default=ROOT/'dist/abaqus-after-hours.sym')
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--core', choices=['snes9x', 'accuracy'], default='snes9x')
    parser.add_argument('--observe', action='store_true')
    parser.add_argument('--fighters', type=int, nargs='+', default=list(range(12)))
    parser.add_argument('--stages', type=int, nargs='+', default=[0, 1, 2])
    parser.add_argument('--phases', type=int, nargs='+', default=[0, 1, 2])
    parser.add_argument('--ports', type=int, nargs='+', default=[0, 1])
    parser.add_argument('--spacing', nargs='+', choices=['wide', 'close'], default=['wide', 'close'])
    parser.add_argument('--compare', type=Path, nargs=2)
    parser.add_argument('--baseline-symbols', type=Path, default=ROOT/'build/special-timing/before/abaqus-after-hours.sym')
    parser.add_argument('--base-commit', default=BASE)
    args = parser.parse_args()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    if args.compare:
        a, b = [json.loads(p.read_text()) for p in args.compare]
        result = compare(a, b)
        report = dict(status='passed' if result['status'] == b['status'] == 'passed' else 'failed',
            comparison=result, contracts=static_contract(args),
            evidence=[dict(path=str(p), sha256=sha(p)) for p in args.compare],
            producer_sha256=sha(__file__), final_combined_certification=False)
    else:
        if args.core == 'accuracy':
            compat.ROM_PATH = args.rom
            compat.MANIFEST_PATH = args.rom.parent/'manifest.json'
            core = compat.verify_manifest_and_pinned_core()
        else:
            core = core_identity()
        started = time.monotonic()
        report = dict(status='failed', core=core, engine=args.core, host=host_contract(),
            rom_sha256=sha(args.rom), symbols_sha256=sha(args.symbols),
            producer_sha256=sha(__file__), cases=[], final_combined_certification=False,
            schedule='test_characters exact menu boot; 120 retreat callbacks; seven complete 3+75 logical move segments; close simultaneous normal trades; natural recharge and ordinary super chords. Offsets 0/1/2 stagger specials/supers only; port chooses leading/approach pad.',
            baseline_source_commit=BASE,
            dependencies={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),
                ROOT/'tools/test_contact_24_timing.py', ROOT/'tools/longrun_host.py',
                ROOT/'tools/test_endurance.py', ROOT/'tools/test_compatibility.py',
                ROOT/'tools/run_background.py']})
        try:
            for f in args.fighters:
                for stage in args.stages:
                    for phase in args.phases:
                        for port in args.ports:
                            for spacing in args.spacing:
                                r = run_case(args, f, stage, phase, port, spacing)
                                stream = args.report.parent/(args.report.stem+f'-{f}-{stage}-{phase}-{port}-{spacing}.json.gz')
                                with gzip.open(stream, 'wt', encoding='utf-8') as output:
                                    json.dump(r.pop('rows'), output, separators=(',', ':'))
                                r.update(stream=str(stream.resolve()), stream_sha256=sha(stream))
                                report['cases'].append(r)
                                print(json.dumps({n:r[n] for n in ('fighter', 'stage', 'phase', 'approach_port', 'spacing', 'status', 'callbacks')}), flush=True)
            report['status'] = 'passed' if all(r['status'] == 'passed' for r in report['cases']) else 'failed'
        except Exception as error:
            report['error'] = repr(error)
            raise
        finally:
            report['elapsed_seconds'] = round(time.monotonic()-started, 3)
            args.report.write_text(json.dumps(report, indent=2)+'\n')
    args.report.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(status=report['status'], report=str(args.report))), flush=True)
    return int(report['status'] != 'passed' and not args.observe)


if __name__ == '__main__':
    raise SystemExit(main())
