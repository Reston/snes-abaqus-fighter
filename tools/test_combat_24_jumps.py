"""Combined v0.24 jump art/motion proof, real two-port input, no WRAM writes.

Run with canonical Python via tools/run_background.py after tools/build.py
--assets. The shared animation Probe reads native SDK timing, OAM and actor
VRAM pages. Historical PPU clips are visual references, never evidence of
unchanged combined gameplay. --fighter N writes only an ignored diagnostic.
"""
from pathlib import Path
import ctypes as C
import argparse,hashlib,io,json,re,subprocess,sys,time
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from test_characters import boot,state
from test_inputs import signed16
from test_champion import host_contract
from test_expansion_01_animation_weight import Probe,symbols,address
from fighter_assets import extract_atlas,HEIGHTS
from expansion_contracts import combined_contract
from v024_contracts import FRAME_OWNERS
from test_endurance import core_identity

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
 check(index['schema']==1 and index['scope']=='jump-v1' and index['baseline_commit']==BASE and
       sorted(row['id'] for row in index['fighters'])==list(range(12)),'complete versioned jump index')
 manifest=json.loads((ROOT/'assets/generated/character-manifest.json').read_bytes())
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
    check(box and box[3]==78 and box[0]>0 and box[2]<96 and box[3]-box[1]<=77,'whole pose has sole baseline and safe margins',[i,n,box])
    check(all(b.getchannel('A').crop((0,y,96,y+1)).getbbox() for y in range(box[1],box[3])),'full silhouette has no detached body row',[i,n])
  check(set(changed)&TARGET==TARGET,'all ten jump-owned poses change within combined allocation',[i,changed])
  packed_changes=[]
  for bank,suffix in enumerate(('','b','c','d','e','f','g','h')):
   path=name+suffix+'.bin';a=git(path);b=(ROOT/path).read_bytes()
   check(len(a)==len(b)==30720,'eight fixed 30,720-byte pose banks retained',[i,bank])
   for frame in range(8):
    if a[frame*3840:(frame+1)*3840]!=b[frame*3840:(frame+1)*3840]:packed_changes.append(bank*8+frame)
  check(set(packed_changes)&TARGET==TARGET,'all ten jump drawings reach packed native banks',[i,packed_changes])
  check(git(name+'_pal.bin')==(ROOT/(name+'_pal.bin')).read_bytes(),'fixed OBJ palette byte-exact',i)
  for suffix in ('','-large','_tiles','_pal'):
   p=f'assets/generated/portrait{i:02d}{suffix}'+('.png' if suffix in ('','-large') else '.bin')
   check(git(p)==(ROOT/p).read_bytes(),'portrait byte-exact',p)
  provenance=ROOT/row['provenance'];record=json.loads(provenance.read_bytes())
  check(sha(provenance.read_bytes())==row['provenance_sha256'],'exact individual jump provenance hash',i)
  check(record['fighter_id']==i and record['scope']=='jump-v1','individual jump source identity',i)
  check(sha((ROOT/record['reference']).read_bytes())==record['reference_sha256'],'exact retained reference hash',i)
  check(sha((ROOT/(name+'_pal.bin')).read_bytes())==record['palette_sha256'],'palette hash binds source conversion',i)
  sources=[];target=[]
  for si,source in enumerate(record['sources']):
   path=ROOT/source['file'];raw=path.read_bytes()
   check(sha(raw)==source['sha256'] and (len(record['sources'])!=1 or sha(raw)==record['raw_output_sha256']),
         'selected jump PNG is exact retained built-in output',[i,si])
   figs,details=extract_atlas(path,pose_names=source['poses'],expected_count=source['count'])
   check(len(figs)==source['count'] and source['count'] in (8,16),'complete connected source figures',[i,si])
   width,height=Image.open(path).size
   check(all(0<m['source_box'][0]<m['source_box'][2]<width and 0<m['source_box'][1]<m['source_box'][3]<height for m in details),
         'jump source figures have transparent edge clearance',[i,si])
   sources.append((source,figs,details));target.extend(n for n in source['frames'] if n is not None)
  check(len(target)==len(set(target))==10 and set(target)==TARGET,'disjoint jump source-to-native mapping',i)
  scale=HEIGHTS[i]/sources[record['anchor']['source']][1][record['anchor']['pose']].height
  frames=manifest[i]['frames'];bounds=[]
  for source,figs,details in sources:
   for figure,detail,n in zip(figs,details,source['frames']):
    if n is None:continue
    frame=frames[n];size=[round(figure.width*scale),round(figure.height*scale)]
    check(frame['source_kind']=='jump-v1' and frame['source_file']==source['file'] and frame['source_sha256']==source['sha256'] and
          frame['revision_source_box']==list(detail['source_box']),
          'own native frame binds selected jump source',[i,n])
    pose=after.crop((n*96,0,(n+1)*96,80));bbox=pose.getchannel('A').getbbox()
    check(frame['conversion_scale']==scale and frame['native_size']==[bbox[2]-bbox[0],bbox[3]-bbox[1]] and
          frame['native_size'][0]<=size[0]<=94 and frame['native_size'][1]<=size[1]<=77,
          'one neutral-anchored isotropic scale fits all jump poses',[i,n,size,scale])
    bounds.append({'frame':n,'native_box':list(pose.getchannel('A').getbbox()),'native_rgba_sha256':sha(pose.tobytes())})
  check(record['height_target']==HEIGHTS[i],'neutral anchor exact approved height',[i,HEIGHTS[i]])
  result.append({'fighter':i,'owned_changed_frames':sorted(set(changed)&TARGET),'combined_changed_frames':changed,
                 'packed_owned_changed_frames':sorted(set(packed_changes)&TARGET),'scale':scale,'height_target':HEIGHTS[i],
                 'native_bounds':bounds,'sources':[{'file':s['file'],'sha256':s['sha256'],'source_boxes':[d['source_box'] for d in details]} for s,_,details in sources]})
 return result

