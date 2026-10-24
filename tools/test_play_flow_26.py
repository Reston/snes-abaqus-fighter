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
import test_training as training

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


def training_drills():
    import test_pacing_floor_25 as monitor
    import re
    addresses = {name: int(address, 16) & 0x1ffff for address, name in re.findall(
        r'^([0-9a-fA-F]{8}) (\S+)$', (ROOT / 'dist/abaqus-after-hours.sym').read_text(), re.M)}
    read = lambda e, name: C.string_at(e.ram + addresses[name], 1)[0]
    original = Emulator.run

    def singles(e, count=1, *args, **kwargs):
        for _ in range(count):
            s = monitor.monitored_run(e, 1, *args, **kwargs)
        return s if count else e.state()

    Emulator.run = singles
    rows = []
    try:
        for fighter in range(12):
            e = inputs.boot(2, fighter=fighter, fighter2=fighter, difficulty=2)
            try:
                e.run(24, p1=['right'])
                moved = inputs.trace(e)['x1']
                inputs.press(e, 'start')
                e.run(4, p1=['x'])
                e.run(4)
                require(inputs.trace(e)['x1'] == moved and read(e, 'paused') == 1,
                        'X on ordinary PAUSED does not reset the fight', fighter)
                for _ in range(3):
                    inputs.press(e, 'select')
                require(read(e, 'pausePage') == 3, 'Training Tools is reached through the existing page cycle', fighter)
                text = training.decode_text(presentation.vram_bytes(e), 11, 12).strip()
                require(text == 'X: RESTART DRILL', 'restart command is present in actual native guide glyphs', text)
                for port in (0, 1):
                    for challenge in (1, 2, 0):
                        prior = inputs.trace(e)
                        inputs.press(e, 'down', port)
                        s = training.public_state(e)
                        expected_dummy = 4 if challenge == 1 else 0
                        require(read(e, 'trainingChallenge') == challenge and s['training_dummy'] == expected_dummy,
                                'choosing a drill prepares its required CPU or Stand dummy', [fighter, port, challenge, s['training_dummy']])
                        require(s['paused'] == 1 and s['x1'] == prior['x1'] and s['x2'] == prior['x2'],
                                'choosing a drill leaves the frozen position intact', [fighter, port, challenge])
                        inputs.press(e, 'x', port)
                        e.run(8)
                        s = training.public_state(e)
                        require(s['paused'] == 1 and s['pause_page'] == 3 and s['guide_build'] == s['guide_dirty'] == 0,
                                'restart stays on the settled frozen Training guide', [fighter, port, challenge, s])
                        require([s[k] for k in ('x1', 'x2', 'y1', 'y2', 'hp1', 'hp2', 'energy1', 'energy2')] ==
                                [66 * 16, 190 * 16, 0, 0, 128, 128, 64, 64],
                                'restart restores real positions health and energy', [fighter, port, challenge, s])
                        require(read(e, 'trainingChallenge') == challenge and read(e, 'trainingResult') == 0 and
                                s['training_dummy'] == expected_dummy and read(e, 'difficulty') == 2,
                                'restart retains the drill and difficulty and clears its progress', [fighter, port, challenge])
                        require(read(e, 'trainingHits') == 0 and read(e, 'trainingDamage') == 0 and
                                C.string_at(e.ram + addresses['trainingHistory'], 10) == bytes(10),
                                'restart clears combo statistics and input history', [fighter, port, challenge])
                        require(s['screen'] == 3 and s['intro'] == s['hitstop'] == 0,
                                'restart uses no scene load or countdown', [fighter, port, challenge])
                        rows.append({'fighter': fighter, 'port': port, 'challenge': challenge, 'dummy': expected_dummy, 'passed': True})
                        if fighter == 0 and port == 0:
                            path = OUT / f'training-drill-{challenge + 1}.png'
                            e.frame.save(path)
                # Start remains the owner of a simultaneous restart sample.
                e.run(1, p1=['start'], p2=['x'])
                e.run(20)
                require(read(e, 'paused') == 0 and read(e, 'pausePage') == 0,
                        'Start from either pad beats a simultaneous drill restart', fighter)
            finally:
                e.close()
            print(json.dumps({'part': 'training', 'fighter': fighter, 'status': 'passed'}), flush=True)
        require(not monitor.HEALTH['failures'], 'guide restarts preserve strict native cadence audio and OBJ budgets', monitor.HEALTH)
        return {'cases': rows, 'native_health': monitor.HEALTH,
                'native_checks': list(monitor.CHECKS.values())}
    finally:
        Emulator.run = original


