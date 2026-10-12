import Foundation

/// Where downloaded wallpapers live: ~/Library/Application Support/Bing Wallpaper/Wallpapers.
/// macOS keeps reading the file after it is set, so it must not be in a cache folder. Each
/// image gets its own file name, because macOS won't redraw a wallpaper whose path didn't change.
public struct WallpaperStore: Sendable {
    public let directory: URL
    /// Wallpapers kept on disk; older ones are deleted.
    public static let keep = 6

    public init(directory: URL) {
        self.directory = directory
    }

    public static var standard: WallpaperStore {
        let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        return WallpaperStore(directory: support.appendingPathComponent("Bing Wallpaper/Wallpapers", isDirectory: true))
    }

    public func fileURL(for image: BingImage, resolution: String) -> URL {
        let allowed = CharacterSet.alphanumerics.union(CharacterSet(charactersIn: "._-"))
        let safeID = String(image.id.unicodeScalars.map { allowed.contains($0) ? Character($0) : "_" })
        return directory.appendingPathComponent("\(safeID)_\(resolution).jpg")
    }

    /// Writes the image and deletes old ones, keeping `keep` newest files.
    @discardableResult
    public func save(_ data: Data, for image: BingImage, resolution: String) throws -> URL {
        let fm = FileManager.default
        try fm.createDirectory(at: directory, withIntermediateDirectories: true)
        let url = fileURL(for: image, resolution: resolution)
        try data.write(to: url, options: .atomic)
        // Touch it so re-setting an old image counts as recent.
        try? fm.setAttributes([.modificationDate: Date()], ofItemAtPath: url.path)
        prune(protecting: url)
        return url
    }

    public func prune(protecting current: URL? = nil) {
        let fm = FileManager.default
        guard let files = try? fm.contentsOfDirectory(at: directory, includingPropertiesForKeys: [.contentModificationDateKey]) else { return }
        let dated = files.filter { $0.pathExtension == "jpg" }.map { url -> (URL, Date) in
            let date = (try? url.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate) ?? .distantPast
            return (url, date)
        }.sorted { $0.1 > $1.1 }
        for (url, _) in dated.dropFirst(Self.keep) where url.standardizedFileURL != current?.standardizedFileURL {
            try? fm.removeItem(at: url)
        }
    }
}
