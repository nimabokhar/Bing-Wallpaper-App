"""Command line interface: `bing-wallpaper --help`."""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional

from . import __version__, bing, core, desktop, schedule, settings


def _print_result(result: desktop.Result, image: bing.BingImage) -> None:
    where = " and ".join("lock screen" if t == desktop.LOCK else "desktop" for t in result.done)
    print(f"Set {where or 'nothing'} to: {image.title or image.id} ({image.nice_date})")
    if image.copyright:
        print(f"  {image.copyright}")
    for note in result.notes:
        print(f"Note: {note}")


def cmd_update(args: argparse.Namespace) -> int:
    if args.login:
        return at_login()
    image = core.update(force=args.force)
    if image is None:
        if not args.quiet:
            print("Already showing the latest Bing image.")
    elif not args.quiet:
        print(f"Applied {image.title or image.id} ({image.nice_date})")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    cfg = settings.Settings()
    state = settings.State()
    print(f"Latest Bing images for {bing.market_name(cfg.market)}:")
    for i, image in enumerate(core.latest(cfg), 1):
        mark = "*" if image.id == state.get("last_applied") else " "
        print(f"{mark}{i}. {image.nice_date}  {image.title}")
    return 0


def cmd_set(args: argparse.Namespace) -> int:
    cfg = settings.Settings()
    images = core.latest(cfg)
    if not 1 <= args.number <= len(images):
        print(f"Pick a number from 1 to {len(images)} (see `bing-wallpaper list`).", file=sys.stderr)
        return 2
    image = images[args.number - 1]
    result = core.apply(image, args.on, cfg, newest_id=images[0].id)
    _print_result(result, image)
    return 0


def cmd_region(args: argparse.Namespace) -> int:
    cfg = settings.Settings()
    if args.list:
        for code, name in bing.MARKETS:
            print(f"{code}  {name}")
        return 0
    if args.code is None:
        if cfg.chosen_market:
            print(f"{cfg.market} ({bing.market_name(cfg.market)})")
        else:
            print(f"Automatic: {cfg.market} ({bing.market_name(cfg.market)})")
        return 0
    if args.code.lower() in ("auto", "automatic"):
        cfg.set("market", None)
    else:
        match = [c for c, _ in bing.MARKETS if c.lower() == args.code.lower()]
        if not match:
            print(f"Unknown region {args.code}. See `bing-wallpaper region --list`.", file=sys.stderr)
            return 2
        cfg.set("market", match[0])
    print(f"Region set to {bing.market_name(cfg.market)}. Applying its image of the day...")
    image = core.update(force=True)
    if image:
        print(f"Applied {image.title or image.id}")
    return 0


def _when(cfg: settings.Settings) -> str:
    t = cfg.get("daily_time")
    return f"at {t}" if t else "as soon as Bing publishes a new image"


def cmd_daily(args: argparse.Namespace) -> int:
    cfg = settings.Settings()
    if args.state is None:
        on = cfg.get("daily") and schedule.enabled()
        print(f"on, {_when(cfg)}" if on else "off")
        return 0
    if args.state == "at":
        if not args.time:
            print("Give a time like 07:30, or \"auto\" for as soon as Bing publishes.", file=sys.stderr)
            return 2
        daily_time = None if args.time.lower() in ("auto", "asap") else schedule.parse_time(args.time)
        if daily_time is None and args.time.lower() not in ("auto", "asap"):
            print(f"{args.time} isn't a time. Use 24-hour HH:MM, e.g. 07:30.", file=sys.stderr)
            return 2
        error = core.set_daily_time(daily_time)
        if not error and cfg.get("daily") and not schedule.enabled():
            error = schedule.enable()
        if error:
            print(error, file=sys.stderr)
            return 1
        print(f"The wallpaper will change {_when(settings.Settings())}.")
        return 0
    on = args.state == "on"
    cfg.set("daily", on)
    error = schedule.enable() if on else schedule.disable()
    if error:
        print(error, file=sys.stderr)
        return 1
    print(f"Daily updates are on, {_when(cfg)}." if on else "Daily updates are off.")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    cfg = settings.Settings()
    state = settings.State()
    print(f"Desktop:        {core.current_desktop(state)}")
    print(f"Region:         {bing.market_name(cfg.market)}{'' if cfg.chosen_market else ' (automatic)'}")
    daily_on = cfg.get("daily") and schedule.enabled()
    print(f"Daily updates:  {'on, ' + _when(cfg) if daily_on else 'off'}")
    print(f"Current image:  {state.get('last_title') or state.get('last_applied') or 'none yet'}")
    print(f"Images folder:  {settings.data_dir()}")
    return 0


def at_login() -> int:
    """Runs at login: makes sure the timer is on (if daily updates are wanted) and
    applies a new image straight away, from inside the session."""
    cfg = settings.Settings()
    if not cfg.get("daily"):
        return 0
    if not schedule.enabled():
        schedule.enable()
    try:
        core.update()
    except Exception as e:  # offline at login, etc.; the timer retries later
        print(f"bing-wallpaper: {e}", file=sys.stderr)
    return 0


def cmd_gui(args: argparse.Namespace) -> int:
    try:
        from . import gui
    except (ImportError, ValueError) as e:
        print(
            f"The window needs GTK 4 and PyGObject ({e}).\n"
            "Install python3-gi + gir1.2-gtk-4.0 (Debian), python3-gobject + gtk4 (Fedora) "
            "or python-gobject + gtk4 (Arch), or use the commands in `bing-wallpaper --help`.",
            file=sys.stderr,
        )
        return 1
    return gui.main([])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bing-wallpaper",
        description="Sets your desktop and lock screen wallpaper to the Bing image of the day. "
        "Run without a command to open the window.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    p = sub.add_parser("update", help="apply today's image if it is new (what the daily timer runs)")
    p.add_argument("--force", action="store_true", help="apply today's image even if already applied")
    p.add_argument("--quiet", "-q", action="store_true")
    p.add_argument("--login", action="store_true", help=argparse.SUPPRESS)
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("list", help="show the latest Bing images")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("set", help="set one of the latest images (1 = today)")
    p.add_argument("number", type=int, nargs="?", default=1)
    p.add_argument("--on", choices=desktop.TARGETS, default=desktop.BOTH,
                   help="desktop, lock screen, or both (default)")
    p.set_defaults(func=cmd_set)

    p = sub.add_parser("region", help="show or set the Bing region (a code like en-GB, or auto)")
    p.add_argument("code", nargs="?")
    p.add_argument("--list", action="store_true", help="list the regions")
    p.set_defaults(func=cmd_region)

    p = sub.add_parser("daily", help="turn daily updates on or off, or set their time: daily at 07:30")
    p.add_argument("state", nargs="?", choices=("on", "off", "at"))
    p.add_argument("time", nargs="?", help='HH:MM (24-hour), or "auto" for as soon as Bing publishes')
    p.set_defaults(func=cmd_daily)

    p = sub.add_parser("status", help="show the current settings")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("gui", help="open the window")
    p.set_defaults(func=cmd_gui)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
            return cmd_gui(args)
        parser.print_help()
        return 0
    try:
        return args.func(args)
    except desktop.WallpaperError as e:
        print(f"Couldn't set the wallpaper: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"Couldn't reach Bing: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
