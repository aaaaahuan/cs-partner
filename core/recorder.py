import os
import json
import time
import cv2
import mss
import numpy as np
from core.minimap import MinimapTracker
from core.data_loader import DataLoader


class Recorder:
    def __init__(self, data_loader: DataLoader, minimap_tracker: MinimapTracker):
        self.data_loader = data_loader
        self.tracker = minimap_tracker
        self.data_folder = self.data_loader.data_folder
        self.images_dir = os.path.join(self.data_folder, "images")
        self.minimaps_dir = os.path.join(self.data_folder, "minimaps")
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.minimaps_dir, exist_ok=True)

    def record_current_position(
        self,
        name: str,
        map_name: str = "inferno",
        grenade_type: str = "Smoke",
        desc: str = "Custom Nade",
        aim_desc: str = "See Image",
    ):
        """
        录制当前位置的投掷点位：
          1. 截取雷达区域，保存为小地图指纹（用于 ORB 位置匹配）
          2. 截取全屏，保存为参考截图（用于瞄准点追踪）
          3. 准星坐标固定为屏幕中心（CS2 准星始终居中）
          4. 写入 grenades.json
        """
        timestamp = int(time.time())

        # 1. 雷达指纹
        minimap_img = self.tracker.grab_minimap()
        minimap_filename = f"minimap_{timestamp}.png"
        minimap_path = os.path.join(self.minimaps_dir, minimap_filename)
        cv2.imwrite(minimap_path, minimap_img)

        # 2. 全屏参考截图
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            raw = np.array(sct.grab(monitor))
            screenshot = cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)

        screen_h, screen_w = screenshot.shape[:2]
        img_filename = f"custom_{timestamp}.png"
        img_path = os.path.join(self.images_dir, img_filename)
        cv2.imwrite(img_path, screenshot)

        # 3. 准星坐标 = 屏幕中心
        aim_x = screen_w // 2
        aim_y = screen_h // 2

        # 4. 构建点位数据
        new_grenade = {
            "name": name,
            "type": grenade_type,
            "desc": desc,
            "aim_desc": aim_desc,
            "image_path": f"images/{img_filename}",
            "minimap_path": f"minimaps/{minimap_filename}",
            "aim_point_x": aim_x,
            "aim_point_y": aim_y,
        }

        # 5. 写入 JSON
        json_path = self.data_loader.data_path
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if map_name not in data["maps"]:
                data["maps"][map_name] = {"name": map_name.capitalize(), "grenades": []}

            data["maps"][map_name]["grenades"].append(new_grenade)

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            print(f"Recorder: Saved '{name}' to map '{map_name}'")
            return True, f"Saved: {name}"

        except Exception as e:
            print(f"Recorder Error: {e}")
            return False, str(e)
