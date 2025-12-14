"""
CLI for Readme Shogi.

Provides commands for local testing and GitHub Actions integration.
"""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from readme_shogi.constants import GAMES_DIR, PROJECT_ROOT, SETTINGS_FILE
from readme_shogi.game import ShogiGame
from readme_shogi.model import MoveRecord, Settings, Stats
from readme_shogi.renderer import generate_readme
from readme_shogi.security import parse_issue_title, validate_game_id, validate_move
from readme_shogi.stats import (
    get_recent_moves,
    load_stats,
    record_game_end,
    record_move,
    record_player_win,
    save_stats,
)

console = Console()


def _resolve_repo_info(
    owner: str | None, repo: str | None
) -> tuple[str | None, str | None]:
    """Resolve repo info preferring explicit args, then settings.toml."""
    settings = Settings.from_toml(SETTINGS_FILE)
    resolved_owner = owner or settings.repository.owner
    resolved_repo = repo or settings.repository.repo
    return resolved_owner, resolved_repo


def _render_readme_if_possible(
    game: ShogiGame,
    owner: str | None,
    repo: str | None,
    output_dir: str | Path | None,
) -> bool:
    """Render README when repo info is available, otherwise warn."""
    resolved_owner, resolved_repo = _resolve_repo_info(owner, repo)
    if resolved_owner and resolved_repo:
        settings = Settings.from_toml(SETTINGS_FILE)
        default_output_dir = PROJECT_ROOT / Path(settings.repository.readme_path)
        output_path = Path(output_dir) if output_dir else default_output_dir
        generate_readme(game, resolved_owner, resolved_repo, output_path)
        console.print(f"[green]✓[/green] README files rendered to: {output_path}")
        return True

    console.print(
        "[yellow]![/yellow] README not rendered: missing repository info. "
        "Provide --owner and --repo, or configure settings.toml."
    )
    return False


@click.group()
@click.version_option()
def cli() -> None:
    """Readme Shogi - Play Shogi in your GitHub Profile README."""
    pass


@cli.command()
@click.option("--owner", "-o", help="Repository owner (default: settings.toml)")
@click.option("--repo", "-r", help="Repository name (default: settings.toml)")
@click.option(
    "--output",
    "-f",
    type=click.Path(),
    help="Output directory path for README files",
)
def new(owner: str | None, repo: str | None, output: str | None) -> None:
    """Start a new game and render the initial board when possible."""
    game = ShogiGame.new_game()
    console.print(
        f"[green]✓[/green] New game created: [bold]{game.state.game_id}[/bold]"
    )
    console.print(f"  SFEN: {game.state.sfen}")
    console.print(f"  Turn: {game.current_turn}")

    # Render initial README so the board is visible immediately.
    _render_readme_if_possible(game, owner, repo, output)


@cli.command()
@click.argument("game_id", required=False)
def show(game_id: str | None) -> None:
    """Show the current game state."""
    if game_id:
        if not validate_game_id(game_id):
            console.print("[red]✗[/red] Invalid game ID format")
            sys.exit(1)
        game = ShogiGame.load_by_id(game_id)
    else:
        game = ShogiGame.get_current_game()

    if not game:
        console.print(
            "[yellow]![/yellow] No active game found. Use 'new' to start one."
        )
        return

    # Display game info
    table = Table(title=f"Game: {game.state.game_id}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Status", game.state.status)
    table.add_row("Turn", game.current_turn)
    table.add_row("Moves", str(game.move_count))
    table.add_row("SFEN", game.state.sfen)

    if game.state.winner:
        table.add_row("Winner", game.state.winner)

    console.print(table)

    # Display board (text representation)
    console.print("\n[bold]Board:[/bold]")
    _display_board(game)

    # Display legal moves
    if not game.is_game_over:
        legal_moves = game.get_legal_moves()
        console.print(f"\n[bold]Legal moves ({len(legal_moves)}):[/bold]")
        console.print(", ".join(sorted(legal_moves)[:20]))
        if len(legal_moves) > 20:
            console.print(f"... and {len(legal_moves) - 20} more")


