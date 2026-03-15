"""
瞄准点追踪引擎
==============
给定录制时保存的全屏参考截图和准星坐标，
在当前游戏画面中找到该准星坐标对应的实时屏幕像素位置。

算法：
  1. 从参考截图提取 ORB 特征点（首次访问时缓存）
  2. 从当前游戏全画面提取 ORB 特征点
  3. FLANN 近似 KNN 匹配 + Lowe 比率测试过滤误匹配
  4. findHomography (RANSAC) 计算参考帧→当前帧的透视变换矩阵 H
  5. 将参考截图中的准星坐标投影到当前帧，得到实时屏幕坐标
"""

import cv2
import numpy as np
import mss
import os


# 最小好匹配数：低于此值时单应矩阵不稳定
MIN_GOOD_MATCHES = 15
# Lowe 比率测试阈值
LOWE_RATIO = 0.75


class AimTracker:
    """
    追踪录制时的准星点在当前游戏画面中的位置。
    """

    def __init__(self, screen_width: int = 1920, screen_height: int = 1080):
        self.screen_width = screen_width
        self.screen_height = screen_height

        # ORB 检测器：特征点数量多于小地图追踪器，以应对全屏大图
        self.orb = cv2.ORB_create(nfeatures=1500)

        # FLANN 匹配器（为 ORB 的二进制描述符配置 LSH 索引）
        FLANN_INDEX_LSH = 6
        index_params = dict(
            algorithm=FLANN_INDEX_LSH,
            table_number=6,
            key_size=12,
            multi_probe_level=1,
        )
        self.flann = cv2.FlannBasedMatcher(index_params, dict(checks=50))

        # 参考特征缓存（避免每帧重复提取参考图特征）
        self._ref_path: str | None = None
        self._ref_kp = None
        self._ref_des = None
        self._ref_aim_pt: tuple | None = None  # (x, y) 在缩小后图像坐标系

    # ──────────────────────────────────────────────
    # 公共接口
    # ──────────────────────────────────────────────

    def find_aim_point(
        self,
        image_path: str,
        aim_point_x: int = None,
        aim_point_y: int = None,
    ):
        """
        在当前游戏画面中找到参考截图里准星点的实时位置。

        Args:
            image_path:   参考全屏截图路径（录制时保存的那张）
            aim_point_x:  准星在参考截图中的 X 坐标（默认 screen_width/2）
            aim_point_y:  准星在参考截图中的 Y 坐标（默认 screen_height/2）

        Returns:
            (screen_x, screen_y, confidence) —— 目标在当前帧的像素坐标 + 置信度（好匹配数）
            None —— 目标不在当前视角内，或匹配不足
        """
        if not os.path.exists(image_path):
            return None

        # 默认准星坐标 = 屏幕中心（CS2 准星固定在中心）
        if aim_point_x is None:
            aim_point_x = self.screen_width // 2
        if aim_point_y is None:
            aim_point_y = self.screen_height // 2

        if not self._load_reference(image_path, aim_point_x, aim_point_y):
            return None

        current = self._grab_game_view()
        return self._match_and_project(current)

    def find_aim_point_in_frame(
        self,
        image_path: str,
        current_frame: np.ndarray,
        aim_point_x: int = None,
        aim_point_y: int = None,
    ):
        """
        与 find_aim_point 相同，但直接接受已截取的帧（避免重复截图）。
        """
        if not os.path.exists(image_path):
            return None

        if aim_point_x is None:
            aim_point_x = self.screen_width // 2
        if aim_point_y is None:
            aim_point_y = self.screen_height // 2

        if not self._load_reference(image_path, aim_point_x, aim_point_y):
            return None

        # 缩小到 50% 与参考图保持一致
        h, w = current_frame.shape[:2]
        small = cv2.resize(current_frame, (w // 2, h // 2))
        return self._match_and_project(small)

    # ──────────────────────────────────────────────
    # 内部方法
    # ──────────────────────────────────────────────

    def _load_reference(self, image_path: str, ax: int, ay: int) -> bool:
        """载入参考截图并缓存特征点。相同路径时直接用缓存。"""
        if image_path == self._ref_path:
            return True

        img = cv2.imread(image_path)
        if img is None:
            return False

        # 缩小到 50%（特征提取速度提升 4x，精度损失可接受）
        h, w = img.shape[:2]
        img_small = cv2.resize(img, (w // 2, h // 2))
        gray = cv2.cvtColor(img_small, cv2.COLOR_BGR2GRAY)

        kp, des = self.orb.detectAndCompute(gray, None)
        if des is None or len(kp) < MIN_GOOD_MATCHES:
            return False

        self._ref_kp = kp
        self._ref_des = des
        self._ref_path = image_path
        # 将准星坐标同步缩小到 50%
        self._ref_aim_pt = (ax // 2, ay // 2)
        return True

    def _grab_game_view(self) -> np.ndarray:
        """截取全屏游戏画面并缩小到 50%。"""
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            raw = np.array(sct.grab(monitor))
        frame = cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)
        h, w = frame.shape[:2]
        return cv2.resize(frame, (w // 2, h // 2))

    def _match_and_project(self, current_small: np.ndarray):
        """核心匹配逻辑：ORB → FLANN → Homography → 投影准星点。"""
        gray = cv2.cvtColor(current_small, cv2.COLOR_BGR2GRAY)
        kp2, des2 = self.orb.detectAndCompute(gray, None)

        if des2 is None or len(kp2) < MIN_GOOD_MATCHES:
            return None

        try:
            matches = self.flann.knnMatch(self._ref_des, des2, k=2)
        except cv2.error:
            return None

        # Lowe 比率测试
        good = []
        for pair in matches:
            if len(pair) == 2:
                m, n = pair
                if m.distance < LOWE_RATIO * n.distance:
                    good.append(m)

        if len(good) < MIN_GOOD_MATCHES:
            return None

        # 求单应矩阵
        src_pts = np.float32(
            [self._ref_kp[m.queryIdx].pt for m in good]
        ).reshape(-1, 1, 2)
        dst_pts = np.float32(
            [kp2[m.trainIdx].pt for m in good]
        ).reshape(-1, 1, 2)

        H, _ = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        if H is None:
            return None

        # 将参考截图中的准星点投影到当前帧
        aim_pt = np.float32([[list(self._ref_aim_pt)]]).reshape(-1, 1, 2)
        projected = cv2.perspectiveTransform(aim_pt, H)
        if projected is None:
            return None

        px, py = projected[0][0]

        # 恢复为全分辨率坐标
        screen_x = int(px * 2)
        screen_y = int(py * 2)

        # 边界检查：点必须在屏幕内
        if not (0 <= screen_x < self.screen_width and 0 <= screen_y < self.screen_height):
            return None

        return (screen_x, screen_y, len(good))
