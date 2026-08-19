@echo off
setlocal
title Genesix - Install Dependencies
cd /d "%~dp0"
echo ================================================
echo   GENESIX - INSTALL DEPENDENCIES
echo ================================================
echo.
echo Checking Python...
py -3 --version
if errorlevel 1 (
    echo Python 3 is not available through the Windows py launcher.
    echo Install Python 3.10+ and enable the "Add Python to PATH" option.
    pause
    exit /b 1
)
echo.
echo Installing Python packages...
py -3 -m pip install -r requirements.txt
if errorlevel 1 (
    echo Package installation failed.
    pause
    exit /b 1
)
echo.
echo Installing Playwright browser components...
py -3 -m playwright install chromium
echo.
echo Installation finished.
pause
