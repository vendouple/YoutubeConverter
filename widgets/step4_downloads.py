import os
import sys
import subprocess
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QFrame,
    QMessageBox,
)

from core.settings import AppSettings, SettingsManager
from core.ffmpeg_manager import FF_EXE, FF_DIR
from core.yt_manager import Downloader, InfoFetcher  # add InfoFetcher


class DownloadItemWidget(QWidget):
    def __init__(self, title: str):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)  # keep in sync with Step 1 spacing feel
        lay.setSpacing(6)

        self.thumb = QLabel()
        self.thumb.setFixedSize(96, 54)
        self.thumb.setObjectName(
            "ThumbnailLabel"
        )  # Use object name for theme-aware styling
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)  # center with letterbox
        self.thumb.setScaledContents(False)

        self.title = QLabel(title)
        self.title.setWordWrap(True)

        self.status = QLabel("Waiting...")
        self.progress = QProgressBar()
        self.progress.setObjectName("DlProgress")
        self.progress.setValue(0)

        col = QVBoxLayout()
        col.addWidget(self.title)
        col.addWidget(self.status)
        col.addWidget(self.progress)

        lay.addWidget(self.thumb)
        lay.addLayout(col, 1)

        # Reserve full height before hiding status/progress so the list doesn't jump
        self._full_size_hint = self.sizeHint()
        self.status.hide()
        self.progress.hide()

    def full_size_hint(self):
        return self._full_size_hint


