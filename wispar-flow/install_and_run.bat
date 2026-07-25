@echo off
title WISPAR FLOW - Setup
cd /d "%~dp0"

echo =========================================
echo   WISPAR FLOW - Auto Installer
echo =========================================
echo.
echo  Step 1: Installing dependencies...
echo.

python -m pip install --upgrade pip 2>nul
pip install openai-whisper sounddevice numpy pywin32 pystray Pillow

if %errorlevel% neq 0 (
    echo.
    echo  FAILED to install packages!
    echo  Make sure Python is installed:
    echo  https://www.python.org/downloads/
    pause
    exit /b 1
)

echo.
echo  Step 2: Starting WISPAR FLOW...
echo.
echo =========================================
echo   HOW TO USE:
echo   1. Press Ctrl+Shift+Space to START recording
echo   2. Speak naturally into your microphone
echo   3. Press Ctrl+Shift+Space to STOP and paste
echo =========================================
echo.

python run.py

echo.
echo  WISPAR FLOW has stopped.
pause
