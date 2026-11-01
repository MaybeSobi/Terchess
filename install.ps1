$ErrorActionPreference = "Stop"
$Repo = "MaybeSobi/Terchess"

function Write-Info($Message) { Write-Host "[Terchess] $Message" -ForegroundColor Cyan }
function Write-Warn($Message) { Write-Host "[Terchess] $Message" -ForegroundColor Yellow }

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

Write-Info "Checking Python 3.10+..."
$Python = Get-PythonCommand
if (-not $Python) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "Python 3.10+ is required. Install it from https://www.python.org/downloads/ and rerun this installer."
    }
    Write-Info "Installing Python with Windows Package Manager..."
    winget install --id Python.Python.3.13 --exact --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw "Python installation failed. Install Python 3.10+ manually, reopen PowerShell, and rerun." }
    $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
    $Python = Get-PythonCommand
    if (-not $Python) { throw "Python was installed, but this PowerShell session cannot find it yet. Reopen PowerShell and rerun this command." }
}

function Test-StockfishExecutable {
    param([Parameter(Mandatory=$true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $false
    }

    # Probe the UCI handshake rather than trusting a filename or a stale PATH entry.
    try {
        $probeOutput = @("uci", "quit") | & $Path 2>$null
        return (($probeOutput -join [Environment]::NewLine) -match "(?m)^uciok\s*$")
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

    # Check common manual-install locations, including the path used by many Windows builds.
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
            Where-Object { $_.Name -match '^stockfish(?:[-_].*)?(?:\.exe)?
Write-Info "Finding the latest stable release..."
$release = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest" -Headers @{ "User-Agent" = "Terchess-Installer" }
$asset = $release.assets | Where-Object { $_.name -match '^Terchess-.*\.zip$' } | Select-Object -First 1
if (-not $asset) { throw "Could not find a Terchess ZIP in the latest GitHub release." }

$temp = Join-Path $env:TEMP ("terchess-install-" + [guid]::NewGuid().ToString("N"))
$zip = Join-Path $temp "Terchess.zip"
$extract = Join-Path $temp "extract"
$destination = Join-Path $env:LOCALAPPDATA "Programs\Terchess"
New-Item -ItemType Directory -Force -Path $extract | Out-Null
try {
    Write-Info "Downloading Terchess $($release.tag_name)..."
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $extract -Force
    $project = Get-ChildItem -Path $extract -Filter "pyproject.toml" -Recurse -File | Select-Object -First 1
    if (-not $project) { throw "The downloaded archive does not contain pyproject.toml." }
    $source = $project.Directory.FullName

    if (Test-Path $destination) { Remove-Item -Path $destination -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $destination | Out-Null
    Copy-Item -Path (Join-Path $source "*") -Destination $destination -Recurse -Force
} finally {
    Remove-Item -Path $temp -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Info "Installed to $destination"
Write-Info "Launching Terchess. First launch installs its Python dependencies."
& (Join-Path $destination "run_terchess.bat")
 }
        foreach ($engineFile in $engineFiles) {
            $candidates.Add($engineFile.FullName)
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
            if ($null -eq $config) { $config = [pscustomobject]@{} }
        } catch {
            Write-Warn "Existing Terchess settings contain invalid JSON. I left them unchanged; you can set the engine path in Terchess."
            return
        }
    } else {
        $config = [pscustomobject]@{}
    }

    $config | Add-Member -MemberType NoteProperty -Name "stockfish_path" -Value $EnginePath -Force
    $json = $config | ConvertTo-Json -Depth 10
    $utf8WithoutBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($configPath, $json + [Environment]::NewLine, $utf8WithoutBom)
    Write-Info "Saved the detected Stockfish path to Terchess settings."
}

Write-Info "Checking Stockfish..."
$StockfishPath = Find-StockfishExecutable
if ($StockfishPath) {
    Write-Info "Found an existing Stockfish engine: $StockfishPath"
    Write-Info "Skipping Stockfish installation."
    Save-DetectedStockfishPath -EnginePath $StockfishPath
} else {
    Write-Warn "No working Stockfish executable was found on PATH or under C:\Engines."
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Info "Trying to install Stockfish with winget..."
        winget install --id Stockfish.Stockfish --exact --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) {
            Write-Warn "Automatic Stockfish installation was not available. Install it from https://stockfishchess.org/download/."
        } else {
            $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
            $StockfishPath = Find-StockfishExecutable
            if ($StockfishPath) {
                Write-Info "Found the newly installed Stockfish engine: $StockfishPath"
                Save-DetectedStockfishPath -EnginePath $StockfishPath
            } else {
                Write-Warn "Stockfish was installed, but this session could not locate its executable. Terchess will ask for its path when you choose Play vs Stockfish."
            }
        }
    } else {
        Write-Warn "Install Stockfish separately from https://stockfishchess.org/download/."
    }
}

Write-Info "Finding the latest stable release..."
$release = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest" -Headers @{ "User-Agent" = "Terchess-Installer" }
$asset = $release.assets | Where-Object { $_.name -match '^Terchess-.*\.zip$' } | Select-Object -First 1
if (-not $asset) { throw "Could not find a Terchess ZIP in the latest GitHub release." }

$temp = Join-Path $env:TEMP ("terchess-install-" + [guid]::NewGuid().ToString("N"))
$zip = Join-Path $temp "Terchess.zip"
$extract = Join-Path $temp "extract"
$destination = Join-Path $env:LOCALAPPDATA "Programs\Terchess"
New-Item -ItemType Directory -Force -Path $extract | Out-Null
try {
    Write-Info "Downloading Terchess $($release.tag_name)..."
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $extract -Force
    $project = Get-ChildItem -Path $extract -Filter "pyproject.toml" -Recurse -File | Select-Object -First 1
    if (-not $project) { throw "The downloaded archive does not contain pyproject.toml." }
    $source = $project.Directory.FullName

    if (Test-Path $destination) { Remove-Item -Path $destination -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $destination | Out-Null
    Copy-Item -Path (Join-Path $source "*") -Destination $destination -Recurse -Force
} finally {
    Remove-Item -Path $temp -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Info "Installed to $destination"
Write-Info "Launching Terchess. First launch installs its Python dependencies."
& (Join-Path $destination "run_terchess.bat")
