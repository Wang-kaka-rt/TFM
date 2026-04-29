param(
  [string]$Entry = "packaging/launcher.py",
  [string]$Name = "strudel-voice",
  [switch]$IncludeHeavyAsr,
  [string]$StrudelDist = "..\strudel-src-real\website\dist",
  [switch]$SkipSyncStrudel
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptRoot
Push-Location $projectRoot
try {
  function Invoke-CheckedNative {
    param(
      [Parameter(Mandatory = $true)]
      [scriptblock]$Command
    )
    & $Command
    if ($LASTEXITCODE -ne 0) {
      throw "Native command failed with exit code $LASTEXITCODE."
    }
  }

  if (-not (Test-Path "requirements.txt")) {
    throw "requirements.txt not found in $projectRoot"
  }
  if (-not (Test-Path "packaging/launcher.py")) {
    throw "packaging/launcher.py not found in $projectRoot"
  }
  if (-not (Test-Path "packaging/requirements-packaging.txt")) {
    throw "packaging/requirements-packaging.txt not found in $projectRoot"
  }

  if (-not $SkipSyncStrudel) {
    $resolvedStrudelDist = Join-Path $projectRoot $StrudelDist
    $strudelIndex = Join-Path $resolvedStrudelDist "index.html"
    if (-not (Test-Path $strudelIndex)) {
      throw "Strudel dist not found: $resolvedStrudelDist (missing index.html). Build Strudel website first."
    }
    $strudelTarget = Join-Path $projectRoot "static\strudel"
    if (Test-Path $strudelTarget) {
      Remove-Item $strudelTarget -Recurse -Force
    }
    New-Item -ItemType Directory -Path $strudelTarget -Force | Out-Null
    Copy-Item (Join-Path $resolvedStrudelDist "*") $strudelTarget -Recurse -Force
    Write-Host "Synced Strudel static assets from $resolvedStrudelDist to $strudelTarget"
  }

  # Prevent WinError 5/32 when old EXE is still running or locked.
  Get-Process -Name $Name -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  $distExe = Join-Path $projectRoot ("dist\" + $Name + ".exe")
  if (Test-Path $distExe) {
    Remove-Item $distExe -Force -ErrorAction SilentlyContinue
  }

  Write-Host "[1/3] Installing runtime dependencies..."
  Invoke-CheckedNative { py -m pip install -r requirements.txt }

  Write-Host "[2/3] Installing packaging dependencies..."
  Invoke-CheckedNative { py -m pip install -r packaging/requirements-packaging.txt }

  Write-Host "[3/3] Building EXE with PyInstaller..."
  $pyiArgs = @(
    "--noconfirm",
    "--clean",
    "--name", $Name,
    "--onefile",
    "--collect-data", "app",
    "--hidden-import", "uvicorn",
    "--hidden-import", "uvicorn.config",
    "--hidden-import", "uvicorn.logging",
    "--hidden-import", "uvicorn.loops.auto",
    "--hidden-import", "uvicorn.protocols.http.auto",
    "--hidden-import", "uvicorn.lifespan.on",
    "--hidden-import", "webview",
    "--hidden-import", "app.main",
    "--hidden-import", "app.api.routes",
    $Entry
  )

  if (-not $IncludeHeavyAsr) {
    # Keep default package lightweight; heavy ASR stacks can be enabled explicitly.
    $pyiArgs += @(
      "--exclude-module", "torch",
      "--exclude-module", "whisperx",
      "--exclude-module", "faster_whisper"
    )
  }

  $optionalAssets = @(
    @{ Path = "assets\ffmpeg"; Dest = "assets\ffmpeg" },
    @{ Path = "assets\models"; Dest = "assets\models" },
    @{ Path = "static"; Dest = "static" }
  )

  foreach ($asset in $optionalAssets) {
    if (Test-Path $asset.Path) {
      $pyiArgs += @("--add-data", "$($asset.Path);$($asset.Dest)")
      Write-Host "Including asset: $($asset.Path)"
    }
  }

  Invoke-CheckedNative { py -m PyInstaller @pyiArgs }

  Write-Host "Build finished. Check dist/$Name.exe"
}
finally {
  Pop-Location
}
