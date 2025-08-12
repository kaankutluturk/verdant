# Verdant Installation and Test Script for Windows
# Run this in PowerShell as Administrator if needed

Write-Host "✨ Verdant Installation and Test Script" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green

# Check if Python is installed
Write-Host "`n🔍 Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
    } else {
        throw "Python not found"
    }
} catch {
    Write-Host "❌ Python not found or not in PATH" -ForegroundColor Red
    Write-Host "`n📥 Please install Python 3.8+ from:" -ForegroundColor Yellow
    Write-Host "   https://www.python.org/downloads/" -ForegroundColor Cyan
    Write-Host "   Make sure to check 'Add Python to PATH' during installation" -ForegroundColor Cyan
    Write-Host "`n🔄 After installing Python, restart PowerShell and run this script again" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if pip is available
Write-Host "`n🔍 Checking pip..." -ForegroundColor Yellow
try {
    $pipVersion = pip --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ pip found: $pipVersion" -ForegroundColor Green
    } else {
        throw "pip not found"
    }
} catch {
    Write-Host "❌ pip not found" -ForegroundColor Red
    Write-Host "   This usually means Python wasn't installed correctly" -ForegroundColor Yellow
    exit 1
}

# Install dependencies
Write-Host "`n📦 Installing dependencies..." -ForegroundColor Yellow
try {
    pip install -r requirements.txt
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Dependencies installed successfully" -ForegroundColor Green
    } else {
        throw "Failed to install dependencies"
    }
} catch {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test the installation
Write-Host "`n🧪 Testing Verdant installation..." -ForegroundColor Yellow
try {
    python test_verdant.py
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n🎉 All tests passed! Verdant is ready to use." -ForegroundColor Green
        Write-Host "`n📖 Next steps:" -ForegroundColor Cyan
        Write-Host "   1. Run: python verdant.py --setup" -ForegroundColor White
        Write-Host "   2. Run: python verdant.py --interactive" -ForegroundColor White
    } else {
        Write-Host "`n❌ Some tests failed. Please check the errors above." -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Test execution failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n🏁 Installation script completed" -ForegroundColor Green
Read-Host "Press Enter to exit" 