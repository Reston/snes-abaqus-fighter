"""Capture a native clip per fighter and build an offline practice companion."""
from __future__ import annotations

import base64
import hashlib
import html
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import test_matchups
from emulator import Emulator
from make_crossup_review import (RecordingEmulator, process_contract, trim_case, write_gif)
from release_evidence import EXPECTED_NATIVE_CORE
from test_crossup_practice import NAMES, RECIPES, practice_case


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def page(manifest, captures, preview):
    items = []
    for capture in captures:
        fighter = capture['fighter']
        route, gap = RECIPES[fighter]
        path = ROOT/capture['gif']
        source = path.as_posix() if preview else 'data:image/gif;base64,'+base64.b64encode(path.read_bytes()).decode('ascii')
        instructions = ('Start close to a stationary opponent. Jump toward them and use medium kick as you pass their center.'
                        if route == 'neutral' else
                        'Have the other player walk toward your jump until you pass them. Begin medium kick just before crossing their center.')
        if fighter in (3, 6):
            instructions += ' Start a little farther apart than the close setup.'
        if fighter == 4:
            instructions += ' Start farther apart to leave room for Negger\u2019s jump and kick startup.'
        mode = ('Try the stationary setup in Training with the Stand dummy.' if route == 'neutral' else
                'Use Local Versus and a second player or both keyboard layouts for the step-under setup.')
        items.append({'id': fighter, 'name': NAMES[fighter], 'route': route,
                      'routeLabel': 'Stationary opponent' if route == 'neutral' else 'Opponent steps under',
                      'instructions': instructions, 'mode': mode, 'src': source,
                      'stage': ('Las Condes', 'El Castillo', 'La Oficina')[capture['stage']],
                      'sha256': capture['gif_sha256'], 'gap': gap})
    options = ''.join(f'<option value="{fighter}">{html.escape(name)}</option>' for fighter, name in enumerate(NAMES))
    template = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Abaqus After Hours \u2014 cross-up practice</title><style>
