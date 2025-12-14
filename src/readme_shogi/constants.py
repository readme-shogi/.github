"""
Constants for the Shogi game.
"""

from pathlib import Path

# Project paths
PROJECT_ROOT = Path.cwd().resolve()
ASSETS_DIR = PROJECT_ROOT / "assets"
DATA_DIR = PROJECT_ROOT / "data"
GAMES_DIR = DATA_DIR / "games"
IMG_DIR = ASSETS_DIR / "img"

# Template files
README_TEMPLATE = ASSETS_DIR / "README.template.md"
SETTINGS_FILE = ASSETS_DIR / "settings.toml"
STATS_FILE = DATA_DIR / "stats.json"

# Board dimensions (9x9 in Shogi)
BOARD_SIZE = 9

# Piece types mapping for cshogi
# cshogi uses specific piece type constants
# Piece types follow cshogi.PIECE_SYMBOLS indexes:
# 1=pawn, 2=lance, 3=knight, 4=silver, 5=bishop, 6=rook, 7=gold, 8=king,
# 9=+pawn, 10=+lance, 11=+knight, 12=+silver, 13=horse, 14=dragon.
PIECE_SYMBOLS = {
    0: None,  # Empty
    1: "FU",  # Pawn
    2: "KY",  # Lance
    3: "KE",  # Knight
    4: "GI",  # Silver
    5: "KA",  # Bishop
    6: "HI",  # Rook
    7: "KI",  # Gold
    8: "OU",  # King
    9: "TO",  # Promoted Pawn
    10: "NY",  # Promoted Lance
    11: "NK",  # Promoted Knight
    12: "NG",  # Promoted Silver
    13: "UM",  # Promoted Bishop (Horse)
    14: "RY",  # Promoted Rook (Dragon)
    # GY (Gyoku) is also King, used for one side
}

# File labels (columns) - using numbers 1-9 from right to left
FILE_LABELS = ["9", "8", "7", "6", "5", "4", "3", "2", "1"]

# Rank labels (rows)
RANK_LABELS = ["a", "b", "c", "d", "e", "f", "g", "h", "i"]
