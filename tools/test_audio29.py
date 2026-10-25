"""Bounded controller-only v29 audio proof. No window/device/writes/savestates.

Both pinned cores: real PCM, all stages, native mixer UI, contacts, pause and
FIFO/cadence. Snes9x additionally earns the eleven-win Champion score.
"""
from __future__ import annotations
import argparse
import array
import ctypes as C
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import tarfile
import time
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from emulator import Emulator
from test_classic_menu import AccuracyMenu
from test_champion import host_contract
from test_compatibility import verify_manifest_and_pinned_core
from test_training import core_identity
from longrun_host import SystemAvInfo
from v024_contracts import symbols
from victory_music import soundbank_budget
from test_training import decode_text
from test_presentation import vram_bytes

BASE = '29fee83'
CHECKS = []
MEDIA = []


def sha(raw): return hashlib.sha256(raw).hexdigest()


def require(ok, name, details=None):
    CHECKS.append({'check': name, 'passed': bool(ok), 'details': details})
    if not ok:
        raise AssertionError((name, details))


def stats(raw):
    values = array.array('h', raw)
    if sys.byteorder != 'little': values.byteswap()
    require(bool(values), 'PCM capture contains actual stereo samples')
    quiet = longest = 0
    for left, right in zip(values[::2], values[1::2]):
        quiet = quiet+1 if abs(left) <= 1 and abs(right) <= 1 else 0
        longest = max(longest, quiet)
    return {'pcm_sha256': sha(raw), 'sample_frames': len(values)//2,
            'peak': max(map(abs, values)), 'rms': round(math.sqrt(sum(v*v for v in values)/len(values)), 4),
            'clipped_samples': sum(abs(v) >= 32767 for v in values), 'longest_near_silence_samples': longest}


def artifact(path):
    record = {'file': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size,
              'sha256': sha(path.read_bytes())}
    MEDIA.append(record)
    return record


def save_pcm(folder, label, raw, rate):
    path = folder/(label+'.wav')
    with wave.open(str(path), 'wb') as out:
        out.setnchannels(2); out.setsampwidth(2); out.setframerate(rate); out.writeframes(raw)
    result = stats(raw)
    require(result['clipped_samples'] == 0, label+': no full-scale clipped PCM', result)
    return {**artifact(path), **result, 'rate': rate}


