@echo off
title WISPAR FLOW
cd /d "%~dp0"

echo =========================================
echo   WISPAR FLOW - Voice Dictation Tool
echo =========================================
echo.
echo  Hotkey: Ctrl+Shift+Space to start/stop
echo  Look for green circle in system tray
echo  Check wispar_flow.log for details
echo.
echo  Press Ctrl+C to exit
echo =========================================
echo.

.venv\Scripts\python run.py
pause
