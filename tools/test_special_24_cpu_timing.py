"""Exact CPU encounter and logical-input replay for the v0.24 timing fix.

All memory access is read-only. Baseline physical failures remain failures;
replay alone removes repeated baseline callbacks to compare the same native
Fighter/Wave/RNG/CPU trajectory on identical logical input edges.
"""
from __future__ import annotations
import argparse
import ctypes as C
import gzip
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from test_special_24_timing import snapshot, sha, require
from test_contact_24_timing import TimingHost, AccuracyHost, symbols, read
from test_endurance import EnduranceRun, core_identity
from test_champion import host_contract
import test_compatibility as compat
import test_expansion_06_cpu_personality as cpu


class ExactSnes9x(TimingHost):
    def tap(self, key, port=0):
        self.run(3, **({'p1': [key]} if port == 0 else {'p2': [key]}))
        return self.run(3)


class ExactAccuracy(AccuracyHost):
    tap = ExactSnes9x.tap


def state(host):
    s = snapshot(host)
    s['rng_hex'] = read(host, 'randomseed', 2).hex()
    s['cpu_hex'] = b''.join(read(host, n, 1) for n in (
        'cpuTick', 'difficulty', 'trainingDummy', 'mode')).hex()
    s['pads_hex'] = b''.join(read(host, n, 2) for n in (
        'pad0', 'pad1', 'edge0', 'edge1')).hex()
    return s


