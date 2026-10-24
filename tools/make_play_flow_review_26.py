"""Render the verified native candidate's review gallery and media provenance."""
import base64
import hashlib
import io
import json
from pathlib import Path
import sys
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from candidate_sources import snapshot

ROOT = Path(__file__).resolve().parents[1]
SCREEN = 'docs/screenshots/play-flow-v026/'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def read(name):
    return json.loads((ROOT / name).read_bytes())



def native_poster(path):
    """Encode the native first frame compactly without changing a color."""
    with Image.open(path) as frame:
        frame.seek(0)
        require(frame.size==(256,224),'Gallery must preserve the native viewport')
        rgb=frame.convert('RGB')
        encoded=rgb.quantize(colors=256,dither=Image.Dither.NONE) if rgb.getcolors(256) is not None else rgb
        require(encoded.convert('RGB').tobytes()==rgb.tobytes(),'Poster encoding changed native pixels')
        buffer=io.BytesIO();encoded.save(buffer,format='PNG',optimize=True)
    return 'data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode()


def build():
    verification = read('docs/verification-v0.26.0.json')
    manifest = read('dist/manifest.json')
    require(verification['status'] == 'passed' and verification['rom_sha256'] == manifest['sha256'] and
            verification['source_sha256'] == snapshot(ROOT), 'Gallery needs passed exact-source/current-ROM verification')
    rom = manifest['sha256']
    before_rom = verification['preservation']['inherited_v025_contract']['baseline_rom_sha256']
    pacing = read('docs/play-flow-v026-pacing-report.json')['result'][0]

    def image(name, caption, identity=rom):
        return {'path': name, 'caption': caption, 'rom_sha256': identity}

    def shot(name, caption):
        return image(SCREEN + name, caption)

    groups = [
        {'id': 'pace', 'label': 'Pacing', 'text': 'A measured approach and retreat before/after. Current walk/projectile travel is about 25% slower than v0.24; attacks, jumps and recovery also give more time.',
         'images': [image(pacing['before']['captures']['movement']['path'], 'Before: approved v0.24', before_rom),
                    image(pacing['after']['captures']['movement']['path'], 'Current: slower native combat')]},
        {'id': 'floors', 'label': 'Floors', 'text': 'Detailed ground shares one connected picture with the scenery. No scanline parallax or live stage uploads.',
         'images': [shot(f'pacing/stages/snes9x-stage{i}-movement.gif', name) for i, name in enumerate(('Las Condes', 'El Castillo', 'La Oficina'))]},
        {'id': 'local', 'label': 'Local play', 'text': 'Either player can rematch. Round wins and session match wins are separate; player labels make mirror results clear.',
         'images': [shot('local-session-2-1.png', 'A running 2–1 local session'), shot('result-p2-mirror.png', 'Player 2 earns the mirror-match result')]},
        {'id': 'practice', 'label': 'Practice', 'text': 'Real light-to-strong confirms beat attempted guard. Late follow-ups are blocked. Retries retain your session best; the guide shows each fighter’s actual normal timing.',
         'images': [shot('hit-confirm-y-x.png', 'Earned two-hit confirm'), shot('hit-confirm-late-block.png', 'A late follow-up is genuinely blocked'),
                    shot('training-best-combo.png', 'Session best survives retries'), shot('normal-timing-p1.png', 'Startup, active time and recovery')]},
        {'id': 'feedback', 'label': 'Feedback', 'text': 'Full energy teaches the super chord. PUNISH! identifies a recovery hit; THROW TECH! explains a simultaneous throw escape.',
         'images': [shot('super-ready.png', 'Full meter: SUPER Y+B'), shot('punish-punch-p2.png', 'A real recovery punish'), shot('throw-tech-p1.png', 'The existing non-damaging throw escape')]},
        {'id': 'comfort', 'label': 'Comfort', 'text': 'Guide L toggles music while retaining sounds and voice. R keeps scenery still; fighters, hit recoil and timing stay the same.',
         'images': [shot('music-muted-guide.png', 'Music preference on the guide'), shot('background-still-guide.png', 'Background-motion preference'),
                    shot('background-moving.gif', 'Normal bounded background movement'), shot('background-still.gif', 'Still scenery with the same combat')]},
        {'id': 'arcade', 'label': 'Arcade', 'text': 'The ladder names your shift and the opponent you will face next or retry after a loss.',
         'images': [shot('arcade-next-opponent.png', 'Next challenger'), shot('arcade-retry-opponent.png', 'Continue against the shown opponent')]},
        {'id': 'arenas', 'label': 'Arenas', 'text': 'The picker derives its landmark views from the current native scenery. Both controllers can choose a local arena.',
         'images': [image(SCREEN + 'before-arena-0.png', 'Historical v0.25 picker', 'f0223f8240e2338ec57674b465a93cc5b0145a6210b5d5933706bac7277168a2'),
                    shot('arena-current-0-snes9x.png', 'Current native-stage previews')]},
        {'id': 'roster', 'label': 'Roster', 'text': 'The approved portraits now sit beside ordinary-special family, command and energy hints.',
         'images': [shot('roster-family-0.png', 'Wave-shot fighter'), shot('roster-family-3.png', 'Rising-strike fighter')]},
    ]
    media = []
    for group in groups:
        for row in group['images']:
            path = ROOT / row['path']
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            require(verification['review_media_sha256'].get(row['path']) == digest, 'Gallery image differs from verified evidence: ' + row['path'])
            row['sha256'] = digest
            row['animated'] = path.suffix == '.gif'
            row['poster'] = native_poster(path)
            media.append({k: v for k, v in row.items() if k != 'poster'})
    metadata = {'status': 'verified-native-review', 'version': '0.26.0', 'rom_sha256': rom,
                'source_commit': verification['source_commit'], 'verification_sha256': hashlib.sha256((ROOT / 'docs/verification-v0.26.0.json').read_bytes()).hexdigest(),
                'media': media, 'human_playtest_approved': None, 'gif_timing_is_approximate': True}
    return groups, metadata


