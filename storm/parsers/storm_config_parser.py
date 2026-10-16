import json
from pathlib import Path


def get_storm_config():
    config_file = Path.home() / ".stormssh" / "config"

    if config_file.exists():
        try:
            return json.loads(config_file.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}
