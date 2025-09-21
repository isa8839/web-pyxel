import pyxel
from config import (
    CARD_WIDTH, CARD_HEIGHT, CARD_MARGIN, CARD_Y, MONSTER_CARD_COUNT, SPELL_CARD_COUNT,
    COLOR_CARD_BG, COLOR_CARD_BORDER, COLOR_CARD_SELECTED, COLOR_TEXT,
    MONSTER_TYPES, SPELL_TYPES, ATTRIBUTES
)
from spell_system import SpellCard


class Card:
    """モンスターカードクラス"""
    
    def __init__(self, x, y, monster_type):
        """
        カードを初期化
        
        Args:
            x (int): カードのX座標
            y (int): カードのY座標
            monster_type (str): モンスタータイプのキー
        """
        self.x = x
        self.y = y
        self.monster_type = monster_type
        self.monster_data = MONSTER_TYPES[monster_type]
        self.selected = False
    
    def is_clicked(self, mouse_x, mouse_y):
        """
        マウスクリックがカード内かどうかを判定
        
        Args:
            mouse_x (int): マウスのX座標
            mouse_y (int): マウスのY座標
            
        Returns:
            bool: クリックされたかどうか
        """
        return (self.x <= mouse_x <= self.x + CARD_WIDTH and
                self.y <= mouse_y <= self.y + CARD_HEIGHT)
    
    def draw(self):
        """カードを描画"""
        # カード背景
        bg_color = COLOR_CARD_SELECTED if self.selected else COLOR_CARD_BG
        pyxel.rect(self.x, self.y, CARD_WIDTH, CARD_HEIGHT, bg_color)
        
        # カード枠
        pyxel.rectb(self.x, self.y, CARD_WIDTH, CARD_HEIGHT, COLOR_CARD_BORDER)
        
        # モンスター色のサンプル（小さく）
        sample_size = 4
        sample_x = self.x + (CARD_WIDTH - sample_size) // 2
        sample_y = self.y + 2
        pyxel.rect(sample_x, sample_y, sample_size, sample_size, self.monster_data["color"])
        
        # モンスター名（短縮）
        name = self.monster_data["name"][:3]  # 3文字に短縮
        text_x = self.x + (CARD_WIDTH - len(name) * 4) // 2
        pyxel.text(text_x, self.y + 8, name, COLOR_TEXT)
        
        # 属性アイコン（1文字）
        attr_name = ATTRIBUTES[self.monster_data["attribute"]]["name"]
        pyxel.text(self.x + 1, self.y + 16, attr_name, COLOR_TEXT)
        
        # ステータス表示（コンパクト）
        hp_text = f"H{self.monster_data['hp']}"
        atk_text = f"A{self.monster_data['attack']}"
        
        pyxel.text(self.x + 1, self.y + 24, hp_text, COLOR_TEXT)
        pyxel.text(self.x + 15, self.y + 24, atk_text, COLOR_TEXT)
        
        # コスト表示
        cost_text = f"M{self.monster_data['cost']}"
        pyxel.text(self.x + 1, self.y + 32, cost_text, COLOR_TEXT)


class CardSystem:
    """カードシステム管理クラス"""
    
    def __init__(self):
        """カードシステムを初期化"""
        self.cards = []
        self.selected_card = None
        self._create_cards()
    
    def _create_cards(self):
        """カードを作成（モンスター5種類 + 呪文3種類）"""
        # 画面幅に合わせてカード配置を計算
        from config import SCREEN_WIDTH
        total_cards = MONSTER_CARD_COUNT + SPELL_CARD_COUNT
        total_width = total_cards * CARD_WIDTH + (total_cards - 1) * CARD_MARGIN
        start_x = (SCREEN_WIDTH - total_width) // 2
        
        # モンスターカード
        monster_types = list(MONSTER_TYPES.keys())
        for i in range(MONSTER_CARD_COUNT):
            card_x = start_x + i * (CARD_WIDTH + CARD_MARGIN)
            monster_type = monster_types[i]
            card = Card(card_x, CARD_Y, monster_type)
            self.cards.append(card)
        
        # 呪文カード
        spell_types = list(SPELL_TYPES.keys())
        for i in range(SPELL_CARD_COUNT):
            card_x = start_x + (MONSTER_CARD_COUNT + i) * (CARD_WIDTH + CARD_MARGIN)
            spell_type = spell_types[i]
            spell_card = SpellCard(card_x, CARD_Y, spell_type)
            self.cards.append(spell_card)
    
    def handle_click(self, mouse_x, mouse_y):
        """
        マウスクリックを処理
        
        Args:
            mouse_x (int): マウスのX座標
            mouse_y (int): マウスのY座標
            
        Returns:
            str or None: 選択されたモンスタータイプ、なければNone
        """
        for card in self.cards:
            if card.is_clicked(mouse_x, mouse_y):
                # 前の選択を解除
                if self.selected_card:
                    self.selected_card.selected = False
                
                # 新しいカードを選択
                card.selected = True
                self.selected_card = card
                return card.monster_type
        
        return None
    
    def get_selected_monster_type(self):
        """
        選択されているモンスタータイプを取得
        
        Returns:
            str or None: 選択されたモンスタータイプ
        """
        if self.selected_card:
            return self.selected_card.monster_type
        return None
    
    def draw(self):
        """全てのカードを描画"""
        for card in self.cards:
            card.draw()
