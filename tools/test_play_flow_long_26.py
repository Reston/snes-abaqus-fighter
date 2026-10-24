"""Strict continuous native hours for the current four-button cartridge.

The older endurance producer's health predicates remain unchanged. This gate
uses current four-face-button coverage, explicit settled roster publication
and actual arena-relative rotation. To regenerate a missing original comparison reference, use --baseline --report
build/v026-arcade-lag/before/record.json. Each --mode N run writes a private
report under build; --merge combines all three. Champion routing is covered
separately by the focused Arcade proof; it is not required of this traffic policy in an hour.
"""
import argparse
import ctypes as C
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import test_endurance as native
from candidate_sources import snapshot
from test_champion import host_contract
from play_flow_media import inventory

BASE='41b2c7e27b9c63c54a2b0864db206f1c7a06a95f'
BASE_ROM='6b392d161e28578169f0a4536f740d961c223881d3099ec79d20a37a66603531'
HEAD=struct.Struct('<6H2BH')
RANGES=[('fighters',128),('waves',32),('randomseed',2),('cpuTick',1),('difficulty',1),('trainingDummy',1),('mode',1),('pad0',2),('pad1',2),('edge0',2),('edge1',2),('rearKickRecoil',1)]+[(n,2) for n in ('superActive','superRequest','superPhase','superNext','superContactEnd','superWaveDamage','superWaveReach','fightClock')]+[(n,1) for n in ('paused','intro','roundEnd','hitstop','winner','roundNumber','seconds','secondTick','arcade')]
ROW_BYTES=HEAD.size+sum(size for _,size in RANGES)


def sha(raw):return hashlib.sha256(raw).hexdigest()
def require(ok,message):
    if not ok:raise RuntimeError(message)


def publications(path):
    rows={};epoch=0;previous=None;prior=None;callbacks=0;repeats=0;faults=[]
    with gzip.open(path,'rb') as stream:
        while True:
            raw=stream.read(ROW_BYTES)
            if not raw:break
            require(len(raw)==ROW_BYTES,'Truncated unmasked native stream')
            p1,p2,frame,trace,lag,vblank,screen,direct,magic=HEAD.unpack(raw[:HEAD.size]);blob=raw[HEAD.size:];callbacks+=1
            if previous is not None and frame<previous and previous-frame>32768:epoch+=65536
            previous=frame
            if magic==0xaaba and frame==trace and screen==direct:
                key=epoch+frame
                if key in rows:repeats+=1
                else:rows[key]=(p1,p2,screen,direct,blob)
            if prior is not None:
                oldframe,oldlag,oldscreen,olddirect,oldblob=prior
                if screen==direct==oldscreen==olddirect==3 and frame==oldframe and ((lag-oldlag)&65535):
                    faults.append({'callback':callbacks,'frame':frame,'lag_delta':(lag-oldlag)&65535,'unmasked_bytes_identical':blob==oldblob})
            prior=(frame,lag,screen,direct,blob)
    require(rows,'No coherent native publications')
    return rows,{'callbacks':callbacks,'logical_frames':len(rows),'additional_publications':repeats,'live_lag_callbacks':faults,'first':min(rows),'last':max(rows)}


def compare_streams(before_path,after_path):
    before,old=publications(before_path);after,new=publications(after_path)
    require(min(before)==min(after) and max(after)>=max(before),'Candidate stream does not cover the full baseline logical span')
    require(max(after)-max(before)<=sum(row['lag_delta'] for row in old['live_lag_callbacks']),'Candidate trailing span exceeds the retained baseline repeats')
    first=min(before);last=max(before)
    oldkeys={k for k in before if first<=k<=last};newkeys={k for k in after if first<=k<=last}
    require(oldkeys==newkeys,'Logical publication frame sets differ inside the shared closed span')
    require(not new['live_lag_callbacks'] and new['additional_publications']==0,'Current native stream contains a repeated candidate publication')
    differences=[k for k in sorted(oldkeys) if before[k]!=after[k]]
    require(not differences,'Unmasked gameplay/input state differs at logical frames '+str(differences[:8]))
    return {'status':'passed','comparison':'first coherent TRACE==native publication; shared closed logical span; every raw byte/input unmasked',
            'baseline':old,'candidate':new,'logical_span':[first,last],'compared_logical_frames':len(oldkeys),
            'candidate_collapsed_callbacks':0,'state_byte_differences':0,'baseline_stream_sha256':sha(Path(before_path).read_bytes()),'candidate_stream_sha256':sha(Path(after_path).read_bytes())}


