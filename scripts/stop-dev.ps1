$ErrorActionPreference = "Continue"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$PidDir = Join-Path $Root ".dev-pids"
$PidFiles = @(
  Join-Path $PidDir "backend.pid"
  Join-Path $PidDir "frontend.pid"
  Join-Path $PidDir "ollama.pid"
)

foreach ($PidFile in $PidFiles) {
  if (Test-Path $PidFile) {
    $ProcessId = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($ProcessId) {
      Write-Host "Stopping process tree $ProcessId ..."
      taskkill /PID $ProcessId /T /F | Out-Null
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
  }
}

$Ports = @(3000, 8000)
foreach ($Port in $Ports) {
  $Connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  foreach ($Connection in $Connections) {
    Write-Host "Stopping listener on port $Port, PID $($Connection.OwningProcess) ..."
    taskkill /PID $Connection.OwningProcess /T /F | Out-Null
  }
}

Write-Host "Stopping PostgreSQL Docker container..."
Push-Location $Root
docker compose down
Pop-Location

Remove-Item $PidDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Development stack stopped."
