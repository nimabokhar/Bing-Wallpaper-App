# Changelog

All notable changes are listed here, newest first. The project uses [semantic versioning](https://semver.org): versions are `MAJOR.MINOR.PATCH`, with an `-alpha.N`, `-beta.N` or `-rc.N` suffix for pre-releases. The version is shared by every platform and lives in [`VERSION`](VERSION).

While the apps are in alpha, expect rough edges and changes between builds.

## [Unreleased]

## [0.2.0-alpha.1] - 2026-10-11

A new look for the Android app, a scrolling gallery and resolution choice on Android, and the first Linux version.

### Android

- New Material 3 design: today's image fills the top of the screen, with a "Set as wallpaper" button on it; the daily change and its time sit in one card; recent images show as a rounded grid with titles on the pictures. On Android 12 and newer the app's colours follow your wallpaper (Material You).
- Region, image resolution and theme moved into a Settings sheet behind the gear icon, where the version is shown too. Choosing home, lock or both screens is a bottom sheet.
- Smoother scrolling: images are decoded at the size they're shown, off the main thread, and kept on disk, so they appear instantly when you come back.
- The gallery loads older images as you scroll, back through every image Bing still has (about two weeks), instead of only the last 8.
- Choose the image size: 4K UHD (default), 1920×1080, 1366×768 or 1080×1920 portrait.

### Linux

- First Linux version for Fedora, Arch and Debian (.rpm, Arch package and .deb): sets the desktop and lock screen on GNOME, KDE Plasma, Cinnamon, MATE and Budgie, and the desktop on XFCE, LXQt, Sway and Hyprland. Daily updates at a time you choose or as soon as Bing publishes, region picker, and a `bing-wallpaper` command.
- The gallery loads older images as you scroll, back through every image Bing still has (about two weeks).
- Choose the image size, from 4K UHD (default) down to 1024×768, or portrait.

### Build

- CI actions moved to their Node 24 versions, removing the Node.js 20 deprecation warning.

## [0.1.0-alpha.1] - 2026-10-11

First alpha.

### Android

- Sets the Bing image of the day on the home screen and lock screen, every day at a time you choose (7:00 by default), and keeps working after a reboot.
- Gallery of the last 8 Bing images: tap one to set it on the home screen, lock screen or both.
- Region picker with 14 Bing markets, or Automatic to follow the phone's language and region.
- Dark mode: follows the phone's theme, or pick Light or Dark.
- Foldable-aware cropping, so the wallpaper stays sharp on both screens.
- App icon, including a themed icon on Android 13 and newer.
- The app shows its version at the bottom of the main screen.

[Unreleased]: https://github.com/nimabokhar/Bing-Wallpaper-Android-App/compare/v0.1.0-alpha.1...HEAD
[0.1.0-alpha.1]: https://github.com/nimabokhar/Bing-Wallpaper-Android-App/releases/tag/v0.1.0-alpha.1
