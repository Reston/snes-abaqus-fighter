"""Controller-only portrait and combat rendering proof for the all-roster native pixel face revision."""
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import test_characters as ch
from fighter_assets import SLUGS
import test_defense29 as defense
import test_presentation as ui
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    defense.SYMS.update(defense.symbols(ROOT/'dist/abaqus-after-hours.sym'))
    out=ROOT/'docs/screenshots/native-faces-v033/native';out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((ROOT/'dist/manifest.json').read_bytes())
    if manifest['version']!='0.33.0' or sha(ROOT/'dist/abaqus-after-hours.sfc')!=manifest['sha256']:raise ValueError('Wrong native expression candidate')
    dependencies=['tools/test_native_faces33.py','tools/native_faces33_contracts.py','tools/test_characters.py',
        'tools/test_defense29.py','tools/test_presentation.py','tools/emulator.py','tools/test_classic_menu.py',
        'tools/test_compatibility.py','tools/fighter_assets.py','tools/portrait_assets.py','tools/native_face_assets.py']
    hashes={p:sha(ROOT/p) for p in dependencies}
    report={'status':'failed','rom_sha256':manifest['sha256'],'version':manifest['version'],
        'emulated_memory_writes':False,'save_states':False,'controller_only':True,'cases':[],
        'media':[],'dependencies_sha256':hashes}
    def shot(e,name):
        p=out/(name+'.png');e.frame.save(p)
        report['media'].append({'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)})
    for core in ('snes9x','accuracy'):
        for fid,slug in enumerate(SLUGS):
            for port in (0,1):
                tag=f'{core}-{slug}-p{port+1}'
                menu=defense.Host(core)
                try:
                    menu.run(120);ch.press(menu,'down');ch.press(menu,'a');ch.wait_screen(menu,1)
                    if port:
                        for _ in range(8):ch.press(menu,'right')
                        ch.press(menu,'a');menu.run(24)
                    key='selected2' if port else 'selected1'
                    # P1's cursor is named selected in the original trace.
                    current=ch.state(menu)
                    selected=current.get(key,current.get('selected',0))
                    for _ in range((fid-selected)%12):ch.press(menu,'right',port)
                    menu.run(30)
                    portrait=ui.verify_large_portrait(menu,fid)
                    shot(menu,tag+'-select')
                    if menu.health['failures']:raise ValueError(menu.health['failures'])
                finally:menu.close()
                prior=ch.Emulator;ch.Emulator=lambda rom=None:defense.Host(core,rom)
                try:e=ch.boot(1,fid if port==0 else 8,(fid+port)%3,8 if port==0 else fid,quiet_frames=8)
                finally:ch.Emulator=prior
                try:
                    state=ch.state(e);expected=(fid,8) if port==0 else (8,fid)
                    if (state['fighter_id1'],state['fighter_id2'])!=expected:raise ValueError('Wrong fighters')
                    ui.verify_fight_font_bank(e,ui.state(e))
                    geometry=ch.verify_oam_geometry(e,port,tag)
                    pixels=ch.verify_rendered_actor(e,fid,port,geometry);shot(e,tag+'-fight')
                    def run(n,keys=()):return e.run(n,**{'p1' if port==0 else 'p2':keys})
                    toward='right' if not port else 'left';away='left' if not port else 'right'
                    run(24,[toward]);shot(e,tag+'-walk');run(24,[away]);run(12)
                    run(3,['up',toward]);run(14);shot(e,tag+'-jump');run(90)
                    for action,keys in [('jab',['y']),('strong',['x']),('kick',['b']),('heavy-kick',['a']),('uppercut',['down','x'])]:
                        run(3,keys);run(9);shot(e,tag+'-'+action);run(100)
                    if e.health['failures']:raise ValueError(e.health['failures'])
                    report['cases'].append({'core':core,'fighter_id':fid,'fighter':slug,'port':port+1,
                        'fighters':expected,'portrait_PPU_pixels':'passed','portrait':portrait,
                        'OAM_and_native_pixels':'passed','geometry':geometry,'pixels':pixels})
                finally:e.close()
    if any(sha(ROOT/p)!=h for p,h in hashes.items()):raise ValueError('Producer dependencies changed')
    if sha(ROOT/'dist/abaqus-after-hours.sfc')!=manifest['sha256']:raise ValueError('ROM changed during proof')
    report.update(status='passed',health=defense.HEALTH,
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        assertion_executions=sum(x['executions'] for x in defense.CHECKS.values()))
    (ROOT/'docs/native-faces33-native-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'status':'passed','cases':len(report['cases']),'captures':len(report['media']),'checks':report['assertion_executions']}))
if __name__=='__main__':main()
