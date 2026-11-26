param(
    [ValidateSet("main", "release")]
    [string]$Channel = "main"
)

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

$helperTemp = Join-Path $env:TEMP ("terchess-stockfish-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $helperTemp | Out-Null
$helperPath = Join-Path $helperTemp "install_stockfish.py"
try {
    Write-Info "Searching for existing Stockfish engines and checking for updates build..."
    Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/MaybeSobi/Terchess/main/scripts/install_stockfish.py" -OutFile $helperPath
    if ($Python -eq "py") { & py -3 $helperPath } else { & python $helperPath }
    if ($LASTEXITCODE -ne 0) { throw "Stockfish installation or validation failed." }
} finally {
    Remove-Item -LiteralPath $helperTemp -Recurse -Force -ErrorAction SilentlyContinue
}

$temp = Join-Path $env:TEMP ("terchess-install-" + [guid]::NewGuid().ToString("N"))
$zipName = "Terchess-main.zip"
$downloadUri = "https://codeload.github.com/$Repo/zip/refs/heads/main"

if ($Channel -eq "release") {
    Write-Info "Finding the latest stable release..."
    $release = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest" -Headers @{
        "User-Agent" = "Terchess-Installer"
        "Accept" = "application/vnd.github+json"
    }
    $asset = $release.assets | Where-Object { $_.name -match '^Terchess-.*\.zip
$extract = Join-Path $temp "extract"
$destination = Join-Path $env:LOCALAPPDATA "Programs\Terchess"
New-Item -ItemType Directory -Force -Path $extract | Out-Null

try {
    Write-Info "Downloading Terchess from the $Channel channel..."
    Invoke-WebRequest -UseBasicParsing -Uri $downloadUri -OutFile $zip
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
 } | Select-Object -First 1
    if (-not $asset) { throw "Could not find a Terchess ZIP in the latest GitHub release." }
    $downloadUri = $asset.browser_download_url
    $zipName = $asset.name
}

$zip = Join-Path $temp $zipName
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
