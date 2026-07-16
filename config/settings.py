import json
import os

CONFIG_FILE = "config.json"

class ConfigManager:
    def __init__(self):
        self.default_config = {
            "camera_index": 0,
            "min_detection_confidence": 0.7,
            "min_tracking_confidence": 0.5,
            "activation_hold_duration": 1.5,
            "cooldown_duration": 1.0,
            "swipe_distance": 0.15,
            "hotkey": "f8"
        }
        self.config = self.load_config()

    def load_config(self) -> dict:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return self.default_config.copy()

    def save_config(self, new_config: dict):
        self.config.update(new_config)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=4)