"""Prepare the twelve illustrated fighters for the SNES OBJ hardware.

This module only isolates, scales and quantizes the imagegen masters. It does
not paint substitute anatomy or recolor a shared body to stand in for a fighter.
"""
from array import array
import hashlib
import json
from PIL import Image, ImageOps

SLUGS = ('damian', 'ivo', 'cristobal', 'cote', 'negger', 'david',
         'fernando', 'cristian', 'mamariaga', 'reston', 'roxana', 'lars')
HEIGHTS = (69, 72, 68, 69, 72, 68, 67, 73, 66, 70, 68, 74)
FACE_PORTRAITS = (1, 2, 5, 7, 11)
POSES = ('idle', 'walk-forward', 'walk-back', 'crouch', 'jump', 'jab',
         'cross', 'kick', 'sweep', 'block', 'hurt', 'victory', 'cast',
         'uppercut', 'knockout', 'rush')


def extract_atlas(path, alpha_threshold=200):
    """Label opaque silhouettes, retaining only the selected figure's pixels.

    Sorting by foot baseline before the four-column row ordering also handles
    raised fists and kicks that extend beyond the nominal source cell edges.
    """
    sheet = Image.open(path).convert('RGBA')
    width, height = sheet.size
    # Reject translucent generation fringes: those can bridge neighboring hands
    # even though the solid illustrated figures remain fully separated.
    alpha = bytes(sheet.getchannel('A').point(lambda v: 255 if v > alpha_threshold else 0).get_flattened_data())
    labels = array('I', [0]) * len(alpha)
    components = []
    label = 0
    for start, opaque in enumerate(alpha):
        if not opaque or labels[start]:
            continue
        label += 1
        labels[start] = label
        stack = [start]
        count = 0
        left, top, right, bottom = width, height, 0, 0
        while stack:
            pixel = stack.pop()
            x, y = pixel % width, pixel // width
            count += 1
            if x < left: left = x
            if x > right: right = x
            if y < top: top = y
            if y > bottom: bottom = y
            # Explicit row bounds prevent wrapping one scanline into the next.
            neighbors = []
            if x: neighbors.append(pixel - 1)
            if x + 1 < width: neighbors.append(pixel + 1)
            if y: neighbors.append(pixel - width)
            if y + 1 < height: neighbors.append(pixel + width)
            for neighbor in neighbors:
                if alpha[neighbor] and not labels[neighbor]:
                    labels[neighbor] = label
                    stack.append(neighbor)
        if count > 700:
            components.append((count, (left, top, right + 1, bottom + 1), label))
    selected = sorted(components, reverse=True)
    assert len(selected) == 16, f'{path}: expected sixteen separate fighter silhouettes; got {len(selected)}: {[(c[0], c[1]) for c in selected]}'
    selected.sort(key=lambda item: item[1][3])
    ordered = []
    for row in range(0, 16, 4):
        ordered.extend(sorted(selected[row:row + 4], key=lambda item: item[1][0]))
    figures = []
    metadata = []
    for pose, (count, box, component) in zip(POSES, ordered):
        figure = sheet.crop(box)
        mask = Image.new('L', figure.size)
        mask.putdata([255 if labels[y * width + x] == component else 0
                      for y in range(box[1], box[3]) for x in range(box[0], box[2])])
        figure.putalpha(mask)
        figures.append(figure)
        metadata.append({'pose': pose, 'source_box': box, 'opaque_pixels': count,
                         'alpha_threshold': alpha_threshold})
    return figures, metadata


