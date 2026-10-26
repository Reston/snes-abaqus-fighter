"""Validate retained native review media; recorded execution remains trusted.

These checks bind the offline companion to its cartridge, helpers, fixed
capture inventory and decoded callback pixels. They do not replay emulation
or constitute human gameplay/balance approval.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import re
from typing import Mapping

from PIL import Image, ImageSequence
from release_evidence import EXPECTED_NATIVE_CORE

NAMES = ('Damian', 'Ivo', 'Cristobal', 'Cote', 'Negger', 'David',
         'Fernando', 'Cristian', 'Madariaga', 'Reston', 'Roxana', 'Lars')
PRACTICE_HELPERS = {'tools/test_crossup_practice.py', 'tools/test_matchups.py',
                    'tools/test_inputs.py', 'tools/emulator.py', 'tools/make_crossup_review.py'}
AI_HELPERS = {'tools/make_cpu_antiair_review.py', 'tools/test_inputs.py',
              'tools/emulator.py', 'tools/make_crossup_review.py'}
TRAINING_HELPERS = {'tools/make_training_cpu_review.py', 'tools/test_training.py',
                    'tools/emulator.py', 'tools/make_crossup_review.py'}


class ReviewError(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise ReviewError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def signed(value):
    return (value+0x8000) % 0x10000-0x8000


def recipe(fighter):
    return {1: ('understep', 24), 3: ('understep', 36), 4: ('understep', 48),
            6: ('understep', 36), 9: ('understep', 24)}.get(fighter, ('neutral', 24))


def review_files(root: Path, version: str) -> dict[str, Path]:
    names = ['CROSSUP-PRACTICE.md', f'CROSSUP-PRACTICE-v{version}.html',
             f'crossup-practice-v{version}.json', f'crossup-practice-captures-v{version}.json',
             'cpu-anti-air-review.json', 'screenshots/cpu-anti-air/hit.gif',
             'screenshots/cpu-anti-air/whiff.gif',
             *(f'screenshots/crossup-practice/v{version}/{fighter:02}.gif' for fighter in range(12))]
    if tuple(map(int, version.split('.'))) >= (0, 17, 0):
        names.extend(('training-cpu-review.json', 'screenshots/training-cpu/practice.gif',
                      'screenshots/training/training-cpu-card.png'))
    return {name: root/'docs'/name for name in names}


def identity(report, root, manifest, helpers):
    need(isinstance(report, Mapping) and report.get('status') == 'passed' and
         report.get('version') == manifest['version'] and report.get('rom_sha256') == manifest['sha256'],
         'Review evidence must identify the current passed cartridge')
    core = root/'.tools/core/snes9x_libretro.dll'
    need(core.is_file() and report.get('core_sha256') == EXPECTED_NATIVE_CORE['dll_sha256'] == digest(core.read_bytes()),
         'Review evidence must use the pinned expanded native core')
    recorded = report.get('harness_sha256')
    need(isinstance(recorded, Mapping) and set(recorded) == helpers and
         all((root/path).is_file() and recorded[path] == digest((root/path).read_bytes()) for path in helpers),
         'Review producer or helper inventory changed')
    host = report.get('host_contract', {})
    cpus = host.get('logical_processors', []) if isinstance(host, Mapping) else []
    need(isinstance(host, Mapping) and host.get('priority_class') == 0x4000 and
         host.get('stdin') == 'DEVNULL' and host.get('controller_only') is True and
         isinstance(cpus, list) and len(cpus) == 2 and all(type(cpu) is int for cpu in cpus) and len(set(cpus)) == 2 and
         all(host.get(key) is False for key in ('gui_opened', 'audio_device_opened', 'audio_playback', 'save_states')) and
         host.get('emulated_memory_writes') == 0 and host.get('sequential_boots') is True and
         host.get('max_active_emulators') == 1, 'Review evidence lost its silent background host contract')


def native_gif(row, root, path):
    need(isinstance(row, Mapping) and row.get('gif') == path, 'Review capture path differs from fixed inventory')
    media = root/path
    need(media.is_file() and row.get('gif_bytes') == media.stat().st_size and
         row.get('gif_sha256') == digest(media.read_bytes()), 'Review GIF bytes changed')
    count, hashes, trace = row.get('frames'), row.get('source_rgb_sha256'), row.get('trace')
    fields = ('frame', 'x1', 'x2', 'y1', 'y2', 'face1', 'face2', 'action1', 'action2',
              'air_action1', 'air_action2', 'connected1', 'connected2', 'hp1', 'hp2',
              'hurt1', 'hurt2', 'guard1', 'guard2', 'down_state1', 'down_state2',
              'anim_tick1', 'anim_tick2', 'hitstop', 'raw_keys1', 'raw_keys2')
    need(type(count) is int and 20 <= count <= 240 and isinstance(hashes, list) and len(hashes) == count and
         all(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) for value in hashes) and
         isinstance(trace, list) and len(trace) == count and
         all(isinstance(state, Mapping) and all(type(state.get(key)) is int for key in fields) for state in trace),
         'Review capture needs bounded callback hashes and complete native telemetry')
    callbacks = row.get('host_video_callback_frames')
    need(isinstance(callbacks, list) and len(callbacks) == count and all(type(value) is int for value in callbacks) and
         callbacks == list(range(callbacks[0], callbacks[0]+count)) and
         row.get('native_frame_numbers') == [state['frame'] for state in trace] and
         all((after['frame']-before['frame']) & 0xffff == 1 for before, after in zip(trace, trace[1:])),
         'Review capture must retain consecutive native video callbacks')
    timing = row.get('gif_timing', {})
    need(isinstance(timing, Mapping) and timing.get('fixed_rate_inspection_sweep') is True and
         timing.get('gif_centisecond_quantization') is True and timing.get('duration_ms_cycle') == [20, 20, 10] and
         timing.get('average_duration_ms') == 50/3, 'Review GIF must disclose approximate inspection timing')
    expected = []
    for index, value in enumerate(hashes):
        duration = (20, 20, 10)[index % 3]
        if expected and expected[-1][0] == value:
            expected[-1][1] += duration
        else:
            expected.append([value, duration])
    try:
        with Image.open(media) as image:
            need(image.format == 'GIF' and image.size == (256, 224) and image.info.get('loop') == 0 and
                 image.n_frames <= count, 'Review GIF must loop at native resolution')
            actual = [[digest(frame.convert('RGB').tobytes()), frame.info.get('duration')]
                      for frame in ImageSequence.Iterator(image)]
    except (OSError, ValueError) as error:
        raise ReviewError(f'Unreadable native GIF: {path}') from error
    need(actual == expected and row.get('decoded_gif_frames') == len(actual),
         'Review GIF pixels or durations differ from the callback record')
    return trace


def validate_practice(proof, media, root, manifest):
    identity(proof, root, manifest, PRACTICE_HELPERS)
    identity(media, root, manifest, PRACTICE_HELPERS | {'tools/make_crossup_practice_review.py'})
    need(proof.get('rom_bytes') == manifest['bytes'] and media.get('native_dimensions') == [256, 224] and
         media.get('unedited_callback_pixels') is True, 'Practice cartridge size or native capture contract differs')
    expected_recipes = {str(f): {'route': recipe(f)[0], 'approach_gap_px': recipe(f)[1]} for f in range(12)}
    need(proof.get('recipes') == expected_recipes, 'Practice recipe inventory changed')
    cases = proof.get('cases')
    need(isinstance(cases, list) and len(cases) == 72 and all(isinstance(row, Mapping) for row in cases),
         'Practice requires all 72 fighter/controller/arena cases')
    by_case = {}
    for row in cases:
        f, p, s = (row.get(key) for key in ('fighter', 'port', 'stage'))
        need(type(f) is type(p) is type(s) is int and f in range(12) and p in (0, 1) and s in range(3),
             'Invalid practice case identity')
        a, d, sign = str(p+1), str(2-p), 1 if p == 0 else -1
        contact, landed = row.get('contact', {}), row.get('landed', {})
        need(row.get('passed') is True and row.get('name') == NAMES[f] and row.get('opponent') == (f+1) % 12 and
             row.get('recipe') == recipe(f)[0] and 0 < row.get('starting_gap_px', 0) <= recipe(f)[1] and
             isinstance(contact, Mapping) and contact.get('action'+a) == 5 and contact.get('air_action'+a) == 1 and
             contact.get('connected'+a) == 2 and signed(contact.get('y'+a, 0)) < 0 and
             0 < (contact.get('x'+a, 0)-contact.get('x'+d, 0))*sign <= 26*16+32 and
             contact.get('hp'+a) == 128 and 0 < contact.get('hp'+d, 128) < 128 and
             row.get('damage') == 128-contact.get('hp'+d, 128) and contact.get('guard'+d) == 0 and
             contact.get('hitstop') == 5 and row.get('hurt_drift_ticks', 0) > 0 and
             isinstance(landed, Mapping) and landed.get('y'+a) == landed.get('air_action'+a) == landed.get('action'+a) == 0 and
             landed.get('face'+a) == int(landed.get('x'+a, 0) < landed.get('x'+d, 0)),
             'Practice case must retain a rear medium-kick hit and completed landing')
        by_case[f, p, s] = row
    need(set(by_case) == {(f, p, s) for f in range(12) for p in (0, 1) for s in range(3)},
         'Practice case inventory contains omissions or duplicates')
    captures = media.get('captures')
    need(isinstance(captures, list) and len(captures) == 12, 'Practice companion requires twelve clips')
    for f, row in enumerate(captures):
        need(isinstance(row, Mapping) and row.get('fighter') == f and row.get('name') == NAMES[f] and
             row.get('stage') == f % 3 and row.get('attacker') == row.get('side') == 'P1' and row.get('defender') == 'P2' and
             row.get('helper') == 'tools/test_crossup_practice.py:practice_case' and
             row.get('helper_parameters') == {'fighter': f, 'port': 0, 'stage': f % 3}, 'Practice clip route changed')
        trace = native_gif(row, root, f"docs/screenshots/crossup-practice/v{manifest['version']}/{f:02}.gif")
        air = [i for i, state in enumerate(trace) if signed(state['y1']) < 0]
        cross = [i for i in air if trace[i]['x1'] > trace[i]['x2']]
        contacts = [i for i, state in enumerate(trace) if state['connected1'] == 2]
        need(air and cross and contacts, 'Practice clip lost its jump-past contact')
        land = [i for i in range(air[0]+1, len(trace)) if trace[i]['y1'] == trace[i]['action1'] == trace[i]['air_action1'] == 0]
        need(land and air[0] < cross[0] <= contacts[0] < land[0], 'Practice clip lost its complete landing')
        landmarks = row.get('proof', {})
        need(isinstance(landmarks, Mapping) and all(landmarks.get('first_'+event+'_clip_frame') == index
             for event, index in (('airborne', air[0]), ('crossed', cross[0]), ('contact', contacts[0]), ('landed', land[0]))) and
             landmarks.get('contact_trace') == trace[contacts[0]] and
             all(by_case[f, 0, f % 3]['contact'].get(key) == value for key, value in trace[contacts[0]].items()),
             'Practice clip landmarks differ from the controller proof')
    page = (root/f"docs/CROSSUP-PRACTICE-v{manifest['version']}.html").read_text(encoding='utf-8')
    match = re.search(r'const clips=(.*?);const choice=', page)
    need(match is not None and manifest['sha256'] in page and 'Cartridge v'+manifest['version'] in page,
         'Practice page lost its cartridge identity or clip inventory')
    try:
        items = json.loads(match[1])
        need(isinstance(items, list) and len(items) == 12, 'Practice page must embed twelve clips')
        for f, (item, row) in enumerate(zip(items, captures)):
            need(isinstance(item, Mapping) and item.get('id') == f and item.get('name') == NAMES[f] and
                 item.get('route') == recipe(f)[0] and item.get('gap') == recipe(f)[1] and
                 item.get('stage') == ('Las Condes', 'El Castillo', 'La Oficina')[f % 3] and
                 item.get('sha256') == row['gif_sha256'] and
                 item.get('src', '').startswith('data:image/gif;base64,') and
                 base64.b64decode(item['src'].split(',', 1)[1], validate=True) == (root/row['gif']).read_bytes(),
                 'Practice page embedded media differs from the retained native clip')
    except (KeyError, TypeError, ValueError) as error:
        raise ReviewError('Invalid practice page embedded clip data') from error


def validate_cpu_review(report, root, manifest):
    identity(report, root, manifest, AI_HELPERS)
    need(report.get('rom_bytes') == manifest['bytes'] and report.get('header_checksum') == manifest['checksum'] and
         report.get('native_dimensions') == [256, 224] and report.get('unedited_callback_pixels') is True and
         report.get('controlled_player') == 1 and report.get('opponent') == 'native CPU', 'CPU capture contract differs')
    checks, captures = report.get('checks'), report.get('captures')
    need(isinstance(checks, list) and len(checks) == 16 and all(isinstance(check, Mapping) and
         check.get('passed') is True and isinstance(check.get('check'), str) and check['check'] for check in checks),
         'CPU capture requires its complete sixteen fixture checks')
    need(isinstance(captures, list) and len(captures) == 2, 'CPU review needs hit and retreat-whiff clips')
    for row, key, fixture in zip(captures, ('hit', 'whiff'), (
            {'cpu_id': 4, 'difficulty': 2, 'title_delay': 0},
            {'cpu_id': 2, 'difficulty': 2, 'title_delay': 11, 'retreat': True, 'kick': False})):
        need(isinstance(row, Mapping) and row.get('key') == key and row.get('fixture') == fixture and
             row.get('expected_hit') is (key == 'hit'), 'CPU review fixture inventory differs')
        trace = native_gif(row, root, f'docs/screenshots/cpu-anti-air/{key}.gif')
        proof = row.get('proof', {})
        index = proof.get('first_uppercut_clip_frame') if isinstance(proof, Mapping) else None
        need(type(index) is int and 1 <= index < len(trace)-13, 'CPU clip lost its startup landmark')
        before, first = trace[index-1], trace[index]
        need(before['action2'] == before['hurt2'] == before['down_state2'] == before['y2'] == before['hitstop'] == 0 and
             before['hp1'] > 0 and before['hp2'] > 0 and before['hurt1'] == before['down_state1'] == 0 and
             -56*16 <= signed(before['y1']) <= -12*16 and abs(before['x1']-before['x2']) < 41*16 and
             int(before['x1'] > before['x2']) == before['face2'] and first['action2'] == 8 and
             first['anim_tick2'] == 1 and first['raw_keys2'] == 1056 and signed(first['y2']) < 0,
             'CPU clip must commit from a visible, available ordinary startup')
        startup = trace[index:index+5]
        need([state['anim_tick2'] for state in startup] == [1, 2, 3, 4, 5] and all(
             state['action2'] == 8 and state['connected2'] == 0 and state['hp1'] == before['hp1'] for state in startup),
             'CPU clip changed the five pre-contact startup ticks')
        contact_index = proof.get('first_contact_clip_frame')
        if key == 'hit':
            need(contact_index == index+5 and trace[contact_index]['anim_tick2'] == 6 and
                 trace[contact_index]['connected2'] == 2 and trace[contact_index]['hp1'] < before['hp1'] and
                 trace[contact_index]['hp2'] == before['hp2'] and signed(trace[contact_index]['y1']) < 0,
                 'CPU hit clip must retain the ordinary sixth-tick airborne contact')
        else:
            active = trace[index+5:index+13]
            need(contact_index is None and [state['anim_tick2'] for state in active] == list(range(6, 14)) and all(
                 state['action2'] == 8 and state['connected2'] == 0 and state['hp1'] == before['hp1'] and
                 abs(state['x1']-state['x2']) > 41*16 for state in active), 'CPU whiff clip must retain all eight missed active ticks')
        result = proof.get('fixture_result', {})
        need(isinstance(result, Mapping) and all(result.get(k) == fixture[k] for k in ('cpu_id', 'difficulty', 'title_delay')),
             'CPU clip fixture identity differs')
        # Fixture snapshots contain a focused subset of the retained telemetry.
        for label, state in (('decision', before), ('first', first),
                             ('contact', trace[contact_index] if contact_index is not None else None)):
            snapshot = result.get(label)
            need((snapshot is None if state is None else isinstance(snapshot, Mapping) and
                  {'frame', 'x1', 'x2', 'y1', 'y2', 'hp1', 'hp2', 'action2', 'anim_tick2'} <= set(snapshot) and
                  all(snapshot[k] == state[k] for k in set(snapshot) & set(state))),
                 'CPU fixture landmark differs from retained native telemetry')


def validate_training_review(report, root, manifest):
    identity(report, root, manifest, TRAINING_HELPERS)
    fixture = {'fighter': 2, 'opponent': 11, 'stage': 2, 'difficulty': 2, 'frames': 180}
    need(report.get('rom_bytes') == manifest['bytes'] and report.get('header_checksum') == manifest['checksum'] and
         report.get('fixture') == fixture and report.get('native_dimensions') == [256, 224] and
         report.get('unedited_callback_pixels') is True and report.get('controlled_player') == 1 and
         report.get('opponent') == 'native CPU', 'CPU Training review contract or fixture differs')
    source = root/'docs/training-test-report.json'
    native = json.loads(source.read_bytes())
    need(native.get('status') == 'passed' and native.get('rom_sha256') == manifest['sha256'] and
         native.get('cpu_training') and report.get('source_report') == 'docs/training-test-report.json' and
         report.get('source_report_comparison') == 'LF-normalized JSON bytes' and
         report.get('source_report_sha256') == digest(source.read_bytes().replace(b'\r\n', b'\n')),
         'CPU Training review must bind the current native Training proof')
    cpu = native['cpu_training']
    play = cpu.get('play', []) if isinstance(cpu, Mapping) else []
    replay = cpu.get('p2_ignored', {}) if isinstance(cpu, Mapping) else {}
    defense = cpu.get('lowwave_defense', []) if isinstance(cpu, Mapping) else []
    names_level = tuple(map(int, manifest['version'].split('.'))) >= (0, 18, 0)
    expected_label = 'DUMMY: CPU NORMAL' if names_level else 'DUMMY: CPU'
    need(isinstance(cpu, Mapping) and cpu.get('selector', {}).get('cpu_label') == expected_label and
         isinstance(play, list) and [(item.get('difficulty'), item.get('fighter'), item.get('opponent'))
         for item in play] == [(0, 0, 0), (1, 4, 10), (2, 2, 11)] and
         all(all(item.get(key, 0) > 0 for key in ('movement_frames', 'attack_frames', 'damage_frames', 'recovery_count'))
             for item in play) and replay.get('frames') == 360 and
         isinstance(replay.get('idle_sha256'), str) and re.fullmatch('[0-9a-f]{64}', replay['idle_sha256']) and
         replay.get('idle_sha256') == replay.get('held_sha256') and
         isinstance(defense, list) and [item.get('difficulty') for item in defense] == [1, 2] and
         all(item.get('wave_frames', 0) > 0 and item.get('guarded_chip_frames', 0) > 0 for item in defense) and
         cpu.get('intro', {}).get('intro_callbacks', 0) > 0, 'CPU Training native proof lost its fixed behavior coverage')
    if names_level:
        checks = native.get('checks')
        need(isinstance(checks, list) and all(isinstance(row, Mapping) for row in checks),
             'CPU Training level proof must retain its native checks')
        expected = [{'difficulty': level, 'label': 'DUMMY: CPU '+name}
                    for level, name in enumerate(('EASY', 'NORMAL', 'HARD'))]
        for name in ('Training CPU pause card shows the selected Easy/Normal/Hard level',
                     'Training CPU level remains visible after quick reset and guide cycling'):
            rows = [row for row in checks if row.get('check') == name]
            need(len(rows) == 3 and all(row.get('passed') is True for row in rows) and
                 [row.get('details') for row in rows] == expected,
                 'CPU Training must prove all three native level labels before and after reset')
    if tuple(map(int, manifest['version'].split('.'))) >= (0, 19, 0):
        controls = cpu.get('level_controls')
        cycle = []
        for port in (0, 1):
            level = 1
            for key, delta in (('r', 1), ('l', -1)):
                for _ in range(3):
                    after = (level+delta) % 3
                    cycle.append({'port':port,'key':key,'before':level,'after':after})
                    level = after
        holds = [{'port':port,'key':key,'before':before,'after':after,'frames':12}
                 for port in (0,1) for key,before,after in (('r',1,2),('l',2,1))]
        opposites = [{'p1':p1,'p2':p2,'difficulty':1} for p1,p2 in
                     ((['l','r'],[]),([],['l','r']),(['l'],['r']),(['r'],['l']))]
        held = [{'first_port':first,'opposite_port':other,'difficulty':0 if first == 0 else 2}
                for first in (0,1) for other in (0,1)]
        excluded = [{'dummy':dummy,'difficulty':1} for dummy in range(4)] + [
            {'page':page,'port':port,'key':key,'difficulty':1}
            for page in (1,2) for port,key in ((0,'r'),(1,'l'))]
        need(isinstance(controls,Mapping) and controls.get('cycle') == cycle and
             controls.get('holds') == holds and controls.get('opposites') == opposites and
             controls.get('held_opposites') == held and controls.get('exclusions') == excluded and
             controls.get('priorities') == ['start','a','select','dummy','b'] and
             controls.get('final_home_difficulty') == 2 and
             cpu.get('nontraining_level_scope') == [{'mode':0,'home_difficulty':1},{'mode':1,'home_difficulty':1}],
             'CPU shoulder proof must retain both ports, wraps, holds, opposites, scope and priority cases')
        held_rows = [row for row in native['checks']
                     if row.get('check') == 'held CPU shoulder changes level once without repeating']
        need(len(held_rows) == 4 and all(row.get('passed') is True and
             isinstance(row.get('details'),list) and len(row['details']) == 12 and
             all(text == 'DUMMY: CPU '+('EASY','NORMAL','HARD')[hold['after']]
                 for text in row['details'][3:]) for row,hold in zip(held_rows,holds)),
             'CPU shoulder holds must retain repeated settled native labels')
        frozen_rows = [row for row in native['checks'] if row.get('check') ==
                       'changing CPU difficulty freezes all combat, bars, animation and ambient state']
        fields = ('x1','x2','y1','y2','hp1','hp2','energy1','energy2','action1','action2',
                  'anim_frame1','anim_frame2','ambient_clock','seconds')
        need(len(frozen_rows) == 1 and frozen_rows[0].get('passed') is True and
             all(frozen_rows[0]['details']['before'].get(key) == frozen_rows[0]['details']['after'].get(key)
                 and key in frozen_rows[0]['details']['before'] for key in fields),
             'CPU shoulder proof must freeze native gameplay state')
    row = report.get('capture')
    trace = native_gif(row, root, 'docs/screenshots/training-cpu/practice.gif')
    need(len(trace) == fixture['frames'] and all(state.get('mode') == 2 and state.get('training_dummy') == 4 and
         state.get('seconds') == 99 and state.get('paused') == state.get('intro') == state.get('round_end') == 0 and
         state.get('fighter_id1') == fixture['fighter'] and state.get('fighter_id2') == fixture['opponent'] and
         state.get('arena') == fixture['stage']
         for state in trace), 'CPU Training clip must retain live untimed fifth-choice play')
    proof = {'moving_frames': sum(state['x2'] != trace[0]['x2'] for state in trace),
             'attack_frames': sum(state['action2'] != 0 for state in trace),
             'damage_frames': sum(state['hp1'] < 128 for state in trace)}
    need(all(proof.values()) and row.get('proof') == proof, 'CPU Training clip must show actual movement, attacks and damage')
    card = report.get('card', {})
    path = 'docs/screenshots/training/training-cpu-card.png'
    need(isinstance(card, Mapping) and card.get('png') == path and card.get('native_dimensions') == [256, 224] and
         path in [str(value).replace('\\', '/') for value in native.get('capture_paths', [])] and
         (root/path).is_file() and card.get('png_bytes') == (root/path).stat().st_size and
         card.get('png_sha256') == digest((root/path).read_bytes()), 'CPU Training card must match the retained native-suite PNG')
    try:
        with Image.open(root/path) as image:
            need(image.format == 'PNG' and image.size == (256, 224) and
                 card.get('source_rgb_sha256') == digest(image.convert('RGB').tobytes()), 'CPU Training card pixels differ')
    except (OSError, ValueError) as error:
        raise ReviewError('Unreadable CPU Training card') from error
