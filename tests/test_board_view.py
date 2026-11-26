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
    compact = _board_cell_dimensions(160, 44, wide_layout=True, board_scale="compact")
    normal = _board_cell_dimensions(160, 44, wide_layout=True, board_scale="normal")
    large = _board_cell_dimensions(160, 44, wide_layout=True, board_scale="large")

    assert compact == (2, 1)
    assert normal == (4, 2)
    assert large == (6, 3)



def test_large_board_is_clamped_to_a_short_terminal() -> None:
    assert _board_cell_dimensions(80, 24, wide_layout=False, board_scale="large") == (2, 1)


def test_large_board_uses_full_size_when_terminal_allows_it() -> None:
    assert _board_cell_dimensions(160, 50, wide_layout=True, board_scale="large") == (6, 3)


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
