<p align="center">
  <img src="icon/png/bing-wallpaper-256.png" width="128" alt="Bing Wallpaper icon">
</p>

<h1 align="center">Bing Wallpaper</h1>

<p align="center">
  A fresh wallpaper every day: sets your background to the <a href="https://www.bing.com">Bing image of the day</a> and keeps it updated automatically.
</p>

## What it does

Every day Bing publishes a new photo, usually a landscape, animal or landmark from somewhere in the world. Bing Wallpaper downloads it in full resolution, crops it to your screen and sets it as your wallpaper. Once it is set up, there is nothing else to do: when Bing publishes the next image, your wallpaper changes with it.

## Platforms

Each platform is a separate app in its own folder, with its own build and its own CI workflow.

| Platform | Folder | Status |
| --- | --- | --- |
| Android (home and lock screen) | [`android/`](android/) | Available: [download the APK](https://github.com/nimabokhar/Bing-Wallpaper-Android-App/releases/download/latest/bing-wallpaper.apk) |
| Linux (desktop and lock screen; Fedora, Arch, Debian) | [`linux/`](linux/) | Available: [.deb](https://github.com/nimabokhar/Bing-Wallpaper-Android-App/releases/download/latest/bing-wallpaper.deb), [.rpm](https://github.com/nimabokhar/Bing-Wallpaper-Android-App/releases/download/latest/bing-wallpaper.rpm), [Arch](https://github.com/nimabokhar/Bing-Wallpaper-Android-App/releases/download/latest/bing-wallpaper.pkg.tar.zst) |
| Windows | `windows/` | Planned |
| macOS (Apple Silicon and Intel, macOS 14+) | [`macos/`](macos/) | Available: [.dmg](https://github.com/nimabokhar/Bing-Wallpaper-Android-App/releases/download/latest/bing-wallpaper-macos.dmg) |

All builds are published to the same [**latest release**](https://github.com/nimabokhar/Bing-Wallpaper-Android-App/releases/tag/latest).

## What the apps can do

| | Android | Linux | macOS |
| --- | --- | --- | --- |
| Sets the wallpaper | Home screen and lock screen | Desktop and lock screen | Every display (the lock screen shows it too) |
| Changes it every day | Yes, at a time you choose (7:00 by default) | Yes, as soon as Bing publishes a new image, or at a time you choose | Yes, at a time you choose (7:00 by default) |
| Keeps working after a restart | Yes | Yes (systemd user timer, also checks at login) | Yes (opens at login, runs in the menu bar) |
| Browse and pick older images | Scroll back through about two weeks of Bing images | Scroll back through about two weeks of Bing images | Scroll back through about two weeks of Bing images |
| Choose where a picked image goes | Home, lock or both | Desktop, lock or both | No, macOS uses the desktop picture on the lock screen |
| Bing region (country) | 14 regions, or Automatic | 14 regions, or Automatic | 14 regions, or Automatic |
| Image resolution | 4K (default), 1920×1080, 1366×768, portrait 1080×1920 | 4K (default) down to 1024×768, plus portrait 1080×1920 | 4K (default) down to 1024×768, plus portrait 1080×1920 |
| Dark mode | Follows the system, or Light or Dark | Not yet | Follows the system, or Light or Dark |
| Command line | No | `bing-wallpaper` does everything the window does | No |

### Android

- **Home and lock screen:** the daily image goes on both. For any image you pick from the gallery, choose home, lock or both.
- **Daily change at a set time:** the wallpaper changes once a day at the time you set under **Change at**. If Bing hasn't published the day's image yet, the app checks again hourly for a few hours. The schedule survives reboots.
- **Gallery:** shows Bing's images newest first and loads older ones as you scroll, back to the roughly 15 days Bing keeps. A hand-picked image stays until the next scheduled change brings a newer one.
- **Today's image** fills the top of the screen; **Set as wallpaper** applies it straight away.
- **Bing region:** pick which country's image you get, or leave it on Automatic to follow your phone's language and region.
- **Image resolution:** 4K/UHD (default), 1920×1080, 1366×768 or 1080×1920 portrait. The image is cropped to fit your screen.
- **Dark mode:** follows your phone's theme, or pick Light or Dark.
- **Material You design:** on Android 12 and newer the app's colours follow your wallpaper. Region, resolution and theme live in the Settings sheet behind the gear icon.
- **Foldables:** the image is cropped for the unfolded screen so it stays sharp on both screens, and the gallery shows its wide image cards side by side when unfolded.
- **Themed icon:** on Android 13 and newer, the launcher icon follows your wallpaper colours.
- The app shows its version in Settings.

Requires Android 7.0 or newer. More detail in the [Android README](android/README.md).

### Linux

- **Desktop and lock screen:** works on GNOME, KDE Plasma 5 and 6, Cinnamon, MATE and Budgie, including their lock screens. XFCE, LXQt, LXDE, Sway, Hyprland and setups using `feh`, `nitrogen` or `swww` get the desktop wallpaper, plus an always-current `lock.jpg` you can point your screen locker at.
- **Daily change:** as soon as Bing publishes a new image (the default), or every day at a time you choose. If the computer was off, it catches up at the next login.
- **Gallery:** Bing's images newest first, loading older ones as you scroll. Click one to put it on the desktop, the lock screen or both.
- **Bing region** and **image size** (4K UHD by default, down to 1024×768, plus portrait 1080×1920).
- **Command line:** everything the window does also works from the terminal, for example `bing-wallpaper update`, `bing-wallpaper set 3 --on lock`, `bing-wallpaper daily at 07:30`.
- **Custom setups:** any other wallpaper tool can be used through a `custom_command` in the settings file.
- Packages for Debian and Ubuntu (.deb), Fedora (.rpm) and Arch (.pkg.tar.zst, or build from the PKGBUILD).

More detail, including the full list of desktops and commands, in the [Linux README](linux/README.md).

### macOS

- **Every display:** today's image goes on all your displays, and on each Space as you switch to it. The lock screen shows the desktop wallpaper on macOS, so it changes too.
- **Daily change at a set time**, with hourly retries until Bing publishes, and catch-up after sleep or a restart.
- **Gallery:** scroll back through about two weeks of Bing images; hover and click **Set as wallpaper**.
- **Menu bar app:** keeps running in the menu bar with the window closed and opens at login. Region, image size, theme and Open at login are in Settings (⌘,).
- One download for Apple Silicon (M1 and newer) and Intel Macs, macOS 14 Sonoma or newer.

More detail in the [macOS README](macos/README.md).

## Install

> The apps are in **alpha**. They work, but expect rough edges and changes between builds. The links below are the newest build; each version also has its own pre-release on the [releases page](https://github.com/nimabokhar/Bing-Wallpaper-Android-App/releases).

### Android

1. On your phone, download [`bing-wallpaper.apk`](https://github.com/nimabokhar/Bing-Wallpaper-Android-App/releases/download/latest/bing-wallpaper.apk).
2. Open it, and allow your browser or file manager to install unknown apps when Android asks.
3. Open **Bing Wallpaper** and tap **Set as wallpaper**. Daily changes run on their own from then on.

Each new alpha build is signed with a fresh key until a signing key is set up, so you may need to uninstall the old version before installing a new one (see the [Android README](android/README.md#updating-without-uninstalling)). If daily changes stop, set the app's battery usage to Unrestricted (Settings → Apps → Bing Wallpaper → Battery).

### Linux

Download the package for your distro, then install it:

| Distro | Download | Install |
| --- | --- | --- |
| Debian, Ubuntu, Mint | [bing-wallpaper.deb](https://github.com/nimabokhar/Bing-Wallpaper-Android-App/releases/download/latest/bing-wallpaper.deb) | `sudo apt install ./bing-wallpaper.deb` |
| Fedora | [bing-wallpaper.rpm](https://github.com/nimabokhar/Bing-Wallpaper-Android-App/releases/download/latest/bing-wallpaper.rpm) | `sudo dnf install ./bing-wallpaper.rpm` |
| Arch, Manjaro | [bing-wallpaper.pkg.tar.zst](https://github.com/nimabokhar/Bing-Wallpaper-Android-App/releases/download/latest/bing-wallpaper.pkg.tar.zst) | `sudo pacman -U ./bing-wallpaper.pkg.tar.zst` |

Then open **Bing Wallpaper** from your app menu once (or log out and back in). Daily changes run on their own from then on.

### macOS

1. Download [`bing-wallpaper-macos.dmg`](https://github.com/nimabokhar/Bing-Wallpaper-Android-App/releases/download/latest/bing-wallpaper-macos.dmg), open it and drag **Bing Wallpaper** to **Applications**.
2. Open it. The app isn't signed with an Apple Developer ID yet, so the first time macOS blocks it: open **System Settings → Privacy & Security**, click **Open Anyway** next to "Bing Wallpaper was blocked", and confirm. This is only needed once.
3. Click **Set as wallpaper**. Daily changes run on their own from then on.

## Versions

Every platform shares one version number, kept in [`VERSION`](VERSION) and following [semantic versioning](https://semver.org) with pre-release labels (`0.1.0-alpha.1`, then `-alpha.2`, `-beta.1`, `-rc.1`, and finally `0.1.0`). What changed in each version is in the [changelog](CHANGELOG.md).

- **Tagged releases:** when a change to `VERSION` reaches `main`, CI publishes a GitHub release tagged `v<version>` (marked pre-release while in alpha, beta or rc) with that version's changelog notes and a versioned download such as `bing-wallpaper-0.1.0-alpha.1.apk`.
- **Latest build:** every push to `main` still updates the [latest release](https://github.com/nimabokhar/Bing-Wallpaper-Android-App/releases/tag/latest). Builds made after a version was released show as `<version>+build.<CI run number>`.
- **In the app:** the version is shown at the bottom of the main screen.

To cut a new version, add its notes under a new `## [<version>]` heading in `CHANGELOG.md`, put the version in `VERSION`, and merge to `main`.

## Repository layout

```
android/            Android app (Kotlin, Gradle)
linux/              Linux app (Python, GTK 4) and its .deb, .rpm and Arch packaging
macos/              macOS app (Swift, SwiftUI) and its .dmg build
icon/               App icon: SVG source plus PNG and ICO exports for every platform
.github/workflows/  One CI workflow per platform, each only runs on changes to its folder
```

### Adding a platform

1. Put the app in a new top-level folder named after the platform (for example `windows/`), with its own README covering features, install and local build.
2. Use the icon from [`icon/`](icon/) rather than drawing a new one.
3. Add `.github/workflows/<platform>.yml` that only runs on changes under that folder (`paths: ["<platform>/**", ".github/workflows/<platform>.yml"]`) and uploads its build to the `latest` release with `gh release upload latest <file> --clobber`. Give the file a platform-specific name so it doesn't replace another platform's download. Read the version from [`VERSION`](VERSION), and attach versioned builds to the tagged release with [`.github/scripts/release.sh`](.github/scripts/release.sh) (`release.sh check`, then `release.sh publish <file>...`); add `VERSION` to the workflow's `paths` so a version bump triggers a release.
4. Add a row to the platforms table above.

## Credits

Images are © their respective owners and are provided by Microsoft Bing. This project is not affiliated with or endorsed by Microsoft.

## License

[MIT](LICENSE)
