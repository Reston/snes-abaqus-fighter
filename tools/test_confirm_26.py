"""Real hit-confirm drills and recovery-guard behavior for the whole roster."""
import ctypes as C
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emulator import ROOT
from play_flow_media import inventory as media_inventory
import test_inputs as inputs
import test_training as training
import test_presentation as presentation
import test_expansion_03_normal_balance as balance
import test_music_26 as native
from test_play_flow_26 import source_hashes
from test_champion import host_contract

CHECKS = []
OUT = ROOT / 'docs/screenshots/play-flow-v026'


def require(ok, label, details=None):
    CHECKS.append({'check': label, 'passed': bool(ok), 'details': details})
    if not ok:
        raise AssertionError((label, details))


def read(e, name, size=1):
    return native.read(e, name, size)


class Rig(balance.Rig):
    def __init__(self, fighter, independent=False):
        original = inputs.Emulator
        try:
            inputs.Emulator = lambda **kwargs: native.Rig(independent)
            self.e = inputs.boot(2, fighter=fighter, fighter2=fighter)
        finally:
            inputs.Emulator = original
        self.fighter, self.port = fighter, 0
        self.a, self.d = '1', '2'
        self.independent = independent
        self.tag = f'fighter{fighter:02} {"Accuracy" if independent else "Snes9x"}'
        self.syms = {name: address + 0x7e0000 for name, address in native.SYMS.items()}
        self.base = native.SYMS['fighters']
        setup_port = fighter % 2
        inputs.press(self.e, 'start', setup_port)
        for _ in range(3):
            inputs.press(self.e, 'select', setup_port)
        inputs.press(self.e, 'x', setup_port)
        self.e.run(10)
        require(read(self.e, 'trainingDummy') == 6 and read(self.e, 'trainingResult') == 0,
                'drill restart supplies recovery guard and clears its result', [fighter, independent, setup_port])
        text = training.decode_text(presentation.vram_bytes(self.e), 12, 13).strip()
        require(text == 'HIT CONFIRM', 'first drill names its actual universal hit-confirm goal', text)
        inputs.press(self.e, 'start', 1 - setup_port)
        self.e.run(16)


def await_status(r, token):
    for waited in range(120):
        text = training.decode_text(presentation.vram_bytes(r.e), 27, 28)
        if token in text:
            return waited
        r.step()
    raise AssertionError(('native drill status did not arrive', token, r.tag, text))


def opener(r, key):
    r.position(23)
    before = r.state()
    require(before['hp2'] == 128 and before['raw_keys2'] == 0,
            'recovery guard stands neutral before the first real hit', [r.tag, before])
    s = r.step((key,))
    for _ in range(60):
        if s['connected1']:
            break
        s = r.step()
    require(s['connected1'] == 2 and s['hp2'] < 128 and s['combo_link1'] == 1,
            'confirm begins with one actual unblocked normal', [r.tag, key, s])
    require(read(r.e, 'trainingResult') == 1,
            'first normal arms the live LINK result without declaring success', r.tag)
    return s


def combo(fighter, first, second, independent=False):
    r = Rig(fighter, independent)
    try:
        initial = opener(r, first)
        s = r.step((second,))
        action = 3 if second == 'x' else 5
        for _ in range(100):
            if s['action1'] == action and s['connected1']:
                break
            s = r.step()
        require(s['action1'] == action and s['connected1'] == 2 and s['combo_link1'] == 2 and not s['guard2'],
                'light-to-strong confirm is a real two-hit combo through attempted guard', [r.tag, first, second, s])
        require(bool(s['raw_keys2'] & (0x200 if s['face2'] else 0x100)),
                'recovery dummy actually holds relative back during the true link', [r.tag, s['raw_keys2'], s['face2']])
        require(read(r.e, 'trainingResult') == 2 and read(r.e, 'trainingHits') == 2 and
                read(r.e, 'trainingDamage', 2) == 128 - s['hp2'],
                'DONE reflects two earned hits and their actual total damage', [r.tag, s])
        waited = await_status(r, 'C1 DONE!')
        if fighter == 0 and not independent:
            r.e.frame.save(OUT / f'hit-confirm-{first}-{second}.png')
        return {'fighter': fighter, 'route': first + '->' + second, 'independent': independent,
                'first_damage': 128 - initial['hp2'], 'total_damage': read(r.e, 'trainingDamage', 2),
                'combo_hits': 2, 'footer_wait_callbacks': waited, 'passed': True}
    finally:
        r.close()


