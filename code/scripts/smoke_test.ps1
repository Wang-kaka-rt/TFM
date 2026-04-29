Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$sessionId = "smoke01"
$pythonBase = "http://127.0.0.1:8787"
$nodeBase = "http://127.0.0.1:3000"

Write-Host "[1/5] Python health"
Invoke-RestMethod -Uri "$pythonBase/health" -Method GET | ConvertTo-Json -Depth 5

Write-Host "[2/5] Start session"
$startBody = @{ session_id = $sessionId } | ConvertTo-Json
Invoke-RestMethod -Uri "$pythonBase/start" -Method POST -ContentType "application/json" -Body $startBody | ConvertTo-Json -Depth 5

Start-Sleep -Seconds 1

Write-Host "[3/5] Reload session"
$reloadBody = @{ session_id = $sessionId } | ConvertTo-Json
Invoke-RestMethod -Uri "$pythonBase/reload" -Method POST -ContentType "application/json" -Body $reloadBody | ConvertTo-Json -Depth 5

Write-Host "[4/5] Stop session"
$stopBody = @{ session_id = $sessionId } | ConvertTo-Json
Invoke-RestMethod -Uri "$pythonBase/stop" -Method POST -ContentType "application/json" -Body $stopBody | ConvertTo-Json -Depth 5

Write-Host "[5/5] Node bridge status/metrics"
Invoke-RestMethod -Uri "$nodeBase/strudel/status?sessionId=$sessionId" -Method GET | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri "$nodeBase/strudel/metrics" -Method GET | ConvertTo-Json -Depth 5
