"""Talks to Bing's image-of-the-day archive."""

from __future__ import annotations

import json
import locale
import os
import urllib.request
from dataclasses import dataclass
from typing import List, Optional

from . import __version__

BASE = "https://www.bing.com"
DEFAULT_MARKET = "en-US"

#: Images per request; Bing returns at most 8.
MAX_IMAGES = 8
#: Bing's feed reaches back about two weeks: idx (days back) stops at 7, n at 8.
MAX_IDX = 7

#: Markets Bing publishes an image of the day for, with display names.
MARKETS = [
    ("en-US", "United States"),
    ("en-GB", "United Kingdom"),
    ("en-CA", "Canada (English)"),
    ("fr-CA", "Canada (French)"),
    ("en-AU", "Australia"),
    ("en-NZ", "New Zealand"),
    ("en-IN", "India"),
    ("de-DE", "Germany"),
    ("fr-FR", "France"),
    ("es-ES", "Spain"),
    ("it-IT", "Italy"),
    ("pt-BR", "Brazil"),
    ("ja-JP", "Japan"),
    ("zh-CN", "China"),
]

#: Sizes Bing serves every image of the day in, largest first, with labels.
RESOLUTIONS = [
    ("UHD", "4K UHD (3840×2160)"),
    ("1920x1200", "1920×1200"),
    ("1920x1080", "Full HD (1920×1080)"),
    ("1366x768", "1366×768"),
    ("1280x720", "HD (1280×720)"),
    ("1024x768", "1024×768"),
    ("1080x1920", "Portrait (1080×1920)"),
]
DEFAULT_RESOLUTION = "UHD"

USER_AGENT = f"Mozilla/5.0 (X11; Linux x86_64) BingWallpaper/{__version__}"


@dataclass
class BingImage:
    #: Stable id of the image, e.g. "OHR.SomePlace_EN-US1234567890".
    id: str
    title: str
    copyright: str
    #: Day the image was Bing's image of the day, as yyyyMMdd.
    start_date: str
    #: Full-resolution 3840x2160 image.
    uhd_url: str
    #: 1920x1080 image, used if UHD fails.
    hd_url: str
    #: Image Bing shows on its home page, used if both fail.
    fallback_url: str
    #: Small landscape version for the gallery.
    thumbnail_url: str
    #: Bing's path prefix for this image's sizes, e.g. "/th?id=OHR.SomePlace_EN-US123".
    url_base: str = ""

    def url_for(self, resolution: str) -> str:
        if not self.url_base:
            return self.uhd_url
        return f"{BASE}{self.url_base}_{resolution}.jpg"

    @property
    def nice_date(self) -> str:
        d = self.start_date
        return f"{d[0:4]}-{d[4:6]}-{d[6:8]}" if len(d) == 8 else d


def system_market(lang: Optional[str] = None) -> str:
    """The market matching the system language and region, or en-US."""
    if lang is None:
        lang = (
            os.environ.get("LC_ALL")
            or os.environ.get("LC_MESSAGES")
            or os.environ.get("LANG")
            or (locale.getlocale()[0] or "")
        )
    # "en_GB.UTF-8@euro" -> "en-GB"
    tag = lang.split(".")[0].split("@")[0].replace("_", "-")
    for code, _ in MARKETS:
        if code.lower() == tag.lower():
            return code
    return DEFAULT_MARKET


def market_name(code: str) -> str:
    return dict(MARKETS).get(code, code)


def parse_archive(data: dict) -> List[BingImage]:
    images = []
    for image in data.get("images", []):
        url_base = image["urlbase"]
        images.append(
            BingImage(
                id=url_base.split("id=", 1)[-1],
                title=image.get("title", ""),
                copyright=image.get("copyright", ""),
                start_date=image.get("startdate", ""),
                uhd_url=f"{BASE}{url_base}_UHD.jpg",
                hd_url=f"{BASE}{url_base}_1920x1080.jpg",
                fallback_url=BASE + image["url"],
                thumbnail_url=f"{BASE}{url_base}_640x360.jpg",
                url_base=url_base,
            )
        )
    return images


def fetch_latest(market: str, count: int = MAX_IMAGES, start: int = 0) -> List[BingImage]:
    """Up to `count` (at most 8) images, newest first, starting `start` days back."""
    url = f"{BASE}/HPImageArchive.aspx?format=js&idx={start}&n={count}&mkt={market}"
    return parse_archive(json.loads(http_get(url).decode("utf-8")))


def fetch_page(market: str, have: int) -> List[BingImage]:
    """The next images for a gallery that already shows `have` of them, newest first.
    Bing can't start further back than MAX_IDX days, so pages overlap and callers drop
    images they already have; an empty result (after that) means there are no more."""
    if have >= MAX_IDX + MAX_IMAGES:
        return []
    return fetch_latest(market, MAX_IMAGES, min(have, MAX_IDX))


def fetch_all(market: str) -> List[BingImage]:
    """Every image Bing still has (about two weeks), newest first."""
    images: List[BingImage] = []
    while True:
        seen = {i.id for i in images}
        new = [i for i in fetch_page(market, len(images)) if i.id not in seen]
        if not new:
            return images
        images += new


def http_get(url: str, timeout: float = 30) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def looks_like_jpeg(data: bytes) -> bool:
    return data[:3] == b"\xff\xd8\xff"


def resolution_name(resolution: str) -> str:
    return dict(RESOLUTIONS).get(resolution, resolution)


def download_image(image: BingImage, resolution: str = DEFAULT_RESOLUTION) -> bytes:
    """The image in `resolution`, falling back to Full HD, UHD and then whatever Bing
    shows on its home page if that size isn't available."""
    urls = []
    for url in (image.url_for(resolution), image.hd_url, image.uhd_url, image.fallback_url):
        if url not in urls:
            urls.append(url)
    for url in urls:
        try:
            data = http_get(url)
        except OSError:
            continue
        if looks_like_jpeg(data):
            return data
    raise OSError(f"Could not download image {image.id}")
