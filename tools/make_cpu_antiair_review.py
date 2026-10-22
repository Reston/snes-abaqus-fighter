"""Record native CPU uppercut hit/whiff clips using the controller fixtures."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from emulator import Emulator
from make_crossup_review import RecordingEmulator, compact_state, process_contract, write_gif
from release_evidence import EXPECTED_NATIVE_CORE
import test_inputs


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def capture(name, fixture, hit):
    RecordingEmulator.instances = []
    original = test_inputs.Emulator
    test_inputs.Emulator = lambda: RecordingEmulator(Emulator)
    try:
        case = test_inputs._cpu_jump_in(**fixture)
        proof = test_inputs._cpu_uppercut_start(case, hit=hit)
    finally:
        test_inputs.Emulator = original
    require(len(RecordingEmulator.instances) == 1 and Emulator._active_instance is None,
            'CPU capture must close its one native emulator')
    samples = RecordingEmulator.instances[0].samples
    lookup = {sample['state']['frame']: index for index, sample in enumerate(samples)}
    start = max(0, lookup[case['samples'][0]['frame']]-6)
    end = lookup[case['samples'][-1]['frame']]+1
    selected = samples[start:end]
    frames = [sample['image'].convert('RGB') for sample in selected]
    require(frames and all(image.size == (256, 224) for image in frames), 'Native frame dimensions changed')
    callbacks = [sample['host_frame'] for sample in selected]
    require(callbacks == list(range(callbacks[0], callbacks[0]+len(callbacks))),
            'CPU review must retain consecutive callback frames')
    trace = [compact_state(sample['state']) for sample in selected]
    require(all((after['frame']-before['frame']) & 0xffff == 1 for before, after in zip(trace, trace[1:])),
            'CPU review telemetry cadence changed')
    target = ROOT/f'docs/screenshots/cpu-anti-air/{name}.gif'
    decoded, digest = write_gif(target, frames)
    return {'key': name, 'fixture': fixture, 'expected_hit': hit,
            'frames': len(frames), 'native_frame_numbers': [state['frame'] for state in trace],
            'host_video_callback_frames': callbacks, 'trace': trace,
            'source_rgb_sha256': [hashlib.sha256(image.tobytes()).hexdigest() for image in frames],
            'gif': target.relative_to(ROOT).as_posix(), 'gif_bytes': target.stat().st_size,
            'gif_sha256': digest, 'decoded_gif_frames': decoded,
            'gif_timing': {'fixed_rate_inspection_sweep': True, 'duration_ms_cycle': [20, 20, 10],
                           'average_duration_ms': 50/3, 'gif_centisecond_quantization': True,
                           'note': 'Native callback pixels; GIF playback timing is approximate.'},
            'proof': {'fixture_result': proof,
                      'first_uppercut_clip_frame': lookup[proof['first']['frame']]-start,
                      'first_contact_clip_frame': lookup[proof['contact']['frame']]-start if proof['contact'] else None}}


def main():
    manifest = json.loads((ROOT/'dist/manifest.json').read_bytes())
    require(sha(ROOT/'dist/abaqus-after-hours.sfc') == manifest['sha256'], 'Cartridge differs from manifest')
    require(tuple(map(int, manifest['version'].split('.'))) >= (0, 16, 0), 'CPU anti-air review requires v0.16 or later')
    core = ROOT/'.tools/core/snes9x_libretro.dll'
    require(sha(core) == EXPECTED_NATIVE_CORE['dll_sha256'], 'Expanded native core pin differs')
    host = process_contract()
    captures = [capture('hit', {'cpu_id': 4, 'difficulty': 2, 'title_delay': 0}, True),
                capture('whiff', {'cpu_id': 2, 'difficulty': 2, 'title_delay': 11,
                                  'retreat': True, 'kick': False}, False)]
    report = {'status': 'passed', 'version': manifest['version'], 'rom_sha256': manifest['sha256'],
              'rom_bytes': manifest['bytes'], 'header_checksum': manifest['checksum'],
              'scope': 'Native CPU anti-air visual review aid; no human gameplay/balance approval',
              'native_dimensions': [256, 224], 'unedited_callback_pixels': True,
              'controlled_player': 1, 'opponent': 'native CPU', 'core_sha256': sha(core),
              'host_contract': host, 'captures': captures, 'checks': test_inputs.checks,
              'harness_sha256': {name: sha(ROOT/name) for name in (
                  'tools/make_cpu_antiair_review.py', 'tools/test_inputs.py',
                  'tools/emulator.py', 'tools/make_crossup_review.py')}}
    target = ROOT/'docs/cpu-anti-air-review.json'
    target.write_bytes((json.dumps(report, indent=2)+'\n').encode())
    print(json.dumps({'status': 'passed', 'rom_sha256': manifest['sha256'],
                      'captures': [row['key'] for row in captures], 'checks': len(test_inputs.checks)}), flush=True)


if __name__ == '__main__':
    main()
