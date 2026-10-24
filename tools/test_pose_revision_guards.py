"""Bounded source/palette/frame-ownership mutations for the v0.24 art overlay."""
import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from pose_revision_assets import apply_pose_revision

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

class PoseRevisionGuards(unittest.TestCase):
    def setUp(self):
        container=ROOT/'build/pose-revision-tests';container.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=container);self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.directory=self.root/'assets/art/characters/00-damian';self.directory.mkdir(parents=True)
        self.source=self.directory/'super-v1.png';Image.new('RGBA',(32,64),(255,120,40,255)).save(self.source)
        self.reference=self.directory/'reference.png';self.reference.write_bytes(b'approved reference bytes')
        self.colors=[(i*8,i*8,i*8) for i in range(15)]
        packed=bytearray()
        for r,g,b in [(0,0,0)]+self.colors:packed.extend(((r>>3)|((g>>3)<<5)|((b>>3)<<10)).to_bytes(2,'little'))
        self.record={'fighter_id':0,'scope':'super-v1','reference':self.reference.relative_to(self.root).as_posix(),
            'reference_sha256':sha(self.reference),'palette_sha256':hashlib.sha256(packed).hexdigest(),
            'sources':[{'file':self.source.relative_to(self.root).as_posix(),'sha256':sha(self.source),'count':8,
                        'poses':[str(i) for i in range(8)],'frames':[1,2,4,None,None,None,None,None]}],
            'anchor':{'source':0,'pose':0}}
        self.provenance=self.directory/'super-v1.json'
        self.index={'schema':1,'scope':'super-v1','fighters':[{'id':i,'slug':('00-damian' if i==0 else f'{i:02d}-fixture'),
                     'provenance':self.provenance.relative_to(self.root).as_posix(),'provenance_sha256':''} for i in range(12)]}
        self.save()
    def save(self):
        self.provenance.write_bytes((json.dumps(self.record)+'\n').encode())
        for row in self.index['fighters']:row['provenance_sha256']=sha(self.provenance)
        (self.root/'assets/art/super-v1.json').write_bytes((json.dumps(self.index)+'\n').encode())
    def run_overlay(self):
        frames=[[0]*7680 for _ in range(64)];meta=[{'physical_scale':1.0} for _ in range(64)]
        preview=Image.new('RGBA',(6144,80))
        def extract(path,pose_names,expected_count):
            return [Image.new('RGBA',(30+i,64),(200,120,40,255)) for i in range(expected_count)], [{'pose':p,'source_box':[0,0,32,64]} for p in pose_names]
        value=apply_pose_revision(self.root,0,'damian',frames,meta,self.colors,preview,extract,69,'super-v1')
        return value,[n for n,frame in enumerate(frames) if any(frame)]
    def test_only_owned_frames_publish(self):
        value,changed=self.run_overlay();self.assertEqual(changed,[1,2,4]);self.assertEqual(value['frame_ids'],[1,2,4])
    def test_mutated_selected_source_rejected(self):
        self.source.write_bytes(b'tampered');self.assertRaisesRegex(ValueError,'source hash',self.run_overlay)
    def test_mutated_reference_rejected(self):
        self.reference.write_bytes(b'tampered');self.assertRaisesRegex(ValueError,'reference changed',self.run_overlay)
    def test_mutated_provenance_rejected(self):
        self.provenance.write_bytes(b'{}');self.assertRaisesRegex(ValueError,'provenance hash',self.run_overlay)
    def test_unauthorized_target_rejected(self):
        self.record['sources'][0]['frames'][2]=20;self.save();self.assertRaisesRegex(ValueError,'target ownership',self.run_overlay)
    def test_duplicate_target_rejected(self):
        self.record['sources'][0]['frames'][2]=2;self.save();self.assertRaisesRegex(ValueError,'target ownership',self.run_overlay)
    def test_incomplete_roster_rejected(self):
        self.index['fighters'].pop();self.save();self.assertRaisesRegex(ValueError,'incomplete roster',self.run_overlay)
    def test_wrong_palette_rejected(self):
        self.record['palette_sha256']='0'*64;self.save();self.assertRaisesRegex(ValueError,'palette changed',self.run_overlay)
    def test_individual_scale_change_rejected(self):
        self.record['height_target']=68;self.save();self.assertRaisesRegex(ValueError,'standing height',self.run_overlay)

if __name__=='__main__':unittest.main()
