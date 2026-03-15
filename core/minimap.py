"""
小地图识别引擎
==============
前提：游戏设置 cl_radar_always_centered 1（玩家图标固定在雷达中心）。

职责：
  1. 截取屏幕左上角的雷达区域
  2. 与录制时保存的雷达指纹做 ORB 特征匹配
  3. 返回相似度分数（越低越匹配，< 35 视为"玩家在该位置"）
"""

import cv2
import numpy as np
import mss
import os


class MinimapTracker:
    def __init__(self, monitor_index: int = 1):
        self.monitor_index = monitor_index

        # 雷达捕获区域（以 1920×1080 为基准，含周边容错区域）
        self.minimap_region = {
            "top": 20,
            "left": 20,
            "width": 500,
            "height": 350,
        }

        # ORB 特征检测器（用于位置指纹匹配）
        self.orb = cv2.ORB_create(nfeatures=500)
        # BFMatcher with crossCheck 减少误匹配
        self.bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

    def grab_minimap(self) -> np.ndarray:
        """截取雷达区域，返回 BGR numpy 数组。"""
        with mss.mss() as sct:
            try:
                monitor = sct.monitors[self.monitor_index]
            except IndexError:
                monitor = sct.monitors[1]

            region = {
                "top": monitor["top"] + self.minimap_region["top"],
                "left": monitor["left"] + self.minimap_region["left"],
                "width": self.minimap_region["width"],
                "height": self.minimap_region["height"],
            }
            img = np.array(sct.grab(region))
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    def compare_current_view(self, saved_image_path: str) -> float:
        """
        比较当前雷达截图与录制时保存的雷达指纹的相似度。

        Returns:
            float: 相似度分数（越低越匹配，> 50 视为不匹配）
                   SIMILARITY_THRESHOLD = 35.0 为推荐触发阈值
            float('inf'): 无法比较（文件不存在、特征点不足等）
        """
        if not os.path.exists(saved_image_path):
            return float("inf")

        target_img = cv2.imread(saved_image_path)
        if target_img is None:
            return float("inf")

        current_img = self.grab_minimap()

        img1 = cv2.cvtColor(target_img, cv2.COLOR_BGR2GRAY)
        img2 = cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY)

        kp1, des1 = self.orb.detectAndCompute(img1, None)
        kp2, des2 = self.orb.detectAndCompute(img2, None)

        if des1 is None or des2 is None:
            return float("inf")

        matches = self.bf.match(des1, des2)
        matches = sorted(matches, key=lambda x: x.distance)
        good = matches[:20]

        if not good:
            return float("inf")

        return sum(m.distance for m in good) / len(good)
