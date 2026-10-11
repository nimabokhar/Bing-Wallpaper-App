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
| macOS | `macos/` | Planned |

All builds are published to the same [**latest release**](https://github.com/nimabokhar/Bing-Wallpaper-Android-App/releases/tag/latest).

## Android

- **Home and lock screen:** the daily image goes on both. For images you pick from the gallery, choose home, lock or both.
- **Daily updates:** checks every few hours in the background and switches as soon as Bing publishes a new image. Keeps working after a reboot.
- **Gallery:** browse the last 8 Bing images and tap one to use it. A hand-picked image stays until Bing publishes the next one.
- **Region picker:** choose which country's Bing image you get (14 markets), or leave it on Automatic to follow your phone's language and region.
- **Dark mode:** follows your phone's theme, or pick Light or Dark.
- **Foldables:** the image is cropped for the unfolded screen so it stays sharp on both screens, and the gallery shows more columns when unfolded.
- **Themed icon:** the launcher icon follows your wallpaper colours on Android 13+.

Requires Android 7.0 or newer.

### Install

1. On your phone, download [`bing-wallpaper.apk`](https://github.com/nimabokhar/Bing-Wallpaper-Android-App/releases/download/latest/bing-wallpaper.apk) from the latest release.
2. Open it, and allow your browser or file manager to install unknown apps when Android asks.
3. Open **Bing Wallpaper** and tap **Set today's image now**. Daily updates run on their own from then on.

If updates stop, set the app's battery usage to Unrestricted (Settings → Apps → Bing Wallpaper → Battery). Some phone makers stop background apps aggressively.

The [Android README](android/README.md) covers updating without uninstalling (signing keys) and building from source.

## Repository layout

```
android/            Android app (Kotlin, Gradle)
linux/              Linux app (in progress)
icon/               App icon: SVG source plus PNG and ICO exports for every platform
.github/workflows/  One CI workflow per platform, each only runs on changes to its folder
```

### Adding a platform

1. Put the app in a new top-level folder named after the platform (for example `windows/`), with its own README covering features, install and local build.
2. Use the icon from [`icon/`](icon/) rather than drawing a new one.
3. Add `.github/workflows/<platform>.yml` that only runs on changes under that folder (`paths: ["<platform>/**", ".github/workflows/<platform>.yml"]`) and uploads its build to the `latest` release with `gh release upload latest <file> --clobber`. Give the file a platform-specific name so it doesn't replace another platform's download.
4. Add a row to the platforms table above.

## Credits

Images are © their respective owners and are provided by Microsoft Bing. This project is not affiliated with or endorsed by Microsoft.

## License

[MIT](LICENSE)
