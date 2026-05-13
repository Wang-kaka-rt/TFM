param(
  [string]$Entry = "packaging/launcher.py",
  [string]$Name = "strudel-voice",
  [switch]$IncludeHeavyAsr,
  [string]$StrudelDist = "..\strudel-src-real\website\dist",
  [switch]$SkipSyncStrudel,
  [string]$PythonExe = ""
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

  function Resolve-PythonCommand {
    if ($PythonExe) {
      if (-not (Test-Path $PythonExe)) {
        throw "PythonExe not found: $PythonExe"
      }
      return @($PythonExe)
    }

    $candidates = @(
      "C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe",
      "python",
      "py"
    )
    foreach ($candidate in $candidates) {
      try {
        if ($candidate -eq "py") {
          & py -3.12 -c "import sys; print(sys.version)" | Out-Null
          if ($LASTEXITCODE -eq 0) {
            return @("py", "-3.12")
          }
        } else {
          & $candidate -c "import sys; print(sys.version)" | Out-Null
          if ($LASTEXITCODE -eq 0) {
            return @($candidate)
          }
        }
      } catch {
        continue
      }
    }
    throw "No usable Python interpreter found. Pass -PythonExe <path-to-python.exe>."
  }

  $pythonCommand = @(Resolve-PythonCommand)
  function Invoke-PythonModule {
    param(
      [Parameter(Mandatory = $true)]
      [string[]]$Arguments
    )
    $pythonArgs = @()
    if ($pythonCommand.Length -gt 1) {
      $pythonArgs = $pythonCommand[1..($pythonCommand.Length - 1)]
    }
    Invoke-CheckedNative { & $pythonCommand[0] @pythonArgs @Arguments }
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
      Microsoft.PowerShell.Management\Remove-Item $strudelTarget -Recurse -Force
    }
    Microsoft.PowerShell.Management\New-Item -ItemType Directory -Path $strudelTarget -Force | Out-Null
    Microsoft.PowerShell.Management\Copy-Item (Join-Path $resolvedStrudelDist "*") $strudelTarget -Recurse -Force
    Write-Host "Synced Strudel static assets from $resolvedStrudelDist to $strudelTarget"
  }

  # Prevent WinError 5/32 when old EXE is still running or locked.
  Get-Process -Name $Name -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  $distExe = Join-Path $projectRoot ("dist\" + $Name + ".exe")
  if (Test-Path $distExe) {
    Microsoft.PowerShell.Management\Remove-Item $distExe -Force -ErrorAction SilentlyContinue
  }

  Write-Host "[1/3] Installing runtime dependencies..."
  if ($IncludeHeavyAsr) {
    Invoke-PythonModule -Arguments @("-m", "pip", "install", "-r", "requirements.realtime.txt")
  } else {
    Invoke-PythonModule -Arguments @("-m", "pip", "install", "-r", "requirements.txt")
  }

  Write-Host "[2/3] Installing packaging dependencies..."
  Invoke-PythonModule -Arguments @("-m", "pip", "install", "-r", "packaging/requirements-packaging.txt")

  Write-Host "[3/3] Building EXE with PyInstaller..."
  $pyCompatArgs = @()
  if ($pythonCommand.Length -gt 1) {
    $pyCompatArgs = $pythonCommand[1..($pythonCommand.Length - 1)]
  }
  $portaudioAliasDir = Join-Path $projectRoot "build\portaudio-binaries-alias"
  if (Test-Path $portaudioAliasDir) {
    Microsoft.PowerShell.Management\Remove-Item $portaudioAliasDir -Recurse -Force -ErrorAction SilentlyContinue
  }
  Microsoft.PowerShell.Management\New-Item -ItemType Directory -Path $portaudioAliasDir -Force | Out-Null
  $portaudio64Path = (& $pythonCommand[0] @pyCompatArgs -c "import pathlib; import _sounddevice_data; p = pathlib.Path(next(iter(_sounddevice_data.__path__))) / 'portaudio-binaries' / 'libportaudio64bit.dll'; print(p if p.exists() else '')")
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to resolve bundled PortAudio runtime path."
  }
  $portaudio64Path = ($portaudio64Path | Select-Object -Last 1).Trim()
  $portaudioArm64Alias = $null
  if ($portaudio64Path) {
    $portaudioArm64Alias = Join-Path $portaudioAliasDir "libportaudioarm64.dll"
    Microsoft.PowerShell.Management\Copy-Item $portaudio64Path $portaudioArm64Alias -Force
    Write-Host "Prepared PortAudio ARM64 alias from $portaudio64Path"
  }

  $pyiArgs = @(
    "--noconfirm",
    "--clean",
    "--name", $Name,
    "--onefile",
    "--collect-data", "app",
    "--hidden-import", "sounddevice",
    "--hidden-import", "_cffi_backend",
    "--hidden-import", "uvicorn",
    "--hidden-import", "uvicorn.config",
    "--hidden-import", "uvicorn.logging",
    "--hidden-import", "uvicorn.loops.auto",
    "--hidden-import", "uvicorn.protocols.http.auto",
    "--hidden-import", "uvicorn.lifespan.on",
    "--hidden-import", "webview",
    "--hidden-import", "app.main",
    "--hidden-import", "app.api.routes",
    "--hidden-import", "faster_whisper",
    "--hidden-import", "ctranslate2",
    "--hidden-import", "tokenizers",
    "--hidden-import", "huggingface_hub",
    "--hidden-import", "av",
    "--collect-all", "sounddevice",
    "--collect-all", "_sounddevice_data",
    "--collect-all", "faster_whisper",
    "--collect-all", "ctranslate2",
    "--collect-all", "tokenizers",
    $Entry
  )

  if ($portaudioArm64Alias) {
    $pyiArgs += @(
      "--add-data", "$portaudioArm64Alias;_sounddevice_data\portaudio-binaries"
    )
  }

  if (-not $IncludeHeavyAsr) {
    # Keep default package lightweight; heavy ASR stacks can be enabled explicitly.
    $pyiArgs += @(
      "--exclude-module", "torch",
      "--exclude-module", "whisperx",
      "--exclude-module", "tensorflow",
      "--exclude-module", "keras",
      "--exclude-module", "tf_keras",
      "--exclude-module", "pandas",
      "--exclude-module", "pyarrow",
      "--exclude-module", "scipy",
      "--exclude-module", "sklearn",
      "--exclude-module", "cv2",
      "--exclude-module", "numba",
      "--exclude-module", "llvmlite",
      "--exclude-module", "matplotlib",
      "--exclude-module", "IPython",
      "--exclude-module", "jupyter_client",
      "--exclude-module", "pytest"
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

  Invoke-PythonModule -Arguments (@("-m", "PyInstaller") + $pyiArgs)

  Write-Host "Bundled audio runtime: sounddevice, _sounddevice_data, _cffi_backend"
  Write-Host "Build finished. Check dist/$Name.exe"
}
finally {
  Pop-Location
}
