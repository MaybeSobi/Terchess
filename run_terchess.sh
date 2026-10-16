#!/usr/bin/env bash
set -u

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR" || exit 1

finish() {
  status=$?
  if [[ -t 0 ]]; then
    printf '\n'
    if [[ $status -eq 0 ]]; then
      echo "Terchess has exited."
    else
      echo "Terchess could not start or exited with status $status."
    fi
    read -r -p "Press Enter to close this window..." _ || true
  fi
}
trap finish EXIT

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.10 or newer is required."
  echo "Install Python from https://www.python.org/downloads/ and try again."
  exit 1
fi

if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo "Python 3.10 or newer is required. Please upgrade Python and try again."
  exit 1
fi

if [[ ! -x ".venv/bin/python" ]]; then
  echo "First run: creating a private Python environment..."
  python3 -m venv .venv || {
    echo "Could not create the environment."
    echo "On Debian/Kali/Ubuntu, install python3-full and python3-venv, then run this launcher again."
    exit 1
  }
fi

VENV_PYTHON=".venv/bin/python"

if ! "$VENV_PYTHON" -c 'import chess, rich, prompt_toolkit, terchess' >/dev/null 2>&1; then
  echo "First run: installing Terchess and its Python dependencies..."
  "$VENV_PYTHON" -m pip install --upgrade pip || {
    echo "Could not upgrade pip. Check your internet connection and try again."
    exit 1
  }
  "$VENV_PYTHON" -m pip install . || {
    echo "Installation failed. Check your internet connection and Python version, then try again."
    exit 1
  }
fi

echo "Starting Terchess..."
"$VENV_PYTHON" -m terchess
