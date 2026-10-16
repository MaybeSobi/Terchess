"""Cross-platform persistent user preferences for Terchess."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
DEFAULT_CONFIG: dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "stockfish_path": None,
    "skill_level": 10,
    "human_color": "white",
    "time_control_key": "3",
    "show_board": True,
}
VALID_TIME_CONTROL_KEYS = {"1", "2", "3", "4", "5"}


def get_config_path() -> Path:
    """Return the standard per-user config file location for this OS."""
    if os.name == "nt":
        root = os.environ.get("APPDATA")
        base = Path(root) if root else Path.home() / "AppData" / "Roaming"
        return base / "Terchess" / "config.json"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Terchess" / "config.json"
    xdg_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_home:
        candidate = Path(xdg_home).expanduser()
        if candidate.is_absolute():
            return candidate / "terchess" / "config.json"
    return Path.home() / ".config" / "terchess" / "config.json"


def _normalize_config(raw: object) -> dict[str, Any]:
    """Merge untrusted or malformed config data with validated defaults."""
    result = DEFAULT_CONFIG.copy()
    if not isinstance(raw, dict):
        return result
    path = raw.get("stockfish_path")
    if isinstance(path, str) and path.strip():
        result["stockfish_path"] = str(Path(path.strip()).expanduser())
    elif path is None or (isinstance(path, str) and not path.strip()):
        result["stockfish_path"] = None
    skill = raw.get("skill_level")
    if isinstance(skill, int) and not isinstance(skill, bool) and 0 <= skill <= 20:
        result["skill_level"] = skill
    color = raw.get("human_color")
    if isinstance(color, str) and color in {"white", "black"}:
        result["human_color"] = color
    time_key = raw.get("time_control_key")
    if isinstance(time_key, str) and time_key in VALID_TIME_CONTROL_KEYS:
        result["time_control_key"] = time_key
    show_board = raw.get("show_board")
    if isinstance(show_board, bool):
        result["show_board"] = show_board
    result["schema_version"] = SCHEMA_VERSION
    return result


def load_config(path: Path | str | None = None) -> dict[str, Any]:
    """Load preferences; return safe defaults if the file is absent or invalid."""
    config_file = Path(path) if path is not None else get_config_path()
    try:
        raw = json.loads(config_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return DEFAULT_CONFIG.copy()
    return _normalize_config(raw)


def save_config(config: dict[str, Any], path: Path | str | None = None) -> Path:
    """Atomically save validated preferences and return the destination path."""
    config_file = Path(path) if path is not None else get_config_path()
    validated = _normalize_config(config)
    config_file.parent.mkdir(parents=True, exist_ok=True)
    temporary = config_file.with_name(config_file.name + ".tmp")
    try:
        temporary.write_text(json.dumps(validated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(temporary, config_file)
    except OSError:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return config_file
