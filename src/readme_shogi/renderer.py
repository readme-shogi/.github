"""
Shogi board and README rendering.

Provides BoardRenderer for board markdown output, render_move_links for clickable
move links, and generate_readme for full README generation from template.
"""

from pathlib import Path
from string import Template
from urllib.parse import quote

from readme_shogi.constants import (
    BOARD_SIZE,
    FILE_LABELS,
    PIECE_SYMBOLS,
    PROJECT_ROOT,
    SETTINGS_FILE,
)
from readme_shogi.game import ShogiGame
from readme_shogi.localization import (
    AVAILABLE_LOCALES,
    DEFAULT_LOCALE,
    generate_language_links,
    get_readme_filename,
    get_template_path,
    set_locale,
    t,
    uses_ki2_notation,
)
from readme_shogi.model import Settings, Stats
from readme_shogi.stats import get_game_recent_moves, get_leaderboard, load_stats

# Rank labels for different notation styles
RANK_LABELS_LATIN = ["a", "b", "c", "d", "e", "f", "g", "h", "i"]
RANK_LABELS_KANJI = ["一", "二", "三", "四", "五", "六", "七", "八", "九"]


def _compute_relative_path(from_dir: Path, to_path: Path) -> str:
    """
    Compute relative path from one directory to another path.

    Both paths should be relative to the same root (project root).
    Returns a POSIX-style path string for use in URLs/markdown.

    Args:
        from_dir: Source directory (relative to project root)
        to_path: Target path (relative to project root)

    Returns:
        Relative path string in POSIX format
    """
    # Normalize paths (handle empty Path() and Path(".") as current directory)
    from_parts = (
        list(from_dir.parts) if from_dir.parts and from_dir.parts != (".",) else []
    )
    to_parts = list(to_path.parts)

    # Find common prefix
    common_length = 0
    for idx, (from_part, to_part) in enumerate(zip(from_parts, to_parts, strict=False)):
        if from_part == to_part:
            common_length = idx + 1
        else:
            break

    # Go up from from_dir to common ancestor
    ups = len(from_parts) - common_length
    # Then go down to to_path
    downs = to_parts[common_length:]

    result_parts = [".."] * ups + downs
    return "/".join(result_parts) if result_parts else "."


class BoardRenderer:
    """Renders the Shogi board as HTML and writes an SVG (foreignObject)."""

    def __init__(
        self,
        game: ShogiGame,
        use_kanji: bool = False,
        readme_dir: Path | None = None,
    ) -> None:
        self.game = game
        self.use_kanji = use_kanji
        self.rank_labels = RANK_LABELS_KANJI if use_kanji else RANK_LABELS_LATIN

        # Calculate relative path from README location to assets
        # readme_dir is relative to project root (e.g., Path() or Path("docs"))
        readme_path = readme_dir or Path()
        assets_path = Path("assets/img")
        # Compute the relative path from readme_dir to assets/img
        # We need to go up from readme_dir to root, then down to assets/img
        self._assets_prefix = _compute_relative_path(readme_path, assets_path)

    def _blank_img_tag(self) -> str:
        """Return a blank <img> tag to keep board cells sized."""
        img_path = f"{self._assets_prefix}/blank.svg"
        return f'<img src="{img_path}" width="48" />'

    def _piece_img_tag(self, piece_symbol: str, color: int) -> str:
        """Return an inline <img> tag for a piece (rotate for gote)."""
        img_path = f"{self._assets_prefix}/{color}{piece_symbol}.svg"
        # Assets already contain correct orientation per side; no CSS rotation needed.
        return f'<img src="{img_path}" width="48" />'

    def _render_hand_markdown(self, color: int) -> str:
        """Render pieces in hand as a compact table with icons only."""
        hand = self.game.get_hand(color)
        if not hand:
            return ""

        side_label = t("gote_hand") if color == 1 else t("sente_hand")
        icons: list[str] = []
        for piece_symbol, count in sorted(hand.items()):
            icons.extend(self._piece_img_tag(piece_symbol, color) for _ in range(count))

        header = f"| {side_label} |"
        separator = "|:-------------:|"
        pieces_row = f"| {' '.join(icons)} |" if icons else "|  |"
        return "\n".join([header, separator, pieces_row])

    def render_markdown(self, highlight_last_move: bool = True) -> str:
        """Render board and hands as markdown table plus inline images."""
        board_array = self.game.get_board_array()
        header = "|   | " + " | ".join(FILE_LABELS) + " |"
        separator = "|:-:|" + "|".join([":-:"] * BOARD_SIZE) + "|"

        rows: list[str] = []
        for rank_index, rank_label in enumerate(self.rank_labels):
            cells: list[str] = []
            for display_file in range(BOARD_SIZE):
                file_index = 8 - display_file
                cell = board_array[rank_index][file_index]
                content = self._blank_img_tag()
                if cell is not None:
                    piece_type, color = cell
                    piece_symbol = PIECE_SYMBOLS.get(piece_type)
                    if piece_symbol:
                        content = self._piece_img_tag(piece_symbol, color)
                cells.append(content)
            rows.append(f"| {rank_label} | " + " | ".join(cells) + " |")

        top_hand = self._render_hand_markdown(1)
        bottom_hand = self._render_hand_markdown(0)

        parts: list[str] = []
        if top_hand:
            parts.extend([top_hand, ""])
        parts.extend([header, separator, *rows])
        if bottom_hand:
            parts.extend(["", bottom_hand])

        return "\n".join(parts)


