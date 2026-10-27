"""Bound in-game expressions while preserving the pre-change select portraits."""
import hashlib,io,json,re,subprocess,tarfile
from pathlib import Path
from v029_contracts import generated_report,require,symbols
BASE='961214932f2ff0cef388635f16ca883e688b3668'
BASE_ROM='187a327c8854bfe568184dcc46c6c59f7d1d3460a60c02a6c1aeb18151b39579'
COMBAT_REFERENCE='1f95209d29cf7be240d5868dee0e09d52e949f03'
TARGETS={1,6,7}
ALLOWED_CHANGED={'assets/generated/'+name for name in ('assets.h','character-manifest.json')}
for fid in TARGETS:
    ALLOWED_CHANGED.update('assets/generated/'+name for name in ([f'fighter{fid:02d}.png']+[f'fighter{fid:02d}{suffix}.bin' for suffix in ('','b','c','d','e','f','g','h')]))
def git(root,*args):return subprocess.check_output(['git',*args],cwd=root)
def canonical(raw):return raw.replace(b'\r\n',b'\n')
def code(raw):
    text=canonical(raw).decode().replace('0.31.0','0.32.1')
    return re.sub(r'\s+','',re.sub(r'/\*.*?\*/|//[^\n]*','',text,flags=re.S))
