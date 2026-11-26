from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch
import subprocess
from types import SimpleNamespace

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "install_stockfish.py"
SPEC = importlib.util.spec_from_file_location("terchess_stockfish_installer", MODULE_PATH)
installer = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(installer)


def test_linux_x86_64_asset_selection():
    with patch.object(installer.platform, "system", return_value="Linux"), patch.object(
        installer.platform, "machine", return_value="x86_64"
    ):
        assert installer.asset_name() == "stockfish-linux-x86-64-universal.tar.gz"


def test_linux_arm64_asset_selection():
    with patch.object(installer.platform, "system", return_value="Linux"), patch.object(
        installer.platform, "machine", return_value="aarch64"
    ):
        assert installer.asset_name() == "stockfish-linux-arm64-universal.tar.gz"


def test_windows_arm64_asset_selection():
    with patch.object(installer.platform, "system", return_value="Windows"), patch.object(
        installer.platform, "machine", return_value="ARM64"
    ):
        assert installer.asset_name() == "stockfish-windows-arm64-universal.zip"


def test_termux_arm64_uses_android_asset():
    with patch.object(installer.platform, "system", return_value="Linux"), patch.object(
        installer.platform, "machine", return_value="aarch64"
    ), patch.dict(installer.os.environ, {"PREFIX": "/data/data/com.termux/files/usr"}):
        assert installer.asset_name() == "stockfish-android-arm64-universal.tar.gz"


def test_release_version_is_read_from_tag():
    assert installer.release_version({"tag_name": "sf_20.1", "name": "Stockfish 20.1"}) == "20.1"


def test_release_version_falls_back_to_release_title():
    assert installer.release_version({"tag_name": "v20.1", "name": "Stockfish 20.1"}) == "20.1"


def test_unidentifiable_release_is_rejected():
    try:
        installer.release_version({"tag_name": "nightly", "name": "Development build"})
    except RuntimeError as exc:
        assert "Could not determine" in str(exc)
    else:
        raise AssertionError("An unidentifiable release must not be accepted.")


def test_expected_latest_engine_and_skill_range_are_accepted(tmp_path):
    output = (
        "id name Stockfish 20.1\n"
        "option name Skill Level type spin default 20 min 0 max 20\n"
        "uciok\n"
    )
    executable = tmp_path / "stockfish"
    executable.write_text("test executable", encoding="utf-8")
    executable.chmod(0o755)
    completed = subprocess.CompletedProcess([str(executable)], 0, stdout=output, stderr="")
    with patch.object(installer.subprocess, "run", return_value=completed):
        assert installer.is_expected_stockfish(executable, "20.1")


def test_older_engine_is_not_accepted_for_new_release(tmp_path):
    output = (
        "id name Stockfish 19\n"
        "option name Skill Level type spin default 20 min 0 max 20\n"
        "uciok\n"
    )
    executable = tmp_path / "stockfish"
    executable.write_text("test executable", encoding="utf-8")
    executable.chmod(0o755)
    completed = subprocess.CompletedProcess([str(executable)], 0, stdout=output, stderr="")
    with patch.object(installer.subprocess, "run", return_value=completed):
        assert not installer.is_expected_stockfish(executable, "20")


def test_engine_with_out_of_range_skill_level_is_rejected(tmp_path):
    output = (
        "id name Stockfish 20\n"
        "option name Skill Level type spin default 20 min 1 max 20\n"
        "uciok\n"
    )
    executable = tmp_path / "stockfish"
    executable.write_text("test executable", encoding="utf-8")
    executable.chmod(0o755)
    completed = subprocess.CompletedProcess([str(executable)], 0, stdout=output, stderr="")
    with patch.object(installer.subprocess, "run", return_value=completed):
        assert not installer.is_expected_stockfish(executable, "20")



def test_parse_uci_info_accepts_any_supported_stockfish_version():
    output = (
        "id name Stockfish 17.1 by the Stockfish developers\n"
        "option name Skill Level type spin default 20 min 0 max 20\n"
        "uciok\n"
    )
    assert installer.parse_uci_info(output) == {
        "version": "17.1",
        "name": "Stockfish 17.1",
    }


