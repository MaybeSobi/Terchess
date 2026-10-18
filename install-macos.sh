#!/usr/bin/env bash
set -euo pipefail

REPO="MaybeSobi/Terchess"
APP_DIR="$HOME/Applications/Terchess"
TMP_DIR="$(mktemp -d)"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

info() { printf '\033[1;36m[Terchess]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[Terchess]\033[0m %s\n' "$*"; }

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is required for automatic setup on macOS."
  echo "Install it from https://brew.sh, then rerun this installer."
  exit 1
fi

info "Installing/checking Python and Stockfish with Homebrew..."
brew install python stockfish || warn "Homebrew reported an install issue; checking whether the required commands are available."

if ! command -v python3 >/dev/null 2>&1 || ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)'; then
  echo "Python 3.10+ is required. Install it from https://www.python.org/downloads/macos/ and rerun."
  exit 1
fi

if ! command -v stockfish >/dev/null 2>&1; then
  warn "Stockfish was not found on PATH. Install it from https://stockfishchess.org/download/ and select its executable in Terchess Settings."
fi

info "Finding the latest stable release..."
ASSET_URL="$(python3 - "$REPO" <<'PY'
import json, sys, urllib.request
repo = sys.argv[1]
req = urllib.request.Request(
    f"https://api.github.com/repos/{repo}/releases/latest",
    headers={"User-Agent": "Terchess-Installer", "Accept": "application/vnd.github+json"},
)
with urllib.request.urlopen(req, timeout=30) as response:
    release = json.load(response)
assets = [a for a in release.get("assets", []) if a.get("name", "").startswith("Terchess-") and a.get("name", "").endswith(".zip")]
if not assets:
    raise SystemExit("No Terchess ZIP asset found in the latest release.")
print(assets[0]["browser_download_url"])
PY
)"

info "Downloading Terchess..."
curl -fL "$ASSET_URL" -o "$TMP_DIR/Terchess.zip"
mkdir "$TMP_DIR/extract"
ditto -x -k "$TMP_DIR/Terchess.zip" "$TMP_DIR/extract"
PROJECT_FILE="$(find "$TMP_DIR/extract" -name pyproject.toml -type f -print -quit)"
if [[ -z "$PROJECT_FILE" ]]; then
  echo "The downloaded archive does not contain pyproject.toml."
  exit 1
fi
PROJECT_DIR="$(dirname "$PROJECT_FILE")"

mkdir -p "$HOME/Applications"
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR"
cp -R "$PROJECT_DIR/." "$APP_DIR/"

info "Installed to $APP_DIR"
info "Launching Terchess. First launch installs its Python dependencies."
chmod +x "$APP_DIR/run_terchess.sh" "$APP_DIR/run_terchess.command"
"$APP_DIR/run_terchess.sh"
