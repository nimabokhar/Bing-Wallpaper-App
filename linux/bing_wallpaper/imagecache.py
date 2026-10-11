"""Disk cache for gallery images, so reopening the window is instant.

Downloads run on a small thread pool (at most 4 at once), and a request for an image
that is already downloading shares that download instead of starting another.
"""

from __future__ import annotations

import hashlib
import os
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Dict, Optional

from . import bing, settings

#: Cached files not used for this long are deleted.
MAX_AGE_DAYS = 30


class DiskCache:
    def __init__(
        self,
        folder: Optional[Path] = None,
        fetch: Callable[[str], bytes] = bing.http_get,
        max_workers: int = 4,
    ) -> None:
        self.folder = folder or settings.cache_dir() / "images"
        self.fetch = fetch
        self.pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="bing-download")
        self.lock = threading.Lock()
        self.in_flight: Dict[str, Future] = {}

    def path_for(self, url: str) -> Path:
        return self.folder / (hashlib.sha1(url.encode("utf-8")).hexdigest() + ".jpg")

    def cached(self, url: str) -> Optional[Path]:
        path = self.path_for(url)
        if path.exists() and path.stat().st_size > 0:
            try:
                os.utime(path)  # marks it as recently used, for prune()
            except OSError:
                pass
            return path
        return None

    def get(self, url: str) -> "Future[Path]":
        """A future for the image on disk, downloading it if needed."""
        with self.lock:
            future = self.in_flight.get(url)
            if future is not None:
                return future
            path = self.cached(url)
            if path is not None:
                done: "Future[Path]" = Future()
                done.set_result(path)
                return done
            future = self.pool.submit(self._download, url)
            self.in_flight[url] = future
        return future

    def _download(self, url: str) -> Path:
        try:
            data = self.fetch(url)
            if not bing.looks_like_jpeg(data):
                raise OSError(f"Not an image: {url}")
            path = self.path_for(url)
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(f".{threading.get_ident()}.part")
            tmp.write_bytes(data)
            os.replace(tmp, path)
            return path
        finally:
            with self.lock:
                self.in_flight.pop(url, None)

    def prefetch(self, url: str) -> None:
        self.get(url)

    def prune(self, max_age_days: float = MAX_AGE_DAYS, now: Optional[float] = None) -> int:
        """Deletes files not used for `max_age_days`. Returns how many were deleted."""
        cutoff = (now or time.time()) - max_age_days * 86400
        removed = 0
        for path in self.folder.glob("*"):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink()
                    removed += 1
            except OSError:
                pass
        return removed
