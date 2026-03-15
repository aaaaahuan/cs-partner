"""
CS2 Partner - 离线演示脚本
============================
无需运行 CS2，演示完整的三层工作流：
  1. 小地图识别 → 找到玩家位置
  2. 检索匹配点位数据
  3. 瞄准点追踪 → 将准星圆圈投影到当前游戏视角

演示策略（无 CS2 时的模拟方式）：
  - 小地图匹配：跳过（直接假设玩家已到达点位）
  - 瞄准点追踪：将参考截图自身作为"当前游戏画面"
    → 此时参考图与当前帧完全相同，特征匹配必然高置信
    → 准星圆圈将出现在参考图的准星坐标（屏幕中心附近）
    → 真实场景中，玩家转动视角后准星圆圈会随目标物移动

运行方式：
    python demo.py

快捷键：
    Space    下一步
    1        小窗模式 (Mini)
    2        幽灵模式 (Ghost)
    Q / ESC  退出
"""

import sys
import os
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QKeyEvent

from core.overlay import Overlay
from core.aim_tracker import AimTracker

# ──────────────────────────────────────────────
# Demo 演示序列
# ──────────────────────────────────────────────
DEMO_STEPS = [
    {
        "phase": "idle",
        "mode": 1,
        "toast": "演示开始：玩家正在 Inferno 地图移动...",
        "active": None,
        "nearby": [],
        "aim_point": None,
        "duration_ms": 3000,
    },
    {
        "phase": "position_matched",
        "mode": 1,
        "toast": "【小地图匹配】雷达指纹匹配成功 → 玩家在 Banana 投掷位",
        "active": {
            "name": "Banana - CT 烟雾弹",
            "type": "Smoke (烟雾弹)",
            "desc": "从香蕉道封锁 CT 通道视野",
            "aim_desc": "左键普通投掷",
            "image_path": "assets/inferno/1.png",
            "aim_point_x": 960,
            "aim_point_y": 540,
        },
        "nearby": [{"name": "Banana - CT 烟雾弹", "_score": 18.5}],
        "aim_point": None,   # 还未开始瞄准追踪
        "duration_ms": 3000,
    },
    {
        "phase": "aim_tracking_mini",
        "mode": 1,
        "toast": "【瞄准追踪】目标进入视野 → 准星圆圈实时跟随",
        "active": {
            "name": "Banana - CT 烟雾弹",
            "type": "Smoke (烟雾弹)",
            "desc": "从香蕉道封锁 CT 通道视野",
            "aim_desc": "左键普通投掷",
            "image_path": "assets/inferno/1.png",
            "aim_point_x": 960,
            "aim_point_y": 540,
        },
        "nearby": [{"name": "Banana - CT 烟雾弹", "_score": 18.5}],
        "aim_point": "compute",   # 标记为需要实际计算
        "duration_ms": 6000,
    },
    {
        "phase": "aim_tracking_ghost",
        "mode": 2,
        "toast": "【幽灵模式】参考图铺满全屏 + 准星圆圈定位，精准对齐",
        "active": {
            "name": "Banana - CT 烟雾弹",
            "type": "Smoke (烟雾弹)",
            "desc": "从香蕉道封锁 CT 通道视野",
            "aim_desc": "左键普通投掷",
            "image_path": "assets/inferno/1.png",
            "aim_point_x": 960,
            "aim_point_y": 540,
        },
        "nearby": [{"name": "Banana - CT 烟雾弹", "_score": 18.5}],
        "aim_point": "compute",
        "duration_ms": 6000,
    },
    {
        "phase": "target_not_in_view",
        "mode": 1,
        "toast": "【目标离开视野】玩家转向其他方向 → 圆圈消失，显示参考卡片提示",
        "active": {
            "name": "Banana - CT 烟雾弹",
            "type": "Smoke (烟雾弹)",
            "desc": "从香蕉道封锁 CT 通道视野",
            "aim_desc": "左键普通投掷",
            "image_path": "assets/inferno/1.png",
            "aim_point_x": 960,
            "aim_point_y": 540,
        },
        "nearby": [{"name": "Banana - CT 烟雾弹", "_score": 18.5}],
        "aim_point": None,   # 模拟目标不在视角内
        "duration_ms": 4000,
    },
    {
        "phase": "second_lineup",
        "mode": 1,
        "toast": "【第二点位】接近拱门投掷位 → 切换到新点位",
        "active": {
            "name": "拱门 - B 包点烟",
            "type": "Smoke (烟雾弹)",
            "desc": "封锁 B 包点守点视野",
            "aim_desc": "双键中距离投掷",
            "image_path": "assets/inferno/2.png",
            "aim_point_x": 960,
            "aim_point_y": 540,
        },
        "nearby": [
            {"name": "拱门 - B 包点烟", "_score": 22.1},
            {"name": "Banana - CT 烟雾弹", "_score": 48.3},
        ],
        "aim_point": "compute",
        "duration_ms": 6000,
    },
    {
        "phase": "idle_end",
        "mode": 1,
        "toast": "演示结束，即将重播... (Q/ESC 退出)",
        "active": None,
        "nearby": [],
        "aim_point": None,
        "duration_ms": 3000,
    },
]


