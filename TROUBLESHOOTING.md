# Troubleshooting

## Start in the project root

Most commands must be run from the extracted Terchess folder: the folder containing `pyproject.toml` and `src/`.

For example, if you extracted the ZIP into Downloads:

- Windows PowerShell: `cd "$HOME\Downloads\Terchess-1.0.2"`
- Kali/Linux: `cd ~/Projects/Terchess-1.0.2` (use the path where you extracted it)
- macOS Terminal: `cd "$HOME/Downloads/Terchess-1.0.2"` (adjust for your chosen location)

If `pyproject.toml` is not in the current directory, use `cd` to enter the correct folder before creating the environment or installing the project.

For full first-time setup—including downloading/extracting the ZIP, installing Python and Stockfish, and platform-specific commands—see the [Installation section in README.md](README.md#installation).

## `py` or `python3` is not recognized

Install Python 3.10 or newer from [python.org](https://www.python.org/downloads/). On Windows, try `py --version`; on macOS/Linux, try `python3 --version`. Reopen the terminal after installing Python.

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

## Windows installer does not detect an existing Stockfish build

One-command installers search the saved engine path, registered engines, PATH, standard system locations, and common manual-install/download folders before downloading anything. Each candidate is checked with UCI and must expose Skill Level 0–20. If the latest official release is missing, the installer offers to switch Terchess to it, keep both versions in separate folders, or defer the update. Side-by-side installs trigger an engine selector every time Terchess starts until **Remember my choice** is enabled. Run `terchess --choose-engine` to reopen the selector. New downloads are SHA-256 verified against the official GitHub release.

## Stockfish cannot be found

Stockfish is a separate executable and is not bundled in the manual Terchess ZIP. The one-command installers first search your existing Stockfish locations and only download when a compatible latest version is not already available or you choose to update.

- **One-command installer:** rerun the installer; it detects existing Stockfish engines and offers to replace the Terchess-selected version, install the latest alongside it, or defer the update.
- **Manual installation:** download the latest stable official Stockfish build for your OS from the [official website](https://stockfishchess.org/download/) and select its executable in Terchess Settings.
- **Kali/Linux:** the distro package may be older (such as 17.1); the one-command installer deliberately does not use it as the final engine.

## Tests cannot import `terchess`, `chess`, or other dependencies

From the project root, activate `.venv`, then run:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Unicode pieces or colors render incorrectly

Use a terminal with Unicode support and a font containing chess-piece glyphs. If glyphs remain unsupported, use Blindfold / text-only mode.


## One-click launcher cannot start

- **Windows:** double-click `run_terchess.bat`. If the message says Python is missing or too old, install Python 3.10 or newer and retry.
- **macOS:** double-click `run_terchess.command`. If needed, open Terminal in the project folder and run `./run_terchess.command`.
- **Kali/Linux:** make sure `python3-full` and `python3-venv` are installed, then run `./run_terchess.sh` from the project folder. If the file is not executable, run `chmod +x run_terchess.sh` once and retry.
- All platforms need internet access on the first launch so pip can install the project's Python dependencies.
- Stockfish is separate from Terchess. Install it for your OS and select its executable in the game if it is not detected automatically.

The launcher stores the Python environment in `.venv/` next to the project. Keep that folder with the extracted project; if you move or re-extract the project to a new directory, run the launcher again to create a fresh environment.


## Reinstalling or updating Terchess

The one-command installers preserve an existing `.venv` when refreshing the application files. They check the project's declared Python dependencies and reinstall only the Terchess package itself, so an ordinary repeat install does not rebuild the virtual environment. If the environment is damaged or cannot be updated, the installer reports the failure rather than silently claiming the update succeeded.

## Launch Terchess with the `terchess` command

The one-command installers register a user-level `terchess` command; no desktop shortcut is created.

- **Windows:** the installer creates `terchess.cmd` in `%LOCALAPPDATA%\Programs\Terchess`, adds that directory to your user PATH, and updates the current PowerShell session. If a new terminal cannot find the command, close and reopen the terminal.
- **Linux/macOS:** the installer creates `~/.local/bin/terchess` and adds `~/.local/bin` to the detected shell startup file. Open a new terminal after installation. In an existing Bash or Zsh terminal, run `export PATH="$HOME/.local/bin:$PATH"`.
- **Manual ZIP installation:** activate the project's `.venv` before using `terchess`; the global command is registered by the one-command installers.

Check the command with:

```bash
terchess --version
```
