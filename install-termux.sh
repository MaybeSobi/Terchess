#!/usr/bin/env bash
set -Eeuo pipefail

REPO="MaybeSobi/Terchess"
APP_DIR="$HOME/.local/share/terchess"
TMP_DIR="$(mktemp -d)"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

info() { printf '\033[1;36m[Terchess]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[Terchess]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[Terchess]\033[0m %s\n' "$*" >&2; exit 1; }

# Termux exposes its own prefix and pkg command. Do not mistake Android's
# Linux kernel and apt compatibility wrapper for a desktop Linux distro.
if [[ -z "${PREFIX:-}" || "$PREFIX" != */com.termux/files/usr ]]; then
  fail "This installer must be run inside the Termux app."
fi
if [[ ! -x "$PREFIX/bin/pkg" ]] || ! command -v pkg >/dev/null 2>&1; then
  fail "Termux's pkg command was not found. Open the official Termux app and try again."
fi
if [[ "$(uname -s)" != "Linux" ]]; then
  fail "Termux on Android is required."
fi
COMMAND_PATH="$PREFIX/bin/terchess"

info "Preparing Termux packages..."
pkg update -y
pkg install -y python curl unzip

PYTHON_BIN="$(command -v python || command -v python3 || true)"
[[ -n "$PYTHON_BIN" ]] || fail "Python could not be found after installing the Termux python package."
if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)'; then
  fail "Python 3.10 or newer is required."
fi

if ! command -v stockfish >/dev/null 2>&1; then
  info "Stockfish was not found; attempting to install the optional engine..."
  if ! pkg install -y stockfish; then
    warn "Stockfish could not be installed. Terchess will still work for Hotseat, history, PGN, and opening lookup."
  fi
fi

info "Downloading Terchess from the current main branch..."
curl -fL --retry 2 "https://codeload.github.com/${REPO}/zip/refs/heads/main" -o "$TMP_DIR/Terchess-main.zip"
mkdir -p "$TMP_DIR/extract"
unzip -q "$TMP_DIR/Terchess-main.zip" -d "$TMP_DIR/extract"
PROJECT_FILE="$(find "$TMP_DIR/extract" -name pyproject.toml -type f -print -quit)"
[[ -n "$PROJECT_FILE" ]] || fail "The downloaded source archive does not contain pyproject.toml."
PROJECT_DIR="$(dirname "$PROJECT_FILE")"

mkdir -p "$APP_DIR"
# Preserve the existing virtual environment; replace only application files.
find "$APP_DIR" -mindepth 1 -maxdepth 1 ! -name ".venv" -exec rm -rf -- {} +
cp -R "$PROJECT_DIR/." "$APP_DIR/"

VENV_PYTHON="$APP_DIR/.venv/bin/python"
if [[ ! -x "$VENV_PYTHON" ]]; then
  info "Creating a private Python environment..."
  "$PYTHON_BIN" -m venv "$APP_DIR/.venv" || fail "Could not create the Python environment in $APP_DIR/.venv."
fi
[[ -x "$VENV_PYTHON" ]] || fail "The private Python interpreter was not created."

info "Installing Terchess and its Python dependencies..."
"$VENV_PYTHON" -m pip install --disable-pip-version-check --force-reinstall "$APP_DIR"

if command -v stockfish >/dev/null 2>&1; then
  STOCKFISH_PATH="$(command -v stockfish)"
  info "Validating the Stockfish UCI engine..."
  if "$PYTHON_BIN" - "$STOCKFISH_PATH" <<'PY'
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

engine_path = str(Path(sys.argv[1]).expanduser().resolve())
try:
    result = subprocess.run(
        [engine_path],
        input="uci\nquit\n",
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
except (OSError, subprocess.SubprocessError) as exc:
    print(f"Stockfish could not be started: {exc}")
    raise SystemExit(1)

if result.returncode != 0 or "uciok" not in result.stdout.splitlines():
    print("Stockfish did not complete a successful UCI handshake.")
    raise SystemExit(1)

match = re.search(
    r"(?m)^option name Skill Level type spin default -?\d+ min (-?\d+) max (-?\d+)\s*$",
    result.stdout,
)
if not match:
    print("The engine does not expose the UCI Skill Level option.")
    raise SystemExit(1)
minimum, maximum = map(int, match.groups())
if minimum > 0 or maximum < 20:
    print(f"Stockfish Skill Level range {minimum}–{maximum} does not cover 0–20.")
    raise SystemExit(1)

xdg_home = os.environ.get("XDG_CONFIG_HOME")
xdg_path = Path(xdg_home).expanduser() if xdg_home else None
config_root = xdg_path if xdg_path and xdg_path.is_absolute() else Path.home() / ".config"
config_path = config_root / "terchess" / "config.json"
config = {}
if config_path.exists():
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"Existing settings were left unchanged: {exc}")
        raise SystemExit(2)
    if not isinstance(config, dict):
        print("Existing settings are not a JSON object; they were left unchanged.")
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
    info "Stockfish is ready for computer games."
  else
    warn "Stockfish was found but could not be validated or saved; select its path in Terchess Settings."
  fi
else
  warn "No Stockfish engine is installed. Computer games need Stockfish; other modes remain available."
fi

mkdir -p "$PREFIX/bin"
if [[ -e "$COMMAND_PATH" || -L "$COMMAND_PATH" ]] && ! grep -Fq '# TERCHESS_MANAGED_COMMAND' "$COMMAND_PATH" 2>/dev/null; then
  warn "$COMMAND_PATH already exists and is not managed by Terchess; it was left untouched."
else
  cat > "$COMMAND_PATH" <<'TERCHESS_COMMAND'
#!/usr/bin/env bash
# TERCHESS_MANAGED_COMMAND
APP_DIR="$HOME/.local/share/terchess"
VENV_PYTHON="$APP_DIR/.venv/bin/python"
if [[ -x "$VENV_PYTHON" ]]; then
  exec "$VENV_PYTHON" -m terchess "$@"
fi
printf '%s\n' "Terchess's Python environment is missing. Re-run the Termux installer." >&2
exit 1
TERCHESS_COMMAND
  chmod 755 "$COMMAND_PATH"
  info "Registered the 'terchess' command in Termux's PATH."
fi

info "Installation complete."
info "Run: terchess"
info "Check: terchess --version"
