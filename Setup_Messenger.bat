@echo off
setlocal
title Genesix - Messenger Setup
cd /d "%~dp0"
echo ================================================
echo   GENESIX - MESSENGER SETUP
echo ================================================
echo.
echo Complete Facebook/Messenger verification in Brave.
echo.
py -3 "class_announcement_agent.py" setup
echo.
pause
