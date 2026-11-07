@echo off
setlocal enabledelayedexpansion
title TeslaUSB - Push to GitHub

echo ===================================================
echo           TeslaUSB - GitHub Push Automation
echo ===================================================
echo.

cd /d "%~dp0"

:: 1. Check current git remote
for /f "tokens=2" %%i in ('git config --get remote.origin.url 2^>nul') do set CURRENT_ORIGIN=%%i
if "%CURRENT_ORIGIN%"=="" (
    for /f %%i in ('git config --get remote.origin.url 2^>nul') do set CURRENT_ORIGIN=%%i
)

echo Current remote origin: %CURRENT_ORIGIN%

:: Check if origin is still pointing to upstream marcone
echo %CURRENT_ORIGIN% | findstr /i "marcone/teslausb" >nul
if %errorlevel% equ 0 (
    echo.
    echo [!] Remote 'origin' is currently pointing to upstream marcone/teslausb (read-only).
    echo     We need to point 'origin' to your personal GitHub repository!
    echo.
    set /p REPO_URL="Enter your GitHub repository URL (e.g. https://github.com/DestructDez1/teslausb.git): "
    if "!REPO_URL!"=="" (
        set "REPO_URL=https://github.com/DestructDez1/teslausb.git"
    )
    
    :: Rename original to upstream so user can still pull updates
    git remote rename origin upstream >nul 2>&1
    git remote add origin !REPO_URL!
    echo [*] Configured 'origin' -> !REPO_URL!
    echo [*] Configured 'upstream' -> %CURRENT_ORIGIN%
    echo.
)

:: 2. Check for changes to commit
git status -s > "%TEMP%\git_status.tmp"
set HAS_CHANGES=0
for %%A in ("%TEMP%\git_status.tmp") do if %%~zA gtr 0 set HAS_CHANGES=1
del "%TEMP%\git_status.tmp" >nul 2>&1

if "%HAS_CHANGES%"=="1" (
    echo Uncommitted changes detected:
    git status -s
    echo.
    set /p COMMIT_MSG="Enter commit message (press ENTER for default timestamp): "
    if "!COMMIT_MSG!"=="" (
        for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set dt=%%I
        set "COMMIT_MSG=Update !dt:~0,4!-!dt:~4,2!-!dt:~6,2! !dt:~8,2!:!dt:~10,2!"
    )
    echo [*] Staging files and creating commit...
    git add -A
    git commit -m "!COMMIT_MSG!"
    echo.
) else (
    echo [OK] Working tree clean. Ready to push.
    echo.
)

:: 3. Push to GitHub
echo [*] Pushing branch main to GitHub...
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ===================================================
    echo    SUCCESS! Pushed all commits to GitHub.
    echo ===================================================
) else (
    echo.
    echo [!] Push failed or authentication required.
    echo     Make sure your repository exists on GitHub and you have write permissions.
)

echo.
pause

