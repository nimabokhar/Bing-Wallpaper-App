import AppKit
import BingWallpaperCore
import CoreServices
import SwiftUI

@main
enum BingWallpaperApp {
    @MainActor
    static func main() {
        let app = NSApplication.shared
        let delegate = AppDelegate()
        app.delegate = delegate
        app.run()
    }
}

/// Runs in the menu bar so the daily change keeps working with the window closed. The Dock
/// icon only shows while a window is open.
@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate, NSMenuDelegate {
    let model = AppModel.shared
    private(set) var mainWindow: NSWindow?
    private(set) var settingsWindow: NSWindow?
    private var statusItem: NSStatusItem?
    private var nextChangeItem: NSMenuItem?
    private var timer: Timer?
    private var launchedAtLogin = false

    /// `--self-test <folder>`: CI check that opens the window, sets a wallpaper and quits.
    private let selfTestFolder: URL? = {
        let args = CommandLine.arguments
        guard let index = args.firstIndex(of: "--self-test"), index + 1 < args.count else { return nil }
        return URL(fileURLWithPath: args[index + 1], isDirectory: true)
    }()

    func applicationWillFinishLaunching(_ notification: Notification) {
        // At login, start quietly in the menu bar instead of opening the window.
        if let event = NSAppleEventManager.shared().currentAppleEvent,
           event.eventID == AEEventID(kAEOpenApplication),
           event.paramDescriptor(forKeyword: AEKeyword(keyAEPropData))?.enumCodeValue == OSType(keyAELaunchedAsLogInItem) {
            launchedAtLogin = true
        }
        if CommandLine.arguments.contains("--background") { launchedAtLogin = true }
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        buildMainMenu()
        buildStatusItem()
        model.applyTheme()
        if selfTestFolder == nil { model.setUpLoginItemOnce() }

        let workspace = NSWorkspace.shared.notificationCenter
        workspace.addObserver(self, selector: #selector(spaceChanged), name: NSWorkspace.activeSpaceDidChangeNotification, object: nil)
        workspace.addObserver(self, selector: #selector(woke), name: NSWorkspace.didWakeNotification, object: nil)
        NotificationCenter.default.addObserver(self, selector: #selector(spaceChanged), name: NSApplication.didChangeScreenParametersNotification, object: nil)
        NotificationCenter.default.addObserver(self, selector: #selector(woke), name: .NSSystemClockDidChange, object: nil)

        let timer = Timer(timeInterval: 60, repeats: true) { [weak self] _ in
            Task { @MainActor in await self?.model.runDailyCheckIfDue() }
        }
        timer.tolerance = 10
        RunLoop.main.add(timer, forMode: .common)
        self.timer = timer

        Task {
            await model.refresh()
            await model.runDailyCheckIfDue()
            model.reapplyWhereMissing()
            await ImageLoader.shared.prune()
        }

        if !launchedAtLogin || selfTestFolder != nil { showMainWindow(nil) }
        if let selfTestFolder {
            Task { await SelfTest.run(folder: selfTestFolder, delegate: self) }
        }
    }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        showMainWindow(nil)
        return true
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { false }

    @objc private func spaceChanged() {
        model.reapplyWhereMissing()
    }

    @objc private func woke() {
        Task {
            await model.runDailyCheckIfDue()
            model.reapplyWhereMissing()
        }
    }

    // MARK: - Windows

    @objc func showMainWindow(_ sender: Any?) {
        if mainWindow == nil {
            let hosting = NSHostingController(rootView: MainView().environmentObject(model))
            hosting.sizingOptions = []
            let window = NSWindow(contentViewController: hosting)
            window.title = "Bing Wallpaper"
            window.styleMask = [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView]
            window.titlebarAppearsTransparent = true
            window.titleVisibility = .hidden
            window.isReleasedWhenClosed = false
            window.minSize = NSSize(width: 560, height: 560)
            window.setContentSize(NSSize(width: 1000, height: 840))
            window.center()
            window.setFrameAutosaveName("MainWindow")
            window.delegate = self
            mainWindow = window
        }
        present(mainWindow)
    }

    @objc func showSettings(_ sender: Any?) {
        if settingsWindow == nil {
            let hosting = NSHostingController(rootView: SettingsView().environmentObject(model))
            let window = NSWindow(contentViewController: hosting)
            window.title = "Settings"
            window.styleMask = [.titled, .closable]
            window.isReleasedWhenClosed = false
            window.center()
            window.delegate = self
            settingsWindow = window
        }
        present(settingsWindow)
    }

    private func present(_ window: NSWindow?) {
        NSApp.setActivationPolicy(.regular)
        window?.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    func windowWillClose(_ notification: Notification) {
        let closing = notification.object as? NSWindow
        let stillOpen = [mainWindow, settingsWindow].contains { $0 != nil && $0 !== closing && $0!.isVisible }
        if !stillOpen {
            // Back to the menu bar only, without a Dock icon.
            DispatchQueue.main.async { NSApp.setActivationPolicy(.accessory) }
        }
    }

    @objc private func setToday(_ sender: Any?) {
        Task {
            if model.today == nil { await model.refresh() }
            if let today = model.today { await model.setWallpaper(today) }
        }
    }

    @objc private func showAbout(_ sender: Any?) {
        NSApp.orderFrontStandardAboutPanel(options: [
            .applicationVersion: AppModel.version,
            .version: "",
            .credits: NSAttributedString(string: "Images © their owners, provided by Microsoft Bing. Not affiliated with Microsoft."),
        ])
        NSApp.activate(ignoringOtherApps: true)
    }

    // MARK: - Menus

    private func buildMainMenu() {
        let main = NSMenu()

        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "About Bing Wallpaper", action: #selector(showAbout(_:)), keyEquivalent: "").target = self
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Settings…", action: #selector(showSettings(_:)), keyEquivalent: ",").target = self
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Hide Bing Wallpaper", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h")
        let hideOthers = appMenu.addItem(withTitle: "Hide Others", action: #selector(NSApplication.hideOtherApplications(_:)), keyEquivalent: "h")
        hideOthers.keyEquivalentModifierMask = [.command, .option]
        appMenu.addItem(withTitle: "Show All", action: #selector(NSApplication.unhideAllApplications(_:)), keyEquivalent: "")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Quit Bing Wallpaper", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        main.addItem(submenu: appMenu, title: "Bing Wallpaper")

        let fileMenu = NSMenu(title: "File")
        fileMenu.addItem(withTitle: "Set Today's Image", action: #selector(setToday(_:)), keyEquivalent: "t").target = self
        fileMenu.addItem(.separator())
        fileMenu.addItem(withTitle: "Close Window", action: #selector(NSWindow.performClose(_:)), keyEquivalent: "w")
        main.addItem(submenu: fileMenu, title: "File")

        let windowMenu = NSMenu(title: "Window")
        windowMenu.addItem(withTitle: "Minimize", action: #selector(NSWindow.performMiniaturize(_:)), keyEquivalent: "m")
        windowMenu.addItem(withTitle: "Zoom", action: #selector(NSWindow.performZoom(_:)), keyEquivalent: "")
        windowMenu.addItem(.separator())
        windowMenu.addItem(withTitle: "Bing Wallpaper", action: #selector(showMainWindow(_:)), keyEquivalent: "0").target = self
        main.addItem(submenu: windowMenu, title: "Window")
        NSApp.windowsMenu = windowMenu

        NSApp.mainMenu = main
    }

    private func buildStatusItem() {
        let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        let symbol = NSImage(systemSymbolName: "sun.horizon.fill", accessibilityDescription: "Bing Wallpaper")
        symbol?.isTemplate = true
        item.button?.image = symbol

        let menu = NSMenu()
        menu.delegate = self
        menu.addItem(withTitle: "Open Bing Wallpaper", action: #selector(showMainWindow(_:)), keyEquivalent: "").target = self
        menu.addItem(withTitle: "Set Today's Image", action: #selector(setToday(_:)), keyEquivalent: "").target = self
        menu.addItem(.separator())
        let next = menu.addItem(withTitle: "", action: nil, keyEquivalent: "")
        next.isEnabled = false
        nextChangeItem = next
        menu.addItem(.separator())
        menu.addItem(withTitle: "Settings…", action: #selector(showSettings(_:)), keyEquivalent: ",").target = self
        menu.addItem(withTitle: "Quit Bing Wallpaper", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        item.menu = menu
        statusItem = item
    }

    func menuNeedsUpdate(_ menu: NSMenu) {
        nextChangeItem?.title = model.dailyEnabled ? model.nextChangeText : "Daily change is off"
    }
}

private extension NSMenu {
    func addItem(submenu: NSMenu, title: String) {
        let item = NSMenuItem(title: title, action: nil, keyEquivalent: "")
        item.submenu = submenu
        addItem(item)
    }
}
