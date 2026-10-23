"""Build the offline review page from verified combined-cartridge evidence."""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def local_link(value):
    value = str(value).replace('\\', '/')
    path = (ROOT / value).resolve()
    require(path.is_relative_to(ROOT), 'Review link escapes project: ' + value)
    require(path.is_file(), 'Missing review input: ' + value)
    return '../' + path.relative_to(ROOT).as_posix()


def main():
    manifest = json.loads((ROOT / 'dist/manifest.json').read_text(encoding='utf-8'))
    evidence = json.loads((ROOT / 'docs/expansion-v0.22.0-verification.json').read_text(encoding='utf-8'))
    source = json.loads((ROOT / 'docs/expansion-review-v0.22.0.json').read_text(encoding='utf-8'))
    rom_sha = hashlib.sha256((ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()).hexdigest()
    require(evidence['status'] == 'passed' and evidence['rom_sha256'] == rom_sha,
            'Combined verification must match current cartridge')
    require(manifest['sha256'] == rom_sha and source['rom_sha256'] == rom_sha,
            'Review metadata must match current cartridge')
    features = source['features']
    require([entry['id'] for entry in features] == list(range(1, 11)),
            'Review must cover all ten improvements in order')
    cards = []
    for entry in features:
        name = f"expansion-{entry['id']:02d}-report.json"
        record = evidence['evidence'][name]
        report_path = ROOT / record['path']
        require(hashlib.sha256(report_path.read_bytes()).hexdigest() == record['sha256'],
                'Focused evidence changed after collation: ' + name)
        guide = local_link(entry['guide'])
        media = []
        for item in entry.get('media', []):
            path = local_link(item['path'])
            label = html.escape(item['label'])
            suffix = Path(path).suffix.lower()
            if suffix in {'.wav', '.mp3', '.ogg'}:
                media.append(f'<figure><audio controls preload="none" src="{html.escape(path)}"></audio><figcaption>{label}</figcaption></figure>')
            else:
                require(suffix in {'.png', '.gif', '.webp', '.jpg'}, 'Unsupported review media')
                media.append(f'<figure><button class="picture" data-zoom="{html.escape(path)}" aria-label="Enlarge {label}"><img loading="lazy" src="{html.escape(path)}" alt="{label}"></button><figcaption>{label}</figcaption></figure>')
        controls = ''.join('<li>' + html.escape(value) + '</li>' for value in entry.get('try', []))
        cards.append(f'''<article data-group="{html.escape(entry['group'])}">
<div class="card-top"><span class="number">{entry['id']:02d}</span><span class="group">{html.escape(entry['group'])}</span></div>
<h2>{html.escape(entry['title'])}</h2><p>{html.escape(entry['description'])}</p>
<ul>{controls}</ul><div class="media">{''.join(media)}</div>
<details><summary>Implementation and native proof</summary><p><a href="{html.escape(guide)}">Feature guide</a> · <a href="{html.escape(local_link(record['path']))}">{record['checks']:,} focused checks</a> · <a href="{html.escape(entry['pr'])}">Feature PR</a></p></details>
</article>''')
    document = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Abaqus After Hours — ten improvements</title>
<style>
:root{color-scheme:dark;--bg:#0c1124;--card:#151d35;--ink:#eef2ff;--muted:#b9c3dc;--gold:#f7cf70;--line:#34415e}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,sans-serif}main{max-width:1140px;margin:auto;padding:36px 24px 56px}a{color:var(--gold);text-underline-offset:3px}h1{font-size:clamp(30px,5vw,48px);line-height:1.12;letter-spacing:-1px;margin:12px 0 18px}h2{font-size:23px;line-height:1.25;margin:14px 0 10px}p{margin:10px 0;color:var(--muted)}.eyebrow{color:var(--gold);font-weight:700;letter-spacing:.12em;font-size:12px;text-transform:uppercase}.intro{max-width:740px}.actions{display:flex;gap:12px;flex-wrap:wrap;margin:24px 0}.actions a,.filters button{border:1px solid var(--line);border-radius:9px;padding:10px 16px;background:var(--card);color:var(--ink);font:inherit;text-decoration:none}.actions .primary,.filters button[aria-pressed=true]{background:var(--gold);border-color:var(--gold);color:#171d30;font-weight:700}.controls{background:var(--card);border-left:3px solid var(--gold);padding:16px 20px;margin:26px 0}.controls p{margin:4px 0}kbd{background:#283451;border:1px solid #53617f;border-bottom-width:2px;border-radius:4px;padding:1px 6px;color:var(--ink);font:14px ui-monospace,monospace}.filters{display:flex;gap:8px;flex-wrap:wrap;margin:28px 0 18px}.filters button{cursor:pointer;padding:7px 13px;font-size:14px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}article{min-width:0;background:var(--card);border:1px solid var(--line);border-radius:15px;padding:22px}article[hidden]{display:none}.card-top{display:flex;align-items:center;justify-content:space-between}.number{font-size:25px;line-height:1;color:var(--gold);font-weight:750}.group{font-size:12px;text-transform:uppercase;letter-spacing:.09em;color:var(--muted)}ul{padding-left:20px;font-size:14px;margin:16px 0}li{margin:6px 0}.media{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-top:18px}figure{margin:0;min-width:0}.picture{display:block;width:100%;padding:0;background:#070b17;border:1px solid var(--line);border-radius:7px;overflow:hidden;cursor:zoom-in}.picture img{width:100%;display:block;image-rendering:pixelated}figcaption{font-size:12px;color:var(--muted);margin-top:7px}audio{width:100%;max-width:100%}details{border-top:1px solid var(--line);margin-top:22px;padding-top:12px;font-size:13px}summary{cursor:pointer;color:var(--muted)}footer{margin-top:32px;font-size:13px;color:var(--muted);overflow-wrap:anywhere}dialog{background:#080d1c;color:var(--ink);border:1px solid var(--line);border-radius:12px;max-width:min(96vw,1000px);padding:16px}dialog::backdrop{background:#000c}dialog img{max-height:78vh;max-width:100%;display:block;image-rendering:pixelated}dialog button{float:right;margin-bottom:12px;background:var(--gold);color:#171d30;border:0;border-radius:6px;padding:8px 14px;cursor:pointer}button:focus-visible,a:focus-visible,summary:focus-visible{outline:3px solid var(--gold);outline-offset:4px}@media(max-width:650px){main{padding:24px 16px 40px}.grid{grid-template-columns:1fr}article{padding:18px}.media{grid-template-columns:1fr}.actions a{flex:1;text-align:center}}
</style></head><body><main><header><div class="eyebrow">Native SNES · v0.22.0</div><h1>Ten improvements.<br>One cartridge.</h1><p class="intro">A single build brings together combat, character, stage and sound improvements. Explore each change below, then play the combined game.</p><div class="actions"><a class="primary" href="../Play.cmd">Play the game</a><a href="../dist/abaqus-after-hours.sfc">SNES cartridge</a><a href="https://github.com/Reston/snes-abaqus-fighter/pull/1">Combined PR</a></div></header>
<section class="controls" aria-label="Controller reminder"><p><strong>Four face buttons:</strong> Y / X punch · B / A kick.</p><p>Included keyboard: <kbd>A</kbd> / <kbd>S</kbd> punch · <kbd>Z</kbd> / <kbd>X</kbd> kick · arrows move · <kbd>Enter</kbd> pause.</p><p>Use each feature’s “Try it” steps below for new commands and modes.</p></section>
<nav class="filters" aria-label="Filter improvements"><button data-filter="all" aria-pressed="true">All ten</button><button data-filter="combat" aria-pressed="false">Combat</button><button data-filter="presentation" aria-pressed="false">Presentation</button><button data-filter="practice" aria-pressed="false">Practice</button><button data-filter="arcade" aria-pressed="false">Arcade</button></nav>
<section class="grid">CARDS</section><footer>Native cartridge ROM_SHA<br>All six native suites: NATIVE_CHECKS checks. Independent emulator smoke and ten feature proofs match this cartridge. <a href="expansion-v0.22.0-verification.json">Verification record</a>.<br>This combined revision awaits your playtest.</footer></main><dialog id="zoom"><button autofocus>Close</button><img alt="Enlarged native game capture"></dialog>
<script>const cards=[...document.querySelectorAll('article')];for(const button of document.querySelectorAll('[data-filter]'))button.addEventListener('click',()=>{for(const other of document.querySelectorAll('[data-filter]'))other.setAttribute('aria-pressed',String(other===button));for(const card of cards)card.hidden=button.dataset.filter!=='all'&&card.dataset.group!==button.dataset.filter});const modal=document.querySelector('#zoom');for(const picture of document.querySelectorAll('[data-zoom]'))picture.addEventListener('click',()=>{modal.querySelector('img').src=picture.querySelector('img').src;modal.querySelector('img').alt=picture.querySelector('img').alt;modal.showModal()});modal.querySelector('button').addEventListener('click',()=>modal.close());modal.addEventListener('click',event=>{if(event.target===modal)modal.close()});</script></body></html>'''
    # A fixed cap also keeps the same page safe for the inline T3 renderer,
    # whose height follows content and cannot use viewport-height units.
    document = document.replace('max-height:78vh', 'max-height:620px')
    document = document.replace('CARDS', ''.join(cards)).replace('ROM_SHA', rom_sha)
    document = document.replace('NATIVE_CHECKS', f"{evidence['native_six_suite_checks']:,}")
    output = ROOT / 'docs/EXPANSION-REVIEW-v0.22.0.html'
    output.write_bytes(document.encode('utf-8'))
    print(output)


if __name__ == '__main__':
    main()