def run_case(args, fighter, difficulty, old=None):
    table = symbols(args.symbols)
    cpu.SYMBOLS = {n:a & 0x1ffff for n,a in table.items()}
    cpu.legacy.Emulator = lambda: (ExactAccuracy if args.core == 'accuracy' else ExactSnes9x)(args.rom, table)
    e = cpu.boot(fighter, difficulty)
    runner = EnduranceRun(2, 1, coverage_required=False)
    rows, failures = [], []
    previous_vram = None
    if old:
        with gzip.open(old['stream'], 'rt') as f:
            baseline = json.load(f)
        # A repeated publication is not a second logical input sample.
        commands = [r for r in baseline if r['frame'] != r['before_frame']]
    else:
        commands = [None] * args.frames
    try:
        for tick, command in enumerate(commands):
            before = state(e)
            keys = command['keys'][0] if command else cpu.p1_script(before, tick)
            samples = e.audio_samples
            e.run(1, p1=keys, p2=())
            after = state(e)
            runner.inspect(e, after, list(keys), [])
            deltas = {n:(after[n]-before[n]) & 65535 for n in (
                'frame', 'native_frame', 'lag_frame_counter', 'snes_vblank_count')}
            if deltas != dict(frame=1, native_frame=1, lag_frame_counter=0, snes_vblank_count=1):
                failures.append(dict(tick=tick, deltas=deltas, frame=after['frame'],
                    keys=[list(keys), []], before={n:before[n] for n in (
                        'lag_frame_counter', 'snes_vblank_count', 'hp1', 'hp2', 'hitstop', 'hurt1', 'raw_keys2')},
                    after={n:after[n] for n in (
                        'lag_frame_counter', 'snes_vblank_count', 'hp1', 'hp2', 'hitstop', 'hurt1', 'raw_keys2')},
                    pcm_delta=e.audio_samples-samples, spc_backlog=after['spc_backlog']))
            require(e.audio_samples > samples, ('PCM callback missing', tick))
            vram = C.string_at(e.core.retro_get_memory_data(3)+0xc000, 10240)
            if previous_vram:
                changed = [sum(a != b for a,b in zip(previous_vram[p*5120:(p+1)*5120], vram[p*5120:(p+1)*5120])) if previous_vram[p*5120:(p+1)*5120] != vram[p*5120:(p+1)*5120] else 0 for p in (0, 1)]
                require(sum(bool(n) for n in changed) <= 1 and sum(changed) <= 3840, ('actor DMA', tick, changed))
            previous_vram = vram
            rows.append(dict(tick=tick, before_frame=before['frame'], keys=[list(keys), []],
                **{n:after[n] for n in ('frame', 'native_frame', 'lag_frame_counter',
                    'snes_vblank_count', 'fighters_hex', 'waves_hex', 'trace_hex',
                    'recoil', 'supers_hex', 'rng_hex', 'cpu_hex', 'pads_hex')}))
        arrays = {n:getattr(runner, n) for n in ('cadence_failures', 'native_timing_failures',
            'ambient_failures', 'overflow_frames', 'spc_fifo_failures')}
        differences = []
        if old:
            baseline_by_frame = {r['frame']:r for r in baseline}
            for r in rows:
                a = baseline_by_frame[r['frame']]
                fields = ('fighters_hex', 'waves_hex', 'recoil', 'supers_hex', 'rng_hex', 'cpu_hex', 'pads_hex')
                diff = {n:[a[n], r[n]] for n in fields if a[n] != r[n]}
                if diff:
                    differences.append(dict(frame=r['frame'], fields=diff))
        return dict(fighter=fighter, difficulty=difficulty, callbacks=len(rows), rows=rows,
            status='failed' if failures or differences or any(arrays.values()) else 'passed',
            failures=failures, health=arrays, sdk_lag_increments=runner.lag_counter_increments,
            peak_spc_backlog=runner.max_spc_backlog, pcm_samples=e.audio_samples, pcm_peak=e.audio_peak,
            comparison=dict(status='failed' if differences else 'passed', logical_ticks=len(rows) if old else 0,
                baseline_repeated_callbacks=len(baseline)-len(commands) if old else None, differences=differences))
    finally:
        e.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom', type=Path, default=ROOT/'dist/abaqus-after-hours.sfc')
    p.add_argument('--symbols', type=Path, default=ROOT/'dist/abaqus-after-hours.sym')
    p.add_argument('--report', type=Path, required=True)
    p.add_argument('--core', choices=['snes9x', 'accuracy'], default='snes9x')
    p.add_argument('--fighters', nargs='+', type=int, default=list(range(12)))
    p.add_argument('--difficulties', nargs='+', type=int, default=[0, 1, 2])
    p.add_argument('--frames', type=int, default=1800)
    p.add_argument('--replay', type=Path)
    p.add_argument('--observe', action='store_true')
    args = p.parse_args()
    args.report.parent.mkdir(exist_ok=True, parents=True)
    if args.core == 'accuracy':
        compat.ROM_PATH = args.rom
        compat.MANIFEST_PATH = args.rom.parent/'manifest.json'
        core = compat.verify_manifest_and_pinned_core()
    else:
        core = core_identity()
    old = json.loads(args.replay.read_text()) if args.replay else None
    cases = [(r['fighter'], r['difficulty'], r) for r in old['cases']] if old else [(f,d,None) for f in args.fighters for d in args.difficulties]
    started = time.monotonic()
    report = dict(status='failed', core=core, engine=args.core, host=host_contract(),
        rom_sha256=sha(args.rom), symbols_sha256=sha(args.symbols), producer_sha256=sha(__file__),
        schedule='cpu.boot(fighter,difficulty); cpu.p1_script; no physical P2 input',
        replay=dict(path=str(args.replay), sha256=sha(args.replay)) if old else None,
        cases=[], final_combined_certification=False)
    try:
        for f,d,base in cases:
            r = run_case(args, f, d, base)
            stream = args.report.parent/(args.report.stem+f'-{f}-{d}.json.gz')
            with gzip.open(stream, 'wt', encoding='utf-8') as output:
                json.dump(r.pop('rows'), output, separators=(',', ':'))
            r.update(stream=str(stream.resolve()), stream_sha256=sha(stream))
            report['cases'].append(r)
            print(json.dumps({n:r[n] for n in ('fighter', 'difficulty', 'callbacks', 'status', 'sdk_lag_increments')}), flush=True)
        report['status'] = 'passed' if all(c['status'] == 'passed' for c in report['cases']) else 'failed'
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        args.report.write_text(json.dumps(report, indent=2)+'\n')
    return int(report['status'] != 'passed' and not args.observe)


if __name__ == '__main__':
    raise SystemExit(main())
