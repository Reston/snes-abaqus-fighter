"""Prepare the twelve illustrated fighters for the SNES OBJ hardware.

This module only isolates, scales and quantizes the imagegen masters. It does
not paint substitute anatomy or recolor a shared body to stand in for a fighter.
"""
from array import array
import hashlib
import json
import math
from pathlib import Path
from PIL import Image
from portrait_assets import build_portrait_pair

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

# The v0.8 roster baseline is an immutable review artifact.  It is deliberately
# separate from assets/generated: a failed or partially completed generation
# must never be able to make its own output the next compatibility baseline.
NATIVE_BASELINE_PATH = 'assets/art/roster-baseline-v0.8.json'
NATIVE_BASELINE_SHA256 = '386a430db966c7f5c843811d78d9e06043838d8893f166bdc58637ddde773bd5'

# Art revisions are allowlisted by exact reviewed contract hash. There is
# intentionally no CLI switch that bypasses the immutable roster baseline.
NATIVE_REVISION_REGISTRY = {
    7: {
        'contract_file': 'assets/art/characters/07-cristian/native-revision.json',
        'contract_sha256': '76ee73991b65aa8f477fcb701cae14b027d8b1e3255039d7c03ba23dc7518d58',
    },
    1: {
        'contract_file': 'assets/art/characters/01-ivo/native-revision.json',
        'contract_sha256': '10f492e7d73a7beb38e3ed86cb357f3edb5432babcea37915dce7a52edbdb22c',
    },
    0: {
        'contract_file': 'assets/art/characters/00-damian/native-revision.json',
        'source_version': 'v5',
        'contract_sha256': 'b6b94f879ed72b1eb0e84e100076f6cb80fddd990c162bc0361f1cd7da4631fc',
    },
    6: {
        'contract_file': 'assets/art/characters/06-fernando/native-revision.json',
        'source_version': 'v5',
        'contract_sha256': '322d43f496156df10e1f2ef83174f95d22becdb28b2cea8e13e1015b4d7cfb72',
    },
    9: {
        'contract_file': 'assets/art/characters/09-reston/native-revision.json',
        'contract_sha256': '9b45e7dcb253a485faa28fb3c287a01399728cfafc23e7808f3bbb3f3b972dbc',
    },
    11: {
        'contract_file': 'assets/art/characters/11-lars/native-revision.json',
        'contract_sha256': '3413da731ed37a650b081fc49a03fa800c0be7c94ed04aca7747f640e3d01b27',
    },
}
REVISION_SOURCE_ROLES = ('legacy', 'motion', 'actions', 'airborne',
                         'airborne_metadata')


def extract_atlas(path, alpha_threshold=200, pose_names=None, expected_count=16):
    """Label opaque silhouettes, retaining only the selected figure's pixels.

    Sorting by foot baseline before the four-column row ordering also handles
    raised fists and kicks that extend beyond the nominal source cell edges.

    ``pose_names`` is intentionally optional: art-review tools and existing
    callers still receive the original sixteen key-pose names, while the
    animation atlases can provide their own sixteen-frame name set.  The
    extraction algorithm and its alpha-threshold semantics remain unchanged.
    """
    names = tuple(POSES if pose_names is None else pose_names)
    count_label='sixteen' if expected_count==16 else 'eight'
    if expected_count not in (8,16) or len(names)!=expected_count:
        raise AssertionError(f'{path}: an atlas must contain exactly {count_label} pose names')
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
    if not (len(selected) == expected_count):
        raise AssertionError(f'{path}: expected {count_label} separate fighter silhouettes; got {len(selected)}: {[(c[0], c[1]) for c in selected]}')
    selected.sort(key=lambda item: item[1][3])
    ordered = []
    for row in range(0, expected_count, 4):
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


def _native_frame_hashes(indices):
    """Return ordered hashes for the 96x80 indexed frame planes."""
    if not (len(indices) == ANIMATION_FRAME_COUNT):
        raise AssertionError()
    if not (all(len(frame) == FRAME_WIDTH * FRAME_HEIGHT for frame in indices)):
        raise AssertionError()
    return [hashlib.sha256(bytes(frame)).hexdigest() for frame in indices]


def _frame_hash_summary(frame_hashes):
    """Summarize ordered per-frame hashes without re-encoding tile banks."""
    if not (len(frame_hashes) == ANIMATION_FRAME_COUNT):
        raise AssertionError()
    if not (all(isinstance(value, str) and len(value) == 64
               for value in frame_hashes)):
        raise AssertionError()
    return hashlib.sha256(''.join(frame_hashes).encode('ascii')).hexdigest()


def _palette_colors_from_bytes(data):
    """Decode the exact sixteen-color SNES palette used by a revision."""
    if not (len(data) == 32):
        raise AssertionError(f'OBJ palette must contain sixteen little-endian colors: {len(data)}')
    colors = []
    for offset in range(0, len(data), 2):
        value = int.from_bytes(data[offset:offset + 2], 'little')
        colors.append(((value & 0x1f) << 3,
                       ((value >> 5) & 0x1f) << 3,
                       ((value >> 10) & 0x1f) << 3))
    return colors