def profile_fields(raw):
 """Read scalar profile fields independently of authorized movement/timing edits."""
 text=re.sub(r'/\*.*?\*/|//[^\n]*','',raw,flags=re.S)
 match=re.search(r'const\s+CharacterProfile\s+characterProfiles\s*\[12\]\s*=\s*\{',text)
 if not match:raise AssertionError('missing twelve-profile initializer')
 rows=[];depth=1;start=None
 for at in range(match.end(),len(text)):
  if text[at]=='{':
   depth+=1
   if depth==2:start=at+1
  elif text[at]=='}':
   if depth==2:
    values=text[start:at].split('{',1)[0].split(',')
    rows.append({key:int(values[n].strip()) for key,n in (('walkSpeed',0),('jumpVy',2),('gravity',3),('uppercutVy',4),('specialVy',15))})
   depth-=1
   if depth==0:break
 check(len(rows)==12,'physics parser reads all twelve independent profiles',len(rows))
 return rows

def physics_contract():
 before=profile_fields(git('src/characters.h').decode());after=profile_fields((ROOT/'src/characters.h').read_text())
 result=[]
 for i,(old,current) in enumerate(zip(before,after)):
  expected=PHYSICS[i][1] if i in PHYSICS else old['jumpVy']
  if i in PHYSICS:check(old['jumpVy']==PHYSICS[i][0],'historical measured jumpVy matches approved input',[i,old])
  check(current['jumpVy']==expected,'only four approved vertical jump launch changes',[i,old['jumpVy'],current['jumpVy'],expected])
  for key in ('gravity','uppercutVy','specialVy'):
   check(current[key]==old[key],'other vertical physics field remains exact',[i,key,old[key],current[key]])
  result.append({'fighter':i,'before_jumpVy':old['jumpVy'],'jumpVy':expected,'gravity':current['gravity'],
                 'retained_horizontal_launch':old['walkSpeed']+8})
 return result

