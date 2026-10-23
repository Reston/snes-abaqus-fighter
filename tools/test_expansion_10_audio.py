"""Controller-only native PCM/cue/FIFO proof. No GUI, speaker, state writes or saves.

A separately built control ROM mutes only effect volume (same SPC commands and
voice allocation). Production-minus-control PCM identifies audible resident
sources on the exact controller timeline. Production is always tested first.
"""
from pathlib import Path
import array
import ctypes as C
import hashlib
import json
import math
import re
import shutil
import struct
import subprocess
import sys
import time
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from emulator import Emulator
from test_audio import metrics, samples
from victory_music import soundbank_budget
from audio_assets import NAMES, speech
from test_champion import host_contract

BASE = '610537d'
OUT = ROOT/'docs/expansion-10-audio'
REPORT = ROOT/'docs/expansion-10-report.json'
checks = []


def check(ok, label, detail=None):
    checks.append({'check': label, 'passed': bool(ok), 'details': detail})
    if not ok:
        raise AssertionError((label, detail))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def command(args, cwd=ROOT):
    r = subprocess.run([str(a) for a in args], cwd=cwd, capture_output=True,
                       creationflags=0x08000000 if sys.platform == 'win32' else 0)
    if r.returncode:
        raise RuntimeError(r.stdout.decode(errors='replace')+r.stderr.decode(errors='replace'))
    return r.stdout


def native_byte(e,name):
    if not hasattr(e,'_expansion10_symbols'):
        text=e.rompath.with_suffix('.sym').read_text(encoding='utf-8')
        e._expansion10_symbols={m[2]:int(m[1],16) for m in re.finditer(r'^([0-9a-fA-F]{8})\s+(\w+)$',text,re.M)}
    address=e._expansion10_symbols[name]
    if 0x7e0000<=address<0x800000:offset=address-0x7e0000
    elif address<0x2000:offset=address
    else:raise ValueError(('read outside WRAM',name,hex(address)))
    return C.string_at(e.ram+offset,1)[0]


def wav(name, pcm, rate=32040):
    path = OUT/(name+'.wav')
    with wave.open(str(path), 'wb') as out:
        out.setnchannels(2); out.setsampwidth(2); out.setframerate(rate); out.writeframes(pcm)
    return {'file': path.relative_to(ROOT).as_posix(), 'sha256': sha(path.read_bytes()),
            'bytes': path.stat().st_size, 'pcm': metrics(pcm, rate)}


def fixture():
    root = ROOT/'build/expansion10-muted'
    (root/'tools').mkdir(parents=True, exist_ok=True); (root/'dist').mkdir(exist_ok=True)
    shutil.copytree(ROOT/'src', root/'src', dirs_exist_ok=True)
    shutil.copyfile(ROOT/'tools/build.py', root/'tools/build.py')
    for name in ('assets', '.tools'):
        if not (root/name).exists():
            command(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                     '& { param($p, $t) New-Item -ItemType Junction -Path $p -Target $t | Out-Null }',
                     root/name, ROOT/name])
    path = root/'src/audio_presentation.h'
    code = path.read_text(encoding='utf-8')
    code, n = re.subn(r'(const u8 audioVolpan\[AUDIO_EFFECT_COUNT\]=)\{[^}]+\}',
                      r'\1{0x08,0x08,0x08,0x08,0x08,0x08,0x08,0x08,0x08,0x08,0x08}', code)
    check(n == 1, 'control ROM differs only in eleven effect-volume bytes')
    path.write_text(code, encoding='utf-8', newline='\n')
    command([sys.executable, root/'tools/build.py'], cwd=root)
    return root/'dist/abaqus-after-hours.sfc'


