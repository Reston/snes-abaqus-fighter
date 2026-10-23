"""Independent shared preservation policy for the approved nine-feature ROM (stage 08 deferred)."""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import subprocess

BASE = '38519cd73e0d41883b502b7496b78690845e49a2'
GENERATED_CHANGES = {
    'assets/generated/effects.bin', 'assets/generated/effects.it',
    'assets/generated/soundbank.asm', 'assets/generated/soundbank.bnk',
}
RAM_GROWTH = {'SECTIONSTART_.bss': 32, 'SECTIONEND_.bss': 32,
              'tccs_libc_c.asm_msys': 32, 'SECTIONEND_globram.data': 331,
              'RAM_USAGE_SLOT_3_BANK_127_END': 331}
TEXT = {'.json', '.asm', '.h', '.c', '.md', '.txt', '.ps1', '.py'}


def require(ok, message, details=None):
    if not ok:
        raise ValueError((message, details))


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root)


def canonical(path, raw):
    return raw.replace(b'\r\n', b'\n') if Path(path).suffix.lower() in TEXT else raw


def preserved_assets(root):
    root = Path(root)
    allowed_changes=set(GENERATED_CHANGES)
    if (root/'assets/art/walking-v2.json').is_file():
        allowed_changes.add('assets/generated/character-manifest.json')
        for fighter in range(12):
            allowed_changes.update({f'assets/generated/fighter{fighter:02d}.png',
                                    f'assets/generated/fighter{fighter:02d}c.bin',
                                    f'assets/generated/fighter{fighter:02d}d.bin'})
    rows = git(root, 'ls-tree', '-r', BASE, '--', 'assets/generated',
               'assets/art', 'assets/references').decode('utf-8').splitlines()
    changed, missing, protected_changes, generated, protected = [], [], [], [], []
    for row in rows:
        metadata, name = row.split('\t', 1)
        expected = metadata.split()[2]
        path = root / name
        if not path.is_file():
            missing.append(name)
            continue
        raw = canonical(name, path.read_bytes())
        actual = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        record = {'path': name, 'sha256': hashlib.sha256(raw).hexdigest(),
                  'baseline_blob': expected, 'preserved': actual == expected}
        if name.startswith('assets/generated/'):
            generated.append(record)
            if actual != expected:
                changed.append(name)
        else:
            protected.append(record)
            if actual != expected:
                protected_changes.append(name)
    require(not missing, 'Baseline assets are missing', missing)
    require(not protected_changes, 'Approved source art or reference changed', protected_changes)
    require(len(generated) == 219, 'Generated baseline inventory must remain 219', len(generated))
    require(set(changed) == allowed_changes, 'Generated changes differ from bounded walking/audio policy', changed)
    actual_names = {p.relative_to(root).as_posix() for p in (root / 'assets/generated').iterdir()
                    if p.is_file() and p.name != 'soundbank.h'}
    require(actual_names == {row['path'] for row in generated},
            'Generated inventory has missing or extra files', sorted(actual_names ^ {r['path'] for r in generated}))
    return {'baseline_commit': BASE, 'generated_count': len(generated),
            'preserved_generated': len(generated) - len(changed),
            'changed_generated': sorted(changed), 'generated': generated,
            'protected_source_count': len(protected), 'protected_source': protected}


def symbols(raw):
    return {name: int(address, 16) for address, name in
            re.findall(r'^([0-9a-fA-F]{6,8})\s+(\S+)\s*$', raw, re.M)}


def preserved_native(root):
    root = Path(root)
    old = symbols(git(root, 'show', BASE + ':dist/abaqus-after-hours.sym').decode('utf-8'))
    current = symbols((root / 'dist/abaqus-after-hours.sym').read_text(encoding='utf-8'))
    prior_ram = {n: a for n, a in old.items() if a < 0x2000 or 0x7e0000 <= a < 0x800000}
    moved = {}
    for name, address in prior_ram.items():
        expected = address + RAM_GROWTH.get(name, 0)
        require(current.get(name) == expected, 'Unexpected prior RAM symbol relocation',
                {'name': name, 'baseline': address, 'expected': expected, 'actual': current.get(name)})
        if current[name] != address:
            moved[name] = {'baseline': address, 'current': current[name]}
    new_ram = {n: a for n, a in current.items() if n not in old and
               (a < 0x2000 or 0x7e0000 <= a < 0x800000)}
    require(all(0x7e29af <= a < 0x7e29cf or 0x7f0448 <= a < 0x7f0593
                for a in new_ram.values()), 'New RAM label escapes bounded appended allocations', new_ram)
    for name in ('src/hardware.asm', 'src/trace.asm'):
        require(canonical(name, (root / name).read_bytes()) ==
                canonical(name, git(root, 'show', BASE + ':' + name)),
                'Native ABI/transfer assembly changed unexpectedly', name)
    crossings = []
    total = 0
    for name, start in current.items():
        if not name.startswith('SECTIONSTART_') or start < 0x8000:
            continue
        if 0x7e0000 <= start < 0x800000:
            continue
        end = current.get('SECTIONEND_' + name[len('SECTIONSTART_'):])
        if end is None or end <= start:
            continue
        total += end - start
        if (start & 0x7fff) + end - start > 32768:
            crossings.append({'section': name, 'start': start, 'end': end})
    require(not crossings, 'Native section crosses 32 KiB LoROM bank', crossings)
    return {'baseline_commit': BASE, 'prior_ram_labels': len(prior_ram),
            'unchanged_prior_ram_labels': len(prior_ram) - len(moved),
            'documented_relocations': moved, 'appended_ram_symbols': new_ram,
            'appended_bss_bytes': 32, 'appended_initialized_bytes': 331,
            'linked_section_bytes': total, 'bank_crossings': crossings,
            'hardware_and_trace_assembly_preserved': True}


def combined_contract(root):
    return {'assets': preserved_assets(root), 'native': preserved_native(root)}


if __name__ == '__main__':
    import json
    root = Path(__file__).resolve().parents[1]
    value = combined_contract(root)
    version=json.loads((root/'dist/manifest.json').read_bytes())['version']
    out = root / f'docs/expansion-preservation-v{version}.json'
    value['rom_sha256'] = hashlib.sha256((root / 'dist/abaqus-after-hours.sfc').read_bytes()).hexdigest()
    value['status'] = 'passed'
    out.write_bytes((json.dumps(value, indent=2) + '\n').encode('utf-8'))
    print(out)
