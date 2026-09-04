@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if not errorlevel 1 (
    py -3 launcher.py
    if errorlevel 1 goto :error
    exit /b 0
)

where python >nul 2>nul
if not errorlevel 1 (
    python launcher.py
    if errorlevel 1 goto :error
    exit /b 0
)

echo Python 3 is not installed or not in your PATH.
echo Download and install it from: https://www.python.org/downloads/
echo Make sure to check "Add Python to PATH" during installation.
echo.
pause
exit /b 1

:error
echo.
pause
exit /b 1
