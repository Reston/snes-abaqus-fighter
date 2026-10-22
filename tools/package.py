"""Package the tested ROM with the official Windows emulator for offline play.

The package gate is deliberately stricter than the ordinary build.  It checks
the exact ROM evidence, verifies the locally cached emulator against both its
archive and expanded executable pins, and refuses to start expensive release
validation while any mapped input is missing.
"""
from __future__ import annotations

import hashlib
import json
import posixpath
import re
import sys
import zipfile
from pathlib import Path
from typing import Mapping

# The pinned embeddable Python does not add the script directory to sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_evidence import (EXTRA_REPORTS, training_report_path,
                               validate_release_evidence)

ROOT = Path(__file__).resolve().parents[1]

GUI_EMULATOR_ARCHIVE_NAME = 'snes9x.zip'
GUI_EMULATOR_ARCHIVE_SHA256 = (
    'E2BD103819051EAE57D163CDBBF6B3B92DB73FDD4A6A0EE6A939E507EAA95DB8'
)
GUI_EMULATOR_MEMBER = 'snes9x-x64.exe'
GUI_EMULATOR_MEMBER_SHA256 = (
    'C843D906C1FA1FEFA672E99CFD218041D229EF7598BCE720465FE7A0905F3A4B'
)
GUI_EMULATOR_PACKAGE_PATH = 'emulator/snes9x-x64.exe'
PLAY_COMMAND = (
    b'@echo off\r\n'
    b'cd /d "%~dp0emulator"\r\n'
    b'start "Abaqus After Hours" "snes9x-x64.exe" '
    b'"..\\abaqus-after-hours.sfc"\r\n'
)

_MARKDOWN_LINK = re.compile(r'(!?\[[^\]]+\])\(([^)\n]+)\)')
_EXTERNAL_LINK = re.compile(r'^(?:[A-Za-z][A-Za-z0-9+.-]*:|//)')
OFFLINE_LINK_ALIASES = {
    ('OBJ-BUDGET.md', 'stage-test-report.json'): 'qa/stages.json',
    ('CHAMPION-ENDING.md', '../assets/art/menu/champion-ending-v1.json'): 'qa/champion-art.json',
    ('CHAMPION-ENDING.md', '../assets/art/menu/source-champion-v1/generation-v1.json'): 'qa/champion-generation.json',
}


class PackageError(RuntimeError):
    """A package input or release gate is invalid."""


def require(condition: bool, message: str, details=None) -> None:
    """Raise a useful error instead of relying on an optimized-away check."""
    if not condition:
        if details is None:
            raise PackageError(message)
        raise PackageError(f'{message}: {details}')


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_json(path: Path, label: str):
    require(path.is_file(), f'Missing JSON input for {label}', path)
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PackageError(f'Invalid JSON input for {label}: {path}') from error


def canonical_manifest_bytes(manifest: Mapping) -> bytes:
    return (json.dumps(manifest, indent=2) + '\n').encode('utf-8')


def package_manifest(manifest: Mapping, pin_record: Mapping) -> dict:
    """Add constant offline-emulator identity only to the ZIP manifest."""
    packaged = dict(manifest)
    packaged['offline_emulator'] = dict(pin_record)
    return packaged


