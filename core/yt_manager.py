import os
from typing import Dict, List, Optional, Callable
from threading import Event
from PyQt6.QtCore import QThread, pyqtSignal
import yt_dlp
import subprocess
import requests
import json
from core.update import YTDLP_EXE

# Centralized HTTP headers with client identifier
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.5",
    "X-Client-App": "YoutubeConverter",
}
EXTRACTOR_ARGS = {
    "youtube": {"player_client": ["tv"], "skip": ["dash", "hls"]},
    "youtubetab": {"skip": ["webpage"]},
}


def _win_no_window_kwargs():
    if os.name != "nt":
        return {}
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0
    return {"startupinfo": si, "creationflags": subprocess.CREATE_NO_WINDOW}


def build_ydl_opts(
    base_dir: str,
    kind: str,
    fmt: str,
    ffmpeg_location: Optional[str] = None,
    progress_hook: Optional[Callable] = None,
    quality: Optional[str] = None,
    sponsorblock_remove: Optional[List[str]] = None,
    sponsorblock_api: Optional[str] = None,
):
    outtmpl = os.path.join(base_dir, "%(title).200s [%(id)s].%(ext)s")
    postprocessors = []
    q = (quality or "best").lower()

    def _parse_height(qv: str) -> Optional[int]:
        try:
            return int(qv.rstrip("p"))
        except Exception:
            return None

    def _parse_abr(qa: str) -> Optional[int]:
        try:
            return int(qa.rstrip("k"))
        except Exception:
            return None

    if kind == "audio":
        postprocessors = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": fmt,
                "preferredquality": "0",
            }
        ]
        if q != "best":
            abr = _parse_abr(q) or 0
            format_selector = f"bestaudio[abr>={abr}]/bestaudio/best"
        else:
            format_selector = "bestaudio/best"
        merge_out = None
    else:
        height = _parse_height(q) if q != "best" else None
        if fmt.lower() == "mp4":
            if height:
                format_selector = (
                    f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/"
                    f"best[height<={height}][ext=mp4]/best[ext=mp4]/best"
                )
            else:
                format_selector = (
                    "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                )
        else:
            if height:
                format_selector = (
                    f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"
                )
            else:
                format_selector = "bestvideo+bestaudio/best"
        merge_out = fmt

    opts = {
        "outtmpl": outtmpl,
        "format": format_selector,
        "noprogress": True,
        "quiet": True,
        "nocheckcertificate": True,
        "merge_output_format": merge_out,
        "postprocessors": postprocessors,
        "ffmpeg_location": ffmpeg_location or None,
        "noplaylist": False,
        "retries": 10,
        "fragment_retries": 10,
        "socket_timeout": 15,
        "extractor_retries": 2,
        "skip_unavailable_fragments": True,
        "cachedir": False,
        "http_headers": HTTP_HEADERS,
        "extractor_args": {"youtube": {"player_client": ["tv"]}},
    }
    if progress_hook:
        opts["progress_hooks"] = [progress_hook]
    if sponsorblock_remove:
        opts["sponsorblock_remove"] = list(sponsorblock_remove)
    if sponsorblock_api:
        opts["sponsorblock_api"] = sponsorblock_api
    return opts


class InfoFetcher(QThread):
    finished_ok = pyqtSignal(dict)
    finished_fail = pyqtSignal(str)

    def __init__(self, url: str, timeout_sec: int = 60):
        super().__init__()
        self.url = url
        self.timeout_sec = timeout_sec

    def _is_search(self) -> bool:
        return isinstance(self.url, str) and self.url.startswith("ytsearch")

    def _is_playlist(self) -> bool:
        try:
            u = str(self.url)
            return ("list=" in u) or ("playlist?" in u)
        except Exception:
            return False

    def _extract_with_binary(self) -> dict:
        is_search = self._is_search()
        is_playlist = self._is_playlist()
        args = [
            YTDLP_EXE,
            "-J",
            "--ignore-config",
            "--no-warnings",
            "--no-progress",
            "--skip-download",
            "--no-write-comments",
            "--no-write-playlist-metafiles",
            "--no-cache-dir",
            "--extractor-retries",
            "1",
            "--extractor-args",
            "youtube:player_client=tv",
            "--extractor-args",
            "youtube:skip=dash,hls",
            "--extractor-args",
            "youtubetab:skip=webpage",
        ]
        if is_search or is_playlist:
            args.append("--flat-playlist")
        args.append(self.url)

        env = os.environ.copy()
        env["YTDLP_NO_PLUGINS"] = "1"
        kwargs = _win_no_window_kwargs()
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=self.timeout_sec,
            env=env,
            **kwargs,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "yt-dlp binary failed")
        if not proc.stdout:
            raise RuntimeError("Empty response from yt-dlp")
        return json.loads(proc.stdout)

    def _extract_with_python_api(self, use_tv_client: bool = True) -> dict:
        is_search = self._is_search()
        is_playlist = self._is_playlist()
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "noprogress": True,
            "noplaylist": False,
            "extract_flat": True if (is_search or is_playlist) else False,
            "socket_timeout": 15,
            "extractor_retries": 1 if (is_search or is_playlist) else 2,
            "cachedir": False,
            "http_headers": HTTP_HEADERS,
        }
        if use_tv_client:
            ydl_opts["extractor_args"] = EXTRACTOR_ARGS
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(self.url, download=False)

    def run(self):
        try:
            if os.path.exists(YTDLP_EXE):
                info = self._extract_with_binary()
            else:
                info = self._extract_with_python_api(use_tv_client=True)
            self.finished_ok.emit(info)
        except subprocess.TimeoutExpired:
            self.finished_fail.emit("Timed out while fetching info")
        except Exception:
            try:
                info = self._extract_with_python_api(use_tv_client=False)
                self.finished_ok.emit(info)
            except Exception as e2:
                self.finished_fail.emit(str(e2))


