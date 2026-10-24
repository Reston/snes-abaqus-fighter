"""Silent native PCM/UI proof for guide-page music control on both cores."""
import ctypes as C
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import time
import wave
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emulator import Emulator, ROOT
from play_flow_media import inventory as media_inventory
import test_inputs as inputs
import test_training as training
import test_presentation as presentation
import test_compatibility as compatibility
from test_play_flow_26 import source_hashes
from test_champion import host_contract
from release_evidence import EXPECTED_NATIVE_CORE

CHECKS = []
HEALTH = {'callbacks': 0, 'max_spc_backlog': 0, 'failures': []}
OUT = ROOT / 'docs/screenshots/play-flow-v026'
AUDIO = ROOT / 'docs/audio/play-flow-v026'
SYMS = {name: int(address, 16) & 0x1ffff for address, name in re.findall(
    r'^([0-9a-fA-F]{8}) (\S+)$', (ROOT / 'dist/abaqus-after-hours.sym').read_text(), re.M)}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(ok, label, details=None):
    CHECKS.append({'check': label, 'passed': bool(ok), 'details': details})
    if not ok:
        raise AssertionError((label, details))


def read(e, name, size=1):
    return int.from_bytes(C.string_at(e.ram + SYMS[name], size), 'little')


class Rig:
    def __init__(self, independent=False):
        self.independent = independent
        self.host = compatibility.Probe() if independent else Emulator(core_options=inputs.MENU_CORE_OPTIONS)
        self.ram, self.core = self.host.ram, self.host.core
        self.cue_events = []
        self.previous_cue = 255

    @property
    def frame(self):
        frame = self.host.frame_image if self.independent else self.host.frame
        return frame.resize((256, 224), Image.Resampling.NEAREST).convert('RGB')

    def state(self):
        return inputs.trace(self)

    def run(self, count=1, p1=(), p2=()):
        for _ in range(count):
            before = inputs.trace(self)
            watch = read(self, 'screen') == 3 and before['screen'] == 3
            counters = [read(self, n, 2) for n in ('frame', 'snes_vblank_count', 'lag_frame_counter')]
            samples = self.host.audio_samples
            self.host.run(1, p1, p2)
            after = inputs.trace(self)
            if watch and read(self, 'screen') == 3 and after['screen'] == 3:
                current = [read(self, n, 2) for n in ('frame', 'snes_vblank_count', 'lag_frame_counter')]
                delta = [(a - b) & 65535 for a, b in zip(current, counters)]
                HEALTH['callbacks'] += 1
                if delta != [1, 1, 0] or (after['frame'] - before['frame']) & 65535 != 1:
                    event = {'before': counters, 'after': current, 'delta': delta, 'core': self.independent}
                    HEALTH['failures'].append(event)
                    require(False, 'music control retains strict native frame/vblank/SDK cadence', event)
                require(self.host.audio_samples > samples, 'PCM callbacks keep advancing while music is muted')
                stat = int.from_bytes(C.string_at(self.ram + 0x1ff00 + 228, 2), 'little')
                require(stat & 0xc0 == 0, 'music control stays within native OBJ scanline limits', stat)
                backlog = (read(self, 'spc_fwrite') - read(self, 'spc_fread')) & 255
                HEALTH['max_spc_backlog'] = max(HEALTH['max_spc_backlog'], backlog)
                require(backlog <= 6, 'music and cue commands retain the resident SPC FIFO bound', backlog)
            cue = read(self, 'audioLastCue')
            if cue != self.previous_cue:
                self.cue_events.append(cue)
                self.previous_cue = cue
        return inputs.trace(self)

    def tap(self, key, port=0):
        self.run(3, **{'p1' if port == 0 else 'p2': [key]})
        return self.run(3)

    def close(self):
        self.host.close()

    def begin_clip(self):
        if not self.independent:
            self.host.pcm.clear()
        self.host.audio_peak = 0
        return self.host.audio_energy, self.host.audio_samples

    def end_clip(self, name, start):
        energy = self.host.audio_energy - start[0]
        samples = self.host.audio_samples - start[1]
        require(samples > 0, 'native capture contains actual stereo PCM samples', name)
        row = {'name': name, 'samples': samples, 'rms': math.sqrt(energy / samples), 'peak': self.host.audio_peak,
               'independent': self.independent}
        require(row['peak'] < 32767, 'music-toggle PCM remains unclipped', row)
        if not self.independent:
            raw = bytes(self.host.pcm)
            require(len(raw) == samples * 2, 'capture retains every native PCM sample', name)
            path = AUDIO / (name + '.wav')
            with wave.open(str(path), 'wb') as output:
                output.setnchannels(2)
                output.setsampwidth(2)
                output.setframerate(32040)
                output.writeframes(raw)
            row.update(path=path.relative_to(ROOT).as_posix(), sha256=sha(path.read_bytes()))
        return row


