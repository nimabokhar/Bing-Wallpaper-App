"""Opens the window with fake Bing data, clicks through it, and exits. Needs a display
(run under xvfb-run in CI) plus GTK 4 and PyGObject."""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
tmp = tempfile.mkdtemp()
for var in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME"):
    os.environ[var] = os.path.join(tmp, var)

from gi.repository import GLib  # noqa: E402

from bing_wallpaper import bing, desktop, gui  # noqa: E402
from test_bing_wallpaper import ARCHIVE  # noqa: E402

applied = []
schedules = []
failed = []


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
            fetch_latest=lambda market: bing.parse_archive(ARCHIVE),
            fetch_thumbnail=lambda image: None,
            apply=fake_apply,
            set_daily_time=lambda t: schedules.append(t) or "",
        )
        window.present()

        def check():
            cards = 0
            child = window.flow.get_first_child()
            while child is not None:
                cards += 1
                child = child.get_next_sibling()
            assert cards == 2, f"expected 2 gallery cards, got {cards}"
            window.today_button.emit("clicked")
            window.when_dropdown.set_selected(1)
            window.hour_spin.set_value(6)
            window.minute_spin.set_value(45)
            GLib.timeout_add(1500, guarded(finish), self)
            return False

        def finish():
            assert applied == [("OHR.Today_EN-US123", "both", "OHR.Today_EN-US123")], applied
            assert schedules == ["06:45"], schedules
            assert window.hour_spin.get_text() == "06", window.hour_spin.get_text()
            window.region_dropdown.set_selected(3)
            print("GUI smoke test passed:", window.status.get_text())
            self.quit()
            return False

        GLib.timeout_add(1000, guarded(check), self)


code = SmokeApp().run([sys.argv[0]])
sys.exit(1 if failed else code)
