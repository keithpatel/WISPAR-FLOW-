@echo off
title WISPAR FLOW - Self Test
cd /d "%~dp0"

echo =========================================
echo   WISPAR FLOW - Self Test
echo =========================================
echo.
echo This will test: microphone, model, and paste
echo.
echo Press Enter to start test...
pause >nul

python run.py --test

echo.
echo Test complete. Check wispar_flow.log for details.
echo.
pause
