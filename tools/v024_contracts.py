"""Independent v0.24 preservation checks against approved v0.23.1 Git bytes."""
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
from PIL import Image

BASE='f75005d'
FRAME_OWNERS={
    'attack-v1':{5,6,7,8,9,10,12,13,15,*range(32,46),47},
    'jump-v1':{29,30,31,*range(49,56)},
    'super-v1':{1,2,4},
}
SUFFIXES=('', 'b','c','d','e','f','g','h')
TEXT={'.json','.asm','.h','.c','.md','.txt','.ps1','.py'}
# Stage/contact additions are expanded only after their concrete allocation
# audit. No wildcard grants a generated directory or prefix permission.
STAGE_CHANGES=set()
ADDED_GENERATED=set()

def require(ok,message,details=None):
    if not ok:raise ValueError((message,details))

def git(root,*args):return subprocess.check_output(['git',*args],cwd=root)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(path,raw):return raw.replace(b'\r\n',b'\n') if Path(path).suffix.lower() in TEXT else raw

def active_scopes(root):
    return {scope:frames for scope,frames in FRAME_OWNERS.items() if (root/f'assets/art/{scope}.json').is_file()}

def _decode_frame(raw):
    require(len(raw)==3840,'Incorrect native pose byte count',len(raw))
    ids=bytearray(96*80)
    for ty in range(10):
        for tx in range(12):
            tile=raw[(ty*12+tx)*32:(ty*12+tx+1)*32]
            for y in range(8):
                p0,p1,p2,p3=tile[y*2],tile[y*2+1],tile[16+y*2],tile[17+y*2]
                for x in range(8):
                    bit=7-x
                    ids[(ty*8+y)*96+tx*8+x]=((p0>>bit)&1)|(((p1>>bit)&1)<<1)|(((p2>>bit)&1)<<2)|(((p3>>bit)&1)<<3)
    return bytes(ids)

def fighter_frames(root,scopes):
    """Check every bank slice, PNG pixel and native hash, not just report rows."""
    current=json.loads((root/'assets/generated/character-manifest.json').read_bytes())
    old=json.loads(git(root,'show',BASE+':assets/generated/character-manifest.json'))
    require(len(current)==len(old)==12,'Twelve fighter records required')
    mutable=set().union(*scopes.values()) if scopes else set();records=[]
    for f,(entry,prior) in enumerate(zip(current,old)):
        require(entry['id']==prior['id']==f and entry['frame_count']==64,'Fighter identity/frame count differs',f)
        require(entry['physical_scale']==prior['physical_scale'] and entry['standing_height']==prior['standing_height'],
                'Fighter scale/height differs',f)
        palette=(root/f'assets/generated/fighter{f:02d}_pal.bin').read_bytes()
        require(palette==git(root,'show',BASE+f':assets/generated/fighter{f:02d}_pal.bin'),'Original palette changed',f)
        colors=[]
        for i in range(0,32,2):
            p=int.from_bytes(palette[i:i+2],'little');colors.append(((p&31)<<3,((p>>5)&31)<<3,((p>>10)&31)<<3,255))
        colors[0]=(0,0,0,0)
        png=Image.open(root/f'assets/generated/fighter{f:02d}.png').convert('RGBA')
        before=Image.open(io.BytesIO(git(root,'show',BASE+f':assets/generated/fighter{f:02d}.png'))).convert('RGBA')
        require(png.size==before.size==(6144,80),'Native preview dimensions differ',f)
        banks=[];old_banks=[]
        for suffix in SUFFIXES:
            name=f'assets/generated/fighter{f:02d}{suffix}.bin'
            b=(root/name).read_bytes();a=git(root,'show',BASE+':'+name)
            require(len(a)==len(b)==30720,'Native bank size differs',name)
            banks.append(b);old_banks.append(a)
        changed=[]
        for n in range(64):
            bank=n//8;at=(n%8)*3840;b=banks[bank][at:at+3840];a=old_banks[bank][at:at+3840]
            preview=png.crop((n*96,0,(n+1)*96,80)).tobytes()
            if b!=a:changed.append(n)
            if n not in mutable:
                require(b==a and preview==before.crop((n*96,0,(n+1)*96,80)).tobytes(),'Unowned native pose changed',[f,n])
            ids=_decode_frame(b);rgba=b''.join(bytes(colors[c]) for c in ids)
            require(rgba==preview,'Preview differs from encoded native tiles',[f,n])
            item=entry['frames'][n]
            require(item['native_hash']==sha(ids) and item['pixels_sha256']==sha(ids),'Native frame hash differs',[f,n])
            if n in mutable:
                owner=next(scope for scope,frames in scopes.items() if n in frames)
                require(item['source_kind']==owner,'Native pose owner differs',[f,n,owner])
                require(sha((root/item['source_file']).read_bytes())==item['source_sha256'],'Selected art hash differs',[f,n])
        require(set(changed)<=mutable,'Unowned encoded frames differ',[f,changed])
        records.append({'fighter':f,'changed_frames':changed,'preserved_frames':64-len(changed)})
    return records

