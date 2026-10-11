"""Turns the systemd user timer for daily updates on and off."""

from __future__ import annotations

import shutil
import subprocess

TIMER = "bing-wallpaper.timer"


def _systemctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["systemctl", "--user", *args], capture_output=True, text=True, timeout=30, check=False
    )


def available() -> bool:
    return shutil.which("systemctl") is not None


def enabled() -> bool:
    return available() and _systemctl("is-enabled", "--quiet", TIMER).returncode == 0


def enable() -> str:
    """Enables and starts the timer. Returns an error message, or "" on success."""
    if not available():
        return "systemd is not available, so daily updates can't be scheduled."
    result = _systemctl("enable", "--now", TIMER)
    return "" if result.returncode == 0 else (result.stderr.strip() or "systemctl failed")


def disable() -> str:
    if not available():
        return ""
    result = _systemctl("disable", "--now", TIMER)
    return "" if result.returncode == 0 else (result.stderr.strip() or "systemctl failed")
