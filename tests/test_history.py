import chess

from terchess.history import export_all_pgn, export_pgn, import_pgn_file, list_games, load_game, save_game


def _sample_board():
    board = chess.Board()
    for san in ("d4", "d5", "c4", "dxc4", "e3", "b5"):
        board.push_san(san)
    return board


def test_save_and_load_game_round_trip(tmp_path):
    database = tmp_path / "history.sqlite3"
    board = _sample_board()
    game_id = save_game(
        board, white_player="Alice", black_player="Bob", game_type="hotseat",
        result="*", termination="unknown", time_control="5+0",
        opening_name="Queen's Gambit Accepted", opening_eco="D20", db_path=database,
    )
    records = list_games(db_path=database)
    assert len(records) == 1
    assert records[0]["id"] == game_id
    assert records[0]["white_player"] == "Alice"
    assert records[0]["black_player"] == "Bob"
    assert records[0]["game_type"] == "hotseat"
    assert records[0]["opening"] == "Queen's Gambit Accepted"
    loaded = load_game(game_id, db_path=database)
    assert loaded is not None
    assert loaded.headers["ECO"] == "D20"
    assert loaded.headers["Opening"] == "Queen's Gambit Accepted"
    assert loaded.end().board().fen() == board.fen()


def test_import_and_export_multiple_pgn_games(tmp_path):
    database = tmp_path / "history.sqlite3"
    source = tmp_path / "incoming.pgn"
    source.write_text(
        '[Event "Friendly"]\n[White "A"]\n[Black "B"]\n[Result "1-0"]\n\n1. e4 e5 1-0\n\n'
        '[Event "Second"]\n[White "C"]\n[Black "D"]\n[Result "0-1"]\n\n1. d4 d5 0-1\n',
        encoding="utf-8",
    )
    assert import_pgn_file(source, db_path=database) == 2
    records = list_games(db_path=database)
    assert len(records) == 2
    assert {record["result"] for record in records} == {"1-0", "0-1"}
    one_game = tmp_path / "one.pgn"
    export_pgn(records[0]["id"], one_game, db_path=database)
    assert '[Event "Second"]' in one_game.read_text(encoding="utf-8")
    all_games = tmp_path / "all.pgn"
    export_all_pgn(all_games, db_path=database)
    assert all_games.read_text(encoding="utf-8").count('[Event "') == 2


def test_import_rejects_file_without_games(tmp_path):
    source = tmp_path / "empty.pgn"
    source.write_text("", encoding="utf-8")
    try:
        import_pgn_file(source, db_path=tmp_path / "history.sqlite3")
    except ValueError as exc:
        assert "No PGN games" in str(exc)
    else:
        raise AssertionError("Expected empty PGN file to be rejected")


def test_load_missing_game_returns_none(tmp_path):
    assert load_game(999, db_path=tmp_path / "history.sqlite3") is None
