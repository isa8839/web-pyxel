"""
カラーパレット管理モジュール

このモジュールでは、ゲームで使用するカラーパレットを定義・管理します。
"""
import pyxel

def reset_blend():
    """ブレンドモードをリセットする"""
    pyxel.pal()
    pyxel.blend = False
    pass

def set_blend():
    """ブレンドモードを有効にする"""
    pyxel.pal()
    pyxel.blend = True
    pass
