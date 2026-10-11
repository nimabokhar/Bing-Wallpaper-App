import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import datetime  # noqa: E402

from bing_wallpaper import bing, cli, core, desktop, schedule, settings  # noqa: E402

ARCHIVE = {
    "images": [
        {
            "startdate": "20261011",
            "url": "/th?id=OHR.Today_EN-US123_1920x1080.jpg&rf=LaDigue_1920x1080.jpg",
            "urlbase": "/th?id=OHR.Today_EN-US123",
            "copyright": "A place (© Someone)",
            "title": "Today",
        },
        {
            "startdate": "20261010",
            "url": "/th?id=OHR.Yesterday_EN-US456_1920x1080.jpg",
            "urlbase": "/th?id=OHR.Yesterday_EN-US456",
            "copyright": "",
            "title": "Yesterday",
        },
    ]
}
JPEG = b"\xff\xd8\xff\xe0fake"


class TempHome(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        env = {
            "XDG_CONFIG_HOME": str(root / "config"),
            "XDG_DATA_HOME": str(root / "data"),
            "XDG_CACHE_HOME": str(root / "cache"),
            "XDG_STATE_HOME": str(root / "state"),
        }
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)


class BingTest(unittest.TestCase):
    def test_parse_archive(self):
        images = bing.parse_archive(ARCHIVE)
        self.assertEqual([i.id for i in images], ["OHR.Today_EN-US123", "OHR.Yesterday_EN-US456"])
        today = images[0]
        self.assertEqual(today.uhd_url, "https://www.bing.com/th?id=OHR.Today_EN-US123_UHD.jpg")
        self.assertEqual(today.hd_url, "https://www.bing.com/th?id=OHR.Today_EN-US123_1920x1080.jpg")
        self.assertTrue(today.fallback_url.startswith("https://www.bing.com/th?id=OHR.Today"))
        self.assertEqual(today.nice_date, "2026-10-11")

    def test_system_market(self):
        self.assertEqual(bing.system_market("en_GB.UTF-8"), "en-GB")
        self.assertEqual(bing.system_market("de_DE@euro"), "de-DE")
        self.assertEqual(bing.system_market("fr_CA.utf8"), "fr-CA")
        self.assertEqual(bing.system_market("nl_NL.UTF-8"), "en-US")
        self.assertEqual(bing.system_market("C"), "en-US")
        self.assertEqual(bing.system_market(""), "en-US")

    def test_download_falls_back_when_uhd_missing(self):
        image = bing.parse_archive(ARCHIVE)[0]

        def fake_get(url, timeout=30):
            if url == image.uhd_url:
                raise OSError("404")
            return JPEG

        with mock.patch.object(bing, "http_get", fake_get):
            self.assertEqual(bing.download_image(image), JPEG)

    def test_fetch_all_pages_through_two_weeks(self):
        # Fake Bing with 15 days: idx is capped at 7 and n at 8, so pages overlap.
        days = [bing.BingImage(f"img{d}", "", "", "", "", "", "", "") for d in range(15)]
        calls = []

        def fake_latest(market, count=8, start=0):
            calls.append(start)
            return days[min(start, 7):min(start, 7) + count]

        with mock.patch.object(bing, "fetch_latest", fake_latest):
            images = bing.fetch_all("en-US")
        self.assertEqual([i.id for i in images], [d.id for d in days])
        self.assertEqual(calls, [0, 7])

    def test_download_in_chosen_resolution(self):
        image = bing.parse_archive(ARCHIVE)[0]
        asked = []

        def fake_get(url, timeout=30):
            asked.append(url)
            if "_1366x768" in url:
                raise OSError("404")
            return JPEG

        with mock.patch.object(bing, "http_get", fake_get):
            bing.download_image(image, "1280x720")
            bing.download_image(image, "1366x768")
        self.assertEqual(asked[0], "https://www.bing.com/th?id=OHR.Today_EN-US123_1280x720.jpg")
        # A missing size falls back to Full HD.
        self.assertEqual(asked[2], image.hd_url)

    def test_download_rejects_non_images(self):
        image = bing.parse_archive(ARCHIVE)[0]
        with mock.patch.object(bing, "http_get", lambda url, timeout=30: b"<html>"):
            with self.assertRaises(OSError):
                bing.download_image(image)


