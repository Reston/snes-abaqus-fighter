"""Integration tests against the compiled ROM in the official Snes9x core.

Only controller inputs drive the game. Assertions read a reserved WRAM trace,
VRAM and actual emulator audio / video output. Run after tools/build.py.
"""
from pathlib import Path
import ctypes as C
import json, sys, time, wave
sys.path.insert(0,str(Path(__file__).parent))
from emulator import Emulator, ROOT

checks=[]
# Native fighter frames are 96x80 (six 16x16 OBJ pieces by five rows),
# encoded as twelve 8x8 4bpp tiles per physical 384-byte row.  Each VRAM page
# is 16 tiles wide, so the next row begins 512 bytes later.  Actor 1 starts at
# byte $D400 (VRAM word $6A00), leaving the two actors independent.
POSE_BYTES=3840
ANIMATION_BANK_SUFFIXES=('', 'b', 'c', 'd', 'e', 'f')
BANK_BYTES=POSE_BYTES*8
VRAM_ACTOR_BASE=0xC000
VRAM_ACTOR_STRIDE=0x1400
VRAM_ROW_STRIDE=0x200
VRAM_ROW_BYTES=0x180

def check(ok,label,details=None):
    assert ok, (label,details)
    checks.append({'check':label,'passed':True,'details':details})