def verify_gui_emulator(root: Path = ROOT) -> dict:
    """Verify the archive pin and the exact expanded GUI executable pin."""
    root = Path(root)
    archive = root / '.tools' / GUI_EMULATOR_ARCHIVE_NAME
    executable = root / '.tools' / 'snes9x' / GUI_EMULATOR_MEMBER
    require(archive.is_file(), 'Pinned GUI emulator archive is missing', archive)
    require(executable.is_file(), 'Expanded GUI emulator is missing', executable)

    archive_digest = sha256_file(archive)
    require(
        archive_digest.lower() == GUI_EMULATOR_ARCHIVE_SHA256.lower(),
        'Pinned GUI emulator archive SHA256 mismatch',
        {'expected': GUI_EMULATOR_ARCHIVE_SHA256, 'actual': archive_digest},
    )
    try:
        with zipfile.ZipFile(archive) as source:
            require(source.testzip() is None,
                    'Pinned GUI emulator archive CRC check failed')
            require(GUI_EMULATOR_MEMBER in source.namelist(),
                    'Pinned GUI emulator archive lacks its executable',
                    GUI_EMULATOR_MEMBER)
            archive_member = source.read(GUI_EMULATOR_MEMBER)
    except PackageError:
        raise
    except (OSError, KeyError, zipfile.BadZipFile) as error:
        raise PackageError(
            f'Pinned GUI emulator archive cannot be read: {archive}'
        ) from error

    member_digest = sha256_bytes(archive_member)
    require(
        member_digest.lower() == GUI_EMULATOR_MEMBER_SHA256.lower(),
        'Pinned GUI emulator archive member SHA256 mismatch',
        {'expected': GUI_EMULATOR_MEMBER_SHA256, 'actual': member_digest},
    )
    expanded = executable.read_bytes()
    expanded_digest = sha256_bytes(expanded)
    require(
        expanded_digest.lower() == GUI_EMULATOR_MEMBER_SHA256.lower(),
        'Expanded GUI emulator SHA256 mismatch',
        {'expected': GUI_EMULATOR_MEMBER_SHA256, 'actual': expanded_digest},
    )
    require(expanded == archive_member,
            'Expanded GUI emulator differs from its pinned archive member')

    return {
        'archive': GUI_EMULATOR_ARCHIVE_NAME,
        'archive_sha256': GUI_EMULATOR_ARCHIVE_SHA256,
        'member': GUI_EMULATOR_MEMBER,
        'member_sha256': GUI_EMULATOR_MEMBER_SHA256,
        'package_path': GUI_EMULATOR_PACKAGE_PATH,
        'launcher': 'Play.cmd',
        'config': 'emulator/snes9x.conf',
    }


