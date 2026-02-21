"""
Configuration management for kakitui.

Reads from ~/.config/kakitui/config.ini (or %APPDATA%/kakitui/config.ini
on Windows).

See config_template.ini for the expected format.
"""

from __future__ import annotations

import configparser
import os
from pathlib import Path

_DEFAULT_CONFIG_DIR = (
    Path(os.environ.get("APPDATA", "")) / "kakitui"
    if os.name == "nt"
    else Path.home() / ".config" / "kakitui"
)
DEFAULT_CONFIG_PATH = _DEFAULT_CONFIG_DIR / "config.ini"


def _get_config_path() -> Path:
    return Path(os.environ.get("KAKITUI_CONFIG", str(DEFAULT_CONFIG_PATH)))


def load_config() -> configparser.ConfigParser:
    """Load config from file."""
    path = _get_config_path()
    config = configparser.ConfigParser()
    if path.exists():
        config.read(path, encoding="utf-8")
    return config