def current_coverage(mode,result,target):
    events=result['events'];counts=result['normal_action_starts']
    require(result['status']=='passed' and result['mode']==mode,'Native hour mode/status differs')
    require(result['stable_fight_lag_increments']==0 and all(not result[k] for k in ('cadence_failures','native_timing_failures','ambient_failures','spc_fifo_failures','ppu_overflow_frames')),'Native hour contains a health failure')
    require(result['max_spc_backlog']<=6 and result['audio_samples']>0 and 0<result['audio_peak_sampled']<32767 and result['video_geometry']==[256,224],'Native hour exceeds PCM/OBJ/FIFO scope')
    coverage={'four_face_normals':all(counts[str(a)]>0 for a in (1,3,4,5)),
              'all_three_stages':set(result['stages'])=={0,1,2},
              'one_live_hour':result['live_frames']>=target,
              'one_continuous_core':result['core_boots']==1 and result['core_unloads']==1 and result['core_reboots']==0,
              'real_combat':all(events[name]>0 for name in ('attack','air','throw','guard','special','down','wake','real_contact','damage'))}
    if mode==0:coverage['ladder_progress']=events['arcade_ladder']>0
    else:coverage['real_roster_roundtrips']=events['menu_roster']>=3
    if mode==2:
        coverage.update(cpu_live_hour=result['training_cpu_live_frames']>=target,
                        all_twelve_cpus={row['fighter2'] for row in result['rosters']}==set(range(12)),training_resets=events['reset']>0)
    require(all(coverage.values()),'Current four-button/route hour coverage is incomplete: '+str(coverage))
    return coverage