def meter_feedback():
    import test_pacing_floor_25 as monitor
    original = Emulator.run

    def singles(e, count=1, *args, **kwargs):
        for _ in range(count):
            s = monitor.monitored_run(e, 1, *args, **kwargs)
        return s if count else e.state()

    def verify(e, full, label):
        # TRACE is published before the serialized HUD DMA. Observe its
        # actual bounded publication rather than comparing yesterday's PPU.
        for settled in range(5):
            s = inputs.trace(e)
            memory = presentation.vram_bytes(e)
            ready = all([inputs.bg2_tile(memory, (30 - i) if port else (1 + i), 3) for i in range(12)] ==
                        inputs.status_bar_expected(s[f'energy{port + 1}'], 12, inputs.ENERGY_TILE,
                                                   inputs.P2_STATUS_ATTR if port else inputs.P1_STATUS_ATTR, False)
                        for port in (0, 1))
            if ready:
                break
            e.run(1)
        require(ready, 'energy-bar publication settles within four native callbacks', [label, settled])
        memory = presentation.vram_bytes(e)
        for port, x in enumerate((1, 22)):
            expected = [(256 + ord(c)) | 0x2400 for c in 'SUPER Y+B'] if full[port] else [158 | 0x2000] * 9
            actual = [inputs.bg2_tile(memory, x + index, 4) for index in range(9)]
            require(actual == expected, 'native full-meter cue and restored rule match the observed threshold',
                    {'port': port, 'label': label, 'actual': actual, 'expected': expected})
        center = [inputs.bg2_tile(memory, x, 4) for x in range(12, 20)]
        require(center == [(256 + ord(c)) | 0x2000 for c in 'P1 VS P2'],
                'super cues retain the central mode label', center)
        inputs.check_status_bars(e, inputs.trace(e), label)

    rows = []
    Emulator.run = singles
    try:
        for fighter in range(12):
            e = inputs.boot(1, fighter=fighter, fighter2=fighter)
            try:
                e.run(16)
                verify(e, (False, False), 'round start')
                for _ in range(800):
                    s = inputs.trace(e)
                    if s['energy1'] == s['energy2'] == 95:
                        break
                    e.run(1)
                else:
                    raise AssertionError(('natural meter did not reach 95', inputs.trace(e)))
                e.run(3)
                require(inputs.trace(e)['energy1'] == inputs.trace(e)['energy2'] == 95,
                        'threshold-negative frame remains below full gauge', fighter)
                verify(e, (False, False), '95 energy')
                for _ in range(40):
                    if inputs.trace(e)['energy1'] == inputs.trace(e)['energy2'] == 96:
                        break
                    e.run(1)
                e.run(2)
                verify(e, (True, True), '96 energy')
                if fighter == 0:
                    path = OUT / 'super-ready.png'
                    e.frame.save(path)
                # Each controller independently spends its own full gauge.
                e.run(1, p1=['y', 'b'])
                require(inputs.trace(e)['energy1'] == 0 and inputs.trace(e)['energy2'] == 96,
                        'P1 cue corresponds to a real accepted full-gauge command', fighter)
                e.run(16)
                verify(e, (False, True), 'only P1 spent')
                e.run(1, p2=['y', 'b'])
                require(inputs.trace(e)['energy2'] == 0,
                        'P2 cue corresponds to a real accepted full-gauge command', fighter)
                e.run(16)
                verify(e, (False, False), 'both spent')
                e.run(220)
                rows.append({'fighter': fighter, 'ports': [0, 1], 'thresholds': [95, 96, 0], 'passed': True})
            finally:
                e.close()
            print(json.dumps({'part': 'meter', 'fighter': fighter, 'status': 'passed'}), flush=True)
        require(not monitor.HEALTH['failures'], 'meter feedback preserves strict native cadence audio and OBJ budgets', monitor.HEALTH)
        return {'cases': rows, 'native_health': monitor.HEALTH, 'native_checks': list(monitor.CHECKS.values())}
    finally:
        Emulator.run = original


