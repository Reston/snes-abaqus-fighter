"""Native all-roster/two-port gait and preservation proof; controller-only."""
from pathlib import Path
import ctypes as C
import hashlib,io,json,subprocess,sys,time
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from test_characters import boot,state,uploaded_frame_id
from emulator import Emulator
from test_champion import host_contract
from expansion_contracts import combined_contract

BASE='f5345f9db6b9d663b629b8d11cb0458e57521be4'
HAND_BOXES={0:(20,43,27,51),2:(33,43,45,51),4:(27,43,40,55),
            6:(23,42,38,54),7:(17,42,45,54),8:(31,42,51,54),
            9:(33,43,46,54),11:(20,42,37,59)}
OUT=ROOT/'docs/screenshots/walking-v1'
checks=[]
def check(ok,label,detail=None):
    checks.append({'passed':bool(ok),'check':label,'detail':detail})
    if not ok:raise AssertionError((label,detail))
def digest(raw):return hashlib.sha256(raw).hexdigest()
def git_file(path):return subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT)

def art_contract():
    result=[]
    for fighter in range(12):
        name=f'assets/generated/fighter{fighter:02d}'
        old=Image.open(io.BytesIO(git_file(name+'.png'))).convert('RGBA')
        new=Image.open(ROOT/(name+'.png')).convert('RGBA')
        check(old.size==new.size==(6144,80),'native canvas preserved',fighter)
        changes=[];spreads=[]
        for frame in range(64):
            a=old.crop((frame*96,0,(frame+1)*96,80));b=new.crop((frame*96,0,(frame+1)*96,80))
            if a.tobytes()!=b.tobytes():changes.append(frame)
            if 20<=frame<28:
                check(a.crop((0,0,96,47)).tobytes()==b.crop((0,0,96,47)).tobytes(),
                      'walking face and upper body pixels preserved',[fighter,frame])
                if fighter in HAND_BOXES:
                    x0,y0,x1,y1=HAND_BOXES[fighter]
                    skin=[(x,y) for y in range(max(47,y0),y1) for x in range(x0,x1)
                          if (lambda c:c[3] and c[0]>=150 and c[0]>c[1]+18 and c[1]>c[2]+6 and c[1]*2>=c[0])(a.getpixel((x,y)))]
                    check(all(a.getpixel(p)==b.getpixel(p) for p in skin),
                          'original fingertips survive below the waist cut',[fighter,frame,len(skin)])
                box=b.getchannel('A').getbbox()
                check(box[3]==78 and box[0]>0 and box[2]<96,'walk keeps grounded sole and margins',[fighter,frame,box])
                foot=b.getchannel('A').crop((0,66,96,80)).getbbox();spreads.append(foot[2]-foot[0])
        check(changes==list(range(20,28)),'only eight authorized walking frames changed',[fighter,changes])
        check(max(spreads)-min(spreads)>=8,'passing feet close visibly between contacts',[fighter,spreads])
        check(git_file(name+'_pal.bin')==(ROOT/(name+'_pal.bin')).read_bytes(),'fixed OBJ palette preserved',fighter)
        for suffix in ('','-large','_tiles','_pal'):
            ext='.png' if suffix in ('','-large') else '.bin'
            p=f'assets/generated/portrait{fighter:02d}{suffix}{ext}'
            check(git_file(p)==(ROOT/p).read_bytes(),'portrait preserved',p)
        result.append({'fighter':fighter,'changed_frames':changes,'foot_span_pixels':spreads})
    return result

def session(fighter,rom=None,current=False):
    e=boot(1,fighter,fighter2=fighter,stage=fighter%3,rom=rom)
    rows=[];images={'forward':[],'retreat':[]};seen={label:[set(),set()] for label in images}
    def tick(p1=(),p2=(),label=None):
        before=e.state()['frame'];e.run(1,p1=p1,p2=p2);s=state(e)
        if current:
            check((s['frame']-before)&65535==1,'native gait callback advances exactly once',[fighter,label,s['frame']])
            stat=C.string_at(e.ram+0x1ff00+114*2,2)
            check(int.from_bytes(stat,'little')&0xc0==0,'native gait stays within OBJ budget',[fighter,label])
        rows.append({k:v for k,v in e.state().items() if k not in ('anim_frame1','anim_frame2')})
        if label:
            images[label].append(e.frame.copy().convert('RGB'))
            if current:
                for p in range(2):seen[label][p].add(s[f'anim_frame{p+1}'])
        return s
    try:
        for _ in range(10):tick(['left'],['right'])
        for _ in range(32):tick(['right'],['left'],'forward')
        tick(p2=['start']);paused=state(e)
        for _ in range(10):
            s=tick()
            if current:check(all(s[k]==paused[k] for k in ('x1','x2','anim_frame1','anim_frame2','anim_tick1','anim_tick2')),'P2 pause freezes both walking poses',fighter)
        tick(p1=['start']);tick()
        for _ in range(48):tick(['left'],['right'],'retreat')
        if current:
            for label,ports in seen.items():
                for port,frames in enumerate(ports):
                    check(frames==set(range(20,28)),'all eight gait poses appear on each port',[fighter,label,port,sorted(frames)])
            for _ in range(4):tick()
            x=(state(e)['x1'],state(e)['x2'])
            for _ in range(20):tick()
            check((state(e)['x1'],state(e)['x2'])==x,'Local Versus leaves both neutral players stationary',fighter)
            s=tick(p1=['y'],p2=['b'])
            for _ in range(2):s=tick(p1=['y'],p2=['b'])
            check(s['action1']==1 and s['action2']==4,'two independent ports accept different simultaneous attacks',fighter)
        return rows,images,seen
    finally:e.close()

