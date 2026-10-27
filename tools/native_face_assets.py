"""Prepare deliberately pixel-authored faces within each existing 4bpp actor.

Artwork comes from retained imagegen masters. This importer extracts complete
figures, applies one scale to an atlas, and maps colours; it never paints facial
anatomy or assembles heads and limbs from separate pictures.
"""
import colorsys
import hashlib
import json
from pathlib import Path
from PIL import Image

MANIFEST = 'assets/art/native-faces-v033/roster.json'
MANIFEST_SHA256 = '101009d958efc5c81a2ba8aaba41547e3e81bc04bd054075a4a133c95714c5f5'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def native_indices(frame, palette):
    """Map to nine outfit/hair colours plus six reserved natural skin values.

    Plain RGB nearest-colour mapping can turn beige into an orange jacket
    colour or brown facial shadow into red cloth. Keep a muted warm source
    colour from becoming a substantially more saturated costume colour.
    Saturated cloth, neutral highlights and dark hair keep ordinary mapping.
    """
    require(len(palette) == 15 and all(len(c) == 3 for c in palette),
            'Native face palette must have exactly fifteen RGB entries')
    hsv = [colorsys.rgb_to_hsv(*(v / 255 for v in c)) for c in palette]
    cache = {}
    result = []
    for r, g, b, alpha in frame.convert('RGBA').get_flattened_data():
        if not alpha:
            result.append(0)
            continue
        rgb = (r, g, b)
        if rgb not in cache:
            distances = [sum((a-b)**2 for a,b in zip(rgb,c)) for c in palette]
            chosen = min(range(15), key=distances.__getitem__)
            h, s, value = colorsys.rgb_to_hsv(r/255, g/255, b/255)
            warm = (h <= 55/360 or h >= 340/360) and r > 65 and g > r*.20 and b > r*.08
            ch, cs, _ = hsv[chosen]
            hue_gap = min(abs(ch-h), 1-abs(ch-h))
            if chosen < 9 and warm and (cs-s > .08 or
                    cs-s > .03 and hue_gap > 6/360):
                chosen = min(range(9,15), key=distances.__getitem__)
            cache[rgb] = chosen + 1
        result.append(cache[rgb])
    return result


def native_image(indices, palette, size=(96,80)):
    require(len(indices) == size[0]*size[1], 'Native indexed frame size differs')
    image = Image.new('RGBA',size)
    image.putdata([(0,0,0,0) if not n else (*palette[n-1],255) for n in indices])
    return image


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def frame_summary(hashes):
    return hashlib.sha256(''.join(hashes).encode('ascii')).hexdigest()


