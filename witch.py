import json
import os
import pyxel

class Witch:
    """魔女クラス。プレイヤーと敵の拠点を表す。"""
    
    def __init__(self, witch_id, is_player=False):
        """
        魔女を初期化する
        
        Args:
            witch_id (str): 魔女のID（例: "fire_witch"）
            is_player (bool): プレイヤー側かどうか
        """
        self.witch_id = witch_id
        self.is_player = is_player
        self.data = self._load_witch_data(witch_id)
        
        # 現在のHPを最大HPで初期化
        self.current_hp = self.data["hp"]
        self.max_hp = self.data["hp"]
        
        # 座標を初期化（デフォルト値）
        self.x = 0
        self.y = 0
        
        # 画像の読み込み
        self.image = self._load_witch_image()
    
    def _load_witch_data(self, witch_id):
        """魔女のデータを読み込む"""
        json_path = os.path.join(os.path.dirname(__file__), "witch.json")
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            witch_data = data["witches"].get(witch_id)
            if not witch_data:
                raise ValueError(f"魔女ID '{witch_id}' が見つかりません。")
            return witch_data
    
    def _load_witch_image(self):
        """
        魔女のスプライト情報を取得する
        pyxres形式のデータを使用して画像を表示する
        """
        try:
            # スプライト情報を取得
            sprite_data = {
                "bank": self.data["pyxres"]["bank"],
                "x": self.data["pyxres"]["start_x"],
                "y": self.data["pyxres"]["start_y"],
                "width": self.data["sprite_width"],
                "height": self.data["sprite_height"]
            }
            print(f"魔女のスプライトを読み込みました: {self.data['name']} - {sprite_data}")
            return sprite_data
            
        except KeyError as e:
            print(f"警告: 魔女のスプライト情報が不完全です: {e}")
            return None
    
    def take_damage(self, amount):
        """
        ダメージを受ける
        
        Args:
            amount (int): 受けるダメージ量
            
        Returns:
            bool: 魔女が倒されたらTrue、それ以外はFalse
        """
        self.current_hp = max(0, self.current_hp - amount)
        return self.current_hp <= 0
    
    def draw(self, x, y):
        """
        魔女を描画する
        
        Args:
            x (int): 描画位置X座標
            y (int): 描画位置Y座標
        """
        # 座標を更新
        self.x = x
        self.y = y
        
        # HPバーを描画
        bar_width = 40
        hp_ratio = self.current_hp / self.max_hp
        pyxel.rect(x, y - 10, bar_width, 5, 8)  # 背景（赤）
        pyxel.rect(x, y - 10, int(bar_width * hp_ratio), 5, 11)  # HP（緑）
        
        # 魔女の名前を描画
        pyxel.text(x, y - 20, self.data["name"], 7)
        
        width = self.image["width"] if self.is_player else -self.image["width"] 
        
        # 画像がある場合は描画
        if hasattr(self, 'image') and self.image:
            pyxel.blt(
                x, y,
                self.image["bank"],
                self.image["x"], self.image["y"],
              width, self.image["height"],
                colkey=0  # 透明色（0）を指定
            )
        else:
            # 画像がない場合は四角で代用
            pyxel.rect(x, y, 32, 48, 8 if self.is_player else 7)
    
    def get_available_monsters(self):
        """
        この魔女が召喚可能なモンスターのリストを返す
        
        Returns:
            list: 召喚可能なモンスターIDのリスト
        """
        return self.data.get("summonable_monsters", [])
    
    def get_available_spells(self):
        """
        この魔女が使用可能な呪文のリストを返す
        
        Returns:
            list: 使用可能な呪文IDのリスト
        """
        return self.data.get("available_spells", [])
