"""Turns the systemd user timer for daily updates on and off, and sets its time."""

from __future__ import annotations

import datetime
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from . import settings

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


def parse_time(text: str) -> Optional[str]:
    """Normalises "7:30", "07:30" or "19:05" to "HH:MM", or None if it isn't a time."""
    match = re.fullmatch(r"\s*(\d{1,2})[:.h](\d{2})\s*", text)
    if not match:
        return None
    hour, minute = int(match[1]), int(match[2])
    if hour > 23 or minute > 59:
        return None
    return f"{hour:02d}:{minute:02d}"


def due_moment(daily_time: str, now: Optional[datetime.datetime] = None) -> datetime.datetime:
    """The latest time-of-day `daily_time` ("HH:MM") at or before `now`."""
    now = now or datetime.datetime.now()
    hour, minute = map(int, daily_time.split(":"))
    moment = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if moment > now:
        moment -= datetime.timedelta(days=1)
    return moment


def dropin_path() -> Path:
    return settings.config_dir().parent / "systemd" / "user" / f"{TIMER}.d" / "schedule.conf"


def dropin_text(daily_time: str) -> str:
    return (
        "# Written by bing-wallpaper: change the wallpaper once a day at the chosen time.\n"
        "[Timer]\n"
        "OnCalendar=\n"
        f"OnCalendar=*-*-* {daily_time}:00\n"
        "RandomizedDelaySec=0\n"
    )


def set_time(daily_time: Optional[str]) -> str:
    """Schedules the daily change at `daily_time` ("HH:MM"), or as soon as Bing
    publishes a new image if None. Returns an error message, or "" on success."""
    path = dropin_path()
    if daily_time:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dropin_text(daily_time), encoding="utf-8")
    else:
        path.unlink(missing_ok=True)
    if not available():
        return ""
    _systemctl("daemon-reload")
    if enabled():
        result = _systemctl("restart", TIMER)
        if result.returncode != 0:
            return result.stderr.strip() or "systemctl failed"
    return ""
