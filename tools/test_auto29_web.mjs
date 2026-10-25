// Actual pinned EmulatorJS/WASM proof. Only ordinary keyboard, touch and
// standard Gamepad/controller inputs drive the cartridge; native memory is read.
import {readFileSync, writeFileSync, mkdirSync, readdirSync} from 'node:fs';
import {resolve, relative, dirname, extname} from 'node:path';
import {createHash} from 'node:crypto';
import {parseArgs} from 'node:util';
import {execFileSync} from 'node:child_process';
import {chromium} from '../.tools/web-qa/node_modules/playwright-core/index.mjs';

const root = resolve(import.meta.dirname, '..');
const {values:options} = parseArgs({options:Object.fromEntries(
  ['url','browser','report','captures','site','expect-rom-sha256'].map(name=>[name,{type:'string'}]))});
const base = (options.url || process.env.AUTO29_URL || 'http://127.0.0.1:8794').replace(/\/$/,'');
const executablePath = options.browser || process.env.AUTO29_BROWSER || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const out = resolve(root, options.captures || process.env.AUTO29_CAPTURES || 'build/v029/auto/browser');
const reportPath = resolve(root, options.report || process.env.AUTO29_REPORT || 'build/v029/auto/browser-report.json');
const site = resolve(root, options.site || process.env.AUTO29_SITE || 'build/cloudflare/site');
const expectedRom = options['expect-rom-sha256'] || process.env.AUTO29_EXPECT_ROM_SHA256;
mkdirSync(out, {recursive: true});
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const paths = ['src','web','tools'].flatMap(folder=>readdirSync(resolve(root,folder),{withFileTypes:true})
  .filter(entry=>entry.isFile() && (folder!=='tools' || ['.py','.mjs'].includes(extname(entry.name))))
  .map(entry=>`${folder}/${entry.name}`)).sort();
const fingerprint = () => Object.fromEntries(paths.map(p => [p, sha(readFileSync(resolve(root, p)))]));
const frozen = fingerprint();
const manifest = JSON.parse(readFileSync(resolve(root, 'dist/manifest.json')));
const symbolBytes = readFileSync(resolve(root,'dist/abaqus-after-hours.sym'));
const symbolSha = sha(symbolBytes);
const symbols = Object.fromEntries([...symbolBytes.toString('utf8')
  .matchAll(/^([0-9a-fA-F]{6,8})\s+(\S+)\s*$/gm)].map(m=>[m[2],parseInt(m[1],16)]));
const nativeOffsets = Object.fromEntries(['pad0','pad1','selectPlayer','menuPreviewConfirm','pausePage','guideBuild',
  'v29AudioState','v29RandomState','randomseed','arcadeStoryTicks','frame','snes_vblank_count','lag_frame_counter'].map(name=>{
  if (!Number.isInteger(symbols[name])) throw new Error(`Required read-only native symbol missing: ${name}`);
  return [name,symbols[name]&0x1ffff];
}));
const report = {status: 'failed', rom_sha256: manifest.sha256, sources: frozen, checks: [], cases: [], media: [],
  source_commit:execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim(),
  symbols_sha256:symbolSha, native_read_offsets:nativeOffsets, integration_checks:[], pacing_windows:[],
  outputs:{report:reportPath,captures:out,site},
  browser: {executable: executablePath, sha256: sha(readFileSync(executablePath)),
    playwright: JSON.parse(readFileSync(resolve(root, '.tools/web-qa/node_modules/playwright-core/package.json'))).version,
    headless: true, audio_output_muted: true, autoplay_policy: 'user-gesture-required'},
  emulated_memory_writes: false, save_states: false};
