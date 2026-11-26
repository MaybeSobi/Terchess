# Changelog

All notable changes to Terchess are documented here.

## [Unreleased]

- Add a shared cross-platform Stockfish installer that selects the latest stable official release and matching OS/CPU binary for Linux, macOS, Windows, and Android/Termux.
- Verify official release asset SHA-256 digests, archive contents, Stockfish UCI identity/version, and Skill Level 0–20 before configuring the engine.
- Store versioned Stockfish binaries outside the Terchess app folder and preserve existing user settings when saving the engine path.
- Keep distribution package managers as an explicitly warned fallback when the official release cannot be downloaded or validated.
- Update installation and troubleshooting documentation to distinguish the one-command installer from manual ZIP setup.

- Add a compact portrait-first Termux game screen with a borderless board, inline clocks, and a short recent-move list.
- Disable the live prompt toolbar refresh in Termux to prevent prompt-toolkit redraws from interfering with board repainting; desktop rendering remains unchanged.

- Register a user-level `terchess` terminal command from one-command installers on Windows, Linux, and macOS.
- Persist the command location in the user's PATH and forward CLI arguments through the platform launchers.
- Refresh the README's quick-install guidance, current feature list, and roadmap descriptions.

- Fix the Windows installer so it detects and reuses existing Stockfish executables (including manual builds under `C:\\Engines`) before attempting a WinGet installation.
- Save a detected Stockfish executable path only after verifying that its UCI options support Terchess Skill Level 0–20.
- Merge the detected engine path into valid JSON settings without overwriting other preferences; leave corrupt or non-object settings files untouched.
- Preserve an existing `.venv` during repeat installs on Windows, Linux, and macOS; refresh the application package and declared dependencies in place.

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
