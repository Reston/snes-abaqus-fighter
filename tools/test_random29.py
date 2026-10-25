"""Bounded controller-only random menu proof on the two pinned native cores."""
import argparse
import ctypes as C
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from emulator import Emulator
from test_classic_menu import AccuracyMenu
from test_training import core_identity
from test_compatibility import verify_manifest_and_pinned_core
from test_champion import host_contract
from menu_preview_checks import uploaded_pose, verify_preview
from v024_contracts import symbols
import test_presentation as presentation

BASE = 'c7510c30e129465bcca0b32e2142daec60546d0f'
CHECKS = []


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(ok, label, detail=None):
    if not ok:
        raise AssertionError((label, detail))
    CHECKS.append(label)


def inputs_snapshot():
    return {p.relative_to(ROOT).as_posix(): sha(p.read_bytes().replace(b'\r\n', b'\n'))
            for folder in ('src', 'tools') for p in sorted((ROOT / folder).iterdir())
            if p.is_file() and p.suffix in ('.c', '.h', '.asm', '.py')}


def preservation(syms):
    archive = subprocess.check_output(['git', 'archive', BASE, 'assets/generated',
                                       'src/hardware.asm', 'src/trace.asm'], cwd=ROOT)
    unchanged = []
    with tarfile.open(fileobj=io.BytesIO(archive)) as files:
        for item in files:
            if not item.isfile():
                continue
            before, after = files.extractfile(item).read(), (ROOT / item.name).read_bytes()
            if Path(item.name).suffix in ('.h', '.asm', '.json'):
                before, after = before.replace(b'\r\n', b'\n'), after.replace(b'\r\n', b'\n')
            require(before == after, 'Baseline asset/assembly exact', item.name)
            unchanged.append(item.name)
    old = symbols(subprocess.check_output(['git', 'show', BASE + ':dist/abaqus-after-hours.sym'], cwd=ROOT).decode())
    ram = lambda value: value < 0x2000 or 0x7e0000 <= value < 0x800000
    prior = {n: v for n, v in old.items() if ram(v)}
    moved = {n: [v, syms.get(n)] for n, v in prior.items() if syms.get(n) != v}
    markers = {'SECTIONEND_globram.data', 'RAM_USAGE_SLOT_3_BANK_127_END'}
    require(set(moved) == markers and all(b == a + 176 for a, b in moved.values()),
            'Only two end markers grow by shared six-feature reservation', moved)
    added = {n: v for n, v in syms.items() if ram(v) and n not in old}
    expected = {'v29DefenseState', 'v29BonusState', 'v29AutoState', 'v29RandomState', 'v29AudioState', 'v29ArenaState'}
    require(set(added) == expected, 'No mutable globals beyond parent reservations', added)
    sections = {}
    for name, start in syms.items():
        if not name.startswith('SECTIONSTART_') or start < 0x8000 or ram(start):
            continue
        end = syms.get(name.replace('SECTIONSTART_', 'SECTIONEND_', 1))
        if end is None or end <= start:
            continue
        require((start & 0x7fff) + end - start <= 32768, 'Linked section fits a LoROM bank', name)
        sections[name] = end - start
    require(len([n for n in unchanged if n.startswith('assets/generated/')]) == 226,
            'All 226 generated assets preserved')
    return {'baseline': BASE, 'generated_preserved': 226, 'hardware_trace_exact': True,
            'prior_ram_labels': len(prior), 'moved_markers': moved, 'new_reserved_labels': added,
            'sections_bytes': sections, 'feature_mutable_bytes_used': 4, 'feature_reservation_bytes': 8,
            'new_obj_entries': 0, 'actor_upload_bytes_per_vblank_max': 3840,
            'new_dma_bytes': 0, 'generator_hooks': [], 'generated_output_allowlist': []}


