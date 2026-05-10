"""Configuration management for JellyfinDownloader."""

import json
from pathlib import Path

from .classes import Config

CONFIG_FILE = Path(__file__).parent.parent / "jellydown.json"


def load_config() -> Config:
    """Load configuration from file, falling back to Pydantic defaults."""
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return Config(**data)
        except Exception as e:
            print("Error loading configuration:", e)

    return Config()


def save_config(config: Config):
    """Saves the current Config object to the JSON file."""
    try:
        config_dict = config.model_dump()
        json_data = json.dumps(config_dict, indent=4)
        CONFIG_FILE.write_text(json_data, encoding="utf-8")
    except Exception as e:
        print(f"Failed to save configuration: {e}")
