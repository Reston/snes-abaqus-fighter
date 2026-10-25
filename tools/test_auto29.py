"""Focused controller-only automatic fight-start proof, with silent pinned cores.

No emulated writes, save states, skip/confirm inputs after arena confirmation,
native windows or audio devices. Also serves the built WASM site with optional
one-shot real HTTP failures for browser error/retry review.
"""
from __future__ import annotations

import argparse
import ctypes as C
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from emulator import Emulator
from test_classic_menu import AccuracyMenu
from test_training import core_identity
from test_compatibility import verify_manifest_and_pinned_core
from test_champion import host_contract
from v024_contracts import symbols


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fingerprint():
    # The parent freezes all six harnesses and their shared imports together.
    # Hash tool sources as well as producers so transitive helpers are bound.
    paths = [p for folder in ('src', 'web', 'tools') for p in (ROOT / folder).iterdir()
             if p.is_file() and (folder != 'tools' or p.suffix in ('.py', '.mjs'))]
    return {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in sorted(paths)}


def serve(port, site):
    # Fault prefixes serve the SAME production bundle. Only the first real
    # loader/ROM HTTP request fails; Try again performs a genuine page reload.
    site = site.resolve()
    if not (site / 'release.json').is_file():
        raise ValueError('Parent must prepare the exact web bundle before starting the fixture')
    failed = set()

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(site), **kwargs)

        def do_GET(self):
            for prefix, suffix in (('/fault-loader/', 'loader.js'),
                                   ('/fault-rom/', 'abaqus-after-hours.sfc')):
                if self.path.startswith(prefix):
                    self.path = '/' + self.path[len(prefix):]
                    if self.path.split('?')[0].endswith(suffix) and prefix not in failed:
                        failed.add(prefix)
                        self.send_error(503, 'auto29 one-shot network failure')
                        return
                    break
            super().do_GET()

        def do_HEAD(self):
            for prefix in ('/fault-loader/', '/fault-rom/'):
                if self.path.startswith(prefix):
                    self.path = '/' + self.path[len(prefix):]
                    break
            super().do_HEAD()

    print(f'Auto29 browser fixture: http://127.0.0.1:{port}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', port), Handler).serve_forever()