def build_package_files(root: Path = ROOT, manifest: Mapping | None = None) -> dict[str, Path]:
    """Return the source-to-archive map for the current candidate."""
    root = Path(root)
    if manifest is None:
        manifest = read_json(root / 'dist/manifest.json', 'manifest')
    require(isinstance(manifest, Mapping), 'Manifest must be a JSON object')
    require('version' in manifest, 'Manifest is missing its version')
    training_source = training_report_path(root)
    version = str(manifest['version'])
    return {
        'abaqus-after-hours.sfc': root / 'dist/abaqus-after-hours.sfc',
        GUI_EMULATOR_PACKAGE_PATH: root / '.tools/snes9x/snes9x-x64.exe',
        'emulator/LICENSE': root / '.tools/snes9x/LICENSE',
        'emulator/snes9x.conf': root / 'tools/snes9x.conf',
        'README.md': root / 'docs/PLAYER-GUIDE.md',
        'CREDITS.md': root / 'docs/CREDITS.md',
        'manifest.json': root / 'dist/manifest.json',
        'ART-DIRECTION.md': root / 'docs/ART-DIRECTION.md',
        'CHARACTERS.md': root / 'docs/CHARACTERS.md',
        'qa/gameplay.json': root / 'docs/test-report.json',
        'qa/characters.json': root / 'docs/character-test-report.json',
        'qa/presentation.json': root / 'docs/presentation-test-report.json',
        'qa/inputs.json': root / 'docs/input-test-report.json',
        'qa/stages.json': root / 'docs/stage-test-report.json',
        'qa/training.json': training_source,
        'qa/stage-dynamics.json': root / 'assets/generated/stage-dynamics.json',
        'qa/compatibility.json': root / 'docs/compatibility-test-report.json',
        # The compatibility guide links these report names in the repository.
        # Keep the same links usable in the offline archive.
        'compatibility-test-report.json': root / 'docs/compatibility-test-report.json',
        'compatibility-combat-test-report.json':
            root / 'docs/compatibility-combat-test-report.json',
        'qa/matchups.json': root / EXTRA_REPORTS['matchups'],
        'qa/independent-combat.json': root / EXTRA_REPORTS['independent_combat'],
        'qa/endurance.json': root / EXTRA_REPORTS['endurance'],
        'qa/fresh-build.json': root / EXTRA_REPORTS['fresh_build'],
        'COMPATIBILITY.md': root / 'docs/COMPATIBILITY.md',
        'ANIMATION-CONTRACT.md': root / 'docs/ANIMATION-CONTRACT.md',
        'COMBAT-ANIMATION-CONTRACT.md':
            root / 'docs/COMBAT-ANIMATION-CONTRACT.md',
        'ANIMATION-PIPELINE.md': root / 'docs/ANIMATION-PIPELINE.md',
        'PUBLIC-RELEASE.md': root / 'docs/PUBLIC-RELEASE.md',
        'BALANCE-AUDIT-v0.6.md': root / 'docs/BALANCE-AUDIT-v0.6.md',
        'PROPORTIONS.md': root / 'docs/PROPORTIONS.md',
        'MENU-DESIGN.md': root / 'docs/MENU-DESIGN.md',
        'OBJ-BUDGET.md': root / 'docs/OBJ-BUDGET.md',
        'STAGE-CARTOON-v2.md': root / 'docs/STAGE-CARTOON-v2.md',
        'cartoon-preservation-report.json':
            root / 'docs/cartoon-preservation-report.json',
        # The current candidate note is selected dynamically. Keep the
        # v0.10.1 art/polish note and its reports as historical context.
        'RELEASE.md': root / f'docs/RELEASE-v{version}.md',
        f'RELEASE-v{version}.md': root / f'docs/RELEASE-v{version}.md',
        f'preservation-v{version}.json': root / f'docs/preservation-v{version}.json',
        f'verification-v{version}.json': root / f'docs/verification-v{version}.json',
        'REVIEW.html': root / f'docs/REVIEW-v{version}.html',
        'CHAMPION-ENDING.md': root / 'docs/CHAMPION-ENDING.md',
        'champion-preservation-report.json': root / 'docs/champion-preservation-report.json',
        'champion-native-budget.json': root / 'docs/champion-native-budget.json',
        'champion-ending-report.json': root / 'docs/champion-ending-report.json',
        'champion-ending-start-report.json': root / 'docs/champion-ending-start-report.json',
        'champion-ending-back-report.json': root / 'docs/champion-ending-back-report.json',
        'qa/champion-art.json': root / 'assets/art/menu/champion-ending-v1.json',
        'qa/champion-generation.json': root / 'assets/art/menu/source-champion-v1/generation-v1.json',
        'screenshots/champion/ending.png': root / 'docs/screenshots/champion/ending.png',
        'screenshots/champion/arcade-result.png': root / 'docs/screenshots/champion/arcade-result.png',
        'screenshots/champion/exit-a.png': root / 'docs/screenshots/champion/exit-a.png',
        'screenshots/champion/exit-start.png': root / 'docs/screenshots/champion/exit-start.png',
        'screenshots/champion/exit-b.png': root / 'docs/screenshots/champion/exit-b.png',
        'screenshots/presentation/training-dummy.png': root / 'docs/screenshots/presentation/training-dummy.png',
        'screenshots/presentation/training-mirror.png': root / 'docs/screenshots/presentation/training-mirror.png',
        'POLISH-v0.10.1.md': root / 'docs/POLISH-v0.10.1.md',
        'polish-test-summary.json': root / 'docs/polish-test-summary.json',
        'polish-preservation-report.json':
            root / 'docs/polish-preservation-report.json',
        'lars-likeness-report.json': root / 'docs/lars-likeness-report.json',
        'review-feedback.json': root / 'docs/review-feedback.json',
        'qa/character-manifest.json':
            root / 'assets/generated/character-manifest.json',
        'LICENSE': root / 'LICENSE',
        'licenses/PVSnesLib.txt': root / 'licenses/PVSnesLib.txt',
        'licenses/SNESMod.txt': root / 'licenses/SNESMod.txt',
        'licenses/Snes9x.txt': root / 'licenses/Snes9x.txt',
    }


