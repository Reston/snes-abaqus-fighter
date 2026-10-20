"""Package the tested ROM with the official Windows emulator for offline play."""
from pathlib import Path
import hashlib, json, zipfile
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'dist/manifest.json').read_text())
report=json.loads((ROOT/'docs/test-report.json').read_text())
assert report['rom_sha256']==manifest['sha256'],'Run tests on the current ROM before packaging.'
roster_report=json.loads((ROOT/'docs/character-test-report.json').read_text())
assert roster_report['status']=='passed','Run the complete roster suite before packaging.'
assert roster_report['rom_sha256']==manifest['sha256'],'Roster verification must match the current ROM.'
presentation_report=json.loads((ROOT/'docs/presentation-test-report.json').read_text())
assert presentation_report['status']=='passed','Run the complete presentation suite before packaging.'
assert presentation_report['rom_sha256']==manifest['sha256'],'Presentation verification must match the current ROM.'
input_report=json.loads((ROOT/'docs/input-test-report.json').read_text())
assert input_report['status']=='passed','Run the focused input suite before packaging.'
assert input_report['rom_sha256']==manifest['sha256'],'Input verification must match the current ROM.'
stage_report=json.loads((ROOT/'docs/stage-test-report.json').read_text())
assert stage_report['status']=='passed','Run the stage and OBJ-budget suite before packaging.'
assert stage_report['rom_sha256']==manifest['sha256'],'Stage verification must match the current ROM.'
for evidence in (report,roster_report,presentation_report,input_report,stage_report):
    assert evidence.get('status','passed')=='passed','A verification suite failed.'
    assert evidence['passed']==len(evidence['checks']) and evidence['passed']>0,'Incomplete verification report.'
    assert all(check['passed'] for check in evidence['checks']),'A reported check failed.'
compatibility_report=json.loads((ROOT/'docs/compatibility-test-report.json').read_text())
assert compatibility_report['status']=='passed','Run the independent-engine smoke check before packaging.'
assert compatibility_report['rom']['sha256']==manifest['sha256'],'Compatibility smoke evidence must match the current ROM.'
assert hashlib.sha256((ROOT/'dist/abaqus-after-hours.sfc').read_bytes()).hexdigest()==manifest['sha256'],'ROM differs from its manifest.'
archive=ROOT/'dist'/('Abaqus-After-Hours-v'+manifest['version']+'-Windows.zip')
files={
 'abaqus-after-hours.sfc':ROOT/'dist/abaqus-after-hours.sfc',
 'emulator/snes9x-x64.exe':ROOT/'.tools/snes9x/snes9x-x64.exe',
 'emulator/LICENSE':ROOT/'.tools/snes9x/LICENSE',
 'emulator/snes9x.conf':ROOT/'tools/snes9x.conf',
 'README.md':ROOT/'docs/PLAYER-GUIDE.md',
 'CREDITS.md':ROOT/'docs/CREDITS.md',
 'manifest.json':ROOT/'dist/manifest.json',
 'ART-DIRECTION.md':ROOT/'docs/ART-DIRECTION.md',
 'CHARACTERS.md':ROOT/'docs/CHARACTERS.md',
 'qa/gameplay.json':ROOT/'docs/test-report.json',
 'qa/characters.json':ROOT/'docs/character-test-report.json',
 'qa/presentation.json':ROOT/'docs/presentation-test-report.json',
 'qa/inputs.json':ROOT/'docs/input-test-report.json',
 'qa/stages.json':ROOT/'docs/stage-test-report.json',
 'qa/stage-dynamics.json':ROOT/'assets/generated/stage-dynamics.json',
 'qa/compatibility.json':ROOT/'docs/compatibility-test-report.json',
 'COMPATIBILITY.md':ROOT/'docs/COMPATIBILITY.md',
 'ANIMATION-CONTRACT.md':ROOT/'docs/ANIMATION-CONTRACT.md',
 'COMBAT-ANIMATION-CONTRACT.md':ROOT/'docs/COMBAT-ANIMATION-CONTRACT.md',
 'ANIMATION-PIPELINE.md':ROOT/'docs/ANIMATION-PIPELINE.md',
 'PUBLIC-RELEASE.md':ROOT/'docs/PUBLIC-RELEASE.md',
 'BALANCE-AUDIT-v0.6.md':ROOT/'docs/BALANCE-AUDIT-v0.6.md',
 'PROPORTIONS.md':ROOT/'docs/PROPORTIONS.md',
 'MENU-DESIGN.md':ROOT/'docs/MENU-DESIGN.md',
 'OBJ-BUDGET.md':ROOT/'docs/OBJ-BUDGET.md',
 'RELEASE.md':ROOT/f"docs/RELEASE-v{manifest['version']}.md",
 'LICENSE':ROOT/'LICENSE',
 'licenses/PVSnesLib.txt':ROOT/'licenses/PVSnesLib.txt',
 'licenses/SNESMod.txt':ROOT/'licenses/SNESMod.txt',
 'licenses/Snes9x.txt':ROOT/'licenses/Snes9x.txt',
}
def write_entry(package,name,data):
    # Source mtimes and the host OS must not change the archive checksum.
    entry=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0))
    entry.create_system=0
    entry.external_attr=0x20
    entry.compress_type=zipfile.ZIP_DEFLATED
    package.writestr(entry,data,compresslevel=9)

with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,path in files.items():write_entry(z,name,path.read_bytes())
    write_entry(z,'Play.cmd',b'@echo off\r\ncd /d "%~dp0emulator"\r\nstart "Abaqus After Hours" "snes9x-x64.exe" "..\\abaqus-after-hours.sfc"\r\n')
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
(ROOT/'dist/release-sha256.txt').write_text(digest+'  '+archive.name+'\n')
print('Packaged',archive.name,archive.stat().st_size,'bytes')