def preserved_assets(root):
    root=Path(root);scopes=active_scopes(root)
    allowed=set(STAGE_CHANGES)
    if scopes:
        allowed.add('assets/generated/character-manifest.json')
        for f in range(12):
            allowed.add(f'assets/generated/fighter{f:02d}.png')
            for bank in {n//8 for frames in scopes.values() for n in frames}:
                allowed.add(f'assets/generated/fighter{f:02d}{SUFFIXES[bank]}.bin')
    rows=git(root,'ls-tree','-r',BASE,'--','assets/generated','assets/art','assets/references').decode().splitlines()
    generated=[];protected=[];changed=[];baseline_names=set()
    for row in rows:
        info,name=row.split('\t',1);p=root/name
        require(p.is_file(),'Approved baseline input missing',name)
        raw=canonical(name,p.read_bytes());before=canonical(name,git(root,'show',BASE+':'+name));same=raw==before
        item={'path':name,'sha256':sha(raw),'baseline_blob':info.split()[2],'preserved':same}
        if name.startswith('assets/generated/'):
            baseline_names.add(name);generated.append(item)
            if not same:changed.append(name)
        else:
            require(same,'Approved source master/reference changed',name);protected.append(item)
    actual={p.relative_to(root).as_posix() for p in (root/'assets/generated').iterdir() if p.is_file() and p.name!='soundbank.h'}
    require(actual==baseline_names|ADDED_GENERATED,'Generated inventory differs',sorted(actual^(baseline_names|ADDED_GENERATED)))
    require(set(changed)<=allowed,'Generated change exceeds explicit allocation',sorted(set(changed)-allowed))
    for name in ADDED_GENERATED:
        generated.append({'path':name,'sha256':sha((root/name).read_bytes()),'baseline_blob':None,'preserved':False})
    frames=fighter_frames(root,scopes)
    return {'baseline_commit':BASE,'generated_count':len(generated),'preserved_generated':len(baseline_names)-len(changed),
            'changed_generated':sorted(changed),'added_generated':sorted(ADDED_GENERATED),'generated':generated,
            'protected_source_count':len(protected),'protected_source':protected,'frame_ownership':{k:sorted(v) for k,v in scopes.items()},'fighters':frames}

def symbols(raw):return {name:int(address,16) for address,name in re.findall(r'^([0-9a-fA-F]{6,8})\s+(\S+)\s*$',raw,re.M)}

def preserved_native(root):
    root=Path(root);old=symbols(git(root,'show',BASE+':dist/abaqus-after-hours.sym').decode())
    current=symbols((root/'dist/abaqus-after-hours.sym').read_text(encoding='utf-8'))
    ram=lambda a:a<0x2000 or 0x7e0000<=a<0x800000
    prior={n:a for n,a in old.items() if ram(a)};moved={}
    end_labels={'SECTIONEND_globram.data','RAM_USAGE_SLOT_3_BANK_127_END'}
    for n,a in prior.items():
        b=current.get(n)
        if n in end_labels:require(b is not None and 0<=b-a<=8,'Initialized state exceeds eight-byte allowance',[n,a,b])
        else:require(a==b,'Prior RAM/ABI symbol moved',[n,a,b])
        if a!=b:moved[n]={'before':a,'after':b,'delta':b-a}
    added={n:a for n,a in current.items() if n not in old and ram(a)}
    require(all(0x7f0593<=a<0x7f059b for a in added.values()),'New state escapes appended pacing allocation',added)
    for name in ('src/trace.asm',):require(canonical(name,(root/name).read_bytes())==canonical(name,git(root,'show',BASE+':'+name)),'Trace assembly changed',name)
    old_hw=git(root,'show',BASE+':src/hardware.asm').decode().replace('\r\n','\n')
    hw=(root/'src/hardware.asm').read_text(encoding='utf-8').replace('\r\n','\n')
    section=r'\.section "hit_reaction_fast" superfree.*?\.ends'
    require(re.sub(section,'<HIT_REACTION>',hw,flags=re.S)==re.sub(section,'<HIT_REACTION>',old_hw,flags=re.S),'Native transfer/hardware assembly changed outside hit reaction')
    crossings=[];total=0
    for n,start in current.items():
        if not n.startswith('SECTIONSTART_') or start<0x8000 or ram(start):continue
        end=current.get('SECTIONEND_'+n[len('SECTIONSTART_'):])
        if end is None or end<=start:continue
        total+=end-start
        if (start&0x7fff)+end-start>32768:crossings.append({'section':n,'start':start,'end':end})
    require(not crossings,'Section crosses 32KiB bank',crossings)
    return {'baseline_commit':BASE,'prior_ram_labels':len(prior),'unchanged_prior_ram_labels':len(prior)-len(moved),
            'documented_relocations':moved,'appended_ram_symbols':added,'linked_section_bytes':total,'bank_crossings':crossings,
            'abi_and_transfer_assembly_preserved':True,'hit_reaction_assembly_changed':hw!=old_hw,
            'hardware_and_trace_assembly_preserved':hw==old_hw}
