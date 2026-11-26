<div align="center">

### Terminal + Chess

**Your terminal. Your board. Your imagination.**

A keyboard-first, offline-first chess application for **Windows, macOS, Linux, and Android (Termux)**.

Play Stockfish locally, train your visualization with Blindfold mode, challenge a friend in Hotseat, and review your games — all without leaving the terminal.

[![CI](https://github.com/MaybeSobi/Terchess/actions/workflows/ci.yml/badge.svg)](https://github.com/MaybeSobi/Terchess/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Platforms](https://img.shields.io/badge/Platforms-Windows%20%7C%20macOS%20%7C%20Linux%20%7C%20Termux-444444)](#installation)
[![License](https://img.shields.io/badge/License-GPL--3.0--or--later-blue.svg)](LICENSE)

</div>

<p align="center">
  <img src="terchess-demo.gif" alt="Terchess running in a terminal" width="850">
</p>

---

## What makes Terchess different?

Terchess brings the full chess experience into your terminal — including a way to play without seeing the board.

| Board View | Blindfold Mode |
|:--:|:--:|
| An adaptive-size chessboard with native Unicode symbols, selectable color themes, move highlights, clocks, and move history. | A text-only game: follow algebraic moves and keep the position in your head. |

Choose the way you want to think about chess. Switch display modes in the app.

### Why don't the chess symbols grow with the board?

Terchess uses the terminal's native Unicode chess characters (`♔ ♕ ♖ ♗ ♘ ♙`) so the pieces keep their familiar, consistent appearance. These symbols are text glyphs supplied by the terminal font, not images that the application can resize independently. Terchess can enlarge the board squares and add empty space around each symbol, but it cannot make just one glyph taller or wider while keeping the terminal's character grid aligned. Increasing the terminal font size would enlarge the entire interface — including labels, clocks, and move history — not only the pieces. For that reason, the board is responsive while the chess symbols remain at the terminal's normal font size.

## Features

- **Play against Stockfish** — run a local engine; no cloud engine or account required.
- **Adjustable engine strength** — Skill Level 0–20 (not a direct Elo rating).
- **Blindfold chess** — play text-only, without a board diagram or piece glyphs.
- **Timed Hotseat** — two players, one device, with chess clocks and increment controls.
- **Game history** — completed games are saved locally in SQLite.
- **PGN tools** — import games, export a selected game or your collection, and replay moves.
- **Offline opening recognition** — identify opening names and ECO codes as the game develops.
- **Board color themes** — choose Classic Wood, Green, Blue, Pink, or Purple from Settings; your choice is saved across sessions.
- **Persistent settings** — save your preferred side, time control, display mode, board size and colors, skill level, and engine path.
- **Cross-platform terminal UI** — including a compact, portrait-friendly layout for Android via Termux.
- **Offline after setup** — gameplay and opening recognition do not require a network connection.

Stockfish is optional for Hotseat, game history, PGN tools, and opening lookup. The engine is distributed separately; Terchess does not bundle it in the app archive. One-command installers first search for an existing compatible Stockfish in your settings, PATH, common system folders, and user download/install folders. If an older version is found, choose to switch to the latest official release, keep both versions side by side, or defer the update. When both are kept, Terchess shows an engine selector at startup; **Remember my choice** saves your preference. Run `terchess --choose-engine` to show the selector again.

## Installation

### One-command installer

Choose your platform and run the matching command:

**Windows — PowerShell**
```powershell
irm https://raw.githubusercontent.com/MaybeSobi/Terchess/main/installers/install.ps1 | iex
```

**macOS — Terminal**
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/MaybeSobi/Terchess/main/installers/install-macos.sh)
```

**Linux — Terminal**
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/MaybeSobi/Terchess/main/installers/install-linux.sh)
```

**Android — Termux**
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/MaybeSobi/Terchess/main/installers/install-termux.sh)
```

After installation, launch Terchess from any terminal:

```console
terchess
terchess --version
terchess --choose-engine
```

Use `terchess --choose-engine` to reopen the Stockfish selector after you have remembered a preferred engine.

> **Engine:** One-command installers discover existing Stockfish binaries first, verify their UCI version and Skill Level range, and offer an update or side-by-side installation when needed. New downloads are verified against the official SHA-256 digest. Manual ZIP installs still require a separate Stockfish download.\n>\n> **Security:** These commands download and execute an installer from this repository. You can inspect the scripts in the repository before running them. Use the dedicated Termux installer on Android; do not use the standard Linux installer inside Termux.

### Manual installation

Terchess requires **Python 3.10+**. To install from a source checkout or extracted ZIP, create a virtual environment and install the project:

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install .
terchess
```

See **[Installation guide](docs/INSTALL.md)** for complete platform-specific instructions, Stockfish setup, launchers, and troubleshooting.

## Quick start

1. Install Terchess using the command for your platform.
2. The one-command installer finds or installs Stockfish and can preserve multiple versions; manual ZIP installs require you to install the engine separately.
3. Run `terchess`.
4. Choose **Play vs Stockfish**, **Hotseat**, or **Game History**.
5. Switch between Board View and Blindfold mode from the main menu.

## Move input

Enter moves in standard algebraic notation or coordinate notation:

```text
e4      Nf3      Qxd5      O-O
e2e4    g1f3
```

Useful in-game commands:

| Command | Action |
|---|---|
| `help` | Show move-entry help |
| `moves` | Print move history |
| `resign` | Resign the current game |
| `menu` | Return to the main menu |

## Project information

- **Python:** 3.10+
- **Platforms:** Windows, macOS, Linux, Android via Termux
- **Engine:** Official Stockfish (existing installations are detected; latest stable can be installed alongside older versions)
- **Storage:** Local SQLite database and per-user settings
- **License:** GPL-3.0-or-later

## Roadmap

See **[ROADMAP.md](docs/ROADMAP.md)** for planned features and project direction.

## Contributing

Bug reports, compatibility feedback, and improvements are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) and use the issue templates when reporting a problem.

## Security

Please see [SECURITY.md](SECURITY.md) for reporting security issues.

## License

Terchess is distributed under **GPL-3.0-or-later**. See [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](docs/THIRD_PARTY_NOTICES.md) for license and dependency notes.

<div align="center">

**Terchess — Your terminal. Your board. Your imagination.** ♟️

</div>
