from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_installer(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_windows_installer_defaults_to_current_main_branch():
    script = read_installer("install.ps1")

    assert '[string]$Channel = "main"' in script
    assert 'https://codeload.github.com/$Repo/zip/refs/heads/main' in script
    assert 'if ($Channel -eq "release")' in script


def test_linux_installer_defaults_to_current_main_branch():
    script = read_installer("install-linux.sh")

    assert 'CHANNEL="${1:-main}"' in script
    assert 'main)' in script
    assert 'https://codeload.github.com/${REPO}/zip/refs/heads/main' in script
    assert 'release)' in script


def test_macos_installer_defaults_to_current_main_branch():
    script = read_installer("install-macos.sh")

    assert 'CHANNEL="${1:-main}"' in script
    assert 'main)' in script
    assert 'https://codeload.github.com/${REPO}/zip/refs/heads/main' in script
    assert 'release)' in script


def test_termux_installer_uses_current_main_branch():
    script = read_installer("install-termux.sh")

    assert "current main branch" in script
    assert 'https://codeload.github.com/${REPO}/zip/refs/heads/main' in script


def test_all_installers_preserve_the_existing_python_environment():
    windows = read_installer("install.ps1")
    linux = read_installer("install-linux.sh")
    macos = read_installer("install-macos.sh")
    termux = read_installer("install-termux.sh")

    assert '$_.Name -eq ".venv"' in windows
    assert '! -name ".venv"' in linux
    assert '! -name ".venv"' in macos
    assert '! -name ".venv"' in termux
