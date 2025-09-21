import pyxel
import json
import os
from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    INITIAL_MP, MAX_MP, MP_REGEN_RATE, MAX_UNITS_PER_SIDE,
    PLAYER_SPAWN_X, ENEMY_SPAWN_X, ENEMY_SPAWN_INTERVAL, ENEMY_SPAWN_X_OFFSET,
    BASE_WIDTH, BASE_HEIGHT, ATTACK_INTERVAL,
    COLOR_TEXT, COLOR_MP
)
from monster import Monster
from window_system import WindowSystem
from witch import Witch

# Bookerクラス：値の変化を予約する
# イベント登録時：update()内でBooker.add()を使う
# Booker.add(対象インスタンス(obj), の変数名(str), 変化させたい量(int),
#   変化開始時間(単位フレーム後開始)(int), 変化に要する時間(0<int), イージング(str))
# イージングはCubicなベジェ曲線を使用(カスタマイズ可)、デフォルトは'linear'
# イベント出力時：Booker.do()をBooker.add()より後ろに記述し、毎フレーム実行する
# 配布元：https://github.com/namosuke/pyxel_class_booker
class Booker:
    books = []
    fr = 0
    
    @classmethod
    def add(cls, obj, key, value, start_time, end_time, easing = 'linear'):
        cls.books.append([
            cls.fr + start_time,
            end_time,
            key,
            value,
            0,  # 最後の差分
            easing,
            obj
        ])
    
    @classmethod
    def do(cls):
        # 逆順にアクセス
        for i in range(len(cls.books) - 1, -1, -1):
            b = cls.books[i]  # 予約情報
            if b[0] <= cls.fr:
                # デフォルトは線形補間
                diff = b[3] * (cls.fr - b[0]) / b[1]
                
                # イージング処理参考　http://nakamura001.hatenablog.com/entry/20111117/1321539246
                if b[5] == 'ease in':
                    t = (cls.fr - b[0]) / b[1]
                    diff = b[3] * t*t*t
                elif b[5] == 'ease out':
                    t = (cls.fr - b[0]) / b[1]
                    t -= 1
                    diff = b[3] * (t*t*t + 1)
                elif b[5] == 'ease in out':
                    t = (cls.fr - b[0]) / (b[1] / 2)
                    if t < 1:
                        diff = (b[3] / 2) * t*t*t
                    else:
                        t -= 2
                        diff = (b[3] / 2) * (t*t*t + 2)

                # 小数誤差を無くすため、毎回整数値を反映させている
                rounded_diff = round(diff)
                b[6].__dict__[b[2]] -= b[4]
                b[6].__dict__[b[2]] += rounded_diff
                b[4] = rounded_diff

            if b[0] + b[1] <= cls.fr:
                del cls.books[i]
                
        cls.fr += 1


