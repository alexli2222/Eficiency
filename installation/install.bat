@echo off
:: Eficiency — Windows installer (Command Prompt / batch)
:: Creates .venv at the project root if it doesn't exist, then pip-installs
:: all required packages.
::
:: Double-click to run, or execute from a terminal:
::   installation\install.bat

setlocal EnableDelayedExpansion

:: Resolve project root (one level up from the installation\ folder)
set "SCRIPT_DIR=%~dp0"
:: Strip trailing backslash
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%I in ("%SCRIPT_DIR%") do set "PROJECT_ROOT=%%~dpI"
:: Strip trailing backslash
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"
set "VENV_DIR=%PROJECT_ROOT%\.venv"

echo Eficiency installer
echo Project root : %PROJECT_ROOT%
echo Virtual env  : %VENV_DIR%
echo.

:: ── Create venv if absent ──────────────────────────────────────────────────
if not exist "%VENV_DIR%\" (
    echo [1/3] Creating virtual environment...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        echo        Make sure Python is installed and on your PATH.
        pause
        exit /b 1
    )
    echo       Done.
) else (
    echo [1/3] Virtual environment already exists, skipping creation.
)

:: ── Activate ───────────────────────────────────────────────────────────────
echo [2/3] Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Could not activate virtual environment.
    pause
    exit /b 1
)

:: ── Install packages ───────────────────────────────────────────────────────
echo [3/3] Installing packages...
pip install --upgrade pip
pip install customtkinter pynput Pillow
if errorlevel 1 (
    echo ERROR: pip install failed.
    pause
    exit /b 1
)

echo.
echo Installation complete.
echo To run Eficiency:
echo   %VENV_DIR%\Scripts\activate.bat
echo   python %PROJECT_ROOT%\main.py
echo.
pause
