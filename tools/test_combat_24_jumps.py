"""Isolated v0.24 jump art/motion proof, real two-port input, no WRAM writes.

Run with canonical Python via tools/run_background.py after tools/build.py
--assets. The shared animation Probe reads native SDK timing, OAM and actor
VRAM pages; its historical visual_checks are deliberately not invoked here.
"""
from pathlib import Path
import ctypes as C
import hashlib,io,json,subprocess,sys,time
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from test_characters import boot,state
from test_inputs import signed16
from test_champion import host_contract
from test_expansion_01_animation_weight import Probe,symbols,address
from fighter_assets import extract_atlas,HEIGHTS

BASE='f75005d';OUT=ROOT/'docs/screenshots/combat-24-jumps'
TARGET={29,30,31,*range(49,56)};checks=[]
PHYSICS={1:(-84,-96),4:(-82,-86),6:(-80,-86),9:(-84,-105)}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(path):return subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT)
def check(ok,label,detail=None):
 checks.append({'passed':bool(ok),'check':label,'detail':detail})
 if not ok:raise AssertionError((label,detail))

class JumpProbe(Probe):
 def __init__(self,e,i,table,base):
  super().__init__(e,i,table,base);self.audio_failures=[];self.max_backlog=0
  self.read=address(table,'spc_fread');self.write=address(table,'spc_fwrite')
  if self.read>=0x7e0000:self.read-=0x7e0000
  if self.write>=0x7e0000:self.write-=0x7e0000
 def step(self,*args,**kwargs):
  samples=self.e.audio_samples;s=super().step(*args,**kwargs)
  label=args[2] if len(args)>2 else kwargs.get('label','')
  if self.base and self.fighter==0 and label in ('jump','air-a'):
   self.clips.setdefault(label,[]).append((self.e.frame.copy(),dict(self.rows[-1])))
  queued=(C.string_at(self.e.ram+self.write,1)[0]-C.string_at(self.e.ram+self.read,1)[0])&255
  self.max_backlog=max(self.max_backlog,queued)
  if self.e.audio_samples==samples or queued>6:self.audio_failures.append({'frame':s['frame'],'backlog':queued,'PCM_samples':self.e.audio_samples-samples})
  return s

def art():
 result=[];index=json.loads((ROOT/'assets/art/jump-v1.json').read_bytes())
 for row in index['fighters']:
  i=row['id'];name=f'assets/generated/fighter{i:02d}'
  before=Image.open(io.BytesIO(git(name+'.png'))).convert('RGBA')
  after=Image.open(ROOT/(name+'.png')).convert('RGBA');changed=[]
  check(before.size==after.size==(6144,80),'native canvas unchanged',i)
  for n in range(64):
   a=before.crop((n*96,0,(n+1)*96,80));b=after.crop((n*96,0,(n+1)*96,80))
   if a.tobytes()!=b.tobytes():changed.append(n)
   if n in TARGET:
    box=b.getchannel('A').getbbox()
    check(box and box[3]==78 and box[0]>0 and box[2]<96,'whole pose has sole baseline and safe margins',[i,n,box])
    check(all(b.getchannel('A').crop((0,y,96,y+1)).getbbox() for y in range(box[1],box[3])),'full silhouette has no detached body row',[i,n])
  check(set(changed)==TARGET,'exactly ten jump-owned poses changed',[i,changed])
  packed_changes=[]
  for bank,suffix in enumerate(('','b','c','d','e','f','g','h')):
   path=name+suffix+'.bin';a=git(path);b=(ROOT/path).read_bytes()
   check(len(a)==len(b)==30720,'eight fixed 30,720-byte pose banks retained',[i,bank])
   for frame in range(8):
    if a[frame*3840:(frame+1)*3840]!=b[frame*3840:(frame+1)*3840]:packed_changes.append(bank*8+frame)
  check(set(packed_changes)==TARGET,'packed SNES bytes preserve walking idle and every unowned frame',[i,packed_changes])
  check(git(name+'_pal.bin')==(ROOT/(name+'_pal.bin')).read_bytes(),'fixed OBJ palette byte-exact',i)
  for suffix in ('','-large','_tiles','_pal'):
   p=f'assets/generated/portrait{i:02d}{suffix}'+('.png' if suffix in ('','-large') else '.bin')
   check(git(p)==(ROOT/p).read_bytes(),'portrait byte-exact',p)
  record=json.loads((ROOT/row['provenance']).read_bytes());figs,details=extract_atlas(ROOT/record['sources'][0]['file'],pose_names=record['sources'][0]['poses'])
  scale=HEIGHTS[i]/figs[record['anchor']['pose']].height
  meta=json.loads((ROOT/'assets/generated/character-manifest.json').read_bytes())[i]
  # Generator metadata is authoritative evidence of the conversion actually used.
  frames=meta['frames']
  check(all(frames[n]['conversion_scale']==scale for n in TARGET),'one neutral-anchored isotropic scale for all ten poses',[i,scale])
  check(record['height_target']==HEIGHTS[i],'neutral anchor exact approved height',[i,HEIGHTS[i]])
  result.append({'fighter':i,'changed_frames':changed,'packed_changed_frames':packed_changes,'scale':scale,'height_target':HEIGHTS[i]})
 return result

