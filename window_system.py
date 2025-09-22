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
    
    def __init__(self, game):
        """ウィンドウシステムを初期化
        
        Args:
            game: Gameクラスのインスタンス
        """
        self.game = game  # Gameクラスのインスタンスを保持
        self.active_window = None  # None, "monster"
        self.selected_monster = None
        self.current_witch = None  # 現在の魔女
        
        # ゲームデータを読み込み
        self.monsters_data = self._load_monster_data()
        self.spells_data = self._load_spell_data()
        
        # カード設定（モンスター名とイラストが収まるサイズ）
        # 注: これらの値は実際には使用されていません。代わりに各メソッド内で直接値を指定しています。
        # 将来的にリファクタリングする場合は、これらの値を使用するように統一すると良いでしょう。
        self.card_width = 80  # カードの幅
        self.card_height = 120  # カードの高さ（実際の描画に合わせて更新）
        self.card_margin = 5  # カード間のマージン（実際の描画に合わせて更新）
        
        # ウィンドウ設定（カードが横に5枚並ぶように調整）
        self.window_width = min(SCREEN_WIDTH - 20, (self.card_width + self.card_margin) * 5 + self.card_margin)  # 画面幅を超えないようにする
        self.window_height = min(SCREEN_HEIGHT - 20, self.card_height + 60)  # 画面高さを超えないようにする
        self.window_x = (SCREEN_WIDTH - self.window_width) // 2
        # 画面の中央よりやや上に配置（下に余裕を持たせる）
        self.window_y = (SCREEN_HEIGHT - self.window_height) // 3
        self.card_margin = 3

        # BDFフォントを読み込み
        font_path = os.path.join(os.path.dirname(__file__), "asset", "umplus_j10r.bdf")
        self.font = pyxel.Font(font_path)
        
        # モンスターボタンのリスト
        self.monster_buttons = []
        
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
                
        # クリック管理用の変数
        self._last_click_time = 0
        self._window_opened_time = 0
        
        # マウス座標の追跡用
        self.mouse_x = 0
        self.mouse_y = 0
        self.hovered_monster = None  # ホバー中のモンスターID
        
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
        
    def open_monster_window(self):
        """モンスター召喚ウィンドウを開く"""
        print("[DEBUG][window_system.open_monster_window] モンスターウィンドウを開きます")
        self.active_window = "monster"
        self.selected_monster = None
        # 現在の魔女が召喚できるモンスターのみを表示
        self.available_monsters = self.get_available_monsters()
        # ウィンドウが開かれた時間を記録（現在のフレームより1フレーム前を設定）
        self._window_opened_time = pyxel.frame_count - 1
        # クリック無視フラグを設定
        self._ignore_clicks_until = pyxel.frame_count + 2
        print(f"[DEBUG][window_system.open_monster_window] ウィンドウを開きました。利用可能なモンスター: {self.available_monsters}")
        print(f"[DEBUG][window_system.open_monster_window] フレーム {pyxel.frame_count} から {self._ignore_clicks_until} までクリックを無視します")

    def get_available_monsters(self):
        """現在の魔女が召喚できるモンスターのリストを返す"""
        if not self.current_witch:
            print("[DEBUG][window_system.get_available_monsters] 現在の魔女が設定されていません")
            return []
        
        # 現在の魔女の属性に基づいて利用可能なモンスターをフィルタリング
        available = []
        for monster_id, monster_data in self.monsters_data.items():
            if monster_data.get("attribute") in self.current_witch.data.get("attributes", []):
                available.append(monster_id)
        
        print(f"[DEBUG][window_system.get_available_monsters] 利用可能なモンスター: {available}")
        return available

    def set_current_witch(self, witch):
        """現在の魔女を設定する"""
        self.current_witch = witch
        print(f"[DEBUG][window_system.set_current_witch] 現在の魔女を設定: {witch.data['name'] if witch else 'None'}")
        
    def _draw_monster_window(self):
        """モンスター選択ウィンドウを描画"""
        # ウィンドウのサイズを調整
        self.window_width = 256  # 幅を少し小さく
        self.window_height = 160  # 高さを少し小さく
        self.window_x = (SCREEN_WIDTH - self.window_width) // 2
        self.window_y = (SCREEN_HEIGHT - self.window_height) // 2

        # ウィンドウの背景
        pyxel.rect(self.window_x, self.window_y, self.window_width, self.window_height, 1)
        pyxel.rectb(self.window_x, self.window_y, self.window_width, self.window_height, 7)
        
        # ウィンドウタイトル
        title = "モンスターを選択"
        title_x = self.window_x + (self.window_width - self.font.text_width(title)) // 2
        pyxel.text(title_x, self.window_y + 12, title, 7, self.font)
        
        # 現在の魔女が召喚できるモンスターのみを表示
        available_monsters = self.get_available_monsters()
        monster_cards = []
        
        # 利用可能なモンスターのデータを取得
        for monster_id in available_monsters:
            if monster_id in self.monsters_data:
                monster_cards.append((monster_id, self.monsters_data[monster_id]))
        
        # 最大3枚まで表示
        monster_cards = monster_cards[:3]
        
        # カード間の余白を調整
        card_margin = 5
        card_width = 80
        card_height = 120
        
        # モンスターカードを横一列に配置
        for i, (monster_id, monster_data) in enumerate(monster_cards):
            # カードの位置を計算（中央揃え）
            total_cards_width = len(monster_cards) * (card_width + card_margin) - card_margin
            start_x = self.window_x + (self.window_width - total_cards_width) // 2
            x = start_x + i * (card_width + card_margin)
            y = self.window_y + 35  # タイトルとの余白を調整
            
            # カードの背景（選択中は色を変える）
            color = 3 if monster_id == self.selected_monster else 2
            pyxel.rect(x, y, card_width, card_height, color)
            pyxel.rectb(x, y, card_width, card_height, 7)
            
            # モンスター名（中央揃え、1行目）
            monster_name = monster_data.get("name", monster_id)
            name_x = x + (card_width - self.font.text_width(monster_name)) // 2
            pyxel.text(name_x, y + 10, monster_name, 7, self.font)
            
            # モンスター画像の表示エリアを定義（カードの大部分を使用）
            image_area_top = y + 20  # モンスター名の下の余白を少し減らす
            image_area_height = card_height - 70  # ステータス表示エリアとの余白を調整
            
            # モンスターのスプライトを表示
            if monster_id in self.monster_sprites:
                sprite = self.monster_sprites[monster_id]
                sprite_w = sprite["w"]
                sprite_h = sprite["h"]
                
                # カード内に収まるようにスケーリングを計算（より大きく表示するため余白を減らす）
                max_width = card_width - 10  # 左右の余白を減らす
                max_height = image_area_height - 10  # 上下の余白
                
                # アスペクト比を維持したスケーリング（より大きいスケールを使用）
                width_ratio = max_width / sprite_w
                height_ratio = max_height / sprite_h
                scale = min(1.0, width_ratio, height_ratio)  # スケールを大きくする（最大1.5倍）
                
                # スケーリング後のサイズ
                scaled_w = int(sprite_w * scale)
                scaled_h = int(sprite_h * scale)
                
                # カード内で中央に配置するための位置を計算
                sprite_x = x -5 + (card_width - scaled_w) // 2
                sprite_y = y + 15  # 上部からのオフセットを調整（小さくするともっと上に）
                
                # スプライトを描画
                pyxel.blt(
                    sprite_x,
                    sprite_y,
                    sprite.get("bank", 0),
                    sprite["x"],
                    sprite["y"],
                    sprite_w,
                    sprite_h,
                    colkey=0,  # 透明色（0番）を指定
                    scale=scale
                )
            else:
                # スプライトが登録されていない場合は四角で代用
                pyxel.rect(x + (card_width - 32) // 2, image_y + 20, 32, 32, 8)
                pyxel.text(x + (card_width - 4) // 2, image_y + 30, "?", 7)
            
            # ステータス表示（画像の下に配置）
            status_y = y + card_height - 60
            
            # コスト（MP）
            cost = monster_data.get("cost", 0)
            cost_text = f"MP: {cost}"
            pyxel.text(x + 10, status_y, cost_text, 7, self.font)
            
            # HP
            hp = monster_data.get("hp", 0)
            hp_text = f"HP: {hp}"
            pyxel.text(x + 10, status_y + 15, hp_text, 7, self.font)
            
            # 攻撃力
            attack = monster_data.get("attack", 0)
            attack_text = f"ATK: {attack}"
            pyxel.text(x + 10, status_y + 30, attack_text, 7, self.font)
            
            # 属性（右寄せ）
            attribute = monster_data.get("attribute", "none")
            attribute_text = f"属性: {self._get_attribute_name(attribute)}"
            attr_x = x + card_width - 10 - self.font.text_width(attribute_text)
            pyxel.text(attr_x, status_y + 45, attribute_text, 7, self.font)

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
        self.monster_buttons = []
        
        # ウィンドウが開かれた時間を記録
        self._window_opened_time = pyxel.frame_count
        
        # 現在の魔女が召喚できるモンスターのみを表示
        available_monsters = self.get_available_monsters()
        print(f"[DEBUG][window_system] 利用可能なモンスター: {available_monsters}")
        self.available_monsters = available_monsters
        
        # モンスターボタンを作成
        for i, monster_id in enumerate(available_monsters):
            monster_data = self.monsters_data.get(monster_id, {})
            x = self.window_x + self.card_margin + (i % 5) * (self.card_width + self.card_margin)
            y = self.window_y + 30 + (i // 5) * (self.card_height + self.card_margin)
            
            # モンスター名を取得（日本語名があればそれを使用、なければIDを表示）
            monster_name = monster_data.get("name_jp", monster_id)
            
            # ボタンを作成
            from button import Button
            button = Button(
                x, y, self.card_width, self.card_height,
                monster_name,
                lambda mid=monster_id: self._on_monster_button_click(mid),
                col=7,  # テキスト色（白）
                bg_col=1,  # 背景色（黒）
                border_col=6,  # 枠線色（黄色）
                hover_col=3,  # ホバー時の色（水色）
                active_col=5,  # 押下時の色（マゼンタ）
                font=self.font  # フォントを設定
            )
            # ボタンにモンスターIDを設定
            button.monster_id = monster_id
            self.monster_buttons.append(button)
    
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
            tuple or None: クリックされたアイテムの種類とデータ (例: ("summon_monster", "goblin")), 
                          ウィンドウを閉じる場合は ("close", None),
                          クリックを処理した場合は ("handled", None) を返す
        """
        if not self.is_window_open():
            print("[DEBUG][window_system.handle_click] ウィンドウが閉じているため、処理をスキップ")
            return None
            
        # 前回のクリックから5フレーム未満の場合は無視
        current_frame = pyxel.frame_count
        if current_frame - self._last_click_time < 5 and self._last_click_time > 0:
            print(f"[DEBUG][window_system.handle_click] 連続クリックを検出、処理をスキップします (前回からのフレーム数: {current_frame - self._last_click_time})")
            return ("handled", None)
            
        # ウィンドウが開かれてから5フレーム未満の場合はクリックを無視
        if hasattr(self, '_window_opened_time') and current_frame - self._window_opened_time < 5:
            print(f"[DEBUG][window_system.handle_click] ウィンドウが開いた直後のため、クリックを無視します (経過フレーム: {current_frame - self._window_opened_time})")
            return ("handled", None)
            
        # ウィンドウタイプに応じたクリック処理
        if self.active_window == "monster":
            print("[DEBUG][window_system.handle_click] モンスターウィンドウのクリックを処理")
            result = self._handle_monster_window_click(mouse_x, mouse_y)
            if result:
                return result
            # モンスターがクリックされなかった場合は、イベント伝播を停止
            print("[DEBUG][window_system.handle_click] モンスターがクリックされませんでした。イベント伝播を停止します。")
            return ("handled", None)
            
        elif self.active_window == "spell":
            print("[DEBUG][window_system.handle_click] 呪文ウィンドウのクリックを処理")
            result = self._handle_spell_window_click(mouse_x, mouse_y)
            if result:
                return result
            # 呪文がクリックされなかった場合は、イベント伝播を停止
            print("[DEBUG][window_system.handle_click] 呪文がクリックされませんでした。イベント伝播を停止します。")
            return ("handled", None)
            
        print("[DEBUG][window_system.handle_click] 不明なウィンドウタイプのため、イベント伝播を停止します。")
        return ("handled", None)
    
    def _handle_monster_window_click(self, mouse_x, mouse_y):
        """
        モンスターウィンドウ内のクリック処理
        
        Args:
            mouse_x (int): マウスのX座標
            mouse_y (int): マウスのY座標
            
        Returns:
            tuple or None: クリックされたモンスターのIDを含むタプル ("summon_monster", monster_id)、
                          ウィンドウを閉じる場合は ("close", None)、
                          何もクリックされていない場合は None を返す
        """
        print(f"[DEBUG][window_system._handle_monster_window_click] クリック位置: ({mouse_x}, {mouse_y})")
        
        # 閉じるボタンのチェック（ウィンドウの右上の×ボタン）
        close_btn_x = self.window_x + self.window_width - 15
        close_btn_y = self.window_y + 5
        
        if (close_btn_x <= mouse_x <= close_btn_x + 10 and 
            close_btn_y <= mouse_y <= close_btn_y + 10):
            print("[DEBUG][window_system._handle_monster_window_click] 閉じるボタンがクリックされました")
            self.close_window()
            return ("close", None)
        
        # モンスターカードのクリックをチェック
        monster_id = self._get_clicked_monster(mouse_x, mouse_y)
        if monster_id:
            print(f"[DEBUG][window_system._handle_monster_window_click] モンスター {monster_id} がクリックされました")
            self.selected_monster = monster_id
            self.close_window()  # ウィンドウを閉じる
            return ("summon_monster", monster_id)
        
        # ウィンドウの背景がクリックされた場合（カード以外の部分）
        print("[DEBUG][window_system._handle_monster_window_click] カード以外がクリックされました")
        return ("handled", None)
        
    def _get_clicked_monster(self, mouse_x, mouse_y):
        """
        クリックされた位置からモンスターを特定する
        
        Args:
            mouse_x (int): マウスのX座標
            mouse_y (int): マウスのY座標
            
        Returns:
            str or None: クリックされたモンスターのID、またはモンスターでない場合はNone
        """
        # 閉じるボタンのチェック（ウィンドウの右上の×ボタン）
        close_btn_x = self.window_x + self.window_width - 15
        close_btn_y = self.window_y + 5
        
        if (close_btn_x <= mouse_x <= close_btn_x + 10 and 
            close_btn_y <= mouse_y <= close_btn_y + 10):
            return None  # 閉じるボタンがクリックされた場合はNoneを返す
            
        # モンスターカードのクリックをチェック
        available_monsters = self.get_available_monsters()
        monster_cards = []
        
        # 利用可能なモンスターのデータを取得
        for monster_id in available_monsters:
            if monster_id in self.monsters_data:
                monster_cards.append((monster_id, self.monsters_data[monster_id]))
        
        # 最大3枚まで表示（_draw_monster_window と同様に）
        monster_cards = monster_cards[:3]
        
        # カードのサイズと余白を_draw_monster_windowと同期
        card_margin = 5  # _draw_monster_windowで使用されている値と同じ
        card_width = 80  # _draw_monster_windowで使用されている値と同じ
        card_height = 120  # _draw_monster_windowで使用されている値と同じ
        
        # カードの位置を計算（_draw_monster_window と完全に同じ計算式）
        total_cards_width = len(monster_cards) * (card_width + card_margin) - card_margin
        start_x = self.window_x + (self.window_width - total_cards_width) // 2
        
        # カードのY座標（_draw_monster_window と同期）
        card_y = self.window_y + 35  # _draw_monster_window と同値
        
        # 各カードのクリックをチェック
        for i, (monster_id, monster_data) in enumerate(monster_cards):
            # カードの位置を計算
            card_left = start_x + i * (card_width + card_margin)
            card_top = card_y
            card_right = card_left + card_width
            card_bottom = card_top + card_height
            
            # デバッグ用にカードの範囲を表示
            print(f"[DEBUG] カード {monster_id} の範囲: ({card_left}, {card_top}) - ({card_right}, {card_bottom})")
            
            # カードがクリックされたかチェック
            if (card_left <= mouse_x <= card_right and 
                card_top <= mouse_y <= card_bottom):
                print(f"[DEBUG] モンスターカードがクリックされました: {monster_id}")
                return monster_id
        
        return None  # どのモンスターもクリックされなかった場合

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
            
    def _on_monster_button_click(self, monster_id):
        """
        モンスターボタンがクリックされたときの処理
        
        Args:
            monster_id (str): クリックされたモンスターのID
        """
        print(f"[DEBUG][window_system] モンスターボタンがクリックされました: {monster_id}")
        self.selected_monster = monster_id
        return ("summon_monster", monster_id)
        
    def _get_attribute_name(self, attribute):
        """属性IDを日本語名に変換する"""
        attribute_names = {
            "fire": "火",
            "water": "水",
            "wind": "風",
            "earth": "土",
            "light": "光",
            "dark": "闇",
            "none": "無"
        }
        return attribute_names.get(attribute, attribute)

    def _split_text(self, text, max_length):
        """テキストを指定された長さで改行する"""
        lines = []
        for i in range(0, len(text), max_length):
            lines.append(text[i:i+max_length])
        return lines

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
    
    def draw(self):
        """
        アクティブなウィンドウを描画
        
        このメソッドは、ゲームのメインループから呼び出され、
        現在アクティブなウィンドウがあればそれを描画します。
        """
        if self.active_window == "monster":
            self._draw_monster_window()
        elif self.active_window == "spell":
            self._draw_spell_window()