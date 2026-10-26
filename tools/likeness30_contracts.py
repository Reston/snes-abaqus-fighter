"""Bound the v0.30 spelling/one-fighter art revision to approved v0.29."""
import hashlib,io,json,re,subprocess,tarfile
from pathlib import Path
from v029_contracts import generated_report,require,symbols
BASE='c4cf41148f76e202d958e8f2e3e2f040505054c1'
BASE_ROM='7e93c7f233ac557f0f5687e952f0ece9ab9c0e54e3c108d04dd0b39c7d26afa0'
ALLOWED_CHANGED={
 'assets/generated/'+name for name in (
 'assets.h','character-manifest.json','fighter06.png',
 'fighter06.bin','fighter06b.bin','fighter06c.bin','fighter06d.bin',
 'fighter06e.bin','fighter06f.bin','fighter06g.bin','fighter06h.bin',
 'portrait06.png','portrait06-large.png','portrait06_pal.bin','portrait06_tiles.bin',
 'select.png','select_map.bin','select_pal.bin','select_tiles.bin')}
def git(root,*args):return subprocess.check_output(['git',*args],cwd=root)
def canonical(raw):return raw.replace(b'\r\n',b'\n')
def code(raw):
 text=canonical(raw).decode().replace('MAMARIAGA','MADARIAGA').replace('0.29.0','0.30.0')
 return re.sub(r'\s+','',re.sub(r'/\*.*?\*/|//[^\n]*','',text,flags=re.S))
def validate(root):
 root=Path(root);manifest=json.loads((root/'dist/manifest.json').read_bytes())
 require(manifest['version']=='0.30.0' and hashlib.sha256((root/'dist/abaqus-after-hours.sfc').read_bytes()).hexdigest()==manifest['sha256'],'Wrong v0.30 cartridge')
 baseline=json.loads(git(root,'show',BASE+':dist/manifest.json'))
 require(baseline['version']=='0.29.0' and baseline['sha256']==BASE_ROM,'Wrong approved baseline')
 with tarfile.open(fileobj=io.BytesIO(git(root,'archive',BASE,'assets/generated'))) as archive:
  prior={m.name:archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()}
 generated=generated_report(root,prior,ALLOWED_CHANGED,set())
 require(len(prior)==237 and generated['current_count']==237,'Generated inventory changed')
 old=json.loads(prior['assets/generated/character-manifest.json']);new=json.loads((root/'assets/generated/character-manifest.json').read_bytes())
 require(len(new)==12 and all(old[n]==new[n] for n in range(12) if n!=6),'Another fighter changed')
 for key in ('palette','physical_scale','standing_height','frame_canvas','baseline_y','frame_count'):
  require(new[6][key]==old[6][key],'Fernando palette/physical contract changed',key)
 require([f['pose'] for f in new[6]['frames']]==[f['pose'] for f in old[6]['frames']],'Fernando move/frame roles changed')
 old_syms=symbols(git(root,'show',BASE+':dist/abaqus-after-hours.sym'));new_syms=symbols((root/'dist/abaqus-after-hours.sym').read_bytes())
 ram={k:v for k,v in old_syms.items() if v<0x8000 or v>>16 in (0x7e,0x7f)}
 require(all(new_syms.get(k)==v for k,v in ram.items()),'Prior RAM/data address moved')
 sources=git(root,'ls-tree','-r','--name-only',BASE,'src').decode().splitlines()
 require(set(sources)=={p.relative_to(root).as_posix() for p in (root/'src').iterdir() if p.is_file()},'Native source inventory changed')
 for name in sources:require(code(git(root,'show',BASE+':'+name))==code((root/name).read_bytes()),'Native rules changed beyond spelling/version',name)
 for scope in ('walking-v2','attack-v1','jump-v1','super-v1'):
  name='assets/art/'+scope+'.json';a=json.loads(git(root,'show',BASE+':'+name));b=json.loads((root/name).read_bytes())
  require(all(x==y for x,y in zip(a['fighters'],b['fighters']) if x['id']!=6),'Another fighter source index changed',scope)
 sections=[]
 for name,start in new_syms.items():
  if not name.startswith('SECTIONSTART_') or start<0x800000:continue
  end=new_syms.get(name.replace('SECTIONSTART_','SECTIONEND_'))
  if end is None:continue
  require(0<=end-start<=32768 and (end==start or start>>16==(end-1)>>16),'ROM section exceeds one bank',name)
  sections.append(end-start)
 return {'status':'passed','baseline_commit':BASE,'version':manifest['version'],'rom_sha256':manifest['sha256'],'generated':generated,'other_fighters_exact':11,'Fernando_palette_scale_roles_exact':True,'prior_ram_labels_exact':len(ram),'native_rules_except_spelling_version_exact':True,'maximum_native_section_bytes':max(sections),'native_geometry':'Rectangles are regenerated from the revised Fernando pixels; eleven other fighter geometry blocks remain exact.'}
