param(
  [string]$SessionId = "final01",
  [string]$PythonBase = "http://127.0.0.1:8787",
  [string]$NodeBase = "http://127.0.0.1:3000"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "[1/7] Health check"
Invoke-RestMethod -Uri "$PythonBase/health" -Method GET | Out-Null

Write-Host "[2/7] Start"
$body = @{ session_id = $SessionId } | ConvertTo-Json
Invoke-RestMethod -Uri "$PythonBase/start" -Method POST -ContentType "application/json" -Body $body | Out-Null

Start-Sleep -Seconds 2

Write-Host "[3/7] Reload"
Invoke-RestMethod -Uri "$PythonBase/reload" -Method POST -ContentType "application/json" -Body $body | Out-Null

Write-Host "[4/7] Stop"
Invoke-RestMethod -Uri "$PythonBase/stop" -Method POST -ContentType "application/json" -Body $body | Out-Null

Write-Host "[5/7] Validate artifacts"
$manifest = Invoke-RestMethod -Uri "$PythonBase/samples/$SessionId/manifest" -Method GET
$metadata = Invoke-RestMethod -Uri "$PythonBase/metadata/$SessionId" -Method GET
$script = Invoke-WebRequest -Uri "$PythonBase/strudel/$SessionId" -Method GET -UseBasicParsing
if (-not $manifest.words) { throw "Manifest words is empty." }
if (-not $metadata.chunks) { throw "Metadata chunks is empty." }
if ($script.Content -notmatch "strudelVoiceSamples") { throw "strudel.js content invalid." }

Write-Host "[6/7] Validate metrics"
$metrics = Invoke-RestMethod -Uri "$PythonBase/metrics" -Method GET
if ($metrics.total_chunks -lt 1) { throw "Metrics total_chunks is invalid." }

Write-Host "[7/7] Optional Node bridge checks"
try {
  Invoke-RestMethod -Uri "$NodeBase/strudel/metrics" -Method GET | Out-Null
  Invoke-RestMethod -Uri "$NodeBase/strudel/status?sessionId=$SessionId" -Method GET | Out-Null
  Write-Host "Node bridge check passed."
} catch {
  Write-Warning "Node bridge check skipped/failed: $($_.Exception.Message)"
}

Write-Host "Final acceptance passed for session: $SessionId"
