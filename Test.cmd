@echo off
cd /d "%~dp0"
".tools\python\python.exe" "tools\test_rom.py"
if errorlevel 1 goto failed
".tools\python\python.exe" "tools\test_characters.py"
if errorlevel 1 goto failed
".tools\python\python.exe" "tools\test_presentation.py"
if errorlevel 1 goto failed
".tools\python\python.exe" "tools\test_inputs.py"
if errorlevel 1 goto failed
".tools\python\python.exe" "tools\test_stages.py"
if errorlevel 1 goto failed
".tools\python\python.exe" "tools\test_training.py"
if errorlevel 1 goto failed
exit /b 0
:failed
if not "%ABAQUS_HEADLESS%"=="1" pause
exit /b 1
