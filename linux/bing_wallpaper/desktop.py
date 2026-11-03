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
        ("niri", ("niri",)),
        ("gnome", ("gnome", "ubuntu", "unity", "pop", "gnome-xorg", "gnome-classic", "zorin")),
    ):
        if any(p in aliases for p in parts):
            return key
    if env.get("HYPRLAND_INSTANCE_SIGNATURE"):
        return "hyprland"
    if env.get("NIRI_SOCKET"):
        return "niri"
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


def _dms_running(run_: Runner) -> bool:
    """True when DankMaterialShell is running and answers its IPC."""
    if not shutil.which("dms"):
        return False
    try:
        run_(["dms", "ipc", "call", "wallpaper", "get"])
        return True
    except WallpaperError:
        return False


SWAYBG_UNIT = "bing-wallpaper-swaybg"


def _quiet(cmd: Sequence[str]) -> None:
    try:
        subprocess.run(list(cmd), capture_output=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        pass


def spawn_swaybg(path: Path) -> None:
    """Starts swaybg in the background, replacing any swaybg already running.

    swaybg has to keep running to show the image. Under the daily timer this
    process lives in a short-lived systemd service that kills its children when
    it ends, so swaybg is started as its own user unit when systemd is there."""
    cmd = ["swaybg", "-i", str(path), "-m", "fill"]
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    use_systemd = bool(shutil.which("systemd-run") and runtime and Path(runtime, "systemd").is_dir())
    if use_systemd:
        _quiet(["systemctl", "--user", "stop", f"{SWAYBG_UNIT}.service"])
    _quiet(["pkill", "-x", "swaybg"])
    if use_systemd:
        run(["systemd-run", "--user", "--collect", f"--unit={SWAYBG_UNIT}", *cmd])
        return
    try:
        subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError as e:
        raise WallpaperError(f"swaybg: {e}") from e


def _set_wayland(path: Path, target: str, run_: Runner, result: Result, name: str) -> None:
    """Wayland compositors without a wallpaper setting of their own (niri, Sway,
    Hyprland and other wlroots-style ones). Tries, in order: DankMaterialShell,
    awww/swww, the compositor's own tool, then swaybg."""
    if _dms_running(run_):
        # DMS draws the wallpaper itself and its lock screen shows the same image.
        run_(["dms", "ipc", "call", "wallpaper", "set", str(path)])
        result.done += [DESKTOP, LOCK] if target == BOTH else [target]
        if target != BOTH:
            result.notes.append("DankMaterialShell uses the same image for the desktop and lock screen.")
        return
    if target in (DESKTOP, BOTH):
        errors: List[str] = []
        for setter in _wayland_setters(path, name):
            try:
                setter(run_)
                break
            except WallpaperError as e:
                errors.append(str(e))
        else:
            hint = (
                f"Couldn't set the wallpaper on {LABELS.get(name, name)}. Install swaybg, awww (swww) "
                "or run DankMaterialShell, or set custom_command in ~/.config/bing-wallpaper/config.json."
            )
            raise WallpaperError(hint + ("\n" + "\n".join(errors) if errors else ""))
        result.done.append(DESKTOP)
    if target in (LOCK, BOTH):
        result.notes.append(_lock_link_note(LOCK_LABELS.get(name, LABELS.get(name, name))))


LABELS = {"niri": "niri", "sway": "Sway", "hyprland": "Hyprland", "wayland": "this desktop"}
LOCK_LABELS = {"hyprland": "Hyprland (hyprlock)"}


def _wayland_setters(path: Path, name: str) -> List[Callable[[Runner], None]]:
    p = str(path)
    setters: List[Callable[[Runner], None]] = []
    # swww was renamed awww; both need their daemon running.
    for tool in ("awww", "swww"):
        if shutil.which(tool):
            setters.append(lambda r, tool=tool: r([tool, "img", p]))
    if name == "sway" and shutil.which("swaymsg"):
        setters.append(lambda r: r(["swaymsg", "output", "*", "bg", p, "fill"]))
    if name == "hyprland" and shutil.which("hyprctl"):
        def hyprpaper(r: Runner) -> None:
            r(["hyprctl", "hyprpaper", "preload", p])
            r(["hyprctl", "hyprpaper", "wallpaper", f",{p}"])
        setters.append(hyprpaper)
    if shutil.which("swaybg"):
        setters.append(lambda r: spawn_swaybg(path))
    return setters


def _set_generic(path: Path, target: str, run_: Runner, result: Result) -> None:
    if os.environ.get("WAYLAND_DISPLAY") or _dms_running(run_):
        _set_wayland(path, target, run_, result, "wayland")
        return
    if target in (DESKTOP, BOTH):
        if shutil.which("feh"):
            run_(["feh", "--bg-fill", str(path)])
        elif shutil.which("nitrogen"):
            run_(["nitrogen", "--set-zoom-fill", "--save", str(path)])
        else:
            raise WallpaperError(
                "Don't know how to set the wallpaper on this desktop. Set custom_command in "
                "~/.config/bing-wallpaper/config.json, e.g. \"feh --bg-fill {path}\"."
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
    "sway": lambda p, t, r, res: _set_wayland(p, t, r, res, "sway"),
    "hyprland": lambda p, t, r, res: _set_wayland(p, t, r, res, "hyprland"),
    "niri": lambda p, t, r, res: _set_wayland(p, t, r, res, "niri"),
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
