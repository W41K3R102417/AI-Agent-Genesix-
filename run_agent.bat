@echo off
setlocal
title Genesix - Live Run
cd /d "%~dp0"
echo ================================================
echo   GENESIX - LIVE RUN
echo ================================================
echo.
py -3 "class_announcement_agent.py" run
echo.
pause
