"""Controller-only stage08 proof: native PPU planes, resources and two cores.

No save state, game-memory write, GUI or audio device. Run through
tools/run_background.py with the canonical .tools Python, after the shared
asset generator, stage_depth_assets.py, and native build. Shared reports stay.
"""
from __future__ import annotations

import ctypes as C
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
FLOOR_IN_SCENERY=json.loads((ROOT/'assets/generated/stage-depth.json').read_bytes()).get('floor_plane')=='BG1'
sys.path.insert(0,str(ROOT/'tools'))
from emulator import Emulator
from test_compatibility import Probe, verify_manifest_and_pinned_core
from test_champion import host_contract
from test_stages import vram_bytes, oam_memory, scanline_budget, actor_contract
from stage_depth_assets import colors, install
from expansion_contracts import combined_contract
from v024_contracts import canonical

OUT = ROOT/'docs/screenshots/combat-24-stage08'
REPORT = ROOT/'docs/combat-24-stage08-report.json'
BASE = '3f51120'
checks = []
failures = {key:[] for key in ('cadence','native_timing','overflow','transfer','ppu','freeze','spc')}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def check(ok,label,details=None):
    checks.append({'check':label,'passed':bool(ok),'details':details})
    if not ok:
        raise AssertionError((label,details))


def require(ok,kind,details):
    if not ok:
        failures[kind].append(details)
        raise AssertionError((kind,details))


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)


def symbol_map(raw):
    return {name:int(value,16) for value,name in re.findall(r'^([0-9A-Fa-f]{8}) (\S+)$',raw,re.M)}


SYMS = symbol_map((ROOT/'dist/abaqus-after-hours.sym').read_text())


def read(e,name,size=1,signed=False):
    address=SYMS[name]
    offset=address-0x7e0000 if address>=0x7e0000 else address
    return int.from_bytes(C.string_at(e.ram+offset,size),'little',signed=signed)


def camera(e):
    return read(e,'stageDepthFar',2,True)


def image(e):
    im=e.frame_image if isinstance(e,Probe) else e.frame
    return im.resize((256,224),Image.Resampling.NEAREST).convert('RGB')


def words(e):
    return [int.from_bytes(C.string_at(e.ram+0x1ff00+i*2,2),'little') for i in range(123)]


def video_timing(e):
    class Geometry(C.Structure):
        _fields_=[('base_width',C.c_uint),('base_height',C.c_uint),('max_width',C.c_uint),('max_height',C.c_uint),('aspect_ratio',C.c_float)]
    class Timing(C.Structure):
        _fields_=[('fps',C.c_double),('sample_rate',C.c_double)]
    class AV(C.Structure):
        _fields_=[('geometry',Geometry),('timing',Timing)]
    info=AV();e.core.retro_get_system_av_info(C.byref(info))
    check(abs(info.timing.fps-60.098811862348406)<0.001,'pinned core retains native NTSC video cadence',info.timing.fps)
    return {'fps':info.timing.fps,'pcm_sample_rate':info.timing.sample_rate,'callback_size':list(image(e).size)}


