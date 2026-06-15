"""Configuration management for media-puller."""

import json
from pathlib import Path
from typing import Any

CONFIG_FILE = Path.home() / ".config" / "media-puller" / "config.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "format": "mp3",
    "quality": "192",
    "output_dir": str(Path.home() / "Music" / "media-puller"),
    "embed_thumbnail": True,
    "keep_original": False,
    "max_downloads": None,
    "yt_dlp_extra": [],
}


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load user config, merging with defaults."""
    cfg_path = path or CONFIG_FILE
    config = dict(DEFAULT_CONFIG)

    if cfg_path.exists():
        try:
            with open(cfg_path) as f:
                user_cfg = json.load(f)
            config.update(user_cfg)
        except (json.JSONDecodeError, OSError) as e:
            print(f"⚠️  config error: {e}")

    return config


def save_config(config: dict[str, Any], path: Path | None = None) -> None:
    """Save config to file."""
    cfg_path = path or CONFIG_FILE
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cfg_path, "w") as f:
        json.dump(config, f, indent=2)
