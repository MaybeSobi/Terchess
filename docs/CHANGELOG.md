# Changelog

All notable changes to Terchess are documented here.

## [1.1.6] — 2026-11-26

- Search for an existing compatible Stockfish before downloading a new engine, including the saved path, PATH, common system folders, Downloads, and common manual-install locations.
- Detect installed Stockfish versions through UCI and verify the Skill Level 0–20 range before registering an engine.
- When an older version is found, offer to switch Terchess to the latest release, install the latest alongside existing copies, or defer the update.
- Preserve manually installed executables outside Terchess's managed engine directory.
- Add a startup engine selector when multiple engines are retained, with a **Remember my choice** option.
- Add `terchess --choose-engine` to reopen the selector after a choice has been remembered.
- Preserve engine catalogs and selection preferences while saving other settings.

## [1.1.5] — 2026-11-26

- Make the regular chessboard responsive to terminal width and height instead of locking every square to three characters.
- Let the desktop two-column layout and board panel expand across the available terminal width, while keeping the information sidebar readable.
- Render larger chess squares across multiple terminal rows on spacious screens and automatically reduce their size on short terminals.
- Preserve the compact portrait-first Termux board.
- Add a compact portrait-first Termux game screen with a borderless board, inline clocks, and a short recent-move list.
- Disable the live prompt toolbar refresh in Termux to prevent prompt-toolkit redraws from interfering with board repainting.
- Register a user-level `terchess` terminal command from one-command installers on Windows, Linux, and macOS.
- Persist the command location in the user's PATH and forward CLI arguments through the platform launchers.
- Refresh the README's quick-install guidance, current feature list, and roadmap descriptions.
- Improve Windows Stockfish discovery and reuse, including manually installed executables, and validate the Skill Level 0–20 option before saving its path.
- Preserve existing valid user preferences while updating the Stockfish path; leave malformed settings files untouched.
- Preserve an existing `.venv` during repeat installs on Windows, Linux, and macOS.
- Update one-command installers to resolve the latest stable official Stockfish release automatically, with release-specific SHA-256 and UCI version validation.

## [Unreleased]

## [1.1.0] — 2026-11-01

- Add automatic local game history backed by SQLite, including game metadata and stored PGN.
- Add a history browser with move replay plus single-game and full-history PGN export.
- Add PGN import for bringing existing games into the local database.
- Add two-player Hotseat play on one device, with player names, shared time controls, resignation, and clock handling.
- Add offline ECO opening recognition using the CC0 Lichess chess-openings dataset.
- Show the detected opening during play and preserve ECO/opening headers in saved PGNs.
- Make Stockfish initialization lazy so Hotseat and Game History work without an engine installed.


## [1.0.2] — 2026-10-16

- Add one-click launch scripts for Windows, macOS, and Linux.
- Create a project-local Python virtual environment automatically on first launch.
- Install Terchess and its Python dependencies on first launch, then reuse the environment on later runs.
- Add Unix shell syntax validation to CI.
- Expand documentation for launchers, first-run setup, and troubleshooting.

## [1.0.1] — 2026-10-16

- Add full macOS installation instructions for Terminal, Python virtual environments, dependencies, and Stockfish.
- Document Homebrew and official Stockfish-download options.
- Add macOS to GitHub Actions CI for Python 3.10–3.13.
- Declare macOS support in the package metadata and release notes.

## [1.0.0] — 2026-10-16

- **First stable release** of Terchess.
- Support local Stockfish play with configurable Skill Level.
- Provide Board View and Blindfold / text-only display modes.
- Include live chess clocks, legal move validation, move history, and persistent settings.
- Publish one source ZIP for Windows and Linux with step-by-step installation instructions.
- Pass all 8 GitHub Actions CI combinations: Python 3.10–3.13 on Windows and Ubuntu.
- Build and validate the wheel and source distributions for the GitHub Release.

## [1.0.0-rc2] — Release candidate

- Expand first-time installation instructions for Windows and Kali/Linux.
- Explain ZIP extraction, changing into the project root, Python virtual environments, automatic dependency installation, and Stockfish setup.
- Publish a single cross-platform source ZIP alongside the Python wheel and source distribution.

## [1.0.0-rc1] — Release candidate

- Prepare the terminal chess experience for public release.
- Support local Stockfish play with configurable Skill Level.
- Provide Board View and Blindfold / text-only display modes.
- Add live chess clocks and persistent user settings.
- Add cross-platform setup guidance, tests, contribution guidance, and issue templates.
- Document the planned Game History, hotseat, LAN multiplayer, and game-analysis milestones.

Earlier release-candidate entries document the pre-release history. Stockfish remains a separate download and is not bundled with Terchess.