def qa_readme_bytes() -> bytes:
    return (
        '# QA evidence in this archive\n\n'
        'The JSON files under qa/ are copied byte-for-byte from the '
        'source checkout used for this candidate. Their ROM, core, check and '
        'provenance fields remain the release evidence that was audited.\n\n'
        'REVIEW.html embeds selected native presentation captures for offline '
        'inspection at 1x or 2x. Path and capture fields in those reports refer to the original '
        'checkout and to captures that are not bundled in this offline '
        'archive. Source-only documentation links are labeled explicitly so '
        'they are not mistaken for package files.\n\n'
        'Champion capture paths recorded as docs/screenshots/champion/... '
        'are bundled under screenshots/champion/...; remove the leading '
        'docs/ to locate those PNGs. The Markdown champion guide links them '
        'directly in the archive.\n\n'
        'The two Training selection captures are likewise bundled under '
        'screenshots/presentation/; their report paths retain the source '
        'docs/ prefix. REVIEW.html embeds both views.\n\n'
        'qa/character-manifest.json carries the source art provenance '
        'manifest used by the native export.\n'
    ).encode('utf-8')


def build_virtual_entries(pin_record: Mapping) -> dict[str, bytes]:
    return {
        'qa/README.md': qa_readme_bytes(),
        'qa/emulator-pins.json':
            (json.dumps(pin_record, indent=2, sort_keys=True) + '\n').encode(
                'utf-8'
            ),
        'Play.cmd': PLAY_COMMAND,
    }


def preflight_package_files(files: Mapping[str, Path],
                            virtual: Mapping[str, bytes] | None = None) -> set[str]:
    """Validate every mapped input before any release-scale validation."""
    virtual = virtual or {}
    names = set(files)
    overlap = names.intersection(virtual)
    require(not overlap, 'Duplicate archive entry names', sorted(overlap))
    names.update(virtual)
    for name, path in files.items():
        normalized = name.replace('\\', '/')
        parts = normalized.split('/')
        require(
            name == normalized and name and not name.startswith('/') and
            '..' not in parts,
            'Unsafe archive entry name',
            name,
        )
        require(Path(path).is_file(), 'Missing mapped package input', path)
    for name in virtual:
        normalized = name.replace('\\', '/')
        parts = normalized.split('/')
        require(
            name == normalized and name and not name.startswith('/') and
            '..' not in parts,
            'Unsafe virtual archive entry name',
            name,
        )
    return names


def _archive_target(archive_name: str, path: str) -> str | None:
    path = path.replace('\\', '/')
    if not path or path.startswith('/'):
        return None
    return posixpath.normpath(posixpath.join(posixpath.dirname(archive_name) or '.',
                                             path))


def _split_markdown_target(raw_target: str) -> tuple[str, str]:
    path, separator, fragment = raw_target.strip().partition('#')
    return path, (separator + fragment) if separator else ''


def _mapped_link(archive_name: str, path: str,
                 package_names: set[str] | None = None) -> str | None:
    mapped = OFFLINE_LINK_ALIASES.get((archive_name, path))
    if mapped is not None:
        return mapped
    # The source docs name the versioned release note.  The ZIP intentionally
    # gives the current note the stable root name RELEASE.md.
    if (package_names is not None and path in package_names and path.startswith('RELEASE-v') and
            path.endswith('.md') and 'RELEASE.md' in package_names):
        return 'RELEASE.md'
    return None


def offline_markdown_text(source: bytes | str, archive_name: str,
                          package_names: set[str]) -> str:
    """Make documentation links truthful when viewed from the ZIP root.

    Existing package-relative links are preserved.  A source-only link is
    rendered as visible text instead of a dead offline hyperlink.  This only
    changes the package copy; source documentation remains byte-identical.
    """
    text = source.decode('utf-8') if isinstance(source, bytes) else source

    def replace(match: re.Match[str]) -> str:
        label, raw_target = match.groups()
        path, suffix = _split_markdown_target(raw_target)
        if not path or path.startswith('#') or _EXTERNAL_LINK.match(path):
            return match.group(0)
        mapped = _mapped_link(archive_name, path, package_names)
        if mapped is not None:
            return f'{label}({mapped}{suffix})'
        resolved = _archive_target(archive_name, path)
        if resolved in package_names:
            return match.group(0)
        visible_label = label[2:-1] if label.startswith('![') else label[1:-1]
        return f'{visible_label} (source-only: {path}{suffix})'

    return _MARKDOWN_LINK.sub(replace, text)


