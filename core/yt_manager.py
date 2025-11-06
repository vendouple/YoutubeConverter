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

_VALID_SB_CATEGORIES = {
    "sponsor",
    "selfpromo",
    "interaction",
    "intro",
    "outro",
    "preview",
    "filler",
    "music_offtopic",
    "exclusive_access",
    "chapter",
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
    download_subs: bool = False,
    sub_langs: str = "en",
    auto_subs: bool = False,
    embed_subs: bool = False,
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
        postprocessors.append(
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": fmt,
                "preferredquality": "0",
            }
        )
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

    # Pass SponsorBlock via yt-dlp native options (CLI-equivalent)
    sb_cats_list: List[str] = []
    if sponsorblock_remove:
        try:
            sb_cats_list = [
                str(c).strip() for c in sponsorblock_remove if str(c).strip()
            ]
        except Exception:
            sb_cats_list = list(sponsorblock_remove)
    # sanitize to known categories
    if sb_cats_list:
        sb_cats_list = [c for c in sb_cats_list if c in _VALID_SB_CATEGORIES]

    # Allow SponsorBlock for audio and video in Python fallback
    if sb_cats_list:
        opts["sponsorblock_remove"] = ",".join(sb_cats_list)
        if sponsorblock_api:
            opts["sponsorblock_api"] = sponsorblock_api
    # Debug: SponsorBlock remove set (disabled in production)
    # print(f"SponsorBlock remove set to: {opts['sponsorblock_remove']}")

    # Subtitle configuration
    if download_subs:
        opts["writesubtitles"] = True
        opts["writeautomaticsub"] = auto_subs
        # Parse language codes
        lang_list = [lang.strip() for lang in sub_langs.split(",") if lang.strip()]
        if lang_list:
            opts["subtitleslangs"] = lang_list
        else:
            opts["subtitleslangs"] = ["en"]

        # Embed subtitles for video only
        if kind == "video" and embed_subs:
            # Add subtitle embedding post-processor
            postprocessors.append(
                {"key": "FFmpegEmbedSubtitle", "already_have_subtitle": False}
            )
            opts["postprocessors"] = postprocessors

    return opts