def main():
    started=time.monotonic();OUT.mkdir(parents=True,exist_ok=True)
    m=json.loads((ROOT/'dist/manifest.json').read_bytes())
    base_rom=ROOT/'build/walking-baseline.sfc';base_rom.write_bytes(git_file('dist/abaqus-after-hours.sfc'))
    report={'status':'failed','version':m['version'],'rom_sha256':m['sha256'],'baseline_commit':BASE,
            'harness_sha256':digest(Path(__file__).read_bytes().replace(b'\r\n',b'\n')),
            'host_contract':host_contract(),'art':[],'cases':[],'checks':checks}
    try:
        e=Emulator()
        try:
            e.run(120)
            vram=C.string_at(e.core.retro_get_memory_data(3),e.core.retro_get_memory_size(3))
            label='LOCAL 1V1 / 2P'
            observed=[int.from_bytes(vram[0xb000+(22*32+x)*2:0xb002+(22*32+x)*2],'little')&1023 for x in range(9,9+len(label))]
            check(observed==[ord(c) for c in label],'title clearly advertises local two-player mode',observed)
            e.shot('walking-v1/local-1v1-title.png')
        finally:e.close()
        config=(ROOT/'tools/snes9x.conf').read_text()
        check('Joypad1:Enabled = TRUE' in config and 'Joypad2:Enabled = TRUE' in config,'included emulator enables both local players')
        report['local_1v1']={'already_supported':True,'label':label,'title_capture':'docs/screenshots/walking-v1/local-1v1-title.png',
                            'ports':'two independent native SNES controller ports; all twelve mirror cases below',
                            'p1_keyboard':'arrows; A/S punch; Z/X kick; Enter Start',
                            'p2_keyboard':'I/J/K/L; numpad7/8 punch; numpad1/2 kick; Space Start',
                            'physical_controllers':'Map each controller to Joypad1/Joypad2 in Snes9x Input Configuration; physical hardware not exercised'}
        report['art']=art_contract()
        report['native_contract']=combined_contract(ROOT)
        for fighter in range(12):
            old,old_images,_=session(fighter,base_rom)
            new,new_images,seen=session(fighter,current=True)
            check(new[:len(old)]==old,'walking preserves non-frame native combat telemetry',fighter)
            captures=[]
            for label,frames in new_images.items():
                p=OUT/f'{fighter:02d}-{label}.gif'
                frames[0].save(p,save_all=True,append_images=frames[1:],duration=34,loop=0,optimize=False)
                captures.append({'path':p.relative_to(ROOT).as_posix(),'sha256':digest(p.read_bytes())})
            if fighter in (0,9,10):
                paired=[]
                for a,b in zip(old_images['forward'],new_images['forward']):
                    im=Image.new('RGB',(512,224));im.paste(a,(0,0));im.paste(b,(256,0));paired.append(im)
                p=OUT/f'{fighter:02d}-before-after.gif'
                paired[0].save(p,save_all=True,append_images=paired[1:],duration=34,loop=0,optimize=False)
                captures.append({'path':p.relative_to(ROOT).as_posix(),'sha256':digest(p.read_bytes())})
            report['cases'].append({'fighter':fighter,'both_ports':True,'forward_frames':[sorted(s) for s in seen['forward']],
                                    'retreat_frames':[sorted(s) for s in seen['retreat']],'preserved_samples':len(old),'captures':captures})
        report['status']='passed'
    except Exception as error:report['error']=repr(error);raise
    finally:
        report['elapsed_seconds']=round(time.monotonic()-started,3)
        (ROOT/'docs/walking-report.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
        print(json.dumps({'status':report['status'],'checks':len(checks),'rom_sha256':m['sha256'],'cases':len(report['cases']),'error':report.get('error')}))
if __name__=='__main__':main()
