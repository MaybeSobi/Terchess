<div align="center">

# ♟️ Terchess

### Terminal + Chess

**Your terminal. Your board. Your imagination.**

A keyboard-first chess experience powered by a local Stockfish engine — play with a visible terminal board or go full blindfold and keep the position in your head.

[![CI](https://github.com/MaybeSobi/Terchess/actions/workflows/ci.yml/badge.svg)](https://github.com/MaybeSobi/Terchess/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-444444)](#installation)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/License-GPL--3.0--or--later-blue.svg)](LICENSE)

</div>

---

## Why Terchess?

Not every chess game needs a graphical interface. Terchess is for people who love the board — and sometimes would rather imagine it.

### Two ways to play

| ♟️ Board View | 🧠 Blindfold / Text-only |
|---|---|
| A colored terminal chessboard, last-move highlighting, clocks, and move history. | No board diagram or piece glyphs. Follow the game through moves, status, and your mental board. |

Type moves like `e4`, `Nf3`, `O-O`, or coordinate notation such as `e2e4`. Your local Stockfish engine responds in the terminal.

## Features

- **Local Stockfish engine** — no cloud engine or account required.
- **Skill Level 0–20** — choose engine strength. Skill Level is not a direct Elo rating.
- **Board View and Blindfold mode** — choose a visual board or text-only play.
- **Live chess clocks** — time controls with increment presets such as `3+2`.
- **Numbered move history** during the current game.
- **Persistent settings** — remember engine path, side, time control, skill level, and display mode.
- **Cross-platform Python CLI** — designed for Windows, macOS, and Linux.
- **Offline gameplay** once Python dependencies and Stockfish are installed.

## Example session

```text
╭──────────── TERCHESS · Terminal + Chess ────────────╮
│ Local Stockfish · Live clocks · Keyboard-first chess│
╰─────────────────────────────────────────────────────╯

MAIN MENU
  1 · Start game
  2 · Display mode: Board view (toggle)
  3 · Settings
  4 · About Terchess
  5 · Quit

Select option > 1
Your move > e4
Stockfish played: e7e5
Your move > Nf3
```

*Illustrative example; terminal formatting varies by terminal and build.*

## Requirements

- Python **3.10 or newer**
- A Stockfish executable for your operating system
- A terminal with Unicode support (color support recommended)

Download Stockfish from the [official Stockfish website](https://stockfishchess.org/download/). Terchess does **not** bundle the Stockfish executable; download it separately and select its path when prompted. Stockfish is a separate GPLv3 project — see [Third-party notices](THIRD_PARTY_NOTICES.md).

## Installation

Terchess is a **Python terminal application**, not a standalone Windows `.exe`. The same source ZIP works on Windows, macOS, and Linux. You extract it, install its Python dependencies into a virtual environment, and run it from a terminal.

### What you need first

1. **Python 3.10 or newer.** Download it from [python.org](https://www.python.org/downloads/). On macOS, use the [official macOS installer](https://www.python.org/downloads/macos/); on Windows, install the Python launcher (`py`) if offered and enable adding Python to PATH.
2. **Stockfish**, installed separately. Terchess does not bundle the engine. Download it from the [official Stockfish page](https://stockfishchess.org/download/), or use Homebrew on macOS if the formula is available for your Mac.
3. **Internet access for the initial Python dependency installation.** The commands below install `python-chess`, `rich`, and `prompt-toolkit` automatically; you do not need to fetch those libraries individually.

### 1. Download and extract the ZIP

Download **[Terchess-1.0.2.zip](https://github.com/MaybeSobi/Terchess/releases/download/v1.0.2/Terchess-1.0.2.zip)** from the [stable v1.0.2 release](https://github.com/MaybeSobi/Terchess/releases/tag/v1.0.2), then extract it.

- **Windows:** In File Explorer, right-click the ZIP and choose **Extract All…**.
- **macOS:** Double-click the ZIP in Finder; macOS extracts the folder beside it.
- **Kali/Linux:** You can extract the ZIP with your file manager, or install and use `unzip` as shown below.

After extraction, you should have a folder named `Terchess-1.0.2`. Open a terminal **inside that folder**. The project root is the folder containing `pyproject.toml` and the `src` directory. The `cd` examples below assume you extracted it into Downloads; adjust the path if you chose another location.

### Quick launch — recommended

After extracting the ZIP, you can launch Terchess with the script for your operating system. **You only need to double-click the launcher after Python is installed.** On the first launch, it creates a local `.venv` folder and installs Terchess's Python dependencies automatically. Later launches reuse that environment and start the game directly.

- **Windows:** double-click `run_terchess.bat`.
- **macOS:** double-click `run_terchess.command`; it opens Terminal and runs Terchess.
- **Kali/Linux:** double-click `run_terchess.sh`. If your file manager opens it as text instead, right-click and choose **Run in Terminal** or **Run as Program**. You can also launch it from a terminal with `./run_terchess.sh`.

Before using a launcher, install **Python 3.10 or newer**. On Kali/Debian/Ubuntu, ensure `python3-venv` is installed; the manual setup below lists the required system packages. The first launch needs an internet connection to download Python dependencies.

**Stockfish is still a separate one-time install.** The launcher does not install or bundle the chess engine. Install Stockfish for your operating system and select its executable in Terchess when asked. See the operating-system instructions below for the recommended method. If setup fails, the launcher leaves an error message in the terminal window.


### 2. Windows — PowerShell

First, open PowerShell and move into the extracted project folder:

```powershell
cd "$HOME\Downloads\Terchess-1.0.2"
Get-ChildItem pyproject.toml
```

The second command should show `pyproject.toml`. If it says the file cannot be found, you are not in the project root; correct the `cd` path before continuing.

Create a virtual environment, activate it, update pip, install Terchess and its required libraries, then launch the game:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install .
terchess
```

The first install downloads the libraries listed by the project automatically. You do **not** need to install each Python dependency one by one.

**If PowerShell blocks activation:** open Command Prompt (CMD) and run these commands instead. The first path assumes the project is in your Downloads folder:

```bat
cd /d "%USERPROFILE%\Downloads\Terchess-1.0.2"
py -3 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install .
terchess
```

**Optional — development and tests:** If you want to edit Terchess or run its tests, use the development install instead of the normal install command above:

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
```

The `[dev]` extra installs `pytest`; it is not required just to play.

### 3. macOS — Terminal (Apple Silicon and Intel)

#### Install Python and Stockfish

1. Install **Python 3.10 or newer** using the [official macOS installer](https://www.python.org/downloads/macos/). Open Terminal and check the version:

   ```bash
   python3 --version
   ```

   It should report Python 3.10 or newer. If it reports an older version or the command is missing, complete the Python installer, close Terminal, open it again, and retry. Python 3.13 is one of the versions covered by this project's CI.

2. Install **Stockfish** separately. If Homebrew is already installed, the quick option is:

   ```bash
   brew install stockfish
   ```

   If you do not have Homebrew, follow its official instructions at [brew.sh](https://brew.sh) and then run the command above. Alternatively, download a macOS build from the [official Stockfish download page](https://stockfishchess.org/download/). The official download is an alternative if the Homebrew package is unavailable for your macOS version or CPU.

   Check whether Stockfish is on your command path:

   ```bash
   command -v stockfish
   ```

   If this prints nothing, you can enter the engine's full path in Terchess Settings when prompted.

#### Download, extract, and enter the project directory

Download [Terchess-1.0.2.zip](https://github.com/MaybeSobi/Terchess/releases/download/v1.0.2/Terchess-1.0.2.zip) from the [stable release page](https://github.com/MaybeSobi/Terchess/releases/tag/v1.0.2). In Finder, double-click the ZIP to extract it. If you saved it to Downloads, open Terminal and enter the extracted project folder:

```bash
cd "$HOME/Downloads/Terchess-1.0.2"
ls pyproject.toml
```

The last command should show `pyproject.toml`. If the file is not found, adjust `cd` to the directory where you extracted the ZIP. You must be in the project root—the folder containing `pyproject.toml` and `src/`—before installing.

#### Create the environment, install, and launch

Run these commands from the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
terchess
```

The install command downloads the Python libraries required by Terchess automatically. You do not need to install `python-chess`, `rich`, or `prompt-toolkit` manually. Keep the `.venv` folder inside the project directory.

For development or to run the test suite, install the optional development tools instead:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

When you open a new Terminal window later, return to the project directory and reactivate the environment:

```bash
cd "$HOME/Downloads/Terchess-1.0.2"
source .venv/bin/activate
terchess
```

### 4. Kali Linux / Debian / Ubuntu

Open a terminal. Install Python's virtual-environment tools and the Stockfish engine from your distribution's package manager:

```bash
sudo apt update
sudo apt install -y python3-full python3-venv python3-pip unzip stockfish
```

Download `Terchess-1.0.2.zip` from the [releases page](https://github.com/MaybeSobi/Terchess/releases), then extract it. For a ZIP saved in Downloads, these commands make a Projects folder, extract the archive, and enter the project root:

```bash
mkdir -p ~/Projects
unzip ~/Downloads/Terchess-1.0.2.zip -d ~/Projects
cd ~/Projects/Terchess-1.0.2
ls
```

Check that the listing includes `pyproject.toml` and `src`. Then create and activate a virtual environment, install the project, and launch it:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
terchess
```

If you extracted the ZIP somewhere else, change the `cd` path to that folder. If your Kali/Debian repositories cannot find the `stockfish` package, install a Linux build from the [official Stockfish download page](https://stockfishchess.org/download/) and select its executable in Terchess.

**Optional — development and tests:** From the project root with the virtual environment active:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

Do not use `sudo pip` or `--break-system-packages`. Keep the project's Python packages inside its `.venv` environment.

### 5. Stockfish on first launch

Terchess needs the Stockfish **engine executable** to play against the computer. Installing Terchess's Python libraries does not install Stockfish.

- **Windows:** Download and extract Stockfish, then choose or enter the full path to its `.exe` when Terchess asks for the engine. The exact filename depends on the build you downloaded.
- **macOS:** With Homebrew, the command is normally `stockfish`; check it using `command -v stockfish`. If Terchess does not detect it, choose the executable in Settings or pass its full path.
- **Kali/Linux:** The package-manager install above usually makes the executable available as `stockfish`. If Terchess does not detect it, choose its path or provide the executable path in Terchess settings.

After installation, keep the `.venv` folder with the project. When opening a new terminal later, `cd` back into the project folder, activate the virtual environment (` .\.venv\Scripts\Activate.ps1` on PowerShell or `source .venv/bin/activate` on macOS/Linux), and run `terchess` again.

## First launch

1. Run `terchess`.
2. If Stockfish is not detected, enter the path to its executable.
3. Choose **Start game**.
4. In **Settings**, choose your side, time control, and Stockfish Skill Level from `0` to `20`.
5. Use **Display mode** to toggle Board View / Blindfold text-only mode.

Settings are stored outside the project directory and persist across restarts:

- **Windows:** `%APPDATA%\Terchess\config.json`
- **Linux:** `$XDG_CONFIG_HOME/terchess/config.json`, or `~/.config/terchess/config.json`
- **macOS:** `~/Library/Application Support/Terchess/config.json`

Override the saved engine path for one run:

```bash
terchess --engine /path/to/stockfish
```

On Windows, provide the full path to the Stockfish `.exe`.

## Controls

| Input | Action |
|---|---|
| `e4`, `Nf3`, `Qxd5` | Enter a move in SAN notation |
| `e2e4` | Enter a coordinate move |
| `O-O`, `0-0` | Castle kingside |
| `help` | Show move-entry help |
| `moves` | Print move history |
| `resign` | Resign the current game |
| `menu` | Return to the main menu |

## Tests

With the virtual environment active, run:

```bash
python -m pytest
```

The stable `v1.0.2` release includes one-click launch scripts for Windows, macOS, and Linux. GitHub Actions tests Python 3.10–3.13 on all three operating systems. The [release checklist](RELEASE_CHECKLIST.md) remains useful when testing future changes.

## Roadmap

### `1.0.2` — One-click launchers · **Released 2026-10-16**

Add launch scripts for Windows, macOS, and Linux that create a private Python environment and install application dependencies on first run.

### `1.0.1` — macOS support · **Released 2026-10-16**

Add step-by-step macOS installation instructions, Stockfish setup options, and automated CI coverage on macOS for Python 3.10–3.13.

### `1.0.0` — Stable offline release · **Released 2026-10-16**

The first stable release includes local Stockfish gameplay, Board View / Blindfold mode, clocks, legal move validation, persistent settings, cross-platform installation instructions, and automated CI tests.

### `1.1.0` — Game History + play with friends

- **Game History:** browse previous games and export/import PGN.
- **Hotseat:** two people play on the same computer and terminal, taking turns.
- **LAN multiplayer:** host or join a local-network game with a friend on another machine.
- Graceful disconnect handling, rematches, and game termination.

### `1.2.0` — Stockfish analysis

- Analyze completed games with Stockfish.
- Show evaluation swings and best-move suggestions.
- Label inaccuracies, mistakes, and blunders.
- Explore a **brilliant move** heuristic while explaining that move labels vary between analysis products.

## Contributing

Bug reports, compatibility feedback, and improvements are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) and use the issue templates when reporting a problem.

## License

Terchess is distributed under **GPL-3.0-or-later**. See [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for license and dependency notes.

<div align="center">

**Terchess — Your terminal. Your board. Your imagination.** ♟️

</div>
