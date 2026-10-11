# Bing Wallpaper

Sets your wallpaper to the [Bing image of the day](https://www.bing.com) and keeps it updated every day.

Each platform is a separate app in its own folder, with its own build and its own CI workflow:

| Platform | Folder | Status |
| --- | --- | --- |
| Android (phone home and lock screen) | [`android/`](android/) | Available: [download the APK](https://github.com/nimabokhar/Bing-Wallpaper-Android-App/releases/tag/latest) |
| Linux | `linux/` | In progress |
| Windows | `windows/` | Planned |
| macOS | `macos/` | Planned |

All builds are published to the same [**latest release**](https://github.com/nimabokhar/Bing-Wallpaper-Android-App/releases/tag/latest).

## Adding a platform

1. Put the app in a new top-level folder named after the platform (for example `windows/`), with its own README covering features, install and local build.
2. Add `.github/workflows/<platform>.yml` that only runs on changes under that folder (`paths: ["<platform>/**", ".github/workflows/<platform>.yml"]`) and uploads its build to the `latest` release with `gh release upload latest <file> --clobber`. Give the file a platform-specific name so it doesn't replace another platform's download.
3. Add a row to the table above.

## License

[MIT](LICENSE)
