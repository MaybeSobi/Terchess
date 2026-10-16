# Terchess Roadmap ♟️

This roadmap describes planned work, not features that have already shipped. Milestones depend on implementation and testing; dates are intentionally omitted.

## 1.0.0 — Stable offline release

- Local Stockfish gameplay with configurable Skill Level.
- Board View and Blindfold / text-only mode.
- Chess clocks and legal move validation.
- Persistent preferences and engine path.
- Reliable setup documentation and automated tests.
- Manual verification on Windows and Linux before stable release.

## 1.1.0 — Game History + play with friends

- **Game History:** browse saved games, replay moves, and export/import PGN.
- **Hotseat:** two people play on one computer and terminal, alternating turns.
- **LAN multiplayer:** one player hosts and another joins over the local network.
- Handle disconnects, rematches, and graceful game termination.
- No public game server or Chess.com account required for local/LAN play.

## 1.2.0 — Stockfish analysis

- Analyze completed PGN games with Stockfish.
- Show best-move suggestions and evaluation changes.
- Label inaccuracies, mistakes, and blunders using documented thresholds.
- Explore a “brilliant move” heuristic while clearly explaining that such labels are subjective and differ between analysis products.

## Later

- Review a compliant integration path for online chess platforms only after offline and LAN features are stable.
- Improve packaging and optional distributions where platform and license requirements are clear.
