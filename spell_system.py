import pyxel
from config import SPELL_TYPES, COLOR_CARD_BG, COLOR_CARD_BORDER, COLOR_CARD_SELECTED, COLOR_TEXT


class Spell:
    """呪文クラス"""
    
    def __init__(self, spell_type):
        """
        呪文を初期化
        
        Args:
            spell_type (str): 呪文タイプのキー
        """
        self.spell_type = spell_type
        self.spell_data = SPELL_TYPES[spell_type]
        self.name = self.spell_data["name"]
        self.cost = self.spell_data["cost"]
        self.effect = self.spell_data["effect"]
        self.value = self.spell_data["value"]
        self.target = self.spell_data["target"]
        self.color = self.spell_data["color"]

    def can_cast(self, current_mp):
        """呪文を使用できるかチェック"""
        return current_mp >= self.cost

    def cast(self, target_monster=None, target_area=None, monsters=None):
        """
        呪文を発動
        
        Args:
            target_monster: 単体対象の場合のターゲット
            target_area: 範囲対象の場合の座標 (x, y)
            monsters: 全モンスターリスト（範囲呪文用）
            
        Returns:
            bool: 呪文が成功したかどうか
        """
        if self.effect == "heal" and target_monster:
            target_monster.heal(self.value)
            return True
        
        elif self.effect == "damage" and target_area and monsters:
            # 範囲ダメージ
            area_x, area_y = target_area
            area_radius = 30  # 範囲半径
            
            for monster in monsters:
                if (monster.alive and monster.is_enemy and 
                    abs(monster.x - area_x) <= area_radius and 
                    abs(monster.y - area_y) <= area_radius):
                    monster.hp -= self.value
            return True
        
        elif self.effect == "buff_attack" and target_monster:
            target_monster.apply_buff("attack", self.value, 300)  # 5秒間
            return True
        
        return False


class SpellCard:
    """呪文カードクラス"""
    
    def __init__(self, x, y, spell_type):
        """
        呪文カードを初期化
        
        Args:
            x (int): カードのX座標
            y (int): カードのY座標
            spell_type (str): 呪文タイプのキー
        """
        self.x = x
        self.y = y
        self.spell = Spell(spell_type)
        self.selected = False
    
    def is_clicked(self, mouse_x, mouse_y):
        """マウスクリックがカード内かどうかを判定"""
        from config import CARD_WIDTH, CARD_HEIGHT
        return (self.x <= mouse_x <= self.x + CARD_WIDTH and
                self.y <= mouse_y <= self.y + CARD_HEIGHT)
    
    def draw(self):
        """呪文カードを描画"""
        from config import CARD_WIDTH, CARD_HEIGHT
        
        # カード背景
        bg_color = COLOR_CARD_SELECTED if self.selected else COLOR_CARD_BG
        pyxel.rect(self.x, self.y, CARD_WIDTH, CARD_HEIGHT, bg_color)
        
        # カード枠
        pyxel.rectb(self.x, self.y, CARD_WIDTH, CARD_HEIGHT, COLOR_CARD_BORDER)
        
        # 呪文色のサンプル（小さく）
        sample_size = 4
        sample_x = self.x + (CARD_WIDTH - sample_size) // 2
        sample_y = self.y + 2
        pyxel.rect(sample_x, sample_y, sample_size, sample_size, self.spell.color)
        
        # 呪文名（短縮）
        name = self.spell.name
        text_x = self.x + (CARD_WIDTH - len(name) * 4) // 2
        pyxel.text(text_x, self.y + 8, name, COLOR_TEXT)
        
        # 効果値表示（コンパクト）
        if self.spell.effect == "heal":
            effect_text = f"+{self.spell.value}"
        elif self.spell.effect == "damage":
            effect_text = f"-{self.spell.value}"
        elif self.spell.effect == "buff_attack":
            effect_text = f"A+{self.spell.value}"
        else:
            effect_text = "?"
        
        pyxel.text(self.x + 1, self.y + 16, effect_text, COLOR_TEXT)
        
        # コスト表示
        cost_text = f"M{self.spell.cost}"
        pyxel.text(self.x + 1, self.y + 24, cost_text, COLOR_TEXT)
        
        # 対象タイプ表示（短縮）
        if self.spell.target == "single_ally":
            target_text = "味方"
        elif self.spell.target == "area_enemy":
            target_text = "範囲"
        else:
            target_text = "?"
        
        pyxel.text(self.x + 1, self.y + 32, target_text, COLOR_TEXT)
