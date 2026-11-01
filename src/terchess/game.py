"""Human-versus-Stockfish game loop with real-time clocks."""

from __future__ import annotations

import asyncio
import sqlite3

import chess
import chess.engine
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel

from terchess.board_view import move_history, render_position, render_text_position
from terchess.clock import ChessClock, ClockExpired, color_name, format_clock
from terchess.engine import configure_skill_level
from terchess.history import save_game
from terchess.openings import format_opening, identify_opening

ENGINE_MOVE_SECONDS = 1.0
PROMPT_STYLE = Style.from_dict({
    "prompt": "bold #80ffad",
    "bottom-toolbar": "bg:#17232d #f4f4f4",
    "clock-active": "bg:#1d4938 #9bffc7 bold",
    "clock-white": "bg:#303944 #f5dfb2 bold",
    "clock-black": "bg:#303944 #f3f3f3 bold",
    "toolbar-label": "bg:#17232d #a8b6c6",
})


def _read_human_move(raw: str, board: chess.Board) -> chess.Move | str:
    """Parse SAN/UCI input and pass through supported game commands."""
    raw = raw.strip()
    command = raw.lower()
    if command in {"help", "quit", "menu", "resign", "moves"}:
        return command
    if not raw:
        return "invalid"
    san_candidates = [raw]
    castle = raw.replace("0", "O").replace("o", "O")
    if castle in {"O-O", "O-O-O"} and castle not in san_candidates:
        san_candidates.append(castle)
    if raw[0].lower() in "nbrqk":
        normalized_san = raw[0].upper() + raw[1:]
        if normalized_san not in san_candidates:
            san_candidates.append(normalized_san)
    for candidate in san_candidates:
        try:
            return board.parse_san(candidate)
        except ValueError:
            continue
    try:
        move = chess.Move.from_uci(raw.lower())
        if move in board.legal_moves:
            return move
    except ValueError:
        pass
    return "invalid"


def _clock_toolbar(clock: ChessClock) -> FormattedText:
    """Return a prompt_toolkit toolbar whose clocks refresh while typing."""
    active = clock.running_color
    parts: list[tuple[str, str]] = [("class:toolbar-label", "  TERCHESS CLOCK  ")]
    for color, cls in ((chess.WHITE, "clock-white"), (chess.BLACK, "clock-black")):
        style = "class:clock-active" if active == color else f"class:{cls}"
        parts.append((style, f"  {color_name(color).upper()}  {format_clock(clock.remaining(color))}  "))
    parts.append(("class:toolbar-label", "  Counts down while you think  "))
    return FormattedText(parts)


async def _clocked_prompt(
    session: PromptSession,
    clock: ChessClock,
    color: chess.Color,
    prompt_label: str = "Your move > ",
) -> str:
    """Read a move while repainting the clock and abort when the flag falls."""
    prompt_task = asyncio.create_task(session.prompt_async(
        [("class:prompt", prompt_label)],
        bottom_toolbar=lambda: _clock_toolbar(clock),
        refresh_interval=0.25,
    ))
    try:
        while not prompt_task.done():
            if clock.is_flagged(color):
                prompt_task.cancel()
                try:
                    await prompt_task
                except (asyncio.CancelledError, EOFError, KeyboardInterrupt):
                    pass
                raise ClockExpired(color)
            await asyncio.sleep(0.05)
        return await prompt_task
    except BaseException:
        if not prompt_task.done():
            prompt_task.cancel()
            try:
                await prompt_task
            except BaseException:
                pass
        raise


def _format_clock_label(base_seconds: int, increment_seconds: int) -> str:
    return f"{base_seconds // 60}+{increment_seconds}"


