# Open Shogi Tournament in README!

$LANGUAGE_LINKS

Welcome to a public [Shogi](https://wikipedia.org/wiki/Shogi) (将棋, Japanese chess) game!

ANYONE can make a move by clicking on one of the links below.

## Current Game

- Game ID: [`$GAME_ID`](https://github.com/$OWNER/$REPO/blob/main/data/games/$GAME_ID.json)
- Status: **$GAME_STATUS_TITLE**
- Moves: **$MOVE_COUNT**
- Turn: **$CURRENT_TURN_LABEL**
- Last move: `$LAST_MOVE`
$WINNER_LINE

$GAME_BOARD_LATIN

### Make Your Move

Click on a move below to make your move!

$MOVE_LINKS

> [!NOTE]
>
> **How this works**
> 
> When you click on a move and open a new issue, a GitHub Actions workflow will automatically process your move, update the game data and commit the changes to the repository.

## Statistics

- Total games: **$TOTAL_GAMES**
- Total moves: **$TOTAL_MOVES**
- Black wins: **$BLACK_WINS**
- White wins: **$WHITE_WINS**
- Draws: **$DRAWS**

### Last 5 Moves in This Game
$RECENT_MOVES_TABLE

### Top 10 Players / Leaderboard
$LEADERBOARD_TABLE

## Credit
[MIT License](LICENSE)

Shogi pieces hosted at [shogi-pieces-ryoko-remix](https://github.com/readme-shogi/shogi-pieces-ryoko-remix) repository, licensed under the [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) license.
