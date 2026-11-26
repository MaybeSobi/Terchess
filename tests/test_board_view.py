from __future__ import annotations

import chess
from rich.console import Console

from terchess.board_view import _board_cell_dimensions, board_table, render_position
from terchess.clock import ChessClock


def test_board_grows_with_available_terminal_space() -> None:
    compact = _board_cell_dimensions(120, 20, wide_layout=True, board_scale="auto")
    spacious = _board_cell_dimensions(160, 44, wide_layout=True, board_scale="auto")

    assert spacious[0] > compact[0]
    assert spacious[1] > compact[1]


def test_board_size_presets_are_distinct() -> None:
    compact = _board_cell_dimensions(160, 50, wide_layout=True, board_scale="compact")
    normal = _board_cell_dimensions(160, 50, wide_layout=True, board_scale="normal")
    large = _board_cell_dimensions(160, 50, wide_layout=True, board_scale="large")

    assert compact == (4, 2)
    assert normal == (6, 3)
    assert large == (8, 4)



def test_large_board_is_clamped_to_a_short_terminal() -> None:
    assert _board_cell_dimensions(80, 24, wide_layout=False, board_scale="large") == (4, 2)


def test_large_board_uses_full_size_when_terminal_allows_it() -> None:
    assert _board_cell_dimensions(160, 50, wide_layout=True, board_scale="large") == (8, 4)


def test_board_respects_short_terminal_height() -> None:
    cell_width, cell_height = _board_cell_dimensions(120, 16, wide_layout=True)

    assert cell_height == 1
    assert cell_width == 2


def test_expanded_board_keeps_all_squares_and_rank_rows() -> None:
    table = board_table(chess.Board(), chess.WHITE, cell_width=6, cell_height=2)

    # Eight ranks, each rendered across two terminal lines, plus file labels.
    assert len(table.rows) == 17
    assert len(table.columns) == 9
    assert [column.width for column in table.columns[1:]] == [6] * 8


def test_default_board_remains_compact_for_termux() -> None:
    table = board_table(chess.Board(), chess.WHITE)

    assert len(table.rows) == 9
    assert [column.width for column in table.columns[1:]] == [2] * 8



def test_wide_layout_uses_the_available_terminal_width() -> None:
    console = Console(width=120, height=30, record=True)
    render_position(
        console,
        chess.Board(),
        chess.WHITE,
        10,
        ChessClock(180, 0),
        "3+0",
    )

    rendered_lines = console.export_text().splitlines()
    assert max(map(len, rendered_lines)) >= 110

def test_piece_fallback_uses_correct_white_and_black_unicode_symbols() -> None:
    from terchess.board_view import _piece_cell_lines

    white_pawn = _piece_cell_lines(chess.Piece(chess.PAWN, chess.WHITE), 2, 1)
    black_pawn = _piece_cell_lines(chess.Piece(chess.PAWN, chess.BLACK), 2, 1)

    assert white_pawn == ["♙ "]
    assert black_pawn == ["♟ "]


def test_large_piece_silhouettes_are_distinct_and_fill_the_cell() -> None:
    from terchess.board_view import _piece_cell_lines

    silhouettes = [
        tuple(_piece_cell_lines(chess.Piece(piece_type, chess.WHITE), 7, 4))
        for piece_type in (
            chess.PAWN, chess.KNIGHT, chess.BISHOP,
            chess.ROOK, chess.QUEEN, chess.KING,
        )
    ]

    assert len(set(silhouettes)) == 6
    assert all(len(lines) == 4 for lines in silhouettes)
    assert all(len(line) == 7 for lines in silhouettes for line in lines)


def test_white_and_black_pieces_have_contrasting_colors_without_changing_square_colors() -> None:
    from terchess.board_view import LIGHT_SQUARE, DARK_SQUARE, _piece_colors

    white = chess.Piece(chess.QUEEN, chess.WHITE)
    black = chess.Piece(chess.QUEEN, chess.BLACK)

    white_on_light = _piece_colors(white, LIGHT_SQUARE)
    black_on_light = _piece_colors(black, LIGHT_SQUARE)
    white_on_dark = _piece_colors(white, DARK_SQUARE)
    black_on_dark = _piece_colors(black, DARK_SQUARE)

    assert white_on_light[0] != black_on_light[0]
    assert white_on_dark[0] != black_on_dark[0]
    assert white_on_light[1] == black_on_light[1] == LIGHT_SQUARE
    assert white_on_dark[1] == black_on_dark[1] == DARK_SQUARE


def test_white_and_black_pawns_use_different_silhouette_styles() -> None:
    from terchess.board_view import _piece_cell_lines

    white_pawn = tuple(_piece_cell_lines(chess.Piece(chess.PAWN, chess.WHITE), 7, 4))
    black_pawn = tuple(_piece_cell_lines(chess.Piece(chess.PAWN, chess.BLACK), 7, 4))

    assert white_pawn != black_pawn


def test_terminal_redraw_explicitly_clears_and_homes_the_viewport() -> None:
    from io import StringIO
    from terchess.board_view import _clear_rendered_screen

    class TTYBuffer(StringIO):
        def isatty(self):
            return True

    output = TTYBuffer()
    console = Console(file=output, force_terminal=True, width=100, height=30)

    _clear_rendered_screen(console)

    assert output.getvalue() == "\x1b[2J\x1b[H"


def test_each_position_render_starts_with_a_fresh_terminal_viewport() -> None:
    from io import StringIO

    class TTYBuffer(StringIO):
        def isatty(self):
            return True

    output = TTYBuffer()
    console = Console(file=output, force_terminal=True, width=100, height=30)
    for _ in range(2):
        render_position(
            console, chess.Board(), chess.WHITE, 10,
            ChessClock(180, 0), "3+0",
        )

    assert output.getvalue().count("\x1b[2J\x1b[H") == 2
