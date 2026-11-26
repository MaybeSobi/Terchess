#!/usr/bin/env python3
"""Discover, install, and register official Stockfish engines for Terchess."""
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
_VERSION_RE = re.compile(r"^\d+(?:\.\d+)*$")
_ENGINE_NAME_RE = re.compile(r"(?i)\bStockfish\s+v?(\d+(?:\.\d+)*)\b")
_UCI_SKILL_RE = re.compile(
    r"(?im)^option name Skill Level type spin default -?\d+ min (-?\d+) max (-?\d+)\s*$"
)
_EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".cache",
    "caches", "temp", "tmp", "site-packages", "windowsapps",
}


def info(message: str) -> None:
    print(f"[Terchess] {message}")


def warn(message: str) -> None:
    print(f"[Terchess] Warning: {message}", file=sys.stderr)


def request(url: str):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
    )
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
    return release, release_version(release)


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


def version_key(version: str) -> tuple[int, ...]:
    """Convert a dotted version to a tuple suitable for numeric comparisons."""
    if not _VERSION_RE.fullmatch(version):
        raise ValueError(f"Invalid Stockfish version: {version}")
    return tuple(int(part) for part in version.split("."))


def is_newer_version(first: str, second: str) -> bool:
    """Return True when first is numerically newer than second."""
    left, right = version_key(first), version_key(second)
    width = max(len(left), len(right))
    return left + (0,) * (width - len(left)) > right + (0,) * (width - len(right))


def same_version(first: str, second: str) -> bool:
    """Compare dotted release versions while ignoring trailing zero components."""
    return not is_newer_version(first, second) and not is_newer_version(second, first)


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


def parse_uci_info(output: str) -> dict[str, str] | None:
    """Parse a Stockfish UCI response and require Terchess's Skill Level range."""
    if "uciok" not in output.splitlines():
        return None
    name_match = _ENGINE_NAME_RE.search(output)
    skill_match = _UCI_SKILL_RE.search(output)
    if not name_match or not skill_match:
        return None
    if int(skill_match.group(1)) > 0 or int(skill_match.group(2)) < 20:
        return None
    return {"version": name_match.group(1), "name": name_match.group(0)}


