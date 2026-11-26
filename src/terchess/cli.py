"""Main menu and command-line entry point for Terchess."""

from __future__ import annotations

import argparse
import asyncio
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import chess
import chess.engine
import chess.pgn
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from terchess import __version__
from terchess.board_view import board_table, move_history
from terchess.clock import color_name
from terchess.config import get_config_path, load_config, save_config
from terchess.engine import find_engine
from terchess.game import play_game, play_hotseat_game
from terchess.history import (
    export_all_pgn,
    export_pgn,
    get_database_path,
    import_pgn_file,
    list_games,
    load_game,
)

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
    return Prompt.ask("Time control", choices=list(TIME_CONTROLS), default=current)


def show_settings(settings: GameSettings) -> None:
    console.print(Panel(
        f"[bold]Skill Level:[/bold] {settings.skill_level}/20\n"
        f"[bold]Your side:[/bold] {color_name(settings.human_color)}\n"
        f"[bold]Time control:[/bold] {settings.time_control_label}\n"
        f"[bold]Display mode:[/bold] {'Board view' if settings.show_board else 'Blindfold (text-only)'}",
        title="Current settings", border_style="cyan",
    ))


def _settings_config(
    settings: GameSettings,
    stockfish_path: str | None,
    stockfish_engines: list[dict[str, str]] | None = None,
    remember_engine_choice: bool = True,
    deferred_version: str | None = None,
) -> dict[str, object]:
    return {
        "stockfish_path": stockfish_path,
        "stockfish_engines": stockfish_engines or [],
        "remember_engine_choice": remember_engine_choice,
        "stockfish_deferred_version": deferred_version,
        "skill_level": settings.skill_level,
        "human_color": "white" if settings.human_color == chess.WHITE else "black",
        "time_control_key": settings.time_control_key,
        "show_board": settings.show_board,
    }


def _save_preferences(
    settings: GameSettings,
    stockfish_path: str | None,
    stockfish_engines: list[dict[str, str]] | None = None,
    remember_engine_choice: bool = True,
    deferred_version: str | None = None,
    *,
    announce: bool = False,
) -> None:
    """Persist settings without making an unwritable config file fatal."""
    try:
        destination = save_config(_settings_config(
            settings, stockfish_path, stockfish_engines,
            remember_engine_choice, deferred_version,
        ))
        if announce:
            console.print(f"[green]Preferences saved to {destination}[/green]")
    except OSError as exc:
        console.print(f"[yellow]Warning: could not save preferences: {exc}[/yellow]")


def _available_engine_catalog(config: dict[str, object]) -> list[dict[str, str]]:
    """Return saved engine choices whose executable files are still present."""
    raw = config.get("stockfish_engines")
    entries: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(path_value: object, version_value: object = "Unknown") -> None:
        if not isinstance(path_value, str) or not path_value.strip():
            return
        path = Path(path_value.strip()).expanduser()
        if not path.is_file():
            return
        try:
            resolved = str(path.resolve())
        except OSError:
            resolved = str(path)
        identity = str(path.resolve()).casefold() if os.name == "nt" else str(path.resolve())
        if identity in seen:
            return
        version = version_value.strip() if isinstance(version_value, str) else "Unknown"
        entries.append({"path": resolved, "version": version or "Unknown"})
        seen.add(identity)

    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                add(item.get("path"), item.get("version"))
    add(config.get("stockfish_path"))
    return entries


def _choose_stockfish_engine(
    engines: list[dict[str, str]],
    current_path: str | None,
) -> tuple[str | None, bool]:
    """Show the installed-engine chooser and ask whether to remember its choice."""
    if not engines:
        return None, False

    table = Table(title="Choose a Stockfish engine", header_style="bold cyan")
    table.add_column("#", justify="center", width=4)
    table.add_column("Version", style="bold")
    table.add_column("Executable")
    default = "1"
    for index, engine_info in enumerate(engines, start=1):
        version = engine_info.get("version", "Unknown")
        table.add_row(str(index), f"Stockfish {version}" if version != "Unknown" else "Stockfish", engine_info["path"])
        if current_path and os.path.normcase(os.path.abspath(engine_info["path"])) == os.path.normcase(os.path.abspath(current_path)):
            default = str(index)
    console.print(Panel(table, title="Installed engines", border_style="bright_green"))
    selected = Prompt.ask("Select engine", choices=[str(i) for i in range(1, len(engines) + 1)], default=default)
    selected_path = engines[int(selected) - 1]["path"]
    remember_answer = Prompt.ask("Remember my choice? [y/N]", choices=["y", "n"], default="n").lower()
    return selected_path, remember_answer == "y"


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
            "  1 · Stockfish difficulty\n"
            "  2 · Play as White or Black\n"
            "  3 · Time control\n"
            "  4 · Back to main menu"
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


