import XCTest
@testable import BingWallpaperCore

final class BingTests: XCTestCase {
    let sample = """
    {"images":[
      {"startdate":"20261012","fullstartdate":"202610120700","enddate":"20261013",
       "url":"/th?id=OHR.Lighthouse_EN-US123_1920x1080.jpg&rf=LaDigue_1920x1080.jpg",
       "urlbase":"/th?id=OHR.Lighthouse_EN-US123","copyright":"A lighthouse in Maine (© Someone/Getty)",
       "title":"Guiding light"},
      {"startdate":"20261011","urlbase":"/th?id=OHR.Fox_DE-DE456","copyright":"Ein Fuchs im Wald (© Jemand)","title":""}
    ]}
    """.data(using: .utf8)!

    func testParsesArchive() throws {
        let images = try Bing.parseArchive(sample)
        XCTAssertEqual(images.count, 2)
        XCTAssertEqual(images[0].id, "OHR.Lighthouse_EN-US123")
        XCTAssertEqual(images[0].title, "Guiding light")
        XCTAssertEqual(images[0].startDate, "20261012")
        XCTAssertEqual(images[0].url(resolution: "UHD").absoluteString,
                       "https://www.bing.com/th?id=OHR.Lighthouse_EN-US123_UHD.jpg")
        XCTAssertEqual(images[0].cardURL.absoluteString,
                       "https://www.bing.com/th?id=OHR.Lighthouse_EN-US123_1366x768.jpg")
    }

    func testMissingTitleComesFromCopyright() throws {
        XCTAssertEqual(try Bing.parseArchive(sample)[1].title, "Ein Fuchs im Wald")
    }

    func testEmptyArchive() throws {
        XCTAssertEqual(try Bing.parseArchive("{}".data(using: .utf8)!), [])
    }

    func testPaging() {
        XCTAssertEqual(Bing.pageStart(have: 0), 0)
        XCTAssertEqual(Bing.pageStart(have: 8), 7)
        XCTAssertNil(Bing.pageStart(have: 15))

        var images = try! Bing.parseArchive(sample)
        let added = Bing.merge(try! Bing.parseArchive(sample) + [BingImage(id: "x", title: "", copyright: "", startDate: "", urlBase: "")], into: &images)
        XCTAssertEqual(added, 1)
        XCTAssertEqual(images.map(\.id), ["OHR.Lighthouse_EN-US123", "OHR.Fox_DE-DE456", "x"])
    }

    func testSystemMarket() {
        XCTAssertEqual(Bing.systemMarket(locale: Locale(identifier: "de_DE")), "de-DE")
        XCTAssertEqual(Bing.systemMarket(locale: Locale(identifier: "fr_CA")), "fr-CA")
        XCTAssertEqual(Bing.systemMarket(locale: Locale(identifier: "nl_NL")), "en-US")
    }

    func testJPEGCheck() {
        XCTAssertTrue(Bing.looksLikeJPEG(Data([0xFF, 0xD8, 0xFF, 0xE0])))
        XCTAssertFalse(Bing.looksLikeJPEG("<html>".data(using: .utf8)!))
    }
}

final class ScheduleTests: XCTestCase {
    var calendar: Calendar = {
        var c = Calendar(identifier: .gregorian)
        c.timeZone = TimeZone(identifier: "Europe/Berlin")!
        return c
    }()

    func date(_ day: Int, _ hour: Int, _ minute: Int = 0) -> Date {
        calendar.date(from: DateComponents(year: 2026, month: 10, day: day, hour: hour, minute: minute))!
    }

    func testDueAfterChangeTimeOnly() {
        let seven = 7 * 60
        XCTAssertFalse(DailySchedule.isDue(now: date(12, 6, 59), minutes: seven, doneDay: "20261011", lastAttempt: nil, calendar: calendar))
        XCTAssertTrue(DailySchedule.isDue(now: date(12, 7), minutes: seven, doneDay: "20261011", lastAttempt: nil, calendar: calendar))
        XCTAssertFalse(DailySchedule.isDue(now: date(12, 9), minutes: seven, doneDay: "20261012", lastAttempt: nil, calendar: calendar))
    }

    func testRetriesHourlyWhileBingHasNoNewImage() {
        let seven = 7 * 60
        XCTAssertFalse(DailySchedule.isDue(now: date(12, 7, 30), minutes: seven, doneDay: "20261011", lastAttempt: date(12, 7), calendar: calendar))
        XCTAssertTrue(DailySchedule.isDue(now: date(12, 8), minutes: seven, doneDay: "20261011", lastAttempt: date(12, 7), calendar: calendar))
        // An attempt from before today's change time doesn't count.
        XCTAssertTrue(DailySchedule.isDue(now: date(12, 7, 5), minutes: seven, doneDay: "20261011", lastAttempt: date(12, 6, 30), calendar: calendar))
    }

    func testNextChange() {
        let seven = 7 * 60
        XCTAssertEqual(DailySchedule.nextChange(after: date(12, 6), minutes: seven, doneDay: "20261011", calendar: calendar), date(12, 7))
        XCTAssertEqual(DailySchedule.nextChange(after: date(12, 9), minutes: seven, doneDay: "20261012", calendar: calendar), date(13, 7))
        XCTAssertEqual(DailySchedule.nextChange(after: date(12, 9), minutes: seven, doneDay: "20261011", calendar: calendar), date(12, 9))
    }

    func check(_ result: (apply: Bool, done: Bool), apply: Bool, done: Bool, line: UInt = #line) {
        XCTAssertEqual(result.apply, apply, "apply", line: line)
        XCTAssertEqual(result.done, done, "done", line: line)
    }

    func testDecide() {
        let today = BingImage(id: "a", title: "", copyright: "", startDate: "20261012", urlBase: "")
        let yesterday = BingImage(id: "b", title: "", copyright: "", startDate: "20261011", urlBase: "")
        check(DailySchedule.decide(latest: today, currentID: "b", today: "20261012"), apply: true, done: true)
        check(DailySchedule.decide(latest: today, currentID: "a", today: "20261012"), apply: false, done: true)
        // Bing hasn't published today's image: put yesterday's up if needed, try again later.
        check(DailySchedule.decide(latest: yesterday, currentID: "z", today: "20261012"), apply: true, done: false)
        check(DailySchedule.decide(latest: yesterday, currentID: "b", today: "20261012"), apply: false, done: false)
    }
}

final class WallpaperStoreTests: XCTestCase {
    func testSavesAndPrunes() throws {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: dir) }
        let store = WallpaperStore(directory: dir)
        var last: URL?
        for i in 0..<(WallpaperStore.keep + 3) {
            let image = BingImage(id: "OHR.Img\(i)/x", title: "", copyright: "", startDate: "", urlBase: "")
            last = try store.save(Data([0xFF, 0xD8, 0xFF]), for: image, resolution: "UHD")
            Thread.sleep(forTimeInterval: 0.02)
        }
        XCTAssertEqual(last?.lastPathComponent, "OHR.Img\(WallpaperStore.keep + 2)_x_UHD.jpg")
        let files = try FileManager.default.contentsOfDirectory(atPath: dir.path)
        XCTAssertEqual(files.count, WallpaperStore.keep)
        XCTAssertTrue(files.contains(last!.lastPathComponent))
    }
}
