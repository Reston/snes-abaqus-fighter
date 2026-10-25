"""Mutate isolated spectator contracts; the game and generated assets stay read-only."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from arena_life29_checks import metadata
GENERATED=ROOT/'assets/generated'


class ArenaContracts(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='arena-oracle-',dir=ROOT/'build')
        self.addCleanup(temp.cleanup)
        self.assets=Path(temp.name)
        names=['arena-life29.json']
        for stage in range(3):
            names.extend([f'stage{stage}{suffix}' for suffix in ('_tiles.bin','_map.bin','_pal.bin')])
            names.append(f'arena_life29_stage{stage}.bin')
        for name in names:
            shutil.copy2(GENERATED/name,self.assets/name)
        self.contract=json.loads((self.assets/'arena-life29.json').read_bytes())

    def save(self):
        (self.assets/'arena-life29.json').write_text(json.dumps(self.contract),encoding='utf-8')

    def reject(self,pattern):
        self.save()
        with self.assertRaisesRegex(ValueError,pattern):metadata(ROOT,self.assets)

    def rehash(self,stage,name):
        raw=(self.assets/name).read_bytes()
        self.contract['stages'][stage]['outputs'][name]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

    def test_original_source_bound_contract_passes(self):
        self.assertEqual(len(metadata(ROOT,self.assets)['stages']),3)

    def test_old_unsafe_map_window_rejected(self):
        self.contract['tile_vram_word']=0x3c00
        self.reject('allocation')

    def test_rehashed_original_tile_corruption_rejected(self):
        path=self.assets/'stage0_tiles.bin';raw=bytearray(path.read_bytes());raw[0]^=1;path.write_bytes(raw)
        self.rehash(0,path.name)
        self.reject('Original scenery')

    def test_rehashed_undeclared_map_edit_rejected(self):
        path=self.assets/'stage0_map.bin';raw=bytearray(path.read_bytes());raw[0]^=1;path.write_bytes(raw)
        self.rehash(0,path.name)
        self.reject('undeclared map')

    def test_rewritten_baseline_hash_rejected(self):
        self.contract['stages'][0]['original_tiles_sha256']='0'*64
        self.reject('actual approved Git')

    def test_floor_patch_relocation_rejected(self):
        self.contract['stages'][0]['animated_cells'][0]['world_rect'][1]=200
        self.reject('inventory')

    def test_phase_extent_and_hash_are_enforced(self):
        self.contract['stages'][0]['phases'][1]['offset_bytes']=0
        self.reject('extent/hash')

    def test_extra_unreviewed_phase_rejected(self):
        self.contract['phase_count']=7
        self.reject('allocation')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generated',type=Path,default=GENERATED)
    args,rest=parser.parse_known_args()
    GENERATED=args.generated.resolve()
    unittest.main(argv=[sys.argv[0],*rest])
