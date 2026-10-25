"""Original v29 arrangements and dry combat Foley, all deterministic synthesis.

No external music/sample/API inputs. Shared timbres leave room for thirteen
resident cues in bank 24. The v28 ITs/encoder remain explicit historical assets.
"""
from pathlib import Path
import hashlib
import json
import math
import random
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parents[1]


def instruments():
    rng = random.Random(2905)
    data = []
    for kind, length in enumerate((256, 256, 896, 768, 320, 256)):
        pcm = []
        for i in range(length):
            t = i/8363
            phase = math.tau*i/32
            if kind == 0:  # rounded FM reed, no buzzy sawtooth aliasing
                value = .52*math.sin(phase+.7*math.sin(phase))+.12*math.sin(2*phase)
            elif kind == 1:  # round, octave-rich electric bass
                p = phase/2
                value = .62*math.sin(p)+.18*math.sin(2*p)+.08*math.sin(3*p)
            elif kind == 2:
                value = .82*math.sin(math.tau*(58*t+2.2*(1-math.exp(-t*65))))*math.exp(-t*35)
                value += .1*rng.uniform(-1, 1)*math.exp(-t*130)
            elif kind == 3:
                value = (.64*rng.uniform(-1, 1)+.2*math.sin(math.tau*181*t))*math.exp(-t*47)
            elif kind == 4:
                value = .48*rng.uniform(-1, 1)*math.exp(-t*110)
            else:  # glass electric piano, harmonic loop with tracker envelope
                value = .53*math.sin(phase)+.19*math.sin(2*phase)+.1*math.sin(4*phase)
            pcm.append(round(max(-.95, min(.95, value))*105) & 255)
        data.append(bytes(pcm))
    return data


def write_score(path, song, samples):
    count = len(samples)
    patterns = []
    for phrase in range(4):
        rows = bytearray()
        for row in range(64):
            bar, step = phrase*4+row//16, row % 16
            root = song['roots'][bar]
            events = []
            # Authored melody cells are semitone offsets from the tonic. A
            # null cell releases the note; no sample-offset/tempo tricks.
            for position, note in zip(song['positions'], song['melody'][bar % 8]):
                if position == step:
                    events.append((0, 254 if note is None else song['tonic']+note,
                                   song['lead'], 34 if phrase == 2 else 40))
            bass_steps = (0, 6, 8, 14) if song['groove'] == 'half' else (0, 3, 8, 11)
            if step in bass_steps:
                events.append((1, root+(12 if step in (11, 14) else 0), 2, 38))
            if step in (0, 8) or (song['groove'] == 'drive' and step == 10):
                events.append((2, 60, 3, 45))
            if step in (4, 12):
                events.append((2, 60, 4, 29 if phrase != 3 else 34))
            if step in (2, 6, 10, 14):
                events.append((3, 60, 5, 15 if step in (6, 14) else 11))
            # Harmony arpeggio replaces two hats, keeping exactly four music
            # voices. It answers the lead with the glass timbre, not a drone.
            if step in (0, 8):
                events.append((3, root+24+(7 if step == 8 else song['third']), 6, 19))
            for channel, note, sample, volume in events:
                if not (0 <= channel < 4 and (0 <= note < 120 or note == 254)):
                    raise ValueError('Audio29 event escaped four-voice format')
                rows.extend((0x81+channel, 7, note, sample, volume))
            rows.append(0)
        patterns.append(struct.pack('<HHI', len(rows), 64, 0)+rows)
    header = bytearray(b'IMPM'+song['title'].encode().ljust(26, b'\0')+bytes((4, 16)))
    header += struct.pack('<8H', 5, count, count, 4, 0x214, 0x214, 13, 0)
    header += bytes((100, 64, 6, song['bpm'], 128, 0))+struct.pack('<HII', 0, 0, 0)
    header += bytes((22, 37, 32, 43)+tuple([128]*60))+bytes([64]*64)
    pos = 192+5+count*8+16
    insoff = [pos+i*554 for i in range(count)]; pos += count*554
    smpoff = [pos+i*80 for i in range(count)]; pos += count*80
    patoff = []
    for pattern in patterns:
        patoff.append(pos); pos += len(pattern)
    dataoff = []
    for sample in samples:
        dataoff.append(pos); pos += len(sample)
    out = header+bytes((0, 1, 2, 3, 255))+struct.pack('<'+'I'*count, *insoff)
    out += struct.pack('<'+'I'*count, *smpoff)+struct.pack('<4I', *patoff)
    names = ('Warm Reed', 'Round Bass', 'Dry Kick', 'Brush Snare', 'Closed Hat', 'Glass Keys')
    for index, name in enumerate(names):
        ins = bytearray(554); ins[:4] = b'IMPI'; struct.pack_into('<H', ins, 20, 256)
        ins[23:26] = bytes((60, 128, 32)); struct.pack_into('<H', ins, 28, 0x214); ins[30] = 1
        ins[32:58] = name.encode().ljust(26, b'\0')
        for note in range(120):
            ins[64+note*2:66+note*2] = bytes((note, index+1))
        if index in (0, 1, 5):
            ins[304:310] = bytes((1, 4, 0, 0, 0, 0))
            ins[310:322] = bytes((0, 0, 0, 64, 1, 0, 42, 5, 0, 0, 14 if index != 1 else 10, 0))
        out += ins
    for index, sample in enumerate(samples):
        looping = index in (0, 1, 5)
        out += (b'IMPS'+b'audio29'.ljust(12, b'\0')+bytes((0, 64, 17 if looping else 1, 50))
                +names[index].encode().ljust(26, b'\0')+bytes((1, 32))
                +struct.pack('<7I', len(sample), 0, len(sample) if looping else 0,
                             8363, 0, 0, dataoff[index])+bytes(4))
    out += b''.join(patterns)+b''.join(samples)
    if len(out) != pos:
        raise ValueError('Audio29 IT offsets differ')
    path.write_bytes(out)


