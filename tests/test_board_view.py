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


def test_board_cells_shrink_on_a_narrow_terminal() -> None:
    assert _board_cell_dimensions(30, 24, wide_layout=False, board_scale="large") == (3, 2)


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

def test_compact_piece_symbols_remain_centered() -> None:
    from terchess.board_view import _piece_cell_lines

    for color in (chess.WHITE, chess.BLACK):
        for piece_type in (
            chess.PAWN, chess.KNIGHT, chess.BISHOP,
            chess.ROOK, chess.QUEEN, chess.KING,
        ):
            piece = chess.Piece(piece_type, color)
            lines = _piece_cell_lines(piece, 2, 1)
            assert len(lines) == 1
            assert lines[0].strip() == piece.unicode_symbol()


def test_larger_board_sizes_render_solid_block_piece_art() -> None:
    from terchess.board_view import _BLOCK_GLYPHS, _PIECE_MASKS, _piece_cell_lines

    allowed_glyphs = set(_BLOCK_GLYPHS.values())
    assert all(len(mask) == 16 and all(len(row) == 16 for row in mask) for mask in _PIECE_MASKS.values())

    for color in (chess.WHITE, chess.BLACK):
        for piece_type in (
            chess.PAWN, chess.KNIGHT, chess.BISHOP,
            chess.ROOK, chess.QUEEN, chess.KING,
        ):
            piece = chess.Piece(piece_type, color)
            for width, height in ((4, 2), (6, 3), (8, 4)):
                lines = _piece_cell_lines(piece, width, height)
                assert len(lines) == height
                assert all(len(line) == width for line in lines)
                assert any(char != " " for line in lines for char in line)
                assert all(char in allowed_glyphs for line in lines for char in line)


def test_piece_art_scales_with_board_size() -> None:
    from terchess.board_view import _piece_cell_lines

    piece = chess.Piece(chess.QUEEN, chess.WHITE)
    compact = _piece_cell_lines(piece, 4, 2)
    normal = _piece_cell_lines(piece, 6, 3)
    large = _piece_cell_lines(piece, 8, 4)

    assert len("".join(large)) > len("".join(normal)) > len("".join(compact))
    assert compact != normal
    assert normal != large


def test_piece_foreground_colors_are_consistent_on_every_square() -> None:
    from terchess.board_view import (
        BLACK_PIECE, DARK_SQUARE, LAST_MOVE_SQUARE, LIGHT_SQUARE,
        WHITE_PIECE, _piece_colors,
    )

    for background in (LIGHT_SQUARE, DARK_SQUARE, LAST_MOVE_SQUARE):
        white = _piece_colors(chess.Piece(chess.QUEEN, chess.WHITE), background)
        black = _piece_colors(chess.Piece(chess.QUEEN, chess.BLACK), background)

        assert white == (WHITE_PIECE, background)
        assert black == (BLACK_PIECE, background)


def test_both_piece_colors_remain_readable_on_all_square_colors() -> None:
    from terchess.board_view import (
        BLACK_PIECE, DARK_SQUARE, LAST_MOVE_SQUARE, LIGHT_SQUARE, WHITE_PIECE,
    )

    def luminance(hex_color: str) -> float:
        channels = [
            int(hex_color[index:index + 2], 16) / 255
            for index in (1, 3, 5)
        ]
        linear = [
            value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
            for value in channels
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    for foreground in (WHITE_PIECE, BLACK_PIECE):
        for background in (LIGHT_SQUARE, DARK_SQUARE, LAST_MOVE_SQUARE):
            lighter, darker = sorted((luminance(foreground), luminance(background)), reverse=True)
            contrast = (lighter + 0.05) / (darker + 0.05)
            assert contrast >= 3.0

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
    console = Console(file=output, force_terminal=False, width=100, height=30)
    for _ in range(2):
        render_position(
            console, chess.Board(), chess.WHITE, 10,
            ChessClock(180, 0), "3+0",
        )

    assert output.getvalue().count("\x1b[2J\x1b[H") == 2
