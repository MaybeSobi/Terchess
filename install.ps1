$ErrorActionPreference = "Stop"
$Repo = "MaybeSobi/Terchess"

function Write-Info($Message) { Write-Host "[Terchess] $Message" -ForegroundColor Cyan }
function Write-Warn($Message) { Write-Host "[Terchess] $Message" -ForegroundColor Yellow }

function Install-TerchessCommand {
    param([Parameter(Mandatory=$true)][string]$InstallDirectory)

    $commandPath = Join-Path $InstallDirectory "terchess.cmd"
    $shim = @'
@echo off
setlocal
set "TERCHESS_HOME=%~dp0"
if exist "%TERCHESS_HOME%.venv\Scripts\python.exe" goto run_terchess
call "%TERCHESS_HOME%run_terchess.bat" %*
exit /b %ERRORLEVEL%
:run_terchess
"%TERCHESS_HOME%.venv\Scripts\python.exe" -m terchess %*
exit /b %ERRORLEVEL%
'@
    $utf8WithoutBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($commandPath, $shim + [Environment]::NewLine, $utf8WithoutBom)

    $normalizedInstallDirectory = $InstallDirectory.TrimEnd('\')
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $pathEntries = @($userPath -split ';' | Where-Object { $_.Trim() })
    $alreadyInUserPath = $false
    foreach ($entry in $pathEntries) {
        if ($entry.Trim().TrimEnd('\') -ieq $normalizedInstallDirectory) {
            $alreadyInUserPath = $true
            break
        }
    }

    if (-not $alreadyInUserPath) {
        $updatedUserPath = (@($pathEntries) + $InstallDirectory) -join ';'
        try {
            [Environment]::SetEnvironmentVariable("Path", $updatedUserPath, "User")
            Write-Info "Added Terchess to your user PATH."
        } catch {
            Write-Warn "Could not update your user PATH automatically. Add this folder to PATH manually: $InstallDirectory"
        }
    }

    $currentPathEntries = @($env:Path -split ';' | Where-Object { $_.Trim() })
    $alreadyInCurrentPath = $false
    foreach ($entry in $currentPathEntries) {
        if ($entry.Trim().TrimEnd('\') -ieq $normalizedInstallDirectory) {
            $alreadyInCurrentPath = $true
            break
        }
    }
    if (-not $alreadyInCurrentPath) {
        $env:Path = "$InstallDirectory;$env:Path"
    }

    Write-Info "You can now launch Terchess from any terminal by typing: terchess"
}

function Get-PythonCommand {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        try {
            & py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) { return "py" }
        } catch {}
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        try {
            & python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) { return "python" }
        } catch {}
    }

    return $null
}

