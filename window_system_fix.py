def handle_click_fix(self, mouse_x, mouse_y):
    """
    ウィンドウ内のクリックを処理（修正版）
    
    Args:
        mouse_x (int): マウスのX座標
        mouse_y (int): マウスのY座標
        
    Returns:
        tuple or None: クリックされたアイテムの種類とデータ (例: ("summon_monster", "goblin")), ウィンドウを閉じる場合は ("close", None)
    """
    # ウィンドウが閉じている場合は何もしない
    if not self.is_window_open():
        return None
        
    # ウィンドウの外側をクリックした場合はウィンドウを閉じる
    if not (self.window_x <= mouse_x < self.window_x + self.window_width and
            self.window_y <= mouse_y < self.window_y + self.window_height):
        self.close_window()
        return ("close", None)
        
    # 閉じるボタンをチェック
    close_button_x = self.window_x + self.window_width - 20
    close_button_y = self.window_y + 5
    if (close_button_x <= mouse_x <= close_button_x + 15 and 
        close_button_y <= mouse_y <= close_button_y + 15):
        self.close_window()
        return ("close", None)
        
    # ウィンドウの処理
    if self.active_window == "monster":
        monster_id = self._get_clicked_monster(mouse_x, mouse_y)
        if monster_id:
            return ("summon_monster", monster_id)
    elif self.active_window == "spell":
        spell_id = self._get_clicked_spell(mouse_x, mouse_y)
        if spell_id:
            return ("cast_spell", spell_id)
            
    return None
