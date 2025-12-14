"""
Security utilities for input validation.
"""

import re

from readme_shogi.model import IssueMove

# Pattern for valid USI moves
USI_MOVE_PATTERN = re.compile(r"^[1-9][a-i][1-9][a-i]\+?$")
USI_DROP_PATTERN = re.compile(r"^[PLNSGBRK]\*[1-9][a-i]$")

# Pattern for valid game IDs (8 hex characters)
GAME_ID_PATTERN = re.compile(r"^[a-f0-9]{8}$")

# Pattern for issue title format
ISSUE_TITLE_PATTERN = re.compile(
    r"^shogi\|move\|([a-f0-9]{8})\|([1-9][a-i][1-9][a-i]\+?|[PLNSGBRK]\*[1-9][a-i])$"
)

# Maximum length for various inputs
MAX_GAME_ID_LENGTH = 8
MAX_MOVE_LENGTH = 6


def validate_move(move: str) -> bool:
    """
    Validate that a move string is in valid USI format.

    Args:
        move: Move string to validate

    Returns:
        True if valid, False otherwise
    """
    if not move or len(move) > MAX_MOVE_LENGTH:
        return False

    return bool(USI_MOVE_PATTERN.match(move) or USI_DROP_PATTERN.match(move))


def validate_game_id(game_id: str) -> bool:
    """
    Validate that a game ID is in valid format.

    Args:
        game_id: Game ID to validate

    Returns:
        True if valid, False otherwise
    """
    if not game_id or len(game_id) != MAX_GAME_ID_LENGTH:
        return False

    return bool(GAME_ID_PATTERN.match(game_id))


def parse_issue_title(title: str) -> IssueMove | None:
    """
    Parse and validate an issue title for move commands.

    Args:
        title: Issue title to parse

    Returns:
        Dictionary with 'game_id' and 'move' keys, or None if invalid
    """
    if not title:
        return None

    match = ISSUE_TITLE_PATTERN.match(title)
    if not match:
        return None

    return IssueMove(game_id=match.group(1), move=match.group(2))
