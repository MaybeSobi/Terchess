# Troubleshooting

## Start in the project root

Most commands must be run from the extracted Terchess folder: the folder containing `pyproject.toml` and `src/`.

For example, if you extracted the ZIP into Downloads:

- Windows PowerShell: `cd "$HOME\Downloads\Terchess-1.0.0-rc2"`
- Kali/Linux: `cd ~/Projects/Terchess-1.0.0-rc2` (use the path where you extracted it)

If `pyproject.toml` is not in the current directory, use `cd` to enter the correct folder before creating the environment or installing the project.

For full first-time setup—including downloading/extracting the ZIP, installing Python and Stockfish, and platform-specific commands—see the [Installation section in README.md](README.md#installation).

## `py` or `python3` is not recognized

Install Python 3.10 or newer from [python.org](https://www.python.org/downloads/). On Windows, try `py --version`; on Kali/Linux, try `python3 --version`. Reopen the terminal after installing Python.

## Virtual environment activation fails on Windows

In PowerShell, run the activation command from the project root:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks the script, use Command Prompt (CMD) and run:

```bat
.venv\Scripts\activate.bat
```

## `terchess: command not found`

Make sure the project's virtual environment is active and install the project from the project root:

```bash
python -m pip install .
terchess
```

On Windows, first activate `.venv\Scripts\Activate.ps1` in PowerShell or `.venv\Scripts\activate.bat` in CMD. On Kali/Linux, activate it with `source .venv/bin/activate`.

If you want to edit the source or run tests, install the development extra instead:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Kali or Debian reports an externally managed environment

Use a project-local virtual environment; do not use `sudo pip` or `--break-system-packages`:

```bash
sudo apt update
sudo apt install -y python3-full python3-venv python3-pip
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

## Stockfish cannot be found

Stockfish is a separate executable and is not bundled in the Terchess ZIP.

- **Kali/Linux:** try `sudo apt install stockfish`, then check `command -v stockfish`.
- **Windows:** download and extract Stockfish from the [official website](https://stockfishchess.org/download/), then enter or select the full path to its `.exe` in Terchess.

## Tests cannot import `terchess`, `chess`, or other dependencies

From the project root, activate `.venv`, then run:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Unicode pieces or colors render incorrectly

Use a terminal with Unicode support and a font containing chess-piece glyphs. If glyphs remain unsupported, use Blindfold / text-only mode.
