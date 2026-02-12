"""
Configuration management for kakitui.

Reads from environment variables first, then from
~/.config/kakitui/config.ini (or %APPDATA%/kakitui/config.ini on Windows).

See config_template.ini for the expected format.
"""

from __future__ import annotations

import configparser
import os
from pathlib import Path
from typing import Literal

UseApiChoice = Literal["true", "false", "auto"]

_DEFAULT_CONFIG_DIR = (
    Path(os.environ.get("APPDATA", "")) / "kakitui"
    if os.name == "nt"
    else Path.home() / ".config" / "kakitui"
)
DEFAULT_CONFIG_PATH = _DEFAULT_CONFIG_DIR / "config.ini"


def _get_config_path() -> Path:
    return Path(os.environ.get("KAKITUI_CONFIG", str(DEFAULT_CONFIG_PATH)))


def load_config() -> configparser.ConfigParser:
    """Load config from file. Does not apply env overrides; callers do that."""
    path = _get_config_path()
    config = configparser.ConfigParser()
    if path.exists():
        config.read(path, encoding="utf-8")
    return config


def get_api_key() -> str | None:
    """Return Kanji Alive API key: env KANJI_ALIVE_API_KEY overrides config."""
    key = os.environ.get("KANJI_ALIVE_API_KEY")
    if key:
        return key.strip() or None
    config = load_config()
    if config.has_section("kanji_alive"):
        key = config["kanji_alive"].get("api_key")
        if key:
            return key.strip()
    return None


def get_use_api() -> Literal["api", "local", "auto"]:
    """
    Return data source preference: 'api', 'local', or 'auto'.
    Env KAKITUI_USE_API overrides config; valid values: api, local, auto.
    """
    raw = os.environ.get("KAKITUI_USE_API", "").strip().lower()
    if raw in ("api", "local", "auto"):
        return raw  # type: ignore[return-value]
    config = load_config()
    if config.has_section("kakitui"):
        raw = config["kakitui"].get("use_api", "auto").strip().lower()
        if raw in ("true", "1", "yes", "api"):
            return "api"
        if raw in ("false", "0", "no", "local"):
            return "local"
        if raw == "auto":
            return "auto"
    return "auto"
