# Bing Wallpaper for Linux

Sets your desktop wallpaper and lock screen to the [Bing image of the day](https://www.bing.com), and keeps it updated every day. Works on Fedora, Arch and Debian (and their relatives such as Ubuntu, Mint and Manjaro).

## Features

- **Today's image** fills the top of the window. **Set as wallpaper** puts it on the desktop and lock screen right away, or click the image to choose desktop, lock screen or both.
- **Recent images** shows the earlier Bing images as large previews. Scroll down to load older ones, back as far as Bing keeps them (about two weeks). Click one to set it on the desktop, the lock screen, or both.
- **Update daily** (on by default) checks every 4 hours with a systemd user timer and switches the wallpaper as soon as Bing publishes a new image. It also checks at login. If you pick an older image by hand, it stays until the next new Bing image comes out.
- **Schedule** picks when the daily change happens: as soon as Bing publishes a new image (the default), or every day at a time you choose, such as 07:00. If the computer is off at that time, it changes at the next login or startup.
- **Settings** (the gear button) holds the region, image size and theme (System, Light or Dark), and shows the version.
- **Bing region** picks which country's image you get. The default follows your system language (falling back to United States).
- **Image size** picks the resolution to download: 4K UHD (3840×2160, the default, sharp on 4K and multi-monitor setups), 1920×1200, Full HD, 1366×768, 1280×720, 1024×768 or portrait 1080×1920. If Bing doesn't have an image in that size, Full HD is used.
- Everything also works from the terminal: `bing-wallpaper --help`.

## Supported desktops

| Desktop | Wallpaper | Lock screen |
| --- | --- | --- |
| GNOME (Fedora Workstation, Debian, Ubuntu) | yes | yes (GNOME shows a blurred copy of the wallpaper) |
| KDE Plasma 5 and 6 | yes | yes |
| Cinnamon, MATE, Budgie | yes | yes (same image as the desktop) |
| XFCE, LXQt, LXDE | yes | see below |
| Sway, Hyprland (with `swww` or `hyprpaper`) | yes | see below |
| Anything else with `feh`, `nitrogen` or `swww` | yes | see below |

Where there is no standard lock screen setting, the app keeps `~/.local/share/bing-wallpaper/lock.jpg` (and `wallpaper.jpg`) pointing at the current image. Point your screen locker at it, e.g. `swaylock -i ~/.local/share/bing-wallpaper/lock.jpg` or `path = ~/.local/share/bing-wallpaper/lock.jpg` in `hyprlock.conf`.

For any other setup, add a command to `~/.config/bing-wallpaper/config.json`, and it's used instead of the built-in methods (`{path}` is the image, `{target}` is `desktop`, `lock` or `both`):

```json
{ "custom_command": "swww img {path}" }
```

## Install

Download the package for your distro from the [**latest release**](https://github.com/nimabokhar/Bing-Wallpaper-Android-App/releases/tag/latest), or a specific version from the [releases page](https://github.com/nimabokhar/Bing-Wallpaper-Android-App/releases). The app is in alpha: versions look like `0.1.0-alpha.1`, written `0.1.0~alpha.1` in the .deb and .rpm and `0.1.0alpha.1` in the Arch package so every package manager upgrades from alpha to the final release correctly. Builds from pull requests are also attached to each run on the Actions tab as the `bing-wallpaper-linux` artifact.

**Debian / Ubuntu**

```sh
sudo apt install ./bing-wallpaper.deb
```

**Fedora**

```sh
sudo dnf install ./bing-wallpaper.rpm
```

**Arch**

```sh
sudo pacman -U ./bing-wallpaper.pkg.tar.zst
```

or build it yourself from the PKGBUILD (also suitable for the AUR as `bing-wallpaper-git`):

```sh
git clone https://github.com/nimabokhar/Bing-Wallpaper-Android-App.git
cd Bing-Wallpaper-Android-App/linux/packaging/arch
makepkg -si
```

Then open **Bing Wallpaper** from your app menu once (or log out and back in). Daily updates are switched on from then on.

## Command line

```sh
bing-wallpaper              # open the window
bing-wallpaper update       # apply today's image if it's new (--force to re-apply)
bing-wallpaper list         # every image Bing still has (about two weeks)
bing-wallpaper set 3 --on lock   # image 3 on the lock screen (desktop, lock or both)
bing-wallpaper region en-GB # or "auto"; --list shows all regions
bing-wallpaper resolution 1920x1080  # image size; --list shows all sizes
bing-wallpaper daily at 07:30  # change every day at 07:30 ("auto" = as soon as Bing publishes)
bing-wallpaper daily off    # stop daily updates
bing-wallpaper status
```

The daily schedule is the `bing-wallpaper.timer` systemd user unit: `systemctl --user status bing-wallpaper.timer`, and its log is in `journalctl --user -u bing-wallpaper`. A set time is stored as a drop-in in `~/.config/systemd/user/bing-wallpaper.timer.d/schedule.conf`.

## Files

- Settings: `~/.config/bing-wallpaper/config.json`
- Downloaded wallpapers (the last 12 are kept): `~/.local/share/bing-wallpaper/images/`
- Gallery previews: `~/.cache/bing-wallpaper/images/` (unused ones are deleted after 30 days)

## Build and test

The app is plain Python 3 (standard library only); the window uses GTK 4 and libadwaita through PyGObject.

```sh
cd linux
make test                       # unit tests
python3 -m bing_wallpaper       # run from the source tree
make install PREFIX=/usr/local  # or install directly (DESTDIR is supported)
make packages                   # .deb, .rpm and .pkg.tar.zst into dist/ (needs nfpm)
```
