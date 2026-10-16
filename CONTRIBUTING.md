# Contributing to Terchess ♟️

Thanks for your interest in Terchess!

## Before opening a pull request

1. Search existing issues to avoid duplicate reports.
2. For a substantial feature, open an issue first to discuss the design.
3. Keep changes focused and explain the user-facing reason.
4. Never commit passwords, tokens, personal configuration, virtual environments, or generated caches.

## Development setup

Python 3.10+ is required.

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell:
# .\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Run checks

```bash
python -m compileall -q src
python -m pytest -q
```

Please run the tests before submitting. If a change affects the interactive terminal UI or Stockfish integration, include manual test steps in your pull request.

## Pull request checklist

- [ ] The change has a clear, focused purpose.
- [ ] Tests were added or updated when appropriate.
- [ ] Existing tests pass locally.
- [ ] User-facing docs and examples are updated.
- [ ] No secrets, personal data, or unrelated generated files are included.
- [ ] Platform-specific behavior is identified.

## Project direction

The near-term roadmap prioritizes saved-game history and PGN support, hotseat play in one terminal, LAN multiplayer, and then Stockfish game analysis. Feature proposals should describe the user problem, a minimal design, and how the behavior can be tested.

## License

By contributing, you agree that your contributions will be distributed under the project's GPL-3.0-or-later license.
