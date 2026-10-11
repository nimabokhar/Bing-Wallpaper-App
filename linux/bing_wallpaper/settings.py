"""Settings and remembered state, stored under the XDG base directories."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from . import bing


def _xdg(var: str, default: str) -> Path:
    value = os.environ.get(var)
    return Path(value) if value else Path.home() / default


def config_dir() -> Path:
    return _xdg("XDG_CONFIG_HOME", ".config") / "bing-wallpaper"


def data_dir() -> Path:
    """Downloaded wallpapers live here. The desktop reads them, so they must not be a cache."""
    return _xdg("XDG_DATA_HOME", ".local/share") / "bing-wallpaper"


def cache_dir() -> Path:
    return _xdg("XDG_CACHE_HOME", ".cache") / "bing-wallpaper"


def state_dir() -> Path:
    return _xdg("XDG_STATE_HOME", ".local/state") / "bing-wallpaper"


DEFAULTS: Dict[str, Any] = {
    # Bing market code, or None to follow the system language.
    "market": None,
    # Check for a new image every few hours and apply it.
    "daily": True,
    # Time of day for the daily change as "HH:MM", or None to change as soon as
    # Bing publishes a new image.
    "daily_time": None,
    # Where the daily image goes: "both", "desktop" or "lock".
    "daily_target": "both",
    # Optional shell command run with the image path as {path}, for desktops we
    # don't know how to set (e.g. "swww img {path}").
    "custom_command": None,
}


def _load(path: Path) -> Dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


class Settings:
    def __init__(self) -> None:
        self.path = config_dir() / "config.json"
        self.values = dict(DEFAULTS)
        self.values.update(_load(self.path))

    def get(self, key: str) -> Any:
        return self.values.get(key, DEFAULTS.get(key))

    def set(self, key: str, value: Any) -> None:
        self.values[key] = value
        _save(self.path, {k: v for k, v in self.values.items()})

    @property
    def chosen_market(self) -> Optional[str]:
        return self.get("market")

    @property
    def market(self) -> str:
        return self.chosen_market or bing.system_market()


class State:
    """What we last applied, so timer runs only change the wallpaper for a new image."""

    def __init__(self) -> None:
        self.path = state_dir() / "state.json"
        self.values = _load(self.path)

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def update(self, **values: Any) -> None:
        self.values.update(values)
        _save(self.path, self.values)
