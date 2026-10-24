"""Earn throw-tech feedback; preserve complete combat bytes against its parent."""
import ctypes as C
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emulator import Emulator, ROOT
from play_flow_media import inventory as media_inventory
from test_characters import boot
import test_expansion_03_normal_balance as balance
import test_pacing_floor_25 as monitor
import test_presentation as presentation
import test_compatibility as compatibility
import test_inputs as inputs
import test_music_26 as native
from test_play_flow_26 import source_hashes
from test_champion import host_contract

BASE = 'a047b54'
BASE_ROM = 'a42c91d621d2522c3c70200e2e2d0305d4b99f4b6e829ea664a317a5462ada7c'
OUT = ROOT / 'build/v026-throw-streams'
CHECKS = []


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(ok, label, details=None):
    CHECKS.append({'check': label, 'passed': bool(ok), 'details': details})
    if not ok:
        raise AssertionError((label, details))


class Rig(balance.Rig):
    def __init__(self, fighter, port, phase):
        self.port, self.fighter = port, fighter
        self.a, self.d = str(port + 1), str(2 - port)
        self.tag = f'{phase} fighter{fighter:02} P{port + 1}'
        self.e = boot(1, fighter, fighter % 3, fighter, rom=OUT / 'before.sfc' if phase == 'before' else None)
        self.syms = monitor.SYMS
        self.base = self.syms['fighters'] & 0x1ffff
        self.stream = []

    def step(self, attack=(), defend=()):
        s = super().step(attack, defend)
        raw = b''.join(C.string_at(self.e.ram + (self.syms[name] & 0x1ffff), size)
                       for name, size in (('fighters', 128), ('waves', 32), ('randomseed', 2),
                                          ('pad0', 2), ('pad1', 2), ('edge0', 2), ('edge1', 2)))
        self.stream.append({'attack': list(attack), 'defend': list(defend), 'state': raw.hex()})
        return s


def case(fighter, port, phase, tech):
    r = Rig(fighter, port, phase)
    try:
        # Position() accepts a one-pixel band; leave margin inside the strict
        # '< range' command test rather than accidentally requesting a punch.
        r.position(min(r.state()['throw_range1'], r.state()['throw_range2']) - 4)
        before = r.state()
        first = (r.direction(), 'x')
        second = (r.direction(True, True), 'x') if tech else ()
        s = r.step(first, second)
        event = None
        for index in range(100):
            if tech and s['guard1'] and s['guard2'] and s['hurt1'] and s['hurt2']:
                event = s
                break
            if not tech and s[f'down_state{r.d}']:
                event = s
                break
            s = r.step()
        require(event is not None, 'real controller throw attempt reaches tech or a linked victim',
                [r.tag, tech, s])
        if tech:
            require(s['hp1'] == s['hp2'] == 128 and s['connected1'] == s['connected2'] == 1,
                    'mutual throw earns a non-damaging escape for both players', [r.tag, s])
            require(s['down_state1'] == s['down_state2'] == 0 and s['hitstop'] == 3,
                    'tech retains its original standing outcome and three-tick pause', r.tag)
            flag = native.read(r.e, 'impactBannerCounter')
            require(flag == (3 if phase == 'after' else 0),
                    'only the actual simultaneous throw gets the new tech classification', [r.tag, flag])
            for _ in range(8):
                r.step()
            if phase == 'after':
                start = len(presentation.checks)
                presentation.verify_opaque_text_rows(r.e, [(9, 10, 'THROW TECH!')], 'earned throw escape')
                require(all(c['passed'] for c in presentation.checks[start:]),
                        'the native PPU displays the earned throw-tech message')
                if fighter == 0:
                    r.e.frame.save(ROOT / f'docs/screenshots/play-flow-v026/throw-tech-p{port + 1}.png')
        else:
            require(native.read(r.e, 'impactBannerCounter') != 3,
                    'an ordinary one-sided throw cannot advertise a tech', r.tag)
        for _ in range(120):
            r.step()
        final = r.state()
        require(final['hp1'] == final['hp2'] == 128 if tech else final[f'hp{r.a}'] == 128 and final[f'hp{r.d}'] < 128,
                'throw escape versus delayed throw damage retains the original result', [r.tag, tech, final])
        data = (json.dumps(r.stream, separators=(',', ':')) + '\n').encode()
        path = OUT / f'{fighter:02}-p{port + 1}-{"tech" if tech else "throw"}-{phase}.json.gz'
        path.write_bytes(gzip.compress(data, mtime=0))
        return r.stream, {'fighter': fighter, 'port': port, 'tech': tech, 'phase': phase,
                          'callbacks': len(r.stream), 'unmasked_sha256': sha(data),
                          'retained_stream': path.relative_to(ROOT).as_posix(), 'gzip_sha256': sha(path.read_bytes())}
    finally:
        r.close()


