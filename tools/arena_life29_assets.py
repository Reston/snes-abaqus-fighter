"""Bounded BG1 spectator animation; run after stage_depth_assets.install.

Original scenery tiles/palettes and every floor cell stay byte-exact. Only
the declared above-floor map cells reference the new 48-tile pool. Each phase
contains six contiguous 256-byte chunks, including restored scenery behind
the atlas alpha. No live map, palette, OBJ, HDMA or scroll-band transfers.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
import re
import struct
import sys

from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
from stage_depth_assets import colors, encode, quantizer

ROOT = Path(__file__).resolve().parents[1]
ART = 'assets/art/stages/arena-life-v029'
TILE_BASE, TILE_COUNT, PHASE_BYTES = 832, 48, 1536
PHASES = ['conversation-a', 'conversation-b', 'impact-flinch',
          'impact-gasp', 'super-excitement', 'ko-celebration']
PEOPLE_Y = [0, 180, 356, 540, 720, 902, 1092, 1272, 1400, 1500, 1600, 1712, 1774]
RECTS = [
    [(64, 136, 16, 32), (104, 136, 16, 32), (192, 136, 16, 32), (240, 136, 16, 32),
     (24, 144, 16, 16), (144, 144, 16, 16), (264, 144, 16, 16), (128, 80, 16, 16)],
    [(40, 112, 16, 32), (88, 112, 16, 32), (184, 112, 16, 32), (232, 112, 16, 32),
     (16, 136, 16, 16), (136, 88, 16, 16), (264, 136, 16, 16), (184, 88, 16, 16)],
    [(32, 72, 16, 32), (104, 72, 16, 32), (176, 72, 16, 32), (248, 72, 16, 32),
     (56, 88, 16, 16), (16, 112, 16, 16), (208, 88, 16, 16), (256, 56, 16, 16)],
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def decode(raw):
    return [sum(((raw[(bit//2)*16+y*2+bit%2] >> (7-x)) & 1) << bit
                for bit in range(4)) for y in range(8) for x in range(8)]


def map_offset(x, y):
    column = x//8
    return (column//32)*1024+(y//8)*32+column%32


def render(gfx, tilemap, palette):
    image = Image.new('RGB', (288, 224))
    for y in range(40, 224, 8):
        for x in range(0, 288, 8):
            word = tilemap[map_offset(x, y)]
            tile = Image.new('RGB', (8, 8))
            bank = ((word >> 10) & 7)-2
            if bank < 0:
                continue
            values = decode(gfx[(word & 1023)*32:(word & 1023)*32+32])
            tile.putdata([palette[bank*16+v] for v in values])
            if word & 0x4000: tile = tile.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            if word & 0x8000: tile = tile.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            image.paste(tile, (x, y))
    return image


def atlas_cells(root):
    """Register original poses by shared row scale and ground baseline.

    Imagegen returned unequal heights for its seated rows; keep that exact
    source, record explicit crops, and reduce each actual authored subject.
    The cropped final row is unused: the burgundy visitor's upper body is
    used as the fourth coworker instead. No redrawing or synthetic animation.
    """
    people = Image.open(root/ART/'spectators-source.png').convert('RGBA')
    props = Image.open(root/ART/'environment-source.png').convert('RGBA')
    if people.size != (887, 1774) or props.size != (2172, 724):
        raise ValueError('Authored atlas dimensions changed; review crop registration')
    result = []
    for stage in range(3):
        subjects = []
        for actor in range(4):
            row = stage*4+actor
            if row == 11: row = 3
            cells = [people.crop((round(c*887/6), PEOPLE_Y[row],
                                  round((c+1)*887/6), PEOPLE_Y[row+1])) for c in range(6)]
            # Preserve a common registration within each character's row.
            bounds = [im.getchannel('A').point(lambda a: 255 if a>=160 else 0).getbbox() for im in cells]
            if any(b is None for b in bounds): raise ValueError('Missing spectator pose')
            width = max(b[2]-b[0] for b in bounds)
            height = max(b[3]-b[1] for b in bounds)
            if stage == 2 and actor == 3: height = min(height, 105)
            scale = min(16/width, (23 if stage==2 else 32)/height)
            phases = []
            for im, box in zip(cells, bounds):
                x0,y0,x1,y1 = box
                if stage == 2 and actor == 3: y1 = min(y1,y0+105)
                subject = im.crop((x0,y0,x1,y1))
                subject = subject.resize((max(1,round(subject.width*scale)),max(1,round(subject.height*scale))),Image.Resampling.BOX)
                native = Image.new('RGBA', (16,32))
                native.alpha_composite(subject, ((16-subject.width)//2,32-subject.height))
                phases.append(native)
            subjects.append(phases)
        for prop in range(4):
            phases = []
            for phase in range(6):
                cell = props.crop((round((phase+prop/4)*2172/6),round(stage*724/3),
                                   round((phase+(prop+1)/4)*2172/6),round((stage+1)*724/3)))
                box = cell.getchannel('A').point(lambda a:255 if a>=160 else 0).getbbox()
                if box is None: raise ValueError('Missing environment detail')
                crop = cell.crop(box)
                crop.thumbnail((16,16),Image.Resampling.BOX)
                native = Image.new('RGBA',(16,16))
                native.alpha_composite(crop,((16-crop.width)//2,16-crop.height))
                phases.append(native)
            subjects.append(phases)
        result.append(subjects)
    return result


def install(root=ROOT, out=None):
    root = Path(root);out = Path(out) if out is not None else root/'assets/generated'
    provenance = json.loads((root/ART/'art.json').read_bytes())
    for name, expected in provenance['files'].items():
        if sha((root/ART/name).read_bytes()) != expected: raise ValueError('Arena art provenance mismatch: '+name)
    atlases = atlas_cells(root)
    asm = (out/'data.asm').read_text();header = (out/'assets.h').read_text()
    records = []
    depth = json.loads((out/'stage-depth.json').read_bytes())
    for stage in range(3):
        name = 'stage'+str(stage)
        original_gfx = (out/(name+'_tiles.bin')).read_bytes()
        original_map = (out/(name+'_map.bin')).read_bytes()
        pal_bytes = (out/(name+'_pal.bin')).read_bytes()
        palette = colors(pal_bytes)
        tilemap = list(struct.unpack('<2048H',original_map))
        if len(original_gfx)>TILE_BASE*32: raise ValueError('Stage scenery invades reserved animation pool')
        original = render(original_gfx,tilemap,palette)
        banks = []
        for subject, (x,y,w,h) in zip(atlases[stage], RECTS[stage]):
            samples = Counter()
            for pose in subject:
                im = original.crop((x,y,x+w,y+h)).convert('RGBA');im.alpha_composite(pose)
                samples.update(im.convert('RGB').get_flattened_data())
            banks.append(min(range(6),key=lambda b:sum(count*min(sum((c[k]-p[k])**2 for k in range(3))
                                                             for p in palette[b*16+1:b*16+16])
                                                        for c,count in samples.items())))
        phase_data = bytearray(); cells = []; previews = []
        for phase in range(6):
            phase_image = original.copy()
            phase_tiles = bytearray()
            for subject, (x,y,w,h), bank in zip(atlases[stage], RECTS[stage], banks):
                rgba = original.crop((x,y,x+w,y+h)).convert('RGBA')
                rgba.alpha_composite(subject[phase])
                # Each patch owns one existing stage palette. Pick the least
                # squared error jointly over scenery AND all authored poses.
                # Fixed phase-0 map; palettes never change during animation.
                q = quantizer(palette[bank*16+1:bank*16+16])
                rgb = rgba.convert('RGB')
                values = [min(v,14)+1 for v in rgb.quantize(palette=q,dither=Image.Dither.NONE).get_flattened_data()]
                native = Image.new('RGB',(w,h));native.putdata([palette[bank*16+v] for v in values])
                phase_image.paste(native,(x,y))
                for ty in range(0,h,8):
                    for tx in range(0,w,8):
                        index = len(phase_tiles)//32
                        phase_tiles += encode([values[(ty+yy)*w+tx+xx] for yy in range(8) for xx in range(8)],4)
                        if phase==0:
                            offset = map_offset(x+tx,y+ty)
                            word = TILE_BASE+index | ((bank+2)<<10)
                            cells.append({'offset_words':offset,'world_rect':[x+tx,y+ty,8,8],
                                          'original_word':tilemap[offset],'word':word,'pool_tile':index,
                                          'palette_bank':bank+2,'chunk':index//8})
                            tilemap[offset] = word
            if len(phase_tiles)!=PHASE_BYTES: raise ValueError('Arena phase exceeds declared tile pool')
            phase_data += phase_tiles;previews.append(phase_image)
        gfx = original_gfx.ljust(TILE_BASE*32,b'\0')+phase_data[:PHASE_BYTES]
        current_map = struct.pack('<2048H',*tilemap)
        outputs = {name+'_tiles.bin':gfx,name+'_map.bin':current_map,
                   'arena_life29_stage'+str(stage)+'.bin':bytes(phase_data)}
        for filename,data in outputs.items(): (out/filename).write_bytes(data)
        previews[0].crop((16,0,272,224)).save(out/(name+'.png'))
        asset = 'arena_life29_stage'+str(stage)
        asm += '\n'+ '\n'.join([f'.section "asset_{asset}" superfree',asset+':',
                                f'.incbin "assets/generated/{asset}.bin"',asset+'_end:', '.ends'])+'\n'
        header += f'extern char {asset}, {asset}_end;\n#define {asset.upper()}_SIZE {len(phase_data)}\n'
        header = re.sub(r'(#define '+name.upper()+r'_TILES_SIZE) \d+',r'\g<1> '+str(len(gfx)),header)
        for filename,raw in outputs.items():
            if filename in depth['stages'][stage]['outputs']:
                depth['stages'][stage]['outputs'][filename]={'bytes':len(raw),'sha256':sha(raw)}
        depth['stages'][stage]['bg1_tiles']=len(gfx)//32
        record = {'id':stage,'rectangles_world':RECTS[stage],'viewport_origin':[16,0],
                  'animated_cells':cells,'original_tiles_bytes':len(original_gfx),
                  'original_tiles_sha256':sha(original_gfx),'original_map_sha256':sha(original_map),
                  'palette_sha256':sha(pal_bytes),'palette_cgram_colors':[32,127],
                  'floor_seam_y':depth['stages'][stage]['floor_seam_y'],
                  'phase_source':asset+'.bin','phase_source_bytes':len(phase_data),
                  'phase_source_sha256':sha(phase_data),
                  'phases':[{'id':p,'event':event,'offset_bytes':p*PHASE_BYTES,'bytes':PHASE_BYTES,
                             'sha256':sha(phase_data[p*PHASE_BYTES:(p+1)*PHASE_BYTES])} for p,event in enumerate(PHASES)],
                  'outputs':{n:{'bytes':len(raw),'sha256':sha(raw)} for n,raw in outputs.items()}}
        records.append(record)
    (out/'data.asm').write_text(asm,newline='\n');(out/'assets.h').write_text(header,newline='\n')
    depth['arena_life29']='arena-life29.json'
    (out/'stage-depth.json').write_text(json.dumps(depth,indent=2)+'\n',newline='\n')
    result = {'schema':1,'scope':'arena-life29','state':'v29ArenaState[48]',
              'tile_base':TILE_BASE,'tile_count':TILE_COUNT,'tile_vram_word':0x3400,
              'tile_vram_end_word':0x36ff,'pool_bytes':PHASE_BYTES,'phase_count':6,
              'chunk_bytes':256,'chunks_per_phase':6,'max_uploads_per_blank':1,
              'map_vram_words':[0x3800,0x3fff],'legacy_ambient_disabled':True,
              'palette_transfers':0,'obj_entries':0,'hdma_mask':0,
              'scheduling':'one 256-byte chunk only on a blank without actor or UI DMA; pause/hitstop/intro/motion-off freeze; KO round-end may celebrate',
              'trace':{'completed_phase':115,'live_clock':116,'in_flight_phase_or_255':117,'completed_chunks_or_0':118},
              'trace_publication':'arenaLife29Publish after traceActorsFast, after completed DMA, and on scene load; no assembly changes',
              'state_bytes':{'stage_plus_one':0,'live_clock':1,'desired_phase':2,'completed_phase':3,'next_chunk_or_6':4,
                             'in_flight_phase':5,'observed_super_mask':6,'reaction_remaining':7,'observed_hp':[8,9],
                             'ko_latch':10,'reaction_kind':11,'may_upload':12,'transfer_serial':14,'last_event':15,
                             'event_counts':[16,17,18],'last_uploaded_chunk':19,'last_uploaded_phase':20},
              'stages':records}
    (out/'arena-life29.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    return result


if __name__=='__main__':
    print(json.dumps(install(),indent=2))
