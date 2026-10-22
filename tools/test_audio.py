"""Silent native PCM audit and reproducible listening material.

Load the pinned Snes9x core and the current cartridge. Controller-only A/B
runs distinguish each resident cue from the same music timeline. Five music
captures check repeated PCM structure near the authored score-cycle length.
No frontend window, audio device, emulated-memory write or savestate is used.
This supplements Test.cmd; it does not claim a human listening verdict.
"""
from __future__ import annotations

import array
import ctypes as C
import hashlib
import json
import math
import re
from pathlib import Path
import struct
import sys
import time
import wave
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emulator import Emulator, ROOT
from longrun_host import SystemAvInfo
from test_endurance import core_identity

REPORT = ROOT / 'docs/audio-test-report.json'
CAPTURES = ROOT / 'build/audio-review'
checks: list[dict] = []


def check(condition: bool, name: str, details=None) -> None:
    checks.append({'check': name, 'passed': bool(condition), 'details': details})
    if not condition:
        raise AssertionError((name, details))


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def state(e: Emulator) -> dict[str, int]:
    s = e.state()
    check(s['magic'] == 0xAABA, 'native trace identity')
    return s


def press(e: Emulator, key: str, port: int = 0) -> None:
    e.run(4, **({'p1': [key]} if port == 0 else {'p2': [key]}))
    e.run(4)


def wait(e: Emulator, screen: int) -> None:
    for _ in range(720):
        if e.state()['screen'] == screen:
            return
        e.run(1)
    raise AssertionError(('menu timeout', screen, e.state()))


def boot_match(stage: int = 0) -> Emulator:
    e = Emulator()
    try:
        e.run(180)
        press(e, 'down')
        press(e, 'a')
        wait(e, 1)
        press(e, 'a')
        press(e, 'a', 1)
        wait(e, 2)
        for _ in range(stage):
            press(e, 'down')
        press(e, 'a')
        wait(e, 3)
        for _ in range(180):
            if e.state()['intro'] == 0:
                break
            e.run(1)
        e.run(4)
        s = state(e)
        check((s['mode'], s['arena'], s['fighter_id1'], s['fighter_id2'],
               s['intro']) == (1, stage, 0, 1, 0),
              'controller-only audio fixture loaded', s)
        return e
    except Exception:
        e.close()
        raise


def timing(e: Emulator) -> tuple[float, int]:
    av = SystemAvInfo()
    e.core.retro_get_system_av_info(C.byref(av))
    fps, rate = av.timing.fps, int(round(av.timing.sample_rate))
    check(59 < fps < 61 and rate == 32040,
          'pinned core native PCM timing', {'fps': fps, 'sample_rate': rate})
    return fps, rate


