#!/usr/bin/env python3
"""Install and validate the latest stable official Stockfish release for Terchess."""
from __future__ import annotations

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
import urllib.request
import zipfile
from pathlib import Path

REPOSITORY = "official-stockfish/Stockfish"
USER_AGENT = "Terchess-Stockfish-Installer"


def info(message: str) -> None:
    print(f"[Terchess] {message}")


def request(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"})
    return urllib.request.urlopen(req, timeout=45)


def latest_release() -> tuple[dict, str]:
    """Return GitHub's latest non-draft, non-prerelease release and its version."""
    url = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
    with request(url) as response:
        release = json.load(response)
    if not isinstance(release, dict):
        raise RuntimeError("GitHub returned an invalid Stockfish release response.")
    if release.get("draft") or release.get("prerelease"):
        raise RuntimeError("GitHub did not return a stable Stockfish release.")
    version = release_version(release)
    return release, version


def release_version(release: dict) -> str:
    """Extract the Stockfish version from the official release tag or title."""
    tag = str(release.get("tag_name", ""))
    match = re.search(r"(?:^|[^A-Za-z0-9])sf[_-](\d+(?:\.\d+)*)", tag, re.IGNORECASE)
    if not match:
        title = str(release.get("name", ""))
        match = re.search(r"\bStockfish\s+(\d+(?:\.\d+)*)\b", title, re.IGNORECASE)
    if not match:
        raise RuntimeError(
            "Could not determine the Stockfish version from the latest official release "
            f"(tag: {tag or 'missing'}). Refusing to install an unidentifiable build."
        )
    return match.group(1)


def asset_name() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == "windows":
        return {
            "amd64": "stockfish-windows-x86-64-universal.zip",
            "x86_64": "stockfish-windows-x86-64-universal.zip",
            "arm64": "stockfish-windows-arm64-universal.zip",
            "aarch64": "stockfish-windows-arm64-universal.zip",
        }.get(machine, "")
    if system == "darwin":
        return "stockfish-macos-universal.tar.gz"
    if system == "android" or "com.termux" in os.environ.get("PREFIX", ""):
        return {
            "aarch64": "stockfish-android-arm64-universal.tar.gz",
            "arm64": "stockfish-android-arm64-universal.tar.gz",
            "armv7l": "stockfish-android-armv7-neon.tar.gz",
            "armv7": "stockfish-android-armv7-neon.tar.gz",
        }.get(machine, "")
    if system == "linux":
        return {
            "x86_64": "stockfish-linux-x86-64-universal.tar.gz",
            "amd64": "stockfish-linux-x86-64-universal.tar.gz",
            "aarch64": "stockfish-linux-arm64-universal.tar.gz",
            "arm64": "stockfish-linux-arm64-universal.tar.gz",
            "riscv64": "stockfish-linux-riscv64-universal.tar.gz",
        }.get(machine, "")
    return ""


def is_expected_stockfish(path: Path, version: str) -> bool:
    try:
        result = subprocess.run(
            [str(path)], input="uci\nquit\n", capture_output=True,
            text=True, timeout=12, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    output = result.stdout + "\n" + result.stderr
    if result.returncode != 0 or "uciok" not in output.splitlines():
        return False
    if not re.search(
        rf"(?im)^id name .*?\bStockfish\s+{re.escape(version)}(?![\d.])",
        output,
    ):
        return False
    match = re.search(
        r"(?m)^option name Skill Level type spin default -?\d+ min (-?\d+) max (-?\d+)\s*$",
        output,
    )
    return bool(match and int(match.group(1)) <= 0 and int(match.group(2)) >= 20)


def config_path() -> Path:
    if platform.system() == "Windows":
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
        return root / "Terchess" / "config.json"
    if platform.system() == "Darwin":
        return Path.home() / "Library/Application Support/Terchess/config.json"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    root = Path(xdg).expanduser() if xdg and Path(xdg).expanduser().is_absolute() else Path.home() / ".config"
    return root / "terchess" / "config.json"


def install_dir() -> Path:
    if platform.system() == "Windows":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
        return root / "Terchess" / "engine"
    if platform.system() == "Darwin":
        return Path.home() / "Library/Application Support/Terchess/engine"
    return Path.home() / ".local/share/terchess-engine"


def save_config(engine: Path) -> None:
    target = config_path()
    config = {}
    if target.exists():
        try:
            config = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Existing Terchess settings are invalid and were not changed: {exc}") from exc
        if not isinstance(config, dict):
            raise RuntimeError("Existing Terchess settings are not a JSON object; they were not changed.")
    config["stockfish_path"] = str(engine.resolve())
    target.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else 0o600
    fd, temporary = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(config, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, target)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    info(f"Saved Stockfish path in {target}")


def safe_extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as zf:
            for item in zf.infolist():
                out = (destination / item.filename).resolve()
                if out != root and root not in out.parents:
                    raise RuntimeError("Unsafe path in Stockfish ZIP archive.")
                if item.is_dir():
                    out.mkdir(parents=True, exist_ok=True)
                else:
                    out.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(item) as src, out.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
    else:
        with tarfile.open(archive, "r:gz") as tf:
            for item in tf.getmembers():
                out = (destination / item.name).resolve()
                if out != root and root not in out.parents:
                    raise RuntimeError("Unsafe path in Stockfish TAR archive.")
                if item.isdir():
                    out.mkdir(parents=True, exist_ok=True)
                elif item.isfile():
                    source = tf.extractfile(item)
                    if source is None:
                        continue
                    out.parent.mkdir(parents=True, exist_ok=True)
                    with source, out.open("wb") as dst:
                        shutil.copyfileobj(source, dst)


def main() -> int:
    release, version = latest_release()
    name = asset_name()
    if not name:
        raise RuntimeError(
            f"Latest official Stockfish {version} has no supported binary for "
            f"{platform.system()} / {platform.machine()}."
        )

    existing = shutil.which("stockfish") or shutil.which("stockfish.exe")
    if existing and is_expected_stockfish(Path(existing), version):
        engine = Path(existing).resolve()
        info(f"Using existing official Stockfish {version}: {engine}")
        save_config(engine)
        return 0

    info(f"Fetching latest stable official Stockfish {version} for {platform.system()} / {platform.machine()}...")
    assets = {item.get("name"): item for item in release.get("assets", []) if isinstance(item, dict)}
    asset = assets.get(name)
    if not asset:
        available = ", ".join(sorted(item for item in assets if item))
        raise RuntimeError(
            f"Official Stockfish {version} asset not found: {name}. "
            f"Assets published in this release: {available or 'none'}"
        )
    digest = asset.get("digest", "")
    if not digest.startswith("sha256:"):
        raise RuntimeError("GitHub did not provide a SHA-256 digest for the Stockfish asset.")
    download_url = asset.get("browser_download_url")
    if not download_url:
        raise RuntimeError("The official Stockfish release asset has no download URL.")

    with tempfile.TemporaryDirectory(prefix="terchess-stockfish-") as temp:
        tempdir = Path(temp)
        archive = tempdir / name
        with request(download_url) as response, archive.open("wb") as output:
            shutil.copyfileobj(response, output)
        actual = hashlib.sha256(archive.read_bytes()).hexdigest()
        if actual.lower() != digest.split(":", 1)[1].lower():
            raise RuntimeError("Stockfish download failed SHA-256 verification.")
        extracted = tempdir / "extracted"
        safe_extract(archive, extracted)
        candidates = [p for p in extracted.rglob("*") if p.is_file() and p.name.lower() in ("stockfish", "stockfish.exe")]
        if not candidates:
            raise RuntimeError("No Stockfish executable was found in the verified release archive.")
        source = candidates[0]
        destination_dir = install_dir()
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = destination_dir / ("stockfish.exe" if os.name == "nt" else "stockfish")
        temporary_engine = destination.with_name(destination.name + ".new")
        shutil.copy2(source, temporary_engine)
        if os.name != "nt":
            temporary_engine.chmod(temporary_engine.stat().st_mode | 0o111)
        if not is_expected_stockfish(temporary_engine, version):
            temporary_engine.unlink(missing_ok=True)
            raise RuntimeError(
                f"Downloaded engine failed Stockfish {version} UCI/version/Skill Level validation."
            )
        os.replace(temporary_engine, destination)
    save_config(destination)
    info(f"Installed and validated latest official Stockfish {version}: {destination}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[Terchess] Stockfish installation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
