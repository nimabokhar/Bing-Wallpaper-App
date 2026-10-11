"""Sets the wallpaper and lock screen using each desktop environment's own tools."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Callable, List, Optional, Sequence

DESKTOP = "desktop"
LOCK = "lock"
BOTH = "both"
TARGETS = (BOTH, DESKTOP, LOCK)

Runner = Callable[[Sequence[str]], str]


class WallpaperError(Exception):
    pass


def run(cmd: Sequence[str]) -> str:
    """Runs a command and returns its output, raising WallpaperError if it fails."""
    try:
        result = subprocess.run(
            list(cmd), capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        raise WallpaperError(f"{cmd[0]}: {e}") from e
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise WallpaperError(f"{' '.join(cmd)} failed: {detail}")
    return result.stdout


def detect(env: Optional[dict] = None) -> str:
    """A short name for the running desktop, e.g. "gnome", "kde", "xfce", or "unknown"."""
    env = os.environ if env is None else env
    names = ":".join(
        filter(None, [env.get("XDG_CURRENT_DESKTOP"), env.get("XDG_SESSION_DESKTOP"), env.get("DESKTOP_SESSION")])
    ).lower()
    parts = [p for p in names.replace(";", ":").split(":") if p]
    # Order matters: Cinnamon and Budgie also report "gnome" in XDG_CURRENT_DESKTOP.
    for key, aliases in (
        ("kde", ("kde", "plasma", "plasmawayland")),
        ("cinnamon", ("cinnamon", "x-cinnamon")),
        ("budgie", ("budgie", "budgie-desktop")),
        ("mate", ("mate",)),
        ("xfce", ("xfce", "xfce4")),
        ("lxqt", ("lxqt",)),
        ("lxde", ("lxde",)),
        ("hyprland", ("hyprland",)),
        ("sway", ("sway",)),
        ("gnome", ("gnome", "ubuntu", "unity", "pop", "gnome-xorg", "gnome-classic", "zorin")),
    ):
        if any(p in aliases for p in parts):
            return key
    if env.get("HYPRLAND_INSTANCE_SIGNATURE"):
        return "hyprland"
    if env.get("SWAYSOCK"):
        return "sway"
    return "unknown"


def file_uri(path: Path) -> str:
    return path.resolve().as_uri()


class Result:
    def __init__(self) -> None:
        self.done: List[str] = []
        self.notes: List[str] = []

    def __repr__(self) -> str:
        return f"Result(done={self.done}, notes={self.notes})"


def _gsettings_has_key(run_: Runner, schema: str, key: str) -> bool:
    try:
        return key in run_(["gsettings", "list-keys", schema]).split()
    except WallpaperError:
        return False


def _set_gnome(path: Path, target: str, run_: Runner, result: Result) -> None:
    uri = file_uri(path)
    if target in (DESKTOP, BOTH):
        run_(["gsettings", "set", "org.gnome.desktop.background", "picture-uri", uri])
        if _gsettings_has_key(run_, "org.gnome.desktop.background", "picture-uri-dark"):
            run_(["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", uri])
        run_(["gsettings", "set", "org.gnome.desktop.background", "picture-options", "zoom"])
        result.done.append(DESKTOP)
    if target in (LOCK, BOTH):
        # GNOME 3.36+ shows a blurred copy of the desktop wallpaper on the lock
        # screen; older GNOME and Budgie read this key.
        if _gsettings_has_key(run_, "org.gnome.desktop.screensaver", "picture-uri"):
            run_(["gsettings", "set", "org.gnome.desktop.screensaver", "picture-uri", uri])
            run_(["gsettings", "set", "org.gnome.desktop.screensaver", "picture-options", "zoom"])
        if target == LOCK:
            result.notes.append(
                "GNOME's lock screen shows the desktop wallpaper, so a lock-only image "
                "may not appear until it is also the desktop wallpaper."
            )
        result.done.append(LOCK)


def _set_cinnamon(path: Path, target: str, run_: Runner, result: Result) -> None:
    # Cinnamon's screensaver shows the desktop wallpaper.
    run_(["gsettings", "set", "org.cinnamon.desktop.background", "picture-uri", file_uri(path)])
    run_(["gsettings", "set", "org.cinnamon.desktop.background", "picture-options", "zoom"])
    result.done += [DESKTOP, LOCK] if target == BOTH else [target]
    if target != BOTH:
        result.notes.append("Cinnamon uses the same image for the desktop and lock screen.")


def _set_mate(path: Path, target: str, run_: Runner, result: Result) -> None:
    run_(["gsettings", "set", "org.mate.background", "picture-filename", str(path)])
    run_(["gsettings", "set", "org.mate.background", "picture-options", "zoom"])
    result.done += [DESKTOP, LOCK] if target == BOTH else [target]
    if target != BOTH:
        result.notes.append("MATE uses the same image for the desktop and lock screen.")


KDE_SCRIPT = """
for (const d of desktops()) {
    d.wallpaperPlugin = "org.kde.image";
    d.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
    d.writeConfig("Image", %s);
    d.writeConfig("FillMode", 2);
}
"""


def _first_available(*names: str) -> Optional[str]:
    for name in names:
        if shutil.which(name):
            return name
    return None


def _set_kde(path: Path, target: str, run_: Runner, result: Result) -> None:
    uri = file_uri(path)
    if target in (DESKTOP, BOTH):
        if shutil.which("plasma-apply-wallpaperimage"):
            run_(["plasma-apply-wallpaperimage", str(path)])
        else:
            qdbus = _first_available("qdbus6", "qdbus-qt6", "qdbus", "qdbus-qt5")
            if not qdbus:
                raise WallpaperError("Neither plasma-apply-wallpaperimage nor qdbus is installed.")
            run_([qdbus, "org.kde.plasmashell", "/PlasmaShell", "org.kde.PlasmaShell.evaluateScript",
                  KDE_SCRIPT % json.dumps(uri)])
        result.done.append(DESKTOP)
    if target in (LOCK, BOTH):
        kwrite = _first_available("kwriteconfig6", "kwriteconfig5")
        if not kwrite:
            raise WallpaperError("kwriteconfig6 (or kwriteconfig5) is needed to set the KDE lock screen.")
        run_([kwrite, "--file", "kscreenlockerrc", "--group", "Greeter",
              "--key", "WallpaperPlugin", "org.kde.image"])
        for key in ("Image", "PreviewImage"):
            run_([kwrite, "--file", "kscreenlockerrc", "--group", "Greeter", "--group", "Wallpaper",
                  "--group", "org.kde.image", "--group", "General", "--key", key, uri])
        result.done.append(LOCK)


def _set_xfce(path: Path, target: str, run_: Runner, result: Result) -> None:
    if target in (DESKTOP, BOTH):
        props = [p for p in run_(["xfconf-query", "-c", "xfce4-desktop", "-l"]).split()
                 if p.endswith("/last-image")]
        if not props:
            raise WallpaperError("No XFCE desktop backdrop found. Set any wallpaper once in Desktop settings.")
        for prop in props:
            run_(["xfconf-query", "-c", "xfce4-desktop", "-p", prop, "-s", str(path)])
            style = prop[: -len("last-image")] + "image-style"
            # 5 = zoomed
            run_(["xfconf-query", "-c", "xfce4-desktop", "-p", style, "-n", "-t", "int", "-s", "5"])
        result.done.append(DESKTOP)
    if target in (LOCK, BOTH):
        result.notes.append(_lock_link_note("XFCE"))


def _set_pcmanfm(path: Path, target: str, run_: Runner, result: Result, qt: bool) -> None:
    if target in (DESKTOP, BOTH):
        if qt:
            run_(["pcmanfm-qt", f"--set-wallpaper={path}", "--wallpaper-mode=zoom"])
        else:
            run_(["pcmanfm", f"--set-wallpaper={path}", "--wallpaper-mode=crop"])
        result.done.append(DESKTOP)
    if target in (LOCK, BOTH):
        result.notes.append(_lock_link_note("LXQt" if qt else "LXDE"))


def _set_sway(path: Path, target: str, run_: Runner, result: Result) -> None:
    if target in (DESKTOP, BOTH):
        if shutil.which("swww"):
            run_(["swww", "img", str(path)])
        else:
            run_(["swaymsg", "output", "*", "bg", str(path), "fill"])
        result.done.append(DESKTOP)
    if target in (LOCK, BOTH):
        result.notes.append(_lock_link_note("Sway"))


def _set_hyprland(path: Path, target: str, run_: Runner, result: Result) -> None:
    if target in (DESKTOP, BOTH):
        if shutil.which("swww"):
            run_(["swww", "img", str(path)])
        elif shutil.which("hyprctl"):
            run_(["hyprctl", "hyprpaper", "preload", str(path)])
            run_(["hyprctl", "hyprpaper", "wallpaper", f",{path}"])
        else:
            raise WallpaperError("Install hyprpaper or swww to set the Hyprland wallpaper.")
        result.done.append(DESKTOP)
    if target in (LOCK, BOTH):
        result.notes.append(_lock_link_note("Hyprland (hyprlock)"))


def _set_generic(path: Path, target: str, run_: Runner, result: Result) -> None:
    if target in (DESKTOP, BOTH):
        if os.environ.get("WAYLAND_DISPLAY") and shutil.which("swww"):
            run_(["swww", "img", str(path)])
        elif shutil.which("feh"):
            run_(["feh", "--bg-fill", str(path)])
        elif shutil.which("nitrogen"):
            run_(["nitrogen", "--set-zoom-fill", "--save", str(path)])
        else:
            raise WallpaperError(
                "Don't know how to set the wallpaper on this desktop. Set custom_command in "
                "~/.config/bing-wallpaper/config.json, e.g. \"swww img {path}\"."
            )
        result.done.append(DESKTOP)
    if target in (LOCK, BOTH):
        result.notes.append(_lock_link_note("this desktop"))


def _lock_link_note(desktop: str) -> str:
    from . import settings

    return (
        f"There's no standard lock screen setting on {desktop}. Point your screen locker at "
        f"{settings.data_dir() / 'lock.jpg'}, which always holds the current lock screen image."
    )


SETTERS = {
    "gnome": _set_gnome,
    "budgie": _set_gnome,
    "cinnamon": _set_cinnamon,
    "mate": _set_mate,
    "kde": _set_kde,
    "xfce": _set_xfce,
    "lxqt": lambda p, t, r, res: _set_pcmanfm(p, t, r, res, qt=True),
    "lxde": lambda p, t, r, res: _set_pcmanfm(p, t, r, res, qt=False),
    "sway": _set_sway,
    "hyprland": _set_hyprland,
    "unknown": _set_generic,
}


def set_wallpaper(
    path: Path,
    target: str = BOTH,
    desktop: Optional[str] = None,
    custom_command: Optional[str] = None,
    run_: Runner = run,
) -> Result:
    """Sets `path` as the wallpaper for `target` ("desktop", "lock" or "both")."""
    if target not in TARGETS:
        raise ValueError(f"target must be one of {TARGETS}")
    result = Result()
    if custom_command:
        cmd = custom_command.replace("{path}", shlex.quote(str(path))).replace("{target}", target)
        run_(["sh", "-c", cmd])
        result.done += [DESKTOP, LOCK] if target == BOTH else [target]
        return result
    SETTERS[desktop or detect()](path, target, run_, result)
    return result
