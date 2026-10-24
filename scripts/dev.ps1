Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  FDR Sentinel - Development Servers      " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$RootPath = (Get-Item -Path "$PSScriptRoot\..").FullName

Write-Host ""
Write-Host "Starting FastAPI Backend on http://127.0.0.1:8000..." -ForegroundColor Green
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd '$RootPath'; & 'backend\.venv\Scripts\python' -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000"

Write-Host "Starting Vite Frontend on http://localhost:5173..." -ForegroundColor Green
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd '$RootPath\frontend'; npm run dev"

Write-Host ""
Write-Host "Servers launched in dedicated background windows." -ForegroundColor Yellow
Write-Host "Backend API Docs: http://127.0.0.1:8000/docs" -ForegroundColor Gray
Write-Host "Frontend Portal:  http://localhost:5173" -ForegroundColor Gray