def _assert_same_scale(actual, expected, label):
    if not (isinstance(actual, (int, float)) and math.isfinite(float(actual))):
        raise AssertionError(f'{label}: invalid uniform scale {actual!r}')
    if not (isinstance(expected, (int, float)) and math.isfinite(float(expected))):
        raise AssertionError(f'{label}: invalid baseline uniform scale {expected!r}')
    if not (float(actual) == float(expected)):
        raise AssertionError(f'{label}: uniform scale changed ({actual!r} != {expected!r})')


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
    if not (isinstance(data, dict)):
        raise AssertionError(f'Invalid airborne provenance metadata: {path}')
    atlas = data.get('atlas') if isinstance(data.get('atlas'), dict) else {}
    output = data.get('output') if isinstance(data.get('output'), dict) else {}
    generation = data.get('generation') if isinstance(data.get('generation'), dict) else {}
    source_path = atlas.get('path') or output.get('path') or data.get('path')
    prompt = (data.get('prompt') or atlas.get('full_prompt') or
              generation.get('full_prompt') or data.get('full_prompt'))
    if not (source_path and prompt):
        raise AssertionError(f'Incomplete airborne provenance metadata: {path}')
    return data


def _normalize_animation(figures, reference_height):
    """Convert one animation atlas into the legacy atlas's source units.

    This is deliberately the only resize performed before the shared native
    scale is selected.  In particular, individual walk or attack figures are
    never fitted separately to the hardware canvas: doing that is what makes
    a character appear to grow and shrink from pose to pose.
    """
    if not (figures and figures[0].height > 0):
        raise AssertionError()
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
    if not (normalized[0].height >= max(1, round(reference_height * .96))):
        raise AssertionError(f'animation neutral normalized to {normalized[0].height}, expected about {reference_height}')
    return normalized, source_scale


def _normalize_animation_locked(figures, source_scale, label):
    """Normalize an approved revision with its prior atlas scale exactly."""
    if not (figures and figures[0].height > 0):
        raise AssertionError()
    if not (isinstance(source_scale, (int, float)) and math.isfinite(float(source_scale)) \
        and source_scale > 0):
        raise AssertionError(f'{label}: invalid locked source normalization')
    normalized = []
    for figure in figures:
        size = (max(1, round(figure.width * source_scale)),
                max(1, round(figure.height * source_scale)))
        normalized.append(figure.resize(size, Image.Resampling.NEAREST))
    return normalized


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
        if not (unique >= minimum):
            raise AssertionError(f'{slug}: {name} has only {unique} distinct source figures; review animation art')


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
        if not (unique >= 3):
            raise AssertionError(f'{slug}: native {name} cycle has only {unique} distinct indexed frames')


