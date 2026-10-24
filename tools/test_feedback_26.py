"""Earn punish/counter feedback and compare complete native combat state.

Both cartridges run identical controller streams. All 128 Fighter and 32 Wave
bytes, RNG and controller latches remain unmasked. Presentation-only banner
classification is intentionally outside that gameplay comparison.
"""
import argparse
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
from test_champion import host_contract
from test_play_flow_26 import source_hashes

BASE = '7e1e68d'
BASE_ROM = '558bff28c45765e7b6997e3cdbb0ced8fa631237f30b267011dc5d269a63e4ce'
CHECKS = []
OUT = ROOT / 'docs/screenshots/play-flow-v026'
STREAMS = ROOT / 'build/v026-feedback-streams'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(ok, label, details=None):
    CHECKS.append({'check': label, 'passed': bool(ok), 'details': details})
    if not ok:
        raise AssertionError((label, details))


class Rig(balance.Rig):
    def __init__(self, fighter, port, phase):
        self.port, self.fighter, self.phase = port, fighter, phase
        self.a, self.d = str(port + 1), str(2 - port)
        self.tag = f'{phase} fighter{fighter:02} P{port + 1}'
        self.e = boot(1, fighter, fighter % 3, fighter,
                      rom=STREAMS / 'before.sfc' if phase == 'before' else None)
        self.syms = monitor.SYMS
        self.base = self.syms['fighters'] & 0x1ffff
        self.stream = []

    def step(self, attack=(), defend=()):
        s = super().step(attack, defend)
        record = b''.join(C.string_at(self.e.ram + (self.syms[name] & 0x1ffff), count)
                          for name, count in (('fighters', 128), ('waves', 32), ('randomseed', 2),
                                              ('pad0', 2), ('pad1', 2), ('edge0', 2), ('edge1', 2)))
        self.stream.append({'attack': list(attack), 'defend': list(defend), 'state': record.hex()})
        return s

    def flag(self):
        return C.string_at(self.e.ram + (self.syms['impactBannerCounter'] & 0x1ffff), 1)[0]

    def raw_timing(self, side):
        raw = C.string_at(self.e.ram + self.base + (int(side) - 1) * 64, 64)
        return {'tick': raw[17], 'startup': raw[24], 'active_end': raw[63], 'end': raw[62]}


