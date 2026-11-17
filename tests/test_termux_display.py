from __future__ import annotations

import chess

from terchess.board_view import _compact_history, is_termux


def test_termux_is_detected_from_prefix(monkeypatch) -> None:
    monkeypatch.delenv("TERMUX_VERSION", raising=False)
    monkeypatch.setenv("PREFIX", "/data/data/com.termux/files/usr")
    assert is_termux()


def test_termux_is_detected_from_version_marker(monkeypatch) -> None:
    monkeypatch.setenv("TERMUX_VERSION", "0.118.0")
    monkeypatch.delenv("PREFIX", raising=False)
    assert is_termux()


def test_desktop_environment_is_not_detected_as_termux(monkeypatch) -> None:
    monkeypatch.delenv("TERMUX_VERSION", raising=False)
    monkeypatch.setenv("PREFIX", "/usr")
    assert not is_termux()


def test_compact_history_keeps_only_recent_plies() -> None:
    board = chess.Board()
    for san in ("e4", "e5", "Nf3", "Nc6", "Bb5", "a6", "Ba4", "Nf6"):
        board.push_san(san)

    assert _compact_history(board, max_plies=4) == "3. Bb5 a6 4. Ba4 Nf6"


def test_compact_history_handles_new_game() -> None:
    assert _compact_history(chess.Board()) == "No moves yet"