def _load_native_baseline(root):
    """Load the reviewed v0.8 64-frame baseline before any output writes."""
    path = root / NATIVE_BASELINE_PATH
    if not (path.exists()):
        raise AssertionError(f'Missing immutable native roster baseline: {path}')
    actual_hash = _sha256(path)
    if not (actual_hash == NATIVE_BASELINE_SHA256):
        raise AssertionError(f'Native roster baseline hash changed ({actual_hash} != {NATIVE_BASELINE_SHA256})')
    data = json.loads(path.read_text())
    if not (data.get('schema') == 1 and data.get('kind') == 'native-roster-baseline'):
        raise AssertionError(f'Unsupported native roster baseline schema: {path}')
    if not (data.get('version') == 'v0.8'):
        raise AssertionError(f'Unexpected native roster baseline version: {data.get("version")}')
    if not (data.get('frame_count') == ANIMATION_FRAME_COUNT):
        raise AssertionError()
    if not (data.get('frame_bytes') == FRAME_WIDTH * FRAME_HEIGHT):
        raise AssertionError()
    if not (data.get('encoded_bank_count') == ANIMATION_BANK_COUNT):
        raise AssertionError()
    if not (data.get('encoded_bank_bytes') == ANIMATION_BANK_COUNT * ANIMATION_BANK_BYTES):
        raise AssertionError()
    if not (data.get('frame_canvas') == [FRAME_WIDTH, FRAME_HEIGHT]):
        raise AssertionError()
    if not (data.get('fit_bounds') == [FIT_WIDTH, FIT_HEIGHT]):
        raise AssertionError()
    if not (data.get('baseline_y') == BASELINE_Y):
        raise AssertionError()
    entries = data.get('fighters')
    if not (isinstance(entries, list) and len(entries) == len(SLUGS)):
        raise AssertionError('Native roster baseline must contain twelve fighters')
    result = {}
    for fighter, entry in enumerate(entries):
        if not (entry.get('id') == fighter and entry.get('slug') == SLUGS[fighter]):
            raise AssertionError(f'Native roster baseline fighter order changed at {fighter}')
        if not (entry.get('frame_count') == ANIMATION_FRAME_COUNT):
            raise AssertionError()
        if not (entry.get('frame_bytes') == FRAME_WIDTH * FRAME_HEIGHT):
            raise AssertionError()
        if not (entry.get('frame_canvas') == [FRAME_WIDTH, FRAME_HEIGHT]):
            raise AssertionError()
        if not (entry.get('fit_bounds') == [FIT_WIDTH, FIT_HEIGHT]):
            raise AssertionError()
        if not (entry.get('baseline_y') == BASELINE_Y):
            raise AssertionError()
        frame_hashes = entry.get('frame_hashes')
        if not (isinstance(frame_hashes, list) and len(frame_hashes) == ANIMATION_FRAME_COUNT):
            raise AssertionError()
        if not (all(isinstance(value, str) and len(value) == 64
                   for value in frame_hashes)):
            raise AssertionError()
        if not (_frame_hash_summary(frame_hashes) == entry.get('frame_hashes_sha256')):
            raise AssertionError(f'{SLUGS[fighter]}: invalid baseline frame-hash summary')
        palette_hex = entry.get('palette_hex')
        if not (isinstance(palette_hex, str) and len(palette_hex) == 64):
            raise AssertionError()
        palette_bytes = bytes.fromhex(palette_hex)
        if not (hashlib.sha256(palette_bytes).hexdigest() == entry.get('palette_sha256')):
            raise AssertionError(f'{SLUGS[fighter]}: invalid baseline palette hash')
        if not (len(palette_bytes) == 32):
            raise AssertionError()
        source_files = entry.get('source_files')
        if not (isinstance(source_files, dict) and set(source_files) == set(REVISION_SOURCE_ROLES)):
            raise AssertionError(f'{SLUGS[fighter]}: baseline source-role set changed')
        for role in REVISION_SOURCE_ROLES:
            descriptor = source_files[role]
            if not (isinstance(descriptor, dict)):
                raise AssertionError()
            if not (isinstance(descriptor.get('file'), str)):
                raise AssertionError()
            if not (isinstance(descriptor.get('sha256'), str) and len(descriptor['sha256']) == 64):
                raise AssertionError()
            if role != 'airborne_metadata':
                scale = descriptor.get('source_normalization')
                if not (isinstance(scale, (int, float)) and math.isfinite(float(scale)) and scale > 0):
                    raise AssertionError()
        result[fighter] = {
            'id': fighter,
            'slug': SLUGS[fighter],
            'source_files': source_files,
            'frame_hashes': frame_hashes,
            'frame_hashes_sha256': entry['frame_hashes_sha256'],
            'palette_hex': palette_hex,
            'palette_bytes': palette_bytes,
            'palette_sha256': entry['palette_sha256'],
            'uniform_scale': entry.get('uniform_scale'),
            'physical_scale': entry.get('physical_scale'),
            'encoded_bank_sha256': entry.get('encoded_bank_sha256'),
        }
        _assert_same_scale(entry.get('uniform_scale'), entry.get('physical_scale'),
                           f'{SLUGS[fighter]} baseline')
    return result


def _resolve_checked_source(root, directory, descriptor, role):
    """Resolve a contract source and reject paths outside its fighter folder."""
    if not (isinstance(descriptor, dict)):
        raise AssertionError(f'{role}: source descriptor must be an object')
    relative = descriptor.get('file')
    expected_hash = descriptor.get('sha256')
    if not (isinstance(relative, str) and relative and not Path(relative).is_absolute()):
        raise AssertionError(f'{role}: source file must be a relative repository path')
    if not (isinstance(expected_hash, str) and len(expected_hash) == 64):
        raise AssertionError(f'{role}: source SHA256 is required')
    path = (root / relative).resolve()
    try:
        path.relative_to(directory.resolve())
    except ValueError:
        raise AssertionError(f'{role}: source escapes fighter directory: {relative}')
    if not (path.exists() and path.is_file()):
        raise AssertionError(f'{role}: missing source file: {path}')
    actual_hash = _sha256(path)
    if not (actual_hash == expected_hash):
        raise AssertionError(f'{role}: source hash changed ({actual_hash} != {expected_hash})')
    return path


def _assert_baseline_sources(root, directory, baseline_entry, slug):
    """Require every selected v0.8 source/provenance file to be unchanged."""
    for role in REVISION_SOURCE_ROLES:
        descriptor = baseline_entry['source_files'][role]
        path = _resolve_checked_source(root, directory, descriptor,
                                       f'{slug} baseline {role}')
        expected = (root / descriptor['file']).resolve()
        if not (path == expected):
            raise AssertionError(f'{slug}: baseline source path changed for {role}')


def _validate_revision_native_block(block, baseline_entry, label):
    """Validate old/expected native values carried by a revision contract."""
    if not (isinstance(block, dict)):
        raise AssertionError(f'{label}: native block must be an object')
    frame_hashes = block.get('frame_hashes')
    if not (isinstance(frame_hashes, list) and len(frame_hashes) == ANIMATION_FRAME_COUNT):
        raise AssertionError()
    if not (all(isinstance(value, str) and len(value) == 64 for value in frame_hashes)):
        raise AssertionError()
    summary = block.get('frame_hashes_sha256')
    if not (_frame_hash_summary(frame_hashes) == summary):
        raise AssertionError(f'{label}: invalid frame hash summary')
    palette_hex = block.get('palette_hex')
    if not (isinstance(palette_hex, str) and len(palette_hex) == 64):
        raise AssertionError()
    palette = bytes.fromhex(palette_hex)
    if not (len(palette) == 32):
        raise AssertionError()
    palette_hash = block.get('palette_sha256')
    if not (hashlib.sha256(palette).hexdigest() == palette_hash):
        raise AssertionError(f'{label}: invalid palette hash')
    scale = block.get('uniform_scale')
    _assert_same_scale(scale, block.get('physical_scale', scale), f'{label} scale')
    return {'frame_hashes': frame_hashes, 'frame_hashes_sha256': summary,
            'palette_hex': palette_hex, 'palette_bytes': palette,
            'palette_sha256': palette_hash, 'uniform_scale': scale,
            'physical_scale': block.get('physical_scale', scale)}


