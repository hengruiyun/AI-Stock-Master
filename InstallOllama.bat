@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo Install Ollama
echo ========================================
echo.
set UV_PYTHON_INSTALL_MIRROR=https://gh-proxy.com/https://github.com/indygreg/python-build-standalone/releases/download
set UV_DEFAULT_INDEX=https://mirrors.aliyun.com/pypi/simple

rem Check if Python 3.10+ is available
echo [1/5] Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo  Python not found in PATH
    goto :setup_venv
)

rem Get Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Found Python version: %PYTHON_VERSION%

rem Extract major and minor version numbers
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set MAJOR=%%a
    set MINOR=%%b
)

rem Check if version is 3.10 or higher
if %MAJOR% LSS 3 goto :setup_venv
if %MAJOR% EQU 3 if %MINOR% LSS 10 goto :setup_venv

echo  Python %PYTHON_VERSION% meets requirements (3.10+)
goto :check_venv

:setup_venv
echo [2/5] Setting up Python 3.10 virtual environment...
if not exist "uv.exe" (
    echo  uv.exe not found in current directory
    echo Please ensure uv.exe is available
    pause
    exit /b 1
)

echo Creating virtual environment with Python 3.10...
uv.exe venv --python=3.10
if errorlevel 1 (
    echo  Failed to create virtual environment
    pause
    exit /b 1
)
echo  Virtual environment created successfully
goto :install_deps

:check_venv
echo [2/5] Checking virtual environment...
if exist ".venv" (
    echo  Virtual environment already exists
) else (
    echo Creating virtual environment...
    if not exist "uv.exe" (
        echo  uv.exe not found in current directory
        pause
        exit /b 1
    )
    uv.exe venv --python=3.10
    if errorlevel 1 (
        echo  Failed to create virtual environment
        pause
        exit /b 1
    )
    echo  Virtual environment created successfully
)

:install_deps
echo [3/5] Installing dependencies...
if not exist "requireOlla.txt" (
    echo  requireOlla.txt not found
    pause
    exit /b 1
)

echo Installing packages from requireOlla.txt...
uv.exe pip install -r requireOlla.txt
if errorlevel 1 (
    echo  Failed to install dependencies
    pause
    exit /b 1
)
echo  Dependencies installed successfully

:rename_pyproject
echo [4/5] Checking pyproject.toml...
if exist "pyproject.toml" (
    echo Renaming pyproject.toml to pyproject-old.toml...
    ren "pyproject.toml" "pyproject-old.toml"
    if errorlevel 1 (
        echo  Failed to rename pyproject.toml
        pause
        exit /b 1
    )
    echo  pyproject.toml renamed to pyproject-old.toml
) else (
    echo   pyproject.toml not found, skipping rename
)






echo Checking Ollama installation...

REM Check if Ollama is in PATH
where ollama >nul 2>&1
if %errorlevel% equ 0 (
    echo Ollama found in PATH.
    echo Current Ollama location:
    where ollama
    goto :endOllamaSetup
)

echo Ollama not found in PATH.
echo Adding Ollama to PATH...

REM Define Ollama installation path
set "OLLAMA_PATH=%userprofile%\AppData\Local\Programs\Ollama"

REM Check if Ollama directory exists
if not exist "%OLLAMA_PATH%" (
    echo Error: Ollama directory not found at %OLLAMA_PATH%
    echo Please install Ollama first.
    REM pause
    goto :endOllamaSetup
)

REM Check if Ollama executable exists
if not exist "%OLLAMA_PATH%\ollama.exe" (
    echo Error: ollama.exe not found in %OLLAMA_PATH%
    echo Please check your Ollama installation.
    REM pause
    goto :endOllamaSetup
)

REM Get current PATH
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "CURRENT_PATH=%%b"

REM Check if Ollama path is already in PATH
echo %CURRENT_PATH% | findstr /i "%OLLAMA_PATH%" >nul
if %errorlevel% equ 0 (
    echo Ollama path already exists in PATH.
    goto :endOllamaSetup
)

REM Add Ollama to PATH
if defined CURRENT_PATH (
    set "NEW_PATH=%CURRENT_PATH%;%OLLAMA_PATH%"
) else (
    set "NEW_PATH=%OLLAMA_PATH%"
)

Set PATH=%PATH%;%OLLAMA_PATH%

REM Update PATH in registry
reg add "HKCU\Environment" /v PATH /t REG_EXPAND_SZ /d "%NEW_PATH%" /f >nul
if %errorlevel% equ 0 (
    echo Successfully added Ollama to PATH.
    echo New PATH: %NEW_PATH%
    echo Please restart your command prompt or reboot to apply changes.
) else (
    echo Error: Failed to update PATH.
    echo Please run this script as administrator.
)

:endOllamaSetup

uv run check_display.py
uv run check_ollama_env.py  gemma3:1b