class Session:
    def __init__(self, core, mode, syms, captures):
        self.core, self.mode, self.syms, self.captures = core, mode, syms, captures
        self.host = AccuracyMenu() if core == 'accuracy' else Emulator(core_options={'snes9x_up_down_allowed': 'enabled'})
        self.callbacks = 0
        self.media = []
        self.roles = []

    def read(self, name, size=1):
        return int.from_bytes(C.string_at(self.host.ram + (self.syms[name] & 0x1ffff), size), 'little')

    def counters(self):
        return [self.read(n, 2) for n in ('frame', 'snes_vblank_count', 'lag_frame_counter')]

    def run(self, count=1, p1=(), p2=(), transition=False):
        for _ in range(count):
            before, scene = self.counters(), self.read('screen')
            self.host.run(1, p1=p1, p2=p2)
            if not transition:
                delta = [(a - b) & 65535 for a, b in zip(self.counters(), before)]
                require(delta == [1, 1, 0], 'Native frame/vblank/SDK cadence', [self.core, self.mode, scene, delta])
                stat = int.from_bytes(C.string_at(self.host.ram + 0x1ff00 + 114 * 2, 2), 'little')
                require(not stat & 0xc0, 'No OBJ range/time overflow', stat)
                self.callbacks += 1
            if self.read('screen') <= 2:
                require(self.read('randomseed', 2) == 0xaba, 'Menu never consumes combat RNG')

    def keys(self, keys, port=0, count=3, transition=False):
        self.run(count, **{'p1' if port == 0 else 'p2': keys}, transition=transition)

    def pulse(self, key, port=0, transition=False):
        self.keys([key], port, transition=transition)
        self.run(5, transition=transition)

    def seed(self):
        return self.read('v29RandomState', 2)

    def save(self, label):
        path = self.captures / self.core / f'mode{self.mode}-{label}.png'
        path.parent.mkdir(parents=True, exist_ok=True)
        self.host.frame.save(path)
        self.media.append({'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path.read_bytes())})

    def select_checks(self, fighter):
        require(uploaded_pose(self.host, fighter) in (16, 17, 18, 19), 'Random hover uses standing poses', fighter)
        pixels = verify_preview(self.host, fighter)
        presentation.verify_select_card_render(self.host)
        presentation.verify_select_markers(self.host)
        presentation.verify_menu_font_bank(self.host, [(27, 1, 'A/START  SELECT: RANDOM  B BACK')], 'Random roster hint')
        require(self.read('menuPreviewConfirm') == 0, 'Random awaits explicit confirmation')
        return pixels

    def sweep(self, role):
        field = 'selected2' if role else 'selected'
        before = self.read(field)
        self.pulse('down', role)
        require(self.read(field) == (before + 6) % 12, 'Down retains six-slot navigation')
        self.pulse('up', role)
        require(self.read(field) == before, 'Up retains six-slot navigation')
        self.keys(['left', 'right', 'up', 'down'], role)
        self.run(4)
        require(self.read(field) == before, 'Held opposite directions cancel')
        if role:
            self.run(3, p1=['left'], p2=['right'])
            self.run(4)
            require(self.read(field) == before, 'Opposites across participating pads cancel')
        seen, values, visual, ports = set(), [], [], set()
        mirror = False
        for attempt in range(96):
            port = attempt % 2 if role else 0
            ports.add(port)
            self.run(attempt % 5)
            self.keys(['select'], port, count=5)
            picked, seed = self.read(field), self.seed()
            if attempt == 0:
                self.keys(['select'], port, count=40)
                require(self.read(field) == picked and self.seed() == seed,
                        'Held SELECT never rerolls')
            self.run(5)
            require(0 <= picked < 12 and self.read('screen') == 1 and self.read('selectPlayer') == role,
                    'Random fighter remains valid on the same selection step')
            require(self.seed() == seed, 'Releasing SELECT never rerolls')
            if picked not in seen:
                visual.append(self.select_checks(picked))
                if self.mode == 0:
                    self.save(f'random-{picked:02}')
            seen.add(picked)
            values.append(picked)
            if role and picked == self.read('selected'):
                presentation.verify_select_markers(self.host)
                if not mirror:
                    self.save('random-mirror')
                mirror = True
            if len(seen) == 12 and (not role or mirror):
                break
        require(seen == set(range(12)), 'Every fighter reachable through fresh SELECT', values)
        require(not role or mirror, 'Random permits mirrors')
        require(ports == ({0, 1} if role else {0}), 'Both participating pads exercised', sorted(ports))
        # Same SELECT edge on both participating pads must produce one choice.
        if role:
            self.run(3, p1=['select'], p2=['select'])
            seed = self.seed()
            self.run(5, p1=['select'], p2=['select'])
            require(seed == self.seed(), 'Simultaneous held SELECT has one shared action')
            self.run(5)
        self.roles.append({'role': role, 'values': values, 'reachable': sorted(seen),
                           'mirror': mirror, 'ports': sorted(ports), 'preview_pixels': visual})

    def confirm(self, role, chord, port, other=()):
        field = 'selected2' if role else 'selected'
        picked, seed = self.read(field), self.seed()
        pads = {'p1': chord if port == 0 else other, 'p2': chord if port == 1 else other}
        self.run(1, **pads)
        input_latency = 1
        # Accuracy can deliver the fresh controller sample one callback later.
        # Count the lock from native acceptance, while checking every idle
        # callback's full frame/vblank/lag deltas as well.
        while self.read('menuPreviewConfirm') == 0 and input_latency < 3:
            self.run(1, **pads)
            input_latency += 1
        observed, poses = [], []
        for _ in range(24):
            if self.read('screen') != 1 or self.read('selectPlayer') != role:
                break
            observed.append(self.read('menuPreviewConfirm'))
            poses.append(uploaded_pose(self.host, picked))
            self.run(1, **pads, transition=True)
        require(observed == list(range(1, 19)), 'Normal 18-tick confirmation lock preserved', observed)
        require(self.seed() == seed, 'Start/A beats SELECT without consuming menu RNG')
        require(self.read(field) == picked, 'Confirmation keeps the highlighted random pick')
        personality = (ROOT / 'src/fighter_personality.h').read_text().split('personalityIntroFrames[12][4]={', 1)[1].split('};', 1)[0]
        rows = [list(map(int, re.findall(r'\d+', line.split('/*')[0]))) for line in personality.splitlines() if '{' in line]
        require(all(p in poses for p in (rows[picked][0], rows[picked][1], 11)),
                'Approved signature and victory poses retained', poses)
        self.run(8, **pads, transition=True)
        self.run(6, transition=True)
        require(self.read('screen') == (1 if self.mode and not role else 2),
                'Held confirm advances only one step')
        return {'role': role, 'fighter': picked, 'ticks': observed, 'poses': poses, 'pads': pads,
                'input_callbacks_until_accepted': input_latency}

    def arenas(self):
        seen, values, ports = set(), [], set()
        for attempt in range(32):
            port = attempt % 2 if self.mode == 1 else 0
            ports.add(port)
            self.run(attempt % 4)
            self.keys(['select'], port, count=4)
            picked, seed = self.read('arena'), self.seed()
            self.keys(['select'], port, count=32 if attempt == 0 else 3)
            require(self.read('arena') == picked and self.seed() == seed, 'Held arena SELECT never rerolls')
            self.run(4)
            require(0 <= picked < 3 and self.read('screen') == 2, 'Random arena stays valid awaiting confirmation')
            presentation.verify_arena_cursor(self.host, picked)
            presentation.verify_arena_plate(self.host, picked)
            hint = 'SELECT: RANDOM / EITHER PAD' if self.mode == 1 else 'SELECT: RANDOM'
            presentation.verify_opaque_text_rows(self.host, [(26, 1 if self.mode == 1 else 9, hint)], 'Random arena hint')
            if picked not in seen:
                self.save(f'arena-{picked}')
            seen.add(picked)
            values.append(picked)
            if len(seen) == 3 and len(ports) == (2 if self.mode == 1 else 1):
                break
        require(seen == {0, 1, 2}, 'Every arena reachable through fresh SELECT', values)
        if self.mode != 1:
            before = self.seed(), self.read('arena')
            self.pulse('select', 1)
            require((self.seed(), self.read('arena')) == before, 'Nonparticipating P2 cannot randomize arena')
        # Back owns a shared chord before A/SELECT; Start owns it before Back.
        seed = self.seed()
        if self.mode == 1:
            self.run(3, p1=['a', 'select'], p2=['b'], transition=True)
        else:
            self.keys(['b', 'a', 'select'], transition=True)
        self.run(8, transition=True)
        require(self.read('screen') == 1 and self.seed() == seed, 'Arena B beats A/SELECT and returns to roster')
        self.confirm(0, ['a'], 0)
        if self.mode:
            self.confirm(1, ['a'], 1)
        selected = [self.read('selected'), self.read('selected2')]
        arena = self.read('arena')
        seed = self.seed()
        if self.mode == 1:
            self.run(3, p1=['b', 'a', 'select'], p2=['start'], transition=True)
        else:
            self.keys(['start', 'b', 'a', 'select'], transition=True)
        self.run(24, transition=True)
        require(self.read('screen') == 3 and self.seed() == seed, 'Arena Start beats Back/A/SELECT and launches confirmed arena')
        # The menu stream must stop throughout real native intro/combat.
        random_state = C.string_at(self.host.ram + (self.syms['v29RandomState'] & 0x1ffff), 8)
        if self.mode == 0:
            self.keys(['a'], transition=True)
            self.run(3, transition=True)
        for _ in range(500):
            if self.host.state()['screen'] == 3 and self.host.state()['intro'] == 0:
                break
            self.run(transition=True)
        require(self.host.state()['intro'] == 0, 'Random choices hand off to live combat')
        self.run(36)
        require(C.string_at(self.host.ram + (self.syms['v29RandomState'] & 0x1ffff), 8) == random_state,
                'All menu RNG bytes freeze during fights')
        require(self.host.state()['arena'] == arena and self.host.state()['fighter_id1'] == selected[0]
                and self.host.state()['fighter_id2'] == selected[1], 'Fight uses confirmed random fighter/arena IDs')
        require(self.host.audio_samples > 0 and self.host.audio_peak < 32767, 'Captured native PCM active and unclipped')
        return {'values': values, 'reachable': sorted(seen), 'ports': sorted(ports),
                'fight_ids': selected, 'fight_arena': arena, 'fight_samples': 36}

    def execute(self):
        self.host.run(120)
        self.run(5)
        for _ in range(self.mode):
            self.pulse('down')
        self.pulse('a', transition=True)
        require(self.read('screen') == 1, 'Native title enters roster')
        seed, fighter = self.seed(), self.read('selected')
        self.pulse('select', 1)
        require(self.seed() == seed and self.read('selected') == fighter, 'P2 cannot randomize P1')
        # Roster Back owns the A/SELECT chord and keeps its ordinary route.
        self.keys(['b', 'a', 'select'], transition=True)
        self.run(10, transition=True)
        require(self.read('screen') == 0 and self.seed() == seed, 'Roster B beats A/SELECT')
        self.pulse('a', transition=True)
        gestures = []
        self.sweep(0)
        # Probe every breathing frame after a random choice.
        idle = set()
        for _ in range(100):
            idle.add(uploaded_pose(self.host, self.read('selected')))
            self.run()
        require(idle == {16, 17, 18, 19}, 'All original breathing frames retained', sorted(idle))
        gestures.append(self.confirm(0, ['start', 'b', 'a', 'select'], 0))
        if self.mode:
            self.sweep(1)
            # P2 Back returns to P1 before confirming P2 again.
            seed = self.seed()
            self.keys(['b', 'a', 'select'], 1, transition=True)
            self.run(7, transition=True)
            require(self.read('selectPlayer') == 0 and self.seed() == seed, 'Participating P2 Back beats A/SELECT')
            gestures.append(self.confirm(0, ['a'], 0))
            gestures.append(self.confirm(1, ['select'], 0, other=['a']))
        arenas = self.arenas()
        return {'core': self.core, 'mode': self.mode, 'roles': self.roles, 'gestures': gestures,
                'arenas': arenas, 'strict_callbacks': self.callbacks, 'media': self.media}


def timing_proof(core, syms, captures):
    sequences = []
    for delay in (0, 7):
        session = Session(core, 0, syms, captures)
        try:
            session.host.run(120)
            session.run(delay)
            session.pulse('a', transition=True)
            values = []
            for _ in range(8):
                session.pulse('select')
                values.append(session.read('selected'))
            sequences.append({'extra_title_callbacks': delay, 'values': values,
                              'strict_callbacks': session.callbacks})
        finally:
            session.host.close()
    require(sequences[0]['values'] != sequences[1]['values'],
            'User timing changes repeated random picks', sequences)
    return sequences


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core', choices=('snes9x', 'accuracy', 'both'), default='both')
    parser.add_argument('--report', type=Path, default=ROOT / 'docs/random29-report.json')
    parser.add_argument('--captures', type=Path, default=ROOT / 'docs/screenshots/random29')
    args = parser.parse_args()
    started = time.monotonic()
    sources = inputs_snapshot()
    manifest = json.loads((ROOT / 'dist/manifest.json').read_bytes())
    syms = symbols((ROOT / 'dist/abaqus-after-hours.sym').read_text())
    report = {'status': 'failed', 'rom_sha256': sha((ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()),
              'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'sources_sha256_lf': sources, 'host': host_contract(), 'sessions': [], 'cores': {},
              'timing_proof': {},
              'memory_writes': False, 'save_states': False, 'combined_verification_claimed': False}
    try:
        require(report['rom_sha256'] == manifest['sha256'], 'Exact ROM manifest')
        require(report['host'].get('logical_processors') == [8, 9] and report['host'].get('priority_class') == 0x4000,
                'Assigned processor pair / below-normal priority', report['host'])
        report['preservation'] = preservation(syms)
        # Exact rejection domain: each outcome owns the same number of bytes.
        report['uniform_domain'] = {str(n): [sum(x % n == y for x in range(252)) for y in range(n)] for n in (12, 3)}
        for n in (12, 3):
            require(len(set(report['uniform_domain'][str(n)])) == 1, 'Unbiased accepted-byte domain', n)
        for core in (('snes9x', 'accuracy') if args.core == 'both' else (args.core,)):
            report['cores'][core] = core_identity() if core == 'snes9x' else verify_manifest_and_pinned_core()
            report['timing_proof'][core] = timing_proof(core, syms, args.captures.resolve())
            for mode in range(3):
                session = Session(core, mode, syms, args.captures.resolve())
                try:
                    result = session.execute()
                    report['sessions'].append(result)
                    print(json.dumps({'core': core, 'mode': mode, 'status': 'passed', 'callbacks': result['strict_callbacks']}), flush=True)
                except BaseException:
                    report['failed_native_state'] = session.host.state()
                    report['failed_symbols'] = {n: session.read(n, 2 if n in ('frame', 'randomseed') else 1)
                                                for n in ('frame', 'screen', 'selected', 'selected2', 'selectPlayer', 'arena', 'menuPreviewConfirm', 'randomseed')}
                    raise
                finally:
                    session.host.close()
        require(sources == inputs_snapshot(), 'Producer/harness inputs stayed frozen')
        require(report['rom_sha256'] == sha((ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()), 'Exact ROM stayed frozen')
        for session in report['sessions']:
            for media in session['media']:
                require(sha((ROOT / media['path']).read_bytes()) == media['sha256'], 'Final capture bytes match recorded hash', media['path'])
        report['status'] = 'passed'
    except BaseException as error:
        report['error'] = repr(error)
        raise
    finally:
        report.update(checks_passed=len(CHECKS), check_labels=sorted(set(CHECKS)),
                      shared_presentation_checks=len(presentation.checks), seconds=round(time.monotonic() - started, 3))
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_bytes((json.dumps(report, indent=2) + '\n').encode())
        print(json.dumps({k: report[k] for k in ('status', 'checks_passed', 'seconds')}), flush=True)


if __name__ == '__main__':
    main()