def run_case(mode,folder,baseline=False):
    folder.mkdir(parents=True,exist_ok=True);events=[];initial=None;recording=False;callbacks=0
    table={name:int(address,16)&0x1ffff for address,name in re.findall(r'^([0-9A-Fa-f]{8}) (\S+)$',(ROOT/'dist/abaqus-after-hours.sym').read_text(),re.M)}
    original_run=native.LongRunHost.run;original_loaded=native.assert_loaded_state
    original_roster=native.roster_transition;original_mode_report=native.MODE_REPORT
    original_init=native.LongRunHost.__init__;original_identity=native.rom_identity
    if baseline:
        require(mode==0,'The historical reference is the fixed original Arcade hour')
        image=subprocess.check_output(['git','show',BASE+':dist/abaqus-after-hours.sfc'],cwd=ROOT);require(sha(image)==BASE_ROM,'Historical reference cartridge differs')
        baseline_path=folder/'baseline.sfc';baseline_path.write_bytes(image)
        def init(host,*args,**kwargs):kwargs['rom']=baseline_path;original_init(host,*args,**kwargs)
        native.LongRunHost.__init__=init;native.rom_identity=lambda:(BASE_ROM,len(image))
    stream_path=folder/'mode0-states.bin.gz';writer=gzip.GzipFile(filename=str(stream_path),mode='wb',compresslevel=1,mtime=0) if mode==0 else None
    def raw(host):return b''.join(C.string_at(host.ram+table[name],size) for name,size in RANGES)
    def loaded(state,game_mode,fighter,other,stage,label):
        nonlocal recording
        original_loaded(state,game_mode,fighter,other,stage,label)
        if label=='initial':recording=True
    def run(host,count=1,p1=(),p2=()):
        nonlocal initial,callbacks
        for _ in range(int(count)):
            if writer and recording and initial is None:initial={'state':host.state(),'raw':raw(host).hex()}
            state=original_run(host,1,p1,p2)
            if writer and recording:
                import longrun_host
                masks=[sum(1<<longrun_host.BUTTONS[key] for key in keys) for keys in (p1,p2)]
                frame=int.from_bytes(C.string_at(host.ram+table['frame'],2),'little')
                writer.write(HEAD.pack(*masks,frame,state['frame'],state['lag_frame_counter'],state['snes_vblank_count'],state['screen'],state['native_screen'],state['magic'])+raw(host));callbacks+=1
        return state
    def roster(host,runner,game_mode,fighter,other,stage):
        state=host.state();require(native.screen_ready(state,3) and not state['paused'],'Roster route must begin in live play')
        stage=(state['arena']+1)%3
        native.tracked_pulse(host,runner,'start');require(host.state()['paused']==1,'Start must pause the current match')
        native.tracked_pulse(host,runner,'b');before=host.state();require(before['native_screen']==1,'Back must change the direct scene on its first pulse')
        waited=0
        while not native.screen_ready(host.state(),1):
            require(waited<32,'Roster publication exceeded its bounded neutral wait');native.tracked_step(host,runner);waited+=1
        events.append({'before_trace':before['screen'],'before_native':before['native_screen'],'neutral_callbacks':waited,'after_trace':host.state()['screen'],'after_native':host.state()['native_screen']})
        state=native.select_from_menu(host,runner,game_mode,fighter,other,stage);native.assert_loaded_state(state,game_mode,fighter,other,stage,'pause-b-select')
        runner.events['menu_roster']+=1;runner.rosters.append({'fighter1':fighter,'fighter2':other,'stage':stage,'route':'pause-b-select'});runner.stages.add(stage)
        return native.select_training_cpu(host,runner) if game_mode==2 else state
    native.LongRunHost.run=run;native.assert_loaded_state=loaded;native.roster_transition=roster;native.MODE_REPORT=folder/'failed-mode{mode}.json'
    timing=native.LongRunHost(video_interval=120);target=math.ceil(timing.video_fps*3600);timing.close()
    try:
        try:result=native.run_mode(mode,target,benchmark=False,coverage_required=False)
        except Exception:
            if not baseline:raise
            failed=folder/'failed-mode0.json';require(failed.exists(),'Original reference did not retain its native failure report');result=json.loads(failed.read_bytes())
    finally:
        if writer:writer.close()
        native.LongRunHost.run=original_run;native.assert_loaded_state=original_loaded;native.roster_transition=original_roster;native.MODE_REPORT=original_mode_report
        native.LongRunHost.__init__=original_init;native.rom_identity=original_identity
    if baseline:
        _,stats=publications(stream_path);require(result['status']=='failed' and len(result['cadence_failures'])==len(result['native_timing_failures'])==1 and len(stats['live_lag_callbacks'])==1 and stats['live_lag_callbacks'][0]['unmasked_bytes_identical'],'The original rare-lag reference was not reproduced exactly')
        return {'status':'historical-reference-failed','rom_sha256':BASE_ROM,'compiled_source_commit':BASE,'native':result,'callbacks':callbacks,'ranges':RANGES,'row_bytes':ROW_BYTES,'stream_path':stream_path.relative_to(ROOT).as_posix(),'stream_sha256':sha(stream_path.read_bytes()),'initial':initial}
    row={'mode':mode,'native':result,'coverage':current_coverage(mode,result,target),'legacy_six_button_champion_completeness_claimed':False,'roster_publication_waits':events}
    if mode==0:
        baseline=ROOT/'build/v026-arcade-lag/before/record.json';require(baseline.exists(),'Retain or regenerate the documented 6b392d original hour reference')
        reference=json.loads(baseline.read_bytes());require(reference['rom_sha256']==BASE_ROM and reference['row_bytes']==ROW_BYTES and reference['ranges']==[list(item) for item in RANGES],'Original Arcade comparison identity/layout differs')
        require(reference['native']['harness_sha256']==native.harness_identity() and reference['native']['core']==result['core'],'Original hour host/core differs')
        require(sha(subprocess.check_output(['git','show',BASE+':dist/abaqus-after-hours.sfc'],cwd=ROOT))==BASE_ROM,'Original native source freeze differs')
        before_path=ROOT/reference['stream_path'];require(sha(before_path.read_bytes())==reference['stream_sha256'],'Original source stream changed')
        row['comparison']=compare_streams(before_path,stream_path)
        require(len(row['comparison']['baseline']['live_lag_callbacks'])==1 and row['comparison']['baseline']['live_lag_callbacks'][0]['unmasked_bytes_identical'],'Original rare lag must stay explicit in the reference')
        row['stream']={'path':stream_path.relative_to(ROOT).as_posix(),'sha256':sha(stream_path.read_bytes()),'callbacks':callbacks,'row_bytes':ROW_BYTES,'initial':initial}
        row['baseline_reference']={'path':baseline.relative_to(ROOT).as_posix(),'sha256':sha(baseline.read_bytes()),'rom_sha256':BASE_ROM,'source_commit':BASE}
    return row


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--mode',type=int,choices=(0,1,2));parser.add_argument('--report',type=Path);parser.add_argument('--merge',type=Path,nargs='+');parser.add_argument('--baseline',action='store_true',help='Regenerate the retained known-failing original Arcade reference from Git');args=parser.parse_args()
    require(args.merge or args.mode is not None or args.baseline,'Select a native hour or merge all three completed modes')
    if args.baseline:args.mode=0
    path=(ROOT/(args.report or Path('docs/play-flow-v026-long-session-report.json'))).resolve();require(args.merge or path.is_relative_to(ROOT/'build'),'Single-mode hour evidence must remain diagnostic')
    require(not args.baseline or not path.exists(),'Retain the old reference; choose a fresh output for a new baseline run')
    path.parent.mkdir(parents=True,exist_ok=True);started=time.monotonic();sources=snapshot(ROOT);manifest=json.loads((ROOT/'dist/manifest.json').read_bytes());commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();checks=[]
    report={'status':'failed','version':manifest['version'],'rom_sha256':manifest['sha256'],'source_commit':commit,'source_sha256':sources,'host_contract':host_contract(),'controller_only':True,'memory_writes':False,'save_states':False,'native_execution':True,'diagnostic':not bool(args.merge),'checks':checks,'cases':[]}
    try:
        require(sha((ROOT/'dist/abaqus-after-hours.sfc').read_bytes())==manifest['sha256'],'Long-session cartridge and manifest differ');report['core']=native.core_identity()
        if args.merge:
            merged={}
            for part in args.merge:
                data=json.loads((ROOT/part).read_bytes());require(data['status']=='passed' and data['rom_sha256']==manifest['sha256'] and data['source_sha256']==sources and data['source_commit']==commit,'Stale or failed native-hour shard')
                for row in data['cases']:require(row['mode'] not in merged,'Duplicated hour mode');merged[row['mode']]=row
            require(set(merged)=={0,1,2},'Exactly three full native hour modes are required');report['cases']=[merged[i] for i in range(3)]
        else:
            signature=sha(json.dumps(sources,sort_keys=True).encode())[:12];folder=ROOT/'build/v026-long'/signature/('baseline-'+sha(str(path).encode())[:8] if args.baseline else str(args.mode));report['cases']=[run_case(args.mode,folder,args.baseline)]
            if args.baseline:
                report.update(report['cases'][0]);report['producer_source_commit']=commit;return
        for row in report['cases']:
            require(row['native']['status']=='passed' and row['native']['rom_sha256']==manifest['sha256'],'Native hour reports another cartridge')
            coverage=current_coverage(row['mode'],row['native'],math.ceil(row['native']['video_fps']*3600));require(coverage==row['coverage'],'Current hour coverage fields differ')
            checks.append({'check':'mode '+str(row['mode'])+' retains strict native health and complete current four-button hour coverage','passed':True})
        require(snapshot(ROOT)==sources,'Long-session producer/runtime source changed');report['captures']=inventory(ROOT,'long-session');report['status']='passed'
    except Exception as error:report['error']=repr(error);raise
    finally:
        report['check_count']=len(checks);report['elapsed_seconds']=round(time.monotonic()-started,3);path.write_bytes((json.dumps(report,indent=2)+'\n').encode());print(json.dumps({k:report[k] for k in ('status','check_count','elapsed_seconds')}),flush=True)

if __name__=='__main__':main()
