#!/usr/bin/env bash
set -euo pipefail

REPO="MaybeSobi/Terchess"
APP_DIR="$HOME/.local/share/terchess"
TMP_DIR="$(mktemp -d)"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

info() { printf '\033[1;36m[Terchess]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[Terchess]\033[0m %s\n' "$*"; }


install_terchess_command() {
  local bin_dir="$HOME/.local/bin"
  local command_path="$bin_dir/terchess"
  mkdir -p "$bin_dir"

  if [[ -e "$command_path" || -L "$command_path" ]] && ! grep -Fq '# TERCHESS_MANAGED_COMMAND' "$command_path" 2>/dev/null; then
    warn "A different command already exists at $command_path; leaving it untouched."
  else
    cat > "$command_path" <<TERCHESS_COMMAND
#!/usr/bin/env bash
# TERCHESS_MANAGED_COMMAND
APP_DIR="$APP_DIR"
VENV_PYTHON="\$APP_DIR/.venv/bin/python"

if [[ -x "\$VENV_PYTHON" ]]; then
  exec "\$VENV_PYTHON" -m terchess "\$@"
fi

exec "\$APP_DIR/run_terchess.sh" "\$@"
TERCHESS_COMMAND
    chmod +x "$command_path"
  fi

  add_path_block() {
    local startup_file="$1"
    local path_line="$2"
    mkdir -p "$(dirname "$startup_file")"
    touch "$startup_file"
    if grep -Fq 'TERCHESS CLI PATH' "$startup_file" || grep -Eq '(^|[[:space:]])(export[[:space:]]+)?PATH=.*\.local/bin|fish_add_path.*\.local/bin' "$startup_file"; then
      return
    fi
    {
      printf '\n# >>> TERCHESS CLI PATH >>>\n'
      printf '%s\n' "$path_line"
      printf '# <<< TERCHESS CLI PATH <<<\n'
    } >> "$startup_file"
  }

  case "${SHELL##*/}" in
    bash)
      add_path_block "$HOME/.bashrc" 'case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) export PATH="$HOME/.local/bin:$PATH" ;; esac'
      if [[ -f "$HOME/.bash_profile" ]]; then
        add_path_block "$HOME/.bash_profile" 'case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) export PATH="$HOME/.local/bin:$PATH" ;; esac'
      else
        add_path_block "$HOME/.profile" 'case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) export PATH="$HOME/.local/bin:$PATH" ;; esac'
      fi
      ;;
    zsh)
      add_path_block "$HOME/.zshrc" 'case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) export PATH="$HOME/.local/bin:$PATH" ;; esac'
      ;;
    fish)
      add_path_block "$HOME/.config/fish/config.fish" 'if not contains -- "$HOME/.local/bin" $PATH; set -gx PATH "$HOME/.local/bin" $PATH; end'
      ;;
    *)
      add_path_block "$HOME/.profile" 'case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) export PATH="$HOME/.local/bin:$PATH" ;; esac'
      ;;
  esac

  if [[ ":$PATH:" == *":$HOME/.local/bin:"* ]]; then
    info "The 'terchess' command is available in this terminal."
  else
    info "Added ~/.local/bin to your shell startup file."
    info "Open a new terminal to use 'terchess', or add ~/.local/bin to PATH in this terminal."
  fi
}

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
  install_packages apt-get install -y python3 python3-venv python3-pip curl unzip
elif command -v dnf >/dev/null 2>&1; then
  install_packages dnf install -y python3 python3-pip curl unzip
elif command -v pacman >/dev/null 2>&1; then
  install_packages pacman -S --needed --noconfirm python python-pip curl unzip
elif command -v zypper >/dev/null 2>&1; then
  install_packages zypper --non-interactive install python3 python3-pip curl unzip
else
  echo "Unsupported package manager. Install Python 3.10+, curl, and unzip manually."
  echo "Python: https://www.python.org/downloads/"
  echo "Stockfish: https://stockfishchess.org/download/"
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1 || ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)'; then
  echo "Python 3.10+ is required. Your distribution may need a newer Python package."
  exit 1
fi

info "Installing the official, checksum-verified Stockfish 19 build..."
curl -fsSL "https://raw.githubusercontent.com/MaybeSobi/Terchess/main/scripts/install_stockfish.py" -o "$TMP_DIR/install_stockfish.py"
python3 "$TMP_DIR/install_stockfish.py"

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
mkdir -p "$APP_DIR"

# Preserve the existing environment and replace only the application files.
find "$APP_DIR" -mindepth 1 -maxdepth 1 ! -name ".venv" -exec rm -rf -- {} +
cp -R "$PROJECT_DIR/." "$APP_DIR/"
chmod +x "$APP_DIR/run_terchess.sh"

# Resolve dependencies and refresh only Terchess inside the existing environment.
VENV_PYTHON="$APP_DIR/.venv/bin/python"
if [[ -x "$VENV_PYTHON" ]]; then
  info "Updating Terchess inside the existing Python environment..."
  "$VENV_PYTHON" -m pip install --disable-pip-version-check "$APP_DIR"
  "$VENV_PYTHON" -m pip install --disable-pip-version-check --force-reinstall --no-deps "$APP_DIR"
fi

install_terchess_command

info "Installed to $APP_DIR"
info "Launching Terchess. First launch creates the Python environment only when needed."
"$APP_DIR/run_terchess.sh"
