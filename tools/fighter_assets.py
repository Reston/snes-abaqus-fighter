"""Prepare the twelve illustrated fighters for the SNES OBJ hardware.

This module only isolates, scales and quantizes the imagegen masters. It does
not paint substitute anatomy or recolor a shared body to stand in for a fighter.
"""
from array import array
import hashlib
import json
from pathlib import Path
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

# The original atlas remains the gameplay key-pose set.  The two new atlases
# deliberately use names that describe the source art rather than pretending
# they are additional gameplay states.  The native renderer can select these
# frames for the animation clock while the combat state continues to use the
# legacy pose indices above.
MOTION_POSES = ('breath-neutral', 'breath-inhale', 'breath-exhale',
                'breath-return', 'walk-forward-contact',
                'walk-forward-pass', 'walk-forward-rear-pass',
                'walk-forward-opposite', 'walk-back-contact',
                'walk-back-pass', 'walk-back-lead-pass',
                'walk-back-opposite', 'crouch-halfway',
                'jump-anticipation', 'jump-extension',
                'landing-compression')
ACTION_POSES = ('ready-guard', 'jab-retract', 'cross-windup',
                 'cross-retract', 'kick-windup', 'kick-retract',
                 'sweep-windup', 'sweep-recovery', 'block-impact',
                 'hurt-recovery', 'special-charge', 'cast-recovery',
                 'uppercut-anticipation', 'uppercut-recovery',
                 'victory-transition', 'knockout-fall')
AIRBORNE_POSES = ('upright-neutral', 'air-punch-anticipation',
                  'air-punch-active', 'air-punch-recovery',
                  'air-kick-anticipation', 'air-kick-active',
                  'air-kick-recovery', 'compact-apex-guard',
                  'thrower-grip', 'thrower-release', 'victim-lift',
                  'victim-impact', 'knockdown-launch', 'knockdown-fall',
                  'grounded-getup', 'wakeup-guard')
ANIMATION_POSES = MOTION_POSES + ACTION_POSES + AIRBORNE_POSES
ANIMATION_FRAME_COUNT = len(POSES) + len(ANIMATION_POSES)
ANIMATION_BANK_COUNT = ANIMATION_FRAME_COUNT // 8
ANIMATION_BANK_BYTES = 30720


def extract_atlas(path, alpha_threshold=200, pose_names=None):
    """Label opaque silhouettes, retaining only the selected figure's pixels.

    Sorting by foot baseline before the four-column row ordering also handles
    raised fists and kicks that extend beyond the nominal source cell edges.

    ``pose_names`` is intentionally optional: art-review tools and existing
    callers still receive the original sixteen key-pose names, while the
    animation atlases can provide their own sixteen-frame name set.  The
    extraction algorithm and its alpha-threshold semantics remain unchanged.
    """
    names = tuple(POSES if pose_names is None else pose_names)
    assert len(names) == 16, f'{path}: an atlas must contain exactly sixteen pose names'
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
    for pose, (count, box, component) in zip(names, ordered):
        figure = sheet.crop(box)
        mask = Image.new('L', figure.size)
        mask.putdata([255 if labels[y * width + x] == component else 0
                      for y in range(box[1], box[3]) for x in range(box[0], box[2])])
        figure.putalpha(mask)
        figures.append(figure)
        metadata.append({'pose': pose, 'source_box': box, 'opaque_pixels': count,
                         'alpha_threshold': alpha_threshold})
    return figures, metadata


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _palette_bytes(colors):
    """Encode RGB colors as the little-endian SNES 15-bit OBJ palette."""
    data = bytearray()
    for red, green, blue in colors:
        value = (red >> 3) | ((green >> 3) << 5) | ((blue >> 3) << 10)
        data.extend(value.to_bytes(2, 'little'))
    return bytes(data)


