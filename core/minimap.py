import cv2
import numpy as np
import mss
import os

class MinimapTracker:
    def __init__(self, monitor_index=1):
        # mss instance is NOT thread safe. 
        # We should create a new instance when needed or manage it carefully.
        # But for continuous tracking loop (Main Thread), one instance is fine.
        # However, grab_minimap is also called by Recorder (Keyboard Thread)
        # via tracker.grab_minimap(). This causes the crash!
        
        # Solution: Don't keep a persistent self.sct. 
        # Create it inside grab_minimap or pass it in.
        self.monitor_index = monitor_index
        
        # Minimap is usually in the top-left corner
        # These are approximations for 1920x1080 resolution
        self.minimap_region = {
            "top": 20,
            "left": 20,
            "width": 500,
            "height": 350
        }
        
        # Method 1: Absolute Tracking (Simple)
        # Assumes cl_radar_always_centered 0 (Map fixed, player moves)
        # Color range for player arrow (White-ish)
        self.lower_white = np.array([0, 0, 200])
        self.upper_white = np.array([180, 50, 255])
        
        # Method 2: Feature Matching (Robust to Rotation)
        # Assumes cl_radar_always_centered 1 (Player fixed, map moves/rotates)
        # We need to capture the current view and compare it to the stored view
        self.orb = cv2.ORB_create(nfeatures=500)
        self.bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

    def grab_minimap(self):
        with mss.mss() as sct:
            try:
                monitor = sct.monitors[self.monitor_index]
            except IndexError:
                monitor = sct.monitors[1]
                
            region = {
                "top": monitor["top"] + self.minimap_region["top"],
                "left": monitor["left"] + self.minimap_region["left"],
                "width": self.minimap_region["width"],
                "height": self.minimap_region["height"]
            }
            img = np.array(sct.grab(region))
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    def get_player_position(self):
        """
        Legacy simple tracker. 
        Works BEST if cl_radar_always_centered 0 (Map Fixed).
        """
        frame = self.grab_minimap()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower_white, self.upper_white)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None
            
        largest_contour = max(contours, key=cv2.contourArea)
        M = cv2.moments(largest_contour)
        
        if M["m00"] == 0:
            return None
            
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        
        norm_x = cx / self.minimap_region["width"]
        norm_y = cy / self.minimap_region["height"]
        
        return (norm_x, norm_y)

    def compare_current_view(self, saved_image_path):
        """
        Compare current minimap view with a saved minimap screenshot.
        Returns a similarity score (lower is better, 0 is identical).
        Robust to small rotations and shifts.
        """
        if not os.path.exists(saved_image_path):
            return float('inf')
            
        # 1. Load Saved Image (The "Target" view)
        target_img = cv2.imread(saved_image_path)
        if target_img is None:
            return float('inf')
            
        # 2. Get Current View
        current_img = self.grab_minimap()
        
        # 3. Convert to Grayscale
        img1 = cv2.cvtColor(target_img, cv2.COLOR_BGR2GRAY)
        img2 = cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY)
        
        # 4. Feature Matching (ORB)
        # Find keypoints and descriptors
        kp1, des1 = self.orb.detectAndCompute(img1, None)
        kp2, des2 = self.orb.detectAndCompute(img2, None)
        
        if des1 is None or des2 is None:
            return float('inf')
            
        # Match descriptors
        matches = self.bf.match(des1, des2)
        
        # Sort them in the order of their distance
        matches = sorted(matches, key=lambda x: x.distance)
        
        # Take top matches
        good_matches = matches[:20]
        
        if not good_matches:
            return float('inf')
            
        # Calculate average distance of top matches
        avg_dist = sum(m.distance for m in good_matches) / len(good_matches)
        
        # 5. Template Matching (Fallback/Confirmation for translation only)
        # If rotation is minimal, template matching is very accurate
        # We use a center crop of the current view to search in the target view?
        # No, for "Am I here?", we assume the views should be nearly identical.
        # So we can just use template matching or simple MSE.
        
        # Let's stick to ORB distance for "Similarity"
        # Lower avg_dist means more similar features found
        
        return avg_dist