def missing_offline_links(text: str, archive_name: str,
                          package_names: set[str]) -> list[str]:
    """Return relative links that remain unresolved in a package document."""
    missing = []
    for match in _MARKDOWN_LINK.finditer(text):
        _, raw_target = match.groups()
        path, _ = _split_markdown_target(raw_target)
        if not path or path.startswith('#') or _EXTERNAL_LINK.match(path):
            continue
        mapped = _mapped_link(archive_name, path, package_names)
        resolved = mapped or _archive_target(archive_name, path)
        if resolved not in package_names:
            missing.append(path)
    return missing


def entry_bytes(name: str, path: Path, package_names: set[str],
                pin_record: Mapping | None = None) -> bytes:
    data = Path(path).read_bytes()
    if name == 'manifest.json':
        manifest = json.loads(data.decode('utf-8'))
        if pin_record is not None:
            manifest = package_manifest(manifest, pin_record)
        return canonical_manifest_bytes(manifest)
    if name.endswith('.md'):
        return offline_markdown_text(data, name, package_names).encode('utf-8')
    return data


def validate_suite(report: Mapping, label: str, manifest_sha: str,
                   suite: str | None = None) -> None:
    require(report.get('rom_sha256') == manifest_sha,
            f'{label} verification must match the current ROM')
    require(report.get('status', 'passed') == 'passed',
            f'Run the complete {label} suite before packaging')
    if suite is not None:
        require(report.get('suite') == suite,
                f'{label} evidence must identify its suite')
    checks = report.get('checks')
    require(isinstance(checks, list) and len(checks) > 0,
            f'Incomplete {label} verification report')
    require(report.get('passed') == len(checks),
            f'Incomplete {label} verification report')
    require(all(item.get('passed') for item in checks),
            f'A {label} verification check failed')


def validate_candidate_docs(files: Mapping[str, Path], manifest: Mapping) -> None:
    """Keep the current guides bound to the candidate, before release checks."""
    marker = (f"<!-- candidate-version: {manifest['version']}; "
              f"rom-sha256: {manifest['sha256']} -->")
    names = ['README.md', 'RELEASE.md', 'COMPATIBILITY.md', 'PUBLIC-RELEASE.md']
    if 'CHAMPION-ENDING.md' in files:
        names.append('CHAMPION-ENDING.md')
    for name in names:
        text = files[name].read_text(encoding='utf-8')
        require(marker in text.splitlines()[:5],
                f'Current candidate identity is missing or stale in {name}', marker)


def validate_champion_provenance(root: Path = ROOT) -> None:
    """Check the art record's claims against retained source files and encoder."""
    from PIL import Image
    import champion_assets as champion
    record = read_json(root / champion.PROVENANCE, 'champion art provenance')
    generation = read_json(root / champion.PROMPT, 'champion exact generation record')
    expected = {
        'asset': champion.MASTER, 'version': 'v1', 'mode': 'built-in imagegen',
        'raw_output_path': champion.RAW,
        'raw_output_sha256': champion.RAW_SHA256,
        'exact_generation_record': champion.PROMPT,
        'generation_record_sha256': champion.text_sha256(root / champion.PROMPT),
        'transparent_background': False, 'prompt': generation['prompt'],
    }
    for field, value in expected.items():
        require(record.get(field) == value, 'Champion provenance mismatch: ' + field)
    with Image.open(root / champion.MASTER) as source:
        selected = {'path': champion.MASTER, 'sha256': sha256_file(root / champion.MASTER),
                    'size': list(source.size), 'mode': source.mode,
                    'colors': len(source.getcolors(1024 * 896) or [])}
    require(record.get('selected_final') == selected,
            'Champion selected-master metadata differs from the actual image')
    processing = record.get('processing', {})
    for field, value in {
        'source_size': [1340, 1174], 'center_aspect_crop_xyxy': list(champion.CROP),
        'cropped_size': [1336, 1169], 'aspect': '8:7',
        'native_size': [256, 224], 'native_resampling': 'nearest-neighbor',
        'master_size': [1024, 896], 'master_upscale': '4x nearest-neighbor',
        'palette': 'Pillow MEDIANCUT, 90 colors, no dithering', 'semantic_edits': False,
        'navy_palette_cleanup': {'rgb': [17, 26, 61], 'max_channel_distance': 12,
             'operation': 'collapse near-identical navy colors globally before quantization'},
    }.items():
        require(processing.get(field) == value,
                'Champion processing metadata mismatch: ' + field)
    # The encoder also verifies the pinned raw bytes and exact master grid.
    champion.load_champion(root)