def delayed(fighter, independent=False):
    r = Rig(fighter, independent)
    try:
        opener(r, 'y')
        for _ in range(100):
            s = r.state()
            if not s['hurt2'] and not s['action1'] and not s['hitstop']:
                break
            r.step()
        s = r.step(('x',))
        for _ in range(80):
            if s['action1'] == 3 and s['connected1']:
                break
            s = r.step()
        require(s['connected1'] == 1 and s['guard2'] == 1 and s['combo_link1'] == 0,
                'late heavy is genuinely blocked after hit stun ends', [r.tag, s])
        require(read(r.e, 'trainingResult') == 3,
                'a late blocked follow-up cannot pass the hit-confirm drill', r.tag)
        await_status(r, 'C1 RETRY')
        if fighter == 0 and not independent:
            r.e.frame.save(OUT / 'hit-confirm-late-block.png')
        inputs.press(r.e, 'select')
        r.e.run(30)
        require(read(r.e, 'trainingDummy') == 6 and read(r.e, 'trainingResult') == 0,
                'live reset retains recovery guard while clearing the drill', r.tag)
        return {'fighter': fighter, 'independent': independent, 'late_follow_up': 'blocked', 'passed': True}
    finally:
        r.close()


def selector(independent):
    original = inputs.Emulator
    try:
        inputs.Emulator = lambda **kwargs: native.Rig(independent)
        e = inputs.boot(2)
    finally:
        inputs.Emulator = original
    try:
        inputs.press(e, 'start')
        for direction, order in (('down', (1, 2, 3, 6, 4, 0)), ('up', (4, 6, 3, 2, 1, 0))):
            for index, expected in enumerate(order):
                inputs.press(e, direction, index % 2)
                require(read(e, 'trainingDummy') == expected,
                        'both pads traverse the exact automated-dummy cycle', [independent, direction, expected])
        inputs.press(e, 'up')
        require(read(e, 'trainingDummy') == 4, 'Stand retains its one-press Up-to-CPU shortcut', independent)
        inputs.press(e, 'x')
        inputs.press(e, 'up')
        require(read(e, 'trainingDummy') == 4, 'manual Up still selects CPU directly', independent)
        inputs.press(e, 'x', 1)
        inputs.press(e, 'down', 1)
        require(read(e, 'trainingDummy') == 0, 'manual Down still selects Stand directly', independent)
    finally:
        e.close()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    before = source_hashes()
    manifest = json.loads((ROOT / 'dist/manifest.json').read_bytes())
    report = {'status': 'failed', 'version': manifest['version'], 'rom_sha256': manifest['sha256'],
              'source_sha256': before, 'checks': CHECKS, 'native_health': native.HEALTH, 'host_contract': host_contract(),
              'controller_only': True, 'memory_writes': False, 'save_states': False, 'cases': []}
    try:
        require(hashlib.sha256((ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()).hexdigest() == manifest['sha256'],
                'confirm proof uses the exact current cartridge')
        require(hashlib.sha256((ROOT / '.tools/core/snes9x_libretro.dll').read_bytes()).hexdigest().lower() == native.EXPECTED_NATIVE_CORE['dll_sha256'].lower(),
                'confirm proof uses the actual pinned native core')
        report['independent_core'] = native.compatibility.verify_manifest_and_pinned_core()
        selector(False)
        selector(True)
        for fighter in range(12):
            report['cases'].extend((combo(fighter, 'y', 'x'), combo(fighter, 'b', 'a'), delayed(fighter)))
            print(json.dumps({'part': 'confirm', 'fighter': fighter, 'status': 'passed'}), flush=True)
        report['cases'].extend((combo(0, 'y', 'x', True), combo(0, 'b', 'a', True), delayed(0, True)))
        require(not native.HEALTH['failures'], 'recovery guard and confirms add no native timing failures', native.HEALTH)
        require(source_hashes() == before, 'confirm production and proof inputs remain fixed')
        report['captures'] = media_inventory(ROOT, 'confirm')
        report['status'] = 'passed'
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        report['check_count'] = len(CHECKS)
        report['native_checks'] = native.CHECKS
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
        (ROOT / 'docs/play-flow-v026-confirm-report.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
        print(json.dumps({k: report[k] for k in ('status', 'check_count', 'elapsed_seconds')}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