def _load_airborne_provenance(path):
    """Accept the two established provenance layouts without weakening checks."""
    data = json.loads(path.read_text())
    assert isinstance(data, dict), f'Invalid airborne provenance metadata: {path}'
    atlas = data.get('atlas') if isinstance(data.get('atlas'), dict) else {}
    output = data.get('output') if isinstance(data.get('output'), dict) else {}
    generation = data.get('generation') if isinstance(data.get('generation'), dict) else {}
    source_path = atlas.get('path') or output.get('path') or data.get('path')
    prompt = (data.get('prompt') or atlas.get('full_prompt') or
              generation.get('full_prompt') or data.get('full_prompt'))
    assert source_path and prompt, f'Incomplete airborne provenance metadata: {path}'
    return data


def _normalize_animation(figures, reference_height):
    """Convert one animation atlas into the legacy atlas's source units.

    This is deliberately the only resize performed before the shared native
    scale is selected.  In particular, individual walk or attack figures are
    never fitted separately to the hardware canvas: doing that is what makes
    a character appear to grow and shrink from pose to pose.
    """
    assert figures and figures[0].height > 0
    source_scale = reference_height / figures[0].height
    normalized = []
    for figure in figures:
        size = (max(1, round(figure.width * source_scale)),
                max(1, round(figure.height * source_scale)))
        normalized.append(figure.resize(size, Image.Resampling.NEAREST))
    # The neutral frame is the reference for the conversion.  A one-pixel
    # rounding difference is acceptable for the source raster, but a missing
    # or implausibly tiny neutral figure is a generation error, not something
    # the native pipeline should hide by compressing all other poses.
    assert normalized[0].height >= max(1, round(reference_height * .96)), \
        f'animation neutral normalized to {normalized[0].height}, expected about {reference_height}'
    return normalized, source_scale


def _fit_uniform_scale(figures, desired_scale):
    """Choose one physical scale for the stable base-48 raster set.

    The airborne/throw atlas is deliberately excluded from this calculation.
    The v0.6 contract keeps every existing frame's physical dimensions stable;
    a new drawing that does not fit at this scale is an art error.
    """
    max_width = max(figure.width for figure in figures)
    max_height = max(figure.height for figure in figures)
    uniform_scale = min(desired_scale, FIT_WIDTH / max_width,
                        FIT_HEIGHT / max_height)

    # PIL's round() can promote a .5 result above the guard by one pixel.
    # Re-evaluate using the rounded dimensions so the manifest's one scale and
    # the actual native rasters agree exactly.
    for _ in range(8):
        sizes = [(max(1, round(figure.width * uniform_scale)),
                  max(1, round(figure.height * uniform_scale)))
                 for figure in figures]
        rounded_width = max(width for width, _ in sizes)
        rounded_height = max(height for _, height in sizes)
        if rounded_width <= FIT_WIDTH and rounded_height <= FIT_HEIGHT:
            return uniform_scale
        uniform_scale *= min(FIT_WIDTH / rounded_width,
                             FIT_HEIGHT / rounded_height)
    raise AssertionError('could not fit the base 48 poses in the native canvas with one scale')


def _assert_animation_cycles(slug, figures):
    """Reject empty or duplicated generated cycles before quantization."""
    signatures = [figure.getchannel('A').tobytes() for figure in figures]
    cycles = ((16, 20, 3, 'breathing'),
              (20, 24, 3, 'forward walk'),
              (24, 28, 3, 'backward walk'),
              (28, 32, 3, 'movement transitions'),
              (32, 36, 3, 'jab/cross'),
              (36, 40, 3, 'kick/sweep'),
              (40, 44, 3, 'block/hurt/charge'),
              (44, 48, 3, 'recovery/results'),
              (48, 52, 3, 'air neutral/punch'),
              (52, 56, 3, 'air kick'),
              (56, 60, 3, 'throw'),
              (60, 64, 3, 'knockdown/recovery'))
    for start, end, minimum, name in cycles:
        unique = len(set(signatures[start:end]))
        assert unique >= minimum, \
            f'{slug}: {name} has only {unique} distinct source figures; review animation art'


