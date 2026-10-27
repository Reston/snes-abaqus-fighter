"""Bound the all-roster native face artwork and preserve non-fighter assets."""
import hashlib,io,json,re,subprocess,tarfile
from pathlib import Path
from v029_contracts import generated_report,require,symbols
from native_face_assets import MANIFEST,MANIFEST_SHA256
BASE='5c1bb02ec2c4576572eb67f00b568bc6726bfc4e'
TARGETS=set(range(12))
ALLOWED_CHANGED={'assets/generated/assets.h','assets/generated/character-manifest.json'}
for fid in TARGETS:
    ALLOWED_CHANGED.update('assets/generated/'+name for name in
        [f'fighter{fid:02d}.png',f'fighter{fid:02d}_pal.bin']+
        [f'fighter{fid:02d}{suffix}.bin' for suffix in ('','b','c','d','e','f','g','h')])
def git(root,*args):return subprocess.check_output(['git',*args],cwd=root)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def canonical(raw):return raw.replace(b'\r\n',b'\n')
def code(raw):
    text=canonical(raw).decode().replace('0.32.1','0.33.0')
    return re.sub(r'\s+','',re.sub(r'/\*.*?\*/|//[^\n]*','',text,flags=re.S))
def validate(root):
    root=Path(root);manifest=json.loads((root/'dist/manifest.json').read_bytes())
    require(manifest['version']=='0.33.0' and digest((root/'dist/abaqus-after-hours.sfc').read_bytes())==manifest['sha256'],'Wrong native face cartridge')
    baseline=json.loads(git(root,'show',BASE+':dist/manifest.json'))
    require(baseline['version']=='0.32.1' and baseline['sha256']=='1dc456430a706fd0e6ac3a4d25bc0455b1cf9e034599d15e581962202dda628b','Wrong native face baseline')
    with tarfile.open(fileobj=io.BytesIO(git(root,'archive',BASE,'assets/generated'))) as archive:
        prior={m.name:archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()}
    generated=generated_report(root,prior,ALLOWED_CHANGED,set())
    require(len(prior)==237 and generated['current_count']==237,'Generated asset inventory changed')
    old=json.loads(prior['assets/generated/character-manifest.json']);new=json.loads((root/'assets/generated/character-manifest.json').read_bytes())
    require(len(new)==12 and [r['id'] for r in new]==list(range(12)),'Roster changed')
    require(digest((root/MANIFEST).read_bytes())==MANIFEST_SHA256,'Native face manifest changed')
    art=json.loads((root/MANIFEST).read_bytes());rows=art['fighters'];changed=[]
    for fid in range(12):
        for key in ('physical_scale','standing_height','frame_canvas','baseline_y','frame_count'):
            require(new[fid][key]==old[fid][key],'Actor size/ABI changed',(fid,key))
        require(new[fid]['portrait_framing']==old[fid]['portrait_framing'],'Portrait framing changed',fid)
        require([f['pose'] for f in new[fid]['frames']]==[f['pose'] for f in old[fid]['frames']],'Pose roles changed',fid)
        revision=new[fid]['native_face_revision'];row=rows[fid]
        require(revision['frame_range']==[0,63] and revision['scope']=='native-pixel-faces' and
                revision['native64_sha256']==row['native64_sha256'],'Native face scope incomplete',fid)
        require(new[fid]['palette']==[[0,0,0]]+row['palette'] and len(row['palette'])==15,
                'Native actor exceeds palette budget',fid)
        for suffix in ('.png','-large.png','_pal.bin','_tiles.bin'):
            name=f'assets/generated/portrait{fid:02d}{suffix}'
            require((root/name).read_bytes()==prior[name],'Selection portrait changed',name)
        for descriptor in ('source','provenance'):
            path=root/row[descriptor];pin=row['sha256' if descriptor=='source' else 'provenance_sha256']
            require(digest(path.read_bytes())==pin,'Native art source/provenance changed',str(path))
        require([f['native_hash'] for f in new[fid]['frames']]==row['frame_sha256'],
                'Final pose hashes differ from reviewed native art',fid)
        changed.append({'id':fid,'poses_covered':64,'poses_changed':sum(a['native_hash']!=b['native_hash'] for a,b in zip(old[fid]['frames'],new[fid]['frames'])),'palette_colours':15,'skin_indices':[10,11,12,13,14,15]})
    for name in ('select.png','select_map.bin','select_pal.bin','select_tiles.bin'):
        path='assets/generated/'+name;require((root/path).read_bytes()==prior[path],'Roster artwork changed',name)
    old_syms=symbols(git(root,'show',BASE+':dist/abaqus-after-hours.sym'));new_syms=symbols((root/'dist/abaqus-after-hours.sym').read_bytes())
    ram={k:v for k,v in old_syms.items() if v<0x8000 or v>>16 in (0x7e,0x7f)}
    require(all(new_syms.get(k)==v for k,v in ram.items()),'Prior RAM/data label moved')
    sources=git(root,'ls-tree','-r','--name-only',BASE,'src').decode().splitlines()
    require(set(sources)=={p.relative_to(root).as_posix() for p in (root/'src').iterdir() if p.is_file()},'Native source inventory changed')
    for name in sources:require(code(git(root,'show',BASE+':'+name))==code((root/name).read_bytes()),'Native rules changed beyond version',name)
    sections=[]
    for name,start in new_syms.items():
        if not name.startswith('SECTIONSTART_') or start<0x800000:continue
        end=new_syms.get(name.replace('SECTIONSTART_','SECTIONEND_'))
        if end is None:continue
        require(0<=end-start<=32768 and (end==start or start>>16==(end-1)>>16),'ROM section exceeds one bank',name)
        sections.append(end-start)
    return {'status':'passed','version':manifest['version'],'rom_sha256':manifest['sha256'],'baseline_commit':BASE,'generated':generated,'fighters':changed,'all_selection_portraits_and_roster_art_exact':True,'native_rules_except_version_exact':True,'prior_ram_labels_exact':len(ram),'maximum_native_section_bytes':max(sections),'poses':768,'new_OBJ_or_DMA_resources':False,'contact_geometry':'Refreshed only from final actor pixels; move timing/damage/input rules remain exact.'}
