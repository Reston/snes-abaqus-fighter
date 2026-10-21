"""Supplemental silent Mesen-S verification of the unchanged release cartridge.

Uses standard Libretro pads/video/PCM and read-only WRAM. No memory writes,
savestates, frontend window, speaker playback, overclock or commercial firmware.
The existing Snes9x/bsnes release reports and package are left untouched.
"""

from __future__ import annotations

import ctypes as C
import hashlib
import json
import sys
import time
import zipfile
from collections import Counter
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_compatibility as compat
import test_compatibility_combat as combat
from longrun_host import SystemAvInfo

ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = ROOT / '.tools/mesen'
ARCHIVE = CORE_ROOT / 'mesen-s_libretro.dll.zip'
CORE = CORE_ROOT / 'mesen-s_libretro.dll'
ARCHIVE_SHA = '3bc041ce07f5645602aac9cf6682df12ff8941e6231aa621c5b2332fab96d754'
CORE_SHA = '87a90f31c331313c4f499d6dfafb59f7911bc60dbb9e10b5d96f959040441abd'
FROZEN_ROM_SHA = '76b456d1ac75471a8b9710c61b0ce4c6ab9ca344b1b8a1f17e38f36e52904466'
REPORT = ROOT / 'docs/mesen-test-report.json'
CAPTURES = ROOT / 'docs/screenshots/mesen'
OPTIONS = {
    'mesen-s_ntsc_filter': 'Disabled',
    'mesen-s_region': 'Auto',
    'mesen-s_overscan_vertical': 'None',
    'mesen-s_overscan_horizontal': 'None',
    'mesen-s_aspect_ratio': 'No Stretching',
    'mesen-s_overclock': 'None',
    'mesen-s_overclock_type': 'Before NMI',
    'mesen-s_superfx_overclock': '100%',
    'mesen-s_blend_high_res': 'disabled',
    'mesen-s_cubic_interpolation': 'disabled',
    'mesen-s_ramstate': 'Random Values (Default)',
    'mesen-s_hle_coprocessor': 'disabled',
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Variable(C.Structure):
    _fields_ = [('key', C.c_char_p), ('value', C.c_char_p)]


class MesenProbe(compat.Probe):
    """Mesen callbacks, with the existing read-only trace/menu helpers reused."""

    records = []

    def __init__(self) -> None:
        require(compat.Probe.active is None, 'another core is active')
        self.core = C.CDLL(str(CORE))
        self.closed = False
        self.loaded = False
        self.held = [set(), set()]
        self.pixel_format = 0
        self.frame_image = None
        self.raw_image = None
        self.width = self.height = self.pitch = 0
        self.raw_prefix = self.last_raw = b''
        self.video_format_history = []
        self.video_callbacks = self.audio_samples = self.audio_energy = self.audio_peak = 0
        self.runs = 0
        self.video_failures = []
        self.audio_empty_runs = 0
        self.audio_clips = 0
        self.requested_options = {}
        self.advertised_options = {}
        self.option_values = {key: value.encode() for key, value in OPTIONS.items()}
        self.directory = str(CORE_ROOT).encode('utf-8')
        ENV = C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p)
        VIDEO = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t)
        AUDIO = C.CFUNCTYPE(None, C.c_int16, C.c_int16)
        BATCH = C.CFUNCTYPE(C.c_size_t, C.POINTER(C.c_int16), C.c_size_t)
        POLL = C.CFUNCTYPE(None)
        INPUT = C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint)

        def environment(command, data):
            command &= 0xFFFF
            if command == 10 and data:
                self.pixel_format = C.cast(data, C.POINTER(C.c_uint))[0]
                return self.pixel_format in (0, 1, 2)
            if command in (2, 3, 17) and data:
                C.cast(data, C.POINTER(C.c_bool))[0] = command == 3
                return True
            if command in (9, 30, 31) and data:
                C.cast(data, C.POINTER(C.c_char_p))[0] = self.directory
                return True
            if command == 15 and data:
                var = C.cast(data, C.POINTER(Variable)).contents
                key = (var.key or b'').decode()
                value = self.option_values.get(key)
                self.requested_options[key] = None if value is None else value.decode()
                if value is None:
                    return False
                var.value = value
                return True
            if command == 16 and data:
                variables = C.cast(data, C.POINTER(Variable))
                for index in range(100):
                    if not variables[index].key:
                        break
                    self.advertised_options[variables[index].key.decode()] = variables[index].value.decode()
                return True
            if command == 24 and data:
                C.cast(data, C.POINTER(C.c_uint64))[0] = 1 << 1  # standard joypad
                return True
            if command == 39 and data:  # GET_LANGUAGE (32 is SET_SYSTEM_AV_INFO)
                C.cast(data, C.POINTER(C.c_uint))[0] = 0  # English
                return True
            if command == 47 and data:
                C.cast(data, C.POINTER(C.c_int))[0] = 3  # audio and video enabled
                return True
            return command in (1, 6, 11, 16, 18, 35, 36, 37, 42)

        def video(data, width, height, pitch):
            if not data or not width or not height:
                self.video_failures.append({'run': self.runs, 'null': True})
                return
            raw = C.string_at(data, pitch * height)
            self.raw_prefix, self.last_raw = raw[:64], raw
            packing = {0: 'BGR;15', 1: 'BGRX', 2: 'BGR;16'}[self.pixel_format]
            image = Image.frombytes('RGB', (width, height), raw, 'raw', packing, pitch)
            self.raw_image = image
            # Keep uncropped output. Native viewport is established by the smoke
            # test, then used for shared 256x224 stage-pixel checks only.
            self.frame_image = image.crop((0, 7, 256, 231)) if image.size == (256, 239) else image
            self.width, self.height, self.pitch = int(width), int(height), int(pitch)
            layout = {'pixel_format': self.pixel_format, 'width': int(width),
                      'height': int(height), 'pitch': int(pitch)}
            if layout not in self.video_format_history:
                self.video_format_history.append(layout)
            self.video_callbacks += 1

        def audio_sample(left, right):
            self.audio_samples += 2
            self.audio_peak = max(self.audio_peak, abs(int(left)), abs(int(right)))
            self.audio_energy += int(left) ** 2 + int(right) ** 2
            self.audio_clips += abs(int(left)) >= 32767
            self.audio_clips += abs(int(right)) >= 32767

        def audio_batch(data, frames):
            if data and frames:
                values = C.cast(data, C.POINTER(C.c_int16 * (frames * 2))).contents
                self.audio_samples += int(frames) * 2
                self.audio_peak = max(self.audio_peak, max(abs(int(value)) for value in values))
                self.audio_energy += sum(int(value) ** 2 for value in values)
                self.audio_clips += sum(abs(int(value)) >= 32767 for value in values)
            return frames

        self.callbacks = [ENV(environment), VIDEO(video), AUDIO(audio_sample),
                          BATCH(audio_batch), POLL(lambda: None),
                          INPUT(lambda port, device, index, button:
                                int(port < 2 and button in self.held[port]))]
        for name, callback in zip(('environment', 'video_refresh', 'audio_sample',
                                   'audio_sample_batch', 'input_poll', 'input_state'), self.callbacks):
            getattr(self.core, 'retro_set_' + name)(callback)
            if name == 'environment':
                # Mesen's renderer/input objects are allocated in retro_init;
                # unlike bsnes, its remaining callback setters need them first.
                self.core.retro_init()
        self.core.retro_get_system_info.argtypes = [C.POINTER(compat.SystemInfo)]
        info = compat.SystemInfo()
        self.core.retro_get_system_info(C.byref(info))
        self.library_name = (info.library_name or b'').decode()
        self.library_version = (info.library_version or b'').decode()
        require(self.library_name == 'Mesen-S', f'wrong engine: {self.library_name}')
        require(self.library_version == '0.4.0', f'wrong version: {self.library_version}')
        for key, value in OPTIONS.items():
            definition = self.advertised_options.get(key, '')
            choices = definition.split('; ', 1)[-1].split('|')
            require(value in choices, f'core does not advertise {key}={value}')
        self.core.retro_load_game.argtypes = [C.POINTER(compat.GameInfo)]
        self.core.retro_load_game.restype = C.c_bool
        self.core.retro_get_memory_data.argtypes = [C.c_uint]
        self.core.retro_get_memory_data.restype = C.c_void_p
        self.core.retro_get_memory_size.argtypes = [C.c_uint]
        self.core.retro_get_memory_size.restype = C.c_size_t
        self.rom = C.create_string_buffer(compat.ROM_PATH.read_bytes())
        game = compat.GameInfo(str(compat.ROM_PATH).encode(), C.cast(self.rom, C.c_void_p),
                               len(self.rom) - 1, None)
        require(self.core.retro_load_game(C.byref(game)), 'Mesen-S rejected ROM')
        self.loaded = True
        self.core.retro_set_controller_port_device.argtypes = [C.c_uint, C.c_uint]
        for port in (0, 1):
            self.core.retro_set_controller_port_device(port, 1)
        self.ram = self.core.retro_get_memory_data(2)
        self.ram_size = int(self.core.retro_get_memory_size(2))
        require(self.ram and self.ram_size >= compat.TRACE_OFFSET + 246, 'WRAM unavailable')
        self.core.retro_get_system_av_info.argtypes = [C.POINTER(SystemAvInfo)]
        av = SystemAvInfo()
        self.core.retro_get_system_av_info(C.byref(av))
        self.fps, self.sample_rate = float(av.timing.fps), float(av.timing.sample_rate)
        self.av_geometry = {key: getattr(av.geometry, key) for key in
                            ('base_width', 'base_height', 'max_width', 'max_height')}
        compat.Probe.active = self

    def state(self):
        result = super().state()
        result.update(zip(('pause_page', 'guide_build', 'training_dummy', 'guide_dirty'),
                          self.trace_words(123)[119:123]))
        return result

    def run(self, count=1, p1=(), p2=()):
        for _ in range(count):
            before = self.video_callbacks, self.audio_samples
            self.runs += 1
            super().run(1, p1, p2)
            require(self.video_callbacks - before[0] == 1, f'video callback missing at run {self.runs}')
            require((self.width, self.height, self.pitch, self.pixel_format) == (256, 239, 1024, 1),
                    f'unexpected raw video geometry at run {self.runs}: {self.video_contract()}')
            if self.audio_samples == before[1]:
                self.audio_empty_runs += 1
        return self.state()

    def frame_signature(self):
        require(self.frame_image is not None, 'no native PPU viewport')
        rgb = self.frame_image.tobytes()
        colors = self.frame_image.getcolors(256 * 224)
        require(colors is not None and len(colors) > 8, 'blank PPU viewport')
        return {'native_width': 256, 'native_height': 224,
                'raw_width': self.width, 'raw_height': self.height,
                'raw_viewport': [0, 7, 256, 231], 'distinct_rgb': len(colors),
                'sha256_rgb': hashlib.sha256(rgb).hexdigest(), 'nonblank': True}

    def capture(self, name):
        require(self.raw_image is not None, f'no raw PPU frame for {name}')
        CAPTURES.mkdir(parents=True, exist_ok=True)
        path = CAPTURES / f'{name}.png'
        self.raw_image.save(path)
        return path.relative_to(ROOT).as_posix()

    def close(self):
        if self.closed:
            return
        self.records.append({
            'library_name': self.library_name, 'library_version': self.library_version,
            'fps': self.fps, 'sample_rate': self.sample_rate, 'runs': self.runs,
            'av_geometry': self.av_geometry, 'layouts': self.video_format_history,
            'video_callbacks': self.video_callbacks, 'video_failures': self.video_failures,
            'audio_samples_int16': self.audio_samples, 'audio_empty_runs': self.audio_empty_runs,
            'audio_energy': self.audio_energy, 'audio_peak': self.audio_peak,
            'full_scale_samples': self.audio_clips,
            'expected_sample_frames': self.runs * self.sample_rate / self.fps,
            'observed_sample_frames': self.audio_samples // 2,
            'requested_options': self.requested_options,
        })
        super().close()