def accuracy():
    original = inputs.Emulator
    try:
        inputs.Emulator = lambda **kwargs: native.Rig(True)
        e = inputs.boot(1, fighter=0, fighter2=0)
    finally:
        inputs.Emulator = original
    try:
        inputs._close_for_throw(e)
        s = inputs.trace(e)
        for _ in range(4):
            e.run(1, p1=['right' if s['face1'] else 'left', 'x'],
                  p2=['right' if s['face2'] else 'left', 'x'])
        e.run(12)
        require(native.read(e, 'impactBannerCounter') == 3 and inputs.trace(e)['hp1'] == inputs.trace(e)['hp2'] == 128,
                'pinned Accuracy independently earns the real non-damaging throw escape')
        presentation.verify_opaque_text_rows(e, [(9, 10, 'THROW TECH!')], 'Accuracy earned throw escape')
        require(not native.HEALTH['failures'], 'Accuracy throw feedback keeps strict native cadence and FIFO bounds')
    finally:
        e.close()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sources = source_hashes()
    started = time.monotonic()
    manifest = json.loads((ROOT / 'dist/manifest.json').read_bytes())
    report = {'status': 'failed', 'version': manifest['version'], 'rom_sha256': manifest['sha256'],
              'baseline_commit': BASE, 'baseline_rom_sha256': BASE_ROM, 'source_sha256': sources,
              'checks': CHECKS, 'native_health': monitor.HEALTH, 'host_contract': host_contract(),
              'controller_only': True, 'memory_writes': False, 'save_states': False, 'cases': []}
    original = Emulator.run

    def singles(e, count=1, *args, **kwargs):
        for _ in range(count):
            s = monitor.monitored_run(e, 1, *args, **kwargs)
        return s if count else e.state()

    try:
        baseline = subprocess.check_output(['git', 'show', BASE + ':dist/abaqus-after-hours.sfc'], cwd=ROOT)
        require(sha(baseline) == BASE_ROM, 'tech reference is the exact committed pre-feedback parent')
        (OUT / 'before.sfc').write_bytes(baseline)
        subprocess.run(['git', 'merge-base', '--is-ancestor', BASE, 'HEAD'], cwd=ROOT, check=True)
        require(sha((ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()) == manifest['sha256'],
                'throw proof loads the exact current cartridge')
        require(sha((ROOT / '.tools/core/snes9x_libretro.dll').read_bytes()).lower() == monitor.EXPECTED_NATIVE_CORE['dll_sha256'].lower(),
                'throw proof hashes the actual pinned expanded Snes9x core')
        report['independent_core'] = compatibility.verify_manifest_and_pinned_core()
        Emulator.run = singles
        for fighter in range(12):
            for port in (0, 1):
                for tech in (True, False):
                    old, prior = case(fighter, port, 'before', tech)
                    new, current = case(fighter, port, 'after', tech)
                    require(old == new, 'throw feedback preserves every unmasked Fighter Wave RNG and pad byte',
                            [fighter, port, tech, len(old), len(new)])
                    report['cases'].append({'before': prior, 'after': current, 'exact_unmasked_equality': True})
            print(json.dumps({'fighter': fighter, 'status': 'passed'}), flush=True)
        Emulator.run = original
        accuracy()
        require(not monitor.HEALTH['failures'], 'throw feedback has no native cadence OBJ or audio failures')
        require(source_hashes() == sources, 'throw proof inputs remain fixed')
        report['captures'] = media_inventory(ROOT, 'throw')
        report['status'] = 'passed'
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        Emulator.run = original
        report['check_count'] = len(CHECKS)
        report['native_checks'] = list(monitor.CHECKS.values())
        report['accuracy_native_health'] = native.HEALTH
        report['accuracy_native_check_count'] = len(native.CHECKS)
        report['accuracy_native_failed_checks'] = [c for c in native.CHECKS if not c['passed']]
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
        (ROOT / 'docs/play-flow-v026-throw-report.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
        print(json.dumps({k: report[k] for k in ('status', 'check_count', 'elapsed_seconds')}), flush=True)


if __name__ == '__main__':
    main()