def _display_board(game: ShogiGame) -> None:
    """Display board as text."""
    board_array = game.get_board_array()
    piece_chars = {
        1: "P",
        2: "L",
        3: "N",
        4: "S",
        5: "G",
        6: "B",
        7: "R",
        8: "K",
        9: "+P",
        10: "+L",
        11: "+N",
        12: "+S",
        13: "+B",
        14: "+R",
    }

    # Display white's hand
    white_hand = game.get_hand(1)
    if white_hand:
        hand_str = " ".join(f"{p}x{c}" for p, c in white_hand.items())
        console.print(f"White hand: {hand_str}")

    console.print("  9  8  7  6  5  4  3  2  1")
    console.print(" +--+--+--+--+--+--+--+--+--+")

    rank_labels = ["a", "b", "c", "d", "e", "f", "g", "h", "i"]

    for rank in range(9):
        row_str = " |"
        for file in range(9):
            cell = board_array[rank][8 - file]
            if cell is None:
                row_str += "  |"
            else:
                piece_type, color = cell
                piece_char = piece_chars.get(piece_type, "?")
                if color == 1:  # White pieces shown as lowercase
                    piece_char = piece_char.lower()
                row_str += f"{piece_char:>2}|"
        console.print(f"{row_str} {rank_labels[rank]}")
        console.print(" +--+--+--+--+--+--+--+--+--+")

    # Display black's hand
    black_hand = game.get_hand(0)
    if black_hand:
        hand_str = " ".join(f"{p}x{c}" for p, c in black_hand.items())
        console.print(f"Black hand: {hand_str}")


@cli.command()
@click.argument("move", required=False)
@click.option("--game-id", "-g", help="Game ID (uses current game if not specified)")
@click.option("--player", "-p", help="Player name/username")
@click.option("--issue-title", help="Issue title payload from GitHub Actions")
@click.option("--owner", help="Repository owner (default: settings.toml)")
@click.option("--repo", help="Repository name (default: settings.toml)")
@click.option(
    "--output",
    type=click.Path(),
    help="Output directory path for README files",
)
def move(
    move: str | None,
    game_id: str | None,
    player: str | None,
    issue_title: str | None,
    owner: str | None,
    repo: str | None,
    output: str | None,
) -> None:
    """Make a move locally or from GitHub Actions."""
    move_from_issue = move

    if issue_title:
        parsed = parse_issue_title(issue_title)
        if not parsed:
            console.print(f"[red]✗[/red] Invalid issue title format: {issue_title}")
            console.print("  Expected format: shogi|move|<game_id>|<move>")
            sys.exit(1)
        game_id = parsed.game_id
        move_from_issue = parsed.move

    if not move_from_issue:
        console.print(
            "[red]✗[/red] Move is required. Provide a move argument or --issue-title."
        )
        sys.exit(1)

    # Validate move format
    if not validate_move(move_from_issue):
        console.print(f"[red]✗[/red] Invalid move format: {move_from_issue}")
        console.print("  USI format examples: 7g7f, P*5e, 2b3c+")
        sys.exit(1)

    # Load game
    if game_id:
        if not validate_game_id(game_id):
            console.print("[red]✗[/red] Invalid game ID format")
            sys.exit(1)
        game = ShogiGame.load_by_id(game_id)
    else:
        game = ShogiGame.get_current_game()

    if not game:
        console.print(
            "[yellow]![/yellow] No active game found. Use 'new' to start one."
        )
        sys.exit(1)

    if game.is_game_over:
        console.print(
            f"[red]✗[/red] Game is already over (status: {game.state.status})"
        )
        sys.exit(1)

    # Check if move is legal
    if not game.is_legal_move(move_from_issue):
        console.print(f"[red]✗[/red] Illegal move: {move_from_issue}")
        legal_moves = game.get_legal_moves()
        console.print(f"  Legal moves: {', '.join(sorted(legal_moves)[:10])}...")
        sys.exit(1)

    # Make the move
    turn_before = game.current_turn
    if game.make_move(move_from_issue, player):
        console.print(
            f"[green]✓[/green] Move {move_from_issue} made by {player or 'unknown'}"
        )

        # Record in stats
        record_move(player, game.state.game_id, move_from_issue, turn_before)

        # Save game
        game.save()

        # Check game status
        if game.is_game_over:
            console.print("\n[bold yellow]Game Over![/bold yellow]")
            console.print(f"  Status: {game.state.status}")
            if game.state.winner:
                console.print(f"  Winner: {game.state.winner}")
                record_game_end(
                    game.state.game_id,
                    game.state.winner,
                    game.state.status,
                    game.move_count,
                )
                # Record win for player if applicable
                if player and turn_before == game.state.winner:
                    record_player_win(player)
        else:
            console.print(f"  Turn: {game.current_turn}")

        _render_readme_if_possible(game, owner, repo, output)
    else:
        console.print(f"[red]✗[/red] Failed to make move: {move_from_issue}")
        sys.exit(1)


