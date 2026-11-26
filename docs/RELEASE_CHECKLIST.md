# Release checklist — Terchess

Reusable checklist for future releases. Verify each relevant item against the exact source being released.

## Automated checks

- [ ] GitHub Actions CI passes on supported Python versions and operating systems.
- [ ] `python -m compileall -q src` passes.
- [ ] `python -m pytest -q` passes in a clean virtual environment.

## Manual checks

- [ ] Fresh installation works on Windows.
- [ ] One-click `run_terchess.bat` creates the environment and starts the game on Windows.
- [ ] Fresh installation and one-click launch work on macOS (Apple Silicon and/or Intel, as available).
- [ ] Fresh installation and one-click launch work on a Linux distribution.
- [ ] Stockfish discovery and manual executable-path selection work.
- [ ] Legal move entry accepts SAN and coordinate notation.
- [ ] Illegal moves are rejected without corrupting the game.
- [ ] Both sides can be selected.
- [ ] Board View and Blindfold mode work.
- [ ] Clock presets, increments, and flag-fall behavior work.
- [ ] Settings persist across restart.
- [ ] Resignation and return-to-menu behavior work.
- [ ] Unicode and color behavior are reasonable in a supported terminal.

## Repository and release hygiene

- [ ] Review every staged file; remove caches, bytecode, local configuration, and secrets.
- [ ] Verify dependency and license notices.
- [ ] Update `CHANGELOG.md` for the exact release.
- [ ] Ensure README claims match the tested build.
- [ ] Create a version tag only after checks pass.
- [ ] Attach a source archive or built artifact to the GitHub release.
- [ ] Clearly label any release candidate as pre-release.

## v1.0.0 release verification

- GitHub Actions passed all 8 combinations: Python 3.10–3.13 on Windows and Ubuntu.
- The release workflow built the wheel and source distribution and validated them with `twine check`.
- The maintainer downloaded a fresh copy of the project and smoke-tested it successfully.

The checklist above is retained as a practical template for future releases; the bullets here state only the verification performed for v1.0.0.


## v1.0.1 macOS support

- The CI matrix tests Python 3.10–3.13 on macOS as well as Windows and Ubuntu.
- README includes steps for installing Python and Stockfish, extracting the ZIP, entering the project directory, creating a virtual environment, installing dependencies, and launching Terchess.
- Manual testing on a physical Mac is recommended when available.


## v1.0.2 launcher verification

- CI checks POSIX shell syntax for `run_terchess.sh` and `run_terchess.command` on Linux and macOS runners.
- Launchers create `.venv` and install project dependencies when required.
- Manual launch testing on physical Windows, macOS, and Linux systems is recommended when available.


## v1.1.0 feature verification

- [ ] Finish a Stockfish game and confirm it is recorded in the SQLite history.
- [ ] Finish a Hotseat game and confirm both player names, result, and time control are stored.
- [ ] Browse a saved game and replay its main line.
- [ ] Import a PGN file containing one game and a file containing multiple games.
- [ ] Export one saved game and export the entire local history; re-import both outputs.
- [ ] Confirm ECO and opening names are recognized for common lines and saved to PGN headers.
- [ ] Confirm Hotseat and Game History work when Stockfish is not installed or not configured.
- [ ] Confirm the database is stored in the per-user data directory, not inside the project folder.
- [ ] Confirm malformed PGN input reports an error without crashing the application.
