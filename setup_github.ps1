# Lumina GitHub Setup Script
# This script helps you push your Lumina MVP to GitHub

Write-Host "🚀 Lumina GitHub Setup" -ForegroundColor Green
Write-Host "=====================" -ForegroundColor Green

Write-Host "`n📋 Before running this script:" -ForegroundColor Yellow
Write-Host "1. Create a new repository on GitHub.com" -ForegroundColor White
Write-Host "2. Don't initialize with README (we already have one)" -ForegroundColor White
Write-Host "3. Note down your GitHub username and repository name" -ForegroundColor White

Write-Host "`n🔗 Enter your GitHub details:" -ForegroundColor Cyan

$username = Read-Host "GitHub Username"
$repoName = Read-Host "Repository Name"

if (-not $username -or -not $repoName) {
    Write-Host "❌ Username and repository name are required!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

$remoteUrl = "https://github.com/$username/$repoName.git"

Write-Host "`n🔍 Adding remote origin..." -ForegroundColor Yellow
Write-Host "URL: $remoteUrl" -ForegroundColor White

try {
    git remote add origin $remoteUrl
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Remote origin added successfully!" -ForegroundColor Green
        
        Write-Host "`n📤 Pushing to GitHub..." -ForegroundColor Yellow
        git push -u origin main
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "`n🎉 Successfully pushed to GitHub!" -ForegroundColor Green
            Write-Host "Your repository is now available at:" -ForegroundColor Cyan
            Write-Host "https://github.com/$username/$repoName" -ForegroundColor White
            
            Write-Host "`n📖 Next steps:" -ForegroundColor Yellow
            Write-Host "1. Visit your repository on GitHub" -ForegroundColor White
            Write-Host "2. Add a description and topics" -ForegroundColor White
            Write-Host "3. Share with others!" -ForegroundColor White
        } else {
            Write-Host "❌ Failed to push to GitHub" -ForegroundColor Red
            Write-Host "Check your GitHub credentials and repository permissions" -ForegroundColor Yellow
        }
    } else {
        Write-Host "❌ Failed to add remote origin" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n🏁 Setup script completed" -ForegroundColor Green
Read-Host "Press Enter to exit" 