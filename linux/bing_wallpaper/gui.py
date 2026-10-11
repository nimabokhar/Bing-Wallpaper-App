"""The window: today's image as a hero, daily change settings, and a scrolling gallery.

Built with GTK 4 and libadwaita, so it follows the system's light/dark style and accent
colour. To stay smooth, everything slow (Bing requests, downloads, decoding) runs off
the UI thread, images are decoded at the size they are shown, and decoded images are
kept in a small in-memory cache on top of the disk cache.
"""

from __future__ import annotations

import sys
import threading
import time
from collections import OrderedDict
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable, List, Optional, Tuple

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Adw, Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango  # noqa: E402

from . import APP_ID, __version__, bing, core, desktop, imagecache, schedule, settings  # noqa: E402

TARGET_LABELS = [
    (desktop.BOTH, "Desktop and lock screen"),
    (desktop.DESKTOP, "Desktop only"),
    (desktop.LOCK, "Lock screen only"),
]
THEMES = [("system", "System"), ("light", "Light"), ("dark", "Dark")]
WHEN_OPTIONS = ["As soon as Bing publishes", "At a set time"]

#: Gallery cards are wide, at the wallpaper's 16:9 shape, and always this size so
#: loading an image never changes the layout.
CARD_WIDTH, CARD_HEIGHT = 400, 225
CARD_IMAGE = "1280x720"
#: The hero is decoded at this width; GTK scales it the rest of the way.
HERO_DECODE_WIDTH = 1600
FADE_MS = 180

CSS = b"""
.hero { border-radius: 0 0 24px 24px; background-color: alpha(currentColor, 0.08); }
.card { border-radius: 16px; background-color: alpha(currentColor, 0.08); }
.scrim { background-image: linear-gradient(to bottom, alpha(black, 0), alpha(black, 0.72)); }
.on-image { color: white; }
.on-image-dim { color: alpha(white, 0.82); }
.hero-title { font-size: 28px; font-weight: 800; }
.card-title { font-weight: 700; }
.card-button { padding: 0; border-radius: 16px; }
"""


def _in_background(work: Callable[[], object], done: Callable[[object, Optional[Exception]], None]) -> None:
    """Runs `work` off the UI thread and hands its result (or error) to `done` on it."""

    def runner() -> None:
        try:
            value, error = work(), None
        except Exception as e:  # shown to the user
            value, error = None, e
        # Default priority, not idle: idle callbacks wait behind every redraw.
        GLib.idle_add(lambda: (done(value, error), False)[1], priority=GLib.PRIORITY_DEFAULT)

    threading.Thread(target=runner, daemon=True).start()


def _ago(timestamp: float, now: Optional[float] = None) -> str:
    seconds = max(0, (now or time.time()) - timestamp)
    if seconds < 60:
        return "just now"
    for size, unit in ((86400, "day"), (3600, "hour"), (60, "minute")):
        if seconds >= size:
            n = int(seconds // size)
            return f"{n} {unit}{'' if n == 1 else 's'} ago"
    return "just now"


def _short_date(image: bing.BingImage) -> str:
    try:
        return time.strftime("%b %-d", time.strptime(image.start_date, "%Y%m%d"))
    except ValueError:
        return image.nice_date


class TextureLoader:
    """Hands out Gdk.Textures decoded at display size, on the UI thread.

    Downloads go through the shared DiskCache (deduplicated, 4 at a time), decoding
    happens on a separate small pool, and the last few dozen textures stay in memory.
    """

    def __init__(self, disk: imagecache.DiskCache, keep: int = 64) -> None:
        self.disk = disk
        self.decoder = ThreadPoolExecutor(max_workers=2, thread_name_prefix="bing-decode")
        self.memory: "OrderedDict[Tuple[str, int, int], Gdk.Texture]" = OrderedDict()
        self.keep = keep

    def load(self, url: str, width: int, height: int, done: Callable[[Optional[Gdk.Texture]], None]) -> None:
        key = (url, width, height)
        texture = self.memory.get(key)
        if texture is not None:
            self.memory.move_to_end(key)
            done(texture)
            return

        def decode(downloaded: Future) -> None:
            try:
                path = downloaded.result()
                # Scale to cover width x height, keeping the aspect ratio.
                _fmt, w, h = GdkPixbuf.Pixbuf.get_file_info(str(path))
                scale = max(width / w, height / h) if w and h else 1
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(path), max(1, int(w * scale)), max(1, int(h * scale)), True
                )
            except Exception:
                GLib.idle_add(lambda: (done(None), False)[1], priority=GLib.PRIORITY_DEFAULT)
                return

            def hand_over() -> bool:
                texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                self.memory[key] = texture
                while len(self.memory) > self.keep:
                    self.memory.popitem(last=False)
                done(texture)
                return False

            GLib.idle_add(hand_over, priority=GLib.PRIORITY_DEFAULT)

        self.disk.get(url).add_done_callback(lambda f: self.decoder.submit(decode, f))


