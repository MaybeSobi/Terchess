"""Offline opening recognition using the CC0 Lichess opening-name dataset."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import chess
import chess.pgn
import chess.polyglot


@dataclass(frozen=True)
class Opening:
    """A named opening position from the bundled ECO reference data."""

    eco: str
    name: str
    ply: int


@lru_cache(maxsize=1)
def _opening_index() -> dict[int, Opening]:
    """Build a position-hash index from the bundled Lichess TSV data."""
    data_path = Path(__file__).parent / "data" / "openings.tsv"
    index: dict[int, Opening] = {}
    with data_path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, delimiter="\t")
        for row in reader:
            eco = (row.get("eco") or "").strip()
            name = (row.get("name") or "").strip()
            pgn = (row.get("pgn") or "").strip()
            if not (eco and name and pgn):
                continue
            game = chess.pgn.read_game(io.StringIO(pgn))
            if game is None or game.errors:
                continue
            board = game.board()
            moves = list(game.mainline_moves())
            if not moves:
                continue
            for move in moves:
                if move not in board.legal_moves:
                    break
                board.push(move)
            else:
                key = chess.polyglot.zobrist_hash(board)
                candidate = Opening(eco=eco, name=name, ply=len(moves))
                previous = index.get(key)
                if previous is None or (candidate.ply, candidate.eco, candidate.name) > (
                    previous.ply, previous.eco, previous.name
                ):
                    index[key] = candidate
    return index


def identify_opening(board: chess.Board, max_plies: int = 40) -> Opening | None:
    """Return the deepest named position reached in this game's main line.

    Lookup is position-based, so common transpositions are recognized too.
    Only the first max_plies half-moves are considered opening territory.
    """
    if max_plies < 1:
        return None
    index = _opening_index()
    replay = board.root()
    latest: Opening | None = None
    for ply, move in enumerate(board.move_stack[:max_plies], start=1):
        if move not in replay.legal_moves:
            break
        replay.push(move)
        found = index.get(chess.polyglot.zobrist_hash(replay))
        if found is not None:
            latest = Opening(eco=found.eco, name=found.name, ply=ply)
    return latest


def format_opening(opening: Opening | None) -> str | None:
    """Format an opening for compact terminal display."""
    if opening is None:
        return None
    return f"{opening.eco} · {opening.name}"
