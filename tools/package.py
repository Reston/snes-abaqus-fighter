"""Package the tested ROM with the official Windows emulator for offline play."""
from pathlib import Path
import hashlib, json, zipfile
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'dist/manifest.json').read_text())
report=json.loads((ROOT/'docs/test-report.json').read_text())
assert report['rom_sha256']==manifest['sha256'],'Run tests on the current ROM before packaging.'
archive=ROOT/'dist/Abaqus-After-Hours-v0.1.0-Windows.zip'
files={
 'abaqus-after-hours.sfc':ROOT/'dist/abaqus-after-hours.sfc',
 'emulator/snes9x-x64.exe':ROOT/'.tools/snes9x/snes9x-x64.exe',
 'emulator/LICENSE':ROOT/'.tools/snes9x/LICENSE',
 'emulator/snes9x.conf':ROOT/'tools/snes9x.conf',
 'README.md':ROOT/'docs/PLAYER-GUIDE.md',
 'CREDITS.md':ROOT/'docs/CREDITS.md',
 'manifest.json':ROOT/'dist/manifest.json',
 'ART-DIRECTION.md':ROOT/'docs/ART-DIRECTION.md',
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
