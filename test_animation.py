import sys
import glob
import json
import os
from PyQt5.QtWidgets import QApplication, QWidget, QMenu, QAction
from PyQt5.QtGui import QPixmap, QPainter, QColor, QFont
from PyQt5.QtCore import QTimer, Qt, QPoint
from pynput import mouse, keyboard

class TrickcalPet(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # ★ 常に0.2に固定
        self.SCALE = 0.2 
        
        self.save_file = "save_data.json"
        
        self.click_count = 0
        self.current_character = ""
        self.load_data()

        self.char_dir = "characters"
        if not os.path.exists(self.char_dir):
            os.makedirs(self.char_dir)
            
        self.characters = [d for d in os.listdir(self.char_dir) if os.path.isdir(os.path.join(self.char_dir, d))]
        
        if not self.characters:
            print("エラー: characters フォルダにキャラクターのフォルダがありません")
            sys.exit()
            
        if self.current_character not in self.characters:
            self.current_character = self.characters[0]

        self.load_character_images()

        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self.next_frame)
        self.anim_timer.start(66)
        
        self.react_timer = QTimer()
        self.react_timer.setSingleShot(True)
        self.react_timer.timeout.connect(self.end_reaction)

        self.update_pixmap_and_size()

        # マウスとキーボードの監視を開始
        self.mouse_listener = mouse.Listener(on_click=self.on_global_click)
        self.mouse_listener.start()
        
        self.keyboard_listener = keyboard.Listener(on_press=self.on_global_keypress)
        self.keyboard_listener.start()

    def on_global_click(self, x, y, button, pressed):
        if button == mouse.Button.left and pressed:
            QTimer.singleShot(0, self.trigger_reaction)

    def on_global_keypress(self, key):
        QTimer.singleShot(0, self.trigger_reaction)

    def trigger_reaction(self):
        self.click_count += 1
        self.save_data() 
        
        self.is_reacting = True
        self.update_pixmap_and_size(is_surprise=True)
        self.react_timer.start(500)

    def load_character_images(self):
        char_path = os.path.join(self.char_dir, self.current_character)
        self.idle_files = sorted(glob.glob(os.path.join(char_path, "*.png")))
        self.idle_files = [f for f in self.idle_files if "surprise" not in f]
        
        if not self.idle_files:
            print(f"エラー: {char_path} に画像がありません")
            return

        surprise_path = os.path.join(char_path, "surprise.png")
        if os.path.exists(surprise_path):
            self.surprise_file = surprise_path
        else:
            self.surprise_file = self.idle_files[0]

        self.current_frame = 0
        self.is_reacting = False

    def load_data(self):
        if os.path.exists(self.save_file):
            try:
                with open(self.save_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.click_count = data.get("click_count", 0)
                    self.current_character = data.get("character", "")
            except Exception as e:
                print(f"データ読み込みエラー: {e}")

    def save_data(self):
        try:
            with open(self.save_file, "w", encoding="utf-8") as f:
                json.dump({"click_count": self.click_count, "character": self.current_character}, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"データ保存エラー: {e}")

    def update_pixmap_and_size(self, is_surprise=False):
        if not self.idle_files: return

        if is_surprise:
            pixmap = QPixmap(self.surprise_file)
        else:
            pixmap = QPixmap(self.idle_files[self.current_frame])
            
        # ★ SCALE（0.2）を掛けてリサイズ
        target_size = pixmap.size() * self.SCALE
        self.current_pixmap = pixmap.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setFixedSize(self.current_pixmap.size())
        self.update()

    def next_frame(self):
        if not self.is_reacting and self.idle_files:
            self.current_frame = (self.current_frame + 1) % len(self.idle_files)
            self.update_pixmap_and_size(is_surprise=False)

    def end_reaction(self):
        self.is_reacting = False
        self.update_pixmap_and_size(is_surprise=False)

    def paintEvent(self, event):
        if hasattr(self, 'current_pixmap'):
            painter = QPainter(self)
            painter.drawPixmap(0, 0, self.current_pixmap)
            
            painter.setPen(QColor(0, 0, 0, 100))
            painter.drawText(12, 32, f"Clicks: {self.click_count}")
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 12, QFont.Bold))
            painter.drawText(10, 30, f"Clicks: {self.click_count}")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.offset = event.pos()
        elif event.button() == Qt.RightButton:
            self.show_context_menu(event.globalPos())

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.offset)
            event.accept()

    def show_context_menu(self, pos):
        menu = QMenu(self)
        char_menu = menu.addMenu("キャラクター切り替え")
        for char_name in self.characters:
            action = QAction(char_name, self)
            action.setCheckable(True)
            if char_name == self.current_character:
                action.setChecked(True)
            action.triggered.connect(lambda checked, name=char_name: self.change_character(name))
            char_menu.addAction(action)
            
        menu.addSeparator()
        reset_action = QAction("カウントをリセット", self)
        reset_action.triggered.connect(self.reset_count)
        menu.addAction(reset_action)
        
        menu.addSeparator()
        exit_action = QAction("終了", self)
        exit_action.triggered.connect(self.close)
        menu.addAction(exit_action)

        menu.exec_(pos)

    def change_character(self, char_name):
        self.current_character = char_name
        self.load_character_images()
        self.save_data()
        self.update_pixmap_and_size()

    def reset_count(self):
        self.click_count = 0
        self.save_data()
        self.update()

    def closeEvent(self, event):
        self.save_data()
        if hasattr(self, 'mouse_listener'):
            self.mouse_listener.stop()
        if hasattr(self, 'keyboard_listener'):
            self.keyboard_listener.stop()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    pet = TrickcalPet()
    pet.show()
    sys.exit(app.exec_())
