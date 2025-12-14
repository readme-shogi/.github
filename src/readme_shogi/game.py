"""
Game state management for Shogi.
"""

import json
import re
import uuid
from datetime import datetime
from pathlib import Path

import cshogi
from cshogi import KI2

from readme_shogi.constants import GAMES_DIR, SETTINGS_FILE
from readme_shogi.model import GameState, MoveHistoryEntry, Settings


class ShogiGame:
    """Manages a Shogi game using cshogi."""

    def __init__(self, state: GameState | None = None) -> None:
        """Initialize a new game or load from state."""
        self.board = cshogi.Board()

        if state:
            self.state = state
            # Replay all moves to get to current position
            for move in state.moves:
                usi_move = self._parse_move(move)
                if usi_move:
                    self.board.push_usi(usi_move)
        else:
            self.state = GameState(
                game_id=str(uuid.uuid4())[:8],
                sfen=self.board.sfen(),
            )

    def _parse_move(self, move: str) -> str | None:
        """Parse a move string to USI format."""
        # Already in USI format
        if re.match(r"^[1-9][a-i][1-9][a-i]\+?$", move):
            return move
        # Drop move format: P*5e
        if re.match(r"^[PLNSGBRK]\*[1-9][a-i]$", move):
            return move
        return move

    @property
    def current_turn(self) -> str:
        """Return whose turn it is."""
        return "black" if self.board.turn == cshogi.BLACK else "white"

    @property
    def is_game_over(self) -> bool:
        """Check if the game is over."""
        return self.state.status != "active"

    @property
    def move_count(self) -> int:
        """Return the number of moves made."""
        return len(self.state.moves)

    def get_legal_moves(self) -> list[str]:
        """Get all legal moves in USI format."""
        return [cshogi.move_to_usi(move) for move in self.board.legal_moves]

    def usi_to_ki2(self, usi_move: str) -> str:
        """
        Convert a USI move to KI2 notation for the current board state.

        Args:
            usi_move: Move in USI format (e.g., "7g7f" or "P*5e")

        Returns:
            The move in KI2 notation
        """
        move_int = self.board.move_from_usi(usi_move)
        result: str = KI2.move_to_ki2(move_int, self.board)
        return result

    def is_legal_move(self, move: str) -> bool:
        """Check if a move is legal."""
        usi_move = self._parse_move(move)
        if not usi_move:
            return False
        return usi_move in self.get_legal_moves()

    def make_move(self, move: str, player: str | None = None) -> bool:
        """
        Make a move on the board.

        Args:
            move: Move in USI format (e.g., "7g7f" or "P*5e" for drops)
            player: Optional player identifier for move history

        Returns:
            True if move was successful, False otherwise
        """
        usi_move = self._parse_move(move)
        if not usi_move or not self.is_legal_move(usi_move):
            return False

        # Record move
        move_record = MoveHistoryEntry(
            move=usi_move,
            player=player,
            timestamp=datetime.now().isoformat(),
            turn=self.current_turn,
        )

        # Make the move
        self.board.push_usi(usi_move)
        self.state.moves.append(usi_move)
        self.state.move_history.append(move_record)
        self.state.sfen = self.board.sfen()
        self.state.last_move_at = datetime.now().isoformat()

        # Check game status
        self._update_game_status()

        return True

    def _update_game_status(self) -> None:
        """Update game status after a move."""
        # Check for checkmate
        if self.board.is_game_over():
            self.state.status = "checkmate"
            # The player who just moved wins
            self.state.winner = "white" if self.current_turn == "black" else "black"
            return

        # Check for max moves (draw)
        settings = Settings.from_toml(SETTINGS_FILE)
        if self.move_count >= settings.game.max_moves:
            self.state.status = "draw"
            return

        # Check for repetition (sennichite)
        if self.board.is_draw():
            self.state.status = "draw"

    def resign(self, player: str) -> None:
        """Resign the game."""
        self.state.status = "resigned"
        # The other player wins
        if player == "black":
            self.state.winner = "white"
        else:
            self.state.winner = "black"

    def get_board_array(self) -> list[list[tuple[int, int] | None]]:
        """
        Get board as 2D array of (piece_type, color) tuples.

        Returns:
            9x9 array where each cell is (piece_type, color) or None
            color: 0 = black (sente), 1 = white (gote)
        """
        board_array: list[list[tuple[int, int] | None]] = []
        for rank in range(9):  # a (top) -> i (bottom)
            row: list[tuple[int, int] | None] = []
            for file_index in range(9):  # file 1 (right) -> 9 (left)
                square = file_index * 9 + rank
                piece = self.board.piece(square)
                if piece != 0:
                    piece_type = piece % 16
                    color = piece >> 4  # 0 = black (sente), 1 = white (gote)
                    row.append((piece_type, color))
                else:
                    row.append(None)
            board_array.append(row)
        return board_array

    def get_hand(self, color: int) -> dict[str, int]:
        """
        Get pieces in hand for a player.

        Args:
            color: 0 for black (sente), 1 for white (gote)

        Returns:
            Dictionary mapping piece symbol to count
        """
        hand: dict[str, int] = {}
        piece_types = ["FU", "KY", "KE", "GI", "KI", "KA", "HI"]

        for i, piece_symbol in enumerate(piece_types):
            count = self.board.pieces_in_hand[color][i]
            if count > 0:
                hand[piece_symbol] = count

        return hand

    def get_last_move(self) -> str | None:
        """Get the last move made."""
        if self.state.moves:
            return self.state.moves[-1]
        return None

    def get_move_ki2(self, move_index: int) -> str | None:
        """
        Get a move in KI2 notation by replaying the game to that point.

        Args:
            move_index: 0-based index of the move in self.state.moves

        Returns:
            The move in KI2 notation, or None if index is invalid
        """
        if move_index < 0 or move_index >= len(self.state.moves):
            return None

        # Create a temporary board and replay moves up to the target
        temp_board = cshogi.Board()
        for i, usi_move in enumerate(self.state.moves):
            move_int = temp_board.move_from_usi(usi_move)
            if i == move_index:
                # Get KI2 notation before making the move
                result: str = KI2.move_to_ki2(move_int, temp_board)
                return result
            temp_board.push(move_int)

        return None

    def get_last_move_ki2(self) -> str | None:
        """Get the last move in KI2 notation."""
        if not self.state.moves:
            return None
        return self.get_move_ki2(len(self.state.moves) - 1)

    def get_recent_moves_ki2(self, limit: int = 5) -> list[str]:
        """
        Get the most recent moves in KI2 notation.

        Args:
            limit: Maximum number of moves to return

        Returns:
            List of moves in KI2 notation, most recent first
        """
        result: list[str] = []
        total_moves = len(self.state.moves)
        start_index = max(0, total_moves - limit)

        for i in range(total_moves - 1, start_index - 1, -1):
            ki2_move = self.get_move_ki2(i)
            if ki2_move:
                result.append(ki2_move)

        return result

    def save(self, filepath: Path | None = None) -> Path:
        """Save game state to file."""
        if filepath is None:
            filepath = GAMES_DIR / f"{self.state.game_id}.json"

        filepath.parent.mkdir(parents=True, exist_ok=True)

        with filepath.open("w", encoding="utf-8") as f:
            json.dump(self.state.model_dump(mode="json"), f, indent=2)

        return filepath

    @classmethod
    def load(cls, filepath: Path) -> "ShogiGame":
        """Load game from file."""
        with filepath.open(encoding="utf-8") as f:
            data = json.load(f)

        state = GameState.model_validate(data)
        return cls(state)

    @classmethod
    def load_by_id(cls, game_id: str) -> "ShogiGame | None":
        """Load game by ID."""
        filepath = GAMES_DIR / f"{game_id}.json"
        if filepath.exists():
            return cls.load(filepath)
        return None

    @classmethod
    def get_current_game(cls) -> "ShogiGame | None":
        """Get the current active game."""
        if not GAMES_DIR.exists():
            return None

        # Find the most recent active game
        games = list(GAMES_DIR.glob("*.json"))
        if not games:
            return None

        # Sort by modification time, newest first
        games.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        for game_path in games:
            game = cls.load(game_path)
            if game.state.status == "active":
                return game

        return None

    @classmethod
    def new_game(cls) -> "ShogiGame":
        """Create and save a new game."""
        game = cls()
        game.save()
        return game
