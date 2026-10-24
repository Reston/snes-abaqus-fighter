"""Bind v0.25 playtest evidence to one frozen native cartridge."""
import argparse,ast,hashlib,itertools,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from v025_contracts import validate,canonical
from release_evidence import EXPECTED_INDEPENDENT_CORE
from collate_combat_24 import failure_arrays,media_files
SIX=('test-report.json','character-test-report.json','presentation-test-report.json',
     'input-test-report.json','stage-test-report.json','training-test-report.json')
FOCUSED={p:f'pacing-floor-v025-{p}-report.json' for p in ('pacing','supers','cpu','stage')}
def require(ok,message):
    if not ok:raise RuntimeError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def read(path):return json.loads((ROOT/path).read_bytes())
def count(report):
    rows=report['checks']
    require(rows and all(row.get('passed') is True for row in rows),'Failed or empty assertion inventory')
    executions=[row.get('executions',1) for row in rows]
    require(all(isinstance(n,int) and not isinstance(n,bool) and n>0 for n in executions),'Assertion execution count must be positive')
    total=sum(executions)
    if report.get('part')=='stages':
        extra=report['result']['checks']
        require(extra and all(row.get('passed') is True for row in extra),'Failed stage oracle checks')
        total+=len(extra)
    require(report.get('passed',total)==total and report.get('check_count',total)==total,'Assertion count differs')
    return total
