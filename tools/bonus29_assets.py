"""Encode original imagegen office targets inside the asset transaction."""
from pathlib import Path
import hashlib
import json
import struct
from PIL import Image

ART = Path('assets/art/bonus-v029')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def tile(values):
    result = bytearray(32)
    for y in range(8):
        for x in range(8):
            for bit in range(4):
                result[(bit // 2) * 16 + y * 2 + bit % 2] |= ((values[y * 8 + x] >> bit) & 1) << (7 - x)
    return result


def target(sheet, index):
    # The authored halves are separate transparent cutouts. Fit the complete
    # silhouette, preserving aspect ratio, with a shared native feet baseline.
    w, h = sheet.size
    cut = sheet.crop((index * (w // 2), 0, (index + 1) * (w // 2), h))
    alpha = cut.getchannel('A').point(lambda value: 255 if value >= 200 else 0)
    bbox = alpha.getbbox()
    if bbox is None:
        raise ValueError('Empty authored target')
    cut = cut.crop(bbox)
    cut.thumbnail((90, 76), Image.Resampling.LANCZOS)
    native = Image.new('RGBA', (96, 80))
    native.alpha_composite(cut, ((96 - cut.width) // 2, 78 - cut.height))
    mask = list(native.getchannel('A').get_flattened_data())
    rgb = native.convert('RGB')
    # Quantize only opaque source pixels, so hidden RGB cannot consume colors.
    opaque = [color for color, alpha in zip(rgb.get_flattened_data(), mask) if alpha >= 200]
    strip = Image.new('RGB', (len(opaque), 1)); strip.putdata(opaque)
    quantized = strip.quantize(colors=15, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    colors = [tuple(quantized.getpalette()[i:i + 3]) for i in range(0, 45, 3)]
    palette = Image.new('P', (1, 1))
    palette.putpalette([component for color in colors for component in color] + [0] * (768 - 45))
    ids = list(rgb.quantize(palette=palette, dither=Image.Dither.NONE).get_flattened_data())
    ids = [min(value, 14) + 1 if alpha >= 200 else 0 for value, alpha in zip(ids, mask)]
    data = bytearray()
    for ty in range(10):
        for tx in range(12):
            data += tile([ids[(ty * 8 + y) * 96 + tx * 8 + x] for y in range(8) for x in range(8)])
    colors = [(0, 0, 0)] + colors
    packed = b''.join(struct.pack('<H', (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)) for r, g, b in colors)
    preview = Image.new('RGBA', (96, 80))
    preview.putdata([(*colors[value], 255) if value else (0, 0, 0, 0) for value in ids])
    if len(data) != 3840 or len(packed) != 32:
        raise ValueError('Target breaks actor-page geometry')
    return bytes(data), packed, preview


def install(root, out):
    root, out = Path(root), Path(out)
    source = root / ART / 'office-targets-v1.png'
    provenance = json.loads((root / ART / 'office-targets-v1.json').read_bytes())
    if provenance['mode'] != 'built-in imagegen' or sha(source.read_bytes()) != provenance['output_sha256']:
        raise ValueError('Office target source/provenance changed')
    sheet = Image.open(source).convert('RGBA')
    if sheet.getchannel('A').getextrema() != (0, 255):
        raise ValueError('Office targets require authored transparency')
    asm = (out / 'data.asm').read_text()
    header = (out / 'assets.h').read_text()
    records = []
    for index, name in enumerate(('bonus29_printer', 'bonus29_inbox')):
        pose, palette, preview = target(sheet, index)
        payloads = {name: pose, name + '_pal': palette}
        for label, payload in payloads.items():
            if label + ':' in asm:
                raise ValueError('Duplicate bonus asset declaration')
            (out / (label + '.bin')).write_bytes(payload)
            asm += '\n' + '\n'.join([f'.section "asset_{label}" superfree', label + ':',
                f'.incbin "assets/generated/{label}.bin"', label + '_end:', '.ends']) + '\n'
            header += f'extern char {label}, {label}_end;\n#define {label.upper()}_SIZE {len(payload)}\n'
        preview.save(out / (name + '.png'))
        records.append({'name': name, 'bytes': len(pose), 'palette_bytes': len(palette),
                        'pose_sha256': sha(pose), 'palette_sha256': sha(palette)})
    (out / 'data.asm').write_text(asm, newline='\n')
    (out / 'assets.h').write_text(header, newline='\n')
    report = {'scope': 'bonus-v029', 'source_sha256': sha(source.read_bytes()),
              'actor_canvas': [96, 80], 'vram_word': [0x6a00, 0x73ff],
              'cgram_color': [144, 159], 'live_target_dma': 0,
              'encoding': 'alpha>=200; aspect fit 90x76; bottom78; MEDIANCUT15; no dither; 4bpp', 'targets': records}
    (out / 'bonus29-assets.json').write_text(json.dumps(report, indent=2) + '\n', newline='\n')
    return report