def make_scores(out):
    source = json.loads((ROOT/'assets/audio/audio29/scores.json').read_text())
    samples = instruments()
    for index, song in enumerate(source['songs']):
        write_score(out/f'music{index}.it', song, samples)


def cues():
    from audio_assets import speech
    rng = random.Random(290511)

    def synth(duration, kind):
        pcm = []
        for i in range(round(duration*8000)):
            t = i/8000
            noise = rng.uniform(-1, 1)
            if kind == 'swing':
                value = (.5*noise+.3*math.sin(math.tau*(420*t+1400*t*t)))*math.sin(math.pi*t/duration)**2
            elif kind == 'light':
                value = (.58*noise*math.exp(-t*100)+.36*math.sin(math.tau*(240*t-600*t*t))*math.exp(-t*46))
            elif kind == 'strong':
                value = (.34*noise*math.exp(-t*80)+.62*math.sin(math.tau*(120*t-180*t*t))*math.exp(-t*26))
            elif kind == 'guard':
                value = (.42*math.sin(math.tau*1110*t)+.28*math.sin(math.tau*1739*t)+.18*noise)*math.exp(-t*52)
            elif kind == 'special':
                value = (.28*noise+.5*math.sin(math.tau*(340*t+2000*t*t)))*math.exp(-t*18)
            elif kind == 'throw':
                value = (.55*noise+.28*math.sin(math.tau*(370*t-1000*t*t)))*math.sin(math.pi*t/duration)**2
            else:  # landing: low floor/body impact plus short textured slap
                value = (.65*math.sin(math.tau*66*t)*math.exp(-t*27)+.28*noise*math.exp(-t*83))
            taper = min(1, i/8, (round(duration*8000)-1-i)/32)
            pcm.append(round(value*18000*taper))
        return pcm

    def chord(notes, duration, spacing):
        pcm = []
        for i in range(round(duration*8000)):
            t = i/8000; value = 0
            for index, hz in enumerate(notes):
                age = t-index*spacing
                if age > 0:
                    value += math.sin(math.tau*hz*age)*math.exp(-age*14)*min(1, age*800)
            pcm.append(round(value*5000*min(1, (duration-t)*80)))
        return pcm
    return [synth(.05, 'swing'), synth(.085, 'light'), synth(.15, 'special'),
            chord((659.25, 880), .12, .035), synth(.15, 'strong'), synth(.105, 'guard'),
            speech('round'), speech('fight'), speech('ko'),
            chord((523.25, 659.25, 783.99), .2, .025),
            chord((523.25, 659.25, 783.99, 1046.5), .42, .065),
            synth(.125, 'throw'), synth(.17, 'landing')]


def make_effects(path):
    from audio_assets import pcm8, write_effects
    return write_effects(path, [pcm8(cue) for cue in cues()])
