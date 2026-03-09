import cv2
import numpy as np
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.data_loader import DataLoader

def create_placeholder_image(output_path, text_lines):
    width, height = 1920, 1080
    # Create a semi-transparent looking image (though saved as PNG it will be opaque, but overlay handles opacity)
    # We use a dark grey background to simulate a "night vision" or "schematic" look
    img = np.zeros((height, width, 3), np.uint8)
    img[:] = (30, 30, 30) # Dark Grey
    
    cx, cy = width // 2, height // 2
    
    # Draw Reference Crosshair (Green)
    # This represents where the player SHOULD aim
    color = (0, 255, 0) # Green
    cv2.line(img, (cx - 40, cy), (cx + 40, cy), color, 2)
    cv2.line(img, (cx, cy - 40), (cx, cy + 40), color, 2)
    cv2.circle(img, (cx, cy), 30, color, 2)
    
    # Add Text
    font = cv2.FONT_HERSHEY_SIMPLEX
    
    # Title
    y = height // 2 - 150
    for i, line in enumerate(text_lines):
        scale = 1.5 if i == 0 else 1.0
        thickness = 3 if i == 0 else 2
        text_size = cv2.getTextSize(line, font, scale, thickness)[0]
        text_x = (width - text_size[0]) // 2
        cv2.putText(img, line, (text_x, y), font, scale, (255, 255, 255), thickness)
        y += 60
        
    # Instructions
    instr = "[PLACEHOLDER REFERENCE IMAGE]"
    text_size = cv2.getTextSize(instr, font, 1, 2)[0]
    cv2.putText(img, instr, ((width - text_size[0]) // 2, height - 100), font, 1, (0, 255, 255), 2)
    
    instr2 = "Please replace with real screenshot: F12 in game -> Save here"
    text_size = cv2.getTextSize(instr2, font, 0.8, 1)[0]
    cv2.putText(img, instr2, ((width - text_size[0]) // 2, height - 60), font, 0.8, (200, 200, 200), 1)
    
    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cv2.imwrite(output_path, img)
    print(f"Generated: {output_path}")

def main():
    loader = DataLoader()
    maps = loader.get_maps()
    
    for map_name in maps:
        grenades = loader.get_grenades(map_name)
        for g in grenades:
            image_path = g.get('image_path')
            if image_path:
                # DataLoader handles relative paths inside its folder
                full_path = os.path.join(loader.data_folder, image_path)
                
                if not os.path.exists(full_path):
                    lines = [
                        f"{g['name']} ({g['type']})",
                        f"Aim: {g.get('aim_desc', '')}"
                    ]
                    create_placeholder_image(full_path, lines)

if __name__ == "__main__":
    main()
