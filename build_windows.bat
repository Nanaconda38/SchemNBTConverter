@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo  SchemNBTConverter - Windows build
echo ========================================
echo.

set "PYTHON_CMD="
python -c "import sys" >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=python"
if defined PYTHON_CMD goto :python_found

py -3 -c "import sys" >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=py -3"
if defined PYTHON_CMD goto :python_found

python3 -c "import sys" >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=python3"
if defined PYTHON_CMD goto :python_found

echo ERROR: Python was not found.
echo Install Python 3.10 or newer, then reopen this file.
echo The Microsoft Store version is supported.
goto :fail

:python_found
echo Using: %PYTHON_CMD%
%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 (
    echo ERROR: Python 3.10 or newer is required.
    goto :fail
)

if exist ".venv-win" if not exist ".venv-win\Scripts\python.exe" (
    echo Removing an incomplete virtual environment...
    rmdir /s /q ".venv-win"
)

if not exist ".venv-win\Scripts\python.exe" (
    echo Creating the Windows virtual environment...
    %PYTHON_CMD% -m venv ".venv-win"
    if errorlevel 1 (
        echo ERROR: Failed to create .venv-win.
        goto :fail
    )
)

set "VENV_PYTHON=%CD%\.venv-win\Scripts\python.exe"

echo Updating build tools...
"%VENV_PYTHON%" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto :dependency_fail

echo Installing dependencies...
"%VENV_PYTHON%" -m pip install -r "requirements-dev.txt"
if errorlevel 1 goto :dependency_fail

echo Running tests...
"%VENV_PYTHON%" -m pytest -q
if errorlevel 1 (
    echo ERROR: Tests failed. The executable was not built.
    goto :fail
)

echo Building the executable...
"%VENV_PYTHON%" -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name SchemNBTConverter ^
  --collect-all litemapy ^
  --collect-all nbtlib ^
  --collect-all tkinterdnd2 ^
  --paths src ^
  launcher.py

if errorlevel 1 goto :build_fail

echo.
echo SUCCESS: dist\SchemNBTConverter.exe was created.
echo.
pause
exit /b 0

:dependency_fail
echo.
echo ERROR: Dependency installation failed.
echo Check your internet connection and Python installation.
goto :fail

:build_fail
echo.
echo ERROR: PyInstaller failed to build the executable.
goto :fail

:fail
echo.
echo BUILD FAILED
pause
exit /b 1