def case(fighter, port, phase, scenario):
    r = Rig(fighter, port, phase)
    try:
        r.position(23)
        if scenario.startswith('punish'):
            key = 'x' if scenario == 'punish-punch' else 'a'
            guard = ('down', r.direction(False, True))
            back = ('down', r.direction(False))
            s = r.step((key,), guard)
            for _ in range(80):
                if s[f'connected{r.a}']:
                    break
                s = r.step((), guard)
            require(s[f'connected{r.a}'] == 1 and s[f'guard{r.d}'] == 1,
                    'punish begins with a real blocked heavy', [r.tag, scenario, s])
            sent = False
            for _ in range(100):
                keys = guard
                if not sent and not s[f'hurt{r.d}']:
                    keys = ('y', r.direction(False, True))
                    sent = True
                prior = r.raw_timing(r.a)
                prior_action = s[f'action{r.a}']
                s = r.step(back, keys)
                if sent and s[f'connected{r.d}']:
                    break
            require(s[f'connected{r.d}'] == 2 and s[f'hp{r.a}'] < 128 and not s[f'guard{r.a}'],
                    'defender earns real unblocked jab damage after blocking', [r.tag, scenario, s])
            require(prior_action != 0 and prior['tick'] >= prior['active_end'],
                    'the punished attack was still in actual recovery at contact', [r.tag, scenario, prior])
            require(s[f'counter{r.d}'] == 0, 'recovery feedback does not become a damage-boosting startup counter', r.tag)
            flag = 2 if phase == 'after' else 0
            winner_port = 1 - port
            label = 'PUNISH!'
        else:
            guard = ('down', r.direction(False, True)) if scenario == 'guard' else ('x',) if scenario == 'counter' else ()
            # Crouch guard needs a real low contact; a standing jab can
            # legitimately pass above a compact fighter's crouching head.
            s = r.step(('down', 'b') if scenario == 'guard' else ('y',), guard)
            for _ in range(60):
                if s[f'connected{r.a}']:
                    break
                s = r.step((), ('down', r.direction(False, True)) if scenario == 'guard' else ())
            require(s[f'connected{r.a}'] == (1 if scenario == 'guard' else 2),
                    'negative/control contact is an actual hit or block', [r.tag, scenario, s])
            flag = 1 if scenario == 'counter' else 0
            winner_port = port
            label = 'COUNTER!' if scenario == 'counter' else None
            require(s[f'counter{r.a}'] == flag, 'startup-counter gameplay flag retains its original meaning', [r.tag, scenario, s])
        require(r.flag() == flag, 'banner classification distinguishes recovery startup guard and ordinary hits',
                [r.tag, scenario, r.flag(), flag])
        for _ in range(8):
            r.step()
        if phase == 'after' and label:
            presentation.verify_opaque_text_rows(r.e, [(9, 20 if winner_port else 2, label)], 'earned contact feedback')
            if fighter == 0:
                path = OUT / f'{scenario}-p{winner_port + 1}.png'
                r.e.frame.save(path)
        if not label:
            text = ''.join(chr((presentation.map_row(presentation.vram_bytes(r.e), 9)[x] & 1023) - 256)
                           if 288 <= (presentation.map_row(presentation.vram_bytes(r.e), 9)[x] & 1023) < 384 else ' '
                           for x in range(32))
            require('PUNISH' not in text, 'guard and ordinary hits never advertise a punish', [r.tag, scenario, text])
        for _ in range(80):
            r.step()
        r.settle()
        raw = (json.dumps(r.stream, separators=(',', ':')) + '\n').encode()
        path = STREAMS / f'{fighter:02}-p{port + 1}-{scenario}-{phase}.json.gz'
        path.write_bytes(gzip.compress(raw, mtime=0))
        return r.stream, {'fighter': fighter, 'port': port, 'scenario': scenario, 'phase': phase,
                          'callbacks': len(r.stream), 'unmasked_stream_sha256': sha(raw),
                          'retained_source_stream': path.relative_to(ROOT).as_posix(),
                          'compressed_sha256': sha(path.read_bytes())}
    finally:
        r.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fighters', default=','.join(map(str, range(12))))
    parser.add_argument('--report', type=Path, default=Path('docs/play-flow-v026-feedback-report.json'))
    args = parser.parse_args()
    fighters = list(map(int, args.fighters.split(',')))
    require(bool(fighters) and len(set(fighters)) == len(fighters) and all(f in range(12) for f in fighters), 'fighter selection is valid')
    path = (ROOT / args.report).resolve()
    require(fighters == list(range(12)) or path.is_relative_to(ROOT / 'build'), 'partial feedback proof remains diagnostic')
    OUT.mkdir(parents=True, exist_ok=True)
    STREAMS.mkdir(parents=True, exist_ok=True)
    baseline = subprocess.check_output(['git', 'show', BASE + ':dist/abaqus-after-hours.sfc'], cwd=ROOT)
    require(sha(baseline) == BASE_ROM, 'paired reference is the committed pre-feedback cartridge')
    (STREAMS / 'before.sfc').write_bytes(baseline)
    subprocess.run(['git', 'merge-base', '--is-ancestor', BASE, 'HEAD'], cwd=ROOT, check=True)
    before = source_hashes()
    started = time.monotonic()
    manifest = json.loads((ROOT / 'dist/manifest.json').read_bytes())
    report = {'status': 'failed', 'version': manifest['version'], 'rom_sha256': manifest['sha256'],
              'baseline_commit': BASE, 'baseline_rom_sha256': BASE_ROM, 'source_sha256': before,
              'host_contract': host_contract(), 'controller_only': True, 'memory_writes': False,
              'save_states': False, 'checks': CHECKS, 'cases': [], 'native_health': monitor.HEALTH}
    original = Emulator.run

    def singles(e, count=1, *args, **kwargs):
        for _ in range(count):
            s = monitor.monitored_run(e, 1, *args, **kwargs)
        return s if count else e.state()

    try:
        require(sha((ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()) == manifest['sha256'], 'feedback proof uses exact current cartridge')
        require(sha((ROOT / '.tools/core/snes9x_libretro.dll').read_bytes()).lower() == monitor.EXPECTED_NATIVE_CORE['dll_sha256'].lower(),
                'feedback proof uses the actual pinned expanded native core')
        Emulator.run = singles
        for fighter in fighters:
            for port in (0, 1):
                for scenario in ('punish-punch', 'punish-kick', 'counter', 'idle-hit', 'guard'):
                    baseline_stream, prior = case(fighter, port, 'before', scenario)
                    candidate_stream, current = case(fighter, port, 'after', scenario)
                    require(candidate_stream == baseline_stream,
                            'identical controller stream preserves every unmasked Fighter Wave RNG and pad byte',
                            {'fighter': fighter, 'port': port, 'scenario': scenario,
                             'before_callbacks': len(baseline_stream), 'after_callbacks': len(candidate_stream)})
                    report['cases'].append({'before': prior, 'after': current, 'exact_unmasked_equality': True})
            print(json.dumps({'part': 'feedback', 'fighter': fighter, 'status': 'passed'}), flush=True)
        require(not monitor.HEALTH['failures'], 'feedback adds no native cadence OBJ or audio failures', monitor.HEALTH)
        require(source_hashes() == before, 'source and harness bytes remain fixed throughout feedback proof')
        report['captures'] = media_inventory(ROOT, 'feedback')
        report['status'] = 'passed'
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        Emulator.run = original
        report['check_count'] = len(CHECKS)
        report['presentation_checks'] = len(presentation.checks)
        report['native_checks'] = list(monitor.CHECKS.values())
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
        path.write_bytes((json.dumps(report, indent=2) + '\n').encode())
        print(json.dumps({k: report[k] for k in ('status', 'check_count', 'elapsed_seconds')}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
