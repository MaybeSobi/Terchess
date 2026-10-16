<div align="center">

# ♟️ Terchess

### Terminal + Chess

**Your terminal. Your board. Your imagination.**

A keyboard-first chess experience powered by a local Stockfish engine — play with a visible terminal board or go full blindfold and keep the position in your head.

[![CI](https://github.com/MaybeSobi/Terchess/actions/workflows/ci.yml/badge.svg)](https://github.com/MaybeSobi/Terchess/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Windows-Linux-444444?logo=linux&logoColor=white)](#installation)
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
- **Cross-platform Python CLI** — designed for Windows and Linux.
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

### Windows — PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
terchess
```

If PowerShell blocks script activation, use Command Prompt instead:

```bat
.venv\Scripts\activate.bat
python -m pip install -e ".[dev]"
terchess
```

### Linux (including Kali Linux)

Install virtual-environment support first:

```bash
sudo apt update
sudo apt install -y python3-full python3-venv python3-pip
```

From the extracted project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
terchess
```

> **Kali/Linux note:** Bash uses `python3 -m venv` and `source .venv/bin/activate`. Commands like `py -3.13` and `.\.venv\Scripts\Activate.ps1` are for Windows, not Linux. Install packages inside the virtual environment; do not use `--break-system-packages`.

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

GitHub Actions is configured to run tests on Windows and Ubuntu. Before the stable `1.0.0` release, complete the manual checks in [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) on real systems.

## Roadmap

### `1.0.0` — Stable offline release

Stabilize local Stockfish play, Board View / Blindfold mode, clocks, legal move validation, persistent settings, installation, and automated tests.

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
