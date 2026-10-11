"""Opens the window with fake Bing data, clicks through it, and exits. Needs a display
(run under xvfb-run in CI) plus GTK 4, libadwaita and PyGObject."""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
tmp = tempfile.mkdtemp()
for var in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME"):
    os.environ[var] = os.path.join(tmp, var)

from gi.repository import GLib  # noqa: E402

from bing_wallpaper import bing, desktop, gui, imagecache  # noqa: E402
from test_bing_wallpaper import ARCHIVE  # noqa: E402

applied = []
pages = []


def fake_page(market, have):
    # Two pages of Bing images, then nothing more.
    pages.append(have)
    images = bing.parse_archive(ARCHIVE)
    if have == 0:
        return images[:1]
    return images if have < 2 else images[1:]
schedules = []
failed = []
downloads = []


def fake_jpeg():
    from gi.repository import GdkPixbuf

    pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, False, 8, 64, 36)
    pixbuf.fill(0x3366AAFF)
    ok, data = pixbuf.save_to_bufferv("jpeg", [], [])
    return bytes(data)


JPEG = fake_jpeg()


def fake_fetch(url):
    downloads.append(url)
    return JPEG


def guarded(fn):
    """GLib swallows exceptions in callbacks, so record them and quit instead."""

    def wrapper(app):
        try:
            return fn()
        except Exception as e:
            failed.append(e)
            print("GUI smoke test FAILED:", repr(e))
            app.quit()
            return False

    return wrapper


def fake_apply(image, target, cfg=None, newest_id=None):
    applied.append((image.id, target, newest_id))
    return desktop.Result()


class SmokeApp(gui.App):
    def do_activate(self):
        window = gui.Window(
            self,
            fetch_page=fake_page,
            disk=imagecache.DiskCache(fetch=fake_fetch),
            apply=fake_apply,
            set_daily_time=lambda t: schedules.append(t) or "",
        )
        window.present()

        def check():
            cards = 0
            child = window.grid.get_first_child()
            while child is not None:
                cards += 1
                child = child.get_next_sibling()
            total = len(bing.parse_archive(ARCHIVE))
            # Today's image is the hero, the grid starts from yesterday.
            assert cards == total - 1, f"expected {total - 1} gallery cards, got {cards}"
            assert window.hero_title.get_text() == window.images[0].title, window.hero_title.get_text()
            assert window.hero_picture.get_paintable() is not None, "hero image never loaded"
            assert len(downloads) == len(set(downloads)), f"downloaded twice: {downloads}"
            assert window.exhausted, "should have stopped once Bing had no more images"
            assert pages[:2] == [0, 1], pages
            window.set_button.emit("clicked")
            window.when_row.set_selected(1)
            window.hour_spin.set_value(6)
            window.minute_spin.set_value(45)
            GLib.timeout_add(1500, guarded(finish), self)
            return False

        def finish():
            assert applied == [("OHR.Today_EN-US123", "both", "OHR.Today_EN-US123")], applied
            assert schedules == ["06:45"], schedules
            assert window.hour_spin.get_text() == "06", window.hour_spin.get_text()
            window.open_preferences()
            window.resolution_row.set_selected(2)
            assert window.cfg.get("resolution") == "1920x1080", window.cfg.get("resolution")
            window.theme_buttons["dark"].set_active(True)
            assert window.cfg.get("theme") == "dark", window.cfg.get("theme")
            window.region_row.set_selected(3)
            print("GUI smoke test passed:", window.last_message)
            self.quit()
            return False

        started = GLib.get_monotonic_time()

        def wait():
            # Pages and images load in the background; give them up to 10 seconds.
            ready = window.exhausted and window.hero_picture.get_paintable() is not None
            if ready or GLib.get_monotonic_time() - started > 10_000_000:
                return check()
            return True

        GLib.timeout_add(100, guarded(wait), self)


code = SmokeApp().run([sys.argv[0]])
sys.exit(1 if failed else code)
