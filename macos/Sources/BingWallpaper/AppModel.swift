import AppKit
import BingWallpaperCore
import ServiceManagement
import SwiftUI

enum Theme: String, CaseIterable, Identifiable {
    case system, light, dark

    var id: String { rawValue }
    var label: String {
        switch self {
        case .system: return "System"
        case .light: return "Light"
        case .dark: return "Dark"
        }
    }
}

/// The wallpaper the app set last, remembered across launches.
struct LastSet: Codable, Equatable {
    let id: String
    let title: String
    let date: Date
    let path: String
}

struct Toast: Equatable {
    let id = UUID()
    let text: String
    let isError: Bool
}

/// Everything the window, menu bar item and daily schedule share.
@MainActor
final class AppModel: ObservableObject {
    static let shared = AppModel()

    private enum Key {
        static let market = "market"
        static let resolution = "resolution"
        static let daily = "dailyEnabled"
        static let dailyMinutes = "dailyMinutes"
        static let theme = "theme"
        static let doneDay = "dailyDoneDay"
        static let lastAttempt = "dailyLastAttempt"
        static let lastSet = "lastSet"
        static let loginItemSetUp = "loginItemSetUp"
    }

    private let defaults = UserDefaults.standard
    private let client = BingClient.shared
    private let store = WallpaperStore.standard

    /// Newest first; the first one is today's image.
    @Published private(set) var images: [BingImage] = []
    @Published private(set) var isLoading = false
    @Published private(set) var loadError: String?
    @Published private(set) var isLoadingMore = false
    @Published private(set) var loadMoreFailed = false
    @Published private(set) var hasMore = true
    @Published private(set) var isSetting = false
    @Published private(set) var toast: Toast?
    @Published private(set) var lastSet: LastSet?
    @Published private(set) var doneDay: String?
    @Published private(set) var loginItemStatus: SMAppService.Status = .notRegistered

    /// Bing market code, or nil to follow the Mac's language and region.
    @Published var market: String? {
        didSet {
            guard market != oldValue else { return }
            defaults.set(market, forKey: Key.market)
            images = []
            hasMore = true
            Task { await refresh() }
        }
    }

    @Published var resolution: String {
        didSet { defaults.set(resolution, forKey: Key.resolution) }
    }

    @Published var dailyEnabled: Bool {
        didSet {
            defaults.set(dailyEnabled, forKey: Key.daily)
            if dailyEnabled { Task { await runDailyCheckIfDue() } }
        }
    }

    /// Time of the daily change, in minutes after midnight.
    @Published var dailyMinutes: Int {
        didSet {
            guard dailyMinutes != oldValue else { return }
            defaults.set(dailyMinutes, forKey: Key.dailyMinutes)
            // Let the new time count today; re-checking an image that's already set changes nothing.
            doneDay = nil
            defaults.removeObject(forKey: Key.doneDay)
            defaults.removeObject(forKey: Key.lastAttempt)
        }
    }

    @Published var theme: Theme {
        didSet {
            defaults.set(theme.rawValue, forKey: Key.theme)
            applyTheme()
        }
    }

    private var dailyCheckRunning = false

    private init() {
        market = defaults.string(forKey: Key.market)
        resolution = defaults.string(forKey: Key.resolution) ?? Bing.defaultResolution
        dailyEnabled = defaults.object(forKey: Key.daily) as? Bool ?? true
        dailyMinutes = defaults.object(forKey: Key.dailyMinutes) as? Int ?? DailySchedule.defaultMinutes
        theme = Theme(rawValue: defaults.string(forKey: Key.theme) ?? "") ?? .system
        doneDay = defaults.string(forKey: Key.doneDay)
        if let data = defaults.data(forKey: Key.lastSet) {
            lastSet = try? JSONDecoder().decode(LastSet.self, from: data)
        }
        loginItemStatus = SMAppService.mainApp.status
    }

    var today: BingImage? { images.first }
    var effectiveMarket: String { market ?? Bing.systemMarket() }

    static var version: String {
        Bundle.main.object(forInfoDictionaryKey: "BWFullVersion") as? String ?? "development build"
    }

    // MARK: - Bing feed

    func refresh() async {
        let market = effectiveMarket
        isLoading = true
        loadError = nil
        defer { isLoading = false }
        do {
            let page = try await client.fetch(market: market)
            guard market == effectiveMarket else { return }
            images = page
            loadMoreFailed = false
            hasMore = Bing.pageStart(have: page.count) != nil
        } catch {
            loadError = error.localizedDescription
        }
    }

    /// Loads the next page of older images for the gallery.
    func loadMore() async {
        guard hasMore, !isLoadingMore, !images.isEmpty else { return }
        let market = effectiveMarket
        isLoadingMore = true
        loadMoreFailed = false
        defer { isLoadingMore = false }
        do {
            let page = try await client.fetchPage(market: market, have: images.count)
            guard market == effectiveMarket else { return }
            var all = images
            let added = Bing.merge(page, into: &all)
            images = all
            hasMore = added > 0 && Bing.pageStart(have: all.count) != nil
        } catch {
            loadMoreFailed = true
        }
    }

    // MARK: - Setting the wallpaper