def _assert_native_animation_cycles(slug, indices):
    """Require distinct frames after palette quantization and tile encoding."""
    cycles = ((16, 20, 'breathing'),
              (20, 24, 'forward walk'),
              (24, 28, 'backward walk'),
              (48, 52, 'air neutral/punch'),
              (52, 56, 'air kick'),
              (56, 60, 'throw'),
              (60, 64, 'knockdown/recovery'))
    for start, end, name in cycles:
        unique = len({bytes(frame) for frame in indices[start:end]})
        assert unique >= 3, \
            f'{slug}: native {name} cycle has only {unique} distinct indexed frames'


def _load_v05_baseline(root, output):
    """Load the committed 48-frame artifacts before writing the new manifest.

    The first 48 frames and OBJ palette are a compatibility boundary.  Keeping
    this check against the checked-in v0.5.1 manifest/binaries catches a subtle
    palette-order or rounding change even when a regenerated image still looks
    plausible.  It is loaded once, before any output is replaced.
    """
    manifest_path = output / 'character-manifest.json'
    if not manifest_path.exists():
        manifest_path = root / 'assets/generated/character-manifest.json'
    assert manifest_path.exists(), (
        'v0.5.1 character-manifest.json is required to preserve base-48 hashes; '
        'restore the committed generated assets before preparing the roster')
    baseline = json.loads(manifest_path.read_text())
    assert len(baseline) == len(SLUGS), 'v0.5.1 roster baseline must contain twelve fighters'
    result = {}
    generated = root / 'assets/generated'
    for fighter, entry in enumerate(baseline):
        assert entry.get('id') == fighter, f'v0.5.1 baseline fighter order changed at {fighter}'
        assert entry.get('frame_count', 0) >= 48 and len(entry.get('frames', [])) >= 48, \
            f'v0.5.1 baseline for fighter {fighter} has fewer than 48 frames'
        palette_path = generated / f'fighter{fighter:02}_pal.bin'
        assert palette_path.exists(), f'Missing v0.5.1 palette baseline: {palette_path}'
        result[fighter] = {
            'frames': entry['frames'][:48],
            'palette_bytes': palette_path.read_bytes(),
        }
    return result


def _assert_v05_legacy(slug, fighter, indices, palette, baseline):
    """Assert that every old native pixel hash and palette byte is unchanged."""
    expected = baseline[fighter]
    assert len(indices) >= 48
    for index, ids in enumerate(indices[:48]):
        digest = hashlib.sha256(bytes(ids)).hexdigest()
        old = expected['frames'][index]
        old_hash = old.get('native_hash') or old.get('pixels_sha256') or old.get('hash')
        assert digest == old_hash, \
            f'{slug}: base frame {index} native hash changed ({digest} != {old_hash})'
    assert _palette_bytes(palette) == expected['palette_bytes'], \
        f'{slug}: base-48 OBJ palette bytes changed; preserve v0.5.1 palette ordering'


