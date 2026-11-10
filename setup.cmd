@echo off
cd /d "%~dp0"
python -c "import sys; sys.exit(sys.version_info < (3, 10))"
if errorlevel 1 goto fail
python -m pip install --upgrade --target ".deps" -r requirements.txt
if errorlevel 1 goto fail
powershell.exe -NoProfile -File "%~dp0setup-tools.ps1"
if errorlevel 1 goto fail
echo Setup complete. Run start.cmd.
pause
exit /b 0

:fail
echo Setup failed. Check Python, internet access and the message above.
pause
exit /b 1
