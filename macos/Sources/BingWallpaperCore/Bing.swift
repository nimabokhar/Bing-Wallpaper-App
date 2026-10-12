import Foundation

/// One Bing image of the day.
public struct BingImage: Codable, Hashable, Identifiable, Sendable {
    /// Stable id, e.g. "OHR.SomePlace_EN-US1234567890".
    public let id: String
    public let title: String
    public let copyright: String
    /// Day the image was Bing's image of the day, as yyyyMMdd.
    public let startDate: String
    /// Bing's path prefix for this image's sizes, e.g. "/th?id=OHR.SomePlace_EN-US123".
    public let urlBase: String

    public init(id: String, title: String, copyright: String, startDate: String, urlBase: String) {
        self.id = id
        self.title = title
        self.copyright = copyright
        self.startDate = startDate
        self.urlBase = urlBase
    }

    /// The image in one of Bing's sizes, e.g. "UHD" or "1920x1080".
    public func url(resolution: String) -> URL {
        URL(string: Bing.base + urlBase + "_" + resolution + ".jpg")!
    }

    /// Size shown at the top of the window.
    public var heroURL: URL { url(resolution: "1920x1080") }
    /// Size shown on the gallery cards.
    public var cardURL: URL { url(resolution: "1366x768") }

    public var date: Date? { Bing.parseDay(startDate) }
}

public struct Market: Hashable, Sendable {
    public let code: String
    public let name: String
}

public struct Resolution: Hashable, Sendable {
    public let code: String
    public let name: String
}

public enum Bing {
    public static let base = "https://www.bing.com"
    /// Images per request; Bing returns at most 8.
    public static let pageSize = 8
    /// Bing's feed reaches back about two weeks: idx (days back) stops at 7, n at 8.
    public static let maxIdx = 7
    public static let defaultMarket = "en-US"
    public static let defaultResolution = "UHD"

    /// Markets Bing publishes an image of the day for. Same list as Android and Linux.
    public static let markets: [Market] = [
        Market(code: "en-US", name: "United States"),
        Market(code: "en-GB", name: "United Kingdom"),
        Market(code: "en-CA", name: "Canada (English)"),
        Market(code: "fr-CA", name: "Canada (French)"),
        Market(code: "en-AU", name: "Australia"),
        Market(code: "en-NZ", name: "New Zealand"),
        Market(code: "en-IN", name: "India"),
        Market(code: "de-DE", name: "Germany"),
        Market(code: "fr-FR", name: "France"),
        Market(code: "es-ES", name: "Spain"),
        Market(code: "it-IT", name: "Italy"),
        Market(code: "pt-BR", name: "Brazil"),
        Market(code: "ja-JP", name: "Japan"),
        Market(code: "zh-CN", name: "China"),
    ]

    /// Sizes Bing serves every image of the day in, largest first.
    public static let resolutions: [Resolution] = [
        Resolution(code: "UHD", name: "4K UHD (3840×2160)"),
        Resolution(code: "1920x1200", name: "1920×1200"),
        Resolution(code: "1920x1080", name: "Full HD (1920×1080)"),
        Resolution(code: "1366x768", name: "1366×768"),
        Resolution(code: "1280x720", name: "HD (1280×720)"),
        Resolution(code: "1024x768", name: "1024×768"),
        Resolution(code: "1080x1920", name: "Portrait (1080×1920)"),
    ]

    /// The market matching the Mac's language and region, or United States.
    public static func systemMarket(locale: Locale = .current) -> String {
        let language = locale.language.languageCode?.identifier ?? "en"
        let region = locale.region?.identifier ?? "US"
        let tag = "\(language)-\(region)"
        return markets.first { $0.code.caseInsensitiveCompare(tag) == .orderedSame }?.code ?? defaultMarket
    }

    public static func marketName(_ code: String) -> String {
        markets.first { $0.code == code }?.name ?? code
    }

    public static func archiveURL(market: String, start: Int, count: Int) -> URL {
        URL(string: "\(base)/HPImageArchive.aspx?format=js&idx=\(start)&n=\(count)&mkt=\(market)")!
    }

    /// Where the next gallery page starts for a gallery that already shows `have` images, or nil
    /// when Bing has nothing older. Bing can't start further back than `maxIdx` days, so pages
    /// overlap and callers drop images they already have.
    public static func pageStart(have: Int) -> Int? {
        have >= maxIdx + pageSize ? nil : min(have, maxIdx)
    }

