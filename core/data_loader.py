import json
import os
import sys

def get_resource_path(relative_path):
    """ 
    Get absolute path to resource.
    For user data (grenades.json, images), we use a folder next to the executable.
    """
    # Get the directory of the executable or script
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(".")
        
    return os.path.join(base_path, relative_path)

class DataLoader:
    def __init__(self, data_folder='cs_partner_data'):
        self.data_folder = get_resource_path(data_folder)
        self.data_path = os.path.join(self.data_folder, 'grenades.json')
        
        # Ensure directory exists
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
        
        # Also ensure subdirectories exist
        os.makedirs(os.path.join(self.data_folder, 'images'), exist_ok=True)
        os.makedirs(os.path.join(self.data_folder, 'minimaps'), exist_ok=True)
            
        self.data = self._load_data()

    def reload(self):
        """Reloads data from disk"""
        self.data = self._load_data()
        print("DataLoader: Data reloaded.")

    def _load_data(self):
        # Create default empty file if not exists
        if not os.path.exists(self.data_path):
            default_data = {"maps": {}}
            try:
                with open(self.data_path, 'w', encoding='utf-8') as f:
                    json.dump(default_data, f, indent=4)
                print(f"Created new data file at: {self.data_path}")
                return default_data
            except Exception as e:
                print(f"Error creating data file: {e}")
                return {}

        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading data: {e}")
            return {}

    def get_maps(self):
        return list(self.data.get('maps', {}).keys())

    def get_grenades(self, map_name):
        return self.data.get('maps', {}).get(map_name, {}).get('grenades', [])

    def save_grenade(self, map_name, grenade_data):
        # Implementation for saving new grenades (future feature)
        pass
