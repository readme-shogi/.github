# 在 README 里下将棋！

$LANGUAGE_LINKS

欢迎来到这场公开的[将棋](https://zh.wikipedia.org/wiki/%E6%97%A5%E6%9C%AC%E5%B0%86%E6%A3%8B)比赛！

任何人都可以点击下方链接来下一步棋。

## 当前对局

- 游戏 ID：[`$GAME_ID`](https://github.com/$OWNER/$REPO/blob/main/data/games/$GAME_ID.json)
- 状态：**$GAME_STATUS_TITLE**
- 手数：**$MOVE_COUNT**
- 行棋方：**$CURRENT_TURN_LABEL**
- 最后一手：`$LAST_MOVE`
$WINNER_LINE

$GAME_BOARD_KANJI

### 行棋

点击下方的着法来下棋！

$MOVE_LINKS

> [!NOTE]
>
> **工作原理**
> 
> 当你点击着法链接并创建 issue 时，GitHub Actions 工作流会自动处理你的着法，更新游戏数据并提交更改到仓库。

## 统计数据

- 总对局数: **$TOTAL_GAMES**
- 总手数: **$TOTAL_MOVES**
- 先手胜: **$BLACK_WINS**
- 后手胜: **$WHITE_WINS**
- 和棋: **$DRAWS**

### 本局最近5手
$RECENT_MOVES_TABLE

### 前10名玩家 / 排行榜
$LEADERBOARD_TABLE

## 致谢
[MIT License](LICENSE)

将棋棋子图像托管在 [shogi-pieces-ryoko-remix](https://github.com/readme-shogi/shogi-pieces-ryoko-remix) 仓库，采用 [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) 许可证。