def render_move_links(
    game: ShogiGame,
    owner: str,
    repo: str,
    base_url: str = "https://github.com",
    use_ki2: bool = False,
) -> str:
    """
    Generate markdown with clickable move links.

    Args:
        game: The Shogi game
        owner: Repository owner
        repo: Repository name
        base_url: Base GitHub URL
        use_ki2: Whether to use KI2 notation for display (USI is always used in URLs)

    Returns:
        Markdown string with move links
    """
    if game.is_game_over:
        return t("game_over")

    legal_moves = game.get_legal_moves()

    # Pre-compute KI2 notation for all moves if needed
    move_ki2_map: dict[str, str] = {}
    if use_ki2:
        for move in legal_moves:
            move_ki2_map[move] = game.usi_to_ki2(move)

    # Generate links
    lines: list[str] = [f"**{t('legal_moves', count=len(legal_moves))}**", ""]

    # Generate the table (grouped by from square)
    moves_by_from: dict[str, list[str]] = {}
    for move in legal_moves:
        if "*" in move:
            piece = move[0]
            if use_ki2:
                # Use piece kanji for KI2 locales
                ki2_full = move_ki2_map[move]
                # Extract piece name from KI2 (e.g., "▲５五歩打" -> "歩打")
                ki2_stripped = ki2_full.lstrip("▲△ ")
                # The piece is the first character before the position
                key = ki2_stripped[-2:]  # "歩打" etc.
            else:
                key = f"Drop {piece}"
        else:
            from_sq = move[:2]
            key = _usi_square_to_ki2(from_sq) if use_ki2 else from_sq

        if key not in moves_by_from:
            moves_by_from[key] = []
        moves_by_from[key].append(move)

    lines.append(f"| {t('move_from')} | {t('moves')} |")
    lines.append("|:---------:|:------|")

    for from_key, moves in sorted(moves_by_from.items()):
        move_links_list: list[str] = []
        for move in sorted(moves):
            # Create issue URL
            title = quote(f"shogi|move|{game.state.game_id}|{move}")
            body = quote(
                f"<!-- DO NOT EDIT THIS ISSUE -->\n\n"
                f"I want to make the move: **{move}**\n\n"
                f"Game ID: {game.state.game_id}"
            )
            url = f"{base_url}/{owner}/{repo}/issues/new?title={title}&body={body}"

            if use_ki2:
                # For KI2: show destination in KI2 format
                if "*" in move:
                    # Drop move: show destination
                    dest = move.split("*")[1]
                    display_move = _usi_square_to_ki2(dest)
                else:
                    # Regular move: show destination + promotion
                    dest = move[2:4]
                    promotion = "成" if move.endswith("+") else ""
                    display_move = _usi_square_to_ki2(dest) + promotion
            else:
                display_move = move.split("*", 1)[1] if "*" in move else move[2:]
            move_links_list.append(f"[{display_move}]({url})")

        lines.append(f"| **{from_key}** | {', '.join(move_links_list)} |")

    # For KI2 locales, add a compact list below the table
    if use_ki2:
        lines.append("")
        lines.append(t("compact_moves_list"))
        lines.append("")

        # Generate compact KI2 move links
        move_links: list[str] = []
        for move in sorted(legal_moves):
            title = quote(f"shogi|move|{game.state.game_id}|{move}")
            body = quote(
                f"<!-- DO NOT EDIT THIS ISSUE -->\n\n"
                f"I want to make the move: **{move}**\n\n"
                f"Game ID: {game.state.game_id}"
            )
            url = f"{base_url}/{owner}/{repo}/issues/new?title={title}&body={body}"

            # Display KI2 notation without the side indicator (▲/△)
            ki2_full = move_ki2_map[move]
            ki2_display = ki2_full.lstrip("▲△ ")
            move_links.append(f"[{ki2_display}]({url})")

        lines.extend("- " + link for link in move_links)

    return "\n".join(lines)


