@echo off
title Building WISPAR FLOW EXE
cd /d "%~dp0"

echo =========================================
echo   Building WISPAR FLOW Standalone EXE
echo =========================================
echo.

pyinstaller --onefile ^
  --windowed ^
  --name "WISPAR_FLOW" ^
  --add-data "models;models" ^
  --hidden-import "win32clipboard" ^
  --hidden-import "sounddevice" ^
  --hidden-import "whisper" ^
  --collect-all whisper ^
  --collect-all torch ^
  run.py

if %errorlevel% equ 0 (
    echo.
    echo =========================================
    echo   SUCCESS! EXE built at:
    echo   dist\WISPAR_FLOW.exe
    echo =========================================
    echo.
    echo NOTE: The first launch will download the
    echo AI model (72MB) - internet required.
) else (
    echo.
    echo BUILD FAILED. Check errors above.
)

pause
