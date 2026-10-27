"""Bound Reston's small hair revision; all eleven other models stay exact."""
import hashlib,io,json,re,subprocess,tarfile,copy
from pathlib import Path
from v029_contracts import generated_report,require,symbols
from native_face_assets import MANIFEST,MANIFEST_SHA256
BASE='bb2237534bde5a377de5755f1d0d06596f398391'
BASE_ROM='64f7db0dea8b42be855abd836a8f7c9d2f249873a74116e4a0f06ee773631aad'
ALLOWED_CHANGED={'assets/generated/character-manifest.json','assets/generated/fighter09.png'}|{'assets/generated/fighter09'+s+'.bin' for s in ('','b','c','d','e','f','g','h')}
def git(root,*args):return subprocess.check_output(['git',*args],cwd=root)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def code(raw):return re.sub(r'\s+','',re.sub(r'/\*.*?\*/|//[^\n]*','',raw.replace(b'\r\n',b'\n').decode().replace('0.33.0','0.33.1'),flags=re.S))
def contact(rom,syms):
 address=syms['contactPoses'];offset=((address>>16)&127)*32768+(address&32767);return rom[offset:offset+12288]
def validate(root):
 root=Path(root);m=json.loads((root/'dist/manifest.json').read_bytes());rom=(root/'dist/abaqus-after-hours.sfc').read_bytes()
 require(m['version']=='0.33.1' and digest(rom)==m['sha256'],'Wrong Reston hair cartridge')
 oldm=json.loads(git(root,'show',BASE+':dist/manifest.json'));require(oldm['version']=='0.33.0' and oldm['sha256']==BASE_ROM,'Wrong approved all-roster base')
 with tarfile.open(fileobj=io.BytesIO(git(root,'archive',BASE,'assets/generated'))) as archive:prior={e.name:archive.extractfile(e).read() for e in archive.getmembers() if e.isfile()}
 generated=generated_report(root,prior,ALLOWED_CHANGED,set());require(len(prior)==237 and generated['current_count']==237,'Generated inventory changed')
 old=json.loads(prior['assets/generated/character-manifest.json']);new=json.loads((root/'assets/generated/character-manifest.json').read_bytes());require(len(new)==12,'Roster changed')
 oldart=json.loads(git(root,'show',BASE+':'+MANIFEST));art=json.loads((root/MANIFEST).read_bytes());require(digest((root/MANIFEST).read_bytes())==MANIFEST_SHA256,'Native face manifest changed')
 for fid in range(12):
  a,b=copy.deepcopy(old[fid]),copy.deepcopy(new[fid]);a['native_face_revision'].pop('manifest_sha256');b['native_face_revision'].pop('manifest_sha256')
  require(new[fid]['native_face_revision']['manifest_sha256']==MANIFEST_SHA256,'Wrong manifest binding',fid)
  if fid!=9:
   require(a==b and oldart['fighters'][fid]==art['fighters'][fid],'Another accepted fighter changed',fid)
  for key in ('palette','physical_scale','standing_height','frame_canvas','baseline_y','frame_count','portrait_framing'):
   require(new[fid][key]==old[fid][key],'Palette/physical/portrait contract changed',(fid,key))
  require([f['pose'] for f in new[fid]['frames']]==[f['pose'] for f in old[fid]['frames']],'Pose roles changed',fid)
 row=art['fighters'][9];generation=json.loads((root/row['provenance']).read_bytes())
 require(digest((root/row['source']).read_bytes())==row['sha256']==generation['raw_output_sha256'] and digest((root/row['provenance']).read_bytes())==row['provenance_sha256'] and generation['mode']=='built-in image_gen','Reston source/provenance changed')
 require(new[9]['native_face_revision']['frame_range']==[0,63] and [f['native_hash'] for f in new[9]['frames']]==row['frame_sha256'],'Reston pose set incomplete')
 for ref,pin in generation['reference_sha256'].items():require(digest((root/ref).read_bytes())==pin,'Reston reference changed',ref)
 oldsyms=symbols(git(root,'show',BASE+':dist/abaqus-after-hours.sym'));syms=symbols((root/'dist/abaqus-after-hours.sym').read_bytes());ram={k:v for k,v in oldsyms.items() if v<0x8000 or v>>16 in (0x7e,0x7f)}
 require(len(ram)==1331 and all(syms.get(k)==v for k,v in ram.items()),'Prior RAM/data label moved')
 a=contact(git(root,'show',BASE+':dist/abaqus-after-hours.sfc'),oldsyms);b=contact(rom,syms)
 require(len(a)==len(b)==12288 and all(a[n*1024:(n+1)*1024]==b[n*1024:(n+1)*1024] for n in range(12) if n!=9),'Another fighter contact geometry changed')
 sources=git(root,'ls-tree','-r','--name-only',BASE,'src').decode().splitlines();require(set(sources)=={p.relative_to(root).as_posix() for p in (root/'src').iterdir() if p.is_file()},'Native source inventory changed')
 for name in sources:require(code(git(root,'show',BASE+':'+name))==code((root/name).read_bytes()),'Native rules changed beyond version',name)
 sections=[]
 for name,start in syms.items():
  if not name.startswith('SECTIONSTART_') or start<0x800000:continue
  end=syms.get(name.replace('SECTIONSTART_','SECTIONEND_'))
  if end is None:continue
  require(0<=end-start<=32768 and (end==start or start>>16==(end-1)>>16),'ROM section exceeds bank',name);sections.append(end-start)
 return {'status':'passed','version':m['version'],'rom_sha256':m['sha256'],'baseline_commit':BASE,'generated':generated,'fighter_id':9,'poses_covered':64,'eleven_accepted_models_exact':True,'all_portrait_and_palette_bytes_exact':True,'other_eleven_contact_geometry_blocks_exact':True,'native_rules_except_version_exact':True,'prior_ram_labels_exact':len(ram),'maximum_native_section_bytes':max(sections),'new_OBJ_or_DMA_resources':False}