def wait(e,screen,maxframes=600):
    for _ in range(maxframes//10):
        if e.state()['screen']==screen:
            e.run(15);return
        e.run(10)
    raise AssertionError(('Screen did not arrive',screen,e.state()))
def press(e,key,port=0):
    e.tap(key,port);e.run(20)
def boot(mode=0,fighter=0,stage=0,opponent=1,difficulty=1):
    e=Emulator();e.run(100)
    if difficulty==0:press(e,'l')
    for _ in range(mode):press(e,'down')
    press(e,'a');wait(e,1)
    for _ in range(fighter):press(e,'right')
    press(e,'a')
    if mode==1:
        for _ in range((opponent-1)%12):press(e,'right',1)
        press(e,'a',1)
    wait(e,2)
    for _ in range(stage):press(e,'down')
    press(e,'a');wait(e,3);e.run(180)
    check(e.state()['intro']==0,'Match intro completes',{'mode':mode,'fighter':fighter,'stage':stage})
    return e
def close_in(e,distance=31):
    for _ in range(150):
        s=e.state()
        if abs(s['x1']-s['x2'])<distance*16:break
        e.run(1,p1=['right'] if s['x1']<s['x2'] else ['left'],p2=['left'] if s['x1']<s['x2'] else ['right'])
    e.run(3)
def play_cpu(e):
    for _ in range(10000):
        s=e.state()
        if s['screen']==4:return
        forward='right' if s['x1']<s['x2'] else 'left'
        back='left' if forward=='right' else 'right'
        distance=abs(s['x1']-s['x2'])//16
        if s['intro'] or s['round_end'] or s['hitstop']:e.run(1)
        elif s['action1']:e.run(1,p1=[forward])
        elif s['action2'] and distance<55:e.run(1,p1=[back,'down'] if 4<=s['action2']<=6 else [back])
        elif distance>25:e.run(1,p1=[forward])
        else:e.run(1,p1=[forward,'l']);e.run(1,p1=[forward])
    raise AssertionError(('CPU match did not finish',e.state()))

def actor_payload(e,side=0):
    """Read one actor's ten compact rows, skipping its padded VRAM tail."""
    vram=C.string_at(e.core.retro_get_memory_data(3),65536)
    base=VRAM_ACTOR_BASE+side*VRAM_ACTOR_STRIDE
    return b''.join(vram[base+r*VRAM_ROW_STRIDE:base+r*VRAM_ROW_STRIDE+VRAM_ROW_BYTES]
                    for r in range(10))

def trace_word(e,index):
    data=C.string_at(e.ram+0x1ff00+index*2,2)
    return int.from_bytes(data,'little')

def animation_payloads(fighter):
    """Load all 48 native frames used by the expanded animation cartridge."""
    payloads=[]
    for suffix in ANIMATION_BANK_SUFFIXES:
        data=(ROOT/f'assets/generated/fighter{fighter:02}{suffix}.bin').read_bytes()
        check(len(data)==BANK_BYTES,'Animation bank has eight complete poses',{
            'fighter':fighter,'suffix':suffix,'bytes':len(data)})
        payloads.extend(data[offset:offset+POSE_BYTES]
                        for offset in range(0,BANK_BYTES,POSE_BYTES))
    return payloads

def verify_uploaded_animation(e,fighter,side=0):
    payload=actor_payload(e,side)
    frames=animation_payloads(fighter)
    matches=[index for index,data in enumerate(frames) if data==payload]
    check(matches,'Actor VRAM contains an exact native animation frame',{
        'fighter':fighter,'side':side,'frames':matches})
    return matches

started=time.time()
e=Emulator();e.run(120)
check(e.state()['magic']==0xaaba and e.state()['screen']==0,'Cold boot to title')
e.shot('title.png');press(e,'r');press(e,'r');press(e,'r')
check(e.state()['screen']==0,'Difficulty can cycle without leaving the title')
press(e,'a');wait(e,1);e.shot('select.png')
for i in range(12):
    check(e.state()['selected']==i,'Roster slot '+str(i+1)+' is selectable')
    press(e,'right')
check(e.state()['selected']==0,'Roster wraps after all twelve fighters')
press(e,'a');wait(e,2);e.shot('arenas.png');e.close()

for i in range(12):
    e=boot(2,i,i%3)
    check(e.state()['arena']==i%3,'Arena loads in the emulator',i%3)
    # Compare every streamed OBJ row against the exact cartridge asset bytes.
    vram=C.string_at(e.core.retro_get_memory_data(3),65536)
    verify_uploaded_animation(e,i,0)
    e.shot('arena-'+str(i%3)+'.png')
    if i==0:e.shot('fight.png')
    e.close()

e=boot(2)
s=e.state();e.run(600);advance=(e.state()['frame']-s['frame'])&65535
check(advance>=590,'Gameplay maintains NTSC frame cadence',{'emulated_frames':600,'game_ticks':advance})
e.run(3,p1=['up']);check(e.state()['y1']>32767,'Jump moves fighter above the floor');e.run(12);e.shot('jump.png');e.run(70)
check(e.state()['y1']==0,'Jump lands back on the floor')
e.run(8,p1=['down']);check(e.state()['pose1']==3,'Crouch has a dedicated pose');e.run(8)
for key,action in [('y',1),('x',2),('l',3),('b',4),('a',5),('r',6)]:
    e.run(4,p1=[key]);check(e.state()['action1']==action,'SNES button '+key.upper()+' starts attack '+str(action));e.run(65)
before=e.state()['energy1'];e.run(18,p1=['down','x'])
check(e.state()['wave1']==1 and e.state()['energy1']<before,'Special launches a projectile and spends meter')
e.shot('special.png');e.run(85)
e.run(4,p1=['down','l']);check(e.state()['action1']==8 and e.state()['y1']>32767,'Uppercut leaves the ground');e.run(75)
# Use the same sustained, facing-aware QCF sampled by the focused input suite.
# A one-frame phase is too short for the libretro/Snes9x pad poll and can turn
# this check into an accidental normal attack.
s=e.state();forward='right' if s['x1']<s['x2'] else 'left'
e.run(3,p1=['down']);e.run(3,p1=['down',forward]);before=e.state()['energy1'];e.run(3,p1=[forward,'y']);e.run(10)
check(e.state()['wave1']==1 and e.state()['energy1']<before,'Quarter-circle forward plus punch recognizes a motion input');e.run(90)
press(e,'start');s=e.state();paused_anim=trace_word(e,62);e.run(60)
check(e.state()['paused']==1 and e.state()['seconds']==s['seconds'] and e.state()['x1']==s['x1'] and trace_word(e,62)==paused_anim,'Pause freezes combat and animation')
e.shot('pause.png');press(e,'a');check(e.state()['paused']==0,'A resumes a paused fight')
check(e.audio_peak>1000 and e.audio_samples>10000,'SPC music and sound produce non-silent audio',{'peak':e.audio_peak,'samples':e.audio_samples})
with wave.open(str(ROOT/'docs/screenshots/audio-sample.wav'),'wb') as f:
    f.setnchannels(2);f.setsampwidth(2);f.setframerate(32040);f.writeframes(e.pcm)
e.close()

e=boot(1);close_in(e)
e.run(7,p1=['y']);e.run(5);e.run(3,p1=['x']);e.run(12)
check(e.state()['combo']>=2,'Confirmed light punch cancels into a medium-punch combo',e.state())
e.shot('combo.png');e.close()

e=boot(1,0,1,10)
check(e.state()['selected2']==10,'Player two can select a fighter with controller two')
# P2 uses its own $D400 actor page; compare the complete 384-byte payload of
# every physical row so a truncated lower half cannot pass as a valid sprite.
verify_uploaded_animation(e,10,1)
s=e.state();e.run(20,p2=['left']);check(e.state()['x2']<s['x2'],'Controller two moves player two')
close_in(e)
e.run(12,p1=['x'],p2=['right'])
check(e.state()['hp2']==128,'Holding back blocks a medium punch')
check(e.state()['pose2']==9,'Blocking keeps the defensive animation')
e.shot('block.png');e.run(60);close_in(e)
e.run(12,p1=['down','b'],p2=['right'])
check(e.state()['hp2']<128,'Low attack beats a standing guard');e.run(65);close_in(e)
hp=e.state()['hp2'];e.run(12,p1=['down','b'],p2=['down','right'])
check(e.state()['hp2']==hp,'Crouch block stops a low attack');e.run(65);close_in(e,23)
hp=e.state()['hp2'];e.run(8,p1=['right','l'],p2=['right'])
check(e.state()['hp2']<hp,'Close forward plus heavy punch throws through guard');e.run(65)
e.close()

e=boot(1)
for _ in range(110):
    if e.state()['screen']==4:break
    s=e.state();forward='right' if s['x1']<s['x2'] else 'left'
    e.run(3,p1=[forward,'l']);e.run(28,p1=[forward])
check(e.state()['screen']==4 and e.state()['wins1']==2,'Two round wins finish a best-of-three local match',e.state())
e.shot('victory.png');press(e,'a');wait(e,3)
check(e.state()['wins1']==0 and e.state()['round']==1,'Rematch resets round wins')
e.close()

e=boot(0,4,difficulty=0)
# Controller-only bot: close the gap and throw, observing the same rules as a player.
for _ in range(220):
    if e.state()['screen']==4:break
    s=e.state();forward='right' if s['x1']<s['x2'] else 'left'
    e.run(3,p1=[forward,'l']);e.run(26,p1=[forward])
check(e.state()['screen']==4,'Arcade CPU match reaches a result',e.state())
if e.state()['wins1']!=2:
    press(e,'a');wait(e,3)
    check(e.state()['wins1']==0 and e.state()['wins2']==0,'Arcade continue restarts a lost match')
    # A different art-bank layout can shift boot timing and the CPU's PRNG path.
    # A bot loss must exercise continue, never silently skip the entire ladder.
    for attempt in range(8):
        play_cpu(e)
        if e.state()['wins1']==2:break
        press(e,'a');wait(e,3)
    check(e.state()['wins1']==2,'Arcade player wins after continuing')
press(e,'a');wait(e,3)
check(e.state()['arcade']==1 and e.state()['arena']==1,'Arcade victory advances opponent and arena')
for match in range(1,11):
    for attempt in range(8):
        play_cpu(e)
        if e.state()['wins1']==2:break
        press(e,'a');wait(e,3)
    check(e.state()['screen']==4,'Arcade ladder match '+str(match+1)+' reaches a result',e.state())
    check(e.state()['wins1']==2,'Controller-only player wins ladder match '+str(match+1))
    if match<10:press(e,'a');wait(e,3)
check(e.state()['champion']==1,'Defeating all eleven opponents awards Office Champion')
e.shot('champion.png');press(e,'a');wait(e,0)
check(e.state()['screen']==0,'Champion returns to the title')
e.close()

e=boot(1);e.run(6400)
check(e.state()['seconds']>=90 and e.state()['wins1']==0 and e.state()['wins2']==0,'A tied timeout starts another round without awarding a win',e.state())
e.close()

manifest=json.loads((ROOT/'dist/manifest.json').read_text())
check(manifest.get('bytes')==4*1024*1024,'Native ROM uses the 4 MiB animation FastROM image',manifest)
report={'emulator':'Official Snes9x 1.63 x64 libretro core','rom_sha256':manifest['sha256'],'rom_bytes':manifest.get('bytes'),
        'passed':len(checks),'elapsed_seconds':round(time.time()-started,2),'checks':checks}
(ROOT/'docs/test-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'passed':len(checks),'seconds':report['elapsed_seconds'],'frame_cadence':advance,'report':'docs/test-report.json'}))
