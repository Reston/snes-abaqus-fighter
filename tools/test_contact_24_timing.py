"""Read-only, controller-driven contact timing regression (silent native cores).

Run through run_background.py. Baseline failures stay failures in the report;
--observe permits retaining their complete trajectories for logical-tick comparison.
"""
from __future__ import annotations
import argparse
import ctypes as C
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import subprocess
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from longrun_host import LongRunHost
from test_endurance import EnduranceRun, boot, core_identity
from test_champion import host_contract
import test_compatibility as compat


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(ok, detail):
    if not ok:
        raise AssertionError(detail)


def dependencies():
    names = ['src/contact_geometry.h', 'src/game.c', 'src/pacing_recoil.h',
             'tools/test_contact_24_timing.py', 'tools/run_background.py',
             'tools/longrun_host.py', 'tools/test_endurance.py', 'tools/test_compatibility.py']
    return {name: digest(ROOT/name) for name in names}


def symbols(path):
    return {n: int(a, 16) for a, n in re.findall(r'^([\da-fA-F]{8}) (\S+)$',
                                              Path(path).read_text(), re.M)}


class TimingHost(LongRunHost):
    def __init__(self, rom, syms):
        self.syms = syms
        super().__init__(rom=rom, video_interval=30)

    def _symbol_offset(self, symbol, fallback):
        return self.syms[symbol] & 0x1ffff


class AccuracyHost(compat.Probe, LongRunHost):
    """Use the pinned Accuracy callbacks, with canonical read-only diagnostics."""
    def __init__(self, rom, syms):
        self.syms = syms
        self._cached_oam_offset = self._cached_vblank_offsets = None
        self._cached_native_screen_offset = self._cached_spc_offsets = None
        compat.ROM_PATH = rom
        compat.Probe.__init__(self)

    state = LongRunHost.state
    tap = LongRunHost.tap
    _symbol_offset = TimingHost._symbol_offset

    @property
    def audio_nonzero_batches(self):
        # The canonical FIFO watchdog only needs a monotonically advancing
        # PCM activity counter. Accuracy's host sums every captured sample.
        return self.audio_energy


def read(host, name, count):
    return C.string_at(host.ram + (host.syms[name] & 0x1ffff), count)


def sample(host):
    s = host.state()
    s['native_frame'] = int.from_bytes(read(host, 'frame', 2), 'little')
    s['fighters_hex'] = read(host, 'fighters', 128).hex()
    s['waves_hex'] = read(host, 'waves', 32).hex()
    s['recoil'] = read(host, 'rearKickRecoil', 1)[0]
    return s


