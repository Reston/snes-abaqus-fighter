"""v0.24 whole scenery / fixed pavement planes, independent of shared pipeline.

Run AFTER make_assets.py for isolated development. The parent can call
install(ROOT) at the end of make_assets.py, after data.asm/assets.h are written.
Only declared stage outputs and generated declarations are replaced. Menu
plates keep their approved historical previews; all fighter/audio/UI bytes stay.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ART = 'assets/art/stages/depth-v1'
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


def build_stage(root, record, ui_palette):
    im = load_native(root, record)
    seam = record['floor_seam_y']
    if seam not in (184,192):
        raise ValueError(('unsupported authored pavement joint',seam))
    positions = [(x,y) for y in range(40, seam, 8) for x in range(0, WIDTH, 8)]
    tiles = [im.crop((x,y,x+8,y+8)) for x,y in positions]
    groups, palettes = palette_for(tiles)
    qs = [quantizer(p[1:]) for p in palettes]
    gfx = bytearray(32)  # transparent tile 0, including the area below seam
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
    if len(gfx)>0x6000:
        raise ValueError(('BG1 invades BG3 tile allocation',len(gfx)))

    # BG3 Mode1 has only CGRAM 0..31. Reuse those exact UI colors, choosing
    # one legal three-opaque-color bank per tile. There is no palette write.
    banks = [ui_palette[i+1:i+4] for i in range(0,32,4)]
    floor_qs = [quantizer(bank) for bank in banks]
    floor_gfx = bytearray(16);floor_lookup = {bytes(16):0};floor_map = [0]*1024
    floor_error = 0
    for y in range(seam,224,8):
        for x in range(0,256,8):
            t = im.crop((x+16,y,x+24,y+8))
            candidates = []
            pixels = list(t.get_flattened_data())
            for bank,q in zip(banks,floor_qs):
                values = [min(v,2)+1 for v in t.quantize(palette=q,dither=Image.Dither.NONE).get_flattened_data()]
                error = sum(sum((c[k]-bank[v-1][k])**2 for k in range(3)) for c,v in zip(pixels,values))
                candidates.append((error,values))
            j = min(range(8),key=lambda i:candidates[i][0])
            error,values = candidates[j];floor_error += error
            tb = encode(values,2)
            if tb not in floor_lookup:
                floor_lookup[tb] = len(floor_lookup);floor_gfx += tb
            floor_map[(y//8)*32+x//8] = floor_lookup[tb] | (j<<10)
            tile_im = Image.new('RGB',(8,8));tile_im.putdata([banks[j][v-1] for v in values])
            preview.paste(tile_im,(x,y))
    if len(floor_gfx)>0x1000:
        raise ValueError(('BG3 floor invades BG1 map',len(floor_gfx)))
    name = 'stage'+str(record['id'])
    outputs = {name+'_tiles.bin':bytes(gfx),name+'_map.bin':struct.pack('<2048H',*tilemap),
               name+'_pal.bin':pack_colors([c for p in palettes for c in p]),
               name+'_floor_tiles.bin':bytes(floor_gfx),name+'_floor_map.bin':struct.pack('<1024H',*floor_map)}
    metadata = {'id':record['id'],'name':record['name'],'source':record['source'],
                'source_sha256':record['source_sha256'],'native_canvas':[288,224],
                'viewport':[16,0,272,224],'camera_range':[-8,8],'edge_gutters':16,
                'floor_seam_y':seam,'bg1_tiles':len(gfx)//32,'bg3_tiles':len(floor_gfx)//16,
                'ambient_enabled':False,'floor_quantization_rms':(floor_error/(256*(224-seam)*3))**0.5,
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
              'bg1':{'gfx_word':[0,0x2fff],'map_word':[0x3800,0x3fff],'map_size':[64,32],'bpp':4},
              'bg3':{'gfx_word':[0x3000,0x37ff],'map_word':[0x5c00,0x5fff],'map_size':[32,32],'bpp':2},
              'cgram':'BG1 uses existing stage colors32..127; BG3 reads unchanged UI colors0..31',
              'hdma_mask':0,'live_dma_bytes':0,'obj_entries':0,'stages':records}
    (out/'stage-depth.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only',type=int,choices=range(3))
    args = parser.parse_args()
    print(json.dumps(install(only=args.only),indent=2))
