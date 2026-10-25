"""Controller-only arena-life proof on both pinned native cores.

No memory writes/save states/GUI/audio device. Feature-owned reports only.
Checks real VRAM, PPU pixels, all OBJ entries, SDK cadence and resident SPC.
Snes9x also replays the exact controllers against the unchanged integration
base, comparing every unmasked gameplay trace word and full Fighter/Wave data.
"""
from __future__ import annotations
import argparse
import ctypes as C
import hashlib
import io
import json
from pathlib import Path
import subprocess
import struct
import sys
import tarfile
import time

from PIL import Image, ImageChops
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from emulator import Emulator
import test_compatibility as compat
from test_classic_menu import AccuracyMenu
from test_training import core_identity
from test_stages import scanline_budget
from v024_contracts import symbols
from arena_life29_assets import render, colors

BASE='29fee8343ceaa47c9c74921494142c2c02a1198f'
CHECKS={}
ACTOR_FRAMES={}


def sha(raw):return hashlib.sha256(raw).hexdigest()
def require(ok,label,detail=None):
    row=CHECKS.setdefault(label,{'check':label,'executions':0,'passed':True});row['executions']+=1
    if not ok:
        row.update(passed=False,detail=detail)
        raise AssertionError((label,detail))


def snapshot():
    return {p.relative_to(ROOT).as_posix():sha(p.read_bytes())
            for directory in ('src','tools','assets/art/stages/arena-life-v029')
            for p in sorted((ROOT/directory).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def preservation(syms):
    allowed={'assets/generated/assets.h','assets/generated/data.asm','assets/generated/stage-depth.json'}
    allowed|={f'assets/generated/stage{s}{suffix}' for s in range(3) for suffix in ('.png','_tiles.bin','_map.bin')}
    changed=[];total=0;old_files={}
    raw=subprocess.check_output(['git','archive',BASE,'assets/generated','src/hardware.asm','src/trace.asm'],cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        for item in archive:
            if not item.isfile():continue
            before=archive.extractfile(item).read();after=(ROOT/item.name).read_bytes();old_files[item.name]=before
            if Path(item.name).suffix in ('.asm','.h','.json'):before=before.replace(b'\r\n',b'\n');after=after.replace(b'\r\n',b'\n')
            if before!=after:changed.append(item.name)
            total+=item.name.startswith('assets/generated/')
    require(set(changed)<=allowed,'Only declared stage map/pool/preview and declarations change',changed)
    prior=symbols(subprocess.check_output(['git','show',BASE+':dist/abaqus-after-hours.sym'],cwd=ROOT).decode())
    ram=lambda a:a<0x2000 or 0x7e0000<=a<0x800000
    old_ram={n:a for n,a in prior.items() if ram(a)}
    moved={n:[a,syms.get(n)] for n,a in old_ram.items() if syms.get(n)!=a}
    added={n:a for n,a in syms.items() if ram(a) and n not in prior}
    # The integration base committed the six reservation declarations but its
    # tracked cartridge/symbols still identify approved v0.28. The parent's
    # initialized 176-byte reservation advances only two allocation markers.
    expected={'v29DefenseState':16,'v29BonusState':64,'v29AutoState':8,'v29RandomState':8,'v29AudioState':32,'v29ArenaState':48}
    cursor=prior['SECTIONEND_globram.data'];reserved={}
    for name,count in expected.items():reserved[name]=cursor;cursor+=count
    markers={'SECTIONEND_globram.data','RAM_USAGE_SLOT_3_BANK_127_END'}
    require(set(moved)==markers and all(b==a+176 for a,b in moved.values()) and added==reserved,
            'Every old variable address exact; only parent six-array reservation and two size markers append',[moved,added])
    records=json.loads((ROOT/'assets/generated/arena-life29.json').read_bytes())
    for stage in records['stages']:
        sid=stage['id'];prefix=f'assets/generated/stage{sid}'
        gfx=(ROOT/(prefix+'_tiles.bin')).read_bytes();old_gfx=old_files[prefix+'_tiles.bin']
        require(gfx[:len(old_gfx)]==old_gfx,'All original scenery and floor tile bytes exact',sid)
        old_map=struct.unpack('<2048H',old_files[prefix+'_map.bin']);new_map=struct.unpack('<2048H',(ROOT/(prefix+'_map.bin')).read_bytes())
        dynamic={row['offset_words'] for row in stage['animated_cells']}
        require(len(dynamic)==48 and all(a==b for i,(a,b) in enumerate(zip(old_map,new_map)) if i not in dynamic),
                'Only 48 declared above-floor cells change',sid)
        require(all(row['world_rect'][1]+8<=stage['floor_seam_y'] for row in stage['animated_cells']),
                'All floor map cells remain exact',sid)
        require(len(gfx)==28160 and records['tile_vram_word']==0x3400 and records['tile_vram_end_word']==0x36ff,
                '48-tile pool ends before map and below word 37FF',sid)
        require((ROOT/(prefix+'_pal.bin')).read_bytes()==old_files[prefix+'_pal.bin'],'All six stage palettes exact',sid)
    sections=[]
    for name,start in syms.items():
        if not name.startswith('SECTIONSTART_') or ram(start):continue
        end=syms.get(name.replace('SECTIONSTART_','SECTIONEND_'))
        if end is not None:
            require(0<end-start<=32768 and start>>16==(end-1)>>16,'Every linked ROM section fits one LoROM bank',[name,end-start])
            sections.append(end-start)
    return {'base':BASE,'prior_ram_labels':len(old_ram),'changed_old_outputs':changed,'preserved_old_outputs':total-len(changed),
            'new_outputs':['arena-life29.json']+[f'arena_life29_stage{s}.bin' for s in range(3)],
            'largest_rom_section_bytes':max(sections),'section_count':len(sections),'state_bytes':48,
            'parent_reservation_symbols':added,'feature_added_mutable_symbols':{},'hardware_and_trace_exact':True}


class Rig:
    def __init__(self,core,stage,fighter,syms,report,rom=None,monitor=True):
        self.core=core;self.stage=stage;self.fighter=fighter;self.syms=syms;self.report=report;self.monitor=monitor
        if core=='accuracy':
            compat.ROM_PATH=Path(rom or ROOT/'dist/abaqus-after-hours.sfc');self.e=AccuracyMenu()
        else:self.e=Emulator(rom)
        self.record=[];self.frames=[];self.health={'callbacks':0,'ambient_uploads':0,'actor_uploads':0,
                         'peak_spc':0,'peak_obj_sprites':0,'peak_obj_tiles':0,'frozen_hitstop_callbacks':0,'completed_phases':[]}
        self.meta=json.loads((ROOT/'assets/generated/arena-life29.json').read_bytes())
        self.sources=[(ROOT/'assets/generated'/s['phase_source']).read_bytes() for s in self.meta['stages']]
        self.capture_dir=ROOT/'docs/screenshots/arena-life29'/core;self.capture_dir.mkdir(parents=True,exist_ok=True)

    def raw(self,name,size=1):return C.string_at(self.e.ram+(self.syms[name]&0x1ffff),size)
    def read(self,name,size=1):return int.from_bytes(self.raw(name,size),'little')
    def state(self):return self.e.state()
    def life(self):return self.raw('v29ArenaState',48)
    def vram(self):return C.string_at(self.e.core.retro_get_memory_data(3),65536)
    def trace(self):return C.string_at(self.e.ram+0x1ff00,246)
    def game(self):
        # No masking of trace words 0..113, full actors, waves or RNG. Include
        # all private super state and presentation/combat clocks explicitly.
        data=self.trace()[:228]+self.raw('fighters',128)+self.raw('waves',32)
        for name,size in [('randomseed',2),('fightClock',2),('cpuTick',1),('secondTick',1),('winner',1),
                          ('shake',1),('fxLife',1),('fxX',1),('fxY',1),('fxType',1)]:data+=self.raw(name,size)
        for name in ('superActive','superRequest','superPhase','superNext','superContactEnd','superWaveDamage','superWaveReach'):
            data+=self.raw(name,2)
        return sha(data)

    def tick(self,p1=(),p2=(),watch=True,record=True):
        old=self.state();active=self.read('screen')==3 and old['screen']==3
        if active and watch and self.monitor:
            counters=[self.read(n,2) for n in ('frame','snes_vblank_count','lag_frame_counter')]
            life=self.life();vram=self.vram();samples=self.e.audio_samples
            before_frozen=(self.read('hitstop') and not self.read('roundEnd')) or self.read('paused') or self.raw('stageDepthTable',10)[9] or self.read('intro')
        self.e.run(1,p1,p2);s=self.state()
        if active and watch and self.monitor and self.read('screen')==3 and s['screen']==3:
            self.health['callbacks']+=1
            delta=[(self.read(n,2)-v)&65535 for n,v in zip(('frame','snes_vblank_count','lag_frame_counter'),counters)]
            require(delta==[1,1,0] and (s['frame']-old['frame'])&65535==1,'Strict native frame/vblank cadence, zero SDK lag',
                    {'core':self.core,'stage':self.stage,'before':old,'after':s,'delta':delta,'keys':[p1,p2]})
            require(not (int.from_bytes(self.trace()[228:230],'little')&0xc0),'STAT77 no OBJ overflow')
            now=self.vram();current=self.life()
            if current[3] not in self.health['completed_phases']:self.health['completed_phases'].append(current[3])
            require(now[:0x6800]==vram[:0x6800] and now[0x6e00:0x8000]==vram[0x6e00:0x8000],
                    'Original tile prefix and complete wide map immutable during play')
            actors=sum(now[a:b]!=vram[a:b] for a,b in ((0xc000,0xd400),(0xd400,0xe800)))
            require(actors<=1,'At most one actor page / 3840-byte upload per blank',actors);self.health['actor_uploads']+=actors
            for side,(a,b) in enumerate(((0xc000,0xd400),(0xd400,0xe800))):
                if now[a:b]==vram[a:b]:continue
                fighter=s['fighter_id'+str(side+1)]
                if fighter not in ACTOR_FRAMES:
                    data=b''.join((ROOT/f'assets/generated/fighter{fighter:02d}{suffix}.bin').read_bytes() for suffix in ('','b','c','d','e','f','g','h'))
                    ACTOR_FRAMES[fighter]={data[i*3840:(i+1)*3840] for i in range(64)}
                payload=b''.join(now[a+row*512:a+row*512+384] for row in range(10))
                require(payload in ACTOR_FRAMES[fighter],'Every changed actor page is a complete exact approved 3840-byte pose',[fighter,side])
            changed=(current[14]-life[14])&255
            require(changed<=1,'At most one 256-byte arena transfer per blank',changed)
            if changed:
                self.health['ambient_uploads']+=1;chunk=current[19];phase=current[20]
                pool=now[0x6800:0x6e00];oldpool=vram[0x6800:0x6e00];a=chunk*256;b=a+256
                source=self.sources[current[0]-1][phase*1536+a:phase*1536+b]
                require(pool[a:b]==source and pool[:a]==oldpool[:a] and pool[b:]==oldpool[b:],
                        'Completed telemetry identifies exact actual 256-byte source/destination',list(current[:20]))
                require(actors==0 and now[0xb000:0xb800]==vram[0xb000:0xb800],
                        'Arena DMA yields to actor and interface DMA')
            else:require(now[0x6800:0x6e00]==vram[0x6800:0x6e00],'Pool cannot change without completed DMA telemetry')
            # Stable frozen samples only; resume is allowed to start live work.
            after_frozen=(self.read('hitstop') and not self.read('roundEnd')) or self.read('paused') or self.raw('stageDepthTable',10)[9] or self.read('intro')
            if before_frozen and after_frozen:
                require(current[1]==life[1] and not changed,'Intro/pause/hitstop/motion-off freeze clock and transfers')
                if self.read('hitstop'):self.health['frozen_hitstop_callbacks']+=1
            budget=scanline_budget(self.raw('oamMemory',544))
            for name,field in (('peak_obj_sprites','max_sprites'),('peak_obj_tiles','max_tiles')):
                self.health[name]=max(self.health[name],budget[field])
            require(budget['max_sprites']<=32 and budget['max_tiles']<=34,'All 128 OAM entries stay within scanline budgets',budget)
            backlog=(self.read('spc_fwrite')-self.read('spc_fread'))&255;self.health['peak_spc']=max(self.health['peak_spc'],backlog)
            require(backlog<=6 and self.e.audio_samples>samples,'SPC FIFO <=6 and fresh captured PCM each callback',backlog)
        if record:self.record.append({'p1':list(p1),'p2':list(p2),'game':self.game()})
        return s

    def run(self,n,p1=(),p2=(),**kw):
        for _ in range(n):s=self.tick(p1,p2,**kw)
        return s
    def pulse(self,key,port=0,**kw):
        self.run(3,[key] if port==0 else (),[key] if port==1 else (),**kw);self.run(23,**kw)
    def boot(self):
        self.run(120,watch=False,record=False)
        self.pulse('down',watch=False,record=False);self.pulse('a',watch=False,record=False)
        for _ in range(self.fighter):self.pulse('right',watch=False,record=False)
        self.pulse('a',watch=False,record=False)
        for _ in range((self.fighter-self.state()['selected2'])%12):self.pulse('right',1,watch=False,record=False)
        self.pulse('a',1,watch=False,record=False)
        for _ in range(self.stage):self.pulse('down',watch=False,record=False)
        self.pulse('a',watch=False,record=False)
        for _ in range(200):
            if self.state()['screen']==3:break
            self.tick(watch=False,record=False)
        require(self.state()['screen']==3 and self.state()['arena']==self.stage,'Controller menus enter selected native arena',self.state())
        for _ in range(160):
            if not self.state()['intro']:break
            self.tick(record=False)
        self.run(6,record=False)
        self.initial_game=self.game()

    def save(self,label):
        path=self.capture_dir/f'stage{self.stage}-{label}.png';self.e.frame.save(path)
        self.report['media'].append({'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path.read_bytes())})

    def pixels(self):
        vram=self.vram();tilemap=struct.unpack('<2048H',vram[0x7000:0x8000])
        palette=colors((ROOT/f'assets/generated/stage{self.stage}_pal.bin').read_bytes())
        expected=render(vram[:0x7000],tilemap,palette)
        camera=int.from_bytes(self.raw('stageDepthFar',2),'little',signed=True)
        actual=self.e.frame
        error=max(hi for lo,hi in ImageChops.difference(actual.crop((0,208,256,224)),expected.crop((16+camera,208,272+camera,224))).getextrema())
        require(error<=8,'Actual detailed floor pixels match static native oracle',{'stage':self.stage,'error':error})
        # Require real visible person pixels that distinguish conversation B
        # from A, excluding any pixel occluded by fighters or UI.
        source=self.sources[self.stage];phase0=vram[:0x6800]+source[:1536]+vram[0x6e00:0x7000]
        still=render(phase0,tilemap,palette);matches=0;changed=0
        for x,y,w,h in self.meta['stages'][self.stage]['rectangles_world'][:4]:
            for yy in range(y,y+h):
                for xx in range(x,x+w):
                    sx=xx-16-camera
                    if not 0<=sx<256:continue
                    color=expected.getpixel((xx,yy));prior=still.getpixel((xx,yy))
                    if color!=prior:
                        changed+=1
                        if max(abs(a-b) for a,b in zip(actual.getpixel((sx,yy)),color))<=8:matches+=1
        require(matches>=8,'Actual PPU shows changed spectator pixels from the uploaded animation',{'stage':self.stage,'changed':changed,'visible_matching':matches})
        return {'floor_max_channel_error':error,'spectator_changed_pixels':changed,'visible_matching':matches}

    def close_gap(self,distance=27):
        for _ in range(180):
            s=self.state()
            if abs(s['x1']-s['x2'])<=distance*16:return
            self.tick(['right'] if s['x1']<s['x2'] else ['left'],['left'] if s['x1']<s['x2'] else ['right'])
        raise AssertionError('Controller approach failed')

    def phase(self,wanted,limit=180):
        for _ in range(limit):
            if self.life()[3]==wanted and self.life()[4]==6:
                self.run(2);return
            self.tick()
        raise AssertionError(('Arena phase did not complete',wanted,list(self.life()),self.state()))


def arena_case(r):
    r.boot();r.save('initial');r.phase(1);ambient=r.pixels();r.save('conversation')
    clip=[]
    for tick in range(140):
        r.tick()
        if tick%3==0:clip.append(r.e.frame.copy())
    # Both physical ports own ordinary pause/resume. Guide R is the approved
    # background-motion preference; no test-only control or WRAM writes.
    r.pulse('start',1);require(r.read('paused')==1,'P2 Start pauses arena')
    frozen=(r.life()[1],r.vram()[0x6800:0x6e00]);r.run(40,['left'],['right'])
    require(frozen==(r.life()[1],r.vram()[0x6800:0x6e00]),'Stable pause freezes full tile pool')
    r.pulse('select');r.pulse('r');require(r.raw('stageDepthTable',10)[9]==1,'Controller guide turns background motion off')
    r.pulse('start');frozen=(r.life()[1],r.vram()[0x6800:0x6e00]);r.run(90,['left'],['right'])
    require(frozen==(r.life()[1],r.vram()[0x6800:0x6e00]),'Motion-off live fight freezes full tile pool')
    r.pulse('start');r.pulse('select');r.pulse('r');r.pulse('start')
    require(r.raw('stageDepthTable',10)[9]==0 and not r.read('paused'),'Both ports return to motion-enabled combat')
    r.close_gap();hp=r.state()['hp2'];r.run(3,['x'])
    hit=None
    for _ in range(85):
        s=r.tick()
        if s['hp2']<hp:hit=s;break
    require(hit is not None and hp-hit['hp2']>=8 and hit['hitstop']>0,'Controller heavy hit earns real damage and hitstop',hit)
    r.phase(2);r.save('impact');r.run(110)
    # Passive meter is earned at native cadence; mirrored two-super activation
    # covers fast volleys, rises and ordinary volleys across the three stages.
    for _ in range(1400):
        s=r.state()
        if s['energy1']==s['energy2']==96 and not s['hurt1'] and not s['hurt2']:break
        r.tick()
    else:raise AssertionError('Passive full meter not reached')
    r.run(100,['left'],['right']);r.run(3)
    r.run(3,['y','b'],['y','b'])
    require(r.raw('superActive',2)==b'\1\1' and r.state()['energy1']==r.state()['energy2']==0,
            'Both physical pads start paid supers simultaneously')
    super_seen=False
    for tick in range(210):
        r.tick()
        if r.life()[3]==4:
            if not super_seen:r.save('super')
            super_seen=True
        if tick%3==0:clip.append(r.e.frame.copy())
    require(super_seen and r.life()[17]>0,'Super excitement reaches actual VRAM after yielding to combat')
    # Earn a KO, retaining ordinary recoil/recovery. Never inject HP or timer.
    for attempt in range(18):
        if r.read('roundEnd'):break
        r.close_gap();r.run(3,['x']);r.run(80)
        if not r.state()['hp2']:break
    require(r.state()['hp2']==0,'Repeated controller heavy contacts earn native KO',r.state())
    ko_seen=False;intro_seen=False;ko_history=[]
    for tick in range(330):
        r.tick()
        if tick%8==0:ko_history.append({'tick':tick,'round_end':r.read('roundEnd'),'intro':r.read('intro'),'life':list(r.life()[:21])})
        if r.life()[3]==5 and r.read('roundEnd'):
            if not ko_seen:r.save('ko')
            ko_seen=True
        if tick%3==0:clip.append(r.e.frame.copy())
        if r.state()['intro']:
            intro_seen=True
            if tick>180:break
    require(ko_seen and r.life()[18]>0,'KO celebration publishes within safe round-end scheduling',ko_history)
    require(intro_seen,'Native round progression retains next-round intro')
    while r.state()['intro']:r.tick()
    r.run(100);require(r.life()[3] in (0,1) and r.life()[11]==0,'Next round returns to quiet conversation')
    require(set(r.health['completed_phases'])==set(range(6)),'All six authored phases complete in actual native VRAM',r.health['completed_phases'])
    require(0<r.e.audio_peak<32767 and r.e.audio_energy>0,'Captured native PCM stays active and unclipped',r.e.audio_peak)
    path=r.capture_dir/f'stage{r.stage}-life-events.gif'
    clip[0].save(path,save_all=True,append_images=clip[1:],duration=50,loop=0,disposal=2)
    r.report['media'].append({'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path.read_bytes()),'scope':'actual PPU; samples every three callbacks; GIF timing approximate'})
    # Record the deterministic combat replay before the scene-changing handoff.
    replay={'initial_game':r.initial_game,'inputs':list(r.record)}
    r.pulse('start');r.pulse('b',watch=False)
    require(r.read('screen')==1 and r.life()[0]==0,'Pause Back hands arena ownership to roster')
    r.pulse('a',watch=False);r.pulse('a',1,watch=False)
    target=(r.stage+1)%3
    for _ in range((target-r.read('arena'))%3):r.pulse('down',watch=False)
    r.pulse('a',watch=False)
    for _ in range(200):
        if r.read('screen')==3 and r.state()['screen']==3:break
        r.tick(watch=False)
    require(r.read('arena')==target and r.life()[0]==target+1,'New arena handoff loads only its own animation state')
    require(r.vram()[0x6800:0x6e00]==r.sources[target][:1536],'New arena begins with exact phase-zero bytes')
    return {'stage':r.stage,'fighter_mirror':r.fighter,'ambient_pixels':ambient,'health':r.health,'replay':replay}


def replay_base(case,syms,report):
    path=ROOT/'build/arena-life29-baseline/abaqus-after-hours.sfc'
    prior=symbols((path.with_suffix('.sym')).read_text())
    r=Rig('snes9x',case['stage'],case['fighter_mirror'],prior,report,rom=path,monitor=False)
    try:
        r.boot();require(r.initial_game==case['replay']['initial_game'],'Baseline starts at identical unmasked gameplay state',case['stage'])
        for i,row in enumerate(case['replay']['inputs']):
            r.tick(row['p1'],row['p2'],record=False)
            require(r.game()==row['game'],'Unmasked gameplay trace/Fighter64/Wave16/RNG/private-super replay equals baseline',
                    {'stage':case['stage'],'callback':i,'before_sha':r.game(),'candidate_sha':row['game'],'keys':[row['p1'],row['p2']]})
        return {'stage':case['stage'],'callbacks':len(case['replay']['inputs']),'all_unmasked_equal':True,'baseline_sha256':sha(path.read_bytes())}
    finally:r.e.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core',choices=('snes9x','accuracy'),required=True)
    parser.add_argument('--stages',default='0,1,2')
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--skip-replay',action='store_true')
    args=parser.parse_args();started=time.monotonic();sources=snapshot();syms=symbols((ROOT/'dist/abaqus-after-hours.sym').read_text())
    stages=list(map(int,args.stages.split(',')))
    require(stages==[0,1,2] or args.report.resolve().is_relative_to(ROOT/'build'),'Partial coverage stays diagnostic')
    manifest=json.loads((ROOT/'dist/manifest.json').read_bytes())
    report={'status':'failed','core':args.core,'rom':manifest,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'sources':sources,'memory_writes':False,'save_states':False,'audio_device':False,'media':[],'cases':[],'baseline_replays':[]}
    try:
        require(sha((ROOT/'dist/abaqus-after-hours.sfc').read_bytes())==manifest['sha256'],'Exact tested ROM identity')
        report['preservation']=preservation(syms)
        report['core_identity']=core_identity() if args.core=='snes9x' else compat.verify_manifest_and_pinned_core()
        report['metadata']=json.loads((ROOT/'assets/generated/arena-life29.json').read_bytes())
        for stage in stages:
            r=Rig(args.core,stage,[8,10,0][stage],syms,report)
            try:case=arena_case(r)
            finally:r.e.close()
            if args.core=='snes9x' and not args.skip_replay:report['baseline_replays'].append(replay_base(case,syms,report))
            case['input_callbacks']=len(case.pop('replay')['inputs']);report['cases'].append(case)
            print(json.dumps({'core':args.core,'stage':stage,'status':'passed','health':r.health}),flush=True)
        require(snapshot()==sources,'Producer/harness/dependency bytes frozen during proof')
        report['status']='passed'
    except BaseException as error:report['error']=repr(error);raise
    finally:
        report.update(checks=list(CHECKS.values()),passed=sum(row['executions'] for row in CHECKS.values() if row['passed']),
                      elapsed_seconds=round(time.monotonic()-started,3))
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
        print(json.dumps({k:report[k] for k in ('status','core','passed','elapsed_seconds')}),flush=True)


if __name__=='__main__':main()
