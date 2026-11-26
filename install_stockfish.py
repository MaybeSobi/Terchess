#!/usr/bin/env python3
"""Install and configure the latest official stable Stockfish release for Terchess."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

API_URL = "https://api.github.com/repos/official-stockfish/Stockfish/releases/latest"
USER_AGENT = "Terchess-Stockfish-Installer"
CHUNK_SIZE = 1024 * 1024


class InstallerError(RuntimeError):
    """Raised when a release cannot be safely installed or validated."""


def normalize_architecture(machine: str | None = None, env: dict[str, str] | None = None,
                           platform_name: str | None = None) -> str:
    env = env or os.environ
    platform_name = (platform_name or platform.system()).lower()
    machine = (machine or platform.machine()).lower()

    if platform_name in {"windows", "win32"}:
        machine = (env.get("PROCESSOR_ARCHITEW6432") or env.get("PROCESSOR_ARCHITECTURE") or machine).lower()

    aliases = {
        "amd64": "x86_64", "x64": "x86_64", "x86-64": "x86_64",
        "arm64": "aarch64", "armv8l": "aarch64",
        "armv7": "armv7l", "armv7l": "armv7l",
    }
    return aliases.get(machine, machine)


def expected_asset_name(platform_name: str, machine: str | None = None,
                        env: dict[str, str] | None = None) -> str:
    platform_name = platform_name.lower()
    arch = normalize_architecture(machine, env, platform_name)

    if platform_name == "macos":
        return "stockfish-macos-universal.tar.gz"
    if platform_name == "linux":
        names = {
            "x86_64": "stockfish-linux-x86-64-universal.tar.gz",
            "aarch64": "stockfish-linux-arm64-universal.tar.gz",
            "riscv64": "stockfish-linux-riscv64-universal.tar.gz",
        }
    elif platform_name == "android":
        names = {
            "aarch64": "stockfish-android-arm64-universal.tar.gz",
            "armv7l": "stockfish-android-armv7-neon.tar.gz",
        }
    elif platform_name == "windows":
        names = {
            "x86_64": "stockfish-windows-x86-64-universal.zip",
            "aarch64": "stockfish-windows-arm64-universal.zip",
        }
    else:
        raise InstallerError(f"Unsupported platform: {platform_name}")

    try:
        return names[arch]
    except KeyError as exc:
        raise InstallerError(
            f"No official Stockfish binary is published for {platform_name}/{arch}."
        ) from exc


def parse_release_version(release: dict[str, Any]) -> int:
    if release.get("draft") or release.get("prerelease"):
        raise InstallerError("The GitHub API did not return a stable Stockfish release.")
    tag = str(release.get("tag_name", ""))
    match = re.fullmatch(r"sf_(\d+)", tag)
    if not match:
        raise InstallerError(f"Unexpected Stockfish release tag: {tag!r}")
    return int(match.group(1))


def find_release_asset(release: dict[str, Any], asset_name: str) -> dict[str, Any]:
    for asset in release.get("assets", []):
        if asset.get("name") == asset_name:
            digest = str(asset.get("digest", ""))
            if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
                raise InstallerError(f"The official release does not provide a SHA-256 digest for {asset_name}.")
            if not asset.get("browser_download_url"):
                raise InstallerError(f"The official release has no download URL for {asset_name}.")
            return asset
    raise InstallerError(f"The official release does not contain the required asset: {asset_name}")


def parse_uci_output(output: str, expected_version: int | None = None) -> tuple[str, int]:
    lines = output.splitlines()
    if "uciok" not in lines:
        raise InstallerError("Stockfish did not complete a successful UCI handshake.")

    id_match = re.search(r"(?m)^id name\s+(.+?)\s*$", output)
    if not id_match:
        raise InstallerError("The engine did not identify itself in its UCI response.")
    engine_name = id_match.group(1).strip()
    version_match = re.search(r"\bStockfish\s+(\d+)(?:\.\d+)?\b", engine_name, re.IGNORECASE)
    if not version_match:
        raise InstallerError(f"The detected UCI engine is not a recognized Stockfish release: {engine_name}")
    version = int(version_match.group(1))
    if expected_version is not None and version != expected_version:
        raise InstallerError(
            f"Expected Stockfish {expected_version}, but the downloaded executable identifies itself as {engine_name}."
        )

    skill_match = re.search(
        r"(?m)^option name Skill Level type spin default -?\d+ min (-?\d+) max (-?\d+)\s*$",
        output,
    )
    if not skill_match:
        raise InstallerError("The engine does not expose the UCI Skill Level option required by Terchess.")
    minimum, maximum = map(int, skill_match.groups())
    if minimum > 0 or maximum < 20:
        raise InstallerError(f"Stockfish Skill Level range {minimum}–{maximum} does not cover 0–20.")
    return engine_name, version


def probe_engine(engine_path: Path, expected_version: int | None = None) -> tuple[str, int]:
    if not engine_path.is_file():
        raise InstallerError(f"Stockfish executable not found: {engine_path}")
    if os.name != "nt":
        engine_path.chmod(engine_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    try:
        result = subprocess.run(
            [str(engine_path)], input="uci\nquit\n", capture_output=True,
            text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise InstallerError(f"Stockfish could not be started: {exc}") from exc
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise InstallerError(f"Stockfish exited with status {result.returncode}: {details[:500]}")
    return parse_uci_output(result.stdout + "\n" + result.stderr, expected_version)


def safe_destination(root: Path, archive_name: str) -> Path:
    normalized = archive_name.replace("\\", "/")
    relative = PurePosixPath(normalized)
    if (relative.is_absolute() or not relative.parts
            or any(part in {"", ".", ".."} for part in relative.parts)
            or ":" in relative.parts[0]):
        raise InstallerError(f"Unsafe path in Stockfish archive: {archive_name!r}")
    root_resolved = root.resolve()
    destination = root.joinpath(*relative.parts).resolve()
    if destination != root_resolved and root_resolved not in destination.parents:
        raise InstallerError(f"Unsafe path in Stockfish archive: {archive_name!r}")
    return destination


def extract_archive(archive_path: Path, extract_to: Path) -> None:
    extract_to.mkdir(parents=True, exist_ok=True)
    if zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path) as archive:
            for item in archive.infolist():
                target = safe_destination(extract_to, item.filename)
                mode = (item.external_attr >> 16) & 0o170000
                if stat.S_ISLNK(mode):
                    raise InstallerError(f"Refusing a symbolic link in archive: {item.filename}")
                if item.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(item) as source, target.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
        return

    try:
        with tarfile.open(archive_path, mode="r:gz") as archive:
            for item in archive.getmembers():
                target = safe_destination(extract_to, item.name)
                if item.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                if not item.isfile():
                    raise InstallerError(f"Refusing a link or special file in archive: {item.name}")
                source = archive.extractfile(item)
                if source is None:
                    raise InstallerError(f"Could not read archive member: {item.name}")
                target.parent.mkdir(parents=True, exist_ok=True)
                with source, target.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
                if os.name != "nt":
                    target.chmod(item.mode & 0o777)
    except (tarfile.TarError, OSError) as exc:
        raise InstallerError(f"Could not extract the Stockfish archive: {exc}") from exc


def find_engine(extract_root: Path, asset_name: str) -> Path:
    if asset_name.endswith(".tar.gz"):
        stem = asset_name[:-7]
    elif asset_name.endswith(".zip"):
        stem = asset_name[:-4]
    else:
        stem = asset_name
    expected_names = {stem.lower(), (stem + ".exe").lower()}
    candidates = sorted(
        (path for path in extract_root.rglob("*") if path.is_file() and path.name.lower() in expected_names),
        key=lambda path: (path.name.lower() != stem.lower(), len(path.parts)),
    )
    if not candidates:
        raise InstallerError(f"The archive did not contain the expected executable ({stem}).")
    return candidates[0]


def download_asset(asset: dict[str, Any], destination: Path) -> None:
    request = urllib.request.Request(
        asset["browser_download_url"], headers={"User-Agent": USER_AGENT}
    )
    expected_digest = asset["digest"].split(":", 1)[1].lower()
    digest = hashlib.sha256()
    try:
        with urllib.request.urlopen(request, timeout=180) as response, destination.open("wb") as stream:
            while True:
                chunk = response.read(CHUNK_SIZE)
                if not chunk:
                    break
                stream.write(chunk)
                digest.update(chunk)
            stream.flush()
            os.fsync(stream.fileno())
    except (OSError, urllib.error.URLError) as exc:
        raise InstallerError(f"Could not download {asset['name']}: {exc}") from exc
    actual_digest = digest.hexdigest()
    if actual_digest != expected_digest:
        destination.unlink(missing_ok=True)
        raise InstallerError(
            f"SHA-256 verification failed for {asset['name']}: expected {expected_digest}, got {actual_digest}."
        )


def write_config(config_path: Path, engine_path: Path) -> bool:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config: dict[str, Any] = {}
    if config_path.exists():
        try:
            with config_path.open("r", encoding="utf-8") as stream:
                loaded = json.load(stream)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            print(f"[Terchess] WARNING: Existing settings could not be read; left unchanged ({exc}).", file=sys.stderr)
            return False
        if not isinstance(loaded, dict):
            print("[Terchess] WARNING: Existing settings are not a JSON object; left unchanged.", file=sys.stderr)
            return False
        config = loaded

    config["stockfish_path"] = str(engine_path.resolve())
    mode = stat.S_IMODE(config_path.stat().st_mode) if config_path.exists() else 0o600
    fd, temporary_name = tempfile.mkstemp(prefix=config_path.name + ".", suffix=".tmp", dir=str(config_path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(config, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        if os.name != "nt":
            os.chmod(temporary_name, mode)
        os.replace(temporary_name, config_path)
    except OSError:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise
    print(f"[Terchess] Saved the Stockfish path in {config_path}.")
    return True


def fetch_latest_release() -> dict[str, Any]:
    request = urllib.request.Request(
        API_URL,
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            release = json.load(response)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise InstallerError(f"Could not query the official Stockfish releases API: {exc}") from exc
    if not isinstance(release, dict):
        raise InstallerError("The official Stockfish releases API returned an invalid response.")
    return release


def install_official_release(platform_name: str, install_root: Path, config_path: Path,
                             machine: str | None = None) -> Path:
    release = fetch_latest_release()
    version = parse_release_version(release)
    tag = str(release["tag_name"])
    asset_name = expected_asset_name(platform_name, machine)
    asset = find_release_asset(release, asset_name)
    install_root.mkdir(parents=True, exist_ok=True)
    target_dir = install_root / tag

    if target_dir.is_dir():
        try:
            engine_path = find_engine(target_dir, asset_name)
            current = probe_engine(engine_path, version)
            print(f"[Terchess] {current[0]} is already installed and verified.")
            write_config(config_path, engine_path)
            return engine_path
        except InstallerError:
            pass

    print(f"[Terchess] Downloading official {release.get('name') or f'Stockfish {version}'} for {platform_name}...", flush=True)
    with tempfile.TemporaryDirectory(prefix=".terchess-stockfish-", dir=str(install_root)) as temporary:
        work_dir = Path(temporary)
        archive_path = work_dir / asset_name
        extract_root = work_dir / "extract"
        download_asset(asset, archive_path)
        extract_archive(archive_path, extract_root)
        candidate = find_engine(extract_root, asset_name)
        engine_name, _ = probe_engine(candidate, version)
        relative_engine = candidate.relative_to(extract_root)
        print(f"[Terchess] Verified {engine_name} (Skill Level 0–20).", flush=True)

        backup_dir = install_root / f".{tag}.previous"
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        if target_dir.exists():
            os.replace(target_dir, backup_dir)
        try:
            os.replace(extract_root, target_dir)
        except OSError:
            if backup_dir.exists() and not target_dir.exists():
                os.replace(backup_dir, target_dir)
            raise
        else:
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
        engine_path = target_dir / relative_engine

    write_config(config_path, engine_path)
    print(f"[Terchess] Installed {engine_name} at {engine_path}")
    return engine_path


def validate_existing(path: Path, config_path: Path) -> int:
    engine_name, version = probe_engine(path)
    write_config(config_path, path)
    print(f"[Terchess] Fallback engine validated: {engine_name} (not necessarily the latest release).")
    return version


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=("linux", "macos", "windows", "android"))
    parser.add_argument("--install-dir", type=Path, help="User-level directory for versioned Stockfish builds")
    parser.add_argument("--config-path", type=Path, required=True, help="Terchess config.json path")
    parser.add_argument("--validate-existing", type=Path, help="Validate and save an existing Stockfish executable instead of downloading")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.validate_existing is not None:
            validate_existing(args.validate_existing, args.config_path)
            return 0
        if not args.platform or args.install_dir is None:
            raise InstallerError("--platform and --install-dir are required when downloading Stockfish.")
        install_official_release(args.platform, args.install_dir, args.config_path)
        return 0
    except InstallerError as exc:
        print(f"[Terchess] ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"[Terchess] ERROR: Unexpected installer failure: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
