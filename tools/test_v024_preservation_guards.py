"""Reject changes outside the approved combat allocation in isolated copies."""
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import v024_contracts as policy


class PreservationGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        container=ROOT/'build/v024-preservation-tests';container.mkdir(parents=True,exist_ok=True)
        cls.container=tempfile.TemporaryDirectory(dir=container)
        cls.baseline=Path(cls.container.name)/'baseline';cls.baseline.mkdir()
        archive=subprocess.check_output(['git','archive','--format=zip',policy.BASE,'assets/generated',
                                         'dist/abaqus-after-hours.sym','src/hardware.asm','src/trace.asm'],cwd=ROOT)
        with zipfile.ZipFile(io.BytesIO(archive)) as files:files.extractall(cls.baseline)
    @classmethod
    def tearDownClass(cls):cls.container.cleanup()
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(dir=self.container.name);self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)/'candidate';shutil.copytree(self.baseline,self.root)
        original_git=policy.git
        patch=mock.patch.object(policy,'git',side_effect=lambda root,*args:original_git(ROOT,*args))
        patch.start();self.addCleanup(patch.stop)
    def manifest(self):return json.loads((self.root/'assets/generated/character-manifest.json').read_bytes())
    def save_manifest(self,value):
        (self.root/'assets/generated/character-manifest.json').write_text(json.dumps(value),encoding='utf-8')
    def test_walk_bank_mutation_with_updated_metadata_rejected(self):
        path=self.root/'assets/generated/fighter00c.bin';raw=bytearray(path.read_bytes())
        at=4*3840;raw[at]^=128;path.write_bytes(raw)
        # Rewriting a reported current hash cannot approve an unowned walking pose.
        value=self.manifest();digest=hashlib.sha256(policy._decode_frame(raw[at:at+3840])).hexdigest()
        value[0]['frames'][20].update(native_hash=digest,pixels_sha256=digest)
        self.save_manifest(value)
        with self.assertRaisesRegex(ValueError,'Unowned native pose changed'):
            policy.fighter_frames(self.root,{})
    def test_palette_change_rejected(self):
        path=self.root/'assets/generated/fighter00_pal.bin';raw=bytearray(path.read_bytes());raw[2]^=1;path.write_bytes(raw)
        with self.assertRaisesRegex(ValueError,'Original palette changed'):policy.fighter_frames(self.root,{})
    def test_physical_scale_change_rejected(self):
        value=self.manifest();value[0]['physical_scale']*=1.01;self.save_manifest(value)
        with self.assertRaisesRegex(ValueError,'scale/height differs'):policy.fighter_frames(self.root,{})
    def test_prior_ram_relocation_rejected(self):
        path=self.root/'dist/abaqus-after-hours.sym';raw=path.read_text(encoding='utf-8')
        symbols=policy.symbols(raw);name=next(n for n,a in symbols.items() if n=='fighters')
        address=symbols[name]
        import re
        raw=re.sub(r'^([0-9a-fA-F]{6,8})(\s+'+name+r'\s*)$',lambda m:f'{address+1:08x}'+m[2],raw,flags=re.M)
        path.write_text(raw,encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'Prior RAM/ABI symbol moved'):policy.preserved_native(self.root)
    def test_trace_change_rejected(self):
        path=self.root/'src/trace.asm';path.write_text(path.read_text()+'\n; changed trace\n',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'Trace assembly changed'):policy.preserved_native(self.root)
    def test_transfer_assembly_change_rejected(self):
        path=self.root/'src/hardware.asm';path.write_text(path.read_text()+'\n; changed transfers\n',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'outside hit reaction'):policy.preserved_native(self.root)


if __name__=='__main__':unittest.main()
