"""Controller-only v0.25 pacing/floor evidence; native 60 Hz, silent/headless."""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from PIL import Image
from emulator import Emulator
from test_characters import boot
import test_expansion_03_normal_balance as balance
from test_champion import host_contract
from v025_contracts import BASE,BASE_ROM,validate,symbols
from release_evidence import EXPECTED_NATIVE_CORE,EXPECTED_INDEPENDENT_CORE

OUT=ROOT/'docs/screenshots/pacing-floor-v025'
BEFORE=ROOT/'build/v025-before/abaqus-after-hours.sfc'
CHECKS={};HEALTH={'measured_callbacks':0,'max_spc_backlog':0,'failures':[]}
SYMS=symbols((ROOT/'dist/abaqus-after-hours.sym').read_bytes())
HARNESS=('tools/test_pacing_floor_25.py','tools/v025_contracts.py','tools/emulator.py',
         'tools/test_characters.py','tools/test_inputs.py','tools/test_champion.py',
         'tools/test_expansion_03_normal_balance.py','tools/test_expansion_07_supers.py',
         'tools/test_expansion_06_cpu_personality.py','tools/test_combat_24_stage08.py',
         'tools/test_compatibility.py','tools/stage_sources.py','tools/stage_depth_assets.py')

def sha(raw):return hashlib.sha256(raw).hexdigest()
def require(ok,label,details=None):
    row=CHECKS.setdefault(label,{'check':label,'passed':True,'executions':0})
    row['executions']+=1
    if not ok:
        row.update(passed=False,details=details)
        raise AssertionError((label,details))

