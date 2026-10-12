# Bing Wallpaper for macOS

Sets your Mac's wallpaper to the Bing image of the day and changes it every day. Built for Apple Silicon Macs (M1 and newer); the same download also runs on Intel Macs.

Requires **macOS 14 Sonoma or newer**.

## Features

- **Every display:** today's image goes on all connected displays, filled to the screen.
- **Lock screen:** macOS doesn't let apps set a separate lock screen picture. The lock screen and login window show your desktop wallpaper, so they change along with it. Right after a restart, the login screen can show the previous image until you log in.
- **Every Space:** macOS keeps a wallpaper per Space (desktop) and apps can only change the one on screen, so the app puts the image on each Space as you switch to it. This only happens while the daily change is on, so a wallpaper you pick yourself in System Settings stays when it's off.
- **Daily change at a set time:** 7:00 by default, change it under **Change at**. If Bing hasn't published the day's image yet, the app checks again hourly. If the Mac was asleep or off, it catches up when it wakes or at login.
- **Gallery:** Bing's images newest first, loading older ones as you scroll, back to the roughly two weeks Bing keeps. Hover over a picture and click **Set as wallpaper**, double-click it, or right-click it.
- **Settings** (gear button or ⌘,): Bing region (14 countries, or Automatic from your Mac's language and region), image resolution (4K UHD by default, down to 1024×768, plus portrait), theme (System, Light or Dark), Open at login, and the version.
- **Menu bar:** the app keeps running in the menu bar (the sun icon) so the daily change works with the window closed. From there you can open the window, set today's image, see when the next change is, or quit. The Dock icon only shows while the window is open.

## Install

1. Download [`bing-wallpaper-macos.dmg`](https://github.com/nimabokhar/Bing-Wallpaper-App/releases/download/latest/bing-wallpaper-macos.dmg) and open it.
2. Drag **Bing Wallpaper** to **Applications**.
3. Open it from Applications. The first time, macOS says it can't check the app for malicious software, because the app isn't signed with an Apple Developer ID yet. Click **Done**, then open **System Settings → Privacy & Security**, scroll down to "Bing Wallpaper was blocked" and click **Open Anyway**, then confirm. You only need to do this once per download.

   Or, in Terminal: `xattr -dr com.apple.quarantine "/Applications/Bing Wallpaper.app"`, then open it normally.
4. Click **Set as wallpaper**. Daily changes run on their own from then on. macOS shows a "Background item added" notice because the app opens at login; you can turn that off in Settings.

To update, quit the app from its menu bar icon, then replace it in Applications with the new one.

## Build it yourself

You need a Mac with Xcode 16 or the Command Line Tools (Swift 5.10 or newer).

```sh
cd macos
swift test                 # unit tests
swift run BingWallpaper    # run from the terminal (no app icon)
scripts/build-app.sh       # dist/Bing Wallpaper.app, .dmg and .zip (Apple Silicon + Intel)
```

`UNIVERSAL=0 scripts/build-app.sh` builds for Apple Silicon only. The version comes from [`../VERSION`](../VERSION).

`"dist/Bing Wallpaper.app/Contents/MacOS/BingWallpaper" --self-test /tmp/out` is what CI runs: it opens the window, loads Bing's images, sets today's image on every display, checks macOS reports it, saves screenshots to `/tmp/out` and quits with 0 on success. It changes your wallpaper.

## How it works

| File | What it does |
| --- | --- |
| `Sources/BingWallpaperCore/Bing.swift` | Bing's image-of-the-day feed: regions, sizes, paging back through about two weeks |
| `Sources/BingWallpaperCore/Schedule.swift` | When the daily change is due, hourly retries while Bing hasn't published |
| `Sources/BingWallpaperCore/WallpaperStore.swift` | Downloaded wallpapers in `~/Library/Application Support/Bing Wallpaper/Wallpapers` (the newest 6 are kept) |
| `Sources/BingWallpaper/AppDelegate.swift` | App entry, menu bar item, windows, timers, Space and wake notifications |
| `Sources/BingWallpaper/AppModel.swift` | State and settings shared by the window and menu bar |
| `Sources/BingWallpaper/WallpaperSetter.swift` | Sets the wallpaper on each display with `NSWorkspace` |
| `Sources/BingWallpaper/ImageLoader.swift` | Gallery pictures: background downloads, disk cache in `~/Library/Caches`, decoded at the size shown |
| `Sources/BingWallpaper/Views.swift` | The SwiftUI window and Settings |
| `Resources/` | `Info.plist` template and the icon on the macOS icon grid |

Settings are stored in the `com.nimabokhar.bingwallpaper` defaults domain.
