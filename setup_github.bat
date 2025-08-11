@echo off
echo 🚀 Lumina GitHub Setup
echo =====================
echo.
echo This script will help you push Lumina to GitHub.
echo.
echo Press any key to continue...
pause >nul

powershell -ExecutionPolicy Bypass -File "setup_github.ps1"

echo.
echo GitHub setup completed. Press any key to exit...
pause >nul 