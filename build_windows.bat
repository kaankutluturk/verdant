@echo off
setlocal

echo Building Verdant Windows .exe (PyInstaller)

where pyinstaller >nul 2>nul
if %errorlevel% neq 0 (
  echo PyInstaller not found. Installing...
  pip install pyinstaller || goto :error
)

REM Clean previous builds
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

REM Build CLI executable
pyinstaller --noconfirm ^
  --onefile ^
  --name Verdant ^
  --add-data "presets.json;." ^
  verdant.py || goto :error

REM Optional: Build GUI executable
pyinstaller --noconfirm ^
  --onefile ^
  --name VerdantGUI ^
  --add-data "presets.json;." ^
  verdant_gui.py || goto :error

echo.
echo Build complete. Check the dist\ folder for Verdant.exe and VerdantGUI.exe
goto :eof

:error
echo Build failed.
exit /b 1 