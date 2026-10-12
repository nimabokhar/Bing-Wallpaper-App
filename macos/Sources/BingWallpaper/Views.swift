import AppKit
import BingWallpaperCore
import ServiceManagement
import SwiftUI

/// The main window: today's image at the top, the daily change below it, then recent images.
struct MainView: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        GeometryReader { window in
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    HeroView(height: max(320, window.size.height * 0.48))
                    VStack(alignment: .leading, spacing: 28) {
                        DailyCard()
                        GallerySection()
                    }
                    .padding(.horizontal, 24)
                    .padding(.bottom, 28)
                }
            }
        }
        .ignoresSafeArea(edges: .top)
        .background(Color(nsColor: .windowBackgroundColor))
        .overlay(alignment: .bottom) { ToastView() }
        .frame(minWidth: 560, minHeight: 560)
    }
}

/// A picture from Bing that fills its frame, cropping the edges, and fades in once loaded.
struct RemoteImage: View {
    let url: URL
    var maxPixel: Int = 1200
    @State private var image: CGImage?

    var body: some View {
        Color.clear
            .overlay {
                if let image {
                    Image(decorative: image, scale: 1)
                        .resizable()
                        .scaledToFill()
                        .transition(.opacity)
                }
            }
            .clipped()
            .task(id: url) {
                image = nil
                let loaded = await ImageLoader.shared.image(for: url, maxPixel: maxPixel)
                withAnimation(.easeOut(duration: 0.18)) { image = loaded }
            }
    }
}

struct HeroView: View {
    @EnvironmentObject private var model: AppModel
    let height: CGFloat

    var body: some View {
        ZStack(alignment: .bottomLeading) {
            Color.black
            if let today = model.today {
                RemoteImage(url: today.heroURL, maxPixel: 2400)
            }
            LinearGradient(colors: [.black.opacity(0.4), .clear], startPoint: .top, endPoint: UnitPoint(x: 0.5, y: 0.22))
            LinearGradient(colors: [.clear, .black.opacity(0.78)], startPoint: UnitPoint(x: 0.5, y: 0.35), endPoint: .bottom)
            content
                .padding(.horizontal, 32)
                .padding(.bottom, 28)
        }
        .frame(maxWidth: .infinity)
        .frame(height: height)
        .clipShape(UnevenRoundedRectangle(bottomLeadingRadius: 24, bottomTrailingRadius: 24, style: .continuous))
        .overlay(alignment: .topTrailing) {
            Button {
                NSApp.sendAction(#selector(AppDelegate.showSettings(_:)), to: nil, from: nil)
            } label: {
                Image(systemName: "gearshape.fill")
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundStyle(.white)
                    .frame(width: 34, height: 34)
                    .background(.ultraThinMaterial, in: Circle())
                    .environment(\.colorScheme, .dark)
            }
            .buttonStyle(.plain)
            .help("Settings")
            .padding(.top, 14)
            .padding(.trailing, 16)
        }
    }

    @ViewBuilder
    private var content: some View {
        if let today = model.today {
            VStack(alignment: .leading, spacing: 6) {
                Text(dateLine(today))
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.white.opacity(0.85))
                Text(today.title)
                    .font(.system(size: 30, weight: .bold))
                    .foregroundStyle(.white)
                    .lineLimit(2)
                Text(today.copyright)
                    .font(.callout)
                    .foregroundStyle(.white.opacity(0.8))
                    .lineLimit(2)
                Button {
                    Task { await model.setWallpaper(today) }
                } label: {
                    Label("Set as wallpaper", systemImage: "photo.on.rectangle")
                        .padding(.horizontal, 6)
                }
                .buttonStyle(.borderedProminent)
                .buttonBorderShape(.capsule)
                .controlSize(.large)
                .disabled(model.isSetting)
                .padding(.top, 10)
            }
            .shadow(color: .black.opacity(0.35), radius: 6, y: 1)
        } else if let error = model.loadError {
            VStack(alignment: .leading, spacing: 10) {
                Text("Couldn't reach Bing")
                    .font(.title.bold())
                    .foregroundStyle(.white)
                Text(error)
                    .foregroundStyle(.white.opacity(0.8))
                Button("Try Again") { Task { await model.refresh() } }
                    .controlSize(.large)
            }
        } else {
            ProgressView()
                .controlSize(.large)
                .tint(.white)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    private func dateLine(_ image: BingImage) -> String {
        guard let date = image.date else { return "" }
        let day = date.formatted(.dateTime.month(.abbreviated).day())
        return Calendar.current.isDateInToday(date) ? "Today · \(day)" : day
    }
}

struct DailyCard: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Change every day").font(.headline)
                    Text("All displays and the lock screen")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Toggle("Change every day", isOn: $model.dailyEnabled)
                    .toggleStyle(.switch)
                    .labelsHidden()
            }
            .padding(16)
            Divider().padding(.leading, 16)
            HStack {
                Text("Change at")
                Spacer()
                DatePicker("Change at", selection: $model.dailyTime, displayedComponents: .hourAndMinute)
                    .datePickerStyle(.field)
                    .labelsHidden()
            }
            .padding(16)
            .disabled(!model.dailyEnabled)
            Divider().padding(.leading, 16)
            TimelineView(.periodic(from: .now, by: 30)) { _ in
                Text(statusLine)
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .padding(16)
            if model.isSetting {
                ProgressView()
                    .progressViewStyle(.linear)
                    .padding(.horizontal, 16)
                    .padding(.bottom, 12)
            }
        }
        .background(Color(nsColor: .controlBackgroundColor), in: RoundedRectangle(cornerRadius: 14, style: .continuous))
        .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous).strokeBorder(Color(nsColor: .separatorColor)))
    }

    private var statusLine: String {
        var parts: [String] = []
        if let last = model.lastSet {
            let ago = RelativeDateTimeFormatter().localizedString(for: last.date, relativeTo: Date())
            parts.append("Last set: \(last.title) (\(ago))")
        } else {
            parts.append("No wallpaper set yet")
        }
        if model.dailyEnabled { parts.append(model.nextChangeText) }
        return parts.joined(separator: " · ")
    }
}