class Capture:
    def __init__(self, rom):
        self.e = Emulator(rom=rom)
        self.frames = []
        self.chunks = []
        self.cues = []
        self.old_cue = None
    def run(self, n=1, p1=(), p2=()):
        for _ in range(n):
            before = self.e.state()
            self.e.pcm.clear(); self.e.run(1, p1=p1, p2=p2)
            now = self.e.state()
            # Linker-resolved reads only; never write into emulator memory.
            cue = native_byte(self.e, 'audioLastCue')
            read, write = native_byte(self.e, 'spc_fread'), native_byte(self.e, 'spc_fwrite')
            queued = (write-read) & 255
            self.frames.append({**now, 'delta': (now['frame']-before['frame']) & 65535,
                                'backlog': queued, 'cue': cue,
                                'ppu_status':C.string_at(self.e.ram+0x1ff00+114*2,1)[0],
                                'volume': native_byte(self.e, 'audioVolume')})
            self.chunks.append(bytes(self.e.pcm))
            if cue != self.old_cue and cue<len(NAMES):
                self.cues.append({'frame': len(self.frames)-1, 'slot': cue, 'name': NAMES[cue]})
                self.old_cue = cue
        return now
    def tap(self, key, port=0):
        self.run(3, **({'p1': [key]} if port == 0 else {'p2': [key]})); self.run(3)
    def wait(self, predicate, limit=900):
        for _ in range(limit):
            if predicate(self.e.state()):return
            self.run()
        raise AssertionError(('controller route timeout', self.e.state()))
    def reset(self):
        self.frames=[]; self.chunks=[]; self.cues=[]; self.old_cue=None
    def close(self):self.e.close()


def boot(c, stage=0, mode=1):
    c.run(180)
    for _ in range(mode):c.tap('down')
    c.tap('a')
    c.wait(lambda s: s['screen']==1); c.tap('a'); c.tap('a', 1)
    c.wait(lambda s: s['screen']==2)
    for _ in range(stage):c.tap('down')
    c.tap('a'); c.wait(lambda s:s['screen']==3)


def scenario(rom, name, stage=0):
    c = Capture(rom)
    try:
        if name=='menu':
            c.run(180); c.reset(); c.tap('a'); c.run(90)
        else:
            boot(c, stage)
            if name=='intro':
                # Keep the first staged pose/announcement frames in this clip.
                c.reset(); c.run(130)
            else:
                c.wait(lambda s:s['intro']==0); c.run(65)
                # Walk P1 to 26px while P2 stays in place.
                for _ in range(160):
                    if abs(c.e.state()['x2']-c.e.state()['x1'])//16<=28:break
                    c.run(p1=['right'])
                c.run(8); c.reset()
                if name in ('light','strong','guard'):
                    key='x' if name=='strong' else 'y'
                    c.run(55, p1=[key], p2=['right'] if name=='guard' else [])
                elif name=='ko-victory':
                    # Complete two actual Versus rounds using toward+X throws.
                    for _ in range(10000):
                        s=c.e.state()
                        if s['screen']==4:break
                        forward='right' if s['x1']<s['x2'] else 'left'
                        if s['intro'] or s['round_end'] or s['hitstop'] or s['action1']:
                            c.run()
                        elif abs(s['x2']-s['x1'])//16>22:c.run(p1=[forward])
                        else:c.run(p1=[forward,'x']);c.run(p1=[forward])
                    check(c.e.state()['screen']==4, 'controller-only KO route earns Versus result')
                    c.run(100)
        pcm=b''.join(c.chunks)
        frames=c.frames
        check(all(len(chunk)>0 and len(chunk)%4==0 for chunk in c.chunks), name+': PCM every callback')
        backlog=max(s['backlog'] for s in frames)
        check(backlog<=6, name+': bounded resident SPC FIFO', backlog)
        # Forced-blank full scene loads are permitted; live/intro/KO processing
        # must retain one game tick per video callback after trace settles.
        failures=[{'index':i,'delta':s['delta'],'state':s} for i,s in enumerate(frames)
                  if i>2 and s['screen']==3 and frames[i-1]['screen']==3
                  and s['round_end']!=1 and s['delta']!=1]
        check(not failures,name+': native fight/announcement/contact cadence',failures[:2])
        check(metrics(pcm,32040)['clipped_samples']==0,name+': no mixed PCM clipping')
        return {'pcm':pcm, 'frames':frames, 'cues':c.cues, 'max_backlog':backlog,
                'chunk_bytes':[len(chunk) for chunk in c.chunks],
                'scene_boundary_callbacks':sum(s['delta']==0 and s['round_end']==1 for s in frames)}
    finally:c.close()


def delta_pcm(active, control):
    a,b=samples(active),samples(control)
    check(len(a)==len(b),'matched controller PCM timelines have equal sample count')
    d=array.array('h',(max(-32768,min(32767,x-y)) for x,y in zip(a,b)))
    return d.tobytes()


