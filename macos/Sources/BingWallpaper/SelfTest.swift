import AppKit
import BingWallpaperCore

/// `BingWallpaper --self-test <folder>`, run by CI on an Apple Silicon Mac: loads Bing's feed in
/// the real window, sets today's image on every display, checks macOS reports it as the
/// wallpaper, loads older gallery images, saves screenshots to <folder> and quits with 0 on success.
@MainActor
enum SelfTest {
    static func run(folder: URL, delegate: AppDelegate) async {
        try? FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        var lines: [String] = []
        var passed = true
        func check(_ ok: Bool, _ what: String) {
            lines.append((ok ? "PASS  " : "FAIL  ") + what)
            if !ok { passed = false }
            print(lines.last!)
        }

        let model = delegate.model
        model.theme = .light
        check(delegate.mainWindow?.isVisible == true, "main window is open")
        check(NSApp.activationPolicy() == .regular, "Dock icon shows while the window is open")

        let deadline = Date().addingTimeInterval(60)
        while model.images.isEmpty && Date() < deadline {
            try? await Task.sleep(for: .milliseconds(250))
        }
        check(!model.images.isEmpty, "loaded \(model.images.count) images from Bing (\(model.effectiveMarket)), error: \(model.loadError ?? "none")")

        if let today = model.today {
            let ok = await model.setWallpaper(today)
            check(ok, "set today's image: \(today.title)")
            if let path = model.lastSet?.path {
                for screen in NSScreen.screens {
                    check(WallpaperSetter.isShowing(URL(fileURLWithPath: path), on: screen),
                          "\(screen.localizedName) shows it (\(NSWorkspace.shared.desktopImageURL(for: screen)?.lastPathComponent ?? "nothing"))")
                }
            }
        }

        await model.loadMore()
        check(model.images.count > Bing.pageSize, "gallery loaded older images (\(model.images.count) in total)")

        // Let thumbnails arrive, then capture the window in both themes and the settings.
        try? await Task.sleep(for: .seconds(6))
        snapshot(delegate.mainWindow, to: folder.appendingPathComponent("window-light.png"))
        model.theme = .dark
        try? await Task.sleep(for: .seconds(2))
        snapshot(delegate.mainWindow, to: folder.appendingPathComponent("window-dark.png"))
        delegate.showSettings(nil)
        try? await Task.sleep(for: .seconds(2))
        snapshot(delegate.settingsWindow, to: folder.appendingPathComponent("settings.png"))
        screenCapture(to: folder.appendingPathComponent("screen.png"))
        model.theme = .system

        lines.append(passed ? "RESULT PASS" : "RESULT FAIL")
        try? lines.joined(separator: "\n").appending("\n").write(to: folder.appendingPathComponent("result.txt"), atomically: true, encoding: .utf8)
        exit(passed ? 0 : 1)
    }

    /// Draws the window's content into a PNG (no screen recording permission needed).
    private static func snapshot(_ window: NSWindow?, to url: URL) {
        guard let view = window?.contentView, let rep = view.bitmapImageRepForCachingDisplay(in: view.bounds) else { return }
        view.cacheDisplay(in: view.bounds, to: rep)
        try? rep.representation(using: .png, properties: [:])?.write(to: url)
    }

    /// The whole screen, wallpaper included. Shows only the wallpaper if screen recording isn't allowed.
    private static func screenCapture(to url: URL) {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/sbin/screencapture")
        process.arguments = ["-x", url.path]
        try? process.run()
        process.waitUntilExit()
    }
}
