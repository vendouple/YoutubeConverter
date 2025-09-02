import re
from typing import Dict, List, Tuple
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QThread
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QTabWidget,
    QMessageBox,
    QCheckBox,
    QProgressBar,
    QFrame,  # NEW
)
from PyQt6.QtGui import QIcon, QPixmap, QColor, QImage
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode
from collections import deque

from core.settings import AppSettings
from core.yt_manager import InfoFetcher

YOUTUBE_URL_RE = re.compile(r"https?://[^\s]+")
VIDEO_HOSTS = ("www.youtube.com", "m.youtube.com", "youtube.com", "youtu.be")
ICON_PIXMAP_ROLE = int(Qt.ItemDataRole.UserRole) + 1  # store original pixmap


class Step1LinkWidget(QWidget):
    # Emits full info dict for a single immediate advance (when not multiple) for backward compat
    urlDetected = pyqtSignal(dict)
    requestAdvance = pyqtSignal(dict)
    # New: emit full list of selected info dicts
    selectionConfirmed = pyqtSignal(list)

    # Small worker to fetch a single thumbnail without blocking UI
    class _ThumbWorker(QThread):
        # CHANGED: emit bytes instead of QPixmap to keep GUI ops in UI thread
        done = pyqtSignal(int, bytes, str)  # row, image_bytes, url

        def __init__(self, row: int, url: str, parent=None):
            super().__init__(parent)
            self.row = row
            self.url = url

        def run(self):
            try:
                from urllib.request import urlopen
                import time

                data = None
                for _ in range(3):  # retry up to 3 times
                    try:
                        data = urlopen(self.url, timeout=5).read()
                        if data:
                            break
                    except Exception:
                        pass
                    time.sleep(0.2)
                if data:
                    self.done.emit(self.row, data, self.url)
            except Exception:
                pass

    def __init__(self, settings: AppSettings):
        super().__init__()
        self.settings = settings
        self.fetcher = None
        self.selected: List[Dict] = []
        self._bg_fetchers = {}
        self._active_req_id = 0
        self._thumb_threads: List[Step1LinkWidget._ThumbWorker] = []
        self._thumb_max = 3
        self._thumb_queue = deque()
        self._thumb_active: set = set()
        self._thumb_cache = {}
        self._thumb_pending: set = set()

        self._queue = deque()
        self._queued_search: str | None = None

        self._confirm_inflight = False
        self._confirm_fetchers: dict[int, InfoFetcher] = {}
        self._confirm_total = 0
        self._confirm_done = 0

        # Setup UI
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        # Top row: input + multi toggle + Paste
        top = QHBoxLayout()
        self.txt = QLineEdit()
        self.txt.setPlaceholderText(
            "Paste a YouTube URL or type to search, then press Enter…"
        )
        # Intercept Ctrl+V to use the same fast-paste logic
        self.txt.installEventFilter(self)
        self.chk_multi = QCheckBox("Add multiple")
        self.chk_multi.setObjectName("ButtonLike")
        self.chk_multi.setChecked(False)
        # prevent dotted focus on key navigation
        self.chk_multi.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_paste = QPushButton("Paste")
        top.addWidget(self.txt, 1)
        top.addWidget(self.chk_multi)
        top.addWidget(self.btn_paste)
        lay.addLayout(top)

        # NEW: Thin YouTube-like loading bar below the top row
        self.loading_bar = QProgressBar()
        self.loading_bar.setTextVisible(False)
        self.loading_bar.setFixedHeight(3)
        self.loading_bar.setRange(0, 0)
        self.loading_bar.setVisible(False)
        self.loading_bar.setStyleSheet(
            f"QProgressBar{{border:0;background:transparent;}}"
            f"QProgressBar::chunk{{background-color:{self.settings.ui.accent_color_hex};}}"
        )
        lay.addWidget(self.loading_bar)

        # Status row (keep only the label; remove spinner)
        status_row = QHBoxLayout()
        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        status_row.addWidget(self.lbl_status, 1)
        lay.addLayout(status_row)

        # Tabs
        self.tabs = QTabWidget()
        self.tab_search = QWidget()
        self.tab_selected = QWidget()
        self.tab_playlist = QWidget()
        self.tabs.addTab(self.tab_search, "Searched Videos")
        self.tabs.addTab(self.tab_selected, "Selected Videos")
        self.tabs.addTab(self.tab_playlist, "Playlist Videos")

        lay.addWidget(self.tabs, 1)
        self.idx_search, self.idx_selected, self.idx_playlist = 0, 1, 2
        self.tabs.setTabVisible(self.idx_selected, False)
        self.tabs.setTabVisible(self.idx_playlist, False)

        ts_lay = QVBoxLayout(self.tab_search)
        ts_lay.setContentsMargins(0, 0, 0, 0)
        self.results = QListWidget()
        self.results.setIconSize(QSize(96, 54))
        self.results.setFrameShape(QFrame.Shape.NoFrame)
        self.results.setSpacing(3)
        self.results.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        ts_lay.addWidget(self.results, 1)

        # Selected tab content
        sel_lay = QVBoxLayout(self.tab_selected)
        sel_lay.setContentsMargins(0, 0, 0, 0)
        self.selected_list = QListWidget()
        self.selected_list.setIconSize(QSize(96, 54))
        self.selected_list.setFrameShape(QFrame.Shape.NoFrame)
        self.selected_list.setSpacing(3)
        self.selected_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        sel_lay.addWidget(self.selected_list, 1)

        # Playlist tab content
        pl_lay = QVBoxLayout(self.tab_playlist)
        pl_lay.setContentsMargins(0, 0, 0, 0)
        self.chk_pl_select_all = QCheckBox("Select all")
        self.chk_pl_select_all.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.chk_pl_select_all.toggled.connect(self._on_pl_select_all_toggled)
        pl_lay.addWidget(self.chk_pl_select_all, 0, Qt.AlignmentFlag.AlignLeft)

        self.playlist_list = QListWidget()
        self.playlist_list.setIconSize(QSize(96, 54))
        self.playlist_list.setFrameShape(QFrame.Shape.NoFrame)
        self.playlist_list.setSpacing(3)
        self.playlist_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        pl_lay.addWidget(self.playlist_list, 1)
        # NEW: trigger lazy thumb loading on viewport resize/show
        try:
            self.playlist_list.viewport().installEventFilter(self)
        except Exception:
            pass

        # Bottom row with Next button
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        self.btn_next = QPushButton("Next")
        self.btn_next.setVisible(False)
        bottom.addWidget(self.btn_next)
        lay.addLayout(bottom)

        # Connect signals
        self.btn_paste.clicked.connect(self._paste)
        self.txt.returnPressed.connect(self._enter_pressed)
        self.txt.textChanged.connect(self._on_text_changed)
        self.chk_multi.toggled.connect(self._on_multi_toggled)
        self.results.itemClicked.connect(self._toggle_from_results)
        self.selected_list.itemClicked.connect(self._remove_from_selected_prompt)
        self.playlist_list.itemClicked.connect(self._toggle_from_playlist)
        self.btn_next.clicked.connect(self._confirm_selection)

        # Debounced search timer
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._do_debounced_search)

        # Ensure the Select-all toggle visibility matches multi-select state
        self.chk_pl_select_all.setVisible(self.chk_multi.isChecked())

    # ----- UI Helpers -----

    def _set_busy(self, on: bool):
        # Show/hide thin loading bar
        if on:
            self.loading_bar.setVisible(True)
            self.loading_bar.setRange(0, 0)
        else:
            self.loading_bar.setVisible(False)
            self.loading_bar.setRange(0, 1)
            self.loading_bar.setValue(0)

    def _refresh_selected_list(self):
        self.selected_list.clear()
        for it in self.selected:
            title = it.get("title") or "Untitled"
            lw = QListWidgetItem(title)
            # Async thumb fetch (bounded)
            url = (it or {}).get("webpage_url") or (it or {}).get("url")
            thumb = (
                (it.get("thumbnail") or (it.get("thumbnails") or [{}])[-1].get("url"))
                if isinstance(it, dict)
                else None
            )
            if thumb:
                self._enqueue_thumb(
                    thumb,
                    lambda px, _, vurl=url: self._set_selected_icon_for_url(vurl, px),
                )
            lw.setData(Qt.ItemDataRole.UserRole, it)
            self.selected_list.addItem(lw)
        self.tabs.setTabVisible(self.idx_selected, self.selected_list.count() > 0)

    # ----- Event Handlers -----

    def eventFilter(self, obj, event):
        if obj is self.txt:
            try:
                from PyQt6.QtCore import QEvent
                from PyQt6.QtGui import QKeySequence
            except Exception:
                return super().eventFilter(obj, event)
            if event.type() == QEvent.Type.KeyPress:
                if event.matches(QKeySequence.StandardKey.Paste):
                    self._handle_paste_from_clipboard()
                    return True
        else:
            # NEW: react to playlist viewport resize/show to (re)load visible thumbs
            try:
                from PyQt6.QtCore import QEvent

                if obj is self.playlist_list.viewport():
                    if event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
                        QTimer.singleShot(0, self._load_visible_playlist_thumbnails)
            except Exception:
                pass
        return super().eventFilter(obj, event)

    def _paste(self):
        self._handle_paste_from_clipboard()

    def _handle_paste_from_clipboard(self):
        from PyQt6.QtWidgets import QApplication

        txt = (QApplication.clipboard().text() or "").strip()
        if not txt:
            return
        self.txt.setText(txt)
        self._process_text(txt, trigger="paste")

    def _on_text_changed(self, _: str):
        q = self.txt.text().strip()
        if not q:
            if hasattr(self, "search_timer"):
                self.search_timer.stop()
            self.lbl_status.setText("")
            self._set_busy(False)
            return
        self._process_text(q, trigger="typing")

    def _do_debounced_search(self):
        q = self.txt.text().strip()
        if not q or YOUTUBE_URL_RE.match(q):
            return
        self._start_fetch(f"ytsearch20:{q}")

    def _enter_pressed(self):
        q = self.txt.text().strip()
        if not q:
            return
        self._process_text(q, trigger="enter")

    # ----- URL Processing -----

    def _process_text(self, text: str, trigger: str = "typing"):
        text = (text or "").strip()
        if not text:
            return
        is_url = bool(YOUTUBE_URL_RE.match(text))
        if is_url:
            kind, norm = self._classify_url(text)
            self._handle_url(kind, norm)
            return

        auto = bool(getattr(self.settings.ui, "auto_search_text", True))  # CHANGED
        if not auto:
            if trigger in ("enter", "paste"):  # manual only
                self._start_fetch(f"ytsearch20:{text}")
            else:
                if hasattr(self, "search_timer"):
                    self.search_timer.stop()
            return

        # Auto search with debounce (single control)
        secs = max(0, int(getattr(self.settings.ui, "search_debounce_seconds", 3)))
        if not hasattr(self, "search_timer"):
            self.search_timer = QTimer(self)
            self.search_timer.setSingleShot(True)
            self.search_timer.timeout.connect(self._do_debounced_search)
        self.search_timer.start(secs * 1000)

    def _handle_url(self, kind: str, norm: str):
        if kind == "radio":
            self.lbl_status.setText("Radio playlists are not supported.")
            return
        if kind == "playlist":
            if not self.chk_multi.isChecked():
                self.chk_multi.setChecked(True)
            self._start_fetch(norm)
            return
        self._start_fetch(norm)

    def _classify_url(self, url: str) -> Tuple[str, str]:
        """
        Returns (kind, normalized_url)
        kind: 'single' | 'playlist' | 'radio' | 'unknown'
        """
        try:
            u = urlparse(url)
            if u.netloc not in VIDEO_HOSTS:
                return "unknown", url
            # youtu.be short form
            if u.netloc == "youtu.be":
                vid = u.path.strip("/")
                q = parse_qs(u.query or "")
                lst = (q.get("list") or [""])[0]
                if lst.startswith("RD") or q.get("start_radio", ["0"])[0] == "1":
                    return "radio", url
                if lst:
                    # normalize to watch with v+list
                    qs = urlencode({"v": vid, "list": lst}, doseq=True)
                    return "playlist", urlunparse(
                        ("https", "www.youtube.com", "/watch", "", qs, "")
                    )
                # single
                qs = urlencode({"v": vid}, doseq=True)
                return "single", urlunparse(
                    ("https", "www.youtube.com", "/watch", "", qs, "")
                )
            # shorts
            if u.path.startswith("/shorts/"):
                vid = u.path.split("/")[-1]
                qs = urlencode({"v": vid}, doseq=True)
                return "single", urlunparse(
                    (u.scheme or "https", "www.youtube.com", "/watch", "", qs, "")
                )
            # standard watch
            if u.path == "/watch":
                q = parse_qs(u.query or "")
                lst = (q.get("list") or [""])[0]
                if lst:
                    if lst.startswith("RD") or (q.get("start_radio", ["0"])[0] == "1"):
                        return "radio", url
                    # keep only v+list for playlist fetch
                    keep = {}
                    if "v" in q:
                        keep["v"] = q["v"]
                    keep["list"] = [lst]
                    qs = urlencode(keep, doseq=True)
                    return "playlist", urlunparse(
                        (u.scheme, u.netloc, u.path, u.params, qs, u.fragment)
                    )
                # single: keep v(+t)
                keep = {}
                if "v" in q:
                    keep["v"] = q["v"]
                if "t" in q:
                    keep["t"] = q["t"]
                qs = urlencode(keep, doseq=True)
                return "single", urlunparse(
                    (u.scheme, u.netloc, u.path, u.params, qs, u.fragment)
                )
        except Exception:
            return "unknown", url
        return "unknown", url

    # ----- Fetch and Queue Management -----

    def _start_fetch(self, url: str):
        if self.fetcher and self.fetcher.isRunning():
            # If a fetch is in progress, handle queuing
            if url.startswith("ytsearch"):
                self._queued_search = url  # Only keep latest search
                self.lbl_status.setText("Queued latest search...")
            else:
                self._queue.append(url)  # Queue non-search URLs in order
                self.lbl_status.setText("Queued request...")
            return

        self.lbl_status.setText(
            "Searching..." if url.startswith("ytsearch") else "Fetching info..."
        )
        self._set_busy(True)
        self.fetcher = InfoFetcher(url)
        req_id = self._active_req_id = self._active_req_id + 1

        self.fetcher.finished_ok.connect(
            lambda info, rid=req_id: self._on_fetch_ok(rid, info)
        )
        self.fetcher.finished_fail.connect(
            lambda err, rid=req_id: self._on_fetch_fail(rid, err)
        )
        self.fetcher.start()

    def _on_fetch_ok(self, rid: int, info: Dict):
        # Ignore stale responses
        if rid != self._active_req_id:
            return
        self.fetcher = None
        self._set_busy(False)

        # Clear input if requested (use unified setting only)
        try:
            if bool(getattr(self.settings.ui, "auto_clear_on_success", False)):
                self.txt.clear()
        except Exception:
            pass
        self.lbl_status.setText("")

        # Handle search results
        if (
            info.get("_type") == "playlist"
            and info.get("extractor_key") == "YoutubeSearch"
        ):
            self.results.clear()
            entries = info.get("entries") or []
            for i, e in enumerate(entries):
                title = e.get("title") or "Unknown title"
                url = e.get("webpage_url") or e.get("url") or ""
                thumb = e.get("thumbnail") or (e.get("thumbnails") or [{}])[-1].get(
                    "url"
                )
                it = QListWidgetItem(title)
                it.setData(
                    Qt.ItemDataRole.UserRole,
                    {
                        "title": title,
                        "webpage_url": url,
                        "url": url,
                        "thumbnail": e.get("thumbnail"),
                        "thumbnails": e.get("thumbnails"),
                    },
                )
                self.results.addItem(it)
                # Enqueue thumbnail download with rate limiting
                if thumb:
                    row = i
                    self._enqueue_thumb(
                        thumb,
                        lambda px, expected=thumb, r=row: self._set_result_icon_if_match(
                            r, px, expected
                        ),
                    )
            self.tabs.setCurrentIndex(self.idx_search)
            self._run_pending_if_any()
            return

        # Handle real playlist - use smaller chunks and defer thumbnail loading
        if info.get("_type") == "playlist" and info.get("entries"):
            entries = list(info.get("entries") or [])
            total = len(entries)
            self.lbl_status.setText(f"Loaded playlist with {total} videos.")
            self.playlist_list.clear()
            self.chk_pl_select_all.blockSignals(True)
            self.chk_pl_select_all.setChecked(False)
            self.chk_pl_select_all.blockSignals(False)

            # Use smaller chunks (25 instead of 50) for smoother UI
            chunk = 25
            self.playlist_list.setUpdatesEnabled(False)

            # Chunk processing function
            def _add_chunk(start: int = 0):
                end = min(start + chunk, total)
                for j in range(start, end):
                    if j >= len(entries):
                        break
                    e = entries[j] or {}
                    title = e.get("title") or "Untitled"
                    item = QListWidgetItem(title)
                    item.setData(Qt.ItemDataRole.UserRole, e)
                    self._style_playlist_item(item, self._is_selected(e))
                    self.playlist_list.addItem(item)

                # Update status progressively
                self.lbl_status.setText(f"Loaded {end}/{total} videos...")

                # Process next chunk with delay to allow UI updates
                if end < total:
                    QTimer.singleShot(10, lambda s=end: _add_chunk(s))
                else:
                    self.playlist_list.setUpdatesEnabled(True)
                    self.tabs.setTabVisible(self.idx_playlist, True)
                    self.tabs.setCurrentIndex(self.idx_playlist)
                    self.chk_pl_select_all.setVisible(self.chk_multi.isChecked())
                    self.lbl_status.setText(f"Loaded {total} videos")

                    # Only NOW set up scroll event handler for lazy loading thumbnails
                    QTimer.singleShot(100, self._load_visible_playlist_thumbnails)

                    # Connect to scrolling event for lazy loading
                    self.playlist_list.verticalScrollBar().valueChanged.connect(
                        self._load_visible_playlist_thumbnails
                    )

                    # Free memory
                    try:
                        import gc

                        gc.collect()
                    except:
                        pass

            # Start the chunked loading process
            _add_chunk(0)
            self._run_pending_if_any()
            return

        # Handle single video
        if not self.chk_multi.isChecked():
            self.urlDetected.emit(info)
            self.requestAdvance.emit(
                {"url": self.txt.text().strip(), "info": info, "is_playlist": False}
            )
        else:
            self._upsert_selected(info)
        self._run_pending_if_any()

    def _on_fetch_fail(self, rid: int, err: str):
        # Ignore stale failures
        if rid != self._active_req_id:
            return
        self.fetcher = None
        self._set_busy(False)
        self.lbl_status.setText(f"Error: {err}")
        try:
            QMessageBox.warning(self, "Fetch failed", str(err))
        except Exception:
            pass
        self._run_pending_if_any()

    def _run_pending_if_any(self):
        # Process pending requests - newest search first, then FIFO queue
        next_url = None
        if self._queued_search:
            next_url = self._queued_search
            self._queued_search = None
        elif self._queue:
            next_url = self._queue.popleft()
        if next_url:
            self._start_fetch(next_url)

    def _cancel_fetch(self):
        # Safer handling of threads
        if self.fetcher and self.fetcher.isRunning():
            # Rather than terminate, just let it finish but ignore results
            try:
                self.fetcher.finished_ok.disconnect()
                self.fetcher.finished_fail.disconnect()
            except:
                pass
            self.fetcher = None

        # Clear thumb queue and pending; let active workers finish quietly
        self._thumb_queue.clear()
        self._thumb_pending.clear()

        # Empty cache if it's getting too large
        if len(self._thumb_cache) > 200:
            self._thumb_cache.clear()

        # Free memory
        try:
            import gc

            gc.collect()
        except:
            pass

    # ----- Selection Management -----

    def _is_selected(self, info: Dict) -> bool:
        url = (info or {}).get("webpage_url") or (info or {}).get("url")
        if not url:
            return False
        return any(
            (it.get("webpage_url") or it.get("url")) == url for it in self.selected
        )

    def _upsert_selected(self, info: Dict):
        if not isinstance(info, dict):
            return
        url = info.get("webpage_url") or info.get("url")
        if not url:
            return
        idx = next(
            (
                i
                for i, it in enumerate(self.selected)
                if (it.get("webpage_url") or it.get("url")) == url
            ),
            -1,
        )
        if idx >= 0:
            self.selected[idx] = {**self.selected[idx], **info}
        else:
            self.selected.append(info)
        self._refresh_selected_list()

    # --- UI lock helper during confirm ---
    def _set_ui_enabled(self, enabled: bool):
        try:
            self.txt.setEnabled(enabled)
            self.btn_paste.setEnabled(enabled)
            self.chk_multi.setEnabled(enabled)
            self.tabs.setEnabled(enabled)
            self.results.setEnabled(enabled)
            self.selected_list.setEnabled(enabled)
            self.playlist_list.setEnabled(enabled)
            self.btn_next.setEnabled(enabled and self.chk_multi.isChecked())
        except Exception:
            pass

    # --- Confirm fetch all (parallel, URL-safe) ---
    def _fetch_all_selected_then_emit(self):
        # Collect URLs needing metadata (do not trust indices that can shift)
        def _has_formats(it: Dict) -> bool:
            fmts = it.get("formats")
            return bool(fmts and isinstance(fmts, list) and len(fmts) > 0)

        urls = []
        for it in list(self.selected):
            if not _has_formats(it):
                u = (it or {}).get("webpage_url") or (it or {}).get("url")
                if u:
                    urls.append(u)

        if not urls:
            self.selectionConfirmed.emit(list(self.selected))
            return
        if getattr(self, "_confirm_inflight", False):
            return

        self._confirm_inflight = True
        self._confirm_total = len(urls)
        self._confirm_done = 0
        self._confirm_fetchers = {}

        # Disable UI and show determinate progress
        self._set_ui_enabled(False)
        self.btn_next.setEnabled(False)
        self.loading_bar.setVisible(True)
        self.loading_bar.setRange(0, self._confirm_total)
        self.loading_bar.setValue(0)
        self.lbl_status.setText(
            f"Fetching metadata for {self._confirm_total} item(s)..."
        )
        self.lbl_status.setText(f"Fetching metadata (0/{self._confirm_total})...")

        def _on_done_one():
            self._confirm_done += 1
            try:
                self.loading_bar.setValue(self._confirm_done)
                # Update "(n/total)" text
                self.lbl_status.setText(
                    f"Fetching metadata ({self._confirm_done}/{self._confirm_total})..."
                )
            except Exception:
                pass
            if self._confirm_done >= self._confirm_total:
                # Finalize
                self._confirm_inflight = False
                self._confirm_fetchers.clear()
                self.lbl_status.setText("")
                # Hide bar and re-enable UI
                self.loading_bar.setVisible(False)
                self.loading_bar.setRange(0, 0)
                self._set_ui_enabled(True)
                self.btn_next.setEnabled(True)
                self.selectionConfirmed.emit(list(self.selected))

        # Launch parallel fetchers keyed by URL to avoid index drift
        for u in urls:
            f = InfoFetcher(u)

            def _ok(meta: dict, url=u):
                try:
                    if isinstance(meta, dict):
                        # merge into the matching selected item by URL if still present
                        for i, s in enumerate(list(self.selected)):
                            surl = (s or {}).get("webpage_url") or (s or {}).get("url")
                            if surl == url:
                                self.selected[i] = {**s, **meta}
                                break
                        self._refresh_selected_list()
                finally:
                    self._confirm_fetchers.pop(url, None)
                    _on_done_one()

            def _fail(_: str, url=u):
                self._confirm_fetchers.pop(url, None)
                _on_done_one()

            f.finished_ok.connect(_ok)
            f.finished_fail.connect(_fail)
            self._confirm_fetchers[u] = f
            f.start()

    # --- Multi toggle: also hide/show playlist "Select all" ---
    def _on_multi_toggled(self, checked: bool):
        self.btn_next.setVisible(checked)
        self.chk_pl_select_all.setVisible(checked)  # NEW
        if checked:
            return
        if self.selected:
            res = QMessageBox.question(
                self,
                "Clear selected",
                "Are you sure you want to clear videos?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if res == QMessageBox.StandardButton.Yes:
                self.selected.clear()
                self._refresh_selected_list()
                self.tabs.setTabVisible(self.idx_selected, False)
                # Reset playlist item styling
                for i in range(self.playlist_list.count()):
                    it = self.playlist_list.item(i)
                    self._style_playlist_item(it, False)
                self.lbl_status.setText("")
            else:
                # Revert to ON
                self.chk_multi.blockSignals(True)
                self.chk_multi.setChecked(True)
                self.chk_multi.blockSignals(False)
        # No selection to clear; still ensure status/UI consistent
        self.lbl_status.setText("")

    # Toggle a playlist entry in/out of selection
    def _toggle_from_playlist(self, item: QListWidgetItem):
        info = item.data(Qt.ItemDataRole.UserRole) or {}
        url = info.get("webpage_url") or info.get("url")
        if not url:
            return

        if self._is_selected(info):
            title = info.get("title") or "Untitled"
            if (
                QMessageBox.question(
                    self, "Remove video", f"Remove '{title}' from selected?"
                )
                == QMessageBox.StandardButton.Yes
            ):
                self.selected = [
                    it
                    for it in self.selected
                    if (it.get("webpage_url") or it.get("url")) != url
                ]
                self._refresh_selected_list()
                self._style_playlist_item(item, False)  # update styling
        else:
            if self.chk_multi.isChecked():
                # Multi: add placeholder and style as selected; do not fetch metadata now
                self._upsert_selected(
                    info if isinstance(info, dict) else {"url": url, "webpage_url": url}
                )
                self._style_playlist_item(item, True)
                self.lbl_status.setText("Added to selected.")
            else:
                self.lbl_status.setText("Fetching info...")
                self._start_fetch(url)

    # Fixed: Define the missing method in the main class body, not as a duplicate at the end
    def _toggle_from_results(self, item: QListWidgetItem):
        """Toggle a search result item in/out of selection"""
        data = item.data(Qt.ItemDataRole.UserRole) or {}
        url = data.get("webpage_url") or data.get("url")
        title = data.get("title") or "Unknown title"
        if not url:
            return

        # Check if already selected
        idx = next(
            (
                i
                for i, it in enumerate(self.selected)
                if (it.get("webpage_url") or it.get("url")) == url
            ),
            -1,
        )

        if idx >= 0:
            # Already selected - confirm removal
            if (
                QMessageBox.question(
                    self, "Remove video", f"Remove '{title}' from selected?"
                )
                == QMessageBox.StandardButton.Yes
            ):
                self.selected.pop(idx)
                self._refresh_selected_list()
            return

        # Not selected - add it
        if self.chk_multi.isChecked():
            # Multi: just add placeholder, do not fetch metadata now
            self._upsert_selected(
                {
                    "title": title,
                    "url": url,
                    "webpage_url": url,
                    "thumbnail": data.get("thumbnail"),
                    "thumbnails": data.get("thumbnails"),
                }
            )
            self.lbl_status.setText("Added to selected.")
        else:
            # Single: fetch metadata and proceed
            self.lbl_status.setText("Fetching info...")
            self._start_fetch(url)

    def reset(self):
        """Reset widget to initial state"""
        # Cancel any in-flight fetch
        self._cancel_fetch()

        # Clear inputs and status
        self.txt.clear()
        self.lbl_status.setText("")
        self._set_busy(False)

        # Clear all lists
        self.results.clear()
        self.playlist_list.clear()
        self.selected.clear()
        self.selected_list.clear()

        # Reset UI state
        self.tabs.setCurrentWidget(self.tab_search)
        self.tabs.setTabVisible(self.idx_selected, False)
        self.tabs.setTabVisible(self.idx_playlist, False)

        # Reset checkboxes without triggering handlers
        self.chk_pl_select_all.blockSignals(True)
        self.chk_pl_select_all.setChecked(False)
        self.chk_pl_select_all.blockSignals(False)

        self.chk_multi.blockSignals(True)
        self.chk_multi.setChecked(False)
        self.chk_multi.blockSignals(False)

        self.btn_next.setVisible(False)

        # Stop timers and clear caches
        if hasattr(self, "search_timer"):
            self.search_timer.stop()

        self._thumb_threads.clear()
        self._thumb_cache.clear()
        self._thumb_pending.clear()

        # Disconnect scroll handlers
        try:
            self.playlist_list.verticalScrollBar().valueChanged.disconnect(
                self._load_visible_playlist_thumbnails
            )
        except Exception:
            pass

    # Keep only one definition of this handler
    def _remove_from_selected_prompt(self, item: QListWidgetItem):
        info = item.data(Qt.ItemDataRole.UserRole) or {}
        url = info.get("webpage_url") or info.get("url")
        title = info.get("title") or "Untitled"
        if not url:
            return
        if (
            QMessageBox.question(
                self, "Remove video", f"Remove '{title}' from selected?"
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.selected = [
                it
                for it in self.selected
                if (it.get("webpage_url") or it.get("url")) != url
            ]
            self._refresh_selected_list()
            for i in range(self.playlist_list.count()):
                pit = self.playlist_list.item(i)
                pdata = pit.data(Qt.ItemDataRole.UserRole) or {}
                pu = pdata.get("webpage_url") or pdata.get("url")
                if pu == url:
                    self._style_playlist_item(pit, False)
                    break
            self.tabs.setTabVisible(self.idx_selected, self.selected_list.count() > 0)

    # "Next" in multi-select mode: emit all selected infos
    def _confirm_selection(self):
        if not self.selected:
            QMessageBox.information(self, "No videos", "No videos selected.")
            return
        # Ensure all selected have metadata before emitting
        self._fetch_all_selected_then_emit()

    # ----- Thumbnail and Styling Helpers (ADDED) -----
    def _load_thumb(self, url: str):
        if not url:
            return None
        try:
            from urllib.request import urlopen

            data = urlopen(url, timeout=5).read()
            pix = QPixmap()
            if pix.loadFromData(data):
                return pix
        except Exception:
            pass
        return None

    def _to_gray(self, pix: QPixmap) -> QPixmap:
        try:
            img = pix.toImage().convertToFormat(QImage.Format.Format_Grayscale8)
            return QPixmap.fromImage(img)
        except Exception:
            return pix

    def _apply_icon_style(self, item: QListWidgetItem, selected: bool):
        pix = item.data(ICON_PIXMAP_ROLE)
        if isinstance(pix, QPixmap):
            item.setIcon(QIcon(pix if selected else self._to_gray(pix)))

    def _style_playlist_item(self, item: QListWidgetItem, selected: bool):
        if selected:
            item.setForeground(QColor(self.settings.ui.accent_color_hex))
        else:
            item.setForeground(QColor("#8a8b90"))
        self._apply_icon_style(item, selected)

    def _set_result_icon_if_match(self, row: int, pix: QPixmap, expected_url: str):
        try:
            if row < 0 or row >= self.results.count():
                return
            it = self.results.item(row)
            data = it.data(Qt.ItemDataRole.UserRole) or {}
            current = data.get("thumbnail") or (data.get("thumbnails") or [{}])[-1].get(
                "url"
            )
            if current != expected_url:
                return  # item changed; skip
            it.setIcon(QIcon(pix))
            it.setData(ICON_PIXMAP_ROLE, pix)
        except Exception:
            pass
        self._thumb_threads.clear()

    # NEW: set icon in playlist tab by video URL
    def _set_playlist_icon_for_url(self, video_url: str, pix: QPixmap):
        try:
            for i in range(self.playlist_list.count()):
                item = self.playlist_list.item(i)
                data = item.data(Qt.ItemDataRole.UserRole) or {}
                u = (data.get("webpage_url") or data.get("url")) or ""
                if u == video_url:
                    item.setIcon(QIcon(pix))
                    item.setData(ICON_PIXMAP_ROLE, pix)
                    # keep current selected/gray style
                    self._apply_icon_style(item, self._is_selected(data))
                    break
        except Exception:
            pass

    # NEW: set icon in selected tab by video URL
    def _set_selected_icon_for_url(self, video_url: str, pix: QPixmap):
        try:
            for i in range(self.selected_list.count()):
                item = self.selected_list.item(i)
                data = item.data(Qt.ItemDataRole.UserRole) or {}
                u = (data.get("webpage_url") or data.get("url")) or ""
                if u == video_url:
                    item.setIcon(QIcon(pix))
                    item.setData(ICON_PIXMAP_ROLE, pix)
                    break
        except Exception:
            pass

    # Allow MainWindow to enable/disable Next and optionally show a hint
    def set_next_enabled(self, enabled: bool, note: str = ""):
        try:
            self.btn_next.setEnabled(enabled)
            if note is not None:
                self.lbl_status.setText(note)
        except Exception:
            pass

    # --- Thumbnail queue helpers (bounded concurrency) ---
    def _enqueue_thumb(self, thumb_url: str, setter_cb, low_priority=False):
        """Queue thumbnail for fetching with prioritization and caching"""
        if not thumb_url:
            return

        # Use cache if available
        if thumb_url in self._thumb_cache:
            try:
                setter_cb(self._thumb_cache[thumb_url])
                return
            except Exception:
                pass

        # Skip if already queued/active
        if thumb_url in self._thumb_pending:
            return

        # Only queue if not overloaded
        if len(self._thumb_queue) < 100:
            item = (thumb_url, setter_cb)
            if low_priority:
                self._thumb_queue.append(item)
            else:
                self._thumb_queue.appendleft(item)
            self._thumb_maybe_start()

    def _thumb_maybe_start(self):
        while len(self._thumb_active) < self._thumb_max and self._thumb_queue:
            url, cb = self._thumb_queue.popleft()
            # Serve from cache if filled while waiting
            if url in self._thumb_cache:
                try:
                    cb(self._thumb_cache[url])
                    continue
                except Exception:
                    pass
            # Avoid launching duplicate worker
            if url in self._thumb_pending:
                continue
            w = Step1LinkWidget._ThumbWorker(-1, url, self)
            self._thumb_pending.add(url)
            self._thumb_active.add(w)
            self._thumb_threads.append(w)

            # Build QPixmap in UI thread, cache it, then call original callback
            def _forward(_row, img_bytes, u, _cb=cb, _url=url, _self=self):
                try:
                    px = QPixmap()
                    if img_bytes and px.loadFromData(img_bytes):
                        _self._thumb_cache[_url] = px
                        try:
                            _cb(px)  # most callbacks accept (pixmap)
                        except TypeError:
                            try:
                                _cb(px, u)  # some accept (pixmap, url)
                            except Exception:
                                pass
                except Exception:
                    pass

            w.done.connect(_forward)
            w.finished.connect(lambda _w=w: self._on_thumb_finished(_w, url))
            w.start()

    # NEW: worker finished handler (cleanup + start next)
    def _on_thumb_finished(self, w, url: str):
        try:
            self._thumb_active.discard(w)
            self._thumb_pending.discard(url)
            try:
                w.deleteLater()
            except Exception:
                pass
        finally:
            self._thumb_maybe_start()

    # NEW: Lazy thumbnail loading for playlist based on scroll position
    def _load_visible_playlist_thumbnails(self):
        try:
            if self.tabs.currentIndex() != self.idx_playlist:
                return
            vp = self.playlist_list.viewport().rect()
            count = self.playlist_list.count()
            if count <= 0:
                return

            first = None
            last = None
            # Scan items until we pass the viewport bottom; breaks early
            for i in range(count):
                it = self.playlist_list.item(i)
                r = self.playlist_list.visualItemRect(it)
                if not r.isValid():
                    continue
                if r.intersects(vp):
                    if first is None:
                        first = i
                    last = i
                elif first is not None and r.top() > vp.bottom():
                    break

            if first is None:
                # Fallback: queue the first screenful
                first = 0
                # heuristic: try ~30 items
                last = min(count - 1, 29)
            else:
                # Add small buffer to avoid loading gaps while scrolling
                first = max(0, first - 5)
                last = min(count - 1, (last if last is not None else first) + 5)

            for i in range(first, last + 1):
                item = self.playlist_list.item(i)
                if not item or not item.icon().isNull():
                    continue
                data = item.data(Qt.ItemDataRole.UserRole) or {}
                turl = data.get("thumbnail") or (data.get("thumbnails") or [{}])[
                    -1
                ].get("url")
                if not turl:
                    continue
                vurl = (data.get("webpage_url") or data.get("url")) or ""
                if not vurl:
                    continue
                if turl in self._thumb_cache:
                    pix = self._thumb_cache[turl]
                    item.setIcon(QIcon(pix))
                    item.setData(ICON_PIXMAP_ROLE, pix)
                    self._apply_icon_style(item, self._is_selected(data))
                    continue
                # Queue with low priority; callback sets by URL to avoid races
                self._enqueue_thumb(
                    turl,
                    lambda px, _, v=vurl: self._set_playlist_icon_for_url(v, px),
                    low_priority=True,
                )
        except Exception:
            pass

    # Handle the "Select all" checkbox in playlist tab
    def _on_pl_select_all_toggled(self, checked: bool):
        self.playlist_list.setUpdatesEnabled(False)
        try:
            if checked:
                # Add all playlist items to selection
                for i in range(self.playlist_list.count()):
                    it = self.playlist_list.item(i)
                    e = it.data(Qt.ItemDataRole.UserRole) or {}
                    if self._is_selected(e):
                        continue
                    self.selected.append(e)
                    self._style_playlist_item(it, True)
            else:
                # Remove any selected item that belongs to this playlist view
                urls = []
                for i in range(self.playlist_list.count()):
                    it = self.playlist_list.item(i)
                    e = it.data(Qt.ItemDataRole.UserRole) or {}
                    u = e.get("webpage_url") or e.get("url")
                    if not u:
                        continue
                    urls.append(u)
                    self._style_playlist_item(it, False)
                urlset = set(urls)
                self.selected = [
                    s
                    for s in self.selected
                    if (s.get("webpage_url") or s.get("url")) not in urlset
                ]
            self._refresh_selected_list()
            self.tabs.setTabVisible(self.idx_selected, self.selected_list.count() > 0)
        finally:
            self.playlist_list.setUpdatesEnabled(True)
            self._thumb_threads.clear()