*{box-sizing:border-box}body{margin:0;color:var(--foreground,#17213a);font:14px/1.5 var(--font-sans,system-ui,sans-serif)}h2{margin:0 0 6px;font-size:22px}p{margin:0 0 12px}.muted,summary{color:var(--muted-foreground,#5a6880)}
.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:18px 0}select,button{font:inherit;color:var(--foreground,#17213a);background:var(--secondary,#eef2f9);border:1px solid var(--border,#cad2e1);border-radius:var(--radius,8px);padding:7px 10px}select{min-width:155px}button{cursor:pointer}.controls label:last-child{margin-left:auto;white-space:nowrap}
.practice{display:grid;grid-template-columns:minmax(256px,1fr) minmax(220px,1fr);gap:18px;align-items:start}.visual,.lesson{padding:16px;border:1px solid var(--border,#d6deeb);border-radius:var(--radius,10px);background:var(--card,#f7f9fd)}.visual{margin:0}img{display:block;margin:auto;width:256px;height:224px;max-width:100%;object-fit:contain;image-rendering:pixelated}.large img{width:512px;height:auto}figcaption{font-size:12px;margin-top:12px;color:var(--muted-foreground,#5a6880)}h3{margin:0 0 8px;font-size:17px}.route{display:inline-block;font-size:12px;margin-bottom:10px;padding:3px 8px;border-radius:20px;background:var(--accent-surface,#e4eaff);color:var(--accent-surface-foreground,#263a72)}.key{display:block;margin:14px 0;font-weight:600}details{margin-top:18px}summary{cursor:pointer}details p{margin-top:10px}code{font:11px/1.5 var(--font-mono,monospace);overflow-wrap:anywhere}
.practice.zoom{display:flex;flex-wrap:wrap}.practice.zoom .visual{flex:1 1 546px;min-width:0}.practice.zoom .lesson{flex:1 1 220px;min-width:0}
@media(max-width:600px){.practice{grid-template-columns:minmax(0,1fr)}}
</style></head><body><main><h2>Practice the cross-up</h2><p class="muted">Learn the close rear medium kick with each fighter\u2019s existing jump and timing.</p>
<div class="controls"><label for="fighter">Fighter</label><select id="fighter">OPTIONS</select><button id="previous" aria-label="Previous fighter">\u2190</button><button id="next" aria-label="Next fighter">\u2192</button><label><input type="checkbox" id="large"> 2\u00d7 view</label></div>
<div class="practice"><figure class="visual"><img id="clip" width="256" height="224" alt=""><figcaption id="caption"></figcaption></figure><section class="lesson" aria-live="polite"><span class="route" id="route"></span><h3 id="name"></h3><p id="instructions"></p><span class="key">Medium kick: SNES A<br>P1 keyboard X \u00b7 P2 numpad 2</span><p id="mode"></p><p class="muted">Keep the kick close. If it misses, change your starting distance or begin it a little earlier.</p><p class="muted">After a crossing, the defender must switch their away direction to block high. Crouch guard loses to a jump-in.</p></section></div>
<details><summary>Capture and practice notes</summary><p>All clips are unedited 256\u00d7224 frames from controller-driven Local Versus. GIF playback timing is approximate. The companion uses one clip per fighter; the separate practice proof covers all twelve fighters, both controllers and all three arenas in 72 cases.</p><p>Clips show successful setups. They do not guarantee a hit against a moving or defending opponent. Human gameplay and balance review remain open.</p><p>Cartridge vVERSION \u00b7 ROM SHA256: <code>ROM_SHA</code></p><p>Selected GIF SHA256: <code id="digest"></code></p></details></main>
<script>const clips=DATA;const choice=document.querySelector('#fighter'),clip=document.querySelector('#clip');
function selectFighter(id){const item=clips[id];choice.value=String(id);clip.src=item.src;clip.alt=item.name+' native cross-up practice capture';document.querySelector('#name').textContent=item.name;document.querySelector('#route').textContent=item.routeLabel;document.querySelector('#instructions').textContent=item.instructions;document.querySelector('#mode').textContent=item.mode;document.querySelector('#caption').textContent=item.stage+' \u00b7 native capture \u00b7 playback timing approximate';document.querySelector('#digest').textContent=item.sha256;}
choice.addEventListener('change',()=>selectFighter(Number(choice.value)));document.querySelector('#previous').addEventListener('click',()=>selectFighter((Number(choice.value)+11)%12));document.querySelector('#next').addEventListener('click',()=>selectFighter((Number(choice.value)+1)%12));document.querySelector('#large').addEventListener('change',event=>{document.querySelector('.visual').classList.toggle('large',event.target.checked);document.querySelector('.practice').classList.toggle('zoom',event.target.checked);});selectFighter(0);const initialSource=clip.src;clip.decode().then(()=>{if(clip.src===initialSource)console.log('Native practice companion ready: 12 fighters, one active clip.');}).catch(error=>{if(clip.src===initialSource)console.error(error);});
</script></body></html>'''
    return template.replace('OPTIONS', options).replace('VERSION', manifest['version']).replace('ROM_SHA', manifest['sha256']).replace('DATA', json.dumps(items))


def main():
    manifest = json.loads((ROOT/'dist/manifest.json').read_bytes())
    require(sha(ROOT/'dist/abaqus-after-hours.sfc') == manifest['sha256'], 'Cartridge differs from manifest')
    version = manifest['version']
    proof = json.loads((ROOT/f'docs/crossup-practice-v{version}.json').read_bytes())
    inventory = {(row['fighter'], row['port'], row['stage']) for row in proof['cases'] if row['passed']}
    require(proof['status'] == 'passed' and proof['rom_sha256'] == manifest['sha256'] and
            len(proof['cases']) == 72 and inventory == {(f, p, s) for f in range(12) for p in (0, 1) for s in range(3)},
            'Complete current-ROM practice proof is required')
    require(all(sha(ROOT/name) == digest for name, digest in proof['harness_sha256'].items()),
            'Practice proof helpers changed')
    core = ROOT/'.tools/core/snes9x_libretro.dll'
    require(sha(core) == EXPECTED_NATIVE_CORE['dll_sha256'], 'Expanded native core differs from its pin')
    host = process_contract()
    captures = []
    original = test_matchups.Emulator
    try:
        for fighter in range(12):
            RecordingEmulator.instances = []
            test_matchups.Emulator = lambda: RecordingEmulator(Emulator)
            result = practice_case(fighter, 0, fighter % 3)
            require(len(RecordingEmulator.instances) == 1 and Emulator._active_instance is None,
                    'Practice capture must close its one sequential emulator')
            capture = trim_case(result, RecordingEmulator.instances[0], 0)
            images = capture.pop('_images')
            target = ROOT/f'docs/screenshots/crossup-practice/v{version}/{fighter:02}.gif'
            decoded, digest = write_gif(target, images)
            capture.update(fighter=fighter, name=NAMES[fighter], stage=fighter % 3,
                           helper='tools/test_crossup_practice.py:practice_case',
                           helper_parameters={'fighter': fighter, 'port': 0, 'stage': fighter % 3},
                           gif=target.relative_to(ROOT).as_posix(), gif_bytes=target.stat().st_size,
                           gif_sha256=digest, decoded_gif_frames=decoded)
            captures.append(capture)
            print(json.dumps({'fighter': fighter, 'frames': capture['frames'], 'gif_sha256': digest}), flush=True)
    finally:
        test_matchups.Emulator = original
    report = {'status': 'passed', 'version': version, 'rom_sha256': manifest['sha256'],
              'scope': 'Native visual practice companion; trusted recorded captures, no human balance approval',
              'native_dimensions': [256, 224], 'unedited_callback_pixels': True,
              'core_sha256': sha(core), 'host_contract': host,
              'harness_sha256': {name: sha(ROOT/name) for name in ('tools/make_crossup_practice_review.py',
                  *proof['harness_sha256'].keys())}, 'captures': captures}
    (ROOT/f'docs/crossup-practice-captures-v{version}.json').write_bytes((json.dumps(report, indent=2)+'\n').encode())
    target = ROOT/f'docs/CROSSUP-PRACTICE-v{version}.html'
    target.write_bytes(page(manifest, captures, False).encode())
    (ROOT/'build/crossup-practice-preview.html').write_bytes(page(manifest, captures, True).encode())
    print(json.dumps({'status': 'passed', 'html': str(target), 'captures': len(captures)}), flush=True)


if __name__ == '__main__':
    main()
