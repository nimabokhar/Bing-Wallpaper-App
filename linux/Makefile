PREFIX ?= /usr
DESTDIR ?=
VERSION := $(shell python3 -c "import re;print(re.search(r'__version__ = \"(.+)\"', open('bing_wallpaper/__init__.py').read())[1])")
APP_ID := io.github.nimabokhar.BingWallpaper

.PHONY: all test install uninstall packages clean

all:

test:
	python3 -m unittest discover -s tests -v

install:
	install -Dm755 data/bing-wallpaper $(DESTDIR)$(PREFIX)/bin/bing-wallpaper
	for f in bing_wallpaper/*.py; do \
		install -Dm644 $$f $(DESTDIR)$(PREFIX)/share/bing-wallpaper/$$f; \
	done
	install -Dm644 data/bing-wallpaper.service $(DESTDIR)$(PREFIX)/lib/systemd/user/bing-wallpaper.service
	install -Dm644 data/bing-wallpaper.timer $(DESTDIR)$(PREFIX)/lib/systemd/user/bing-wallpaper.timer
	install -Dm644 data/$(APP_ID).desktop $(DESTDIR)$(PREFIX)/share/applications/$(APP_ID).desktop
	install -Dm644 data/$(APP_ID).svg $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps/$(APP_ID).svg
	install -Dm644 data/bing-wallpaper-autostart.desktop $(DESTDIR)/etc/xdg/autostart/bing-wallpaper-autostart.desktop
	install -Dm644 ../LICENSE $(DESTDIR)$(PREFIX)/share/licenses/bing-wallpaper/LICENSE

uninstall:
	rm -rf $(DESTDIR)$(PREFIX)/share/bing-wallpaper
	rm -f $(DESTDIR)$(PREFIX)/bin/bing-wallpaper \
		$(DESTDIR)$(PREFIX)/lib/systemd/user/bing-wallpaper.service \
		$(DESTDIR)$(PREFIX)/lib/systemd/user/bing-wallpaper.timer \
		$(DESTDIR)$(PREFIX)/share/applications/$(APP_ID).desktop \
		$(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps/$(APP_ID).svg \
		$(DESTDIR)/etc/xdg/autostart/bing-wallpaper-autostart.desktop

# Builds .deb, .rpm and Arch .pkg.tar.zst into dist/ (needs nfpm: https://nfpm.goreleaser.com).
packages:
	rm -rf build dist && mkdir -p dist
	$(MAKE) install DESTDIR=$(CURDIR)/build/root
	for p in deb rpm archlinux; do \
		VERSION=$(VERSION) nfpm package -f packaging/nfpm.yaml -p $$p -t dist/; \
	done

clean:
	rm -rf build dist
	find . -name __pycache__ -prune -exec rm -rf {} +