def verify_pins():
    require(digest(ARCHIVE) == ARCHIVE_SHA, 'Mesen archive pin mismatch; run setup-mesen.ps1')
    with zipfile.ZipFile(ARCHIVE) as archive:
        require(archive.namelist() == ['mesen-s_libretro.dll'], 'unexpected archive members')
        require(hashlib.sha256(archive.read(archive.namelist()[0])).hexdigest() == CORE_SHA,
                'Mesen archive DLL pin mismatch')
    require(digest(CORE) == CORE_SHA, 'Mesen installed DLL pin mismatch')
    manifest = json.loads(compat.MANIFEST_PATH.read_text(encoding='utf-8'))
    rom_hash = digest(compat.ROM_PATH)
    require(rom_hash == manifest['sha256'] == FROZEN_ROM_SHA, 'ROM/manifest differ from frozen v0.8.1')
    require(compat.ROM_PATH.stat().st_size == 4194304, 'ROM size differs')
    return rom_hash


def guide_settle(core):
    history = []
    for _ in range(8):
        current = core.run(1)
        history.append({key: current[key] for key in ('pause_page', 'guide_build', 'guide_dirty')})
        if current['guide_build'] == current['guide_dirty'] == 0:
            core.run(1)  # align completed native DMA and video callback
            return history
    raise AssertionError(f'guide did not publish: {history}')


