"""Fixed native review-media inventories attached by the actual producers."""
import hashlib
from pathlib import Path
import wave
from PIL import Image

SCREENSHOTS = 'docs/screenshots/play-flow-v026/'
AUDIO = 'docs/audio/play-flow-v026/'
FILES = {
    'results': ['result-p1-mirror.png', 'result-p2-mirror.png'],
    'training': [f'training-drill-{i}.png' for i in (1, 2, 3)],
    'meter': ['super-ready.png'],
    'arenas': [],
    'arcade': ['arcade-shift-01.png', 'arcade-shift-10.png', 'arcade-shift-11.png', 'arcade-next-opponent.png', 'arcade-retry-opponent.png'],
    'manual': ['training-p2-controller.png'],
    'rounds': ['round-ko-p1.png', 'round-ko-p2.png', 'round-winner-p1.png', 'round-winner-p2.png', 'round-timeout-draw.png'],
    'feedback': [f'{kind}-p{port}.png' for kind in ('punish-punch', 'punish-kick', 'counter') for port in (1, 2)],
    'previews': [f'arena-current-{stage}-{core}.png' for core in ('snes9x', 'accuracy') for stage in range(3)],
    'repeat': ['roster-hold-snes9x.gif', 'roster-hold-accuracy.gif'],
    'music': ['music-muted-guide.png'],
    'confirm': ['hit-confirm-y-x.png', 'hit-confirm-b-a.png', 'hit-confirm-late-block.png'],
    'normal-guide': ['normal-timing-p1.png', 'normal-timing-p2.png'],
    'throw': ['throw-tech-p1.png', 'throw-tech-p2.png'],
    'best': ['training-best-combo.png'],
    'session': ['local-session-2-1.png'],
    'roster': [f'roster-family-{i}.png' for i in range(4)],
    'motion': ['background-still-guide.png', 'background-moving.gif', 'background-still.gif'],
    'build': [], 'native-build': [], 'native-suite': [], 'launcher': [],
}
WAVS = ('music-on', 'music-muted', 'muted-menu-cue', 'muted-round-fight', 'music-restored')


def inventory(root, part):
    root = Path(root).resolve()
    if part not in FILES:
        raise ValueError('unknown native-media producer: ' + part)
    names = [SCREENSHOTS + name for name in FILES[part]]
    if part == 'music':
        names += [AUDIO + name + '.wav' for name in WAVS]
    records = []
    for name in names:
        path = root / name
        if not path.is_file() or not path.resolve().is_relative_to(root / 'docs'):
            raise ValueError('missing or redirected current native media: ' + name)
        raw = path.read_bytes()
        row = {'path': name, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        if path.suffix in ('.png', '.gif'):
            with Image.open(path) as image:
                if image.size != (256, 224):
                    raise ValueError('native capture dimensions differ: ' + name)
                row.update(width=256, height=224, frames=getattr(image, 'n_frames', 1))
                if path.suffix == '.gif' and row['frames'] < 2:
                    raise ValueError('native motion capture has no changing frames: ' + name)
        else:
            with wave.open(str(path), 'rb') as sound:
                if sound.getnchannels() != 2 or sound.getsampwidth() != 2 or sound.getframerate() != 32040:
                    raise ValueError('native captured PCM format differs: ' + name)
                if not sound.getnframes():
                    raise ValueError('native PCM capture is empty: ' + name)
                row.update(sample_frames=sound.getnframes(), sample_rate=32040, channels=2)
        records.append(row)
    return records
