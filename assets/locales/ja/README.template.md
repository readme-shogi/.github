# オープン将棋トーナメント in README!

$LANGUAGE_LINKS

公開の[将棋](https://ja.wikipedia.org/wiki/%E5%B0%86%E6%A3%8B)ゲームへようこそ！

下のリンクをクリックして、どなたでも一手指すことができます。

## 現在の対局

- ゲームID: [`$GAME_ID`](https://github.com/$OWNER/$REPO/blob/main/data/games/$GAME_ID.json)
- ステータス: **$GAME_STATUS_TITLE**
- 手数: **$MOVE_COUNT**
- 手番: **$CURRENT_TURN_LABEL**
- 最終手: `$LAST_MOVE`
$WINNER_LINE

$GAME_BOARD_KANJI

### あなたの一手を指す

下のリンクをクリックして着手してください！

$MOVE_LINKS

> [!NOTE]
>
> **仕組みについて**
> 
> リンクをクリックしてissueを作成すると、GitHub Actionsワークフローが自動的にあなたの着手を処理し、ゲームデータを更新してリポジトリにコミットします。

## 統計

- 総対局数: **$TOTAL_GAMES**
- 総手数: **$TOTAL_MOVES**
- 先手勝ち: **$BLACK_WINS**
- 後手勝ち: **$WHITE_WINS**
- 引き分け: **$DRAWS**

### この対局の最近の5手
$RECENT_MOVES_TABLE

### トップ10プレイヤー / リーダーボード
$LEADERBOARD_TABLE

## クレジット
[MIT License](LICENSE)

駒の画像は [shogi-pieces-ryoko-remix](https://github.com/readme-shogi/shogi-pieces-ryoko-remix) リポジトリでホストされており、[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) ライセンスの下で提供されています。
