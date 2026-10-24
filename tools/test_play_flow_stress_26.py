"""Strict simultaneous-special regression using the retained native producer.

Current candidate cadence is never collapsed. Independent shards retain one
complete report/stream per case so an interrupted worker can resume safely.
This is a native-health proof, not a baseline byte-equivalence claim.
"""
import argparse
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emulator import ROOT
from candidate_sources import snapshot
from release_evidence import EXPECTED_NATIVE_CORE
from test_champion import host_contract
from test_special_24_timing import run_case
from test_endurance import core_identity

KEYS = ('fighter', 'stage', 'phase', 'approach_port', 'spacing')
ALL = list(itertools.product(range(12), range(3), range(3), range(2), ('wide', 'close')))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(ok, label):
    if not ok:
        raise RuntimeError(label)


def write(path, value):
    raw = (json.dumps(value, indent=2) + '\n').encode()
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_bytes(raw)
    temporary.replace(path)


def validate_case(row, signature, identity):
    require(tuple(row[k] for k in KEYS) == identity and row.get('source_signature') == signature, 'Stress case identity/source differs')
    require(row.get('status') == 'passed' and not row.get('failures') and row.get('sdk_lag_increments') == 0 and
            row.get('callbacks', 0) > 0 and row.get('max_changed_actor_bytes', 99999) <= 3840 and
            row.get('peak_spc_backlog', 255) <= 6 and row.get('pcm_samples', 0) > 0 and 0 < row.get('pcm_peak', 32767) < 32767,
            'Strict current-candidate native stress failure: ' + str(identity))
    path = (ROOT / row['retained_stream']).resolve()
    require(path.is_relative_to(ROOT / 'build') and path.is_file() and sha(path.read_bytes()) == row['stream_sha256'], 'Retained stress stream differs')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fighters', type=int, nargs='+', default=list(range(12)))
    parser.add_argument('--stages', type=int, nargs='+', default=list(range(3)))
    parser.add_argument('--phases', type=int, nargs='+', default=list(range(3)))
    parser.add_argument('--ports', type=int, nargs='+', default=[0, 1])
    parser.add_argument('--spacing', nargs='+', choices=('wide', 'close'), default=['wide', 'close'])
    parser.add_argument('--report', type=Path, default=ROOT / 'docs/play-flow-v026-stress-report.json')
    parser.add_argument('--merge', type=Path, nargs='+')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    args.rom, args.symbols, args.core = ROOT / 'dist/abaqus-after-hours.sfc', ROOT / 'dist/abaqus-after-hours.sym', 'snes9x'
    path = args.report.resolve() if args.report.is_absolute() else (ROOT / args.report).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    selected = list(itertools.product(args.fighters, args.stages, args.phases, args.ports, args.spacing))
    require(len(set(selected)) == len(selected) and all(case in ALL for case in selected), 'Invalid/duplicate native stress selection')
    require(args.merge or selected == ALL or path.is_relative_to(ROOT / 'build'), 'Partial stress selection must remain diagnostic')
    sources = snapshot(ROOT)
    signature = sha(json.dumps(sources, sort_keys=True).encode())
    manifest = json.loads((ROOT / 'dist/manifest.json').read_bytes())
    started = time.monotonic()
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    report = {'status': 'failed', 'version': manifest['version'], 'rom_sha256': manifest['sha256'],
              'symbols_sha256': sha(args.symbols.read_bytes()), 'source_commit': commit, 'source_sha256': sources,
              'source_signature': signature, 'host_contract': host_contract(), 'controller_only': True,
              'memory_writes': False, 'save_states': False, 'candidate_collapsed_callbacks': 0,
              'baseline_byte_equivalence_claimed': False, 'engine': 'snes9x', 'cases': [],
              'diagnostic': selected != ALL and not args.merge,
              'retained_producer': 'tools/test_special_24_timing.py',
              'scope': 'Fresh current-candidate native health only; historical producer baseline comments are not current provenance'}
    try:
        require(manifest['version'] == '0.26.0' and sha(args.rom.read_bytes()) == manifest['sha256'], 'Stress cartridge differs from the current manifest')
        require(sha((ROOT / '.tools/core/snes9x_libretro.dll').read_bytes()).lower() == EXPECTED_NATIVE_CORE['dll_sha256'].lower(), 'Actual expanded stress core differs from the pin')
        report['core'] = core_identity()
        if args.merge:
            merged = {}
            for source in args.merge:
                value = json.loads(source.read_bytes())
                require(value['status'] == 'passed' and value['rom_sha256'] == manifest['sha256'] and
                        value['source_sha256'] == sources and value['source_commit'] == commit, 'Stale/failed stress shard')
                for row in value['cases']:
                    identity = tuple(row[k] for k in KEYS)
                    require(identity not in merged, 'Duplicated stress shard case')
                    validate_case(row, signature, identity)
                    merged[identity] = row
            require(set(merged) == set(ALL), 'Full stress merge needs exactly 432 cases')
            report['cases'] = [merged[identity] for identity in ALL]
        else:
            folder = ROOT / 'build/v026-stress-streams' / (manifest['sha256'][:12] + '-' + signature[:12])
            folder.mkdir(parents=True, exist_ok=True)
            for identity in selected:
                tag = '-'.join(map(str, identity))
                case_path = folder / (tag + '.json')
                if args.resume and case_path.exists():
                    row = json.loads(case_path.read_bytes())
                    validate_case(row, signature, identity)
                else:
                    row = run_case(args, *identity)
                    stream = folder / (tag + '.json.gz')
                    raw = (json.dumps(row.pop('rows'), separators=(',', ':')) + '\n').encode()
                    stream.write_bytes(gzip.compress(raw, mtime=0))
                    row.update(source_signature=signature, retained_stream=stream.relative_to(ROOT).as_posix(),
                               stream_sha256=sha(stream.read_bytes()))
                    write(case_path, row)
                    report['cases'].append(row)
                    validate_case(row, signature, identity)
                    print(json.dumps({k: row[k] for k in (*KEYS, 'status', 'callbacks')}), flush=True)
                    continue
                report['cases'].append(row)
                print(json.dumps({'resumed': tag, 'status': row['status']}), flush=True)
        require(snapshot(ROOT) == sources and sha(args.rom.read_bytes()) == manifest['sha256'] and
                sha(args.symbols.read_bytes()) == report['symbols_sha256'], 'Stress source/artifacts changed during execution')
        require(len(report['cases']) == (len(ALL) if args.merge else len(selected)), 'Stress execution ended before full requested coverage')
        report['callbacks'] = sum(row['callbacks'] for row in report['cases'])
        report['status'] = 'passed'
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
        write(path, report)
        print(json.dumps({k: report[k] for k in ('status', 'elapsed_seconds')}), flush=True)


if __name__ == '__main__':
    main()
