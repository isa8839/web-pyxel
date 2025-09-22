import pyxel

def _get_text_width(text):
    """テキストの描画幅をピクセル単位で計算する
    
    Args:
        text (str): 幅を計算するテキスト
        
    Returns:
        int: テキストの幅（ピクセル）
    """
    if not text:
        return 0
        
    # 半角文字は6ピクセル、全角文字は10ピクセル（umplus_j10r.bdfの実際の幅に基づく）
    # 文字間隔は1ピクセル
    width = 0
    for i, char in enumerate(text):
        # 最初の文字以外は文字間隔を追加
        if i > 0:
            width += 1
            
        # 文字の幅を追加（半角・全角で分岐）
        if ord(char) < 128:  # 半角文字
            width += 6
        else:  # 全角文字
            width += 10
            
    return width

class Button:
    def __init__(self, x, y, w, h, text, onclick, 
                 col=7, bg_col=1, border_col=6, 
                 hover_col=None, active_col=None, disabled=False, font=None):
        """
        x, y : 左上の座標
        w, h : ボタンの幅と高さ
        text : ボタンに表示する文字列
        onclick : クリック時に実行する関数
        col : 文字の色
        bg_col : 背景色
        border_col : 枠線の色
        hover_col : ホバー時の背景色（Noneの場合は自動調整）
        active_col : 押下時の背景色（Noneの場合は自動調整）
        disabled : 無効状態かどうか
        font : 使用するフォントオブジェクト（Noneの場合はデフォルトのテキスト描画を使用）
        """
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.text = text
        self.onclick = onclick
        self.col = col
        self.bg_col = bg_col
        self.border_col = border_col
        self.hover_col = hover_col if hover_col is not None else min(15, bg_col + 2)
        self.active_col = active_col if active_col is not None else max(0, bg_col - 2)
        self.disabled = disabled
        self.hover = False
        self.pressed = False
        self._last_click_time = 0
        self._click_cooldown = 15  # クリック間のクールダウン（フレーム数）
        self.font = font  # フォントオブジェクトを保持

    def draw(self):
        """ボタンを描画"""
        if self.disabled:
            # 無効状態
            bg_col = 13  # 灰色
            border_col = 5  # 暗い灰色
            text_col = 5  # 暗い灰色
        elif self.pressed:
            # 押下時
            bg_col = self.active_col
            border_col = max(0, self.border_col - 2)
            text_col = self.col
        elif self.hover:
            # ホバー時
            bg_col = self.hover_col
            border_col = min(15, self.border_col + 2)
            text_col = self.col
        else:
            # 通常時
            bg_col = self.bg_col
            border_col = self.border_col
            text_col = self.col
        
        # 背景
        pyxel.rect(self.x, self.y, self.w, self.h, bg_col)
        # 枠線
        pyxel.rectb(self.x, self.y, self.w, self.h, border_col)
        
        # テキストを行ごとに分割
        lines = self.text.split('\n')
        line_height = 8  # 行の高さ
        total_height = len(lines) * line_height
        start_y = self.y + (self.h - total_height) // 2
        
        # 各行を中央揃えで描画
        for i, line in enumerate(lines):
            # テキストの幅を正確に計算
            text_w = _get_text_width(line)
            text_x = self.x + (self.w - text_w) // 2
            text_y = start_y + i * (line_height+2)
            pyxel.text(text_x, text_y, line, text_col,font=self.font)
            
        # デバッグ用：ボタンの範囲を表示（必要に応じてコメントアウト）
        #pyxel.rectb(self.x, self.y, self.w, self.h, 8)

    def update(self, mouse_x, mouse_y, mouse_pressed):
        """ボタンの状態を更新
        
        Args:
            mouse_x: マウスのX座標
            mouse_y: マウスのY座標
            mouse_pressed: マウスボタンが押されているか
            
        Returns:
            bool: クリックされたかどうか
        """
        if self.disabled:
            self.hover = False
            self.pressed = False
            return False
            
        # 前回のクリックから十分な時間が経過しているか確認
        current_time = pyxel.frame_count
        can_click = (current_time - self._last_click_time) >= self._click_cooldown
        
        # ホバー状態を更新
        self.hover = (self.x <= mouse_x < self.x + self.w and
                     self.y <= mouse_y < self.y + self.h)
        
        # クリック状態を更新
        if self.hover and mouse_pressed and can_click:
            if not self.pressed:  # 押下開始時のみ実行
                self.pressed = True
                self._last_click_time = current_time
                if self.onclick:
                    self.onclick()
                return True
        else:
            self.pressed = False
            
        return False
        
    def set_disabled(self, disabled):
        """ボタンの無効状態を設定
        
        Args:
            disabled (bool): 無効にするかどうか
        """
        self.disabled = disabled
        if disabled:
            self.pressed = False
            self.hover = False

    def is_clicked(self, mouse_x, mouse_y, mouse_pressed=None):
        """ボタンがクリックされたかどうかを判定（状態を変更せずにチェック）
        
        Args:
            mouse_x: マウスのX座標
            mouse_y: マウスのY座標
            mouse_pressed: マウスボタンが押されているか。Noneの場合は自動的に左クリックをチェック
            
        Returns:
            bool: クリックされたかどうか
        """
        if self.disabled:
            return False
            
        # 前回のクリックから十分な時間が経過しているか確認
        current_time = pyxel.frame_count
        can_click = (current_time - self._last_click_time) >= self._click_cooldown
        
        # ホバー状態とクリック状態をチェック
        is_hover = (self.x <= mouse_x < self.x + self.w and
                   self.y <= mouse_y < self.y + self.h)
        
        # mouse_pressedがNoneの場合は、左クリックをチェック
        if mouse_pressed is None:
            mouse_pressed = pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
        
        return is_hover and mouse_pressed and can_click