def scene_check(mode):
    """Menus, both pads, all pause cards, and the native Training reset path."""
    core = MesenProbe()
    result = {'mode': mode, 'captures': [], 'guide_pages': []}
    try:
        title = core.run(120)
        require(title['magic'] == 0xAABA and title['screen'] == 0, f'no title: {title}')
        result['title'] = core.frame_signature()
        # The observed seven/eight black rows agree with the documented core
        # padding. Static stage-plate comparisons independently check alignment.
        for rect in ((0, 0, 256, 7), (0, 231, 256, 239)):
            require(core.raw_image.crop(rect).getbbox() is None, 'overscan padding is not black')
        if mode == 0:
            result['captures'].append(core.capture('title'))
        for _ in range(mode):
            compat.press(core, 'down')
        compat.press(core, 'a')
        compat.wait_screen(core, 1)
        for _ in range(9):
            compat.press(core, 'right')
        if mode == 0:
            result['captures'].append(core.capture('reston-select'))
        compat.press(core, 'a')
        # Local VS confirms P2 through its own controller port.
        if mode == 1:
            compat.press(core, 'a', 1)
        compat.wait_screen(core, 2)
        for _ in range(mode):
            compat.press(core, 'down')
        compat.press(core, 'a')
        compat.wait_screen(core, 3)
        for _ in range(180):
            if core.state()['intro'] == 0:
                break
            core.run(1)
        core.run(3)
        initial = core.state()
        require(initial['screen'] == 3 and initial['intro'] == 0 and initial['mode'] == mode,
                f'wrong live mode: {initial}')
        require(initial['fighter_id1'] == 9 and initial['arena'] == mode,
                f'loaded selection differs: {initial}')
        before = initial['x1']
        moved = core.run(6, p1=['left'])
        require(moved['x1'] < before, 'P1 controller movement missing')
        if mode == 1:
            before = moved['x2']
            moved = core.run(6, p2=['right'])
            require(moved['x2'] > before, 'P2 controller movement missing')
        jumped = core.run(4, p1=['up'])
        require(compat.signed16(jumped['y1']) < 0, 'P1 jump missing')
        for _ in range(90):
            landed = core.run(1)
            if landed['y1'] == 0:
                break
        require(core.state()['y1'] == 0, 'P1 did not land')
        compat.press(core, 'start')
        require(core.state()['paused'] == 1, 'pause did not open')
        frozen_keys = ('hp1', 'hp2', 'x1', 'x2', 'y1', 'y2', 'seconds', 'action1', 'action2',
                       'anim_frame1', 'anim_frame2', 'ambient_clock', 'ambient_phase')
        for page in range(3):
            if page:
                compat.press(core, 'select')
            history = guide_settle(core)
            state = core.state()
            require(state['pause_page'] == page and state['paused'] == 1, f'wrong guide page: {state}')
            frozen = {key: state[key] for key in frozen_keys}
            core.run(12)
            require(frozen == {key: core.state()[key] for key in frozen_keys}, 'combat advanced in pause')
            result['guide_pages'].append({'page': page, 'publication': history,
                                          'signature': core.frame_signature()})
            result['captures'].append(core.capture(f'mode{mode}-pause{page}'))
        require(len({page['signature']['sha256_rgb'] for page in result['guide_pages']}) == 3,
                'pause cards have identical actual PPU pixels')
        if mode == 2:
            compat.press(core, 'select')  # dummy selector lives on normal pause
            guide_settle(core)
            require(core.state()['pause_page'] == 0, 'normal pause did not return')
            for dummy in range(1, 4):
                compat.press(core, 'down')
                guide_settle(core)
                require(core.state()['training_dummy'] == dummy, f'dummy selection failed: {core.state()}')
            compat.press(core, 'start')
            require(core.state()['paused'] == 0, 'Training resume failed')
            air_samples = []
            takeoffs = 0
            prior_y = 0
            for _ in range(150):
                current = core.run(1)
                y = compat.signed16(current['y2'])
                takeoffs += prior_y == 0 and y < 0
                air_samples.append(y)
                prior_y = y
            require(takeoffs >= 2, f'Jump dummy did not repeat: {takeoffs}')
            compat.press(core, 'select')
            reset = core.state()
            require(reset['hp1'] == reset['hp2'] == 128 and reset['training_dummy'] == 3,
                    'Training reset did not restore HP/preserve dummy')
            result['training'] = {'dummy_takeoffs': takeoffs, 'minimum_y': min(air_samples),
                                  'reset_hp': [reset['hp1'], reset['hp2']], 'dummy_preserved': True}
        else:
            compat.press(core, 'start')
            require(core.state()['paused'] == 0, 'resume failed')
        result['passed'] = True
        return result
    finally:
        core.close()


