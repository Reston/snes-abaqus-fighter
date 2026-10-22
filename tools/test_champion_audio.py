"""Focused, silent Champion score proof; no canonical release reports written.

Run at BELOW_NORMAL on the last two logical CPUs. All cartridge interaction
uses real controllers. The cue-under-victory fixture changes one SPC module
selection literal in an isolated build, never emulated memory or save states.
"""
from __future__ import annotations

import io
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emulator import Emulator, ROOT
import test_audio as audio
from test_champion import host_contract
from victory_music import soundbank_budget

BASE = '8f51915e060dc4a9d47139767f607ef2f26fe4b8'
REPORT = ROOT/'docs/champion-audio-report.json'
CAPTURES = ROOT/'build/champion-audio'


def command(args, cwd=ROOT) -> bytes:
    result = subprocess.run([str(a) for a in args], cwd=cwd, capture_output=True,
                            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
    if result.returncode:
        raise RuntimeError(result.stdout.decode(errors='replace')+result.stderr.decode(errors='replace'))
    return result.stdout


def bank_pointer(raw: bytes, table: int, index: int) -> int:
    address, bank = struct.unpack_from('<HB', raw, table+3*index)
    return bank*32768+address-0x8000


def bank_module(raw: bytes, index: int) -> bytes:
    offset = bank_pointer(raw, 4, index)
    words, sources = struct.unpack_from('<HH', raw, offset)
    return raw[offset:offset+4+sources*2+words*2]


def bank_sample(raw: bytes, index: int) -> bytes:
    offset = bank_pointer(raw, 388, index)
    length = struct.unpack_from('<H', raw, offset)[0]
    return raw[offset:offset+4+length]


def it_samples(raw: bytes) -> list[bytes]:
    orders, instruments, count = struct.unpack_from('<3H', raw, 32)
    offsets = struct.unpack_from('<'+str(count)+'I', raw, 192+orders+instruments*4)
    result = []
    for offset in offsets:
        length = struct.unpack_from('<I', raw, offset+48)[0]
        start = struct.unpack_from('<I', raw, offset+72)[0]
        result.append(raw[start:start+length])
    return result


def preservation() -> dict:
    archive = command(['git', 'archive', '--format=zip', BASE, 'assets/generated'])
    with zipfile.ZipFile(io.BytesIO(archive)) as package:
        old = {name: package.read(name) for name in package.namelist() if not name.endswith('/')}
    current = {p.relative_to(ROOT).as_posix(): p.read_bytes()
               for p in (ROOT/'assets/generated').iterdir() if p.is_file() and p.name != 'soundbank.h'}
    def comparable(name, data):
        return data.replace(b'\r\n', b'\n') if Path(name).suffix in ('.asm', '.h', '.json') else data

    changed = [name for name, data in old.items()
               if name not in current or comparable(name, current[name]) != comparable(name, data)]
    added = sorted(set(current)-set(old))
    audio.check(sorted(changed) == ['assets/generated/soundbank.asm', 'assets/generated/soundbank.bnk']
                and added == ['assets/generated/music4.it'],
                'all existing fighter/stage/UI/generated art and original audio sources are byte-preserved', changed)
    audio.check(len(current) == 219, 'actual generated-file count is 219', len(current))
    proof = {}
    for name in ['effects.it']+[f'music{i}.it' for i in range(4)]+[f'sfx{i}.bin' for i in range(4)]:
        path = 'assets/generated/'+name
        audio.check(old[path] == current[path], 'exact original source bytes: '+name)
        proof[name] = audio.digest(current[path])
    before, after = old['assets/generated/soundbank.bnk'], current['assets/generated/soundbank.bnk']
    for index in range(5):
        audio.check(bank_module(before, index) == bank_module(after, index),
                    'exact native effects/music payload and ordering '+str(index))
    cue_hashes, resident_hashes = [], []
    for index, data in enumerate(it_samples(current['assets/generated/effects.it'])):
        cue_hashes.append(audio.digest(data))
        audio.check(bank_sample(before, index) == bank_sample(after, index),
                    'exact resident BRR source '+str(index))
        resident_hashes.append(audio.digest(bank_sample(after, index)))
    audio.check(it_samples(current['assets/generated/music4.it']) ==
                it_samples(current['assets/generated/music0.it']),
                'victory reuses all five exact synthesized title timbres')
    return {'base_commit': BASE, 'original_files': len(old), 'current_files': len(current),
            'unchanged_files': len(old)-len(changed), 'changed': sorted(changed), 'added': added,
            'original_sources_sha256': proof, 'cue_signed8_pcm_sha256': cue_hashes,
            'resident_source_header_and_brr_sha256': resident_hashes,
            'old_native_module_payloads_identical': list(range(5)),
            'text_comparison': 'LF-normalized; IT, BRR and other binary assets compare exact bytes'}


def cue_fixture() -> dict:
    root = ROOT/'build/champion-audio-fixture'
    root.mkdir(parents=True, exist_ok=True)
    (root/'tools').mkdir(exist_ok=True)
    (root/'dist').mkdir(exist_ok=True)
    shutil.copytree(ROOT/'src', root/'src', dirs_exist_ok=True)
    shutil.copyfile(ROOT/'tools/build.py', root/'tools/build.py')
    # Junctions contain only shared build inputs; neither asset regeneration
    # nor SDK setup is invoked, and all outputs stay under this fixture root.
    for name in ('assets', '.tools'):
        destination = root/name
        if not destination.exists():
            if sys.platform == 'win32':
                # Literal paths are arguments to PowerShell, never interpolated shell text.
                command(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                         '& { param($p, $t) New-Item -ItemType Junction -Path $p -Target $t | Out-Null }',
                         str(destination), str(ROOT/name)])
            else:
                destination.symlink_to(ROOT/name, target_is_directory=True)
    source = root/'src/game.c'
    old = 'spcStop();spcLoad(MOD_MUSIC0+index);'
    new = 'spcStop();spcLoad(MOD_MUSIC4);'
    code = source.read_text()
    audio.check(code.count(old) == 1, 'fixture has one explicit score-selection substitution')
    source.write_text(code.replace(old, new))
    log = command([sys.executable, root/'tools/build.py'], cwd=root)
    (CAPTURES/'fixture-build.txt').write_bytes(log)
    fixture_rom = root/'dist/abaqus-after-hours.sfc'
    production_factory, previous_captures = audio.Emulator, audio.CAPTURES
    audio.CAPTURES = CAPTURES/'victory-cues'
    audio.CAPTURES.mkdir(exist_ok=True)
    audio.Emulator = lambda: Emulator(rom=fixture_rom)
    try:
        cues = audio.verify_cues()
    finally:
        audio.Emulator, audio.CAPTURES = production_factory, previous_captures
    return {'scope': 'test-only ROM; all score loads select native MOD_MUSIC4; controllers drive every cue',
            'production_rom': False, 'emulated_memory_writes': 0, 'savestates': 0,
            'source_change': {'before': old, 'after': new},
            'source_sha256': audio.digest(source.read_bytes()),
            'rom_sha256': audio.digest(fixture_rom.read_bytes()), 'cues': cues}