    /// Downloads `image` and puts it on every display. Returns whether it worked.
    @discardableResult
    func setWallpaper(_ image: BingImage, announce: Bool = true) async -> Bool {
        guard !isSetting else { return false }
        isSetting = true
        defer { isSetting = false }
        do {
            let data = try await client.downloadWallpaper(image, resolution: resolution)
            let url = try store.save(data, for: image, resolution: resolution)
            try WallpaperSetter.apply(url)
            let set = LastSet(id: image.id, title: image.title, date: Date(), path: url.path)
            lastSet = set
            if let encoded = try? JSONEncoder().encode(set) {
                defaults.set(encoded, forKey: Key.lastSet)
            }
            if announce { show("Wallpaper set: \(image.title)") }
            return true
        } catch {
            show("Couldn't set the wallpaper: \(error.localizedDescription)", isError: true)
            return false
        }
    }

    /// Puts the current wallpaper on displays and Spaces that don't show it yet. macOS sets a
    /// wallpaper per Space, and apps can only reach the Space on screen, so this runs whenever
    /// you switch Spaces or plug in a display. It only does so while the daily change is on, so a
    /// wallpaper you pick yourself in System Settings stays when the daily change is off.
    func reapplyWhereMissing() {
        guard dailyEnabled, let path = lastSet?.path, FileManager.default.fileExists(atPath: path) else { return }
        WallpaperSetter.applyWhereDifferent(URL(fileURLWithPath: path))
    }

    // MARK: - Daily change

    var nextChange: Date {
        DailySchedule.nextChange(after: Date(), minutes: dailyMinutes, doneDay: doneDay)
    }

    var nextChangeText: String {
        let next = nextChange
        if next <= Date() { return "Waiting for Bing's new image" }
        let time = next.formatted(date: .omitted, time: .shortened)
        return Calendar.current.isDateInToday(next) ? "Next change today at \(time)" : "Next change tomorrow at \(time)"
    }

    var dailyTime: Date {
        get { DailySchedule.changeMoment(on: Date(), minutes: dailyMinutes) }
        set {
            let parts = Calendar.current.dateComponents([.hour, .minute], from: newValue)
            dailyMinutes = (parts.hour ?? 7) * 60 + (parts.minute ?? 0)
        }
    }

    /// Runs the daily change if it's due. Called every minute, at launch and after waking.
    func runDailyCheckIfDue(now: Date = Date()) async {
        guard dailyEnabled, !dailyCheckRunning else { return }
        let lastAttempt = defaults.object(forKey: Key.lastAttempt) as? Date
        guard DailySchedule.isDue(now: now, minutes: dailyMinutes, doneDay: doneDay, lastAttempt: lastAttempt) else { return }
        dailyCheckRunning = true
        defer { dailyCheckRunning = false }
        defaults.set(now, forKey: Key.lastAttempt)
        do {
            guard let latest = try await client.fetch(market: effectiveMarket, count: 1).first else { return }
            let today = Bing.dayKey(now)
            let decision = DailySchedule.decide(latest: latest, currentID: lastSet?.id, today: today)
            if decision.apply {
                guard await setWallpaper(latest, announce: false) else { return }
            }
            if decision.done {
                doneDay = today
                defaults.set(today, forKey: Key.doneDay)
            }
            if images.first?.id != latest.id { await refresh() }
        } catch {
            // Offline or Bing unreachable: the next hourly retry tries again.
        }
    }

    // MARK: - Settings

    func applyTheme() {
        switch theme {
        case .system: NSApp.appearance = nil
        case .light: NSApp.appearance = NSAppearance(named: .aqua)
        case .dark: NSApp.appearance = NSAppearance(named: .darkAqua)
        }
    }

    var openAtLogin: Bool {
        loginItemStatus == .enabled || loginItemStatus == .requiresApproval
    }

    func setOpenAtLogin(_ on: Bool) {
        do {
            if on {
                try SMAppService.mainApp.register()
            } else {
                try SMAppService.mainApp.unregister()
            }
        } catch {
            show("Couldn't change Open at login: \(error.localizedDescription)", isError: true)
        }
        refreshLoginItemStatus()
    }

    func refreshLoginItemStatus() {
        loginItemStatus = SMAppService.mainApp.status
    }

    /// Opens at login by default, so the daily change keeps working after a restart. Only done
    /// once, so turning it off in Settings or System Settings sticks.
    func setUpLoginItemOnce() {
        guard !defaults.bool(forKey: Key.loginItemSetUp) else { return }
        defaults.set(true, forKey: Key.loginItemSetUp)
        if SMAppService.mainApp.status != .enabled {
            try? SMAppService.mainApp.register()
        }
        refreshLoginItemStatus()
    }

    // MARK: - Notices

    func show(_ text: String, isError: Bool = false) {
        let toast = Toast(text: text, isError: isError)
        withAnimation(.spring(duration: 0.3)) { self.toast = toast }
        Task {
            try? await Task.sleep(for: .seconds(isError ? 5 : 3))
            if self.toast == toast {
                withAnimation(.easeOut(duration: 0.25)) { self.toast = nil }
            }
        }
    }
}
