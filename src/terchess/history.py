"""Local SQLite game history and PGN import/export helpers."""

from __future__ import annotations

import io
import os
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

import chess
import chess.pgn

_VALID_RESULTS = {"1-0", "0-1", "1/2-1/2", "*"}


def get_database_path() -> Path:
    """Return the per-user database path for the current operating system."""
    if os.name == "nt":
        root = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        base = Path(root) if root else Path.home() / "AppData" / "Local"
        return base / "Terchess" / "games.sqlite3"
    if os.sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Terchess" / "games.sqlite3"
    data_home = os.environ.get("XDG_DATA_HOME")
    if data_home:
        candidate = Path(data_home).expanduser()
        if candidate.is_absolute():
            return candidate / "terchess" / "games.sqlite3"
    return Path.home() / ".local" / "share" / "terchess" / "games.sqlite3"


def _connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path is not None else get_database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            played_at TEXT NOT NULL,
            white_player TEXT NOT NULL,
            black_player TEXT NOT NULL,
            game_type TEXT NOT NULL,
            result TEXT NOT NULL,
            termination TEXT NOT NULL,
            time_control TEXT NOT NULL,
            eco TEXT,
            opening TEXT,
            pgn TEXT NOT NULL
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_games_played_at ON games(played_at)")
    connection.commit()
    return connection


def _export_game(game: chess.pgn.Game) -> str:
    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
    return game.accept(exporter).strip() + "\n"


def _insert_game(
    game: chess.pgn.Game,
    *,
    game_type: str,
    played_at: str | None = None,
    db_path: Path | str | None = None,
) -> int:
    headers = game.headers
    result = headers.get("Result", "*")
    if result not in _VALID_RESULTS:
        result = "*"
        headers["Result"] = result
    timestamp = played_at or datetime.now().astimezone().isoformat(timespec="seconds")
    pgn_text = _export_game(game)
    with _connect(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO games (
                played_at, white_player, black_player, game_type, result,
                termination, time_control, eco, opening, pgn
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                headers.get("White", "Unknown"),
                headers.get("Black", "Unknown"),
                game_type,
                result,
                headers.get("Termination", "unknown"),
                headers.get("TimeControl", "?"),
                headers.get("ECO") or None,
                headers.get("Opening") or None,
                pgn_text,
            ),
        )
        return int(cursor.lastrowid)


def save_game(
    board: chess.Board,
    *,
    white_player: str,
    black_player: str,
    game_type: str,
    result: str,
    termination: str,
    time_control: str,
    opening_name: str | None = None,
    opening_eco: str | None = None,
    db_path: Path | str | None = None,
) -> int:
    """Persist a completed game and return its local database ID."""
    if result not in _VALID_RESULTS:
        raise ValueError(f"Unsupported PGN result: {result}")
    game = chess.pgn.Game.from_board(board.copy(stack=True))
    game.headers["Event"] = "Terchess"
    game.headers["Site"] = "Terchess"
    game.headers["Date"] = date.today().strftime("%Y.%m.%d")
    game.headers["White"] = white_player or "White"
    game.headers["Black"] = black_player or "Black"
    game.headers["Result"] = result
    game.headers["Termination"] = termination
    game.headers["TimeControl"] = time_control
    game.headers["GameType"] = game_type
    if opening_name:
        game.headers["Opening"] = opening_name
    if opening_eco:
        game.headers["ECO"] = opening_eco
    return _insert_game(game, game_type=game_type, db_path=db_path)


def list_games(limit: int = 100, db_path: Path | str | None = None) -> list[dict[str, Any]]:
    """Return recent game summaries, newest first."""
    if limit < 1:
        return []
    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, played_at, white_player, black_player, game_type,
                   result, termination, time_control, eco, opening
            FROM games ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def load_game(game_id: int, db_path: Path | str | None = None) -> chess.pgn.Game | None:
    """Load a saved PGN game by its local database ID."""
    with _connect(db_path) as connection:
        row = connection.execute("SELECT pgn FROM games WHERE id = ?", (game_id,)).fetchone()
    if row is None:
        return None
    game = chess.pgn.read_game(io.StringIO(row["pgn"]))
    if game is None:
        raise ValueError(f"Saved game {game_id} contains invalid PGN data.")
    return game


def export_pgn(game_id: int, destination: Path | str, db_path: Path | str | None = None) -> Path:
    """Export one saved game to a PGN file."""
    with _connect(db_path) as connection:
        row = connection.execute("SELECT pgn FROM games WHERE id = ?", (game_id,)).fetchone()
    if row is None:
        raise KeyError(f"No saved game has ID {game_id}.")
    path = Path(destination).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(row["pgn"], encoding="utf-8")
    return path


def export_all_pgn(destination: Path | str, db_path: Path | str | None = None) -> Path:
    """Export every saved game, newest first, to a multi-game PGN file."""
    with _connect(db_path) as connection:
        rows = connection.execute("SELECT pgn FROM games ORDER BY id DESC").fetchall()
    if not rows:
        raise ValueError("There are no saved games to export.")
    path = Path(destination).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(row["pgn"].strip() for row in rows) + "\n", encoding="utf-8")
    return path


def import_pgn_file(source: Path | str, db_path: Path | str | None = None) -> int:
    """Import all valid games from a PGN file and return the number imported."""
    path = Path(source).expanduser()
    imported: list[chess.pgn.Game] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        while True:
            game = chess.pgn.read_game(handle)
            if game is None:
                break
            if game.errors:
                details = "; ".join(str(error) for error in game.errors)
                raise ValueError(f"Invalid PGN game in {path}: {details}")
            imported.append(game)
    if not imported:
        raise ValueError(f"No PGN games were found in {path}.")

    count = 0
    for game in imported:
        headers = game.headers
        game_type = headers.get("GameType", "imported")
        played_at = None
        pgn_date = headers.get("Date")
        if pgn_date and pgn_date != "????.??.??":
            try:
                parsed_date = datetime.strptime(pgn_date, "%Y.%m.%d").date()
                played_at = datetime.combine(parsed_date, datetime.min.time()).astimezone().isoformat(timespec="seconds")
            except ValueError:
                played_at = None
        _insert_game(game, game_type=game_type, played_at=played_at, db_path=db_path)
        count += 1
    return count
