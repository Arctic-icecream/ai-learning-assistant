$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$PidDir = Join-Path $Root ".dev-pids"
$BackendPidFile = Join-Path $PidDir "backend.pid"
$FrontendPidFile = Join-Path $PidDir "frontend.pid"

New-Item -ItemType Directory -Force -Path $PidDir | Out-Null

Write-Host "Checking Docker Desktop..."
docker info | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "Docker is not running. Open Docker Desktop first, then run start-dev.cmd again."
}

Write-Host "Starting PostgreSQL with Docker Compose..."
Push-Location $Root
docker compose up -d

Write-Host "Waiting for PostgreSQL to accept connections..."
$DatabaseReady = $false
for ($Attempt = 1; $Attempt -le 30; $Attempt++) {
  docker compose exec -T postgres pg_isready -U ai_learning_user -d ai_learning_assistant | Out-Null
  if ($LASTEXITCODE -eq 0) {
    $DatabaseReady = $true
    break
  }

  Start-Sleep -Seconds 2
}
Pop-Location

if (-not $DatabaseReady) {
  throw "PostgreSQL did not become ready in time. Check Docker Desktop and run docker compose logs postgres."
}

Write-Host "Starting FastAPI backend on http://127.0.0.1:8000 ..."
$BackendCommand = @"
Set-Location "$Root"
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
"@
$BackendProcess = Start-Process powershell.exe `
  -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $BackendCommand) `
  -PassThru
$BackendProcess.Id | Set-Content -Path $BackendPidFile

Write-Host "Starting Next.js frontend on http://localhost:3000 ..."
$FrontendCommand = @"
Set-Location "$Root\frontend"
npm.cmd run dev
"@
$FrontendProcess = Start-Process powershell.exe `
  -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $FrontendCommand) `
  -PassThru
$FrontendProcess.Id | Set-Content -Path $FrontendPidFile

Write-Host ""
Write-Host "Development stack started."
Write-Host "Frontend: http://localhost:3000"
Write-Host "Backend:  http://127.0.0.1:8000/health"
Write-Host ""
Write-Host "Use stop-dev.cmd to stop the frontend, backend, and database."
