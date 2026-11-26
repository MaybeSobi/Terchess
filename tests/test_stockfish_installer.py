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


def test_stockfish_19_requires_version_and_skill_range():
    output = (
        "id name Stockfish 19\n"
        "option name Skill Level type spin default 20 min 0 max 20\n"
        "uciok\n"
    )
    completed = subprocess.CompletedProcess(["stockfish"], 0, stdout=output, stderr="")
    with patch.object(installer.subprocess, "run", return_value=completed):
        assert installer.is_stockfish_19(Path("stockfish"))


def test_old_engine_is_not_accepted():
    output = (
        "id name Stockfish 17.1\n"
        "option name Skill Level type spin default 20 min 0 max 20\n"
        "uciok\n"
    )
    completed = subprocess.CompletedProcess(["stockfish"], 0, stdout=output, stderr="")
    with patch.object(installer.subprocess, "run", return_value=completed):
        assert not installer.is_stockfish_19(Path("stockfish"))