CSS = '''html,body{margin:0;color:var(--foreground,#e6edf3);font-family:var(--font-sans,system-ui)}*{box-sizing:border-box}p{line-height:1.5;margin:0 0 12px}.muted,small{color:var(--muted-foreground,#a4b0c3)}.controls,nav{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 14px}button{min-height:44px;font:inherit;font-size:14px;border:1px solid var(--border,#3c4960);border-radius:var(--radius,8px);padding:7px 12px;background:transparent;color:inherit;cursor:pointer}button[aria-selected=true]{background:var(--accent-surface,#28365a);color:var(--accent-surface-foreground,#ffdd66);border-color:var(--accent,#e3b84e)}button:focus-visible{outline:2px solid var(--ring,#ffdd66);outline-offset:2px}.shots{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}figure{margin:0;padding:16px;border-radius:var(--radius,10px);background:var(--card,#131d36)}img{display:block;width:100%;height:auto;image-rendering:pixelated;background:#000}figcaption{font-size:13px;line-height:1.4;margin:9px 0 0}details{font-size:12px;margin-top:12px;overflow-wrap:anywhere}code{font-family:var(--font-mono,monospace)}@media(max-width:430px){.shots{gap:8px;grid-template-columns:1fr}nav{gap:5px}button{padding:7px 9px}figcaption{font-size:12px}}'''


def document(groups, metadata, inline):
    data = []
    for group in groups:
        data.append({**group, 'images': [{**row, 'src': (ROOT / row['path']).as_posix() if inline else
                                       Path(row['path']).relative_to('docs').as_posix()} for row in group['images']]})
    script = '''const nav=document.querySelector('nav'),panel=document.querySelector('main'),toggle=document.querySelector('#motion');let active='pace',playing=false;
function select(id,focus=false){active=id;const g=groups.find(x=>x.id===id);for(const b of nav.children){const chosen=b.dataset.id===id;b.setAttribute('aria-selected',String(chosen));b.tabIndex=chosen?0:-1;if(chosen&&focus)b.focus()}panel.setAttribute('aria-labelledby','tab-'+id);panel.replaceChildren();const p=document.createElement('p');p.textContent=g.text;panel.append(p);const shots=document.createElement('div');shots.className='shots';for(const im of g.images){const f=document.createElement('figure'),img=document.createElement('img'),c=document.createElement('figcaption');img.src=playing&&im.animated?im.src:im.poster;img.alt=im.caption;img.width=256;img.height=224;c.textContent=im.caption;f.append(img,c);shots.append(f)}panel.append(shots);document.querySelector('#identity').textContent=g.images.map(im=>im.caption+': '+im.rom_sha256).join(' | ')}
for(const g of groups){const b=document.createElement('button');b.textContent=g.label;b.dataset.id=g.id;b.id='tab-'+g.id;b.setAttribute('role','tab');b.setAttribute('aria-controls','review-panel');b.onclick=()=>select(g.id);b.onkeydown=e=>{let i=groups.findIndex(x=>x.id===active);if(e.key==='ArrowRight')i=(i+1)%groups.length;else if(e.key==='ArrowLeft')i=(i+groups.length-1)%groups.length;else if(e.key==='Home')i=0;else if(e.key==='End')i=groups.length-1;else return;e.preventDefault();select(groups[i].id,true)};nav.append(b)}
toggle.onclick=()=>{playing=!playing;toggle.setAttribute('aria-pressed',String(playing));toggle.textContent=playing?'Show still frames':'Play captured motion';select(active)};select(active);window.addEventListener('load',()=>console.log(JSON.stringify({groups:groups.length,images:document.images.length,loaded:[...document.images].every(x=>x.complete&&x.naturalWidth>0),overflow:document.documentElement.scrollWidth>innerWidth,autoplay:playing})));'''
    styles=CSS
    if not inline:
        styles=':root{color-scheme:dark;--background:#0b1120;--foreground:#edf2fb;--muted-foreground:#acb9cc;--card:#17223b;--border:#405174;--accent-surface:#283b63;--accent-surface-foreground:#ffe18b;--accent:#e3b84e;--ring:#ffdc66}html{background:var(--background)}body{max-width:1100px;margin:0 auto;padding:24px}@media(max-width:430px){body{padding:16px}}'+CSS
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Abaqus v0.26 native review</title><style>' + styles + '</style><body><p class="muted">v0.26 · technically verified, ready for playtest</p><nav aria-label="Review topic" role="tablist"></nav><div class="controls"><button id="motion" type="button" aria-pressed="false">Play captured motion</button></div><main id="review-panel" role="tabpanel" tabindex="0"></main><details><summary>Capture identity and timing</summary><p>Native captures are bound to the verification record. Historical views are labeled separately. GIF playback timing is approximate; the SNES cartridge is authoritative.</p><div id="identity"></div></details><script>const groups=' + json.dumps(data) + ';' + script + '</script></body></html>'


def main():
    groups, metadata = build()
    (ROOT / 'docs/REVIEW-v0.26.0.html').write_text(document(groups, metadata, False), encoding='utf-8', newline='\n')
    (ROOT / 'build/v026-inline.html').write_text(document(groups, metadata, True), encoding='utf-8', newline='\n')
    (ROOT / 'docs/play-flow-v026-review.json').write_bytes((json.dumps(metadata, indent=2) + '\n').encode())
    print(json.dumps({'groups': len(groups), 'images': len(metadata['media']), 'rom_sha256': metadata['rom_sha256']}))


if __name__ == '__main__':
    main()
