# Release checklist — Terchess

Do not publish a stable release until each relevant item has been verified against the exact source being released.

## Automated checks

- [ ] GitHub Actions CI passes on supported Python versions and operating systems.
- [ ] `python -m compileall -q src` passes.
- [ ] `python -m pytest -q` passes in a clean virtual environment.

## Manual checks

- [ ] Fresh installation works on Windows.
- [ ] Fresh installation works on a Linux distribution.
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

## Current status

This checklist is a guide, not a statement that these checks have passed. The maintainer must verify the exact release candidate before declaring `1.0.0` stable.