def session(i,rom,table,base=False,physics=None):
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
     active=[r for r in p.rows if r['label']==label and r['non_animation_trace'][f'air_action{a}'] and
             r[f'startup{a}']<=r[f'tick{a}']<r[f'active_end{a}']]
     check(active and all(r[f'anim_frame{a}']==(50 if key in ('y','x') else 53) for r in active),
           'air normal keeps dedicated active frame throughout real contact window',[i,a,key])
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
   if not base:
    check(crossed,'ordinary diagonal jump crosses standing opponent',[i,evidence])
    if physics is not None:
     check(evidence['jump_vy']==physics['jumpVy'],'native profile exposes approved jumpVy',[i,evidence,physics])
     launch=[signed16(s[f'jump_vx{a}']) for s in arc if signed16(s[f'y{a}'])<0]
     check(launch and all(v==sign*physics['retained_horizontal_launch'] for v in launch),
           'diagonal arc retains original horizontal launch without midair steering',[i,port,launch,physics])
     evidence['horizontal_launch']=launch[0]
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

def historical_visuals(i,rom,table):
 """Fixed historical visual samples only; no old gameplay-equality gate."""
 e=boot(1,i,stage=i%3,fighter2=i,rom=rom);p=JumpProbe(e,i,table,True)
 try:
  p.run(3,['up'],['up'],'jump');p.run(82,label='jump')
  for key in ('y','x','b','a'):
   label='air-'+key;p.run(3,['up'],['up'],label);p.run(3,label=label)
   p.run(3,[key],[key],label);p.run(75,label=label)
  return p
 finally:e.close()

def save_clips(after,before):
 captures=[];ms=1000/60.098811862348406
 def save(path,frames,**metadata):
  durations=[10*(round((i+1)*ms/10)-round(i*ms/10)) for i in range(len(frames))]
  frames[0].save(path,save_all=True,append_images=frames[1:],duration=durations,loop=0,optimize=False)
  captures.append({'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path.read_bytes()),'native_callbacks':len(frames),
                   'playback':'10/20 ms cumulative GIF approximation to native 60.098811862348406 Hz',**metadata})
 for label,clip in after.clips.items():
  if not clip:continue
  frames=[]
  for image,_ in clip:
   frame=Image.new('RGB',(256,244));frame.paste(image,(0,20))
   ImageDraw.Draw(frame).text((5,4),'COMBINED v0.24 '+label,fill='white');frames.append(frame)
  save(OUT/('combined-'+label+'.gif'),frames,scope='current combined native PPU')
 for label in ('jump','air-a'):
  frames=[]
  a=before.clips[label];b=after.clips[label]
  check(len(a)==len(b),'historical/current visual segments have identical fixed input length',[label,len(a),len(b)])
  for (left,_),(right,_) in zip(a,b):
   pair=Image.new('RGB',(512,244));pair.paste(left,(0,20));pair.paste(right,(256,20));draw=ImageDraw.Draw(pair)
   draw.text((5,4),'HISTORICAL v0.23.1 '+label,fill='white');draw.text((261,4),'COMBINED v0.24 '+label,fill='white');frames.append(pair)
  save(OUT/(label+'-combined-vs-historical.gif'),frames,left='HISTORICAL v0.23.1',right='combined v0.24',
       comparison='presentation only; authorized pacing/contact/jump/super/stage behavior differs')
 return captures