def record(e: Emulator, frames: int, *, fps: float, rate: int,
           p1=(), p2=(), live: bool = True, transition: bool = False,
           scene: int | None = None, transition_screens: tuple = (0, 1)):
    """Copy every batch; clear only the Python capture buffer between frames."""
    chunks, states = [], []
    before_samples = e.audio_samples
    before = e.state()
    videos = 0
    video_errors, pcm_errors, cadence_errors = [], [], []
    original_video = e.callbacks[1]

    def video(data, width, height, pitch):
        nonlocal videos
        videos += 1
        if (width, height) != (256, 224):
            video_errors.append((width, height, pitch))
        original_video(data, width, height, pitch)

    bridge = type(original_video)(video)
    e.core.retro_set_video_refresh(bridge)
    try:
        for index in range(frames):
            e.pcm.clear()
            e.run(1, p1=p1, p2=p2)
            chunk = bytes(e.pcm)
            if not chunk or len(chunk) % 4:
                pcm_errors.append((index, len(chunk)))
            chunks.append(chunk)
            if videos != index+1:
                video_errors.append(('callback count', index+1, videos))
            now = e.state()
            valid = now['magic'] == 0xAABA
            if transition:
                valid = valid and now['screen'] in transition_screens
            elif scene is not None:
                valid = valid and now['screen'] == scene
            elif live:
                valid = valid and now['screen'] == 3 and now['intro'] == now['round_end'] == 0
            else:
                valid = valid and now['screen'] == 0
            # Scene loading can keep old TRACE while forced blank executes;
            # real video and sample cadence remain mandatory through it.
            if not transition:
                valid = valid and (now['frame']-before['frame']) & 0xffff == 1
            if not valid:
                cadence_errors.append({'index': index, 'before': before, 'now': now})
            states.append({key: now[key] for key in (
                'screen', 'frame', 'hp1', 'hp2', 'action1', 'action2', 'wave1',
                'energy1', 'hitstop', 'pose1', 'fighter_id1', 'fighter_id2')})
            before = now
    finally:
        e.core.retro_set_video_refresh(original_video)
    pcm = b''.join(chunks)
    check(not video_errors, 'one native 256x224 video callback per capture frame', video_errors[:3])
    check(not pcm_errors, 'every capture frame supplies complete stereo PCM', pcm_errors[:3])
    check(not cadence_errors, 'expected scene and native cadence during audio capture', cadence_errors[:1])
    check(len(pcm) // 2 == e.audio_samples - before_samples,
          'every stereo PCM sample was retained', len(pcm))
    expected = frames * rate / fps
    check(abs(len(pcm)/4-expected) <= 2,
          'actual PCM duration agrees with independent native AV timing', {
              'frames': frames, 'expected_sample_frames': expected,
              'actual_sample_frames': len(pcm)//4, 'tolerance_sample_frames': 2})
    return pcm, states


def native_byte(e: Emulator, name: str) -> int:
    """Read a linker-resolved native byte without adding a trace field."""
    if not hasattr(e, '_audio_symbols'):
        e._audio_symbols = {}
        symbol_file = e.rompath.with_suffix('.sym')
        for line in symbol_file.read_text().splitlines():
            match = re.match(r'^([0-9a-fA-F]{8})\s+(\w+)$', line)
            if match:
                e._audio_symbols[match[2]] = int(match[1], 16)
    address = e._audio_symbols[name]
    if address >> 16 == 0x7e:
        offset = address & 0xffff
    elif address < 0x2000:
        offset = address
    else:
        raise ValueError(('Audio probe symbol is outside WRAM', name, address))
    return C.string_at(e.ram+offset, 1)[0]


def boot_champion() -> Emulator:
    """Earn the actual ending through eleven controller-only Arcade wins."""
    from collections import deque
    from test_champion import play_cpu, press as ladder_press, wait as ladder_wait
    e = Emulator()
    ladder, transition = [], deque(maxlen=150)
    original_run = e.run
    try:
        e.run(100)
        ladder_press(e, 'l')  # Normal -> Easy; choose Enzo as the existing proof does.
        ladder_press(e, 'a'); ladder_wait(e, 1)
        for _ in range(4):
            ladder_press(e, 'right')
        ladder_press(e, 'a'); ladder_wait(e, 2)
        ladder_press(e, 'a'); ladder_wait(e, 3); e.run(180)
        fps, rate = timing(e)

        def capture_run(n=1, p1=(), p2=()):
            for _ in range(n):
                e.pcm.clear()
                now = original_run(1, p1=p1, p2=p2)
                read, write = native_byte(e, 'spc_fread'), native_byte(e, 'spc_fwrite')
                transition.append((bytes(e.pcm), {
                    'screen': now['screen'], 'champion': now['champion'],
                    'music_index': native_byte(e, 'musicIndex'),
                    'spc_backlog': (write-read) & 255}))
            return now

        ordinary = None
        for match in range(11):
            if match == 10:
                e.run = capture_run
            attempts = []
            for _ in range(8):
                play_cpu(e)
                current = state(e)
                check(current['screen'] == 4 and current['arcade'] == match,
                      'audio ladder reaches the actual next result', current)
                attempts.append([current['wins1'], current['wins2']])
                if current['wins1'] == 2:
                    break
                check(not current['champion'], 'loss cannot award Champion score')
                ladder_press(e, 'a'); ladder_wait(e, 3)
            check(current['wins1'] == 2 and current['champion'] == int(match == 10),
                  'victory score is earned only after the eleventh win', current)
            ladder.append({'opponent': current['fighter_id2'], 'arena': current['arena'],
                           'attempts': attempts})
            if match == 0:
                check(native_byte(e, 'musicIndex') == current['arena']+1,
                      'ordinary result keeps the current arena score')
                pcm, _ = record(e, 60, fps=fps, rate=rate, live=False, scene=4)
                ordinary = {'music_index': native_byte(e, 'musicIndex'),
                            'pcm': metrics(pcm, rate),
                            'capture': save_wav('ordinary-result', pcm, rate)}
            if match < 10:
                ladder_press(e, 'a'); ladder_wait(e, 3)
        e.run(90)
        e.run = original_run
        check(len({item['opponent'] for item in ladder}) == 11,
              'all eleven distinct opponents were defeated with controllers')
        check(native_byte(e, 'musicIndex') == 4,
              'actual Champion scene selects the fifth music score')
        pcm = b''.join(item[0] for item in transition)
        states = [item[1] for item in transition]
        check({s['music_index'] for s in states} == {2, 4},
              'final arena score changes directly to Champion score', states)
        check(max(s['spc_backlog'] for s in states) <= 6 and states[-1]['spc_backlog'] == 0,
              'Champion load preserves the resident SPC FIFO budget')
        stats = metrics(pcm, rate)
        check(stats['clipped_samples'] == 0 and stats['rms'] > 32 and
              stats['longest_near_silence_seconds'] < 0.5,
              'Champion transition has audible unclipped PCM without a long dropout', stats)
        e.champion_audio_proof = {
            'controller_only': True, 'ladder': ladder, 'ordinary_result': ordinary,
            'champion_transition': {'pcm': stats, 'frames': states,
                                    'capture': save_wav('champion-transition', pcm, rate)}}
        return e
    except Exception:
        e.run = original_run
        e.close()
        raise


def samples(pcm: bytes) -> array.array:
    values = array.array('h')
    values.frombytes(pcm)
    if sys.byteorder != 'little':
        values.byteswap()
    return values


def metrics(pcm: bytes, rate: int) -> dict:
    values = samples(pcm)
    check(bool(values) and len(values) % 2 == 0, 'valid signed-16 stereo PCM')
    count = len(values)
    peak = max(abs(v) for v in values)
    rms = math.sqrt(sum(v*v for v in values) / count)
    left, right = values[::2], values[1::2]
    run, longest = 0, 0
    for l, r in zip(left, right):
        run = run+1 if abs(l) <= 1 and abs(r) <= 1 else 0
        longest = max(longest, run)
    return {'sha256_pcm': digest(pcm), 'sample_frames': count // 2,
            'seconds': count / (2 * rate), 'peak': peak,
            'rms': round(rms, 4),
            'rms_dbfs': round(20*math.log10(max(rms, 1e-10)/32768), 4),
            'clipped_samples': sum(abs(v) >= 32767 for v in values),
            'dc_left': round(sum(left)/(count//2), 4),
            'dc_right': round(sum(right)/(count//2), 4),
            'longest_near_silence_sample_frames': longest,
            'longest_near_silence_seconds': longest/rate}


def save_wav(name: str, pcm: bytes, rate: int) -> dict:
    path = CAPTURES / (name + '.wav')
    with wave.open(str(path), 'wb') as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(pcm)
    return {'file': path.relative_to(ROOT).as_posix(),
            'sha256': digest(path.read_bytes()), 'bytes': path.stat().st_size}


def cue_capture(name: str, active: bool):
    if name == 'round-confirm':
        e = Emulator()
        e.run(180)
    else:
        e = boot_match()
    try:
        fps, rate = timing(e)
        if name == 'impact':
            e.run(48, p1=['right'])
            e.run(22, p1=['right'] if active else [])
        elif name == 'special':
            e.run(4, p1=['down'])
        elif name == 'swing':
            e.run(26)
        initial = state(e)
        if name == 'round-confirm':
            keys = ['a'] if active else []
        elif name == 'impact':
            keys = ['y']  # same swing in both runs, contact only in one
        elif name == 'special':
            keys = ['down', 'x'] if active else ['down']
        else:
            keys = ['y'] if active else []
        # Observe the projectile cue before it can travel across the arena and
        # add a second impact cue to the same comparison.
        frames = 24 if name == 'special' else 45
        pcm, states = record(e, frames, fps=fps, rate=rate, p1=keys,
                             live=name != 'round-confirm',
                             transition=name == 'round-confirm' and active)
        return pcm, initial, states, rate
    finally:
        e.close()


def verify_cues() -> dict:
    result = {}
    for index, name in enumerate(('swing', 'impact', 'special', 'round-confirm')):
        baseline, initial0, states0, rate = cue_capture(name, False)
        repeated, repeated_initial, repeated_states, repeated_rate = cue_capture(name, False)
        check(baseline == repeated and rate == repeated_rate,
              name + ': cold-boot control PCM is bit-identical', digest(baseline))
        active, initial1, states1, active_rate = cue_capture(name, True)
        check(rate == active_rate and len(baseline) == len(active),
              name + ': A/B timelines have equal sample count')
        if name == 'swing':
            check(any(s['action1'] == 1 for s in states1) and
                  all(s['hp2'] == 128 for s in states1),
                  'swing is an actual whiff without a contact cue')
        elif name == 'impact':
            check(all(s['hp2'] == 128 for s in states0) and
                  any(s['hp2'] < 128 for s in states1),
                  'impact A/B uses the same normal with contact only in active run')
        elif name == 'special':
            check(any(s['action1'] == 7 for s in states1) and
                  any(s['wave1'] for s in states1) and
                  all(s['hp2'] == 128 for s in states1),
                  'special launches a real wave without impact contamination', {
                      'minimum_hp2': min(s['hp2'] for s in states1),
                      'actions': sorted({s['action1'] for s in states1}),
                      'wave_seen': any(s['wave1'] for s in states1)})
        else:
            check(states0[-1]['screen'] == 0 and states1[-1]['screen'] == 1,
                  'confirmation cue accompanies a real title-to-select transition')
        delta = [a-b for a, b in zip(samples(active), samples(baseline))]
        energy = sum(v*v for v in delta)
        check(max(map(abs, delta)) > 128 and energy / len(delta) > 64,
              name + ': resident cue changes the actual mixed PCM', {
                  'delta_peak': max(map(abs, delta)),
                  'delta_rms': round(math.sqrt(energy/len(delta)), 4)})
        active_metrics, baseline_metrics = metrics(active, rate), metrics(baseline, rate)
        for role, stats in [('active', active_metrics), ('control and identical repeat', baseline_metrics)]:
            check(stats['clipped_samples'] == 0 and stats['rms'] > 32 and stats['peak'] > 128,
                  name + ': ' + role + ' PCM is non-silent without full-scale clipping', stats)
        result[name] = {'cue_id': index,
                        'baseline': save_wav(name+'-control', baseline, rate),
                        'active': save_wav(name+'-active', active, rate),
                        'baseline_pcm_sha256': digest(baseline),
                        'repeat_pcm_sha256': digest(repeated),
                        'delta_peak': max(map(abs, delta)),
                        'delta_rms': round(math.sqrt(energy/len(delta)), 4),
                        'mixed_pcm': active_metrics,
                        'control_pcm': baseline_metrics,
                        'initial': [initial0, initial1],
                        'trace': [states0, states1]}
    return result


def tracker_duration(path: Path) -> float:
    raw = path.read_bytes()
    check(raw[:4] == b'IMPM', 'authored music uses the IT module format')
    orders, instruments, smps, patterns = struct.unpack_from('<4H', raw, 32)
    speed, tempo = raw[50], raw[51]
    check(speed > 0 and tempo >= 32, 'fixed native tracker speed and tempo')
    offsets = struct.unpack_from('<'+str(patterns)+'I', raw,
                                 192+orders+4*(instruments+smps))
    # Validate the narrow authored pattern vocabulary: no effect/tempo/order
    # commands or mask reuse. This is not an arbitrary IT timing interpreter.
    for offset in offsets:
        packed_bytes, rows = struct.unpack_from('<HH', raw, offset)
        packed = raw[offset+8:offset+8+packed_bytes]
        cursor, row_count = 0, 0
        while cursor < len(packed):
            channel = packed[cursor]
            cursor += 1
            if channel == 0:
                row_count += 1
                continue
            check(channel & 0x80 and cursor+4 <= len(packed) and
                  packed[cursor] == 7,
                  'authored score has no timing or order effect commands')
            cursor += 4  # explicit mask, note, instrument and volume
        check(row_count == rows, 'authored pattern row count matches packed data')
    ticks = 0
    for pattern in raw[192:192+orders]:
        if pattern == 255:
            break
        check(pattern < patterns, 'tracker order references an existing pattern')
        rows = struct.unpack_from('<H', raw, offsets[pattern]+2)[0]
        ticks += rows * speed
    return ticks * 2.5 / tempo


def score_repeat(pcm: bytes, rate: int, nominal: float) -> dict:
    """Match a long native audio passage at the next approximate score period.

    Envelope correlation is refined with zero-crossing correlation so matching
    only a drum beat is insufficient. This observes PCM repetition, not an SPC
    order register or a claim that the loop seam sounds finished.
    """
    values = samples(pcm)
    block = rate // 200  # approximately 5 ms, always complete stereo frames
    envelope, crossings = [], []
    for start in range(0, len(values)-block*2+1, block*2):
        mono = [values[i]+values[i+1] for i in range(start, start+block*2, 2)]
        envelope.append(sum(map(abs, mono))/block)
        crossings.append(sum((x < 0) != (y < 0) for x, y in zip(mono, mono[1:])))
    reference = round(nominal * rate/block)

    def prepare(series):
        mean = sum(series[:reference])/reference
        centered = [value-mean for value in series[:reference]]
        power = sum(value*value for value in centered)
        sums, squares = [0.0], [0.0]
        for value in series:
            sums.append(sums[-1]+value)
            squares.append(squares[-1]+value*value)
        return centered, power, sums, squares

    def correlation(series, prepared, lag):
        centered, power, sums, squares = prepared
        total = sums[lag+reference]-sums[lag]
        other_power = squares[lag+reference]-squares[lag]-total*total/reference
        denominator = math.sqrt(max(0, power*other_power))
        if denominator == 0:
            return 0.0
        return sum(x*y for x, y in zip(centered, series[lag:lag+reference]))/denominator

    envelope_data, crossing_data = prepare(envelope), prepare(crossings)
    low = round(nominal * 0.92 * rate/block)
    high = min(round(nominal * 1.08 * rate/block), len(envelope)-reference)
    candidates = sorted(((correlation(envelope, envelope_data, lag), lag)
                         for lag in range(low, high+1)), reverse=True)[:8]
    scored = [(energy + correlation(crossings, crossing_data, lag), energy,
               correlation(crossings, crossing_data, lag), lag)
              for energy, lag in candidates]
    _, energy, frequency, lag = max(scored)
    # A five-millisecond grid can blur a sharp percussion attack. Refine the
    # winning lag directly in sample time instead of lowering the thresholds.
    # Prefix sums retain exact window statistics without re-reading every
    # sample for every candidate phase.
    absolute = array.array('Q', [0])
    zero_crossings = array.array('I', [0])
    previous = False
    for i in range(0, len(values), 2):
        mono = values[i]+values[i+1]
        negative = mono < 0
        absolute.append(absolute[-1]+abs(mono))
        zero_crossings.append(zero_crossings[-1]+int(i > 0 and negative != previous))
        previous = negative

    def exact_features(start):
        levels, changes = [], []
        for i in range(reference):
            a = start+i*block
            b = a+block
            levels.append((absolute[b]-absolute[a])/block)
            changes.append(zero_crossings[b]-zero_crossings[a+1])
        return levels, changes

    def exact_correlation(other, prepared):
        centered, power, _, _ = prepared
        total = sum(other)
        other_power = sum(x*x for x in other)-total*total/reference
        denominator = math.sqrt(max(0, power*other_power))
        return sum(x*y for x, y in zip(centered, other))/denominator if denominator else 0.0

    refined = []
    for offset in range(-block, block+1, 4):
        start = lag*block+offset
        if start < 0 or start+reference*block >= len(absolute):
            continue
        levels, changes = exact_features(start)
        e = exact_correlation(levels, envelope_data)
        z = exact_correlation(changes, crossing_data)
        refined.append((e+z, e, z, start))
    _, energy, frequency, start = max(refined)
    result = {'method': 'long-passage envelope and zero-crossing correlation',
              'nominal_cycle_seconds': nominal,
              'observed_pcm_repeat_seconds': start/rate,
              'reference_seconds': reference*block/rate,
              'search_seconds': [low*block/rate, high*block/rate],
              'refinement_sample_frames': 4,
              'envelope_correlation': energy,
              'zero_crossing_correlation': frequency,
              'thresholds': {'envelope': 0.96, 'zero_crossing': 0.85}}
    check(energy >= 0.96 and frequency >= 0.85,
          'native PCM repeats a long score passage near the expected cycle', result)
    return result


def verify_music(verified_assets: dict[str, str]) -> dict:
    result = {}
    for module, name in enumerate(('title', 'las-condes', 'el-castillo', 'la-oficina', 'office-champion')):
        if module == 0:
            e = Emulator()
            e.run(180)
        elif module == 4:
            e = boot_champion()
        else:
            e = boot_match(module-1)
        try:
            fps, rate = timing(e)
            module_file = f'assets/generated/music{module}.it'
            module_hash = digest((ROOT / module_file).read_bytes())
            check(verified_assets.get(module_file) == module_hash,
                  name + ': score source matches the exact-ROM fresh rebuild')
            cycle = tracker_duration(ROOT / module_file)
            # Allow native tempo quantization and retain a long passage after
            # the second cycle for an observed repetition check.
            frames = math.ceil((cycle*2+4) * fps)
            pcm, states = record(e, frames, fps=fps, rate=rate, live=module not in (0, 4),
                                 scene=4 if module == 4 else None)
            stats = metrics(pcm, rate)
            repeat = score_repeat(pcm, rate, cycle)
            check(stats['seconds'] > repeat['observed_pcm_repeat_seconds']*2,
                  name + ': capture spans two measured PCM repeat intervals')
            check(stats['rms'] > 32 and stats['clipped_samples'] == 0 and
                  stats['longest_near_silence_seconds'] < 0.5,
                  name + ': music remains audible without clipping or long silence', stats)
            result[name] = {'module': module, 'module_file': module_file,
                            'module_sha256': module_hash, 'cycle_seconds': cycle,
                            'frames': frames, 'timing': {'fps': fps, 'sample_rate': rate},
                            'repeat': repeat,
                            'pcm': stats, 'capture': save_wav('music-'+name, pcm, rate),
                            'start': states[0], 'end': states[-1]}
            if module == 4:
                result[name]['controller_proof'] = verify_champion_exit(e, fps, rate)
        finally:
            e.close()
    return result


def verify_champion_exit(e: Emulator, fps: float, rate: int, key: str = 'a') -> dict:
    pcm, states = record(e, 120, fps=fps, rate=rate, p1=[key], live=False,
                         transition=True, transition_screens=(4, 0))
    check(states[-1]['screen'] == 0 and native_byte(e, 'musicIndex') == 0,
          'Champion A/Start exit restores title music with controllers')
    stats = metrics(pcm, rate)
    check(stats['clipped_samples'] == 0 and stats['rms'] > 32 and
          stats['longest_near_silence_seconds'] < 0.5,
          'Champion-to-title PCM has no clipping or long dropout', stats)
    return {**e.champion_audio_proof, 'title_exit': {
        'key': key, 'music_index': native_byte(e, 'musicIndex'), 'pcm': stats,
        'capture': save_wav('champion-title-exit-'+key, pcm, rate)}}


def make_listening_pack(report: dict) -> dict:
    path = ROOT / 'dist' / ('Abaqus-After-Hours-v'+report['version']+'-Audio-Review.zip')
    notice = ('Audio captured silently from the native SNES ROM.\n'
              'Music files span two measured score-length PCM repeat intervals.\n'
              'Correlation is technical evidence, not a loop-seam listening verdict.\n'
              'Cue control/active files are matched controller-driven A/B runs.\n'
              'Mixed PCM differences include any music-voice interaction; they\n'
              'are not isolated source samples or a listening-quality verdict.\n'
              'No speakers or audio device were used during verification.\n'
              'ROM SHA256: '+report['rom_sha256']+'\n')
    records = [item[role] for item in report['cues'].values()
               for role in ('baseline', 'active')]
    records += [item['capture'] for item in report['music'].values()]
    manifest = {
        'schema': 1, 'purpose': 'human listening review, not public certification',
        'rom_sha256': report['rom_sha256'], 'version': report['version'],
        'core': report['core'], 'harness_sha256': report['harness_sha256'],
        'host_contract': report['host_contract'], 'human_listening_approved': False,
        'captures': [{**item, 'file': Path(item['file']).name} for item in records],
        'cues': {name: {
            'cue_id': item['cue_id'],
            'control': Path(item['baseline']['file']).name,
            'active': Path(item['active']['file']).name,
            'delta_peak': item['delta_peak'], 'delta_rms': item['delta_rms'],
            'mixed_pcm': item['mixed_pcm']}
            for name, item in report['cues'].items()},
        'music': {name: {
            'capture': Path(item['capture']['file']).name,
            'module_sha256': item['module_sha256'],
            'cycle_seconds': item['cycle_seconds'], 'repeat': item['repeat'], 'pcm': item['pcm']}
            for name, item in report['music'].items()},
    }
    with zipfile.ZipFile(path, 'w') as out:
        entries = [('README.txt', notice.encode('utf-8')),
                   ('manifest.json', (json.dumps(manifest, indent=2)+'\n').encode('utf-8'))]
        for record in sorted(records, key=lambda item: item['file']):
            source = ROOT / record['file']
            data = source.read_bytes()
            check(digest(data) == record['sha256'],
                  'listening archive contains only current verified captures', record['file'])
            entries.append((source.name, data))
        for name, data in entries:
            entry = zipfile.ZipInfo(name, date_time=(2026,1,1,0,0,0))
            entry.create_system = 0
            entry.external_attr = 0x20
            entry.compress_type = zipfile.ZIP_DEFLATED
            out.writestr(entry, data, compresslevel=9)
    return {'file': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size,
            'sha256': digest(path.read_bytes())}


def main() -> int:
    started = time.monotonic()
    manifest = json.loads((ROOT/'dist/manifest.json').read_text(encoding='utf-8'))
    report = {'suite': 'audio', 'status': 'failed', 'rom_sha256': manifest['sha256'],
              'rom_bytes': manifest['bytes'], 'version': manifest['version'],
              'checks': checks, 'human_listening_approved': False,
              'host_contract': {'controller_only': True, 'emulated_memory_writes': 0,
                                'savestate_calls': 0, 'frontend_window_created': False,
                                'audio_device_opened': False, 'pcm_capture_only': True}}
    try:
        cartridge = (ROOT/'dist/abaqus-after-hours.sfc').read_bytes()
        check(digest(cartridge) == manifest['sha256']
              and len(cartridge) == manifest['bytes'] == 4194304,
              'exact current 4 MiB cartridge')
        report['core'] = core_identity()
        fresh_path = ROOT/'docs/fresh-build-test-report.json'
        fresh = json.loads(fresh_path.read_text(encoding='utf-8'))
        check(fresh['status'] == 'passed' and
              fresh['rom_sha256'] == fresh['rebuilt_rom_sha256'] == manifest['sha256'],
              'score provenance belongs to the exact freshly rebuilt ROM')
        verified_assets = {item['file']: item['sha256']
                           for item in fresh['generated_assets']
                           if item['comparison'] == 'exact bytes'}
        report['source_provenance'] = {
            'report': fresh_path.relative_to(ROOT).as_posix(),
            'report_sha256': digest(fresh_path.read_bytes()),
            'source_commit': fresh['source_commit']}
        report['harness_sha256'] = digest(b''.join((ROOT/name).read_bytes() for name in (
            'tools/test_audio.py', 'tools/emulator.py', 'tools/longrun_host.py',
            'tools/test_endurance.py')))
        CAPTURES.mkdir(parents=True, exist_ok=True)
        report['cues'] = verify_cues()
        report['music'] = verify_music(verified_assets)
        report['listening_pack'] = make_listening_pack(report)
        report['status'] = 'passed'
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        report['passed'] = sum(c['passed'] for c in checks)
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        REPORT.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'passed': report['passed'],
                      'rom_sha256': report['rom_sha256'],
                      'seconds': report['elapsed_seconds'],
                      'listening_pack': report['listening_pack']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
