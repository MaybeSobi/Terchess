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

info "Installing the official, checksum-verified Stockfish 19 Android build..."
curl -fsSL "https://raw.githubusercontent.com/MaybeSobi/Terchess/main/scripts/install_stockfish.py" -o "$TMP_DIR/install_stockfish.py"
"$PYTHON_BIN" "$TMP_DIR/install_stockfish.py"

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
