"""Colorful terminal board, clock display, and numbered move history."""

from __future__ import annotations

import chess
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from terchess.clock import ChessClock, color_name, format_clock

LIGHT_SQUARE = "#F0D9B5"
DARK_SQUARE = "#B58863"
LAST_MOVE_SQUARE = "#E6E36A"


def board_table(board: chess.Board, human_color: chess.Color) -> Table:
    """Build a colored Unicode board oriented from the human player's side."""
    table = Table.grid(padding=(0, 0), collapse_padding=True)
    table.add_column(justify="right", width=2)
    for _ in range(8):
        table.add_column(width=3, justify="center")
    files = list(range(8)) if human_color == chess.WHITE else list(range(7, -1, -1))
    ranks = list(range(7, -1, -1)) if human_color == chess.WHITE else list(range(8))
    last_squares: set[chess.Square] = set()
    if board.move_stack:
        last_move = board.peek()
        last_squares = {last_move.from_square, last_move.to_square}
    for rank in ranks:
        cells: list[Text] = [Text(str(rank + 1), style="bold bright_cyan")]
        for file_index in files:
            square = chess.square(file_index, rank)
            piece = board.piece_at(square)
            is_light = (file_index + rank) % 2 == 1
            background = LAST_MOVE_SQUARE if square in last_squares else (LIGHT_SQUARE if is_light else DARK_SQUARE)
            if piece:
                foreground = "#FFFFFF" if piece.color == chess.WHITE else "#171717"
                glyph = piece.unicode_symbol()
                cell = Text(f" {glyph} ", style=f"bold {foreground} on {background}")
            else:
                cell = Text(" · ", style=f"on {background}")
            cells.append(cell)
        table.add_row(*cells)
    footer = [Text("  ", style="bright_cyan")]
    footer.extend(Text(f" {chess.FILE_NAMES[file_index]} ", style="bold bright_cyan") for file_index in files)
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
    skill_level: int,
    clock: ChessClock,
    time_control_name: str,
    notice: str | None = None,
) -> None:
    """Clear and render the board plus a live-clock snapshot and move history."""
    console.clear()
    side_name = color_name(human_color)
    turn_name = f"{color_name(board.turn)} to move"
    header = Text(
        f"TERCHESS  |  {side_name}  |  Skill {skill_level}/20  |  {time_control_name}",
        style="bold bright_white",
    )
    board_panel = Panel(
        board_table(board, human_color), title=header, subtitle="Last move highlighted",
        border_style="bright_green", padding=(1, 1), expand=False,
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
    if notice:
        info_text = f"[bold]Status[/bold]\n{notice}\n\n" + info_text
    info = Panel(info_text, title="Game info", border_style="magenta")
    if console.width >= 100:
        layout = Table.grid(padding=(1, 2))
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
    skill_level: int,
    clock: ChessClock,
    time_control_name: str,
    notice: str | None = None,
) -> None:
    """Render a blindfold/text-only game screen without a chessboard diagram."""
    console.clear()
    side_name = color_name(human_color)
    engine_color = color_name(not human_color)
    turn_name = f"{color_name(board.turn)} to move"
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
    if notice:
        info += f"\n\n[bold]Latest:[/bold] {notice}"
    console.print(Panel(info, title="Blindfold play", border_style="magenta"))
