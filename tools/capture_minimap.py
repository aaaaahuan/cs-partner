import os
import cv2
import numpy as np
import sys
import mss

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.data_loader import DataLoader
from core.minimap import MinimapTracker

def capture_minimap_template(output_path):
    print("Capturing Minimap Template...")
    tracker = MinimapTracker()
    img = tracker.grab_minimap()
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cv2.imwrite(output_path, img)
    print(f"Saved Minimap Template to: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        name = sys.argv[1]
    else:
        name = "test_template.png"
        
    # Use cs_partner_data directory
    loader = DataLoader() # Initialize to ensure folders exist
    output_path = os.path.join(loader.data_folder, "minimaps", name)
    
    capture_minimap_template(output_path)
