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
BASE_ROM_SHA='09eaa47ddc12d419e259f1330eb225f1e56f75d42efdd2faf5c27063f8f2357c'
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


def file_hashes(directory):
    return {p.relative_to(ROOT).as_posix():sha(p.read_bytes())
            for p in sorted(directory.iterdir()) if p.is_file()}


def baseline_identity(rom, symbol_path):
    """Bind the unchanged original replay to committed bytes before booting.

    A combined-rule mismatch remains a failure. An animation-only current
    source counterfactual requires a separately reviewed parent preparation;
    this harness does not silently replace or normalize the original baseline.
    """
    result={'source_commit':BASE,'rom_path':str(rom),'symbols_path':str(symbol_path)}
    for path, name in ((rom,'abaqus-after-hours.sfc'),(symbol_path,'abaqus-after-hours.sym')):
        require(path.is_file(),'Original baseline artifact exists before native proof',str(path))
        original=subprocess.check_output(['git','show',BASE+':dist/'+name],cwd=ROOT)
        raw=path.read_bytes()
        require(raw==original,'Replay baseline artifact equals exact committed original bytes',str(path))
        result['rom_sha256' if name.endswith('.sfc') else 'symbols_sha256']=sha(raw)
    require(result['rom_sha256']==BASE_ROM_SHA,'Replay baseline identifies approved v0.28 ROM',result)
    return result


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
    def __init__(self,core,stage,fighter,syms,report,rom=None,monitor=True,captures=None):
        self.core=core;self.stage=stage;self.fighter=fighter;self.syms=syms;self.report=report;self.monitor=monitor
        if core=='accuracy':
            compat.ROM_PATH=Path(rom or ROOT/'dist/abaqus-after-hours.sfc');self.e=AccuracyMenu()
        else:self.e=Emulator(rom)
        self.record=[];self.frames=[];self.health={'callbacks':0,'ambient_uploads':0,'actor_uploads':0,
                         'peak_spc':0,'peak_obj_sprites':0,'peak_obj_tiles':0,'frozen_hitstop_callbacks':0,'completed_phases':[],
                         'trace':{key:0 for key in ('callbacks','idle','partial_pool','queued_zero','pause','intro','intro_abort','mixed_pool','ko','no_upload','completed_upload','last_chunk')}}
        self.pool_phases=[0]*6;self.pool_stage=stage+1
        self.last_trace_life=None;self.last_trace_pool=None
        self.meta=json.loads((ROOT/'assets/generated/arena-life29.json').read_bytes())
        self.sources=[(ROOT/'assets/generated'/s['phase_source']).read_bytes() for s in self.meta['stages']]
        self.capture_dir=(Path(captures) if captures is not None else ROOT/'docs/screenshots/arena-life29')/core
        self.capture_dir.mkdir(parents=True,exist_ok=True)

    def raw(self,name,size=1):return C.string_at(self.e.ram+(self.syms[name]&0x1ffff),size)
    def read(self,name,size=1):return int.from_bytes(self.raw(name,size),'little')
    def state(self):return self.e.state()
    def life(self):return self.raw('v29ArenaState',48)
    def vram(self):return C.string_at(self.e.core.retro_get_memory_data(3),65536)
    def trace(self):return C.string_at(self.e.ram+0x1ff00,246)
    def verify_trace(self):
        current=self.life();actual=list(struct.unpack('<4H',self.trace()[230:238]))
        expected=[current[3],current[1],current[5] if current[4]<6 else 255,current[4] if current[4]<6 else 0]
        require(actual==expected,'Every callback TRACE115..118 equals exact arena reservation state',
                {'core':self.core,'stage':self.stage,'frame':self.state()['frame'],'trace':actual,'expected':expected,'state':list(current[:21])})
        require(current[3] in (*range(6),255) and current[4]<=6 and current[5]<6,
                'TRACE publication uses only legal phase/progress and explicit mixed marker',list(current[:21]))
        counts=self.health['trace'];counts['callbacks']+=1
        counts['idle']+=int(actual[2]==255)
        counts['partial_pool']+=int(actual[2]!=255 and 0<actual[3]<6)
        counts['queued_zero']+=int(actual[2]!=255 and actual[3]==0)
        counts['pause']+=int(bool(self.read('paused')))
        counts['intro']+=int(bool(self.read('intro')))
        counts['mixed_pool']+=int(actual[0]==255)
        counts['ko']+=int(bool(self.read('roundEnd')) and (not self.state()['hp1'] or not self.state()['hp2']))
        pool=C.string_at(self.e.core.retro_get_memory_data(3)+0x6800,1536)
        previous=self.last_trace_life
        if current[3]==255 and previous is not None and previous[3]!=255:
            require(previous[4]<6 and current[4]==6 and self.read('intro')>0 and current[13]!=previous[13],
                    'Mixed TRACE marker is earned by aborting an actual partial pool at new-round intro',[list(previous[:21]),list(current[:21])])
            require(pool==self.last_trace_pool and current[14]==previous[14],
                    'Intro abort publishes mixed state without inventing a completed DMA')
            counts['intro_abort']+=1
        self.last_trace_life=current;self.last_trace_pool=pool
        return actual
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
        actual_trace=None
        if self.monitor and self.read('screen')==3 and s['screen']==3:actual_trace=self.verify_trace()
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
                self.health['trace']['completed_upload']+=1
                self.health['trace']['last_chunk']+=int(chunk==5)
                pool=now[0x6800:0x6e00];oldpool=vram[0x6800:0x6e00];a=chunk*256;b=a+256
                source=self.sources[current[0]-1][phase*1536+a:phase*1536+b]
                require(pool[a:b]==source and pool[:a]==oldpool[:a] and pool[b:]==oldpool[b:],
                        'Completed telemetry identifies exact actual 256-byte source/destination',list(current[:20]))
                require(actors==0 and now[0xb000:0xb800]==vram[0xb000:0xb800],
                        'Arena DMA yields to actor and interface DMA')
                self.pool_phases[chunk]=phase
            else:
                self.health['trace']['no_upload']+=1
                require(now[0x6800:0x6e00]==vram[0x6800:0x6e00],'Pool cannot change without completed DMA telemetry')
            require(current[0]==self.pool_stage,'Live arena keeps completed-chunk oracle ownership',current[0])
            source=self.sources[current[0]-1]
            expected_pool=b''.join(source[phase*1536+chunk*256:phase*1536+(chunk+1)*256] for chunk,phase in enumerate(self.pool_phases))
            require(now[0x6800:0x6e00]==expected_pool,'Full pool matches independently retained completed-DMA history, including mixed intro abort')
            if actual_trace[0]!=255:
                trace_pool=b''.join(source[(actual_trace[2] if chunk<actual_trace[3] else actual_trace[0])*1536+chunk*256:
                                          (actual_trace[2] if chunk<actual_trace[3] else actual_trace[0])*1536+(chunk+1)*256] for chunk in range(6))
                require(now[0x6800:0x6e00]==trace_pool,'TRACE completed/pending/progress directly reconstruct every actual pool byte')
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


