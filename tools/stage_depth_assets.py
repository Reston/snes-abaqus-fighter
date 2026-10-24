"""Whole native scenery with the v0.25 detailed-color floor restoration.

Run AFTER make_assets.py for isolated development. The parent can call
install(ROOT) at the end of make_assets.py, after data.asm/assets.h are written.
Only declared stage outputs and generated declarations are replaced. The menu
generator separately derives its arena previews from these native BG1 bytes;
all fighter/audio/UI bytes stay.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parent))
from stage_sources import load_stage_sources

ROOT = Path(__file__).resolve().parents[1]
ART = 'assets/art/stages/depth-v1'
FLOOR_ART = 'assets/art/stages/depth-floor-v2'
WIDTH = 288


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(values, bpp):
    result = bytearray(8 * bpp)
    for y in range(8):
        for x in range(8):
            for bit in range(bpp):
                result[(bit // 2) * 16 + y * 2 + bit % 2] |= ((values[y*8+x] >> bit) & 1) << (7-x)
    return bytes(result)


def colors(raw):
    return [tuple(((value >> shift) & 31) * 255 // 31 for shift in (0, 5, 10))
            for value in struct.unpack('<' + 'H' * (len(raw)//2), raw)]


def pack_colors(values):
    return b''.join(struct.pack('<H', (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10))
                    for r, g, b in values)


def quantizer(palette):
    q = Image.new('P', (1, 1))
    q.putpalette([v for color in palette for v in color] + list(palette[-1]) * (256-len(palette)))
    return q


def palette_for(tiles):
    means = [tuple(sum(p[k] for p in t.get_flattened_data()) / 64 for k in range(3)) for t in tiles]
    centers = [means[i*len(means)//6] for i in range(6)]
    for _ in range(12):
        groups = [min(range(6), key=lambda j:sum((c[k]-centers[j][k])**2 for k in range(3))) for c in means]
        for j in range(6):
            points = [means[i] for i, g in enumerate(groups) if g == j]
            if points:
                centers[j] = tuple(sum(p[k] for p in points)/len(points) for k in range(3))
    palettes = []
    for j in range(6):
        selected = [t for i, t in enumerate(tiles) if groups[i] == j] or [tiles[0]]
        strip = Image.new('RGB', (8, 8*len(selected)))
        for i, t in enumerate(selected):
            strip.paste(t, (0, i*8))
        raw = strip.quantize(colors=15, method=Image.Quantize.MEDIANCUT).getpalette()[:45]
        raw += (raw[-3:] or [0,0,0]) * ((45-len(raw))//3)
        palettes.append([(0,0,0)] + [tuple(raw[k:k+3]) for k in range(0,45,3)])
    return groups, palettes


def load_native(root, record):
    path = root / record['source']
    if not path.resolve().is_relative_to((root/ART).resolve()):
        raise ValueError(('stage source outside versioned art directory',path))
    if digest(path.read_bytes()) != record['source_sha256']:
        raise ValueError(('stage source hash mismatch', path))
    provenance = root / record['provenance']
    if digest(provenance.read_bytes()) != record['provenance_sha256']:
        raise ValueError(('stage provenance hash mismatch', provenance))
    data = json.loads(provenance.read_text())
    if data['mode'] != 'built-in imagegen' or data['id'] != record['id']:
        raise ValueError(('stage generation identity mismatch',record['id']))
    for filename,expected in data['source_hashes'].items():
        source = provenance.parent/filename
        if digest(source.read_bytes()) != expected:
            raise ValueError(('retained stage source hash mismatch',source))
    if digest((root/data['reference']).read_bytes()) != data['reference_sha256']:
        raise ValueError(('stage reference hash mismatch',record['id']))
    im = Image.open(path).convert('RGB')
    # One full-scene isotropic crop and nearest reduction; no object surgery.
    unit = min(im.width // 9, im.height // 7)
    w, h = unit*9, unit*7
    x, y = (im.width-w)//2, (im.height-h)//2
    return im.crop((x,y,x+w,y+h)).resize((WIDTH,224), Image.Resampling.NEAREST)


def load_floor(root, record, ui_palette):
    """Convert the complete authored apron, without drawing synthetic joints.

    Two existing UI grays (CGRAM6/7) keep the floor quiet and the navy actor
    shadows readable. BOX reduction retains authored thin paving/carpet joints;
    nearest-color conversion has no temporal or spatial dithering.
    """
    floor = record['floor']
    path, provenance = (root/floor[key] for key in ('source','provenance'))
    for p, key in ((path,'source_sha256'),(provenance,'provenance_sha256')):
        if not p.resolve().is_relative_to((root/FLOOR_ART).resolve()):
            raise ValueError(('floor source outside versioned art directory',p))
        if digest(p.read_bytes()) != floor[key]:
            raise ValueError(('floor source/provenance hash mismatch',p))
    data = json.loads(provenance.read_text())
    if data['mode'] != 'built-in imagegen' or data['id'] != record['id']:
        raise ValueError(('floor generation identity mismatch',record['id']))
    for name, expected in data['source_hashes'].items():
        if digest((provenance.parent/name).read_bytes()) != expected:
            raise ValueError(('retained floor source hash mismatch',name))
    reference = root/data['reference']
    if digest(reference.read_bytes()) != data['reference_sha256']:
        raise ValueError(('floor scenery reference hash mismatch',reference))
    if digest((root/'assets/generated/ui_pal.bin').read_bytes()) != data['palette_sha256']:
        raise ValueError('floor UI palette changed; review authored conversion')
    size = (256,224-record['floor_seam_y'])
    im = Image.open(path).convert('RGB').resize(size,Image.Resampling.BOX)
    # Imagegen's requested grays can drift in luminance. First recover its
    # two authored tonal groups, then map those complete groups to legal UI
    # grays. Direct RGB nearest-color matching flattened the office carpet.
    q = im.quantize(colors=2,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE)
    source_palette = [tuple(q.getpalette()[i:i+3]) for i in (0,3)]
    order = sorted(range(2),key=lambda i:sum(source_palette[i]))
    mapping = {order[0]:2,order[1]:3}
    values = [mapping[v] for v in q.get_flattened_data()]
    native = Image.new('RGB',size)
    native.putdata([ui_palette[v+4] for v in values])
    return native, {**floor,'native_size':list(size),'cgram_indices':[6,7],
                    'source_tone_centers':source_palette,
                    'resampling':'BOX full authored floor; MEDIANCUT two tones mapped to UI grays; no crop, synthetic geometry or dithering'}


def build_stage(root, record, ui_palette):
    im = load_native(root, record)
    seam = record['floor_seam_y']
    if seam not in (184,192):
        raise ValueError(('unsupported authored pavement joint',seam))
    # v0.25: restore the approved detailed material instead of flattening a
    # separately authored apron into two UI grays. One connected 4bpp plane
    # contains scenery AND ground, so camera/impact never split their join.
    prior = load_stage_sources(root)[record['id']]
    floor = prior['image'].crop((0,seam,256,224)).resize((WIDTH,224-seam),Image.Resampling.NEAREST)
    floor_metadata = {'source':prior['master']['file'],'source_sha256':prior['master']['sha256'],
                      'native_rows':[seam,224],'conversion':'approved native floor; nearest horizontal gutter fit; full stage 4bpp palettes',
                      'plane':'BG1','previous_two_gray_floor_retained_as_history':record['floor']['source']}
    if record['id']==2:
        provenance=root/'assets/art/stages/floor-v025/02-oficina.json'
        data=json.loads(provenance.read_bytes())
        if data['mode']!='built-in imagegen' or data['id']!=2:
            raise ValueError('Office material provenance identity differs')
        for key in ('raw_output','selected_final'):
            path=(root/data[key+'_path']).resolve()
            if not path.is_relative_to((root/'assets/art/stages/floor-v025').resolve()):
                raise ValueError('Office material escapes its retained art directory')
            if digest(path.read_bytes())!=data[key+'_sha256']:
                raise ValueError('Office material source hash differs')
        for name,expected in data['input_sha256'].items():
            if digest((root/name).read_bytes())!=expected:
                raise ValueError('Office material reference changed: '+name)
        floor=Image.open(root/data['selected_final_path']).convert('RGB').resize((WIDTH,224-seam),Image.Resampling.NEAREST)
        floor_metadata={'source':data['selected_final_path'],'source_sha256':data['selected_final_sha256'],
                        'provenance':provenance.relative_to(root).as_posix(),'provenance_sha256':digest(provenance.read_bytes()),
                        'plane':'BG1','conversion':data['processing']}
    im.paste(floor,(0,seam))
    positions = [(x,y) for y in range(40, 224, 8) for x in range(0, WIDTH, 8)]
    tiles = [im.crop((x,y,x+8,y+8)) for x,y in positions]
    groups, palettes = palette_for(tiles)
    qs = [quantizer(p[1:]) for p in palettes]
    gfx = bytearray(32)  # transparent tile 0 outside the stage canvas
    lookup = {bytes(32):0}
    tilemap = [0] * 2048
    preview = Image.new('RGB', (256,224))
    for (x,y), t, bank in zip(positions, tiles, groups):
        values = [min(v,14)+1 for v in t.quantize(palette=qs[bank], dither=Image.Dither.NONE).get_flattened_data()]
        tb = encode(values,4)
        if tb not in lookup:
            lookup[tb] = len(lookup)
            gfx += tb
        column = x//8
        offset = (column//32)*1024+(y//8)*32+column%32
        tilemap[offset] = lookup[tb] | ((bank+2)<<10)
        tile_im = Image.new('RGB',(8,8));tile_im.putdata([palettes[bank][v] for v in values])
        if 16 <= x < 272:
            preview.paste(tile_im,(x-16,y))
    if len(gfx)>0x7000:
        raise ValueError(('BG1 invades its map allocation',len(gfx)))

    # Keep the historical generated inventory, but BG3 is disabled and these
    # compatibility assets are transparent. Its former gfx space belongs to
    # the richer BG1 picture; UI, maps, actors and effects retain addresses.
    floor_gfx = bytes(16);floor_map = [0]*1024
    name = 'stage'+str(record['id'])
    outputs = {name+'_tiles.bin':bytes(gfx),name+'_map.bin':struct.pack('<2048H',*tilemap),
               name+'_pal.bin':pack_colors([c for p in palettes for c in p]),
               name+'_floor_tiles.bin':bytes(floor_gfx),name+'_floor_map.bin':struct.pack('<1024H',*floor_map)}
    metadata = {'id':record['id'],'name':record['name'],'source':record['source'],
                'source_sha256':record['source_sha256'],'native_canvas':[288,224],
                'viewport':[16,0,272,224],'camera_range':[-8,8],'edge_gutters':16,
                'floor_seam_y':seam,'bg1_tiles':len(gfx)//32,'bg3_tiles':len(floor_gfx)//16,
                'authored_floor':floor_metadata,'floor_plane':'BG1',
                'ambient_enabled':False,
                'outputs':{n:{'bytes':len(v),'sha256':digest(v)} for n,v in outputs.items()}}
    return outputs, preview, metadata


def install(root=ROOT, only=None):
    root = Path(root);out = root/'assets/generated'
    manifest = json.loads((root/ART/'stages.json').read_text())
    if manifest['schema'] != 1 or manifest['scope'] != 'stage-depth-v1':
        raise ValueError('unknown stage-depth manifest schema or scope')
    if [r['id'] for r in manifest['stages']] != [0,1,2]:
        raise ValueError('stage-depth manifest must own all three stages exactly once')
    ui_palette = colors((out/'ui_pal.bin').read_bytes())
    asm = (out/'data.asm').read_text();header = (out/'assets.h').read_text()
    records = []
    for record in manifest['stages']:
        if only is not None and record['id'] != only:
            continue
        outputs, preview, metadata = build_stage(root,record,ui_palette)
        for filename,data in outputs.items():
            (out/filename).write_bytes(data)
            name = filename.removesuffix('.bin')
            if not re.search(r'^'+name+':$',asm,re.M):
                asm += '\n'+ '\n'.join([f'.section "asset_{name}" superfree',name+':',
                    f'.incbin "assets/generated/{filename}"',name+'_end:', '.ends'])+'\n'
                header += f'extern char {name}, {name}_end;\n#define {name.upper()}_SIZE {len(data)}\n'
            else:
                header = re.sub(r'(#define '+name.upper()+r'_SIZE) \d+',r'\g<1> '+str(len(data)),header)
        preview.save(out/('stage'+str(record['id'])+'.png'))
        records.append(metadata)
    (out/'data.asm').write_text(asm,newline='\n')
    (out/'assets.h').write_text(header,newline='\n')
    result = {'schema':1,'scope':'stage-depth-v1','baseline_commit':'3f51120',
              'bg1':{'gfx_word':[0,0x37ff],'map_word':[0x3800,0x3fff],'map_size':[64,32],'bpp':4},
              'bg3':{'enabled':False,'map_word':[0x5c00,0x5fff],'map_size':[32,32],'bpp':2},
              'floor_plane':'BG1','revision':'detailed-color-floor-v025',
              'cgram':'Whole scenery and restored floor use stage colors32..127; UI colors0..31 stay unchanged',
              'hdma_mask':0,'live_dma_bytes':0,'obj_entries':0,'stages':records}
    (out/'stage-depth.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only',type=int,choices=range(3))
    args = parser.parse_args()
    print(json.dumps(install(only=args.only),indent=2))