def session(i,rom,table,base=False):
 e=boot(1,i,stage=i%3,fighter2=i,rom=rom);p=JumpProbe(e,i,table,base)
 def run(n=1,k1=(),k2=(),label='quiet',film=False):
  p.run(n,k1,k2,label,film);return state(e)
 def drive(port,keys=(),n=1,label='contact'):
  return run(n,keys if port==0 else (),keys if port==1 else (),label,not base and i==0)
 def wait_ground():
  for _ in range(110):
   s=state(e)
   if all(s[f'y{a}']==0 and not s[f'action{a}'] and not s[f'hurt{a}'] and not s[f'down_state{a}'] for a in (1,2)):break
   run()
  else:raise AssertionError(('ground timeout',i,state(e)))
  run(12)
 def spread():
  wait_ground();s=state(e)
  run(125,['left'] if s['x1']<s['x2'] else ['right'],['right'] if s['x1']<s['x2'] else ['left']);run(6)
 try:
  run(3,['up'],['up'],'jump',True);run(82,label='jump',film=True)
  if not base:
   for a in (1,2):
    rows=[r for r in p.rows if r['label']=='jump'];seq=[r[f'anim_frame{a}'] for r in rows]
    first=[seq.index(n) for n in (29,30,55,54,31)]
    check(first==sorted(first),'takeoff rise apex descent landing order',[i,a,first])
    check(all(r[f'anim_frame{a}']==31 for r in rows if r[f'landing{a}']),'compression only at actual floor',[i,a])
    release=[r for r in rows if r[f'anim_state{a}']==15]
    check(release and all(r[f'y{a}']==0 and r[f'anim_frame{a}']==54 for r in release),'grounded landing releases through extended legs',[i,a])
    check(all(r[f'anim_frame{a}']==30 for r in rows if r[f'anim_tick{a}']>2 and r[f'vy{a}'] < -32 and signed16(r[f'y{a}'])<0),'rising guard follows velocity',[i,a])
  for key in ('y','x','b','a'):
   label='air-'+key;run(3,['up'],['up'],label,True);run(3,label=label,film=True)
   run(3,[key],[key],label,True);run(75,label=label,film=True)
   if not base:
    for a in (1,2):
     frames={r[f'anim_frame{a}'] for r in p.rows if r['label']==label}
     expected={49,50,51} if key in ('y','x') else {52,53,54}
     check(expected<=frames,'both ports stream windup/contact/recovery',[i,a,key,sorted(frames)])
  arcs=[]
  for port in (0,1):
   a=str(port+1);d=str(2-port);wait_ground()
   forward='right' if state(e)[f'face{a}'] else 'left';sign=1 if forward=='right' else -1
   # A fixed 24px approach, independent of tuned jump values, proves that
   # ordinary diagonal jumps can cross a standing opponent on both ports.
   for _ in range(180):
    s=state(e)
    if abs(s['x1']-s['x2'])<=24*16:break
    drive(port,[forward],label='cross-approach')
   # Move a pair near the wall to open ground before measuring.
   center=(state(e)['x1']+state(e)['x2'])//32
   if center>185:run(60,['left'],['left'],'cross-center')
   elif center<70:run(60,['right'],['right'],'cross-center')
   run(3);initial=state(e);label=f'cross-arc-{port}'
   drive(port,['up',forward],label=label);arc=[]
   for _ in range(90):
    s=state(e);arc.append(s)
    if s[f'landing{a}']:break
    run(label=label)
   crossed=any((s[f'x{a}']-s[f'x{d}'])*sign>0 for s in arc)
   evidence={'port':port,'jump_vy':signed16(initial[f'jump{a}']),'apex_pixels':-min(signed16(s[f'y{a}']) for s in arc)/16,'flight_samples':len(arc),'standing_crossed':crossed,'clearance_samples':sum(signed16(s[f'y{a}'])<=-50*16 for s in arc)}
   if not base:check(crossed,'ordinary diagonal jump crosses standing opponent',[i,evidence])
   arcs.append(evidence);run(14)
  p.arcs=arcs;spread()
  # Both corner landings retain floor clamp; inward pad changes cannot steer.
  run(180,['left'],['right']);run(3,['up','left'],['up','right'],'corner',True)
  run(60,['right'],['left'],'corner',True);run(12)
  if not base:
   rows=[r for r in p.rows if r['label']=='corner']
   check(all(24*16<=r['non_animation_trace'][f'x{a}']<=232*16 for r in rows for a in (1,2)),'corner flight clamps inside both walls',i)
   check(all(r['non_animation_trace']['jump_vx1']>=32768 and 0<r['non_animation_trace']['jump_vx2']<32768 for r in rows if r['y1'] and r['y2']),'opposite held pad does not add midair steering',i)
  # Landing jump buffer: queue and RELEASE the edge before ground contact.
  spread();run(3,['up'],['up'],'buffer-jump')
  for _ in range(90):
   s=state(e);last=p.rows[-1]
   if -16*16<signed16(s['y1'])<0 and last['vy1']>0:break
   run(label='buffer-jump')
  run(1,['up'],['up'],'buffer-jump');queued=state(e);run(1,label='buffer-jump')
  run(24,label='buffer-jump');run(65)
  check(queued['jump_buffer1'] and queued['jump_buffer2'],'both ports capture released landing jump edge',i)
  rows=[r for r in p.rows if r['label']=='buffer-jump']
  floor=next((n for n,r in enumerate(rows) if r['landing1']),None)
  check(floor is not None and any(signed16(r['y1'])<0 and signed16(r['y2'])<0 for r in rows[floor+1:]),'both ports consume buffer into second jump',i)
  # Fresh attacks cancel visual release without waiting its six samples.
  spread();run(3,['up'],['up'],'release-cancel')
  for _ in range(90):
   if state(e)['landing1']==1:break
   run(label='release-cancel')
  run(label='release-cancel');run(1,['y'],['y'],'release-cancel');accepted=state(e)
  check(accepted['action1']==accepted['action2']==1,'punch accepted immediately during landing release',i);run(50)
  # A RELEASED recovery tap must execute after the preceding action ends.
  spread();run(3,['x'],['x'],'buffer-attack')
  for _ in range(80):
   r=p.rows[-1]
   if r['action1'] and r['tick1']+4>=r['action_end1']:break
   run(label='buffer-attack')
  run(1,['y'],['y'],'buffer-attack');queued=state(e);run(1,label='buffer-attack')
  run(9,label='buffer-attack');rows=[r for r in p.rows if r['label']=='buffer-attack']
  check(queued['buffered_action1']==queued['buffered_action2']==1,'both ports queue recovery attack tap',i)
  check(any(r['action1']==r['action2']==1 for r in rows),'both ports execute released recovery attack buffer',i);run(45)
  # Active air punch/front strong kick and short rear A on every fighter/port.
  contacts=[]
  for port in (0,1):
   a=str(port+1);d=str(2-port)
   for key,rear in (('y',False),('a',False),('a',True)):
    spread()
    forward='right' if state(e)[f'face{a}'] else 'left';sign=1 if forward=='right' else -1
    gap=24 if key=='y' or rear else 40
    for _ in range(220):
     s=state(e)
     if abs(s['x1']-s['x2'])<=gap*16:break
     drive(port,[forward],label='approach')
    # A rear contact requires space beyond the defender. Shift the pair off
    # the outward wall with ordinary movement, then release before takeoff.
    if rear:
     back='left' if forward=='right' else 'right'
     run(60,[back],[back],'rear-center')
    run(3);initial=state(e);hp=initial[f'hp{d}'];label=f'p{a}-{key}-'+('rear' if rear else 'front')
    drive(port,['up',forward] if rear else ['up',key],label=label)
    sent=not rear;contact=None;rows=[]
    for t in range(84):
     s=state(e);crossed=(s[f'x{a}']-s[f'x{d}'])*sign>0;keys=[]
     # Cote's eight-sample windup needs its edge just before crossing to
     # retain the short rear box. The other arcs start after crossing so the
     # active window overlaps the standing body on descent, below the apex.
     will_cross=(s[f'x{a}']+signed16(s[f'jump_vx{a}'])-s[f'x{d}'])*sign>0
     if not sent and rear and (crossed or (i==3 and will_cross)):keys=[key];sent=True
     s=drive(port,keys,label=label);rows.append(s)
     # connected persists after a prior attack until the next attack starts;
     # identify a NEW contact from actual HP loss, never the stale latch.
     if contact is None and s[f'connected{a}']==2 and s[f'hp{d}']<hp:contact=s
    if not (base and i in PHYSICS and rear):
     check(contact is not None and contact[f'hp{d}']<hp,'air normal produces actual contact',{'fighter':i,'port':port,'key':key,'rear':rear,'initial':{k:initial[k] for k in ('x1','x2','face1','face2','hp1','hp2')},'active':[{k:s[k] for k in ('x1','x2','y1','y2','action1','action2','anim_frame1','anim_frame2','connected1','connected2','hp1','hp2')} for s in rows if s[f'anim_frame{a}'] in (50,53)]})
    if not base:check(contact[f'anim_frame{a}']==(50 if key=='y' else 53),'contact uses dedicated active drawing',[i,port,key,rear,contact[f'anim_frame{a}']])
    if not base and rear:check((contact[f'x{a}']-contact[f'x{d}'])*sign>0,'strong kick contacts behind locked takeoff facing',[i,port])
    check(all(s[f'face{a}']==initial[f'face{a}'] for s in rows if signed16(s[f'y{a}'])<0),'air attack locks takeoff facing',[i,port,key,rear])
    check(rows[-1][f'y{a}']==rows[-1][f'air_action{a}']==rows[-1][f'action{a}']==0,'air normal clears on landing',[i,port,key,rear])
    contacts.append({'port':port,'key':key,'rear':rear,'contact':contact})
  # Throw, floor, get-up and released wake jump on all fighters, both ports.
  for victim in (0,1):
   wait_ground();p.close();run(4);attacker=1-victim
   forward='right' if state(e)[f'face{attacker+1}'] else 'left'
   drive(attacker,[forward,'x'],3,'wake')
   for _ in range(180):
    if state(e)[f'down_state{victim+1}']==5:break
    run(label='wake')
   else:raise AssertionError(('wake timeout',i,victim,state(e)))
   drive(victim,['up'],1,'wake');queued=state(e);run(label='wake')
   check(queued[f'wake_jump{victim+1}']>0,'wake captures single released jump edge',[i,victim])
   woke=False
   for _ in range(20):
    s=run(label='wake')
    if signed16(s[f'y{victim+1}'])<0:woke=True;break
   check(woke,'released wake jump executes after get-up',[i,victim]);run(80)
  return p,contacts
 finally:e.close()

