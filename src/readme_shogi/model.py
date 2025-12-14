"""
Pydantic models for game state and statistics.
"""

import tomllib
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _now_iso() -> str:
    """Return current time in ISO format."""
    return datetime.now().isoformat()


class MoveHistoryEntry(BaseModel):
    """Single move entry within a game history."""

    move: str
    player: str | None = None
    timestamp: str = Field(default_factory=_now_iso)
    turn: str | None = None

    model_config = ConfigDict(extra="ignore")


class GameState(BaseModel):
    """Represents a Shogi game state."""

    game_id: str
    sfen: str
    moves: list[str] = Field(default_factory=list)
    move_history: list[MoveHistoryEntry] = Field(default_factory=list)
    created_at: str = Field(default_factory=_now_iso)
    last_move_at: str = Field(default_factory=_now_iso)
    status: str = "active"  # active, checkmate, stalemate, resigned, draw
    winner: str | None = None  # "black", "white", or None

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="after")
    def _sync_last_move(self) -> "GameState":
        """Ensure last_move_at is set even when empty in persisted data."""
        if not self.last_move_at:
            self.last_move_at = self.created_at
        return self


class PlayerStats(BaseModel):
    """Aggregated stats for a player."""

    moves: int = 0
    wins: int = 0

    model_config = ConfigDict(extra="ignore")


class RecentGame(BaseModel):
    """Summary of a recently finished game."""

    game_id: str
    winner: str | None
    status: str
    moves: int

    model_config = ConfigDict(extra="ignore")


class MoveRecord(BaseModel):
    """Recent move across games for stats."""

    game_id: str
    player: str | None = None
    move: str | None = None
    turn: str | None = None
    timestamp: str = Field(default_factory=_now_iso)

    model_config = ConfigDict(extra="ignore")


class Stats(BaseModel):
    """Global statistics tracked across games."""

    total_games: int = 0
    total_moves: int = 0
    black_wins: int = 0
    white_wins: int = 0
    draws: int = 0
    top_players: dict[str, PlayerStats] = Field(default_factory=dict)
    recent_games: list[RecentGame] = Field(default_factory=list)
    recent_moves: list[MoveRecord] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class IssueMove(BaseModel):
    """Parsed move payload from issue title."""

    game_id: str
    move: str

    model_config = ConfigDict(extra="ignore")


class RepositorySettings(BaseModel):
    """Repository related settings."""

    owner: str = ""
    repo: str = ""
    readme_path: str = "."

    model_config = ConfigDict(extra="forbid")


class GameSettings(BaseModel):
    """Game configuration settings."""

    max_moves: int = 500

    model_config = ConfigDict(extra="forbid")


class Settings(BaseModel):
    """Project settings loaded from TOML with explicit fields."""

    repository: RepositorySettings = Field(default_factory=RepositorySettings)
    game: GameSettings = Field(default_factory=GameSettings)

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def from_mapping(cls, data: Mapping[str, object] | None) -> "Settings":
        """Build settings from a generic mapping safely."""
        return cls.model_validate(data or {})

    @classmethod
    def from_toml(cls, path: Path) -> "Settings":
        """Load settings from a TOML file with safe defaults on errors."""
        if not path.exists():
            return cls()

        try:
            with path.open("rb") as file:
                raw = tomllib.load(file)
        except (tomllib.TOMLDecodeError, OSError):
            return cls()

        return cls.from_mapping(raw)
