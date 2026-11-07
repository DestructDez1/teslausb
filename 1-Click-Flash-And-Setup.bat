@echo off
title TeslaUSB Setup Studio
cd /d "%~dp0"

:: Check for Administrator privileges so direct USB flashing works
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting Administrator privileges for USB block flashing...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~dp01-Click-Flash-And-Setup.bat\"\"' -Verb RunAs"
    exit /b
)

echo ========================================================
echo   TeslaUSB Setup Studio (In-Browser Flasher ^& Config)
echo ========================================================
echo.
echo Starting server and opening your browser...
echo http://localhost:8000
echo.
echo Keep this window open while using Setup Studio.
echo Press Ctrl+C to close when done.
echo.

python "%~dp0setup-studio\server.py"
pause
