@echo off
echo 🌱 EcoAI Installation Script
echo ===========================
echo.
echo This script will install EcoAI and its dependencies.
echo.
echo Press any key to continue...
pause >nul

powershell -ExecutionPolicy Bypass -File "install_and_test.ps1"

echo.
echo Installation completed. Press any key to exit...
pause >nul 