    public static func parseArchive(_ data: Data) throws -> [BingImage] {
        struct Archive: Decodable { let images: [Raw]? }
        struct Raw: Decodable {
            let startdate: String?
            let urlbase: String
            let copyright: String?
            let title: String?
        }
        let archive = try JSONDecoder().decode(Archive.self, from: data)
        return (archive.images ?? []).map { raw in
            let copyright = raw.copyright ?? ""
            var title = raw.title ?? ""
            if title.isEmpty || title == "Info" {
                // Some markets leave the title out; the copyright starts with a description.
                title = copyright.components(separatedBy: " (©").first ?? copyright
            }
            let id = raw.urlbase.components(separatedBy: "id=").last ?? raw.urlbase
            return BingImage(id: id, title: title, copyright: copyright,
                             startDate: raw.startdate ?? "", urlBase: raw.urlbase)
        }
    }

    /// Adds `page` to `images`, dropping images already there. Returns how many were new.
    public static func merge(_ page: [BingImage], into images: inout [BingImage]) -> Int {
        var seen = Set(images.map(\.id))
        var added = 0
        for image in page where !seen.contains(image.id) {
            images.append(image)
            seen.insert(image.id)
            added += 1
        }
        return added
    }

    private static func dayFormatter(_ calendar: Calendar) -> DateFormatter {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.calendar = calendar
        formatter.timeZone = calendar.timeZone
        formatter.dateFormat = "yyyyMMdd"
        return formatter
    }

    public static func parseDay(_ day: String, calendar: Calendar = .current) -> Date? {
        dayFormatter(calendar).date(from: day)
    }

    /// The day `date` falls on, as yyyyMMdd.
    public static func dayKey(_ date: Date, calendar: Calendar = .current) -> String {
        dayFormatter(calendar).string(from: date)
    }

    public static func looksLikeJPEG(_ data: Data) -> Bool {
        data.count > 3 && data.prefix(3) == Data([0xFF, 0xD8, 0xFF])
    }
}

public enum BingError: LocalizedError {
    case badResponse(Int)
    case notAnImage

    public var errorDescription: String? {
        switch self {
        case .badResponse(let status): return "Bing answered with HTTP \(status)."
        case .notAnImage: return "Bing didn't send an image."
        }
    }
}

/// Network access to Bing. At most 4 downloads run at once.
public final class BingClient: Sendable {
    public static let shared = BingClient()

    private let session: URLSession

    public init(userAgent: String = "BingWallpaper-macOS") {
        let config = URLSessionConfiguration.default
        config.httpMaximumConnectionsPerHost = 4
        config.timeoutIntervalForRequest = 30
        config.httpAdditionalHeaders = ["User-Agent": "Mozilla/5.0 (Macintosh) \(userAgent)"]
        session = URLSession(configuration: config)
    }

    public func data(from url: URL) async throws -> Data {
        let (data, response) = try await session.data(from: url)
        if let http = response as? HTTPURLResponse, http.statusCode != 200 {
            throw BingError.badResponse(http.statusCode)
        }
        return data
    }

    /// Up to `count` (at most 8) images, newest first, starting `start` days back.
    public func fetch(market: String, start: Int = 0, count: Int = Bing.pageSize) async throws -> [BingImage] {
        try Bing.parseArchive(try await data(from: Bing.archiveURL(market: market, start: start, count: count)))
    }

    /// The next page for a gallery that already shows `have` images (may overlap; see `Bing.merge`).
    public func fetchPage(market: String, have: Int) async throws -> [BingImage] {
        guard let start = Bing.pageStart(have: have) else { return [] }
        return try await fetch(market: market, start: start)
    }

    /// The image in `resolution`, falling back to Full HD and then UHD if that size isn't available.
    public func downloadWallpaper(_ image: BingImage, resolution: String) async throws -> Data {
        var tried: [String] = []
        var lastError: Error = BingError.notAnImage
        for size in [resolution, "1920x1080", "UHD"] where !tried.contains(size) {
            tried.append(size)
            do {
                let data = try await data(from: image.url(resolution: size))
                if Bing.looksLikeJPEG(data) { return data }
                lastError = BingError.notAnImage
            } catch {
                lastError = error
            }
        }
        throw lastError
    }
}
