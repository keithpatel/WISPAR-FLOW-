"""
WISPAR FLOW - Configuration Manager
Handles local user settings stored in wispar_config.json
"""

import json
from pathlib import Path

DEFAULT_CONFIG = {
    "model_size": "tiny",
    "language": "en",
    "hotkey": "Ctrl+Shift+Space",
    "hotkey_mode": "toggle",  # "toggle" or "push_to_talk"
    "dictation_mode": "general",  # "general", "coding", "markdown"
    "custom_vocabulary": "WISPAR FLOW, Python, JavaScript, API",
    "sound_effects": True,
    "vad_threshold": 0.008,
    "hud_enabled": True,
    "cleaner_enabled": True,
    "remove_fillers": True,
    "auto_punctuation": True,
    "custom_replacements": {
        "my email": "user@example.com",
        "wispar flow": "WISPAR FLOW",
        "today date": "{date}",
        "current time": "{time}"
    },
    "audio_device": None,  # None means default microphone
    "ollama_enabled": False,
    "ollama_url": "http://localhost:11434",
    "ollama_model": "llama3"
}

class ConfigManager:
    def __init__(self, config_dir=None):
        if config_dir is None:
            config_dir = Path(__file__).parent.parent
        else:
            config_dir = Path(config_dir)
        self.config_path = config_dir / "wispar_config.json"
        self.data = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        """Load configuration from disk, creating default if missing."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.data.update(loaded)
            except Exception as e:
                print(f"[Config] Error loading config: {e}. Using defaults.")
        else:
            self.save()

    def save(self):
        """Save current configuration to disk."""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"[Config] Error saving config: {e}")

    def get(self, key, default=None):
        return self.data.get(key, default if default is not None else DEFAULT_CONFIG.get(key))

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def update(self, dict_values):
        self.data.update(dict_values)
        self.save()
