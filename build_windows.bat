@echo off
setlocal

REM Detect Python
set PYTHON=python
%PYTHON% --version >nul 2>nul
if %errorlevel% neq 0 (
  set PYTHON=py
  %PYTHON% --version >nul 2>nul || (echo Python not found & goto :error)
)

echo Building Verdant Windows .exe (PyInstaller)

REM Ensure dependencies
%PYTHON% -m pip install --upgrade pip || goto :error
%PYTHON% -m pip install -r requirements.txt pyinstaller || goto :error

REM Ensure icon exists
if not exist assets\icon\verdant.ico (
  echo Generating application icon...
  %PYTHON% tools\make_icon.py || goto :error
)

REM Clean previous builds
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

REM Build main GUI app (single EXE)
%PYTHON% -m PyInstaller --noconfirm ^
  --onefile ^
  --name VerdantApp ^
  --windowed ^
  --add-data "presets.json;." ^
  --collect-all llama_cpp ^
  --icon assets/icon/verdant.ico ^
  verdant_app.py || goto :error

REM Build updater (console EXE)
%PYTHON% -m PyInstaller --noconfirm ^
  --onefile ^
  --name VerdantUpdater ^
  --console ^
  --icon assets/icon/verdant.ico ^
  tools/verdant_updater.py || goto :error

echo.
echo Build complete. Check the dist\ folder for VerdantApp.exe and VerdantUpdater.exe
goto :eof

:error
echo Build failed.
exit /b 1 