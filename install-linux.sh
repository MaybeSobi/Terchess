#!/usr/bin/env bash
set -euo pipefail

REPO="MaybeSobi/Terchess"
APP_DIR="$HOME/.local/share/terchess"
TMP_DIR="$(mktemp -d)"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

info() { printf '\033[1;36m[Terchess]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[Terchess]\033[0m %s\n' "$*"; }

install_packages() {
  if [[ $EUID -eq 0 ]]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    echo "Package installation requires root or sudo privileges."
    exit 1
  fi
}

info "Checking system packages..."
if command -v apt-get >/dev/null 2>&1; then
  install_packages apt-get update
  install_packages apt-get install -y python3 python3-venv python3-pip curl unzip stockfish
elif command -v dnf >/dev/null 2>&1; then
  install_packages dnf install -y python3 python3-pip curl unzip stockfish
elif command -v pacman >/dev/null 2>&1; then
  install_packages pacman -Sy --needed --noconfirm python python-pip curl unzip stockfish
elif command -v zypper >/dev/null 2>&1; then
  install_packages zypper --non-interactive install python3 python3-pip curl unzip stockfish
else
  echo "Unsupported package manager. Install Python 3.10+, curl, unzip, and Stockfish manually."
  echo "Python: https://www.python.org/downloads/"
  echo "Stockfish: https://stockfishchess.org/download/"
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1 || ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)'; then
  echo "Python 3.10+ is required. Your distribution may need a newer Python package."
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
unzip -q "$TMP_DIR/Terchess.zip" -d "$TMP_DIR/extract"
PROJECT_FILE="$(find "$TMP_DIR/extract" -name pyproject.toml -type f -print -quit)"
if [[ -z "$PROJECT_FILE" ]]; then
  echo "The downloaded archive does not contain pyproject.toml."
  exit 1
fi
PROJECT_DIR="$(dirname "$PROJECT_FILE")"

mkdir -p "$(dirname "$APP_DIR")"
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR"
cp -R "$PROJECT_DIR/." "$APP_DIR/"
chmod +x "$APP_DIR/run_terchess.sh"

info "Installed to $APP_DIR"
info "Launching Terchess. First launch installs its Python dependencies."
"$APP_DIR/run_terchess.sh"
