"""Controller-only classic-menu proof on both pinned native emulator cores."""
from __future__ import annotations

import ctypes as C
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import time

from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
from emulator import Emulator, ROOT
import test_compatibility as compat
import test_presentation as presentation
from test_training import core_identity
from test_champion import host_contract
from v024_contracts import symbols

BASE = '2886087473a66b89898088b89a1ce78c02d41c99'
REPORT = ROOT / 'docs/classic-menu-native.json'
CAPTURES = ROOT / 'docs/screenshots/classic-menu/both-cores'
DEPENDENCIES = ('src/game.c', 'src/version.h', 'tools/menu_assets.py',
                'tools/test_classic_menu.py', 'tools/test_presentation.py',
                'tools/test_training.py', 'tools/test_compatibility.py',
                'tools/test_champion.py', 'tools/emulator.py', 'tools/v024_contracts.py')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(ok, message, details=None):
    if not ok:
        raise AssertionError((message, details))


def preservation():
    archived = subprocess.check_output(['git', 'archive', BASE, 'assets/generated',
                                       'src/hardware.asm', 'src/trace.asm'], cwd=ROOT)
    allowed = {'assets/generated/assets.h'} | {
        'assets/generated/' + name + suffix for name in ('title', 'select', 'arenas')
        for suffix in ('.png', '_tiles.bin', '_map.bin', '_pal.bin')}
    changed, preserved = [], []
    with tarfile.open(fileobj=io.BytesIO(archived)) as archive:
        for item in archive:
            if not item.isfile():
                continue
            before = archive.extractfile(item).read()
            after = (ROOT / item.name).read_bytes()
            if Path(item.name).suffix in ('.asm', '.h', '.json'):
                before, after = before.replace(b'\r\n', b'\n'), after.replace(b'\r\n', b'\n')
            (preserved if before == after else changed).append(item.name)
    require(set(changed) <= allowed, 'Unexpected asset/native-assembly change', changed)
    prior = symbols(subprocess.check_output(['git', 'show', BASE + ':dist/abaqus-after-hours.sym'],
                                           cwd=ROOT).decode())
    current = symbols((ROOT / 'dist/abaqus-after-hours.sym').read_text(encoding='utf-8'))
    ram = lambda value: value < 0x2000 or 0x7e0000 <= value < 0x800000
    previous_ram = {name: value for name, value in prior.items() if ram(value)}
    moved = {name: [value, current.get(name)] for name, value in previous_ram.items()
             if current.get(name) != value}
    added = {name: value for name, value in current.items() if ram(value) and name not in prior}
    require(len(previous_ram) == 1318 and not moved and not added,
            'Existing WRAM/direct-page ABI must remain exact', [len(previous_ram), moved, added])
    inventory = {str(p.relative_to(ROOT)).replace('\\', '/')
                 for p in (ROOT / 'assets/generated').iterdir() if p.is_file() and p.name != 'soundbank.h'}
    expected = set(subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASE,
                                         'assets/generated'], cwd=ROOT, text=True).splitlines())
    require(inventory == expected and len(inventory) == 226,
            'The complete generated inventory must remain 226 files')
    return {'baseline_commit': BASE, 'generated_total': 226,
            'generated_preserved': 226 - sum(p.startswith('assets/generated/') for p in changed),
            'changed': changed, 'prior_ram_labels': len(previous_ram),
            'moved_ram': moved, 'added_ram': added,
            'hardware_and_trace_preserved': True}


class AccuracyMenu(compat.Probe):
    @property
    def frame(self):
        if self.frame_image is None:
            return None
        return self.frame_image.resize((256, 224), Image.Resampling.NEAREST)


