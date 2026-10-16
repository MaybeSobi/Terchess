"""Main menu and command-line entry point for Terchess."""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

import chess
import chess.engine
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from terchess import __version__
from terchess.clock import color_name
from terchess.config import get_config_path, load_config, save_config
from terchess.engine import find_engine
from terchess.game import play_game

console = Console()
TIME_CONTROLS: dict[str, tuple[int, int]] = {
    "1": (60, 0), "2": (180, 2), "3": (300, 0), "4": (600, 0), "5": (900, 10),
}
TIME_CONTROL_LABELS = {
    "1": "Bullet 1+0", "2": "Blitz 3+2", "3": "Blitz 5+0",
    "4": "Rapid 10+0", "5": "Rapid 15+10",
}


@dataclass
class GameSettings:
    skill_level: int = 10
    human_color: chess.Color = chess.WHITE
    time_control_key: str = "3"
    show_board: bool = True

    @property
    def base_seconds(self) -> int:
        return TIME_CONTROLS[self.time_control_key][0]

    @property
    def increment_seconds(self) -> int:
        return TIME_CONTROLS[self.time_control_key][1]

    @property
    def time_control_label(self) -> str:
        return TIME_CONTROL_LABELS[self.time_control_key]


def parse_color_choice(value: str) -> chess.Color | None:
    """Accept numeric, single-letter, and full-word color choices."""
    normalized = value.strip().lower()
    if normalized in {"1", "w", "white"}:
        return chess.WHITE
    if normalized in {"2", "b", "black"}:
        return chess.BLACK
    return None


def _ask_skill_level(current: int) -> int:
    while True:
        raw = Prompt.ask("Stockfish Skill Level (0-20)", default=str(current)).strip()
        try:
            level = int(raw)
        except ValueError:
            console.print("[red]Enter a whole number from 0 to 20.[/red]")
            continue
        if 0 <= level <= 20:
            return level
        console.print("[red]Skill Level must be between 0 and 20.[/red]")


def _ask_color(current: chess.Color) -> chess.Color:
    console.print("\n[bold cyan]Choose your side[/bold cyan]")
    console.print("  [bold]1[/bold] · White (you move first)")
    console.print("  [bold]2[/bold] · Black (Stockfish moves first)")
    default = "1" if current == chess.WHITE else "2"
    while True:
        value = Prompt.ask("Your choice [1/2, white/black, w/b]", default=default)
        color = parse_color_choice(value)
        if color is not None:
            return color
        console.print("[red]Enter 1 / white / w or 2 / black / b.[/red]")


def _ask_time_control(current: str) -> str:
    table = Table(title="Choose a time control", header_style="bold cyan")
    table.add_column("Option", justify="center", width=8)
    table.add_column("Mode")
    table.add_column("Clock", justify="center")
    for key, label in TIME_CONTROL_LABELS.items():
        base, increment = TIME_CONTROLS[key]
        table.add_row(key, label.split(" ")[0], f"{base // 60}+{increment}")
    console.print(table)
    while True:
        key = Prompt.ask("Time control", choices=list(TIME_CONTROLS), default=current)
        if key in TIME_CONTROLS:
            return key


def show_settings(settings: GameSettings) -> None:
    console.print(Panel(
        f"[bold]Skill Level:[/bold] {settings.skill_level}/20\n"
        f"[bold]Your side:[/bold] {color_name(settings.human_color)}\n"
        f"[bold]Time control:[/bold] {settings.time_control_label}\n"
        f"[bold]Display mode:[/bold] {'Board view' if settings.show_board else 'Blindfold (text-only)'}",
        title="Current settings", border_style="cyan",
    ))


def _settings_config(settings: GameSettings, stockfish_path: str | None) -> dict[str, object]:
    return {
        "stockfish_path": stockfish_path,
        "skill_level": settings.skill_level,
        "human_color": "white" if settings.human_color == chess.WHITE else "black",
        "time_control_key": settings.time_control_key,
        "show_board": settings.show_board,
    }


def _save_preferences(settings: GameSettings, stockfish_path: str | None, *, announce: bool = False) -> None:
    """Persist settings without making an unwritable config file fatal."""
    try:
        destination = save_config(_settings_config(settings, stockfish_path))
        if announce:
            console.print(f"[green]Preferences saved to {destination}[/green]")
    except OSError as exc:
        console.print(f"[yellow]Warning: could not save preferences: {exc}[/yellow]")


def _settings_from_config(config: dict[str, object]) -> GameSettings:
    return GameSettings(
        skill_level=int(config["skill_level"]),
        human_color=chess.WHITE if config["human_color"] == "white" else chess.BLACK,
        time_control_key=str(config["time_control_key"]),
        show_board=bool(config["show_board"]),
    )