def digest(raw):return hashlib.sha256(raw).hexdigest()
def validate(root):
    root=Path(root);manifest=json.loads((root/'dist/manifest.json').read_bytes())
    require(manifest['version']=='0.32.1' and digest((root/'dist/abaqus-after-hours.sfc').read_bytes())==manifest['sha256'],'Wrong v0.32.1 cartridge')
    baseline=json.loads(git(root,'show',BASE+':dist/manifest.json'))
    require(baseline['version']=='0.31.0' and baseline['sha256']==BASE_ROM,'Wrong v0.31 body reference')
    with tarfile.open(fileobj=io.BytesIO(git(root,'archive',BASE,'assets/generated'))) as archive:
        prior={m.name:archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()}
    generated=generated_report(root,prior,ALLOWED_CHANGED,set())
    require(len(prior)==237 and generated['current_count']==237,'Generated inventory changed')
    old=json.loads(prior['assets/generated/character-manifest.json']);new=json.loads((root/'assets/generated/character-manifest.json').read_bytes())
    require(len(new)==12 and all(old[n]==new[n] for n in range(12) if n not in TARGETS),'Another fighter changed')
    combat=json.loads(git(root,'show',COMBAT_REFERENCE+':assets/generated/character-manifest.json'))
    portrait_paths=[f'assets/generated/portrait{fid:02d}{suffix}' for fid in range(12) for suffix in ('.png','-large.png','_pal.bin','_tiles.bin')]
    select_paths=['assets/generated/'+name for name in ('select.png','select_map.bin','select_pal.bin','select_tiles.bin')]
    require(all((root/p).read_bytes()==prior[p] for p in portrait_paths+select_paths),'Selection portrait or roster art changed')
    art=[]
    for fid,slug in [(1,'ivo'),(6,'fernando'),(7,'cristian')]:
        for key in ('palette','physical_scale','standing_height','frame_canvas','baseline_y','frame_count'):
            require(new[fid][key]==old[fid][key],'Revised palette/physical contract changed',(fid,key))
        require([f['pose'] for f in new[fid]['frames']]==[f['pose'] for f in old[fid]['frames']],'Move/frame roles changed',fid)
        changed=sum(a['native_hash']!=b['native_hash'] for a,b in zip(old[fid]['frames'],new[fid]['frames']))
        require(changed==64,'Incomplete expression revision',fid)
        require(new[fid]['frames']==combat[fid]['frames'],'Existing in-game expression frames changed',fid)
        for filename in [f'fighter{fid:02d}.png']+[f'fighter{fid:02d}{suffix}.bin' for suffix in ('','b','c','d','e','f','g','h')]:
            p='assets/generated/'+filename
            require((root/p).read_bytes()==git(root,'show',COMBAT_REFERENCE+':'+p),'In-game sprite bytes changed during portrait restoration',p)
        directory=f'assets/art/characters/{fid:02d}-{slug}'
        head=directory+'/expression-study-v032/head.png';head_sha=digest(git(root,'show',BASE+':'+head))
        require(digest((root/head).read_bytes())==head_sha,'Approved expression master changed',fid)
        framing=new[fid]['portrait_framing']
        require(framing==old[fid]['portrait_framing'],'Selection portrait framing changed',fid)
        record=json.loads((root/directory/'expression-v032-generation.json').read_bytes())
        require(record['reference_direction_approval']['quote']=='Yes, use this direction' and len(record['assets'])==9,'Missing approved expression scope',fid)
        for asset in record['assets']:
            require(asset['mode']=='built-in image_gen' and digest((root/asset['selected_final']).read_bytes())==asset['sha256']==asset['raw_output_sha256'],'Generated source identity changed',asset['source'])
            target=asset['references'][0]
            require(digest((root/target['path']).read_bytes())==target['sha256']==digest(git(root,'show',BASE+':'+target['path'])),'v0.31 body target changed',target['path'])
            require(asset['references'][1]['path']==head and asset['references'][1]['sha256']==head_sha,'Wrong expression guide',fid)
        art.append({'id':fid,'changed_frames':changed,'approved_expression_reference_sha256':head_sha,'animation_atlases':9,'selection_portrait_restored_exact':True})
    old_syms=symbols(git(root,'show',BASE+':dist/abaqus-after-hours.sym'));new_syms=symbols((root/'dist/abaqus-after-hours.sym').read_bytes())
    ram={k:v for k,v in old_syms.items() if v<0x8000 or v>>16 in (0x7e,0x7f)}
    require(all(new_syms.get(k)==v for k,v in ram.items()),'Prior RAM/data address moved')
    combat_syms=symbols(git(root,'show',COMBAT_REFERENCE+':dist/abaqus-after-hours.sym'))
    def contact_bytes(rom,syms):
        address=syms['contactPoses'];offset=((address>>16)&127)*32768+(address&32767)
        return rom[offset:offset+12288]
    require(contact_bytes((root/'dist/abaqus-after-hours.sfc').read_bytes(),new_syms)==contact_bytes(git(root,'show',COMBAT_REFERENCE+':dist/abaqus-after-hours.sfc'),combat_syms),'Combat geometry changed during portrait restoration')
    sources=git(root,'ls-tree','-r','--name-only',BASE,'src').decode().splitlines()
    require(set(sources)=={p.relative_to(root).as_posix() for p in (root/'src').iterdir() if p.is_file()},'Native source inventory changed')
    for name in sources:require(code(git(root,'show',BASE+':'+name))==code((root/name).read_bytes()),'Native rules changed beyond version',name)
    for scope in ('walking-v2','attack-v1','jump-v1','super-v1'):
        name='assets/art/'+scope+'.json';a=json.loads(git(root,'show',BASE+':'+name));b=json.loads((root/name).read_bytes())
        require(all(x==y for x,y in zip(a['fighters'],b['fighters']) if x['id'] not in TARGETS),'Another fighter source index changed',scope)
    sections=[]
    for name,start in new_syms.items():
        if not name.startswith('SECTIONSTART_') or start<0x800000:continue
        end=new_syms.get(name.replace('SECTIONSTART_','SECTIONEND_'))
        if end is None:continue
        require(0<=end-start<=32768 and (end==start or start>>16==(end-1)>>16),'ROM section exceeds one bank',name)
        sections.append(end-start)
    return {'status':'passed','baseline_commit':BASE,'baseline_scope':'v0.31 selection portrait and body-design reference; its in-game faces were rejected','combat_reference':COMBAT_REFERENCE,'all_existing_v032_combat_frames_exact':True,'all_selection_portraits_and_roster_art_exact':True,'version':manifest['version'],'rom_sha256':manifest['sha256'],'generated':generated,'other_fighters_exact':9,'revised_palette_scale_roles_exact':True,'revised_ids':sorted(TARGETS),'expression_art':art,'prior_ram_labels_exact':len(ram),'native_rules_except_version_exact':True,'maximum_native_section_bytes':max(sections),'native_geometry':'Only the three revised fighter blocks may differ from v0.31; the full geometry must stay exact to v0.32.'}
