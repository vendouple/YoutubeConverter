import os
import sys
import signal
from typing import List, Dict
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QPushButton,
    QFrame,
    QScrollArea,
    QProgressDialog,
    QDialog,
    QDialogButtonBox,
    QTextBrowser,
    QLabel,
)


def _app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


# Prefer a user-writable logs directory; try SETTINGS_DIR if available, else APPDATA, else app dir
def _log_dir() -> str:
    try:
        d = None
        if "SETTINGS_DIR" in globals() and isinstance(
            globals().get("SETTINGS_DIR"), str
        ):
            d = os.path.join(globals()["SETTINGS_DIR"], "logs")
        if not d:
            appdata = os.getenv("APPDATA") or os.path.expanduser("~")
            d = os.path.join(appdata, "YoutubeConverter", "logs")
        os.makedirs(d, exist_ok=True)
        return d
    except Exception:
        fallback = os.path.join(_app_dir(), "logs")
        try:
            os.makedirs(fallback, exist_ok=True)
        except Exception:
            pass
        return fallback


# NEW: helper to write both timestamped and rolling logs, returns the timestamped path
def _write_crash_log(exctype, value, tb_text: str) -> str | None:
    try:
        from datetime import datetime

        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        logs = _log_dir()
        ts_path = os.path.join(logs, f"error-{ts}.log")
        latest_path = os.path.join(logs, "error.log")
        line1 = f"[{ts}] {getattr(exctype, '__name__', str(exctype))}: {value}\n"
        for path in (ts_path, latest_path):
            try:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(line1)
                    f.write((tb_text or "").rstrip() + "\n")
            except Exception:
                pass
        return ts_path
    except Exception:
        return None


# Global exception handler: write error to file and show dialog instead of hard crash
def _install_exception_handler():
    def _hook(exctype, value, tb):
        try:
            import traceback

            msg = "".join(traceback.format_exception(exctype, value, tb))
            log_path = _write_crash_log(exctype, value, msg)
            try:
                from PyQt6.QtWidgets import QMessageBox

                app = QApplication.instance() or QApplication(sys.argv)
                box = QMessageBox()
                box.setIcon(QMessageBox.Icon.Critical)
                box.setWindowTitle("Unexpected Error")
                summary = f"{getattr(exctype, '__name__', str(exctype))}: {value}"
                box.setText(f"{summary}\n\nLog: {log_path}" if log_path else summary)
                box.setDetailedText(msg)

                box.exec()
            except Exception:
                pass
        finally:
            sys.__excepthook__(exctype, value, tb)

    sys.excepthook = _hook

    try:
        import threading, traceback

        def _thread_hook(args):
            msg = "".join(
                traceback.format_exception(
                    args.exc_type, args.exc_value, args.exc_traceback
                )
            )
            _write_crash_log(args.exc_type, args.exc_value, msg)

        threading.excepthook = _thread_hook
    except Exception:
        pass

    try:
        import traceback

        def _unraisable_hook(unraisable):
            exctype = type(unraisable.exc_value)
            msg = "".join(
                traceback.format_exception(
                    exctype, unraisable.exc_value, unraisable.exc_traceback
                )
            )
            _write_crash_log(exctype, unraisable.exc_value, msg)

        sys.unraisablehook = _unraisable_hook
    except Exception:
        pass

    try:
        from PyQt6.QtCore import qInstallMessageHandler, QtMsgType

        def _qt_msg_handler(msg_type, context, message):
            level = {
                QtMsgType.QtDebugMsg: "QtDebug",
                QtMsgType.QtInfoMsg: "QtInfo",
                QtMsgType.QtWarningMsg: "QtWarning",
                QtMsgType.QtCriticalMsg: "QtCritical",
                QtMsgType.QtFatalMsg: "QtFatal",
            }.get(msg_type, "QtLog")
            try:
                ctx = f"{getattr(context, 'file', '?')}:{getattr(context, 'line', 0)} ({getattr(context, 'function', '')})"
            except Exception:
                ctx = ""
            text = f"{level}: {message}\n{ctx}".strip()
            _write_crash_log("QtMessage", level, text)

        qInstallMessageHandler(_qt_msg_handler)
    except Exception as e:
        _write_crash_log("QtMsgInstallError", e, "Failed to install Qt message handler")


