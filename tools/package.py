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
 'PROPORTIONS.md':ROOT/'docs/PROPORTIONS.md',
 'MENU-DESIGN.md':ROOT/'docs/MENU-DESIGN.md',
 'RELEASE.md':ROOT/'docs/RELEASE-v0.4.md',
 'LICENSE':ROOT/'LICENSE',
 'licenses/PVSnesLib.txt':ROOT/'licenses/PVSnesLib.txt',
 'licenses/SNESMod.txt':ROOT/'licenses/SNESMod.txt',
 'licenses/Snes9x.txt':ROOT/'licenses/Snes9x.txt',
}
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,path in files.items():z.write(path,name)
    z.writestr('Play.cmd','@echo off\r\ncd /d "%~dp0emulator"\r\nstart "Abaqus After Hours" "snes9x-x64.exe" "..\\abaqus-after-hours.sfc"\r\n')
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
(ROOT/'dist/release-sha256.txt').write_text(digest+'  '+archive.name+'\n')
print('Packaged',archive.name,archive.stat().st_size,'bytes')
