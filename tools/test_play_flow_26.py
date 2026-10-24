"""Silent controller-only proof for the v0.26 play-flow polish passes."""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emulator import Emulator, ROOT
import test_inputs as inputs
import test_presentation as presentation
from test_champion import host_contract
from release_evidence import EXPECTED_NATIVE_CORE

BASE = '7ba40c106000b2b2eb916f6b35d47065334dd4c7'
CHECKS = []
OUT = ROOT / 'docs/screenshots/play-flow-v026'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(ok, label, details=None):
    CHECKS.append({'check': label, 'passed': bool(ok), 'details': details})
    if not ok:
        raise AssertionError((label, details))


def source_hashes():
    return {p.relative_to(ROOT).as_posix(): sha(p.read_bytes().replace(b'\r\n', b'\n'))
            for folder in ('src', 'tools') for p in sorted((ROOT / folder).iterdir())
            if p.suffix in ('.py', '.c', '.h', '.asm')}


def earn_result(winner_side):
    """Earn a real two-round mirror-match victory without changing memory."""
    e = inputs.boot(1, fighter=0, fighter2=0)
    side, other = str(winner_side + 1), str(2 - winner_side)
    port = 'p1' if winner_side == 0 else 'p2'
    for _ in range(12000):
        s = inputs.trace(e)
        if inputs.native_screen(e) == 4:
            e.run(30)
            require(s['mode'] == 1, 'result belongs to local versus', s['mode'])
            s = inputs.trace(e)
            require(s['wins' + side] == 2 and s['wins' + other] == 0,
                    'winner earns the displayed 2-0 result', [winner_side, s])
            return e
        if s['intro'] or s['round_end'] or s['hitstop']:
            e.run(1)
            continue
        delta = inputs.signed16(s['x' + other]) - inputs.signed16(s['x' + side])
        forward = 'right' if delta > 0 else 'left'
        if s['action' + side] or s['hurt' + side] or s['down_state' + side]:
            e.run(1)
        elif abs(delta) > 29 * 16:
            e.run(1, **{port: [forward]})
        else:
            e.run(1, **{port: ['x']})
            e.run(1)
    last = inputs.trace(e)
    e.close()
    raise AssertionError(('controller-only victory did not finish', last))


def result_routes():
    routes = (
        ('p1-a', ['a'], [], 3), ('p2-a', [], ['a'], 3),
        ('p1-start', ['start'], [], 3), ('p2-start', [], ['start'], 3),
        ('p1-back', ['b'], [], 1), ('p2-back', [], ['b'], 1),
        ('p2-start-over-p1-back', ['b'], ['start'], 3),
        ('p1-start-over-p2-back', ['start'], ['b'], 3),
        ('p2-back-over-p1-a', ['a'], ['b'], 1),
        ('p1-back-over-p2-a', ['b'], ['a'], 1),
    )
    rows = []
    for winner in (0, 1):
        for index, (name, p1, p2, target) in enumerate(routes):
            e = earn_result(winner)
            try:
                if index == 0:
                    before = len(presentation.checks)
                    presentation.verify_result_font_bank(e, inputs.trace(e))
                    presentation.verify_result_score(e, winner)
                    require(all(r['passed'] for r in presentation.checks[before:]),
                            'actual result PPU text identifies the winning port and both-pad controls', winner)
                    path = OUT / f'result-p{winner + 1}-mirror.png'
                    e.frame.save(path)
                    rows.append({'winner': winner, 'capture': path.relative_to(ROOT).as_posix(),
                                 'capture_sha256': sha(path.read_bytes())})
                e.run(60)
                require(inputs.native_screen(e) == 4, 'quiet result waits for a deliberate command')
                e.run(1, p1=p1, p2=p2)
                require(inputs.native_screen(e) == target,
                        'either-pad result action applies on its first native sample', [winner, name, target])
                e.run(45)
                s = inputs.trace(e)
                require(s['screen'] == target, 'result destination is published without a second action', [name, s])
                if target == 3:
                    require(s['wins1'] == s['wins2'] == 0 and s['round'] == 1,
                            'rematch clears both scores and starts round one', name)
                    require(s['fighter_id1'] == s['fighter_id2'] == 0 and s['arena'] == 0,
                            'rematch retains the chosen fighters and arena', name)
                else:
                    require(s['mode'] == 1 and s['selected'] == s['selected2'] == 0,
                            'back returns to the same local roster choices', name)
                rows.append({'winner': winner, 'route': name, 'target': target, 'passed': True})
            finally:
                e.close()
            print(json.dumps({'part': 'results', 'winner': winner, 'route': name, 'status': 'passed'}), flush=True)
    e = inputs.menu_title()
    try:
        for keys in (['a'], ['start'], ['b'], ['down']):
            inputs.menu_press(e, keys, port=1)
            require(inputs.native_screen(e) == 0 and inputs.trace(e)['mode'] == 0,
                    'P2 result ownership does not leak to the title', keys)
    finally:
        e.close()
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--part', choices=('results',), required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    path = ROOT / (args.report or Path(f'docs/play-flow-v026-{args.part}-report.json'))
    path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    manifest = json.loads((ROOT / 'dist/manifest.json').read_bytes())
    before = source_hashes()
    report = {'status': 'failed', 'version': manifest['version'], 'rom_sha256': manifest['sha256'],
              'part': args.part, 'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'source_sha256': before, 'host_contract': host_contract(), 'checks': CHECKS,
              'controller_only': True, 'memory_writes': False, 'save_states': False}
    try:
        require(sha((ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()) == manifest['sha256'],
                'proof uses the exact current cartridge')
        require(sha((ROOT / '.tools/core/snes9x_libretro.dll').read_bytes()).lower() == EXPECTED_NATIVE_CORE['dll_sha256'].lower(),
                'actual expanded native core matches its pin')
        report['result'] = result_routes()
        require(source_hashes() == before, 'production and harness inputs remain fixed during proof')
        report['status'] = 'passed'
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        report['check_count'] = len(CHECKS)
        report['presentation_checks'] = len(presentation.checks)
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
        path.write_bytes((json.dumps(report, indent=2) + '\n').encode())
        print(json.dumps({k: report[k] for k in ('status', 'part', 'check_count', 'elapsed_seconds')}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
