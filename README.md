# Bing Wallpaper for Android

Sets your phone's home screen and lock screen wallpaper to the [Bing image of the day](https://www.bing.com), and keeps it updated every day.

## Features

- Shows today's Bing image with its title and credit.
- **Set wallpaper now** applies it to both home and lock screen immediately.
- **Update daily** (on by default) checks every few hours in the background and switches the wallpaper as soon as Bing publishes a new image. The schedule survives reboots.
- Uses the Bing market that matches your phone's language and region (falls back to en-US), and downloads a portrait 1080×1920 image cropped to your screen.

Requires Android 7.0 (API 24) or newer.

## Install

1. Open the [**latest release**](../../releases/tag/latest) on your phone and download `bing-wallpaper.apk`.
   (Builds from pull requests are also attached to each run on the Actions tab as the `bing-wallpaper-apk` artifact.)
2. Open the file and allow your browser or file manager to install unknown apps when Android asks.
3. Launch **Bing Wallpaper** and tap **Set wallpaper now** once. Daily updates run from then on.

If daily updates stop on your phone, exclude the app from battery optimisation (Settings → Apps → Bing Wallpaper → Battery → Unrestricted). Some manufacturers aggressively stop background work.

### Updating without uninstalling

By default each CI build is signed with a fresh debug key, so Android will refuse to install a new build over an old one; uninstall first. To get in-place updates, add a signing key as repository secrets:

| Secret | Value |
| --- | --- |
| `SIGNING_KEYSTORE_BASE64` | your `.jks` keystore, base64-encoded |
| `SIGNING_STORE_PASSWORD` | keystore password |
| `SIGNING_KEY_ALIAS` | key alias |
| `SIGNING_KEY_PASSWORD` | key password |

Create a keystore with `keytool -genkeypair -keystore release.jks -alias bing -keyalg RSA -validity 10000` and encode it with `base64 -w0 release.jks`.

## Build locally

```sh
./gradlew assembleRelease
```

Needs JDK 17 and the Android SDK (platform 35). The APK lands in `app/build/outputs/apk/release/`.
