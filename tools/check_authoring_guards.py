"""Record normal/optimized mutation checks against a frozen authoring source."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from preservation import git, resolve
from test_champion import host_contract


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-ref',required=True)
    parser.add_argument('--producer-ref',required=True,
                        help='committed report producer; may follow the cartridge source freeze')
    args=parser.parse_args()
    started=time.monotonic()
    manifest=json.loads((ROOT/'dist/manifest.json').read_bytes())
    freeze=resolve(ROOT,args.source_ref)
    producer=resolve(ROOT,args.producer_ref)
    report={'status':'failed','scope':'Source-authoring mutation checks; no emulator or asset generation.',
            'version':manifest['version'],'rom_sha256':manifest['sha256'],
            'source_commit':freeze,'producer_commit':producer,
            'host_contract':host_contract(),'runs':[],'source_sha256':{},'producer_sha256':{}}
    try:
        if json.loads(git(ROOT,'show',freeze+':dist/manifest.json'))!=manifest:
            raise RuntimeError('Frozen authoring source must identify the current cartridge')
        for name in ('tools/fighter_assets.py','tools/make_assets.py','tools/stage_sources.py',
                     'tools/test_authoring_guards.py','tools/release_evidence.py'):
            raw=(ROOT/name).read_bytes().replace(b'\r\n',b'\n')
            if raw!=git(ROOT,'show',freeze+':'+name).replace(b'\r\n',b'\n'):
                raise RuntimeError(('Authoring source changed after freeze',name))
            report['source_sha256'][name]=hashlib.sha256(raw).hexdigest()
        git(ROOT,'merge-base','--is-ancestor',freeze,producer)
        if json.loads(git(ROOT,'show',producer+':dist/manifest.json'))!=manifest:
            raise RuntimeError('Producer commit must identify this cartridge')
        name='tools/check_authoring_guards.py'
        raw=(ROOT/name).read_bytes().replace(b'\r\n',b'\n')
        if raw!=git(ROOT,'show',producer+':'+name).replace(b'\r\n',b'\n'):
            raise RuntimeError('Report producer changed after evidence freeze')
        report['producer_sha256'][name]=hashlib.sha256(raw).hexdigest()
        host=report['host_contract']
        if host['priority_class']!=0x4000 or len(host['logical_processors'])!=2:
            raise RuntimeError('Run below normal on the last two logical CPUs')
        for optimized in (False,True):
            command=[sys.executable]+(['-O'] if optimized else [])+[str(ROOT/'tools/test_authoring_guards.py')]
            result=subprocess.run(command,cwd=ROOT,stdin=subprocess.DEVNULL,capture_output=True,text=True,
                                  creationflags=(0x08000000|0x4000) if sys.platform=='win32' else 0)
            output=result.stdout+result.stderr
            count=re.search(r'Ran (\d+) tests? in',output)
            report['runs'].append({'optimized':optimized,'arguments':(['-O'] if optimized else [])+
                                  ['tools/test_authoring_guards.py'],'exit_code':result.returncode,
                                  'tests':int(count[1]) if count else 0,'output':output})
            if result.returncode or count is None or int(count[1])==0 or not output.rstrip().endswith('OK'):
                raise RuntimeError(('Authoring mutation checks failed',optimized,output[-2000:]))
        report['status']='passed'
    except Exception as error:
        report['error']=repr(error)
        raise
    finally:
        report['elapsed_seconds']=round(time.monotonic()-started,3)
        (ROOT/'docs/authoring-guards-report.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    print(json.dumps({key:report[key] for key in ('status','version','rom_sha256','elapsed_seconds')}))


if __name__=='__main__': main()