def static_contract(args):
    from contact_geometry import generate
    header, data = generate()
    before = symbols(args.baseline_symbols)
    after = symbols(args.symbols)
    prior_ram = {n: a for n, a in before.items() if a < 0x2000 or 0x7e0000 <= a < 0x800000}
    moved = {n: [a, after.get(n)] for n, a in prior_ram.items() if after.get(n) != a}
    added = {n: a for n, a in after.items() if n not in before and (a < 0x2000 or 0x7e0000 <= a < 0x800000)}
    require(not moved and not added, ('RAM changed', moved, added))
    table = bytes(v for poses in data['poses'] for pose in poses for rect in pose for v in rect)
    table_records = []
    for label, path, syms in [('before', args.baseline_symbols.with_suffix('.sfc'), before),
                              ('after', args.rom, after)]:
        rom = path.read_bytes()
        require(len(rom) == 4*1024*1024, 'ROM size')
        require(rom[0x7fd5] == 0x30, 'NTSC FastROM LoROM mapping')
        require(rom[0x7fd9] == 1, 'NTSC region')
        for name, expected in [('contactPoses', table), ('contactGeometryDigest', bytes.fromhex(data['digest']))]:
            address = syms[name]
            require(address >> 16 not in (0x7e, 0x7f), 'table in RAM')
            require((address & 65535)+len(expected) <= 65536, 'table crosses bank')
            offset = ((address >> 16) & 127)*32768+(address & 32767)
            require(rom[offset:offset+len(expected)] == expected, (label, name))
        table_records.append({'label': label, 'table_address': hex(syms['contactPoses']),
                              'rom_sha256': digest(path)})
    require((ROOT/'build/contact_geometry_data.h').read_bytes() == header, 'stale contact header')
    raw = subprocess.check_output(['git', 'archive', args.base_commit, 'assets/generated',
                                   'src/hardware.asm', 'src/trace.asm'], cwd=ROOT)
    preserved = {}
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        for item in archive:
            if not item.isfile():
                continue
            expected = archive.extractfile(item).read()
            actual = (ROOT/item.name).read_bytes()
            require(actual == expected, ('changed retained file', item.name))
            preserved[item.name] = hashlib.sha256(actual).hexdigest()
    comparisons = 0
    for offset in range(0, len(table), 4):
        rect = table[offset:offset+4]
        lt, rb = int.from_bytes(rect[:2], 'little'), int.from_bytes(rect[2:], 'little')
        require([lt&255, lt>>8, rb&255, rb>>8] == list(rect), 'packed table decode')
        # The native code keeps its original signed 12.4 transforms. Check
        # every 1/16 pixel remainder beside each actual bound in both faces.
        for face in (0, 1):
            left, top, right, bottom = rect
            if not face:
                left, right = 96-right, 96-left
            for edge, packed in zip((left, top, right, bottom),
                                    ((lt&255) if face else 96-(rb&255), lt>>8,
                                     (rb&255) if face else 96-(lt&255), rb>>8)):
                for remainder in range(-16, 17):
                    x = edge*16+remainder
                    require((x < edge*16) == (x < packed*16), 'packed near edge')
                    require((x > edge*16) == (x > packed*16), 'packed far edge')
                    comparisons += 2
    return {'prior_ram_symbols': len(prior_ram), 'moved_ram': moved, 'added_ram': added,
            'fighter_bytes': 64, 'wave_bytes': 16, 'trace_words': 123,
            'geometry_bytes': len(table)+32, 'geometry_digest': data['digest'],
            'table_sha256': hashlib.sha256(table).hexdigest(), 'cartridges': table_records,
            'preserved_files': preserved, 'generated_files': sum(n.startswith('assets/generated/') for n in preserved),
            'packed_edge_equivalence_assertions': comparisons}


def compare_reports(before, after):
    def identity(case):
        return tuple(case[k] for k in ('fighter', 'stage', 'phase', 'key', 'approach_port'))
    old = {identity(c): c for c in before['cases']}
    result = []
    for case in after['cases']:
        base = old[identity(case)]
        # Lag callbacks remain failed timing evidence. Only this explicit
        # behavioral comparison collapses old repeated logical frames.
        a = {r['native_frame']: r for r in base['rows']}
        b = {r['native_frame']: r for r in case['rows']}
        common = a.keys() & b.keys()
        mismatches = []
        for tick in sorted(common):
            fields = ('fighters_hex', 'waves_hex', 'recoil', 'seconds', 'round', 'round_end', 'hitstop', 'combo')
            diff = {k: [a[tick][k], b[tick][k]] for k in fields if a[tick][k] != b[tick][k]}
            if diff:
                mismatches.append({'tick': tick, 'fields': diff})
        result.append({'case': list(identity(case)), 'common_logical_ticks': len(common),
                       'baseline_duplicate_callbacks': len(base['rows'])-len(a),
                       'candidate_duplicate_callbacks': len(case['rows'])-len(b),
                       'candidate_tail_ticks': len(b.keys()-a.keys()), 'mismatches': mismatches})
    return {'status': 'passed' if not any(c['mismatches'] for c in result) else 'failed',
            'compared_logical_ticks': sum(c['common_logical_ticks'] for c in result),
            'baseline_duplicate_callbacks': sum(c['baseline_duplicate_callbacks'] for c in result), 'cases': result}


