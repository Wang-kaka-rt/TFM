Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$pythonDir = Join-Path $root "python"
$nodeDir = Join-Path $root "node"

Write-Host "[1/4] Ensure python deps..."
Push-Location $pythonDir
py -m pip install -r requirements.txt
Pop-Location

Write-Host "[2/4] Ensure node deps..."
Push-Location $nodeDir
npm install
Pop-Location

Write-Host "[3/4] Start python backend at :8787"
$pythonProc = Start-Process -FilePath "py" -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port 8787" -WorkingDirectory $pythonDir -PassThru

Write-Host "[4/4] Start node bridge at :3000"
$nodeProc = Start-Process -FilePath "npm.cmd" -ArgumentList "run start" -WorkingDirectory $nodeDir -PassThru

Start-Sleep -Seconds 3
try {
  Invoke-RestMethod -Uri "http://127.0.0.1:8787/health" -Method GET | Out-Null
  Write-Host "Python health check: OK"
} catch {
  Write-Warning "Python health check failed: $($_.Exception.Message)"
}
try {
  Invoke-RestMethod -Uri "http://127.0.0.1:3000/health" -Method GET | Out-Null
  Write-Host "Node health check: OK"
} catch {
  Write-Warning "Node health check failed: $($_.Exception.Message)"
}

Write-Host "Started."
Write-Host "Python PID: $($pythonProc.Id)"
Write-Host "Node PID:   $($nodeProc.Id)"
Write-Host "Press Ctrl+C to stop this script. Processes keep running in background."
