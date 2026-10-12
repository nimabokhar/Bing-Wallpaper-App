// swift-tools-version:5.10
import PackageDescription

let package = Package(
    name: "BingWallpaper",
    platforms: [.macOS(.v14)],
    targets: [
        // Bing feed, schedule and file storage: Foundation only, unit tested.
        .target(name: "BingWallpaperCore", path: "Sources/BingWallpaperCore"),
        // The app itself: AppKit shell, SwiftUI window, menu bar item.
        .executableTarget(
            name: "BingWallpaper",
            dependencies: ["BingWallpaperCore"],
            path: "Sources/BingWallpaper"
        ),
        .testTarget(
            name: "BingWallpaperCoreTests",
            dependencies: ["BingWallpaperCore"],
            path: "Tests/BingWallpaperCoreTests"
        ),
    ]
)
