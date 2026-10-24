"""Isolated v0.24 attack-art proof: canonical background Python, native PPU.

Read-only WRAM/VRAM/OAM and actual controllers only. No saves, windows or
audio devices. This does not run or replace the parent's six native suites.
Run after tools/build.py --assets; --fighter N is an ignored diagnostic run.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,io,json,platform,subprocess,sys,time
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from fighter_assets import extract_atlas,HEIGHTS
from test_characters import boot
from test_inputs import trace
from test_champion import host_contract
from test_endurance import core_identity
from test_expansion_01_animation_weight import Probe,symbols,address

BASE='f75005d'
OWNED={5,6,7,8,9,10,12,13,15,*range(32,46),47}
OUT=ROOT/'docs/screenshots/combat-24-attack'
CHECKS=[]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def old(path):return git('show',BASE+':'+path)
def check(ok,label,detail=None):
    CHECKS.append({'passed':bool(ok),'check':label,'detail':detail})
    if not ok:raise AssertionError((label,detail))
def write(path,value):path.write_bytes((json.dumps(value,indent=2)+'\n').encode())

def art_contract():
    index=json.loads((ROOT/'assets/art/attack-v1.json').read_bytes())
    check(index['schema']==1 and len(index['fighters'])==12,'complete versioned attack index')
    result=[]
    for row in index['fighters']:
        f=row['id'];p=ROOT/row['provenance'];record=json.loads(p.read_bytes())
        check(sha(p.read_bytes())==row['provenance_sha256'],'exact individual provenance hash',f)
        check(sha((ROOT/record['reference']).read_bytes())==record['reference_sha256'],'exact approved reference hash',f)
        new=Image.open(ROOT/f'assets/generated/fighter{f:02d}.png').convert('RGBA')
        prior=Image.open(io.BytesIO(old(f'assets/generated/fighter{f:02d}.png'))).convert('RGBA')
        check(new.size==prior.size==(6144,80),'64 fixed native canvases',f)
        changed=[];bounds=[]
        for n in range(64):
            box=(n*96,0,(n+1)*96,80);a=prior.crop(box);b=new.crop(box)
            if a.tobytes()!=b.tobytes():changed.append(n)
            if n in OWNED:
                alpha=b.getchannel('A');bbox=alpha.getbbox()
                check(bbox and bbox[0]>0 and bbox[2]<96 and bbox[3]==78 and bbox[3]-bbox[1]<=77,'unclipped grounded fixed-scale attack', [f,n,bbox])
                # Literal per-row raster edges are geometry evidence, not hitboxes.
                edges=[]
                for y in range(80):
                    line=alpha.crop((0,y,96,y+1)).getbbox()
                    if line:edges.append([y,line[0],line[2]-1])
                bounds.append({'frame':n,'native_box':list(bbox),'native_sha256':sha(b.tobytes()),'opaque_row_edges_y_left_right':edges})
        check(set(changed)==OWNED,'exactly 24 owned poses change; other 40 remain byte exact',[f,changed])
        for suffix in ('_pal.bin',):
            path=f'assets/generated/fighter{f:02d}'+suffix
            check(old(path)==(ROOT/path).read_bytes(),'fixed native OBJ palette',f)
            check(sha((ROOT/path).read_bytes())==record['palette_sha256'],'palette hash binds source conversion',f)
        for suffix,ext in (('','.png'),('-large','.png'),('_tiles','.bin'),('_pal','.bin')):
            path=f'assets/generated/portrait{f:02d}'+suffix+ext
            check(old(path)==(ROOT/path).read_bytes(),'approved portrait remains exact',path)
        target=[];anchor=None;source_rows=[]
        for si,source in enumerate(record['sources']):
            path=ROOT/source['file']
            check(sha(path.read_bytes())==source['sha256']==source['raw_output_sha256'],'selected PNG is untouched built-in raw output',[f,si])
            figures,details=extract_atlas(path,pose_names=source['poses'],expected_count=source['count'])
            check(len(figures)==16,'sixteen connected whole-body source silhouettes',[f,si])
            check(all(0<m['source_box'][0]<m['source_box'][2]<Image.open(path).width and 0<m['source_box'][1]<m['source_box'][3]<Image.open(path).height for m in details),'source figures have transparent edge clearance',[f,si])
            if si==record['anchor']['source']:anchor=figures[record['anchor']['pose']]
            target.extend(n for n in source['frames'] if n is not None)
            source_rows.append({'path':source['file'],'sha256':source['sha256'],'count':len(figures),'source_boxes':[m['source_box'] for m in details]})
        check(len(target)==len(set(target))==24 and set(target)==OWNED,'disjoint source-to-native frame mapping',f)
        check(record['height_target']==HEIGHTS[f],'approved neutral physical height',f)
        result.append({'fighter':f,'changed_frames':changed,'preserved_frames':sorted(set(range(64))-OWNED),'height_target':HEIGHTS[f],'shared_conversion_scale':HEIGHTS[f]/anchor.height,'sources':source_rows,'native_bounds':bounds})
    # Check every previously committed source/reference, not merely selected inputs.
    protected=git('ls-tree','-r','--name-only',BASE,'--','assets/art','assets/references').decode().splitlines()
    bad=[p for p in protected if old(p)!=((ROOT/p).read_bytes().replace(b'\r\n',b'\n') if Path(p).suffix in ('.json','.md','.txt') else (ROOT/p).read_bytes())]
    check(not bad,'all prior source masters and provenance preserved',bad)
    generated=git('ls-tree','-r','--name-only',BASE,'--','assets/generated').decode().splitlines()
    # Binary data must not be newline-normalized.
    delta=[p for p in generated if old(p)!=((ROOT/p).read_bytes().replace(b'\r\n',b'\n') if Path(p).suffix in ('.json','.asm','.h') else (ROOT/p).read_bytes())]
    allowed={'assets/generated/character-manifest.json'}
    for f in range(12):
        allowed.add(f'assets/generated/fighter{f:02d}.png')
        for suffix in ('','b','e','f'):allowed.add(f'assets/generated/fighter{f:02d}{suffix}.bin')
    check(set(delta)==allowed,'only four owned banks and review strip per fighter plus metadata differ',delta)
    names={p.relative_to(ROOT).as_posix() for p in (ROOT/'assets/generated').iterdir() if p.is_file() and p.name!='soundbank.h'}
    check(names==set(generated) and len(names)==219,'generated inventory stays 219',len(names))
    return {'fighters':result,'old_source_files_preserved':len(protected),'generated_delta':sorted(delta),'generated_preserved':len(generated)-len(delta)}

def memory_contract(table):
    before={n:int(a,16) for a,n in __import__('re').findall(r'^([0-9a-fA-F]{6,8})\s+(\S+)\s*$',old('dist/abaqus-after-hours.sym').decode(),__import__('re').M)}
    ram={n:a for n,a in before.items() if a<0x2000 or 0x7e0000<=a<0x800000}
    moved={n:[a,table.get(n)] for n,a in ram.items() if table.get(n)!=a}
    added={n:a for n,a in table.items() if n not in before and (a<0x2000 or 0x7e0000<=a<0x800000)}
    check(not moved and not added,'all RAM symbols remain exact with no additions',[moved,added])
    for path in ('src/hardware.asm','src/trace.asm','src/game.c','src/characters.h','src/super_moves.h','src/version.h','tools/fighter_assets.py','tools/pose_revision_assets.py'):
        check((ROOT/path).read_bytes().replace(b'\r\n',b'\n')==git('show','3f51120:'+path).replace(b'\r\n',b'\n'),'shared module or hardware ABI unchanged',path)
    crossings=[]
    for n,start in table.items():
        if not n.startswith('SECTIONSTART_') or start<0x8000 or 0x7e0000<=start<0x800000:continue
        end=table.get('SECTIONEND_'+n[len('SECTIONSTART_'):])
        if end and end>start and start//0x10000!=(end-1)//0x10000:crossings.append([n,start,end])
    check(not crossings,'ROM sections remain within native banks',crossings)
    return {'existing_ram_symbols_preserved':len(ram),'new_ram_symbols':added,'bank_crossings':crossings,'fighter_stride':64,'wave_stride':16,'trace_words':123,'pose_bytes':3840,'actor_obj':30}

class AttackProbe(Probe):
    def __init__(self,e,fighter,table,base=False):
        super().__init__(e,fighter,table,base)
        self.table=table;self.films={};self.spc_failures=[];self.peak_spc=0
    def step(self,p1=(),p2=(),label='',film=False):
        s=super().step(p1,p2,label,False)
        ptrs=[C.string_at(self.e.ram+(address(self.table,n)&0x1ffff),1)[0] for n in ('spc_fread','spc_fwrite')]
        backlog=(ptrs[1]-ptrs[0])&255;self.peak_spc=max(self.peak_spc,backlog)
        if backlog>32:self.spc_failures.append([label,s['frame'],backlog])
        if film:self.films.setdefault(label,[]).append(self.e.frame.copy().convert('RGB'))
        return s

MOVES=(('jab',('y',),1,5),('cross',('x',),3,6),('light-kick',('b',),4,7),('strong-kick',('a',),5,7),('sweep',('down','a'),6,8),('uppercut',('down','x'),8,13),('special',('down','y'),7,None))
def scenario(rom,fighter,table,base=False):
    e=boot(1,fighter,fighter%3,fighter,rom=rom);p=AttackProbe(e,fighter,table,base)
    def drive(port,keys=(),other=(),label='',film=False):
        return p.step(keys if port==0 else other,other if port==0 else keys,label,film)
    def settle(label='settle'):
        for _ in range(160):
            s=trace(e)
            if not any(s[f'{key}{port}'] for port in (1,2) for key in ('action','hurt','down_state','y')) and not s['hitstop']:
                p.run(6,label=label);return
            p.step(label=label)
        raise AssertionError(('settle failed',fighter,label,trace(e)))
    def gap(target,port=0):
        settle()
        for _ in range(180):
            s=trace(e);d=abs(s['x1']-s['x2'])/16
            if abs(d-target)<2:return
            toward='right' if s[f'x{port+1}']<s[f'x{2-port}'] else 'left'
            key=toward if d>target else ('left' if toward=='right' else 'right')
            drive(port,[key])
        raise AssertionError(('spacing failed',fighter,target,d))
    try:
        p.run(12,['left'],['right'],label='separate')
        for label,keys,action,frame in MOVES:
            p.run(3,keys,keys,label,True);p.run(75,label=label,film=True)
            if not base:
                rows=[r for r in p.rows if r['label']==label]
                for port in (1,2):
                    seq=[r for r in rows if r[f'action{port}']==action]
                    check(bool(seq),'both controller ports execute intended grounded command',[fighter,port,label])
                    active=[r for r in seq if r[f'startup{port}']<=r[f'tick{port}']<r[f'active_end{port}']]
                    expect=frame
                    if expect is None:expect=15 if trace(e)[f'family{port}']==1 else 13 if trace(e)[f'family{port}']==3 else 12
                    check(active and all(r[f'anim_frame{port}']==expect for r in active),'active frame ID aligns exactly with contact window',[fighter,port,label,expect])
                    check(any(r[f'uploaded{port}']==expect for r in rows),'contact pose reaches actual actor VRAM on both ports',[fighter,port,label,expect])
                    recovery=[r for r in seq if r[f'tick{port}']>=r[f'active_end{port}']]
                    if label=='special' and expect==12:
                        # Projectile active lasts one tick. Its established
                        # release hold must survive the alternating actor DMA,
                        # then visibly retract and reclaim guard before expiry.
                        release=[r for r in recovery if r[f'tick{port}']<r[f'active_end{port}']+7 and r[f'tick{port}']+4<r[f'action_end{port}']]
                        retract=[r for r in recovery if r[f'tick{port}']>=r[f'active_end{port}']+7 and r[f'tick{port}']+4<r[f'action_end{port}']]
                        check(release and all(r[f'anim_frame{port}']==12 for r in release),'one-tick cast keeps its native release hold for alternating DMA',[fighter,port,label])
                        check(retract and all(r[f'anim_frame{port}']==43 for r in retract),'cast retracts after release hold before neutral',[fighter,port,label])
                    else:
                        check(recovery and all(r[f'anim_frame{port}']!=expect for r in recovery),'active contact drawing retracts when recovery starts',[fighter,port,label])
                    check(any(r[f'tick{port}']<r[f'startup{port}'] for r in seq),'anticipation precedes contact',[fighter,port,label])
                    check(rows[-1][f'action{port}']==0,'complete sequence returns to neutral',[fighter,port,label])
        for port in (0,1):
            # Fresh and already-held high guard must both brace after impact.
            for guarded in (False,True):
                gap(25,port);s=trace(e);defender=2-port
                back='left' if s[f'face{defender}'] else 'right'
                label=f'P{port+1}-'+('block' if guarded else 'hurt')
                if guarded:
                    for _ in range(12):drive(port,['right' if port==0 else 'left'],[back],label,True)
                for _ in range(3):drive(port,['x'],[back] if guarded else [],label,True)
                for _ in range(62):drive(port,[],[back] if guarded else [],label,True)
                if not base:
                    seq=[r for r in p.rows if r['label']==label]
                    observed={r[f'anim_frame{defender}'] for r in seq}
                    needed={40,9} if guarded else {10,41}
                    check(needed.issubset(observed),'held guard braces or hurt recoils then recovers',[fighter,port,guarded,sorted(observed)])
        # Physical pause freezes both requested animation clocks during an attack.
        settle();p.run(1,['x'],['x'],label='pause-attack');p.run(1,p2=['start'],label='pause')
        p.run(12,label='pause');paused=[r for r in p.rows if r['label']=='pause' and r['paused']]
        if not base:
            check(paused and len({(r['anim_frame1'],r['anim_frame2'],r['anim_tick1'],r['anim_tick2']) for r in paused})==1,'P2 pause freezes both attack clocks',fighter)
        p.run(1,p1=['start'],label='resume');p.run(55,label='resume')
        if not base:
            for name,failures in (('cadence',p.drops),('SDK timing',p.native_failures),('OBJ overflow',p.overflow),('native actor payload',p.bad_payload),('30-piece actor geometry',p.geometry),('SPC FIFO',p.spc_failures)):
                check(not failures,name+' stays healthy',{'fighter':fighter,'failures':failures[:4]})
            check(p.uploads[2]==0,'at most one 3840-byte actor page changes per callback',[fighter,dict(p.uploads)])
            check(e.audio_samples>0 and e.audio_peak>0,'SPC PCM remains live without device playback',[fighter,e.audio_samples,e.audio_peak])
            frozen=[(a,b) for a,b in zip(p.rows,p.rows[1:]) if a['hitstop']>1 and a['label']==b['label'] and not a['round_end'] and not b['round_end']]
            check(frozen and all((a['anim_frame1'],a['anim_frame2'],a['anim_tick1'],a['anim_tick2'])==(b['anim_frame1'],b['anim_frame2'],b['anim_tick1'],b['anim_tick2']) for a,b in frozen),'hitstop freezes both attack clocks',[fighter,len(frozen)])
        return p
    finally:e.close()

def save_clips(before,after,fighter):
    captures=[]
    # Each roster clip includes anticipation, active, retraction and neutral.
    labels=[m[0] for m in MOVES]
    labels+=['P1-hurt','P1-block']
    pairs=[]
    for label in labels:
        a=before.films[label];b=after.films[label]
        check(len(a)==len(b),'before/after capture has identical physical-input length',[fighter,label,len(a),len(b)])
        for x,y in zip(a,b):
            im=Image.new('RGB',(512,244));im.paste(x,(0,20));im.paste(y,(256,20))
            d=ImageDraw.Draw(im);d.text((5,4),'v0.23.1 '+label,fill='white');d.text((261,4),'attack-v1 '+label,fill='white');pairs.append(im)
    path=OUT/f'{fighter:02d}-complete-sequences.gif'
    ms=1000/60.098811862348406
    durations=[10*(round((i+1)*ms/10)-round(i*ms/10)) for i in range(len(pairs))]
    pairs[0].save(path,save_all=True,append_images=pairs[1:],duration=durations,loop=0,optimize=True)
    captures.append({'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path.read_bytes()),'native_callbacks':len(pairs),'playback':'10/20 ms cumulative GIF approximation to native 60.098811862348406 Hz','left':'approved v0.23.1 baseline','right':'isolated attack candidate','labels':labels})
    return captures

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--fighter',type=int);args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);(ROOT/'build').mkdir(exist_ok=True)
    report_path=ROOT/('build/combat24-attack-diagnostic.json' if args.fighter is not None else 'docs/combat-24-attack-report.json')
    baseline=ROOT/'build/v024-attack-baseline.sfc';baseline.write_bytes(old('dist/abaqus-after-hours.sfc'))
    rom=ROOT/'dist/abaqus-after-hours.sfc';manifest=json.loads((ROOT/'dist/manifest.json').read_bytes())
    table=symbols(ROOT/'dist/abaqus-after-hours.sym');started=time.monotonic()
    report={'status':'failed','scope':'isolated attack art/grounded sequencing; not final combined evidence','baseline_commit':BASE,'baseline_rom_sha256':sha(baseline.read_bytes()),'source_commit':git('rev-parse','HEAD').decode().strip(),'source_diff_sha256':sha(git('diff','HEAD','--','src','tools/test_combat24_attack.py','assets/art/attack-v1.json')),'harness_sha256':sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n')),'rom_sha256':sha(rom.read_bytes()),'rom_bytes':rom.stat().st_size,'checksum':manifest['checksum'],'host':host_contract(),'platform':platform.platform(),'command':subprocess.list2cmdline([sys.executable,*sys.argv]),'cases':[],'checks':CHECKS,'failures':{'cadence':[],'native_timing':[],'ppu_overflow':[],'actor_payload':[],'actor_geometry':[],'spc_fifo':[],'assertions':[]}}
    try:
        report['core']=core_identity()
        check(report['rom_sha256']==manifest['sha256'] and report['rom_bytes']==4194304,'exact manifest identifies native 4 MiB ROM')
        report['art']=art_contract();report['native_contract']=memory_contract(table)
        for fighter in ([args.fighter] if args.fighter is not None else range(12)):
            before=scenario(baseline,fighter,table,True);after=scenario(rom,fighter,table)
            check(before.game_hash.hexdigest()==after.game_hash.hexdigest(),'identical controller replay preserves all non-animation Fighter bytes and trace',[fighter,before.game_hash.hexdigest(),after.game_hash.hexdigest()])
            captures=save_clips(before,after,fighter)
            report['cases'].append({'fighter':fighter,'ports':[1,2],'callbacks':len(after.rows),'non_animation_sha256':after.game_hash.hexdigest(),'peak_spc_backlog':after.peak_spc,'native_lag_increments':after.lag_increments,'uploads_per_callback':dict(after.uploads),'uploaded_frame_ids':[sorted(x) for x in after.frames],'captures':captures})
            print(json.dumps({'fighter':fighter,'callbacks':len(after.rows),'checks':len(CHECKS)}),flush=True)
        report['status']='passed'
    except Exception as error:
        report['failures']['assertions'].append(repr(error));raise
    finally:
        report['elapsed_seconds']=round(time.monotonic()-started,3);report['check_count']=len(CHECKS)
        write(report_path,report)
        print(json.dumps({'status':report['status'],'checks':len(CHECKS),'rom_sha256':report['rom_sha256'],'report':str(report_path)}),flush=True)
if __name__=='__main__':main()
