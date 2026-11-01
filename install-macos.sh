#!/usr/bin/env bash
set -euo pipefail

REPO="MaybeSobi/Terchess"
APP_DIR="$HOME/Applications/Terchess"
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

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is needed to install Python and Stockfish automatically on macOS."
  read -r -p "Install Homebrew now from its official installer? [y/N] " answer
  case "$answer" in
    y|Y|yes|YES)
      /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
      ;;
    *)
      echo "Install Homebrew from https://brew.sh, then rerun this installer."
      exit 1
      ;;
  esac
  if [[ -x /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [[ -x /usr/local/bin/brew ]]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
fi

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew was not found after installation. Open a new Terminal and rerun this installer."
  exit 1
fi

info "Installing/checking Python with Homebrew..."
brew install python || warn "Homebrew reported a Python install issue; checking whether Python is available."
info "Installing/checking Stockfish with Homebrew..."
brew install stockfish || warn "Stockfish could not be installed automatically; it can be installed separately."

if ! command -v python3 >/dev/null 2>&1 || ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)'; then
  echo "Python 3.10+ is required. Install it from https://www.python.org/downloads/macos/ and rerun."
  exit 1
fi

if STOCKFISH_PATH="$(command -v stockfish 2>/dev/null)"; then
  if python3 - "$STOCKFISH_PATH" "macos" <<'PY'
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

engine_path = str(Path(sys.argv[1]).expanduser().resolve())
platform_name = sys.argv[2]

try:
    result = subprocess.run(
        [engine_path],
        input="uci\nquit\n",
        capture_output=True,
        text=True,
        timeout=8,
        check=False,
    )
except (OSError, subprocess.SubprocessError) as exc:
    print(f"Stockfish could not be started: {exc}", file=sys.stderr)
    raise SystemExit(1)

if result.returncode != 0 or "uciok" not in result.stdout.splitlines():
    print("Stockfish did not complete a successful UCI handshake.", file=sys.stderr)
    raise SystemExit(1)

match = re.search(
    r"(?m)^option name Skill Level type spin default -?\d+ min (-?\d+) max (-?\d+)\s*$",
    result.stdout,
)
if not match:
    print("The engine does not expose the UCI Skill Level option.", file=sys.stderr)
    raise SystemExit(1)

minimum, maximum = map(int, match.groups())
if minimum > 0 or maximum < 20:
    print(f"The engine supports Skill Level {minimum}–{maximum}, not the full 0–20 range.", file=sys.stderr)
    raise SystemExit(1)

if platform_name == "macos":
    config_path = Path.home() / "Library" / "Application Support" / "Terchess" / "config.json"
else:
    xdg_home = os.environ.get("XDG_CONFIG_HOME")
    xdg_path = Path(xdg_home).expanduser() if xdg_home else None
    config_root = xdg_path if xdg_path and xdg_path.is_absolute() else Path.home() / ".config"
    config_path = config_root / "terchess" / "config.json"

config = {}
if config_path.exists():
    try:
        with config_path.open("r", encoding="utf-8") as stream:
            config = json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"Existing Terchess settings could not be read ({exc}); they were left unchanged.", file=sys.stderr)
        raise SystemExit(2)
    if not isinstance(config, dict):
        print("Existing Terchess settings are not a JSON object; they were left unchanged.", file=sys.stderr)
        raise SystemExit(2)

config["stockfish_path"] = engine_path
config_path.parent.mkdir(parents=True, exist_ok=True)
mode = stat.S_IMODE(config_path.stat().st_mode) if config_path.exists() else 0o600
fd, temporary_path = tempfile.mkstemp(
    prefix=config_path.name + ".",
    suffix=".tmp",
    dir=str(config_path.parent),
)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(config, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(temporary_path, mode)
    os.replace(temporary_path, config_path)
except OSError:
    try:
        os.unlink(temporary_path)
    except OSError:
        pass
    raise

print(f"Validated Stockfish Skill Level 0–20 and saved its path to {config_path}.")
PY
  then
    info "Stockfish supports Terchess Skill Level 0–20; its path was saved."
  else
    warn "Stockfish failed the Skill Level 0–20 check, or settings could not be updated safely. Its path was not saved."
  fi
else
  warn "Stockfish was not found on PATH. Install it separately and select its executable in Terchess Settings."
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
mkdir -p "$APP_DIR"

# Preserve the existing environment and replace only the application files.
find "$APP_DIR" -mindepth 1 -maxdepth 1 ! -name ".venv" -exec rm -rf -- {} +
cp -R "$PROJECT_DIR/." "$APP_DIR/"
chmod +x "$APP_DIR/run_terchess.sh" "$APP_DIR/run_terchess.command"

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
