"""Independent native pool/map oracle for the approved v0.29 spectator design."""
from __future__ import annotations

import ctypes as C
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from PIL import Image

BASE = 'c7510c30e129465bcca0b32e2142daec60546d0f'
RECTS = (
    ((64,136,16,32),(104,136,16,32),(192,136,16,32),(240,136,16,32),
     (24,144,16,16),(144,144,16,16),(264,144,16,16),(128,80,16,16)),
    ((40,112,16,32),(88,112,16,32),(184,112,16,32),(232,112,16,32),
     (16,136,16,16),(136,88,16,16),(264,136,16,16),(184,88,16,16)),
    ((32,72,16,32),(104,72,16,32),(176,72,16,32),(248,72,16,32),
     (56,88,16,16),(16,112,16,16),(208,88,16,16),(256,56,16,16)),
)


def require(ok, label, details=None):
    if not ok:
        raise ValueError((label, details))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def metadata(root, generated=None):
    root = Path(root)
    generated = root/'assets/generated' if generated is None else Path(generated)
    path = generated/'arena-life29.json'
    if not path.is_file():
        return None
    value = json.loads(path.read_bytes())
    required = {'schema':1,'scope':'arena-life29','tile_base':832,'tile_count':48,
                'tile_vram_word':0x3400,'tile_vram_end_word':0x36ff,
                'pool_bytes':1536,'phase_count':6,'chunk_bytes':256,
                'chunks_per_phase':6,'max_uploads_per_blank':1,
                'map_vram_words':[0x3800,0x3fff],'legacy_ambient_disabled':True,
                'palette_transfers':0,'obj_entries':0,'hdma_mask':0}
    require(all(value.get(key) == expected for key, expected in required.items()),
            'Unknown spectator allocation; review oracle policy explicitly')
    require([row.get('id') for row in value.get('stages',[])] == [0,1,2],
            'Spectator contract must cover all three arenas')
    def baseline(name):
        return subprocess.check_output(['git','show',BASE+':assets/generated/'+name],cwd=root)
    for stage, row in enumerate(value['stages']):
        name = 'stage'+str(stage)
        old_gfx, old_map, old_pal = [baseline(name+suffix) for suffix in ('_tiles.bin','_map.bin','_pal.bin')]
        gfx, tilemap, palette = [(generated/(name+suffix)).read_bytes() for suffix in ('_tiles.bin','_map.bin','_pal.bin')]
        require(row['original_tiles_bytes'] == len(old_gfx) and row['original_tiles_sha256'] == sha(old_gfx)
                and row['original_map_sha256'] == sha(old_map) and row['palette_sha256'] == sha(old_pal),
                'Spectator provenance differs from actual approved Git blobs', stage)
        require(gfx[:len(old_gfx)] == old_gfx and not any(gfx[len(old_gfx):0x6800])
                and len(gfx) == 0x6e00 and palette == old_pal,
                'Original scenery tile prefix/palettes or animation allocation changed',stage)
        require(len(tilemap) == len(old_map) == 4096, 'Whole-stage map allocation changed',stage)
        rects = row.get('rectangles_world')
        require(rects == [list(rect) for rect in RECTS[stage]], 'Spectator patch placement changed',stage)
        expected_rects = [[x+dx,y+dy,8,8] for x,y,w,h in RECTS[stage]
                          for dy in range(0,h,8) for dx in range(0,w,8)]
        cells = row.get('animated_cells',[])
        require(len(cells) == 48 and [cell['world_rect'] for cell in cells] == expected_rects,
                'Spectator patch inventory differs',stage)
        old_words = struct.unpack('<2048H',old_map)
        new_words = struct.unpack('<2048H',tilemap)
        offsets = set()
        for index, cell in enumerate(cells):
            x,y,_,_ = cell['world_rect'];offset = (x//256)*1024+(y//8)*32+(x%256)//8
            bank = cell['palette_bank']
            word = (832+index) | (bank<<10)
            require(bank in range(2,8) and y >= 40 and y+8 <= row['floor_seam_y']
                    and cell['offset_words'] == offset and cell['pool_tile'] == index
                    and cell['chunk'] == index//8 and cell['original_word'] == old_words[offset]
                    and cell['word'] == word and new_words[offset] == word,
                    'Animated map word escaped reviewed cells/palettes/floor', [stage,index])
            offsets.add(offset)
        require(all(a == b for i,(a,b) in enumerate(zip(old_words,new_words)) if i not in offsets),
                'Spectator generator changed an undeclared map cell',stage)
        source_name = f'arena_life29_stage{stage}.bin'
        source = (generated/source_name).read_bytes()
        require(row['phase_source'] == source_name and len(source) == row['phase_source_bytes'] == 9216
                and sha(source) == row['phase_source_sha256'] and gfx[0x6800:] == source[:1536],
                'Authored spectator phase source/initial pool differs',stage)
        phases = row.get('phases',[])
        require([phase['id'] for phase in phases] == list(range(6)), 'Missing spectator phases',stage)
        for index, phase in enumerate(phases):
            require(phase['offset_bytes'] == index*1536 and phase['bytes'] == 1536
                    and phase['sha256'] == sha(source[index*1536:(index+1)*1536]),
                    'Spectator phase extent/hash differs',[stage,index])
        expected_outputs = {name+'_tiles.bin',name+'_map.bin',source_name}
        require(set(row['outputs']) == expected_outputs, 'Unexpected spectator output inventory',stage)
        for filename, record in row['outputs'].items():
            data = (generated/filename).read_bytes()
            require(record['bytes'] == len(data) and record['sha256'] == sha(data),
                    'Spectator output differs from allocation record',filename)
    return value


class ArenaPool:
    """Observe source-bound chunks; decode their pixels without encoder imports."""
    def __init__(self, root, host, symbols, stage, contract, generated=None):
        self.root, self.host, self.symbols, self.stage = Path(root), host, symbols, stage
        assets = self.root/'assets/generated' if generated is None else Path(generated)
        self.row = contract['stages'][stage]
        self.source = (assets/self.row['phase_source']).read_bytes()
        self.map = (assets/f'stage{stage}_map.bin').read_bytes()
        self.palette = (assets/f'stage{stage}_pal.bin').read_bytes()
        self.previous = self.life();self.previous_vram = self.vram()
        self.previous_frozen = self.frozen()
        self.callbacks = self.uploads = 0;self.phases = set();self.cached_pool = None;self.cached_plane = None

    def read(self, name, size=1):
        return int.from_bytes(C.string_at(self.host.ram+(self.symbols[name]&0x1ffff),size),'little')

    def life(self):
        return C.string_at(self.host.ram+(self.symbols['v29ArenaState']&0x1ffff),48)

    def vram(self):
        return C.string_at(self.host.core.retro_get_memory_data(3),65536)

    def frozen(self):
        if self.read('intro') or self.read('paused'):
            return True
        if C.string_at(self.host.ram+(self.symbols['stageDepthTable']&0x1ffff),10)[9]:
            return True
        return bool(self.read('hitstop') and not self.read('roundEnd'))

    def valid_pool(self, pool):
        require(len(pool) == 1536, 'Spectator VRAM pool size differs')
        for chunk in range(6):
            require(any(pool[chunk*256:(chunk+1)*256] == self.source[p*1536+chunk*256:p*1536+(chunk+1)*256]
                        for p in range(6)), 'Live spectator chunk is not an authored phase',[self.stage,chunk])

    def observe(self, current):
        state = self.life();previous = self.previous;before = self.previous_vram
        pool = current[0x6800:0x6e00]
        self.valid_pool(pool)
        require(current[0x7000:0x8000] == self.map, 'Live spectator upload corrupted wide stage map',self.stage)
        require(current[:0x6800] == before[:0x6800] and current[0x6e00:0x7000] == before[0x6e00:0x7000],
                'Live spectator upload escaped reserved tile pool',self.stage)
        delta = (state[14]-previous[14])&255
        require(delta in (0,1), 'Multiple spectator transfers in one callback',delta)
        if delta:
            chunk, phase = state[19], state[20]
            require(chunk < 6 and phase < 6, 'Completed spectator source index invalid',[chunk,phase])
            a,b = chunk*256,(chunk+1)*256
            require(pool[a:b] == self.source[phase*1536+a:phase*1536+b]
                    and pool[:a] == before[0x6800:0x6800+a] and pool[b:] == before[0x6800+b:0x6e00],
                    'Completed spectator telemetry differs from actual source/destination',[chunk,phase])
            require(current[0xb000:0xb800] == before[0xb000:0xb800]
                    and current[0xc000:0xe800] == before[0xc000:0xe800],
                    'Spectator DMA shares an actor/UI blank')
            self.uploads += 1
        else:
            require(pool == before[0x6800:0x6e00], 'Spectator pool changed without completed transfer')
        frozen = self.frozen()
        if frozen and self.previous_frozen:
            require(not delta and state[1] == previous[1], 'Frozen spectator clock/transfer advanced')
        actual = list(struct.unpack('<4H',C.string_at(self.host.ram+0x1ffe6,8)))
        expected = [state[3],state[1],state[5] if state[4]<6 else 255,state[4] if state[4]<6 else 0]
        require(actual == expected, 'Published arena TRACE differs from actual completed/queued state',[actual,expected])
        self.callbacks += 1;self.phases.add(state[3])
        self.previous,self.previous_vram,self.previous_frozen = state,current,frozen

    def plane(self, original):
        pool = self.vram()[0x6800:0x6e00]
        self.valid_pool(pool)
        if pool == self.cached_pool:
            return self.cached_plane
        result = original.copy()
        for cell in self.row['animated_cells']:
            x,y,_,_ = cell['world_rect'];data = pool[cell['pool_tile']*32:(cell['pool_tile']+1)*32]
            pixels=[]
            for yy in range(8):
                for xx in range(8):
                    color=sum(((data[(bit//2)*16+yy*2+bit%2]>>(7-xx))&1)<<bit for bit in range(4))
                    at=((cell['palette_bank']-2)*16+color)*2
                    word=int.from_bytes(self.palette[at:at+2],'little')
                    pixels.append(tuple(((word>>shift)&31)*255//31 for shift in (0,5,10)))
            tile=Image.new('RGB',(8,8));tile.putdata(pixels);result.paste(tile,(x,y))
        self.cached_pool,self.cached_plane=pool,result
        return result

    def report(self):
        return {'callbacks':self.callbacks,'uploads':self.uploads,'completed_phases':sorted(self.phases),
                'pool_source_bound':True,'map_floor_immutable':True,'trace_matches_direct_state':True}