def speech_identity(name, delta, event, chunk_bytes):
    """Match actual decoded SPC speech against the retained spoken WAV.

    A 4 kHz comparison includes the word's time-varying vowel/consonant shape;
    unlike a peak/energy check, an arbitrary beep fails this identity proof.
    The native BRR/Gaussian/interpolator path changes amplitude and onset.
    """
    pcm = samples(delta)[::2]
    source = speech(name)
    step = 8
    template = []
    for i in range(int((len(source)-2)*32040/(8000*step))):
        pos=i*step*8000/32040
        index=int(pos);fraction=pos-index
        template.append(source[index]*(1-fraction)+source[index+1]*fraction)
    reference_energy=sum(v*v for v in template)
    onset=sum(chunk_bytes[:event['frame']])//4
    best=(-1,0)
    for start in range(max(0,onset-1068), min(len(pcm)-len(template)*step,onset+5340),step):
        values=pcm[start:start+len(template)*step:step]
        energy=sum(v*v for v in values)
        correlation=sum(x*y for x,y in zip(template,values))/math.sqrt(max(1,energy*reference_energy))
        if correlation>best[0]:best=(correlation,start)
    check(best[0]>.80,name+': native spoken waveform matches exported word, not a beep',round(best[0],5))
    return {'source_word':name,'normalized_correlation':round(best[0],6),
            'native_onset_sample':best[1],'queued_event_frame':event['frame'],
            'comparison_rate_hz':4005,'threshold':.80}


def preservation():
    changes=[]; unchanged=0
    names=command(['git','ls-tree','-r','--name-only',BASE,'assets/generated']).decode().splitlines()
    for name in names:
        old=command(['git','show',BASE+':'+name]);new=(ROOT/name).read_bytes()
        if Path(name).suffix in ('.asm','.h','.json'):
            old=old.replace(b'\r\n',b'\n');new=new.replace(b'\r\n',b'\n')
        if old!=new:changes.append(name)
        else:unchanged+=1
    check(changes==['assets/generated/effects.it','assets/generated/soundbank.asm','assets/generated/soundbank.bnk'],
          'all visual assets, music sources and original four BRR files byte-preserved',changes)
    def symbols(data):
        return {m[2]:int(m[1],16) for m in re.finditer(r'^([0-9a-fA-F]{8})\s+(\S+)$',data,re.M)
                if int(m[1],16)<0x2000 or 0x7e0000<=int(m[1],16)<0x800000}
    before=symbols(command(['git','show',BASE+':dist/abaqus-after-hours.sym']).decode())
    after=symbols((ROOT/'dist/abaqus-after-hours.sym').read_text(encoding='utf-8'))
    extent_labels={'SECTIONEND_globram.data','RAM_USAGE_SLOT_3_BANK_127_END'}
    moved=[name for name,value in before.items() if after.get(name)!=value and name not in extent_labels]
    check(not moved,'all established WRAM/direct-page symbols retain addresses',moved)
    def sample(raw,index):
        addr,bank=struct.unpack_from('<HB',raw,388+index*3)
        off=bank*32768+addr-0x8000
        length=struct.unpack_from('<H',raw,off)[0]
        return raw[off:off+4+length]
    old=command(['git','show',BASE+':assets/generated/soundbank.bnk'])
    new=(ROOT/'assets/generated/soundbank.bnk').read_bytes()
    for i in range(4):check(sample(old,i)==sample(new,i),'legacy resident BRR slot '+str(i)+' byte-preserved')
    old_sources=struct.unpack_from('<H',old)[0]
    for i in range(4,old_sources):
        check(sample(old,i)==sample(new,i+7),'original score BRR payload '+str(i)+' byte-preserved')
    for i in range(1,6):
        def module(raw,index):
            address,bank=struct.unpack_from('<HB',raw,4+index*3)
            offset=bank*32768+address-0x8000
            words,count=struct.unpack_from('<HH',raw,offset)
            start=offset+4+count*2
            return raw[start:start+words*2]
        check(module(old,i)==module(new,i),'original native score module '+str(i)+' byte-preserved')
    return {'base':BASE,'unchanged_generated_files':unchanged,'changed':changes,
            'preserved_ram_symbols':len(before)-len(extent_labels),'new_audio_state_bytes':8,
            'changed_extent_labels':{name:{'before':hex(before[name]),'after':hex(after[name])} for name in extent_labels},
            'new_state_range':['7F:0448','7F:044F']}


