"""Downloads Bing images and applies them, remembering what was applied."""

from __future__ import annotations

import datetime
import os
import time
from pathlib import Path
from typing import Callable, List, Optional

from . import bing, desktop, schedule, settings

#: Downloaded wallpapers to keep, so the gallery can re-apply recent ones offline.
KEEP_IMAGES = 12


def image_path(image: bing.BingImage, resolution: str = bing.DEFAULT_RESOLUTION) -> Path:
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in image.id)
    if safe.lower().endswith(".jpg"):
        safe = safe[:-4]
    if resolution != bing.DEFAULT_RESOLUTION:
        safe += f"_{resolution}"
    safe += ".jpg"
    return settings.data_dir() / "images" / safe


def download(
    image: bing.BingImage,
    resolution: str = bing.DEFAULT_RESOLUTION,
    fetch: Callable[..., bytes] = bing.download_image,
) -> Path:
    """The image on disk in `resolution`, downloading it if needed."""
    path = image_path(image, resolution)
    if path.exists() and path.stat().st_size > 0:
        return path
    data = fetch(image, resolution)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    return path


def _link(name: str, target: Path) -> None:
    """Keeps ~/.local/share/bing-wallpaper/<name> pointing at the current image, for
    screen lockers and tools we can't configure ourselves (swaylock -i, hyprlock...)."""
    link = settings.data_dir() / name
    tmp = link.with_name(name + ".new")
    try:
        if tmp.is_symlink() or tmp.exists():
            tmp.unlink()
        tmp.symlink_to(target)
        os.replace(tmp, link)
    except OSError:
        pass


def _prune() -> None:
    folder = settings.data_dir() / "images"
    in_use = set()
    for name in ("wallpaper.jpg", "lock.jpg"):
        try:
            in_use.add((settings.data_dir() / name).resolve())
        except OSError:
            pass
    files = sorted(folder.glob("*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in files[KEEP_IMAGES:]:
        if old.resolve() not in in_use:
            old.unlink(missing_ok=True)


def current_desktop(state: settings.State) -> str:
    """The running desktop. Timer runs may not see the session's XDG_CURRENT_DESKTOP,
    so the last desktop seen from inside the session is remembered and used then."""
    name = os.environ.get("BING_WALLPAPER_DESKTOP") or desktop.detect()
    if name != "unknown":
        if state.get("desktop") != name:
            state.update(desktop=name)
        return name
    return state.get("desktop") or name


def apply(
    image: bing.BingImage,
    target: str,
    cfg: Optional[settings.Settings] = None,
    state: Optional[settings.State] = None,
    newest_id: Optional[str] = None,
) -> desktop.Result:
    """Sets `image` on `target`. Pass the id of Bing's newest image as `newest_id` when
    applying an older one by hand, so the daily update keeps it until a new image comes out."""
    cfg = cfg or settings.Settings()
    state = state or settings.State()
    path = download(image, cfg.get("resolution") or bing.DEFAULT_RESOLUTION)
    result = desktop.set_wallpaper(
        path,
        target,
        desktop=current_desktop(state),
        custom_command=cfg.get("custom_command"),
    )
    if target in (desktop.DESKTOP, desktop.BOTH):
        _link("wallpaper.jpg", path)
    if target in (desktop.LOCK, desktop.BOTH):
        _link("lock.jpg", path)
    state.update(last_seen=newest_id or image.id, last_applied=image.id, last_title=image.title,
                 last_applied_at=time.time())
    _prune()
    return result


def latest(cfg: Optional[settings.Settings] = None) -> List[bing.BingImage]:
    cfg = cfg or settings.Settings()
    return bing.fetch_all(cfg.market)


def update(force: bool = False, now: Optional[datetime.datetime] = None) -> Optional[bing.BingImage]:
    """Applies the newest Bing image if it is new since the last check (or if `force`).

    Returns the image applied, or None if already up to date. If the user picked an
    older image by hand, it stays until Bing publishes a new one.

    With a daily time set, the change happens once a day at that time: runs before it
    (at startup or login) do nothing, and a run after a missed time catches up.
    """
    cfg = settings.Settings()
    state = settings.State()
    daily_time = cfg.get("daily_time")
    due = None
    if daily_time and not force:
        due = schedule.due_moment(daily_time, now).isoformat(timespec="minutes")
        if state.get("scheduled_done") == due:
            return None
    newest = bing.fetch_latest(cfg.market, 1)[0]
    if due:
        state.update(scheduled_done=due)
    if not force and state.get("last_seen") == newest.id:
        return None
    apply(newest, cfg.get("daily_target") or desktop.BOTH, cfg, state)
    return newest


def set_daily_time(daily_time: Optional[str], now: Optional[datetime.datetime] = None) -> str:
    """Sets the time of day for the daily change ("HH:MM"), or None for "as soon as
    Bing publishes". Returns an error message, or "" on success."""
    settings.Settings().set("daily_time", daily_time)
    if daily_time:
        # Start from the next occurrence, rather than changing straight away
        # because today's time has already passed.
        due = schedule.due_moment(daily_time, now).isoformat(timespec="minutes")
        settings.State().update(scheduled_done=due)
    return schedule.set_time(daily_time)