def run_case(args, fighter=5, stage=2, phase=0, key='y', port=0):
    host = (AccuracyHost if args.core == 'accuracy' else TimingHost)(args.rom, symbols(args.symbols))
    started = time.monotonic()
    rows, failures, controls = [], [], []
    runner = EnduranceRun(1, 1, coverage_required=False)
    old_vram = None
    max_dma = 0
    try:
        boot(host, 1, fighter, fighter, stage)

        def step(p1=(), p2=()):
            nonlocal old_vram, max_dma
            before = sample(host)
            host.run(1, p1=p1, p2=p2)
            s = sample(host)
            runner.inspect(host, s, list(p1), list(p2))
            vram = C.string_at(host.core.retro_get_memory_data(3)+0xc000, 10240)
            if old_vram is not None:
                changed = [sum(a != b for a, b in zip(old_vram[p*5120:(p+1)*5120],
                                                    vram[p*5120:(p+1)*5120])) for p in (0, 1)]
                max_dma = max(max_dma, sum(changed))
                if sum(bool(n) for n in changed) > 1 or sum(changed) > 3840:
                    failures.append({'kind': 'actor_dma', 'changed': changed, 'callback': len(rows)+1})
            old_vram = vram
            deltas = {name: (s[name]-before[name]) & 65535
                      for name in ('native_frame', 'frame', 'lag_frame_counter', 'snes_vblank_count')}
            if deltas != {'native_frame': 1, 'frame': 1, 'lag_frame_counter': 0, 'snes_vblank_count': 1}:
                failures.append({'kind': 'direct_cadence', 'callback': len(rows)+1,
                                 'deltas': deltas, 'before': before, 'after': s})
            rows.append(s)
            keys = [list(p1), list(p2)]
            if controls and controls[-1]['keys'] == keys:
                controls[-1]['callbacks'] += 1
            else:
                controls.append({'at_callback': len(rows), 'callbacks': 1, 'keys': keys})
            return s

        # Exact root Rig: its initial step, settle's two neutral callbacks,
        # David's 94 forward callbacks, then two neutral position callbacks.
        for _ in range(3):
            step()
        for _ in range(300):
            s = host.state()
            if abs(abs(s['x1']-s['x2'])/16-29) < 1.35:
                break
            keys = ('right',) if not port else ('left',)
            step(keys if not port else (), keys if port else ())
        else:
            raise AssertionError('controller positioning exceeded bound')
        for _ in range(2+phase):
            step()
        before = sample(host)
        contact_start = len(rows)
        step((key,), (key,))
        for _ in range(60):
            step()
        outcome = sample(host)
        if outcome['hp1'] == before['hp1'] or outcome['hp2'] == before['hp2']:
            failures.append({'kind': 'missing_symmetric_contact', 'before': before, 'after': outcome})
        if args.core == 'accuracy':
            arrays = {k: getattr(runner, k) for k in ('cadence_failures', 'native_timing_failures',
                      'ambient_failures', 'overflow_frames', 'spc_fifo_failures')}
            video_ok = (host.width, host.height, host.pitch) == (512, 224, 2048)
            pcm_ok = host.audio_samples > 0 and host.audio_energy > 0 and host.audio_peak < 32767
            budget = dict(arrays, status='passed' if not any(arrays.values()) and video_ok and pcm_ok else 'failed',
                          video=host.video_contract(), pcm_samples=host.audio_samples, pcm_peak=host.audio_peak,
                          pcm_energy=host.audio_energy, max_spc_backlog=runner.max_spc_backlog,
                          max_oam_sprites=runner.max_oam_sprites, max_oam_visible=runner.max_oam_visible)
        else:
            try:
                budget = runner.result(host, time.monotonic()-started)
            except AssertionError as error:
                budget = {'status': 'failed', 'error': repr(error)}
        return {'fighter': fighter, 'stage': stage, 'phase': phase, 'key': key, 'approach_port': port,
                'status': 'failed' if failures or budget['status'] != 'passed' else 'passed',
                'callbacks': len(rows), 'contact_start': contact_start, 'position': before,
                'outcome': outcome, 'failures': failures, 'native': budget,
                'max_changed_actor_bytes': max_dma, 'controller_runs': controls, 'rows': rows}
    finally:
        host.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, default=ROOT/'dist/abaqus-after-hours.sfc')
    parser.add_argument('--symbols', type=Path, default=ROOT/'dist/abaqus-after-hours.sym')
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--observe', action='store_true')
    parser.add_argument('--matrix', action='store_true')
    parser.add_argument('--core', choices=('snes9x', 'accuracy'), default='snes9x')
    parser.add_argument('--fighters', type=int, nargs='+', choices=range(12))
    parser.add_argument('--keys', nargs='+', choices=('y', 'x', 'a'), default=['y', 'x', 'a'])
    parser.add_argument('--ports', type=int, nargs='+', choices=(0, 1), default=[0, 1])
    parser.add_argument('--phases', type=int, nargs='+', choices=(0, 1, 2), default=[0, 1, 2])
    parser.add_argument('--stages', type=int, nargs='+', choices=(0, 1, 2))
    parser.add_argument('--summarize', type=Path, nargs=2, metavar=('BEFORE', 'AFTER'))
    parser.add_argument('--baseline-symbols', type=Path, default=ROOT/'build/contact-timing/before/abaqus-after-hours.sym')
    parser.add_argument('--base-commit', default='14f4fd6')
    args = parser.parse_args()
    if args.summarize:
        before, after = [json.loads(p.read_text()) for p in args.summarize]
        comparison = compare_reports(before, after)
        passed = comparison['status'] == 'passed' and after['status'] == 'passed'
        report = {'status': 'passed' if passed else 'failed', 'comparison': comparison, 'contracts': static_contract(args),
                  'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
                  'rom_sha256': digest(args.rom), 'driver_sha256': digest(__file__),
                  'evidence': [{'path': str(p), 'sha256': digest(p)} for p in args.summarize]}
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps({'status': report['status'], 'compared_ticks': comparison['compared_logical_ticks']}))
        return int(report['status'] != 'passed')
    if args.core == 'accuracy':
        compat.ROM_PATH = args.rom
        compat.MANIFEST_PATH = args.rom.parent/'manifest.json'
        core = compat.verify_manifest_and_pinned_core()
    else:
        core = core_identity()
    report = {'host': host_contract(), 'core': core, 'engine': args.core, 'rom_sha256': digest(args.rom),
              'symbols_sha256': digest(args.symbols), 'command': [sys.executable, *sys.argv],
              'driver_sha256': digest(__file__), 'dependencies_start': dependencies(),
              'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
              'final_certification': False, 'cases': []}
    if args.matrix:
        cases = [(f, stage, phase, key, port) for f in (args.fighters or range(12))
                 for key in args.keys for port in args.ports for phase in args.phases
                 for stage in (args.stages or [(f+phase)%3])]
    else:
        cases = [(5, 2, 0, 'y', 0)]
    try:
        for case in cases:
            result = run_case(args, *case)
            report['cases'].append(result)
            print(json.dumps({k: result[k] for k in ('fighter', 'stage', 'phase', 'key', 'approach_port', 'status', 'callbacks')}), flush=True)
        report['status'] = 'passed' if all(c['status'] == 'passed' for c in report['cases']) else 'failed'
    except Exception as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        report['dependencies_end'] = dependencies()
        report['dependencies_stable'] = report['dependencies_start'] == report['dependencies_end']
        if not report['dependencies_stable']:
            report['status'] = 'stale-dependencies'
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2)+'\n')
    return int(report['status'] != 'passed' and not args.observe)


if __name__ == '__main__':
    raise SystemExit(main())