class DetectTest(unittest.TestCase):
    def test_detect(self):
        cases = {
            "GNOME": "gnome",
            "ubuntu:GNOME": "gnome",
            "KDE": "kde",
            "X-Cinnamon": "cinnamon",
            "Budgie:GNOME": "budgie",
            "MATE": "mate",
            "XFCE": "xfce",
            "LXQt": "lxqt",
            "sway": "sway",
            "Hyprland": "hyprland",
            "": "unknown",
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(desktop.detect({"XDG_CURRENT_DESKTOP": value}), expected)
        self.assertEqual(desktop.detect({"SWAYSOCK": "/run/sway"}), "sway")


class SetterTest(TempHome):
    def setUp(self):
        super().setUp()
        self.calls = []
        self.path = Path(self.tmp.name) / "img.jpg"
        self.path.write_bytes(JPEG)

    def runner(self, outputs=None):
        outputs = outputs or {}

        def run(cmd):
            self.calls.append(list(cmd))
            return outputs.get(tuple(cmd[:3]), "")

        return run

    def test_gnome_both(self):
        keys = "picture-uri picture-uri-dark picture-options"
        run = self.runner({
            ("gsettings", "list-keys", "org.gnome.desktop.background"): keys,
            ("gsettings", "list-keys", "org.gnome.desktop.screensaver"): "picture-uri picture-options",
        })
        result = desktop.set_wallpaper(self.path, desktop.BOTH, desktop="gnome", run_=run)
        uri = self.path.resolve().as_uri()
        self.assertIn(["gsettings", "set", "org.gnome.desktop.background", "picture-uri", uri], self.calls)
        self.assertIn(["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", uri], self.calls)
        self.assertIn(["gsettings", "set", "org.gnome.desktop.screensaver", "picture-uri", uri], self.calls)
        self.assertEqual(result.done, [desktop.DESKTOP, desktop.LOCK])

    def test_gnome_desktop_only_leaves_lock(self):
        run = self.runner({("gsettings", "list-keys", "org.gnome.desktop.background"): "picture-uri"})
        desktop.set_wallpaper(self.path, desktop.DESKTOP, desktop="gnome", run_=run)
        self.assertFalse(any("org.gnome.desktop.screensaver" in c for c in self.calls))
        self.assertFalse(any("picture-uri-dark" in c for c in self.calls))

    def test_kde_lock(self):
        with mock.patch.object(desktop.shutil, "which", lambda name: name if name == "kwriteconfig6" else None):
            result = desktop.set_wallpaper(self.path, desktop.LOCK, desktop="kde", run_=self.runner())
        uri = self.path.resolve().as_uri()
        self.assertIn(
            ["kwriteconfig6", "--file", "kscreenlockerrc", "--group", "Greeter", "--group", "Wallpaper",
             "--group", "org.kde.image", "--group", "General", "--key", "Image", uri],
            self.calls,
        )
        self.assertEqual(result.done, [desktop.LOCK])

    def test_kde_desktop_uses_plasma_tool(self):
        with mock.patch.object(desktop.shutil, "which", lambda name: name):
            desktop.set_wallpaper(self.path, desktop.DESKTOP, desktop="kde", run_=self.runner())
        self.assertEqual(self.calls, [["plasma-apply-wallpaperimage", str(self.path)]])

    def test_kde_desktop_falls_back_to_qdbus(self):
        with mock.patch.object(desktop.shutil, "which", lambda name: name if name == "qdbus6" else None):
            desktop.set_wallpaper(self.path, desktop.DESKTOP, desktop="kde", run_=self.runner())
        self.assertEqual(self.calls[0][:4], ["qdbus6", "org.kde.plasmashell", "/PlasmaShell",
                                            "org.kde.PlasmaShell.evaluateScript"])
        self.assertIn('"' + self.path.resolve().as_uri() + '"', self.calls[0][4])

    def test_xfce_sets_every_monitor(self):
        props = "/backdrop/screen0/monitorHDMI-1/workspace0/last-image\n" \
                "/backdrop/screen0/monitoreDP-1/workspace0/last-image\n/other\n"
        run = self.runner({("xfconf-query", "-c", "xfce4-desktop"): props})
        result = desktop.set_wallpaper(self.path, desktop.BOTH, desktop="xfce", run_=run)
        sets = [c for c in self.calls if "-s" in c and c[-1] == str(self.path)]
        self.assertEqual(len(sets), 2)
        self.assertEqual(result.done, [desktop.DESKTOP])
        self.assertIn("lock.jpg", result.notes[0])

    def test_custom_command(self):
        result = desktop.set_wallpaper(self.path, desktop.BOTH, custom_command="swww img {path}",
                                       run_=self.runner())
        self.assertEqual(self.calls, [["sh", "-c", f"swww img {self.path}"]])
        self.assertEqual(result.done, [desktop.DESKTOP, desktop.LOCK])


class UpdateTest(TempHome):
    def setUp(self):
        super().setUp()
        self.applied = []
        self.resolutions = []

        def fake_set(path, target, desktop=None, custom_command=None):
            self.applied.append((Path(path).name, target))
            return result_type()

        result_type = desktop.Result
        for module, name, value in (
            (bing, "fetch_latest", lambda market, count=8, start=0: bing.parse_archive(ARCHIVE)[start:start + count]),
            (desktop, "set_wallpaper", fake_set),
            (core, "download", self._download),
        ):
            p = mock.patch.object(module, name, value)
            p.start()
            self.addCleanup(p.stop)

    def _download(self, image, resolution="UHD"):
        self.resolutions.append(resolution)
        path = core.image_path(image, resolution)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(JPEG)
        return path

    def test_update_only_applies_new_images(self):
        self.assertEqual(core.update().id, "OHR.Today_EN-US123")
        self.assertIsNone(core.update())
        self.assertEqual(len(self.applied), 1)
        self.assertEqual(core.update(force=True).id, "OHR.Today_EN-US123")
        self.assertEqual(len(self.applied), 2)

    def test_manual_pick_survives_until_new_image(self):
        images = bing.parse_archive(ARCHIVE)
        core.apply(images[1], desktop.BOTH, newest_id=images[0].id)
        self.assertIsNone(core.update())
        self.assertEqual(settings.State().get("last_applied"), "OHR.Yesterday_EN-US456")

    def test_symlinks_point_at_current_image(self):
        images = bing.parse_archive(ARCHIVE)
        core.apply(images[0], desktop.DESKTOP)
        core.apply(images[1], desktop.LOCK)
        data = settings.data_dir()
        self.assertEqual((data / "wallpaper.jpg").resolve().name, "OHR.Today_EN-US123.jpg")
        self.assertEqual((data / "lock.jpg").resolve().name, "OHR.Yesterday_EN-US456.jpg")

    def test_remembers_desktop_for_timer_runs(self):
        state = settings.State()
        with mock.patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE"}):
            self.assertEqual(core.current_desktop(state), "kde")
        with mock.patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": ""}):
            self.assertEqual(core.current_desktop(settings.State()), "kde")

    def test_resolution_setting(self):
        with mock.patch("sys.stdout"):
            self.assertEqual(cli.main(["resolution", "1920x1080"]), 0)
            self.assertEqual(cli.main(["set", "1"]), 0)
            with mock.patch("sys.stderr"):
                self.assertEqual(cli.main(["resolution", "123x45"]), 2)
        self.assertEqual(self.resolutions, ["1920x1080"])
        self.assertEqual(self.applied, [("OHR.Today_EN-US123_1920x1080.jpg", "both")])

    def test_region_setting(self):
        cfg = settings.Settings()
        cfg.set("market", "ja-JP")
        self.assertEqual(settings.Settings().market, "ja-JP")
        with mock.patch("sys.stdout"):
            self.assertEqual(cli.main(["region", "auto"]), 0)
        self.assertIsNone(settings.Settings().chosen_market)

    def test_cli_set_and_list(self):
        with mock.patch("sys.stdout"):
            self.assertEqual(cli.main(["set", "2", "--on", "lock"]), 0)
            self.assertEqual(cli.main(["list"]), 0)
            self.assertEqual(cli.main(["set", "9"]), 2)
        self.assertEqual(self.applied, [("OHR.Yesterday_EN-US456.jpg", "lock")])


class ScheduleTest(UpdateTest):
    def at(self, hhmm, day=11):
        hour, minute = map(int, hhmm.split(":"))
        return datetime.datetime(2026, 10, day, hour, minute)

    def test_parse_time(self):
        self.assertEqual(schedule.parse_time("7:30"), "07:30")
        self.assertEqual(schedule.parse_time("19:05"), "19:05")
        self.assertIsNone(schedule.parse_time("24:00"))
        self.assertIsNone(schedule.parse_time("7pm"))

    def test_due_moment(self):
        self.assertEqual(schedule.due_moment("07:00", self.at("08:00")), self.at("07:00"))
        self.assertEqual(schedule.due_moment("07:00", self.at("06:59")), self.at("07:00", day=10))

    def test_dropin(self):
        with mock.patch.object(schedule, "available", lambda: False):
            self.assertEqual(schedule.set_time("06:30"), "")
            text = schedule.dropin_path().read_text()
            self.assertIn("OnCalendar=\nOnCalendar=*-*-* 06:30:00", text)
            schedule.set_time(None)
            self.assertFalse(schedule.dropin_path().exists())

    def test_changes_once_a_day_at_the_set_time(self):
        with mock.patch.object(schedule, "available", lambda: False):
            core.set_daily_time("07:00", now=self.at("15:00", day=10))
        # Startup/login runs before 07:00 don't change it, even with a new image.
        self.assertIsNone(core.update(now=self.at("06:00")))
        self.assertEqual(self.applied, [])
        # The 07:00 run does, once.
        self.assertIsNotNone(core.update(now=self.at("07:00")))
        self.assertIsNone(core.update(now=self.at("09:00")))
        self.assertEqual(len(self.applied), 1)

    def test_catches_up_after_a_missed_time(self):
        with mock.patch.object(schedule, "available", lambda: False):
            core.set_daily_time("07:00", now=self.at("15:00", day=9))
        # Computer was off at 07:00 on the 10th and 11th; first run afterwards applies.
        self.assertIsNotNone(core.update(now=self.at("12:00")))

    def test_cli_daily_at(self):
        with mock.patch.object(schedule, "available", lambda: False), \
                mock.patch.object(schedule, "enabled", lambda: True), mock.patch("sys.stdout"):
            self.assertEqual(cli.main(["daily", "at", "6:15"]), 0)
            self.assertEqual(settings.Settings().get("daily_time"), "06:15")
            self.assertEqual(cli.main(["daily", "at", "auto"]), 0)
            self.assertIsNone(settings.Settings().get("daily_time"))
            with mock.patch("sys.stderr"):
                self.assertEqual(cli.main(["daily", "at", "25:00"]), 2)


if __name__ == "__main__":
    unittest.main()