def main():
 global OUT
 parser=argparse.ArgumentParser();parser.add_argument('--fighter',type=int,choices=range(12));parser.add_argument('--report',type=Path);args=parser.parse_args()
 checks.clear();started=time.monotonic();(ROOT/'build').mkdir(exist_ok=True)
 report_path=ROOT/(args.report or ('build/combat24-jumps-diagnostic.json' if args.fighter is not None else 'docs/combat-24-jumps-report.json'))
 if args.fighter is not None and not report_path.resolve().is_relative_to((ROOT/'build').resolve()):
  parser.error('--fighter diagnostics must write under ignored build/, never final docs evidence')
 report_path.parent.mkdir(parents=True,exist_ok=True)
 if args.fighter is not None:OUT=report_path.parent/(report_path.stem+'-captures')
 OUT.mkdir(parents=True,exist_ok=True)
 candidate=ROOT/'build/v024-jumps.sfc';candidate.write_bytes((ROOT/'dist/abaqus-after-hours.sfc').read_bytes())
 old=ROOT/'build/v024-jumps-baseline.sfc';old.write_bytes(git('dist/abaqus-after-hours.sfc'))
 oldsym=ROOT/'build/v024-jumps-baseline.sym';oldsym.write_bytes(git('dist/abaqus-after-hours.sym'))
 table=symbols(ROOT/'dist/abaqus-after-hours.sym');base_table=symbols(oldsym)
 manifest=json.loads((ROOT/'dist/manifest.json').read_bytes());producer='tools/test_combat_24_jumps.py'
 report={'status':'failed','scope':'combined v0.24 jump art, physics, landing and both-port air contacts','diagnostic':args.fighter is not None,'full_roster':args.fighter is None,
         'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
         'source_diff_sha256':sha(subprocess.check_output(['git','diff','HEAD','--','src','tools','assets/art'],cwd=ROOT)),
         'producer':producer,'producer_sha256':sha(Path(__file__).read_bytes()),'harness_sha256':sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n')),
         'source_files_sha256':{p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in sorted((ROOT/'src').iterdir()) if p.is_file()},
         'rom_sha256':sha(candidate.read_bytes()),'rom_bytes':candidate.stat().st_size,'checksum':manifest['checksum'],
         'baseline_commit':BASE,'baseline_rom_sha256':sha(old.read_bytes()),'baseline_role':'historical presentation comparison only; no gameplay equality claim',
         'command':subprocess.list2cmdline([sys.executable,*sys.argv]),'host':host_contract(),'checks':checks,'cases':[],'failures':[]}
 report['dependency_sha256']={p:sha((ROOT/p).read_bytes()) for p in ('tools/emulator.py','tools/test_expansion_01_animation_weight.py','tools/test_characters.py','tools/test_inputs.py','tools/test_champion.py','tools/test_presentation.py','tools/test_endurance.py','tools/release_evidence.py','tools/fighter_assets.py','tools/pose_revision_assets.py','tools/expansion_contracts.py','tools/v024_contracts.py','tools/run_background.py','dist/abaqus-after-hours.sym','dist/manifest.json','assets/art/jump-v1.json')}
 inputs={'assets/generated/character-manifest.json','.tools/core/snes9x_libretro.dll'}
 for row in json.loads((ROOT/'assets/art/jump-v1.json').read_bytes())['fighters']:
  inputs.add(row['provenance']);record=json.loads((ROOT/row['provenance']).read_bytes());inputs.add(record['reference'])
  inputs.update(source['file'] for source in record['sources']);stem=f'assets/generated/fighter{row["id"]:02d}'
  inputs.update(stem+suffix for suffix in ('.png','_pal.bin','.bin','b.bin','c.bin','d.bin','e.bin','f.bin','g.bin','h.bin'))
 report['dependency_sha256'].update({p:sha((ROOT/p).read_bytes()) for p in sorted(inputs)})
 report['behavioral_proof']='Current both-port physical jump/cross-up/air-normal/buffer/wake/landing assertions; authorized combined changes invalidate historical non-animation replay equality.'
 try:
  check(report['rom_sha256']==manifest['sha256'] and report['rom_bytes']==4194304 and manifest['version']=='0.24.0','exact manifest identifies combined native 4 MiB ROM')
  report['combined_contract']=combined_contract(ROOT)
  check(report['combined_contract']['assets']['frame_ownership']=={scope:sorted(frames) for scope,frames in FRAME_OWNERS.items()},'strict parent policy covers all three disjoint frame owners')
  report['native_contract']=report['combined_contract']['native']
  report['art']=art()
  report['active_air_frames']={'punch':50,'kick':53,'active_phase_cycling':False}
  report['rom_header_checksum']=f'{int.from_bytes(candidate.read_bytes()[0x7fde:0x7fe0],"little"):04X}'
  physics=physics_contract();report['physics']=physics
  report['jumpVy_changes']={i:{'before':v[0],'after':v[1]} for i,v in PHYSICS.items()}
  report['core']=core_identity();report['native_core_sha256']=sha((ROOT/'.tools/core/snes9x_libretro.dll').read_bytes())
  report['shared_harness_sha256']={name:sha((ROOT/'tools'/name).read_bytes()) for name in ('emulator.py','test_expansion_01_animation_weight.py','test_characters.py','test_inputs.py')}
  for i in ([args.fighter] if args.fighter is not None else range(12)):
   after,contacts=session(i,candidate,table,physics=physics[i])
   for name,failures in [('cadence',after.drops),('native_timing',after.native_failures),('OBJ_overflow',after.overflow),('actor_payload',after.bad_payload),('OAM_geometry',after.geometry),('SPC_PCM_cadence',after.audio_failures)]:
    check(not failures,name+' failure array empty',[i,failures[:8]])
   check(not after.uploads[2],'at most one 3840B actor page changes per vblank',[i,dict(after.uploads)])
   check(after.e.audio_samples>0 and after.e.audio_peak>0,'SPC PCM remains live without device playback',[i,after.e.audio_samples,after.e.audio_peak])
   captures=[]
   if i==0:
    before=historical_visuals(i,old,base_table);captures=save_clips(after,before)
   report['cases'].append({'fighter':i,'ports':[1,2],'both_ports':True,'samples':len(after.rows),'current_simulation_sha256':after.game_hash.hexdigest(),'intentional_jumpVy_change':i in PHYSICS,'candidate_arcs':after.arcs,'contacts':contacts,'uploads':dict(after.uploads),'native_lag_increments':after.lag_increments,'native_timing_failures':after.native_failures,'cadence_failures':after.drops,'OBJ_failures':after.overflow,'payload_failures':after.bad_payload,'geometry_failures':after.geometry,'SPC_PCM_failures':after.audio_failures,'max_SPC_backlog':after.max_backlog,'captures':captures})
   print(json.dumps({'fighter':i,'samples':len(after.rows),'checks':len(checks)}),flush=True)
  check(sorted(row['fighter'] for row in report['cases'])==([args.fighter] if args.fighter is not None else list(range(12))),'requested roster coverage complete')
  changes={'rom':sha((ROOT/'dist/abaqus-after-hours.sfc').read_bytes())!=report['rom_sha256'],
           'dependencies':[p for p,digest in report['dependency_sha256'].items() if sha((ROOT/p).read_bytes())!=digest],
           'production_source':[p for p,digest in report['source_files_sha256'].items() if sha((ROOT/p).read_bytes())!=digest],
           'producer':sha(Path(__file__).read_bytes())!=report['producer_sha256']}
  report['input_changes_during_run']=changes
  check(not any(changes.values()),'ROM, production source, producer and dependencies remain frozen throughout run',changes)
  report['generated_count']=report['combined_contract']['assets']['generated_count'];report['status']='diagnostic_passed' if args.fighter is not None else 'passed'
 except Exception as exc:report['failures'].append(repr(exc));raise
 finally:
  report['elapsed_seconds']=round(time.monotonic()-started,3);report['check_count']=len(checks)
  report_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
  print(json.dumps({'status':report['status'],'checks':len(checks),'rom_sha256':report['rom_sha256'],'failures':report['failures'],'report':str(report_path)}),flush=True)
if __name__=='__main__':main()
