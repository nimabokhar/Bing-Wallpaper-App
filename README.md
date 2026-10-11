# Bing Wallpaper for Android

Sets your phone's home screen and lock screen wallpaper to the [Bing image of the day](https://www.bing.com), and keeps it updated every day.

## Features

- **Latest images** shows the last 8 Bing images of the day (as far back as Bing's archive goes). Tap one to set it on the home screen, the lock screen, or both.
- **Set today's image now** applies the newest image to both home and lock screen immediately.
- **Update daily** (on by default) checks every few hours in the background and switches the wallpaper as soon as Bing publishes a new image. The schedule survives reboots. If you pick an older image by hand, it stays until the next new Bing image comes out.
- **Bing region** lets you pick which country's image you get. The default follows your phone's language and region (falling back to United States). The app downloads the full-resolution (UHD) image and crops it to your screen.
- **Foldable phones:** the wallpaper is cropped for the inner (unfolded) screen, and Android centre-crops it for the narrower cover screen, so it looks right and stays sharp on both. The gallery shows more columns when the phone is unfolded.

Requires Android 7.0 (API 24) or newer.

## Install

1. Open the [**latest release**](../../releases/tag/latest) on your phone and download `bing-wallpaper.apk`.
   (Builds from pull requests are also attached to each run on the Actions tab as the `bing-wallpaper-apk` artifact.)
2. Open the file and allow your browser or file manager to install unknown apps when Android asks.
3. Launch **Bing Wallpaper** and tap **Set today's image now** (or pick an image) once. Daily updates run from then on.

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