def inputs():
    files=sorted(set(HARNESS)|{p.relative_to(ROOT).as_posix() for directory in ('src','tools')
                              for p in (ROOT/directory).iterdir() if p.is_file() and p.suffix in ('.py','.c','.h','.asm')})
    return {name:sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n')) for name in files}

def read(e,name,size=2):return int.from_bytes(C.string_at(e.ram+(SYMS[name]&0x1ffff),size),'little')
ORIGINAL_RUN=Emulator.run
def monitored_run(e,count=1,*args,**kwargs):
    before=e.state();watch=count==1 and before['screen']==3 and read(e,'screen',1)==3 and not before['intro']
    if watch:
        counters=[read(e,n) for n in ('frame','snes_vblank_count','lag_frame_counter')]
        samples=e.audio_samples
    result=ORIGINAL_RUN(e,count,*args,**kwargs)
    after=e.state()
    # A result loader assigns its real scene byte before the next TRACE
    # publication. Forced-blank scene loads are outside live fight cadence.
    if watch and after['screen']==3 and read(e,'screen',1)==3 and not after['intro']:
        current=[read(e,n) for n in ('frame','snes_vblank_count','lag_frame_counter')]
        deltas=[(a-b)&65535 for a,b in zip(current,counters)]
        HEALTH['measured_callbacks']+=1
        if deltas!=[1,1,0] or (after['frame']-before['frame'])&65535!=1:
            event={'before':counters,'after':current,'deltas':deltas,'trace':[before['frame'],after['frame']]}
            HEALTH['failures'].append(event)
            require(False,'native frame/vblank advance once with zero SDK lag',event)
        stat=int.from_bytes(C.string_at(e.ram+0x1ff00+228,2),'little')
        require(stat&0xc0==0,'native STAT77 stays within OBJ limits',stat)
        require(e.audio_samples>samples,'PCM callback advances without opening a device')
        backlog=(read(e,'spc_fwrite',1)-read(e,'spc_fread',1))&255
        HEALTH['max_spc_backlog']=max(HEALTH['max_spc_backlog'],backlog)
        require(backlog<=6,'resident SPC FIFO remains bounded',backlog)
    return result

class Rig(balance.Rig):
    def __init__(self,fighter,port,phase):
        self.port,self.fighter,self.phase=port,fighter,phase
        self.a,self.d=str(port+1),str(2-port)
        self.tag=f'{phase} fighter{fighter:02d} P{port+1}'
        self.e=boot(1,fighter,fighter%3,fighter,rom=BEFORE if phase=='before' else None)
        self.syms=SYMS;self.base=SYMS['fighters']&0x1ffff
        self.label=None;self.images={}
    def step(self,attack=(),defend=()):
        s=super().step(attack,defend)
        if self.fighter==0 and self.port==0 and self.label:
            self.images.setdefault(self.label,[]).append(self.e.frame.copy())
        return s
    def save(self):
        captures={}
        for name,frames in self.images.items():
            path=OUT/f'{self.phase}-{name}.gif';selected=frames[::3]
            selected[0].save(path,save_all=True,append_images=selected[1:],duration=50,loop=0,disposal=2)
            captures[name]={'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path.read_bytes()),'native_callbacks':len(frames),'sample_stride':3,'gif_duration_ms':50}
        return captures

def measure(fighter,port,phase):
    r=Rig(fighter,port,phase);row={'fighter':fighter,'port':port,'phase':phase,'normals':{},'impacts':{}}
    try:
        r.position(112)
        r.label='movement';start=r.state()[f'x{r.a}']
        for _ in range(24):s=r.step((r.direction(True),))
        row['walk_pixels_per_tick']=abs(s[f'x{r.a}']-start)/384
        start=s[f'x{r.a}']
        for _ in range(24):s=r.step((r.direction(False),))
        row['retreat_pixels_per_tick']=abs(s[f'x{r.a}']-start)/384;r.label=None
        for keys,action,name in [(('y',),1,'jab'),(('b',),4,'light-kick'),(('x',),3,'strong-punch'),(('a',),5,'strong-kick')]:
            r.position(112);r.label='heavy' if action==3 else None
            s=r.step(keys);require(s[f'action{r.a}']==action,'face buttons still select the intended action',[r.tag,keys,s])
            timing=r.timing();ticks=[];hp=s[f'hp{r.d}']
            for _ in range(120):
                if not s[f'action{r.a}']:break
                ticks.append(s[f'tick{r.a}']);s=r.step()
            require(ticks==list(range(1,timing['total'])) and s[f'hp{r.d}']==hp,'every native whiff tick completes without phantom contact',[r.tag,name,timing,ticks])
            row['normals'][name]=timing;r.label=None
        r.position(112);r.label='jump';ys=[]
        s=r.step(('up',));require(s[f'y{r.a}']!=0,'a jump begins through the controller',r.tag)
        for _ in range(100):
            y=s[f'y{r.a}'];ys.append(y-65536 if y&32768 else y)
            if y==0:break
            s=r.step()
        require(ys[-1]==0 and min(ys)<-16,'jump reaches a real apex and returns to the floor',r.tag)
        row['jump']={'airborne_callbacks':len(ys)-1,'apex_pixels':-min(ys)/16};r.label=None
        for keys,name,blocked in [(('y',),'light-hit',False),(('x',),'strong-hit',False),(('a',),'guard',True)]:
            r.position(24);r.label=name;guard=('down',r.direction(False,True)) if blocked else ()
            hp=r.state()[f'hp{r.d}'];s=r.step(keys,guard)
            for _ in range(60):
                if s[f'connected{r.a}']:break
                s=r.step((),guard)
            require(s[f'connected{r.a}']==(1 if blocked else 2),'impact is earned by real hit or guard',[r.tag,name,s])
            row['impacts'][name]={'hitstop':s['hitstop'],'hurt':s[f'hurt{r.d}'],'damage':hp-s[f'hp{r.d}']}
            for _ in range(100):
                if not s['hitstop'] and not s[f'hurt{r.d}']:break
                s=r.step((),guard)
            r.label=None;r.settle()
        row['captures']=r.save()
        return row
    finally:r.close()

def pacing(fighters):
    rows=[]
    for fighter in fighters:
        for port in range(2):
            before=measure(fighter,port,'before');after=measure(fighter,port,'after')
            for field in ('walk_pixels_per_tick','retreat_pixels_per_tick'):
                require(0<after[field]<=before[field]*.82,'ground travel is visibly slower on both native ports',[fighter,port,field,before[field],after[field]])
            require(after['jump']['airborne_callbacks']>=before['jump']['airborne_callbacks']*1.15,'jump airtime grows at least fifteen percent',[fighter,port,before['jump'],after['jump']])
            require(.88<=after['jump']['apex_pixels']/before['jump']['apex_pixels']<=1.12,'slower jumps retain their physical height identity',[fighter,port,before['jump'],after['jump']])
            for name,timing in after['normals'].items():
                prior=before['normals'][name]
                require(timing['startup']>prior['startup'] and timing['total']>=prior['total']*1.18,'light and strong attacks both have longer readable commitment',[fighter,port,name,prior,timing])
            for name,impact in after['impacts'].items():
                require(impact['hitstop']>before['impacts'][name]['hitstop'],'all hit/guard classes gain a perceptible contact pause',[fighter,port,name,before['impacts'][name],impact])
                require(impact['damage']==before['impacts'][name]['damage'],'pacing does not change normal damage',[fighter,port,name])
            rows.append({'before':before,'after':after,'crossing':crossing(fighter,port)})
            print(json.dumps({'part':'pacing','fighter':fighter,'port':port,'status':'passed'}),flush=True)
    return rows

def crossing(fighter,port):
    r=Rig(fighter,port,'after')
    try:
        r.position(32);initial=r.state();forward=r.direction(True);crossed=False;rows=[]
        r.label='crossing'
        for index in range(110):
            s=r.step(('up',forward) if index==0 else (forward,))
            rows.append({k:s[k] for k in ('frame',f'x{r.a}',f'x{r.d}',f'y{r.a}',f'face{r.a}')})
            beyond=(s[f'x{r.a}']>s[f'x{r.d}']) if forward=='right' else (s[f'x{r.a}']<s[f'x{r.d}'])
            if s[f'y{r.a}'] and beyond:
                crossed=True
                require(s[f'face{r.a}']==initial[f'face{r.a}'],'crossing keeps committed airborne facing',[r.tag,s])
            if crossed and not s[f'y{r.a}']:break
        require(crossed and not s[f'y{r.a}'],'every fighter crosses a standing opponent and lands through real controls',[r.tag,rows])
        r.label=None
        for _ in range(3):s=r.step()
        require(s[f'face{r.a}']!=initial[f'face{r.a}'],'grounded facing updates after the slower cross-over',[r.tag,s])
        return {'fighter':fighter,'port':port,'native_callbacks':len(rows),'crossed_airborne':crossed,'landed':not bool(s[f'y{r.a}']),'captures':r.save()}
    finally:r.close()

def supers(fighters):
    import test_expansion_07_supers as legacy
    import test_combat24_super as dedicated
    legacy.SYMBOLS=SYMS
    rows=[]
    for fighter in fighters:
        for port in range(2):
            for guard in (False,True):
                rows.append(dedicated.guarded_contact(fighter,port) if guard else legacy.contact(fighter,port,False))
        print(json.dumps({'part':'supers','fighter':fighter,'status':'passed'}),flush=True)
    require(not legacy.timing['cadence_failures'] and not legacy.timing['overflow_failures'],'all slower super phases retain strict native cadence and complete hit/guard sequences',legacy.timing)
    return rows

def cpu(fighters):
    import test_expansion_06_cpu_personality as legacy
    legacy.SYMBOLS={n:a&0x1ffff for n,a in SYMS.items()}
    rows={'before':[],'after':[],'hard_replays':[]}
    original_init=Emulator.__init__
    def prior_init(e,rom=None,core_options=None):
        original_init(e,BEFORE if rom is None else rom,core_options)
    try:
        for phase in ('before','after'):
            Emulator.__init__=prior_init if phase=='before' else original_init
            for fighter in fighters:
                for level in range(3):
                    row=legacy.encounter(fighter,level,1800)
                    require(not row['cadence_failures'],'all CPU personalities advance without missed native ticks',[phase,fighter,level])
                    rows[phase].append(row)
                print(json.dumps({'part':'cpu','phase':phase,'fighter':fighter,'status':'passed'}),flush=True)
        for fighter in fighters:
            row=legacy.encounter(fighter,2,1800,noisy_p2=True)
            prior=next(r for r in rows['after'] if r['cpu']==fighter and r['difficulty']==2)
            require(not row['cadence_failures'] and row['trace_sha256']==prior['trace_sha256'],
                    'Hard CPU replay ignores the physical P2 gameplay stream',[fighter,row['trace_sha256'],prior['trace_sha256']])
            rows['hard_replays'].append(row)
    finally:Emulator.__init__=original_init
    counts={phase:sum(r['metrics']['attack_starts'] for r in rows[phase]) for phase in ('before','after')}
    require(counts['after']<counts['before'],'paired native encounters actually reduce aggregate CPU attack frequency',counts)
    rows['pressure']={**counts,'reduction_percent':round((1-counts['after']/counts['before'])*100,2),
                      'policy':'same 1800-tick player script responds to the observed state; no gameplay equality claimed'}
    return rows

def stages():
    import test_combat_24_stage08 as depth
    depth.OUT=OUT/'stages';depth.OUT.mkdir(parents=True,exist_ok=True)
    rows=[]
    for independent in (False,True):
        for stage in range(3):
            rows.append({'stage':depth.stage_case(stage,independent),'stress':depth.stress(stage,independent)})
            print(json.dumps({'part':'stages','stage':stage,'accuracy':independent,'status':'passed'}),flush=True)
    require(all(not a for a in depth.failures.values()),'both cores preserve stage geometry freezes cadence and transfer/OBJ budgets',depth.failures)
    return {'cases':rows,'checks':depth.checks,'failure_arrays':depth.failures}

def candidate_stem(version):
    if version=='0.25.0':return 'pacing-floor-v025'
    if version=='0.26.0':return 'play-flow-v026'
    raise AssertionError(('Unreviewed pacing/floor fixture version',version))

def stage_main():
    return main(['--part','stages'])

def main(argv=None):
    global OUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--part',choices=('static','pacing','supers','cpu','stages'),required=True)
    parser.add_argument('--fighters',default=','.join(map(str,range(12))))
    parser.add_argument('--report',type=Path)
    args=parser.parse_args(argv);fighters=list(map(int,args.fighters.split(',')))
    require(bool(fighters) and len(set(fighters))==len(fighters) and all(i in range(12) for i in fighters),'roster selection is valid')
    manifest=json.loads((ROOT/'dist/manifest.json').read_bytes())
    stem=candidate_stem(manifest['version'])
    part_name='stage' if args.part=='stages' else args.part
    report_path=(ROOT/(args.report or Path(f'docs/{stem}-{part_name}-report.json'))).resolve()
    diagnostic=report_path.is_relative_to((ROOT/'build').resolve())
    require(diagnostic or fighters==list(range(12)),'partial roster evidence remains diagnostic under build')
    if diagnostic:OUT=report_path.parent/(report_path.stem+'-captures')
    elif manifest['version']=='0.26.0':OUT=ROOT/'docs/screenshots/play-flow-v026/pacing'
    OUT.mkdir(parents=True,exist_ok=True);report_path.parent.mkdir(parents=True,exist_ok=True)
    started=time.monotonic();manifest=json.loads((ROOT/'dist/manifest.json').read_bytes());before=inputs()
    report={'status':'failed','part':args.part,'version':manifest['version'],'rom_sha256':manifest['sha256'],
            'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'diagnostic':diagnostic,'selected_fighters':fighters,'host_contract':host_contract(),'source_sha256':before,
            'checks':[],'native_health':HEALTH,'memory_writes':False,'save_states':False,'audio_device_opened':False}
    try:
        require(manifest['version'] in ('0.25.0','0.26.0') and sha((ROOT/'dist/abaqus-after-hours.sfc').read_bytes())==manifest['sha256'],'candidate is the exact native cartridge retaining the v0.25 pacing contract')
        if not BEFORE.exists():
            BEFORE.parent.mkdir(parents=True,exist_ok=True)
            baseline=subprocess.check_output(['git','show',BASE+':dist/abaqus-after-hours.sfc'],cwd=ROOT)
            require(sha(baseline)==BASE_ROM,'committed before cartridge has the approved identity')
            BEFORE.write_bytes(baseline)
        require(sha(BEFORE.read_bytes())==BASE_ROM,'before measurements use the approved v0.24 cartridge')
        for path,pin in (('.tools/core/snes9x_libretro.dll',EXPECTED_NATIVE_CORE),
                         ('.tools/compat/bsnes_libretro.dll',EXPECTED_INDEPENDENT_CORE)):
            # Actual expanded emulator identity, not only a report constant.
            if 'bsnes' in path:
                from test_compatibility import CORE_PATH
                file=CORE_PATH
            else:file=ROOT/path
            require(sha(Path(file).read_bytes()).lower()==pin['dll_sha256'].lower(),'expanded native core is pinned',str(file))
        report['preservation']=validate(ROOT,allow_arena_previews=manifest['version']=='0.26.0')
        Emulator.run=monitored_run
        report['result']=({'static':lambda:report['preservation'],'pacing':lambda:pacing(fighters),
                           'supers':lambda:supers(fighters),'cpu':lambda:cpu(fighters),'stages':stages}[args.part])()
        require(inputs()==before,'production and harness inputs stayed stable throughout the run')
        require(not HEALTH['failures'],'strict native health contains no failure')
        report['status']='passed'
    except Exception as error:
        report['error']=repr(error)
        raise
    finally:
        Emulator.run=ORIGINAL_RUN
        report['checks']=list(CHECKS.values());report['check_count']=sum(r['executions'] for r in CHECKS.values())
        if args.part=='stages' and 'result' in report:
            report['check_count']+=len(report['result']['checks'])
        report['elapsed_seconds']=round(time.monotonic()-started,3)
        report_path.write_bytes((json.dumps(report,indent=2)+'\n').encode())
        print(json.dumps({k:report[k] for k in ('status','part','rom_sha256','check_count','elapsed_seconds')}),flush=True)
    return 0

if __name__=='__main__':raise SystemExit(main())
