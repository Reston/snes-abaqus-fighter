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
from release_evidence import (EXTRA_REPORTS, EXPECTED_NATIVE_CORE, GENERATED_ASSET_COUNT, SOURCE_INPUT_EXACT, training_report_path,
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


def menu_capture_files(root: Path) -> dict[str, Path]:
    """Fixed capture inventory; report paths cannot add arbitrary package files."""
    names = []
    for mode in ('arcade', 'versus', 'training'):
        for scene in (('p1',) if mode == 'arcade' else ('p1', 'second')):
            names.extend(f'{mode}-{scene}-{fighter:02}' for fighter in range(12))
        names.extend(f'{mode}-arena-{arena}' for arena in range(3))
    files = {f'screenshots/menu-preservation/{role}/{name}{extension}':
            root/f'docs/screenshots/menu-preservation/{role}/{name}{extension}'
            for name in names for role in ('parent', 'candidate')
            for extension in ('.png', '.vram.bin')}
    for mode in ('arcade', 'versus', 'training'):
        scenes = ['p1', *(('second',) if mode != 'arcade' else ()),
                  *(f'arena-{arena}' for arena in range(3))]
        for scene in scenes:
            name = f'screenshots/menu-preservation/{mode}-{scene}.png'
            files[name] = root/'docs'/name
    return files


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
        **menu_capture_files(root),
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
        'ROSTER-REVIEW.html': root / f'docs/ROSTER-REVIEW-v{version}.html',
        'CHAMPION-ENDING.md': root / 'docs/CHAMPION-ENDING.md',
        'CHAMPION-AUDIO.md': root / 'docs/CHAMPION-AUDIO.md',
        'champion-audio-report.json': root / 'docs/champion-audio-report.json',
        'menu-footer-report.json': root / 'docs/menu-footer-report.json',
        'authoring-guards-report.json': root / 'docs/authoring-guards-report.json',
        f'audio-listening-v{version}.json': root / f'docs/audio-listening-v{version}.json',
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
        'ROSTER-REVIEW.html embeds the twelve generated native fighter strips '
        'for frame/facing inspection. Its fixed-rate sweep is an inspection aid, '
        'not emulator gameplay or the game animation timing.\n\n'
        'Champion capture paths recorded as docs/screenshots/champion/... '
        'are bundled under screenshots/champion/...; remove the leading '
        'docs/ to locate those PNGs. The Markdown champion guide links them '
        'directly in the archive.\n\n'
        'The two Training selection captures are likewise bundled under '
        'screenshots/presentation/; their report paths retain the source '
        'docs/ prefix. REVIEW.html embeds both views.\n\n'
        'menu-footer-report.json retains all 69 baseline/candidate menu states. '
        'Their original PNG and 64 KiB VRAM captures are bundled under '
        'screenshots/menu-preservation/parent/ and candidate/; remove the '
        'leading docs/ from report paths. Packaging recomputes PNG/VRAM hashes '
        'and compares actual pixels and VRAM above the changed footer. '
        'These are recorded controller-only emulator captures; the package '
        'validator does not replay the emulator to authenticate execution.\n\n'
        'The fourteen top-level footer captures in that report are also '
        'bundled directly under screenshots/menu-preservation/. Report paths '
        'retain the source docs/ prefix and may use Windows separators; '
        'remove that prefix and use forward slashes to locate the PNGs.\n\n'
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
    names += [name for name in ('CHAMPION-ENDING.md', 'CHAMPION-AUDIO.md') if name in files]
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
    require(isinstance(preserved, Mapping), 'Champion preservation report must be a JSON object')
    require(preserved.get('status') == 'passed' and
            preserved.get('rom_sha256') == manifest['sha256'],
            'Champion preservation evidence is stale or incomplete')
    fresh = read_json(root / 'docs/fresh-build-test-report.json', 'fresh source identity')
    require(fresh.get('status') == 'passed' and fresh.get('rom_sha256') == manifest['sha256'] and
            preserved.get('source_freeze') == fresh.get('source_commit'),
            'Champion preservation source must match the isolated current-ROM rebuild')
    validate_preservation(preserved, root, manifest, fresh['source_commit'])
    records, added = preserved.get('files', []), preserved.get('added', [])
    expected = {row['file'] for row in fresh['generated_assets']} | {'src/hardware.asm','src/trace.asm'}
    require(len(records) + len(added) == len(expected) and
            {row.get('path') for row in records + added} == expected,
            'Preservation must cover every generated file and both protected native ASM files')
    generated = [row for row in records if row['path'].startswith('assets/generated/')]
    counts = {'generated_assets_total':GENERATED_ASSET_COUNT,
              'existing_assets_preserved':sum(row.get('preserved') is True for row in generated),
              'generated_assets_modified':sum(row.get('preserved') is False for row in generated),
              'generated_assets_added':len(added),
              'native_assembly_preserved':sum(row.get('preserved') is True for row in records
                                             if row['path'].startswith('src/'))}
    for field, value in counts.items():
        require(preserved.get(field) == value, 'Champion preservation count: ' + field)
    require(counts['native_assembly_preserved'] == 2 and
            counts['existing_assets_preserved'] + counts['generated_assets_modified'] + len(added) == GENERATED_ASSET_COUNT,
            'Preservation totals must match the current native asset set')
    for row in records + added:
        require(sha256_file(root / row['path']) == row.get('sha256'),
                'Preservation file hash differs from the current input', row['path'])
    require(read_json(root / 'docs/champion-native-budget.json', 'champion native budget') ==
            champion_native_budget(root, manifest),
            'Champion native address/budget record is stale or incomplete')
    validate_champion_audio(read_json(root / 'docs/champion-audio-report.json', 'champion audio'),
                            root, manifest)
    validate_listening_record(root, manifest)


def validate_preservation(report: Mapping, root: Path, manifest: Mapping, source_freeze: str) -> None:
    require(isinstance(report, Mapping), 'Preservation report must be a JSON object')
    from preservation import validate_report
    try:
        validate_report(root, report, manifest, source_freeze)
    except (ValueError, OSError, KeyError) as error:
        raise PackageError('Preservation baseline comparison failed: '+str(error)) from error


def validate_champion_audio(report: Mapping, root: Path, manifest: Mapping) -> None:
    """Require production capture proof, with its separate cue fixture identified."""
    from victory_music import soundbank_budget
    require(report.get('suite') == 'focused-champion-audio' and
            report.get('status') == 'passed' and report.get('rom_sha256') == manifest['sha256'] and
            report.get('checksum') == manifest['checksum'],
            'Champion audio evidence must pass on the exact current cartridge')
    checks = report.get('checks')
    require(isinstance(checks, list) and checks and all(row.get('passed') is True for row in checks),
            'Champion audio checks are empty or failed')
    host = report.get('host_contract', {})
    require(report.get('controller_only') is True and report.get('emulated_memory_writes') == 0 and
            report.get('savestates') == 0 and host.get('gui_opened') is False and
            host.get('audio_device_opened') is False and host.get('priority_class') == 0x4000 and
            len(host.get('logical_processors', [])) == 2 and
            report.get('human_listening_approved') is False,
            'Champion audio must retain its silent controller-only technical scope')
    require(report.get('native_budget') == soundbank_budget(root / 'assets/generated/soundbank.bnk'),
            'Champion audio native soundbank budget is stale')
    require(report.get('core_sha256') == EXPECTED_NATIVE_CORE['dll_sha256'] ==
            sha256_file(root / '.tools/core/snes9x_libretro.dll'),
            'Champion audio core differs from the pinned native core')
    harness = report.get('harness_sha256', {})
    expected_harness = ('tools/test_champion_audio.py', 'tools/test_audio.py', 'tools/test_champion.py',
                        'tools/emulator.py', 'tools/victory_music.py', 'tools/make_assets.py')
    require(set(harness) == set(expected_harness) and
            all(harness[name] == sha256_file(root/name) for name in expected_harness),
            'Champion audio harness or authoring inputs changed after capture')
    cue_names = {'swing', 'impact', 'special', 'round-confirm'}
    require(set(report.get('production_cues', {})) == cue_names,
            'Champion audio must capture all four production cues')
    scores = ('title', 'las-condes', 'el-castillo', 'la-oficina', 'office-champion')
    music = report.get('music', {})
    require(set(music) == set(scores), 'Champion audio must capture all five scores')
    for index, name in enumerate(scores):
        score = music[name]
        pcm, repeat = score.get('pcm', {}), score.get('repeat', {})
        require(score.get('module') == index and score.get('module_sha256') ==
                sha256_file(root / f'assets/generated/music{index}.it'),
                'Champion audio score source is stale', name)
        require(pcm.get('clipped_samples') == 0 and pcm.get('rms', 0) > 32 and
                pcm.get('longest_near_silence_seconds', 1) < 0.5 and
                pcm.get('seconds', 0) > 2 * repeat.get('observed_pcm_repeat_seconds', float('inf')) and
                repeat.get('envelope_correlation', 0) >= 0.96 and
                repeat.get('zero_crossing_correlation', 0) >= 0.85,
                'Champion audio score lacks healthy full-cycle PCM evidence', name)
    for key, proof in (('a', music['office-champion'].get('controller_proof', {})),
                       ('start', report.get('start_exit', {}))):
        ladder, exit = proof.get('ladder', []), proof.get('title_exit', {})
        transition = proof.get('champion_transition', {}).get('frames', [])
        require(proof.get('controller_only') is True and len(ladder) == 11 and
                len({row.get('opponent') for row in ladder}) == 11 and
                all(row.get('arena') == index % 3 and row.get('attempts') and
                    row['attempts'][-1][0] == 2 for index, row in enumerate(ladder)) and
                exit.get('key') == key and exit.get('music_index') == 0 and transition and
                {row.get('music_index') for row in transition} == {2, 4} and
                max(row.get('spc_backlog', 256) for row in transition) <= 6 and
                transition[-1].get('spc_backlog') == 0,
                'Champion audio requires earned victory and drained title-exit proof', key)
    fixture = report.get('victory_cue_fixture', {})
    require(fixture.get('production_rom') is False and fixture.get('emulated_memory_writes') == 0 and
            fixture.get('savestates') == 0 and fixture.get('rom_sha256') != manifest['sha256'] and
            set(fixture.get('cues', {})) == cue_names,
            'Champion cue fixture must remain separately identified')


def validate_listening_record(root: Path, manifest: Mapping) -> None:
    record = read_json(root / f"docs/audio-listening-v{manifest['version']}.json", 'listening archive record')
    require(isinstance(record, Mapping) and record.get('status') == 'passed' and
            record.get('version') == manifest['version'] and record.get('rom_sha256') == manifest['sha256'] and
            record.get('human_listening_approved') is False and
            record.get('source_report') == 'docs/champion-audio-report.json' and
            record.get('source_report_sha256') == sha256_file(root/'docs/champion-audio-report.json'),
            'Listening archive record must match current capture evidence')
    archive = record.get('archive', {})
    relative = f"dist/Abaqus-After-Hours-v{manifest['version']}-Audio-Review.zip"
    path = root / relative
    require(archive.get('file') == relative and path.is_file() and
            archive.get('bytes') == path.stat().st_size and archive.get('sha256') == sha256_file(path),
            'Separate listening archive differs from its exact capture record')
    with zipfile.ZipFile(path) as listening:
        require(listening.testzip() is None, 'Listening archive CRC failed')
        inside = json.loads(listening.read('manifest.json'))
        require(inside.get('version') == manifest['version'] and
                inside.get('rom_sha256') == manifest['sha256'] and
                inside.get('human_listening_approved') is False and len(inside.get('captures', [])) == 13,
                'Listening archive manifest must identify all thirteen current technical captures')
        for capture in inside['captures']:
            require(sha256_bytes(listening.read(capture['file'])) == capture['sha256'],
                    'Listening archive capture differs from its verified hash', capture['file'])


def validate_menu_evidence(report: Mapping, root: Path, manifest: Mapping) -> None:
    from PIL import Image
    from preservation import POLICIES, committed_files, git, resolve
    require(isinstance(report, Mapping), 'Menu footer proof must be a JSON object')
    require(report.get('status') == 'passed' and report.get('rom_sha256') == manifest['sha256'] and
            report.get('header_checksum') == manifest['checksum'],
            'Menu footer proof must match the exact current cartridge')
    checks, host = report.get('checks'), report.get('host_contract', {})
    require(isinstance(checks, list) and len(checks) == 4650 and
            all(isinstance(row, Mapping) and row.get('passed') is True and
                isinstance(row.get('check'), str) and row['check'] and 'details' in row for row in checks) and
            report.get('controller_only') is True and report.get('memory_writes') is False and
            report.get('save_states') is False and host.get('gui_opened') is False and
            host.get('audio_device_opened') is False and host.get('priority_class') == 0x4000 and
            len(host.get('logical_processors', [])) == 2,
            'Menu footer proof must retain its complete silent controller-only scope')
    core = root/'.tools/core/snes9x_libretro.dll'
    require(core.is_file() and sha256_file(core) == report.get('core_sha256') ==
            EXPECTED_NATIVE_CORE['dll_sha256'],
            'Menu footer proof must use the pinned native core')
    harness = report.get('harness_sha256', {})
    names = ('test_menu_footers.py', 'test_presentation.py', 'emulator.py',
             'test_champion.py', 'preservation.py')
    require(set(harness) == set(names) and
            all(harness[name] == sha256_file(root/'tools'/name) for name in names),
            'Menu footer proof harness changed after capture')
    assets = report.get('asset_preservation', {})
    policy = POLICIES[manifest['version']]
    try:
        baseline = resolve(root, assets.get('baseline_ref', ''))
    except ValueError as error:
        raise PackageError('Menu footer baseline does not resolve') from error
    require(baseline == policy['baseline_commit'] and
            assets.get('generated_files') == GENERATED_ASSET_COUNT and
            assets.get('identical_generated_files') == GENERATED_ASSET_COUNT,
            'Menu footer assets must match the approved baseline')
    fresh = read_json(root/'docs/fresh-build-test-report.json', 'menu footer asset coverage')
    require(fresh.get('status') == 'passed' and fresh.get('rom_sha256') == manifest['sha256'],
            'Menu footer source freeze must identify the current cartridge')
    for name in ('tools/preservation.py', 'tools/test_champion.py'):
        actual = (root/name).read_bytes().replace(b'\r\n', b'\n')
        frozen = git(root, 'show', fresh['source_commit']+':'+name).replace(b'\r\n', b'\n')
        require(actual == frozen, 'Menu footer shared helper differs from source freeze', name)
    expected = {row['file'] for row in fresh['generated_assets']} | {'tools/menu_assets.py'}
    files = assets.get('files', {})
    require(set(files) == expected, 'Menu footer asset inventory is incomplete')
    before = {name: data for name, data in committed_files(root, baseline).items()
              if name.startswith('assets/generated/')}
    before['tools/menu_assets.py'] = git(root, 'show', baseline+':tools/menu_assets.py')
    require(set(before) == expected, 'Menu footer baseline asset inventory differs')
    for name, row in files.items():
        text = Path(name).suffix in ('.asm', '.h', '.json', '.py')
        raw = (root/name).read_bytes()
        comparable = raw.replace(b'\r\n', b'\n') if text else raw
        original = before[name].replace(b'\r\n', b'\n') if text else before[name]
        require(comparable == original,
                'Menu footer asset differs from the approved baseline Git blob', name)
        require(isinstance(row, Mapping) and
                row.get('comparison') == ('LF-normalized text' if text else 'exact bytes') and
                row.get('sha256') == sha256_bytes(comparable) and row.get('bytes') == len(comparable),
                'Menu footer asset comparison differs from its current input', name)
    native = report.get('native_preservation', {})
    states = native.get('states', {})
    expected_states = set()
    for mode in ('arcade', 'versus', 'training'):
        for scene in (('p1',) if mode == 'arcade' else ('p1', 'second')):
            expected_states.update(f'{mode}-{scene}-{fighter:02}' for fighter in range(12))
        expected_states.update(f'{mode}-arena-{arena}' for arena in range(3))
    require(native.get('baseline_rom_sha256') == policy['baseline_rom_sha256'] and
            native.get('roster_states') == 60 and native.get('arena_states') == 9 and
            native.get('pixel_difference_above_footer') == 0 and set(states) == expected_states,
            'Menu footer native proof must cover every preserved scene')
    for name, state in states.items():
        bottom = 208 if '-arena-' in name else 216
        bounds = [0, 0, 256, bottom]
        require(isinstance(state, Mapping) and isinstance(state.get('baseline'), Mapping),
                'Menu footer native proof must retain both capture records', name)
        pixels, regions = [], []
        for role, recorded in (('parent', state['baseline']), ('candidate', state)):
            directory = f'docs/screenshots/menu-preservation/{role}/{name}'
            require(recorded.get('preserved_pixel_bounds') == bounds and
                    recorded.get('capture') == directory+'.png' and
                    recorded.get('vram_capture') == directory+'.vram.bin',
                    'Menu footer capture must use its exact bounded evidence path', name)
            png, memory_path = root/(directory+'.png'), root/(directory+'.vram.bin')
            require(png.is_file() and memory_path.is_file() and
                    sha256_file(png) == recorded.get('capture_sha256') and
                    sha256_file(memory_path) == recorded.get('vram_sha256'),
                    'Menu footer retained capture bytes differ from the report', (role, name))
            try:
                with Image.open(png) as frame:
                    require(frame.size == (256, 224) and frame.mode == 'RGB',
                            'Menu footer capture must retain native RGB dimensions', name)
                    cropped = frame.crop(tuple(bounds)).tobytes()
            except (OSError, ValueError) as error:
                raise PackageError('Menu footer PNG cannot be decoded: '+name) from error
            memory = memory_path.read_bytes()
            preserved = (memory[:0x7800], memory[0xB000:0xB000+bottom//8*64])
            require(len(memory) == 0x10000 and
                    sha256_bytes(cropped) == recorded.get('pixels_sha256') and
                    sha256_bytes(preserved[0]) == recorded.get('bg1_tiles_and_map_sha256') and
                    sha256_bytes(preserved[1]) == recorded.get('bg2_above_footer_sha256'),
                    'Menu footer pixel/VRAM hashes differ from actual retained data', (role, name))
            pixels.append(cropped)
            regions.append(preserved)
        require(pixels[0] == pixels[1] and regions[0] == regions[1],
                'Menu footer baseline/candidate preserved pixels or VRAM differ', name)
    validate_menu_captures(report.get('captures'), root)
    cases = report.get('controller_actions', [])
    actual_cases = set()
    key_sets = (('a',), ('start',), ('b',), ('b', 'a'), ('start', 'b', 'a'))
    expected_cases = set()
    for mode in ('arcade', 'versus', 'training'):
        scenes = (('p1', 0), ('arena', 0)) if mode == 'arcade' else (
            ('p1', 0), ('second', 0), ('second', 1), ('arena', 0))
        expected_cases.update((mode, scene, port, keys) for scene, port in scenes for keys in key_sets)
    for case in cases:
        key = (case.get('mode'), case.get('scene'), case.get('port'), tuple(case.get('keys', [])))
        require(key in expected_cases and key not in actual_cases,
                'Menu footer proof has a missing, duplicate or unknown route')
        actual_cases.add(key)
        confirms = 'start' in key[3] or ('a' in key[3] and 'b' not in key[3])
        if key[1] == 'arena':
            wanted = 3 if confirms else 1
        elif key[1] == 'p1':
            wanted = (2 if key[0] == 'arcade' else 1) if confirms else 0
        else:
            wanted = 2 if confirms else 1
        require(case.get('screen') == wanted, 'Menu footer route destination is incorrect', key)
    require(actual_cases == expected_cases, 'Menu footer proof must cover all fifty advertised routes')


def validate_menu_captures(captures, root: Path) -> None:
    """Recompute the fourteen native footer comparisons from bundled PNGs."""
    from PIL import Image
    require(isinstance(captures, Mapping) and set(captures) == {'arcade', 'versus', 'training'},
            'Menu footer captures must retain all three modes')
    generated = root/'assets/generated'
    tiles = (generated/'ui_tiles.bin').read_bytes()
    palette = (generated/'ui_pal.bin').read_bytes()
    colors = []
    for index in range(16):
        value = int.from_bytes(palette[index*2:index*2+2], 'little')
        colors.append(tuple((((value >> shift) & 31) << 3) | (((value >> shift) & 31) >> 2)
                            for shift in (0, 5, 10)))

    def draw(image, tile, left, top, transparent=False):
        raw = tiles[tile*32:tile*32+32]
        require(len(raw) == 32, 'Menu footer source glyph is incomplete', tile)
        for y in range(8):
            planes = (raw[y*2], raw[y*2+1], raw[16+y*2], raw[17+y*2])
            for x in range(8):
                index = sum(((plane >> (7-x)) & 1) << bit for bit, plane in enumerate(planes))
                if index or not transparent:
                    image.putpixel((left+x, top+y), colors[index])

    roster_text = 'D-PAD SELECT A/START OK B BACK'
    arena_text = 'UP/DOWN A/START OK B BACK'
    with Image.open(generated/'select.png') as plate:
        roster = plate.convert('RGB').crop((0, 216, 256, 224))
    for offset, character in enumerate(roster_text):
        draw(roster, ord(character), (1+offset)*8, 0, True)
    arena = Image.new('RGB', (256, 16))
    for row in range(2):
        for column in range(32):
            tile = 128
            if row == 1 and 3 <= column < 3+len(arena_text):
                tile = 256+ord(arena_text[column-3])
            draw(arena, tile, column*8, row*8)
    for mode in ('arcade', 'versus', 'training'):
        record = captures[mode]
        scenes = ('p1',) if mode == 'arcade' else ('p1', 'second')
        require(isinstance(record, Mapping) and set(record) == set(scenes)|{'arenas'} and
                isinstance(record['arenas'], list) and len(record['arenas']) == 3,
                'Menu footer capture scene inventory is incomplete', mode)
        rows = [(scene, record[scene], roster, roster_text, 1, 216) for scene in scenes]
        rows.extend((f'arena-{number}', entry, arena, arena_text, 3, 208)
                    for number, entry in enumerate(record['arenas']))
        for scene, entry, expected, text, x, top in rows:
            relative = f'docs/screenshots/menu-preservation/{mode}-{scene}.png'
            require(isinstance(entry, Mapping) and entry.get('capture') == relative and
                    entry.get('text') == text and entry.get('tile_x') == x and entry.get('tile_row') == 27 and
                    (top != 208 or entry.get('panel_pixel_bounds') == [0, 208, 256, 224]),
                    'Menu footer capture path, text or placement differs from its fixed contract', (mode, scene))
            path = root/relative
            require(path.is_file() and sha256_file(path) == entry.get('capture_sha256'),
                    'Menu footer screenshot differs from its recorded hash', relative)
            try:
                with Image.open(path) as image:
                    require(image.size == (256, 224) and image.mode == 'RGB',
                            'Menu footer screenshot must retain native RGB dimensions', relative)
                    actual = image.crop((0, top, 256, 224))
            except (OSError, ValueError) as error:
                raise PackageError('Menu footer screenshot cannot be decoded: '+relative) from error
            differences = [tuple(abs(a-b) for a, b in zip(ap, ep))
                           for ap, ep in zip(actual.get_flattened_data(), expected.get_flattened_data())]
            delta = {'mean_channel_delta': sum(sum(pixel) for pixel in differences)/(len(differences)*3),
                     'max_channel_delta': max(max(pixel) for pixel in differences),
                     'pixels_over_16': sum(max(pixel) > 16 for pixel in differences),
                     'pixels': len(differences)}
            require(delta['max_channel_delta'] <= 8 and all(entry.get(key) == value for key, value in delta.items()),
                    'Menu footer screenshot comparison differs from actual source glyph pixels', relative)


def validate_authoring_evidence(report: Mapping, root: Path, manifest: Mapping) -> None:
    import ast
    from preservation import git
    require(isinstance(report, Mapping) and report.get('status') == 'passed' and
            report.get('version') == manifest['version'] and report.get('rom_sha256') == manifest['sha256'],
            'Authoring guard evidence must identify the current candidate')
    fresh = read_json(root/'docs/fresh-build-test-report.json', 'authoring source freeze')
    require(fresh.get('status') == 'passed' and fresh.get('rom_sha256') == manifest['sha256'] and
            report.get('source_commit') == fresh.get('source_commit'),
            'Authoring checks must match the isolated source freeze')
    host = report.get('host_contract', {})
    require(host.get('gui_opened') is False and host.get('audio_device_opened') is False and
            host.get('priority_class') == 0x4000 and len(host.get('logical_processors', [])) == 2,
            'Authoring checks must retain their quiet background host contract')
    names = {name for name in SOURCE_INPUT_EXACT if name.endswith('.py')} | {
        'tools/test_authoring_guards.py', 'tools/test_champion.py'}
    hashes = report.get('source_sha256', {})
    require(set(hashes) == set(names), 'Authoring checks must identify every tested source')
    for name in names:
        actual = (root/name).read_bytes().replace(b'\r\n', b'\n')
        frozen = git(root, 'show', fresh['source_commit']+':'+name).replace(b'\r\n', b'\n')
        require(actual == frozen and hashes[name] == sha256_bytes(actual),
                'Authoring checks source differs from its frozen provenance', name)
    try:
        from preservation import resolve
        producer = resolve(root, report.get('producer_commit', ''))
        git(root, 'merge-base', '--is-ancestor', fresh['source_commit'], producer)
        git(root, 'merge-base', '--is-ancestor', producer, 'HEAD')
        frozen_manifest = json.loads(git(root, 'show', producer+':dist/manifest.json'))
        producer_hashes = {}
        for name in ('tools/check_authoring_guards.py', 'tools/release_evidence.py'):
            actual = (root/name).read_bytes().replace(b'\r\n', b'\n')
            frozen = git(root, 'show', producer+':'+name).replace(b'\r\n', b'\n')
            require(actual == frozen, 'Authoring producer differs from its committed bytes', name)
            producer_hashes[name] = sha256_bytes(actual)
    except (ValueError, OSError) as error:
        raise PackageError('Authoring producer commit cannot be verified') from error
    require(frozen_manifest == manifest and report.get('producer_sha256') == producer_hashes,
            'Authoring report producer differs from its committed provenance')
    tree = ast.parse((root/'tools/test_authoring_guards.py').read_text(encoding='utf-8'))
    expected_tests = sum(isinstance(node, ast.FunctionDef) and node.name.startswith('test_')
                         for cls in tree.body if isinstance(cls, ast.ClassDef) and cls.name == 'AuthoringGuards'
                         for node in cls.body)
    runs = report.get('runs', [])
    require(expected_tests > 0 and len(runs) == 2, 'Authoring checks require both interpreter modes')
    for optimized, run in zip((False, True), runs):
        output = run.get('output', '')
        count = re.search(r'Ran (\d+) tests? in', output)
        require(run.get('optimized') is optimized and run.get('exit_code') == 0 and
                run.get('tests') == expected_tests and count is not None and int(count[1]) == expected_tests and
                output.rstrip().endswith('OK') and run.get('arguments') ==
                (['-O'] if optimized else [])+['tools/test_authoring_guards.py'],
                'Authoring mutation checks must pass completely in both normal and optimized Python')


def validate_verification_summary(report: Mapping, root: Path, manifest: Mapping) -> None:
    """Bind the collated package record to its independently validated inputs."""
    fresh = read_json(root/'docs/fresh-build-test-report.json', 'verification source freeze')
    require(isinstance(report, Mapping) and report.get('status') == 'passed' and
            report.get('version') == manifest['version'] and report.get('rom_sha256') == manifest['sha256'] and
            report.get('checksum') == manifest['checksum'] and report.get('rom_bytes') == manifest['bytes'] and
            report.get('source_commit') == fresh.get('source_commit') and
            report.get('source_tree') == fresh.get('source_tree') and
            report.get('public_release_certified') is False,
            'Collated verification must identify the current cartridge and source freeze')
    paths = {'gameplay': 'docs/test-report.json', 'characters': 'docs/character-test-report.json',
             'presentation': 'docs/presentation-test-report.json', 'inputs': 'docs/input-test-report.json',
             'stages': 'docs/stage-test-report.json', 'training': 'docs/training-test-report.json'}
    suites = report.get('native_suites', {})
    require(isinstance(suites, Mapping) and set(suites) == set(paths),
            'Collated verification must retain all six native suites')
    total = 0
    for name, path in paths.items():
        source = read_json(root/path, 'verification '+name)
        validate_suite(source, name, manifest['sha256'], 'training' if name == 'training' else None)
        row = suites[name]
        require(isinstance(row, Mapping) and row.get('report') == path and
                row.get('status') == 'passed' and row.get('passed') == source['passed'] and
                row.get('checks') == len(source['checks']),
                'Collated verification native counts differ from exact-ROM evidence', name)
        total += source['passed']
    require(report.get('native_checks_total') == total,
            'Collated verification total differs from all six native suites')


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
    validate_verification_summary(read_json(ROOT/f"docs/verification-v{manifest['version']}.json",
                                           'collated verification'), ROOT, manifest)
    validate_champion_evidence(ROOT, manifest)
    validate_menu_evidence(read_json(ROOT/'docs/menu-footer-report.json', 'menu footer proof'), ROOT, manifest)
    validate_authoring_evidence(read_json(ROOT/'docs/authoring-guards-report.json', 'authoring guard proof'), ROOT, manifest)
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
