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

REM Single unified executable (GUI by default, CLI with --cli)
pyinstaller --noconfirm ^
  --onefile ^
  --name VerdantApp ^
  --add-data "presets.json;." ^
  verdant_app.py || goto :error

echo.
echo Build complete. Check the dist\ folder for VerdantApp.exe
goto :eof

:error
echo Build failed.
exit /b 1 