Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  FDR Sentinel - Test Suite Execution     " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$RootPath = (Get-Item -Path "$PSScriptRoot\..").FullName
Set-Location $RootPath

Write-Host ""
Write-Host "[1/2] Running Backend Pytest Suite..." -ForegroundColor Yellow
& "$RootPath\backend\.venv\Scripts\pytest" "$RootPath\backend\tests" -v
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Backend tests failed!" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "[2/2] Running Frontend Vitest Suite..." -ForegroundColor Yellow
Set-Location "$RootPath\frontend"
npm test
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Frontend tests failed!" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "  All Backend and Frontend Tests Passed!  " -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
