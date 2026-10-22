"""Build an offline native-screen gallery only from complete current-ROM suites."""
import base64
import hashlib
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from package import validate_crossup_review, validate_cpu_review, validate_training_cpu_review

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root/'dist/manifest.json').read_text())
validate_crossup_review(json.loads((root/'docs/crossup-review.json').read_bytes()), root, manifest)
validate_cpu_review(json.loads((root/'docs/cpu-anti-air-review.json').read_bytes()), root, manifest)
validate_training_cpu_review(root, manifest)
total = 0
for name in ['test', 'character-test', 'presentation-test', 'input-test', 'stage-test', 'training-test']:
    report = json.loads((root/f'docs/{name}-report.json').read_text())
    if (report.get('rom_sha256') != manifest['sha256'] or report.get('status', 'passed') != 'passed'
            or report.get('passed', 0) != len(report.get('checks', []))
            or not report.get('passed')
            or not all(check.get('passed') for check in report['checks'])):
        raise RuntimeError(('Unverified native gallery source', name))
    total += report['passed']
shots = [
    ('new', 'CPU catches a jump-in', 'Hard CPU commits to an ordinary uppercut with its full startup. Native capture; GIF playback timing is approximate.', 'cpu-anti-air/hit.gif'),
    ('new', 'Retreat makes it whiff', 'The committed uppercut misses a retreating jumper through all eight active ticks. Human balance review remains open.', 'cpu-anti-air/whiff.gif'),
    ('results', 'Office Champion', 'An earned trophy, winner portrait, score and title/roster actions.', 'champion/ending.png'),
    ('menus', 'Choose a Training opponent', 'DUMMY selection supports any opponent through either controller.', 'presentation/training-dummy.png'),
    ('menus', 'Practice a mirror match', 'Choose the same fighter on both sides before selecting an arena.', 'presentation/training-mirror.png'),
    ('menus', 'P1 right cross-up', 'Jump past and use medium kick: SNES A, or P1 keyboard X. Native capture; GIF playback timing is approximate.', 'crossup/p1.gif'),
    ('menus', 'P2 left cross-up', 'The mirrored left-cross route: SNES A, or P2 numpad 2. Native capture; GIF playback timing is approximate.', 'crossup/p2.gif'),
    ('menus', 'Controls cross-up cue', 'Controls page teaches CROSS-UP: JUMP PAST + A.', 'training/mode1-controls.png'),
    ('results', 'Player one wins', 'Winner portrait, score, quote and Start rematch.', 'presentation/result-score.png'),
    ('results', 'Player two wins', 'A neutral match heading and the correct winner.', 'presentation/result-score-p2.png'),
    ('results', 'Healthy timeout tie', 'The first banner reads TIME OVER / DRAW.', 'presentation/timeout-draw.png'),
    ('menus', 'Lars', 'Revised face and hair in the native roster screen.', 'presentation/select-11.png'),
    ('menus', 'Location previews', 'Wider views of the entrance, patio and trading desks.', 'presentation/arena-0.png'),
    ('menus', 'Pause controls', 'Both A and Start appear in the resume hint.', 'pause.png'),
]
if tuple(map(int, manifest['version'].split('.'))) >= (0, 17, 0):
    shots = [
        ('new', 'Practice against the CPU', "On Training's PAUSED card, use Up/Down to choose CPU. Your home difficulty carries into practice; P1 Select resets the round.", 'training/training-cpu-card.png'),
        ('new', 'Untimed CPU practice', 'Hard difficulty: Cristobal versus Lars at La Oficina, with health recovery and the 99 clock. Native capture; GIF timing is approximate.', 'training-cpu/practice.gif'),
        *((('menus' if category == 'new' else category), title, caption, path)
          for category, title, caption, path in shots),
    ]
cards = []
for category, title, caption, filename in shots:
    data = (root/'docs/screenshots'/filename).read_bytes()
    mime = 'image/gif' if filename.lower().endswith('.gif') else 'image/png'
    src = (str(root/'docs/screenshots'/filename).replace('\\', '/') if '--preview' in sys.argv
           else f'data:{mime};base64,' + base64.b64encode(data).decode('ascii'))
    source_attribute = 'data-animated-src' if mime == 'image/gif' else 'src'
    cards.append(f'<figure class="screen" data-category="{category}"><h3>{html.escape(title)}</h3>'
                 f'<img {source_attribute}="{src}" width="256" height="224" alt="{html.escape(title)} native SNES frame" '
                 f'data-sha256="{hashlib.sha256(data).hexdigest()}">'
                 f'<figcaption>{html.escape(caption)}</figcaption></figure>')
page = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Abaqus After Hours — vVERSION native review</title><style>
*{box-sizing:border-box}body{margin:0;color:var(--foreground,#17213a);font:14px/1.5 var(--font-sans,system-ui,sans-serif)}
h2{font-size:21px;margin:0 0 5px}p{margin:0 0 14px}.muted,figcaption,summary{color:var(--muted-foreground,#5a6880)}
.controls{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:16px 0}button{font:inherit;cursor:pointer;border:1px solid var(--border,#cad2e1);padding:7px 11px;border-radius:var(--radius,8px);background:var(--secondary,#eef2f9);color:var(--foreground,#17213a)}
button[aria-pressed="true"]{background:var(--primary,#1c376b);color:var(--primary-foreground,#fff);border-color:transparent}label{margin-left:auto;white-space:nowrap;cursor:pointer}
/* A zoom card needs 512 pixels plus 32 pixels of padding and two borders. */
.gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,290px),1fr));gap:16px}.gallery.zoom{grid-template-columns:repeat(auto-fit,minmax(min(100%,546px),1fr))}
.screen{margin:0;padding:16px;border:1px solid var(--border,#d6deeb);border-radius:var(--radius,10px);background:var(--card,#f7f9fd);color:var(--card-foreground,#17213a)}
.screen[hidden]{display:none}h3{font-size:15px;margin:0 0 12px}img{display:block;width:256px;height:auto;max-width:100%;margin:0 auto 12px;image-rendering:pixelated}.zoom img{width:512px}figcaption{font-size:13px;min-height:38px}
details{margin-top:18px}summary{cursor:pointer}code{font:11px/1.5 var(--font-mono,monospace);overflow-wrap:anywhere}details p{margin-top:8px}.status{margin-top:14px;font-size:12px}
</style></head><body><main><h2>vVERSION native review</h2><p class="muted">Frames from the actual SNES cartridge. Switch views or enlarge the pixels.</p>
<div class="controls" aria-label="Gallery controls"><button data-view="results" aria-pressed="true">Results</button><button data-view="menus" aria-pressed="false">Art &amp; menus</button><button data-view="all" aria-pressed="false">All screens</button><label><input id="zoom" type="checkbox"> 2× view</label></div>
<div class="gallery">CARDS</div><details><summary>Build details</summary><p>Native resolution: 256 × 224. Verified native checks: TOTAL.<br>ROM SHA256: <code>ROM_SHA</code></p><p class="muted">Snapshots support presentation review. Human gameplay, full listening, physical-controller, likeness/consent and team/public-use review remain open. Original hardware support is unverified.</p></details>
<p class="status muted">Abaqus: After Hours · vVERSION technical review candidate</p></main>
<script>
const gallery=document.querySelector('.gallery'),cards=[...document.querySelectorAll('.screen')],buttons=[...document.querySelectorAll('[data-view]')];
let viewRequest=0;
function show(view){
  const request=++viewRequest;
  gallery.dataset.ready='false';
  cards.forEach(card=>{
    card.hidden=view!=='all'&&card.dataset.category!==view;
    const image=card.querySelector('img');
    if(image.dataset.animatedSrc){
      if(card.hidden)image.removeAttribute('src');
      else if(!image.hasAttribute('src'))image.src=image.dataset.animatedSrc;
    }
  });
  buttons.forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.view===view)));
  const visible=cards.filter(card=>!card.hidden);
  Promise.all(visible.map(card=>card.querySelector('img').decode())).then(()=>{
    if(request!==viewRequest)return;
    if(visible.some(card=>{const image=card.querySelector('img');return image.naturalWidth!==256||image.naturalHeight!==224}))throw Error('Non-native frame dimensions');
    gallery.dataset.ready='true';
    console.log('Native review ready: '+cards.length+' frames, '+visible.length+' shown.');
  }).catch(error=>{if(request===viewRequest)console.error(error)});
}
buttons.forEach(button=>button.addEventListener('click',()=>show(button.dataset.view)));document.querySelector('#zoom').addEventListener('change',event=>gallery.classList.toggle('zoom',event.target.checked));show('results');
</script></body></html>'''
page = page.replace('VERSION', manifest['version'])
page = page.replace('<button data-view="results" aria-pressed="true">Results</button>',
                    '<button data-view="new" aria-pressed="true">New scenes</button><button data-view="results" aria-pressed="false">Results</button>')
page = page.replace("show('results')", "show('new')")
if tuple(map(int, manifest['version'].split('.'))) >= (0, 17, 0):
    page = page.replace('Art &amp; menus', 'Practice &amp; menus')
page = page.replace('CARDS', ''.join(cards)).replace('ROM_SHA', manifest['sha256']).replace('TOTAL', f'{total:,}')
target = root/('build/gallery-preview.html' if '--preview' in sys.argv else f"docs/REVIEW-v{manifest['version']}.html")
target.write_bytes(page.encode('utf-8'))
print(json.dumps({'html': str(target), 'native_frames': len(shots), 'bytes': target.stat().st_size}))
