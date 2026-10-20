$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot 'setup.ps1') -EmulatorOnly
$emulatorPath = Join-Path $projectRoot '.tools/snes9x/snes9x-x64.exe'
$configPath = Join-Path $projectRoot '.tools/snes9x/snes9x.conf'
if (-not (Test-Path -LiteralPath $configPath)) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'snes9x.conf') -Destination $configPath
}
$romPath = Join-Path $projectRoot 'dist/abaqus-after-hours.sfc'
if (-not (Test-Path -LiteralPath $romPath)) { throw 'Build the ROM first with Build.cmd.' }
# This is the interactive game window requested by the player.
Start-Process -FilePath $emulatorPath -ArgumentList ('"'+$romPath+'"') -WorkingDirectory (Split-Path $emulatorPath) -WindowStyle Normal
