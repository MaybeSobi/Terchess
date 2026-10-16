"""Stockfish discovery and UCI setup."""

from __future__ import annotations

import shutil
from pathlib import Path

import chess.engine


def find_engine(explicit_path: str | None = None) -> str | None:
    """Find a Stockfish executable from an explicit path or PATH."""
    if explicit_path:
        candidate = Path(explicit_path.strip().strip('"')).expanduser()
        if candidate.is_file():
            return str(candidate.resolve())
        return shutil.which(explicit_path.strip())
    return shutil.which("stockfish")


def validate_skill_level(engine: chess.engine.SimpleEngine, skill_level: int) -> None:
    """Validate that the connected engine supports the requested Skill Level."""
    option = engine.options.get("Skill Level")
    if option is None:
        raise RuntimeError("This engine does not expose the UCI 'Skill Level' option. Please use an official Stockfish build.")
    if not 0 <= skill_level <= 20:
        raise ValueError("Skill Level must be between 0 and 20.")
    if option.min is not None and skill_level < option.min:
        raise ValueError(f"This engine's minimum Skill Level is {option.min}.")
    if option.max is not None and skill_level > option.max:
        raise ValueError(f"This engine's maximum Skill Level is {option.max}.")


def configure_skill_level(engine: chess.engine.SimpleEngine, skill_level: int) -> None:
    """Set Stockfish strength using its UCI Skill Level option."""
    validate_skill_level(engine, skill_level)
    engine.configure({"Skill Level": skill_level})