def _switch_row(title: str, subtitle: str) -> Tuple[Gtk.Widget, Callable[[], bool], Callable[[bool], None], Callable]:
    """An Adw.SwitchRow, or an ActionRow with a Gtk.Switch on libadwaita before 1.4.
    Returns (row, get, set, connect(callback))."""
    if hasattr(Adw, "SwitchRow"):
        row = Adw.SwitchRow(title=title, subtitle=subtitle)
        return (row, row.get_active, row.set_active,
                lambda cb: row.connect("notify::active", lambda *a: cb(row.get_active())))
    row = Adw.ActionRow(title=title, subtitle=subtitle)
    switch = Gtk.Switch(valign=Gtk.Align.CENTER)
    row.add_suffix(switch)
    row.set_activatable_widget(switch)
    return (row, switch.get_active, switch.set_active,
            lambda cb: switch.connect("notify::active", lambda *a: cb(switch.get_active())))


class Window(Adw.ApplicationWindow):
    def __init__(
        self,
        app: Gtk.Application,
        fetch_page: Callable[[str, int], List[bing.BingImage]] = bing.fetch_page,
        apply: Callable[..., desktop.Result] = core.apply,
        set_daily_time: Callable[[Optional[str]], str] = core.set_daily_time,
        disk: Optional[imagecache.DiskCache] = None,
    ) -> None:
        super().__init__(application=app, title="Bing Wallpaper")
        self.set_default_size(1100, 880)
        self.fetch_page = fetch_page
        self.apply_image = apply
        self.set_daily_time = set_daily_time
        self.disk = disk or imagecache.DiskCache()
        self.textures = TextureLoader(self.disk)
        self.cfg = settings.Settings()
        self.images: List[bing.BingImage] = []
        self.loading = False
        self.exhausted = False
        self.generation = 0
        self.apply_after_load = False
        self.applying = 0
        self.last_message = ""
        self.when_timeout = 0
        self.prefs: Optional[Gtk.Widget] = None

        self.toasts = Adw.ToastOverlay()
        view = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        header = Adw.HeaderBar()
        prefs_button = Gtk.Button(icon_name="emblem-system-symbolic", tooltip_text="Settings")
        prefs_button.connect("clicked", lambda b: self.open_preferences())
        header.pack_end(prefs_button)
        self.prefs_button = prefs_button
        view.append(header)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        content.append(self.build_hero())

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18,
                       margin_start=24, margin_end=24, margin_bottom=24)
        body.append(self.build_daily_card())
        heading = Gtk.Label(label="Recent images", xalign=0)
        heading.add_css_class("title-3")
        body.append(heading)
        self.grid = Gtk.FlowBox(
            selection_mode=Gtk.SelectionMode.NONE,
            homogeneous=True,
            min_children_per_line=1,
            max_children_per_line=4,
            row_spacing=14,
            column_spacing=14,
            valign=Gtk.Align.START,
        )
        body.append(self.grid)
        self.end_label = Gtk.Label(xalign=0.5)
        self.end_label.add_css_class("dim-label")
        body.append(self.end_label)
        content.append(body)

        self.scroller = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.scroller.set_child(content)
        # Infinite scroll: reaching the bottom loads older images.
        self.scroller.connect("edge-reached", self.on_edge_reached)
        view.append(self.scroller)

        self.toasts.set_child(view)
        self.set_content(self.toasts)
        self.connect("notify::default-height", lambda *a: self.size_hero())
        self.size_hero()

        self.reload()
        _in_background(self.disk.prune, lambda v, e: None)
        if self.cfg.get("daily"):
            # Opening the app once is enough to start daily updates.
            _in_background(lambda: schedule.enabled() or schedule.enable(), lambda v, e: None)

    # -- building blocks -------------------------------------------------------

    def build_hero(self) -> Gtk.Widget:
        overlay = Gtk.Overlay()
        overlay.add_css_class("hero")
        overlay.set_overflow(Gtk.Overflow.HIDDEN)
        self.hero_picture = Gtk.Picture(can_shrink=True, hexpand=True)
        if hasattr(self.hero_picture, "set_content_fit"):  # GTK 4.8+
            self.hero_picture.set_content_fit(Gtk.ContentFit.COVER)
        self.hero_reveal = Gtk.Revealer(transition_type=Gtk.RevealerTransitionType.CROSSFADE,
                                        transition_duration=FADE_MS, child=self.hero_picture)
        overlay.set_child(self.hero_reveal)

        scrim = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, valign=Gtk.Align.END)
        scrim.add_css_class("scrim")
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                        margin_start=28, margin_end=28, margin_top=48, margin_bottom=24)
        self.hero_date = Gtk.Label(xalign=0, label="Today")
        self.hero_date.add_css_class("on-image-dim")
        self.hero_title = Gtk.Label(xalign=0, wrap=True, label="Loading today's image…")
        self.hero_title.add_css_class("on-image")
        self.hero_title.add_css_class("hero-title")
        self.hero_copyright = Gtk.Label(xalign=0, wrap=True, ellipsize=Pango.EllipsizeMode.END, lines=2)
        self.hero_copyright.add_css_class("on-image-dim")
        self.set_button = Gtk.Button(label="Set as wallpaper", halign=Gtk.Align.START, margin_top=8)
        self.set_button.add_css_class("suggested-action")
        self.set_button.add_css_class("pill")
        self.set_button.set_sensitive(False)
        self.set_button.connect("clicked", self.on_set_today)
        for widget in (self.hero_date, self.hero_title, self.hero_copyright, self.set_button):
            inner.append(widget)
        scrim.append(inner)
        overlay.add_overlay(scrim)

        click = Gtk.GestureClick()
        click.connect("released", lambda g, n, x, y: self.images and self.ask_target(self.hero_picture, self.images[0]))
        self.hero_picture.add_controller(click)
        self.hero = overlay
        return overlay

    def size_hero(self) -> None:
        height = self.get_default_size()[1] or 820
        self.hero.set_size_request(-1, max(320, int(height * 0.55)))

    def build_daily_card(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        group = Adw.PreferencesGroup(title="Daily change")

        row, self.daily_get, self.daily_set, connect = _switch_row("Change every day", "Desktop and lock screen")
        self.daily_set(bool(self.cfg.get("daily")))
        connect(self.on_daily)
        self.daily_row = row
        group.add(row)

        self.when_row = Adw.ComboRow(title="Change at", model=Gtk.StringList.new(WHEN_OPTIONS))
        self.when_row.set_selected(1 if self.cfg.get("daily_time") else 0)
        self.when_row.connect("notify::selected", lambda *a: self.on_when_changed())
        group.add(self.when_row)

        self.time_row = Adw.ActionRow(title="Time")
        daily_time = self.cfg.get("daily_time") or "07:00"
        hour, minute = map(int, daily_time.split(":"))
        self.hour_spin = Gtk.SpinButton.new_with_range(0, 23, 1)
        self.minute_spin = Gtk.SpinButton.new_with_range(0, 59, 5)
        time_box = Gtk.Box(spacing=4, valign=Gtk.Align.CENTER)
        for spin, value in ((self.hour_spin, hour), (self.minute_spin, minute)):
            spin.set_wrap(True)
            spin.set_value(value)
            spin.connect("output", self.on_spin_output)
            spin.connect("value-changed", lambda *a: self.on_when_changed())
        time_box.append(self.hour_spin)
        time_box.append(Gtk.Label(label=":"))
        time_box.append(self.minute_spin)
        self.time_row.add_suffix(time_box)
        self.time_row.set_visible(bool(self.cfg.get("daily_time")))
        group.add(self.time_row)
        box.append(group)

        self.last_set = Gtk.Label(xalign=0, wrap=True, margin_start=4)
        self.last_set.add_css_class("dim-label")
        self.last_set.add_css_class("caption")
        box.append(self.last_set)
        self.progress = Gtk.ProgressBar(visible=False)
        box.append(self.progress)
        self.update_last_set()
        return box

    def card(self, image: bing.BingImage) -> Gtk.Widget:
        overlay = Gtk.Overlay()
        overlay.add_css_class("card")
        overlay.set_overflow(Gtk.Overflow.HIDDEN)
        overlay.set_size_request(CARD_WIDTH, CARD_HEIGHT)
        picture = Gtk.Picture(can_shrink=True)
        if hasattr(picture, "set_content_fit"):
            picture.set_content_fit(Gtk.ContentFit.COVER)
        reveal = Gtk.Revealer(transition_type=Gtk.RevealerTransitionType.CROSSFADE,
                              transition_duration=FADE_MS, child=picture)
        overlay.set_child(reveal)

        scrim = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, valign=Gtk.Align.END)
        scrim.add_css_class("scrim")
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2,
                        margin_start=12, margin_end=12, margin_top=32, margin_bottom=12)
        title = Gtk.Label(label=image.title or image.id, xalign=0, wrap=True, lines=2,
                          ellipsize=Pango.EllipsizeMode.END, max_width_chars=40)
        title.add_css_class("on-image")
        title.add_css_class("card-title")
        date = Gtk.Label(label=_short_date(image), xalign=0)
        date.add_css_class("on-image-dim")
        date.add_css_class("caption")
        inner.append(title)
        inner.append(date)
        scrim.append(inner)
        overlay.add_overlay(scrim)

        # Fixed size, centred in its column, so the image keeps its 16:9 shape.
        # The clamp stops the full-resolution texture from widening the card.
        clamp = Adw.Clamp(maximum_size=CARD_WIDTH, tightening_threshold=CARD_WIDTH, child=overlay)
        button = Gtk.Button(child=clamp, tooltip_text=image.copyright, halign=Gtk.Align.CENTER)
        button.add_css_class("flat")
        button.add_css_class("card-button")
        button.connect("clicked", lambda b: self.ask_target(b, image))

        def show(texture: Optional[Gdk.Texture]) -> None:
            if texture is not None:
                picture.set_paintable(texture)
                reveal.set_reveal_child(True)

        self.textures.load(image.url_for(CARD_IMAGE), CARD_WIDTH * 2, CARD_HEIGHT * 2, show)
        return button

    # -- gallery ---------------------------------------------------------------

    def reload(self) -> None:
        child = self.grid.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.grid.remove(child)
            child = nxt
        self.images = []
        self.exhausted = False
        self.loading = False
        self.end_label.set_text("")
        self.hero_reveal.set_reveal_child(False)
        self.set_button.set_sensitive(False)
        # Results from a request made before a region change are dropped.
        self.generation += 1
        self.load_more()

    def load_more(self) -> None:
        if self.loading or self.exhausted:
            return
        self.loading = True
        self.end_label.set_text("Loading…")
        market, have, generation = self.cfg.market, len(self.images), self.generation
        _in_background(lambda: self.fetch_page(market, have),
                       lambda images, error: self.on_loaded(images, error, generation))

    def on_edge_reached(self, _scroller: Gtk.ScrolledWindow, position: Gtk.PositionType) -> None:
        if position == Gtk.PositionType.BOTTOM:
            self.load_more()

    def fill_window(self) -> bool:
        """Keeps loading while the end of the gallery is on screen (or nearly), since a
        short page never reaches the bottom edge to trigger the next one."""
        adj = self.scroller.get_vadjustment()
        if adj.get_value() + adj.get_page_size() >= adj.get_upper() - CARD_HEIGHT:
            self.load_more()
        return False

    def on_loaded(self, images: object, error: Optional[Exception], generation: int = 0) -> None:
        if generation != self.generation:
            return
        self.loading = False
        self.end_label.set_text("")
        if error is not None:
            if not self.images:
                self.hero_title.set_text("Couldn't reach Bing")
            self.toast(f"Couldn't reach Bing: {error}")
            return
        seen = {i.id for i in self.images}
        new = [i for i in images if i.id not in seen]  # type: ignore[union-attr]
        if not new:
            self.exhausted = True
            self.end_label.set_text("That's every image Bing still has, about two weeks.")
            return
        first_page = not self.images
        self.images += new
        # Start downloading the thumbnails now, before their cards scroll into view.
        for image in new:
            self.disk.prefetch(image.url_for(CARD_IMAGE))
        if first_page:
            self.show_hero(new[0])
            new = new[1:]  # today's image is the hero; the grid starts from yesterday
        for image in new:
            self.grid.append(self.card(image))
        if first_page and self.apply_after_load:
            self.apply_after_load = False
            self.apply_in_background(self.images[0], self.cfg.get("daily_target") or desktop.BOTH)
        GLib.idle_add(self.fill_window)

    def show_hero(self, image: bing.BingImage) -> None:
        self.hero_date.set_text(f"Today · {_short_date(image)}")
        self.hero_title.set_text(image.title or image.id)
        self.hero_copyright.set_text(image.copyright)
        self.set_button.set_sensitive(True)

        def show(texture: Optional[Gdk.Texture]) -> None:
            if texture is not None:
                self.hero_picture.set_paintable(texture)
                self.hero_reveal.set_reveal_child(True)

        self.textures.load(image.hd_url, HERO_DECODE_WIDTH, HERO_DECODE_WIDTH * 9 // 16, show)

    def ask_target(self, anchor: Gtk.Widget, image: bing.BingImage) -> None:
        popover = Gtk.Popover()
        menu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        header = Gtk.Label(label="Set on", xalign=0, margin_start=8, margin_top=4, margin_bottom=4)
        header.add_css_class("heading")
        menu.append(header)
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
        self.start_progress()

        def done(result: object, error: Optional[Exception]) -> None:
            self.stop_progress()
            if error is not None:
                self.toast(f"Couldn't set the wallpaper: {error}")
                return
            notes = " ".join(result.notes)  # type: ignore[attr-defined]
            self.toast(f"Wallpaper set: {image.title or image.id}")
            if notes:
                self.toast(notes)
            self.update_last_set()

        _in_background(lambda: self.apply_image(image, target, self.cfg, newest_id=newest), done)

    def start_progress(self) -> None:
        self.applying += 1
        self.progress.set_visible(True)
        if self.applying == 1:
            def pulse() -> bool:
                if self.applying:
                    self.progress.pulse()
                    return True
                return False

            GLib.timeout_add(120, pulse)

    def stop_progress(self) -> None:
        self.applying = max(0, self.applying - 1)
        if not self.applying:
            self.progress.set_visible(False)

    def update_last_set(self) -> None:
        state = settings.State()
        title = state.get("last_title") or state.get("last_applied")
        if not title:
            self.last_set.set_text("No wallpaper set yet.")
            return
        when = state.get("last_applied_at")
        self.last_set.set_text(f"Last set: {title}" + (f" ({_ago(when)})" if when else ""))

    def on_set_today(self, _button: Gtk.Button) -> None:
        if self.images:
            self.apply_in_background(self.images[0], desktop.BOTH)

    def on_daily(self, on: bool) -> None:
        if on == bool(self.cfg.get("daily")) and on == schedule.enabled():
            return
        self.cfg.set("daily", on)

        def done(error: object, exc: Optional[Exception]) -> None:
            if exc is not None or error:
                self.toast(f"Couldn't change daily updates: {exc or error}")

        _in_background(lambda: schedule.enable() if on else schedule.disable(), done)

    @staticmethod
    def on_spin_output(spin: Gtk.SpinButton) -> bool:
        spin.set_text(f"{int(spin.get_value()):02d}")
        return True

    def chosen_time(self) -> Optional[str]:
        if self.when_row.get_selected() == 0:
            return None
        return f"{int(self.hour_spin.get_value()):02d}:{int(self.minute_spin.get_value()):02d}"

    def on_when_changed(self) -> None:
        self.time_row.set_visible(self.when_row.get_selected() == 1)
        # Wait until the user stops clicking the spin buttons before rewriting the timer.
        if self.when_timeout:
            GLib.source_remove(self.when_timeout)
        self.when_timeout = GLib.timeout_add(700, self.save_when)

    def save_when(self) -> bool:
        self.when_timeout = 0
        daily_time = self.chosen_time()
        if daily_time == self.cfg.get("daily_time"):
            return False
        self.cfg.values["daily_time"] = daily_time

        def done(error: object, exc: Optional[Exception]) -> None:
            if exc is not None or error:
                self.toast(f"Couldn't change the schedule: {exc or error}")
            elif daily_time:
                self.toast(f"The wallpaper will change every day at {daily_time}")
            else:
                self.toast("The wallpaper will change as soon as Bing publishes a new image")

        _in_background(lambda: self.set_daily_time(daily_time), done)
        return False

    # -- preferences -------------------------------------------------------------

    def open_preferences(self) -> None:
        page = Adw.PreferencesPage()

        images = Adw.PreferencesGroup(title="Images")
        system = bing.system_market()
        self.market_codes: List[Optional[str]] = [None] + [c for c, _ in bing.MARKETS]
        names = [f"Automatic ({bing.market_name(system)})"] + [n for _, n in bing.MARKETS]
        self.region_row = Adw.ComboRow(title="Bing region", model=Gtk.StringList.new(names))
        chosen = self.cfg.chosen_market
        self.region_row.set_selected(self.market_codes.index(chosen) if chosen in self.market_codes else 0)
        self.region_row.connect("notify::selected", self.on_region)
        images.add(self.region_row)

        self.resolution_codes = [c for c, _ in bing.RESOLUTIONS]
        self.resolution_row = Adw.ComboRow(
            title="Image resolution",
            subtitle="Used from the next wallpaper change",
            model=Gtk.StringList.new([n for _, n in bing.RESOLUTIONS]),
        )
        current = self.cfg.get("resolution")
        self.resolution_row.set_selected(
            self.resolution_codes.index(current) if current in self.resolution_codes else 0
        )
        self.resolution_row.connect("notify::selected", self.on_resolution)
        images.add(self.resolution_row)
        page.add(images)

        appearance = Adw.PreferencesGroup(title="Appearance")
        theme_row = Adw.ActionRow(title="Theme")
        toggles = Gtk.Box(valign=Gtk.Align.CENTER)
        toggles.add_css_class("linked")
        self.theme_buttons = {}
        first = None
        for code, label in THEMES:
            button = Gtk.ToggleButton(label=label)
            if first is None:
                first = button
            else:
                button.set_group(first)
            button.set_active(code == (self.cfg.get("theme") or "system"))
            button.connect("toggled", lambda b, code=code: b.get_active() and self.on_theme(code))
            self.theme_buttons[code] = button
            toggles.append(button)
        theme_row.add_suffix(toggles)
        appearance.add(theme_row)
        page.add(appearance)

        about = Adw.PreferencesGroup(title="About")
        about.add(Adw.ActionRow(title="Version", subtitle=__version__))
        page.add(about)

        if hasattr(Adw, "PreferencesDialog"):  # libadwaita 1.5+
            dialog = Adw.PreferencesDialog(title="Settings")
            dialog.add(page)
            dialog.present(self)
        else:
            dialog = Adw.PreferencesWindow(title="Settings", transient_for=self, modal=True)
            dialog.add(page)
            dialog.present()
        self.prefs = dialog

    def on_resolution(self, row: Adw.ComboRow, _pspec: object) -> None:
        code = self.resolution_codes[row.get_selected()]
        if code != self.cfg.get("resolution"):
            self.cfg.set("resolution", code)

    def on_region(self, row: Adw.ComboRow, _pspec: object) -> None:
        code = self.market_codes[row.get_selected()]
        if code == self.cfg.chosen_market:
            return
        self.cfg.set("market", code)
        # Like the daily update would, switch to the new region's image of the day.
        self.apply_after_load = bool(self.cfg.get("daily"))
        self.reload()

    def on_theme(self, code: str) -> None:
        self.cfg.set("theme", code)
        apply_theme(code)

    def toast(self, text: str) -> None:
        self.last_message = text
        self.toasts.add_toast(Adw.Toast(title=GLib.markup_escape_text(text), timeout=4))


def apply_theme(code: str) -> None:
    schemes = {
        "light": Adw.ColorScheme.FORCE_LIGHT,
        "dark": Adw.ColorScheme.FORCE_DARK,
    }
    Adw.StyleManager.get_default().set_color_scheme(schemes.get(code, Adw.ColorScheme.DEFAULT))


class App(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS
                         if hasattr(Gio.ApplicationFlags, "DEFAULT_FLAGS") else Gio.ApplicationFlags.FLAGS_NONE)

    def do_startup(self) -> None:
        Adw.Application.do_startup(self)
        Gtk.Window.set_default_icon_name(APP_ID)
        apply_theme(settings.Settings().get("theme") or "system")
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def do_activate(self) -> None:
        window = self.get_active_window() or Window(self)
        window.present()


def main(argv: Optional[List[str]] = None) -> int:
    return App().run([sys.argv[0]] + list(argv or []))
