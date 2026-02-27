# Start Backend
Write-Host "Starting Backend on Port 8000..." -ForegroundColor Green
Start-Process -NoNewWindow -FilePath "uvicorn" -ArgumentList "backend.app.main:app", "--reload", "--port", "8000"

# Start Frontend
Write-Host "Starting Next.js Frontend on Port 3000..." -ForegroundColor Blue
Start-Process -NoNewWindow -FilePath "npm" -ArgumentList "run", "dev"

Write-Host "Both servers are starting..." -ForegroundColor Cyan
