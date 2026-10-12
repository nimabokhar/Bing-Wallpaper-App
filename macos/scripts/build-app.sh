#!/usr/bin/env bash
# Builds "Bing Wallpaper.app" (Apple Silicon and Intel in one binary), signs it ad hoc, and
# packages it as dist/bing-wallpaper-macos.dmg and .zip. Run from anywhere on a Mac with Xcode
# or the Command Line Tools.
#
#   BUILD_NUMBER=42 macos/scripts/build-app.sh   # version shows as <VERSION>+build.42
set -euo pipefail

here="$(cd "$(dirname "$0")/.." && pwd)"
root="$(cd "$here/.." && pwd)"
cd "$here"

version="$(tr -d '[:space:]' < "$root/VERSION" 2>/dev/null || echo 0.0.0-dev)"
full_version="$version${BUILD_NUMBER:++build.$BUILD_NUMBER}"
short_version="${version%%-*}"           # 0.2.0-alpha.2 -> 0.2.0
build_version="${BUILD_NUMBER:-$short_version}" # must be numbers and dots

arch_flags=(--arch arm64)
if [ "${UNIVERSAL:-1}" = 1 ]; then arch_flags+=(--arch x86_64); fi
swift build -c release "${arch_flags[@]}"
bin="$(swift build -c release "${arch_flags[@]}" --show-bin-path)/BingWallpaper"

dist="$here/dist"
app="$dist/Bing Wallpaper.app"
rm -rf "$dist"
mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources"
cp "$bin" "$app/Contents/MacOS/BingWallpaper"
sed -e "s/@SHORT_VERSION@/$short_version/" -e "s/@BUILD_VERSION@/$build_version/" -e "s/@FULL_VERSION@/$full_version/" \
  Resources/Info.plist > "$app/Contents/Info.plist"
plutil -lint "$app/Contents/Info.plist"

# App icon: the shared icon on the macOS icon grid (Resources/AppIcon-1024.png), at every size.
iconset="$dist/AppIcon.iconset"
mkdir -p "$iconset"
for size in 16 32 128 256 512; do
  sips -z "$size" "$size" Resources/AppIcon-1024.png --out "$iconset/icon_${size}x${size}.png" >/dev/null
  sips -z $((size * 2)) $((size * 2)) Resources/AppIcon-1024.png --out "$iconset/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$iconset" -o "$app/Contents/Resources/AppIcon.icns"
rm -rf "$iconset"

# Ad hoc signature: Apple Silicon only runs signed code, and there's no Developer ID yet.
codesign --force --deep --sign - --timestamp=none "$app"
codesign --verify --strict --verbose=2 "$app"
lipo -info "$app/Contents/MacOS/BingWallpaper"

# Zip (keeps the signature and permissions) and a disk image with an Applications shortcut.
ditto -c -k --keepParent "$app" "$dist/bing-wallpaper-macos.zip"
staging="$dist/dmg"
mkdir -p "$staging"
cp -R "$app" "$staging/"
ln -s /Applications "$staging/Applications"
hdiutil create -volname "Bing Wallpaper" -srcfolder "$staging" -fs HFS+ -format UDZO -ov "$dist/bing-wallpaper-macos.dmg"
rm -rf "$staging"

echo "Built $full_version:"
ls -la "$dist"
