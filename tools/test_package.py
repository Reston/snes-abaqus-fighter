"""Headless mutation checks for package pins and preflight, including python -O."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
import importlib.util
import json
import re
import copy
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('package_under_test',
                                               ROOT / 'tools/package.py')
PACKAGE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(PACKAGE)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def expect_package_error(action, label: str) -> None:
    try:
        action()
    except PACKAGE.PackageError:
        return
    raise RuntimeError(f'expected PackageError: {label}')


def check_menu_input_mutations(menu, manifest) -> None:
    """Change real inputs and matching report rows in a disposable Git-backed copy."""
    from PIL import Image
    with tempfile.TemporaryDirectory(dir=ROOT/'build/package-audit') as temporary:
        sandbox = Path(temporary)/'checkout'
        # Read approved objects through a local shared clone; never mutate the
        # real checkout, baseline objects, core or retained capture evidence.
        subprocess.run(['git', 'clone', '--shared', '--no-checkout', '--quiet', str(ROOT), str(sandbox)],
                       stdin=subprocess.DEVNULL, capture_output=True, check=True)
        relative = set(menu['asset_preservation']['files']) | {
            'docs/fresh-build-test-report.json', '.tools/core/snes9x_libretro.dll'}
        relative.update('tools/'+name for name in menu['harness_sha256'])
        relative.update(path.relative_to(ROOT).as_posix()
                        for path in PACKAGE.menu_capture_files(ROOT).values())
        for name in relative:
            target = sandbox/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/name, target)
        PACKAGE.validate_menu_evidence(menu, sandbox, manifest)

        name = 'assets/generated/arenas_pal.bin'
        path = sandbox/name
        original = path.read_bytes()
        changed = bytearray(original)
        changed[0] ^= 1
        path.write_bytes(changed)
        altered = copy.deepcopy(menu)
        altered['asset_preservation']['files'][name].update(
            sha256=PACKAGE.sha256_bytes(changed), bytes=len(changed))
        expect_package_error(lambda: PACKAGE.validate_menu_evidence(altered, sandbox, manifest),
                             'current asset and its matching rewritten report row')
        path.write_bytes(original)

        core = sandbox/'.tools/core/snes9x_libretro.dll'
        original = core.read_bytes()
        changed = bytearray(original)
        changed[0] ^= 1
        core.write_bytes(changed)
        expect_package_error(lambda: PACKAGE.validate_menu_evidence(menu, sandbox, manifest),
                             'changed installed libretro core with unchanged report')
        core.write_bytes(original)

        name = 'arcade-p1-00'
        state = menu['native_preservation']['states'][name]
        png = sandbox/state['capture']
        original = png.read_bytes()
        with Image.open(png) as frame:
            changed = frame.copy()
        pixel = changed.getpixel((0, 0))
        changed.putpixel((0, 0), (pixel[0] ^ 1, pixel[1], pixel[2]))
        changed.save(png)
        altered = copy.deepcopy(menu)
        entry = altered['native_preservation']['states'][name]
        entry['capture_sha256'] = PACKAGE.sha256_file(png)
        entry['pixels_sha256'] = PACKAGE.sha256_bytes(
            changed.crop(tuple(entry['preserved_pixel_bounds'])).tobytes())
        expect_package_error(lambda: PACKAGE.validate_menu_evidence(altered, sandbox, manifest),
                             'changed actual capture and matching candidate hashes')
        png.write_bytes(original)

        memory = sandbox/state['vram_capture']
        original = memory.read_bytes()
        changed = bytearray(original)
        changed[0] ^= 1
        memory.write_bytes(changed)
        altered = copy.deepcopy(menu)
        entry = altered['native_preservation']['states'][name]
        entry['vram_sha256'] = PACKAGE.sha256_bytes(changed)
        entry['bg1_tiles_and_map_sha256'] = PACKAGE.sha256_bytes(changed[:0x7800])
        expect_package_error(lambda: PACKAGE.validate_menu_evidence(altered, sandbox, manifest),
                             'changed actual preserved VRAM and matching candidate hashes')
        memory.write_bytes(original)
        PACKAGE.validate_menu_evidence(menu, sandbox, manifest)

        entry = menu['captures']['arcade']['p1']
        png = sandbox/entry['capture']
        with Image.open(png) as frame:
            changed = frame.copy()
        changed.putpixel((8, 217), (255, 0, 255))
        changed.save(png)
        altered = copy.deepcopy(menu)
        altered['captures']['arcade']['p1']['capture_sha256'] = PACKAGE.sha256_file(png)
        expect_package_error(lambda: PACKAGE.validate_menu_evidence(altered, sandbox, manifest),
                             'changed actual footer pixels with matching rewritten screenshot hash')


def main() -> None:
    (ROOT / 'build/package-audit').mkdir(parents=True, exist_ok=True)
    # Production guards remain active under python -O.
    expect_package_error(lambda: PACKAGE.require(False, 'sentinel'),
                         'explicit require guard')

    with tempfile.TemporaryDirectory(
            dir=ROOT / 'build/package-audit') as temporary:
        sandbox = Path(temporary)
        tools = sandbox / '.tools/snes9x'
        tools.mkdir(parents=True)
        shutil.copy2(ROOT / '.tools/snes9x.zip', sandbox / '.tools/snes9x.zip')
        shutil.copy2(ROOT / '.tools/snes9x/snes9x-x64.exe',
                     tools / 'snes9x-x64.exe')
        PACKAGE.verify_gui_emulator(sandbox)

        executable = tools / 'snes9x-x64.exe'
        data = bytearray(executable.read_bytes())
        data[0] ^= 0x01
        executable.write_bytes(data)
        expect_package_error(lambda: PACKAGE.verify_gui_emulator(sandbox),
                             'tampered expanded executable')

        shutil.copy2(ROOT / '.tools/snes9x/snes9x-x64.exe', executable)
        archive = sandbox / '.tools/snes9x.zip'
        data = bytearray(archive.read_bytes())
        data[0] ^= 0x01
        archive.write_bytes(data)
        expect_package_error(lambda: PACKAGE.verify_gui_emulator(sandbox),
                             'tampered GUI archive')

        expect_package_error(
            lambda: PACKAGE.preflight_package_files(
                {'missing.txt': sandbox / 'does-not-exist.txt'}
            ),
            'missing mapped package input',
        )

        candidate = {'version': '0.11.0', 'sha256': 'a' * 64}
        marker = '<!-- candidate-version: 0.11.0; rom-sha256: ' + 'a' * 64 + ' -->'
        guide = sandbox / 'guide.md'
        guide.write_text('# Current guide\n' + marker + '\n')
        guide_names = ('README.md', 'RELEASE.md', 'COMPATIBILITY.md', 'PUBLIC-RELEASE.md')
        guides = {name: guide for name in guide_names}
        PACKAGE.validate_candidate_docs(guides, candidate)
        expect_package_error(
            lambda: PACKAGE.validate_candidate_docs(guides, dict(candidate, sha256='b' * 64)),
            'stale candidate documentation identity',
        )
        champion_guide = sandbox / 'champion.md'
        champion_guide.write_text('# Champion\n' + marker + '\n')
        guides['CHAMPION-ENDING.md'] = champion_guide
        PACKAGE.validate_candidate_docs(guides, candidate)
        champion_guide.write_text('# Champion\n<!-- stale child ROM -->\n')
        expect_package_error(lambda: PACKAGE.validate_candidate_docs(guides, candidate),
                             'stale champion documentation identity')
        guides.pop('CHAMPION-ENDING.md')
        guides['CHAMPION-AUDIO.md'] = champion_guide
        expect_package_error(lambda: PACKAGE.validate_candidate_docs(guides, candidate),
                             'stale champion audio documentation identity')

        import champion_assets as champion
        for relative in (champion.PROVENANCE, champion.PROMPT, champion.RAW, champion.MASTER):
            target = sandbox / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        PACKAGE.validate_champion_provenance(sandbox)
        provenance_path = sandbox / champion.PROVENANCE
        original = json.loads(provenance_path.read_text())
        for field, value in (('raw_output_path', 'wrong.png'),
                             ('raw_output_sha256', '0' * 64),
                             ('exact_generation_record', 'wrong.json'),
                             ('prompt', 'substituted prompt'),
                             ('selected_final', dict(original['selected_final'], path='wrong.png')),
                             ('processing', dict(original['processing'], native_size=[512, 448]))):
            altered = dict(original, **{field:value})
            provenance_path.write_text(json.dumps(altered))
            expect_package_error(lambda: PACKAGE.validate_champion_provenance(sandbox),
                                 'false champion provenance: ' + field)
        provenance_path.write_text(json.dumps(original))

        for relative in ('dist/manifest.json', 'dist/abaqus-after-hours.sfc',
                         'dist/abaqus-after-hours.sym', 'docs/fresh-build-test-report.json',
                         'assets/generated/champion_tiles.bin', 'assets/generated/champion_map.bin',
                         'assets/generated/champion_pal.bin'):
            target = sandbox / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        manifest = json.loads((sandbox/'dist/manifest.json').read_text())
        budget = PACKAGE.champion_native_budget(sandbox, manifest)
        cartridge = sandbox/'dist/abaqus-after-hours.sfc'
        cartridge_bytes = cartridge.read_bytes()
        changed = bytearray(cartridge_bytes)
        changed[budget['blocks'][0]['rom_offset']] ^= 1
        cartridge.write_bytes(changed)
        expect_package_error(lambda: PACKAGE.champion_native_budget(sandbox, manifest),
                             'native block differs from the actual cartridge')
        cartridge.write_bytes(cartridge_bytes)
        symbols = sandbox/'dist/abaqus-after-hours.sym'
        symbols.write_text(re.sub(r'(?m)^[0-9a-f]{8} champion_tiles$',
                                 '00e5ffff champion_tiles', symbols.read_text()))
        expect_package_error(lambda: PACKAGE.champion_native_budget(sandbox, manifest),
                             'native block crosses a LoROM bank')

    valid = {'rom_sha256': 'a' * 64, 'status': 'passed', 'passed': 1,
             'checks': [{'passed': True}]}
    PACKAGE.validate_suite(valid, 'fixture', 'a' * 64)
    for altered in (dict(valid, rom_sha256='b' * 64),
                    dict(valid, checks=[], passed=0),
                    dict(valid, checks=[{'passed': False}]),
                    dict(valid, status='failed')):
        expect_package_error(lambda: PACKAGE.validate_suite(altered, 'fixture', 'a' * 64),
                             'stale, empty, incomplete or failed suite')

    route = json.loads((ROOT/'docs/champion-ending-start-report.json').read_text())
    PACKAGE.validate_champion_route(route, route['rom_sha256'], 'start', 0)
    for altered in (dict(route, controller_only=False), dict(route, memory_writes=True),
                    dict(route, save_states=True), dict(route, headless=False),
                    dict(route, audio_device_opened=True), dict(route, ladder=route['ladder'][:10]),
                    dict(route, exit={'key':'start','screen':1}),
                    dict(route, champion_state=dict(route['champion_state'], arcade=9))):
        expect_package_error(lambda: PACKAGE.validate_champion_route(altered, route['rom_sha256'], 'start', 0),
                             'incomplete or altered champion route contract')

    manifest = json.loads((ROOT/'dist/manifest.json').read_text())
    verification = json.loads((ROOT/f"docs/verification-v{manifest['version']}.json").read_bytes())
    PACKAGE.validate_verification_summary(verification, ROOT, manifest)
    altered_total = copy.deepcopy(verification)
    altered_total['native_suites']['inputs']['passed'] += 1
    altered_total['native_checks_total'] += 1
    for altered in (dict(verification, version='0.0.0'), dict(verification, rom_sha256='0'*64),
                    dict(verification, source_commit='0'*40), dict(verification, native_checks_total=1),
                    dict(verification, public_release_certified=True), altered_total):
        expect_package_error(lambda: PACKAGE.validate_verification_summary(altered, ROOT, manifest),
                             'stale or inconsistent collated verification')
    audio = json.loads((ROOT/'docs/champion-audio-report.json').read_text())
    PACKAGE.validate_champion_audio(audio, ROOT, manifest)
    mutations = [dict(audio, rom_sha256='0'*64), dict(audio, status='failed'),
                 dict(audio, checks=[]), dict(audio, human_listening_approved=True),
                 dict(audio, production_cues={}), dict(audio, native_budget={}),
                 dict(audio, music={}), dict(audio, start_exit={})]
    altered = copy.deepcopy(audio)
    altered['music']['office-champion']['pcm']['clipped_samples'] = 1
    mutations.append(altered)
    altered = copy.deepcopy(audio)
    altered['victory_cue_fixture']['production_rom'] = True
    mutations.append(altered)
    for altered in mutations:
        expect_package_error(lambda: PACKAGE.validate_champion_audio(altered, ROOT, manifest),
                             'stale or malformed champion audio proof')

    menu = json.loads((ROOT/'docs/menu-footer-report.json').read_bytes())
    PACKAGE.validate_menu_evidence(menu, ROOT, manifest)
    menu_mutations = [dict(menu, status='failed'), dict(menu, rom_sha256='0'*64),
                      dict(menu, checks=[]), dict(menu, controller_only=False),
                      dict(menu, checks=menu['checks'][:1]), dict(menu, captures={}),
                      dict(menu, controller_actions=menu['controller_actions'][:-1])]
    altered = copy.deepcopy(menu)
    altered['captures']['arcade']['p1']['capture'] = 'missing.png'
    menu_mutations.append(altered)
    altered = copy.deepcopy(menu)
    altered['captures']['training']['arenas'][0]['mean_channel_delta'] += 1
    menu_mutations.append(altered)
    altered = copy.deepcopy(menu)
    altered['native_preservation']['pixel_difference_above_footer'] = 1
    menu_mutations.append(altered)
    altered = copy.deepcopy(menu)
    altered['asset_preservation']['files']['assets/generated/arenas_pal.bin']['sha256'] = '0'*64
    menu_mutations.append(altered)
    altered = copy.deepcopy(menu)
    altered['controller_actions'][0]['screen'] = 4
    menu_mutations.append(altered)
    altered = copy.deepcopy(menu)
    altered['asset_preservation']['baseline_ref'] = 'HEAD'
    menu_mutations.append(altered)
    for altered in menu_mutations:
        expect_package_error(lambda: PACKAGE.validate_menu_evidence(altered, ROOT, manifest),
                             'stale or malformed menu footer proof')
    check_menu_input_mutations(menu, manifest)

    authoring = json.loads((ROOT/'docs/authoring-guards-report.json').read_bytes())
    PACKAGE.validate_authoring_evidence(authoring, ROOT, manifest)
    altered_run = copy.deepcopy(authoring)
    altered_run['runs'][1]['arguments'] = ['tools/test_authoring_guards.py']
    altered_source = copy.deepcopy(authoring)
    altered_source['source_sha256']['tools/fighter_assets.py'] = '0'*64
    altered_inventory = copy.deepcopy(authoring)
    altered_inventory['producer_sha256'].pop('tools/release_evidence.py')
    altered_producer = copy.deepcopy(authoring)
    altered_producer['producer_sha256']['tools/check_authoring_guards.py'] = '0'*64
    for altered in (dict(authoring, rom_sha256='0'*64), dict(authoring, source_commit='0'*40),
                    dict(authoring, runs=[]), altered_run, altered_source,
                    altered_inventory, altered_producer, dict(authoring, producer_commit='0'*40)):
        expect_package_error(lambda: PACKAGE.validate_authoring_evidence(altered, ROOT, manifest),
                             'stale or malformed authoring guard proof')

    with tempfile.TemporaryDirectory(dir=ROOT/'build/package-audit') as temporary:
        sandbox = Path(temporary)
        record_name = f"docs/audio-listening-v{manifest['version']}.json"
        original = json.loads((ROOT/record_name).read_bytes())
        for relative in (record_name, 'docs/champion-audio-report.json', original['archive']['file']):
            target = sandbox/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/relative, target)
        PACKAGE.validate_listening_record(sandbox, manifest)
        changed_archive = dict(original, archive=dict(original['archive'], sha256='0'*64))
        for altered in (dict(original, human_listening_approved=True),
                        dict(original, source_report_sha256='0'*64), changed_archive, None):
            (sandbox/record_name).write_text(json.dumps(altered))
            expect_package_error(lambda: PACKAGE.validate_listening_record(sandbox, manifest),
                                 'stale or falsely approved listening archive')

    names = {'README.md', 'qa/stages.json', 'RELEASE.md', 'RELEASE-v0.11.0.md'}
    rendered = PACKAGE.offline_markdown_text(
        '[local](README.md)\n'
        '[stage](stage-test-report.json)\n'
        '[art](../assets/source.png)\n'
        '![image](../assets/image.png)\n'
        '[current](RELEASE-v0.11.0.md)\n'
        '[history](RELEASE-v0.9.0.md)\n'
        '[web](https://example.test/release)\n',
        'OBJ-BUDGET.md',
        names,
    )
    check('[local](README.md)' in rendered, 'existing offline link changed')
    check('[stage](qa/stages.json)' in rendered, 'offline link alias missing')
    check('[art](' not in rendered and 'source-only: ../assets/source.png' in rendered,
          'source-only link was not made honest')
    check('[web](https://example.test/release)' in rendered,
          'external link changed')
    check('[current](RELEASE.md)' in rendered,
          'current versioned release link did not map to offline note')
    check('history (source-only: RELEASE-v0.9.0.md)' in rendered,
          'historical release link incorrectly points at current release')
    check('image (source-only: ../assets/image.png)' in rendered and '![' not in rendered,
          'missing image link leaves broken image markup')
    check(not PACKAGE.missing_offline_links(rendered, 'OBJ-BUDGET.md', names),
          'rendered document still has an unresolved offline link')
    print('package-audit mutation checks passed')


if __name__ == '__main__':
    main()