class Game:
    """メインゲームクラス"""
    
    def __init__(self):
        """ゲームを初期化"""
        # 魔女の初期化（プレイヤーは炎の魔女、敵は氷の魔女）
        self.player = Witch("red_witch", is_player=True)
        self.enemy = Witch("blue_witch", is_player=False)

        # モンスターリスト
        self.monsters = []

        # 勝敗フラグ
        self.win = False
        self.lose = False
        
        # ウィンドウシステムに現在の魔女を設定
        self.window_system = WindowSystem()
        self.window_system.set_current_witch(self.player)

        # 敵召喚タイマー
        self.enemy_spawn_timer = 0

        # MPシステム
        self.player_mp = INITIAL_MP
        self.max_mp = MAX_MP
        
        # ゲーム状態
        self.paused = False
        self.casting_spell = None
        self.spell_target_mode = False
        self.long_pressed_spell = None  # 長押し中の呪文ID
        self.long_press_timer = 0  # 長押し時間を計測するタイマー
        self.showing_tooltip = False  # ツールチップ表示中フラグ

        # Pyxelを初期化
        pyxel.init(SCREEN_WIDTH, SCREEN_HEIGHT, title="Monster Battle Game")
        # 背景色を灰色に設定
        pyxel.cls(13)
        
        # マウスカーソルを表示
        pyxel.mouse(True)
        
        # BDFフォントを読み込み
        font_path = os.path.join(os.path.dirname(__file__), "asset", "umplus_j10r.bdf")
        self.font = pyxel.Font(font_path)   

        # モンスター画像を読み込む
        monsters_image_path = os.path.join(os.path.dirname(__file__), "asset", "Monsters.png")
        print(f"モンスター画像を読み込みます: {monsters_image_path}")
        # 画像バンク0にモンスター画像を読み込む
        pyxel.images[0].load(0, 0, monsters_image_path, incl_colors=True)
        
        # 魔女の画像を読み込む（バンク1に読み込む）
        witches1_path = os.path.join(os.path.dirname(__file__), "asset", "WitchesMini.png")
        print(f"魔女の画像を読み込みます: {witches1_path}")
        
        # バンク1にWitches.pngを読み込む
        if os.path.exists(witches1_path):
            pyxel.images[1].load(0, 0, witches1_path)
        else:
            print(f"警告: 魔女の画像が見つかりません: {witches1_path}")
        
        # モンスターデータを読み込み
        self.monsters_data, self.attributes = self._load_monster_data()
        
        # 呪文データを読み込み
        self.spells_data = self._load_spell_data()
        
        pyxel.run(self.update, self.draw)

    def _load_spell_data(self):
        """spell.jsonから呪文データを読み込む"""
        from config import SPELLS_JSON_PATH
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
        """monsters.jsonからモンスターデータを読み込む"""
        from config import MONSTERS_JSON_PATH
        json_path = os.path.join(os.path.dirname(__file__), MONSTERS_JSON_PATH)
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            monsters_data = data.get("monsters", {})
            attributes = data.get("attributes", {})
            print("monsters.jsonからデータを読み込みました")
            
            # モンスターデータに画像バンク情報を設定
            for monster_type in monsters_data:
                monsters_data[monster_type]["image_bank"] = 0  # デフォルトでバンク0を使用
                monsters_data[monster_type]["loaded"] = True
            
            return monsters_data, attributes

    def update(self):
        """ゲームの更新処理"""
        # ウィンドウが開いている間はゲームを一時停止
        if self.window_system.is_window_open():
            # 長押し状態をリセット
            self.long_pressed_spell = None
            self.showing_tooltip = False
            return
            
        # マウスクリックの処理
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            mouse_x, mouse_y = pyxel.mouse_x, pyxel.mouse_y
            self._handle_mouse_click(mouse_x, mouse_y)
            
        # ゲームオーバーチェック
        if self.win or self.lose:
            return
        
        # マウス入力は一時停止に関係なく処理
        # マウスクリックはpyxel.btnpで既に処理されているため、ここでは処理不要
        
        # MPを回復
        if self.player_mp < self.max_mp:
            self.player_mp = min(self.max_mp, self.player_mp + MP_REGEN_RATE)
        
        # 敵の自動召喚
        if pyxel.frame_count % ENEMY_SPAWN_INTERVAL == 0 and self._count_enemy_units() < MAX_UNITS_PER_SIDE:
            self._spawn_enemy_monster()
        
        # 各モンスターの更新
        for monster in self.monsters[:]:
            monster.update()
            
            # 攻撃可能な場合、最も近い敵を攻撃
            if monster.attack_timer <= 0:
                target = self._find_nearest_enemy(monster)
                if target:
                    monster.attack(target)
                    monster.attack_timer = ATTACK_INTERVAL
            else:
                monster.attack_timer -= 1
            
            # 死亡判定
            if monster.hp <= 0:
                self.monsters.remove(monster)
        
        # 魔女のHPチェック
        if self.player.current_hp <= 0:
            self.lose = True
        elif self.enemy.current_hp <= 0:
            self.win = True

    def _check_long_press(self, mouse_x, mouse_y):
        """長押しを検出して対応する呪文IDを返す"""
        # マウスがUIボタンエリア外の場合は何もしない
        if mouse_y < SCREEN_HEIGHT - 50:
            return None
            
        # 現在の魔女が使用できる呪文を取得
        current_witch = self.window_system.current_witch or self.player
        available_spells = current_witch.get_available_spells()
        
        # ボタンのサイズと間隔
        button_width = 70
        button_height = 30
        button_margin = 8
        total_width = (button_width * 3) + (button_margin * 2)
        start_x = (SCREEN_WIDTH - total_width) // 2
        button_y = SCREEN_HEIGHT - button_height - 10
        
        # 各ボタンの上にマウス/タッチがあるかチェック
        for i, spell_id in enumerate(available_spells):
            if i >= 3:  # 最大3つのボタンのみ表示
                break
                
            x = start_x + i * (button_width + button_margin)
            
            # ボタンの上にマウス/タッチがあるかチェック
            if (x <= mouse_x <= x + button_width and 
                button_y <= mouse_y <= button_y + button_height):
                return spell_id
        
        return None

    def _handle_mouse_click(self, mouse_x, mouse_y):
        """マウスクリックの処理"""
        print(f"\n[DEBUG] クリックイベント: ({mouse_x}, {mouse_y})")
        
        # 呪文の対象選択モード中の場合
        if self.spell_target_mode:
            print("[DEBUG] 呪文の対象選択モード中")
            self._handle_spell_target_selection(mouse_x, mouse_y)
            return
        
        # ウィンドウが開いている場合は、ウィンドウのクリック処理を優先
        if self.window_system.is_window_open():
            print(f"[DEBUG] ウィンドウが開いています。クリック位置: ({mouse_x}, {mouse_y})")
            print(f"[DEBUG] ウィンドウの範囲: x={self.window_system.window_x}-{self.window_system.window_x + self.window_system.window_width}, y={self.window_system.window_y}-{self.window_system.window_y + self.window_system.window_height}")
            
            # ウィンドウの外側をクリックしたかチェック
            if not (self.window_system.window_x <= mouse_x < self.window_system.window_x + self.window_system.window_width and
                    self.window_system.window_y <= mouse_y < self.window_system.window_y + self.window_system.window_height):
                print("[DEBUG] ウィンドウの外側をクリックしました")
            
            result = self.window_system.handle_click(mouse_x, mouse_y)
            print(f"[DEBUG] handle_click の結果: {result}")
            
            if result:
                action_type, data = result
                print(f"[DEBUG] アクションタイプ: {action_type}, データ: {data}")
                
                if action_type == "summon_monster" and data:
                    print(f"[DEBUG] モンスター召喚を試みます: {data}")
                    if self._try_summon_monster_from_window(data, mouse_x, mouse_y):
                        print("[DEBUG] モンスター召喚に成功しました。ウィンドウを閉じます。")
                        self.window_system.close_window()
                    else:
                        print("[DEBUG] モンスター召喚に失敗しました。")
                elif action_type == "close":
                    print("[DEBUG] ウィンドウを閉じます。")
                    self.window_system.close_window()
            
            # ウィンドウがまだ開いているか確認
            if self.window_system.is_window_open():
                print("[DEBUG] ウィンドウがまだ開いているため、他の処理をスキップします。")
                return
            else:
                print("[DEBUG] ウィンドウは閉じられました。通常のクリック処理に進みます。")
        
        print(f"[DEBUG] 通常のクリック処理: ({mouse_x}, {mouse_y})")
        
        # 魔女をクリックしたかチェック
        if self._is_click_on_witch(mouse_x, mouse_y, self.player):
            print("[DEBUG] 魔女がクリックされました。モンスターウィンドウを開きます。")
            self.window_system.open_monster_window()
            return

        # 使用可能な呪文を取得
        current_witch = self.window_system.current_witch or self.player
        available_spells = current_witch.get_available_spells()
        
        # ボタンのサイズと間隔
        button_width = 70
        button_height = 30
        button_margin = 8
        total_width = (button_width * 3) + (button_margin * 2)
        start_x = (SCREEN_WIDTH - total_width) // 2
        button_y = SCREEN_HEIGHT - button_height - 10
        
        # 各呪文ボタンの描画とクリック判定
        for i, spell_id in enumerate(available_spells):
            if i >= 3:  # 最大3つのボタンのみ表示
                break
                
            x = start_x + i * (button_width + button_margin)
            
            # ボタンの背景色（MPが足りるかどうかで色を変更）
            spell_data = self.spells_data.get(spell_id, {})
            can_cast = self.player_mp >= spell_data.get("cost", 0)
            button_color = 1 if can_cast else 8
            
            # ボタンが選択されている場合は色を変える
            if self.spell_target_mode and self.casting_spell == spell_id:
                button_color = 3 if can_cast else 10
            
            # ボタンの背景
            pyxel.rect(x, button_y, button_width, button_height, button_color)
            pyxel.rectb(x, button_y, button_width, button_height, 7)
            
            # 呪文名（中央揃え）
            spell_name = spell_data.get("name", "呪文")
            name_width = self.font.text_width(spell_name)
            name_x = x + (button_width - name_width) // 2
            pyxel.text(name_x, button_y + 5, spell_name, 7, self.font)
            
            # MPコスト（中央揃え）
            cost_text = f"MP: {spell_data.get('cost', 0)}"
            cost_width = self.font.text_width(cost_text)
            cost_x = x + (button_width - cost_width) // 2
            pyxel.text(cost_x, button_y + 15, cost_text, 7, self.font)
            
            # ボタンがクリックされたかチェック
            if self._is_click_on_button(mouse_x, mouse_y, x, button_y, button_width, button_height):
                if spell_data:
                    # MPチェック
                    if can_cast:
                        # 範囲攻撃呪文の場合は直接発動
                        if spell_data.get("target") == "area":
                            self._cast_area_spell(spell_data)
                        # 単体対象呪文の場合は対象選択モードに
                        else:
                            self.casting_spell = spell_id
                            self.spell_target_mode = True
                    else:
                        print("MPが足りません")
                    break
            
            # 戦場クリック（呪文対象選択用）
            if mouse_y < SCREEN_HEIGHT - 30:
                if self.spell_target_mode and self.casting_spell:
                    self._handle_spell_target_selection(mouse_x, mouse_y)

    def _is_click_on_witch(self, mouse_x, mouse_y, witch):
        """魔女の画像がクリックされたかどうかを判定"""
        # 魔女の画像サイズ（適宜調整してください）
        witch_width = 64
        witch_height = 64
        
        # 魔女の位置（Witchクラスのdrawメソッドに依存）
        witch_x = witch.x
        witch_y = witch.y
        
        # クリックされた位置が魔女の画像内かどうかを判定
        return (witch_x <= mouse_x <= witch_x + witch_width and 
                witch_y <= mouse_y <= witch_y + witch_height)

    def _is_click_on_button(self, mouse_x, mouse_y, button_x, button_y, width, height):
        """マウスクリックがボタン上かどうかを判定"""
        return (button_x <= mouse_x <= button_x + width and 
                button_y <= mouse_y <= button_y + height)

    def _handle_button_click(self, mouse_x, mouse_y):
        """ボタンクリック処理"""
        # ウィンドウが開いている場合は、ウィンドウのクリック処理を優先
        if self.window_system.is_window_open():
            result = self.window_system.handle_click(mouse_x, mouse_y)
            if result:
                action_type, data = result
                if action_type == "summon_monster":
                    self._try_summon_monster_from_window(data, mouse_x, mouse_y)
                elif action_type == "close":
                    self.window_system.close_window()
            return
        
        # 魔女をクリックしたかチェック
        if self._is_click_on_witch(mouse_x, mouse_y, self.player):
            self.window_system.open_monster_window()
            return

        # 使用可能な呪文を取得
        current_witch = self.window_system.current_witch or self.player
        available_spells = current_witch.get_available_spells()
        
        # ボタンのサイズと間隔
        button_width = 70
        button_height = 30
        button_margin = 8
        total_width = (button_width * 3) + (button_margin * 2)
        start_x = (SCREEN_WIDTH - total_width) // 2
        button_y = SCREEN_HEIGHT - button_height - 10
        
        # 各呪文ボタンのクリックをチェック
        for i, spell_id in enumerate(available_spells):
            if i >= 3:  # 最大3つのボタンのみ表示
                break
                
            x = start_x + i * (button_width + button_margin)
            
            # ボタンがクリックされたかチェック
            if self._is_click_on_button(mouse_x, mouse_y, x, button_y, button_width, button_height):
                spell_data = self.spells_data.get(spell_id)
                if spell_data:
                    # MPチェック
                    if self.player_mp >= spell_data.get("cost", 0):
                        # 範囲攻撃呪文の場合は直接発動
                        if spell_data.get("target") == "area":
                            self._cast_area_spell(spell_data)
                        # 単体対象呪文の場合は対象選択モードに
                        else:
                            self.casting_spell = spell_id
                            self.spell_target_mode = True
                    else:
                        print("MPが足りません")
                break
            
        # 戦場クリック（呪文対象選択用）
        if mouse_y < SCREEN_HEIGHT - 30:
            if self.spell_target_mode and self.casting_spell:
                self._handle_spell_target_selection(mouse_x, mouse_y)

    def _try_summon_monster_from_window(self, monster_type, mouse_x, mouse_y):
        """ウィンドウからモンスター召喚を試行"""
        try:
            # 現在の魔女を取得
            current_witch = self.window_system.current_witch or self.player
            
            # 魔女がこのモンスターを召喚できるかチェック
            available_monsters = current_witch.get_available_monsters()
            if monster_type not in available_monsters:
                print(f"この魔女は{monster_type}を召喚できません")
                return False
                
            # モンスターのデータを取得
            monster_data = self.monsters_data.get(monster_type)
            if not monster_data:
                print(f"モンスターのデータが見つかりません: {monster_type}")
                return False
                
            # MPチェック
            cost = monster_data.get("cost", 1)
            if self.player_mp < cost:
                print("MPが足りません")
                return False
            
            # 同時出撃数チェック
            player_units = len([m for m in self.monsters if not m.is_enemy])
            if player_units >= MAX_UNITS_PER_SIDE:
                print("ユニットの最大数に達しています")
                return False
            
            # モンスターの基本データをコピーして、スプライト情報を追加
            monster_info = monster_data.copy()
            monster_info["image_bank"] = monster_data.get("image_bank", 0)
            monster_info["loaded"] = monster_data.get("loaded", False)
            
            # モンスターの画像サイズを取得（デフォルトは16x16）
            sprite_width = monster_info.get("sprite_width", 16)
            sprite_height = monster_info.get("sprite_height", 16)
            
            # モンスターを画面中央に配置（Y座標を調整）
            spawn_y = (SCREEN_HEIGHT - sprite_height) // 2
            monster = Monster(
                x=PLAYER_SPAWN_X, 
                y=spawn_y,
                is_enemy=False,  # プレイヤー側
                monster_type=monster_type,
                monster_data=monster_info,
                attributes=self.attributes
            )
            
            self.monsters.append(monster)
            self.player_mp -= cost
            print(f"{current_witch.data['name']}が{monster_type}を召喚しました (MP: -{cost})")
            return True
            
        except Exception as e:
            print(f"モンスターの召喚中にエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _handle_spell_target_selection(self, mouse_x, mouse_y):
        """呪文の対象選択処理"""
        if not self.casting_spell:
            self.spell_target_mode = False
            return False
            
        # 呪文データを取得
        spell_data = self.spells_data.get(self.casting_spell)
        if not spell_data:
            self.spell_target_mode = False
            return False
        
        # 対象タイプを取得
        target_type = spell_data.get("target")
        
        # 対象モンスターを探す
        target_monster = None
        for monster in self.monsters:
            if not monster.alive:
                continue
            
            # モンスターの当たり判定（画像サイズに基づく）
            monster_width = monster.sprite_data.get("sprite_width", 32) if hasattr(monster, 'sprite_data') else 32
            monster_height = monster.sprite_data.get("sprite_height", 32) if hasattr(monster, 'sprite_data') else 32
            
            # モンスターの中心座標を計算
            monster_center_x = monster.x + monster_width // 2
            monster_center_y = monster.y + monster_height // 2
            
            # クリック判定範囲（モンスターのサイズに基づく）
            click_radius = max(monster_width, monster_height) // 2
            
            # クリック位置がモンスターの範囲内かチェック
            distance_sq = (mouse_x - monster_center_x) ** 2 + (mouse_y - monster_center_y) ** 2
            
            if distance_sq <= click_radius ** 2:
                # 対象タイプに応じたチェック
                if target_type == "single_ally" and not monster.is_enemy:
                    target_monster = monster
                    break
                elif target_type == "single_enemy" and monster.is_enemy:
                    target_monster = monster
                    break
                elif target_type == "any" and (monster.is_enemy or not monster.is_enemy):
                    target_monster = monster
                    break
    
        # 対象が見つかった場合
        if target_monster:
            # MPを消費
            spell_cost = spell_data.get("cost", 0)
            if self.player_mp >= spell_cost:
                # 呪文を発動
                self._cast_single_spell(spell_data, target_monster)
                self.player_mp -= spell_cost
                print(f"{spell_data.get('name')}を{target_monster.name}に発動しました！ (MP: -{spell_cost})")
                
                # エフェクト表示（必要に応じて実装）
                if hasattr(target_monster, 'show_effect'):
                    effect_text = spell_data.get('effect_text', '')
                    if effect_text:
                        target_monster.show_effect(effect_text, pyxel.COLOR_WHITE)
            else:
                print(f"MPが足りません！ (必要MP: {spell_cost}, 現在MP: {self.player_mp})")
        
        # 対象選択モードを終了
        self.casting_spell = None
        self.spell_target_mode = False
        
        # ウィンドウを閉じる
        self.window_system.close_window()
        
        return target_monster is not None

    def _cast_single_spell(self, spell_data, target_monster):
        """単体対象呪文を発動
        
        Args:
            spell_data (dict): 発動する呪文のデータ
            target_monster (Monster): 対象のモンスター
        """
        current_witch = self.window_system.current_witch or self.player
        
        # 呪文の効果を適用
        effect = spell_data.get("effect")
        value = spell_data.get("value", 0)
        
        # 呪文名を取得（デバッグ用）
        spell_name = spell_data.get('name', '未知の呪文')
        # モンスターの名前を取得（sprite_dataがあればそれを使用、なければmonster_typeを使用）
        monster_name = target_monster.sprite_data.get('name', target_monster.monster_type)
        print(f"{current_witch.data['name']}が{spell_name}を{monster_name}に発動しました")
        
        # エフェクトカラー（デフォルトは白）
        effect_color = spell_data.get('color', pyxel.COLOR_WHITE)
        
        try:
            if effect == "heal":
                # 回復呪文
                original_hp = target_monster.hp
                target_monster.hp = min(target_monster.max_hp, target_monster.hp + value)
                heal_amount = target_monster.hp - original_hp
                
                if heal_amount > 0:
                    print(f"{target_monster.name}のHPが{heal_amount}回復しました (HP: {target_monster.hp}/{target_monster.max_hp})")
                    
                    # 回復エフェクト（緑色の数字）
                    if hasattr(target_monster, 'show_effect'):
                        target_monster.show_effect(f"+{heal_amount}", pyxel.COLOR_GREEN)
                
            elif effect == "damage":
                # ダメージ呪文
                damage = max(1, value - target_monster.defense // 2)
                target_monster.take_damage(damage)
                print(f"{target_monster.name}に{damage}のダメージ！ (HP: {target_monster.hp}/{target_monster.max_hp})")
                
                # ダメージエフェクト（赤色の数字）
                if hasattr(target_monster, 'show_effect'):
                    target_monster.show_effect(f"-{damage}", pyxel.COLOR_RED)
                
            elif effect == "buff_attack":
                # 攻撃力上昇バフ
                target_monster.attack_power += value
                print(f"{target_monster.name}の攻撃力が{value}上がった！ (攻撃力: {target_monster.attack_power})")
                
                # バフエフェクト（黄色の数字）
                if hasattr(target_monster, 'show_effect'):
                    target_monster.show_effect(f"攻撃力+{value}", pyxel.COLOR_YELLOW)
                    
            elif effect == "buff_defense":
                # 防御力上昇バフ
                target_monster.defense += value
                print(f"{target_monster.name}の防御力が{value}上がった！ (防御力: {target_monster.defense})")
                
                # バフエフェクト（水色の数字）
                if hasattr(target_monster, 'show_effect'):
                    target_monster.show_effect(f"防御力+{value}", pyxel.COLOR_LIGHT_BLUE)
            
            else:
                print(f"未知の効果: {effect}")
                
            # エフェクトアニメーション用のフラグを設定
            if hasattr(target_monster, 'effect_timer'):
                target_monster.effect_timer = 30  # 30フレーム表示
                
        except Exception as e:
            print(f"呪文発動中にエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()
                    
            # バフアニメーション（緑色で点滅）
            if hasattr(target_monster, 'flash'):
                target_monster.flash(11, 10)  # 緑色で10フレーム点滅
    
    def _cast_area_spell(self, spell_data):
        """範囲攻撃呪文を発動"""
        if spell_data["effect"] == "damage":
            # 敵全体にダメージ（アニメーション付き）
            for i, monster in enumerate(self.monsters):
                if monster.alive and monster.is_enemy:
                    # 少しずつ遅らせてダメージを与える（波のように広がるエフェクト）
                    delay = i * 2  # モンスターごとに2フレーム遅らせる
                    
                    # ダメージアニメーション（赤く点滅）
                    original_color = getattr(monster, 'flash_color', None)
                    monster.flash_color = 8  # 赤色
                    
                    # 0.1秒後に元の色に戻す
                    def reset_color(m):
                        m.flash_color = original_color
                    
                    # ダメージは少し遅らせて適用（アニメーションと同期）
                    def apply_damage(m, dmg):
                        m.hp -= dmg
                        # ダメージテキスト表示
                        if hasattr(m, 'add_floating_text'):
                            m.add_floating_text(f"-{dmg}", 8)  # 8は赤色
                    
                    # アニメーションをスケジュール
                    Booker.add(monster, 'flash_color', 0, delay, 6)  # 点滅開始
                    
                    # ダメージ適用（アニメーションと同期）
                    import types
                    delayed_damage = types.MethodType(lambda self: apply_damage(monster, spell_data["value"]), self)
                    setattr(self, f'_delayed_damage_{id(monster)}', delayed_damage)
                    
                    # 色を元に戻す
                    if original_color is not None:
                        Booker.add(monster, 'flash_color', original_color - 8, 6, 6)  # 点滅終了

    def _spawn_enemy_monster(self):
        """敵モンスターの自動召喚"""
        # ランダムな敵モンスターを選択
        import random
        available_monsters = [m for m in self.monsters_data.keys() 
                           if self.monsters_data[m].get("enemy_available", True)]
        
        if not available_monsters:
            available_monsters = list(self.monsters_data.keys())
        
        if not available_monsters:  # モンスターが1つもいない場合
            return
            
        monster_type = random.choice(available_monsters)
        monster_data = self.monsters_data[monster_type]
        
        # モンスターの基本データをコピーして、スプライト情報を追加
        monster_info = monster_data.copy()
        
        # スプライトデータを設定
        sprite_data = {
            "image_bank": monster_data.get("image_bank", 0),
            "image_file": monster_data.get("image_file"),
            "sprite_width": monster_data.get("sprite_width", 64),
            "sprite_height": monster_data.get("sprite_height", 64),
            "loaded": monster_data.get("loaded", False)
        }
        monster_info["sprite_data"] = sprite_data
        
        # モンスターの画像サイズを取得（デフォルトは64x64）
        sprite_height = sprite_data["sprite_height"]
        
        # 敵モンスターを画面中央に配置（Y座標を調整）
        spawn_x = SCREEN_WIDTH - ENEMY_SPAWN_X_OFFSET
        spawn_y = (SCREEN_HEIGHT - sprite_height) // 2
        
        monster = Monster(
            x=spawn_x,
            y=spawn_y,
            is_enemy=True,
            monster_type=monster_type,
            monster_data=monster_info,
            attributes=self.attributes
        )
        
        # 出現アニメーション（フェードイン）
        monster.alpha = 0
        Booker.add(monster, 'alpha', 255, 0, 30, 'ease_out')
        
        self.monsters.append(monster)
        print(f"敵モンスターが出現: {monster_type}")

    def _find_nearest_enemy(self, monster):
        """最も近い敵モンスターを探す"""
        nearest_enemy = None
        min_distance = float('inf')
        
        for m in self.monsters:
            if m.alive and m.is_enemy != monster.is_enemy:
                distance = ((m.x - monster.x) ** 2 + (m.y - monster.y) ** 2) ** 0.5
                if distance < min_distance:
                    min_distance = distance
                    nearest_enemy = m
        
        return nearest_enemy

    def _count_enemy_units(self):
        """敵ユニット数を数える"""
        return len([m for m in self.monsters if m.alive and m.is_enemy])

    def draw(self):
        """ゲームの描画処理"""
        # 画面全体をクリア（色13: 薄いグレー）
        pyxel.cls(13)
        
        # 魔女の描画
        self.player.draw(PLAYER_SPAWN_X, SCREEN_HEIGHT-100)
        self.enemy.draw(ENEMY_SPAWN_X, SCREEN_HEIGHT - 100)

        # 魔女の上にHPを表示
        self._draw_witch_hp(self.player, PLAYER_SPAWN_X, SCREEN_HEIGHT - 110)
        self._draw_witch_hp(self.enemy, ENEMY_SPAWN_X, SCREEN_HEIGHT - 110)    
        # MPバーの描画
        self._draw_mp_bar(SCREEN_WIDTH // 2 - 50, 10, self.player_mp, self.max_mp)
        
        # モンスターの描画
        for monster in self.monsters:
            monster.draw()
              
        # UIボタンの描画
        self._draw_ui_buttons()  
        # ウィンドウの描画
        self.window_system.draw()

        

        
        # 呪文対象選択モードの場合はメッセージを表示（_draw_ui_buttonsで既に表示しているためコメントアウト）
        # if self.spell_target_mode and self.casting_spell:
        #     spell_data = self.spells_data.get(self.casting_spell, {})
        #     if spell_data:
        #         spell_name = spell_data.get("name", "呪文")
        #         text = f"{spell_name}の対象を選択"
        #         pyxel.text(SCREEN_WIDTH // 2 - len(text) * 2, 30, text, COLOR_TEXT)
        
        # 勝敗メッセージの表示
        if self.win:
            self._draw_centered_text("勝利！", 8)
        elif self.lose:
            self._draw_centered_text("敗北...", 8)
            
    def _draw_witch_hp(self, witch, x, y):
        """魔女のHPを表示"""
        # HPバーのサイズ
        bar_width = 60
        bar_height = 10
        
        # HPバーの背景（赤）
        pyxel.rect(x, y, bar_width, bar_height, 8)
        
        # 現在のHPに応じたバーの長さを計算
        hp_ratio = witch.current_hp / witch.max_hp
        current_width = max(1, int(bar_width * hp_ratio))
        
        # HPバー（緑）
        pyxel.rect(x, y, current_width, bar_height, 11)
        
        # 枠線
        pyxel.rectb(x, y, bar_width, bar_height, 7)
        
        # HPテキスト（白）
        hp_text = f"{witch.current_hp}/{witch.max_hp}"
        text_x = x + (bar_width - len(hp_text) * 4) // 2  # 中央揃え
        text_y = y + 2
        pyxel.text(text_x, text_y, hp_text, 7)

    def _draw_spell_tooltip(self, spell_id, x, y):
        """呪文のツールチップを描画"""
        spell_data = self.spells_data.get(spell_id, {})
        if not spell_data:
            return
            
        # ツールチップの内容
        name = spell_data.get('name', '未知の呪文')
        cost = spell_data.get('cost', 0)
        effect = spell_data.get('effect', '')
        description = spell_data.get('description', '説明がありません')
        
        # テキストを整形
        lines = [
            f"{name} (MP: {cost})",
            "",
            f"効果: {effect}",
            "",
        ]
        
        # 説明文を改行
        max_chars = 30
        for i in range(0, len(description), max_chars):
            lines.append(description[i:i+max_chars])
        
        # ツールチップのサイズを計算
        max_width = max(self.font.text_width(line) for line in lines)
        line_height = 8
        padding = 5
        width = max_width + padding * 2
        height = len(lines) * line_height + padding * 2
        
        # ボタンの下に表示
        tooltip_x = max(5, min(x, SCREEN_WIDTH - width - 5))  # 画面外にはみ出さないように
        tooltip_y = y - height - 5  # ボタンの上に表示
        
        # ツールチップの背景と枠
        pyxel.rect(tooltip_x, tooltip_y, width, height, 1)
        pyxel.rectb(tooltip_x, tooltip_y, width, height, 7)
        
        # テキストを描画
        for i, line in enumerate(lines):
            pyxel.text(tooltip_x + padding, tooltip_y + padding + i * line_height, line, 7, self.font)

    def _draw_ui_buttons(self):
        """UIボタンの描画"""
        # 呪文対象選択モードの表示
        if self.spell_target_mode and self.casting_spell:
            # 画面上部に指示を表示
            spell_name = self.casting_spell  # 文字列の呪文名を取得
            spell_data = self.spells_data.get(spell_name, {})
            if spell_data:
                instruction = f"{spell_data.get('name', '呪文')}の対象を選択してください"
                text_width = self.font.text_width(instruction)
                text_x = (SCREEN_WIDTH - text_width) // 2
                pyxel.rect(text_x - 5, 35, text_width + 10, 12, 1)
                pyxel.rectb(text_x - 5, 35, text_width + 10, 12, 7)
                pyxel.text(text_x, 40, instruction, 7, self.font)
        
        # 使用可能なスペルを画面下にボタンとして表示
        current_witch = self.window_system.current_witch or self.player
        available_spells = current_witch.get_available_spells()
        
        # ボタンのサイズと間隔
        button_width = 70
        button_height = 30
        button_margin = 8
        total_width = (button_width * 3) + (button_margin * 2)
        start_x = (SCREEN_WIDTH - total_width) // 2
        button_y = SCREEN_HEIGHT - button_height - 10
        
        for i, spell_id in enumerate(available_spells):
            if i >= 3:  # 最大3つのボタンのみ表示
                break
                
            spell_data = self.spells_data.get(spell_id, {})
            if not spell_data:
                continue
                
            x = start_x + i * (button_width + button_margin)
            
            # ボタンの背景（MPが足りるかどうかで色を変更）
            button_color = 1 if self.player_mp >= spell_data.get("cost", 0) else 8
            pyxel.rect(x, button_y, button_width, button_height, button_color)
            
            # ボタンの枠
            pyxel.rectb(x, button_y, button_width, button_height, 7)
            
            # 呪文名（中央揃え）
            spell_name = spell_data.get("name", "呪文")
            name_width = self.font.text_width(spell_name)
            name_x = x + (button_width - name_width) // 2
            pyxel.text(name_x, button_y + 5, spell_name, 7, self.font)
            
            # MPコスト（中央揃え）
            cost_text = f"MP: {spell_data.get('cost', 0)}"
            cost_width = self.font.text_width(cost_text)
            cost_x = x + (button_width - cost_width) // 2
            pyxel.text(cost_x, button_y + 15, cost_text, 7, self.font)

    def _draw_mp_bar(self, x, y, current_mp, max_mp):
        """MPバーを描画する
        
        Args:
            x (int): バーのX座標
            y (int): バーのY座標
            current_mp (int): 現在のMP
            max_mp (int): 最大MP
        """
        # バーのサイズ
        bar_width = 100
        bar_height = 10
        
        # バーの枠を描画
        pyxel.rectb(x, y, bar_width, bar_height, 7)  # 枠線（白）
        
        # MPの割合に応じてバーの長さを計算
        if max_mp > 0:
            fill_width = int((current_mp / max_mp) * (bar_width - 2))
            fill_width = max(0, min(fill_width, bar_width - 2))  # 0からbar_width-2の範囲に収める
            
            # MPの割合に応じて色を変更（青から赤に変化）
            if current_mp > max_mp * 0.7:
                color = 12  # 青
            elif current_mp > max_mp * 0.3:
                color = 5   # 紫
            else:
                color = 8   # 赤
                
            # バーを描画
            pyxel.rect(x + 1, y + 1, fill_width, bar_height - 2, color)
            
            # MPの数値を表示
            mp_text = f"MP: {int(current_mp)}/{max_mp}"
            text_x = x + (bar_width - len(mp_text) * 4) // 2  # 中央揃え
            pyxel.text(text_x, y + 2, mp_text, 7)  # 白文字

    def _draw_game_result(self):
        """勝敗メッセージの描画"""
        if self.win:
            text = "勝利！"
            color = 11  # シアン
        elif self.lose:
            text = "敗北..."
            color = 8  # 赤
        else:
            return
            
        # メッセージを中央に表示
        text_width = len(text) * 4  # 1文字4ピクセルと仮定
        pyxel.rect(SCREEN_WIDTH // 2 - text_width - 10, 50, text_width + 20, 20, 0)
        pyxel.rectb(SCREEN_WIDTH // 2 - text_width - 10, 50, text_width + 20, 20, 7)
        pyxel.text(SCREEN_WIDTH // 2 - text_width // 2, 57, text, color)        

    def _draw_ui(self):
        """UIを描画"""
        # ウィンドウを先に描画（背景として）
        self.window_system.draw()
        
        # HPバーとMPバーを後から描画（前面に表示）
        pyxel.rect(12, 12, int(100 * (self.player_mp / self.max_mp)), 12, 11)
        pyxel.text(15, 14, f"MP: {int(self.player_mp)}/{self.max_mp}", 0)  # テキストを黒色に変更
        
        # 敵のMP表示
        #pyxel.rect(SCREEN_WIDTH - 114, 10, 104, 16, 7)  # 背景を灰色に変更
        #pyxel.rect(SCREEN_WIDTH - 112, 12, int(100 * (self.enemy_mp / self.max_mp)), 12, 11)
        #pyxel.text(SCREEN_WIDTH - 109, 14, f"MP: {int(self.enemy_mp)}/{self.max_mp}", 0)  # テキストを黒色に変更
        
        # 使用可能なSpellボタンは_draw_ui_buttonsで描画
