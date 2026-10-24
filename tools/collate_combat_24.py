"""Bind the six-feature playtest evidence to one frozen native cartridge."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from expansion_contracts import combined_contract
from check_combat_24_guards import SUITES
from release_evidence import EXPECTED_INDEPENDENT_CORE

SIX=('test-report.json','character-test-report.json','presentation-test-report.json',
     'input-test-report.json','stage-test-report.json','training-test-report.json')
FEATURES={'pacing':'combat-24-pacing-report.json','attacks':'combat-24-attack-report.json',
          'contacts':'combat-24-contact-report.json','stages':'combat-24-stage08-report.json',
          'jumps':'combat-24-jumps-report.json','supers':'combat-24-super-report.json'}


def require(ok,message):
    if not ok:raise RuntimeError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(name):return json.loads((ROOT/name).read_bytes())
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def canonical(name,raw):
    return raw.replace(b'\r\n',b'\n') if Path(name).suffix.lower() in ('.py','.ps1','.asm','.h','.c','.json','.md','.txt') else raw


def failure_arrays(value,location):
    if isinstance(value,dict):
        for key,item in value.items():
            if key.endswith('failures') or key in ('errors','failure_arrays'):
                empty=all(not x for x in item.values()) if isinstance(item,dict) else not item
                require(empty,location+' contains '+key)
            failure_arrays(item,location+'/'+key)
    elif isinstance(value,list):
        for item in value:failure_arrays(item,location)


def media_files(value,media):
    if isinstance(value,dict):
        path=value.get('path');digest=value.get('sha256')
        if isinstance(path,str) and isinstance(digest,str) and 'docs/screenshots/' in path.replace('\\','/'):
            resolved=media_path(path);require(sha(resolved.read_bytes())==digest,'Capture hash differs: '+path)
        for item in value.values():media_files(item,media)
    elif isinstance(value,list):
        for item in value:media_files(item,media)
    elif isinstance(value,str) and 'docs/screenshots/' in value.replace('\\','/'):
        if Path(value).suffix.lower() in ('.png','.gif','.wav','.mp4','.webm'):
            path=media_path(value);media[path.relative_to(ROOT).as_posix()]=sha(path.read_bytes())


def media_path(name):
    path=Path(name.replace('\\','/'));path=(ROOT/path).resolve() if not path.is_absolute() else path.resolve()
    require(path.is_relative_to(ROOT/'docs/screenshots') and path.is_file(),'Missing current-checkout review media: '+name)
    return path


def counted_checks(report,name):
    checks=report.get('checks')
    if isinstance(checks,list):
        require(checks and all(isinstance(row,dict) and row.get('passed') is True for row in checks),name+' has failed/empty checks')
        count=len(checks)
        for key in ('passed','passed_checks','check_count'):
            if key in report:require(report[key]==count,name+' count differs: '+key)
        return count
    require(isinstance(checks,int) and not isinstance(checks,bool) and checks>0,name+' has no counted checks')
    return checks


def collect(source_ref):
    manifest=read('dist/manifest.json');rom=sha((ROOT/'dist/abaqus-after-hours.sfc').read_bytes())
    require(manifest['version']=='0.24.0' and manifest['sha256']==rom and manifest['bytes']==4194304,'Wrong current cartridge')
    freeze=git('rev-parse',source_ref+'^{commit}').decode().strip()
    git('merge-base','--is-ancestor',freeze,'HEAD')
    require(sha(git('show',freeze+':dist/abaqus-after-hours.sfc'))==rom,'Frozen ROM differs')
    require(json.loads(git('show',freeze+':dist/manifest.json'))==manifest,'Frozen manifest differs')
    tracked=git('diff','--name-only',freeze,'--','src','tools','assets','dist').decode().splitlines()
    untracked=git('ls-files','--others','--exclude-standard','src','tools','assets','dist').decode().splitlines()
    require(not tracked and not untracked,'Source/test inputs changed after freeze: '+str(tracked+untracked))
    tree=git('rev-parse',freeze+'^{tree}').decode().strip()
    contract=combined_contract(ROOT);records={};media={}
    for name in (*SIX,*FEATURES.values(),'compatibility-test-report.json'):
        path='docs/'+name;report=read(path)
        require(report.get('rom_sha256',report.get('rom',{}).get('sha256'))==rom,'Stale native evidence: '+name)
        require(report.get('status','passed')=='passed',name+' did not pass')
        failure_arrays(report,name)
        if name=='compatibility-test-report.json':
            require(report.get('pinned_core') is True and report['checks']['cadence']['passed'] is True,'Independent smoke/cadence missing')
            require(report['core']['dll_sha256'].lower()==EXPECTED_INDEPENDENT_CORE['dll_sha256'],'Wrong independent core')
            count=None
        else:count=counted_checks(report,name)
        host=report.get('host',report.get('host_contract',{}))
        if name in FEATURES.values():
            require(host.get('gui_opened') is False and host.get('audio_device_opened') is False,name+' headless contract missing')
        media_files(report,media)
        records[name]={'path':path,'sha256':sha((ROOT/path).read_bytes()),'checks':count}
    composition_path='docs/combat-24-composition-report.json'
    composition=read(composition_path)
    require(composition.get('status')=='passed' and composition.get('rom_sha256')==rom,
            'Stale or failed contact/super composition proof')
    failure_arrays(composition,'composition')
    cases=composition.get('cases',[])
    expected={'dedicated-simultaneous':12,'rising-pulses':24,'remote-whiff':6,
              'startup-interrupt':6,'recovery-punish':1}
    require(len(cases)==49 and
            {kind:sum(row.get('kind')==kind for row in cases) for kind in expected}==expected and
            {row['fighter'] for row in cases if row['kind']=='dedicated-simultaneous'}==set(range(12)),
            'Composition coverage is incomplete')
    for row in cases:
        samples=row.get('native_counters',[])
        require(samples and all(sample['delta']['frame']==1 and
                sample['delta']['snes_vblank_count']==1 and sample['delta']['lag_frame_counter']==0
                for sample in samples),'Composition native cadence differs')
    require(composition['harness_sha256']==sha(canonical('tools/test_contact_super_composition.py',
            (ROOT/'tools/test_contact_super_composition.py').read_bytes())),
            'Composition producer differs')
    records[Path(composition_path).name]={'path':composition_path,
            'sha256':sha((ROOT/composition_path).read_bytes()),'cases':len(cases)}
    timing_path='docs/combat-24-special-timing-report.json'
    timing=read(timing_path)
    require(timing.get('status')=='passed' and timing.get('version')==manifest['version'] and
            timing.get('rom_sha256')==rom,'Stale or failed native optimization regression proof')
    # This report deliberately retains failing historical baseline and
    # Accuracy byte comparisons. Its counts are not pooled with current suites.
    records[Path(timing_path).name]={'path':timing_path,'sha256':sha((ROOT/timing_path).read_bytes()),
            'scope':'Optimization regression; historical failures retained separately'}
    stage=read('docs/stage-test-report.json')
    require(stage.get('shared_native_execution') is True and
            stage.get('focused_report')=='docs/'+FEATURES['stages'] and
            stage.get('focused_report_sha256')==records[FEATURES['stages']]['sha256'],
            'Shared stage execution differs from its focused appendix')
    sample_path='docs/combat-24-pacing-samples.json';samples=read(sample_path)
    require(samples.get('status')=='passed' and samples.get('rom_sha256')==rom and
            samples['samples']['after']['rom_sha256']==rom and
            samples['samples']['before']['rom_sha256']==samples['baseline_rom_sha256'],
            'Recoil review clips do not identify current and historical cartridges')
    require(samples['producer_sha256']==sha(canonical(samples['producer'],(ROOT/samples['producer']).read_bytes())),
            'Recoil clip retention producer differs')
    media_files(samples,media)
    records['combat-24-pacing-samples.json']={'path':sample_path,'sha256':sha((ROOT/sample_path).read_bytes())}
    for name in ('fresh-build-test-report.json','authoring-guards-report.json','combat-24-guards-report.json'):
        report=read('docs/'+name)
        require(report.get('status')=='passed' and report.get('rom_sha256')==rom and report.get('source_commit')==freeze,name+' does not identify passing frozen-source evidence')
        if name=='fresh-build-test-report.json':
            require(report.get('source_tree')==tree and report.get('rebuilt_rom_sha256')==rom and
                    report.get('generated_assets_verified')==contract['assets']['generated_count'] and
                    report.get('symbols_equal_after_source_path_normalization') is True,'Fresh export did not reproduce the cartridge/assets/symbols')
            generated=report.get('generated_assets',[])
            require({row['file'] for row in generated}=={row['path'] for row in contract['assets']['generated']},'Fresh generated inventory differs')
            for row in generated:require(sha(canonical(row['file'],(ROOT/row['file']).read_bytes()))==row['sha256'],'Fresh asset hash differs: '+row['file'])
        else:
            suites=SUITES if name=='combat-24-guards-report.json' else ('tools/test_authoring_guards.py',)
            runs=report['runs'];require(len(runs)==2*len(suites),name+' lacks both interpreter modes')
            for suite in suites:
                parsed=ast.parse((ROOT/suite).read_text(encoding='utf-8'))
                count=sum(isinstance(n,ast.FunctionDef) and n.name.startswith('test_')
                          for cls in parsed.body if isinstance(cls,ast.ClassDef) for n in cls.body)
                selected=[row for row in runs if row.get('suite',suite)==suite]
                require(len(selected)==2 and {row['optimized'] for row in selected}=={False,True} and
                        all(row['exit_code']==0 and row['tests']==count and row['output'].rstrip().endswith('OK') for row in selected),name+' has incomplete guard runs')
        records[name]={'path':'docs/'+name,'sha256':sha((ROOT/'docs'/name).read_bytes())}
    state=read('docs/combat-24-prs.json');prs=state['feature_prs']
    require(set(prs)==set(FEATURES) and all(row.get('merged') is True for row in prs.values()),'All six feature PRs must be integrated')
    for row in prs.values():
        git('merge-base','--is-ancestor',row['head'],freeze)
        git('merge-base','--is-ancestor',row['merge_commit'],freeze)
    sources={}
    for name in git('ls-files','src','tools').decode().splitlines():
        if Path(name).suffix.lower() in ('.py','.ps1','.h','.c','.asm'):
            sources[name]=sha(canonical(name,(ROOT/name).read_bytes()))
    result={'status':'passed','scope':'Six-feature combined native playtest candidate; no new offline package',
            'version':manifest['version'],'rom_sha256':rom,'checksum':manifest['checksum'],
            'source_commit':freeze,'source_tree':tree,'source_sha256':sources,
            'native_six_suite_checks':sum(records[name]['checks'] for name in SIX),
            'evidence':records,'native_contract':contract,'review_media_sha256':media,
            'feature_prs':prs,'integration_pr':state['final_pr'],
            'shared_stage_and_focused_execution':True,'human_combined_playtest':None,
            'public_release_certified':False,'full_offline_package_regenerated':False}
    output=ROOT/'docs/verification-v0.24.0.json'
    output.write_bytes((json.dumps(result,indent=2)+'\n').encode())
    print(json.dumps({'status':'passed','rom_sha256':rom,'six_suite_checks':result['native_six_suite_checks'],'review_media':len(media)}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-freeze',required=True)
    collect(parser.parse_args().source_freeze)