def local_arenas():
    rows = []
    for port in (0, 1):
        for key, destination in (('a', 3), ('start', 3), ('b', 1)):
            e = inputs.menu_title()
            try:
                inputs.menu_arena(e, 1)
                e.run(10)
                text = training.decode_text(presentation.vram_bytes(e), 26, 27).strip()
                require(text == 'LOCAL 1V1: EITHER PAD', 'local arena picker advertises both controllers', text)
                inputs.menu_press(e, ['down'], port)
                require(inputs.trace(e)['arena'] == 1, 'either pad moves the local arena cursor down', port)
                inputs.menu_press(e, ['up'], port)
                require(inputs.trace(e)['arena'] == 0, 'either pad moves the local arena cursor up', port)
                # Opposites across the two participating pads cancel.
                e.run(3, p1=['down'], p2=['up'])
                e.run(10)
                require(inputs.trace(e)['arena'] == 0, 'opposite arena directions cancel across controllers', port)
                # A held opposite also suppresses a new edge on the other pad.
                e.run(3, p1=['up'])
                before = inputs.trace(e)['arena']
                e.run(3, p1=['up'], p2=['down'])
                e.run(10)
                require(inputs.trace(e)['arena'] == before, 'held arena opposite suppresses a newly pressed direction', port)
                inputs.menu_press(e, ['down'], port)
                chosen = inputs.trace(e)['arena']
                inputs.menu_press(e, [key], port)
                require(inputs.native_screen(e) == destination and inputs.trace(e)['screen'] == destination,
                        'either pad can confirm or leave the chosen local arena', [port, key, destination])
                if destination == 3:
                    require(inputs.trace(e)['arena'] == chosen and inputs.trace(e)['round'] == 1,
                            'arena confirmation loads the chosen stage exactly once', [port, key, chosen])
                rows.append({'port': port, 'key': key, 'destination': destination, 'passed': True})
            finally:
                e.close()
    for p1, p2, destination in ((['b'], ['start'], 3), (['start'], ['b'], 3),
                                 (['a'], ['b'], 1), (['b'], ['a'], 1)):
        e = inputs.menu_title()
        try:
            inputs.menu_arena(e, 1)
            e.run(10)
            e.run(1, p1=p1, p2=p2)
            require(inputs.native_screen(e) == destination, 'local arena applies shared Start/B/A priority on its first sample',
                    {'p1': p1, 'p2': p2, 'destination': destination})
            rows.append({'p1': p1, 'p2': p2, 'destination': destination, 'passed': True})
        finally:
            e.close()
    for mode in (0, 2):
        e = inputs.menu_title()
        try:
            inputs.menu_arena(e, mode)
            e.run(10)
            prior = inputs.trace(e)
            for keys in (['down'], ['up'], ['a'], ['start'], ['b']):
                inputs.menu_press(e, keys, port=1)
                s = inputs.trace(e)
                require(s['screen'] == 2 and s['arena'] == prior['arena'],
                        'local arena ownership does not leak into Arcade or Training', [mode, keys, s])
        finally:
            e.close()
    return rows


