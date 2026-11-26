"""Colorful terminal board, clock display, and numbered move history."""

from __future__ import annotations

import os
import shutil

import chess
from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from terchess.clock import ChessClock, color_name, format_clock
from terchess.config import load_config

LIGHT_SQUARE = "#F0D9B5"
DARK_SQUARE = "#B58863"
LAST_MOVE_SQUARE = "#E6E36A"


def is_termux() -> bool:
    """Return True when running inside the native Android Termux environment."""
    prefix = os.environ.get("PREFIX", "")
    return bool(os.environ.get("TERMUX_VERSION")) or prefix.endswith("/com.termux/files/usr")


def _compact_history(board: chess.Board, max_plies: int = 6) -> str:
    """Return only the most recent moves for small terminal screens."""
    if not board.move_stack:
        return "No moves yet"
    replay = chess.Board()
    tokens: list[str] = []
    start = max(0, len(board.move_stack) - max_plies)
    for move in board.move_stack:
        san = replay.san(move)
        if replay.turn == chess.WHITE:
            tokens.append(f"{replay.fullmove_number}. {san}")
        else:
            tokens.append(san)
        replay.push(move)
    return " ".join(tokens[start:])


def _render_termux_position(
    console: Console,
    board: chess.Board,
    human_color: chess.Color,
    skill_level: int | None,
    clock: ChessClock,
    time_control_name: str,
    notice: str | None,
    opening_name: str | None,
    game_label: str | None,
) -> None:
    """Render a short, borderless screen that fits a portrait phone terminal."""
    side_name = color_name(human_color)
    mode = game_label or (f"Skill {skill_level}/20" if skill_level is not None else "Local game")
    console.print(Text(f"TERCHESS · {side_name} · {mode} · {time_control_name}", style="bold bright_white"))
    console.print(board_table(board, human_color))
    clock_line = Text("Clock  ")
    for color in (chess.WHITE, chess.BLACK):
        active = clock.running_color == color
        style = "bold bright_green" if active else "bold bright_white"
        prefix = "▶ " if active else ""
        clock_line.append(f"{prefix}{color_name(color)} {format_clock(clock.remaining(color))}   ", style=style)
    console.print(clock_line)
    console.print(Text(f"Moves: {_compact_history(board)}", style="bright_cyan"))
    if opening_name:
        console.print(Text(f"Opening: {opening_name}", style="cyan"))
    if notice:
        mobile_notice = (
            f"Recent moves: {_compact_history(board, max_plies=12)}"
            if notice == move_history(board) else notice
        )
        console.print(f"Status: {mobile_notice}")
    console.print(Text("SAN/UCI move · help · moves · resign · menu", style="dim"))



