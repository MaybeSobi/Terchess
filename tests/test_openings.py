import chess

from terchess.openings import format_opening, identify_opening


def test_queen_gambit_accepted_is_recognized_offline():
    board = chess.Board()
    for san in ("d4", "d5", "c4", "dxc4"):
        board.push_san(san)
    opening = identify_opening(board)
    assert opening is not None
    assert opening.eco.startswith("D")
    assert "Queen's Gambit Accepted" in opening.name
    assert format_opening(opening) is not None


def test_sicilian_najdorf_is_recognized():
    board = chess.Board()
    for san in ("e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "a6"):
        board.push_san(san)
    opening = identify_opening(board)
    assert opening is not None
    assert opening.eco == "B90"
    assert "Najdorf" in opening.name


def test_opening_recognition_works_after_later_moves():
    board = chess.Board()
    for san in ("d4", "d5", "c4", "dxc4", "e3", "e5", "Bxc4"):
        board.push_san(san)
    opening = identify_opening(board)
    assert opening is not None
    assert "Queen's Gambit Accepted" in opening.name


def test_opening_lookup_returns_none_when_disabled():
    board = chess.Board()
    for san in ("d4", "d5", "c4", "dxc4"):
        board.push_san(san)
    assert identify_opening(board, max_plies=0) is None
