"""Controller-only full-body selection proof; no GUI/audio/writes/save states."""
import argparse,ctypes as C,hashlib,io,json,re,subprocess,sys,tarfile,time
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from emulator import Emulator
from test_classic_menu import AccuracyMenu
from test_training import core_identity
from test_compatibility import verify_manifest_and_pinned_core
from test_champion import host_contract
from v024_contracts import symbols
from menu_preview_checks import uploaded_pose,verify_preview
import test_presentation as presentation

BASE='adb522e'
CHECKS=[]
def require(ok,label,details=None):
    if not ok:raise AssertionError((label,details))
    CHECKS.append({'check':label,'passed':True})
def sha(raw):return hashlib.sha256(raw).hexdigest()
def preservation():
    changed=[];count=0
    allowed={'assets/generated/assets.h'}|{f'assets/generated/select{s}' for s in ('.png','_tiles.bin','_map.bin','_pal.bin')}
    with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['git','archive',BASE,'assets/generated','src/hardware.asm','src/trace.asm'],cwd=ROOT))) as archive:
        for item in archive:
            if not item.isfile():continue
            before=archive.extractfile(item).read();after=(ROOT/item.name).read_bytes()
            if Path(item.name).suffix in ('.h','.asm','.json'):before=before.replace(b'\r\n',b'\n');after=after.replace(b'\r\n',b'\n')
            count+=item.name.startswith('assets/generated/')
            if before!=after:changed.append(item.name)
    require(count==226 and set(changed)<=allowed,'Only the selection plate and its size header change',changed)
    old=symbols(subprocess.check_output(['git','show',BASE+':dist/abaqus-after-hours.sym'],cwd=ROOT).decode())
    new=symbols((ROOT/'dist/abaqus-after-hours.sym').read_text())
    ram=lambda v:v<0x2000 or 0x7e0000<=v<0x800000
    prior={n:v for n,v in old.items() if ram(v)}
    markers={'SECTIONEND_globram.data','RAM_USAGE_SLOT_3_BANK_127_END'}
    moved={n:[v,new.get(n)] for n,v in prior.items() if new.get(n)!=v}
    added={n:v for n,v in new.items() if ram(v) and n not in old}
    expected={'menuPreviewId','menuPreviewFrame','menuPreviewClock','menuPreviewConfirm','menuPreviewPaletteDirty'}
    require(len(prior)==1318 and set(moved)==markers and all(b==a+5 for a,b in moved.values()),'Only two allocation markers grow by five bytes',moved)
    require(set(added)==expected and sorted(added.values())==list(range(old['SECTIONEND_globram.data'],old['SECTIONEND_globram.data']+5)),
            'Five menu-only bytes append after all existing variables',added)
    return {'baseline_commit':subprocess.check_output(['git','rev-parse',BASE],cwd=ROOT,text=True).strip(),
            'generated_count':count,'generated_preserved':count-len(changed),'changed':changed,
            'existing_variable_labels_unchanged':len(prior)-len(markers),'allocation_markers':moved,'new_menu_bytes':added,
            'hardware_and_trace_assembly_exact':True}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core',choices=('snes9x','accuracy'),required=True)
    parser.add_argument('--fighters',default=','.join(map(str,range(12))))
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--captures',type=Path,default=ROOT/'docs/screenshots/menu-preview')
    args=parser.parse_args();fighters=list(map(int,args.fighters.split(',')))
    report_path=args.report.resolve();captures=args.captures.resolve()/args.core;captures.mkdir(parents=True,exist_ok=True)
    require(fighters==list(range(12)) or report_path.is_relative_to(ROOT/'build'),'Partial runs remain diagnostic')
    manifest=json.loads((ROOT/'dist/manifest.json').read_bytes());syms=symbols((ROOT/'dist/abaqus-after-hours.sym').read_text())
    sources={p.relative_to(ROOT).as_posix():sha(p.read_bytes().replace(b'\r\n',b'\n')) for folder in ('src','tools') for p in (ROOT/folder).iterdir() if p.is_file() and p.suffix in ('.py','.h','.c','.asm')}
    started=time.monotonic();health={'steady_callbacks':0,'failures':[]};cases=[];media=[]
    report={'status':'failed','version':manifest['version'],'rom_sha256':manifest['sha256'],'core':args.core,
            'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'sources':sources,'host':host_contract(),'memory_writes':False,'save_states':False,'audio_device_opened':False}
    try:
        require(sha((ROOT/'dist/abaqus-after-hours.sfc').read_bytes())==manifest['sha256'],'Exact ROM/manifest identity')
        report['preservation']=preservation();report['core_identity']=core_identity() if args.core=='snes9x' else verify_manifest_and_pinned_core()
        intro_text=(ROOT/'src/fighter_personality.h').read_text()
        block=intro_text.split('personalityIntroFrames[12][4]={',1)[1].split('};',1)[0]
        intro=[list(map(int,re.findall(r'\d+',line.split('/*')[0]))) for line in block.splitlines() if '{' in line]
        for mode in range(3):
            for fighter in fighters:
                host=AccuracyMenu() if args.core=='accuracy' else Emulator()
                def read(name,size=1):return int.from_bytes(C.string_at(host.ram+(syms[name]&0x1ffff),size),'little')
                def counters():return [read(n,2) for n in ('frame','snes_vblank_count','lag_frame_counter')]
                def run(n=1,port=0,keys=(),transition=False):
                    for _ in range(n):
                        screen=read('screen');before=counters();host.run(1,**({'p1':list(keys)} if port==0 else {'p2':list(keys)}))
                        if not transition and screen==read('screen')==1:
                            delta=[(a-b)&65535 for a,b in zip(counters(),before)];health['steady_callbacks']+=1
                            if delta!=[1,1,0]:health['failures'].append({'mode':mode,'fighter':fighter,'delta':delta})
                            stat=int.from_bytes(C.string_at(host.ram+0x1ff00+114*2,2),'little')
                            require(not (stat&0xc0),'No preview OBJ overflow')
                def pulse(key,port=0,transition=False):run(3,port,[key],transition);run(22,transition=transition)
                def save(label):
                    path=captures/f'mode{mode}-{fighter:02}-{label}.png';host.frame.save(path);media.append({'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path.read_bytes())})
                try:
                    host.run(120)
                    for _ in range(mode):pulse('down')
                    pulse('a',transition=True)
                    require(read('screen')==1,'Native title opens selection')
                    for _ in range(fighter):pulse('right')
                    role_results=[]
                    for role in range(2 if mode else 1):
                        port=1 if mode==1 and role else 0
                        if role:
                            target=(fighter+5)%12 if mode==1 else fighter
                            for _ in range((target-read('selected2'))%12):pulse('right',port)
                        active=(fighter+5)%12 if mode==1 and role else fighter
                        require(read('selectPlayer')==role and read('selected2' if role else 'selected')==active,'Correct active fighter and player')
                        idle=set();last=None;visual=[];clip=[]
                        for tick in range(100):
                            pose=uploaded_pose(host,active)
                            require(pose in (16,17,18,19),'Idle uses approved standing frames',pose)
                            idle.add(pose)
                            if pose==last and pose not in [x['pose'] for x in visual]:visual.append(verify_preview(host,active))
                            last=pose
                            if mode==0 and args.core=='snes9x' and tick%3==0:clip.append(host.frame.copy())
                            run()
                        require(idle=={16,17,18,19},'All four breathing poses appear without moving the feet',sorted(idle))
                        presentation.verify_select_card_render(host);presentation.verify_select_markers(host)
                        if not role:save('idle')
                        held='a' if (fighter+role)%2==0 else 'start';seen=[];gesture=[];last=None
                        run(1,port,[held])
                        for tick in range(30):
                            if read('screen')!=1 or read('selectPlayer')!=role:break
                            pose=uploaded_pose(host,active);seen.append(pose)
                            if pose==last and pose not in [x['pose'] for x in gesture]:gesture.append(verify_preview(host,active))
                            last=pose
                            if mode==0 and args.core=='snes9x' and tick%3==0:clip.append(host.frame.copy())
                            if tick==9 and not role:save('gesture')
                            run(1,port,[held])
                        expected=[intro[active][0],intro[active][1],11]
                        compact=[p for i,p in enumerate(seen) if i==0 or p!=seen[i-1]]
                        require(all(p in compact for p in expected) and all(compact.index(a)<compact.index(b) for a,b in zip(expected,expected[1:])),
                                'Confirmation plays the two signature beats and victory pose before advancing',{'seen':compact,'expected':expected})
                        run(12,port,[held],transition=True);run(3,transition=True)
                        require(read('screen')==(1 if not role and mode else 2),'Held confirm advances exactly one selection step')
                        require(read('menuPreviewConfirm')==0,'Confirmation lock releases at the next step')
                        role_results.append({'role':role,'fighter':active,'idle':sorted(idle),'idle_pixels':visual,'gesture':compact,'gesture_pixels':gesture,'held_key':held})
                        if mode==0 and args.core=='snes9x':
                            path=captures/f'{fighter:02}-idle-confirm.gif';clip[0].save(path,save_all=True,append_images=clip[1:],duration=50,loop=0)
                            media.append({'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path.read_bytes()),'scope':'sampled every three native callbacks; GIF timing is approximate'})
                    require(read('screen')==2,'Confirmed fighter choices reach the location menu')
                    pulse('b',transition=True);require(read('screen')==1 and read('selectPlayer')==0,'Back restores an idle P1 preview')
                    require(uploaded_pose(host,read('selected')) in (16,17,18,19),'Returned selection clears the confirmation animation')
                    run(4);verify_preview(host,read('selected'))
                    # The preview page/palette must not leak into a real match.
                    pulse('a',transition=True)
                    if mode:pulse('a',1 if mode==1 else 0,transition=True)
                    pulse('a',transition=True)
                    require(read('screen')==3,'Selection hands off to the native fight renderer')
                    for _ in range(120):
                        if host.state()['screen']==3:break
                        run(transition=True)
                    require(host.state()['screen']==3,'Forced-blank match load publishes its native scene')
                    run(3,transition=True)
                    if mode==0:run(3,keys=['a'],transition=True);run(3,transition=True)
                    for _ in range(180):
                        if host.state()['intro']==0:break
                        run(transition=True)
                    require(host.state()['intro']==0,'Preview handoff reaches live combat')
                    for _ in range(24):
                        before=counters();host.run(1)
                        require([(a-b)&65535 for a,b in zip(counters(),before)]==[1,1,0],'Preview handoff retains native live-fight cadence')
                    require(host.state()['fighter_id1']==read('selected') and host.state()['fighter_id2']==(read('selected2') if mode else (read('selected')+1)%12),'Fight uses the confirmed roster IDs')
                    require(host.audio_samples>0 and host.audio_peak<32767,'Menu/fight PCM stays active and unclipped')
                    cases.append({'mode':mode,'fighter':fighter,'roles':role_results})
                    print(json.dumps({'core':args.core,'mode':mode,'fighter':fighter,'status':'passed'}),flush=True)
                finally:host.close()
        require(not health['failures'],'Strict native menu cadence and SDK lag',health['failures'])
        require(sources=={p.relative_to(ROOT).as_posix():sha(p.read_bytes().replace(b'\r\n',b'\n')) for folder in ('src','tools') for p in (ROOT/folder).iterdir() if p.is_file() and p.suffix in ('.py','.h','.c','.asm')},'Source/harness stayed frozen')
        report['status']='passed'
    except BaseException as error:report['error']=repr(error);raise
    finally:
        report.update(health=health,cases=cases,media=media,checks=CHECKS,passed=len(CHECKS),seconds=round(time.monotonic()-started,3))
        report_path.parent.mkdir(parents=True,exist_ok=True);report_path.write_bytes((json.dumps(report,indent=2)+'\n').encode())
        print(json.dumps({k:report[k] for k in ('status','core','passed','seconds')}),flush=True)

if __name__=='__main__':main()
