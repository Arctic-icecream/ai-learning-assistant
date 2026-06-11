$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$PidDir = Join-Path $Root ".dev-pids"
$BackendPidFile = Join-Path $PidDir "backend.pid"
$FrontendPidFile = Join-Path $PidDir "frontend.pid"
$OllamaPidFile = Join-Path $PidDir "ollama.pid"

New-Item -ItemType Directory -Force -Path $PidDir | Out-Null

$OllamaPath = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
if (-not (Test-Path $OllamaPath)) {
  throw "Ollama was not found at $OllamaPath. Install Ollama before starting the app."
}

Write-Host "Checking Ollama..."
$OllamaReady = $false
try {
  Invoke-RestMethod "http://127.0.0.1:11434/api/tags" | Out-Null
  $OllamaReady = $true
} catch {
  Write-Host "Ollama is not running. Starting Ollama service..."
  $OllamaProcess = Start-Process -FilePath $OllamaPath -ArgumentList @("serve") -PassThru
  $OllamaProcess.Id | Set-Content -Path $OllamaPidFile

  for ($Attempt = 1; $Attempt -le 30; $Attempt++) {
    Start-Sleep -Seconds 2
    try {
      Invoke-RestMethod "http://127.0.0.1:11434/api/tags" | Out-Null
      $OllamaReady = $true
      break
    } catch {
    }
  }
}

if (-not $OllamaReady) {
  throw "Ollama did not become ready in time."
}

$OllamaModels = & $OllamaPath list
if ($OllamaModels -notmatch "nomic-embed-text") {
  throw "Ollama model nomic-embed-text is missing. Run: ollama pull nomic-embed-text"
}

Write-Host "Checking Docker Desktop..."
$DockerReady = $false
docker info | Out-Null
if ($LASTEXITCODE -eq 0) {
  $DockerReady = $true
} else {
  $DockerDesktopPath = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
  if (-not (Test-Path $DockerDesktopPath)) {
    throw "Docker Desktop was not found at $DockerDesktopPath."
  }

  Write-Host "Docker is not running. Starting Docker Desktop..."
  Start-Process -FilePath $DockerDesktopPath | Out-Null

  Write-Host "Waiting for Docker engine to become ready..."
  for ($Attempt = 1; $Attempt -le 60; $Attempt++) {
    Start-Sleep -Seconds 2
    docker info | Out-Null
    if ($LASTEXITCODE -eq 0) {
      $DockerReady = $true
      break
    }
  }
}

if (-not $DockerReady) {
  throw "Docker did not become ready in time. Check Docker Desktop and try start-dev.cmd again."
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