def main() -> None:
    started = time.monotonic()
    CAPTURES.mkdir(parents=True, exist_ok=True)
    audio.CAPTURES = CAPTURES
    manifest = json.loads((ROOT/'dist/manifest.json').read_text())
    report = {'suite': 'focused-champion-audio', 'status': 'failed',
        'scope': 'focused capture-only proof; six-suite batch, release gates, package and human listening are separate',
              'rom_sha256': manifest['sha256'], 'checksum': manifest['checksum'],
              'human_listening_approved': False, 'host_contract': host_contract(),
              'controller_only': True, 'emulated_memory_writes': 0, 'savestates': 0,
              'checks': audio.checks}
    try:
        contract = report['host_contract']
        audio.check(contract.get('priority_class') == 0x4000 and
                    len(contract.get('logical_processors', [])) == 2,
                    'Windows BELOW_NORMAL with two logical CPUs', contract)
        cartridge = (ROOT/'dist/abaqus-after-hours.sfc').read_bytes()
        audio.check(audio.digest(cartridge) == manifest['sha256'] and len(cartridge) == 4194304
                    and cartridge[0x7fd5] == 0x30 and cartridge[0x7fd9] == 1,
                    'exact 4 MiB NTSC FastROM LoROM cartridge')
        report['preservation'] = preservation()
        report['native_budget'] = soundbank_budget(ROOT/'assets/generated/soundbank.bnk')
        report['harness_sha256'] = {name: audio.digest((ROOT/name).read_bytes()) for name in (
            'tools/test_champion_audio.py', 'tools/test_audio.py', 'tools/test_champion.py',
            'tools/emulator.py', 'tools/victory_music.py', 'tools/make_assets.py')}
        report['core_sha256'] = audio.digest((ROOT/'.tools/core/snes9x_libretro.dll').read_bytes())
        report['production_cues'] = audio.verify_cues()
        assets = {f'assets/generated/music{i}.it': audio.digest(
            (ROOT/f'assets/generated/music{i}.it').read_bytes()) for i in range(5)}
        report['music'] = audio.verify_music(assets)
        # A second real ladder proves the alternative Start prompt as well.
        e = audio.boot_champion()
        try:
            fps, rate = audio.timing(e)
            report['start_exit'] = audio.verify_champion_exit(e, fps, rate, 'start')
        finally:
            e.close()
        report['victory_cue_fixture'] = cue_fixture()
        report['status'] = 'passed'
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        report['elapsed_seconds'] = round(time.monotonic()-started, 3)
        REPORT.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'rom_sha256': report['rom_sha256'],
                      'report': REPORT.relative_to(ROOT).as_posix()}))


if __name__ == '__main__':
    main()
