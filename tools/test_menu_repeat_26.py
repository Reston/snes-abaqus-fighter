"""Controller-only proof of delayed directional repeat and single menu actions."""
import ctypes as C
import hashlib
import json
from pathlib import Path
import re
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emulator import Emulator, ROOT
from play_flow_media import inventory as media_inventory
import test_inputs as inputs
from test_play_flow_26 import source_hashes
from test_champion import host_contract
from release_evidence import EXPECTED_NATIVE_CORE
from test_arena_preview_26 import AccuracyAdapter
import test_compatibility as compatibility

CHECKS = []
CORE = 'snes9x'
SYMS = {name: int(address, 16) & 0x1ffff for address, name in re.findall(
    r'^([0-9a-fA-F]{8}) (\S+)$', (ROOT / 'dist/abaqus-after-hours.sym').read_text(), re.M)}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(ok, label, details=None):
    CHECKS.append({'check': label, 'passed': bool(ok), 'details': details})
    if not ok:
        raise AssertionError((label, details))


def read(e, name):
    return C.string_at(e.ram + SYMS[name], 1)[0]


def repeat_state(e):
    return list(C.string_at(e.ram + SYMS['stageDepthTable'] + 1, 2))


def hold(e, field, key, port, interval, count, delta):
    e.run(10)
    before = read(e, field)
    rows, events, frames = [], [], []
    previous_timer = None
    for callback in range(84):
        prior = read(e, field)
        e.run(1, **{'p1' if port == 0 else 'p2': [key]})
        current = read(e, field)
        signature, timer = repeat_state(e)
        changed = current != prior
        rows.append({'callback': callback + 1, 'value': current, 'signature': signature, 'timer': timer})
        if changed:
            require(current == (prior + delta) % count, 'held direction advances exactly one menu item', [field, port, prior, current])
            events.append(callback + 1)
        if callback == 0:
            require(changed and timer == 24, 'fresh direction acts immediately and arms a 24-tick delay', [field, port, rows[-1]])
        elif previous_timer is not None:
            if previous_timer > 1:
                require(timer in (previous_timer, previous_timer - 1) and not changed,
                        'held direction waits through the exact native countdown', [field, port, previous_timer, rows[-1]])
            elif previous_timer == 1:
                require((timer == 1 and not changed) or (timer == interval and changed),
                        'repeat fires only when its countdown expires', [field, port, previous_timer, rows[-1]])
            elif previous_timer == interval:
                require(timer in (interval, interval - 1), 'repeat interval rearms deterministically', rows[-1])
        previous_timer = timer
        if field == 'selected' and port == 0:
            frames.append(e.frame.copy())
    require(len(events) >= 5 and events[1] - events[0] >= 24 and
            all(b - a >= interval for a, b in zip(events[1:], events[2:])),
            'repeat has a deliberate initial delay and slower bounded menu cadence', [field, port, interval, events])
    e.run(4)
    require(repeat_state(e) == [0, 0], 'releasing menu directions clears repeat ownership', field)
    if frames:
        path = ROOT / f'docs/screenshots/play-flow-v026/roster-hold-{CORE}.gif'
        selected = frames[::3]
        selected[0].save(path, save_all=True, append_images=selected[1:], duration=50, loop=0, disposal=2)
    return {'field': field, 'port': port, 'interval_ticks': interval, 'events_at_callbacks': events,
            'start': before, 'end': read(e, field), 'observations': rows}