def _usi_square_to_ki2(square: str) -> str:
    """Convert USI square (e.g., '7g') to KI2 format (e.g., '７七')."""
    if len(square) != 2:
        return square
    file_char = square[0]
    rank_char = square[1]

    # Full-width numbers for file
    file_mapping = {
        "1": "１",
        "2": "２",
        "3": "３",
        "4": "４",
        "5": "５",
        "6": "６",
        "7": "７",
        "8": "８",
        "9": "９",
    }
    # Kanji for rank
    rank_mapping = {
        "a": "一",
        "b": "二",
        "c": "三",
        "d": "四",
        "e": "五",
        "f": "六",
        "g": "七",
        "h": "八",
        "i": "九",
    }
    return file_mapping.get(file_char, file_char) + rank_mapping.get(
        rank_char, rank_char
    )


# ---------------------------------------------------------------------------
# Statistics and game info helpers
# ---------------------------------------------------------------------------


def generate_stats_blocks(
    game: ShogiGame | None = None, use_ki2: bool = False
) -> dict[str, str]:
    """Generate statistics data and pre-rendered tables where needed."""
    stats: Stats = load_stats()
    leaderboard = get_leaderboard(10)

    recent_moves_table = t("no_recent_moves")
    if game:
        recent_moves = get_game_recent_moves(game.state.game_id, limit=5)
        if recent_moves:
            rows: list[str] = [
                f"| # | {t('move')} | {t('player')} | {t('side')} |",
                "|---|------|--------|------|",
            ]
            # Get KI2 moves from game object if needed
            total_moves = len(game.state.moves)
            ki2_moves: list[str] = []
            if use_ki2:
                # Get the last N moves in KI2 format
                for i in range(max(0, total_moves - len(recent_moves)), total_moves):
                    ki2_move = game.get_move_ki2(i)
                    ki2_moves.append(ki2_move or "?")

            for i, move_record in enumerate(recent_moves, 1):
                move = move_record.move or "?"
                # Use KI2 format if available
                if use_ki2 and ki2_moves:
                    # Map recent_moves index to ki2_moves index
                    ki2_index = len(recent_moves) - i
                    display_move = (
                        ki2_moves[ki2_index] if ki2_index < len(ki2_moves) else move
                    )
                else:
                    display_move = move
                player = move_record.player
                turn = move_record.turn or "?"
                side = t("sente") if turn == "black" else t("gote")
                player_str = (
                    f"[@{player}](https://github.com/{player})"
                    if player
                    else t("anonymous")
                )
                rows.append(f"| {i} | `{display_move}` | {player_str} | {side} |")
            recent_moves_table = "\n".join(rows)

    leaderboard_table = t("no_leaderboard")
    if leaderboard:
        leader_rows: list[str] = [
            f"| {t('rank')} | {t('player')} | {t('total_moves')} | {t('wins')} |",
            "|------|--------|-------------|------|",
        ]
        for i, (player, moves, wins) in enumerate(leaderboard, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else str(i)
            player_str = f"[@{player}](https://github.com/{player})"
            leader_rows.append(f"| {medal} | {player_str} | {moves} | {wins} |")
        leaderboard_table = "\n".join(leader_rows)

    return {
        "total_games": str(stats.total_games),
        "total_moves": str(stats.total_moves),
        "black_wins": str(stats.black_wins),
        "white_wins": str(stats.white_wins),
        "draws": str(stats.draws),
        "recent_moves_table": recent_moves_table,
        "leaderboard_table": leaderboard_table,
    }


def generate_game_info(game: ShogiGame, use_ki2: bool = False) -> dict[str, str]:
    """Return game info fields for templating."""
    current_turn_label = t("sente") if game.current_turn == "black" else t("gote")
    status_key = f"status_{game.state.status}"
    status_title = t(status_key)
    winner_line = ""
    if game.state.winner:
        winner_label = t("sente") if game.state.winner == "black" else t("gote")
        winner_line = f"- {t('winner')}: **{winner_label}**"

    last_move_usi = game.get_last_move() or "—"
    # Convert to KI2 format if needed
    if use_ki2 and last_move_usi != "—":
        last_move = game.get_last_move_ki2() or last_move_usi
    else:
        last_move = last_move_usi

    return {
        "game_id": game.state.game_id,
        "status_title": status_title,
        "move_count": str(game.move_count),
        "current_turn_label": current_turn_label,
        "winner_line": winner_line,
        "last_move": last_move,
    }


# ---------------------------------------------------------------------------
# README generation
# ---------------------------------------------------------------------------


def generate_readme(
    game: ShogiGame,
    owner: str,
    repo: str,
    output_dir: Path | None = None,
) -> str:
    """
    Generate README files for all available locales.

    Args:
        game: Current game state
        owner: Repository owner
        repo: Repository name
        output_dir: Directory to write README files (default: readme_path from settings)

    Returns:
        Generated README content for the default locale (English)
    """
    settings = Settings.from_toml(SETTINGS_FILE)
    repo_settings = settings.repository
    target_dir = (
        output_dir or (PROJECT_ROOT / Path(repo_settings.readme_path))
    ).resolve()

    # Calculate readme_dir relative to project root for image path computation
    readme_dir = target_dir.relative_to(PROJECT_ROOT)

    default_content = ""

    for locale in AVAILABLE_LOCALES:
        # Set the current locale for translations
        set_locale(locale)

        use_ki2 = uses_ki2_notation(locale)

        # Generate board Markdown (table with inline images)
        game_board_kanji = BoardRenderer(
            game, use_kanji=True, readme_dir=readme_dir
        ).render_markdown(highlight_last_move=True)
        game_board_latin = BoardRenderer(
            game, use_kanji=False, readme_dir=readme_dir
        ).render_markdown(highlight_last_move=True)

        # Generate move links
        move_links = render_move_links(game, owner, repo, use_ki2=use_ki2)

        # Generate stats
        stats_blocks = generate_stats_blocks(game, use_ki2=use_ki2)

        # Generate game info fields
        game_info = generate_game_info(game, use_ki2=use_ki2)

        # Generate language links
        language_links = generate_language_links(locale)

        # Prepare template variables
        template_vars = {
            "GAME_BOARD_KANJI": game_board_kanji,
            "GAME_BOARD_LATIN": game_board_latin,
            "LANGUAGE_LINKS": language_links,
            "MOVE_LINKS": move_links,
            "TOTAL_GAMES": stats_blocks["total_games"],
            "TOTAL_MOVES": stats_blocks["total_moves"],
            "BLACK_WINS": stats_blocks["black_wins"],
            "WHITE_WINS": stats_blocks["white_wins"],
            "DRAWS": stats_blocks["draws"],
            "RECENT_MOVES_TABLE": stats_blocks["recent_moves_table"],
            "LEADERBOARD_TABLE": stats_blocks["leaderboard_table"],
            "GAME_ID": game_info["game_id"],
            "GAME_STATUS_TITLE": game_info["status_title"],
            "MOVE_COUNT": game_info["move_count"],
            "CURRENT_TURN_LABEL": game_info["current_turn_label"],
            "WINNER_LINE": game_info["winner_line"],
            "LAST_MOVE": game_info["last_move"],
            "OWNER": owner,
            "REPO": repo,
            "REPOSITORY_OWNER": repo_settings.owner,
            "REPOSITORY_REPO": repo_settings.repo,
            "REPOSITORY_README_PATH": repo_settings.readme_path,
            "GAME_MAX_MOVES": str(settings.game.max_moves),
        }

        # Load locale-specific template
        template_path = get_template_path(locale)
        if not template_path.exists():
            raise FileNotFoundError(f"README template not found: {template_path}")

        with template_path.open(encoding="utf-8") as f:
            template_content = f.read()

        # Use Template for safe substitution
        template = Template(template_content)
        readme_content = template.safe_substitute(template_vars)

        # Write to file
        readme_filename = get_readme_filename(locale)
        target_output = target_dir / readme_filename
        target_output.parent.mkdir(parents=True, exist_ok=True)
        with target_output.open("w", encoding="utf-8") as f:
            f.write(readme_content)

        # Keep default locale content for return
        if locale == DEFAULT_LOCALE:
            default_content = readme_content

    # Reset to default locale
    set_locale(DEFAULT_LOCALE)

    return default_content