def settings_menu(settings: GameSettings, stockfish_path: str | None) -> None:
    while True:
        console.print()
        show_settings(settings)
        console.print(
            "[bold cyan]SETTINGS[/bold cyan]\n"
            "  [bold]1[/bold] · Stockfish difficulty\n"
            "  [bold]2[/bold] · Play as White or Black\n"
            "  [bold]3[/bold] · Time control\n"
            "  [bold]4[/bold] · Back to main menu"
        )
        choice = Prompt.ask("Select setting", choices=["1", "2", "3", "4"], default="4")
        if choice == "1":
            settings.skill_level = _ask_skill_level(settings.skill_level)
            _save_preferences(settings, stockfish_path)
        elif choice == "2":
            settings.human_color = _ask_color(settings.human_color)
            _save_preferences(settings, stockfish_path)
        elif choice == "3":
            settings.time_control_key = _ask_time_control(settings.time_control_key)
            _save_preferences(settings, stockfish_path)
        else:
            return


def _ask_engine_path() -> str | None:
    console.print(
        "Stockfish wasn't found automatically. Enter the full path to the Stockfish executable.\n"
        "Examples: C:\\Engines\\stockfish\\stockfish-windows-x86-64-avx2.exe\n"
        "          /usr/games/stockfish\n"
        "Type 'quit' to exit."
    )
    while True:
        raw = Prompt.ask("Stockfish path").strip()
        if raw.lower() == "quit":
            return None
        found = find_engine(raw)
        if found:
            return found
        console.print("[red]File not found. Check the path and try again.[/red]")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="terchess",
        description="Terchess (Terminal + Chess): terminal chess against local Stockfish.",
    )
    parser.add_argument("--engine", help="Temporarily override the saved Stockfish executable path")
    parser.add_argument("--version", action="version", version=f"Terchess {__version__}")
    args = parser.parse_args()
    saved_config = load_config()
    settings = _settings_from_config(saved_config)
    explicit_engine_override = args.engine is not None
    saved_engine_path = saved_config.get("stockfish_path")
    release_label = f"Release Candidate {__version__}" if "rc" in __version__ else f"Version {__version__}"
    console.print(Panel.fit(
        "[bold bright_green]TERCHESS[/bold bright_green] [white]· Terminal + Chess[/white]\n"
        f"[white]{release_label}[/white]\n"
        "[dim]Local Stockfish · Live clocks · Keyboard-first chess[/dim]",
        border_style="bright_green",
    ))
    if explicit_engine_override:
        engine_path = find_engine(args.engine)
        if engine_path is None:
            console.print(f"[red]Could not find Stockfish at: {args.engine}[/red]")
            sys.exit(2)
        persistent_engine_path = saved_engine_path if isinstance(saved_engine_path, str) else None
    else:
        engine_path = find_engine(saved_engine_path) if isinstance(saved_engine_path, str) else None
        if engine_path is None:
            engine_path = find_engine()
        if engine_path is None:
            engine_path = _ask_engine_path()
            if engine_path is None:
                return
        persistent_engine_path = engine_path
        _save_preferences(settings, persistent_engine_path)
    console.print(f"[dim]Preferences: {get_config_path()}[/dim]")
    try:
        console.print(f"[dim]Starting Stockfish: {Path(engine_path).name}[/dim]")
        with chess.engine.SimpleEngine.popen_uci(engine_path, timeout=30.0) as engine:
            console.print(f"[green]Connected to {engine.id.get('name', 'UCI engine')}[/green]")
            while True:
                console.print()
                show_settings(settings)
                console.print(
                    "[bold bright_green]MAIN MENU[/bold bright_green]\n"
                    "  [bold]1[/bold] · Start game\n"
                    f"  [bold]2[/bold] · Display mode: {'Board view' if settings.show_board else 'Blindfold / text-only'} (toggle)\n"
                    "  [bold]3[/bold] · Settings\n"
                    "  [bold]4[/bold] · About Terchess\n"
                    "  [bold]5[/bold] · Quit"
                )
                choice = Prompt.ask("Select option", choices=["1", "2", "3", "4", "5"], default="1")
                if choice == "1":
                    asyncio.run(play_game(
                        engine, settings.skill_level, settings.human_color,
                        settings.base_seconds, settings.increment_seconds, console,
                        show_board=settings.show_board,
                    ))
                elif choice == "2":
                    settings.show_board = not settings.show_board
                    mode_name = "Board view" if settings.show_board else "Blindfold / text-only"
                    _save_preferences(settings, persistent_engine_path)
                    console.print(f"[green]Display mode set to: {mode_name}[/green]")
                elif choice == "3":
                    settings_menu(settings, persistent_engine_path)
                elif choice == "4":
                    console.print(Panel(
                        f"Terchess {__version__}\n\n"
                        "Terminal + Chess: play chess in your terminal against a local Stockfish engine.\n"
                        "The main menu display toggle switches between the board and Blindfold text-only mode.\n"
                        "Settings include Skill Level 0–20, side, and time control. Preferences are saved between runs.",
                        title="About", border_style="bright_blue",
                    ))
                else:
                    console.print("[green]Thanks for playing Terchess. Goodbye![/green]")
                    return
    except (OSError, chess.engine.EngineError, RuntimeError, ValueError) as exc:
        console.print(f"[bold red]Could not run Terchess: {exc}[/bold red]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted. Goodbye.[/yellow]")


if __name__ == "__main__":
    main()
