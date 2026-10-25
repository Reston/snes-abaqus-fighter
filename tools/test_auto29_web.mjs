// Actual pinned EmulatorJS/WASM proof. Only ordinary keyboard, touch and
// standard Gamepad/controller inputs drive the cartridge; native memory is read.
import {readFileSync, writeFileSync, mkdirSync} from 'node:fs';
import {resolve, relative} from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from '../.tools/web-qa/node_modules/playwright-core/index.mjs';

const root = resolve(import.meta.dirname, '..');
const base = process.env.AUTO29_URL || 'http://127.0.0.1:8794';
const executablePath = process.env.AUTO29_BROWSER || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const out = resolve(root, 'docs/screenshots/auto29/browser');
mkdirSync(out, {recursive: true});
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const paths = ['web/index.html', 'web/player.js', 'web/style.css', 'web/vendor-lock.json',
  'tools/test_auto29.py', 'tools/test_auto29_web.mjs', 'tools/build_web.py'];
const fingerprint = () => Object.fromEntries(paths.map(p => [p, sha(readFileSync(resolve(root, p)))]));
const frozen = fingerprint();
const manifest = JSON.parse(readFileSync(resolve(root, 'dist/manifest.json')));
const symbols = Object.fromEntries([...readFileSync(resolve(root,'dist/abaqus-after-hours.sym'),'utf8')
  .matchAll(/^([0-9a-fA-F]{6,8})\s+(\S+)\s*$/gm)].map(m=>[m[2],parseInt(m[1],16)]));
const nativePads = [symbols.pad0 & 0x1ffff, symbols.pad1 & 0x1ffff];
const report = {status: 'failed', rom_sha256: manifest.sha256, sources: frozen, checks: [], cases: [], media: [],
  browser: {executable: executablePath, sha256: sha(readFileSync(executablePath)),
    playwright: JSON.parse(readFileSync(resolve(root, '.tools/web-qa/node_modules/playwright-core/package.json'))).version,
    headless: true, audio_output_muted: true, autoplay_policy: 'user-gesture-required'},
  emulated_memory_writes: false, save_states: false};
function check(ok, label, detail) {
  if (!ok) throw new Error(`${label}: ${JSON.stringify(detail)}`);
  report.checks.push(label);
}
const lock = JSON.parse(readFileSync(resolve(root,'web/vendor-lock.json')));
const release = JSON.parse(readFileSync(resolve(root,'build/cloudflare/site/release.json')));
report.runtime = {emulatorjs_version:lock.emulatorjs_version, files:{}};
for (const [name, expected] of Object.entries(lock.files)) {
  const actual = sha(readFileSync(resolve(root,'build/cloudflare/site',release.emulator_path,name)));
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
  return page.evaluate(pads => {
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
    const words = Array.from(new Uint16Array(heap.buffer, window.auto29Trace, 32));
    const ram = window.auto29Trace-0x1ff00;
    const pad = address => heap[ram+address] | heap[ram+address+1]<<8;
    return {screen:words[1],frame:words[2],mode:words[3],arena:words[14],intro:words[16],paused:words[17],
      selected:words[22],selected2:words[23],seconds:words[25],pad0:pad(pads[0]),pad1:pad(pads[1])};
  }, nativePads);
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
    if (mode===0) await capture(page,'automatic-native-title');
    for (let n=0;n<mode;n++) await key(page,'ArrowDown');
    await key(page,'Enter');
    await waitScene(page,1);
    check(await page.locator('#enable-sound').isHidden(), 'First keyboard gesture enables sound without consuming confirm');
    check(await page.evaluate(()=>EJS_emulator.Module.AL.currentCtx.audioCtx.state)==='running', 'Audio context running after interaction');
    await key(page,'x');
    if (mode) await key(page,mode===1?' ':'x');
    await waitScene(page,2);
    for (let n=0;n<mode;n++) await key(page,'ArrowDown');
    await key(page,'x');
    await waitScene(page,3);
    const start = Date.now();
    let seenIntro = false, seenFight = false;
    const samples = [];
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
    check(seenFight, 'WASM runs the native FIGHT countdown');
    if (mode===0) check(seenIntro && Date.now()-start>=5500, 'Arcade dialogue remains visible and auto advances after six seconds');
    await capture(page,`mode${mode}-unassisted-combat`);
    await key(page,'Enter');
    check((await state(page)).paused===1, 'Keyboard Start still pauses');
    await key(page,'Enter');
    check((await state(page)).paused===0, 'Keyboard Start still resumes');
    check(errors.length===0, 'No page JavaScript errors', errors);
    report.cases.push({route:'keyboard',mode,arena:mode,no_input_ms:noInputMs,samples});
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
  check(JSON.stringify(fingerprint())===JSON.stringify(frozen), 'Browser producer and harness bytes stayed frozen');
  check(sha(readFileSync(resolve(root,'build/cloudflare/site/abaqus-after-hours.sfc')))===manifest.sha256, 'WASM bundle uses exact candidate ROM');
  report.status='passed';
} catch (error) {
  report.error = String(error.stack || error);
  console.error(report.error);
  process.exitCode=1;
} finally {
  report.elapsed_seconds=(Date.now()-begin)/1000;
  writeFileSync(resolve(root,'docs/auto29-browser-report.json'),JSON.stringify(report,null,2)+'\n');
  await browser.close();
  console.log(JSON.stringify({status:report.status,checks:report.checks.length,cases:report.cases.length,seconds:report.elapsed_seconds}));
}