def validate_airborne_atlas(root, fighter):
    """Validate one airborne source without writing generated artifacts.

    Art agents can call this after exporting ``animation-airborne.png``.  It
    derives the exact scale from that fighter's existing 48 sources, applies
    the frame-48 upright-anchor normalization once, and returns native boxes
    and dimensions for review.  All fixed-scale overflows are reported
    together so the source can be repaired in one pass.
    """
    root = Path(root).resolve()
    if isinstance(fighter, str):
        assert fighter in SLUGS, f'unknown fighter slug: {fighter}'
        fighter_id = SLUGS.index(fighter)
    else:
        fighter_id = int(fighter)
        assert 0 <= fighter_id < len(SLUGS), f'fighter id out of range: {fighter_id}'
    slug = SLUGS[fighter_id]
    directory = root / f'assets/art/characters/{fighter_id:02}-{slug}'
    source = directory / 'atlas.png'
    motion_source = directory / 'animation-motion.png'
    action_source = directory / 'animation-actions.png'
    airborne_source = directory / 'animation-airborne.png'
    airborne_metadata_source = directory / 'animation-airborne.json'
    for required in (source, motion_source, action_source, airborne_source):
        assert required.exists(), f'Missing airborne validation source: {required}'
    assert airborne_metadata_source.exists(), \
        f'Missing airborne provenance metadata: {airborne_metadata_source}'
    _load_airborne_provenance(airborne_metadata_source)

    figures, _ = extract_atlas(source)
    motion_figures, _ = extract_atlas(motion_source, pose_names=MOTION_POSES)
    action_figures, _ = extract_atlas(action_source, pose_names=ACTION_POSES)
    airborne_figures, airborne_metadata = extract_atlas(
        airborne_source, pose_names=AIRBORNE_POSES)
    reference_height = figures[0].height
    motion_figures, _ = _normalize_animation(motion_figures, reference_height)
    action_figures, _ = _normalize_animation(action_figures, reference_height)
    base_figures = figures + motion_figures + action_figures
    uniform_scale = _fit_uniform_scale(
        base_figures, HEIGHTS[fighter_id] / reference_height)
    airborne_figures, source_scale = _normalize_animation(
        airborne_figures, reference_height)
    all_figures = base_figures + airborne_figures
    assert len(all_figures) == ANIMATION_FRAME_COUNT
    _assert_animation_cycles(slug, all_figures)

    overflow = []
    frames = []
    for offset, (figure, item) in enumerate(zip(airborne_figures, airborne_metadata)):
        index = 48 + offset
        size = (max(1, round(figure.width * uniform_scale)),
                max(1, round(figure.height * uniform_scale)))
        if size[0] > FIT_WIDTH or size[1] > FIT_HEIGHT:
            overflow.append({'global_index': index, 'pose': item['pose'],
                             'required_native_size': list(size),
                             'fit_bounds': [FIT_WIDTH, FIT_HEIGHT]})
            continue
        resized = figure.resize(size, Image.Resampling.NEAREST)
        frame = Image.new('RGBA', (FRAME_WIDTH, FRAME_HEIGHT))
        frame.alpha_composite(resized,
                              ((FRAME_WIDTH - resized.width) // 2,
                               BASELINE_Y - resized.height))
        box = frame.getchannel('A').getbbox()
        assert box, f'{slug}/frame{index}-{item["pose"]}: figure disappeared after scaling'
        frames.append({'global_index': index, 'pose': item['pose'],
                       'native_size': list(size), 'native_box': list(box),
                       'baseline_y': BASELINE_Y})
    assert not overflow, f'{slug}: airborne art exceeds fixed base scale: {overflow}'
    return {
        'id': fighter_id,
        'name': slug,
        'source_file': str(airborne_source.relative_to(root)).replace('\\', '/'),
        'source_sha256': _sha256(airborne_source),
        'metadata_file': str(airborne_metadata_source.relative_to(root)).replace('\\', '/'),
        'metadata_sha256': _sha256(airborne_metadata_source),
        'source_scale': source_scale,
        'physical_scale': uniform_scale,
        'uniform_scale': uniform_scale,
        'frame_count': 16,
        'frames': frames,
    }


