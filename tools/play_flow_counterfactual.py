"""Build a current-source feedback counterfactual without changing combat rules.

Only recovery/throw banner stores are removed. Menus, asset bytes, controller
cadence and every gameplay store stay current, so full-byte comparisons do not
confound older menu timing with the feedback feature under test.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from candidate_sources import snapshot
from asset_transaction import workspace_lock
from v025_contracts import symbols


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def patched(game, knockdown):
    if game.count('impactBannerCounter=2;') != 2:
        raise ValueError('Expected exactly the macro and pointer recovery classifications')
    line = '    impactBannerCounter=3;impactBannerCombo=0;impactBannerPending=1;impactSettle=1;\n'
    if knockdown.count(line) != 1:
        raise ValueError('Expected exactly one deferred throw-tech banner hook')
    return {'src/game.c': game.replace('impactBannerCounter=2;', 'impactBannerCounter=0;'),
            'src/knockdown.h': knockdown.replace(line, '')}


def validate(root, record):
    root = Path(root).resolve()
    if record.get('status') != 'passed' or record.get('source_sha256') != snapshot(root):
        raise ValueError('Counterfactual source identity differs')
    current = json.loads((root / 'dist/manifest.json').read_bytes())
    if record.get('candidate_rom_sha256') != current['sha256']:
        raise ValueError('Counterfactual was built for another cartridge')
    workspace = (root / record['workspace']).resolve()
    if not workspace.is_relative_to(root / 'build'):
        raise ValueError('Counterfactual workspace escapes ignored build')
    expected = patched((root / 'src/game.c').read_text(encoding='utf-8'),
                       (root / 'src/knockdown.h').read_text(encoding='utf-8'))
    for name, text in expected.items():
        if (workspace / name).read_text(encoding='utf-8') != text or record['patch_sha256'].get(name) != sha(text.encode()):
            raise ValueError('Counterfactual patch escapes its exact banner stores')
    for name, digest in record['source_sha256'].items():
        wanted = sha(expected[name].encode()) if name in expected else digest
        actual = sha((workspace / name).read_bytes().replace(b'\r\n', b'\n'))
        if actual != wanted:
            raise ValueError('Counterfactual dependency changed: ' + name)
    for name, digest in record['artifacts'].items():
        if sha((workspace / 'dist' / name).read_bytes()) != digest:
            raise ValueError('Retained counterfactual native artifact changed')
    before = symbols((workspace / 'dist/abaqus-after-hours.sym').read_bytes())
    after = symbols((root / 'dist/abaqus-after-hours.sym').read_bytes())
    ram = {name: address for name, address in after.items() if address < 0x2000 or 0x7e0000 <= address < 0x800000}
    if len(ram) < 1318 or any(before.get(name) != address for name, address in ram.items()):
        raise ValueError('Counterfactual changes the gameplay state addresses')
    if record.get('ram_addresses_preserved') != len(ram):
        raise ValueError('Counterfactual RAM count differs')
    return workspace / 'dist/abaqus-after-hours.sfc'


def prepare(root):
    root = Path(root).resolve()
    with workspace_lock(root, 'native-build.lock'):
        sources = snapshot(root)
        signature = sha(json.dumps(sources, sort_keys=True).encode())
        folder = root / 'build' / ('feedback-reference-' + signature[:16])
        report_path = folder / 'reference.json'
        if report_path.exists():
            record = json.loads(report_path.read_bytes())
            return validate(root, record), record
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
        changed = subprocess.check_output(['git', 'diff', '--name-only', 'HEAD', '--', 'src', 'tools', 'assets', 'dist', 'Build.cmd', 'Test.cmd', 'Play.cmd'], cwd=root, text=True)
        extra = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', 'src', 'tools', 'assets', 'dist'], cwd=root, text=True)
        if changed.strip() or extra.strip():
            raise ValueError('Commit the exact candidate source before deriving its counterfactual')
        folder.mkdir(exist_ok=True)
        archive = folder / 'source.zip'
        subprocess.run(['git', 'archive', '--format=zip', '--output=' + str(archive), commit], cwd=root, check=True)
        with zipfile.ZipFile(archive) as package:
            for item in package.infolist():
                if Path(item.filename).parts[0] not in ('src', 'tools', 'assets', 'dist', 'Build.cmd', 'Test.cmd', 'Play.cmd'):
                    continue
                target = (folder / item.filename).resolve()
                if not target.is_relative_to(folder):
                    raise ValueError('Counterfactual source entry escapes its workspace')
                package.extract(item, folder)
        subprocess.run(['cmd', '/d', '/c', 'mklink', '/J', str(folder / '.tools'), str(root / '.tools')],
                       cwd=root, check=True, capture_output=True)
        (folder / 'build').mkdir(exist_ok=True)
        shutil.copyfile(root / 'assets/generated/soundbank.h', folder / 'assets/generated/soundbank.h')
        shutil.copyfile(root / 'build/asset-cache-v1.json', folder / 'build/asset-cache-v1.json')
        patch = patched((root / 'src/game.c').read_text(encoding='utf-8'), (root / 'src/knockdown.h').read_text(encoding='utf-8'))
        for name, text in patch.items():
            (folder / name).write_text(text, encoding='utf-8', newline='\n')
        run = subprocess.run([sys.executable, str(folder / 'tools/build.py')], cwd=folder,
                             stdin=subprocess.DEVNULL, capture_output=True)
        (folder / 'build.log').write_bytes(run.stdout + run.stderr)
        if run.returncode:
            raise RuntimeError('Counterfactual native build failed: ' + str(folder / 'build.log'))
        for path in (root / 'assets/generated').iterdir():
            if path.is_file() and path.read_bytes() != (folder / 'assets/generated' / path.name).read_bytes():
                raise ValueError('Counterfactual changed an asset: ' + path.name)
        current = json.loads((root / 'dist/manifest.json').read_bytes())
        baseline = json.loads((folder / 'dist/manifest.json').read_bytes())
        ram = {name: address for name, address in symbols((root / 'dist/abaqus-after-hours.sym').read_bytes()).items()
               if address < 0x2000 or 0x7e0000 <= address < 0x800000}
        record = {'status': 'passed', 'scope': 'current-source banner-only counterfactual; no historical menu phase comparison',
                  'source_commit': commit, 'source_sha256': sources, 'candidate_rom_sha256': current['sha256'],
                  'baseline_rom_sha256': baseline['sha256'], 'workspace': folder.relative_to(root).as_posix(),
                  'patch_sha256': {name: sha(text.encode()) for name, text in patch.items()},
                  'ram_addresses_preserved': len(ram), 'all_generated_assets_exact': True,
                  'artifacts': {name: sha((folder / 'dist' / name).read_bytes()) for name in
                                ('abaqus-after-hours.sfc', 'abaqus-after-hours.sym', 'manifest.json')}}
        validate(root, record)
        report_path.write_bytes((json.dumps(record, indent=2) + '\n').encode())
        return folder / 'dist/abaqus-after-hours.sfc', record
