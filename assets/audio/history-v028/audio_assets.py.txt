"""Bounded original resident audio; no downloads, runtime synthesis or RNG drift.

The first four cues remain byte-exact. New speech comes only from the retained
project utterance WAVs exported by synthesize_announcements.ps1, never a game.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import random
import struct
import subprocess
import sys
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
NAMES = ['swing', 'light', 'special', 'legacy-confirm', 'strong', 'guard',
         'round', 'fight', 'ko', 'menu-chord', 'victory-cadence']
RATE = 8000


def speech(name):
    path = ROOT/'assets/audio/announcements'/(name+'.wav')
    with wave.open(str(path), 'rb') as source:
        if (source.getnchannels(), source.getsampwidth(), source.getframerate()) != (1, 2, 16000):
            raise ValueError('Announcement must be retained 16 kHz mono signed16 PCM')
        values = array.array('h', source.readframes(source.getnframes()))
    if sys.byteorder != 'little':
        values.byteswap()
    # Anti-alias FIR, 16->8 kHz. Preserve consonants; remove only outer silence.
    taps = []
    for n in range(-16, 17):
        sinc = .43 if n == 0 else math.sin(math.pi*.43*n)/(math.pi*n)
        taps.append(sinc*(.54+.46*math.cos(math.pi*n/16)))
    gain = sum(taps)
    filtered = [sum(values[min(len(values)-1, max(0, i+n))]*taps[n+16]
                    for n in range(-16, 17))/gain for i in range(0, len(values), 2)]
    active = [i for i, value in enumerate(filtered) if abs(value) > 140]
    if not active:
        raise ValueError('Silent announcement')
    filtered = filtered[max(0, active[0]-80):min(len(filtered), active[-1]+161)]
    peak = max(abs(value) for value in filtered)
    # About -6 dBFS source headroom, with a tiny click-preventing outer taper.
    pcm = [int(value*16000/peak*min(1, i/24, (len(filtered)-1-i)/24))
           for i, value in enumerate(filtered)]
    if not 2000 < len(pcm) < 6000:
        raise ValueError('Announcement escaped 0.25..0.75 second resident budget')
    return pcm


def new_cues():
    noise = random.Random(2210)
    strong, guard = [], []
    for i in range(1120):
        t = i/RATE
        # Strong has a low body plus a dry attack; guard is a short metal ring.
        strong.append(int(14000*(.6*math.sin(math.tau*(105*t-170*t*t))*math.exp(-t*24)
                                +.4*noise.uniform(-1, 1)*math.exp(-t*65))))
    for i in range(880):
        t = i/RATE
        guard.append(int(10500*(.42*math.sin(math.tau*1230*t)
                               +.3*math.sin(math.tau*1867*t)
                               +.28*noise.uniform(-1, 1))*math.exp(-t*44)))

    def chord(notes, duration, offsets):
        pcm = []
        for i in range(int(duration*RATE)):
            t = i/RATE
            v = 0
            for hz, start in zip(notes, offsets):
                age = t-start
                if age >= 0:
                    v += (math.sin(math.tau*hz*age)+.18*math.sin(math.tau*hz*2*age))*math.exp(-age*11)*min(1, age*500)
            pcm.append(int(v*4200*min(1, (duration-t)*100)))
        return pcm
    return [strong, guard, speech('round'), speech('fight'), speech('ko'),
            chord([523.251, 659.255, 783.991], .24, [0, .035, .07]),
            chord([523.251, 659.255, 783.991, 1046.502], .52, [0, .07, .14, .21])]


def pcm8(values):
    return bytes(max(-128, min(127, round(value/256))) & 255 for value in values)


def write_effects(path, samples):
    count = len(samples)
    if count != len(NAMES):
        raise ValueError('Resident cue identity/count changed')
    hdr = bytearray(b'IMPM'+b'Abaqus Resident Voice'.ljust(26, b'\0')+bytes([4, 16]))
    hdr += struct.pack('<8H', 2, count, count, 1, 0x214, 0x214, 13, 0)
    hdr += bytes([100, 64, 6, 125, 128, 0])+struct.pack('<HII', 0, 0, 0)
    hdr += bytes([128]*64)+bytes([64]*64)
    pos = 194+count*8+4
    ins_offsets = [pos+i*554 for i in range(count)]; pos += count*554
    smp_offsets = [pos+i*80 for i in range(count)]; pos += count*80
    pattern = struct.pack('<HHI', 64, 64, 0)+bytes(64)
    pattern_offset = pos; pos += len(pattern)
    data_offsets = []
    for data in samples:
        data_offsets.append(pos); pos += len(data)
    out = hdr+bytes([0, 255])+struct.pack('<'+'I'*count, *ins_offsets)
    out += struct.pack('<'+'I'*count, *smp_offsets)+struct.pack('<I', pattern_offset)
    for i in range(count):
        ins = bytearray(554); ins[:4] = b'IMPI'
        ins[4:16] = ('sfx'+str(i)).encode().ljust(12, b'\0')
        ins[20:22] = struct.pack('<H', 256)
        ins[23:26] = bytes([60, 128, 32]); ins[28:30] = struct.pack('<H', 0x214); ins[30] = 1
        ins[32:58] = NAMES[i].encode().ljust(26, b'\0')
        for note in range(120):
            ins[64+note*2:66+note*2] = bytes([note, i+1])
        out += ins
    for i, data in enumerate(samples):
        sh = b'IMPS'+('sfx'+str(i)).encode().ljust(12, b'\0')+bytes([0, 64, 1, 50])
        sh += NAMES[i].encode().ljust(26, b'\0')+bytes([1, 32])
        sh += struct.pack('<7I', len(data), 0, 0, RATE, 0, 0, data_offsets[i])+bytes(4)
        out += sh
    out += pattern+b''.join(samples)
    if len(out) != pos:
        raise ValueError('IT offset mismatch')
    path.write_bytes(out)
    return [hashlib.sha256(data).hexdigest() for data in samples]


def expand_effects(path, legacy):
    return write_effects(path, [pcm8(cue) for cue in legacy]+[pcm8(cue) for cue in new_cues()])


def rebuild_audio():
    """Audio-only regeneration, preserving existing scores and all visual assets."""
    out = ROOT/'assets/generated'
    raw = (out/'effects.it').read_bytes()
    orders, instruments, count = struct.unpack_from('<3H', raw, 32)
    offsets = struct.unpack_from('<'+'I'*count, raw, 192+orders+instruments*4)
    samples = []
    for offset in offsets[:4]:
        size = struct.unpack_from('<I', raw, offset+48)[0]
        start = struct.unpack_from('<I', raw, offset+72)[0]
        samples.append(raw[start:start+size])
    write_effects(out/'effects.it', samples+[pcm8(cue) for cue in new_cues()])
    command = [str(ROOT/'.tools/sdk/pvsneslib/devkitsnes/tools/smconv.exe'), '-s', '-o',
               'assets/generated/soundbank', '-b', '24', '-f', '-V', str(out/'effects.it')]
    command += [str(out/f'music{i}.it') for i in range(5)]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stdout+result.stderr)
    from victory_music import soundbank_budget
    print(json.dumps(soundbank_budget(out/'soundbank.bnk'), indent=2))


if __name__ == '__main__':
    rebuild_audio()