class Native:
    def __init__(self, core, syms, folder):
        self.engine = core; self.syms = syms; self.folder = folder
        self.host = AccuracyMenu() if core == 'accuracy' else Emulator()
        self.core = self.host.core; self.ram = self.host.ram
        self.closed = False; self.strict = 0; self.max_fifo = 0; self.max_transition_fifo = 0; self.failures = []
        self.cues = []; self.volumes = []; self.pcm = bytearray(); self.recording = False
        self.video_calls = 0; self.command_count = 0
        self.pcm_callback_sizes = {}; self.pcm_windows = []
        av = SystemAvInfo(); self.core.retro_get_system_av_info(C.byref(av))
        self.fps = float(av.timing.fps); self.exact_rate = float(av.timing.sample_rate)
        self.rate = round(self.exact_rate)
        original = self.host.callbacks[1]
        def video(data, w, h, pitch):
            self.video_calls += 1; original(data, w, h, pitch)
        def batch(data, count):
            self.pcm_callback_sizes[int(count)] = self.pcm_callback_sizes.get(int(count), 0)+1
            if self.recording: self.pcm.extend(C.string_at(data, count*4))
            return count
        def sample(left, right):
            if self.recording: self.pcm.extend(struct.pack('<hh', left, right))
        self.bridges = (type(original)(video), type(self.host.callbacks[3])(batch),
                        type(self.host.callbacks[2])(sample))
        self.core.retro_set_video_refresh(self.bridges[0])
        self.core.retro_set_audio_sample_batch(self.bridges[1])
        self.core.retro_set_audio_sample(self.bridges[2])

    def read(self, name, size=1, offset=0):
        return int.from_bytes(C.string_at(self.ram+(self.syms[name] & 0x1ffff)+offset, size), 'little')

    def a(self, index):
        return C.string_at(self.ram+(self.syms['v29AudioState'] & 0x1ffff)+index, 1)[0]

    def state(self): return Emulator.state(self)

    def counters(self):
        return [self.read(n, 2) for n in ('frame', 'snes_vblank_count', 'lag_frame_counter')]

    def run(self, n=1, p1=(), p2=(), transition=False):
        for _ in range(n):
            before = self.counters(); screen = self.read('screen'); calls = self.video_calls
            serial = self.a(10)
            self.host.run(1, p1=p1, p2=p2)
            now = self.counters()
            if not transition:
                self.strict += 1
                delta = [(a-b)&65535 for a, b in zip(now, before)]
                if delta != [1, 1, 0] or self.video_calls-calls != 1:
                    self.failures.append({'before_screen': screen, 'screen': self.read('screen'),
                                          'delta': delta, 'video_callbacks': self.video_calls-calls,
                                          'before_counters': before, 'state': self.state(),
                                          'controller_input': {'p1': sorted(p1), 'p2': sorted(p2)},
                                          'randomseed': self.read('randomseed', 2),
                                          'cue': self.a(8), 'command': self.a(9),
                                          'native_clock': {n:self.read(n) for n in ('secondTick','seconds','hudSeconds','hudDirty')},
                                          'native_audio_state': [self.a(i) for i in range(32)]})
                if self.state()['screen'] == 3 and self.read('screen') == 3:
                    stat = int.from_bytes(C.string_at(self.ram+0x1ff00+228, 2), 'little')
                    if stat & 0xc0: self.failures.append({'obj_stat77': stat})
            backlog = (self.read('spc_fwrite')-self.read('spc_fread'))&255
            if not transition: self.max_fifo = max(self.max_fifo, backlog)
            elif self.state()['magic'] == 0xaaba: self.max_transition_fifo = max(self.max_transition_fifo, backlog)
            if not transition and backlog > 3: self.failures.append({'fifo_bytes': backlog})
            if not transition and (self.a(10)-serial)&255 > 1:
                self.failures.append({'producer_commands': (self.a(10)-serial)&255})
            if self.a(10) != serial:
                self.command_count += 1
                if self.a(9) == 1: self.cues.append({'slot': self.a(8), 'volpan': self.a(7), 'frame': self.read('frame', 2)})
                elif self.a(9) == 2: self.volumes.append(self.read('audioVolume'))
        return self.state()

    def tap(self, key, port=0, transition=False):
        self.run(3, **({'p1': [key]} if port == 0 else {'p2': [key]}), transition=transition)
        return self.run(22, transition=transition)

    def take(self, n, **keys):
        self.pcm.clear(); self.recording = True
        self.run(n, **keys)
        self.recording = False
        raw = bytes(self.pcm)
        expected = n*self.exact_rate/self.fps
        # Accuracy advances its independently scheduled SMP/DSP and flushes
        # <=64-frame callback packets at retro_run's boundary. The approved
        # ROM itself measures -12.28..+11.72 samples across 240-frame windows.
        # One packet bounds phase error; this cannot hide a missing video tick
        # (~533 samples). Snes9x retains the original <=3-sample exact bound.
        bound = 64 if self.engine == 'accuracy' else 3
        window = {'frames': n, 'sample_frames': len(raw)//4, 'expected': expected,
                  'sample_error': len(raw)/4-expected, 'bound': bound}
        self.pcm_windows.append(window)
        require(abs(window['sample_error']) <= bound, 'PCM duration follows native AV cadence and core packet phase', window)
        return raw

    def wait(self, scene):
        for _ in range(600):
            if self.read('screen') == scene:
                self.run(8, transition=True); return
            self.run(1, transition=True)
        raise AssertionError(('scene timeout', scene, self.state()))

    def shot(self, label):
        path = self.folder/(str(len(MEDIA)).zfill(2)+'-'+label+'.png')
        self.host.frame.save(path); return artifact(path)

    def close(self):
        if self.closed: return
        self.host.close(); self.closed = True

    def finish(self):
        require(not self.failures, 'Strict native frame/vblank/SDK/OBJ/producer/FIFO cadence', self.failures[:3])
        return {'strict_callbacks': self.strict, 'max_fifo_bytes': self.max_fifo,
                'max_scene_load_fifo_bytes': self.max_transition_fifo,
                'av_fps': self.fps, 'av_sample_rate': self.exact_rate, 'wav_integer_sample_rate': self.rate,
                'pcm_callback_sizes': self.pcm_callback_sizes, 'pcm_windows': self.pcm_windows,
                'commands_observed': self.command_count, 'cues': self.cues,
                'volume_envelope_values': sorted(set(self.volumes))}


