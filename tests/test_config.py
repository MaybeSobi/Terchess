import json

from terchess.config import DEFAULT_CONFIG, load_config, save_config


def test_missing_config_uses_defaults(tmp_path):
    config = load_config(tmp_path / "missing.json")
    assert config == DEFAULT_CONFIG


def test_preferences_round_trip(tmp_path):
    path = tmp_path / "Terchess" / "config.json"
    original = {
        "stockfish_path": r"C:\Engines\Stockfish\stockfish.exe",
        "skill_level": 17,
        "human_color": "black",
        "time_control_key": "2",
        "show_board": False,
    }
    saved_path = save_config(original, path)
    loaded = load_config(path)
    assert saved_path == path
    assert loaded["stockfish_path"] == original["stockfish_path"]
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