def collect(source_ref):
    manifest=read('dist/manifest.json');rom=sha((ROOT/'dist/abaqus-after-hours.sfc').read_bytes())
    require(manifest['version']=='0.25.0' and manifest['sha256']==rom,'Wrong current cartridge')
    freeze=git('rev-parse',source_ref+'^{commit}').decode().strip();git('merge-base','--is-ancestor',freeze,'HEAD')
    require(json.loads(git('show',freeze+':dist/manifest.json'))==manifest,'Frozen manifest differs')
    require(sha(git('show',freeze+':dist/abaqus-after-hours.sfc'))==rom,'Frozen ROM differs')
    dirty=git('diff','--name-only',freeze,'--','src','tools','assets','dist').decode().splitlines()
    extra=git('ls-files','--others','--exclude-standard','src','tools','assets','dist').decode().splitlines()
    require(not dirty and not extra,'Source/test inputs changed after freeze: '+str(dirty+extra))
    tree=git('rev-parse',freeze+'^{tree}').decode().strip()
    sources={n:sha(canonical(n,(ROOT/n).read_bytes())) for n in git('ls-files','src','tools').decode().splitlines()
             if Path(n).suffix in ('.py','.h','.c','.asm','.ps1')}
    preservation=validate(ROOT);records={};media={}
    for name in (*SIX,*FOCUSED.values(),'compatibility-test-report.json','fresh-build-test-report.json','authoring-guards-report.json'):
        path='docs/'+name;report=read(path)
        require(report.get('rom_sha256',report.get('rom',{}).get('sha256'))==rom,'Stale evidence: '+name)
        # The original gameplay suite writes its complete report only after
        # success and has no status field; its counted checks are mandatory.
        require(report.get('status','passed' if name=='test-report.json' else None)=='passed',
                'Failed evidence: '+name);failure_arrays(report,name)
        checks=count(report) if name in (*SIX,*FOCUSED.values()) else None
        if name in FOCUSED.values():
            require(report.get('source_commit')==freeze and report.get('diagnostic') is False,'Noncanonical focused proof: '+name)
            require(report['selected_fighters']==list(range(12)) and report['preservation']==preservation,'Focused roster/preservation differs')
            require(report.get('memory_writes') is False and report.get('save_states') is False and
                    report.get('audio_device_opened') is False,'Focused native observation contract differs')
            require(all(sources.get(n)==h for n,h in report['source_sha256'].items()),'Focused producer dependencies differ')
        if name=='compatibility-test-report.json':
            require(report.get('pinned_core') is True and report['checks']['cadence']['passed'] is True and
                    report['core']['dll_sha256'].lower()==EXPECTED_INDEPENDENT_CORE['dll_sha256'],'Independent pinned cadence proof differs')
        if name=='fresh-build-test-report.json':
            require(report['source_commit']==freeze and report['source_tree']==tree and report['rebuilt_rom_sha256']==rom and
                    report['generated_assets_verified']==226 and report['symbols_equal_after_source_path_normalization'] is True,
                    'Fresh export does not reproduce the frozen cartridge')
            require(len(report['generated_assets'])==226,'Fresh inventory differs')
            for row in report['generated_assets']:
                require(sha(canonical(row['file'],(ROOT/row['file']).read_bytes()))==row['sha256'],'Fresh payload differs: '+row['file'])
        if name=='authoring-guards-report.json':
            require(report['source_commit']==freeze,'Authoring source freeze differs')
            parsed=ast.parse((ROOT/'tools/test_authoring_guards.py').read_text(encoding='utf-8'))
            tests=sum(isinstance(n,ast.FunctionDef) and n.name.startswith('test_') for cls in parsed.body if isinstance(cls,ast.ClassDef) for n in cls.body)
            runs=report['runs']
            require(len(runs)==2 and {r['optimized'] for r in runs}=={False,True} and
                    all(r['exit_code']==0 and r['tests']==tests and r['output'].rstrip().endswith('OK') for r in runs),
                    'Authoring mutations lack both interpreter modes')
        media_files(report,media);records[name]={'path':path,'sha256':sha((ROOT/path).read_bytes()),'checks':checks}
    pacing=read('docs/'+FOCUSED['pacing'])['result']
    require([(r['after']['fighter'],r['after']['port']) for r in pacing]==list(itertools.product(range(12),range(2))),
            'Pacing proof does not cover all twelve fighters and both ports')
    require(all(r['crossing']['crossed_airborne'] and r['crossing']['landed'] for r in pacing),'Incomplete crossing proof')
    supers=read('docs/'+FOCUSED['supers'])['result']
    require([(r['fighter'],r['port'],r['guard']) for r in supers]==list(itertools.product(range(12),range(2),(False,True))),
            'Super hit/guard inventory differs')
    cpu=read('docs/'+FOCUSED['cpu'])['result']
    for phase in ('before','after'):
        require([(r['cpu'],r['difficulty']) for r in cpu[phase]]==list(itertools.product(range(12),range(3))),'CPU difficulty inventory differs')
    require(len(cpu['hard_replays'])==12 and cpu['pressure']['after']<cpu['pressure']['before'],'CPU pressure/replay proof differs')
    stages=read('docs/'+FOCUSED['stage']);require(len(stages['result']['cases'])==6,'Stage proof lacks both cores')
    shared=read('docs/stage-test-report.json')
    require(shared.get('shared_native_execution') is True and shared['focused_report']=='docs/'+FOCUSED['stage'] and
            shared['focused_report_sha256']==records[FOCUSED['stage']]['sha256'],'Shared/focused stage execution differs')
    result={'status':'passed','scope':'Native pacing and detailed-floor playtest candidate; no offline package',
            'version':manifest['version'],'rom_sha256':rom,'checksum':manifest['checksum'],
            'source_commit':freeze,'source_tree':tree,'source_sha256':sources,
            'native_six_suite_checks':sum(records[n]['checks'] for n in SIX),
            'focused_checks':{p:records[n]['checks'] for p,n in FOCUSED.items()},
            'shared_stage_and_focused_execution':True,'preservation':preservation,'evidence':records,
            'cpu_pressure':cpu['pressure'],'damian_before_after':pacing[0],
            'review_media_sha256':media,'human_playtest_approved':None,
            'public_release_certified':False,'full_offline_package_regenerated':False}
    (ROOT/'docs/verification-v0.25.0.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    print(json.dumps({k:result[k] for k in ('status','rom_sha256','native_six_suite_checks','focused_checks','cpu_pressure')}))
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-freeze',required=True)
    collect(parser.parse_args().source_freeze)