@cli.command()
@click.option("--game-id", "-g", help="Game ID (uses current game if not specified)")
def legal(game_id: str | None) -> None:
    """List all legal moves for the current position."""
    if game_id:
        if not validate_game_id(game_id):
            console.print("[red]✗[/red] Invalid game ID format")
            sys.exit(1)
        game = ShogiGame.load_by_id(game_id)
    else:
        game = ShogiGame.get_current_game()

    if not game:
        console.print("[yellow]![/yellow] No active game found.")
        return

    if game.is_game_over:
        console.print("[yellow]![/yellow] Game is over.")
        return

    legal_moves = game.get_legal_moves()

    # Group by from square
    moves_by_from: dict[str, list[str]] = {}
    for m in legal_moves:
        key = f"Drop {m[0]}" if "*" in m else m[:2]

        if key not in moves_by_from:
            moves_by_from[key] = []
        moves_by_from[key].append(m)

    console.print(f"\n[bold]Legal moves ({len(legal_moves)}):[/bold]\n")

    for from_key, moves in sorted(moves_by_from.items()):
        console.print(f"  [cyan]{from_key}[/cyan]: {', '.join(sorted(moves))}")


@cli.command()
@click.option("--owner", "-o", help="Repository owner (default: settings.toml)")
@click.option("--repo", "-r", help="Repository name (default: settings.toml)")
@click.option(
    "--output",
    "-f",
    type=click.Path(),
    help="Output directory path for README files",
)
@click.option("--game-id", "-g", help="Game ID (uses current game if not specified)")
def render(
    owner: str | None, repo: str | None, output: str | None, game_id: str | None
) -> None:
    """Render the README with the current game state respecting settings.toml."""
    if game_id:
        if not validate_game_id(game_id):
            console.print("[red]✗[/red] Invalid game ID format")
            sys.exit(1)
        game = ShogiGame.load_by_id(game_id)
    else:
        game = ShogiGame.get_current_game()

    if not game:
        console.print("[yellow]![/yellow] No active game found. Creating new game...")
        game = ShogiGame.new_game()

    output_dir = Path(output) if output else None

    if not _render_readme_if_possible(game, owner, repo, output_dir):
        sys.exit(1)

    console.print(f"  Game ID: {game.state.game_id}")
    console.print(f"  Move count: {game.move_count}")


