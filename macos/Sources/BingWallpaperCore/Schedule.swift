import Foundation

/// When the daily change happens. The wallpaper changes once a day at a chosen time; if Bing
/// hasn't published that day's image yet, the app checks again every hour until it has.
public enum DailySchedule {
    public static let defaultMinutes = 7 * 60
    /// How long to wait between checks while Bing hasn't published the day's image.
    public static let retryInterval: TimeInterval = 60 * 60

    /// The change time (`minutes` after midnight) on the day `date` falls on.
    public static func changeMoment(on date: Date, minutes: Int, calendar: Calendar = .current) -> Date {
        let start = calendar.startOfDay(for: date)
        return calendar.date(bySettingHour: minutes / 60, minute: minutes % 60, second: 0, of: start) ?? start
    }

    /// Whether to check Bing now: it's past today's change time, today's change hasn't
    /// happened yet, and the last check (if any) was long enough ago.
    public static func isDue(now: Date, minutes: Int, doneDay: String?, lastAttempt: Date?,
                             calendar: Calendar = .current) -> Bool {
        let moment = changeMoment(on: now, minutes: minutes, calendar: calendar)
        guard now >= moment, doneDay != Bing.dayKey(now, calendar: calendar) else { return false }
        guard let lastAttempt, lastAttempt >= moment else { return true }
        return now.timeIntervalSince(lastAttempt) >= retryInterval
    }

    /// When the next daily change will happen, for showing in the window and menu.
    public static func nextChange(after now: Date, minutes: Int, doneDay: String?,
                                  calendar: Calendar = .current) -> Date {
        if doneDay == Bing.dayKey(now, calendar: calendar) {
            let tomorrow = calendar.date(byAdding: .day, value: 1, to: now) ?? now
            return changeMoment(on: tomorrow, minutes: minutes, calendar: calendar)
        }
        // Today's change is still to come, or due now (waiting for Bing).
        return max(now, changeMoment(on: now, minutes: minutes, calendar: calendar))
    }

    /// What to do with Bing's newest image at a daily check: apply it if it isn't already the
    /// wallpaper, and call the day done once it is today's (or a later day's) image.
    public static func decide(latest: BingImage, currentID: String?, today: String) -> (apply: Bool, done: Bool) {
        (apply: latest.id != currentID, done: latest.startDate >= today)
    }
}
