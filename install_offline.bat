@echo off
REM ============================================
REM PumpForge3D Offline Installation Script
REM ============================================
REM For users without internet access

echo === PumpForge3D Offline Install ===
echo.

REM Check if virtual environment exists
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        echo Make sure Python 3.10+ is installed and in PATH.
        pause
        exit /b 1
    )
)

REM Activate and install from wheel files
echo Installing packages from whls folder...
call .venv\Scripts\activate.bat
pip install --no-index --find-links=whls -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Installation failed.
    echo Make sure all required wheel files are in the whls folder.
    pause
    exit /b 1
)

echo.
echo === Installation Complete ===
echo.
echo To run PumpForge3D:
echo   1. Activate: .venv\Scripts\activate.bat
echo   2. Run: python -m apps.PumpForge3D
echo.
pause