def boot_match(e, stage=0, mode=1):
    e.run(120, transition=True)
    require([e.a(i) for i in range(3)] == [2, 3, 3], 'Cold boot defaults are medium music / high contacts / high voice')
    for _ in range(mode): e.tap('down')
    e.tap('a', transition=True); e.wait(1)
    e.tap('a', transition=True)
    if mode: e.tap('a', 1 if mode == 1 else 0, transition=True)
    e.wait(2)
    for _ in range(stage): e.tap('down')
    e.pcm.clear(); e.recording = True
    e.tap('a', transition=True); e.wait(3)
    e.run(180)
    e.recording = False
    require(e.state()['intro'] == 0 and e.read('arena') == stage, 'Selected stage reaches live native fight')
    return bytes(e.pcm)


def sound_page(e, port=0):
    if not e.read('paused'):
        e.tap('start', port)
        require('Y SOUND' in decode_text(vram_bytes(e), 10, 11), 'Pause sound route is present in actual uploaded BG2')
        e.shot('pause-sound-entry')
    e.tap('y', port)
    require(e.read('pausePage') == 4 and e.read('guideBuild') == 0, 'Y opens completed sound panel from either pad')


def level(e, channel, value, port=0):
    require(e.read('pausePage') == 4, 'Level edits use native sound page')
    for _ in range(3):
        if e.a(3) == channel: break
        e.tap('down', port)
    for _ in range(3):
        current = e.a(channel)
        if current == value: break
        e.tap('left' if current > value else 'right', port)
    require(e.a(channel) == value, 'Controller changes only selected independent level', [channel, value, [e.a(i) for i in range(3)]])


def settings(e):
    sound_page(e, 1)
    screenshot = e.shot('sound-levels')
    # Opposite held directions across ports cancel before the page sees them.
    prior = [e.a(i) for i in range(4)]
    e.run(3, p1=['left'], p2=['right']); e.run(20)
    require(prior == [e.a(i) for i in range(4)], 'Opposite cross-pad sound inputs cancel')
    level(e, 0, 1); level(e, 1, 2); level(e, 2, 0)
    e.tap('l')
    e.tap('b', transition=True); e.wait(1)
    require([e.a(i) for i in range(3)] == [1, 2, 0], 'Non-default levels persist through roster scene')
    e.tap('a', transition=True); e.tap('a', 1, transition=True); e.wait(2)
    e.tap('a', transition=True); e.wait(3); e.run(180)
    require([e.a(i) for i in range(3)] == [1, 2, 0], 'Non-default levels persist through music reload and match reset')
    sound_page(e)
    require(e.read('audioVolume') == 0, 'Music toggle remains off through music reload with announcer muted')
    e.tap('l'); e.run(100)
    require(e.read('audioVolume') == 24, 'Music restores after a scene load even when announcer is off')
    # Verify three gain values on actual isolated resident strong and voice PCM.
    level(e, 0, 0); level(e, 2, 0)
    effects = []
    for value in (1, 2, 3, 0):
        level(e, 1, value); e.run(50)
        e.pcm.clear(); e.recording = True; e.tap('x'); e.run(45); e.recording = False
        result = save_pcm(e.folder, 'effects-level-'+str(value), bytes(e.pcm), e.rate)
        effects.append({'level': value, **result})
    require(effects[0]['rms'] < effects[1]['rms'] < effects[2]['rms'] and effects[0]['rms'] > 32,
            'Effects low/medium/high have strictly increasing audible native RMS')
    require(effects[3]['peak'] <= 1, 'Effects off is silent with music/voice off', effects[3])
    voice = []
    for value in (1, 2, 3, 0):
        level(e, 2, value); e.run(50)
        e.pcm.clear(); e.recording = True; e.tap('x', 1); e.run(55); e.recording = False
        result = save_pcm(e.folder, 'voice-level-'+str(value), bytes(e.pcm), e.rate)
        voice.append({'level': value, **result})
    require(voice[0]['rms'] < voice[1]['rms'] < voice[2]['rms'] and voice[0]['rms'] > 32,
            'Announcer low/medium/high remain audible with effects and music off')
    require(voice[3]['peak'] <= 1, 'Announcer off is silent with music/effects off', voice[3])
    music = []
    for value in (1, 2, 3, 0):
        level(e, 0, value); e.run(100)
        raw = e.take(240)
        music.append({'level': value, **save_pcm(e.folder, 'music-level-'+str(value), raw, e.rate)})
    require(music[0]['rms'] < music[1]['rms'] < music[2]['rms'] and music[0]['rms'] > 32,
            'Music low/medium/high remain audible with effects and announcer off')
    require(music[3]['peak'] <= 1, 'Music off is silent without muting other channel preferences')
    remembered = e.a(13); e.tap('l'); e.run(100)
    require(e.a(0) == remembered and e.read('audioVolume') > 0,
            'Legacy toggle restores the last audible level from Off')
    level(e, 0, 2); level(e, 1, 3); level(e, 2, 3)
    e.run(100); base = e.read('audioVolume')
    e.tap('x'); e.run(100)
    require(base == e.read('audioVolume') == 48 and e.read('audioSpeechTicks') == 0,
            'Speech duck restores the selected music gain')
    e.tap('l'); e.run(100)
    require(e.read('audioVolume') == 0 and e.a(0) == 2, 'Legacy music toggle preserves chosen level')
    e.tap('l'); e.run(100)
    require(e.read('audioVolume') == 48, 'Legacy music toggle restores chosen level')
    old_comfort = e.read('stageDepthTable', offset=9)
    e.tap('r'); require(e.read('stageDepthTable', offset=9) == 1-old_comfort, 'Scenery comfort control remains available')
    e.tap('r')
    # Start/A/B own their original priorities even with other fresh edges.
    e.run(3, p1=['start', 'b', 'a', 'select']); e.run(10)
    require(e.read('screen') == 3 and not e.read('paused'), 'Start retains priority over B/A/Select')
    e.tap('start'); e.tap('select'); require(e.read('pausePage') == 1, 'Existing controls route remains page 1')
    e.tap('y'); e.tap('select'); require(e.read('pausePage') == 1, 'Sound Select returns to originating guide')
    e.tap('a'); require(not e.read('paused'), 'A resumes from guide')
    return {'screenshot': screenshot, 'effects': effects, 'voice': voice, 'music': music}