def main():
 started=time.monotonic();OUT.mkdir(parents=True,exist_ok=True)
 candidate=ROOT/'build/v024-jumps.sfc';candidate.write_bytes((ROOT/'dist/abaqus-after-hours.sfc').read_bytes())
 old=ROOT/'build/v024-jumps-baseline.sfc';old.write_bytes(git('dist/abaqus-after-hours.sfc'))
 oldsym=ROOT/'build/v024-jumps-baseline.sym';oldsym.write_bytes(git('dist/abaqus-after-hours.sym'))
 table=symbols(ROOT/'dist/abaqus-after-hours.sym');base_table=symbols(oldsym)
 report={'status':'failed','scope':'isolated jump-v1 only; no combined pass claim','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'source_files_sha256':{p:sha((ROOT/p).read_bytes()) for p in ('src/animation_weight.h','src/characters.h','tools/test_combat_24_jumps.py')},'rom_sha256':sha(candidate.read_bytes()),'baseline_commit':BASE,'baseline_rom_sha256':sha(old.read_bytes()),'command':'D:/snes-abaqus-fighter/.tools/python/python.exe tools/run_background.py --log build/combat-24-jumps.log -- D:/snes-abaqus-fighter/.tools/python/python.exe tools/test_combat_24_jumps.py','host':host_contract(),'checks':checks,'cases':[],'failures':[]}
 try:
  report['art']=art()
  report['active_air_frames']={'punch':50,'kick':53,'active_phase_cycling':False}
  report['rom_header_checksum']=f'{int.from_bytes(candidate.read_bytes()[0x7fde:0x7fe0],"little"):04X}'
  report['build_command']='D:/snes-abaqus-fighter/.tools/python/python.exe tools/run_background.py --log build/jump-frozen-build.log -- D:/snes-abaqus-fighter/.tools/python/python.exe tools/build.py --assets'
  original=git('src/characters.h').decode().replace('\r\n','\n');expected=original
  for a,b in [('17,12,-84,5,-66','17,12,-96,5,-66'),('16,11,-82,4,-64','16,11,-86,4,-64'),('17,12,-80,4,-65','17,12,-86,4,-65'),('18,12,-84,6,-68','18,12,-105,6,-68')]:expected=expected.replace(a,b)
  check((ROOT/'src/characters.h').read_text()==expected,'only four measured jumpVy values differ; all other profiles/physics fields exact')
  report['jumpVy_changes']={i:{'before':v[0],'after':v[1]} for i,v in PHYSICS.items()}
  report['native_core_sha256']=sha((ROOT/'.tools/core/snes9x_libretro.dll').read_bytes())
  report['shared_harness_sha256']={name:sha((ROOT/'tools'/name).read_bytes()) for name in ('emulator.py','test_expansion_01_animation_weight.py','test_characters.py','test_inputs.py')}
  prior_ram={k:v for k,v in base_table.items() if 0x7e0000<=v<0x800000}
  moved={k:[v,table.get(k)] for k,v in prior_ram.items() if table.get(k)!=v}
  check(not moved,'all prior WRAM symbols retain exact address',moved)
  report['prior_RAM_labels']=len(prior_ram);report['moved_RAM_labels']=moved
  for i in range(12):
   before,baseline_contacts=session(i,old,base_table,True);after,contacts=session(i,candidate,table)
   same=before.game_hash.hexdigest()==after.game_hash.hexdigest()
   if i not in PHYSICS:check(same,'unchanged profile preserves every non-animation Fighter byte and trace sample',i)
   else:check(not all(a['standing_crossed'] for a in before.arcs) and all(a['standing_crossed'] for a in after.arcs),'measured baseline cross-up limitation repaired on both ports',[i,before.arcs,after.arcs])
   for name,failures in [('cadence',after.drops),('native_timing',after.native_failures),('OBJ_overflow',after.overflow),('actor_payload',after.bad_payload),('OAM_geometry',after.geometry),('SPC_PCM_cadence',after.audio_failures)]:
    check(not failures,name+' failure array empty',[i,failures[:8]])
   check(not after.uploads[2],'at most one 3840B actor page changes per vblank',[i,dict(after.uploads)])
   captures=[]
   if i==0:
    for label,clip in after.clips.items():
     if not clip:continue
     path=OUT/(label+'.gif');frames=[x[0] for x in clip]
     frames[0].save(path,save_all=True,append_images=frames[1:],duration=17,loop=0,optimize=False)
     captures.append(path.relative_to(ROOT).as_posix())
    for label in ('jump','air-a'):
     frames=[]
     for (a,_),(b,_) in zip(before.clips[label],after.clips[label]):
      pair=Image.new('RGB',(512,224));pair.paste(a,(0,0));pair.paste(b,(256,0));frames.append(pair)
     path=OUT/(label+'-before-after.gif')
     frames[0].save(path,save_all=True,append_images=frames[1:],duration=17,loop=0,optimize=False)
     captures.append(path.relative_to(ROOT).as_posix())
   report['cases'].append({'fighter':i,'both_ports':True,'samples':len(after.rows),'simulation_sha256':after.game_hash.hexdigest(),'simulation_baseline_equal':same,'intentional_jumpVy_change':i in PHYSICS,'baseline_arcs':before.arcs,'candidate_arcs':after.arcs,'baseline_contacts':baseline_contacts,'contacts':contacts,'uploads':dict(after.uploads),'native_timing_failures':after.native_failures,'cadence_failures':after.drops,'OBJ_failures':after.overflow,'payload_failures':after.bad_payload,'geometry_failures':after.geometry,'SPC_PCM_failures':after.audio_failures,'max_SPC_backlog':after.max_backlog,'captures':captures})
   print(json.dumps({'fighter':i,'samples':len(after.rows),'checks':len(checks)}),flush=True)
  names=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE,'assets/generated'],cwd=ROOT,text=True).splitlines()
  report['generated_delta']=[name for name in names if git(name)!=(ROOT/name).read_bytes()]
  report['generated_count']=len(names);report['status']='passed'
 except Exception as exc:report['failures'].append(repr(exc));raise
 finally:
  report['elapsed_seconds']=round(time.monotonic()-started,3);report['check_count']=len(checks)
  (ROOT/'docs/combat-24-jumps-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
  print(json.dumps({'status':report['status'],'checks':len(checks),'rom_sha256':report['rom_sha256'],'failures':report['failures']}),flush=True)
if __name__=='__main__':main()