async def play_game(
    engine: chess.engine.SimpleEngine,
    skill_level: int,
    human_color: chess.Color,
    base_seconds: int,
    increment_seconds: int,
    console: Console | None = None,
    show_board: bool = True,
) -> str:
    """Run a timed game. Returns to the main menu when the game closes."""
    console = console or Console()
    configure_skill_level(engine, skill_level)
    board = chess.Board()
    clock = ChessClock(base_seconds, increment_seconds)
    time_control_name = _format_clock_label(base_seconds, increment_seconds)
    session: PromptSession[str] = PromptSession(style=PROMPT_STYLE, refresh_interval=0.25)
    console.print(Panel(
        ("Enter SAN moves like [bold]e4[/bold], [bold]Nf3[/bold], [bold]O-O[/bold], or coordinates like [bold]e2e4[/bold].\n"
         "Your clock runs while you think. Both clocks update in the toolbar.\n"
         "Commands: [bold]help[/bold], [bold]moves[/bold], [bold]resign[/bold], [bold]menu[/bold]."),
        title=f"Terchess · {'Board view' if show_board else 'Blindfold / text-only'} · Skill {skill_level}/20 · Time {time_control_name}",
        border_style="bright_green",
    ))
    console.input("Press Enter to start the clock...")
    resigned = False
    timed_out: chess.Color | None = None
    quit_to_menu = False
    notice: str | None = None
    opening_name: str | None = None
    while not board.is_game_over(claim_draw=True):
        side = board.turn
        clock.start(side)
        if show_board:
            render_position(console, board, human_color, skill_level, clock, time_control_name, notice, opening_name=opening_name)
        else:
            render_text_position(console, board, human_color, skill_level, clock, time_control_name, notice, opening_name=opening_name)
        if side == human_color:
            try:
                raw = await _clocked_prompt(session, clock, side)
            except ClockExpired:
                timed_out = side
                break
            except EOFError:
                quit_to_menu = True
                break
            entry = _read_human_move(raw, board)
            if entry in {"quit", "menu"}:
                quit_to_menu = True
                break
            if entry == "resign":
                resigned = True
                break
            if entry == "help":
                notice = "Enter SAN (e4, Nf3, Qxd5, O-O) or UCI coordinates (e2e4). Use moves, resign, or menu."
                continue
            if entry == "moves":
                notice = move_history(board)
                continue
            if entry == "invalid":
                turn = color_name(board.turn)
                notice = f"[red]Illegal move: it is {turn}'s turn. Try SAN (e4/Nf3) or UCI (e2e4). Clock is running.[/red]"
                continue
            if isinstance(entry, chess.Move):
                san = board.san(entry)
                if not clock.finish_move(side):
                    timed_out = side
                    break
                board.push(entry)
                opening_name = format_opening(identify_opening(board))
                notice = f"[green]You played {san}[/green]"
        else:
            console.print("[yellow]Stockfish is thinking... (clock is running)[/yellow]")
            remaining = clock.remaining(side)
            engine_budget = max(0.01, min(ENGINE_MOVE_SECONDS, remaining * 0.9))
            result = engine.play(board, chess.engine.Limit(time=engine_budget))
            if result.move is None:
                break
            san = board.san(result.move)
            if not clock.finish_move(side):
                timed_out = side
                break
            board.push(result.move)
            opening_name = format_opening(identify_opening(board))
            notice = f"[cyan]Stockfish played {san}[/cyan]"
    clock.stop()
    if quit_to_menu:
        return "menu"
    if show_board:
        render_position(console, board, human_color, skill_level, clock, time_control_name, notice, opening_name=opening_name)
    else:
        render_text_position(console, board, human_color, skill_level, clock, time_control_name, notice, opening_name=opening_name)
    if timed_out is not None:
        winner = chess.BLACK if timed_out == chess.WHITE else chess.WHITE
        result_text = f"{color_name(timed_out)} ran out of time.\n{color_name(winner)} wins on time."
    elif resigned:
        winner = chess.BLACK if human_color == chess.WHITE else chess.WHITE
        result_text = f"You resigned. {color_name(winner)} wins."
    else:
        outcome = board.outcome(claim_draw=True)
        if outcome is None:
            result_text = "Game ended without a recorded result."
        else:
            result_text = f"Result: {outcome.result()}\nReason: {outcome.termination.name.replace('_', ' ').title()}"
    if timed_out is not None:
        result = "0-1" if timed_out == chess.WHITE else "1-0"
        termination = "time forfeit"
    elif resigned:
        result = "0-1" if human_color == chess.WHITE else "1-0"
        termination = "resignation"
    else:
        outcome = board.outcome(claim_draw=True)
        result = outcome.result() if outcome is not None else "*"
        termination = outcome.termination.name.replace("_", " ").lower() if outcome is not None else "unknown"
    try:
        opening = identify_opening(board)
        save_game(
            board,
            white_player="You" if human_color == chess.WHITE else "Stockfish",
            black_player="Stockfish" if human_color == chess.WHITE else "You",
            game_type="stockfish",
            result=result,
            termination=termination,
            time_control=time_control_name,
            opening_name=opening.name if opening else None,
            opening_eco=opening.eco if opening else None,
        )
        console.print("[dim]Game saved to local history.[/dim]")
    except (OSError, sqlite3.Error, ValueError) as exc:
        console.print(f"[yellow]Warning: could not save game history: {exc}[/yellow]")
    console.print(Panel(result_text, title="Game Over", border_style="magenta"))
    console.input("Press Enter to return to the main menu...")
    return "menu"