struct GallerySection: View {
    @EnvironmentObject private var model: AppModel

    /// Today's image is the big one at the top, so the gallery starts from yesterday.
    private var gallery: [BingImage] { Array(model.images.dropFirst()) }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Recent images")
                .font(.title2.weight(.semibold))
            LazyVGrid(columns: [GridItem(.adaptive(minimum: 320), spacing: 16)], spacing: 16) {
                ForEach(gallery) { image in
                    GalleryCard(image: image)
                        .onAppear {
                            if image.id == gallery.last?.id { Task { await model.loadMore() } }
                        }
                }
            }
            Group {
                if model.isLoadingMore {
                    ProgressView().controlSize(.small)
                } else if model.loadMoreFailed {
                    Button("Load More") { Task { await model.loadMore() } }
                } else if !model.hasMore && !gallery.isEmpty {
                    Text("That's every image Bing still has, about two weeks.")
                        .font(.callout)
                        .foregroundStyle(.secondary)
                }
            }
            .frame(maxWidth: .infinity)
        }
    }
}

struct GalleryCard: View {
    @EnvironmentObject private var model: AppModel
    let image: BingImage
    @State private var hovering = false

    var body: some View {
        Color.clear
            .aspectRatio(16 / 9, contentMode: .fit)
            .overlay { RemoteImage(url: image.cardURL, maxPixel: 1000) }
            .overlay(alignment: .bottom) {
                LinearGradient(colors: [.clear, .black.opacity(0.75)], startPoint: .top, endPoint: .bottom)
                    .frame(height: 96)
            }
            .overlay(alignment: .bottomLeading) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(image.title)
                        .font(.headline)
                        .foregroundStyle(.white)
                        .lineLimit(1)
                    Text(image.date?.formatted(.dateTime.weekday(.abbreviated).month(.abbreviated).day()) ?? "")
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.8))
                }
                .padding(14)
            }
            .overlay(alignment: .topTrailing) {
                if hovering {
                    Button("Set as wallpaper") { set() }
                        .buttonStyle(.borderedProminent)
                        .buttonBorderShape(.capsule)
                        .disabled(model.isSetting)
                        .padding(10)
                        .transition(.opacity)
                }
            }
            .background(Color.black)
            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
            .contentShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
            .onHover { inside in
                withAnimation(.easeOut(duration: 0.15)) { hovering = inside }
            }
            .onTapGesture(count: 2) { set() }
            .contextMenu {
                Button("Set as Wallpaper") { set() }
            }
            .help(image.copyright)
    }

    private func set() {
        Task { await model.setWallpaper(image) }
    }
}

struct ToastView: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        if let toast = model.toast {
            Label(toast.text, systemImage: toast.isError ? "exclamationmark.triangle.fill" : "checkmark.circle.fill")
                .lineLimit(2)
                .padding(.horizontal, 18)
                .padding(.vertical, 10)
                .background(.regularMaterial, in: Capsule())
                .shadow(color: .black.opacity(0.2), radius: 10, y: 3)
                .padding(.bottom, 22)
                .padding(.horizontal, 24)
                .transition(.move(edge: .bottom).combined(with: .opacity))
                .id(toast.id)
        }
    }
}

struct SettingsView: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        Form {
            Section("Images") {
                Picker("Bing region", selection: $model.market) {
                    Text("Automatic (\(Bing.marketName(Bing.systemMarket())))").tag(String?.none)
                    Divider()
                    ForEach(Bing.markets, id: \.code) { market in
                        Text(market.name).tag(Optional(market.code))
                    }
                }
                Picker("Image resolution", selection: $model.resolution) {
                    ForEach(Bing.resolutions, id: \.code) { resolution in
                        Text(resolution.name).tag(resolution.code)
                    }
                }
            }
            Section("Appearance") {
                Picker("Theme", selection: $model.theme) {
                    ForEach(Theme.allCases) { theme in
                        Text(theme.label).tag(theme)
                    }
                }
                .pickerStyle(.segmented)
            }
            Section {
                Toggle("Open at login", isOn: Binding(
                    get: { model.openAtLogin },
                    set: { model.setOpenAtLogin($0) }
                ))
                if model.loginItemStatus == .requiresApproval {
                    HStack {
                        Text("Allow Bing Wallpaper under Login Items in System Settings.")
                            .font(.callout)
                            .foregroundStyle(.secondary)
                        Spacer()
                        Button("Open") { SMAppService.openSystemSettingsLoginItems() }
                    }
                }
            } footer: {
                Text("Bing Wallpaper stays in the menu bar to change your wallpaper each day.")
                    .font(.callout)
                    .foregroundStyle(.secondary)
            }
            Section {
                LabeledContent("Version", value: AppModel.version)
            }
        }
        .formStyle(.grouped)
        .frame(width: 480, height: 440)
        .onAppear { model.refreshLoginItemStatus() }
    }
}