class Step4DownloadsWidget(QWidget):
    allFinished = pyqtSignal()
    backRequested = pyqtSignal()
    # Signal for manual completion when auto-reset is disabled
    doneRequested = pyqtSignal()
    # Signals for UI locking
    downloadsStarted = pyqtSignal()  # Emitted when downloads start
    downloadsStopped = pyqtSignal()  # Emitted when downloads are stopped or finished

    class _ThumbWorker(QThread):
        done = pyqtSignal(str, QPixmap)  # video_url, pixmap

        def __init__(self, video_url: str, thumb_url: str, parent=None):
            super().__init__(parent)
            self.vurl = video_url
            self.turl = thumb_url

        def run(self):
            try:
                import requests

                r = requests.get(self.turl, timeout=8)
                if not r.ok:
                    return
                px = QPixmap()
                if px.loadFromData(r.content):
                    # ensure we emit original pixmap; scaling is done in UI thread
                    self.done.emit(self.vurl, px)
            except Exception:
                pass

    def __init__(self, settings: AppSettings | None = None):
        super().__init__()
        if settings is None:
            try:
                from core.settings import SettingsManager as _SM

                settings = _SM().load()
            except Exception:
                pass
        self.settings = settings  # type: ignore[assignment]
        self.settings_mgr = SettingsManager()
        self.items: List[Dict] = []
        self.kind = "audio"
        self.fmt = "mp3"
        self.quality = "best"
        self.downloader: Optional[Downloader] = None
        self._meta_fetchers: dict[int, InfoFetcher] = {}
        self._thumb_threads: List[Step4DownloadsWidget._ThumbWorker] = []
        self._downloading = False
        self._file_map = {}  # row -> filepath
        self._nightly_prompt_shown = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        # Footer controls
        self.btn_back = QPushButton("Back")
        try:
            last_dir = getattr(self.settings, "last_download_dir", "")
        except Exception:
            last_dir = ""
        if not last_dir:
            try:
                last_dir = os.path.expanduser("~")
            except Exception:
                last_dir = ""
        self.lbl_dir = QLabel(last_dir)
        self.btn_choose = QPushButton("Choose folder")
        self.btn_start = QPushButton("Start")
        self.btn_start.setEnabled(False)
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setVisible(False)  # Hidden until started
        self.btn_done = QPushButton("Done")
        self.btn_done.setVisible(False)
        self.btn_back.clicked.connect(self.backRequested.emit)
        self.btn_choose.clicked.connect(self._choose_dir)
        self.btn_start.clicked.connect(self._toggle_start_pause)
        self.btn_stop.clicked.connect(self._stop_downloads)
        self.btn_done.clicked.connect(self._done_clicked)

        # List content
        self.list = QListWidget()
        self.list.setFrameShape(QFrame.Shape.NoFrame)
        self.list.setSpacing(4)
        self.list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        lay.addWidget(self.list, 1)

        # Footer with separator and controls (Back on left, folder + actions on right)
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        lay.addWidget(sep)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        footer.addWidget(self.btn_back)

        # Middle: folder picker
        folder_bar = QHBoxLayout()
        folder_bar.setSpacing(6)
        folder_bar.addWidget(QLabel("Save to:"))
        folder_bar.addWidget(self.lbl_dir, 1)
        folder_bar.addWidget(self.btn_choose)
        footer.addLayout(folder_bar, 1)

        # Right: actions
        actions = QHBoxLayout()
        actions.setSpacing(6)
        actions.addWidget(self.btn_start)
        actions.addWidget(self.btn_stop)
        actions.addWidget(self.btn_done)
        footer.addLayout(actions)
        lay.addLayout(footer)

        # Hook double click on list if available
        try:
            self.list.itemDoubleClicked.connect(self._open_item_file)
        except Exception:
            pass

    # Allow MainWindow to push settings changes
    def apply_ez_mode(self, settings=None):
        try:
            if settings is not None:
                self.settings = settings
        except Exception:
            pass

    def configure(self, selection: Dict, settings: AppSettings):
        # Stop any prior background metadata fetchers safely
        self._cleanup_bg_metadata()
        if self.downloader:
            try:
                self.downloader.stop()
            except Exception:
                pass
            self.downloader = None
        self._downloading = False
        self._nightly_prompt_shown = False
        self.items = selection.get("items", [])
        self.kind = selection.get("kind", settings.defaults.kind)
        self.fmt = selection.get("format", settings.defaults.format)
        self.quality = selection.get("quality", "best")
        self._populate()

    # Call when downloads are about to start
    def _on_downloads_started(self):
        self._downloading = True
        try:
            if hasattr(self, "btn_back"):
                self.btn_back.setEnabled(False)
        except Exception:
            pass
        try:
            self.btn_done.setVisible(False)
        except Exception:
            pass

    def _populate(self):
        self.list.clear()
        self._file_map.clear()
        for idx, it in enumerate(self.items):
            title = it.get("title") or "Untitled"
            w = DownloadItemWidget(title)
            # Async thumb fetch
            vurl = (it.get("webpage_url") or it.get("url")) or ""
            thumb_url = it.get("thumbnail") or (it.get("thumbnails") or [{}])[-1].get(
                "url"
            )
            if thumb_url and vurl:
                worker = Step4DownloadsWidget._ThumbWorker(vurl, thumb_url, self)
                worker.done.connect(self._set_dl_thumb_if_match)
                worker.finished.connect(
                    lambda w=worker: (
                        self._thumb_threads.remove(w)
                        if w in self._thumb_threads
                        else None
                    )
                )
                self._thumb_threads.append(worker)
                worker.start()
            item = QListWidgetItem()
            item.setSizeHint(w.full_size_hint())  # Keep height stable
            self.list.addItem(item)
            self.list.setItemWidget(item, w)

        # Reset button states for new items
        self.btn_start.setEnabled(bool(self.items))
        self.btn_start.setText("Start")
        self.btn_stop.setVisible(False)
        self.btn_stop.setEnabled(False)
        self.btn_done.setVisible(False)
        self._downloading = False

    # Do not start background metadata fetching

    def _start_bg_metadata(self):
        for idx, it in enumerate(self.items):
            if not self._needs_metadata(it) or idx in self._meta_fetchers:
                continue
            url = it.get("webpage_url") or it.get("url")
            if not url:
                continue
            f = InfoFetcher(url)

            def _ok(meta: dict, i=idx):
                try:
                    self.items[i] = {**self.items[i], **(meta or {})}
                    w = self._get_widget(i)
                    if w:
                        title = self.items[i].get("title") or "Untitled"
                        w.title.setText(title)
                        turl = self.items[i].get("thumbnail") or (
                            self.items[i].get("thumbnails") or [{}]
                        )[-1].get("url")
                        if turl:
                            try:
                                import requests

                                r = requests.get(turl, timeout=6)
                                if r.ok:
                                    px = QPixmap()
                                    if px.loadFromData(r.content):
                                        w.thumb.setPixmap(px)
                            except Exception:
                                pass
                        w.status.setText("Waiting...")
                        w.progress.setRange(0, 100)
                        w.progress.setValue(0)
                finally:
                    self._meta_fetchers.pop(i, None)

            def _fail(err: str, i=idx):
                self._meta_fetchers.pop(i, None)

            f.finished_ok.connect(_ok)
            f.finished_fail.connect(_fail)
            self._meta_fetchers[idx] = f
            f.start()

    def _cleanup_bg_metadata(self):
        """Safely disconnect and clean up metadata fetchers"""
        for i, f in list(self._meta_fetchers.items()):
            try:
                f.finished_ok.disconnect()
            except Exception:
                pass
            try:
                f.finished_fail.disconnect()
            except Exception:
                pass
        self._meta_fetchers.clear()

        # Free memory
        try:
            import gc

            gc.collect()
        except Exception:
            pass

    # Small helper to mirror Downloader heuristic
    def _needs_metadata(self, it: dict) -> bool:
        """Determine if an item needs metadata fetching"""
        if not it:
            return True
        if not it.get("url") and not it.get("webpage_url"):
            return False
        has_core = (
            bool(it.get("id")) or bool(it.get("duration")) or bool(it.get("extractor"))
        )
        has_thumb = bool(it.get("thumbnail")) or bool(it.get("thumbnails"))
        return not (has_core and has_thumb)

    def _toggle_start_pause(self):
        if not self.downloader:
            self.start_downloads()
            return
        # Toggle pause/resume
        if self.downloader.is_paused():
            self.downloader.resume()
            self.btn_start.setText("Pause")
        else:
            self.downloader.pause()
            self.btn_start.setText("Resume")

    def _check_file_conflicts(self, base_dir: str) -> list:
        """
        Check if any files in the download list already exist.

        Returns a list of conflicts with 'title', 'path', and 'index' keys.
        """
        conflicts = []
        try:
            for idx, item in enumerate(self.items):
                title = item.get("title", "Untitled")
                # Construct expected filename based on download settings
                ext = self.fmt or ("mp3" if self.kind == "audio" else "mp4")
                # Sanitize title for filename
                safe_title = "".join(
                    c for c in title if c.isalnum() or c in (" ", "-", "_")
                ).strip()
                safe_title = safe_title[:200]  # Limit length

                expected_path = os.path.join(base_dir, f"{safe_title}.{ext}")

                if os.path.exists(expected_path):
                    conflicts.append(
                        {"title": title, "path": expected_path, "index": idx}
                    )
        except Exception:
            pass

        return conflicts

    def start_downloads(self):
        # Do not start unless FFmpeg is available
        try:
            import shutil

            ff_ready = os.path.exists(FF_EXE) or (shutil.which("ffmpeg") is not None)
        except Exception:
            ff_ready = False
        if not ff_ready:
            try:
                from PyQt6.QtWidgets import QMessageBox

                QMessageBox.information(
                    self,
                    "Please wait",
                    "FFmpeg is still installing. Try again when finished.",
                )
            except Exception:
                pass
            return
        if not self.items:
            return
        base = self.lbl_dir.text()
        os.makedirs(base, exist_ok=True)
        # Save last dir
        try:
            if self.settings is not None:
                self.settings.last_download_dir = base
                self.settings_mgr.save(self.settings)
        except Exception:
            pass

        # Ensure all items show their UI only now
        for i in range(self.list.count()):
            w = self._get_widget(i)
            if w:
                w.status.setText("Queued")
                w.status.show()
                w.progress.setRange(0, 100)
                w.progress.setValue(0)
                w.progress.show()

        ff_path = FF_DIR if os.path.exists(FF_EXE) else None

        # Check for file conflicts before starting download
        conflicts = self._check_file_conflicts(base)
        if conflicts:
            from widgets.file_conflict_dialog import FileConflictDialog

            dialog = FileConflictDialog(conflicts, self)
            if dialog.exec() == dialog.DialogCode.Accepted:
                action = dialog.get_action()
                if action == "skip_all":
                    # User chose to skip all - don't start download
                    return
                elif action == "skip":
                    # Skip the first conflict only (for single file scenarios)
                    # Remove the conflicting item from download list
                    if conflicts:
                        conflict_idx = conflicts[0].get("index", -1)
                        if 0 <= conflict_idx < len(self.items):
                            self.items.pop(conflict_idx)
                            self._populate()
                    if not self.items:
                        return
                elif action == "replace" or action == "replace_all":
                    # Proceed with download - files will be overwritten
                    pass
            else:
                # Dialog was cancelled
                return

        self.downloader = Downloader(
            self.items,
            base,
            self.kind,
            self.fmt,
            ff_path,
            quality=self.quality,
        )
        self.downloader.itemStatus.connect(self._on_item_status)
        self.downloader.itemProgress.connect(self._on_item_progress)
        self.downloader.itemThumb.connect(self._on_item_thumb)
        self.downloader.itemFileReady.connect(self._on_item_file_ready)
        self.downloader.finished_all.connect(self._on_all_finished)
        self.downloader.retryLimitReached.connect(self._on_retry_limit)
        self.btn_start.setText("Pause")
        self.btn_start.setEnabled(True)
        self.btn_stop.setVisible(True)  # Show Stop once started
        self.btn_stop.setEnabled(True)

        # Emit signal to lock UI
        try:
            self.downloadsStarted.emit()
        except Exception:
            pass

        self.downloader.start()

    def _stop_downloads(self):
        if self.downloader:
            try:
                self.downloader.stop()
            except Exception:
                pass
            self.downloader = None

        # Re-enable start button to allow restart
        self.btn_start.setText("Start")
        self.btn_start.setEnabled(bool(self.items))
        self.btn_stop.setVisible(False)
        self.btn_stop.setEnabled(False)

        # Emit signal to unlock UI
        try:
            self.downloadsStopped.emit()
        except Exception:
            pass

        # Update all items to "Stopped" state
        for i in range(self.list.count()):
            w = self._get_widget(i)
            if w:
                current_status = w.status.text().lower()
                # Only update if not already done or failed
                if not (
                    "done" in current_status
                    or "error" in current_status
                    or "failed" in current_status
                ):
                    w.status.setText("Stopped")
                    w.progress.setRange(0, 100)
                    w.progress.setValue(0)

        self._on_downloads_stopped()
        self._cleanup_bg_metadata()

    def _choose_dir(self):
        d = QFileDialog.getExistingDirectory(
            self, "Choose download folder", self.lbl_dir.text()
        )
        if d:
            self.lbl_dir.setText(d)

    def _on_retry_limit(self, message: str):
        if self._nightly_prompt_shown:
            return
        self._nightly_prompt_shown = True
        try:
            details = message or "Downloads are still failing after multiple retries."
            details += (
                "\n\nSwitching yt-dlp to the nightly branch can resolve recent site changes."
                "\nWould you like to switch now?"
            )
            resp = QMessageBox.question(
                self,
                "Consider yt-dlp nightly",
                details,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if resp == QMessageBox.StandardButton.Yes:
                try:
                    ytdlp_settings = getattr(self.settings, "ytdlp", None)
                    if ytdlp_settings is not None and self.settings is not None:
                        setattr(ytdlp_settings, "branch", "nightly")
                        self.settings_mgr.save(self.settings)
                        QMessageBox.information(
                            self,
                            "Nightly branch enabled",
                            "Future yt-dlp updates will use the nightly build.",
                        )
                except Exception:
                    pass
        except Exception:
            pass

    def _on_item_status(self, idx: int, text: str):
        w = self._get_widget(idx)
        if w:
            if not w.status.isVisible():
                w.status.show()
            if not w.progress.isVisible():
                w.progress.show()
            w.status.setText(text)

            # Busy indicator for processing/removal phase
            t = (text or "").strip().lower()
            if (
                t.startswith("processing")
                or t.startswith("removing")
                or t.startswith("trimming")
                or t.startswith("merging")
            ):
                w.progress.setRange(0, 0)
            elif (
                t.startswith("error")
                or t.startswith("failed")
                or t.startswith("done")
                or t.startswith("stopped")
                or "already downloaded" in t
            ):
                w.progress.setRange(0, 100)

                # Visual feedback for different states
                if t.startswith("done") or "already downloaded" in t:
                    # Success - green-tinted progress bar
                    w.progress.setValue(100)
                    try:
                        w.progress.setStyleSheet(
                            """
                            QProgressBar {
                                border: 1px solid #4caf50;
                                border-radius: 4px;
                                text-align: center;
                                background: #e8f5e9;
                            }
                            QProgressBar::chunk {
                                background-color: #4caf50;
                            }
                        """
                        )
                    except Exception:
                        pass
                elif t.startswith("error") or t.startswith("failed"):
                    # Error - red-tinted progress bar
                    w.progress.setValue(0)
                    try:
                        w.progress.setStyleSheet(
                            """
                            QProgressBar {
                                border: 1px solid #f44336;
                                border-radius: 4px;
                                text-align: center;
                                background: #ffebee;
                                color: #c62828;
                            }
                            QProgressBar::chunk {
                                background-color: #f44336;
                            }
                        """
                        )
                        # Make error text more prominent
                        w.status.setStyleSheet("color: #c62828; font-weight: bold;")
                    except Exception:
                        pass
                elif t.startswith("stopped"):
                    # Stopped - neutral gray
                    w.progress.setValue(0)
                    try:
                        w.progress.setStyleSheet("")
                        w.status.setStyleSheet("")
                    except Exception:
                        pass

    def _on_item_progress(
        self, idx: int, percent: float, speed: float, eta: Optional[int]
    ):
        w = self._get_widget(idx)
        if w:
            # Ensure determinate during downloading
            if w.progress.minimum() == 0 and w.progress.maximum() == 0:
                w.progress.setRange(0, 100)
            w.progress.setValue(int(percent))
            if eta is not None:
                w.status.setText(
                    f"{percent:.1f}% | {speed/1024/1024:.2f} MB/s | ETA {eta}s"
                )

    def _on_item_thumb(self, idx: int, data: bytes):
        w = self._get_widget(idx)
        if w:
            px = QPixmap()
            if px.loadFromData(data):
                w.thumb.setPixmap(
                    px.scaled(
                        w.thumb.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )

    # Connect this to Downloader.itemFileReady
    def _on_item_file_ready(self, row: int, path: str):
        self._file_map[row] = path
        try:
            # Add a shortcut icon to indicate openable file
            if hasattr(self, "list") and 0 <= row < self.list.count():
                it: QListWidgetItem = self.list.item(row)
                if it and it.icon().isNull():
                    try:
                        # Create a custom shortcut icon (box with arrow)
                        from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen
                        from PyQt6.QtCore import QRect, QPoint

                        pixmap = QPixmap(48, 48)
                        pixmap.fill(Qt.GlobalColor.transparent)

                        painter = QPainter(pixmap)
                        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

                        # Draw document icon (rectangle with folded corner)
                        painter.setPen(QPen(QColor("#2196F3"), 2))
                        painter.setBrush(QColor("#E3F2FD"))
                        painter.drawRoundedRect(8, 6, 28, 36, 3, 3)

                        # Draw folded corner
                        painter.setBrush(QColor("#BBDEFB"))
                        points = [QPoint(30, 6), QPoint(36, 12), QPoint(30, 12)]
                        painter.drawPolygon(points)

                        # Draw shortcut arrow overlay (white circle with blue arrow)
                        painter.setBrush(QColor("#FFFFFF"))
                        painter.setPen(QPen(QColor("#1976D2"), 2))
                        painter.drawEllipse(26, 26, 18, 18)

                        # Draw arrow
                        painter.setPen(QPen(QColor("#1976D2"), 2))
                        # Arrow shaft
                        painter.drawLine(30, 35, 38, 35)
                        # Arrow head
                        painter.drawLine(38, 35, 35, 32)
                        painter.drawLine(38, 35, 35, 38)

                        painter.end()

                        it.setIcon(QIcon(pixmap))
                    except Exception:
                        # Fallback to system icon
                        try:
                            it.setIcon(QIcon.fromTheme("document-open"))
                        except Exception:
                            pass
                it.setData(
                    Qt.ItemDataRole.UserRole,
                    {**(it.data(Qt.ItemDataRole.UserRole) or {}), "filepath": path},
                )
        except Exception:
            pass

    def _open_item_file(self, item: QListWidgetItem):
        try:
            data = item.data(Qt.ItemDataRole.UserRole) or {}
            path = data.get("filepath")
            if not path or not os.path.exists(path):
                return
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:
            pass

    def open_or_reveal(self, item: dict):
        """Open file if it exists, else reveal containing folder, else no-op.

        Must not raise exceptions even on malformed input.
        """
        try:
            path = item.get("output_path") if isinstance(item, dict) else None
            if path and os.path.exists(path):
                if sys.platform.startswith("win"):
                    os.startfile(path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", path])
                else:
                    subprocess.Popen(["xdg-open", path])
                return
            # Try containing folder if path is defined but missing
            if path:
                folder = os.path.dirname(path)
                if folder and os.path.isdir(folder):
                    if sys.platform.startswith("win"):
                        os.startfile(folder)
                    elif sys.platform == "darwin":
                        subprocess.Popen(["open", folder])
                    else:
                        subprocess.Popen(["xdg-open", folder])
        except Exception:
            pass

    def _get_widget(self, idx: int) -> Optional[DownloadItemWidget]:
        it = self.list.item(idx)
        if not it:
            return None
        return self.list.itemWidget(it)

    # Call when user presses Stop (ensure to re-enable Back only after stopped)
    def _on_downloads_stopped(self):
        self._downloading = False
        try:
            if hasattr(self, "btn_back"):
                self.btn_back.setEnabled(True)
        except Exception:
            pass

    # Call when all finished
    def _on_all_finished(self):
        self._downloading = False

        # Emit signal to unlock UI
        try:
            self.downloadsStopped.emit()
        except Exception:
            pass

        # Disable Back button to make done state obvious
        try:
            if hasattr(self, "btn_back"):
                self.btn_back.setEnabled(False)
        except Exception:
            pass

        # Disable folder selection
        try:
            if hasattr(self, "btn_choose"):
                self.btn_choose.setEnabled(False)
        except Exception:
            pass

        # Disable Start and Stop buttons when finished
        self.btn_start.setEnabled(False)
        self.btn_start.setText("Start")
        self.btn_stop.setVisible(False)
        self.btn_stop.setEnabled(False)

        # Gray out the download list to make done state obvious
        try:
            self.list.setEnabled(False)
            self.list.setStyleSheet(
                """
                QListWidget:disabled {
                    background: #f5f5f5;
                    color: #999999;
                    opacity: 0.6;
                }
            """
            )
        except Exception:
            pass

        # Show Done button if auto reset is disabled
        try:
            auto_reset = getattr(self.settings.app, "auto_reset_after_downloads", True)
            if not auto_reset:
                self.btn_done.setEnabled(True)
                self.btn_done.setVisible(True)
                try:
                    accent = getattr(self.settings.ui, "accent_color_hex", "#F28C28")
                    self.btn_done.setStyleSheet(
                        f"""
                        QPushButton {{
                            background: {accent};
                            color: white;
                            border: 2px solid {accent};
                            border-radius: 8px;
                            padding: 10px 20px;
                            font-weight: bold;
                            font-size: 14px;
                        }}
                        QPushButton:hover {{
                            background: {accent};
                            opacity: 0.9;
                        }}
                    """
                    )
                except Exception:
                    self.btn_done.setVisible(True)
        except Exception:
            pass

        try:
            self.allFinished.emit()
        except Exception:
            pass

    def _done_clicked(self):
        # Reset the download UI
        self.reset()
        # Signal to parent to go back to step 1
        try:
            self.doneRequested.emit()
        except Exception:
            pass

    def reset(self):
        """Reset widget to initial state and free resources"""
        self._cleanup_bg_metadata()
        self.list.clear()
        self.items = []
        self._file_map.clear()
        self.downloader = None
        self._downloading = False
        self.btn_start.setText("Start")
        self.btn_start.setEnabled(False)
        self.btn_stop.setVisible(False)
        self.btn_stop.setEnabled(False)
        self.btn_done.setVisible(False)
        self.btn_done.setStyleSheet("")
        self._nightly_prompt_shown = False

        # Re-enable list and clear any disabled styling
        try:
            self.list.setEnabled(True)
            self.list.setStyleSheet("")
        except Exception:
            pass

        # Clear thumbnail threads
        for worker in self._thumb_threads:
            try:
                if worker.isRunning():
                    worker.disconnect()
                    worker.terminate()
                    worker.wait(100)
            except Exception:
                pass
        self._thumb_threads.clear()

        # Force garbage collection
        try:
            import gc

            gc.collect()
        except Exception:
            pass

    # --- Open / reveal helper (robust against missing file) ---
    def open_or_reveal(self, item: dict):
        try:
            path = (item or {}).get("output_path")
            if not path:
                return
            if not os.path.exists(path):
                # Attempt to reveal parent directory if exists
                parent = os.path.dirname(path)
                if parent and os.path.isdir(parent):
                    try:
                        if sys.platform.startswith("win"):
                            os.startfile(parent)
                        elif sys.platform == "darwin":
                            subprocess.Popen(["open", parent])
                        else:
                            subprocess.Popen(["xdg-open", parent])
                    except Exception:
                        pass
                return
            # Open existing file
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:
            pass

    # Apply a thumbnail to the matching list widget by video URL
    def _set_dl_thumb_if_match(self, video_url: str, pix: QPixmap):
        try:
            for i, it in enumerate(self.items):
                u = (it.get("webpage_url") or it.get("url")) or ""
                if u == video_url:
                    w = self._get_widget(i)
                    if w:
                        w.thumb.setPixmap(
                            pix.scaled(
                                w.thumb.size(),
                                Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation,
                            )
                        )
                    break
        except Exception:
            pass


DownloadsWidget = Step4DownloadsWidget
