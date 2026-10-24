param([switch]$ValidateOnly)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$cartridge = & (Join-Path $PSScriptRoot 'validate_cartridge.ps1') -ProjectRoot $projectRoot | ConvertFrom-Json
if ($ValidateOnly) { $cartridge | ConvertTo-Json; return }
Write-Host ('Starting Abaqus: After Hours v' + $cartridge.Version)
& (Join-Path $PSScriptRoot 'setup.ps1') -EmulatorOnly
$emulatorPath = Join-Path $projectRoot '.tools/snes9x/snes9x-x64.exe'
$configPath = Join-Path $projectRoot '.tools/snes9x/snes9x.conf'
if (-not (Test-Path -LiteralPath $configPath)) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'snes9x.conf') -Destination $configPath
}
$romPath = $cartridge.RomPath
# This is the interactive game window requested by the player.
Start-Process -FilePath $emulatorPath -ArgumentList ('"'+$romPath+'"') -WorkingDirectory (Split-Path $emulatorPath) -WindowStyle Normal
