"""Independent native preservation/budget checks for the six-feature revision."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preservation import committed_files, git, normalize

BASE = 'c7510c30e129465bcca0b32e2142daec60546d0f'
BASE_ROM = '09eaa47ddc12d419e259f1330eb225f1e56f75d42efdd2faf5c27063f8f2357c'
STATE = {'v29DefenseState': 16, 'v29BonusState': 64, 'v29AutoState': 8,
         'v29RandomState': 8, 'v29AudioState': 32, 'v29ArenaState': 48}
MARKERS = {'SECTIONEND_globram.data', 'RAM_USAGE_SLOT_3_BANK_127_END'}
# Parent-owned policy, never read from a captured report. Final feature review
# must narrow/update these inventories before the combined source freeze.
ALLOWED_CHANGED = {'assets/generated/assets.h', 'assets/generated/data.asm',
                   'assets/generated/effects.it', 'assets/generated/soundbank.asm',
                   'assets/generated/soundbank.bnk', 'assets/generated/stage-depth.json'}
ALLOWED_CHANGED.update(f'assets/generated/music{i}.it' for i in range(5))
ALLOWED_CHANGED.update(f'assets/generated/stage{i}{suffix}' for i in range(3)
                       for suffix in ('.png', '_tiles.bin', '_map.bin'))
ALLOWED_ADDED = {'assets/generated/arena-life29.json'} | {
    f'assets/generated/arena_life29_stage{i}.bin' for i in range(3)}
ALLOWED_ADDED |= {'assets/generated/bonus29-assets.json'} | {
    'assets/generated/bonus29_'+name+suffix for name in ('printer','inbox')
    for suffix in ('.bin','_pal.bin','.png')}


def require(ok, message, details=None):
    if not ok:
        raise ValueError((message, details))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def symbols(raw):
    return {name: int(address, 16) for address, name in
            re.findall(r'^([0-9a-fA-F]{8}) (\S+)$', raw.decode(), re.M)}


def generated_report(root, prior, allowed_changed=None, allowed_added=None):
    root = Path(root)
    allowed_changed = ALLOWED_CHANGED if allowed_changed is None else set(allowed_changed)
    allowed_added = ALLOWED_ADDED if allowed_added is None else set(allowed_added)
    expected = {name for name in prior if name.startswith('assets/generated/')}
    current = {p.relative_to(root).as_posix() for p in (root/'assets/generated').iterdir()
               if p.is_file() and p.name != 'soundbank.h'}
    require(not expected-current, 'Approved generated file removed', sorted(expected-current))
    require(current-expected == allowed_added, 'New generated inventory differs from reviewed policy',
            sorted(current-expected))
    changed, preserved = [], []
    for name in sorted(expected):
        raw = (root/name).read_bytes()
        row = {'path': name, 'sha256': sha(raw), 'baseline_sha256': sha(prior[name])}
        (preserved if normalize(name, raw) == normalize(name, prior[name]) else changed).append(row)
    require({r['path'] for r in changed} <= allowed_changed,
            'Generated change escapes six-feature policy',
            sorted({r['path'] for r in changed}-allowed_changed))
    return {'baseline_count': len(expected), 'current_count': len(current),
            'preserved_count': len(preserved), 'changed': changed,
            'added': [{'path': name, 'sha256': sha((root/name).read_bytes())}
                      for name in sorted(allowed_added)], 'preserved': preserved}


def ram_report(old, new):
    ram = lambda value: value < 0x2000 or 0x7e0000 <= value < 0x800000
    prior = {name: value for name, value in old.items() if ram(value)}
    moved = {name: [value, new.get(name)] for name, value in prior.items()
             if new.get(name) != value}
    added = {name: value for name, value in new.items() if ram(value) and name not in old}
    require(set(moved) == MARKERS, 'Prior variable/data address changed', moved)
    require(all(after == before+sum(STATE.values()) for before, after in moved.values()),
            'Allocation markers must grow only by the reserved state', moved)
    require(set(added) == set(STATE), 'Unexpected new RAM label', added)
    cursor = old['SECTIONEND_globram.data']
    for name, size in STATE.items():
        require(added[name] == cursor, 'Feature reservation moved or overlapped', [name, cursor, added[name]])
        cursor += size
    return {'prior_labels': len(prior), 'existing_variable_addresses_exact': len(prior)-len(MARKERS),
            'allocation_markers': moved, 'reserved_bytes': sum(STATE.values()), 'reservations': added}


def floor_pixels(gfx, tilemap, palette, seam, width=288):
    """Decode the hardware tile format independently, without an art encoder."""
    require(len(tilemap) == 4096 and len(palette) == 192 and len(gfx) % 32 == 0,
            'Native whole-stage payload shape differs')
    result = bytearray()
    for y in range(seam, 224):
        for x in range(width):
            col = x//8
            at = ((col//32)*1024 + (y//8)*32 + col%32)*2
            entry = int.from_bytes(tilemap[at:at+2], 'little')
            tile, bank = entry & 1023, (entry >> 10) & 7
            require(bank in range(2, 8), 'Floor escaped six authored stage palettes', [x, y, bank])
            xx, yy = x%8, y%8
            if entry & 0x4000:
                xx = 7-xx
            if entry & 0x8000:
                yy = 7-yy
            start = tile*32
            require(start+32 <= len(gfx), 'Floor references missing tile', tile)
            index = 0
            for bit in range(4):
                value = gfx[start+(bit//2)*16+yy*2+bit%2]
                index |= ((value >> (7-xx)) & 1) << bit
            color = ((bank-2)*16+index)*2
            result.extend(palette[color:color+2])
    return bytes(result)


def validate(root):
    root = Path(root).resolve()
    git(root, 'merge-base', '--is-ancestor', BASE, 'HEAD')
    manifest = json.loads((root/'dist/manifest.json').read_bytes())
    baseline = json.loads(git(root, 'show', BASE+':dist/manifest.json'))
    require(baseline['version'] == '0.28.0' and baseline['sha256'] == BASE_ROM,
            'Approved baseline identity changed')
    rom = (root/'dist/abaqus-after-hours.sfc').read_bytes()
    require(manifest['version'] == '0.29.0' and manifest['sha256'] == sha(rom),
            'Candidate ROM/version identity differs')
    require(len(rom) == 4*1024*1024 and rom[0x7fd5] == 0x30,
            'Native 4 MiB FastROM LoROM changed')
    require(int.from_bytes(rom[0x7fde:0x7fe0], 'little') == sum(rom) & 65535,
            'Native checksum differs')
    before = committed_files(root, BASE)
    for name in ('src/hardware.asm', 'src/trace.asm'):
        require(normalize(name, (root/name).read_bytes()) == normalize(name, before[name]),
                'Protected hardware/trace assembly changed', name)
    generated = generated_report(root, before)
    require({row['path'] for row in generated['changed']} == ALLOWED_CHANGED,
            'Complete six-feature generated changes differ from reviewed inventory')
    # Git's committed blob IDs independently bind every retained original art
    # and reference file; reports cannot authorize edited masters.
    protected = git(root, 'ls-tree', '-r', BASE, '--', 'assets/art', 'assets/references').decode().splitlines()
    for row in protected:
        metadata, name = row.split('\t', 1)
        path = root/name
        require(path.is_file(), 'Original art/reference removed', name)
        raw = path.read_bytes()
        if path.suffix.lower() in {'.asm', '.h', '.json', '.md', '.txt', '.py', '.c', '.ps1', '.csv', '.svg'}:
            raw = raw.replace(b'\r\n', b'\n')
        actual = hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        require(actual == metadata.split()[2], 'Original art/reference modified', name)
    old = symbols(git(root, 'show', BASE+':dist/abaqus-after-hours.sym'))
    new = symbols((root/'dist/abaqus-after-hours.sym').read_bytes())
    memory = ram_report(old, new)
    sections = []
    for name, start in new.items():
        if not name.startswith('SECTIONSTART_') or start < 0x800000:
            continue
        end = new.get(name.replace('SECTIONSTART_', 'SECTIONEND_'))
        if end is None:
            continue
        size = end-start
        require(0 <= size <= 32768 and (not size or start >> 16 == (end-1) >> 16),
                'Native section crosses LoROM bank', [name, start, end])
        sections.append({'name': name, 'bytes': size})
    depth = json.loads(before['assets/generated/stage-depth.json'])
    floors = []
    for row in depth['stages']:
        stage, seam = row['id'], row['floor_seam_y']
        paths = [f'assets/generated/stage{stage}{suffix}' for suffix in ('_tiles.bin', '_map.bin', '_pal.bin')]
        prior = floor_pixels(*(before[name] for name in paths), seam)
        current = floor_pixels(*((root/name).read_bytes() for name in paths), seam)
        require(current == prior, 'Approved detailed floor pixels changed', stage)
        require((root/paths[0]).stat().st_size <= 28*1024, 'BG1 tile pool exceeds 28 KiB', stage)
        floors.append({'stage': stage, 'native_rows': [seam, 224], 'width': 288,
                       'bytes': len(current), 'baseline_sha256': sha(prior), 'sha256': sha(current)})
    from victory_music import soundbank_budget
    budget = soundbank_budget(root/'assets/generated/soundbank.bnk')
    from arena_life29_checks import metadata as arena_metadata
    arenas = arena_metadata(root)
    bonus = json.loads((root/'assets/generated/bonus29-assets.json').read_bytes())
    require(bonus.get('scope') == 'bonus-v029' and bonus.get('actor_canvas') == [96,80] and
            bonus.get('vram_word') == [0x6a00,0x73ff] and bonus.get('cgram_color') == [144,159] and
            bonus.get('live_target_dma') == 0, 'Bonus target native allocation differs')
    source = root/'assets/art/bonus-v029/office-targets-v1.png'
    provenance = json.loads(source.with_suffix('.json').read_bytes())
    require(provenance.get('mode') == 'built-in imagegen' and
            bonus.get('source_sha256') == provenance.get('output_sha256') == sha(source.read_bytes()),
            'Bonus source/provenance differs')
    require([row.get('name') for row in bonus.get('targets',[])] == ['bonus29_printer','bonus29_inbox'],
            'Bonus target inventory differs')
    for row in bonus['targets']:
        pose = (root/'assets/generated'/(row['name']+'.bin')).read_bytes()
        palette = (root/'assets/generated'/(row['name']+'_pal.bin')).read_bytes()
        require(row.get('bytes') == len(pose) == 3840 and row.get('palette_bytes') == len(palette) == 32 and
                row.get('pose_sha256') == sha(pose) and row.get('palette_sha256') == sha(palette),
                'Bonus actor page/palette differs',row['name'])
    return {'status': 'passed', 'version': manifest['version'], 'rom_sha256': manifest['sha256'],
            'baseline_commit': BASE, 'baseline_rom_sha256': BASE_ROM,
            'generated': generated, 'original_art_reference_files_exact': len(protected),
            'memory': memory, 'hardware_trace_exact': True, 'floors': floors,
            'native_sections': sections, 'soundbank': budget,
            'arena_animation_contract': arenas, 'bonus_target_contract': bonus}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = validate(Path(__file__).resolve().parents[1])
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({key: result[key] for key in ('status', 'version', 'rom_sha256')}))
