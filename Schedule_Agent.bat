@echo off
setlocal
title Genesix - Schedule
cd /d "%~dp0"
echo ================================================
echo   GENESIX - SCHEDULER
echo ================================================
echo.
py -3 "class_announcement_agent.py" schedule
echo.
pause