def _load_revision_sources(root, fighter, slug, directory, baseline_entry):
    """Resolve an explicitly allowlisted four-atlas revision, if present."""
    registry = NATIVE_REVISION_REGISTRY.get(fighter)
    source_version = registry.get('source_version', 'v4') if registry else 'v4'
    if source_version not in ('v4', 'v5'):
        raise AssertionError(f'{slug}: unsupported registered source version')
    candidates = [directory / f'{stem}-{source_version}{suffix}'
                  for stem, suffix in (('atlas', '.png'),
                                       ('animation-motion', '.png'),
                                       ('animation-actions', '.png'),
                                       ('animation-airborne', '.png'),
                                       ('animation-airborne', '.json'))]
    contract_path = root / registry['contract_file'] if registry else None
    if not registry:
        if not (not any(path.exists() for path in candidates)):
            raise AssertionError(f'{slug}: versioned art exists but this fighter has no approved revision slot')
        return None
    if not contract_path.exists() and not any(path.exists() for path in candidates):
        return None
    if not (registry and contract_path):
        raise AssertionError(f'{slug}: art revisions are not registered')
    if not (contract_path.exists()):
        raise AssertionError(f'{slug}: versioned art exists without native-revision.json')
    approved_hash = registry.get('contract_sha256')
    actual_contract_hash = _sha256(contract_path)
    if not (approved_hash):
        raise AssertionError(f'{slug}: native art revision is present but unapproved')
    if not (actual_contract_hash == approved_hash):
        raise AssertionError(f'{slug}: native revision contract hash is not allowlisted')
    contract = json.loads(contract_path.read_text())
    if not (contract.get('schema') == 1):
        raise AssertionError()
    if not (contract.get('fighter_id') == fighter and contract.get('slug') == slug):
        raise AssertionError()
    if not (contract.get('baseline', {}).get('file') == NATIVE_BASELINE_PATH):
        raise AssertionError()
    if not (contract.get('baseline', {}).get('sha256') == NATIVE_BASELINE_SHA256):
        raise AssertionError()
    provenance_files = contract.get('provenance_files')
    expected_provenance_names = (
        f'likeness-{source_version}.json', f'animation-{source_version}.json',
        f'animation-airborne-{source_version}.json')
    if not (isinstance(provenance_files, list) and len(provenance_files) == 3):
        raise AssertionError(f'{slug}: revision must pin exactly three provenance descriptors')
    provenance_paths = []
    folder = str(directory.relative_to(root)).replace('\\', '/')
    for descriptor, expected_name in zip(provenance_files, expected_provenance_names):
        if not (descriptor.get('file') == f'{folder}/{expected_name}'):
            raise AssertionError(f'{slug}: provenance path must be the reviewed same-folder {expected_name}')
        provenance_paths.append(_resolve_checked_source(
            root, directory, descriptor, f'{slug} provenance {expected_name}'))
    old_sources = contract.get('old_sources')
    new_sources = contract.get('new_sources')
    if not (isinstance(old_sources, dict) and set(old_sources) == set(REVISION_SOURCE_ROLES)):
        raise AssertionError(f'{slug}: revision old_sources must cover every atlas and provenance file')
    if not (isinstance(new_sources, dict) and set(new_sources) == set(REVISION_SOURCE_ROLES)):
        raise AssertionError(f'{slug}: revision new_sources must cover every atlas and provenance file')
    resolved_old = {}
    resolved_new = {}
    expected_new_names = {
        'legacy': f'atlas-{source_version}.png',
        'motion': f'animation-motion-{source_version}.png',
        'actions': f'animation-actions-{source_version}.png',
        'airborne': f'animation-airborne-{source_version}.png',
        'airborne_metadata': f'animation-airborne-{source_version}.json',
    }
    for role in REVISION_SOURCE_ROLES:
        old = old_sources[role]
        expected_old = baseline_entry['source_files'][role]
        if not (old.get('file') == expected_old['file'] and old.get('sha256') == expected_old['sha256']):
            raise AssertionError(f'{slug}: revision old {role} source does not match immutable baseline')
        resolved_old[role] = _resolve_checked_source(root, directory, old, f'{slug} old {role}')
        if not (Path(new_sources[role].get('file', '')).name == expected_new_names[role]):
            raise AssertionError(f'{slug}: revision {role} must use the registered {source_version} source name')
        resolved_new[role] = _resolve_checked_source(root, directory, new_sources[role],
                                                     f'{slug} new {role}')
    old_native = _validate_revision_native_block(
        contract.get('old_native'), baseline_entry, f'{slug} old_native')
    if not (old_native['frame_hashes'] == baseline_entry['frame_hashes']):
        raise AssertionError()
    if not (old_native['palette_hex'] == baseline_entry['palette_hex']):
        raise AssertionError()
    _assert_same_scale(old_native['uniform_scale'], baseline_entry['uniform_scale'],
                       f'{slug} old_native')
    expected_native = _validate_revision_native_block(
        contract.get('expected_native'), baseline_entry, f'{slug} expected_native')
    if not (expected_native['palette_hex'] == baseline_entry['palette_hex']):
        raise AssertionError(f'{slug}: revised palette must remain the immutable v0.8 OBJ palette')
    _assert_same_scale(expected_native['uniform_scale'], baseline_entry['uniform_scale'],
                       f'{slug} expected_native')
    scales = contract.get('source_normalization')
    if not (isinstance(scales, dict) and set(scales) == set(REVISION_SOURCE_ROLES) - {'airborne_metadata'}):
        raise AssertionError()
    policy = contract.get('normalization_policy', 'baseline')
    if not (policy in ('baseline', 'neutral-height')):
        raise AssertionError(f'{slug}: unknown normalization policy')
    if policy == 'neutral-height':
        # A regenerated sheet may use different source pixel units. Pin one
        # conversion for each complete atlas to the original upright height;
        # never fit individual poses or change the native physical scale.
        reference_height = extract_atlas(resolved_old['legacy'])[0][0].height
        if not (contract.get('normalization_reference_height') == reference_height):
            raise AssertionError()
    for role in ('legacy', 'motion', 'actions', 'airborne'):
        if policy == 'neutral-height':
            neutral_height = extract_atlas(resolved_new[role])[0][0].height
            expected_scale = reference_height / neutral_height
        else:
            expected_scale = baseline_entry['source_files'][role]['source_normalization']
        _assert_same_scale(scales.get(role), expected_scale,
                           f'{slug} {role} source normalization')
    return {
        'contract_file': str(contract_path.relative_to(root)).replace('\\', '/'),
        'contract_sha256': actual_contract_hash,
        'contract': contract,
        'old_sources': resolved_old,
        'new_sources': resolved_new,
        'old_native': old_native,
        'expected_native': expected_native,
        'source_normalization': scales,
        'provenance_files': provenance_paths,
    }


