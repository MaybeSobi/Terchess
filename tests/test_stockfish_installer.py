from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch
import subprocess

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


def test_expected_latest_engine_and_skill_range_are_accepted():
    output = (
        "id name Stockfish 20.1\n"
        "option name Skill Level type spin default 20 min 0 max 20\n"
        "uciok\n"
    )
    completed = subprocess.CompletedProcess(["stockfish"], 0, stdout=output, stderr="")
    with patch.object(installer.subprocess, "run", return_value=completed):
        assert installer.is_expected_stockfish(Path("stockfish"), "20.1")


def test_older_engine_is_not_accepted_for_new_release():
    output = (
        "id name Stockfish 19\n"
        "option name Skill Level type spin default 20 min 0 max 20\n"
        "uciok\n"
    )
    completed = subprocess.CompletedProcess(["stockfish"], 0, stdout=output, stderr="")
    with patch.object(installer.subprocess, "run", return_value=completed):
        assert not installer.is_expected_stockfish(Path("stockfish"), "20")


def test_engine_with_out_of_range_skill_level_is_rejected():
    output = (
        "id name Stockfish 20\n"
        "option name Skill Level type spin default 20 min 1 max 20\n"
        "uciok\n"
    )
    completed = subprocess.CompletedProcess(["stockfish"], 0, stdout=output, stderr="")
    with patch.object(installer.subprocess, "run", return_value=completed):
        assert not installer.is_expected_stockfish(Path("stockfish"), "20")
