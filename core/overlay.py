from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QBrush, QImage, QPixmap
import sys
import os
from core.data_loader import get_resource_path

class OverlaySignal(QObject):
    update_hud = pyqtSignal(dict)        # {active_grenade: {}, nearby_grenades: []}
    show_toast = pyqtSignal(str, int)    # message, duration_ms
    set_mode = pyqtSignal(int)           # 1: Mini, 2: Ghost
    update_aim_point = pyqtSignal(object)  # (screen_x, screen_y, confidence) or None

class Overlay(QWidget):
    def __init__(self, screen_width=1920, screen_height=1080):
        super().__init__()
        
        # Display Mode: 1=Mini(TopRight), 2=Full(Ghost)
        self.display_mode = 1 
        
        # Signal handler
        self.signals = OverlaySignal()
        self.signals.update_hud.connect(self.update_state)
        self.signals.show_toast.connect(self.display_toast)
        self.signals.set_mode.connect(self.change_mode)
        self.signals.update_aim_point.connect(self.update_aim_point)
        
        # Window Flags
        self.setWindowFlags(
            Qt.FramelessWindowHint |       # No border
            Qt.WindowStaysOnTopHint |      # Always on top
            Qt.Tool                        # Don't show in taskbar
        )
        
        # Attributes for transparency and click-through
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        # Geometry
        self.setGeometry(0, 0, screen_width, screen_height)
        
        # Data
        self.active_grenade = None   # The one we are standing on
        self.nearby_grenades = []    # List of nearby grenades
        self.toast_message = None
        self.toast_end_time = 0
        self.aim_point = None        # (screen_x, screen_y, confidence) or None
        
        # Fonts
        self.title_font = QFont("Arial", 18, QFont.Bold)
        self.text_font = QFont("Arial", 14)
        self.toast_font = QFont("Arial", 24, QFont.Bold)

    def display_toast(self, message, duration_ms):
        self.toast_message = message
        # Use QTimer for single shot reset or just check timestamp in paintEvent
        # Here we use timestamp for simplicity
        import time
        self.toast_end_time = time.time() + (duration_ms / 1000.0)
        self.update()
        
        # Force update after duration to clear
        QTimer.singleShot(duration_ms + 100, self.update)
        
    def change_mode(self, mode):
        self.display_mode = mode
        self.update()

    def update_state(self, data):
        self.active_grenade = data.get("active_grenade")
        self.nearby_grenades = data.get("nearby_grenades", [])
        self.update()

    def update_aim_point(self, result):
        """接收 (screen_x, screen_y, confidence) 或 None。"""
        self.aim_point = result
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # -1. Draw Status Bar (Always Visible)
        self.draw_status_bar(painter)
        
        # 0. Draw Toast (High Priority)
        import time
        if self.toast_message and time.time() < self.toast_end_time:
            self.draw_toast(painter)
        
        # 1. Draw "Radar" Hints (Stereo-like markers)
        # Since we don't have true 3D, we show markers on the HUD edges or minimap overlay
        # For simplicity, we list nearby grenades on the left side
        self.draw_nearby_list(painter)
        
        # 2. Draw Active Grenade Info (If standing on spot)
        if self.active_grenade:
            self.draw_active_info(painter)

        # 3. Draw Aim Crosshair (if aim point tracked in current view)
        if self.aim_point is not None:
            self.draw_aim_crosshair(painter, *self.aim_point)

    def draw_status_bar(self, painter):
        # Small green label at top center
        w, h = 120, 20
        x = (self.width() - w) // 2
        y = 0
        
        painter.setBrush(QBrush(QColor(0, 180, 0))) # Green
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(x, y, w, h, 0, 0)
        
        painter.setPen(QColor("white"))
        font = QFont("Arial", 8, QFont.Bold)
        painter.setFont(font)
        painter.drawText(x, y, w, h, Qt.AlignCenter, "CS2 Partner Ready")

    def draw_nearby_list(self, painter):
        if not self.nearby_grenades:
            return

        x = 20
        y = 300
        
        painter.setFont(self.title_font)
        painter.setPen(QColor("cyan"))
        painter.drawText(x, y, "Nearby Lineups:")
        y += 30
        
        painter.setFont(self.text_font)
        for g in self.nearby_grenades:
            painter.setPen(QColor("white"))
            dist = g.get('distance', 0)
            painter.drawText(x, y, f"{g['name']} ({dist:.2f})")
            y += 25

    def draw_active_info(self, painter):
        if self.display_mode == 1:
            self.draw_mini_window(painter)
        else:
            self.draw_ghost_mode(painter)

    def draw_mini_window(self, painter):
        # Draw Mini-Window in Top Right Corner
        margin = 20
        win_w = 400
        win_h = 300
        x = self.width() - win_w - margin
        y = margin + 30 # Below status bar
        
        # Draw Background
        painter.setBrush(QBrush(QColor(0, 0, 0, 200))) # Semi-transparent black
        painter.setPen(QPen(QColor("yellow"), 2))
        painter.drawRoundedRect(x, y, win_w, win_h, 10, 10)
        
        # Try to load image
        image_path = self.active_grenade.get("image_path")
        pixmap = None
        if image_path:
            full_path = get_resource_path(image_path)
            if not os.path.exists(full_path):
                # Fallback: Try looking inside cs_partner_data explicitly
                # This handles cases where image_path is relative to data folder (images/foo.png)
                # but get_resource_path is relative to EXE.
                full_path = get_resource_path(os.path.join("cs_partner_data", image_path))
            
            if os.path.exists(full_path):
                pixmap = QPixmap(full_path)
        
        # Content Area
        content_x = x + 10
        content_y = y + 10
        content_w = win_w - 20
        
        # 1. Draw Image (Top half of mini window)
        img_h = 180
        if pixmap:
            scaled_pixmap = pixmap.scaled(content_w, img_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            # Center horizontally
            px = content_x + (content_w - scaled_pixmap.width()) // 2
            painter.drawPixmap(px, content_y, scaled_pixmap)
        else:
            # Placeholder text
            painter.setPen(QColor("gray"))
            painter.setFont(QFont("Arial", 10))
            painter.drawText(content_x, content_y, content_w, img_h, Qt.AlignCenter, "No Image Available")
            
        # 2. Draw Text Info (Bottom half)
        text_y = content_y + img_h + 10
        
        painter.setFont(QFont("Arial", 14, QFont.Bold))
        painter.setPen(QColor("yellow"))
        painter.drawText(content_x, text_y, self.active_grenade['name'])
        
        painter.setFont(QFont("Arial", 11))
        painter.setPen(QColor("white"))
        
        text_y += 25
        lines = [
            f"Type: {self.active_grenade['type']}",
            f"Action: {self.active_grenade.get('aim_desc', 'See image')}",
        ]
        
        for line in lines:
            painter.drawText(content_x, text_y, line)
            text_y += 20

    def draw_ghost_mode(self, painter):
        # Center Screen HUD
        cx, cy = self.width() // 2, self.height() // 2
        
        # Try to load image
        image_path = self.active_grenade.get("image_path")
        pixmap = None
        if image_path:
            full_path = get_resource_path(image_path)
            if not os.path.exists(full_path):
                # Fallback: Try looking inside cs_partner_data explicitly
                full_path = get_resource_path(os.path.join("cs_partner_data", image_path))
                
            if os.path.exists(full_path):
                pixmap = QPixmap(full_path)
        
        if pixmap:
            # Ghost Mode: Draw the reference image full screen (or large centered)
            # scaled to fit the screen while keeping aspect ratio
            scaled_pixmap = pixmap.scaled(self.width(), self.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Calculate position to center it
            px = (self.width() - scaled_pixmap.width()) // 2
            py = (self.height() - scaled_pixmap.height()) // 2
            
            # Draw with low opacity (Ghost)
            painter.setOpacity(0.3) 
            painter.drawPixmap(px, py, scaled_pixmap)
            painter.setOpacity(1.0)
            
            # Hint text
            painter.setPen(QColor("yellow"))
            painter.setFont(QFont("Arial", 12))
            painter.drawText(cx + 20, cy + 20, "ALIGN WITH GHOST IMAGE")
            
        else:
            # Fallback: Just text, no annoying box
            painter.setPen(QColor("red"))
            painter.setFont(self.text_font)
            painter.drawText(cx - 100, cy - 50, "No Reference Image Found")
            painter.setPen(QColor("gray"))
            painter.setFont(QFont("Arial", 10))
            painter.drawText(cx - 100, cy - 30, f"Please add: {image_path}")
        
        # 3. Draw Instructions (Bottom Center)
        info_x = cx - 200
        info_y = cy + 200
        
        # Background for text
        painter.setBrush(QBrush(QColor(0, 0, 0, 150)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(info_x - 10, info_y - 30, 400, 120, 10, 10)
        
        painter.setFont(self.title_font)
        painter.setPen(QColor("yellow"))
        painter.drawText(info_x, info_y, f"READY: {self.active_grenade['name']}")
        
        painter.setFont(self.text_font)
        painter.setPen(QColor("white"))
        
        y = info_y + 35
        lines = [
            f"Type: {self.active_grenade['type']}",
            f"Action: {self.active_grenade.get('aim_desc', 'See image')}",
        ]
        
        for line in lines:
            painter.drawText(info_x, y, line)
            y += 25

    def draw_aim_crosshair(self, painter, screen_x: int, screen_y: int, confidence: int):
        """
        在屏幕 (screen_x, screen_y) 绘制准星圆圈，指示玩家应将准星对准此处。
        confidence 越高，圆圈越绿（高置信）；较低时显示橙色（中等置信）。
        """
        color = QColor(0, 255, 0) if confidence >= 25 else QColor(255, 165, 0)
        pen = QPen(color, 2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        # 外圆：半径 28px
        r_outer = 28
        painter.drawEllipse(screen_x - r_outer, screen_y - r_outer, r_outer * 2, r_outer * 2)

        # 十字线（中心小空白，避免遮挡准星）
        gap = 6
        arm = 18
        painter.drawLine(screen_x - arm - gap, screen_y, screen_x - gap, screen_y)
        painter.drawLine(screen_x + gap, screen_y, screen_x + arm + gap, screen_y)
        painter.drawLine(screen_x, screen_y - arm - gap, screen_x, screen_y - gap)
        painter.drawLine(screen_x, screen_y + gap, screen_x, screen_y + arm + gap)

        # 标签文字（在圆圈右上方）
        label_x = screen_x + r_outer + 6
        label_y = screen_y - r_outer
        if self.active_grenade:
            aim_desc = self.active_grenade.get("aim_desc", "Aim Here")
            grenade_type = self.active_grenade.get("type", "")
            painter.setFont(QFont("Arial", 11, QFont.Bold))
            painter.setPen(color)
            painter.drawText(label_x, label_y, aim_desc)
            painter.setFont(QFont("Arial", 10))
            painter.setPen(QColor("white"))
            painter.drawText(label_x, label_y + 18, grenade_type)

    def draw_toast(self, painter):
        cx, cy = self.width() // 2, self.height() // 4
        
        text = self.toast_message
        painter.setFont(self.toast_font)
        fm = painter.fontMetrics()
        text_w = fm.horizontalAdvance(text)
        text_h = fm.height()
        
        # Draw Background
        padding = 20
        rect_x = cx - text_w // 2 - padding
        rect_y = cy - text_h // 2 - padding
        rect_w = text_w + padding * 2
        rect_h = text_h + padding * 2
        
        painter.setBrush(QBrush(QColor(0, 200, 0, 200))) # Green background
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect_x, rect_y, rect_w, rect_h, 15, 15)
        
        # Draw Text
        painter.setPen(QColor("white"))
        painter.drawText(rect_x + padding, rect_y + padding + fm.ascent(), text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = Overlay()
    overlay.show()
    overlay.signals.update_hud.emit({
        "active_grenade": {
            "name": "Test Smoke",
            "type": "Smoke",
            "desc": "Test Description",
            "aim_desc": "Aim at the sun"
        },
        "nearby_grenades": [
            {"name": "Other Smoke", "distance": 0.05}
        ]
    })
    sys.exit(app.exec_())
