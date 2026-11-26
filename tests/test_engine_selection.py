from __future__ import annotations

from terchess import cli


def test_available_engine_catalog_keeps_only_existing_unique_paths(tmp_path):
    old_engine = tmp_path / "stockfish-17"
    new_engine = tmp_path / "stockfish-19"
    old_engine.write_text("old", encoding="utf-8")
    new_engine.write_text("new", encoding="utf-8")

    catalog = cli._available_engine_catalog({
        "stockfish_path": str(old_engine),
        "stockfish_engines": [
            {"path": str(old_engine), "version": "17.1"},
            {"path": str(new_engine), "version": "19"},
            {"path": str(tmp_path / "missing"), "version": "18"},
        ],
    })

    assert catalog == [
        {"path": str(old_engine.resolve()), "version": "17.1"},
        {"path": str(new_engine.resolve()), "version": "19"},
    ]


def test_choose_engine_returns_selection_without_remembering(tmp_path, monkeypatch):
    first = tmp_path / "stockfish-17"
    second = tmp_path / "stockfish-19"
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")
    answers = iter(["2", "n"])
    monkeypatch.setattr(cli.Prompt, "ask", lambda *args, **kwargs: next(answers))

    selected, remember = cli._choose_stockfish_engine(
        [
            {"path": str(first), "version": "17.1"},
            {"path": str(second), "version": "19"},
        ],
        str(first),
    )

    assert selected == str(second)
    assert remember is False


def test_choose_engine_can_remember_the_selected_engine(tmp_path, monkeypatch):
    first = tmp_path / "stockfish-17"
    second = tmp_path / "stockfish-19"
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")
    answers = iter(["1", "y"])
    monkeypatch.setattr(cli.Prompt, "ask", lambda *args, **kwargs: next(answers))

    selected, remember = cli._choose_stockfish_engine(
        [
            {"path": str(first), "version": "17.1"},
            {"path": str(second), "version": "19"},
        ],
        str(second),
    )

    assert selected == str(first)
    assert remember is True


def test_settings_config_preserves_engine_catalog_and_selection_mode():
    settings = cli.GameSettings()
    catalog = [
        {"path": "/opt/stockfish-17", "version": "17.1"},
        {"path": "/opt/stockfish-19", "version": "19"},
    ]

    result = cli._settings_config(
        settings,
        "/opt/stockfish-17",
        catalog,
        remember_engine_choice=False,
        deferred_version="20",
    )

    assert result["stockfish_engines"] == catalog
    assert result["remember_engine_choice"] is False
    assert result["stockfish_deferred_version"] == "20"
