"""GTK 4 window: today's image, daily updates, region, and a gallery of the latest images."""

from __future__ import annotations

import sys
import threading
from typing import Callable, List, Optional

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk, Pango  # noqa: E402

from . import APP_ID, bing, core, desktop, schedule, settings  # noqa: E402

TARGET_LABELS = [
    (desktop.DESKTOP, "Desktop"),
    (desktop.LOCK, "Lock screen"),
    (desktop.BOTH, "Both"),
]


def _in_background(work: Callable[[], object], done: Callable[[object, Optional[Exception]], None]) -> None:
    """Runs `work` off the UI thread and hands its result (or error) to `done` on it."""

    def runner() -> None:
        try:
            value, error = work(), None
        except Exception as e:  # shown to the user
            value, error = None, e
        GLib.idle_add(lambda: (done(value, error), False)[1])

    threading.Thread(target=runner, daemon=True).start()


class Window(Gtk.ApplicationWindow):
    def __init__(
        self,
        app: Gtk.Application,
        fetch_latest: Callable[[str], List[bing.BingImage]] = bing.fetch_latest,
        fetch_thumbnail: Callable[[bing.BingImage], Optional[str]] = lambda i: (
            str(p) if (p := core.thumbnail(i)) else None
        ),
        apply: Callable[..., desktop.Result] = core.apply,
    ) -> None:
        super().__init__(application=app, title="Bing Wallpaper")
        self.set_default_size(860, 680)
        self.fetch_latest = fetch_latest
        self.fetch_thumbnail = fetch_thumbnail
        self.apply_image = apply
        self.cfg = settings.Settings()
        self.images: List[bing.BingImage] = []
        self.apply_after_load = False

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for side in ("top", "bottom", "start", "end"):
            getattr(outer, f"set_margin_{side}")(18)

        # Today's image and daily updates
        top = Gtk.Box(spacing=12)
        self.today_button = Gtk.Button(label="Set today's image now")
        self.today_button.add_css_class("suggested-action")
        self.today_button.connect("clicked", self.on_today)
        top.append(self.today_button)

        spacer = Gtk.Box(hexpand=True)
        top.append(spacer)

        top.append(Gtk.Label(label="Update daily"))
        self.daily_switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.daily_switch.set_active(bool(self.cfg.get("daily")))
        self.daily_switch.connect("notify::active", self.on_daily)
        top.append(self.daily_switch)
        outer.append(top)

        # Region
        region = Gtk.Box(spacing=12)
        region.append(Gtk.Label(label="Bing region"))
        system = bing.system_market()
        self.market_codes: List[Optional[str]] = [None] + [c for c, _ in bing.MARKETS]
        names = [f"Automatic ({bing.market_name(system)})"] + [n for _, n in bing.MARKETS]
        self.region_dropdown = Gtk.DropDown.new_from_strings(names)
        chosen = self.cfg.chosen_market
        self.region_dropdown.set_selected(self.market_codes.index(chosen) if chosen in self.market_codes else 0)
        self.region_dropdown.connect("notify::selected", self.on_region)
        region.append(self.region_dropdown)
        outer.append(region)

        heading = Gtk.Label(label="Latest images", xalign=0)
        heading.add_css_class("title-4")
        outer.append(heading)

        self.flow = Gtk.FlowBox(
            selection_mode=Gtk.SelectionMode.NONE,
            homogeneous=True,
            min_children_per_line=1,
            max_children_per_line=4,
            row_spacing=12,
            column_spacing=12,
            valign=Gtk.Align.START,
        )
        scroller = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroller.set_child(self.flow)
        outer.append(scroller)

        self.status = Gtk.Label(xalign=0, wrap=True)
        self.status.add_css_class("dim-label")
        outer.append(self.status)

        self.set_child(outer)
        self.reload()
        if self.cfg.get("daily"):
            # Opening the app once is enough to start daily updates.
            _in_background(lambda: schedule.enabled() or schedule.enable(), lambda v, e: None)

    # -- gallery ---------------------------------------------------------------

    def reload(self) -> None:
        child = self.flow.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.flow.remove(child)
            child = nxt
        self.set_status("Loading the latest Bing images...")
        market = self.cfg.market
        _in_background(lambda: self.fetch_latest(market), self.on_loaded)

    def on_loaded(self, images: object, error: Optional[Exception]) -> None:
        if error is not None:
            self.set_status(f"Couldn't reach Bing: {error}")
            return
        self.images = list(images)  # type: ignore[arg-type]
        state = settings.State()
        for image in self.images:
            self.flow.append(self.card(image, current=image.id == state.get("last_applied")))
        self.set_status(f"Bing region: {bing.market_name(self.cfg.market)}. Click an image to use it.")
        if self.apply_after_load and self.images:
            self.apply_after_load = False
            self.apply_in_background(self.images[0], self.cfg.get("daily_target") or desktop.BOTH)

    def card(self, image: bing.BingImage, current: bool) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        picture = Gtk.Picture(can_shrink=True)
        picture.set_size_request(200, 112)
        if hasattr(picture, "set_content_fit"):  # GTK 4.8+
            picture.set_content_fit(Gtk.ContentFit.COVER)
        box.append(picture)
        title = Gtk.Label(label=image.title or image.id, wrap=True, xalign=0, lines=2,
                          ellipsize=Pango.EllipsizeMode.END)
        box.append(title)
        date = Gtk.Label(label=image.nice_date + ("  (current)" if current else ""), xalign=0)
        date.add_css_class("dim-label")
        box.append(date)

        button = Gtk.Button(child=box, tooltip_text=image.copyright)
        button.add_css_class("flat")
        button.connect("clicked", lambda b: self.ask_target(b, image))

        def show(path: object, error: Optional[Exception]) -> None:
            if path:
                picture.set_filename(str(path))

        _in_background(lambda: self.fetch_thumbnail(image), show)
        return button

    def ask_target(self, anchor: Gtk.Widget, image: bing.BingImage) -> None:
        popover = Gtk.Popover()
        menu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        menu.append(Gtk.Label(label="Use this image on"))
        for target, label in TARGET_LABELS:
            item = Gtk.Button(label=label)
            item.add_css_class("flat")

            def picked(_b: Gtk.Button, target: str = target) -> None:
                popover.popdown()
                self.apply_in_background(image, target)

            item.connect("clicked", picked)
            menu.append(item)
        popover.set_child(menu)
        popover.set_parent(anchor)
        popover.connect("closed", lambda p: GLib.idle_add(lambda: (p.unparent(), False)[1]))
        popover.popup()

    # -- actions ---------------------------------------------------------------

    def apply_in_background(self, image: bing.BingImage, target: str) -> None:
        newest = self.images[0].id if self.images else None
        self.set_status(f"Setting {image.title or image.id}...")

        def done(result: object, error: Optional[Exception]) -> None:
            if error is not None:
                self.set_status(f"Couldn't set the wallpaper: {error}")
                return
            notes = " ".join(result.notes)  # type: ignore[attr-defined]
            self.set_status(f"Wallpaper set: {image.title or image.id}. {notes}".strip())
            self.reload_marks(image.id)

        _in_background(lambda: self.apply_image(image, target, self.cfg, newest_id=newest), done)

    def reload_marks(self, current_id: str) -> None:
        # Cheap way to move the "(current)" mark: rebuild the cards from the loaded list.
        child = self.flow.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.flow.remove(child)
            child = nxt
        for image in self.images:
            self.flow.append(self.card(image, current=image.id == current_id))

    def on_today(self, _button: Gtk.Button) -> None:
        if self.images:
            self.apply_in_background(self.images[0], desktop.BOTH)
        else:
            self.set_status("Still loading the latest image...")

    def on_daily(self, switch: Gtk.Switch, _pspec: object) -> None:
        on = switch.get_active()
        self.cfg.set("daily", on)
        error = schedule.enable() if on else schedule.disable()
        if error:
            self.set_status(error)
        else:
            self.set_status("Daily updates are on." if on else "Daily updates are off.")

    def on_region(self, dropdown: Gtk.DropDown, _pspec: object) -> None:
        code = self.market_codes[dropdown.get_selected()]
        if code == self.cfg.chosen_market:
            return
        self.cfg.set("market", code)
        # Like the daily update would, switch to the new region's image of the day.
        self.apply_after_load = bool(self.cfg.get("daily"))
        self.reload()

    def set_status(self, text: str) -> None:
        self.status.set_text(text)


class App(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID)

    def do_activate(self) -> None:
        window = self.get_active_window() or Window(self)
        window.present()


def main(argv: Optional[List[str]] = None) -> int:
    return App().run([sys.argv[0]] + list(argv or []))