def _assert_native_baseline64(slug, fighter, indices, palette, uniform_scale, baseline):
    """Assert that an unchanged fighter still matches every v0.8 native frame."""
    expected = baseline[fighter]
    frame_hashes = _native_frame_hashes(indices)
    if not (frame_hashes == expected['frame_hashes']):
        raise AssertionError(f'{slug}: one or more native 64-frame hashes changed')
    if not (_frame_hash_summary(frame_hashes) == expected['frame_hashes_sha256']):
        raise AssertionError()
    palette_bytes = _palette_bytes(palette)
    if not (palette_bytes == expected['palette_bytes']):
        raise AssertionError(f'{slug}: v0.8 OBJ palette bytes changed')
    _assert_same_scale(uniform_scale, expected['uniform_scale'], f'{slug} physical scale')


def _assert_reviewed_revision(slug, fighter, indices, palette, uniform_scale, revision):
    """Assert output equals the fighter's reviewed native revision contract."""
    expected = revision['expected_native']
    frame_hashes = _native_frame_hashes(indices)
    if not (frame_hashes == expected['frame_hashes']):
        raise AssertionError(f'{slug}: native revision frame hashes differ from reviewed expectations')
    if not (_frame_hash_summary(frame_hashes) == expected['frame_hashes_sha256']):
        raise AssertionError()
    palette_bytes = _palette_bytes(palette)
    if not (palette_bytes == expected['palette_bytes']):
        raise AssertionError(f'{slug}: native revision palette differs from reviewed palette')
    _assert_same_scale(uniform_scale, expected['uniform_scale'],
                       f'{slug} reviewed physical scale')


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
        if not (fighter in SLUGS):
            raise AssertionError(f'unknown fighter slug: {fighter}')
        fighter_id = SLUGS.index(fighter)
    else:
        fighter_id = int(fighter)
        if not (0 <= fighter_id < len(SLUGS)):
            raise AssertionError(f'fighter id out of range: {fighter_id}')
    slug = SLUGS[fighter_id]
    directory = root / f'assets/art/characters/{fighter_id:02}-{slug}'
    baseline = _load_native_baseline(root)
    baseline_entry = baseline[fighter_id]
    _assert_baseline_sources(root, directory, baseline_entry, slug)
    revision = _load_revision_sources(root, fighter_id, slug, directory,
                                      baseline_entry)
    if revision:
        source = revision['new_sources']['legacy']
        motion_source = revision['new_sources']['motion']
        action_source = revision['new_sources']['actions']
        airborne_source = revision['new_sources']['airborne']
        airborne_metadata_source = revision['new_sources']['airborne_metadata']
    else:
        source = directory / 'atlas.png'
        motion_source = directory / 'animation-motion.png'
        action_source = directory / 'animation-actions.png'
        airborne_source = directory / 'animation-airborne.png'
        airborne_metadata_source = directory / 'animation-airborne.json'
    for required in (source, motion_source, action_source, airborne_source):
        if not (required.exists()):
            raise AssertionError(f'Missing airborne validation source: {required}')
    if not (airborne_metadata_source.exists()):
        raise AssertionError(f'Missing airborne provenance metadata: {airborne_metadata_source}')
    _load_airborne_provenance(airborne_metadata_source)

    figures, _ = extract_atlas(source)
    motion_figures, _ = extract_atlas(motion_source, pose_names=MOTION_POSES)
    action_figures, _ = extract_atlas(action_source, pose_names=ACTION_POSES)
    airborne_figures, airborne_metadata = extract_atlas(
        airborne_source, pose_names=AIRBORNE_POSES)
    reference_height = figures[0].height
    if revision:
        scales = revision['source_normalization']
        figures = _normalize_animation_locked(figures, scales['legacy'],
                                               f'{slug}/legacy-revision')
        motion_source_scale = scales['motion']
        action_source_scale = scales['actions']
        source_scale = scales['airborne']
        motion_figures = _normalize_animation_locked(
            motion_figures, motion_source_scale, f'{slug}/motion-revision')
        action_figures = _normalize_animation_locked(
            action_figures, action_source_scale, f'{slug}/actions-revision')
        airborne_figures = _normalize_animation_locked(
            airborne_figures, source_scale, f'{slug}/airborne-revision')
        uniform_scale = baseline_entry['uniform_scale']
    else:
        motion_figures, motion_source_scale = _normalize_animation(
            motion_figures, reference_height)
        action_figures, action_source_scale = _normalize_animation(
            action_figures, reference_height)
        uniform_scale = _fit_uniform_scale(
            figures + motion_figures + action_figures,
            HEIGHTS[fighter_id] / reference_height)
        airborne_figures, source_scale = _normalize_animation(
            airborne_figures, reference_height)
    base_figures = figures + motion_figures + action_figures
    all_figures = base_figures + airborne_figures
    if not (len(all_figures) == ANIMATION_FRAME_COUNT):
        raise AssertionError()
    _assert_animation_cycles(slug, all_figures)

    overflow = []
    frames = []
    if revision:
        for index, figure in enumerate(base_figures):
            size = (max(1, round(figure.width * uniform_scale)),
                    max(1, round(figure.height * uniform_scale)))
            if size[0] > FIT_WIDTH or size[1] > FIT_HEIGHT:
                overflow.append({'global_index': index,
                                 'required_native_size': list(size),
                                 'fit_bounds': [FIT_WIDTH, FIT_HEIGHT]})
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
        if not (box):
            raise AssertionError(f'{slug}/frame{index}-{item["pose"]}: figure disappeared after scaling')
        frames.append({'global_index': index, 'pose': item['pose'],
                       'native_size': list(size), 'native_box': list(box),
                       'baseline_y': BASELINE_Y})
    if not (not overflow):
        raise AssertionError(f'{slug}: airborne art exceeds fixed base scale: {overflow}')
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
        'palette_sha256': (revision['expected_native']['palette_sha256']
                           if revision else baseline_entry['palette_sha256']),
        'frame_count': 16,
        'frames': frames,
    }


