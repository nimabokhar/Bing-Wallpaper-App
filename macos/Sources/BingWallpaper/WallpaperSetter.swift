import AppKit

/// Puts an image on the desktop of every display.
///
/// macOS has no separate lock screen wallpaper for apps to set: the lock screen and the login
/// window show the desktop wallpaper of the main display, so setting the desktop changes them too.
enum WallpaperSetter {
    /// "Fill Screen": scaled to cover the display, cropping the edges if the shapes differ.
    static let options: [NSWorkspace.DesktopImageOptionKey: Any] = [
        .imageScaling: NSImageScaling.scaleProportionallyUpOrDown.rawValue,
        .allowClipping: true,
    ]

    static func apply(_ url: URL) throws {
        var lastError: Error?
        var applied = 0
        for screen in NSScreen.screens {
            do {
                try NSWorkspace.shared.setDesktopImageURL(url, for: screen, options: options)
                applied += 1
            } catch {
                lastError = error
            }
        }
        if applied == 0, let lastError { throw lastError }
    }

    /// Sets `url` only on displays (in the current Space) that show something else.
    static func applyWhereDifferent(_ url: URL) {
        for screen in NSScreen.screens where !isShowing(url, on: screen) {
            try? NSWorkspace.shared.setDesktopImageURL(url, for: screen, options: options)
        }
    }

    static func isShowing(_ url: URL, on screen: NSScreen) -> Bool {
        NSWorkspace.shared.desktopImageURL(for: screen)?.standardizedFileURL.path == url.standardizedFileURL.path
    }
}
