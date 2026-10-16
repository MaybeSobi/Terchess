# Troubleshooting

## `terchess: command not found`

Activate the project's virtual environment and install the package from its root directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
terchess
```

On Windows PowerShell, use `.\.venv\Scripts\Activate.ps1` and then `python -m pip install -e ".[dev]"`.

## Kali or Debian reports an externally managed environment

Install virtual-environment support and use a project-local virtual environment:

```bash
sudo apt update
sudo apt install -y python3-full python3-venv python3-pip
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Do not use `--break-system-packages` for this project.

## Stockfish cannot be found

Install Stockfish from its official download page and choose the executable path in Terchess settings. The Stockfish binary is not bundled with Terchess.

- Linux: the executable may be named `stockfish` and may be available through your distribution's package manager.
- Windows: select the full path to the Stockfish `.exe`.

## Tests cannot import `terchess` or `chess`

From the project root, activate the virtual environment and install the package with its development dependencies:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Unicode pieces or colors render incorrectly

Use a terminal with Unicode support and a font containing chess-piece glyphs. If glyphs remain unsupported, use Blindfold / text-only mode.