def validate_champion_route(report: Mapping, rom_sha: str, key: str, screen: int) -> None:
    require(report.get('status') == 'passed' and report.get('rom_sha256') == rom_sha,
            'Champion route evidence is stale or incomplete', key)
    require(report.get('exit', {}).get('key') == key and
            report.get('exit', {}).get('screen') == screen,
            'Champion route does not prove the advertised destination', key)
    for field, expected in {'controller_only': True, 'headless': True,
                           'memory_writes': False, 'save_states': False,
                           'audio_device_opened': False}.items():
        require(report.get(field) is expected, 'Champion route contract: ' + field, key)
    host = report.get('host_contract', {})
    require(host.get('gui_opened') is False and host.get('audio_device_opened') is False,
            'Champion host must remain headless and silent', key)
    state = report.get('champion_state', {})
    require(state.get('mode') == 0 and state.get('champion') == 1 and
            state.get('arcade') == 10 and state.get('wins1') == 2,
            'Champion route must reach the earned Arcade ending', key)
    ladder = report.get('ladder', [])
    require(isinstance(ladder, list) and len(ladder) == 11,
            'Champion route must defeat eleven opponents', key)
    require({row.get('opponent') for row in ladder} == set(range(12)) - {state.get('fighter_id1')},
            'Champion route must defeat every other fighter exactly once', key)
    for index, row in enumerate(ladder):
        attempts = row.get('attempts', [])
        require(row.get('arena') == index % 3 and attempts and attempts[-1].get('wins1') == 2,
                'Champion ladder must retain actual stage order and victories', (key, index))


def champion_native_budget(root: Path, manifest: Mapping) -> dict:
    """Locate each static champion block in the linked cartridge, not prose."""
    symbols = (root / 'dist/abaqus-after-hours.sym').read_text()
    rom = (root / 'dist/abaqus-after-hours.sfc').read_bytes()
    blocks = []
    for label in ('champion_tiles', 'champion_map', 'champion_pal'):
        match = re.search(r'^([0-9a-fA-F]{8})\s+' + label + r'\s*$', symbols, re.M)
        require(match is not None, 'Missing native champion symbol', label)
        address = int(match.group(1), 16)
        bank, start = address >> 16, address & 0xffff
        data = (root / 'assets/generated' / (label + '.bin')).read_bytes()
        require(start >= 0x8000 and start + len(data) <= 0x10000,
                'Champion block crosses a 32 KiB LoROM bank', label)
        offset = (bank & 0x7f) * 0x8000 + start - 0x8000
        require(rom[offset:offset + len(data)] == data,
                'Linked champion block differs from its generated bytes', label)
        blocks.append({'symbol':label, 'cpu_start':f'${bank:02X}:{start:04X}',
                       'last_cpu_byte':f'${bank:02X}:{start + len(data) - 1:04X}',
                       'rom_offset':offset, 'bytes':len(data),
                       'sha256':sha256_bytes(data), 'fits_lorom_bank':True})
    fresh = read_json(root / 'docs/fresh-build-test-report.json', 'native budget source identity')
    require(fresh.get('status') == 'passed' and fresh.get('rom_sha256') == manifest['sha256'],
            'Native budget requires the matching clean-source rebuild')
    return {'version':manifest['version'], 'rom_sha256':manifest['sha256'],
            'source_freeze':fresh['source_commit'], 'status':'passed', 'blocks':blocks,
            'scope':'Linked symbol addresses, generated byte lengths and actual LoROM cartridge block bytes.'}