class Downloader(QThread):
    itemProgress = pyqtSignal(int, float, float, object)
    itemStatus = pyqtSignal(int, str)
    itemThumb = pyqtSignal(int, bytes)
    finished_all = pyqtSignal()

    def __init__(
        self,
        items: List[dict],
        base_dir: str,
        kind: str,
        fmt: str,
        ffmpeg_location: Optional[str] = None,
        quality: Optional[str] = None,
    ):
        super().__init__()
        self.items = items
        self.base_dir = base_dir
        self.kind = kind
        self.fmt = fmt
        self.ffmpeg_location = ffmpeg_location
        self.quality = quality or "best"
        self._pause_evt = Event()
        self._pause_evt.set()
        self._stop = False
        self._meta_threads: Dict[int, InfoFetcher] = {}

    def pause(self):
        self._pause_evt.clear()
        for idx, _ in enumerate(self.items):
            self.itemStatus.emit(idx, "Paused")

    def resume(self):
        self._pause_evt.set()
        for idx, _ in enumerate(self.items):
            self.itemStatus.emit(idx, "Resuming...")

    def is_paused(self) -> bool:
        return not self._pause_evt.is_set()

    def stop(self):
        self._stop = True

    def _hook_builder(self, idx: int):
        def hook(d):
            self._pause_evt.wait()
            if self._stop:
                raise yt_dlp.utils.DownloadError("Stopped by user")
            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimated") or 0
                downloaded = d.get("downloaded_bytes", 0)
                pct = (downloaded / total * 100.0) if total else 0.0
                speed = d.get("speed") or 0.0
                eta = d.get("eta")
                self.itemProgress.emit(idx, pct, speed, eta)
            elif status == "finished":
                self.itemStatus.emit(idx, "Processing...")
            elif status == "postprocessing":
                self.itemStatus.emit(idx, "Processing...")

        return hook

    def run(self):
        # Throttle initial thumbnail fetching to avoid overwhelming requests
        thumb_queue = []
        for idx, it in enumerate(self.items):
            thumb_url = (
                (it.get("thumbnail") or it.get("thumbnails", [{}])[-1].get("url"))
                if it
                else None
            )
            if thumb_url:
                thumb_queue.append((idx, thumb_url))

        # Process thumbs in batches of 5 to avoid network overload
        for i in range(0, len(thumb_queue), 5):
            batch = thumb_queue[i : i + 5]
            for idx, thumb_url in batch:
                try:
                    r = requests.get(thumb_url, timeout=5)
                    if r.ok:
                        self.itemThumb.emit(idx, r.content)
                except Exception:
                    pass
                # Small delay between requests
                QThread.msleep(50)

        for idx, it in enumerate(self.items):
            if self._stop:
                break
            url = it.get("webpage_url") or it.get("url")
            if not url:
                self.itemStatus.emit(idx, "Invalid URL")
                continue
            self.itemStatus.emit(idx, "Starting...")

            # Per-item overrides with fallback to global
            kind = (it.get("desired_kind") or self.kind or "audio").strip()
            fmt = (
                it.get("desired_format")
                or self.fmt
                or ("mp3" if kind == "audio" else "mp4")
            ).strip()
            qual = (it.get("desired_quality") or self.quality or "best").strip()

            # SponsorBlock (no API key required; use canonical API root)
            sb_enabled = bool(it.get("sb_enabled"))
            sb_cats = list(it.get("sb_categories") or [])
            sb_api = "https://sponsor.ajay.app" if sb_enabled else None

            opts = build_ydl_opts(
                self.base_dir,
                kind,
                fmt,
                self.ffmpeg_location,
                self._hook_builder(idx),
                qual,
                sponsorblock_remove=(sb_cats if sb_enabled and sb_cats else None),
                sponsorblock_api=sb_api,
            )
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])
                if not self._stop:
                    self.itemProgress.emit(idx, 100.0, 0.0, 0)
                    self.itemStatus.emit(idx, "Done")
            except Exception as e:
                if self._stop:
                    self.itemStatus.emit(idx, "Stopped")
                    break
                self.itemStatus.emit(idx, f"Error: {e}")
        self.finished_all.emit()

    def _start_meta_fetch(self, idx: int, url: str):
        if idx in self._meta_threads:
            return
        self.itemStatus.emit(idx, "Fetching metadata...")
        f = InfoFetcher(url)

        def _ok(meta: dict, i=idx):
            try:
                self.items[i] = {**self.items[i], **(meta or {})}
                thumb_url = self.items[i].get("thumbnail") or (
                    self.items[i].get("thumbnails") or [{}]
                )[-1].get("url")
                if thumb_url:
                    try:
                        r = requests.get(thumb_url, timeout=10)
                        if r.ok:
                            self.itemThumb.emit(i, r.content)
                    except Exception:
                        pass
                title = self.items[i].get("title") or "Untitled"
                self.itemStatus.emit(i, f"Metadata ready: {title}")
            finally:
                self._meta_threads.pop(i, None)

        def _fail(err: str, i=idx):
            self.itemStatus.emit(i, f"Metadata fetch failed, will try best available")
            self._meta_threads.pop(i, None)

        f.finished_ok.connect(_ok)
        f.finished_fail.connect(_fail)
        self._meta_threads[idx] = f
        f.start()

    def _needs_metadata(self, it: dict) -> bool:
        """Check if an item needs metadata fetching"""
        if not it:
            return True
        if not it.get("url") and not it.get("webpage_url"):
            return False
        has_core = (
            bool(it.get("id")) or bool(it.get("duration")) or bool(it.get("extractor"))
        )
        has_thumb = bool(it.get("thumbnail")) or bool(it.get("thumbnails"))
        return not (has_core and has_thumb)

    def _needs_metadata(self, it: dict) -> bool:
        if not it:
            return True
        if not it.get("url") and not it.get("webpage_url"):
            return False
        has_core = (
            bool(it.get("id")) or bool(it.get("duration")) or bool(it.get("extractor"))
        )
        has_thumb = bool(it.get("thumbnail")) or bool(it.get("thumbnails"))
        return not (has_core and has_thumb)