def apply_native_faces(root, fighter, slug, indices, metadata, old_palette,
                       physical_scale, standing_height, extract):
    """Import one complete authored64-pose sheet after historical art passes.

    Selection portraits are prepared before this call from their retained
    sources. This changes only the full fighting model and its existing palette;
    canvas, pose IDs, physical height, actor upload size and OBJ count stay fixed.
    """
    path = root / MANIFEST
    if not path.exists():
        require('"0.33.' not in (root/'src/version.h').read_text(),
                'The native-face release requires its reviewed roster manifest')
        return None
    require(sha(path) == MANIFEST_SHA256, 'Native-face roster manifest pin changed')
    record = json.loads(path.read_bytes())
    rows = record.get('fighters')
    require(record.get('schema') == 1 and record.get('scope') == 'native-pixel-faces' and
            isinstance(rows,list) and len(rows) == 12 and
            [r.get('id') for r in rows] == list(range(12)),
            'Native face roster must cover twelve fighters in stable order')
    row = rows[fighter]
    require(row.get('slug') == slug and row.get('standing_height') == standing_height,
            'Native face fighter identity or physical height changed')
    require(isinstance(row.get('frame_sha256'),list) and
            len(row['frame_sha256']) == 64 and
            all(isinstance(h,str) and len(h)==64 for h in row['frame_sha256']),
            'Native face manifest must pin all sixty-four frame hashes')
    before = [hashlib.sha256(bytes(frame)).hexdigest() for frame in indices]
    require(before == row.get('baseline_frame_sha256'),
            'Historical body/pose inputs changed before the face revision: '+slug)
    packed = bytearray()
    for r,g,b in old_palette:
        packed.extend(((r>>3)|((g>>3)<<5)|((b>>3)<<10)).to_bytes(2,'little'))
    require(hashlib.sha256(packed).hexdigest() == row.get('baseline_palette_sha256'),
            'Historical actor palette changed before the face revision: '+slug)
    if row.get('restore_original'):
        require(fighter == 5 and row['restore_original'].get('version')=='0.32.1' and
                before == row['frame_sha256'] and
                frame_summary(before)==row['native64_sha256'],
                'Only the pinned original David model may bypass the new face art')
        return None
    source = (root/row['source']).resolve()
    directory = (root/'assets/art/native-faces-v033').resolve()
    require(source.parent == directory and source.name.startswith(f'{fighter:02d}-{slug}-'),
            'Native face source escapes its reviewed roster directory')
    require(sha(source) == row['sha256'], 'Native face master bytes changed: '+slug)
    provenance = root/row['provenance']
    require(provenance.resolve().parent == directory and
            sha(provenance) == row['provenance_sha256'],
            'Native face generation record changed: '+slug)
    generation = json.loads(provenance.read_bytes())
    require(generation.get('mode') == 'built-in image_gen' and
            generation.get('selected_final') == row['source'] and
            generation.get('sha256') == row['sha256'] == generation.get('raw_output_sha256'),
            'Native face source is not the retained unmodified generation')
    for reference,pin in generation['reference_sha256'].items():
        reference_path = (root/reference).resolve()
        require(reference_path.is_relative_to(root.resolve()),
                'Native face reference escapes source tree')
        require(sha(reference_path) == pin, 'Native face reference changed: '+reference)
    palette = row.get('palette')
    require(isinstance(palette,list) and len(palette) == 15 and
            len({tuple(c) for c in palette}) == 15 and
            all(len(c)==3 and all(isinstance(v,int) and 0<=v<=248 and v%8==0
                                 for v in c) for c in palette),
            'Native face palette must fit fifteen unique SNES colours')
    figures, details = extract(source, pose_names=[r['pose'] for r in metadata],
                               expected_count=64)
    factor = standing_height/figures[0].height
    require(factor == row['conversion'], 'Native face conversion scale changed')
    result = []
    preview = Image.new('RGBA',(6144,80))
    for n,(figure,detail) in enumerate(zip(figures,details)):
        size = (max(1,round(figure.width*factor)),max(1,round(figure.height*factor)))
        require(size[0]<=94 and size[1]<=77,
                f'{slug}/frame{n}: native face art exceeds fixed96x80 actor canvas')
        scaled = figure.resize(size,Image.Resampling.NEAREST)
        # Nearest sampling may omit an isolated edge pixel, leaving a blank
        # outer row/column. Trim only that empty border before baseline placement;
        # every opaque pixel still uses the atlas's single isotropic scale.
        box = scaled.getchannel('A').getbbox()
        require(box is not None, f'{slug}/frame{n}: empty converted figure')
        scaled = scaled.crop(box)
        frame = Image.new('RGBA',(96,80))
        frame.alpha_composite(scaled,((96-scaled.width)//2,78-scaled.height))
        ids = native_indices(frame,palette)
        digest = hashlib.sha256(bytes(ids)).hexdigest()
        require(digest == row['frame_sha256'][n],
                f'{slug}/frame{n}: reviewed native pixels changed')
        image = native_image(ids,palette)
        box = image.getchannel('A').getbbox()
        require(box and box[0]>0 and box[2]<96 and box[3]==78,
                f'{slug}/frame{n}: native face sprite clips or loses its baseline')
        previous = metadata[n]
        previous.update(previous_source_kind=previous['source_kind'],
            previous_source_file=previous['source_file'],
            previous_source_sha256=previous['source_sha256'],
            source_kind='native-face-pixels',source_file=row['source'],
            sourcefile=row['source'],source_hash=row['sha256'],
            sourcehash=row['sha256'],source_sha256=row['sha256'],
            source_scale=factor/physical_scale,
            source_normalization=factor/physical_scale,
            native_face_source_box=detail['source_box'],
            native_face_conversion=factor,native_hash=digest,
            pixels_sha256=digest,hash=digest,native_box=list(box),
            nativebox=list(box),native_size=size,
            effective_width=box[2]-box[0],effective_height=box[3]-box[1])
        result.append(ids)
        preview.alpha_composite(image,(n*96,0))
    require(frame_summary([r['native_hash'] for r in metadata]) == row['native64_sha256'],
            'Native face final frame identity differs')
    return {'indices':result,'palette':[(0,0,0)]+palette,'preview':preview,
            'revision':{'manifest':MANIFEST,'manifest_sha256':MANIFEST_SHA256,
                'source':row['source'],'sha256':row['sha256'],
                'frame_range':[0,63],'scope':'native-pixel-faces',
                'conversion':factor,'skin_palette_indices':[10,11,12,13,14,15],
                'baseline_native64_sha256':frame_summary(before),
                'native64_sha256':row['native64_sha256']}}