# Redirect stdout/stderr to logs in GUI onefile builds (no console)
class _LogStream:
    def write(self, s: str):
        if not s:
            return
        try:
            with open(
                os.path.join(_log_dir(), "error.log"), "a", encoding="utf-8"
            ) as f:
                f.write(s)
        except Exception:
            pass

    def flush(self):
        pass


_install_exception_handler()
_ = _log_dir()
if getattr(sys, "frozen", False):
    try:
        sys.stderr = _LogStream()
        sys.stdout = _LogStream()
    except Exception:
        pass

# CHANGED: also import SETTINGS_DIR for user-writable path
from core.settings import SettingsManager, AppSettings, SETTINGS_DIR


from core.ffmpeg_manager import FfmpegInstaller, ensure_ffmpeg_in_path
from core.update import YtDlpUpdateWorker, AppUpdateWorker
from core.yt_manager import InfoFetcher  # kept
from ui.style import StyleManager
from ui.stepper import Stepper
from ui.toast import ToastManager
from widgets.step1_link import Step1LinkWidget
from widgets.step3_quality import Step3QualityWidget
from widgets.step4_downloads import Step4DownloadsWidget
from widgets.settings_page import SettingsPage


def _read_version_from_file() -> str:
    try:
        ver_path = os.path.join(_app_dir(), "version.txt")
        if os.path.exists(ver_path):
            with open(ver_path, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception:
        pass
    return ""


APP_VERSION = _read_version_from_file() or "Unknown"
APP_REPO = "noneeeeeeeeeee/YoutubeConverter"


# Safe QApplication subclass to catch exceptions raised in Qt event handlers
class CrashSafeApplication(QApplication):
    def notify(self, receiver, event):
        try:
            return super().notify(receiver, event)
        except Exception as e:
            import traceback

            msg = traceback.format_exc()
            _write_crash_log(type(e), e, msg)
            try:
                from PyQt6.QtWidgets import QMessageBox

                box = QMessageBox()
                box.setIcon(QMessageBox.Icon.Critical)
                box.setWindowTitle("Unexpected Error")
                box.setText(str(e))
                box.setDetailedText(msg)
                box.exec()
            except Exception:
                pass
            return False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"YouTube Converter - {APP_VERSION}")
        self.setMinimumSize(1024, 640)
        self.settings_mgr = SettingsManager()
        self.settings: AppSettings = self.settings_mgr.load()
        self._migrate_settings()

        self.style_mgr = StyleManager(self.settings.ui.accent_color_hex)
        self.setStyleSheet(self.style_mgr.qss())
        self.toast = ToastManager(self)

        # Track dependency state
        self._deps_installing_ff = False
        self._deps_installing_ytdlp = False
        self._init_dialog: QProgressDialog | None = None
        self._init_ops = 0

        self.sidebar = self._build_sidebar()
        self.stepper = Stepper()
        self.stack = QStackedWidget()
        self._build_pages()

        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self.sidebar)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(8)
        right_layout.addWidget(self.stepper)
        right_layout.addWidget(self.stack, 1)
        root_layout.addWidget(right, 1)

        self.setCentralWidget(root)

        # Signals wiring
        self._wire_signals()

        # FFmpeg ensure
        self._ensure_ffmpeg()
        self._ensure_ytdlp()

        # yt-dlp auto update
        if self.settings.ytdlp.auto_update:
            self._check_ytdlp_updates(startup=True)

        # App auto update on launch or check-and-prompt (mutually exclusive)
        if self.settings.app.auto_update:
            self._check_app_updates(check_only=False, prompt_on_available=False)
        elif getattr(self.settings.app, "check_on_launch", False):
            self._check_app_updates(check_only=True, prompt_on_available=True)

        self._refresh_stepper_titles()

        self._bg_fetcher = None

    def _build_sidebar(self) -> QWidget:
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(64)
        lay = QVBoxLayout(side)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        self.btn_home = QPushButton("🏠")
        self.btn_home.setToolTip("Home")
        self.btn_home.setObjectName("IconButton")
        self.btn_home.setFixedSize(48, 48)
        # Remove focus outline on icon buttons
        self.btn_home.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.btn_settings = QPushButton("⚙️")
        self.btn_settings.setToolTip("Settings")
        self.btn_settings.setObjectName("IconButton")
        self.btn_settings.setFixedSize(48, 48)
        self.btn_settings.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        lay.addWidget(self.btn_home)
        lay.addWidget(self.btn_settings)
        lay.addStretch(1)
        return side

    def _build_pages(self):
        self.page_flow = QWidget()
        flow_layout = QVBoxLayout(self.page_flow)
        flow_layout.setContentsMargins(0, 0, 0, 0)
        flow_layout.setSpacing(0)

        self.step1 = Step1LinkWidget(self.settings)
        self.step3 = Step3QualityWidget(self.settings)
        self.step4 = Step4DownloadsWidget(self.settings)

        self.flow_stack = QStackedWidget()
        self.flow_stack.addWidget(self.step1)
        self.flow_stack.addWidget(self.step3)
        self.flow_stack.addWidget(self.step4)

        flow_layout.addWidget(self.flow_stack)

        # Settings page
        self.settings_page = SettingsPage(self.settings)  # inner widget

        # Make settings scrollable
        self.settings_scroll = QScrollArea()
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setObjectName("SettingsScrollArea")
        self.settings_scroll.setWidget(self.settings_page)
        # Flatten look: remove border/frame, keep scrollbar
        self.settings_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.settings_scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
        )

        self.stack.addWidget(self.page_flow)
        self.stack.addWidget(self.settings_scroll)

    def _wire_signals(self):
        self.btn_home.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.btn_settings.clicked.connect(lambda: self.stack.setCurrentIndex(1))

        # Step 1
        self.step1.urlDetected.connect(lambda _: self._refresh_stepper_titles())
        self.step1.requestAdvance.connect(self._advance_single_from_step1)
        self.step1.selectionConfirmed.connect(self._advance_multi_from_step1)

        # Step 2
        self.step3.qualityConfirmed.connect(self._advance_from_step3)
        self.step3.backRequested.connect(
            lambda: (self.flow_stack.setCurrentIndex(0), self.stepper.set_current(0))
        )

        # Step 3
        self.step4.allFinished.connect(self._on_downloads_finished)
        self.step4.backRequested.connect(
            lambda: (self.flow_stack.setCurrentIndex(1), self.stepper.set_current(1))
        )

        # Settings page signals (connect on inner widget)
        self.settings_page.changed.connect(self._settings_changed)
        self.settings_page.accentPickRequested.connect(self._pick_accent)
        self.settings_page.checkYtDlpRequested.connect(self._check_ytdlp_updates)
        self.settings_page.checkAppCheckOnlyRequested.connect(
            lambda: self._check_app_updates(check_only=True, prompt_on_available=True)
        )

    def _refresh_stepper_titles(self):
        self.stepper.set_steps(["Select", "Quality", "Download"])
        self.stepper.set_current(0)

    def _on_url_detected(self, info: Dict):
        is_playlist = info.get("_type") == "playlist" or info.get("entries") is not None
        self._refresh_stepper_titles()

    def _advance_single_from_step1(self, payload: Dict):
        # Gate advancing until deps are ready
        if not self._deps_ready():
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.information(
                self,
                "Please wait",
                "Installing required tools (FFmpeg/yt-dlp). Try again when finished.",
            )
            return

        info = payload.get("info") or {}
        if not info:
            return
        # If already on downloads page, do not go back to Step 2
        if self.flow_stack.currentIndex() == 2:
            url = payload.get("url") or info.get("webpage_url") or info.get("url")
            if not url:
                return
            # Fetch full metadata before adding
            self.toast.show("Fetching video info...")
            self._bg_fetcher = InfoFetcher(url)

            def _ok(meta):
                # Build default selection (use user's defaults; quality best)
                kind = self.settings.defaults.kind or "audio"
                fmt = self.settings.defaults.format if kind == "audio" else "mp4"
                selection = {
                    "items": [meta],
                    "kind": kind,
                    "format": fmt,
                    "quality": "best",
                }
                self.step4.configure(selection, self.settings)
                self._toast("Added to downloads.")

            def _fail(err):
                self._toast(f"Failed to fetch info: {err}")

            self._bg_fetcher.finished_ok.connect(_ok)
            self._bg_fetcher.finished_fail.connect(_fail)
            self._bg_fetcher.start()
            return

        url = payload.get("url") or info.get("webpage_url") or info.get("url")
        if url and not info.get("formats"):
            self._toast("Fetching video info...")
            self._bg_fetcher = InfoFetcher(url)

            def _ok(meta):
                self.step3.set_items([meta])
                self.flow_stack.setCurrentIndex(1)
                self.stepper.set_current(1)

            def _fail(_err):
                self.step3.set_items([info])
                self.flow_stack.setCurrentIndex(1)
                self.stepper.set_current(1)

            self._bg_fetcher.finished_ok.connect(_ok)
            self._bg_fetcher.finished_fail.connect(_fail)
            self._bg_fetcher.start()
            return

        # Existing path when formats are already present
        self.step3.set_items([info])
        self.flow_stack.setCurrentIndex(1)
        self.stepper.set_current(1)

    def _advance_multi_from_step1(self, items: List[Dict]):
        if not items:
            return
        # Gate advancing until deps are ready
        if not self._deps_ready():
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.information(
                self,
                "Please wait",
                "Installing required tools (FFmpeg/yt-dlp). Try again when finished.",
            )
            return
        # If only one item was selected in multi mode, use single-video path
        if len(items) == 1:
            s = items[0] or {}
            self._advance_single_from_step1(
                {"url": s.get("webpage_url") or s.get("url"), "info": s}
            )
            return
        self.step3.set_items(items)
        self.flow_stack.setCurrentIndex(1)
        self.stepper.set_current(1)

    def _advance_from_step3(self, selection: Dict):
        items = selection.get("items", [])
        if not items:
            return
        self.step4.configure(selection, self.settings)
        self.flow_stack.setCurrentIndex(2)
        self.stepper.set_current(2)

    def _on_downloads_finished(self):
        # Always reset the app to a clean state after downloads
        self.step1.reset()
        try:
            self.step4.reset()
        except Exception:
            pass
        self.flow_stack.setCurrentIndex(0)
        self.stepper.set_current(0)
        self._toast("Downloads finished.")

    def _pick_accent(self):
        from PyQt6.QtWidgets import QColorDialog

        c = QColorDialog.getColor()
        if c.isValid():
            self.settings.ui.accent_color_hex = c.name()
            self.setStyleSheet(self.style_mgr.with_accent(c.name()))
            self._settings_changed()
            self._toast(f"Accent changed to {c.name()}")

    def _settings_changed(self):
        # Persist changes immediately using SettingsPage
        self.settings_page.apply_to(self.settings)
        self.settings_mgr.save(self.settings)

    # --- Dependencies gating ---
    def _ffmpeg_ready(self) -> bool:
        try:
            import shutil
            from core.ffmpeg_manager import FF_EXE

            return os.path.exists(FF_EXE) or (shutil.which("ffmpeg") is not None)
        except Exception:
            return False

    def _ytdlp_ready(self) -> bool:
        try:
            from core.update import YTDLP_EXE

            return os.path.exists(YTDLP_EXE)
        except Exception:
            return False

    def _deps_ready(self) -> bool:
        return (
            self._ffmpeg_ready()
            and self._ytdlp_ready()
            and not (self._deps_installing_ff or self._deps_installing_ytdlp)
        )

    def _ensure_ffmpeg(self):
        from core.ffmpeg_manager import FfmpegInstaller, ensure_ffmpeg_in_path

        ok = ensure_ffmpeg_in_path()
        if ok:
            return
        self._deps_installing_ff = True
        try:
            self.step1.set_next_enabled(False, "Installing FFmpeg...")
        except Exception:
            pass
        self._begin_init("Installing FFmpeg...")
        self._toast("FFmpeg not found. Downloading...")
        self.ff_thread = FfmpegInstaller(self)
        self.ff_thread.progress.connect(
            lambda p: (
                self._toast(f"Downloading FFmpeg... {p}%"),
                self._update_init(f"Downloading FFmpeg... {p}%"),
            )
        )

        def _ff_ok(_path: str):
            self._deps_installing_ff = False
            self._toast("FFmpeg ready")
            self._end_init()
            try:
                self.step1.set_next_enabled(True, "")
            except Exception:
                pass

        def _ff_fail(err: str):
            self._deps_installing_ff = False
            self._toast(f"FFmpeg install failed: {err}")
            self._end_init()

        self.ff_thread.finished_ok.connect(_ff_ok)
        self.ff_thread.finished_fail.connect(_ff_fail)
        self.ff_thread.start()

    def _ensure_ytdlp(self):
        # If no yt-dlp binary exists, fetch it. While installing, disable Next.
        from core.update import YtDlpUpdateWorker, YTDLP_EXE

        if os.path.exists(YTDLP_EXE):
            return
        self._deps_installing_ytdlp = True
        try:
            self.step1.set_next_enabled(False, "Installing yt-dlp...")
        except Exception:
            pass
        self._begin_init("Installing yt-dlp...")
        self._toast("Installing yt-dlp...")
        self.yt_thread = YtDlpUpdateWorker(
            branch=self.settings.ytdlp.branch, check_only=False
        )

        def _status(msg: str):
            self._toast(msg)
            self._update_init(msg)

        def _after():
            # This worker only emits status; verify presence and re-enable Next
            self._deps_installing_ytdlp = False
            ready = False
            try:
                from core.update import YTDLP_EXE

                ready = os.path.exists(YTDLP_EXE)
            except Exception:
                pass
            self._end_init()
            try:
                self.step1.set_next_enabled(
                    bool(ready), "" if ready else "yt-dlp install failed"
                )
            except Exception:
                pass

        self.yt_thread.status.connect(_status)
        self.yt_thread.finished.connect(_after)
        self.yt_thread.start()

    def _check_ytdlp_updates(self, startup: bool = False):
        if startup:
            self._begin_init("Checking for yt-dlp updates...")
        self._toast("Checking for yt-dlp updates...")
        self.yt_thread = YtDlpUpdateWorker(self.settings.ytdlp.branch, check_only=True)
        self.yt_thread.status.connect(
            lambda s: (self._toast(s), self._update_init(s) if startup else None)
        )
        if self.settings.ytdlp.auto_update:
            self.yt_thread.check_only = False
        self.yt_thread.finished.connect(lambda: (self._end_init() if startup else None))
        self.yt_thread.start()

    def _show_update_prompt(
        self, remote_ver: str, local_ver: str, changelog_md: str | None
    ) -> bool:
        # Win11-like, keep native border/title
        dlg = QDialog(self)
        dlg.setWindowTitle("Update Available")
        dlg.setModal(True)

        accent = self.settings.ui.accent_color_hex or "#F28C28"

        root = QVBoxLayout(dlg)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        # Header: versions
        header = QHBoxLayout()
        header.setSpacing(10)

        lhs = QVBoxLayout()
        lhs.setSpacing(2)
        lbl_cur = QLabel(f"Current version: {local_ver or 'Unknown'}")
        lbl_new = QLabel(f"Updating to: {remote_ver or 'Unknown'}")
        lbl_new.setStyleSheet(f"color: {accent}; font-weight: 800;")
        lhs.addWidget(lbl_cur)
        lhs.addWidget(lbl_new)
        header.addLayout(lhs, 1)

        root.addLayout(header)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        root.addWidget(sep)

        # Changelog area with markdown support
        lbl_changes = QLabel("Changelog")
        lbl_changes.setStyleSheet(f"font-weight: 800; font-size: 25px;")
        root.addWidget(lbl_changes)

        view = QTextBrowser()
        view.setOpenExternalLinks(True)
        view.setStyleSheet(
            "QTextBrowser { background: #1e1f22; border: 1px solid #34353b; border-radius: 8px; padding: 8px; }"
        )
        text = changelog_md or "_No changelog provided._"
        try:
            view.setMarkdown(text)
        except Exception:
            view.setPlainText(text)
        view.setMinimumSize(520, 280)
        root.addWidget(view, 1)

        # Buttons
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.No | QDialogButtonBox.StandardButton.Yes
        )
        btn_update = btns.button(QDialogButtonBox.StandardButton.Yes)
        btn_update.setText("Update now")
        btn_later = btns.button(QDialogButtonBox.StandardButton.No)
        btn_later.setText("Later")

        for b in (btn_update, btn_later):
            b.setStyleSheet(
                f"QPushButton {{ background: #2a2b30; border: 1px solid #33343a; border-radius: 8px; padding: 6px 12px; }}"
                f"QPushButton:hover {{ border-color: {accent}; }}"
            )
        btn_update.setStyleSheet(
            f"QPushButton {{ background: {accent}; color: #ffffff; border: 1px solid {accent}; border-radius: 8px; padding: 6px 12px; }}"
            f"QPushButton:hover {{ filter: brightness(1.05); }}"
        )

        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        root.addWidget(btns)

        return dlg.exec() == QDialog.DialogCode.Accepted

    def _check_app_updates(
        self,
        check_only: bool = False,
        prompt_on_available: bool = False,
        force_update: bool = False,
    ):
        do_update = (not check_only) and (self.settings.app.auto_update or force_update)
        channel = self.settings.app.channel
        self._toast("Checking app updates...")
        self.app_up_thread = AppUpdateWorker(APP_REPO, channel, APP_VERSION, do_update)
        self.app_up_thread.status.connect(self._toast)

        if prompt_on_available:

            def _on_available_details(remote: str, local: str, body_md: str):
                if self._show_update_prompt(remote, local, body_md or ""):
                    self._check_app_updates(
                        check_only=False, prompt_on_available=False, force_update=True
                    )

            # Subscribe only to the detailed signal to avoid double prompts
            self.app_up_thread.availableDetails.connect(_on_available_details)

        def _after(updated: bool):
            if updated:
                # Apply pending update with elevation (if needed), then restart
                root = _app_dir()
                staging = os.path.join(root, "_update_staging")
                if os.path.isdir(staging):
                    pid = os.getpid()
                    exe = sys.executable
                    ps_cmd = (
                        f"$pid={pid};"
                        f"Start-Process -Verb RunAs powershell -ArgumentList "
                        f"'-NoProfile','-ExecutionPolicy','Bypass','-Command',"
                        f'"Wait-Process -Id $pid; '
                        f"Copy-Item -Path '{staging}\\*' -Destination '{root}' -Recurse -Force; "
                        f"Remove-Item -Path '{staging}' -Recurse -Force; "
                        f"Start-Process -FilePath '{exe}'\""
                    )
                    try:
                        import subprocess

                        subprocess.Popen(
                            ["powershell", "-NoProfile", "-Command", ps_cmd],
                            shell=False,
                        )
                    except Exception:
                        try:
                            import shutil

                            for name in os.listdir(staging):
                                src = os.path.join(staging, name)
                                dst = os.path.join(root, name)
                                if os.path.isdir(src):
                                    shutil.copytree(src, dst, dirs_exist_ok=True)
                                else:
                                    shutil.copy2(src, dst)
                            shutil.rmtree(staging, ignore_errors=True)
                            subprocess.Popen([exe])
                        except Exception:
                            pass
                    # Terminate current process to allow replacement
                    QApplication.quit()
                    return

        self.app_up_thread.updated.connect(_after)
        self.app_up_thread.start()

    def _back_from_step2(self):
        self.flow_stack.setCurrentIndex(0)
        self.stepper.set_current(0)

    def _back_from_step3(self):
        is_playlist = len(self.stepper._labels) == 4
        self.flow_stack.setCurrentIndex(1 if is_playlist else 0)
        self.stepper.set_current(1 if is_playlist else 0)

    def _back_from_step4(self):
        self.flow_stack.setCurrentIndex(2)
        is_playlist = len(self.stepper._labels) == 4
        self.stepper.set_current(2 if is_playlist else 1)

    def _toast(self, msg: str):
        try:
            if self.isMinimized() or not self.isActiveWindow():
                return
            self.toast.show(msg)
        except Exception:
            pass

    def _migrate_settings(self):
        try:
            ui = self.settings.ui
            app = self.settings.app
            # Ensure unified flag exists (legacy mapping handled in SettingsManager.load)
            if not hasattr(ui, "auto_clear_on_success"):
                setattr(ui, "auto_clear_on_success", True)
            if not hasattr(app, "check_on_launch"):
                setattr(app, "check_on_launch", False)
            self.settings_mgr.save(self.settings)
        except Exception:
            pass

    def _begin_init(self, msg: str):
        try:
            self._init_ops += 1
            if self._init_dialog is None:
                d = QProgressDialog(self)
                d.setWindowTitle("Initializing")
                d.setLabelText(msg or "Please wait…")
                d.setRange(0, 0)  # busy
                d.setCancelButton(None)
                d.setModal(True)
                d.setMinimumWidth(360)
                self._init_dialog = d
                d.show()
            else:
                self._init_dialog.setLabelText(msg or "Please wait…")
        except Exception:
            pass

    def _update_init(self, msg: str):
        try:
            if self._init_dialog:
                self._init_dialog.setLabelText(msg or "Please wait…")
        except Exception:
            pass

    def _end_init(self):
        try:
            self._init_ops = max(0, self._init_ops - 1)
            if self._init_ops == 0 and self._init_dialog:
                self._init_dialog.hide()
                self._init_dialog.deleteLater()
                self._init_dialog = None
        except Exception:
            pass


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = CrashSafeApplication(sys.argv)
    try:
        if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
            app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
        if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
            app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
    except Exception:
        pass
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