def validate_champion_evidence(root: Path, manifest: Mapping) -> None:
    validate_champion_provenance(root)
    for suffix, key, screen in (('', 'a', 0), ('-start', 'start', 0), ('-back', 'b', 1)):
        report = read_json(root / f'docs/champion-ending{suffix}-report.json', 'champion route')
        validate_champion_route(report, manifest['sha256'], key, screen)
    preserved = read_json(root / 'docs/champion-preservation-report.json', 'champion preservation')
    require(preserved.get('status') == 'passed' and
            preserved.get('rom_sha256') == manifest['sha256'],
            'Champion preservation evidence is stale or incomplete')
    for field, expected in {'generated_assets_total':218, 'existing_assets_preserved':212,
                           'registration_files_extended':2, 'generated_assets_added':4,
                           'native_assembly_preserved':2}.items():
        require(preserved.get(field) == expected, 'Champion preservation count: ' + field)
    fresh = read_json(root / 'docs/fresh-build-test-report.json', 'fresh source identity')
    require(fresh.get('status') == 'passed' and fresh.get('rom_sha256') == manifest['sha256'] and
            preserved.get('source_freeze') == fresh.get('source_commit'),
            'Champion preservation source must match the isolated current-ROM rebuild')
    require(read_json(root / 'docs/champion-native-budget.json', 'champion native budget') ==
            champion_native_budget(root, manifest),
            'Champion native address/budget record is stale or incomplete')


def write_entry(package: zipfile.ZipFile, name: str, data: bytes) -> None:
    # Source mtimes and the host OS must not change the archive checksum.
    entry = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
    entry.create_system = 0
    entry.external_attr = 0x20
    entry.compress_type = zipfile.ZIP_DEFLATED
    package.writestr(entry, data, compresslevel=9)


def main() -> None:
    manifest = read_json(ROOT / 'dist/manifest.json', 'manifest')
    require(isinstance(manifest, Mapping), 'Manifest must be a JSON object')
    require('sha256' in manifest and 'version' in manifest,
            'Manifest lacks package identity fields')

    # Catch a missing release note or report before checking the large release
    # evidence set or opening any output archive.
    files = build_package_files(ROOT, manifest)
    preflight_package_files(files)
    validate_candidate_docs(files, manifest)
    validate_champion_evidence(ROOT, manifest)
    pin_record = verify_gui_emulator(ROOT)
    virtual = build_virtual_entries(pin_record)
    package_names = preflight_package_files(files, virtual)

    reports = {
        'gameplay': read_json(ROOT / 'docs/test-report.json', 'gameplay'),
        'characters': read_json(ROOT / 'docs/character-test-report.json',
                                'roster'),
        'presentation': read_json(ROOT / 'docs/presentation-test-report.json',
                                  'presentation'),
        'inputs': read_json(ROOT / 'docs/input-test-report.json', 'input'),
        'stages': read_json(ROOT / 'docs/stage-test-report.json', 'stage'),
    }
    training_report = read_json(training_report_path(ROOT), 'training')
    for label, report in reports.items():
        validate_suite(report, label, manifest['sha256'])
    validate_suite(training_report, 'Training', manifest['sha256'], 'training')

    compatibility = read_json(ROOT / 'docs/compatibility-test-report.json',
                              'compatibility')
    require(compatibility.get('status') == 'passed',
            'Run the independent-engine smoke check before packaging')
    require(compatibility.get('rom', {}).get('sha256') == manifest['sha256'],
            'Compatibility smoke evidence must match the current ROM')

    rom_path = files['abaqus-after-hours.sfc']
    rom_sha256 = sha256_file(rom_path)
    require(rom_sha256 == manifest['sha256'], 'ROM differs from its manifest')
    # These release-scale reports are deliberately separate from Test.cmd.
    # Keep their validation shared with audit_release.py so stale or partial
    # evidence cannot enter the offline package.
    validate_release_evidence(ROOT, rom_sha256)

    archive = ROOT / 'dist' / (
        f"Abaqus-After-Hours-v{manifest['version']}-Windows.zip"
    )
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED,
                         compresslevel=9) as package:
        for name, path in files.items():
            write_entry(package, name, entry_bytes(name, path, package_names,
                                                    pin_record))
        for name, data in virtual.items():
            write_entry(package, name, data)
    digest = sha256_file(archive)
    (ROOT / 'dist/release-sha256.txt').write_bytes(
        (digest + '  ' + archive.name + '\n').encode('utf-8')
    )
    print('Packaged', archive.name, archive.stat().st_size, 'bytes')


if __name__ == '__main__':
    main()
