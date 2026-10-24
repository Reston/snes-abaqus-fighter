"""Strict read-only first-publication comparison of native special streams.

Native producer/assertions remain unchanged. Only repeated BASELINE trace
callbacks collapse, deterministically keeping the first coherent publication.
Later straddles remain diagnostic failures; no candidate callback collapses.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import itertools
import json
from pathlib import Path

NATIVE_PRODUCER = '65f6aa8689ad7fa080e428bdf04399113275f04a9b40ff8070bdb80278d283ad'
IDENTITY = ('fighter', 'stage', 'phase', 'approach_port', 'spacing')
STATE = ('fighters_hex', 'waves_hex', 'recoil', 'supers_hex')
COUNTERS = ('frame', 'native_frame', 'lag_frame_counter', 'snes_vblank_count')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_stream(case):
    path = Path(case['stream'])
    if sha(path) != case['stream_sha256']:
        raise AssertionError(('stream hash changed', str(path)))
    with gzip.open(path, 'rt', encoding='utf-8') as source:
        rows = json.load(source)
    if len(rows) != case['callbacks'] or not rows:
        raise AssertionError(('incomplete stream', str(path)))
    for index, row in enumerate(rows, 1):
        trace = bytes.fromhex(row['trace_hex'])
        if (row['callback'] != index or len(bytes.fromhex(row['fighters_hex'])) != 128
                or len(bytes.fromhex(row['waves_hex'])) != 32 or len(trace) != 246
                or int.from_bytes(trace[4:6], 'little') != row['frame']):
            raise AssertionError(('incomplete whole-state/trace row', str(path), index))
    return rows


def compare_case(old, new):
    a, b = load_stream(old), load_stream(new)
    issues, straddles = [], []
    first, kept = {}, []
    for row in a:
        frame = row['frame']
        if frame not in first:
            first[frame] = row
            kept.append(row)
            if row['native_frame'] != frame:
                issues.append(dict(kind='baseline_first_publication_incoherent', callback=row['callback'], frame=frame, native_frame=row['native_frame']))
        elif row['native_frame'] == frame:
            differing = [n for n in STATE if first[frame][n] != row[n]]
            if differing or row['keys'] != first[frame]['keys']:
                issues.append(dict(kind='coherent_baseline_duplicate_changed', callback=row['callback'], frame=frame, fields=differing))
        else:
            straddles.append(dict(status='failed', kind='historical_baseline_publication_straddle',
                callback=row['callback'], frame=frame, native_frame=row['native_frame'],
                first_callback=first[frame]['callback'], compared=False,
                differing_fields=[n for n in STATE if first[frame][n] != row[n]]))
    for previous, current in zip(kept, kept[1:]):
        if (current['frame']-previous['frame']) & 65535 != 1:
            issues.append(dict(kind='baseline_unique_frame_gap', before=previous['frame'], after=current['frame']))
    if new['status'] != 'passed' or new['failures'] or new['sdk_lag_increments']:
        issues.append(dict(kind='candidate_original_native_checks_failed', status=new['status'], failures=new['failures'], sdk_lag_increments=new['sdk_lag_increments']))
    for name, condition in (
        ('actor_dma', 0 <= new['max_changed_actor_bytes'] <= 3840),
        ('spc_backlog', 0 <= new['peak_spc_backlog'] <= 32),
        ('pcm', new['pcm_samples'] > 0 and 0 < new['pcm_peak'] < 32767)):
        if not condition:
            issues.append(dict(kind='candidate_retained_native_metric_failed', metric=name))
    for row in b:
        if row['native_frame'] != row['frame']:
            issues.append(dict(kind='candidate_publication_incoherent', callback=row['callback'], frame=row['frame'], native_frame=row['native_frame']))
    for previous, current in zip(b, b[1:]):
        delta = {n:(current[n]-previous[n]) & 65535 for n in COUNTERS}
        if delta != dict(frame=1, native_frame=1, lag_frame_counter=0, snes_vblank_count=1):
            issues.append(dict(kind='candidate_direct_counter_failure', callback=current['callback'], deltas=delta))
    frames_equal = [r['frame'] for r in kept] == [r['frame'] for r in b]
    if not frames_equal:
        issues.append(dict(kind='ordered_complete_frame_sets_differ', baseline=[r['frame'] for r in kept], candidate=[r['frame'] for r in b]))
    differences = []
    if frames_equal:
        for old_row, new_row in zip(kept, b, strict=True):
            if old_row['keys'] != new_row['keys'] or old_row['label'] != new_row['label']:
                issues.append(dict(kind='logical_input_or_segment_differs', frame=new_row['frame'], baseline_keys=old_row['keys'], candidate_keys=new_row['keys'], baseline_label=old_row['label'], candidate_label=new_row['label']))
            fields = {n:[old_row[n],new_row[n]] for n in STATE if old_row[n] != new_row[n]}
            if fields:
                differences.append(dict(frame=new_row['frame'], fields=fields))
    return dict(**{n:new[n] for n in IDENTITY}, status='failed' if issues or differences else 'passed',
        baseline_callbacks=len(a), baseline_repeated_callbacks=len(a)-len(kept), candidate_callbacks=len(b),
        candidate_collapsed_callbacks=0, logical_ticks=len(b), ordered_complete_frame_sets_equal=frames_equal,
        issues=issues, differences=differences, historical_baseline_straddles=straddles,
        baseline_stream_sha256=old['stream_sha256'], candidate_stream_sha256=new['stream_sha256'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--expected-cases', type=int, default=432)
    args = parser.parse_args()
    before, after = [json.loads(path.read_text()) for path in (args.baseline,args.candidate)]
    issues = []
    old_ids = [tuple(c[n] for n in IDENTITY) for c in before['cases']]
    new_ids = [tuple(c[n] for n in IDENTITY) for c in after['cases']]
    if len(old_ids) != args.expected_cases or old_ids != new_ids or len(set(new_ids)) != len(new_ids):
        raise AssertionError('case identity/count/order differs')
    if args.expected_cases == 432 and new_ids != list(itertools.product(range(12),range(3),range(3),range(2),('wide','close'))):
        raise AssertionError('incomplete Cartesian roster/stage/offset/port/spacing matrix')
    if before['producer_sha256'] != NATIVE_PRODUCER or after['producer_sha256'] != NATIVE_PRODUCER:
        raise AssertionError('native producer changed')
    if after['status'] != 'passed':
        issues.append(dict(kind='candidate_native_aggregate_failed', status=after['status']))
    cases = [compare_case(a,b) for a,b in zip(before['cases'],after['cases'],strict=True)]
    report = dict(status='failed' if issues or any(c['status'] != 'passed' for c in cases) else 'passed',
        version='0.24.0', rom_sha256=after['rom_sha256'], producer_sha256=sha(__file__),
        native_producer_sha256=NATIVE_PRODUCER,
        policy='Deterministic FIRST baseline callback per trace frame, requiring Trace==Native. Coherent duplicates must have identical unmasked state/input; later incoherent straddles remain historical diagnostic failures. Candidate callbacks never collapse; full ordered frames/inputs/segments must match exactly.',
        authorization='Parent explicitly approved first-publication correction after all432 baseline control inventory:118 repeats, zero incoherent first publications,12 later state-changing straddles. Original last-policy comparison and native failures remain retained.',
        whole_state_fields=list(STATE), fighter_bytes=128, wave_bytes=32, normalization=False,
        issues=issues, cases=cases, case_count=len(cases), logical_ticks=sum(c['logical_ticks'] for c in cases),
        baseline_repeated_callbacks=sum(c['baseline_repeated_callbacks'] for c in cases), candidate_collapsed_callbacks=0,
        historical_baseline_diagnostics=dict(status='failed' if any(c['historical_baseline_straddles'] for c in cases) else 'passed',
            included_in_candidate_gate=False, straddles=sum(len(c['historical_baseline_straddles']) for c in cases),
            baseline_native_status=before['status']),
        evidence=[dict(path=str(path.resolve()),sha256=sha(path)) for path in (args.baseline,args.candidate)],
        final_combined_certification=False)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({n:report[n] for n in ('status','case_count','logical_ticks','baseline_repeated_callbacks')}))
    return int(report['status'] != 'passed')


if __name__ == '__main__':
    raise SystemExit(main())
