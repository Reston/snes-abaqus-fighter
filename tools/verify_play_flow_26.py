"""Run every v0.26 native proof against one committed cartridge/source freeze.

The plan never changes source or Git history. It stages host build proofs
before native workers, retains every command/log/exit, stops scheduling after
a failure and lets active native writers finish. All mode reports are merged
and collated only after every required command succeeds.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED, as_completed
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import threading

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from candidate_sources import snapshot
from play_flow_counterfactual import prepare as prepare_reference


def require(ok,message):
    if not ok:raise RuntimeError(message)


def git(root,*args):
    return subprocess.check_output(['git',*args],cwd=root,text=True).strip()


def task(name,script,*args):
    return {'id':name,'arguments':['tools/'+script+'.py',*map(str,args)]}


def plan():
    host=[task('asset-build','test_stage_pipeline_26'),task('native-publication','test_native_build_26')]
    # These are intentionally independent of root asset/native publication.
    isolated=[task('fresh-build','test_fresh_build','--source-ref','<FREEZE>'),
              task('authoring','check_authoring_guards','--source-ref','<FREEZE>','--producer-ref','<FREEZE>')]
    jobs=[task('native-six','check_play_flow_native_26'),task('session-limit','test_session_limit_26'),
          task('cpu','test_pacing_floor_25','--part','cpu'),task('feedback','test_feedback_26')]
    jobs += [task('hour-'+str(mode),'test_play_flow_long_26','--mode',mode,'--report','<RUN>/hour-'+str(mode)+'.json') for mode in range(3)]
    jobs += [task('stress-'+str(group),'test_play_flow_stress_26','--fighters',*(range(group*3,group*3+3)),'--report','<RUN>/stress-'+str(group)+'.json','--resume') for group in range(4)]
    jobs += [task(part,'test_pacing_floor_25','--part',part) for part in ('pacing','supers')]
    jobs += [task(part,'test_play_flow_26','--part',part) for part in ('results','training','meter','arenas','arcade','manual','rounds')]
    jobs += [task(part,driver) for part,driver in (
        ('throw','test_throw_feedback_26'),('best','test_training_best_26'),('session','test_local_session_26'),
        ('normal-guide','test_normal_guide_26'),('confirm','test_confirm_26'),('music','test_music_26'),
        ('motion','test_motion_26'),('repeat','test_menu_repeat_26'),('previews','test_arena_preview_26'),
        ('roster','test_roster_hints_26'),('compatibility','test_compatibility'),('launcher','test_launcher_26'))]
    finish=[task('merge-stress','test_play_flow_stress_26','--merge',*('<RUN>/stress-'+str(i)+'.json' for i in range(4))),
            task('merge-hours','test_play_flow_long_26','--merge',*('<RUN>/hour-'+str(i)+'.json' for i in range(3))),
            task('collate','collate_play_flow_26','--source-freeze','<FREEZE>'),
            task('review','make_play_flow_review_26')]
    all_jobs=host+isolated+jobs+finish
    require(len({item['id'] for item in all_jobs})==len(all_jobs),'Verification plan repeats an id')
    return {'host':host,'isolated':isolated,'native':jobs,'finish':finish}


def expand(item,freeze,run):
    return {'id':item['id'],'arguments':[str(arg).replace('<FREEZE>',freeze).replace('<RUN>',run) for arg in item['arguments']]}


def available_pairs():
    if os.name=='nt':
        kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.GetCurrentProcess.restype=ctypes.c_void_p
        kernel.GetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_size_t),ctypes.POINTER(ctypes.c_size_t)]
        allowed,system=ctypes.c_size_t(),ctypes.c_size_t()
        require(kernel.GetProcessAffinityMask(kernel.GetCurrentProcess(),ctypes.byref(allowed),ctypes.byref(system))!=0,'Cannot query allowed verification processors')
        cpus=[i for i in range(ctypes.sizeof(ctypes.c_size_t)*8) if allowed.value&(1<<i)]
    elif hasattr(os,'sched_getaffinity'):cpus=sorted(os.sched_getaffinity(0))
    else:cpus=list(range(os.cpu_count() or 1))
    # Each worker gets a distinct pair whenever the caller allows enough.
    return [cpus[i:i+2] for i in range(0,len(cpus),2)]


def preflight(root,ref):
    freeze=git(root,'rev-parse','--verify','--end-of-options',ref+'^{commit}')
    require(Path(sys.executable).resolve()==(root/'.tools/python/python.exe').resolve(),'Run verification with the pinned project .tools/python/python.exe')
    require((root/'build').resolve()==root/'build','Verification logs must stay in the ordinary workspace build directory')
    require(freeze==git(root,'rev-parse','HEAD'),'Source ref must be current HEAD; commit the built inputs before verification')
    tracked=git(root,'diff','--name-only',freeze,'--','src','tools','assets','dist','Build.cmd','Test.cmd','Play.cmd')
    extra=git(root,'ls-files','--others','--exclude-standard','src','tools','assets','dist')
    require(not tracked and not extra,'Runtime/producer/build inputs differ from the committed source freeze')
    manifest=json.loads((root/'dist/manifest.json').read_bytes())
    require(manifest['version']=='0.26.0','This complete verification plan targets v0.26 only')
    image=(root/'dist/abaqus-after-hours.sfc').read_bytes()
    require(len(image)==4194304 and hashlib.sha256(image).hexdigest()==manifest['sha256'],'The current cartridge does not match its manifest')
    frozen=json.loads(subprocess.check_output(['git','show',freeze+':dist/manifest.json'],cwd=root))
    require(frozen==manifest,'Commit the exact built cartridge/manifest before verification')
    return freeze,manifest,snapshot(root)


def persist(path,value):
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_bytes((json.dumps(value,indent=2)+'\n').encode())
    for attempt in range(10):
        try:os.replace(temporary,path);return
        except PermissionError:
            if attempt==9:raise
            time.sleep(0.05)


def run_job(root,item,log_dir,processors):
    started=time.monotonic();path=log_dir/(item['id']+'.log');environment=dict(os.environ,ABAQUS_HEADLESS='1')
    command=[sys.executable,*item['arguments']]
    with path.open('wb') as output:
        flags=(0x08000000|0x4000) if os.name=='nt' else 0
        child=subprocess.Popen(command,cwd=root,stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,env=environment,creationflags=flags)
        if os.name=='nt' and processors:
            kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
            if not kernel.SetProcessAffinityMask(ctypes.c_void_p(int(child._handle)),sum(1<<cpu for cpu in processors)):
                # Do not terminate an already started native writer. Its exit is
                # retained, but a failed affinity setup is itself a failed gate.
                affinity_error=ctypes.get_last_error()
            else:affinity_error=None
        else:affinity_error=None
        code=child.wait()
    raw=path.read_bytes()
    result={'id':item['id'],'command':command,'exit_code':code,'affinity_error':affinity_error,
            'processors':processors,'elapsed_seconds':round(time.monotonic()-started,3),
            'log':path.relative_to(root).as_posix(),'log_sha256':hashlib.sha256(raw).hexdigest()}
    # A producer may itself write <id>.json (hour/stress shards do). Keep
    # command outcomes separate so publication never replaces native evidence.
    persist(log_dir/(item['id']+'.command.json'),result)
    return result


def pool(items,workers,execute,on_result):
    """No new work after failure; every already running future finishes."""
    results=[];pending={};next_index=0;failed=False
    with ThreadPoolExecutor(max_workers=workers) as executor:
        free=list(range(workers))
        while pending or (next_index<len(items) and not failed):
            while free and next_index<len(items) and not failed:
                slot=free.pop();item=items[next_index];next_index+=1;pending[executor.submit(execute,item,slot)]=(slot,item['id'])
            completed,_=wait(pending,return_when=FIRST_COMPLETED)
            for future in completed:
                slot,identity=pending.pop(future);free.append(slot)
                try:row=future.result()
                except Exception as error:row={'id':identity,'exit_code':-1,'error':repr(error)}
                results.append(row);on_result(row)
                failed=failed or row['exit_code']!=0 or row.get('affinity_error') is not None
    require(not failed,'One or more verification commands failed; completed/active results and logs were retained')
    require(len(results)==len(items),'Verification pool ended without all required commands')
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-ref',default='HEAD');parser.add_argument('--jobs',type=int,default=4);parser.add_argument('--dry-run',action='store_true');args=parser.parse_args()
    require(1<=args.jobs<=8,'Use one to eight native workers')
    graph=plan()
    if args.dry_run:print(json.dumps({'status':'plan-only','gui_opened':False,'plan':graph},indent=2));return
    require(os.name=='nt','The complete current build/proof plan uses the Windows x64 project toolchain')
    freeze,manifest,sources=preflight(ROOT,args.source_ref);pairs=available_pairs();workers=min(args.jobs,len(pairs));require(workers>0,'No allowed verification processors')
    selected=pairs[-workers:];stamp=time.strftime('%Y%m%d-%H%M%S');folder=ROOT/'build'/('verify-v026-'+freeze[:8]+'-'+stamp);folder.mkdir();relative=folder.relative_to(ROOT).as_posix()
    report={'status':'failed','version':manifest['version'],'rom_sha256':manifest['sha256'],'source_commit':freeze,'source_sha256':sources,'workers':workers,'processors':selected,'commands':[],'source_changed':False}
    lock=threading.Lock()
    def keep(row):
        with lock:
            report['commands'].append(row);persist(folder/'execution.json',report);print(json.dumps(row),flush=True)
    def execute(item,slot):return run_job(ROOT,expand(item,freeze,relative),folder,selected[slot])
    try:
        prepare_reference(ROOT)
        def root_publication():
            for item in graph['host']:
                row=execute(item,0);keep(row);require(row['exit_code']==0 and row.get('affinity_error') is None,'Host publication proof failed')
            return None
        with ThreadPoolExecutor(max_workers=min(workers,3)) as executor:
            host_futures=[executor.submit(root_publication)]
            for index,item in enumerate(graph['isolated']):
                slot=min(index+1,workers-1)
                host_futures.append(executor.submit(execute,item,slot))
            errors=[]
            for future in as_completed(host_futures):
                try:
                    row=future.result()
                    if row is not None:keep(row);require(row['exit_code']==0 and row.get('affinity_error') is None,'Isolated host proof failed')
                except Exception as error:errors.append(repr(error))
            require(not errors,'Host proof failure(s): '+str(errors))
        baseline=ROOT/'build/v026-arcade-lag/before/record.json'
        if not baseline.exists():
            row=execute(task('original-hour-reference','test_play_flow_long_26','--baseline','--report',baseline.relative_to(ROOT).as_posix()),0);keep(row);require(row['exit_code']==0,'Historical comparison reference could not be reproduced')
        pool(graph['native'],workers,execute,keep)
        require(snapshot(ROOT)==sources and git(ROOT,'rev-parse','HEAD')==freeze,'Verification source changed while native commands ran')
        for item in graph['finish']:
            row=execute(item,0);keep(row);require(row['exit_code']==0 and row.get('affinity_error') is None,'Final merge/collation/review command failed')
        require(snapshot(ROOT)==sources,'Verification changed its own source inputs');report['status']='passed'
    except Exception as error:report['error']=repr(error);report['source_changed']=snapshot(ROOT)!=sources;raise
    finally:
        persist(folder/'execution.json',report);print(json.dumps({'status':report['status'],'execution':(folder/'execution.json').relative_to(ROOT).as_posix(),'rom_sha256':manifest['sha256']}),flush=True)

if __name__=='__main__':main()