def training_ownership(e):
    boot_match(e, 2, 2)
    sound_page(e, 1); level(e, 0, 1); level(e, 1, 2); level(e, 2, 0)
    e.tap('select', 1)
    require(e.read('pausePage') == 0, 'Sound back returns to ordinary Training pause')
    e.tap('x'); require(e.read('trainingDummy') == 5, 'Training X still chooses manual P2 dummy')
    e.tap('x'); e.tap('up'); require(e.read('trainingDummy') == 4, 'Training Up still chooses CPU')
    difficulty = e.read('difficulty'); e.tap('r', 1)
    require(e.read('difficulty') == (difficulty+1)%3, 'P2 shoulder still changes CPU level on ordinary Training pause')
    for _ in range(3): e.tap('select')
    require(e.read('pausePage') == 3, 'Existing Training tools retain page 3')
    e.tap('y', 1); e.tap('select', 1)
    require(e.read('pausePage') == 3, 'Sound back returns to Training tools')
    e.tap('start'); e.tap('select')
    require([e.a(i) for i in range(3)] == [1, 2, 0] and e.read('screen') == 3,
            'Live Training reset retains independent sound preferences')
    return {'levels_after_live_reset': [e.a(i) for i in range(3)], 'dummy': e.read('trainingDummy')}


def mixed_contacts(e):
    # Two-port bursts cover alternate contacts, block, sweeps, specials and
    # the neutral super chord on an actual Training P2 controller dummy.
    e.tap('start'); e.tap('x'); e.tap('start')
    require(e.read('trainingDummy') == 5, 'Rapid-mix fixture uses real P2 controller dummy')
    start = len(e.cues); e.pcm.clear(); e.recording = True
    for tick in range(720):
        s = e.state(); toward = 'right' if s['x1'] < s['x2'] else 'left'
        away = 'left' if toward == 'right' else 'right'
        phase = tick % 120
        if phase < 25: p1, p2 = [toward], [away]
        elif phase < 28: p1, p2 = ['y'], ['a']
        elif phase < 52: p1, p2 = [toward], [toward]
        elif phase < 55: p1, p2 = ['down', 'a'], ['down', 'y']
        elif phase < 85: p1, p2 = [], []
        elif phase < 88: p1, p2 = ['y', 'b'], ['y', 'b']
        else: p1, p2 = [toward, 'x'], [toward]
        e.run(1, p1=p1, p2=p2)
    e.recording = False
    return {'slots': sorted({c['slot'] for c in e.cues[start:]}),
            'pcm': save_pcm(e.folder, 'rapid-two-pad-mix', bytes(e.pcm), e.rate)}


