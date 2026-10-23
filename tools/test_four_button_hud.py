"""Native four-face-button, contact-shadow and HUD proof; controller input only."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_characters import boot, state, oam_memory, oam_entry

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/screenshots/four-button-hud'
checks = []


def check(ok, label, details=None):
    checks.append({'check': label, 'passed': bool(ok), 'details': details})
    if not ok:
        raise AssertionError((label, details))


def drive(e, port, keys=(), frames=3):
    e.run(frames, **{f'p{port + 1}': keys})
    return state(e)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / 'dist/manifest.json').read_text())
    report = {'status': 'failed', 'version': manifest['version'],
              'rom_sha256': manifest['sha256'], 'checks': checks,
              'host_contract': {'headless': True, 'controller_only': True,
                                'memory_writes': False, 'save_states': False,
                                'audio_playback': False}, 'captures': []}
    try:
        check(hashlib.sha256((ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()).hexdigest()
              == manifest['sha256'], 'Exact cartridge matches manifest')
        for fighter in range(12):
            e = boot(1, fighter, fighter % 3, fighter)
            try:
                for port in (0, 1):
                    suffix = str(port + 1)
                    for key, action in (('y', 1), ('x', 3), ('b', 4), ('a', 5)):
                        s = drive(e, port, (key,))
                        check(s[f'action{suffix}'] == action,
                              f'Fighter {fighter} P{suffix} {key.upper()} starts action {action}', s)
                        e.run(80)
                    for keys in (('l',), ('r',), ('l', 'r')):
                        samples = [drive(e, port, keys, 1) for _ in range(12)]
                        check(all(not s[f'action{suffix}'] and not s[f'buffered_action{suffix}']
                                  for s in samples),
                              f'Fighter {fighter} P{suffix} shoulders never attack or buffer', keys)
                        e.run(8)
                    s = drive(e, port, ('down', 'a'))
                    check(s[f'action{suffix}'] == 6,
                          f'Fighter {fighter} P{suffix} Down+A is the sweep', s)
                    e.run(85)
                    s = drive(e, port, ('down', 'x'))
                    check(s[f'action{suffix}'] == 8 and s[f'y{suffix}'] != 0,
                          f'Fighter {fighter} P{suffix} Down+X is the uppercut', s)
                    e.run(90)
            finally:
                e.close()
        for stage in range(3):
            e = boot(1, 5, stage, 6)
            try:
                e.run(30)
                s = state(e)
                raw = oam_memory(e)
                for port in (0, 1):
                    center = s[f'x{port + 1}'] >> 4
                    shadows = [oam_entry(raw, 64 + port * 2 + i) for i in (0, 1)]
                    check([v['x'] for v in shadows] == [center - 16, center]
                          and all(v['y'] == 200 and v['tile'] == 430 for v in shadows),
                          f'Stage {stage} P{port + 1} shallow shadow touches floor', shadows)
                path = OUT / f'stage-{stage}-hud.png'
                e.frame.save(path)
                report['captures'].append(str(path.relative_to(ROOT)).replace('\\', '/'))
                e.run(12, p1=['up'])
                raw = oam_memory(e)
                check(all(oam_entry(raw, slot)['y'] == 200 for slot in (64, 65)),
                      f'Stage {stage} jumping shadow stays on the floor')
                e.frame.save(OUT / f'stage-{stage}-jump.png')
            finally:
                e.close()
        e = boot(1, 5, 1, 6)
        try:
            def close_gap():
                for _ in range(180):
                    s = state(e)
                    if abs(s['x1'] - s['x2']) < 30 * 16:
                        e.run(5)
                        return
                    e.run(1, p1=['right' if s['x1'] < s['x2'] else 'left'],
                          p2=['left' if s['x1'] < s['x2'] else 'right'])
                raise AssertionError('Cannot position native HUD contact fixture')

            for _ in range(24):
                if state(e)['wins1']:
                    break
                close_gap()
                e.run(3, p1=['x'])
                e.run(70)
            check(state(e)['wins1'] == 1, 'HUD medal is earned through a real round win', state(e))
            e.run(360)
            for _ in range(30):
                if 0 < state(e)['hp2'] <= 32:
                    break
                close_gap()
                e.run(3, p1=['y'])
                e.run(65)
            s = state(e)
            check(s['wins1'] == 1 and 0 < s['hp2'] <= 32,
                  'Current-round low HP and the earned medal appear together', s)
            path = OUT / 'earned-medal-low-health.png'
            e.frame.save(path)
            report['captures'].append(path.relative_to(ROOT).as_posix())
        finally:
            e.close()
        report['status'] = 'passed'
        report['passed'] = len(checks)
    finally:
        (ROOT / 'docs/four-button-hud-report.json').write_text(
            json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'passed': len(checks),
                      'rom_sha256': manifest['sha256']}))


if __name__ == '__main__':
    main()
