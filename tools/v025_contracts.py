"""Independent preservation/budget policy for the authorized pacing/floor pass."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import io

BASE='8f028775f1712fc210d9cebf21c418c31e62f3c8'
BASE_ROM='408cadfdddef97a24215e40f6ddb366140bc68fc80e7f1de82ee87e4084beb79'
OFFICE_SOURCE='02309e1227bd60af0036707430c20113c5c59025780acf49c477624736cd96eb'
STAGE_CHANGES={'assets/generated/assets.h','assets/generated/stage-depth.json'}|{
    f'assets/generated/stage{i}{suffix}' for i in range(3)
    for suffix in ('.png','_tiles.bin','_map.bin','_pal.bin','_floor_tiles.bin','_floor_map.bin')}

def require(ok,message,details=None):
    if not ok:raise AssertionError((message,details))

def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(path,raw):return raw.replace(b'\r\n',b'\n') if Path(path).suffix in ('.json','.h','.asm','.py','.c','.md','.txt','.ps1') else raw
def git(root,*args):return subprocess.check_output(['git',*args],cwd=root)
def symbols(raw):return {n:int(a,16) for a,n in re.findall(r'^([0-9a-fA-F]{8}) (\S+)$',raw.decode(),re.M)}

def validate(root, allow_arena_previews=False, allow_classic_menus=False):
    root=Path(root)
    git(root,'merge-base','--is-ancestor',BASE,'HEAD')
    prior_manifest=json.loads(git(root,'show',BASE+':dist/manifest.json'))
    require(prior_manifest['sha256']==BASE_ROM,'Approved v0.24 baseline differs')
    names=git(root,'ls-tree','-r','--name-only',BASE,'--','assets/generated').decode().splitlines()
    actual={p.relative_to(root).as_posix() for p in (root/'assets/generated').iterdir() if p.is_file() and p.name!='soundbank.h'}
    require(actual==set(names) and len(actual)==226,'Exact 226-file generated inventory retained')
    changed=[];preserved=[]
    for name in names:
        raw=canonical(name,(root/name).read_bytes())
        before=canonical(name,git(root,'show',BASE+':'+name))
        (preserved if raw==before else changed).append(name)
    allowed=STAGE_CHANGES|({'assets/generated/arenas'+suffix for suffix in ('.png','_tiles.bin','_map.bin','_pal.bin')}
                           if allow_arena_previews else set())
    if allow_classic_menus:
        # The menu follow-up retains every v0.26.2 stage byte. Independently
        # bind its bounded menu changes to that committed parent as well.
        from test_classic_menu import preservation
        preservation()
        allowed|={f'assets/generated/{stem}{suffix}' for stem in ('title','select','arenas')
                  for suffix in ('.png','_tiles.bin','_map.bin','_pal.bin')}
    require(set(changed)<=allowed,'Generated change escapes reviewed floor/menu scope',sorted(set(changed)-allowed))
    protected=git(root,'ls-tree','-r','--name-only',BASE,'--','assets/art','assets/references').decode().splitlines()
    for name in protected:
        require(canonical(name,(root/name).read_bytes())==canonical(name,git(root,'show',BASE+':'+name)),
                'Existing art/provenance/reference changed',name)
    old=symbols(git(root,'show',BASE+':dist/abaqus-after-hours.sym'))
    new=symbols((root/'dist/abaqus-after-hours.sym').read_bytes())
    ram=lambda a:a<0x2000 or 0x7e0000<=a<0x800000
    prior={n:a for n,a in old.items() if ram(a)}
    moved={n:[a,new.get(n)] for n,a in prior.items() if new.get(n)!=a}
    added={n:a for n,a in new.items() if ram(a) and n not in old}
    require(len(prior)==1318 and not moved and not added,'RAM/ABI moved or grew',[moved,added])
    require(canonical('trace.asm',(root/'src/trace.asm').read_bytes())==canonical('trace.asm',git(root,'show',BASE+':src/trace.asm')),
            'Native trace assembly changed')
    def reaction_code(raw):
        text=raw.decode('utf-8');text=re.sub(r';[^\n]*','',text)
        return re.sub(r'hitStunByDamage:.*?\.ends','hitStunByDamage:\n.ends',text,flags=re.S)
    require(reaction_code((root/'src/hardware.asm').read_bytes()).split()==reaction_code(git(root,'show',BASE+':src/hardware.asm')).split(),
            'Only hit-stun ROM table changes in native hardware assembly')
    rom=(root/'dist/abaqus-after-hours.sfc').read_bytes()
    address=new['hitStunByDamage'];offset=((address>>16)&127)*32768+(address&32767)
    require(rom[offset:offset+256]==bytes(16+d//3 for d in range(256)),
            'All 256 compiled damage-to-stun values match the reviewed v0.25 contract')
    sections=[]
    for name,start in new.items():
        if name.startswith('SECTIONSTART_') and start>=0x800000:
            end=new.get(name.replace('SECTIONSTART_','SECTIONEND_'))
            if end is not None:
                require(0<=end-start<=32768 and (start>>16)==((end-1)>>16), 'Linked section crosses a native bank',[name,start,end])
                sections.append(end-start)
    depth=json.loads((root/'assets/generated/stage-depth.json').read_bytes())
    require(depth['floor_plane']=='BG1' and depth['bg3']['enabled'] is False and depth['bg1']['gfx_word']==[0,0x37ff],
            'Full-color floor and scenery share the declared native plane')
    from stage_depth_assets import build_stage,colors
    records=json.loads((root/'assets/art/stages/depth-v1/stages.json').read_bytes())['stages']
    require([r['id'] for r in depth['stages']]==[0,1,2],'All three stage records required')
    require(sha((root/'assets/art/stages/floor-v025/02-oficina.png').read_bytes())==OFFICE_SOURCE,
            'Reviewed office material changed')
    ui_palette=colors((root/'assets/generated/ui_pal.bin').read_bytes())
    for row,record in zip(depth['stages'],records,strict=True):
        expected,preview,metadata=build_stage(root,record,ui_palette)
        require(row==metadata,'Stage metadata differs from retained source conversion',row['id'])
        require(row['bg1_tiles']<=896,'Stage exceeds its reclaimed 28 KiB tile allocation',row['id'])
        require(set(row['outputs'])==set(expected),'Stage payload inventory differs',row['id'])
        for name,item in row['outputs'].items():
            raw=(root/'assets/generated'/name).read_bytes()
            require(raw==expected[name] and len(raw)==item['bytes'] and sha(raw)==item['sha256'],
                    'Encoded stage differs from retained source pixels',name)
        buffer=io.BytesIO();preview.save(buffer,format='PNG')
        require((root/f"assets/generated/stage{row['id']}.png").read_bytes()==buffer.getvalue(),
                'Native stage preview differs from encoded source conversion',row['id'])
    require(len(rom)==4194304 and rom[0x7fd5]==0x30,'Native NTSC FastROM LoROM image required')
    return {'baseline_commit':BASE,'baseline_rom_sha256':BASE_ROM,'generated_count':226,'changed_generated':changed,
            'preserved_generated':len(preserved),'protected_art_inputs':len(protected),'unchanged_ram_labels':len(prior),
            'added_ram_symbols':added,'moved_ram_symbols':moved,'all_fighter_art_palettes_and_portraits_exact':True,
            'largest_linked_section_bytes':max(sections),'stage_tile_counts':[r['bg1_tiles'] for r in depth['stages']],
            'hit_stun_table':'16+floor(damage/3);256 compiled entries verified','hardware_instruction_changes':False}
