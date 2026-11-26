import json
import os
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

from install_stockfish import (
    InstallerError,
    expected_asset_name,
    extract_archive,
    find_release_asset,
    parse_release_version,
    parse_uci_output,
    safe_destination,
    write_config,
)


class StockfishInstallerTests(unittest.TestCase):
    def test_asset_selection_for_supported_platforms(self):
        self.assertEqual(expected_asset_name("linux", "x86_64"), "stockfish-linux-x86-64-universal.tar.gz")
        self.assertEqual(expected_asset_name("linux", "aarch64"), "stockfish-linux-arm64-universal.tar.gz")
        self.assertEqual(expected_asset_name("macos", "arm64"), "stockfish-macos-universal.tar.gz")
        self.assertEqual(
            expected_asset_name("windows", "AMD64", {"PROCESSOR_ARCHITECTURE": "AMD64"}),
            "stockfish-windows-x86-64-universal.zip",
        )
        self.assertEqual(expected_asset_name("windows", "ARM64", {"PROCESSOR_ARCHITECTURE": "ARM64"}),
                         "stockfish-windows-arm64-universal.zip")
        self.assertEqual(expected_asset_name("android", "aarch64"), "stockfish-android-arm64-universal.tar.gz")
        self.assertEqual(expected_asset_name("android", "armv7l"), "stockfish-android-armv7-neon.tar.gz")

    def test_unsupported_architecture_is_explicit(self):
        with self.assertRaises(InstallerError):
            expected_asset_name("linux", "i686")

    def test_only_stable_numeric_release_tags_are_accepted(self):
        self.assertEqual(parse_release_version({"tag_name": "sf_19", "draft": False, "prerelease": False}), 19)
        with self.assertRaises(InstallerError):
            parse_release_version({"tag_name": "sf_19", "prerelease": True})
        with self.assertRaises(InstallerError):
            parse_release_version({"tag_name": "stockfish-dev-20261125"})

    def test_release_asset_requires_published_sha256(self):
        digest = "sha256:" + "a" * 64
        asset = {"name": "engine.tar.gz", "digest": digest, "browser_download_url": "https://example.invalid/engine.tar.gz"}
        self.assertIs(find_release_asset({"assets": [asset]}, "engine.tar.gz"), asset)
        with self.assertRaises(InstallerError):
            find_release_asset(
                {"assets": [{"name": "engine.tar.gz", "browser_download_url": "https://example.invalid"}]},
                "engine.tar.gz",
            )

    def test_uci_handshake_checks_engine_version_and_skill_range(self):
        uci = """id name Stockfish 19 by the Stockfish developers
option name Skill Level type spin default 20 min 0 max 20
uciok
"""
        self.assertEqual(parse_uci_output(uci, 19), ("Stockfish 19 by the Stockfish developers", 19))
        with self.assertRaises(InstallerError):
            parse_uci_output(uci, 18)
        with self.assertRaises(InstallerError):
            parse_uci_output("id name Stockfish 19\\nuciok\\n", 19)

    def test_archive_paths_cannot_escape_extraction_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual(
                safe_destination(root, "stockfish/engine"),
                (root / "stockfish" / "engine").resolve(),
            )
            for name in ("../outside", "/etc/passwd", "stockfish/../../outside", "..\\\\outside", "C:/outside"):
                with self.subTest(name=name), self.assertRaises(InstallerError):
                    safe_destination(root, name)

    def test_extract_tar_archive_and_preserve_executable_mode(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive_path = root / "stockfish.tar.gz"
            payload = b"fake linux engine"
            with tarfile.open(archive_path, "w:gz") as archive:
                item = tarfile.TarInfo("stockfish/stockfish-linux-x86-64-universal")
                item.mode = 0o755
                item.size = len(payload)
                import io
                archive.addfile(item, io.BytesIO(payload))

            output = root / "extracted"
            extract_archive(archive_path, output)
            engine = output / "stockfish" / "stockfish-linux-x86-64-universal"
            self.assertEqual(engine.read_bytes(), payload)
            if os.name != "nt":
                self.assertTrue(engine.stat().st_mode & 0o100)

    def test_extract_windows_zip_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive_path = root / "stockfish.zip"
            payload = b"fake windows engine"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr(
                    "stockfish/stockfish-windows-x86-64-universal.exe",
                    payload,
                )

            output = root / "extracted"
            extract_archive(archive_path, output)
            engine = output / "stockfish" / "stockfish-windows-x86-64-universal.exe"
            self.assertEqual(engine.read_bytes(), payload)

    def test_config_write_preserves_existing_preferences(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config_path = root / "config.json"
            config_path.write_text(
                json.dumps({"display_mode": "blindfold", "skill_level": 12}),
                encoding="utf-8",
            )
            engine_path = root / "engines" / "sf_19" / "stockfish"
            self.assertTrue(write_config(config_path, engine_path))
            saved = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["display_mode"], "blindfold")
            self.assertEqual(saved["skill_level"], 12)
            self.assertEqual(saved["stockfish_path"], str(engine_path.resolve()))

    def test_config_write_does_not_overwrite_invalid_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config_path = root / "config.json"
            original = "{not valid json"
            config_path.write_text(original, encoding="utf-8")
            self.assertFalse(write_config(config_path, root / "stockfish"))
            self.assertEqual(config_path.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