function Test-StockfishExecutable {
    param([Parameter(Mandatory=$true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $false
    }

    # Probe with a timeout and require the full Skill Level 0-20 range.
    $probeScript = @'
import re
import subprocess
import sys

try:
    result = subprocess.run(
        [sys.argv[1]],
        input="uci\nquit\n",
        capture_output=True,
        text=True,
        timeout=8,
        check=False,
    )
except (OSError, subprocess.SubprocessError):
    raise SystemExit(1)

if result.returncode != 0 or "uciok" not in result.stdout.splitlines():
    raise SystemExit(1)

match = re.search(
    r"(?m)^option name Skill Level type spin default -?\d+ min (-?\d+) max (-?\d+)\s*$",
    result.stdout,
)
if not match:
    raise SystemExit(1)

minimum, maximum = map(int, match.groups())
raise SystemExit(0 if minimum <= 0 and maximum >= 20 else 1)
'@

    try {
        if ($Python -eq "py") {
            $pythonArgs = @("-3", "-c", $probeScript, $Path)
        } else {
            $pythonArgs = @("-c", $probeScript, $Path)
        }
        & $Python @pythonArgs 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Find-StockfishExecutable {
    $candidates = New-Object System.Collections.Generic.List[string]

    # First check commands visible through PATH.
    foreach ($commandName in @("stockfish", "stockfish.exe")) {
        $commands = Get-Command $commandName -CommandType Application -ErrorAction SilentlyContinue
        foreach ($command in $commands) {
            if ($command.Source) { $candidates.Add($command.Source) }
        }
    }

    # Check common manual-install locations.
    foreach ($candidate in @(
        "C:\Engines\stockfish-windows-x86-64-universal\stockfish",
        "C:\Engines\stockfish-windows-x86-64-universal\stockfish.exe",
        "C:\Program Files\Stockfish\stockfish.exe",
        "C:\Program Files\Stockfish\stockfish-windows-x86-64-avx2.exe",
        (Join-Path $env:LOCALAPPDATA "Programs\Stockfish\stockfish.exe")
    )) {
        if ($candidate) { $candidates.Add($candidate) }
    }

    # Also discover manually extracted builds anywhere under C:\Engines.
    $enginesRoot = "C:\Engines"
    if (Test-Path -LiteralPath $enginesRoot -PathType Container) {
        $engineFiles = Get-ChildItem -LiteralPath $enginesRoot -Filter "stockfish*" -File -Recurse -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match '^stockfish(?:[-_].*)?(?:\.exe)?$' }

        foreach ($engineFile in $engineFiles) {
            $candidates.Add($engineFile.FullName)
        }
    }

    # Discover versioned Stockfish builds installed by Terchess.
    $managedRoot = Join-Path $env:LOCALAPPDATA "Terchess\Engines"
    if (Test-Path -LiteralPath $managedRoot -PathType Container) {
        $managedFiles = Get-ChildItem -LiteralPath $managedRoot -Filter "stockfish*" -File -Recurse -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match '^stockfish(?:[-_].*)?(?:\.exe)?$' }
        foreach ($managedFile in $managedFiles) {
            $candidates.Add($managedFile.FullName)
        }
    }

    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (Test-StockfishExecutable -Path $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    return $null
}

function Save-DetectedStockfishPath {
    param([Parameter(Mandatory=$true)][string]$EnginePath)

    $configDirectory = Join-Path $env:APPDATA "Terchess"
    $configPath = Join-Path $configDirectory "config.json"
    New-Item -ItemType Directory -Force -Path $configDirectory | Out-Null

    if (Test-Path -LiteralPath $configPath -PathType Leaf) {
        try {
            $config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
            if ($null -eq $config -or $config -isnot [pscustomobject]) {
                Write-Warn "Existing Terchess settings are not a JSON object. I left them unchanged."
                return
            }
        } catch {
            Write-Warn "Existing Terchess settings contain invalid JSON. I left them unchanged; you can set the engine path in Terchess Settings."
            return
        }
    } else {
        $config = [pscustomobject]@{}
    }

    # Add or replace only this property; all other existing settings are retained.
    $config | Add-Member -MemberType NoteProperty -Name "stockfish_path" -Value $EnginePath -Force
    $json = $config | ConvertTo-Json -Depth 20
    $utf8WithoutBom = [System.Text.UTF8Encoding]::new($false)
    $temporaryPath = "$configPath.$([guid]::NewGuid().ToString('N')).tmp"

    try {
        [System.IO.File]::WriteAllText(
            $temporaryPath,
            $json + [Environment]::NewLine,
            $utf8WithoutBom
        )

        if (Test-Path -LiteralPath $configPath -PathType Leaf) {
            [System.IO.File]::Replace($temporaryPath, $configPath, $null)
        } else {
            [System.IO.File]::Move($temporaryPath, $configPath)
        }
        Write-Info "Saved the detected Stockfish path without changing other Terchess settings."
    } catch {
        Remove-Item -LiteralPath $temporaryPath -Force -ErrorAction SilentlyContinue
        Write-Warn "Could not safely update Terchess settings; the existing config was preserved. Set the engine path in Terchess Settings."
    }
}

Write-Info "Checking Python 3.10+..."
$Python = Get-PythonCommand
if (-not $Python) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "Python 3.10+ is required. Install it from https://www.python.org/downloads/ and rerun this installer."
    }

    Write-Info "Installing Python with Windows Package Manager..."
    winget install --id Python.Python.3.13 --exact --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "Python installation failed. Install Python 3.10+ manually, reopen PowerShell, and rerun."
    }

    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath"
    $Python = Get-PythonCommand
    if (-not $Python) {
        throw "Python was installed, but this PowerShell session cannot find it yet. Reopen PowerShell and rerun this command."
    }
}

$StockfishRoot = Join-Path $env:LOCALAPPDATA "Terchess\Engines"
$StockfishConfig = Join-Path $env:APPDATA "Terchess\config.json"
$StockfishHelper = Join-Path $env:TEMP ("terchess-stockfish-" + [guid]::NewGuid().ToString("N") + ".py")
$StockfishHelperReady = $false
$StockfishReady = $false

