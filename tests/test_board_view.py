from __future__ import annotations

import chess

from terchess.board_view import _board_cell_dimensions, board_table


def test_board_grows_with_available_terminal_space() -> None:
    compact = _board_cell_dimensions(120, 30, wide_layout=True)
    spacious = _board_cell_dimensions(160, 44, wide_layout=True)

    assert spacious[0] > compact[0]
    assert spacious[1] > compact[1]


def test_board_respects_short_terminal_height() -> None:
    cell_width, cell_height = _board_cell_dimensions(120, 16, wide_layout=True)

    assert cell_height == 1
    assert cell_width == 3


def test_expanded_board_keeps_all_squares_and_rank_rows() -> None:
    table = board_table(chess.Board(), chess.WHITE, cell_width=6, cell_height=2)

    # Eight ranks, each rendered across two terminal lines, plus file labels.
    assert len(table.rows) == 17
    assert len(table.columns) == 9
    assert [column.width for column in table.columns[1:]] == [6] * 8


def test_default_board_remains_compact_for_termux() -> None:
    table = board_table(chess.Board(), chess.WHITE)

    assert len(table.rows) == 9
    assert [column.width for column in table.columns[1:]] == [3] * 8
