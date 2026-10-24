"""Record the combat importer and preservation mutations against frozen inputs."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from test_champion import host_contract

SUITES=('tools/test_pose_revision_guards.py','tools/test_v024_preservation_guards.py',
        'tools/test_combat_24_evidence.py')
INPUTS=(*SUITES,'tools/pose_revision_assets.py','tools/v024_contracts.py',
        'tools/check_combat_24_guards.py','tools/test_champion.py',
        'tools/collate_combat_24.py','tools/compare_special_24_state.py',
        'tools/test_special_24_timing.py','tools/test_special_24_cpu_timing.py')


def require(ok,message):
    if not ok:raise RuntimeError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-ref',required=True)
    args=parser.parse_args();started=time.monotonic()
    manifest=json.loads((ROOT/'dist/manifest.json').read_bytes())
    freeze=git('rev-parse',args.source_ref+'^{commit}').decode().strip()
    report={'status':'failed','version':manifest['version'],'rom_sha256':manifest['sha256'],
            'source_commit':freeze,'host_contract':host_contract(),'source_sha256':{},'runs':[]}
    try:
        require(manifest['version']=='0.24.0','Expected the combined v0.24 cartridge')
        require(sha((ROOT/'dist/abaqus-after-hours.sfc').read_bytes())==manifest['sha256'],'Current ROM differs')
        require(json.loads(git('show',freeze+':dist/manifest.json'))==manifest,'Frozen cartridge differs')
        git('merge-base','--is-ancestor',freeze,'HEAD')
        for name in INPUTS:
            raw=(ROOT/name).read_bytes().replace(b'\r\n',b'\n')
            require(raw==git('show',freeze+':'+name).replace(b'\r\n',b'\n'),'Guard input changed after freeze: '+name)
            report['source_sha256'][name]=sha(raw)
        for suite in SUITES:
            tree=ast.parse((ROOT/suite).read_text(encoding='utf-8'))
            expected=sum(isinstance(n,ast.FunctionDef) and n.name.startswith('test_')
                         for cls in tree.body if isinstance(cls,ast.ClassDef) for n in cls.body)
            require(expected>0,'Guard suite is empty: '+suite)
            for optimized in (False,True):
                arguments=(['-O'] if optimized else [])+[suite]
                result=subprocess.run([sys.executable,*arguments],cwd=ROOT,stdin=subprocess.DEVNULL,
                                      capture_output=True,text=True,
                                      creationflags=0x08004000 if sys.platform=='win32' else 0)
                output=result.stdout+result.stderr;match=re.search(r'Ran (\d+) tests? in',output)
                report['runs'].append({'suite':suite,'optimized':optimized,'arguments':arguments,
                                       'exit_code':result.returncode,'tests':int(match[1]) if match else 0,
                                       'output':output})
                require(result.returncode==0 and match is not None and int(match[1])==expected and
                        output.rstrip().endswith('OK'),'Guard suite failed: '+suite)
        report['status']='passed'
    except Exception as error:
        report['error']=repr(error)
        raise
    finally:
        report['elapsed_seconds']=round(time.monotonic()-started,3)
        (ROOT/'docs/combat-24-guards-report.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    print(json.dumps({k:report[k] for k in ('status','version','rom_sha256','elapsed_seconds')}))


if __name__=='__main__':main()
