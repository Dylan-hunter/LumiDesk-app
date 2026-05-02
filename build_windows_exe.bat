@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo        LumiDesk Windows EXE Builder
echo ============================================

echo [1/5] Checking Python...
py -3 --version >nul 2>nul
if errorlevel 1 (
  echo Python 3 not found. Please install Python 3.11 or 3.12 first.
  pause
  exit /b 1
)

echo [2/5] Creating virtual environment...
if not exist .venv (
  py -3 -m venv .venv
  if errorlevel 1 (
    echo Failed to create virtual environment.
    pause
    exit /b 1
  )
)

call .venv\Scripts\activate.bat
if errorlevel 1 (
  echo Failed to activate virtual environment.
  pause
  exit /b 1
)

echo [3/5] Upgrading pip...
python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
  echo Failed to upgrade pip.
  pause
  exit /b 1
)

echo [4/5] Installing dependencies...
pip install -r requirements.txt pyinstaller
if errorlevel 1 (
  echo Failed to install dependencies.
  pause
  exit /b 1
)

echo [5/5] Building EXE...
pyinstaller --clean --noconfirm LumiDesk.spec
if errorlevel 1 (
  echo Build failed.
  pause
  exit /b 1
)

echo.
echo Build succeeded!
echo EXE location:
echo %cd%\dist\LumiDesk.exe
echo.
if exist dist\LumiDesk.exe explorer /select,dist\LumiDesk.exe
pause
endlocal