class InfoFetcher(QThread):
    finished_ok = pyqtSignal(dict)
    finished_fail = pyqtSignal(str)

    def __init__(self, url: str, timeout_sec: int = 60, parent=None):
        super().__init__(parent)
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
    # Announce final file for item when available
    itemFileReady = pyqtSignal(int, str)
    retryLimitReached = pyqtSignal(str)

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
        self._dl_filename: Dict[int, str] = {}
        self.max_retries = 3

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
        # Clean up partial download files
        self._cleanup_partial_files()

    def _cleanup_partial_files(self):
        """Remove temporary/partial download files"""
        try:
            if not self.base_dir or not os.path.exists(self.base_dir):
                return

            # Extensions to clean up
            temp_extensions = (".part", ".ytdl", ".temp", ".tmp", ".f*")

            for filename in os.listdir(self.base_dir):
                file_path = os.path.join(self.base_dir, filename)
                # Skip directories
                if os.path.isdir(file_path):
                    continue

                # Check if it's a temp file
                is_temp = any(filename.lower().endswith(ext) for ext in temp_extensions)
                # Also check for f-numbers (fragments)
                is_temp = is_temp or (
                    filename.startswith("f") and filename[1:].split(".")[0].isdigit()
                )

                if is_temp:
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
        except Exception:
            pass

    def _hook_builder(self, idx: int):
        def hook(d):
            self._pause_evt.wait()
            if self._stop:
                raise yt_dlp.utils.DownloadError("Stopped by user")
            status = d.get("status")
            try:
                fn = d.get("filename") or (d.get("info_dict") or {}).get("_filename")
                if fn:
                    self._dl_filename[idx] = fn
            except Exception:
                pass
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
                # Be explicit about which PP is running
                pp = (d.get("postprocessor") or "").lower()
                if "sponsorblock" in pp:
                    self.itemStatus.emit(idx, "Removing segments…")
                elif "extractaudio" in pp or "ffmpegextractaudio" in pp:
                    self.itemStatus.emit(idx, "Converting audio…")
                elif "merge" in pp or "remux" in pp:
                    self.itemStatus.emit(idx, "Merging…")
                else:
                    self.itemStatus.emit(idx, "Processing…")

        return hook

    # Find the final output file after yt-dlp finishes (accounts for postprocessors)
    def _resolve_output_file(self, idx: int, kind: str, fmt: str) -> str | None:
        try:
            p = self._dl_filename.get(idx)
            if p and os.path.exists(p):
                return p
            it = self.items[idx] or {}
            vid = str(it.get("id") or "").strip()
            if not vid:
                return p
            import glob
            import time

            candidates = glob.glob(os.path.join(self.base_dir, f"*[{vid}].*"))
            if not candidates:
                # small delay in case filesystem is slow to update
                QThread.msleep(50)
                candidates = glob.glob(os.path.join(self.base_dir, f"*[{vid}].*"))
            if not candidates:
                return p
            # Prefer target format when possible
            if kind == "audio" and fmt:
                pref = [c for c in candidates if c.lower().endswith(f".{fmt.lower()}")]
                if pref:
                    return max(pref, key=lambda fp: os.path.getmtime(fp))
            if kind == "video" and fmt:
                pref = [c for c in candidates if c.lower().endswith(f".{fmt.lower()}")]
                if pref:
                    return max(pref, key=lambda fp: os.path.getmtime(fp))
            return max(candidates, key=lambda fp: os.path.getmtime(fp))
        except Exception:
            return self._dl_filename.get(idx)

    def _existing_output_file(self, idx: int, kind: str, fmt: str) -> str | None:
        try:
            it = self.items[idx] or {}
            vid = str(it.get("id") or "").strip()
            if not vid:
                return None
            import glob
            import time

            candidates = glob.glob(os.path.join(self.base_dir, f"*[{vid}].*"))
            if not candidates:
                return None
            valid = [
                c
                for c in candidates
                if not c.lower().endswith((".part", ".ytdl", ".temp", ".tmp"))
            ]
            if not valid:
                return None
            if kind == "audio" and fmt:
                pref = [c for c in valid if c.lower().endswith(f".{fmt.lower()}")]
                if pref:
                    return max(pref, key=lambda fp: os.path.getmtime(fp))
            if kind == "video" and fmt:
                pref = [c for c in valid if c.lower().endswith(f".{fmt.lower()}")]
                if pref:
                    return max(pref, key=lambda fp: os.path.getmtime(fp))
            return max(valid, key=lambda fp: os.path.getmtime(fp))
        except Exception:
            return None

    # Build CLI args for yt-dlp binary to mirror Python options
    def _build_cli_args(
        self,
        url: str,
        kind: str,
        fmt: str,
        quality: str,
        base_dir: str,
        ffmpeg_location: Optional[str],
        sb_enabled: bool,
        sb_cats: List[str],
        download_subs: bool = False,
        sub_langs: str = "en",
        auto_subs: bool = False,
        embed_subs: bool = False,
    ) -> List[str]:
        outtmpl = os.path.join(base_dir, "%(title).200s [%(id)s].%(ext)s")
        args = [
            YTDLP_EXE,
            "--ignore-config",
            "--no-warnings",
            "--newline",
            "--no-cache-dir",
            "-o",
            outtmpl,
        ]

        # Format selection based on kind/quality
        q = (quality or "best").lower()
        if kind == "audio":
            # Prefer higher ABR if specified
            if q != "best":
                try:
                    abr = int(q.rstrip("k"))
                except Exception:
                    abr = 0
                fsel = f"bestaudio[abr>={abr}]/bestaudio/best"
            else:
                fsel = "bestaudio/best"
            args += ["-f", fsel, "-x", "--audio-format", fmt]
        else:
            # video
            def _video_selector(height: Optional[int], ext: Optional[str]) -> str:
                if ext == "mp4":
                    if height:
                        return (
                            f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/"
                            f"best[height<={height}][ext=mp4]/best[ext=mp4]/best"
                        )
                    return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                else:
                    if height:
                        return (
                            f"bestvideo[height<={height}]+bestaudio/"
                            f"best[height<={height}]/best"
                        )
                    return "bestvideo+bestaudio/best"

            height = (
                None
                if q == "best"
                else (
                    int(q.rstrip("p")) if q.endswith("p") and q[:-1].isdigit() else None
                )
            )
            fsel = _video_selector(height, fmt.lower())
            args += ["-f", fsel, "--merge-output-format", fmt]

        # SponsorBlock for both audio and video; also mark chapters to ensure cutting works
        if sb_enabled:
            cats = [c for c in (sb_cats or []) if c in _VALID_SB_CATEGORIES]
            args += ["--sponsorblock-mark", "all"]
            if cats:
                args += ["--sponsorblock-remove", ",".join(cats)]

        # FFmpeg location (if provided)
        if ffmpeg_location:
            args += ["--ffmpeg-location", ffmpeg_location]

        # Subtitle configuration
        if download_subs:
            args.append("--write-subs")
            if auto_subs:
                args.append("--write-auto-subs")
            # Language codes
            lang_list = [lang.strip() for lang in sub_langs.split(",") if lang.strip()]
            if lang_list:
                args += ["--sub-langs", ",".join(lang_list)]
            else:
                args += ["--sub-langs", "en"]

            # Embed subtitles for video only
            if kind == "video" and embed_subs:
                args.append("--embed-subs")

        # Progress template
        args += [
            "--progress-template",
            "download:DL|%(progress.downloaded_bytes)s|%(progress.total_bytes)s|%(progress.speed)s|%(progress.eta)s",
        ]

        args.append(url)
        return args

    # Parse progress lines from yt-dlp stdout
    def _parse_progress_line(self, line: str):
        # Expected: "DL|downloaded|total|speed|eta"
        try:
            if not line.startswith("DL|"):
                return None
            parts = line.strip().split("|")
            if len(parts) != 5:
                return None
            downloaded = float(parts[1]) if parts[1] not in ("", "None") else 0.0
            total = float(parts[2]) if parts[2] not in ("", "None") else 0.0
            speed = float(parts[3]) if parts[3] not in ("", "None") else 0.0
            eta = float(parts[4]) if parts[4] not in ("", "None") else 0.0
            pct = (downloaded / total * 100.0) if total > 0 else 0.0
            return pct, speed, int(eta)
        except Exception:
            return None

    # Download using the yt-dlp binary (preferred for SponsorBlock correctness)
    def _download_with_binary(
        self,
        idx: int,
        url: str,
        kind: str,
        fmt: str,
        qual: str,
        sb_enabled: bool,
        sb_cats: List[str],
        download_subs: bool = False,
        sub_langs: str = "en",
        auto_subs: bool = False,
        embed_subs: bool = False,
    ) -> tuple[bool, Optional[str]]:
        try:
            args = self._build_cli_args(
                url,
                kind,
                fmt,
                qual,
                self.base_dir,
                self.ffmpeg_location,
                sb_enabled,
                sb_cats,
                download_subs,
                sub_langs,
                auto_subs,
                embed_subs,
            )
            kwargs = _win_no_window_kwargs()
            # Disable third-party plugins for stability
            env = os.environ.copy()
            env["YTDLP_NO_PLUGINS"] = "1"
            proc = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env,
                **kwargs,
            )
            self.itemStatus.emit(idx, "Downloading...")
            for line in proc.stdout or []:
                # Never block reading stdout; just suppress UI updates while paused
                paused = not self._pause_evt.is_set()
                if self._stop:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                    self.itemStatus.emit(idx, "Stopped")
                    return False, "Stopped"
                if not line:
                    continue

                p = self._parse_progress_line(line)
                if p and not paused:
                    pct, speed, eta = p
                    self.itemProgress.emit(idx, pct, speed, eta)
                    continue

                s = line.strip().lower()
                if "sponsorblock" in s and not paused:
                    self.itemStatus.emit(idx, "Removing segments…")
                elif "extractaudio" in s and not paused:
                    self.itemStatus.emit(idx, "Converting audio…")
                elif (
                    "[merger]" in s or "merging formats" in s or "remux" in s
                ) and not paused:
                    self.itemStatus.emit(idx, "Merging…")
                elif "post-processing" in s and not paused:
                    self.itemStatus.emit(idx, "Processing…")

            code = proc.wait()
            if code != 0:
                err = f"yt-dlp failed (code {code})"
                self.itemStatus.emit(idx, f"Error: {err}")
                return False, err

            if not self._stop:
                self.itemProgress.emit(idx, 100.0, 0.0, 0)
                self.itemStatus.emit(idx, "Done")
            return True, None
        except Exception as e:
            self.itemStatus.emit(idx, f"Error: {e}")
            return False, str(e)

    def _attempt_download(
        self,
        idx: int,
        url: str,
        kind: str,
        fmt: str,
        qual: str,
        sb_enabled: bool,
        sb_cats: List[str],
        download_subs: bool = False,
        sub_langs: str = "en",
        auto_subs: bool = False,
        embed_subs: bool = False,
    ) -> tuple[bool, Optional[str]]:
        last_error: Optional[str] = None
        binary_exists = os.path.exists(YTDLP_EXE)

        if binary_exists:
            ok, err = self._download_with_binary(
                idx,
                url,
                kind,
                fmt,
                qual,
                sb_enabled,
                sb_cats,
                download_subs,
                sub_langs,
                auto_subs,
                embed_subs,
            )
            if ok:
                try:
                    fp = self._resolve_output_file(idx, kind, fmt)
                    if fp:
                        self.itemFileReady.emit(idx, fp)
                except Exception:
                    pass
                return True, None
            last_error = err
            if self._stop:
                return False, err or "Stopped"

        opts = build_ydl_opts(
            self.base_dir,
            kind,
            fmt,
            self.ffmpeg_location,
            self._hook_builder(idx),
            qual,
            sponsorblock_remove=(sb_cats if sb_enabled and sb_cats else None),
            sponsorblock_api=("https://sponsor.ajay.app" if sb_enabled else None),
            download_subs=download_subs,
            sub_langs=sub_langs,
            auto_subs=auto_subs,
            embed_subs=embed_subs,
        )
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            if not self._stop:
                self.itemProgress.emit(idx, 100.0, 0.0, 0)
                self.itemStatus.emit(idx, "Done")
                try:
                    fp = self._resolve_output_file(idx, kind, fmt)
                    if fp:
                        self.itemFileReady.emit(idx, fp)
                except Exception:
                    pass
            return True, None
        except Exception as e:
            err = str(e) or last_error or "Unknown error"
            if self._stop:
                self.itemStatus.emit(idx, "Stopped")
                return False, "Stopped"
            self.itemStatus.emit(idx, f"Error: {err}")
            return False, err

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
            kind = (it.get("desired_kind") or self.kind or "audio").strip()
            fmt = (
                it.get("desired_format")
                or self.fmt
                or ("mp3" if kind == "audio" else "mp4")
            ).strip()
            qual = (it.get("desired_quality") or self.quality or "best").strip()

            # SponsorBlock settings
            sb_enabled = bool(it.get("sb_enabled"))
            sb_cats = [
                c for c in (it.get("sb_categories") or []) if c in _VALID_SB_CATEGORIES
            ]
            # Debug: printing formatted size (disabled in production)
            # print(f"Item {idx} SponsorBlock: enabled={sb_enabled}, categories={sb_cats}")

            # Subtitle settings
            download_subs = bool(it.get("download_subs", False))
            sub_langs = str(it.get("sub_langs", "en"))
            auto_subs = bool(it.get("auto_subs", False))
            embed_subs = bool(it.get("embed_subs", False))

            binary_exists = os.path.exists(YTDLP_EXE)
            if not binary_exists:
                # Debug: printing percent (disabled in production)
                # print(f"Warning: yt-dlp binary not found at {YTDLP_EXE}, falling back to Python API")
                pass

            last_error: Optional[str] = None
            success = False
            for attempt in range(self.max_retries + 1):
                if self._stop:
                    break
                if attempt == 0:
                    self.itemStatus.emit(idx, "Starting...")
                else:
                    self.itemStatus.emit(
                        idx, f"Retrying ({attempt}/{self.max_retries})…"
                    )
                    QThread.msleep(350)
                success, err = self._attempt_download(
                    idx,
                    url,
                    kind,
                    fmt,
                    qual,
                    sb_enabled,
                    sb_cats,
                    download_subs,
                    sub_langs,
                    auto_subs,
                    embed_subs,
                )
                if success:
                    break
                last_error = err

            if self._stop:
                break

            if not success:
                if self._stop:
                    break
                err_text = last_error or "Download failed"
                self.itemStatus.emit(idx, f"Failed: {err_text}")
                try:
                    title = (it or {}).get("title") or "This download"
                    self.retryLimitReached.emit(
                        f"{title} failed after {self.max_retries} retries.\nError: {err_text}"
                    )
                except Exception:
                    pass
        if not self._stop:
            self.finished_all.emit()