def run_cases():
    rows = []
    e = inputs.menu_title()
    try:
        rows.append(hold(e, 'menu', 'down', 0, 12, 3, 1))
    finally:
        e.close()
    e = inputs.menu_title()
    try:
        inputs.menu_select(e, 1)
        rows.append(hold(e, 'selected', 'right', 0, 8, 12, 1))
        inputs.menu_press(e, ['a'])
        require(read(e, 'selectPlayer') == 1 and repeat_state(e) == [0, 0],
                'roster owner change resets the held-repeat delay')
        rows.append(hold(e, 'selected2', 'left', 1, 8, 12, -1))
        # Both participating pads must agree before a held repeat can occur.
        e.run(3, p1=['right'])
        prior = read(e, 'selected2')
        e.run(40, p1=['right'], p2=['left'])
        require(read(e, 'selected2') == prior and repeat_state(e) == [0, 0],
                'opposite directions across pads suppress both edges and repeats')
        e.run(12, p1=['right'])
        require(read(e, 'selected2') == prior, 'releasing one opposite rearms a full delay without inventing an edge')
        e.run(20, p1=['right'])
        require(read(e, 'selected2') == (prior + 1) % 12, 'a remaining held direction eventually repeats after cancellation')
    finally:
        e.close()
    for port in (0, 1):
        e = inputs.menu_title()
        try:
            inputs.menu_arena(e, 1)
            rows.append(hold(e, 'arena', 'down', port, 12, 3, 1))
        finally:
            e.close()
    e = inputs.menu_title()
    try:
        e.run(100, p2=['down'])
        require(read(e, 'menu') == 0 and repeat_state(e) == [0, 0], 'P2 held title input does not gain menu ownership')
        inputs.menu_press(e, ['down'])
        require(read(e, 'menu') == 1, 'confirm-hold fixture selects Local Versus before testing both roster steps')
        e.run(100, p1=['a'])
        require(inputs.native_screen(e) == 1 and read(e, 'selectPlayer') == 0,
                'held confirm enters P1 selection exactly once')
        e.run(5)
        e.run(100, p1=['a'])
        require(inputs.native_screen(e) == 1 and read(e, 'selectPlayer') == 1,
                'held confirm enters P2 selection exactly once')
    finally:
        e.close()
    e = inputs.menu_title()
    try:
        inputs.menu_arena(e, 1)
        e.run(100, p2=['b'])
        require(inputs.native_screen(e) == 1 and read(e, 'selectPlayer') == 0,
                'held back leaves the arena once without backing out of the roster again')
    finally:
        e.close()
    e = inputs.menu_title()
    try:
        inputs.menu_arena(e, 1)
        e.run(200, p2=['start', 'a'])
        s = inputs.trace(e)
        require(inputs.native_screen(e) == 3 and not s['paused'] and s['round'] == 1 and
                s['action1'] == s['action2'] == 0,
                'held confirm neither pauses nor becomes an opening attack after loading')
        require(repeat_state(e) == [0, 0], 'menu-only reserved bytes are clear throughout native combat')
    finally:
        e.close()
    return rows


def main():
    global CORE
    started = time.monotonic()
    before = source_hashes()
    manifest = json.loads((ROOT / 'dist/manifest.json').read_bytes())
    report = {'status': 'failed', 'version': manifest['version'], 'rom_sha256': manifest['sha256'],
              'source_sha256': before, 'checks': CHECKS, 'host_contract': host_contract(),
              'controller_only': True, 'memory_writes': False, 'save_states': False}
    try:
        require(sha((ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()) == manifest['sha256'], 'repeat proof uses the exact current cartridge')
        require(sha((ROOT / '.tools/core/snes9x_libretro.dll').read_bytes()).lower() == EXPECTED_NATIVE_CORE['dll_sha256'].lower(),
                'repeat proof uses the actual pinned native core')
        report['cases'] = {'snes9x': run_cases()}
        report['independent_core'] = compatibility.verify_manifest_and_pinned_core()
        original = inputs.Emulator
        try:
            CORE = 'accuracy'
            inputs.Emulator = lambda **kwargs: AccuracyAdapter()
            report['cases']['accuracy'] = run_cases()
        finally:
            inputs.Emulator = original
        require(source_hashes() == before, 'menu-repeat production and harness inputs remain fixed')
        report['captures'] = media_inventory(ROOT, 'repeat')
        report['status'] = 'passed'
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        report['check_count'] = len(CHECKS)
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
        (ROOT / 'docs/play-flow-v026-repeat-report.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
        print(json.dumps({k: report[k] for k in ('status', 'check_count', 'elapsed_seconds')}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