def run_core(independent, syms):
    engine = 'accuracy' if independent else 'snes9x'
    states, captures, failures, steady = [], [], [], 0
    for mode in range(3):
        host = AccuracyMenu() if independent else Emulator()
        try:
            def native():
                def read(name, count):
                    return int.from_bytes(C.string_at(host.ram + (syms[name] & 0x1ffff), count), 'little')
                return {'frame': read('frame', 2), 'lag': read('lag_frame_counter', 2),
                        'vblank': read('snes_vblank_count', 2), 'screen': read('screen', 1)}

            def run(count, p1=(), p2=(), transition=False):
                nonlocal steady
                for _ in range(count):
                    before = native()
                    host.run(1, p1=p1, p2=p2)
                    after = native()
                    if not transition:
                        steady += 1
                        delta = {key: (after[key] - before[key]) & 65535
                                 for key in ('frame', 'lag', 'vblank')}
                        if delta != {'frame': 1, 'lag': 0, 'vblank': 1}:
                            failures.append({'mode': mode, 'at': steady, 'delta': delta,
                                             'before': before, 'after': after})
                        require(not (host.state().get('ppu_stat', 0) & 0xc0),
                                'Native PPU overflow', host.state())

            def pulse(key, port=0, transition=False):
                keys = {'p1': [key]} if port == 0 else {'p2': [key]}
                run(3, **keys, transition=transition)
                run(36 if transition else 20, transition=transition)

            def record(label, save=False):
                image = host.frame
                require(image is not None and image.size == (256, 224), 'Native menu video', label)
                entry = {'mode': mode, 'label': label, 'state': host.state(),
                         'rgb_sha256': sha(image.tobytes())}
                if save:
                    path = CAPTURES / engine / f'mode{mode}-{label}.png'
                    path.parent.mkdir(parents=True, exist_ok=True)
                    image.save(path)
                    entry['capture'] = path.relative_to(ROOT).as_posix()
                    entry['capture_sha256'] = sha(path.read_bytes())
                    captures.append(entry['capture'])
                states.append(entry)

            host.run(120)
            require(native()['screen'] == 0, 'Native title boot', engine)
            run(10)
            record('title', True)
            for _ in range(mode):
                pulse('down')
            pulse('a', transition=True)
            require(native()['screen'] == 1, 'Title confirm opens roster')
            for player in range(2 if mode else 1):
                field = 'selected2' if player else 'selected'
                for _ in range(12):
                    selected = host.state()[field]
                    presentation.verify_large_portrait(host, selected)
                    presentation.verify_select_card_render(host)
                    presentation.verify_select_markers(host)
                    record(f'p{player+1}-{selected:02}', selected in (0, 11))
                    pulse('right', player)
                original = host.state()[field]
                pulse('down', player)
                require(host.state()[field] == (original + 6) % 12,
                        'Vertical movement matches the six-card row')
                pulse('up', player)
                require(host.state()[field] == original, 'Vertical return preserves the column')
                if player:
                    for _ in range((host.state()['selected'] - host.state()['selected2']) % 12):
                        pulse('right', 1)
                    presentation.verify_select_markers(host)
                    record('mirror', True)
                pulse('a', player, transition=True)
            require(native()['screen'] == 2, 'Roster confirmation opens arenas')
            for arena in range(3):
                require(host.state()['arena'] == arena, 'Arena order is preserved')
                record(f'arena{arena}', True)
                if arena < 2:
                    pulse('down')
            require(host.audio_peak < 32767 and host.audio_samples > 0,
                    'Native menu PCM stays active and unclipped')
        finally:
            host.close()
    require(len(states) == 74, 'Complete title/roster/mirror/arena coverage', len(states))
    return {'status': 'failed' if failures else 'passed', 'states': states, 'state_count': len(states),
            'steady_callbacks': steady, 'native_failures': failures, 'captures': captures}


def main():
    start = time.monotonic()
    dependencies = {name: sha((ROOT / name).read_bytes()) for name in DEPENDENCIES}
    manifest = json.loads((ROOT / 'dist/manifest.json').read_bytes())
    report = {'status': 'failed', 'version': manifest['version'], 'rom_sha256': manifest['sha256'],
              'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'host': host_contract(), 'dependencies': dependencies}
    try:
        require(sha((ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()) == manifest['sha256'], 'ROM/manifest binding')
        report['preservation'] = preservation()
        report['snes9x_core'] = core_identity()
        report['accuracy_core'] = compat.verify_manifest_and_pinned_core()
        syms = symbols((ROOT / 'dist/abaqus-after-hours.sym').read_text(encoding='utf-8'))
        report['snes9x'] = run_core(False, syms)
        report['accuracy'] = run_core(True, syms)
        require(report['snes9x']['status'] == report['accuracy']['status'] == 'passed',
                'Strict steady menu cadence/SDK counters', {
                    name: report[name]['native_failures'] for name in ('snes9x', 'accuracy')})
        require(dependencies == {name: sha((ROOT / name).read_bytes()) for name in DEPENDENCIES},
                'Source/harness changed during the native proof')
        report['status'] = 'passed'
    except Exception as exc:
        report['error'] = repr(exc)
        raise
    finally:
        report['seconds'] = round(time.monotonic() - start, 3)
        REPORT.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({name: report[name] for name in ('status', 'version', 'rom_sha256', 'seconds')}))


if __name__ == '__main__':
    main()