def native(core, report_path, captures, combined=False, expected_rom=None):
    report_path, captures = report_path.resolve(), captures.resolve()
    checks = []

    def require(ok, label, details=None):
        if not ok:
            raise AssertionError((label, details))
        checks.append(label)

    manifest = json.loads((ROOT / 'dist/manifest.json').read_bytes())
    symbol_path = ROOT / 'dist/abaqus-after-hours.sym'
    symbol_sha = sha(symbol_path.read_bytes())
    syms = symbols(symbol_path.read_text())
    frozen = fingerprint()
    start = time.monotonic()
    report = dict(status='failed', core=core, rom_sha256=manifest['sha256'],
                  source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_and_harness=frozen, host=host_contract(), cases=[], media=[],
                  symbols_sha256=symbol_sha, combined=combined,
                  outputs={'report':str(report_path), 'captures':str(captures)},
                  memory_writes=False, save_states=False, post_arena_skip_inputs=0)
    steady = 0
    try:
        require(sha((ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()) == manifest['sha256'], 'ROM matches manifest')
        if expected_rom:
            require(manifest['sha256'] == expected_rom.lower(), 'ROM matches parent frozen SHA-256')
        if combined:
            from v029_contracts import validate
            report['integration_contract'] = validate(ROOT)
            require(report['integration_contract']['generated']['current_count'] == 237,
                    'Combined parent inventory contains exactly 237 generated files')
        report['core_identity'] = core_identity() if core == 'snes9x' else verify_manifest_and_pinned_core()
        for mode in range(3):
            for arena in range(3):
                host = Emulator() if core == 'snes9x' else AccuracyMenu()

                def read(name, size=1):
                    return int.from_bytes(C.string_at(host.ram + (syms[name] & 0x1ffff), size), 'little')

                def counters():
                    return [read(n, 2) for n in ('frame', 'snes_vblank_count', 'lag_frame_counter')]

                def step(keys=(), port=0, strict=False):
                    nonlocal steady
                    before = counters()
                    host.run(1, **({'p1': keys} if port == 0 else {'p2': keys}))
                    if strict:
                        delta = [(a-b) & 65535 for a, b in zip(counters(), before)]
                        require(delta == [1, 1, 0], 'One native tick and vblank; zero SDK lag', delta)
                        stat = int.from_bytes(C.string_at(host.ram + 0x1ff00 + 114*2, 2), 'little')
                        require(not stat & 0xc0, 'No native OBJ range/time overflow', stat)
                        steady += 1

                def pulse(key, port=0):
                    host.run(3, **({'p1': [key]} if port == 0 else {'p2': [key]}))
                    host.run(24)

                def shot(label):
                    path = captures / core / f'mode{mode}-arena{arena}-{label}.png'
                    path.parent.mkdir(parents=True, exist_ok=True)
                    host.frame.save(path)
                    report['media'].append(dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path.read_bytes())))

                try:
                    host.run(120)
                    require(read('screen') == 0, 'Cold boot waits at intentional native title')
                    for _ in range(mode):
                        pulse('down')
                    pulse('a')
                    require(read('screen') == 1, 'Mode confirmation opens fighter selection')
                    for _ in range(arena*4):
                        pulse('right')
                    selected = read('selected')
                    host.run(40)
                    require(read('screen') == 1 and read('selected') == selected, 'No automatic fighter choice')
                    pulse('a')
                    if mode:
                        require(read('screen') == 1 and read('selectPlayer') == 1, 'Second deliberate fighter choice remains')
                        pulse('a', 1 if mode == 1 else 0)
                    require(read('screen') == 2, 'Fighter confirmations reach arena selection')
                    for _ in range(arena):
                        pulse('down')
                    host.run(40)
                    require(read('screen') == 2 and read('arena') == arena, 'No automatic arena choice')
                    confirm_port = 1 if mode == 1 and arena == 1 else 0
                    confirm = 'start' if arena == 2 else 'a'
                    step([confirm], confirm_port)
                    # NO input of either port from this point until live combat
                    # is independently observed. In particular, never skip story.
                    seen_story = set()
                    seen_intro = set()
                    live = False
                    for tick in range(550):
                        # beginMatch sets screen=FIGHT before its forced-blank
                        # asset load. Start cadence checks only after the native
                        # trace actually publishes the completed fight scene.
                        coherent = host.state()['screen'] == 3
                        step(strict=coherent)
                        if host.state()['screen'] != 3:
                            continue
                        story, intro = read('arcadeStoryTicks', 2), read('intro')
                        seen_story.add(story)
                        seen_intro.add(intro)
                        if coherent:
                            require(read('pad0', 2) == read('pad1', 2) == 0, 'Both actual native pads released after arena')
                            require(not read('paused'), 'Arena Start does not become a pause edge')
                        if arena == 0 and story == 180:
                            shot('story-automatic')
                        if arena == 0 and not story and intro == 50:
                            shot('fight-countdown')
                        if not story and not intro:
                            live = True
                            break
                    require(live, 'Unassisted story and countdown reach combat within 550 callbacks')
                    require({0, 50, 109}.issubset(seen_intro), 'Native intro counts down through FIGHT to zero', sorted(seen_intro))
                    if mode == 0:
                        require({0, 1, 180, 350}.issubset(seen_story), 'Arcade retains six-second automatic dialogue', sorted(seen_story))
                    else:
                        require(seen_story == {0}, 'Local/Training enter countdown directly')
                    require(read('mode') == mode and read('arena') == arena, 'Chosen mode and arena retained')
                    for _ in range(30):
                        step(strict=True)
                    if arena == 0:
                        shot('unassisted-combat')
                    # Ordinary Start pause remains owned by either port, after
                    # the no-extra-key assertion has already passed.
                    pause_port = arena % 2
                    pulse('start', pause_port)
                    require(read('paused') == 1, 'Start still pauses combat from either pad')
                    before = (read('seconds'), read('intro'), read('arcadeStoryTicks', 2))
                    for _ in range(30):
                        step(strict=True)
                    require(before == (read('seconds'), read('intro'), read('arcadeStoryTicks', 2)), 'Native pause freezes timers')
                    pulse('start', pause_port)
                    require(read('paused') == 0, 'Start resumes combat')
                    require(host.audio_samples > 0 and 0 < host.audio_peak < 32767, 'Silent PCM capture remains active and unclipped')
                    report['cases'].append(dict(mode=mode, arena=arena, fighter=selected,
                                                confirm=confirm, confirm_port=confirm_port,
                                                pause_port=pause_port, no_input_callbacks_to_combat=tick+1,
                                                story_values=len(seen_story), intro_values=len(seen_intro)))
                    print(json.dumps(report['cases'][-1]), flush=True)
                finally:
                    host.close()
        require(len(report['cases']) == 9, 'All three modes crossed with all three arenas completed')
        require(fingerprint() == frozen, 'Source/harness bytes stayed frozen during proof')
        require(sha(symbol_path.read_bytes()) == symbol_sha, 'Read-only symbol offsets stayed frozen')
        require(sha((ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()) == manifest['sha256'], 'Tested ROM stayed frozen')
        report['status'] = 'passed'
    except BaseException as error:
        report['error'] = repr(error)
        raise
    finally:
        report.update(passed=len(checks), steady_callbacks=steady, elapsed_seconds=round(time.monotonic()-start, 3))
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_bytes((json.dumps(report, indent=2)+'\n').encode('utf-8'))
        print(json.dumps({k: report[k] for k in ('status', 'core', 'passed', 'steady_callbacks', 'elapsed_seconds')}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core', choices=('snes9x', 'accuracy'))
    parser.add_argument('--report', type=Path)
    parser.add_argument('--captures', type=Path, default=ROOT / 'build/v029/auto/native')
    parser.add_argument('--combined', action='store_true', help='Use the parent-owned 237-file integration contract')
    parser.add_argument('--expect-rom-sha256', help='Require the parent frozen cartridge identity')
    parser.add_argument('--serve', type=int, metavar='PORT')
    parser.add_argument('--site', type=Path, default=ROOT / 'build/cloudflare/site',
                        help='Parent-prepared web bundle served by --serve; no web build is performed')
    args = parser.parse_args()
    if args.serve:
        serve(args.serve, args.site)
    elif args.core and args.report:
        native(args.core, args.report, args.captures, args.combined, args.expect_rom_sha256)
    else:
        parser.error('--core and --report, or --serve, required')


if __name__ == '__main__':
    main()
