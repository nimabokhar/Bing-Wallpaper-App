import AppKit
import BingWallpaperCore
import CryptoKit
import ImageIO

/// Loads the window's pictures without stalling it: downloads run in the background (at most 4
/// at once, never twice for the same picture), are cached on disk, and are decoded at the size
/// they're shown rather than full size. Decoded pictures are kept in memory for instant reuse.
actor ImageLoader {
    static let shared = ImageLoader()

    /// Cached files unused for this long are deleted.
    static let maxAge: TimeInterval = 30 * 24 * 60 * 60

    private let memory = NSCache<NSString, Box>()
    private var inflight: [String: Task<CGImage?, Never>] = [:]
    private let directory: URL

    private final class Box {
        let image: CGImage
        init(_ image: CGImage) { self.image = image }
    }

    init() {
        let caches = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)[0]
        directory = caches.appendingPathComponent("com.nimabokhar.bingwallpaper/images", isDirectory: true)
        try? FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        memory.countLimit = 80
    }

    /// The picture at `url`, decoded so its longer side is at most `maxPixel` pixels.
    func image(for url: URL, maxPixel: Int) async -> CGImage? {
        let key = "\(maxPixel)|\(url.absoluteString)"
        if let hit = memory.object(forKey: key as NSString) { return hit.image }
        if let running = inflight[key] { return await running.value }

        let file = directory.appendingPathComponent(Self.hash(url.absoluteString) + ".jpg")
        let task = Task.detached(priority: .userInitiated) { () -> CGImage? in
            var data = try? Data(contentsOf: file)
            if data != nil {
                try? FileManager.default.setAttributes([.modificationDate: Date()], ofItemAtPath: file.path)
            } else {
                guard let fetched = try? await BingClient.shared.data(from: url), Bing.looksLikeJPEG(fetched) else {
                    return nil
                }
                try? fetched.write(to: file, options: .atomic)
                data = fetched
            }
            return data.flatMap { Self.decode($0, maxPixel: maxPixel) }
        }
        inflight[key] = task
        let result = await task.value
        inflight[key] = nil
        if let result { memory.setObject(Box(result), forKey: key as NSString) }
        return result
    }

    /// Deletes cached pictures that haven't been shown for `maxAge`.
    func prune() {
        let fm = FileManager.default
        guard let files = try? fm.contentsOfDirectory(at: directory, includingPropertiesForKeys: [.contentModificationDateKey]) else { return }
        let cutoff = Date().addingTimeInterval(-Self.maxAge)
        for file in files {
            let modified = (try? file.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate) ?? .distantPast
            if modified < cutoff { try? fm.removeItem(at: file) }
        }
    }

    static func decode(_ data: Data, maxPixel: Int) -> CGImage? {
        guard let source = CGImageSourceCreateWithData(data as CFData, nil) else { return nil }
        let options: [CFString: Any] = [
            kCGImageSourceCreateThumbnailFromImageAlways: true,
            kCGImageSourceCreateThumbnailWithTransform: true,
            kCGImageSourceShouldCacheImmediately: true,
            kCGImageSourceThumbnailMaxPixelSize: maxPixel,
        ]
        return CGImageSourceCreateThumbnailAtIndex(source, 0, options as CFDictionary)
    }

    static func hash(_ text: String) -> String {
        SHA256.hash(data: Data(text.utf8)).map { String(format: "%02x", $0) }.joined()
    }
}
