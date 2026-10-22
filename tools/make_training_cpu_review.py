"""Capture opt-in CPU Training after its current-ROM native proof passes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from make_crossup_review import compact_state, process_contract, write_gif
from release_evidence import EXPECTED_NATIVE_CORE
import test_training

HELPERS = ('tools/make_training_cpu_review.py', 'tools/test_training.py',
           'tools/emulator.py', 'tools/make_crossup_review.py')
FIXTURE = {'fighter': 2, 'opponent': 11, 'stage': 2, 'difficulty': 2, 'frames': 180}


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    manifest = json.loads((ROOT/'dist/manifest.json').read_bytes())
    need(tuple(map(int, manifest['version'].split('.'))) >= (0, 17, 0),
         'CPU Training capture requires the v0.17 feature or later')
    need(digest((ROOT/'dist/abaqus-after-hours.sfc').read_bytes()) == manifest['sha256'],
         'Cartridge differs from manifest')
    source = ROOT/'docs/training-test-report.json'
    native = json.loads(source.read_bytes())
    need(native.get('status') == 'passed' and native.get('rom_sha256') == manifest['sha256'] and
         native.get('cpu_training') and native.get('passed') == len(native.get('checks', [])) and
         all(row.get('passed') for row in native['checks']), 'Current complete native Training proof is required')
    core = ROOT/'.tools/core/snes9x_libretro.dll'
    need(digest(core.read_bytes()) == EXPECTED_NATIVE_CORE['dll_sha256'], 'Expanded native core pin differs')
    host = process_contract()
    card_path = 'docs/screenshots/training/training-cpu-card.png'
    need(card_path in [str(path).replace('\\', '/') for path in native['capture_paths']],
         'CPU card must be retained by the current native suite')
    with Image.open(ROOT/card_path) as card:
        need(card.format == 'PNG' and card.size == (256, 224), 'CPU card must be a native PNG')
        card_rgb = digest(card.convert('RGB').tobytes())
    card = {'png': card_path, 'png_bytes': (ROOT/card_path).stat().st_size,
            'png_sha256': digest((ROOT/card_path).read_bytes()), 'source_rgb_sha256': card_rgb,
            'native_dimensions': [256, 224], 'source': 'current native Training suite'}
    test_training.CHECKS.clear()
    q = test_training.boot(ROOT/'dist/abaqus-after-hours.sfc', fighter=FIXTURE['fighter'],
                           fighter2=FIXTURE['opponent'], stage=FIXTURE['stage'],
                           difficulty=FIXTURE['difficulty'], label='cpu-training-review')
    images, trace, callbacks = [], [], []
    try:
        test_training.pause(q)
        test_training.set_dummy(q, 4)
        test_training.resume(q)
        for _ in range(FIXTURE['frames']):
            state = q.step()
            image = q.emulator.frame
            need(image is not None and image.size == (256, 224), 'Native callback frame is missing')
            images.append(image.convert('RGB').copy())
            row = compact_state(state)
            row.update({key: state[key] for key in ('mode', 'training_dummy', 'seconds', 'paused', 'intro', 'round_end',
                                                    'fighter_id1', 'fighter_id2', 'arena')})
            trace.append(row)
            callbacks.append(q.emulator.frames)
    finally:
        q.close()
    need(all(row['mode'] == 2 and row['training_dummy'] == 4 and row['seconds'] == 99 and
             row['fighter_id1'] == FIXTURE['fighter'] and row['fighter_id2'] == FIXTURE['opponent'] and
             row['arena'] == FIXTURE['stage'] and
             row['paused'] == row['intro'] == row['round_end'] == 0 for row in trace),
         'Review must stay in live untimed CPU Training')
    proof = {'moving_frames': sum(row['x2'] != trace[0]['x2'] for row in trace),
             'attack_frames': sum(row['action2'] != 0 for row in trace),
             'damage_frames': sum(row['hp1'] < 128 for row in trace)}
    need(all(proof.values()), 'Training clip must show real CPU movement, attacks and damage')
    need(callbacks == list(range(callbacks[0], callbacks[0]+len(callbacks))) and
         all((b['frame']-a['frame']) & 0xffff == 1 for a, b in zip(trace, trace[1:])),
         'Review must retain consecutive native video callbacks')
    gif = ROOT/'docs/screenshots/training-cpu/practice.gif'
    decoded, gif_sha = write_gif(gif, images)
    capture = {'gif': gif.relative_to(ROOT).as_posix(), 'gif_bytes': gif.stat().st_size,
               'gif_sha256': gif_sha, 'decoded_gif_frames': decoded, 'frames': len(images),
               'native_frame_numbers': [row['frame'] for row in trace],
               'host_video_callback_frames': callbacks, 'trace': trace, 'proof': proof,
               'source_rgb_sha256': [digest(image.tobytes()) for image in images],
               'gif_timing': {'fixed_rate_inspection_sweep': True, 'duration_ms_cycle': [20, 20, 10],
                              'average_duration_ms': 50/3, 'gif_centisecond_quantization': True,
                              'note': 'Native callback pixels; GIF playback timing is approximate.'}}
    report = {'status': 'passed', 'version': manifest['version'], 'rom_sha256': manifest['sha256'],
              'rom_bytes': manifest['bytes'], 'header_checksum': manifest['checksum'],
              'scope': 'Native CPU Training review aid; trusted recorded execution, human gameplay/balance remains open',
              'native_dimensions': [256, 224], 'unedited_callback_pixels': True,
              'controlled_player': 1, 'opponent': 'native CPU', 'core_sha256': digest(core.read_bytes()),
              'host_contract': host, 'fixture': FIXTURE, 'capture': capture, 'card': card,
              'source_report': 'docs/training-test-report.json',
              'source_report_comparison': 'LF-normalized JSON bytes',
              'source_report_sha256': digest(source.read_bytes().replace(b'\r\n', b'\n')),
              'harness_sha256': {name: digest((ROOT/name).read_bytes()) for name in HELPERS}}
    (ROOT/'docs/training-cpu-review.json').write_bytes((json.dumps(report, indent=2)+'\n').encode())
    print(json.dumps({'status': 'passed', 'rom_sha256': manifest['sha256'], 'frames': len(trace), 'proof': proof}))


if __name__ == '__main__':
    main()
