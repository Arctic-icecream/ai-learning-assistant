$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$UploadsDir = Join-Path $Root "backend\storage\uploads"

Write-Host "Clearing documents table in PostgreSQL..."
Push-Location $Root
docker compose exec -T postgres psql `
  -U ai_learning_user `
  -d ai_learning_assistant `
  -c "TRUNCATE TABLE document_chunks, documents RESTART IDENTITY;"
Pop-Location

Write-Host "Removing uploaded test files..."
if (Test-Path $UploadsDir) {
  Get-ChildItem -Path $UploadsDir -File |
    Where-Object { $_.Name -ne ".gitkeep" } |
    Remove-Item -Force
}

Write-Host ""
Write-Host "Development data reset complete."
