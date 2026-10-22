"""Headless mutation checks for package pins and preflight, including python -O."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
import importlib.util


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

    valid = {'rom_sha256': 'a' * 64, 'status': 'passed', 'passed': 1,
             'checks': [{'passed': True}]}
    PACKAGE.validate_suite(valid, 'fixture', 'a' * 64)
    for altered in (dict(valid, rom_sha256='b' * 64),
                    dict(valid, checks=[], passed=0),
                    dict(valid, checks=[{'passed': False}]),
                    dict(valid, status='failed')):
        expect_package_error(lambda: PACKAGE.validate_suite(altered, 'fixture', 'a' * 64),
                             'stale, empty, incomplete or failed suite')

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