def paired_supers(e, stage):
    """Earn both meters with real light contacts, then command both supers."""
    for port in (0, 1):
        for attempt in range(8):
            if e.state()['energy'+str(port+1)] == 96: break
            e.run(90)
            for _ in range(180):
                s = e.state()
                if abs(s['x1']-s['x2'])//16 <= 24: break
                toward = ('right' if s['x1'] < s['x2'] else 'left') if port == 0 else ('left' if s['x1'] < s['x2'] else 'right')
                e.run(1, **({'p1': [toward]} if port == 0 else {'p2': [toward]}))
            e.run(8)
            e.run(3, **({'p1': ['y']} if port == 0 else {'p2': ['y']}))
            e.run(70)
        require(e.state()['energy'+str(port+1)] == 96, 'Both meters are earned through real controller contact', [stage, port, e.state()])
    e.run(100)
    for _ in range(90):
        s = e.state()
        if abs(s['x1']-s['x2'])//16 >= 110: break
        e.run(1, p1=['left' if s['x1'] < s['x2'] else 'right'],
              p2=['right' if s['x1'] < s['x2'] else 'left'])
    e.run(12); e.pcm.clear(); e.recording = True
    e.run(1, p1=['y', 'b'], p2=['y', 'b'])
    require(e.read('superActive') and e.read('superActive', offset=1),
            'Both pads accept simultaneous neutral super chords', [stage, e.state()])
    both_wave_frames = 0
    for _ in range(240):
        e.run(1)
        s = e.state(); both_wave_frames += bool(s['wave1'] and s['wave2'])
    e.recording = False
    require(both_wave_frames > 0, 'Two native super waves overlap within strict audio/OBJ cadence', [stage, both_wave_frames])
    return {'arena': stage, 'two_wave_frames': both_wave_frames,
            'pcm': save_pcm(e.folder, 'stage'+str(stage)+'-paired-supers', bytes(e.pcm), e.rate)}


def contact(e, name, attack, defender=(), distance=40, port=0):
    # Local matchup, reset by returning to roster each time would be needless.
    # Approach only through real walking, then wait ordinary hit recovery.
    e.run(100)
    for _ in range(200):
        s = e.state(); gap = abs(s['x1']-s['x2'])//16
        if gap <= distance: break
        e.run(1, p1=['right' if s['x1'] < s['x2'] else 'left'])
    e.run(10)
    before = e.state(); start = len(e.cues)
    if name == 'block':
        defender = ['right' if before['x1'] < before['x2'] else 'left']
        e.run(4, p2=defender)
    p1, p2 = (attack, defender) if port == 0 else (defender, attack)
    raw = e.take(90, p1=p1, p2=p2)
    after = e.state(); slots = [c['slot'] for c in e.cues[start:]]
    expected = {'light': 1, 'strong': 4, 'block': 5, 'throw': 11, 'knockdown': 12}[name]
    require(expected in slots, name+': semantic cue is produced by actual controller combat', slots)
    require(after['hp2'] < before['hp2'] if name != 'block' else after['hp2'] == before['hp2'],
            name+': damage agrees with intended contact', [before['hp2'], after['hp2']])
    return {'slots': slots, 'hp_before': before['hp2'], 'hp_after': after['hp2'],
            'pcm': save_pcm(e.folder, name, raw, e.rate)}


