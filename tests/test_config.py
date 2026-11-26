import json

from terchess.config import DEFAULT_CONFIG, load_config, save_config


def test_missing_config_uses_defaults(tmp_path):
    config = load_config(tmp_path / "missing.json")
    assert config == DEFAULT_CONFIG


def test_preferences_round_trip(tmp_path):
    path = tmp_path / "Terchess" / "config.json"
    original = {
        "stockfish_path": r"C:\Engines\Stockfish\stockfish.exe",
        "stockfish_engines": [
            {"path": r"C:\Engines\Stockfish\stockfish.exe", "version": "17.1"},
            {"path": r"C:\Engines\Stockfish19\stockfish.exe", "version": "19"},
        ],
        "remember_engine_choice": False,
        "skill_level": 17,
        "human_color": "black",
        "time_control_key": "2",
        "show_board": False,
    }
    saved_path = save_config(original, path)
    loaded = load_config(path)
    assert saved_path == path
    assert loaded["stockfish_path"] == original["stockfish_path"]
    assert loaded["stockfish_engines"] == original["stockfish_engines"]
    assert loaded["remember_engine_choice"] is False
    assert loaded["skill_level"] == 17
    assert loaded["human_color"] == "black"
    assert loaded["time_control_key"] == "2"
    assert loaded["show_board"] is False
    assert loaded["schema_version"] == 1
    assert not path.with_name(path.name + ".tmp").exists()


def test_invalid_values_fall_back_to_safe_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "stockfish_path": {"not": "a path"},
        "skill_level": 99,
        "human_color": ["white"],
        "time_control_key": "999",
        "show_board": "no",
    }), encoding="utf-8")
    config = load_config(path)
    assert config["stockfish_path"] is None
    assert config["skill_level"] == 10
    assert config["human_color"] == "white"
    assert config["time_control_key"] == "3"
    assert config["show_board"] is True


def test_corrupt_config_does_not_crash(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{ broken json", encoding="utf-8")
    assert load_config(path) == DEFAULT_CONFIG



def test_legacy_config_gets_safe_engine_selection_defaults(tmp_path):
    path = tmp_path / "legacy.json"
    path.write_text('{"stockfish_path": "/usr/games/stockfish"}', encoding="utf-8")

    config = load_config(path)

    assert config["stockfish_path"] == "/usr/games/stockfish"
    assert config["stockfish_engines"] == []
    assert config["remember_engine_choice"] is True
    assert config["stockfish_deferred_version"] is None


def test_engine_catalog_discards_invalid_and_duplicate_entries(tmp_path):
    path = tmp_path / "config.json"
    executable = str(tmp_path / "stockfish")
    path.write_text(json.dumps({
        "stockfish_engines": [
            {"path": executable, "version": "19"},
            {"path": executable, "version": "19"},
            {"path": "   ", "version": "18"},
            {"path": "/tmp/other", "version": {"bad": "version"}},
        ],
        "remember_engine_choice": "yes",
        "stockfish_deferred_version": "nightly",
    }), encoding="utf-8")

    config = load_config(path)

    assert len(config["stockfish_engines"]) == 2
    assert config["stockfish_engines"][0]["version"] == "19"
    assert config["stockfish_engines"][1]["version"] == "Unknown"
    assert config["remember_engine_choice"] is True
    assert config["stockfish_deferred_version"] is None