def prepare_roster(root, output):
    """Prepare twelve fighters with the stable 48 plus 16 combat frames.

    The immutable v0.8 baseline keeps all 64 frames, palettes and scales stable.
    Only an exact, reviewed per-fighter contract may select versioned masters;
    each replacement still uses the old normalization, palette and physical
    scale. ``animation-airborne.png`` supplies frames 48..63. Its first
    upright-neutral figure is source-normalized once to the legacy idle height;
    the selected base scale is then applied to every new figure without any
    per-pose fitting or old-frame shrink.
    """
    root = root.resolve()
    baseline = _load_native_baseline(root)
    output.mkdir(parents=True, exist_ok=True)
    fighters = []
    manifests = []
    pending_images = []
    for fighter, slug in enumerate(SLUGS):
        directory = root / f'assets/art/characters/{fighter:02}-{slug}'
        baseline_entry = baseline[fighter]
        _assert_baseline_sources(root, directory, baseline_entry, slug)
        revision = _load_revision_sources(root, fighter, slug, directory,
                                           baseline_entry)
        if revision:
            source = revision['new_sources']['legacy']
            motion_source = revision['new_sources']['motion']
            action_source = revision['new_sources']['actions']
            airborne_source = revision['new_sources']['airborne']
            airborne_metadata_source = revision['new_sources']['airborne_metadata']
        else:
            source = directory / 'atlas.png'
            motion_source = directory / 'animation-motion.png'
            action_source = directory / 'animation-actions.png'
            airborne_source = directory / 'animation-airborne.png'
            airborne_metadata_source = directory / 'animation-airborne.json'
        if not (source.exists()):
            raise AssertionError(f'Missing individual fighter master: {source}')
        if not (motion_source.exists()):
            raise AssertionError(f'Missing motion animation atlas: {motion_source}')
        if not (action_source.exists()):
            raise AssertionError(f'Missing action animation atlas: {action_source}')
        if not (airborne_source.exists()):
            raise AssertionError(f'Missing airborne animation atlas: {airborne_source}')
        if not (airborne_metadata_source.exists()):
            raise AssertionError(f'Missing airborne provenance metadata: {airborne_metadata_source}')
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
        if not (len(airborne_figures) == 16 and len(airborne_metadata) == 16):
            raise AssertionError()

        # Base-48 normalization and fitting are unchanged for the normal path.
        # An approved art revision instead uses the old per-atlas conversions
        # and physical scale exactly, so a taller replacement hair silhouette
        # cannot resize or recolor the established body.
        reference_height = figures[0].height
        base_figures = figures + motion_figures + action_figures
        if revision:
            source_normalization = revision['source_normalization']
            figures = _normalize_animation_locked(
                figures, source_normalization['legacy'], f'{slug}/legacy-revision')
            motion_source_scale = source_normalization['motion']
            action_source_scale = source_normalization['actions']
            airborne_source_scale = source_normalization['airborne']
            motion_figures = _normalize_animation_locked(
                motion_figures, motion_source_scale, f'{slug}/motion-revision')
            action_figures = _normalize_animation_locked(
                action_figures, action_source_scale, f'{slug}/actions-revision')
            airborne_figures = _normalize_animation_locked(
                airborne_figures, airborne_source_scale, f'{slug}/airborne-revision')
            base_figures = figures + motion_figures + action_figures
            uniform_scale = baseline_entry['uniform_scale']
        else:
            motion_figures, motion_source_scale = _normalize_animation(
                motion_figures, reference_height)
            action_figures, action_source_scale = _normalize_animation(
                action_figures, reference_height)
            desired_scale = HEIGHTS[fighter] / reference_height
            motion_figures = motion_figures
            action_figures = action_figures
            base_figures = figures + motion_figures + action_figures
            uniform_scale = _fit_uniform_scale(base_figures, desired_scale)
            airborne_figures, airborne_source_scale = _normalize_animation(
                airborne_figures, reference_height)
        if not (len(base_figures) == ANIMATION_FRAME_COUNT - len(AIRBORNE_POSES)):
            raise AssertionError()
        if revision:
            for index, figure in enumerate(base_figures):
                size = (max(1, round(figure.width * uniform_scale)),
                        max(1, round(figure.height * uniform_scale)))
                if not (size[0] <= FIT_WIDTH and size[1] <= FIT_HEIGHT):
                    raise AssertionError(f'{slug}/frame{index} exceeds locked physical scale '
                        f'{uniform_scale}: {size}; repair the revised art')
        all_figures = base_figures + airborne_figures
        if not (len(all_figures) == ANIMATION_FRAME_COUNT):
            raise AssertionError()
        _assert_animation_cycles(slug, all_figures)

        specs = []
        for index, (figure, item) in enumerate(zip(figures, legacy_metadata)):
            specs.append((index, item['pose'], figure, 'legacy', source,
                          legacy_hash, revision['source_normalization']['legacy']
                          if revision else 1.0, item))
        for index, (figure, item) in enumerate(zip(motion_figures, motion_metadata), 16):
            specs.append((index, item['pose'], figure, 'motion', motion_source,
                          motion_hash, motion_source_scale, item))
        for index, (figure, item) in enumerate(zip(action_figures, action_metadata), 32):
            specs.append((index, item['pose'], figure, 'actions', action_source,
                          action_hash, action_source_scale, item))
        for index, (figure, item) in enumerate(zip(airborne_figures, airborne_metadata), 48):
            specs.append((index, item['pose'], figure, 'airborne', airborne_source,
                          airborne_hash, airborne_source_scale, item))
        if not (len(specs) == ANIMATION_FRAME_COUNT):
            raise AssertionError()

        frames = []
        metadata = []
        for index, pose, figure, source_kind, source_path, frame_source_hash, source_scale, item in specs:
            resized_size = (max(1, round(figure.width * uniform_scale)),
                            max(1, round(figure.height * uniform_scale)))
            if not (resized_size[0] <= FIT_WIDTH and resized_size[1] <= FIT_HEIGHT):
                raise AssertionError(f'{slug}/frame{index}-{pose} exceeds {FIT_WIDTH}x{FIT_HEIGHT} at '
                    f'base uniform scale {uniform_scale}: {resized_size}; repair the new art')
            resized = figure.resize(resized_size, Image.Resampling.NEAREST)
            frame = Image.new('RGBA', (FRAME_WIDTH, FRAME_HEIGHT))
            frame.alpha_composite(resized,
                                  ((FRAME_WIDTH - resized.width) // 2,
                                   BASELINE_Y - resized.height))
            alpha_box = frame.getchannel('A').getbbox()
            if not (alpha_box and alpha_box[0] >= 0 and alpha_box[1] >= 0 \
                and alpha_box[2] <= FRAME_WIDTH and alpha_box[3] <= FRAME_HEIGHT):
                raise AssertionError(f'{slug}/frame{index}-{pose} clipped in {FRAME_WIDTH}x{FRAME_HEIGHT} canvas')
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
        if not (opaque):
            raise AssertionError(f'{slug}: no opaque base animation pixels after normalization')
        if revision:
            # A reviewed likeness edit is quantized into the old palette.  It
            # may add hair pixels but cannot reorder or recolor the fighter's
            # established fifteen OBJ colors.
            locked_palette = revision['expected_native']['palette_bytes']
            if not (locked_palette == baseline_entry['palette_bytes']):
                raise AssertionError()
            colors = _palette_colors_from_bytes(locked_palette)[1:]
            if not (len(colors) == 15):
                raise AssertionError()
        else:
            strip = Image.new('RGB', (len(opaque), 1))
            strip.putdata(opaque)
            palette = strip.quantize(colors=15, method=Image.Quantize.MEDIANCUT).getpalette()[:45]
            colors = sorted({tuple((channel >> 3) << 3 for channel in palette[i:i + 3])
                             for i in range(0, 45, 3)}, key=lambda c: (sum(c), c))
            if not (colors):
                raise AssertionError(f'{slug}: palette quantization returned no colors')
            source_color_count = len({pixel for pixel in opaque})
            if not (source_color_count >= 3):
                raise AssertionError(f'{slug}: source art has only {source_color_count} opaque RGB colors')
            if not (len(colors) >= 3):
                raise AssertionError(f'{slug}: native palette collapsed to {len(colors)} unique colors')
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
            if not (native_box):
                raise AssertionError(f'{slug}/frame{index}: quantization erased the figure')
            metadata[index]['native_box'] = list(native_box)
            metadata[index]['nativebox'] = list(native_box)
            metadata[index]['effective_width'] = native_box[2] - native_box[0]
            metadata[index]['effective_height'] = native_box[3] - native_box[1]
            frame_hash = hashlib.sha256(bytes(ids)).hexdigest()
            metadata[index]['pixels_sha256'] = frame_hash
            metadata[index]['native_hash'] = frame_hash
            metadata[index]['hash'] = frame_hash

        fighter_palette = [(0, 0, 0)] + colors
        if revision:
            _assert_reviewed_revision(slug, fighter, indices, fighter_palette,
                                      uniform_scale, revision)
        else:
            _assert_native_baseline64(slug, fighter, indices, fighter_palette,
                                      uniform_scale, baseline)
        from walking_assets import apply_walking
        walking_revision=apply_walking(root,fighter,slug,indices,metadata,colors,
                                      preview,extract_atlas,HEIGHTS[fighter])
        from pose_revision_assets import apply_pose_revision,SCOPES
        combat_revisions=[]
        for scope in SCOPES:
            change=apply_pose_revision(root,fighter,slug,indices,metadata,colors,
                                       preview,extract_atlas,HEIGHTS[fighter],scope)
            if change:combat_revisions.append(change)
        _assert_native_animation_cycles(slug, indices)
        if not (len({bytes(ids) for ids in indices[:16]}) >= 14):
            raise AssertionError(f'{slug}: legacy key poses were duplicated')
        pending_images.append((output / f'fighter{fighter:02}.png', preview))

        # Reuse the same illustrated face and costume for the select portrait.
        portrait_pair = build_portrait_pair(figures[0], backdrop=colors[0])
        backdrop = portrait_pair['small']
        backdrop_large = portrait_pair['large']
        pending_images.append((output / f'portrait{fighter:02}.png', backdrop))
        pending_images.append((output / f'portrait{fighter:02}-large.png', backdrop_large))

        effective_standing_height = metadata[0]['effective_height']
        effective_height = max(item['effective_height'] for item in metadata)
        effective_width = max(item['effective_width'] for item in metadata)
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
        manifest_entry = {
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
            'portrait_framing': portrait_pair['metadata'],
            'palette': fighter_palette,
            'frames': metadata,
        }
        if revision:
            manifest_entry['revision'] = {
                'contract_file': revision['contract_file'],
                'contract_sha256': revision['contract_sha256'],
                'baseline_native64_sha256': revision['old_native']['frame_hashes_sha256'],
                'expected_native64_sha256': revision['expected_native']['frame_hashes_sha256'],
                'replacement_sources': {
                    role: {
                        'file': str(path.relative_to(root)).replace('\\', '/'),
                        'sha256': _sha256(path),
                    }
                    for role, path in revision['new_sources'].items()
                },
            }
        if walking_revision:
            manifest_entry['walking_revision']=walking_revision
            if revision:manifest_entry['revision']['scope']='Approved base identity before the bounded walking overlay; walking_revision records the final native identity.'
        if combat_revisions:
            manifest_entry['combat_revisions']=combat_revisions
            manifest_entry['native64_sha256']=_frame_hash_summary(_native_frame_hashes(indices))
            manifest_entry['walking_revision']['scope']='Walking-only checkpoint before the disjoint combat revisions; native64_sha256 records the final set.'
        manifests.append(manifest_entry)
        print(f'Prepared {slug}: 64 individual frames, 15-color OBJ palette', flush=True)
    if not (len({tuple(f['indices'][0]) for f in fighters}) == 12):
        raise AssertionError('Roster must have twelve distinct idle drawings')
    # All twelve native frames, palettes, bounds and cycle checks have passed
    # before any review image or generated manifest is published.
    for path, image in pending_images:
        image.save(path)
    (output / 'character-manifest.json').write_text(json.dumps(manifests, indent=2) + '\n')
    return fighters