def intro_abort_case(r):
    """Earn P2's first win, freeze a partial KO phase, and let round 3 start.

    Motion OFF keeps the partial pool intact while the real round-end clock
    expires. The new-round intro must explicitly publish 255/clock/255/0;
    the completed-DMA history continues to prove every mixed VRAM byte.
    """
    for attempt in range(18):
        if not r.state()['hp1']:break
        r.close_gap();r.run(3,p2=['x'])
        for _ in range(80):
            if not r.state()['hp1']:break
            r.tick()
    require(r.state()['hp1']==0 and r.state()['wins1']==r.state()['wins2']==1,
            'Controller P2 KO earns a third-round intro without ending the match',r.state())
    for _ in range(160):
        life=r.life()
        if life[5]==5 and 0<life[4]<6:break
        r.tick()
    else:raise AssertionError(('KO partial pool not reached for intro-abort fixture',list(r.life())))
    r.run(3,['start']);r.run(10)
    require(r.read('paused')==1 and 0<r.life()[4]<6,'P1 pauses an actual partially uploaded KO pool',list(r.life()[:21]))
    r.pulse('select');r.pulse('r')
    require(r.raw('stageDepthTable',10)[9]==1,'Controller motion-off retains the partial pool through round end')
    before=list(struct.unpack('<4H',r.trace()[230:238]));pool=r.vram()[0x6800:0x6e00];serial=r.life()[14]
    r.pulse('start')
    for _ in range(220):
        if r.read('intro'):break
        r.tick()
    require(r.read('intro')>0 and r.life()[3]==255 and r.life()[4]==6,'New-round intro aborts a real partial pool with explicit mixed marker',list(r.life()[:21]))
    after=list(struct.unpack('<4H',r.trace()[230:238]))
    require(after==[255,before[1],255,0] and pool==r.vram()[0x6800:0x6e00] and r.life()[14]==serial,
            'Aborted intro TRACE remains exact without advancing clock or completed DMA',[before,after])
    r.save('intro-abort')
    while r.read('intro'):r.tick()
    r.run(12)
    require(list(struct.unpack('<4H',r.trace()[230:238]))==after,'No-upload motion-off samples retain exact mixed TRACE after intro')
    r.pulse('start');r.pulse('select');r.pulse('r');r.pulse('start');r.run(100)
    require(r.raw('stageDepthTable',10)[9]==0 and r.life()[3] in (0,1) and r.life()[11]==0,
            'Motion-on resumes and converges a fresh complete phase after intro abort',list(r.life()[:21]))
    return {'partial_trace':before,'aborted_trace':after,'mixed_pool_sha256':sha(pool),
            'resumed_trace':list(struct.unpack('<4H',r.trace()[230:238])),'wins':[r.state()['wins1'],r.state()['wins2']]}


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
    aborted=intro_abort_case(r) if r.stage==0 else None
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
    return {'stage':r.stage,'fighter_mirror':r.fighter,'ambient_pixels':ambient,'health':r.health,'intro_abort':aborted,'replay':replay}


