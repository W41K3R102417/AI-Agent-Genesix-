@echo off
setlocal
title Genesix - Test
cd /d "%~dp0"
echo ================================================
echo   GENESIX - TEST
echo ================================================
echo.
py -3 "class_announcement_agent.py" test
echo.
pause