def local_result(e):
    e.pcm.clear(); e.recording = True; start = len(e.cues)
    for _ in range(16000):
        s = e.state()
        if s['screen'] == 4: break
        forward = 'right' if s['x1'] < s['x2'] else 'left'
        if s['intro'] or s['round_end'] or s['hitstop']:
            e.run(1, transition=s['round_end'] == 1 and max(s['wins1'], s['wins2']) >= 2)
        elif s['action1'] or s['down_state2']: e.run(1, p1=[forward])
        elif abs(s['x1']-s['x2'])//16 > 22: e.run(1, p1=[forward])
        else: e.run(1, p1=[forward, 'x']); e.run(1, p1=[forward])
        if len(e.pcm) > e.rate*4*12: del e.pcm[:-e.rate*4*12]
    e.recording = False
    require(e.read('screen') == 4, 'Actual local KO rounds reach native result')
    slots = [c['slot'] for c in e.cues[start:]]
    require(8 in slots and 10 in slots, 'Actual KO and result preserve announcer/cadence hooks', slots)
    return {'slots': sorted(set(slots)), 'pcm': save_pcm(e.folder, 'ko-result-last12s', bytes(e.pcm), e.rate)}


def play_cpu(e):
    """Retained earned-win controller policy, with only final scene load marked.

    All actual combat, intro, hitstop and ordinary round-end ticks stay strict.
    """
    for _ in range(10000):
        s = e.state()
        if s['screen'] == 4: return
        forward = 'right' if s['x1'] < s['x2'] else 'left'
        back = 'left' if forward == 'right' else 'right'
        distance = abs(s['x1']-s['x2'])//16
        if s['intro'] or s['round_end'] or s['hitstop']:
            e.run(1, transition=s['round_end'] == 1 and max(s['wins1'], s['wins2']) >= 2)
        elif s['action1']: e.run(1, p1=[forward])
        elif s['action2'] and distance < 55:
            e.run(1, p1=[back, 'down'] if 4 <= s['action2'] <= 6 else [back])
        elif distance > 25: e.run(1, p1=[forward])
        else: e.run(1, p1=[forward, 'x']); e.run(1, p1=[forward])
    raise AssertionError(('CPU match did not finish', e.state()))


def play_cpu_defense(e):
    """Earn wins under reviewed wake defense; pressure visible recovery.

    Separate from the retained historical throw policy. Same 10,000-step
    bound, three-attempt ladder and strict native counters; no loading flag
    is granted to any live, intro, contact, pause or ordinary round-end tick.
    """
    for _ in range(10000):
        s = e.state()
        if s['screen'] == 4: return
        forward = 'right' if s['x1'] < s['x2'] else 'left'
        back = 'left' if forward == 'right' else 'right'
        distance = abs(s['x1']-s['x2'])//16
        clock = C.string_at(e.ram+(e.syms['fighters'] & 0x1ffff)+64, 64)
        if s['intro'] or s['round_end'] or s['hitstop']:
            e.run(1, transition=s['round_end'] == 1 and max(s['wins1'],s['wins2']) >= 2)
        elif s['action1']: e.run(1,p1=[forward])
        elif s['action2'] and clock[17] < clock[63] and distance < 55:
            e.run(1,p1=[back,'down'] if 4 <= s['action2'] <= 6 else [back])
        elif distance > 25: e.run(1,p1=[forward])
        else:
            e.run(1,p1=[forward,'x']); e.run(1,p1=[forward])
    raise AssertionError(('Defense-aware CPU match did not finish',e.state()))


def score_passage(e, index, label):
    """One full arrangement plus its loop boundary, with a short review WAV."""
    raw_it = (ROOT/f'assets/generated/music{index}.it').read_bytes()
    seconds = 256*raw_it[50]*2.5/raw_it[51]
    frames = math.ceil((seconds+2)*e.fps)
    raw = e.take(frames); result = stats(raw)
    require(result['clipped_samples'] == 0 and result['rms'] > 32,
            label+': complete arrangement and loop boundary are audible/unclipped', result)
    require(result['longest_near_silence_samples']/e.rate < .5,
            label+': no long silence through complete arrangement and loop boundary')
    return {'module_sha256': sha(raw_it), 'nominal_cycle_seconds': seconds,
            'complete_passage': result,
            'excerpt': save_pcm(e.folder, label, raw[:round(7*e.rate)*4], e.rate)}