def replay_base(case,syms,report):
    identity=report['baseline_inputs'];path=Path(identity['rom_path']);symbol_path=Path(identity['symbols_path'])
    require(sha(path.read_bytes())==identity['rom_sha256'] and sha(symbol_path.read_bytes())==identity['symbols_sha256'],
            'Original replay ROM/symbol bytes remain frozen before each stage')
    prior=symbols(symbol_path.read_text())
    r=Rig('snes9x',case['stage'],case['fighter_mirror'],prior,report,rom=path,monitor=False,captures=report['capture_root'])
    try:
        r.boot();require(r.initial_game==case['replay']['initial_game'],'Baseline starts at identical unmasked gameplay state',case['stage'])
        for i,row in enumerate(case['replay']['inputs']):
            r.tick(row['p1'],row['p2'],record=False)
            require(r.game()==row['game'],'Unmasked gameplay trace/Fighter64/Wave16/RNG/private-super replay equals baseline',
                    {'stage':case['stage'],'callback':i,'before_sha':r.game(),'candidate_sha':row['game'],'keys':[row['p1'],row['p2']]})
        return {'stage':case['stage'],'callbacks':len(case['replay']['inputs']),'all_unmasked_equal':True,
                'baseline_sha256':identity['rom_sha256'],'baseline_symbols_sha256':identity['symbols_sha256']}
    finally:r.e.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core',choices=('snes9x','accuracy'),required=True)
    parser.add_argument('--stages',default='0,1,2')
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--captures',type=Path,help='Capture base; each core owns its own subdirectory')
    parser.add_argument('--baseline-rom',type=Path,default=ROOT/'build/arena-life29-baseline/abaqus-after-hours.sfc')
    parser.add_argument('--baseline-symbols',type=Path,default=ROOT/'build/arena-life29-baseline/abaqus-after-hours.sym')
    parser.add_argument('--skip-replay',action='store_true')
    parser.add_argument('--combined',action='store_true',help='Bind preservation to the parent six-topic policy')
    args=parser.parse_args();started=time.monotonic();sources=snapshot();syms=symbols((ROOT/'dist/abaqus-after-hours.sym').read_text())
    stages=list(map(int,args.stages.split(',')))
    args.report=args.report.resolve()
    captures=(args.captures or ROOT/'docs/screenshots/arena-life29'/('current' if args.combined else '')).resolve()
    require(captures.is_relative_to(ROOT/'docs/screenshots') or captures.is_relative_to(ROOT/'build'),
            'Captures stay in this root workspace',str(captures))
    if args.combined:
        require(args.report==ROOT/f'docs/arena-life29-current-{args.core}.json' or args.report.is_relative_to(ROOT/'build'),
                'Combined proof uses its disjoint current report path',str(args.report))
        require(captures.is_relative_to(ROOT/'docs/screenshots/arena-life29/current') or captures.is_relative_to(ROOT/'build'),
                'Combined captures cannot overwrite isolated historical media',str(captures))
        require(not(args.core=='snes9x' and args.skip_replay),'Combined Snes9x proof must retain original unmasked baseline replay')
    require(stages==[0,1,2] or args.report.is_relative_to(ROOT/'build'),'Partial coverage stays diagnostic')
    manifest=json.loads((ROOT/'dist/manifest.json').read_bytes())
    report={'status':'failed','core':args.core,'rom':manifest,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'sources':sources,'memory_writes':False,'save_states':False,'audio_device':False,'media':[],'cases':[],'baseline_replays':[],
            'capture_root':str(captures),'native_inputs':{p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in
                (ROOT/'dist/abaqus-after-hours.sfc',ROOT/'dist/abaqus-after-hours.sym',ROOT/'dist/manifest.json')},
            'generated_inputs':file_hashes(ROOT/'assets/generated')}
    try:
        require(sha((ROOT/'dist/abaqus-after-hours.sfc').read_bytes())==manifest['sha256'],'Exact tested ROM identity')
        if args.combined:
            from v029_contracts import validate
            report['preservation']=validate(ROOT)
            require(report['preservation']['generated']['current_count']==237,
                    'Combined final inventory contains exactly 237 generated files excluding soundbank.h')
            report['combined_rom_context']=True
            report['combined_verification_claimed']=False
        else:report['preservation']=preservation(syms)
        report['core_identity']=core_identity() if args.core=='snes9x' else compat.verify_manifest_and_pinned_core()
        report['metadata']=json.loads((ROOT/'assets/generated/arena-life29.json').read_bytes())
        if args.core=='snes9x' and not args.skip_replay:
            report['baseline_inputs']=baseline_identity(args.baseline_rom.resolve(),args.baseline_symbols.resolve())
        for stage in stages:
            r=Rig(args.core,stage,[8,10,0][stage],syms,report,captures=captures)
            try:case=arena_case(r)
            finally:r.e.close()
            if args.core=='snes9x' and not args.skip_replay:report['baseline_replays'].append(replay_base(case,syms,report))
            case['input_callbacks']=len(case.pop('replay')['inputs']);report['cases'].append(case)
            print(json.dumps({'core':args.core,'stage':stage,'status':'passed','health':r.health}),flush=True)
        coverage={key:sum(c['health']['trace'][key] for c in report['cases']) for key in report['cases'][0]['health']['trace']}
        require(all(coverage[key]>0 for key in coverage),'Strict TRACE coverage includes partial/idle/pause/intro-abort/KO/no-upload and last-chunk samples',coverage)
        report['trace_coverage']=coverage
        require(snapshot()==sources,'Producer/harness/dependency bytes frozen during proof')
        require(file_hashes(ROOT/'assets/generated')==report['generated_inputs'],'Generated source/palette/phase bytes frozen during proof')
        require(all(sha((ROOT/name).read_bytes())==digest for name,digest in report['native_inputs'].items()),
                'Actual tested ROM/symbol/manifest bytes frozen during proof')
        if 'baseline_inputs' in report:
            require(baseline_identity(args.baseline_rom.resolve(),args.baseline_symbols.resolve())==report['baseline_inputs'],
                    'Original unmasked replay baseline remains exact after the full proof')
        report['status']='passed'
    except BaseException as error:report['error']=repr(error);raise
    finally:
        report.update(checks=list(CHECKS.values()),passed=sum(row['executions'] for row in CHECKS.values() if row['passed']),
                      elapsed_seconds=round(time.monotonic()-started,3))
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
        print(json.dumps({k:report[k] for k in ('status','core','passed','elapsed_seconds')}),flush=True)


if __name__=='__main__':main()