def arcade_orientation():
    import test_pacing_floor_25 as monitor
    import test_expansion_09_arcade_story as story
    story.SYMBOLS = story.symbols((ROOT / 'dist/abaqus-after-hours.sym').read_bytes())
    original = Emulator.run

    def singles(e, count=1, *args, **kwargs):
        for _ in range(count):
            try:
                s = monitor.monitored_run(e, 1, *args, **kwargs)
            except Exception:
                detail = {'native_screen': inputs.native_screen(e), 'state': inputs.trace(e),
                          'black_ppu': e.frame.getbbox() is None,
                          'native_intro': monitor.read(e, 'intro', 1),
                          'native_round_end': monitor.read(e, 'roundEnd', 1),
                          'health': monitor.HEALTH}
                (ROOT / 'build/v026-arcade-failure-detail.json').write_text(json.dumps(detail, indent=2))
                raise
        return s if count else e.state()

    def text(e, y, x, expected):
        presentation.verify_opaque_text_rows(e, [(y, x, expected)], 'Arcade orientation')
        require(True, 'native Arcade progress/preview glyphs and pixels match the earned route', expected)

    def pause_level(e, level):
        inputs.press(e, 'start')
        e.run(4)
        expected = 'CPU: ' + ('EASY', 'NORMAL', 'HARD')[level]
        text(e, 11, (32 - len(expected)) // 2, expected)
        inputs.press(e, 'start')
        e.run(4)

    rows = []
    Emulator.run = singles
    try:
        e = story.boot(hero=4)
        try:
            pause_level(e, 0)
            for shift in range(11):
                s = inputs.trace(e)
                require(s['arcade'] == shift and s['fighter_id2'] == (5 + shift) % 12,
                        'progress follows the actual eleven-opponent ladder', s)
                text(e, 9, 19, f'SHIFT {shift + 1:02}/11')
                if shift in (0, 9, 10):
                    e.frame.save(OUT / f'arcade-shift-{shift + 1:02}.png')
                story.skip_story(e)
                attempts = []
                for attempt in range(8):
                    story.play_cpu(e)
                    e.run(15)
                    s = inputs.trace(e)
                    attempts.append({'attempt': attempt + 1, 'wins1': s['wins1'], 'wins2': s['wins2']})
                    if s['wins1'] == 2:
                        break
                    text(e, 17, 15, f'SHIFT {shift + 1:02}/11')
                    text(e, 19, 15, 'RETRY')
                    text(e, 19, 21, presentation.NAMES[s['fighter_id2']])
                    inputs.menu_press(e, ['a'])
                    require(inputs.trace(e)['arcade'] == shift, 'losing and continuing retains ladder progress', shift)
                    story.skip_story(e)
                require(s['wins1'] == 2, 'controller-only player earns each progress transition', [shift, attempts])
                if shift == 10:
                    require(s['champion'] == 1, 'eleventh win enters the existing Champion scene', s)
                    presentation.verify_result_font_bank(e, s)
                    break
                text(e, 17, 15, f'SHIFT {shift + 1:02}/11')
                text(e, 19, 15, 'NEXT')
                next_id = (6 + shift) % 12
                text(e, 19, 21, presentation.NAMES[next_id])
                if shift == 0:
                    e.frame.save(OUT / 'arcade-next-opponent.png')
                    for keys in (['a'], ['start'], ['b']):
                        inputs.menu_press(e, keys, port=1)
                        require(inputs.trace(e)['screen'] == 4 and inputs.trace(e)['arcade'] == shift,
                                'P2 local-flow controls do not advance an Arcade result', keys)
                inputs.menu_press(e, ['a'])
                require(inputs.trace(e)['arcade'] == shift + 1 and inputs.trace(e)['fighter_id2'] == next_id,
                        'NEXT preview matches the actual next loaded opponent', [shift, next_id])
                rows.append({'shift': shift + 1, 'opponent': s['fighter_id2'], 'next': next_id, 'attempts': attempts})
                print(json.dumps({'part': 'arcade', 'shift': shift + 1, 'status': 'passed'}), flush=True)
        finally:
            e.close()
        for level in (1, 2):
            e = story.boot(hero=0, difficulty=level)
            try:
                pause_level(e, level)
                if level == 2:
                    story.skip_story(e)
                    for _ in range(18000):
                        if inputs.native_screen(e) == 4:
                            break
                        e.run(1)
                    e.run(30)
                    s = inputs.trace(e)
                    require(s['screen'] == 4 and s['wins2'] == 2 and s['arcade'] == 0,
                            'passive player genuinely loses before retry verification', s)
                    text(e, 17, 15, 'SHIFT 01/11')
                    text(e, 19, 15, 'RETRY')
                    text(e, 19, 21, presentation.NAMES[1])
                    e.frame.save(OUT / 'arcade-retry-opponent.png')
                    inputs.menu_press(e, ['start'])
                    s = inputs.trace(e)
                    require(s['arcade'] == 0 and s['fighter_id2'] == 1 and s['wins1'] == s['wins2'] == 0,
                            'Continue retries the shown opponent and same ladder position', s)
            finally:
                e.close()
        require(not monitor.HEALTH['failures'], 'Arcade orientation retains strict native combat cadence audio and OBJ budgets', monitor.HEALTH)
        return {'ladder': rows, 'native_health': monitor.HEALTH, 'native_checks': list(monitor.CHECKS.values())}
    finally:
        Emulator.run = original


def manual_training():
    import test_pacing_floor_25 as monitor
    original = Emulator.run

    def singles(e, count=1, *args, **kwargs):
        for _ in range(count):
            s = monitor.monitored_run(e, 1, *args, **kwargs)
        return s if count else e.state()

    def recover(e):
        for _ in range(320):
            s = inputs.trace(e)
            if not any(s[k] for k in ('action1', 'action2', 'y1', 'y2', 'hurt1', 'hurt2', 'wave1', 'wave2', 'down_state1', 'down_state2')):
                e.run(3)
                return
            e.run(1)
        raise AssertionError(('manual practice recovery did not finish', s))

    rows = []
    Emulator.run = singles
    try:
        for fighter in range(12):
            e = inputs.boot(2, fighter=fighter, fighter2=fighter, core_options=inputs.MENU_CORE_OPTIONS)
            try:
                start = inputs.trace(e)
                e.run(12, p2=['right', 'x'])
                s = inputs.trace(e)
                require(s['x2'] == start['x2'] and s['action2'] == 0,
                        'default Stand still ignores physical P2 combat input', fighter)
                port = fighter % 2
                inputs.press(e, 'start', port)
                before = inputs.trace(e)
                inputs.press(e, 'x', port)
                e.run(4)
                s = training.public_state(e)
                require(s['paused'] == 1 and s['training_dummy'] == 5 and s['x1'] == before['x1'] and s['x2'] == before['x2'],
                        'either paused controller explicitly enables manual P2 without resetting the fight', [fighter, port, s])
                presentation.verify_opaque_text_rows(e, [(11, 6, 'DUMMY: P2 CONTROLLER')], 'manual Training')
                if fighter == 0:
                    e.frame.save(OUT / 'training-p2-controller.png')
                inputs.press(e, 'start', 1 - port)
                e.run(12, p2=['right'])
                s = inputs.trace(e)
                require(s['x2'] > start['x2'] and s['action1'] == 0,
                        'manual P2 movement follows its real controller independently', [fighter, s])
                stationary = s['x2']
                e.run(8, p2=['left', 'right'])
                require(inputs.trace(e)['x2'] == stationary, 'manual P2 opposing directions cancel', fighter)
                for key, action in (('y', 1), ('x', 3), ('b', 4), ('a', 5)):
                    e.run(1, p2=[key])
                    s = inputs.trace(e)
                    require(s['action2'] == action and s['action1'] == 0,
                            'manual P2 face buttons use the shared four-button commands', [fighter, key, s['action2']])
                    recover(e)
                e.run(1, p2=['down', 'y'])
                s = inputs.trace(e)
                require(s['action2'] == 7, 'manual P2 can execute its ordinary special', fighter)
                recover(e)
                for _ in range(1400):
                    if inputs.trace(e)['energy2'] == 96:
                        break
                    e.run(1)
                e.run(3)
                e.run(1, p2=['y', 'b'])
                s = inputs.trace(e)
                require(s['energy2'] == 0 and s['action2'] == 7,
                        'manual P2 can spend a naturally full super gauge', [fighter, s])
                recover(e)
                inputs.press(e, 'select')
                e.run(30)
                s = training.public_state(e)
                require(s['training_dummy'] == 5 and s['x1'] == 66 * 16 and s['x2'] == 190 * 16 and s['hp1'] == s['hp2'] == 128,
                        'live P1 reset preserves manual practice and restores both fighters', [fighter, s])
                e.run(20, p2=['right'])
                moved = inputs.trace(e)['x2']
                inputs.press(e, 'select', 1)
                require(inputs.trace(e)['x2'] == moved,
                        'live P2 Select does not gain P1 reset ownership in manual practice', fighter)
                inputs.press(e, 'start', 1)
                inputs.press(e, 'x', 1)
                s = training.public_state(e)
                require(s['paused'] == 1 and s['training_dummy'] == 0,
                        'manual toggle returns explicitly to Stand', [fighter, s])
                inputs.press(e, 'start')
                e.run(12, p2=['right', 'x'])
                require(inputs.trace(e)['x2'] == moved and inputs.trace(e)['action2'] == 0,
                        'returning to Stand restores ignored physical P2 combat input', fighter)
                rows.append({'fighter': fighter, 'enable_port': port, 'normal_actions': [1, 3, 4, 5],
                             'special_and_super': True, 'reset_retains_manual': True, 'passed': True})
            finally:
                e.close()
            print(json.dumps({'part': 'manual', 'fighter': fighter, 'status': 'passed'}), flush=True)
        require(not monitor.HEALTH['failures'], 'manual practice preserves strict native cadence audio and OBJ budgets', monitor.HEALTH)
        return {'cases': rows, 'native_health': monitor.HEALTH, 'native_checks': list(monitor.CHECKS.values())}
    finally:
        Emulator.run = original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--part', choices=('results', 'training', 'meter', 'arenas', 'arcade', 'manual'), required=True)
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
        report['result'] = {'results': result_routes, 'training': training_drills, 'meter': meter_feedback,
                            'arenas': local_arenas, 'arcade': arcade_orientation, 'manual': manual_training}[args.part]()
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
