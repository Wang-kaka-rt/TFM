Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$sessionId = "smoke01"
$pythonBase = "http://127.0.0.1:8787"
$nodeBase = "http://127.0.0.1:3000"

Write-Host "[1/4] Python health"
Invoke-RestMethod -Uri "$pythonBase/health" -Method GET | ConvertTo-Json -Depth 5

Write-Host "[2/4] Start session"
$startBody = @{ session_id = $sessionId } | ConvertTo-Json
Invoke-RestMethod -Uri "$pythonBase/start" -Method POST -ContentType "application/json" -Body $startBody | ConvertTo-Json -Depth 5

Start-Sleep -Seconds 1

Write-Host "[3/4] Stop session"
$stopBody = @{ session_id = $sessionId } | ConvertTo-Json
Invoke-RestMethod -Uri "$pythonBase/stop" -Method POST -ContentType "application/json" -Body $stopBody | ConvertTo-Json -Depth 5

Write-Host "[4/4] Node bridge status/metrics"
Invoke-RestMethod -Uri "$nodeBase/strudel/status?sessionId=$sessionId" -Method GET | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri "$nodeBase/strudel/metrics" -Method GET | ConvertTo-Json -Depth 5