def prepare_roster(root, output):
    fighters = []
    manifests = []
    for fighter, slug in enumerate(SLUGS):
        source = root / f'assets/art/characters/{fighter:02}-{slug}/atlas.png'
        assert source.exists(), f'Missing individual fighter master: {source}'
        figures, metadata = extract_atlas(source)
        base_scale = HEIGHTS[fighter] / figures[0].height
        frames = []
        for figure in figures:
            scale = min(base_scale, 62 / figure.width, 77 / figure.height)
            resized = figure.resize((max(1, round(figure.width * scale)),
                                     max(1, round(figure.height * scale))), Image.Resampling.NEAREST)
            frame = Image.new('RGBA', (64, 80))
            frame.alpha_composite(resized, ((64 - resized.width) // 2, 78 - resized.height))
            frames.append(frame)
        # Build a per-fighter palette from opaque pixels only. Transparent black
        # cannot consume a color; all sixteen frames share the same CGRAM bank.
        opaque = [pixel[:3] for frame in frames for pixel in frame.get_flattened_data() if pixel[3]]
        strip = Image.new('RGB', (len(opaque), 1))
        strip.putdata(opaque)
        palette = strip.quantize(colors=15, method=Image.Quantize.MEDIANCUT).getpalette()[:45]
        colors = sorted({tuple((channel >> 3) << 3 for channel in palette[i:i + 3])
                         for i in range(0, 45, 3)}, key=lambda c: (sum(c), c))
        colors += [colors[-1]] * (15 - len(colors))
        quantizer = Image.new('P', (1, 1))
        quantizer.putpalette(sum((list(c) for c in colors), []) + list(colors[-1]) * 241)
        indices = []
        preview = Image.new('RGBA', (64 * 16, 80))
        for pose, frame in enumerate(frames):
            indexed = frame.convert('RGB').quantize(palette=quantizer, dither=Image.Dither.NONE)
            ids = [min(color, 14) + 1 if alpha else 0
                   for color, alpha in zip(indexed.get_flattened_data(), frame.getchannel('A').get_flattened_data())]
            indices.append(ids)
            raster = Image.new('RGBA', (64, 80))
            raster.putdata([((0, 0, 0, 0) if not value else colors[value - 1] + (255,)) for value in ids])
            preview.paste(raster, (pose * 64, 0))
            metadata[pose]['native_box'] = raster.getbbox()
            metadata[pose]['pixels_sha256'] = hashlib.sha256(bytes(ids)).hexdigest()
        assert len({bytes(ids) for ids in indices}) >= 14, f'{slug}: animation poses were duplicated'
        preview.save(output / f'fighter{fighter:02}.png')
        # Reuse the same illustrated face and costume for the select portrait.
        # This is a source-master crop, not an enlarged 64x80 runtime sprite.
        idle = figures[0]
        # The likeness pass gives the corrected faces more of the select card.
        # Keep enough collar and hair visible to preserve recognition cues.
        portrait_fraction = .40 if fighter in FACE_PORTRAITS else .56
        portrait_center = .68 if fighter in FACE_PORTRAITS else .58
        upper = idle.crop((0, 0, idle.width, round(idle.height * portrait_fraction)))
        portrait = ImageOps.fit(upper, (32, 40), Image.Resampling.NEAREST, centering=(portrait_center, .18))
        backdrop = Image.new('RGB', (32, 40), colors[0])
        backdrop.paste(portrait, (0, 0), portrait.getchannel('A'))
        backdrop.save(output / f'portrait{fighter:02}.png')
        fighters.append({'indices': indices, 'palette': [(0, 0, 0)] + colors, 'portrait': backdrop})
        manifests.append({'id': fighter, 'name': slug, 'source': str(source.relative_to(root)).replace('\\', '/'),
                          'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                          'standing_height': HEIGHTS[fighter], 'palette': [(0, 0, 0)] + colors, 'frames': metadata})
        print(f'Prepared {slug}: 16 individual frames, 15-color OBJ palette', flush=True)
    assert len({tuple(f['indices'][0]) for f in fighters}) == 12, 'Roster must have twelve distinct idle drawings'
    (output / 'character-manifest.json').write_text(json.dumps(manifests, indent=2) + '\n')
    return fighters
