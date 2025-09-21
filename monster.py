import pyxel
import math
import random
import json
import os
from palette import  set_blend, reset_blend
from PIL import Image
import os
import pyxel
from config import (
    MONSTER_SIZE, COLLISION_DISTANCE, SCREEN_HEIGHT,
    COLOR_PLAYER_MONSTER, COLOR_ENEMY_MONSTER, COLOR_COMBAT_FLASH
)
from PIL import Image as PILImage
import io

# 画像キャッシュ用のグローバル変数
_image_cache = {}

class ImageBankManager:
    """画像バンクを管理するクラス"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._bank_usage = {}  # バンク番号 -> (monster_type, image_path)
            cls._instance._monster_banks = {}  # (monster_type, image_path) -> バンク番号
            cls._instance._bank_loaded = set()  # 読み込み済みバンク
            cls._instance._image_cache = {}  # 画像データのキャッシュ
        return cls._instance
    
    def get_bank_for_image(self, monster_type, image_path):
        """画像用のバンクを取得する"""
        # 既存のバンクを検索
        bank_key = (monster_type, image_path)
        if bank_key in self._monster_banks:
            bank = self._monster_banks[bank_key]
            if bank in self._bank_loaded:
                return bank
        
        # 新しいバンクを割り当て
        bank = self._get_available_bank()
        if bank is not None:
            self._bank_usage[bank] = bank_key
            self._monster_banks[bank_key] = bank
            return bank
        return None
    
    def _get_available_bank(self):
        """利用可能なバンクを取得する"""
        for bank in range(3):  # 0, 1, 2のバンクをチェック
            if bank not in self._bank_loaded:
                return bank
        return None

class Monster:
    """ゲーム内のモンスタークラス"""
    
    def __init__(self, x, y, is_enemy=False, monster_type="red_warrior", monster_data=None, attributes=None):
        """
        モンスターを初期化
        
        Args:
            x (int): 初期X座標
            y (int): 初期Y座標
            is_enemy (bool): 敵モンスターかどうか
            monster_type (str): モンスターの種類
            monster_data (dict): モンスターのデータ（オプション）
            attributes (dict): モンスターの属性（オプション）
        """
        # デフォルトの初期化
        self.x = x
        self.y = y
        self.is_enemy = is_enemy
        self.monster_type = monster_type
        self.alive = True
        self.in_combat = False
        self.combat_timer = 0
        self._image = None
        
        # モンスターデータを設定
        self.sprite_data = monster_data or {}
        self.attributes = attributes or {}
        
        # 基本ステータス
        self.hp = monster_data.get("hp", 10)
        self.max_hp = self.hp
        self.base_atk = monster_data.get("attack", 2)
        self._atk = self.base_atk  # 現在の攻撃力（バフ込み）
        self.speed = monster_data.get("speed", 1.0)
        self.attribute = monster_data.get("attribute", "neutral")
        self.attack_timer = 0  # 攻撃間隔を管理するタイマー
        
        # バフ/デバフ
        self.buffs = {}
        
        # モンスターごとにユニークなIDを割り当て
        if not hasattr(Monster, '_next_id'):
            Monster._next_id = 0
        self._monster_id = Monster._next_id
        Monster._next_id += 1
        
        self.alpha = 255  # 透明度（255: 不透明, 0: 完全に透明））
        
        # 画像を読み込む
        self._load_image()
        
    @property
    def atk(self):
        """攻撃力を取得するプロパティ"""
        return self._atk

    def add_floating_text(self, text, color=7, duration=30):
        """フローティングテキストを追加する
        
        Args:
            text (str): 表示するテキスト
            color (int): テキストの色（Pyxelのカラーコード）
            duration (int): 表示フレーム数
        """
        if not hasattr(self, 'floating_texts'):
            self.floating_texts = []
            
        self.floating_texts.append({
            'text': text,
            'x': self.x,
            'y': self.y,
            'color': color,
            'timer': duration,
            'vy': -0.5,  # 上方向に移動
            'alpha': 255  # 不透明度
        })
    
    def _update_floating_texts(self):
        """フローティングテキストを更新する"""
        if not hasattr(self, 'floating_texts') or not self.floating_texts:
            return
            
        # テキストを更新
        for text_info in self.floating_texts[:]:
            text_info['y'] += text_info['vy']
            text_info['timer'] -= 1
            
            # フェードアウト処理（最後の10フレームで徐々に消える）
            if text_info['timer'] < 10:
                text_info['alpha'] = int(255 * (text_info['timer'] / 10))
            
            # タイマーが切れたら削除
            if text_info['timer'] <= 0:
                self.floating_texts.remove(text_info)
    
    def _draw_floating_texts(self):
        """フローティングテキストを描画する"""
        if not hasattr(self, 'floating_texts') or not self.floating_texts:
            return
            
        for text_info in self.floating_texts:
            # テキストの幅を計算して中央揃え
            text_width = len(text_info['text']) * 4  # おおよその幅
            x = int(text_info['x'] - text_width // 2)
            y = int(text_info['y'] - 20)  # 少し上に表示
            
            # アルファブレンディングを適用
            if text_info['alpha'] < 255:
                set_blend()
            
            # テキストを描画
            pyxel.text(x, y, text_info['text'], text_info['color'])
            
            # アルファブレンディングをリセット
            if text_info['alpha'] < 255:
                reset_blend()
    
    def update(self):
        """モンスターの状態を更新"""
        if not self.alive:
            return
            
        # フローティングテキストの更新
        self._update_floating_texts()
        
        # 戦闘中でない場合、移動
        if not self.in_combat:
            if self.is_enemy:
                self.x -= 0.5 * self.speed
            else:
                self.x += 0.5 * self.speed
        
        if self.hp <= 0:
            self.alive = False

    def _update_buffs(self):
        """バフ/デバフの持続時間を更新（Bookerに移行済みのため不要）"""
        pass


    def apply_buff(self, stat, value, duration):
        """バフ/デバフを適用"""
        from game import Booker
        
        # 既存のバフを削除
        if stat in self.buffs:
            del self.buffs[stat]
        
        # 新しいバフを適用
        self.buffs[stat] = {
            'value': value,
            'duration': duration,
            'applied_at': Booker.fr  # 適用時のフレームを記録
        }
        
        # ステータスを更新
        self._update_stats()
        
        # バフの終了をスケジュール
        def remove_buff():
            if stat in self.buffs and self.buffs[stat]['applied_at'] == self.buffs[stat].get('applied_at', 0):
                del self.buffs[stat]
                self._update_stats()
                
                # バフ解除のエフェクト
                if hasattr(self, 'add_floating_text'):
                    self.add_floating_text(f"Buff ended", 12)  # 12は水色
        
        # 指定フレーム後にバフを解除
        Booker.add(self, 'x', 0, duration, 1, on_complete=remove_buff)

    def _remove_buff(self, buff_type):
        """バフを削除"""
        if buff_type in self.buffs:
            del self.buffs[buff_type]

    def _get_attack_multiplier(self, target_attribute):
        """
        属性による攻撃倍率を取得
        
        Args:
            target_attribute (str): 対象の属性
            
        Returns:
            float: 攻撃倍率(1.5: 有利, 1.0: 通常, 0.5: 不利)
        """
        if not self.attributes:
            return 1.0
            
        attr_info = self.attributes.get(self.attribute, {})
        if not attr_info:
            return 1.0
            
        if attr_info.get("strong_against") == target_attribute:
            return 1.5
        elif attr_info.get("weak_against") == target_attribute:
            return 0.5
            
        return 1.0

    def attack(self, target):
        """ターゲットに攻撃"""
        if not self.alive or not target.alive:
            return
            
        # 属性相性によるダメージ補正
        damage = self.atk
        if self.attribute == target.attribute:
            pass  # 同属性は等倍
        elif self.attribute == "fire" and target.attribute == "ice":
            damage = int(damage * 1.5)  # 有利
        elif self.attribute == "ice" and target.attribute == "fire":
            damage = int(damage * 0.5)  # 不利
            
        target.take_damage(damage, self)
        
        
        # ダメージテキストを表示
        target.add_floating_text(f"-{damage}", 8)  # 8は赤色

    def take_damage(self, amount, attacker=None):
        """
        ダメージを受ける
        
        Args:
            amount (int): 受けるダメージ量
            attacker (Monster, optional): 攻撃元のモンスター
            
        Returns:
            bool: モンスターが倒された場合はTrue、それ以外はFalse
        """
        if not self.alive:
            return False
            
        # ダメージ適用
        self.hp = max(0, self.hp - amount)
        
        # ダメージエフェクト（点滅）
        self._damage_flash = 5
        
        # ダメージテキストを表示
        if hasattr(self, 'add_floating_text'):
            self.add_floating_text(f"-{amount}", 8)  # 8は赤色
        
        # 死亡判定
        if self.hp <= 0:
            self.alive = False
            if hasattr(self, 'add_floating_text'):
                self.add_floating_text("撃破!", 8)
            return True
            
        return False
    
    def check_collision(self, other):
        """
        他のモンスターとの衝突判定
        
        Args:
            other (Monster): 衝突判定を行う相手のモンスター
            
        Returns:
            bool: 衝突しているかどうか
        """
        if not self.alive or not other.alive or self.is_enemy == other.is_enemy:
            return False
        
        # 矩形衝突判定
        return (abs(self.x - other.x) < COLLISION_DISTANCE and 
                abs(self.y - other.y) < COLLISION_DISTANCE)

    def _load_sprite_data(self):
        """スプライトデータをロードする"""
        try:
            # スプライトデータファイルのパスを取得
            sprite_file = os.path.join(os.path.dirname(__file__), 'monsters.json')
            if not os.path.exists(sprite_file):
                print(f"スプライトデータファイルが見つかりません: {sprite_file}")
                return None
                
            # JSONファイルを読み込む
            with open(sprite_file, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
                
            # モンスターのデータを取得
            all_sprites = all_data.get('monsters', {})
            
            # 現在のモンスタータイプのスプライトデータを取得
            sprite_data = all_sprites.get(self.monster_type)
            if not sprite_data:
                print(f"モンスター {self.monster_type} のスプライトデータが見つかりません")
                return None
                
            # スプライトデータをインスタンス変数に保存
            self.sprite_data = sprite_data
            return sprite_data
            
        except Exception as e:
            print(f"スプライトデータの読み込みに失敗しました: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _load_image(self):
        """モンスターの画像を読み込む"""
        try:
            print(f"画像読み込み開始: {self.monster_type}")
            
            # スプライトデータをロード
            sprite_data = self._load_sprite_data()
            if sprite_data is None:
                print(f"スプライトデータの読み込みに失敗しました: {self.monster_type}")
                return False
                
            print(f"スプライトデータ: {sprite_data}")
                
            # pyxres から画像情報を取得
            pyxres_data = sprite_data.get("pyxres", {})
            if not pyxres_data:
                print(f"pyxres データが見つかりません: {self.monster_type}")
                return False
                
            # 必要な情報を取得
            self._sprite_bank = pyxres_data.get("bank", 0)
            self._sprite_x = pyxres_data.get("start_x", 0)
            self._sprite_y = pyxres_data.get("start_y", 0)
            self._sprite_width = -sprite_data.get("sprite_width", 16) if self.is_enemy else sprite_data.get("sprite_width", 16)
            self._sprite_height = sprite_data.get("sprite_height", 16)
            
            # 初期化
            
            print(f"画像を読み込みました: bank={self._sprite_bank}, x={self._sprite_x}, y={self._sprite_y}, "
                  f"size={self._sprite_width}x{self._sprite_height}")
            return True
            
        except Exception as e:
            print(f"画像の読み込み中にエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()
            self._sprite_bank = None

    def _try_draw_sprite(self, alpha):
        """スプライトを描画する（成功したらTrueを返す）"""
        if not hasattr(self, '_sprite_bank') or self._sprite_bank is None:
            print(f"スプライトバンクが見つかりません: has_attr={hasattr(self, '_sprite_bank')}, bank={getattr(self, '_sprite_bank', None)}")
            return False
            
        try:
            # 描画位置を計算（中央揃え）
            draw_x = int(self.x - self._sprite_width // 2)
            draw_y = int(self.y - self._sprite_height // 2)

            pyxel.blt(
                draw_x, draw_y,  # 描画位置
                self._sprite_bank,  # 画像バンク
                self._sprite_x, self._sprite_y,  # スプライトの位置
                self._sprite_width, self._sprite_height,  # スプライトのサイズ
                colkey=0  # 黒を透明色として使用
            )
            
            # アルファブレンディングをリセット
            if alpha < 255:
                pyxel.blend = False
                
            # HPバーを表示（モンスターの頭上に）
            hp_ratio = max(0, min(self.hp / self.max_hp, 1.0))  # 0.0〜1.0にクランプ
            bar_width = 60  # バーの幅を固定
            bar_height = 10  # バーの高さ
            bar_x = int(self.x - bar_width // 2+(- self._sprite_width if self.is_enemy else 0))  # 中央揃え
            
            # スプライトの高さの半分を基準に、その上にHPバーを表示
            bar_y = int(self.y - self._sprite_height // 2 - 10)
            
            # 敵モンスターの場合は、スプライトの反転を考慮して位置を調整
            if self.is_enemy:
                bar_y = int(self.y - abs(self._sprite_height) // 2 - 10)

            # HPバーの背景（赤）
            pyxel.rect(bar_x, bar_y, bar_width, bar_height, 8)

            # HPバー（緑）
            current_width = max(1, int(bar_width * hp_ratio))
            pyxel.rect(bar_x, bar_y, current_width, bar_height, 11)

            # HPバーの枠
            pyxel.rectb(bar_x, bar_y, bar_width, bar_height, 7)

            # HPテキスト（白）
            hp_text = f"{self.hp}/{self.max_hp}"
            text_x = bar_x + (bar_width - len(hp_text) * 4) // 2  # 中央揃え
            text_y = bar_y + 2
            pyxel.text(text_x, text_y, hp_text, 7)
            
            # バフアイコンを表示（右上に）
            if self.buffs:
                pyxel.text(draw_x + self._sprite_width - 10, draw_y, "↑", 9)  # 黄色い上矢印
                
            return True
            
        except Exception as e:
            print(f"スプライトの描画に失敗しました: {e}")
            import traceback
            traceback.print_exc()
            self._draw_fallback(alpha)
            return False

    def _draw_fallback(self, alpha=255):
        """画像が読み込めない場合の代替描画
        
        Args:
            alpha (int): 透明度 (0-255)
        """
        try:
            # 敵か味方かで基本色を変更
            color = 8 if self.is_enemy else 9  # 敵: 赤、味方: 青
            size = 16  # モンスターの基本サイズ
            
            # モンスターの属性に応じた色
            if self.attribute == "fire":
                color = 8    # 赤
            elif self.attribute == "ice":
                color = 12   # 水色
            elif self.attribute == "nature":
                color = 11   # 緑
                
            # 戦闘中は色を点滅
            if hasattr(self, 'in_combat') and self.in_combat and (pyxel.frame_count // 4) % 2 == 0:
                color = 10  # 黄色で点滅
                
            # 点滅中は色を薄く
            if alpha < 255:
                color = 7  # グレー
            
            # アルファブレンディングを適用
            if alpha < 255:
                set_blend()
                
            # モンスターを描画（四角形）
            pyxel.rect(int(self.x - size//2), int(self.y - size//2), size, size, color)
            
            # HPバーを表示（モンスターの頭上に）
            hp_ratio = max(0, min(self.hp / self.max_hp, 1.0))  # 0.0〜1.0にクランプ
            bar_width = 40  # バーの幅
            bar_height = 10  # バーの高さ
            bar_x = int(self.x - bar_width // 2)  # 中央揃え
            
            # 敵モンスターの場合は、スプライトの反転を考慮して位置を調整
            bar_y = int(self.y - size//2 - 10)

            # HPバーの背景（赤）
            pyxel.rect(bar_x, bar_y, bar_width, bar_height, 8)

            # HPバー（緑）
            current_width = max(1, int(bar_width * hp_ratio))
            pyxel.rect(bar_x, bar_y, current_width, bar_height, 11)

            # HPバーの枠
            pyxel.rectb(bar_x, bar_y, bar_width, bar_height, 7)

            # HPテキスト（白）
            hp_text = f"{self.hp}/{self.max_hp}"
            text_x = bar_x + (bar_width - len(hp_text) * 4) // 2  # 中央揃え
            text_y = bar_y + 2
            pyxel.text(text_x, text_y, hp_text, 7)
            
            # モンスターの種類を表示（デバッグ用）
            name = self.monster_type[:3]  # 最初の3文字だけ表示
            pyxel.text(
                int(self.x - len(name) * 2),  # テキストを中央揃え
                int(self.y - 2),  # 少し上に表示
                name,
                7 if color == 0 else 0  # 背景色に応じて文字色を反転
            )
            
            # アルファブレンディングをリセット
            if alpha < 255:
                pyxel.blend = False
                
        except Exception as e:
            print(f"代替描画中にエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()

    def draw(self):
        """モンスターを描画する"""
        if not self.alive:
            return
            
        # スプライトを描画（失敗した場合はフォールバック描画）
        if not self._try_draw_sprite(self.alpha):
            self._draw_fallback(self.alpha)
            
        # フローティングテキストを描画
        self._draw_floating_texts()

    def _load_sprite_data(self):
        """スプライトデータをロードする"""
        try:
            # スプライトデータファイルのパスを取得
            sprite_file = os.path.join(os.path.dirname(__file__), 'monsters.json')
            if not os.path.exists(sprite_file):
                print(f"スプライトデータファイルが見つかりません: {sprite_file}")
                return None
                
            # JSONファイルを読み込む
            with open(sprite_file, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
                
            # モンスターのデータを取得
            all_sprites = all_data.get('monsters', {})
            
            # 現在のモンスタータイプのスプライトデータを取得
            sprite_data = all_sprites.get(self.monster_type)
            if not sprite_data:
                print(f"モンスター {self.monster_type} のスプライトデータが見つかりません")
                return None
                
            return sprite_data
            
        except Exception as e:
            print(f"スプライトデータの読み込み中にエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()
            return None
            
            # HPバーの設定
            hp_bar_width = size
            hp_bar_height = 2
            hp_ratio = max(0, min(1, self.hp / self.max_hp)) if hasattr(self, 'max_hp') and self.max_hp > 0 else 1
            hp_fill_width = max(1, int(hp_bar_width * hp_ratio))
            hp_bar_y = self.y - size // 2 - 5
            
            # HPバーの色を256色パレットから選択
            if hasattr(self, '_palette') and self._palette and len(self._palette) > 10:
                hp_color = 10 if hp_ratio > 0.5 else 8  # 緑 or 赤
            else:
                hp_color = 11 if hp_ratio > 0.5 else 8  # 緑 or 赤
            
            # モンスターを描画（四角形）
            pyxel.rect(
                int(self.x - size // 2),
                int(self.y - size // 2),
                size,
                size,
                color
            )
            
            # HPバー（背景）
            pyxel.rect(
                int(self.x - size // 2),
                hp_bar_y,
                hp_bar_width,
                hp_bar_height,
                0  # 黒
            )
            
            # HPバー（現在のHP）
            if hp_fill_width > 0:
                pyxel.rect(
                    int(self.x - size // 2),
                    hp_bar_y,
                    hp_fill_width,
                    hp_bar_height,
                    hp_color
                )
        except Exception as e:
            # エラーが発生した場合は最小限の描画のみ行う
            print(f"モンスター描画エラー: {e}")
            color = 8 if not self.is_enemy else 1
            pyxel.rect(self.x - 10, self.y - 10, 20, 20, color)
