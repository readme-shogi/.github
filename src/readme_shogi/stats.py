"""
Statistics tracking for Shogi games.
"""

import json

from readme_shogi.constants import STATS_FILE
from readme_shogi.model import MoveRecord, PlayerStats, RecentGame, Stats


def load_stats() -> Stats:
    """Load statistics from file."""
    if STATS_FILE.exists():
        with STATS_FILE.open(encoding="utf-8") as f:
            return Stats.model_validate(json.load(f))

    return Stats()


def save_stats(stats: Stats) -> None:
    """Save statistics to file."""
    STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with STATS_FILE.open("w", encoding="utf-8") as f:
        json.dump(stats.model_dump(mode="json"), f, indent=2)


def record_move(
    player: str | None,
    game_id: str,
    move: str | None = None,
    turn: str | None = None,
) -> None:
    """
    Record a move in statistics.

    Args:
        player: Player username who made the move
        game_id: ID of the game
        move: The move in USI format (optional)
        turn: Which side made the move - 'black' or 'white' (optional)
    """
    stats = load_stats()
    stats.total_moves += 1

    if player:
        stats.top_players.setdefault(player, PlayerStats())
        stats.top_players[player].moves += 1

    # Track recent moves (keep last 100 for history)
    from datetime import datetime

    move_record = MoveRecord(
        game_id=game_id,
        player=player,
        move=move,
        turn=turn,
        timestamp=datetime.now().isoformat(),
    )
    stats.recent_moves.insert(0, move_record)
    # Keep only last 100 moves for memory efficiency
    stats.recent_moves = stats.recent_moves[:100]

    save_stats(stats)


def record_game_end(
    game_id: str, winner: str | None, status: str, move_count: int
) -> None:
    """Record game end in statistics."""
    stats = load_stats()
    stats.total_games += 1

    if winner == "black":
        stats.black_wins += 1
    elif winner == "white":
        stats.white_wins += 1
    else:
        stats.draws += 1

    # Add to recent games
    recent = stats.recent_games
    recent.insert(
        0,
        RecentGame(
            game_id=game_id,
            winner=winner,
            status=status,
            moves=move_count,
        ),
    )
    # Keep only last 10 games
    stats.recent_games = recent[:10]

    save_stats(stats)


def get_leaderboard(limit: int = 10) -> list[tuple[str, int, int]]:
    """
    Get top players by moves.

    Returns:
        List of (player, moves, wins) tuples
    """
    stats = load_stats()
    top_players = stats.top_players

    # Sort by moves descending
    sorted_players = sorted(top_players.items(), key=lambda x: x[1].moves, reverse=True)

    return [(player, data.moves, data.wins) for player, data in sorted_players[:limit]]


def record_player_win(player: str) -> None:
    """Record a win for a player."""
    stats = load_stats()

    stats.top_players.setdefault(player, PlayerStats())
    stats.top_players[player].wins += 1

    save_stats(stats)


def get_recent_moves(limit: int = 5) -> list[MoveRecord]:
    """
    Get the most recent moves across all games.

    Args:
        limit: Maximum number of moves to return

    Returns:
        List of move records with game_id, player, move, turn, and timestamp
    """
    stats = load_stats()
    recent_moves = stats.recent_moves
    return recent_moves[:limit]


def get_game_recent_moves(game_id: str, limit: int = 5) -> list[MoveRecord]:
    """
    Get the most recent moves for a specific game.

    Args:
        game_id: The game ID to filter by
        limit: Maximum number of moves to return

    Returns:
        List of move records for the specified game
    """
    stats = load_stats()
    recent_moves = stats.recent_moves

    # Filter by game_id
    game_moves = [m for m in recent_moves if m.game_id == game_id]
    return game_moves[:limit]