def render_plane(stage,floor=False):
    """Independent hardware bitplane/map decode, including both map screens."""
    name='stage'+str(stage)
    gfx=(ROOT/'assets/generated'/(name+('_floor_tiles.bin' if floor else '_tiles.bin'))).read_bytes()
    raw=(ROOT/'assets/generated'/(name+('_floor_map.bin' if floor else '_map.bin'))).read_bytes()
    entries=[int.from_bytes(raw[i:i+2],'little') for i in range(0,len(raw),2)]
    palette=colors((ROOT/'assets/generated'/('ui_pal.bin' if floor else name+'_pal.bin')).read_bytes())
    bpp=2 if floor else 4;width=256 if floor else 512
    result=Image.new('RGB',(width,256));pixels=result.load()
    for y in range(256):
        for x in range(width):
            col=x//8
            entry=entries[(col//32)*1024+(y//8)*32+col%32]
            index=entry&1023;bank=(entry>>10)&7;value=0
            xx=7-x%8 if entry&0x4000 else x%8
            yy=7-y%8 if entry&0x8000 else y%8
            for bit in range(bpp):
                value|=((gfx[index*(8*bpp)+(bit//2)*16+yy*2+bit%2]>>(7-xx))&1)<<bit
            if value:
                pixels[x,y]=palette[bank*4+value] if floor else palette[(bank-2)*16+value]
    return result


def difference(a,b):
    return max(high for low,high in ImageChops.difference(a,b).getextrema())


def oracle(e,plane,floor,offsets,impact=False):
    actual=image(e)
    # Above every standing actor. Impact text begins at row72.
    top,bottom=(40,72) if impact else (40,112)
    # A single full-picture offset must explain every scenery row and the
    # fixed floor. During contact, the SAME +/-2 shake composes on both planes.
    pairs=[(look+shake,shake) for look in offsets for shake in (range(-2,3) if impact else (0,))]
    scores=[]
    for d,shake in pairs:
        scenery_error=difference(actual.crop((0,top,256,bottom)),plane.crop((16+d,top,272+d,bottom)))
        expected_floor=(plane.crop((16+d,208,272+d,224)) if FLOOR_IN_SCENERY else
                        ImageChops.offset(floor,-shake,0).crop((0,208,256,224)))
        floor_error=difference(actual.crop((0,208,256,224)),expected_floor)
        scores.append(max(scenery_error,floor_error))
    if min(scores)>8:
        actual.save(ROOT/'build/stage08-oracle-failure.png')
    require(min(scores)<=8,'ppu',{'offset_pairs':pairs,'max_channel_errors':scores,'frame':e.state()['frame']})
    return pairs[scores.index(min(scores))][0],min(scores)


def gif(frames,name,step=3):
    selected=frames[::step];path=OUT/name
    selected[0].save(path,save_all=True,append_images=selected[1:],duration=round(1000*step/60.098811862348406),loop=0,disposal=2)
    return path.relative_to(ROOT).as_posix()


def boot(e,stage,fighter=0,fighter2=1):
    e.run(120)
    def tap(key,port=0):
        e.run(3,[key] if port==0 else (),[key] if port==1 else ());e.run(23)
    tap('down');tap('a')
    for _ in range(fighter):tap('right')
    tap('a')
    for _ in range((fighter2-e.state()['selected2'])%12):tap('right',1)
    tap('a',1)
    for _ in range(stage):tap('down')
    tap('a')
    # Screen-off stage/music loading deliberately spans callbacks. Begin the
    # live/intro cadence contract only after the published FIGHT trace.
    for _ in range(180):
        if e.state()['screen']==3:break
        e.run(1)
    check(e.state()['screen']==3 and e.state()['mode']==1,'controller menus reach chosen native local match',[stage,fighter,fighter2])
    return tap


class Observe:
    def __init__(self,e,label):
        self.e=e;self.label=label;self.frames=0;self.deltas=set();self.max_backlog=0
        self.peak_sprites=0;self.peak_tiles=0;self.actor_dma_frames=0
        self.vram=vram_bytes(e)
    def tick(self,p1=(),p2=()):
        e=self.e;old=e.state();vblank=read(e,'snes_vblank_count',2);lag=read(e,'lag_frame_counter',2)
        e.run(1,p1,p2);s=e.state();w=words(e);current=vram_bytes(e)
        delta=(s['frame']-old['frame'])&65535;self.deltas.add(delta);self.frames+=1
        require(delta==1,'cadence',{'case':self.label,'before':old,'after':s,'p1':p1,'p2':p2})
        require((read(e,'snes_vblank_count',2)-vblank)&65535==1,'native_timing',{'case':self.label,'frame':s['frame']})
        require(read(e,'lag_frame_counter',2)==lag,'native_timing',{'case':self.label,'frame':s['frame'],'kind':'lag'})
        require(w[114]&0xc0==0,'overflow',{'case':self.label,'frame':s['frame'],'stat77':w[114]})
        backlog=(read(e,'spc_fwrite')-read(e,'spc_fread'))&255;self.max_backlog=max(self.max_backlog,backlog)
        require(backlog<=6,'spc',{'case':self.label,'frame':s['frame'],'backlog':backlog})
        # Entire wide BG1 map and floor map immutable: legacy ambient must
        # never corrupt the right map half. Guide/UI uploads cannot cross.
        for a,b in ((0x7000,0x8000),(0xb800,0xc000),(0x6000,0x7000),(0xf000,0xf800)):
            require(current[a:b]==self.vram[a:b],'transfer',{'case':self.label,'range':[hex(a),hex(b)],'frame':s['frame']})
        changed=sum(current[a:b]!=self.vram[a:b] for a,b in ((0xc000,0xd400),(0xd400,0xe800)))
        require(changed<=1,'transfer',{'case':self.label,'actor_pages_changed':changed,'frame':s['frame']})
        self.actor_dma_frames+=changed
        budget=scanline_budget(oam_memory(e));self.peak_sprites=max(self.peak_sprites,budget['max_sprites']);self.peak_tiles=max(self.peak_tiles,budget['max_tiles'])
        require(self.peak_sprites<=32 and self.peak_tiles<=34,'overflow',{'case':self.label,'budget':budget})
        require(w[115:119]==[0,0,255,0],'transfer',{'case':self.label,'ambient_trace':w[115:119]})
        self.vram=current
        return s
    def run(self,n,p1=(),p2=()):
        for _ in range(n):s=self.tick(p1,p2)
        return s
    def report(self):
        return {'measured_frames':self.frames,'cadence_deltas':sorted(self.deltas),'max_spc_backlog':self.max_backlog,
                'obj_peak_sprites':self.peak_sprites,'obj_peak_tiles':self.peak_tiles,'actor_dma_frames':self.actor_dma_frames}


def stage_case(stage,independent=False):
    label=('accuracy' if independent else 'snes9x')+'-stage'+str(stage)
    e=Probe() if independent else Emulator();frames=[];impact_frames=[];states=[];stills={}
    def save_still(frame,name):
        path=OUT/(label+'-'+name+'.png');frame.save(path)
        stills[path.relative_to(ROOT).as_posix()]=sha(path.read_bytes())
    plane,floor=render_plane(stage),render_plane(stage,True)
    try:
        boot(e,stage,4,6)
        obs=Observe(e,label)
        intro_samples=0
        while e.state()['intro']:
            old=camera(e);obs.tick(['left'],['right']);intro_samples+=1
            require(camera(e)==old==0,'freeze',{'case':label,'policy':'intro'})
        obs.run(8)
        initial=image(e);save_still(initial,'center')
        oracle(e,plane,floor,[0])
        glyphs=vram_bytes(e)[0x8000:0xb000]
        pixel_checks=1
        for direction,count in (('left',90),('right',170),('left',170)):
            for i in range(count):
                before=camera(e);obs.tick([direction],[direction]);after=camera(e)
                matched,error=oracle(e,plane,floor,sorted({before,after}));pixel_checks+=1
                states.append([e.state()['frame'],before,after,matched,error])
                frames.append(image(e))
            obs.run(4)
            expected=-8 if direction=='left' else 8
            check(camera(e)==expected,'both ports drive full authored camera bounds',[label,direction,camera(e)])
            require(vram_bytes(e)[0x8000:0xb000]==glyphs,'transfer',{'case':label,'policy':'glyph/portrait preservation'})
            # Clock and energy legitimately progress during this long walk.
            # Names and untouched health bars must remain pixel-exact.
            for rect in ((0,0,112,16),(160,0,256,16)):
                check(difference(initial.crop(rect),image(e).crop(rect))==0,'HUD names/health stay exact during whole-plane movement',[label,rect])
            actor_contract(e,expected_floor=201)
            save_still(image(e),direction)
        # Match the shared controller fixtures' three-frame button press.
        # One callback pulses can fall between this core's joypad samples.
        obs.run(3,p2=['start']);obs.run(10)
        check(e.state()['paused']==1,'P2 Start enters native pause before freeze proof',label)
        frozen=camera(e);obs.run(32,['left'],['right'])
        require(e.state()['paused'] and camera(e)==frozen,'freeze',{'case':label,'policy':'pause'})
        obs.run(3,['select']);obs.run(15);frozen_image=image(e)
        obs.run(24)
        require(image(e).tobytes()==frozen_image.tobytes(),'freeze',{'case':label,'policy':'opaque Controls guide'})
        save_still(image(e),'guide')
        obs.run(3,['start']);obs.run(10)
        # Native contact, hitstop, shake and real KO. Never write game state.
        saw_hitstop=0;shake_pixels=set();hits=0;oldhp=e.state()['hp2']
        for i in range(2600):
            s=e.state();distance=abs(s['x1']-s['x2'])//16
            # Contacts now follow the actual active fist/body rectangles.
            # Approach inside24px instead of the historical26px whiff edge.
            keys=['right' if s['x1']<s['x2'] else 'left'] if distance>22 else (['down','x'] if i%38<3 else [])
            before=camera(e);oldstop=s['hitstop'];obs.tick(keys)
            if oldstop and not s['round_end']:
                require(camera(e)==before,'freeze',{'case':label,'policy':'hitstop look','frame':s['frame']});saw_hitstop+=1
            if e.state()['hp2']<oldhp:hits+=1;oldhp=e.state()['hp2']
            if e.state()['hitstop'] or read(e,'shake'):
                matched,error=oracle(e,plane,floor,sorted({before,camera(e)}),impact=True)
                shake_pixels.add(matched-camera(e));impact_frames.append(image(e));pixel_checks+=1
            if e.state()['round_end']:break
        check(e.state()['hp2']==0 and hits>0 and saw_hitstop>0,'actual controller contacts produce hitstop and KO',[label,hits,saw_hitstop])
        check(any(x for x in shake_pixels),'PPU shows bounded whole-scene contact shake',[label,sorted(shake_pixels)])
        frozen=camera(e);obs.run(60)
        require(camera(e)==frozen,'freeze',{'case':label,'policy':'round end'})
        # Separate simultaneous low-wave and jump traffic follows below;
        # contacts here are high specials so the scene stays visually clear.
        result={'stage':stage,'core':label.split('-')[0],'video_timing':video_timing(e),'intro_frozen_samples':intro_samples,
                'camera_bounds':[-8,8],'pixel_oracle_frames':pixel_checks,'contacts':hits,'frozen_hitstop_samples':saw_hitstop,
                'impact_pixel_offsets':sorted(shake_pixels),'movement_clip':gif(frames,label+'-movement.gif'),
                'impact_clip':gif(impact_frames,label+'-contacts.gif',step=1),
                'impact_clip_policy':'selected contact/hitstop episodes concatenated; GIF playback timing is approximate',
                'stills':[{'path':path,'sha256':digest,'scope':'current native PPU'} for path,digest in sorted(stills.items())],
                'pixel_samples_sha256':sha(json.dumps(states).encode()),**obs.report()}
        check(e.audio_samples>0 and e.audio_peak>0,'native SPC produces captured PCM without a device',[label,e.audio_samples,e.audio_peak])
        return result
    finally:e.close()


def stress(stage,independent=False):
    e=Probe() if independent else Emulator();label=('accuracy' if independent else 'snes9x')+'-stress'+str(stage)
    try:
        boot(e,stage,4,6)
        while e.state()['intro']:e.run(1)
        e.run(8);obs=Observe(e,label);two=0;waves=0;frames=[]
        for i in range(720):
            phase=i%120
            if phase<4:p1=p2=['down']
            elif phase<6:p1=p2=['down','y']
            elif 65<=phase<67:p1=p2=['up']
            elif 70<=phase<90:p1,p2=['right'],['left']
            elif 90<=phase<110:p1,p2=['left'],['right']
            else:p1=p2=[]
            s=obs.tick(p1,p2);two+=int(bool(s['wave1'] and s['wave2']));waves+=int(bool(s['wave1'] or s['wave2']))
            if i<240:frames.append(image(e))
        check(two>0,'both ports issue simultaneous native low waves',[label,two])
        return {'stage':stage,'core':label.split('-')[0],'two_wave_frames':two,'wave_frames':waves,
                'clip':gif(frames,label+'.gif'),**obs.report()}
    finally:e.close()


def roster():
    rows=[]
    for fighter in range(0,12,2):
        e=Emulator()
        try:
            boot(e,fighter%3,fighter,fighter+1)
            while e.state()['intro']:e.run(1)
            e.run(8);obs=Observe(e,'roster'+str(fighter))
            for i in range(180):
                phase=i%60
                p1,p2=(['left'],['right']) if phase<20 else ((['right'],['left']) if phase<40 else (['up'],['up']))
                obs.tick(p1,p2)
            rows.append({'fighters':[fighter,fighter+1],**obs.report()})
        finally:e.close()
    check(len(rows)==6,'every fighter and both controller ports covered by native motion',list(range(12)))
    return rows


def before_clips():
    path=ROOT/'build/stage08-baseline.sfc';path.write_bytes(git('show',BASE+':dist/abaqus-after-hours.sfc'))
    rows=[]
    for stage in range(3):
        e=Emulator(rom=path);frames=[]
        try:
            boot(e,stage,4,6)
            while e.state()['intro']:e.run(1)
            e.run(8)
            for direction,count in (('left',90),('right',170),('left',170)):
                for _ in range(count):e.run(1,[direction],[direction]);frames.append(image(e))
            rows.append({'stage':stage,'rom_sha256':sha(path.read_bytes()),'clip':gif(frames,'baseline-stage'+str(stage)+'.gif')})
        finally:e.close()
    return rows


def before_floor_clips(path):
    """Optional same-contact-base old-floor ROM, retained under ignored build.

    Capture native before/after material comparisons. This additional review
    input never replaces any assertions on the current candidate cartridge.
    """
    rows=[]
    for stage in range(3):
        e=Emulator(rom=path);frames=[]
        try:
            boot(e,stage,4,6)
            while e.state()['intro']:e.run(1)
            e.run(8)
            before=image(e);before.save(OUT/f'floor-before-stage{stage}.png')
            after=Image.open(OUT/f'snes9x-stage{stage}-center.png').convert('RGB')
            seam=(184,192,184)[stage]
            check(difference(before.crop((0,40,256,seam)),after.crop((0,40,256,seam)))==0,
                  'native floor review keeps the complete upper scene exact',stage)
            check(difference(before.crop((0,208,256,224)),after.crop((0,208,256,224)))>8,
                  'native floor review shows actual ground material change',stage)
            # Left is before, right is after. Nearest enlargement preserves
            # native pixels; this review artifact never changes source art.
            comparison=Image.new('RGB',(512,224));comparison.paste(before,(0,0));comparison.paste(after,(256,0))
            comparison.resize((1024,448),Image.Resampling.NEAREST).save(OUT/f'floor-comparison-stage{stage}.png')
            for direction,count in (('left',90),('right',170),('left',170)):
                for _ in range(count):e.run(1,[direction],[direction]);frames.append(image(e))
            rows.append({'stage':stage,'rom_sha256':sha(path.read_bytes()),
                         'native_before':f'docs/screenshots/combat-24-stage08/floor-before-stage{stage}.png',
                         'native_comparison':f'docs/screenshots/combat-24-stage08/floor-comparison-stage{stage}.png',
                         'layout':'before left / after right;2x nearest native pixels',
                         'clip':gif(frames,f'floor-before-stage{stage}.gif')})
        finally:e.close()
    return rows


def resources():
    combined=combined_contract(ROOT)
    changed=[];added=[];preserved=0
    tracked=git('ls-tree','-r','--name-only',BASE,'--','assets/generated').decode().splitlines()
    allowed={'assets/generated/'+n for n in ('assets.h','data.asm')}
    for i in range(3):
        allowed|={f'assets/generated/stage{i}'+ext for ext in ('.png','_tiles.bin','_map.bin','_pal.bin')}
    for name in tracked:
        new=canonical(name,(ROOT/name).read_bytes());old=canonical(name,git('show',BASE+':'+name))
        if new!=old:changed.append(name)
        else:preserved+=1
    for path in (ROOT/'assets/generated').iterdir():
        name=path.relative_to(ROOT).as_posix()
        if name not in tracked and path.name!='soundbank.h':added.append(name)
    expected={f'assets/generated/stage{i}_floor_{part}.bin' for i in range(3) for part in ('tiles','map')}|{'assets/generated/stage-depth.json'}
    check(allowed<=set(changed) and set(added)==expected,'all declared stage planes are present within the combined allocation',{'changed':changed,'added':added,'preserved':preserved})
    check(set(changed)==set(combined['assets']['changed_generated']) and set(added)==set(combined['assets']['added_generated']),
          'independent combined preservation policy binds every generated change')
    protected=git('ls-tree','-r','--name-only',BASE,'--','assets/art','assets/references').decode().splitlines()
    for name in protected:
        check(canonical(name, (ROOT/name).read_bytes()) == canonical(name, git('show', BASE+':'+name)),
              'original source or provenance preserved (canonical text, exact binary)', name)
    oldsyms=symbol_map(git('show',BASE+':dist/abaqus-after-hours.sym').decode())
    ram={n:v for n,v in oldsyms.items() if v<0x2000 or 0x7e0000<=v<0x800000}
    moved={n:[hex(v),hex(SYMS.get(n,0))] for n,v in ram.items() if SYMS.get(n)!=v}
    check(set(moved)==set(combined['native']['documented_relocations']),
          'prior RAM symbols obey the bounded combined policy',{'count':len(ram),'moved':moved})
    check(SYMS['stageVictoryPhase']+1-SYMS['stageDepthTable']==16,'exact historical sixteen-byte stage reservation retained')
    sections=[]
    for name,start in SYMS.items():
        if name.startswith('SECTIONSTART_') and start>=0x800000:
            end=SYMS.get(name.replace('SECTIONSTART_','SECTIONEND_'))
            if end is not None and end>start:
                check(start>>15==(end-1)>>15,'native linked section fits one32KiB bank',name);sections.append(end-start)
    data=(ROOT/'dist/abaqus-after-hours.sfc').read_bytes()
    check(len(data)==4194304 and data[0x7fd5]==0x30,'native4MiB NTSC FastROM LoROM retained')
    manifest=json.loads((ROOT/'assets/generated/stage-depth.json').read_text())
    previous=json.loads(git('show','7c5bf13:docs/combat-24-stage08-report.json'))['resources']['stage_allocations']
    for stage in manifest['stages']:
        for name,record in stage['outputs'].items():
            check(sha((ROOT/'assets/generated'/name).read_bytes())==record['sha256'],'generated stage payload matches exact encoder manifest',name)
        old=previous['stages'][stage['id']]
        for part in ('tiles','map','pal'):
            name=f"stage{stage['id']}_{part}.bin"
            check(stage['outputs'][name]==old['outputs'][name],'round2 preserves complete upper scenery byte for byte',name)
        check(2<stage['bg3_tiles']<=256,'authored ground has genuine material tiles within existing BG3 allocation',[stage['id'],stage['bg3_tiles']])
        floor=render_plane(stage['id'],True).crop((0,stage['floor_seam_y'],256,224))
        palette=set(floor.get_flattened_data())
        check(palette==set(colors((ROOT/'assets/generated/ui_pal.bin').read_bytes())[6:8]),
              'ground uses exactly two quiet existing blue-gray UI colors',[stage['id'],sorted(palette)])
        check(max(abs(a[k]-b[k]) for a in palette for b in palette for k in range(3))<=48,
              'floor contrast remains restrained beneath dark actor shadows',stage['id'])
    generated=lambda:{p.name:sha(p.read_bytes()) for p in (ROOT/'assets/generated').iterdir() if p.is_file()}
    before=generated();install(ROOT);after=generated()
    check(before==after,'full authored stage generation is byte-idempotent',{'files':len(before),'changed':[n for n in before if before[n]!=after.get(n)]})
    return {'changed_generated':changed,'added_generated':sorted(added),'preserved_generated':preserved,
            'generated_count':len(tracked)+len(added),'existing_ram_symbols':len(ram),'ram_moved':moved,
            'new_stage_ram_bytes':0,'combined_native_policy':combined['native'],'reused_stage_bytes':16,'hdma_mask':0,'live_stage_dma_bytes':0,'new_obj_entries':0,
            'actor_pose_dma_bytes':3840,'actor_obj_entries':30,'linked_section_bytes':sum(sections),'stage_allocations':manifest,
            'idempotent_encoder':{'files':len(before),'changed':[]}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--floor-before-rom',type=Path)
    args=parser.parse_args()
    started=time.monotonic();OUT.mkdir(parents=True,exist_ok=True)
    report={'status':'failed','scope':'current-cartridge whole scenery and authored-floor proof; combined completion remains parent-owned','baseline_commit':BASE,
            'integration_base':'8d0505d','previous_feature_head':'7c5bf13b1578d769d308a5e89d4913c08baf654d',
            'source_commit':git('rev-parse','HEAD').decode().strip(),'command':subprocess.list2cmdline([sys.executable,*sys.argv]),
            'rom_sha256':sha((ROOT/'dist/abaqus-after-hours.sfc').read_bytes()),'rom_bytes':4194304,
            'harness_sha256':sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n')),'host':host_contract(),
            'checks':checks,'failure_arrays':failures,'stages':[],'stress':[],'roster':[]}
    owned=[ROOT/'src/game.c',ROOT/'src/stage_depth.h',ROOT/'tools/stage_depth_assets.py',Path(__file__),
           *sorted((ROOT/'assets/art/stages/depth-v1').rglob('*')),
           *sorted((ROOT/'assets/art/stages/depth-floor-v2').rglob('*'))]
    report['source_files_sha256']={p.relative_to(ROOT).as_posix():sha(p.read_bytes().replace(b'\r\n',b'\n') if p.suffix in ('.py','.h','.c','.json') else p.read_bytes()) for p in owned if p.is_file()}
    report['retained_candidate_rom']='build/v024-stage08.sfc'
    report['version']=json.loads((ROOT/'dist/manifest.json').read_text())['version']
    try:
        report['resources']=resources();report['accuracy_core']=verify_manifest_and_pinned_core()
        report['snes9x_core_sha256']=sha((ROOT/'.tools/core/snes9x_libretro.dll').read_bytes())
        check(report['snes9x_core_sha256']=='f00db5bd97bbe0e80761e590449eb14716bd9ab5785a1b50725c55e10505c343','official Snes9x1.63 x64 core is pinned')
        for independent in (False,True):
            for stage in range(3):
                report['stages'].append(stage_case(stage,independent));report['stress'].append(stress(stage,independent))
        report['roster']=roster();report['before']=before_clips()
        if args.floor_before_rom:report['floor_before']=before_floor_clips(args.floor_before_rom)
        report['status']='passed'
    except Exception as exc:
        report['error']=repr(exc)
        raise
    finally:
        report['elapsed_seconds']=round(time.monotonic()-started,3);report['check_count']=len(checks)
        REPORT.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
        print(json.dumps({k:report[k] for k in ('status','rom_sha256','check_count','elapsed_seconds','failure_arrays')}),flush=True)


if __name__=='__main__':main()