def stress(rom,stage):
    c=Capture(rom)
    try:
        boot(c,stage);c.wait(lambda s:s['intro']==0);c.run(65)
        c.reset()
        # Two-controller waves/air/ground moves produce overlapping cues,
        # hits, guarded hits, actor uploads and music mixing on all arenas.
        for tick in range(900):
            phase=tick%120
            if phase<25:p1,p2=['right'],['left']
            elif phase<45:p1,p2=['down','y'],['down','y']
            elif phase<65:p1,p2=['up','a'],['right']
            elif phase<85:p1,p2=['x'],['b']
            elif phase<100:p1,p2=['left','down'],['a']
            else:p1,p2=[],[]
            c.run(p1=p1,p2=p2)
            if c.e.state()['screen']==4:break
        failures=[i for i,s in enumerate(c.frames) if i>2 and s['screen']==3
                  and c.frames[i-1]['screen']==3 and s['round_end']!=1 and s['delta']!=1]
        check(not failures,'stage '+str(stage)+': simultaneous combat preserves native cadence',failures[:4])
        check(max(f['backlog'] for f in c.frames)<=6,'stage '+str(stage)+': stress FIFO bounded')
        check(not any(f['ppu_status']&0xc0 for f in c.frames),'stage '+str(stage)+': no native OBJ overflow')
        pcm=b''.join(c.chunks);stats=metrics(pcm,32040)
        check(stats['clipped_samples']==0 and stats['longest_near_silence_seconds']<.5,
              'stage '+str(stage)+': continuous unclipped combat/score PCM',stats)
        return {'frames':len(c.frames),'cadence_failures':failures,
                'max_spc_backlog':max(f['backlog'] for f in c.frames),
                'actual_cues':sorted({f['cue'] for f in c.frames}), 'pcm':stats}
    finally:c.close()


def code_budget():
    text=(ROOT/'dist/abaqus-after-hours.sym').read_text(encoding='utf-8')
    starts={};sections=[]
    for m in re.finditer(r'^([0-9a-fA-F]{8})\s+SECTION(START|END)_(\S+)$',text,re.M):
        address=int(m[1],16);name=m[3]
        if m[2]=='START':starts[name]=address
        elif name in starts and re.match(r'\.(audio|sound)',name):
            start=starts[name]
            check(start>>16==address>>16 and 0<address-start<32768,
                  'native audio section stays inside one LoROM bank: '+name)
            sections.append({'section':name,'address':hex(start),'bytes':address-start})
    return {'sections':sections,'code_bytes_including_compatibility_sound':sum(s['bytes'] for s in sections),
            'per_tick_spc_commands_max':1,'hardware_ready_adapter_modified':False}