def guide(e):
    inputs.press(e, 'start')
    inputs.press(e, 'select')
    e.run(8)
    require(read(e, 'paused') == 1 and read(e, 'pausePage') == 1, 'music control is reached through the existing guide')


def verify_label(e, on):
    text = 'MUSIC ON  L TO MUTE' if on else 'MUSIC OFF L TO PLAY'
    presentation.verify_opaque_text_rows(e, [(25, (32 - len(text)) // 2, text)], 'music preference')
    require(read(e, 'musicOn') == int(on), 'native music caption matches the stored preference', on)


def physics(e):
    s = training.public_state(e)
    return {k: s[k] for k in ('x1', 'x2', 'y1', 'y2', 'hp1', 'hp2', 'energy1', 'energy2',
                               'action1', 'action2', 'anim_frame1', 'anim_frame2', 'anim_tick1', 'anim_tick2',
                               'hurt1', 'hurt2', 'hitstop', 'down_state1', 'down_state2', 'wave1', 'wave2')}


def case(independent):
    original = inputs.Emulator
    inputs.Emulator = lambda **kwargs: Rig(independent)
    e = inputs.boot(2, fighter=0, fighter2=0)
    try:
        guide(e)
        verify_label(e, True)
        frozen = physics(e)
        e.run(120)
        mark = e.begin_clip()
        e.run(120)
        on = e.end_clip('music-on', mark)
        require(on['rms'] > 50, 'default paused music remains audible in native PCM', on)
        # Opposing shoulders do not toggle, even when the opposite arrives later.
        e.run(3, p2=['r'])
        e.run(3, p1=['l'], p2=['r'])
        e.run(3, p1=['l'])
        e.run(3)
        require(read(e, 'musicOn') == 1, 'held/opposite shoulders suppress guide music toggles across pads')
        e.run(48, p2=['l'])
        e.run(80)
        verify_label(e, False)
        require(read(e, 'audioVolume') == 0, 'muted module envelope reaches zero without stopping the SPC driver')
        mark = e.begin_clip()
        e.run(120)
        muted = e.end_clip('music-muted', mark)
        require(muted['rms'] <= 1 and muted['peak'] <= 4, 'muted background score is actually silent in captured PCM', muted)
        require(physics(e) == frozen, 'audio settings keep both fighters and combat clocks frozen on the guide')
        if not independent:
            e.frame.save(OUT / 'music-muted-guide.png')
        mark = e.begin_clip()
        inputs.press(e, 'right')
        e.run(20)
        cue = e.end_clip('muted-menu-cue', mark)
        require(read(e, 'audioLastCue') == 0 and cue['rms'] > 50 and cue['peak'] > 300,
                'resident navigation feedback remains audible with music off', cue)
        # Preferences survive scene reloads. Capture Round/Fight over silence.
        inputs.press(e, 'b')
        e.run(45)
        require(inputs.native_screen(e) == 1 and read(e, 'musicOn') == 0 and read(e, 'audioVolume') == 0,
                'music preference persists into the roster score')
        inputs.menu_press(e, ['a'])
        inputs.menu_press(e, ['a'])
        require(inputs.native_screen(e) == 2, 'muted rehearsal returns to its ordinary arena selection')
        first_cue = len(e.cue_events)
        mark = e.begin_clip()
        inputs.menu_press(e, ['a'])
        e.run(170)
        speech = e.end_clip('muted-round-fight', mark)
        require(6 in e.cue_events[first_cue:] and 7 in e.cue_events[first_cue:] and speech['rms'] > 50,
                'Round and Fight announcements remain audible over muted music', {'pcm': speech, 'cues': e.cue_events[first_cue:]})
        require(read(e, 'musicOn') == 0 and read(e, 'audioVolume') == 0,
                'announcer duck/restore does not unmute a muted background score')
        e.run(80)
        guide(e)
        verify_label(e, False)
        # Both pads' L edges are one shared action, rather than two toggles.
        e.run(48, p1=['l'], p2=['l'])
        e.run(80)
        verify_label(e, True)
        require(read(e, 'audioVolume') == 86, 'unmute restores the ordinary module mix smoothly')
        mark = e.begin_clip()
        e.run(120)
        restored = e.end_clip('music-restored', mark)
        require(restored['rms'] > 50, 'restored music is actually present in native PCM', restored)
        # Start/Select and Tools X retain priority over a simultaneous music edge.
        e.run(3, p1=['l'], p2=['select'])
        e.run(10)
        require(read(e, 'pausePage') == 2 and read(e, 'musicOn') == 1, 'Select owns a simultaneous guide music sample',
                {'page': read(e, 'pausePage'), 'music': read(e, 'musicOn'), 'independent': independent})
        inputs.press(e, 'select')
        require(read(e, 'pausePage') == 3, 'priority probe reaches Training Tools')
        e.run(3, p1=['x'], p2=['l'])
        e.run(12)
        require(read(e, 'pausePage') == 3 and read(e, 'musicOn') == 1, 'drill restart owns a simultaneous music sample')
        e.run(3, p1=['l'], p2=['start'])
        e.run(12)
        require(read(e, 'paused') == 0 and read(e, 'musicOn') == 1, 'Start resume owns a simultaneous music sample')
        return {'independent': independent, 'clips': [on, muted, cue, speech, restored], 'cue_events': e.cue_events}
    finally:
        e.close()
        inputs.Emulator = original


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    AUDIO.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    before = source_hashes()
    manifest = json.loads((ROOT / 'dist/manifest.json').read_bytes())
    report = {'status': 'failed', 'version': manifest['version'], 'rom_sha256': manifest['sha256'],
              'source_sha256': before, 'checks': CHECKS, 'host_contract': host_contract(), 'native_health': HEALTH,
              'controller_only': True, 'memory_writes': False, 'save_states': False, 'audio_device_opened': False}
    try:
        require(sha((ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()) == manifest['sha256'], 'music proof identifies the exact current cartridge')
        require(sha((ROOT / '.tools/core/snes9x_libretro.dll').read_bytes()).lower() == EXPECTED_NATIVE_CORE['dll_sha256'].lower(),
                'music proof uses the actual pinned Snes9x core')
        report['independent_core'] = compatibility.verify_manifest_and_pinned_core()
        report['cases'] = []
        for independent in (False, True):
            report['cases'].append(case(independent))
        require(not HEALTH['failures'], 'both-core music control has no native timing failures', HEALTH)
        require(source_hashes() == before, 'music preference and proof sources remain fixed throughout execution')
        report['captures'] = media_inventory(ROOT, 'music')
        report['status'] = 'passed'
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        report['check_count'] = len(CHECKS)
        report['presentation_checks'] = len(presentation.checks)
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
        (ROOT / 'docs/play-flow-v026-music-report.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
        print(json.dumps({k: report[k] for k in ('status', 'check_count', 'elapsed_seconds')}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