def _history_table(records: list[dict[str, object]]) -> None:
    table = Table(title="Recent games · Local history", header_style="bold cyan")
    table.add_column("ID", justify="right", style="dim")
    table.add_column("Date")
    table.add_column("White")
    table.add_column("Black")
    table.add_column("Result", justify="center")
    table.add_column("Mode")
    table.add_column("Opening")
    for record in records:
        played_at = str(record.get("played_at", "")).replace("T", " ")[:16]
        table.add_row(
            str(record["id"]), played_at,
            str(record["white_player"]), str(record["black_player"]),
            str(record["result"]), str(record["game_type"]),
            str(record.get("opening") or "—"),
        )
    console.print(table)


def _replay_game(game: chess.pgn.Game) -> None:
    board = game.board()
    moves = list(game.mainline_moves())
    title = f"{game.headers.get('White', 'White')} vs {game.headers.get('Black', 'Black')}"
    if not moves:
        console.print("[yellow]This PGN contains no moves.[/yellow]")
        return
    for index, move in enumerate(moves):
        san = board.san(move)
        board.push(move)
        console.clear()
        console.print(Panel(
            board_table(board, chess.WHITE),
            title=f"Replay · {title} · {index + 1}/{len(moves)} · {san}",
            border_style="bright_green",
        ))
        console.print(move_history(board))
        if index + 1 < len(moves):
            if Prompt.ask("Enter for next move, or q to stop", default="").strip().lower() == "q":
                break


