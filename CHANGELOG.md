# Changelog

All notable changes are listed here, newest first. The project uses [semantic versioning](https://semver.org): versions are `MAJOR.MINOR.PATCH`, with an `-alpha.N`, `-beta.N` or `-rc.N` suffix for pre-releases. The version is shared by every platform and lives in [`VERSION`](VERSION).

While the apps are in alpha, expect rough edges and changes between builds.

## [Unreleased]

### Linux

- First Linux version for Fedora, Arch and Debian (.rpm, Arch package and .deb): sets the desktop and lock screen on GNOME, KDE Plasma, Cinnamon, MATE and Budgie, and the desktop on XFCE, LXQt, Sway and Hyprland. Daily updates at a time you choose or as soon as Bing publishes, region picker, and a `bing-wallpaper` command.
- The gallery loads older images as you scroll, back through every image Bing still has (about two weeks).
- Choose the image size, from 4K UHD (default) down to 1024×768, or portrait.
- New modern look built with libadwaita: today's image fills the top of the window with a Set as wallpaper button, recent images show as large wide previews, and region, image size, theme (System, Light or Dark) and the version are in a Settings dialog. Feedback appears as small pop-up notices.
- Faster and smoother: images download in the background (at most 4 at once, never twice), are decoded at the size they're shown, and are cached on disk so reopening the window is instant. Unused cached images are deleted after 30 days.
- The packages now also depend on libadwaita.

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