function check(ok, label, detail) {
  if (!ok) throw new Error(`${label}: ${JSON.stringify(detail)}`);
  report.checks.push(label);
}
const lock = JSON.parse(readFileSync(resolve(root,'web/vendor-lock.json')));
const release = JSON.parse(readFileSync(resolve(site,'release.json')));
check(release.rom_sha256===manifest.sha256, 'Parent web bundle release matches the exact current native manifest');
check(sha(readFileSync(resolve(root,'dist/abaqus-after-hours.sfc')))===manifest.sha256, 'Native ROM matches manifest before browser launch');
if (expectedRom) check(manifest.sha256===expectedRom.toLowerCase(), 'Browser ROM matches parent frozen SHA-256');
report.runtime = {emulatorjs_version:lock.emulatorjs_version, files:{}};
for (const [name, expected] of Object.entries(lock.files)) {
  const actual = sha(readFileSync(resolve(site,release.emulator_path,name)));
  check(actual===expected, `Actual bundled runtime matches pin: ${name}`);
  report.runtime.files[name] = actual;
}
const browser = await chromium.launch({executablePath, headless: true,
  args: ['--mute-audio', '--autoplay-policy=user-gesture-required']});
report.browser.version = browser.version();
const begin = Date.now();
async function capture(page, name) {
  const path = resolve(out, `${name}.png`);
  await page.screenshot({path, fullPage: true});
  report.media.push({path: relative(root, path).replaceAll('\\', '/'), sha256: sha(readFileSync(path))});
}
async function state(page) {
  return page.evaluate(offsets => {
    const heap = window.EJS_emulator.Module.HEAPU8;
    if (!window.auto29Trace) {
      const candidates = [];
      for (let i = 0; i < heap.length-256; i += 2) {
        if (heap[i] !== 186 || heap[i+1] !== 170) continue;
        const w = new Uint16Array(heap.buffer, i, 32);
        if (w[1] <= 4 && w[3] <= 2 && w[22] < 12 && w[23] < 12 && w[14] < 3) candidates.push(i);
      }
      if (candidates.length !== 1) throw new Error(`Read-only trace candidates: ${JSON.stringify(candidates)}`);
      window.auto29Trace = candidates[0];
    }
    const words = Array.from(new Uint16Array(heap.buffer, window.auto29Trace, 34));
    const ram = window.auto29Trace-0x1ff00;
    const byte = address => heap[ram+address];
    const word = address => byte(address) | byte(address+1)<<8;
    return {screen:words[1],frame:words[2],mode:words[3],arena:words[14],intro:words[16],paused:words[17],
      selected:words[22],selected2:words[23],seconds:words[25],pad0:word(offsets.pad0),pad1:word(offsets.pad1),
      fighter1:words[32],fighter2:words[33],selectPlayer:byte(offsets.selectPlayer),
      menuPreviewConfirm:byte(offsets.menuPreviewConfirm),pausePage:byte(offsets.pausePage),guideBuild:byte(offsets.guideBuild),
      story:word(offsets.arcadeStoryTicks),combatRng:word(offsets.randomseed),randomSeed:word(offsets.v29RandomState),
      randomClock:word(offsets.v29RandomState+2),audioLevels:[0,1,2].map(i=>byte(offsets.v29AudioState+i)),
      audioCursor:byte(offsets.v29AudioState+3)};
  }, nativeOffsets);
}
async function boot(page, path = '/', loadingCapture = false) {
  await page.goto(base+path, {waitUntil:'domcontentloaded'});
  if (loadingCapture) {
    check((await page.locator('#status').textContent()).includes('Loading'), 'Page explains automatic loading');
    await capture(page,'loading-native-title');
  }
  await page.waitForFunction(() => window.EJS_emulator?.gameManager?.getFrameNum() > 120, null, {timeout:30000});
  check(await page.locator('.ejs_start_button').count() === 0, 'No browser Play gate');
  check((await state(page)).screen === 0, 'Page boots actual native title without input');
  const timing = await page.evaluate(() => ({configured:EJS_defaultOptions.vsync,
    registry:EJS_emulator.allSettings.vsync,value:EJS_emulator.getSettingValue('vsync'),
    fastForward:EJS_emulator.isFastForward,slowMotion:EJS_emulator.isSlowMotion}));
  check(timing.configured==='disabled' && timing.registry==='disabled' && timing.value==='disabled',
    'Supported pinned VSync setting binds to the actual runtime registry', timing);
  check(!timing.fastForward && !timing.slowMotion, 'Normal emulator speed modes remain active', timing);
}
async function measureNtsc(page, label) {
  // Observe five real seconds independently of display RAF. A 30 Hz monitor
  // must still receive the cartridge's normal NTSC logic/audio cadence.
  await state(page);
  const window = await page.evaluate(offsets => new Promise(done => {
    const trace=window.auto29Trace,ram=trace-0x1ff00;
    const read=() => {
      const heap=EJS_emulator.Module.HEAPU8,byte=i=>heap[ram+i],word=i=>byte(i)|byte(i+1)<<8;
      const words=new Uint16Array(heap.buffer,trace,34);
      return {sample_ms:performance.now(),coreFrame:EJS_emulator.gameManager.getFrameNum(),
        directFrame:word(offsets.frame),traceFrame:words[2],vblank:word(offsets.snes_vblank_count),
        lag:word(offsets.lag_frame_counter),pad0:word(offsets.pad0),pad1:word(offsets.pad1),
        paused:words[17],story:word(offsets.arcadeStoryTicks),intro:words[16],
        audioTime:EJS_emulator.Module.AL.currentCtx.audioCtx.currentTime};
    };
    const begin=performance.now(),start=read(),samples=[];
    let finished=false;
    const sample=raf => {if(finished)return;samples.push({...read(),raf_ms:raf});requestAnimationFrame(sample)};
    requestAnimationFrame(sample);
    setTimeout(() => {finished=true;done({target_ms:5000,actual_ms:performance.now()-begin,start,end:read(),samples})},5000);
  }), nativeOffsets);
  window.label=label;
  const seconds=window.actual_ms/1000;
  window.summary={raf_hz:window.samples.length/seconds};
  for (const field of ['coreFrame','directFrame','traceFrame','vblank']) {
    const delta=(window.end[field]-window.start[field])&65535;
    window.summary[field]={delta,hz:delta/seconds};
  }
  window.summary.lag_delta=(window.end.lag-window.start.lag)&65535;
  window.summary.audio_clock_delta=window.end.audioTime-window.start.audioTime;
  // Retain failed measurements in the report before any assertion can throw.
  report.pacing_windows.push(window);
  for (const field of ['coreFrame','directFrame','traceFrame','vblank'])
    check(window.summary[field].hz>=58.5 && window.summary[field].hz<=61.5,
      `${label}: ${field} advances at normal NTSC wall-clock speed`, window.summary);
  check(new Set(['coreFrame','directFrame','traceFrame','vblank'].map(field=>window.summary[field].delta)).size===1,
    `${label}: core/direct/TRACE/vblank deltas match`, window.summary);
  check(window.summary.lag_delta===0, `${label}: no steady SDK lag`, window.summary);
  check(window.samples.every(s=>s.pad0===0 && s.pad1===0 && s.paused===0),
    `${label}: all observed controllers remain released and unpaused`, window.summary);
  check(window.summary.audio_clock_delta>=4.85 && window.summary.audio_clock_delta<=5.15,
    `${label}: audio clock advances at wall-clock speed`, window.summary);
}
async function key(page, key) {
  await page.keyboard.down(key); await page.waitForTimeout(65); await page.keyboard.up(key);
  await page.waitForTimeout(410);
}
async function waitScene(page, screen, timeout=5000) {
  const until = Date.now()+timeout;
  while (Date.now() < until) {
    if ((await state(page)).screen === screen) return;
    await page.waitForTimeout(50);
  }
  throw new Error(`Native scene ${screen} did not arrive: ${JSON.stringify(await state(page))}`);
}
async function randomKeyboardPick(page, field, selectKey, count) {
  const before = await state(page);
  await key(page,selectKey);
  const after = await state(page);
  check(after.screen===before.screen && after.selectPlayer===before.selectPlayer,
    `Random ${field} retains the deliberate menu step`, {before,after});
  check(after[field]>=0 && after[field]<count && after[field]===(after.randomSeed>>8)%count
    && (after.randomSeed>>8)<252, `Keyboard random ${field} matches the native rejection-sampled stream`, after);
  check(after.combatRng===before.combatRng, `Menu random ${field} leaves combat RNG unchanged`, {before,after});
  if (after.screen===1) check(after.menuPreviewConfirm===0, 'Random fighter pick does not auto-confirm');
  return {field,key:selectKey,before:before[field],picked:after[field],
    seed_before:before.randomSeed,seed_after:after.randomSeed,combat_rng:after.combatRng};
}
async function restoreRosterChoice(page, field, target, player) {
  const current = (await state(page))[field];
  const delta = (target-current+12)%12;
  const retreat = delta>6;
  const moves = retreat?12-delta:delta;
  const button = player===1?(retreat?'j':'l'):(retreat?'ArrowLeft':'ArrowRight');
  for (let i=0;i<moves;i++) await key(page,button);
  check((await state(page))[field]===target, 'Original keyboard fighter fixture is restored after random proof');
  return moves;
}
async function soundPageKeyboard(page) {
  await key(page,'Enter');
  const paused = await state(page);
  check(paused.paused===1 && paused.pausePage===0, 'Additional Sound-page bridge starts from ordinary pause');
  await key(page,'a'); // Browser A is native SNES Y.
  const opened = await state(page);
  check(opened.paused===1 && opened.pausePage===4 && opened.guideBuild===0,
    'Keyboard native Y opens the completed Sound page 4', opened);
  check(opened.audioCursor===0 && JSON.stringify(opened.audioLevels)===JSON.stringify([2,3,3]),
    'Cold-boot native mix defaults and Music cursor remain exact', opened);
  await key(page,'ArrowLeft');
  const changed = await state(page);
  const expected = [opened.audioLevels[0]-1,...opened.audioLevels.slice(1)];
  check(changed.paused===1 && changed.pausePage===4 && changed.guideBuild===0
    && JSON.stringify(changed.audioLevels)===JSON.stringify(expected),
    'Keyboard changes only the selected native Music level by one step', {opened,changed});
  check(changed.seconds===paused.seconds && changed.intro===paused.intro && changed.story===paused.story,
    'Sound-page keyboard work retains the frozen native fight timers');
  await capture(page,'wasm-sound-page4');
  await key(page,'Enter');
  const resumed = await state(page);
  check(resumed.paused===0 && resumed.pausePage===0 && resumed.screen===3
    && JSON.stringify(resumed.audioLevels)===JSON.stringify(expected),
    'Start resumes from Sound page 4 and preserves the chosen level', resumed);
  return {route:'keyboard-sound-page4',native_key:'Y',browser_key:'a',levels_before:opened.audioLevels,
    levels_after:resumed.audioLevels,resumed:true};
}
try {
  // Keyboard: every mode, normal selections, then no input until combat.
  for (let mode=0; mode<3; mode++) {
    const context = await browser.newContext({viewport:{width:1280,height:1000}});
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await boot(page,'/',mode===0);
    const before = await state(page);
    await page.waitForTimeout(400);
    check((await state(page)).screen === 0, 'Native title retains deliberate mode choice');
    check((await state(page)).frame > before.frame, 'Actual WASM core advances before interaction');
    const quiet = await page.evaluate(() => ({volume:EJS_emulator.volume,muted:EJS_emulator.muted,
      gains:EJS_emulator.Module.AL.currentCtx.sources.filter(s=>s.gain).map(s=>s.gain.gain.value)}));
    check(quiet.muted && quiet.gains.every(x=>x===0), 'Boot is silent until first interaction', quiet);
    if (mode===0) {
      await capture(page,'automatic-native-title');
      await measureNtsc(page,'native-title');
    }
    for (let n=0;n<mode;n++) await key(page,'ArrowDown');
    await key(page,'Enter');
    await waitScene(page,1);
    check(await page.locator('#enable-sound').isHidden(), 'First keyboard gesture enables sound without consuming confirm');
    check(await page.evaluate(()=>EJS_emulator.Module.AL.currentCtx.audioCtx.state)==='running', 'Audio context running after interaction');
    const randomPicks = [];
    if (mode===1) {
      const original = (await state(page)).selected;
      randomPicks.push(await randomKeyboardPick(page,'selected','Shift',12));
      await restoreRosterChoice(page,'selected',original,0);
    }
    await key(page,'x');
    if (mode===1) {
      const original = (await state(page)).selected2;
      randomPicks.push(await randomKeyboardPick(page,'selected2','q',12));
      await restoreRosterChoice(page,'selected2',original,1);
    }
    if (mode) await key(page,mode===1?' ':'x');
    await waitScene(page,2);
    for (let n=0;n<mode;n++) await key(page,'ArrowDown');
    if (mode===1) {
      randomPicks.push(await randomKeyboardPick(page,'arena','q',3));
      const moves = (mode-(await state(page)).arena+3)%3;
      for (let i=0;i<moves;i++) await key(page,'ArrowDown');
      check((await state(page)).arena===mode, 'Original keyboard arena fixture is restored after random proof');
      check(new Set(randomPicks.flatMap(p=>[p.seed_before,p.seed_after])).size>1,
        'Bounded keyboard random actions exercise the native stream; self-picks remain valid');
      report.integration_checks.push({route:'keyboard-random',mode,picks:randomPicks,original_fixture_restored:true});
    }
    const confirmed = await state(page);
    await key(page,'x');
    await waitScene(page,3);
    // beginMatch's first published trace still contains the arena-confirm
    // sample taken before forced blank. Observe the next input poll without
    // sending anything; every subsequent physical pad sample must be zero.
    const handoffFrame = (await state(page)).frame;
    const freshPollDeadline = Date.now()+1000;
    while ((await state(page)).frame===handoffFrame && Date.now()<freshPollDeadline) await page.waitForTimeout(5);
    check((await state(page)).frame!==handoffFrame, 'Native input polls again after match-load publication');
    const start = Date.now();
    let seenIntro = false, seenFight = false;
    const samples = [];
    // This observation is INSIDE the original 12-second no-input deadline.
    if (mode===0) await measureNtsc(page,'arcade-story');
    while (Date.now()-start < 12000) {
      const s = await state(page);
      // raw_keys2 is the CPU's generated command in Arcade; pad0/pad1 are the
      // actual SNES ports. Require both physical pad samples to stay released.
      check(s.pad0 === 0 && s.pad1 === 0, 'Both WASM controllers released after arena', s);
      check(s.paused === 0, 'Unassisted WASM intro is unpaused', s);
      if (s.intro===110) seenIntro = true;
      if (s.intro>0 && s.intro<51) seenFight = true;
      samples.push(s);
      if (!s.intro) break;
      if (mode===0 && samples.length===5) await capture(page,'arcade-automatic-dialogue');
      await page.waitForTimeout(70);
    }
    const live = await state(page);
    const noInputMs = Date.now()-start;
    check(live.intro===0 && live.mode===mode && live.arena===mode, 'Actual WASM reaches chosen fight with no extra key', live);
    check(live.fighter1===confirmed.selected && live.fighter2===(mode===0?(confirmed.selected+1)%12:confirmed.selected2),
      'WASM fight uses the explicitly confirmed fighters after bounded random-menu checks', {confirmed,live});
    check(seenFight, 'WASM runs the native FIGHT countdown');
    if (mode===0) check(seenIntro && Date.now()-start>=5500, 'Arcade dialogue remains visible and auto advances after six seconds');
    await capture(page,`mode${mode}-unassisted-combat`);
    if (mode===0) await measureNtsc(page,'arcade-live');
    await key(page,'Enter');
    check((await state(page)).paused===1, 'Keyboard Start still pauses');
    await key(page,'Enter');
    check((await state(page)).paused===0, 'Keyboard Start still resumes');
    if (mode===2) report.integration_checks.push(await soundPageKeyboard(page));
    check(errors.length===0, 'No page JavaScript errors', errors);
    report.cases.push({route:'keyboard',mode,arena:mode,handoff_frame:handoffFrame,no_input_ms:noInputMs,samples});
    await context.close();
  }
  // Touch: controls must be visible on initial boot even though the old start
  // button's touchstart handler no longer runs. Use real touchscreen taps.
  {
    const context = await browser.newContext({viewport:{width:390,height:844},hasTouch:true,isMobile:true});
    const page = await context.newPage();
    await boot(page);
    const start = page.locator('.ejs_virtualGamepad_button').filter({hasText:'Start'});
    check(await start.isVisible(), 'Touch Start is visible after automatic boot');
    await capture(page,'touch-native-title');
    // Hold a realistic touch through several native input polls. A zero-time
    // synthetic tap releases both edges before the 60 Hz core can sample it.
    const box = await start.boundingBox();
    const touch = await context.newCDPSession(page);
    await touch.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:box.x+box.width/2,y:box.y+box.height/2}]});
    await page.waitForTimeout(90);
    await touch.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
    await waitScene(page,1);
    check(await page.locator('#enable-sound').isHidden(), 'First touch unlocks sound and reaches fighter selection');
    report.cases.push({route:'touch',screen:(await state(page)).screen});
    await context.close();
  }
  // Gamepad: deterministic standard Gamepad API fixture, not real hardware.
  // A gamepad press cannot grant browser user activation; sound is optional.
  {
    const context = await browser.newContext();
    await context.addInitScript(() => {
      window.auto29Pad = {id:'Auto29 standard controller fixture',index:0,connected:true,mapping:'standard',
        timestamp:0,axes:[0,0,0,0],buttons:Array.from({length:17},()=>({pressed:false,touched:false,value:0}))};
      navigator.getGamepads = () => [window.auto29Pad];
    });
    const page = await context.newPage();
    await boot(page);
    await page.evaluate(()=>{const event=new Event('gamepadconnected');Object.defineProperty(event,'gamepad',{value:auto29Pad});window.dispatchEvent(event)});
    await page.evaluate(()=>{auto29Pad.buttons[9]={pressed:true,touched:true,value:1};auto29Pad.timestamp=performance.now()});
    await page.waitForTimeout(130);
    await page.evaluate(()=>{auto29Pad.buttons[9]={pressed:false,touched:false,value:0};auto29Pad.timestamp=performance.now()});
    await waitScene(page,1);
    check(await page.locator('#enable-sound').isVisible(), 'Gamepad reaches selection while optional sound action remains');
    await page.locator('#enable-sound').click();
    check(await page.locator('#enable-sound').isHidden(), 'Sound action unlocks gamepad audio independently');
    report.cases.push({route:'standard-gamepad-api-fixture',screen:(await state(page)).screen,physical_hardware:false});
    await context.close();
  }
  for (const fault of ['loader','rom']) {
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.goto(`${base}/fault-${fault}/`);
    await page.locator('#retry').waitFor({state:'visible',timeout:30000});
    check((await page.locator('#status').textContent()).includes('Could not load'), `Real ${fault} HTTP failure shows error`);
    await capture(page,`${fault}-failure-retry`);
    await page.locator('#retry').click();
    await page.waitForFunction(()=>window.EJS_emulator?.gameManager?.getFrameNum()>120,null,{timeout:30000});
    check((await state(page)).screen===0 && await page.locator('#retry').isHidden(), `Retry recovers ${fault} failure and automatically boots title`);
    report.cases.push({route:`one-shot-http-${fault}-503`,retry:'passed'});
    await context.close();
  }
  check(report.cases.length===7, 'All original seven browser scenarios completed');
  check(report.integration_checks.length===2, 'Bounded keyboard random and native Sound-page bridges completed');
  check(report.pacing_windows.length===3, 'Five-second title/story/live NTSC wall-clock proofs completed');
  check(JSON.stringify(fingerprint())===JSON.stringify(frozen), 'Browser producer and harness bytes stayed frozen');
  check(sha(readFileSync(resolve(site,'abaqus-after-hours.sfc')))===manifest.sha256, 'WASM bundle uses exact candidate ROM');
  check(sha(readFileSync(resolve(root,'dist/abaqus-after-hours.sfc')))===manifest.sha256, 'Native ROM stayed frozen during browser proof');
  check(sha(readFileSync(resolve(root,'dist/abaqus-after-hours.sym')))===symbolSha, 'Browser read-only symbol offsets stayed frozen');
  report.status='passed';
} catch (error) {
  report.error = String(error.stack || error);
  console.error(report.error);
  process.exitCode=1;
} finally {
  report.elapsed_seconds=(Date.now()-begin)/1000;
  mkdirSync(dirname(reportPath),{recursive:true});
  writeFileSync(reportPath,JSON.stringify(report,null,2)+'\n');
  await browser.close();
  console.log(JSON.stringify({status:report.status,checks:report.checks.length,cases:report.cases.length,seconds:report.elapsed_seconds}));
}
