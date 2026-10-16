@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_CMD="
where py >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=py -3"
if not defined PYTHON_CMD (
    where python >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD goto no_python

%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if errorlevel 1 goto old_python

if not exist ".venv\Scripts\python.exe" (
    echo First run: creating a private Python environment...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto setup_failed
)

".venv\Scripts\python.exe" -c "import chess, rich, prompt_toolkit, terchess" >nul 2>&1
if errorlevel 1 (
    echo First run: installing Terchess and its Python dependencies...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    if errorlevel 1 goto setup_failed
    ".venv\Scripts\python.exe" -m pip install .
    if errorlevel 1 goto setup_failed
)

echo Starting Terchess...
".venv\Scripts\python.exe" -m terchess
if errorlevel 1 goto app_failed
echo.
echo Terchess has exited.
pause
exit /b 0

:no_python
echo Python 3.10 or newer is required.
echo Install it from https://www.python.org/downloads/ and try again.
pause
exit /b 1

:old_python
echo Python 3.10 or newer is required. Please upgrade Python and try again.
pause
exit /b 1

:setup_failed
echo.
echo Setup failed. Check your internet connection and Python installation, then try again.
pause
exit /b 1

:app_failed
echo.
echo Terchess exited with an error. Please read the message above.
pause
exit /b 1