def probe_stockfish(path: Path | str) -> dict[str, str] | None:
    """Run a short UCI handshake and identify a compatible Stockfish executable."""
    executable = Path(path).expanduser()
    if not executable.is_file():
        return None
    if os.name != "nt" and not os.access(executable, os.X_OK):
        return None
    try:
        result = subprocess.run(
            [str(executable)],
            input="uci\nquit\n",
            capture_output=True,
            text=True,
            timeout=12,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return parse_uci_info(result.stdout + "\n" + result.stderr)


def is_expected_stockfish(path: Path, version: str) -> bool:
    """Compatibility wrapper: validate an executable against one exact version."""
    details = probe_stockfish(path)
    return bool(details and details["version"] == version)


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


def _path_identity(path: Path | str) -> str:
    return os.path.normcase(os.path.abspath(str(Path(path).expanduser())))


def _candidate_name(name: str) -> bool:
    value = name.lower()
    if value in {"stockfish", "stockfish.exe"}:
        return True
    if not value.startswith("stockfish"):
        return False
    if os.name == "nt":
        return value.endswith(".exe")
    return not value.endswith((".zip", ".tar.gz", ".tgz", ".txt", ".md", ".json", ".sha256"))


def search_roots() -> tuple[list[Path], list[Path]]:
    """Return shallow scan roots and direct executable directories for this OS."""
    home = Path.home()
    shallow = [
        home / "Downloads",
        home / "Desktop",
        home / "Documents",
        home / "Engines",
        home / "Stockfish",
        home / "Applications",
        home / "tools",
        home / ".local" / "share" / "terchess-engine",
        home / ".local" / "share" / "stockfish",
    ]
    direct = [Path.cwd()]
    direct.extend(Path(p) for p in os.environ.get("PATH", "").split(os.pathsep) if p)

    if platform.system() == "Windows":
        local = Path(os.environ.get("LOCALAPPDATA", home / "AppData/Local"))
        program_files = Path(os.environ.get("ProgramFiles", "C:/Program Files"))
        program_files_x86 = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
        shallow.extend([
            Path("C:/Engines"),
            local / "Programs" / "Stockfish",
            local / "Stockfish",
            program_files / "Stockfish",
            program_files_x86 / "Stockfish",
        ])
    elif platform.system() == "Darwin":
        direct.extend([
            Path("/usr/local/bin"),
            Path("/opt/homebrew/bin"),
            Path("/usr/local/games"),
            Path("/usr/games"),
        ])
        shallow.extend([
            Path("/Applications/Stockfish.app/Contents/MacOS"),
            Path("/opt/homebrew/Cellar/stockfish"),
            Path("/usr/local/Cellar/stockfish"),
        ])
    else:
        direct.extend([
            Path("/usr/bin"),
            Path("/usr/games"),
            Path("/usr/local/bin"),
            Path("/usr/local/games"),
            Path("/snap/bin"),
        ])
        prefix = os.environ.get("PREFIX")
        if prefix:
            direct.append(Path(prefix) / "bin")

    return shallow, direct


def candidate_executables(
    config: dict,
    extra_roots: list[Path] | None = None,
    extra_directories: list[Path] | None = None,
) -> list[Path]:
    """Find plausible local Stockfish executables without crawling the whole disk."""
    found: list[Path] = []
    seen: set[str] = set()

    def add(path: Path | str) -> None:
        try:
            candidate = Path(path).expanduser()
            if not candidate.is_file():
                return
            resolved = candidate.resolve()
            identity = _path_identity(resolved)
            if identity not in seen:
                found.append(resolved)
                seen.add(identity)
        except (OSError, RuntimeError):
            return

    configured = config.get("stockfish_path")
    if isinstance(configured, str) and configured.strip():
        add(configured)
    catalog = config.get("stockfish_engines")
    if isinstance(catalog, list):
        for item in catalog:
            if isinstance(item, dict) and isinstance(item.get("path"), str):
                add(item["path"])

    for command in ("stockfish", "stockfish.exe"):
        located = shutil.which(command)
        if located:
            add(located)

    shallow, direct = search_roots()
    if extra_roots:
        shallow.extend(extra_roots)
    if extra_directories:
        direct.extend(extra_directories)

    # Search PATH and known OS install directories one level deep.
    for directory in direct:
        try:
            if not directory.is_dir():
                continue
            for child in directory.iterdir():
                if child.is_file() and _candidate_name(child.name):
                    add(child)
        except OSError:
            continue

    # Search common user download/install folders to a bounded depth. This finds
    # manually extracted Stockfish ZIPs without traversing the entire home disk.
    for root in shallow:
        if not root.is_dir():
            continue
        root_depth = len(root.parts)
        try:
            for current, directories, files in os.walk(root):
                current_path = Path(current)
                depth = len(current_path.parts) - root_depth
                directories[:] = [
                    name for name in directories
                    if name.lower() not in _EXCLUDED_DIRS and depth < 4
                ]
                for filename in files:
                    if _candidate_name(filename):
                        add(current_path / filename)
                        if len(found) >= 40:
                            return found
        except OSError:
            continue

    return found


def discover_existing_engines(config: dict) -> list[dict[str, str]]:
    """Find and UCI-validate every Stockfish binary in known local locations."""
    results: list[dict[str, str]] = []
    for path in candidate_executables(config):
        details = probe_stockfish(path)
        if details:
            results.append({"path": str(path), "version": details["version"]})
    results.sort(key=lambda item: version_key(item["version"]), reverse=True)
    return results


def read_config() -> dict:
    target = config_path()
    if not target.exists():
        return {}
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Existing Terchess settings are invalid and were not changed: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("Existing Terchess settings are not a JSON object; they were not changed.")
    return value


def save_config(
    engines: list[dict[str, str]],
    selected_path: str | None,
    remember_choice: bool,
    deferred_version: str | None = None,
) -> None:
    """Merge the detected engines into existing preferences atomically."""
    target = config_path()
    config = read_config()
    config["stockfish_engines"] = engines
    config["stockfish_path"] = selected_path
    config["remember_engine_choice"] = remember_choice
    config["stockfish_deferred_version"] = deferred_version
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
    info(f"Saved {len(engines)} Stockfish engine(s) in {target}")


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


def download_release(release: dict, version: str, *, alongside: bool) -> Path:
    """Download, checksum, extract, and validate one official release asset."""
    name = asset_name()
    if not name:
        raise RuntimeError(
            f"Latest official Stockfish {version} has no supported binary for "
            f"{platform.system()} / {platform.machine()}."
        )
    assets = {
        item.get("name"): item
        for item in release.get("assets", [])
        if isinstance(item, dict)
    }
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
        digest_hash = hashlib.sha256()
        with archive.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest_hash.update(chunk)
        if digest_hash.hexdigest().lower() != digest.split(":", 1)[1].lower():
            raise RuntimeError("Stockfish download failed SHA-256 verification.")
        extracted = tempdir / "extracted"
        safe_extract(archive, extracted)
        candidates = [
            path for path in extracted.rglob("*")
            if path.is_file() and path.name.lower() in {"stockfish", "stockfish.exe"}
        ]
        if not candidates:
            raise RuntimeError("No Stockfish executable was found in the verified release archive.")
        source = candidates[0]

        base = install_dir()
        destination = (
            base / "versions" / version / ("stockfish.exe" if os.name == "nt" else "stockfish")
            if alongside
            else base / ("stockfish.exe" if os.name == "nt" else "stockfish")
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
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
    return destination.resolve()


def _configured_engine_path(config: dict, engines: list[dict[str, str]]) -> str | None:
    previous = config.get("stockfish_path")
    if isinstance(previous, str):
        previous_key = _path_identity(previous)
        for engine in engines:
            if _path_identity(engine["path"]) == previous_key:
                return engine["path"]
    return engines[0]["path"] if engines else None


def prompt_update_strategy(existing: list[dict[str, str]], latest_version: str) -> str:
    """Ask whether to replace, keep both, or defer this release update."""
    info("An update is available:")
    for engine in existing:
        info(f"  Installed Stockfish {engine['version']}: {engine['path']}")
    info(f"  Latest stable Stockfish {latest_version}")
    print("  1 · Replace the engine Terchess uses with the latest version")
    print("      (manually installed files outside Terchess are not deleted)")
    print("  2 · Install the latest version alongside the existing engine(s)")
    print("      (Terchess will ask which engine to use each time it starts)")
    print("  3 · Keep the existing engine and skip this update for now")
    if not sys.stdin.isatty():
        warn("No interactive terminal is available; keeping the existing engine.")
        return "keep"
    while True:
        try:
            choice = input("Choose [1/2/3] (default 1): ").strip() or "1"
        except EOFError:
            return "keep"
        if choice == "1":
            return "replace"
        if choice == "2":
            return "alongside"
        if choice == "3":
            return "keep"
        print("Enter 1, 2, or 3.")


def _remember_default(config: dict, engines: list[dict[str, str]]) -> bool:
    raw_catalog = config.get("stockfish_engines")
    if isinstance(raw_catalog, list) and raw_catalog:
        value = config.get("remember_engine_choice", True)
        return value if isinstance(value, bool) else True
    return len(engines) <= 1


def _remove_replaced_managed_engines(
    existing: list[dict[str, str]],
    new_engine: Path,
) -> None:
    """Remove only old binaries inside Terchess's private engine directory."""
    managed_root = install_dir().resolve()
    for item in existing:
        old_path = Path(item["path"]).resolve()
        if old_path == new_engine.resolve():
            continue
        try:
            old_path.relative_to(managed_root)
        except ValueError:
            continue
        try:
            old_path.unlink(missing_ok=True)
            parent = old_path.parent
            while parent != managed_root and managed_root in parent.parents:
                try:
                    parent.rmdir()
                except OSError:
                    break
                parent = parent.parent
        except OSError as exc:
            warn(f"Could not remove replaced Terchess-managed engine {old_path}: {exc}")


def main() -> int:
    # Scan local engine paths before downloading anything. This includes the
    # saved configuration, PATH, normal package locations, Downloads, and
    # common manual-install folders such as C:\Engines.
    config = read_config()
    existing = discover_existing_engines(config)
    configured_path = _configured_engine_path(config, existing)

    try:
        release, latest = latest_release()
    except Exception as exc:
        if not existing:
            raise
        info(f"Could not check the latest Stockfish release: {exc}")
        save_config(existing, configured_path, _remember_default(config, existing))
        info("Keeping the compatible Stockfish engine(s) already installed.")
        return 0

    if existing:
        best_installed = existing[0]["version"]
        has_latest = any(same_version(item["version"], latest) for item in existing)
        if has_latest:
            remember = _remember_default(config, existing)
            selected = _configured_engine_path(config, existing)
            # If a previously single-engine setup now has a second discovered
            # version, surface the chooser rather than silently staying on an
            # older remembered path.
            previous_catalog = config.get("stockfish_engines")
            catalog_was_multiple = isinstance(previous_catalog, list) and len(previous_catalog) > 1
            selected_version = next(
                (item["version"] for item in existing if selected and _path_identity(item["path"]) == _path_identity(selected)),
                None,
            )
            if len(existing) > 1 and not catalog_was_multiple and (selected_version is None or not same_version(selected_version, latest)):
                remember = False
            save_config(existing, selected, remember, None)
            info(f"Stockfish {latest} is already installed. No engine download is needed.")
            if len(existing) > 1 and not remember:
                info("Multiple engines are available; Terchess will ask which one to use when it starts.")
            return 0

        if is_newer_version(best_installed, latest):
            save_config(existing, configured_path, _remember_default(config, existing))
            info(
                f"Your installed Stockfish {best_installed} is newer than the latest stable "
                f"release listed by GitHub ({latest}). It will not be downgraded."
            )
            return 0

        if config.get("stockfish_deferred_version") == latest:
            save_config(existing, configured_path, _remember_default(config, existing), latest)
            info(f"Stockfish {latest} was previously deferred. Keeping your existing engine(s).")
            return 0

        strategy = prompt_update_strategy(existing, latest)
        if strategy == "keep":
            save_config(existing, configured_path, _remember_default(config, existing), latest)
            info("Keeping your existing Stockfish engine. The update will be offered again when a newer release appears.")
            return 0
        alongside = strategy == "alongside"
    else:
        alongside = False
        info("No compatible Stockfish installation was found. Installing the latest stable release.")

    info(f"Downloading official Stockfish {latest}...")
    installed_path = download_release(release, latest, alongside=alongside)
    new_entry = {"path": str(installed_path), "version": latest}

    if alongside:
        catalog = existing + [new_entry]
        selected = configured_path or existing[0]["path"]
        save_config(catalog, selected, False, None)
        info("Installed alongside the existing engine(s); none of the previous copies were removed.")
        info("The next 'terchess' launch will show the engine selector.")
    else:
        if existing:
            _remove_replaced_managed_engines(existing, installed_path)
        catalog = [new_entry]
        save_config(catalog, str(installed_path), True, None)
        info(f"Terchess will now use Stockfish {latest}.")
        if existing:
            info("Any manually installed executable outside Terchess was left untouched.")
    info(f"Installed and validated official Stockfish {latest}: {installed_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[Terchess] Stockfish installation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