def _board_cell_dimensions(
    terminal_width: int,
    terminal_height: int,
    wide_layout: bool | None = None,
    board_scale: str = "compact",
) -> tuple[int, int]:
    """Return board cell dimensions for the selected size and live terminal area.

    Compact cells keep piece glyphs visually prominent. Larger presets add
    square padding/height; the terminal itself controls the actual font size.
    """
    if wide_layout is None:
        wide_layout = terminal_width >= 100

    available_width = max(24, terminal_width - (54 if wide_layout else 12))
    available_rank_height = max(1, (terminal_height - (12 if wide_layout else 18)) // 8)
    if board_scale == "auto":
        cell_height = min(3, max(1, (terminal_height - 18) // 8))
        cell_width = min(7, max(3, available_width // 16), cell_height * 3)
        return cell_width, cell_height

    presets = {
        "compact": (3, 1),
        "normal": (4, 2),
        "large": (6, 3),
    }
    target_width, target_height = presets.get(board_scale, presets["compact"])
    cell_width = min(target_width, max(3, available_width // 8))
    cell_height = min(target_height, available_rank_height)
    return cell_width, cell_height


def _live_terminal_size(console: Console) -> tuple[int, int]:
    """Read the current terminal dimensions instead of relying on startup size."""
    try:
        size = os.get_terminal_size(console.file.fileno())
        return max(40, size.columns), max(12, size.lines)
    except (AttributeError, OSError, ValueError):
        size = shutil.get_terminal_size(fallback=(console.width, console.height))
        return max(40, size.columns), max(12, size.lines)


def board_table(
    board: chess.Board,
    human_color: chess.Color,
    cell_width: int = 3,
    cell_height: int = 1,
) -> Table:
    """Build a responsive colored board oriented from the human player's side."""
    cell_width = max(3, int(cell_width))
    cell_height = max(1, int(cell_height))
    middle_row = cell_height // 2
    table = Table.grid(padding=(0, 0), collapse_padding=True)
    table.add_column(justify="right", width=2)
    for _ in range(8):
        table.add_column(width=cell_width, justify="center")

    files = list(range(8)) if human_color == chess.WHITE else list(range(7, -1, -1))
    ranks = list(range(7, -1, -1)) if human_color == chess.WHITE else list(range(8))
    last_squares: set[chess.Square] = set()
    if board.move_stack:
        last_move = board.peek()
        last_squares = {last_move.from_square, last_move.to_square}

    for rank in ranks:
        for row_index in range(cell_height):
            cells: list[Text] = [
                Text(str(rank + 1) if row_index == middle_row else "", style="bold bright_cyan")
            ]
            for file_index in files:
                square = chess.square(file_index, rank)
                piece = board.piece_at(square)
                is_light = (file_index + rank) % 2 == 1
                background = LAST_MOVE_SQUARE if square in last_squares else (LIGHT_SQUARE if is_light else DARK_SQUARE)

                glyph = piece.unicode_symbol() if piece else "·"
                if row_index == middle_row:
                    left = (cell_width - 1) // 2
                    right = cell_width - left - 1
                    cell_text = (" " * left) + glyph + (" " * right)
                else:
                    cell_text = " " * cell_width

                if piece and row_index == middle_row:
                    foreground = "#FFFFFF" if piece.color == chess.WHITE else "#171717"
                    style = f"bold {foreground} on {background}"
                else:
                    style = f"on {background}"
                cells.append(Text(cell_text, style=style))
            table.add_row(*cells)

    footer = [Text("  ", style="bright_cyan")]
    footer.extend(
        Text(chess.FILE_NAMES[file_index].center(cell_width), style="bold bright_cyan")
        for file_index in files
    )
    table.add_row(*footer)
    return table


def move_history(board: chess.Board) -> str:
    """Format complete move history in numbered SAN notation."""
    replay = chess.Board()
    formatted: list[str] = []
    for move in board.move_stack:
        san = replay.san(move)
        move_number = replay.fullmove_number
        if replay.turn == chess.WHITE:
            formatted.append(f"{move_number}. {san}")
        elif formatted:
            formatted[-1] += f" {san}"
        else:
            formatted.append(f"{move_number}... {san}")
        replay.push(move)
    return "  ".join(formatted) if formatted else "No moves yet"


def move_history_table(board: chess.Board, max_rows: int = 10) -> Table:
    """Build a compact table showing numbered white/black moves."""
    table = Table(show_header=True, header_style="bold bright_cyan", box=None, padding=(0, 1), expand=True)
    table.add_column("#", justify="right", width=3, style="dim")
    table.add_column("White", ratio=1)
    table.add_column("Black", ratio=1)
    replay = chess.Board()
    rows: list[tuple[str, str, str]] = []
    moves = board.move_stack
    for index in range(0, len(moves), 2):
        move_number = replay.fullmove_number
        white_san = replay.san(moves[index])
        replay.push(moves[index])
        black_san = ""
        if index + 1 < len(moves):
            black_san = replay.san(moves[index + 1])
            replay.push(moves[index + 1])
        rows.append((str(move_number), white_san, black_san))
    rows = rows[-max_rows:]
    if not rows:
        table.add_row("—", "—", "—")
    else:
        for number, white_san, black_san in rows:
            table.add_row(number, white_san, black_san)
    return table


def render_position(
    console: Console,
    board: chess.Board,
    human_color: chess.Color,
    skill_level: int | None,
    clock: ChessClock,
    time_control_name: str,
    notice: str | None = None,
    opening_name: str | None = None,
    game_label: str | None = None,
) -> None:
    """Clear and render the board plus a live-clock snapshot and move history."""
    if is_termux():
        console.clear()
        _render_termux_position(
            console, board, human_color, skill_level, clock, time_control_name,
            notice, opening_name, game_label,
        )
        return

    terminal_width, terminal_height = _live_terminal_size(console)
    # Rich's Console captures dimensions when it is created. Recreate the
    # renderer for each board refresh so Windows Terminal resizes are honored.
    console = Console(
        file=console.file,
        width=terminal_width,
        height=terminal_height,
        force_terminal=console.is_terminal,
        color_system=console.color_system,
    )
    console.clear()
    side_name = color_name(human_color)
    turn_name = f"{color_name(board.turn)} to move"
    header = Text(
        f"TERCHESS  |  {side_name}  |  {f'Skill {skill_level}/20' if skill_level is not None else (game_label or 'Local game')}  |  {time_control_name}",
        style="bold bright_white",
    )
    wide_layout = terminal_width >= 100
    board_scale = str(load_config().get("board_scale", "compact"))
    cell_width, cell_height = _board_cell_dimensions(
        terminal_width, terminal_height, wide_layout=wide_layout,
        board_scale=board_scale,
    )
    board_panel = Panel(
        Align(board_table(board, human_color, cell_width, cell_height), align="center"),
        title=header,
        subtitle=(f"{opening_name} · Last move highlighted" if opening_name else "Last move highlighted"),
        border_style="bright_green",
        padding=(0, 1),
        expand=True,
    )
    clocks = Table.grid(padding=(0, 1))
    clocks.add_column()
    clocks.add_column(justify="right")
    for color in (chess.WHITE, chess.BLACK):
        active = clock.running_color == color
        label_style = "bold bright_green" if active else "bold"
        time_style = "bold bright_green" if active else "bold bright_white"
        prefix = "▶ " if active else "  "
        clocks.add_row(Text(prefix + color_name(color), style=label_style), Text(format_clock(clock.remaining(color)), style=time_style))
    clock_panel = Panel(clocks, title="Clock", border_style="yellow", expand=True)
    history_panel = Panel(move_history_table(board), title="Moves · White / Black", border_style="bright_blue")
    info_text = (
        f"[bold yellow]{turn_name}[/bold yellow]\n\n"
        "[bold]Commands[/bold]\n"
        "[cyan]help[/cyan]   show instructions\n"
        "[cyan]moves[/cyan]  show move list\n"
        "[cyan]resign[/cyan] resign game\n"
        "[cyan]menu[/cyan]  return to main menu"
    )
    if game_label:
        info_text = f"[bold]{game_label}[/bold]\n" + info_text
    if opening_name:
        info_text = f"[bold cyan]Opening: {opening_name}[/bold cyan]\n" + info_text
    if notice:
        info_text = f"[bold]Status[/bold]\n{notice}\n\n" + info_text
    info = Panel(info_text, title="Game info", border_style="magenta")
    if wide_layout:
        layout = Table.grid(padding=(1, 2), expand=True)
        layout.add_column(ratio=3)
        layout.add_column(ratio=2, width=36)
        layout.add_row(board_panel, Group(clock_panel, history_panel, info))
        console.print(layout)
    else:
        console.print(board_panel)
        console.print(clock_panel)
        console.print(history_panel)
        console.print(info)


def render_text_position(
    console: Console,
    board: chess.Board,
    human_color: chess.Color,
    skill_level: int | None,
    clock: ChessClock,
    time_control_name: str,
    notice: str | None = None,
    opening_name: str | None = None,
    game_label: str | None = None,
) -> None:
    """Render a blindfold/text-only game screen without a chessboard diagram."""
    console.clear()
    if is_termux():
        mode = game_label or f"You: {color_name(human_color)} · Stockfish: {color_name(not human_color)}"
        console.print(Text(f"TERCHESS · BLINDFOLD · {mode} · {time_control_name}", style="bold bright_green"))
        clock_line = Text("Clock  ")
        for color in (chess.WHITE, chess.BLACK):
            active = clock.running_color == color
            clock_line.append(
                f"{'▶ ' if active else ''}{color_name(color)} {format_clock(clock.remaining(color))}   ",
                style="bold bright_green" if active else "bold bright_white",
            )
        console.print(clock_line)
        console.print(Text(f"Moves: {_compact_history(board, max_plies=8)}", style="bright_cyan"))
        console.print(Text(f"Status: {color_name(board.turn)} to move", style="yellow"))
        if opening_name:
            console.print(Text(f"Opening: {opening_name}", style="cyan"))
        if notice:
            mobile_notice = (
                f"Recent moves: {_compact_history(board, max_plies=12)}"
                if notice == move_history(board) else notice
            )
            console.print(f"Latest: {mobile_notice}")
        console.print(Text("SAN/UCI move · help · moves · resign · menu", style="dim"))
        return
    side_name = color_name(human_color)
    engine_color = color_name(not human_color)
    turn_name = f"{color_name(board.turn)} to move"
    if game_label:
        header = (
            f"[bold bright_green]TERCHESS · BLINDFOLD MODE[/bold bright_green]\n"
            f"[bold]{game_label}[/bold]\n"
            f"Time: [bold]{time_control_name}[/bold]"
        )
    else:
        header = (
            f"[bold bright_green]TERCHESS · BLINDFOLD MODE[/bold bright_green]\n"
            f"You: [bold]{side_name}[/bold]  ·  Stockfish: [bold]{engine_color}[/bold]\n"
            f"Skill Level: [bold]{skill_level}/20[/bold]  ·  Time: [bold]{time_control_name}[/bold]"
        )
    console.print(Panel(header, title="Text-only game", border_style="bright_green"))
    clocks = Table.grid(padding=(0, 2))
    clocks.add_column()
    clocks.add_column(justify="right")
    for color in (chess.WHITE, chess.BLACK):
        active = clock.running_color == color
        name_style = "bold bright_green" if active else "bold"
        time_style = "bold bright_green" if active else "bold bright_white"
        prefix = "▶ " if active else "  "
        clocks.add_row(Text(prefix + color_name(color), style=name_style), Text(format_clock(clock.remaining(color)), style=time_style))
    console.print(Panel(clocks, title="Clock", border_style="yellow"))
    console.print(Panel(move_history_table(board, max_rows=20), title="Move history", border_style="bright_blue"))
    info = (
        f"[bold yellow]Status:[/bold yellow] {turn_name}\n"
        "[bold]Moves:[/bold] SAN (e4, Nf3, O-O) or coordinates (e2e4)\n"
        "[bold]Commands:[/bold] help · moves · resign · menu"
    )
    if opening_name:
        info += f"\n[bold cyan]Opening:[/bold cyan] {opening_name}"
    if notice:
        info += f"\n\n[bold]Latest:[/bold] {notice}"
    console.print(Panel(info, title="Blindfold play", border_style="magenta"))