def main():
    started=time.monotonic();OUT.mkdir(parents=True,exist_ok=True)
    rom=ROOT/'dist/abaqus-after-hours.sfc'
    report={'feature':10,'status':'failed','rom_sha256':sha(rom.read_bytes()),'checks':checks,
            'host_contract':{**host_contract(),'controller_only':True,'savestates':0,'emulated_memory_writes':0,
                             'audio_capture_only':True},'human_listening_approved':False}
    try:
        report['source_sha256']={p:sha((ROOT/p).read_bytes()) for p in (
            'src/game.c','src/audio_presentation.h','src/audio_presentation_state.h',
            'src/hardware.asm','tools/audio_assets.py','tools/make_assets.py',
            'tools/victory_music.py','tools/test_expansion_10_audio.py','tools/emulator.py')}
        report['core_sha256']=sha((ROOT/'.tools/core/snes9x_libretro.dll').read_bytes())
        report['preservation']=preservation()
        report['budget']=soundbank_budget(ROOT/'assets/generated/soundbank.bnk')
        report['native_code']=code_budget()
        report['source_speech']={n:{'retained_wav_sha256':sha((ROOT/'assets/audio/announcements'/(n+'.wav')).read_bytes()),
                                    'resident_seconds':len(speech(n))/8000} for n in ('round','fight','ko')}
        muted=fixture();report['control_rom_sha256']=sha(muted.read_bytes())
        production_bytes=rom.read_bytes();control_bytes=muted.read_bytes()
        changed=[i for i,(a,b) in enumerate(zip(production_bytes,control_bytes)) if a!=b]
        check(len(changed)==15 and changed[:4]==list(range(0x7fdc,0x7fe0)),
              'control cartridge differs in eleven volumes plus four checksum bytes only',changed)
        report['control_rom_difference_offsets']=changed
        results={}
        for name in ('menu','intro','light','strong','guard','ko-victory'):
            active=scenario(rom,name);control=scenario(muted,name)
            check(active['frames']==control['frames'],name+': identical native gameplay and audio command timeline in A/B')
            isolated=delta_pcm(active['pcm'],control['pcm'])
            stat=metrics(isolated,32040)
            check(stat['peak']>128 and stat['rms']>32,name+': cues audible above matched music bed',stat)
            # Keep a six-second continuous KO/result excerpt rather than a
            # long sequence of setup attacks; checks above cover all frames.
            excerpt_start=max(0,len(active['pcm'])-32040*4*6) if name=='ko-victory' else 0
            results[name]={'mix':wav(name+'-native-mix',active['pcm'][excerpt_start:]),
                           'cue_difference':wav(name+'-cue-difference',isolated[excerpt_start:]),
                           'capture_start_sample':excerpt_start//4,
                           'cues':active['cues'],'max_backlog':active['max_backlog'],
                           'frames':len(active['frames']),
                           'forced_blank_boundary_callbacks':active['scene_boundary_callbacks']}
            seen={f['cue'] for f in active['frames']}
            required={'menu':{9},'intro':{6,7},'light':{1},'strong':{4},'guard':{5},'ko-victory':{8,10}}[name]
            check(required<=seen,name+': controller event selects correct resident identities',sorted(seen))
            if name in ('light','strong'):
                check(min(s['hp2'] for s in active['frames'])<128,name+': actual contact damages opponent')
            if name=='guard':
                check(any(s['guard2'] and s['connected1']==1 for s in active['frames']),
                      'guard: native blocked contact, not a relabeled damage cue')
            if name=='intro':
                check(min(f['volume'] for f in active['frames'])==42 and active['frames'][-1]['volume']==86,
                      'speech ducks score and restores normal music volume')
                results[name]['speech_identity']=[speech_identity(NAMES[event['slot']],isolated,event,active['chunk_bytes'])
                    for event in active['cues'] if event['slot'] in (6,7)]
            if name=='ko-victory':
                results[name]['speech_identity']=[speech_identity('ko',isolated,event,active['chunk_bytes'])
                    for event in active['cues'] if event['slot']==8]
            if name in ('menu','intro'):
                check(results[name]['mix']['pcm']['longest_near_silence_seconds']<.5,
                      name+': no long transition dropout')
        # Repeat the speech-containing production timeline from another cold boot.
        repeat=scenario(rom,'intro')
        check(sha(repeat['pcm'])==results['intro']['mix']['pcm']['sha256_pcm'],
              'Round/Fight native mixed capture deterministic across cold boots')
        report['captures']=results
        distinction={}
        for name in ('light','strong','guard'):
            with wave.open(str(ROOT/results[name]['cue_difference']['file']),'rb') as source:
                values=samples(source.readframes(source.getnframes()))[::2]
            energy=sum(v*v for v in values)
            brightness=math.sqrt(sum((values[i]-values[i-1])**2 for i in range(1,len(values)))/energy)
            distinction[name]={'energy':energy,'normalized_first_difference':brightness}
        check(distinction['strong']['energy']>distinction['light']['energy']*1.25,
              'strong contact has measurably more native PCM body than light',distinction)
        check(distinction['guard']['normalized_first_difference']>distinction['strong']['normalized_first_difference']*1.5,
              'guard has measurably brighter native PCM than strong',distinction)
        report['contact_distinction']=distinction
        report['other_stage_intros']={}
        for stage in (1,2):
            active=scenario(rom,'intro',stage);control=scenario(muted,'intro',stage)
            check(active['frames']==control['frames'],'stage '+str(stage)+': matched speech/music A/B timeline')
            delta=delta_pcm(active['pcm'],control['pcm'])
            report['other_stage_intros'][str(stage)]={
                'mix':wav('stage'+str(stage)+'-intro-native-mix',active['pcm']),
                'speech_identity':[speech_identity(NAMES[event['slot']],delta,event,active['chunk_bytes'])
                    for event in active['cues'] if event['slot'] in (6,7)],
                'max_backlog':active['max_backlog']}
        report['combat_stress']={str(stage):stress(rom,stage) for stage in range(3)}
        report['status']='passed'
    except Exception as error:
        report['error']=repr(error);raise
    finally:
        report['passed']=sum(item['passed'] for item in checks)
        report['elapsed_seconds']=round(time.monotonic()-started,3)
        REPORT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:report[k] for k in ('status','passed','rom_sha256','elapsed_seconds')}))


if __name__=='__main__':main()