def history_menu() -> None:
    """Browse saved games and import/export standard PGN files."""
    while True:
        console.print(
            "\n[bold bright_green]GAME HISTORY[/bold bright_green]\n"
            "  1 · Browse and replay saved games\n"
            "  2 · Import PGN file\n"
            "  3 · Export one game or all games to PGN\n"
            "  4 · Back to main menu"
        )
        choice = Prompt.ask("Select option", choices=["1", "2", "3", "4"], default="4")
        try:
            if choice == "1":
                records = list_games()
                if not records:
                    console.print("[yellow]No saved games yet. Finish a game or import a PGN file first.[/yellow]")
                    continue
                _history_table(records)
                selected = Prompt.ask("Game ID to inspect (Enter to go back)", default="").strip()
                if not selected:
                    continue
                try:
                    game_id = int(selected)
                except ValueError:
                    console.print("[red]Game ID must be a number.[/red]")
                    continue
                game = load_game(game_id)
                if game is None:
                    console.print("[red]No game found with that ID.[/red]")
                    continue
                headers = game.headers
                console.print(Panel(
                    f"[bold]{headers.get('White', 'White')}[/bold] vs [bold]{headers.get('Black', 'Black')}[/bold]\n"
                    f"Result: {headers.get('Result', '*')}  ·  Date: {headers.get('Date', 'Unknown')}\n"
                    f"Opening: {headers.get('Opening', 'Unknown')}  ·  ECO: {headers.get('ECO', '—')}\n\n"
                    f"{move_history(game.end().board())}",
                    title=f"Game #{game_id}",
                    border_style="cyan",
                ))
                if Prompt.ask("Replay this game? [y/N]", default="n").strip().lower() in {"y", "yes"}:
                    _replay_game(game)
            elif choice == "2":
                source = Prompt.ask("Path to PGN file").strip()
                if not source:
                    continue
                imported = import_pgn_file(source)
                console.print(f"[green]Imported {imported} game(s) into local history.[/green]")
            elif choice == "3":
                records = list_games()
                if not records:
                    console.print("[yellow]There are no saved games to export.[/yellow]")
                    continue
                selected = Prompt.ask("Game ID or 'all'", default="all").strip().lower()
                destination = Prompt.ask("Output PGN path", default="terchess-games.pgn").strip()
                if not destination:
                    continue
                if selected == "all":
                    path = export_all_pgn(destination)
                else:
                    path = export_pgn(int(selected), destination)
                console.print(f"[green]PGN exported to {path}[/green]")
            else:
                return
        except (OSError, sqlite3.Error, ValueError, KeyError) as exc:
            console.print(f"[red]History operation failed: {exc}[/red]")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="terchess",
        description="Terchess (Terminal + Chess): offline terminal chess.",
    )
    parser.add_argument("--engine", help="Temporarily override the saved Stockfish executable path")
    parser.add_argument(
        "--choose-engine",
        action="store_true",
        help="Show the Stockfish selector even when a preferred engine is remembered",
    )
    parser.add_argument("--version", action="version", version=f"Terchess {__version__}")
    args = parser.parse_args()

    saved_config = load_config()
    settings = _settings_from_config(saved_config)
    engine_catalog = _available_engine_catalog(saved_config)
    saved_engine_path = saved_config.get("stockfish_path")
    persistent_engine_path = saved_engine_path if isinstance(saved_engine_path, str) else None
    remember_engine_choice = bool(saved_config.get("remember_engine_choice", True))
    deferred_version = saved_config.get("stockfish_deferred_version")
    preferred_engine_path = args.engine or persistent_engine_path
    explicit_engine_override = args.engine is not None
    engine: chess.engine.SimpleEngine | None = None

    console.print(Panel.fit(
        "[bold bright_green]TERCHESS[/bold bright_green] [white]· Terminal + Chess[/white]\n"
        f"[white]Version {__version__}[/white]\n"
        "[dim]Game History · Hotseat · Opening Recognition · Stockfish[/dim]",
        border_style="bright_green",
    ))

    try:
        if not explicit_engine_override and len(engine_catalog) > 1 and (
            not remember_engine_choice or args.choose_engine
        ):
            selected_path, remember = _choose_stockfish_engine(engine_catalog, persistent_engine_path)
            if selected_path:
                preferred_engine_path = selected_path
                remember_engine_choice = remember
                if remember:
                    persistent_engine_path = selected_path
                try:
                    save_config(_settings_config(
                        settings,
                        persistent_engine_path if remember else (
                            persistent_engine_path
                        ),
                        engine_catalog,
                        remember_engine_choice,
                        deferred_version if isinstance(deferred_version, str) else None,
                    ))
                except OSError as exc:
                    console.print(f"[yellow]Warning: could not save engine choice: {exc}[/yellow]")
        elif not preferred_engine_path and len(engine_catalog) == 1:
            preferred_engine_path = engine_catalog[0]["path"]

        while True:
            console.print()
            show_settings(settings)
            console.print(
                "[bold bright_green]MAIN MENU[/bold bright_green]\n"
                "  1 · Play vs Stockfish\n"
                f"  2 · Display mode: {'Board view' if settings.show_board else 'Blindfold / text-only'} (toggle)\n"
                "  3 · Settings\n"
                "  4 · About Terchess\n"
                "  5 · Hotseat (two players, one device)\n"
                "  6 · Game History (browse / PGN import / export)\n"
                "  7 · Quit"
            )
            choice = Prompt.ask("Select option", choices=["1", "2", "3", "4", "5", "6", "7"], default="1")
            if choice == "1":
                if engine is None:
                    engine_path = find_engine(preferred_engine_path) if preferred_engine_path else find_engine()
                    if engine_path is None and preferred_engine_path and not explicit_engine_override:
                        engine_path = find_engine()
                    if engine_path is None:
                        engine_path = _ask_engine_path()
                    if engine_path is None:
                        continue
                    try:
                        engine = chess.engine.SimpleEngine.popen_uci(engine_path, timeout=30.0)
                        console.print(f"[green]Connected to {engine.id.get('name', 'UCI engine')}[/green]")
                    except (OSError, chess.engine.EngineError, RuntimeError, ValueError) as exc:
                        console.print(f"[bold red]Could not start Stockfish: {exc}[/bold red]")
                        engine = None
                        preferred_engine_path = None
                        continue
                    if not explicit_engine_override and remember_engine_choice:
                        persistent_engine_path = engine_path
                        preferred_engine_path = engine_path
                        _save_preferences(
                            settings, persistent_engine_path, engine_catalog,
                            remember_engine_choice,
                            deferred_version if isinstance(deferred_version, str) else None,
                        )
                asyncio.run(play_game(
                    engine, settings.skill_level, settings.human_color,
                    settings.base_seconds, settings.increment_seconds, console,
                    show_board=settings.show_board,
                ))
            elif choice == "2":
                settings.show_board = not settings.show_board
                _save_preferences(
                    settings, persistent_engine_path, engine_catalog,
                    remember_engine_choice,
                    deferred_version if isinstance(deferred_version, str) else None,
                )
                mode_name = "Board view" if settings.show_board else "Blindfold / text-only"
                console.print(f"[green]Display mode set to: {mode_name}[/green]")
            elif choice == "3":
                settings_menu(settings, persistent_engine_path)
            elif choice == "4":
                console.print(Panel(
                    f"Terchess {__version__}\n\n"
                    "Terminal chess with local Stockfish play, two-player Hotseat, "
                    "offline opening recognition, and a searchable local PGN history.\n"
                    f"Game database: {get_database_path()}",
                    title="About", border_style="bright_blue",
                ))
            elif choice == "5":
                white_player = Prompt.ask("White player name", default="Player 1").strip() or "Player 1"
                black_player = Prompt.ask("Black player name", default="Player 2").strip() or "Player 2"
                time_key = _ask_time_control(settings.time_control_key)
                base_seconds, increment_seconds = TIME_CONTROLS[time_key]
                asyncio.run(play_hotseat_game(
                    white_player, black_player, base_seconds, increment_seconds, console,
                    show_board=settings.show_board,
                ))
            elif choice == "6":
                history_menu()
            else:
                console.print("[green]Thanks for playing Terchess. Goodbye![/green]")
                break
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted. Goodbye.[/yellow]")
    finally:
        if engine is not None:
            try:
                engine.quit()
            except (OSError, chess.engine.EngineError):
                pass


if __name__ == "__main__":
    main()
