"""
ウィンドウシステム - カード選択用の子ウィンドウ管理

モンスター召喚ウィンドウと呪文発動ウィンドウを提供し、
ウィンドウ表示中はゲームを一時停止します。
"""

import pyxel
import json
import os
from config import *
from config import MONSTERS_JSON_PATH, SPELLS_JSON_PATH


class WindowSystem:
    """ウィンドウシステム管理クラス"""
    
    def __init__(self):
        """ウィンドウシステムを初期化"""
        self.active_window = None  # None, "monster"
        self.selected_monster = None
        self.current_witch = None  # 現在の魔女
        
        # ゲームデータを読み込み
        self.monsters_data = self._load_monster_data()
        self.spells_data = self._load_spell_data()
        
        # カード設定（モンスター名とイラストが収まるサイズ）
        self.card_width = 80  # カードの幅を広げる
        self.card_height = 100  # カードの高さも少し広げる
        self.card_margin = 10  # カード間のマージンも広げる
        
        # ウィンドウ設定（カードが横に5枚並ぶように調整）
        self.window_width = (self.card_width + self.card_margin) * 5 + self.card_margin
        self.window_height = self.card_height + 60  # タイトルや余白のための高さ
        self.window_x = (SCREEN_WIDTH - self.window_width) // 2
        self.window_y = (SCREEN_HEIGHT - self.window_height) // 2
        self.card_margin = 3
        
        # BDFフォントを読み込み
        font_path = os.path.join(os.path.dirname(__file__), "asset", "umplus_j10r.bdf")
        self.font = pyxel.Font(font_path)
        
        # モンスターのスプライト情報（monsters.jsonから動的に読み込む）
        self.monster_sprites = {}
        # モンスターデータからスプライト情報を抽出
        for monster_id, monster_data in self.monsters_data.items():
            if "pyxres" in monster_data:
                pyxres = monster_data["pyxres"]
                self.monster_sprites[monster_id] = {
                    "x": pyxres.get("start_x", 0),
                    "y": pyxres.get("start_y", 0),
                    "w": monster_data.get("sprite_width", 16),
                    "h": monster_data.get("sprite_height", 16),
                    "bank": pyxres.get("bank", 0)
                }
        
    def _load_spell_data(self):
        """呪文データを読み込む"""
        json_path = os.path.join(os.path.dirname(__file__), SPELLS_JSON_PATH)
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            spells_data = data.get("spells", {})
            print("spell.jsonからデータを読み込みました")
            
            # 各呪文に色情報を追加
            for spell_id, spell in spells_data.items():
                # 効果に応じた色を設定
                if spell["effect"] == "heal":
                    spell["color"] = 11  # 水色
                elif spell["effect"] == "damage":
                    spell["color"] = 8   # 赤
                elif spell["effect"] == "buff_attack":
                    spell["color"] = 10  # 黄緑
            
            return spells_data
            
    def _load_monster_data(self):
        """モンスターデータと属性データを読み込む"""
        json_path = os.path.join(os.path.dirname(__file__), MONSTERS_JSON_PATH)
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.attributes = data.get("attributes", {})
            return data.get("monsters", {})
    
    def is_window_open(self):
        """ウィンドウが開いているかチェック"""
        return self.active_window is not None
    
    def set_current_witch(self, witch):
        """現在の魔女を設定する"""
        self.current_witch = witch
    
    def get_available_monsters(self):
        """現在の魔女が召喚できるモンスターのリストを返す"""
        if not self.current_witch:
            return []
        return self.current_witch.get_available_monsters()
    
    def get_available_spells(self):
        """現在の魔女が使用できる呪文のリストを返す"""
        if not self.current_witch:
            return []
        return self.current_witch.get_available_spells()
    
    def open_monster_window(self):
        """モンスター召喚ウィンドウを開く"""
        print("\n[DEBUG][window_system] モンスターウィンドウを開きます")
        self.active_window = "monster"
        self.selected_monster = None
        
        # 現在の魔女が召喚できるモンスターのみを表示
        available_monsters = self.get_available_monsters()
        print(f"[DEBUG][window_system] 利用可能なモンスター: {available_monsters}")
        self.available_monsters = available_monsters
    
    def open_spell_window(self):
        """呪文発動ウィンドウを開く"""
        self.active_window = "spell"
        self.selected_spell = None
        # 現在の魔女が使用できる呪文のみを表示
        self.available_spells = self.get_available_spells()
    
    def close_window(self):
        """ウィンドウを閉じる"""
        self.active_window = None
        self.selected_monster = None
    
    def handle_click(self, mouse_x, mouse_y):
        """
        ウィンドウ内のクリックを処理
        
        Args:
            mouse_x (int): マウスのX座標
            mouse_y (int): マウスのY座標
            
        Returns:
            tuple or None: クリックされたアイテムの種類とデータ (例: ("summon_monster", "goblin")), ウィンドウを閉じる場合は ("close", None)
        """
        print(f"\n[DEBUG][window_system] handle_click 開始: ({mouse_x}, {mouse_y})")
        
        # ウィンドウが閉じている場合は何もしない
        if not self.is_window_open():
            print("[DEBUG][window_system] ウィンドウが閉じているため、処理をスキップ")
            return None
            
        # ウィンドウの外側をクリックした場合はウィンドウを閉じる
        if not (self.window_x <= mouse_x < self.window_x + self.window_width and
                self.window_y <= mouse_y < self.window_y + self.window_height):
            print(f"[DEBUG][window_system] ウィンドウの外側をクリック: ウィンドウ範囲=({self.window_x}, {self.window_y}, {self.window_width}, {self.window_height})")
            self.close_window()
            print("[DEBUG][window_system] ウィンドウを閉じました")
            return ("close", None)
            
        print(f"[DEBUG][window_system] ウィンドウ内をクリック: アクティブウィンドウ={self.active_window}")
            
        # 閉じるボタンをチェック
        close_button_x = self.window_x + self.window_width - 20
        close_button_y = self.window_y + 5
        if (close_button_x <= mouse_x <= close_button_x + 15 and 
            close_button_y <= mouse_y <= close_button_y + 15):
            print("[DEBUG][window_system] 閉じるボタンがクリックされました")
            self.close_window()
            print("[DEBUG][window_system] ウィンドウを閉じました (閉じるボタン)")
            return ("close", None)
            
        # ウィンドウの処理
        if self.active_window == "monster":
            print("[DEBUG][window_system] モンスターウィンドウの処理を開始")
            monster_id = self._get_clicked_monster(mouse_x, mouse_y)
            if monster_id:
                print(f"[DEBUG][window_system] モンスターがクリックされました: {monster_id}")
                return ("summon_monster", monster_id)
            else:
                print("[DEBUG][window_system] モンスターはクリックされませんでした")
        elif self.active_window == "spell":
            print("[DEBUG][window_system] 呪文ウィンドウの処理を開始")
            spell_id = self._get_clicked_spell(mouse_x, mouse_y)
            if spell_id:
                print(f"[DEBUG][window_system] 呪文がクリックされました: {spell_id}")
                return ("cast_spell", spell_id)
            else:
                print("[DEBUG][window_system] 呪文はクリックされませんでした")
        
        print("[DEBUG][window_system] クリックされた有効な要素はありませんでした")
        return None
    
    def _get_clicked_monster(self, mouse_x, mouse_y):
        """
        クリックされた位置からモンスターを特定する
        
        Args:
            mouse_x (int): マウスのX座標
            mouse_y (int): マウスのY座標
            
        Returns:
            str or None: クリックされたモンスターのID、またはモンスターでない場合はNone
        """
        print(f"\n[DEBUG][window_system] _get_clicked_monster: クリック位置=({mouse_x}, {mouse_y})")
        
        available_monsters = self.get_available_monsters()
        monster_cards = []
        
        # 利用可能なモンスターのデータを取得
        for monster_id in available_monsters:
            if monster_id in self.monsters_data:
                monster_cards.append((monster_id, self.monsters_data[monster_id]))
        
        # 最大5枚まで表示
        monster_cards = monster_cards[:5]
        
        print(f"[DEBUG][window_system] モンスターカード数: {len(monster_cards)}")
        
        for i, (monster_id, monster_data) in enumerate(monster_cards):
            x = self.window_x + 10 + i * (self.card_width + self.card_margin)
            y = self.window_y + 25
            
            print(f"[DEBUG][window_system] モンスター {monster_id} のカード位置: x={x}-{x+self.card_width}, y={y}-{y+self.card_height}")
            
            # カードがクリックされたかチェック
            if (x <= mouse_x <= x + self.card_width and 
                y <= mouse_y <= y + self.card_height):
                print(f"[DEBUG][window_system] モンスター {monster_id} がクリックされました")
                return monster_id
            else:
                print(f"[DEBUG][window_system] モンスター {monster_id} はクリック範囲外です")
        
        print("[DEBUG][window_system] どのモンスターもクリックされませんでした")
        return None

    def _handle_spell_window_click(self, mouse_x, mouse_y):
        """呪文ウィンドウ内のクリック処理"""
        spell_id = self._get_clicked_spell(mouse_x, mouse_y)
        if spell_id:
            self.selected_spell = spell_id
            return ("cast_spell", spell_id)
        return None
        
    def _get_clicked_spell(self, mouse_x, mouse_y):
        """クリックされた位置から呪文を特定する"""
        available_spells = self.get_available_spells()
        spells_data = self._load_spell_data()
        
        # カードのサイズとマージン
        card_width = 100
        card_height = 80
        card_margin = 10
        max_cards_per_row = 3
        
        for i, spell_id in enumerate(available_spells):
            if spell_id not in spells_data:
                continue
                
            # カードの位置を計算
            row = i // max_cards_per_row
            col = i % max_cards_per_row
            
            x = self.window_x + 20 + col * (card_width + card_margin)
            y = self.window_y + 30 + row * (card_height + card_margin)
            
            # カードがクリックされたかチェック
            if (x <= mouse_x <= x + card_width and 
                y <= mouse_y <= y + card_height):
                return spell_id
                
        return None
            
    def _handle_monster_window_click(self, mouse_x, mouse_y):
        """モンスターウィンドウ内のクリック処理"""
        monster_type = self._get_clicked_monster(mouse_x, mouse_y)
        if monster_type:
            self.selected_monster = monster_type
            return ("summon_monster", monster_type)
        return None
            
    def draw(self):
        """ウィンドウを描画"""
        if not self.is_window_open():
            return
            
        # 背景を暗くする（半透明効果）
        for y in range(0, SCREEN_HEIGHT, 2):
            for x in range(0, SCREEN_WIDTH, 2):
                pyxel.pset(x, y, 1)
        
        # ウィンドウ背景
        pyxel.rect(self.window_x, self.window_y, self.window_width, self.window_height, 0)
        pyxel.rectb(self.window_x, self.window_y, self.window_width, self.window_height, 7)
        
        # ウィンドウを描画
        if self.active_window == "monster":
            self._draw_monster_window()
        elif self.active_window == "spell":
            self._draw_spell_window()
    
    def _draw_spell_window(self):
        """呪文選択ウィンドウを描画"""
        # ウィンドウの背景
        pyxel.rect(self.window_x, self.window_y, self.window_width, self.window_height, 1)
        pyxel.rectb(self.window_x, self.window_y, self.window_width, self.window_height, 7)
        
        # タイトル
        title = "呪文を選択"
        title_x = self.window_x + (self.window_width - len(title) * 4) // 2
        pyxel.text(title_x, self.window_y + 10, title, 7)
        
        # 利用可能な呪文を取得
        available_spells = self.get_available_spells()
        
        # 呪文データを読み込み
        spells_data = self._load_spell_data()
        
        # カードのサイズとマージン
        card_width = 100
        card_height = 80
        card_margin = 10
        
        # 最大3つまで横並びで表示
        max_cards_per_row = 3
        
        # 利用可能な呪文を表示
        for i, spell_id in enumerate(available_spells):
            if spell_id not in spells_data:
                continue
                
            spell = spells_data[spell_id]
            
            # カードの位置を計算
            row = i // max_cards_per_row
            col = i % max_cards_per_row
            
            x = self.window_x + 20 + col * (card_width + card_margin)
            y = self.window_y + 30 + row * (card_height + card_margin)
            
            # カードの背景（選択中はハイライト）
            card_color = spell.get('color', 1)
            if self.selected_spell == spell_id:
                pyxel.rectb(x-2, y-2, card_width+4, card_height+4, 7)  # 選択中の枠
            
            pyxel.rect(x, y, card_width, card_height, card_color)
            pyxel.rectb(x, y, card_width, card_height, 7)  # 枠線
            
            # 呪文名
            name = spell.get('name', spell_id)
            name_x = x + (card_width - len(name) * 4) // 2
            pyxel.text(name_x, y + 10, name, 0)  # 黒文字
            
            # コスト
            cost = spell.get('cost', 0)
            pyxel.text(x + 10, y + 25, f"MP: {cost}", 0)
            
            # 説明
            desc = spell.get('description', '')
            # 説明文を改行して表示（1行20文字まで）
            for j, line in enumerate(self._split_text(desc, 20)):
                pyxel.text(x + 10, y + 40 + j * 10, line, 0)
    
    def _get_attribute_name(self, attribute):
        """属性IDを日本語名に変換する"""
        attribute_names = {
            "power": "力",
            "wisdom": "知",
            "spirit": "霊",
            "none": "なし"
        }
        return attribute_names.get(attribute, attribute)

    def _split_text(self, text, max_length):
        """テキストを指定された長さで改行する"""
        lines = []
        for i in range(0, len(text), max_length):
            lines.append(text[i:i+max_length])
        return lines

    def _draw_monster_window(self):
        """モンスター選択ウィンドウを描画"""
        # ウィンドウの背景
        pyxel.rect(self.window_x, self.window_y, self.window_width, self.window_height, 1)
        pyxel.rectb(self.window_x, self.window_y, self.window_width, self.window_height, 7)
        
        # ウィンドウタイトル
        title = "モンスターを選択"
        title_x = self.window_x + (self.window_width - self.font.text_width(title)) // 2
        pyxel.text(title_x, self.window_y + 8, title, 7, self.font)
        
        # 現在の魔女が召喚できるモンスターのみを表示（最大5枚）
        available_monsters = self.get_available_monsters()
        monster_cards = []
        
        # 利用可能なモンスターのデータを取得
        for monster_id in available_monsters:
            if monster_id in self.monsters_data:
                monster_cards.append((monster_id, self.monsters_data[monster_id]))
        
        # 最大5枚まで表示
        monster_cards = monster_cards[:5]
        
        # モンスターカードを横一列に配置
        for i, (monster_id, monster_data) in enumerate(monster_cards):
            # カードの位置を計算（中央揃え）
            total_cards_width = len(monster_cards) * (self.card_width + self.card_margin) - self.card_margin
            start_x = self.window_x + (self.window_width - total_cards_width) // 2
            x = start_x + i * (self.card_width + self.card_margin)
            y = self.window_y + 30  # タイトルの下に余白を設ける
            
            # カードの背景（選択中は色を変える）
            color = 3 if monster_id == self.selected_monster else 2
            pyxel.rect(x, y, self.card_width, self.card_height, color)
            pyxel.rectb(x, y, self.card_width, self.card_height, 7)
            
            # モンスター名（中央揃え、1行目）
            monster_name = monster_data.get("name", monster_id)
            name_x = x + (self.card_width - self.font.text_width(monster_name)) // 2
            pyxel.text(name_x, y + 5, monster_name, 7, self.font)
            
            # コスト（2行目）
            cost = monster_data.get("cost", 0)
            cost_text = f"MP: {cost}"
            pyxel.text(x + 5, y + 15, cost_text, 7, self.font)
            
            # HP（3行目）
            hp = monster_data.get("hp", 0)
            hp_text = f"HP: {hp}"
            pyxel.text(x + 5, y + 25, hp_text, 7, self.font)
            
            # 攻撃力（4行目）
            attack = monster_data.get("attack", 0)
            attack_text = f"ATK: {attack}"
            pyxel.text(x + 5, y + 35, attack_text, 7, self.font)
            
            # 属性（5行目）
            attribute = monster_data.get("attribute", "none")
            attribute_text = f"属性: {self._get_attribute_name(attribute)}"
            pyxel.text(x + 5, y + 45, attribute_text, 7, self.font)
            
            # モンスターのスプライトを表示
            if monster_id in self.monster_sprites:
                sprite = self.monster_sprites[monster_id]
                sprite_w = sprite["w"]
                sprite_h = sprite["h"]
                
                # カード内に収まるようにスケーリング
                max_width = self.card_width - 20  # 左右の余白
                max_height = self.card_height - 70  # 上下の余白（テキストとボタンの分を考慮）
                scale = min(1.0, max_width / sprite_w, max_height / sprite_h)
                scaled_w = int(sprite_w * scale)
                scaled_h = int(sprite_h * scale)
                
                # スプライトの描画（中央揃え、下寄せ）
                sprite_x = x + (self.card_width - scaled_w) // 2
                sprite_y = y + self.card_height - scaled_h - 10  # 下部に余白を残して配置
                
                pyxel.blt(
                    sprite_x,
                    sprite_y,
                    sprite.get("bank", 0),
                    sprite["x"],
                    sprite["y"],
                    sprite_w,
                    sprite_h,
                    colkey=0  # 透明色（0番）を指定
                )
            else:
                # スプライトが登録されていない場合は四角で代用
                pyxel.rect(x + (self.card_width - 16) // 2, y + 30, 16, 16, 8)
                pyxel.text(x + (self.card_width - 4) // 2, y + 35, "?", 7)  # 中央に「?」を表示
            
        # 操作説明
        pyxel.text(self.window_x + 10, self.window_y + self.window_height - 15, "Click to summon", 7)
    
    def _draw_spell_window(self):
        """呪文発動ウィンドウを描画"""
        # タイトル
        title = "Cast Spell"
        title_width = self.font.text_width(title)
        title_x = self.window_x + (self.window_width - title_width) // 2
        pyxel.text(title_x, self.window_y + 8, title, 7, self.font)
        
        # 利用可能な呪文を取得
        available_spells = self.get_available_spells()
        
        for i, spell_type in enumerate(available_spells):
            if spell_type not in self.spells_data:
                continue
                
            spell_data = self.spells_data[spell_type]
            
            card_x = self.window_x + 10 + i * (self.card_width + self.card_margin)
            card_y = self.window_y + 30
            
            # カード背景
            bg_color = 6 if self.selected_spell == spell_type else 5
            pyxel.rect(card_x, card_y, self.card_width, self.card_height, bg_color)
            pyxel.rectb(card_x, card_y, self.card_width, self.card_height, 7)
            
            # 呪文色サンプル
            sample_size = 4
            sample_x = card_x + (self.card_width - sample_size) // 2
            sample_y = card_y + 2
            pyxel.rect(sample_x, sample_y, sample_size, sample_size, spell_data["color"])
            
            # 呪文名
            name = spell_data["name"]
            name_width = self.font.text_width(name)
            name_x = card_x + (self.card_width - name_width) // 2
            pyxel.text(name_x, card_y + 8, name, 7, self.font)
            
            # 効果値
            if spell_data["effect"] == "heal":
                effect_text = f"+{spell_data['value']}"
            elif spell_data["effect"] == "damage":
                effect_text = f"-{spell_data['value']}"
            elif spell_data["effect"] == "buff_attack":
                effect_text = f"A+{spell_data['value']}"
            else:
                effect_text = "?"
            
            pyxel.text(card_x + 1, card_y + 16, effect_text, 7, self.font)
            
            # コスト
            cost_text = f"M{spell_data['cost']}"
            pyxel.text(card_x + 1, card_y + 24, cost_text, 7, self.font)
            
            # 対象
            if spell_data["target"] == "single_ally":
                target_text = "味方"
            elif spell_data["target"] == "area_enemy":
                target_text = "範囲"
            else:
                target_text = "?"
            
            pyxel.text(card_x + 1, card_y + 32, target_text, 7, self.font)
        
        # 操作説明
        pyxel.text(self.window_x + 10, self.window_y + self.window_height - 15, "Click to cast", 7, self.font)
