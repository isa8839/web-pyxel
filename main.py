"""
Monster Battle Game - メインエントリーポイント

スペースキーでモンスターを召喚し、敵拠点を攻撃するゲームです。
敵も自動的にモンスターを召喚してきます。
モンスター同士が出会うと戦闘が発生します。
"""

from game import Game


def main():
    """ゲームのメインエントリーポイント"""
    try:
        print("ゲーム開始")
        # ゲームを開始
        Game()
    except KeyboardInterrupt:
        print("ゲームが終了されました")
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
