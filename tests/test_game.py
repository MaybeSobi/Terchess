import chess

from terchess.game import _read_human_move
from terchess.cli import parse_color_choice


def test_san_move_parses():
    assert _read_human_move("e4", chess.Board()) == chess.Move.from_uci("e2e4")


def test_uci_move_parses():
    assert _read_human_move("e2e4", chess.Board()) == chess.Move.from_uci("e2e4")


def test_illegal_move_returns_invalid():
    assert _read_human_move("e5", chess.Board()) == "invalid"


def test_command_passes_through():
    assert _read_human_move("resign", chess.Board()) == "resign"
    assert _read_human_move("menu", chess.Board()) == "menu"


def test_knight_move_after_e4_e5_parses():
    board = chess.Board()
    board.push_san("e4")
    board.push_san("e5")
    assert _read_human_move("Nf3", board) == chess.Move.from_uci("g1f3")


def test_lowercase_piece_move_parses():
    board = chess.Board()
    board.push_san("e4")
    board.push_san("e5")
    assert _read_human_move("nf3", board) == chess.Move.from_uci("g1f3")


def test_zero_castling_notation_parses():
    board = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    assert _read_human_move("0-0", board) == chess.Move.from_uci("e1g1")


def test_color_choices_accept_full_words_and_shortcuts():
    assert parse_color_choice("white") == chess.WHITE
    assert parse_color_choice("W") == chess.WHITE
    assert parse_color_choice("1") == chess.WHITE
    assert parse_color_choice("black") == chess.BLACK
    assert parse_color_choice("B") == chess.BLACK
    assert parse_color_choice("2") == chess.BLACK
    assert parse_color_choice("sometimes") is None


def test_game_settings_default_to_board_view_and_allow_blindfold_toggle():
    from terchess.cli import GameSettings
    settings = GameSettings()
    assert settings.show_board is True
    settings.show_board = not settings.show_board
    assert settings.show_board is False


def test_text_only_renderer_displays_moves_without_chessboard_symbols():
    from io import StringIO
    from rich.console import Console
    from terchess.board_view import render_text_position
    from terchess.clock import ChessClock
    output = StringIO()
    console = Console(file=output, record=True, force_terminal=False, width=100)
    board = chess.Board()
    board.push_san("e4")
    board.push_san("e5")
    clock = ChessClock(300, 0, now=lambda: 0.0)
    clock.start(chess.WHITE)
    render_text_position(console, board, chess.WHITE, 10, clock, "5+0", "Stockfish played e5")
    rendered = console.export_text()
    assert "BLINDFOLD MODE" in rendered
    assert "1." in rendered
    assert "e4" in rendered and "e5" in rendered
    for piece in "♔♕♖♗♘♙♚♛♜♝♞♟":
        assert piece not in rendered
