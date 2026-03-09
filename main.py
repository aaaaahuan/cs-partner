import sys
import threading
import time
import math
import keyboard
import os
from PyQt5.QtWidgets import QApplication
from core.overlay import Overlay
from core.data_loader import DataLoader, get_resource_path
from core.minimap import MinimapTracker
from core.recorder import Recorder

# Configuration
NEARBY_THRESHOLD = 0.15 # Minimap percentage distance to show in "Nearby"
ACTIVE_THRESHOLD = 0.02 # Strict threshold for activation (approx 1-2 meters in game)
SIMILARITY_THRESHOLD = 35.0 # ORB distance threshold (Lower is better match, < 40 is decent)

class GameLogic:
    def __init__(self, overlay_signals):
        self.signals = overlay_signals
        self.data_loader = DataLoader()
        self.tracker = MinimapTracker()
        self.recorder = Recorder(self.data_loader, self.tracker)
        self.running = True
        
        # Simple map selection (In a real app, we'd detect map name from screen text)
        self.current_map = "mirage" 
        self.grenades = self.data_loader.get_grenades(self.current_map)
        print(f"Loaded {len(self.grenades)} grenades for {self.current_map}")

    def loop(self):
        print("Starting Logic Loop...")
        
        # Register Hotkey for Recording
        keyboard.add_hotkey('F5', self.record_position)
        # Register Display Mode Hotkeys
        keyboard.add_hotkey('F1', lambda: self.set_display_mode(1)) # Mini
        keyboard.add_hotkey('F2', lambda: self.set_display_mode(2)) # Full
        
        while self.running:
            # 1. Get Player Position
            # For now, we use the simple position tracker
            # If cl_radar_always_centered 1, we should rely on image matching
            pos = self.tracker.get_player_position()
            
            # If pos is None, we can try to match against stored minimap snapshots for active grenades
            # But that's expensive to do for ALL grenades every frame.
            # So we stick to:
            # - If pos found (cl_radar_always_centered 0): Use Distance
            # - If pos not found (maybe rotated map): Use Feature Matching on "Nearby" candidates?
            
            active = None
            nearby = []
            
            if pos:
                player_x, player_y = pos
                
                # 2. Find Nearby Grenades (Distance Based)
                min_dist = float('inf')
                
                for g in self.grenades:
                    gx, gy = g.get('pos_x', -1), g.get('pos_y', -1)
                    if gx == -1: continue # Skip if no coordinates
                    
                    dist = math.sqrt((gx - player_x)**2 + (gy - player_y)**2)
                    
                    if dist < NEARBY_THRESHOLD:
                        g_copy = g.copy()
                        g_copy['distance'] = dist
                        nearby.append(g_copy)
                        
                        if dist < ACTIVE_THRESHOLD and dist < min_dist:
                            min_dist = dist
                            active = g_copy
            else:
                # Fallback: Feature Matching
                # This logic is computationally more expensive, so we only run it if needed.
                # To optimize, we could only check grenades that are known to have minimaps.
                
                # Only check every N frames? No, we need responsiveness.
                # Let's iterate all grenades with 'minimap_path'
                
                best_score = float('inf')
                
                for g in self.grenades:
                    minimap_rel_path = g.get('minimap_path')
                    if not minimap_rel_path:
                        continue
                        
                    # Resolve full path
                    # Assuming paths in json are relative to data folder (e.g. "minimaps/xxx.png")
                    # But DataLoader sets paths relative to executable or cwd.
                    # We need to use DataLoader's base path logic.
                    
                    # Construct absolute path: data_folder + minimap_rel_path
                    full_path = os.path.join(self.data_loader.data_folder, minimap_rel_path)
                    
                    score = self.tracker.compare_current_view(full_path)
                    
                    # Check if match is good enough
                    if score < SIMILARITY_THRESHOLD:
                        g_copy = g.copy()
                        g_copy['distance'] = score # Hack: store score as distance for sorting
                        nearby.append(g_copy)
                        
                        if score < best_score:
                            best_score = score
                            active = g_copy
            
            # Sort nearby by distance (or score)
            nearby.sort(key=lambda x: x['distance'])
            
            # 3. Update HUD
            self.signals.update_hud.emit({
                "active_grenade": active,
                "nearby_grenades": nearby
            })
            
            time.sleep(0.1)

    def set_display_mode(self, mode):
        mode_name = "Mini Window" if mode == 1 else "Ghost Mode"
        self.signals.set_mode.emit(mode)
        self.signals.show_toast.emit(f"Mode: {mode_name}", 2000)

    def record_position(self):
        print("Recording Position...")
        
        # Use Recorder Module
        name = f"Custom Nade {int(time.time())}"
        success, msg = self.recorder.record_current_position(name)
        
        if success:
            self.signals.show_toast.emit(f"Recorded: {name}", 3000)
            # Reload Data
            self.data_loader.reload()
            self.grenades = self.data_loader.get_grenades(self.current_map)
        else:
            self.signals.show_toast.emit(f"Record Error: {msg}", 3000)

def main():
    app = QApplication(sys.argv)
    
    # Get screen resolution
    screen = app.primaryScreen()
    size = screen.size()
    
    # Initialize Overlay
    overlay = Overlay(size.width(), size.height())
    overlay.show()
    
    # Initialize Logic
    logic = GameLogic(overlay.signals)
    
    # Show Startup Toast
    overlay.signals.show_toast.emit("CS2 Partner Ready! Press F5 to Record", 5000)
    
    # Start Logic Thread
    thread = threading.Thread(target=logic.loop, daemon=True)
    thread.start()
    
    print("CS2 Partner - Location Trigger Mode Started.")
    print("Note: Ensure CS2 is in Fullscreen Windowed mode.")
    print(f"Tracking Map: {logic.current_map} (Edit main.py to change)")
    
    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        pass
    finally:
        logic.running = False
        keyboard.unhook_all()

if __name__ == "__main__":
    main()