def stage_check(stage_id, record, trace_map):
    core = MesenProbe()
    try:
        rects = compat.stage_phase_probe_rects(record)
        boot = compat.boot_match(core, stage_id, trace_map, rects)
        core.run(40)
        return {'stage_id': stage_id, 'boot': boot,
                'plate': compat.static_plate_color_agreement(core, stage_id, record),
                'phases': compat.verify_stage_phases(core, stage_id, record, trace_map),
                'pause': compat.verify_pause_freeze(core, trace_map, rects),
                'hitstop': compat.verify_hitstop_freeze(core, trace_map, rects),
                'round_end': compat.verify_round_end_freeze(core, trace_map, rects), 'passed': True}
    finally:
        core.close()


def main():
    started = time.perf_counter()
    MesenProbe.records = []
    report = {
        'status': 'failed', 'suite': 'mesen-s-supplement', 'rom': {},
        'scope': 'three-mode scene/guide smoke, stage phases/freezes, two-wave stress, 48x600 bounded combat',
        'core': {'archive_sha256': ARCHIVE_SHA, 'dll_sha256': CORE_SHA,
                 'url': 'https://buildbot.libretro.com/nightly/windows/x86_64/latest/mesen-s_libretro.dll.zip',
                 'library_name': 'Mesen-S', 'library_version': '0.4.0', 'license': 'GPL-3.0'},
        'core_options': OPTIONS, 'scenes': [], 'stages': [], 'cases': [], 'errors': [],
        'host_contract': {'controller_callbacks_only': True, 'emulated_memory_writes': 0,
                          'savestate_calls': 0, 'frontend_window_created': False,
                          'audio_device_opened': False, 'pcm_capture_only': True,
                          'overclock': False, 'power_on_ram': 'Random Values (Default)'},
        'limitations': ['Supplemental third-engine evidence; existing six-suite release gate is unchanged.',
                        '48 bounded cases are not a full ordered-pair matrix or hour-per-mode soak.',
                        'Captured PCM health is not human listening or controller/hardware approval.'],
    }
    original_combat_probe, original_compat_probe = combat.Probe, compat.Probe
    try:
        report['rom'] = {'sha256': verify_pins(), 'bytes': compat.ROM_PATH.stat().st_size}
        sources = [Path(__file__), ROOT / 'tools/test_compatibility.py',
                   ROOT / 'tools/test_compatibility_combat.py', ROOT / 'tools/test_matchups.py',
                   ROOT / 'tools/longrun_host.py']
        report['harness_sha256'] = hashlib.sha256(b''.join(path.read_bytes() for path in sources)).hexdigest()
        report['harness_sources'] = [path.relative_to(ROOT).as_posix() for path in sources]
        _, trace_map, stages = compat.load_stage_dynamics()
        report['stage_manifest_sha256'] = digest(compat.STAGE_MANIFEST_PATH)
        for mode in range(3):
            report['scenes'].append(scene_check(mode))
            print(f'Mesen scenes/guide mode {mode}: passed', flush=True)
        for stage_id in range(3):
            report['stages'].append(stage_check(stage_id, stages[stage_id], trace_map))
            print(f'Mesen stage {stage_id} phases/freezes: passed', flush=True)
        # Dependency injection changes only this process's frontend constructor,
        # not cartridge memory or any canonical bsnes report/pin/file.
        compat.Probe = MesenProbe
        report['two_low_waves'] = compat.verify_synchronized_low_wave(
            trace_map, compat.stage_phase_probe_rects(stages[0]))
        compat.Probe = original_compat_probe
        combat.Probe = MesenProbe
        cases = combat.case_matrix()
        for index, case in enumerate(cases):
            report['cases'].append(combat.run_case(*case, 600, capture=False))
            if (index + 1) % 8 == 0:
                print(f'Mesen combat: {index + 1}/{len(cases)} cases passed', flush=True)
        require(len(report['cases']) == 48, 'bounded matrix incomplete')
        require({case['stage'] for case in report['cases']} == {0, 1, 2}, 'stage coverage incomplete')
        require({case['fighter1'] for case in report['cases']} == set(range(12)), 'P1 coverage incomplete')
        require({case['fighter2'] for case in report['cases']} == set(range(12)), 'P2 coverage incomplete')
        for record in MesenProbe.records:
            require(record['video_callbacks'] == record['runs'] and not record['video_failures'], 'video cadence failed')
            require(record['audio_empty_runs'] == 0 and record['audio_energy'] > 0, 'empty PCM output')
            require(record['full_scale_samples'] == 0, 'full-scale PCM clipping')
            # Mesen's first SPC buffer is shorter by about 76 sample frames;
            # later output follows AV timing. One video frame bounds startup.
            require(abs(record['observed_sample_frames'] - record['expected_sample_frames']) <=
                    record['sample_rate'] / record['fps'], 'PCM duration differs by >1 video frame')
            require(record['requested_options']['mesen-s_overclock'] == 'None', 'overclock option not consumed')
            require(record['requested_options']['mesen-s_ramstate'] == 'Random Values (Default)', 'RAM option not consumed')
        report['summary'] = {'combat_cases': 48, 'combat_live_frames': 28800,
                             'case_stage_counts': dict(Counter(case['stage'] for case in report['cases'])),
                             'trace_non_one_deltas': sum(case['cadence']['trace_non_one_deltas'] for case in report['cases']),
                             'video_non_one_deltas': sum(case['cadence']['video_non_one_deltas'] for case in report['cases']),
                             'native_viewport': [0, 7, 256, 231], 'raw_frame': [256, 239],
                             'cold_boots': len(MesenProbe.records)}
        report['status'] = 'passed'
    except Exception as exc:
        report['errors'].append(str(exc))
        print(f'Mesen verification failed: {exc}', flush=True)
    finally:
        combat.Probe, compat.Probe = original_combat_probe, original_compat_probe
        report['hosts'] = MesenProbe.records
        report['elapsed_seconds'] = time.perf_counter() - started
        REPORT.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f"Mesen verification: {report['status']} ({report['elapsed_seconds']:.2f}s)", flush=True)
    return int(report['status'] != 'passed')


if __name__ == '__main__':
    raise SystemExit(main())
