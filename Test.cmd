@echo off
cd /d "%~dp0"
".tools\python\python.exe" "tools\test_rom.py"
if errorlevel 1 pause