@cli.command()
def stats() -> None:
    """Show game statistics."""
    statistics: Stats = load_stats()

    panel = Panel(
        f"Total games: [bold]{statistics.total_games}[/bold]\n"
        f"Total moves: [bold]{statistics.total_moves}[/bold]\n"
        f"Black wins: [bold]{statistics.black_wins}[/bold]\n"
        f"White wins: [bold]{statistics.white_wins}[/bold]\n"
        f"Draws: [bold]{statistics.draws}[/bold]",
        title="📊 Statistics",
    )
    console.print(panel)

    # Recent moves (last 5 across all games)
    recent_moves: list[MoveRecord] = get_recent_moves(limit=5)
    if recent_moves:
        table = Table(title="📝 Recent Moves (Last 5)")
        table.add_column("#", style="dim")
        table.add_column("Game", style="cyan")
        table.add_column("Move", style="green")
        table.add_column("Player", style="yellow")
        table.add_column("Side", style="magenta")

        for i, move_record in enumerate(recent_moves, 1):
            game_id = move_record.game_id[:8]
            move = move_record.move or "?"
            player = move_record.player or "anonymous"
            turn = move_record.turn or "?"
            side = "Black" if turn == "black" else "White" if turn == "white" else "?"
            table.add_row(str(i), game_id, move, player, side)

        console.print(table)

    # Top 10 players (leaderboard)
    top_players = statistics.top_players
    if top_players:
        table = Table(title="🏆 Top 10 Players (Leaderboard)")
        table.add_column("Rank", style="dim")
        table.add_column("Player", style="cyan")
        table.add_column("Total Moves", style="green")
        table.add_column("Wins", style="yellow")

        sorted_players = sorted(
            top_players.items(),
            key=lambda x: x[1].moves,
            reverse=True,
        )

        for i, (player, data) in enumerate(sorted_players[:10], 1):
            rank = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else str(i)
            table.add_row(rank, player, str(data.moves), str(data.wins))

        console.print(table)


@cli.command()
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def reset(yes: bool) -> None:
    """
    Reset all game data.

    This will delete all games and reset statistics to zero.
    Use with caution!
    """
    if not yes and not click.confirm(
        "⚠️  This will delete ALL games and reset statistics. Continue?"
    ):
        console.print("[yellow]![/yellow] Reset cancelled.")
        return

    # Reset stats
    save_stats(Stats())
    console.print("[green]✓[/green] Statistics reset.")

    # Delete all game files
    if GAMES_DIR.exists():
        game_files = list(GAMES_DIR.glob("*.json"))
        for game_file in game_files:
            game_file.unlink()
        console.print(f"[green]✓[/green] Deleted {len(game_files)} game file(s).")
    else:
        console.print("[yellow]![/yellow] No games directory found.")

    console.print("[bold green]✓ Reset complete![/bold green]")


@cli.command()
def games() -> None:
    """List all games."""
    if not GAMES_DIR.exists():
        console.print("[yellow]![/yellow] No games directory found.")
        return

    game_files = list(GAMES_DIR.glob("*.json"))
    if not game_files:
        console.print("[yellow]![/yellow] No games found.")
        return

    table = Table(title="📂 Games")
    table.add_column("Game ID", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Moves", style="yellow")
    table.add_column("Winner", style="magenta")

    for game_file in sorted(game_files, key=lambda p: p.stat().st_mtime, reverse=True):
        game = ShogiGame.load(game_file)
        table.add_row(
            game.state.game_id,
            game.state.status,
            str(game.move_count),
            game.state.winner or "-",
        )

    console.print(table)


@cli.command(hidden=True)
@click.option("--issue-title", required=True, help="Issue title from GitHub Actions")
@click.option("--username", help="GitHub username who created the issue")
@click.option("--owner", required=True, help="Repository owner")
@click.option("--repo", required=True, help="Repository name")
@click.option(
    "--output",
    type=click.Path(),
    help="Output directory path for README files",
)
def action(
    issue_title: str,
    username: str | None,
    owner: str,
    repo: str,
    output: str | None,
) -> None:
    """Deprecated alias for GitHub Actions; forwards to 'move --issue-title'."""
    console.print(
        "[yellow]![/yellow] 'action' command is deprecated. Forwarding to 'move --issue-title'."
    )
    move(None, None, username, issue_title, owner, repo, output)


@cli.command("new-game-action", hidden=True)
@click.option("--owner", required=True, help="Repository owner")
@click.option("--repo", required=True, help="Repository name")
@click.option(
    "--output",
    type=click.Path(),
    help="Output directory path for README files",
)
def new_game_action(owner: str, repo: str, output: str | None) -> None:
    """Deprecated alias for creating a game; forwards to 'new'."""
    console.print(
        "[yellow]![/yellow] 'new-game-action' command is deprecated. Forwarding to 'new'."
    )
    new(owner, repo, output)


if __name__ == "__main__":
    cli()
