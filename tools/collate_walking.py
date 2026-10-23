"""Bind v0.23 walking/local-play evidence to its committed cartridge inputs."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SIX=('test-report.json','character-test-report.json','presentation-test-report.json',
     'input-test-report.json','stage-test-report.json','training-test-report.json')
def require(ok,message):
    if not ok:raise RuntimeError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-freeze',required=True);args=parser.parse_args()
    m=json.loads((ROOT/'dist/manifest.json').read_bytes());rom=sha((ROOT/'dist/abaqus-after-hours.sfc').read_bytes())
    require(m['version']=='0.23.1' and m['sha256']==rom,'Wrong walking cartridge')
    freeze=subprocess.check_output(['git','rev-parse',args.source_freeze+'^{commit}'],cwd=ROOT,text=True).strip()
    subprocess.run(['git','merge-base','--is-ancestor',freeze,'HEAD'],cwd=ROOT,check=True)
    require(sha(subprocess.check_output(['git','show',freeze+':dist/abaqus-after-hours.sfc'],cwd=ROOT))==rom,'Frozen cartridge differs')
    records={};total=0
    for name in (*SIX,'compatibility-test-report.json','walking-report.json','fresh-build-test-report.json','authoring-guards-report.json'):
        p=ROOT/'docs'/name;r=json.loads(p.read_bytes())
        require(r.get('rom_sha256',r.get('rom',{}).get('sha256'))==rom,name+' is stale')
        if name in SIX:
            require(r['checks'] and all(c.get('passed') is True for c in r['checks']) and r['passed']==len(r['checks']),name+' failed')
            total+=len(r['checks'])
        else:require(r.get('status')=='passed',name+' failed')
        if name=='walking-report.json':
            require(r.get('walking_scope')=='coordinated-full-body','Walking proof uses the rejected torso overlay')
            require(len(r['cases'])==12 and all(c.get('passed') is True for c in r['checks']),name+' lacks complete passing roster')
            for case in r['cases']:
                require(case['both_ports'] and all(frames==list(range(20,28)) for key in ('forward_frames','retreat_frames') for frames in case[key]),'Incomplete two-port gait coverage')
                for cap in case['captures']:require(sha((ROOT/cap['path']).read_bytes())==cap['sha256'],'Walking capture changed')
        if name in ('fresh-build-test-report.json','authoring-guards-report.json'):
            require(r.get('source_commit')==freeze,name+' source freeze differs')
        if name=='fresh-build-test-report.json':require(r.get('rebuilt_rom_sha256')==rom and r.get('generated_assets_verified')==219 and r.get('symbols_equal_after_source_path_normalization') is True,'Fresh export mismatch')
        if name=='authoring-guards-report.json':require(len(r['runs'])==2 and all(x['exit_code']==0 and x['tests']==20 for x in r['runs']),'Authoring runs incomplete')
        records[name]={'path':'docs/'+name,'sha256':sha(p.read_bytes()),'checks':len(r['checks']) if isinstance(r.get('checks'),list) else None}
    inputs={}
    for name in subprocess.check_output(['git','ls-files','src','tools','assets/art/walking-v2.json'],cwd=ROOT,text=True).splitlines():
        p=ROOT/name
        if p.suffix not in ('.c','.h','.asm','.py','.ps1','.json'):continue
        now=p.read_bytes().replace(b'\r\n',b'\n');old=subprocess.check_output(['git','show',freeze+':'+name],cwd=ROOT).replace(b'\r\n',b'\n')
        require(now==old,'Source/test changed after freeze: '+name);inputs[name]=sha(now)
    for row in json.loads((ROOT/'assets/art/walking-v2.json').read_bytes())['fighters']:
        p=ROOT/row['provenance'];require(sha(p.read_bytes())==row['provenance_sha256'],'Walking provenance changed')
        r=json.loads(p.read_bytes());require(sha((ROOT/r['source']).read_bytes())==r['sha256'],'Walking master changed')
    result={'status':'passed','version':m['version'],'rom_sha256':rom,'checksum':m['checksum'],'source_commit':freeze,
            'source_tree':subprocess.check_output(['git','rev-parse',freeze+'^{tree}'],cwd=ROOT,text=True).strip(),
            'native_six_suite_checks':total,'evidence':records,'source_sha256':inputs,
            'main_checkpoint':'f5345f9db6b9d663b629b8d11cb0458e57521be4','main_merge_pr':1,
            'stage08_deferred':True,'local_1v1_already_supported':True,'public_release_certified':False,
            'human_walking_review':None,'physical_controller_review':None,'full_offline_package_regenerated':False}
    (ROOT/'docs/verification-v0.23.1.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    print(json.dumps({'status':'passed','rom_sha256':rom,'six_checks':total,'records':len(records)}))
if __name__=='__main__':main()
