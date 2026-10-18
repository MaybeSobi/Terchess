$ErrorActionPreference = "Stop"
$Repo = "MaybeSobi/Terchess"

function Write-Info($Message) { Write-Host "[Terchess] $Message" -ForegroundColor Cyan }
function Write-Warn($Message) { Write-Host "[Terchess] $Message" -ForegroundColor Yellow }

function Get-PythonCommand {
    foreach ($candidate in @(@("py", "-3"), @("python", ""))) {
        $cmd = $candidate[0]
        if (Get-Command $cmd -ErrorAction SilentlyContinue) {
            try {
                & $cmd $candidate[1] -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" 2>$null
                if ($LASTEXITCODE -eq 0) { return $candidate }
            } catch {}
        }
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

Write-Info "Checking Stockfish..."
if (-not (Get-Command stockfish -ErrorAction SilentlyContinue)) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Info "Trying to install Stockfish with winget..."
        winget install --id Stockfish.Stockfish --exact --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) {
            Write-Warn "Automatic Stockfish installation was not available. Install it from https://stockfishchess.org/download/."
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