def champion(e, policy='legacy'):
    e.run(120, transition=True); e.tap('l'); e.tap('a', transition=True); e.wait(1)
    for _ in range(4): e.tap('right')
    e.tap('a', transition=True); e.wait(2); e.tap('a', transition=True); e.wait(3); e.run(180)
    ladder = []
    # Existing earned-win policy, bounded to three attempts per opponent.
    for match in range(11):
        for attempt in range(3):
            (play_cpu_defense if policy == 'defense' else play_cpu)(e); s = e.state()
            require(s['screen'] == 4, 'Earned Arcade result for Champion music')
            if s['wins1'] == 2: break
            e.tap('a', transition=True); e.wait(3)
        require(s['wins1'] == 2 and s['arcade'] == match, 'Actual next ladder win', [match, s])
        ladder.append({'opponent': s['fighter_id2'], 'arena': s['arena'], 'attempts': attempt+1})
        if match != 10:
            e.tap('a', transition=True); e.wait(3)
    require(e.state()['champion'] == 1 and e.read('musicIndex') == 4, 'Eleventh earned win selects Champion arrangement')
    result = score_passage(e, 4, 'champion')
    return {'policy': policy, 'ladder': ladder, 'pcm': result}


def preservation(syms, combined=False):
    if combined:
        # Parent policy checks the added animated-arena outputs, exact prior
        # addresses, immutable art/ASM, native sections and resident bank.
        # Sound semantics, PCM and every per-callback assertion remain below.
        from v029_contracts import validate
        result = validate(ROOT)
        require(result['status'] == 'passed', 'Parent v029 combined preservation policy passes')
        return {'policy': 'parent tools/v029_contracts.py', 'combined': result}
    allowed = {'assets/generated/music'+str(i)+'.it' for i in range(5)} | {
        'assets/generated/effects.it', 'assets/generated/soundbank.bnk', 'assets/generated/soundbank.asm'}
    changed = []; preserved = 0
    archive = subprocess.check_output(['git', 'archive', BASE, 'assets/generated', 'src/hardware.asm', 'src/trace.asm'], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as items:
        for item in items:
            if not item.isfile(): continue
            old, new = items.extractfile(item).read(), (ROOT/item.name).read_bytes()
            if Path(item.name).suffix in ('.asm', '.h', '.json'):
                old, new = old.replace(b'\r\n', b'\n'), new.replace(b'\r\n', b'\n')
            if old != new: changed.append(item.name)
            elif item.name.startswith('assets/generated/'): preserved += 1
    require(set(changed) <= allowed, 'Only the eight allowed audio outputs change; visual/native ASM bytes preserved', changed)
    old = symbols(subprocess.check_output(['git', 'show', BASE+':dist/abaqus-after-hours.sym'], cwd=ROOT).decode())
    ram = lambda v: v < 0x2000 or 0x7e0000 <= v < 0x800000
    prior = {n:v for n,v in old.items() if ram(v)}
    # Integration scaffold adds all reservations; base dist predates scaffold.
    markers = {'SECTIONEND_globram.data', 'RAM_USAGE_SLOT_3_BANK_127_END'}
    moved = {n:[v, syms.get(n)] for n,v in prior.items() if syms.get(n) != v}
    added = {n:v for n,v in syms.items() if ram(v) and n not in old}
    reservations = {'v29DefenseState', 'v29BonusState', 'v29AutoState', 'v29RandomState', 'v29AudioState', 'v29ArenaState'}
    require(set(moved) <= markers and set(added) == reservations,
            'Old variable/data RAM addresses fixed; only six pre-reserved arrays added', [moved, added])
    return {'baseline': BASE, 'changed': changed, 'generated_preserved': preserved,
            'old_ram_count': len(prior), 'markers': moved, 'scaffold_reservations': added,
            'soundbank': soundbank_budget(ROOT/'assets/generated/soundbank.bnk')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core', choices=('snes9x', 'accuracy'), required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--captures', type=Path, default=ROOT/'docs/audio29')
    parser.add_argument('--skip-champion', action='store_true')
    parser.add_argument('--combined', action='store_true',
                        help='Use parent v029 preservation policy for merged arena assets')
    parser.add_argument('--champion-policy', choices=('legacy','defense'), default='legacy',
                        help='Keep historical policy or pressure visible recovery under reviewed wake defense')
    args = parser.parse_args(); folder = args.captures.resolve()/args.core; folder.mkdir(parents=True, exist_ok=True)
    syms = symbols((ROOT/'dist/abaqus-after-hours.sym').read_text())
    paths = sorted([p for base in ('src', 'tools') for p in (ROOT/base).iterdir()
                    if p.is_file() and p.suffix in ('.py', '.h', '.asm', '.c')])
    paths += sorted((ROOT/'assets/audio').rglob('*'))
    inputs = {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in paths if p.is_file()}
    report = {'status': 'failed', 'scope': ('topic5 focused proof on merged v029 context; parent owns final combined suites/reproduction'
                                          if args.combined else 'isolated topic5; parent owns combined suites/reproduction'),
              'combined_preservation': args.combined,
              'rom_sha256': sha((ROOT/'dist/abaqus-after-hours.sfc').read_bytes()), 'core': args.core,
              'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'inputs': inputs, 'host': host_contract(), 'checks': CHECKS, 'media': MEDIA,
              'harness_sha256': sha(Path(__file__).read_bytes()),
              'human_listening_approved': False, 'cases': []}
    started = time.monotonic(); e = None
    try:
        report['core_identity'] = core_identity() if args.core == 'snes9x' else verify_manifest_and_pinned_core()
        report['preservation'] = preservation(syms, args.combined)
        e = Native(args.core, syms, folder); e.run(120, transition=True)
        title_full = score_passage(e, 0, 'menu'); title = title_full['excerpt']
        report['menu'] = title_full; report['cases'].append(e.finish()); e.close()
        scores = []
        for stage in range(3):
            e = Native(args.core, syms, folder); intro = boot_match(e, stage)
            report.setdefault('intros', []).append(save_pcm(folder, 'stage'+str(stage)+'-intro', intro, e.rate))
            require({6, 7} <= {c['slot'] for c in e.cues}, 'Round/Fight announcements are real intro commands')
            complete = score_passage(e, stage+1, 'stage'+str(stage)+'-music')
            pcm = complete['excerpt']
            report.setdefault('complete_scores', []).append(complete)
            scores.append(pcm)
            report.setdefault('paired_supers', []).append(paired_supers(e, stage))
            if stage == 0:
                report['settings'] = settings(e)
                sound_page(e); level(e, 0, 0); e.tap('start')
                report['contacts'] = {}
                for name, keys, defense, distance in (
                    ('light', ['y'], [], 36), ('strong', ['a'], [], 38),
                    ('block', ['y'], ['left'], 35), ('throw', ['right', 'x'], [], 21),
                    ('knockdown', ['down', 'a'], [], 36)):
                    report['contacts'][name] = contact(e, name, keys, defense, distance)
                require(len({r['pcm']['pcm_sha256'] for r in report['contacts'].values()}) == 5,
                        'Five controller-produced contact cues have distinct music-muted native PCM')
                sound_page(e); level(e, 0, 2); e.tap('start')
                report['result'] = local_result(e)
            report['cases'].append(e.finish()); e.close()
        require(len({x['pcm_sha256'] for x in scores+[title]}) == 4, 'Menu and three stages have distinct actual PCM')
        report['scores'] = scores
        e = Native(args.core, syms, folder)
        report['training'] = training_ownership(e)
        # Restore defaults using the same UI; obtain a mixed live capture.
        sound_page(e); level(e, 0, 2); level(e, 1, 3); level(e, 2, 3); e.tap('start')
        report['mixed'] = mixed_contacts(e)
        report['cases'].append(e.finish()); e.close()
        if args.core == 'snes9x' and not args.skip_champion:
            e = Native(args.core, syms, folder); report['champion'] = champion(e, args.champion_policy)
            report['cases'].append(e.finish()); e.close()
        require(all(sha((ROOT/path).read_bytes()) == value for path, value in inputs.items()),
                'Producer/harness/dependency bytes stayed fixed through proof')
        require(all(sha((ROOT/m['file']).read_bytes()) == m['sha256'] for m in MEDIA),
                'Every retained capture matches its bound hash')
        report['status'] = 'passed'
    except Exception as error:
        if e is not None:
            report['failure_health'] = {'strict_callbacks': e.strict, 'max_fifo': e.max_fifo,
                                         'failures': e.failures[:12]}
        report['error'] = repr(error); raise
    finally:
        if e is not None: e.close()
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        report['passed'] = sum(c['passed'] for c in CHECKS)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: report[k] for k in ('status', 'passed', 'rom_sha256', 'elapsed_seconds')}))


if __name__ == '__main__': main()
