@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "tools\setup.ps1"
if errorlevel 1 goto failed
".tools\python\python.exe" "tools\build.py" %*
if errorlevel 1 goto failed
exit /b 0
:failed
pause
exit /b 1