class DemoController(QWidget):
    """
    透明控制器，驱动演示步进 + 键盘响应。
    """

    def __init__(self, overlay: Overlay, screen_w: int, screen_h: int):
        super().__init__()
        self.overlay = overlay
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.step_index = 0

        # 用于演示的 AimTracker
        self.aim_tracker = AimTracker(screen_w, screen_h)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._next_step)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(0, 0, 1, 1)
        self.show()

        self._apply_step(self.step_index)

    def _compute_demo_aim_point(self, step: dict):
        """
        离线演示的瞄准点计算：
        用参考截图自身作为"当前游戏画面"，
        使 ORB 匹配必然成功，从而展示准星圆圈 UI 效果。
        实际产品中传入的是 grab_game_view() 的实时画面。
        """
        active = step.get("active")
        if not active:
            return None

        img_path = active.get("image_path", "")
        full_path = os.path.abspath(img_path)
        if not os.path.exists(full_path):
            return None

        ref_img = cv2.imread(full_path)
        if ref_img is None:
            return None

        ax = active.get("aim_point_x", self.screen_w // 2)
        ay = active.get("aim_point_y", self.screen_h // 2)

        return self.aim_tracker.find_aim_point_in_frame(full_path, ref_img, ax, ay)

    def _apply_step(self, idx: int):
        step = DEMO_STEPS[idx % len(DEMO_STEPS)]

        # 更新显示模式
        self.overlay.signals.set_mode.emit(step["mode"])

        # Toast 提示
        toast_dur = min(step["duration_ms"] - 300, 4500)
        self.overlay.signals.show_toast.emit(step["toast"], toast_dur)

        # 更新 HUD
        self.overlay.signals.update_hud.emit({
            "active_grenade": step["active"],
            "nearby_grenades": step["nearby"],
        })

        # 更新瞄准点
        if step["aim_point"] == "compute":
            aim_result = self._compute_demo_aim_point(step)
        else:
            aim_result = step["aim_point"]  # None

        self.overlay.signals.update_aim_point.emit(aim_result)

        # 定时下一步
        self.timer.stop()
        self.timer.start(step["duration_ms"])

    def _next_step(self):
        self.step_index = (self.step_index + 1) % len(DEMO_STEPS)
        self._apply_step(self.step_index)

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key in (Qt.Key_Q, Qt.Key_Escape):
            QApplication.quit()
        elif key == Qt.Key_Space:
            self.timer.stop()
            self._next_step()
        elif key == Qt.Key_1:
            self.overlay.signals.set_mode.emit(1)
            self.overlay.signals.show_toast.emit("小窗模式 (Mini)", 2000)
        elif key == Qt.Key_2:
            self.overlay.signals.set_mode.emit(2)
            self.overlay.signals.show_toast.emit("幽灵模式 (Ghost)", 2000)


def main():
    app = QApplication(sys.argv)

    screen = app.primaryScreen()
    w, h = screen.size().width(), screen.size().height()

    overlay = Overlay(w, h)
    overlay.show()

    overlay.signals.show_toast.emit(
        "CS2 Partner Demo  |  Space=下一步  1/2=切换模式  Q=退出", 4000
    )

    controller = DemoController(overlay, w, h)

    print("=" * 55)
    print("CS2 Partner - 离线演示模式")
    print("=" * 55)
    print(f"屏幕: {w}x{h}")
    print("Space=下一步  1=小窗  2=幽灵  Q/ESC=退出")
    print("演示将自动循环，每步约 3-6 秒")
    print("=" * 55)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