def test_parse_uci_info_rejects_engines_without_skill_level_zero_to_twenty():
    output = (
        "id name Stockfish 18\n"
        "option name Skill Level type spin default 20 min 1 max 20\n"
        "uciok\n"
    )
    assert installer.parse_uci_info(output) is None


def test_parse_uci_info_rejects_non_stockfish_uci_engines():
    output = (
        "id name SomeChessEngine 1.0\n"
        "option name Skill Level type spin default 20 min 0 max 20\n"
        "uciok\n"
    )
    assert installer.parse_uci_info(output) is None


def test_version_comparison_is_numeric_and_handles_trailing_zeroes():
    assert installer.is_newer_version("19.2", "19.1")
    assert installer.is_newer_version("20", "19.9")
    assert not installer.is_newer_version("19.0", "19")
    assert not installer.is_newer_version("18", "19")


def test_candidate_search_finds_a_manually_extracted_download(tmp_path, monkeypatch):
    download_dir = tmp_path / "Downloads"
    engine_dir = download_dir / "Stockfish 17.1"
    engine_dir.mkdir(parents=True)
    executable = engine_dir / "stockfish"
    executable.write_text("placeholder", encoding="utf-8")
    executable.chmod(0o755)

    monkeypatch.setattr(installer, "search_roots", lambda: ([], []))
    monkeypatch.setattr(installer.shutil, "which", lambda _command: None)

    found = installer.candidate_executables({}, extra_roots=[download_dir])
    assert found == [executable.resolve()]


def test_candidate_search_includes_the_previously_saved_engine(tmp_path, monkeypatch):
    executable = tmp_path / "my-stockfish"
    executable.write_text("placeholder", encoding="utf-8")
    executable.chmod(0o755)
    monkeypatch.setattr(installer, "search_roots", lambda: ([], []))
    monkeypatch.setattr(installer.shutil, "which", lambda _command: None)

    found = installer.candidate_executables({"stockfish_path": str(executable)})
    assert found == [executable.resolve()]


def test_save_config_preserves_other_preferences_and_engine_catalog(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    config_file.write_text(
        '{"skill_level": 16, "human_color": "black", "show_board": false}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(installer, "config_path", lambda: config_file)

    engines = [
        {"path": str(tmp_path / "old-stockfish"), "version": "17.1"},
        {"path": str(tmp_path / "new-stockfish"), "version": "19"},
    ]
    installer.save_config(engines, engines[0]["path"], False, None)

    import json
    saved = json.loads(config_file.read_text(encoding="utf-8"))
    assert saved["skill_level"] == 16
    assert saved["human_color"] == "black"
    assert saved["show_board"] is False
    assert saved["stockfish_engines"] == engines
    assert saved["stockfish_path"] == engines[0]["path"]
    assert saved["remember_engine_choice"] is False


def test_prompt_update_strategy_can_keep_both_engines(monkeypatch):
    monkeypatch.setattr(installer.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr("builtins.input", lambda _prompt: "2")
    assert installer.prompt_update_strategy(
        [{"path": "/usr/games/stockfish", "version": "17"}],
        "19",
    ) == "alongside"


def test_prompt_update_strategy_can_defer_an_update(monkeypatch):
    monkeypatch.setattr(installer.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: "3")
    assert installer.prompt_update_strategy(
        [{"path": "/usr/games/stockfish", "version": "17"}],
        "19",
    ) == "keep"



def test_same_version_ignores_trailing_zero_components():
    assert installer.same_version("19.0", "19")
    assert installer.same_version("19.0.0", "19")
    assert not installer.same_version("19.1", "19")


def test_candidate_name_accepts_common_platform_build_names():
    assert installer._candidate_name("stockfish-windows-x86-64-avx2.exe")
    if installer.os.name != "nt":
        assert installer._candidate_name("stockfish_17.1")
    else:
        assert installer._candidate_name("stockfish_17.1.exe")
    assert not installer._candidate_name("stockfish-17.1.tar.gz")