async def play_hotseat_game(
    white_player: str,
    black_player: str,
    base_seconds: int,
    increment_seconds: int,
    console: Console | None = None,
    show_board: bool = True,
) -> str:
    """Run a local two-player game with one terminal and a shared chess clock."""
    console = console or Console()
    white_player = white_player.strip() or "Player 1"
    black_player = black_player.strip() or "Player 2"
    game_label = f"Hotseat · {white_player} vs {black_player}"
    board = chess.Board()
    clock = ChessClock(base_seconds, increment_seconds)
    time_control_name = _format_clock_label(base_seconds, increment_seconds)
    session: PromptSession[str] = PromptSession(style=PROMPT_STYLE, refresh_interval=0.25)
    console.print(Panel(
        (
            f"[bold]{white_player}[/bold] plays White; [bold]{black_player}[/bold] plays Black.\n"
            "Enter SAN moves (e4, Nf3, O-O) or coordinates (e2e4).\n"
            "Commands: help, moves, resign, menu."
        ),
        title=f"Terchess · Hotseat · {time_control_name}",
        border_style="bright_green",
    ))
    console.input("Press Enter to start the clock...")
    resigned_color: chess.Color | None = None
    timed_out: chess.Color | None = None
    quit_to_menu = False
    notice: str | None = None
    opening_name: str | None = None

    while not board.is_game_over(claim_draw=True):
        side = board.turn
        player_name = white_player if side == chess.WHITE else black_player
        clock.start(side)
        if show_board:
            render_position(
                console, board, chess.WHITE, None, clock, time_control_name, notice,
                opening_name=opening_name, game_label=game_label,
            )
        else:
            render_text_position(
                console, board, chess.WHITE, None, clock, time_control_name, notice,
                opening_name=opening_name, game_label=game_label,
            )

        try:
            raw = await _clocked_prompt(
                session, clock, side, prompt_label=f"{player_name} ({color_name(side)}) > "
            )
        except ClockExpired:
            timed_out = side
            break
        except EOFError:
            quit_to_menu = True
            break

        entry = _read_human_move(raw, board)
        if entry in {"quit", "menu"}:
            quit_to_menu = True
            break
        if entry == "resign":
            resigned_color = side
            break
        if entry == "help":
            notice = "Enter SAN or UCI coordinates. Use moves, resign, or menu."
            continue
        if entry == "moves":
            notice = move_history(board)
            continue
        if entry == "invalid":
            notice = f"[red]Illegal move: it is {color_name(side)}'s turn. Try SAN (e4/Nf3) or UCI (e2e4).[/red]"
            continue
        if isinstance(entry, chess.Move):
            san = board.san(entry)
            if not clock.finish_move(side):
                timed_out = side
                break
            board.push(entry)
            opening_name = format_opening(identify_opening(board))
            notice = f"[green]{player_name} played {san}[/green]"

    clock.stop()
    if quit_to_menu:
        return "menu"

    if show_board:
        render_position(
            console, board, chess.WHITE, None, clock, time_control_name, notice,
            opening_name=opening_name, game_label=game_label,
        )
    else:
        render_text_position(
            console, board, chess.WHITE, None, clock, time_control_name, notice,
            opening_name=opening_name, game_label=game_label,
        )

    if timed_out is not None:
        winner_color = not timed_out
        winner = white_player if winner_color == chess.WHITE else black_player
        result = "1-0" if winner_color == chess.WHITE else "0-1"
        termination = "time forfeit"
        result_text = f"{color_name(timed_out)} ran out of time.\n{winner} wins on time."
    elif resigned_color is not None:
        winner_color = not resigned_color
        winner = white_player if winner_color == chess.WHITE else black_player
        result = "1-0" if winner_color == chess.WHITE else "0-1"
        termination = "resignation"
        result_text = f"{color_name(resigned_color)} resigned.\n{winner} wins."
    else:
        outcome = board.outcome(claim_draw=True)
        if outcome is None:
            result = "*"
            termination = "unknown"
            result_text = "Game ended without a recorded result."
        else:
            result = outcome.result()
            termination = outcome.termination.name.replace("_", " ").lower()
            result_text = f"Result: {result}\nReason: {outcome.termination.name.replace('_', ' ').title()}"

    try:
        opening = identify_opening(board)
        save_game(
            board,
            white_player=white_player,
            black_player=black_player,
            game_type="hotseat",
            result=result,
            termination=termination,
            time_control=time_control_name,
            opening_name=opening.name if opening else None,
            opening_eco=opening.eco if opening else None,
        )
        console.print("[dim]Game saved to local history.[/dim]")
    except (OSError, sqlite3.Error, ValueError) as exc:
        console.print(f"[yellow]Warning: could not save game history: {exc}[/yellow]")

    console.print(Panel(result_text, title="Game Over", border_style="magenta"))
    console.input("Press Enter to return to the main menu...")
    return "menu"
