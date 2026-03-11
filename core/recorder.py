import os
import json
import time
import cv2
import mss
import numpy as np
from core.minimap import MinimapTracker
from core.data_loader import DataLoader

class Recorder:
    def __init__(self, data_loader, minimap_tracker):
        self.data_loader = data_loader
        self.tracker = minimap_tracker
        # mss.mss() is not thread-safe if initialized once and used across threads.
        # It's better to initialize it inside the method where it's used, 
        # OR ensure it's used in the same thread.
        # Since record_current_position is called from a hotkey (keyboard thread),
        # we should initialize it there.
        self.sct = None 
        # Use centralized data folder
        self.data_folder = self.data_loader.data_folder
        self.images_dir = os.path.join(self.data_folder, "images")
        self.minimaps_dir = os.path.join(self.data_folder, "minimaps")
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.minimaps_dir, exist_ok=True)

    def record_current_position(self, name, grenade_type="Smoke", desc="Custom Nade", aim_desc="See Image"):
        # 1. Get Player Position (Try absolute first, but proceed even if failed for fingerprinting)
        pos = self.tracker.get_player_position()
        pos_x, pos_y = pos if pos else (-1, -1)
        
        timestamp = int(time.time())
        
        # 2. Capture Minimap Fingerprint (Crucial for rotation support)
        minimap_img = self.tracker.grab_minimap()
        minimap_filename = f"minimap_{timestamp}.png"
        minimap_path = os.path.join(self.minimaps_dir, minimap_filename)
        cv2.imwrite(minimap_path, minimap_img)
        
        # 3. Take Screenshot (Full Screen for Aiming)
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            screenshot = np.array(sct.grab(monitor))
            screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
        
        filename = f"custom_{timestamp}.png"
        file_path = os.path.join(self.images_dir, filename)
        cv2.imwrite(file_path, screenshot)
        
        # 4. Create Grenade Data Entry
        new_grenade = {
            "name": name,
            "type": grenade_type,
            "desc": desc,
            "pos_x": pos_x,
            "pos_y": pos_y,
            "aim_desc": aim_desc,
            "image_path": f"images/{filename}",
            "minimap_path": f"minimaps/{minimap_filename}"
        }
        
        # 5. Save to JSON (Append to current map)
        json_path = self.data_loader.data_path
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            target_map = "mirage" 
            if target_map not in data["maps"]:
                data["maps"][target_map] = {"name": "Mirage", "grenades": []}
                
            data["maps"][target_map]["grenades"].append(new_grenade)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                
            print(f"Recorder: Saved {name} to {json_path}")
            return True, f"Saved: {name}"
            
        except Exception as e:
            print(f"Recorder Error: {e}")
            return False, str(e)
