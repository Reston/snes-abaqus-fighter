"""Collect independently produced current-cartridge evidence; never run emulation."""
import hashlib
import json
from pathlib import Path
import subprocess
import argparse
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from expansion_contracts import combined_contract

ROOT=Path(__file__).resolve().parents[1]
SIX=('test-report.json','character-test-report.json','presentation-test-report.json','input-test-report.json','stage-test-report.json','training-test-report.json')

def require(ok,message):
    if not ok: raise RuntimeError(message)

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def collect(source_freeze: str):
    manifest=json.loads((ROOT/'dist/manifest.json').read_text(encoding='utf-8'))
    sha=digest(ROOT/'dist/abaqus-after-hours.sfc')
    require(manifest['sha256']==sha,'Manifest does not match current ROM')
    require(manifest['version']=='0.22.0','Expected combined v0.22.0 ROM')
    records={}
    for name in (*SIX,'compatibility-test-report.json',*(f'expansion-{i:02d}-report.json' for i in range(1,11))):
        path=ROOT/'docs'/name
        require(path.is_file(),'Missing '+name)
        value=json.loads(path.read_text(encoding='utf-8'))
        recorded_sha=value.get('rom_sha256',value.get('rom',{}).get('sha256'))
        require(recorded_sha==sha,name+' was not produced from combined ROM')
        checks=value.get('checks')
        if name=='compatibility-test-report.json':
            require(value.get('status')=='passed' and value.get('errors')==[],name+' did not pass')
            require(checks.get('cadence',{}).get('passed') is True,name+' cadence did not pass')
            require(value.get('host_contract',{}).get('audio_device_opened') is False,name+' audio playback contract missing')
            require(value['host_contract'].get('emulated_memory_writes')==0 and value['host_contract'].get('savestate_calls')==0,name+' controller-only contract missing')
            records[name]={'path':'docs/'+name,'sha256':digest(path),'check_groups':len(checks)}
            continue
        if name=='expansion-06-report.json':
            # CPU proof counts every monitored callback but retains compact
            # summaries and per-case trace hashes instead of repeating every
            # successful frame assertion in the JSON.
            require(value.get('status')=='passed' and value.get('failures')==[] and
                    value.get('cadence_failures')==[],name+' has native failures')
            require(isinstance(checks,int) and checks>100000 and
                    value.get('passed_checks')==checks and value.get('failed_checks')==0,
                    name+' counted assertions did not all pass')
            summary=value.get('summary_checks')
            require(isinstance(summary,list) and summary and
                    all(row.get('passed') is True for row in summary),name+' summary did not pass')
            require({(c.get('cpu'),c.get('difficulty')) for c in value.get('cases',[])}==
                    {(cpu,d) for cpu in range(12) for d in range(3)},name+' lacks full CPU matrix')
            require(len(value.get('p2_noise_replays',[]))==12,name+' lacks all-roster ignored-pad replays')
            records[name]={'path':'docs/'+name,'sha256':digest(path),'checks':checks,
                           'retained_summary_checks':len(summary)}
            continue
        if name=='expansion-07-report.json':
            require(value.get('status')=='passed' and isinstance(checks,int) and checks>=2000,
                    name+' counted super assertions did not pass')
            require(value.get('rom_sha256_after')==sha and
                    value.get('controller_only') is True and value.get('memory_writes') is False and
                    value.get('save_states') is False,name+' native execution contract changed')
            timing=value.get('timing',{})
            require(timing.get('frames',0)>=30000 and timing.get('cadence_failures')==[] and
                    timing.get('overflow_failures')==[],name+' has native timing failures')
            require(len(value.get('activation',[]))==12 and
                    all(len(value.get(key,[]))==24 for key in ('hits','blocks','whiffs','interruptions')),
                    name+' lacks all-roster and both-port coverage')
            for capture in value.get('captures',[]):
                require(digest(ROOT/capture['path'])==capture['sha256'],name+' capture changed')
            records[name]={'path':'docs/'+name,'sha256':digest(path),'checks':checks}
            continue
        require(isinstance(checks,list) and checks,name+' has no recorded checks')
        require(all(isinstance(row,dict) and row.get('passed') is True for row in checks),name+' has failed or malformed checks')
        if name in SIX:
            require(value.get('passed')==len(checks),name+' count does not match recorded checks')
            if 'status' in value: require(value['status']=='passed',name+' did not pass')
        else:
            require(value.get('status')=='passed',name+' did not pass')
        records[name]={'path':'docs/'+name,'sha256':digest(path),'checks':len(checks)}
    state=json.loads((ROOT/'docs/expansion-prs-v0.22.0.json').read_text(encoding='utf-8'))
    prs=state['feature_prs']
    require(len(prs)==10,'Not all ten feature PRs are recorded')
    require(all(x.get('merged') is True for x in prs.values()),'Not all ten feature PRs are merged into integration')
    frozen=subprocess.check_output(['git','rev-parse',source_freeze+'^{commit}'],cwd=ROOT,text=True).strip()
    require(subprocess.run(['git','merge-base','--is-ancestor',frozen,'HEAD'],cwd=ROOT).returncode==0,
            'Source freeze is not an ancestor of current checkout')
    source_tree=subprocess.check_output(['git','rev-parse',frozen+'^{tree}'],cwd=ROOT,text=True).strip()
    contract=combined_contract(ROOT)
    frozen_rom=subprocess.check_output(['git','show',frozen+':dist/abaqus-after-hours.sfc'],cwd=ROOT)
    require(hashlib.sha256(frozen_rom).hexdigest()==sha,'Frozen cartridge differs from current cartridge')
    for name in ('authoring-guards-report.json','fresh-build-test-report.json'):
        path=ROOT/'docs'/name
        value=json.loads(path.read_text(encoding='utf-8'))
        require(value.get('status')=='passed' and value.get('rom_sha256')==sha and
                value.get('source_commit')==frozen,name+' is not a passing current-source record')
        if name=='fresh-build-test-report.json':
            require(value.get('source_tree')==source_tree and value.get('rebuilt_rom_sha256')==sha and
                    value.get('generated_assets_verified')==219 and
                    value.get('symbols_equal_after_source_path_normalization') is True,
                    name+' does not reproduce cartridge, assets and symbols')
        else:
            runs=value.get('runs',[])
            require(len(runs)==2 and {row.get('optimized') for row in runs}=={False,True} and
                    all(row.get('exit_code')==0 and row.get('tests')==20 for row in runs),
                    name+' lacks normal and optimized mutation checks')
        records[name]={'path':'docs/'+name,'sha256':digest(path)}
    inputs={}
    paths=sorted(set(subprocess.check_output(['git','ls-files','src','tools'],cwd=ROOT,text=True).splitlines()))
    for name in paths:
        path=ROOT/name
        if path.suffix not in {'.c','.h','.asm','.py','.ps1'}: continue
        current=path.read_bytes().replace(b'\r\n',b'\n')
        baseline=subprocess.check_output(['git','show',frozen+':'+name],cwd=ROOT).replace(b'\r\n',b'\n')
        require(current==baseline,'Source or test changed after freeze: '+name)
        inputs[name]=hashlib.sha256(current).hexdigest()
    report={'status':'passed','version':'0.22.0','rom_sha256':sha,'checksum':manifest['checksum'],
            'source_commit':frozen,'source_tree':source_tree,'source_sha256':inputs,
            'native_contract':{'generated_count':contract['assets']['generated_count'],
                               'preserved_generated':contract['assets']['preserved_generated'],
                               'changed_generated':contract['assets']['changed_generated'],
                               **contract['native']},
            'native_six_suite_checks':sum(records[name]['checks'] for name in SIX),
            'evidence':records,'feature_prs':prs,'integration_pr':state['final_pr'],
            'scope':'All ten integrated features, six native suites, independent emulator smoke, source-authoring mutations and fresh export on one exact cartridge',
            'public_release_certified':False,'full_offline_release_evidence_regenerated':False,
            'human_review_of_combined_revision':None}
    out=ROOT/'docs/expansion-v0.22.0-verification.json'
    out.write_bytes((json.dumps(report,indent=2)+'\n').encode('utf-8'))
    print(json.dumps({'path':str(out),'rom_sha256':sha,'six_checks':report['native_six_suite_checks'],'feature_checks':sum(records[f'expansion-{i:02d}-report.json']['checks'] for i in range(1,11))}))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-freeze',required=True)
    collect(parser.parse_args().source_freeze)
