"""Background comfort option: real PPU stability and unchanged combat state."""
import ctypes as C
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emulator import ROOT
import test_inputs as inputs
import test_music_26 as native
import test_presentation as presentation
from test_play_flow_26 import source_hashes
from test_champion import host_contract

CHECKS = []
OUT = ROOT / 'docs/screenshots/play-flow-v026'
STREAMS = ROOT / 'build/v026-motion-streams'


def require(ok, label, details=None):
    CHECKS.append({'check': label, 'passed': bool(ok), 'details': details})
    if not ok:
        raise AssertionError((label, details))


def read(e):
    return (native.read(e, 'stageDepthTable', 10) >> 72) & 255


def record(e):
    return b''.join(C.string_at(e.ram + native.SYMS[n], size) for n, size in
                    (('fighters', 128), ('waves', 32), ('randomseed', 2), ('rearKickRecoil', 1),
                     ('pad0', 2), ('pad1', 2), ('edge0', 2), ('edge1', 2)))


def case(stage, independent, still, plan=None):
    e = native.Rig(independent)
    try:
        e.run(120)
        inputs.menu_arena(e, 1)
        for _ in range(stage):
            inputs.menu_press(e, ['down'], 1)
        inputs.menu_press(e, ['a'], 1)
        e.run(160)
        require(read(e) == 0, 'background motion defaults on at a cold boot', [stage, independent])
        reference = e.frame.crop((0, 48, 256, 64)).tobytes()
        inputs.press(e, 'start')
        inputs.press(e, 'select')
        e.run(10)
        frozen = native.physics(e)
        # Opposite shoulders do not change either comfort preference.
        e.run(3, p1=['l'], p2=['r'])
        e.run(3)
        require(read(e) == 0 and native.read(e, 'musicOn') == 1,
                'opposing shoulders across pads cancel music and background toggles')
        e.run(48, p2=['r'] if still else [])
        e.run(10)
        require(read(e) == int(still) and native.physics(e) == frozen,
                'a held R toggles once while leaving both fighters frozen', [stage, independent, still])
        label = 'R BACKGROUND: STILL' if still else 'R BACKGROUND: MOVING'
        start = len(presentation.checks)
        presentation.verify_opaque_text_rows(e, [(27, (32 - len(label)) // 2, label)], 'background comfort')
        require(all(c['passed'] for c in presentation.checks[start:]), 'native guide accurately displays the background preference')
        if stage == 0 and still and not independent:
            e.frame.save(OUT / 'background-still-guide.png')
        inputs.press(e, 'start')
        e.run(10)
        generated = plan is None
        if generated:
            plan = []
            for _ in range(220):
                s = inputs.trace(e)
                if abs(inputs.signed16(s['x1']) - inputs.signed16(s['x2'])) <= 25 * 16:
                    break
                e.run(1, p1=['right'])
                plan.append(['right'])
            # Replay starts from the same initial fight state below. Build the
            # movement schedule using only physical controls, then cold-boot
            # again rather than resetting or writing any emulated memory.
            e.close()
            return case(stage, independent, still, plan + [[]] + [['x']] + [[] for _ in range(90)])
        records, observable, strips, frames = [], [], set(), []
        saw_shake, saw_contact = False, False
        for index, keys in enumerate(plan):
            s = e.run(1, p1=keys)
            records.append(record(e))
            observable.append({key: s[key] for key in ('x1', 'x2', 'y1', 'y2', 'hp1', 'hp2', 'action1', 'action2',
                'hurt1', 'hurt2', 'hitstop', 'energy1', 'energy2', 'connected1', 'connected2', 'down_state1', 'down_state2')})
            strip = e.frame.crop((0, 48, 256, 64)).tobytes()
            strips.add(hashlib.sha256(strip).hexdigest())
            if still:
                require(strip == reference, 'actual scenery pixels remain fixed through walking, contact and shake', [stage, independent, index])
            saw_shake |= native.read(e, 'shake') > 0
            saw_contact |= s['hp2'] < 128 and s['connected1'] == 2
            if stage == 0 and not independent and index % 5 == 0:
                frames.append(e.frame)
        require(saw_shake and saw_contact, 'comfort proof includes real damaging contact and active shake state')
        require(len(strips) == 1 if still else len(strips) > 1,
                'native PPU distinguishes still scenery from the normal bounded camera and shake', [stage, independent, still, len(strips)])
        if stage == 0 and not independent:
            path = OUT / ('background-still.gif' if still else 'background-moving.gif')
            frames[0].save(path, save_all=True, append_images=frames[1:], duration=83, loop=0, optimize=False)
        # The setting survives scenes and can be restored from the guide.
        inputs.press(e, 'start')
        inputs.press(e, 'b')
        e.run(35)
        require(inputs.native_screen(e) == 1 and read(e) == int(still), 'background preference persists through character select')
        data = b''.join(records)
        path = STREAMS / f'stage{stage}-{"accuracy" if independent else "snes9x"}-{"still" if still else "moving"}.bin.gz'
        path.write_bytes(gzip.compress(data, mtime=0))
        return records, observable, plan, {'stage': stage, 'independent': independent, 'still': still,
            'callbacks': len(records), 'real_contact_and_shake': True, 'distinct_background_strips': len(strips),
            'unmasked_combat_sha256': hashlib.sha256(data).hexdigest(), 'retained_stream': path.relative_to(ROOT).as_posix(),
            'retained_stream_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'passed': True}
    finally:
        e.close()


def main():
    STREAMS.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    sources = source_hashes()
    manifest = json.loads((ROOT / 'dist/manifest.json').read_bytes())
    report = {'status': 'failed', 'version': manifest['version'], 'rom_sha256': manifest['sha256'],
              'source_sha256': sources, 'checks': CHECKS, 'native_health': native.HEALTH,
              'host_contract': host_contract(), 'controller_only': True, 'memory_writes': False,
              'save_states': False, 'cases': [], 'comparisons': [],
              'accuracy_byte_equivalence_claimed': False}
    try:
        require(hashlib.sha256((ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()).hexdigest() == manifest['sha256'], 'motion proof loads the exact current cartridge')
        require(hashlib.sha256((ROOT / '.tools/core/snes9x_libretro.dll').read_bytes()).hexdigest().lower() == native.EXPECTED_NATIVE_CORE['dll_sha256'].lower(), 'motion proof hashes the pinned native core')
        report['independent_core'] = native.compatibility.verify_manifest_and_pinned_core()
        for independent in (False, True):
            for stage in range(3):
                original, behavior, plan, first = case(stage, independent, False)
                candidate, actual, replay, second = case(stage, independent, True, plan)
                require(replay == plan and actual == behavior, 'identical physical input streams preserve every observed combat result', [stage, independent])
                if not independent:
                    require(candidate == original, 'Snes9x preserves all unmasked Fighter Wave RNG recoil and controller bytes', stage)
                report['cases'].extend((first, second))
                report['comparisons'].append({'stage': stage, 'independent': independent, 'observable_equality': True,
                    'exact_unmasked_equality': True if not independent else None, 'callbacks': len(plan)})
        require(not native.HEALTH['failures'], 'background comfort adds no native timing OBJ PCM or FIFO failures')
        require(source_hashes() == sources, 'motion runtime and producer inputs stay fixed')
        report['status'] = 'passed'
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        report['check_count'] = len(CHECKS)
        report['native_check_count'] = len(native.CHECKS)
        report['native_failed_checks'] = [r for r in native.CHECKS if not r['passed']]
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
        (ROOT / 'docs/play-flow-v026-motion-report.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
        print(json.dumps({k: report[k] for k in ('status', 'check_count', 'elapsed_seconds')}), flush=True)


if __name__ == '__main__':
    main()
