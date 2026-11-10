@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-tools.ps1"
if errorlevel 1 (
    echo Installation failed. Check your internet connection and try again.
    pause
    exit /b 1
)
echo Components are ready. Start YtConvert.exe.
pause
