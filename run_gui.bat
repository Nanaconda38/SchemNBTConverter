@echo off
setlocal EnableExtensions
cd /d "%~dp0"

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

echo ERROR: Python 3.10 or newer was not found.
echo Install Python, then run this launcher again.
pause
exit /b 1

:python_found
if exist ".venv-win" if not exist ".venv-win\Scripts\python.exe" rmdir /s /q ".venv-win"

if not exist ".venv-win\Scripts\python.exe" (
    echo First launch: creating the virtual environment...
    %PYTHON_CMD% -m venv ".venv-win"
    if errorlevel 1 goto :setup_fail
)

set "VENV_PYTHON=%CD%\.venv-win\Scripts\python.exe"
set "VENV_PYTHONW=%CD%\.venv-win\Scripts\pythonw.exe"

"%VENV_PYTHON%" -c "import litemapy, nbtlib" >nul 2>&1
if errorlevel 1 (
    echo Installing application dependencies...
    "%VENV_PYTHON%" -m pip install --upgrade pip
    if errorlevel 1 goto :setup_fail
    "%VENV_PYTHON%" -m pip install -r "requirements.txt"
    if errorlevel 1 goto :setup_fail
)

set "PYTHONPATH=%CD%\src"
if exist "%VENV_PYTHONW%" (
    start "" "%VENV_PYTHONW%" -m schem_nbt_converter --gui
) else (
    "%VENV_PYTHON%" -m schem_nbt_converter --gui
)
exit /b 0

:setup_fail
echo.
echo ERROR: The application could not be prepared.
echo Check your internet connection and Python installation.
pause
exit /b 1
