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
# Native OBJ frames are six 16x16 pieces by five rows.  Keep a small safety
# margin inside the 96x80 canvas so a one-pixel rounding difference never
# clips an extended hand or kick at the frame edge.
FRAME_WIDTH = 96
FRAME_HEIGHT = 80
FIT_WIDTH = 94
FIT_HEIGHT = 77
BASELINE_Y = 78
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
        # One fighter scale is shared by every pose.  The idle figure sets the
        # desired standing height; the all-frame guard only reduces it when an
        # extended kick, jump, KO, etc. would exceed the native canvas.
        base_scale = HEIGHTS[fighter] / figures[0].height
        max_width = max(figure.width for figure in figures)
        max_height = max(figure.height for figure in figures)
        uniform_scale = min(base_scale, FIT_WIDTH / max_width,
                            FIT_HEIGHT / max_height)

        # PIL's round() can promote a .5 result above the guard by one pixel.
        # Re-evaluate once using the rounded dimensions so the manifest's
        # recorded scale and the actual native raster agree exactly.
        for _ in range(3):
            sizes = [(max(1, round(figure.width * uniform_scale)),
                      max(1, round(figure.height * uniform_scale)))
                     for figure in figures]
            rounded_width = max(width for width, _ in sizes)
            rounded_height = max(height for _, height in sizes)
            if rounded_width <= FIT_WIDTH and rounded_height <= FIT_HEIGHT:
                break
            uniform_scale *= min(FIT_WIDTH / rounded_width,
                                 FIT_HEIGHT / rounded_height)
        else:
            raise AssertionError(f'{slug}: could not fit all poses in the native canvas')

        frames = []
        for pose, figure in enumerate(figures):
            resized_size = (max(1, round(figure.width * uniform_scale)),
                            max(1, round(figure.height * uniform_scale)))
            assert resized_size[0] <= FIT_WIDTH and resized_size[1] <= FIT_HEIGHT, \
                f'{slug}/{POSES[pose]} exceeds {FIT_WIDTH}x{FIT_HEIGHT}: {resized_size}'
            resized = figure.resize(resized_size, Image.Resampling.NEAREST)
            frame = Image.new('RGBA', (FRAME_WIDTH, FRAME_HEIGHT))
            frame.alpha_composite(resized,
                                  ((FRAME_WIDTH - resized.width) // 2,
                                   BASELINE_Y - resized.height))
            frames.append(frame)
            alpha_box = frame.getchannel('A').getbbox()
            assert alpha_box and alpha_box[1] >= 0 and alpha_box[3] <= FRAME_HEIGHT, \
                f'{slug}/{POSES[pose]} clipped in {FRAME_WIDTH}x{FRAME_HEIGHT} canvas'
            metadata[pose]['scale'] = uniform_scale
            metadata[pose]['native_size'] = list(resized_size)
            metadata[pose]['native_box'] = list(alpha_box)
            metadata[pose]['effective_width'] = alpha_box[2] - alpha_box[0]
            metadata[pose]['effective_height'] = alpha_box[3] - alpha_box[1]
            metadata[pose]['frame_canvas'] = [FRAME_WIDTH, FRAME_HEIGHT]
            metadata[pose]['baseline_y'] = BASELINE_Y
            metadata[pose]['clipped'] = False
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
        preview = Image.new('RGBA', (FRAME_WIDTH * 16, FRAME_HEIGHT))
        for pose, frame in enumerate(frames):
            indexed = frame.convert('RGB').quantize(palette=quantizer, dither=Image.Dither.NONE)
            ids = [min(color, 14) + 1 if alpha else 0
                   for color, alpha in zip(indexed.get_flattened_data(), frame.getchannel('A').get_flattened_data())]
            indices.append(ids)
            raster = Image.new('RGBA', (FRAME_WIDTH, FRAME_HEIGHT))
            raster.putdata([((0, 0, 0, 0) if not value else colors[value - 1] + (255,)) for value in ids])
            preview.paste(raster, (pose * FRAME_WIDTH, 0))
            native_box = raster.getchannel('A').getbbox()
            metadata[pose]['native_box'] = list(native_box) if native_box else None
            metadata[pose]['effective_width'] = (native_box[2] - native_box[0]) if native_box else 0
            metadata[pose]['effective_height'] = (native_box[3] - native_box[1]) if native_box else 0
            metadata[pose]['pixels_sha256'] = hashlib.sha256(bytes(ids)).hexdigest()
        assert len({bytes(ids) for ids in indices}) >= 14, f'{slug}: animation poses were duplicated'
        preview.save(output / f'fighter{fighter:02}.png')
        # Reuse the same illustrated face and costume for the select portrait.
        # These are close face crops for every roster member.  The large copy
        # is intentionally made from the source-derived idle figure rather
        # than enlarging the 32x40 card, so menu and review art share details.
        idle = figures[0]
        portrait_fraction = .44
        portrait_center = .50
        upper = idle.crop((0, 0, idle.width,
                           max(1, round(idle.height * portrait_fraction))))
        portrait = ImageOps.fit(upper, (32, 40), Image.Resampling.NEAREST,
                                centering=(portrait_center, .18))
        portrait_large = ImageOps.fit(upper, (64, 80), Image.Resampling.NEAREST,
                                      centering=(portrait_center, .18))
        backdrop = Image.new('RGB', (32, 40), colors[0])
        backdrop.paste(portrait, (0, 0), portrait.getchannel('A'))
        backdrop_large = Image.new('RGB', (64, 80), colors[0])
        backdrop_large.paste(portrait_large, (0, 0), portrait_large.getchannel('A'))
        backdrop.save(output / f'portrait{fighter:02}.png')
        backdrop_large.save(output / f'portrait{fighter:02}-large.png')
        effective_standing_height = metadata[0]['effective_height']
        effective_height = max(item['effective_height'] for item in metadata)
        effective_width = max(item['effective_width'] for item in metadata)
        fighters.append({'indices': indices, 'palette': [(0, 0, 0)] + colors,
                         'portrait': backdrop, 'portrait_large': backdrop_large,
                         'scale': uniform_scale, 'portrait_face': backdrop,
                         'portrait_face_large': backdrop_large})
        manifests.append({'id': fighter, 'name': slug, 'source': str(source.relative_to(root)).replace('\\', '/'),
                          'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                          'standing_height': HEIGHTS[fighter],
                          'desired_standing_height': HEIGHTS[fighter],
                          'effective_height': effective_height,
                          'effective_standing_height': effective_standing_height,
                          'effective_width': effective_width,
                          'scale': uniform_scale,
                          'uniform_scale': uniform_scale,
                          'frame_canvas': [FRAME_WIDTH, FRAME_HEIGHT],
                          'fit_bounds': [FIT_WIDTH, FIT_HEIGHT],
                          'baseline_y': BASELINE_Y,
                          'palette': [(0, 0, 0)] + colors, 'frames': metadata})
        print(f'Prepared {slug}: 16 individual frames, 15-color OBJ palette', flush=True)
    assert len({tuple(f['indices'][0]) for f in fighters}) == 12, 'Roster must have twelve distinct idle drawings'
    (output / 'character-manifest.json').write_text(json.dumps(manifests, indent=2) + '\n')
    return fighters
