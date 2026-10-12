PREFIX ?= /usr
DESTDIR ?=
# The repo-wide VERSION file (semver, e.g. 0.1.0-alpha.1) when there is one,
# else the version in the Python package.
VERSION := $(shell cat ../VERSION 2>/dev/null || sed -n 's/^__version__ = "\(.*\)"/\1/p' bing_wallpaper/__init__.py)
# Package managers order pre-releases before the final release when written
# 0.1.0~alpha.1 (deb, rpm) or 0.1.0alpha.1 (pacman, which allows no - or ~).
TILDE_VERSION := $(subst -,~,$(VERSION))
ARCH_VERSION := $(subst -,,$(VERSION))
APP_ID := io.github.nimabokhar.BingWallpaper
ICON_SIZES := 16 24 32 48 64 128 256 512

.PHONY: all test install uninstall packages version clean

all:

test:
	python3 -m unittest discover -s tests -v

install:
	install -Dm755 data/bing-wallpaper $(DESTDIR)$(PREFIX)/bin/bing-wallpaper
	for f in bing_wallpaper/*.py; do \
		install -Dm644 $$f $(DESTDIR)$(PREFIX)/share/bing-wallpaper/$$f; \
	done
	sed -i 's/^__version__ = .*/__version__ = "$(VERSION)"/' \
		$(DESTDIR)$(PREFIX)/share/bing-wallpaper/bing_wallpaper/__init__.py
	install -Dm644 data/bing-wallpaper.service $(DESTDIR)$(PREFIX)/lib/systemd/user/bing-wallpaper.service
	install -Dm644 data/bing-wallpaper.timer $(DESTDIR)$(PREFIX)/lib/systemd/user/bing-wallpaper.timer
	install -Dm644 data/$(APP_ID).desktop $(DESTDIR)$(PREFIX)/share/applications/$(APP_ID).desktop
	install -Dm644 ../icon/icon.svg $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps/$(APP_ID).svg
	install -Dm644 ../icon/icon-symbolic.svg $(DESTDIR)$(PREFIX)/share/icons/hicolor/symbolic/apps/$(APP_ID)-symbolic.svg
	for size in $(ICON_SIZES); do \
		install -Dm644 ../icon/png/bing-wallpaper-$$size.png \
			$(DESTDIR)$(PREFIX)/share/icons/hicolor/$${size}x$${size}/apps/$(APP_ID).png; \
	done
	install -Dm644 data/bing-wallpaper-autostart.desktop $(DESTDIR)/etc/xdg/autostart/bing-wallpaper-autostart.desktop
	install -Dm644 ../LICENSE $(DESTDIR)$(PREFIX)/share/licenses/bing-wallpaper/LICENSE

uninstall:
	rm -rf $(DESTDIR)$(PREFIX)/share/bing-wallpaper
	rm -f $(DESTDIR)$(PREFIX)/bin/bing-wallpaper \
		$(DESTDIR)$(PREFIX)/lib/systemd/user/bing-wallpaper.service \
		$(DESTDIR)$(PREFIX)/lib/systemd/user/bing-wallpaper.timer \
		$(DESTDIR)$(PREFIX)/share/applications/$(APP_ID).desktop \
		$(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps/$(APP_ID).svg \
		$(DESTDIR)$(PREFIX)/share/icons/hicolor/symbolic/apps/$(APP_ID)-symbolic.svg \
		$(foreach size,$(ICON_SIZES),$(DESTDIR)$(PREFIX)/share/icons/hicolor/$(size)x$(size)/apps/$(APP_ID).png) \
		$(DESTDIR)/etc/xdg/autostart/bing-wallpaper-autostart.desktop
	rm -rf $(DESTDIR)$(PREFIX)/share/licenses/bing-wallpaper

# Builds .deb, .rpm and Arch .pkg.tar.zst into dist/ (needs nfpm: https://nfpm.goreleaser.com).
packages:
	rm -rf build dist && mkdir -p dist
	$(MAKE) install DESTDIR=$(CURDIR)/build/root
	cd build/root && find usr -type f | LC_ALL=C sort \
		| sed 's|.*|  - src: build/root/&\n    dst: /&|' > ../usr-files.yaml
	sed -e '/# @USR_FILES@/r build/usr-files.yaml' -e '/# @USR_FILES@/d' packaging/nfpm.yaml > build/nfpm.yaml
	PKG_VERSION=$(TILDE_VERSION) nfpm package -f build/nfpm.yaml -p deb -t dist/
	PKG_VERSION=$(TILDE_VERSION) nfpm package -f build/nfpm.yaml -p rpm -t dist/
	PKG_VERSION=$(ARCH_VERSION) nfpm package -f build/nfpm.yaml -p archlinux -t dist/

version:
	@echo $(VERSION)

clean:
	rm -rf build dist
	find . -name __pycache__ -prune -exec rm -rf {} +