try {
    Write-Info "Downloading the Terchess Stockfish installer helper..."
    try {
        Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/$Repo/main/install_stockfish.py" -OutFile $StockfishHelper
        $StockfishHelperReady = Test-Path -LiteralPath $StockfishHelper -PathType Leaf
    } catch {
        Write-Warn "Could not download the Stockfish installer helper: $($_.Exception.Message)"
    }

    if ($StockfishHelperReady) {
        Write-Info "Installing the latest official stable Stockfish release..."
        if ($Python -eq "py") {
            & py -3 $StockfishHelper --platform windows --install-dir $StockfishRoot --config-path $StockfishConfig
        } else {
            & python $StockfishHelper --platform windows --install-dir $StockfishRoot --config-path $StockfishConfig
        }
        $StockfishReady = ($LASTEXITCODE -eq 0)
        if (-not $StockfishReady) {
            Write-Warn "The official Stockfish download or validation failed."
        }
    }

    if (-not $StockfishReady) {
        Write-Warn "Trying an existing/system Stockfish executable as a fallback; it may be older than the latest official release."
        $StockfishPath = Find-StockfishExecutable

        if (-not $StockfishPath -and (Get-Command winget -ErrorAction SilentlyContinue)) {
            Write-Info "Trying WinGet as a fallback source..."
            winget install --id Stockfish.Stockfish --exact --accept-package-agreements --accept-source-agreements
            if ($LASTEXITCODE -eq 0) {
                $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
                $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
                $env:Path = "$machinePath;$userPath"
                $StockfishPath = Find-StockfishExecutable
            } else {
                Write-Warn "WinGet could not install the fallback Stockfish package."
            }
        }

        if ($StockfishPath) {
            if ($StockfishHelperReady) {
                if ($Python -eq "py") {
                    & py -3 $StockfishHelper --validate-existing $StockfishPath --config-path $StockfishConfig
                } else {
                    & python $StockfishHelper --validate-existing $StockfishPath --config-path $StockfishConfig
                }
                if ($LASTEXITCODE -eq 0) {
                    Write-Warn "Using the system fallback. Its version may be older than the latest official Stockfish release."
                } else {
                    Write-Warn "The fallback Stockfish executable failed validation. Select a compatible engine in Terchess Settings."
                }
            } else {
                Write-Info "Found an existing Stockfish executable: $StockfishPath"
                Save-DetectedStockfishPath -EnginePath $StockfishPath
                Write-Warn "The existing engine was saved as a fallback; its version could not be checked against the latest official release."
            }
        } else {
            Write-Warn "No compatible Stockfish engine is available. Install it manually from https://stockfishchess.org/download/ and select it in Terchess Settings."
        }
    }
} finally {
    Remove-Item -LiteralPath $StockfishHelper -Force -ErrorAction SilentlyContinue
}

Write-Info "Finding the latest stable release..."
$release = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest" -Headers @{
    "User-Agent" = "Terchess-Installer"
    "Accept" = "application/vnd.github+json"
}
$asset = $release.assets | Where-Object { $_.name -match '^Terchess-.*\.zip$' } | Select-Object -First 1
if (-not $asset) { throw "Could not find a Terchess ZIP in the latest GitHub release." }

$temp = Join-Path $env:TEMP ("terchess-install-" + [guid]::NewGuid().ToString("N"))
$zip = Join-Path $temp "Terchess.zip"
$extract = Join-Path $temp "extract"
$destination = Join-Path $env:LOCALAPPDATA "Programs\Terchess"
New-Item -ItemType Directory -Force -Path $extract | Out-Null

try {
    Write-Info "Downloading Terchess $($release.tag_name)..."
    Invoke-WebRequest -UseBasicParsing -Uri $asset.browser_download_url -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $extract -Force

    $project = Get-ChildItem -Path $extract -Filter "pyproject.toml" -Recurse -File | Select-Object -First 1
    if (-not $project) { throw "The downloaded archive does not contain pyproject.toml." }
    $source = $project.Directory.FullName

    if (Test-Path -LiteralPath $destination -PathType Container) {
        # Keep the existing virtual environment; replace only application files.
        Get-ChildItem -LiteralPath $destination -Force |
            Where-Object { -not ($_.Name -eq ".venv" -and $_.PSIsContainer) } |
            Remove-Item -Recurse -Force
    } else {
        if (Test-Path -LiteralPath $destination) {
            Remove-Item -LiteralPath $destination -Force
        }
        New-Item -ItemType Directory -Force -Path $destination | Out-Null
    }

    Get-ChildItem -LiteralPath $source -Force |
        Copy-Item -Destination $destination -Recurse -Force

    # Check declared dependencies, then refresh only Terchess itself in the old venv.
    $venvPython = Join-Path $destination ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPython -PathType Leaf) {
        Write-Info "Updating Terchess inside the existing Python environment..."
        & $venvPython -m pip install --disable-pip-version-check $destination
        if ($LASTEXITCODE -ne 0) {
            throw "Could not update Python dependencies in the existing .venv. Check the connection and rerun the installer."
        }

        & $venvPython -m pip install --disable-pip-version-check --force-reinstall --no-deps $destination
        if ($LASTEXITCODE -ne 0) {
            throw "Could not refresh Terchess in the existing .venv. Rerun the installer to retry."
        }
    }
} finally {
    Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
}

Install-TerchessCommand -InstallDirectory $destination

Write-Info "Installed to $destination"
Write-Info "Launching Terchess. First launch installs its Python dependencies."
& (Join-Path $destination "run_terchess.bat")
