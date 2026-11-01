# Terchess Roadmap ♟️

This roadmap describes shipped milestones and planned work.

## 1.1.0 — Game history, Hotseat + opening recognition · Released 2026-11-01

- SQLite local game database for completed Stockfish and Hotseat games.
- Browse saved games, inspect metadata, and replay PGN main lines.
- Import PGN files and export one game or the full local collection.
- Two-player Hotseat on one computer with player names and chess clocks.
- Offline ECO opening recognition using the CC0 Lichess dataset.
- Opening names and ECO codes are stored in game PGN headers.
- Stockfish is optional until the user selects Play vs Stockfish.

## 1.2.0 — LAN multiplayer

- Host or join a two-player game over a local network.
- Validate and synchronize legal moves, clocks, game results, and rematches.
- Handle unexpected disconnects and allow safe reconnection.
- No public game server or online account required.

## 1.3.0 — Stockfish analysis

- Analyze completed PGN games with Stockfish.
- Show a text Evaluation Bar and numerical centipawn/mate evaluations.
- Show best-move suggestions and evaluation changes.
- Label inaccuracies, mistakes, and blunders using documented thresholds.
- Explore a “brilliant move” heuristic while clearly explaining that such labels are subjective.

## Later

- Review optional integrations only after offline and LAN features are stable.
- Improve packaging and optional distributions where platform and license requirements are clear.