def prepare_roster(root, output):
    """Prepare twelve fighters with the stable 48 plus 16 combat frames.

    Frames 0..47 retain the v0.5.1 source order, physical scale, palette and
    indexed pixels.  ``animation-airborne.png`` supplies frames 48..63.  Its
    first upright-neutral figure is source-normalized once to the legacy idle
    height; the already-selected base-48 scale is then applied to every new
    figure without any per-pose fitting or old-frame shrink.
    """
    root = root.resolve()
    output.mkdir(parents=True, exist_ok=True)
    baseline = _load_v05_baseline(root, output)
    fighters = []
    manifests = []
    for fighter, slug in enumerate(SLUGS):
        directory = root / f'assets/art/characters/{fighter:02}-{slug}'
        source = directory / 'atlas.png'
        motion_source = directory / 'animation-motion.png'
        action_source = directory / 'animation-actions.png'
        airborne_source = directory / 'animation-airborne.png'
        airborne_metadata_source = directory / 'animation-airborne.json'
        assert source.exists(), f'Missing individual fighter master: {source}'
        assert motion_source.exists(), f'Missing motion animation atlas: {motion_source}'
        assert action_source.exists(), f'Missing action animation atlas: {action_source}'
        assert airborne_source.exists(), f'Missing airborne animation atlas: {airborne_source}'
        assert airborne_metadata_source.exists(), \
            f'Missing airborne provenance metadata: {airborne_metadata_source}'
        _load_airborne_provenance(airborne_metadata_source)
        legacy_hash = _sha256(source)
        motion_hash = _sha256(motion_source)
        action_hash = _sha256(action_source)
        airborne_hash = _sha256(airborne_source)

        figures, legacy_metadata = extract_atlas(source)
        motion_figures, motion_metadata = extract_atlas(
            motion_source, pose_names=MOTION_POSES)
        action_figures, action_metadata = extract_atlas(
            action_source, pose_names=ACTION_POSES)
        airborne_figures, airborne_metadata = extract_atlas(
            airborne_source, pose_names=AIRBORNE_POSES)
        assert len(airborne_figures) == 16 and len(airborne_metadata) == 16

        # Base-48 normalization and fitting are unchanged.  The new source is
        # normalized exactly once using frame 48's upright neutral as its
        # anchor, with the legacy idle height as the target source unit.
        reference_height = figures[0].height
        motion_figures, motion_source_scale = _normalize_animation(
            motion_figures, reference_height)
        action_figures, action_source_scale = _normalize_animation(
            action_figures, reference_height)
        desired_scale = HEIGHTS[fighter] / reference_height
        base_figures = figures + motion_figures + action_figures
        assert len(base_figures) == ANIMATION_FRAME_COUNT - len(AIRBORNE_POSES)
        uniform_scale = _fit_uniform_scale(base_figures, desired_scale)
        airborne_figures, airborne_source_scale = _normalize_animation(
            airborne_figures, reference_height)
        all_figures = base_figures + airborne_figures
        assert len(all_figures) == ANIMATION_FRAME_COUNT
        _assert_animation_cycles(slug, all_figures)

        specs = []
        for index, (figure, item) in enumerate(zip(figures, legacy_metadata)):
            specs.append((index, item['pose'], figure, 'legacy', source,
                          legacy_hash, 1.0, item))
        for index, (figure, item) in enumerate(zip(motion_figures, motion_metadata), 16):
            specs.append((index, item['pose'], figure, 'motion', motion_source,
                          motion_hash, motion_source_scale, item))
        for index, (figure, item) in enumerate(zip(action_figures, action_metadata), 32):
            specs.append((index, item['pose'], figure, 'actions', action_source,
                          action_hash, action_source_scale, item))
        for index, (figure, item) in enumerate(zip(airborne_figures, airborne_metadata), 48):
            specs.append((index, item['pose'], figure, 'airborne', airborne_source,
                          airborne_hash, airborne_source_scale, item))
        assert len(specs) == ANIMATION_FRAME_COUNT

        frames = []
        metadata = []
        for index, pose, figure, source_kind, source_path, frame_source_hash, source_scale, item in specs:
            resized_size = (max(1, round(figure.width * uniform_scale)),
                            max(1, round(figure.height * uniform_scale)))
            assert resized_size[0] <= FIT_WIDTH and resized_size[1] <= FIT_HEIGHT, (
                f'{slug}/frame{index}-{pose} exceeds {FIT_WIDTH}x{FIT_HEIGHT} at '
                f'base uniform scale {uniform_scale}: {resized_size}; repair the new art')
            resized = figure.resize(resized_size, Image.Resampling.NEAREST)
            frame = Image.new('RGBA', (FRAME_WIDTH, FRAME_HEIGHT))
            frame.alpha_composite(resized,
                                  ((FRAME_WIDTH - resized.width) // 2,
                                   BASELINE_Y - resized.height))
            alpha_box = frame.getchannel('A').getbbox()
            assert alpha_box and alpha_box[0] >= 0 and alpha_box[1] >= 0 \
                and alpha_box[2] <= FRAME_WIDTH and alpha_box[3] <= FRAME_HEIGHT, \
                f'{slug}/frame{index}-{pose} clipped in {FRAME_WIDTH}x{FRAME_HEIGHT} canvas'
            frames.append(frame)
            entry = dict(item)
            entry.update({
                'global_index': index,
                'globalindex': index,
                'pose': pose,
                'source_kind': source_kind,
                'source_file': str(source_path.relative_to(root)).replace('\\', '/'),
                'source_hash': frame_source_hash,
                'source_sha256': frame_source_hash,
                'source_scale': source_scale,
                'source_normalization': source_scale,
                'physical_scale': uniform_scale,
                'global_scale': uniform_scale,
                'uniform_scale': uniform_scale,
                'scale': uniform_scale,
                'native_size': list(resized_size),
                'native_box': list(alpha_box),
                'nativebox': list(alpha_box),
                'effective_width': alpha_box[2] - alpha_box[0],
                'effective_height': alpha_box[3] - alpha_box[1],
                'frame_canvas': [FRAME_WIDTH, FRAME_HEIGHT],
                'baseline_y': BASELINE_Y,
                'clipped': False,
            })
            entry['sourcefile'] = entry['source_file']
            entry['sourcehash'] = frame_source_hash
            metadata.append(entry)

        # The palette is intentionally derived from the base 48 only.  New
        # airborne colors are quantized into this fixed palette so old native
        # pixels and the emitted OBJ palette bytes remain byte-for-byte stable.
        base_frames = frames[:48]
        opaque = [pixel[:3] for frame in base_frames
                  for pixel in frame.get_flattened_data() if pixel[3]]
        assert opaque, f'{slug}: no opaque base animation pixels after normalization'
        strip = Image.new('RGB', (len(opaque), 1))
        strip.putdata(opaque)
        palette = strip.quantize(colors=15, method=Image.Quantize.MEDIANCUT).getpalette()[:45]
        colors = sorted({tuple((channel >> 3) << 3 for channel in palette[i:i + 3])
                         for i in range(0, 45, 3)}, key=lambda c: (sum(c), c))
        assert colors, f'{slug}: palette quantization returned no colors'
        source_color_count = len({pixel for pixel in opaque})
        assert source_color_count >= 3, \
            f'{slug}: source art has only {source_color_count} opaque RGB colors'
        assert len(colors) >= 3, \
            f'{slug}: native palette collapsed to {len(colors)} unique colors'
        colors += [colors[-1]] * (15 - len(colors))
        quantizer = Image.new('P', (1, 1))
        quantizer.putpalette(sum((list(c) for c in colors), []) + list(colors[-1]) * 241)
        indices = []
        preview = Image.new('RGBA',
                            (FRAME_WIDTH * ANIMATION_FRAME_COUNT, FRAME_HEIGHT))
        for index, frame in enumerate(frames):
            indexed = frame.convert('RGB').quantize(palette=quantizer, dither=Image.Dither.NONE)
            ids = [min(color, 14) + 1 if alpha else 0
                   for color, alpha in zip(indexed.get_flattened_data(),
                                           frame.getchannel('A').get_flattened_data())]
            indices.append(ids)
            raster = Image.new('RGBA', (FRAME_WIDTH, FRAME_HEIGHT))
            raster.putdata([((0, 0, 0, 0) if not value else colors[value - 1] + (255,))
                            for value in ids])
            preview.paste(raster, (index * FRAME_WIDTH, 0))
            native_box = raster.getchannel('A').getbbox()
            assert native_box, f'{slug}/frame{index}: quantization erased the figure'
            metadata[index]['native_box'] = list(native_box)
            metadata[index]['nativebox'] = list(native_box)
            metadata[index]['effective_width'] = native_box[2] - native_box[0]
            metadata[index]['effective_height'] = native_box[3] - native_box[1]
            frame_hash = hashlib.sha256(bytes(ids)).hexdigest()
            metadata[index]['pixels_sha256'] = frame_hash
            metadata[index]['native_hash'] = frame_hash
            metadata[index]['hash'] = frame_hash

        _assert_v05_legacy(slug, fighter, indices, [(0, 0, 0)] + colors,
                           baseline)
        _assert_native_animation_cycles(slug, indices)
        assert len({bytes(ids) for ids in indices[:16]}) >= 14, \
            f'{slug}: legacy key poses were duplicated'
        preview.save(output / f'fighter{fighter:02}.png')

        # Reuse the same illustrated face and costume for the select portrait.
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
        fighter_palette = [(0, 0, 0)] + colors
        fighters.append({
            'indices': indices,
            'palette': fighter_palette,
            'portrait': backdrop,
            'portrait_large': backdrop_large,
            'scale': uniform_scale,
            'uniform_scale': uniform_scale,
            'physical_scale': uniform_scale,
            'frame_count': ANIMATION_FRAME_COUNT,
            'pose_names': [item['pose'] for item in metadata],
            'portrait_face': backdrop,
            'portrait_face_large': backdrop_large,
        })
        manifests.append({
            'id': fighter,
            'name': slug,
            'source': str(source.relative_to(root)).replace('\\', '/'),
            'source_sha256': legacy_hash,
            'source_legacy': {
                'file': str(source.relative_to(root)).replace('\\', '/'),
                'sha256': legacy_hash,
                'frame_range': [0, 15],
            },
            'animation_sources': [
                {'file': str(motion_source.relative_to(root)).replace('\\', '/'),
                 'sha256': motion_hash, 'frame_range': [16, 31],
                 'source_scale': motion_source_scale},
                {'file': str(action_source.relative_to(root)).replace('\\', '/'),
                 'sha256': action_hash, 'frame_range': [32, 47],
                 'source_scale': action_source_scale},
                {'file': str(airborne_source.relative_to(root)).replace('\\', '/'),
                 'sha256': airborne_hash, 'frame_range': [48, 63],
                 'source_scale': airborne_source_scale,
                 'normalization_anchor': 48},
            ],
            'animation_metadata': {
                'file': str(airborne_metadata_source.relative_to(root)).replace('\\', '/'),
                'sha256': _sha256(airborne_metadata_source),
                'frame_range': [48, 63],
            },
            'frame_count': ANIMATION_FRAME_COUNT,
            'standing_height': HEIGHTS[fighter],
            'desired_standing_height': HEIGHTS[fighter],
            'effective_height': effective_height,
            'effective_standing_height': effective_standing_height,
            'effective_width': effective_width,
            'scale': uniform_scale,
            'physical_scale': uniform_scale,
            'global_scale': uniform_scale,
            'uniform_scale': uniform_scale,
            'frame_canvas': [FRAME_WIDTH, FRAME_HEIGHT],
            'fit_bounds': [FIT_WIDTH, FIT_HEIGHT],
            'baseline_y': BASELINE_Y,
            'palette': fighter_palette,
            'frames': metadata,
        })
        print(f'Prepared {slug}: 64 individual frames, 15-color OBJ palette', flush=True)
    assert len({tuple(f['indices'][0]) for f in fighters}) == 12, \
        'Roster must have twelve distinct idle drawings'
    (output / 'character-manifest.json').write_text(json.dumps(manifests, indent=2) + '\n')
    return fighters
