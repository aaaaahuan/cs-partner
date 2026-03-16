import sys
import threading
import time
import keyboard
import os
import ctypes
from PyQt5.QtWidgets import QApplication


def _ensure_admin():
    """若非管理员则以管理员权限重启自身。"""
    if not ctypes.windll.shell32.IsUserAnAdmin():
        print("🚀 [Admin] Not running as admin, relaunching with elevation...")
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit(0)


_ensure_admin()
from core.overlay import Overlay
from core.data_loader import DataLoader, get_resource_path
from core.minimap import MinimapTracker
from core.aim_tracker import AimTracker
from core.recorder import Recorder

# ──────────────────────────────────────────────
# 配置
# ──────────────────────────────────────────────
# 雷达 ORB 匹配相似度阈值（越低越相似，< 35 视为触发）
SIMILARITY_THRESHOLD = 35.0


class GameLogic:
    def __init__(self, overlay_signals, screen_width: int, screen_height: int):
        self.signals = overlay_signals
        self.data_loader = DataLoader()
        self.tracker = MinimapTracker()
        self.aim_tracker = AimTracker(screen_width, screen_height)
        self.recorder = Recorder(self.data_loader, self.tracker)
        self.running = True

        # 当前地图（后续可接入自动检测）
        self.current_map = "inferno"
        self.grenades = self.data_loader.get_grenades(self.current_map)
        print(f"🚀 [Init] map={self.current_map}  grenades_count={len(self.grenades)}")

    def loop(self):
        print("Starting Logic Loop...")

        try:
            keyboard.add_hotkey("F5", self.record_position)
            keyboard.add_hotkey("F1", lambda: self._set_mode(1))
            keyboard.add_hotkey("F2", lambda: self._set_mode(2))
            print("Hotkeys registered: F1=Mini  F2=Ghost  F5=Record")
        except Exception as e:
            print(f"Hotkey Error: {e}")
            self.signals.show_toast.emit("Hotkey Error: Run as Admin!", 5000)

        while self.running:
            active = None
            nearby = []
            best_score = float("inf")

            # ── Step 1：雷达指纹匹配，判断玩家位置 ──
            for g in self.grenades:
                minimap_rel = g.get("minimap_path", "")
                if not minimap_rel:
                    continue

                full_path = os.path.join(self.data_loader.data_folder, minimap_rel)
                score = self.tracker.compare_current_view(full_path)
                if score < SIMILARITY_THRESHOLD:
                    g_copy = g.copy()
                    g_copy["_score"] = score
                    nearby.append(g_copy)

                    if score < best_score:
                        best_score = score
                        active = g_copy

            nearby.sort(key=lambda x: x["_score"])
            print(f"🚀 [Step1] best_score={best_score:.2f}  nearby_count={len(nearby)}  active={active.get('name') if active else None}")

            # ── Step 2：瞄准点追踪（只在有激活点位时执行）──
            aim_result = None
            if active:
                image_path = active.get("image_path", "")
                if image_path:
                    # 构建绝对路径（支持相对路径和 assets/ 前缀）
                    full_img_path = get_resource_path(image_path)
                    if not os.path.exists(full_img_path):
                        full_img_path = get_resource_path(
                            os.path.join("cs_partner_data", image_path)
                        )

                    if os.path.exists(full_img_path):
                        aim_x = active.get("aim_point_x")
                        aim_y = active.get("aim_point_y")
                        aim_result = self.aim_tracker.find_aim_point(
                            full_img_path, aim_x, aim_y
                        )
                        print(f"🚀 [Step2] aim_x={aim_x}  aim_y={aim_y}  aim_result={aim_result}")

            # ── Step 3：更新 UI ──
            self.signals.update_hud.emit(
                {"active_grenade": active, "nearby_grenades": nearby}
            )
            self.signals.update_aim_point.emit(aim_result)

            time.sleep(0.1)

    def _set_mode(self, mode: int):
        name = "Mini Window" if mode == 1 else "Ghost Mode"
        self.signals.set_mode.emit(mode)
        self.signals.show_toast.emit(f"Mode: {name}", 2000)

    def record_position(self):
        print("Recording Position...")
        try:
            name = f"Custom Nade {int(time.time())}"
            success, msg = self.recorder.record_current_position(
                name, map_name=self.current_map
            )
            print(f"🚀 [Record] name={name}  success={success}  msg={msg}")
            if success:
                self.signals.show_toast.emit(f"Recorded: {name}", 3000)
                self.data_loader.reload()
                self.grenades = self.data_loader.get_grenades(self.current_map)
                print(f"🚀 [Record] grenades reloaded, count={len(self.grenades)}")
            else:
                self.signals.show_toast.emit(f"Record Error: {msg}", 3000)
        except Exception as e:
            print(f"Record Crash: {e}")
            self.signals.show_toast.emit(f"Record Crash: {e}", 5000)


def main():
    app = QApplication(sys.argv)

    screen = app.primaryScreen()
    w, h = screen.size().width(), screen.size().height()

    overlay = Overlay(w, h)
    overlay.show()

    logic = GameLogic(overlay.signals, w, h)

    overlay.signals.show_toast.emit("CS2 Partner Ready! F1=Mini  F2=Ghost  F5=Record", 5000)

    thread = threading.Thread(target=logic.loop, daemon=True)
    thread.start()

    print(f"🚀 [Main] CS2 Partner started.  screen={w}x{h}  map={logic.current_map}")
    print("Ensure CS2 is in Fullscreen Windowed mode with cl_radar_always_centered 1")

    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        pass
    finally:
        logic.running = False
        keyboard.unhook_all()


if __name__ == "__main__":
    main()
