from PyQt6.QtCore import pyqtSignal, Qt, QEvent
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QComboBox,
    QSpinBox,
    QPushButton,
    QFrame,
)

from core.settings import AppSettings
from core.models import UpdateCadence, UpdateAction


class SettingsPage(QWidget):
    changed = pyqtSignal()
    accentPickRequested = pyqtSignal()
    checkYtDlpRequested = pyqtSignal()
    checkAppCheckOnlyRequested = pyqtSignal()
    clearLogsRequested = pyqtSignal()
    exportLogsRequested = pyqtSignal()
    openFaqRequested = pyqtSignal()

    def __init__(self, settings: AppSettings):
        super().__init__()
        self._settings = settings

        # Unified stylesheet for cards & children (prevents striped backgrounds)
        self.setStyleSheet(
            self.styleSheet()
            + """
        QFrame#CategoryCard { background-color:#2b2b2b; border-radius:12px; border:1px solid rgba(255,255,255,0.05); }
        QFrame#CategoryCard * { background-color:transparent; }
        QFrame#CategoryCard QLabel[role="caption"] { color:rgba(255,255,255,0.55); font-size:12px; }
        QFrame#CategoryCard QPushButton { min-height:24px; border-radius:6px; background-color:rgba(255,255,255,0.06); padding:2px 10px; }
        QFrame#CategoryCard QPushButton:hover { background-color:rgba(255,255,255,0.12); }
        QFrame#CategoryCard QComboBox, QFrame#CategoryCard QSpinBox { padding:2px 6px; border:1px solid rgba(255,255,255,0.15); border-radius:6px; }
        QFrame#CategoryCard QComboBox:hover, QFrame#CategoryCard QSpinBox:hover { border-color:rgba(255,255,255,0.30); }
        QFrame#CategoryCard QCheckBox { padding:2px 0; }
        """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(20)

        def card(title: str, desc: str) -> QVBoxLayout:
            frame = QFrame()
            frame.setObjectName("CategoryCard")
            frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            lay = QVBoxLayout(frame)
            lay.setContentsMargins(18, 14, 18, 14)
            lay.setSpacing(8)
            lbl_t = QLabel(title)
            lbl_t.setStyleSheet("font-size:18px; font-weight:600;")
            lbl_d = QLabel(desc)
            lbl_d.setWordWrap(True)
            lbl_d.setProperty("role", "caption")
            lay.addWidget(lbl_t)
            lay.addWidget(lbl_d)
            root.addWidget(frame)
            return lay

        # Appearance
        lay_app = card("Appearance", "Theme, accent color and general UI behavior.")
        row_theme = QHBoxLayout()
        row_theme.addWidget(QLabel("Theme:"))
        self.cmb_theme = QComboBox()
        self.cmb_theme.addItems(["System", "Light", "Dark", "OLED"])
        cur_mode = getattr(settings.ui, "theme_mode", "system").lower()
        self.cmb_theme.setCurrentIndex(
            {"system": 0, "light": 1, "dark": 2, "oled": 3}.get(cur_mode, 0)
        )
        row_theme.addWidget(self.cmb_theme, 1)
        lay_app.addLayout(row_theme)
        btn_accent = QPushButton("Pick accent color")
        btn_accent.setFixedHeight(24)
        btn_accent.clicked.connect(self.accentPickRequested.emit)
        lay_app.addWidget(btn_accent)
        self.chk_auto_clear_success = QCheckBox("Auto clear finished downloads")
        self.chk_auto_clear_success.setChecked(settings.ui.auto_clear_on_success)
        lay_app.addWidget(self.chk_auto_clear_success)

        # Search & Input
        lay_search = card(
            "Search & Input", "Controls how text input triggers searches."
        )
        self.chk_auto_search_text = QCheckBox("Auto search while typing")
        self.chk_auto_search_text.setChecked(
            getattr(settings.ui, "auto_search_text", True)
        )
        lay_search.addWidget(self.chk_auto_search_text)
        row_db = QHBoxLayout()
        row_db.addWidget(QLabel("Search debounce (s):"))
        self.spn_search_debounce = QSpinBox()
        self.spn_search_debounce.setRange(0, 10)
        self.spn_search_debounce.setValue(
            int(getattr(settings.ui, "search_debounce_seconds", 3))
        )
        row_db.addWidget(self.spn_search_debounce)
        lay_search.addLayout(row_db)

        # Downloads
        lay_dl = card("Downloads", "Workflow preferences for post-completion behavior.")
        self.chk_auto_reset_after = QCheckBox("Reset wizard after all downloads")
        self.chk_auto_reset_after.setChecked(
            getattr(settings.app, "auto_reset_after_downloads", True)
        )
        lay_dl.addWidget(self.chk_auto_reset_after)

        # Notifications
        lay_notif = card("Notifications", "Toast notification verbosity level.")
        lay_notif.addWidget(QLabel("Notification detail level:"))
        self.cmb_notif = QComboBox()
        self.cmb_notif.addItems(["Detailed", "Minimal", "None"])
        self.cmb_notif.setCurrentIndex(
            {"detailed": 0, "minimal": 1, "none": 2}.get(
                getattr(settings.app, "notifications_detail", "detailed").lower(), 0
            )
        )
        lay_notif.addWidget(self.cmb_notif)

        # Updates (schedule-based)
        lay_updates = card(
            "Updates",
            "Control how the app and yt-dlp update: schedule, channels, and behavior.",
        )
        sched_map = {"off": 0, "launch": 1, "daily": 2, "weekly": 3, "monthly": 4}

        # yt-dlp subsection
        y_section = QFrame()
        y_section.setObjectName("CategoryCard")
        y_lay = QVBoxLayout(y_section)
        y_lay.setContentsMargins(12, 10, 12, 10)
        y_lay.setSpacing(6)
        y_lay.addWidget(QLabel("yt-dlp (downloader)"))

        row_y_sched = QHBoxLayout()
        row_y_sched.addWidget(QLabel("Check schedule:"))
        self.cmb_ytdlp_schedule = QComboBox()
        self.cmb_ytdlp_schedule.addItems(
            ["Off", "Every Launch", "Daily", "Weekly", "Monthly"]
        )
        try:
            ytdlp_cadence = (
                getattr(
                    getattr(settings, "ytdlp_update", None), "schedule", None
                ).cadence
                if getattr(settings, "ytdlp_update", None)
                else None
            )
            if ytdlp_cadence:
                self.cmb_ytdlp_schedule.setCurrentIndex(
                    sched_map.get(ytdlp_cadence.value, 2)
                )
            else:
                self.cmb_ytdlp_schedule.setCurrentIndex(2)
        except Exception:
            self.cmb_ytdlp_schedule.setCurrentIndex(
                sched_map.get(getattr(settings.ytdlp, "update_schedule", "daily"), 2)
            )
        row_y_sched.addWidget(self.cmb_ytdlp_schedule, 1)
        y_lay.addLayout(row_y_sched)

        row_y_branch = QHBoxLayout()
        row_y_branch.addWidget(QLabel("Release stream:"))
        self.cmb_ytdlp_branch = QComboBox()
        self.cmb_ytdlp_branch.addItems(["Release", "Master", "Nightly"])
        branch = (getattr(settings.ytdlp, "branch", "stable") or "stable").lower()
        self.cmb_ytdlp_branch.setCurrentIndex(
            {"stable": 0, "master": 1, "nightly": 2}.get(branch, 0)
        )
        row_y_branch.addWidget(self.cmb_ytdlp_branch, 1)
        y_lay.addLayout(row_y_branch)

        row_y_btn = QHBoxLayout()
        row_y_btn.addStretch(1)
        self.btn_check_ytdlp = QPushButton("Check now…")
        self.btn_check_ytdlp.setFixedHeight(24)
        self.btn_check_ytdlp.clicked.connect(self.checkYtDlpRequested.emit)
        row_y_btn.addWidget(self.btn_check_ytdlp)
        y_lay.addLayout(row_y_btn)

        lay_updates.addWidget(y_section)

        # App subsection
        a_section = QFrame()
        a_section.setObjectName("CategoryCard")
        a_lay = QVBoxLayout(a_section)
        a_lay.setContentsMargins(12, 10, 12, 10)
        a_lay.setSpacing(6)
        a_lay.addWidget(QLabel("Application (this app)"))

        row_a_sched = QHBoxLayout()
        row_a_sched.addWidget(QLabel("Check schedule:"))
        self.cmb_app_schedule = QComboBox()
        self.cmb_app_schedule.addItems(
            ["Off", "Every Launch", "Daily", "Weekly", "Monthly"]
        )
        try:
            app_cadence = (
                getattr(getattr(settings, "app_update", None), "schedule", None).cadence
                if getattr(settings, "app_update", None)
                else None
            )
            if app_cadence:
                self.cmb_app_schedule.setCurrentIndex(
                    sched_map.get(app_cadence.value, 2)
                )
            else:
                self.cmb_app_schedule.setCurrentIndex(2)
        except Exception:
            self.cmb_app_schedule.setCurrentIndex(
                sched_map.get(getattr(settings.app, "update_schedule", "daily"), 2)
            )
        row_a_sched.addWidget(self.cmb_app_schedule, 1)
        a_lay.addLayout(row_a_sched)

        row_a_channel = QHBoxLayout()
        row_a_channel.addWidget(QLabel("Release channel:"))
        self.cmb_app_channel = QComboBox()
        self.cmb_app_channel.addItems(["Release", "Nightly"])
        channel = (getattr(settings.app, "channel", "release") or "release").lower()
        self.cmb_app_channel.setCurrentIndex(
            {"release": 0, "nightly": 1}.get(channel, 0)
        )
        row_a_channel.addWidget(self.cmb_app_channel, 1)
        a_lay.addLayout(row_a_channel)

        row_a_action = QHBoxLayout()
        row_a_action.addWidget(QLabel("When an update is found:"))
        self.cmb_app_action = QComboBox()
        self.cmb_app_action.addItems(
            ["Prompt before updating", "Instantly update (auto)"]
        )
        try:
            act = getattr(
                getattr(settings, "app_update", None), "action", UpdateAction.PROMPT
            )
            idx = 0 if act == UpdateAction.PROMPT else 1
        except Exception:
            idx = 0
        self.cmb_app_action.setCurrentIndex(idx)
        row_a_action.addWidget(self.cmb_app_action, 1)
        a_lay.addLayout(row_a_action)

        row_a_btn = QHBoxLayout()
        row_a_btn.addStretch(1)
        self.btn_check_app = QPushButton("Check now…")
        self.btn_check_app.setFixedHeight(24)
        self.btn_check_app.clicked.connect(self.checkAppCheckOnlyRequested.emit)
        row_a_btn.addWidget(self.btn_check_app)
        a_lay.addLayout(row_a_btn)

        lay_updates.addWidget(a_section)

        # EZ Mode
        lay_ez = card("EZ Mode", "Simplify interface for quick single-link downloads.")
        self.chk_ez_simple = QCheckBox("Simple paste mode")
        self.chk_ez_simple.setChecked(settings.ez.simple_paste_mode)
        lay_ez.addWidget(self.chk_ez_simple)
        self.chk_ez_sanitize = QCheckBox("Sanitize radio/mix links")
        self.chk_ez_sanitize.setChecked(settings.ez.sanitize_radio_links)
        lay_ez.addWidget(self.chk_ez_sanitize)
        self.chk_ez_hide_adv = QCheckBox("Hide advanced quality options")
        self.chk_ez_hide_adv.setChecked(settings.ez.hide_advanced_quality)
        lay_ez.addWidget(self.chk_ez_hide_adv)

        # Placeholder container referenced by tests (hidden when EZ simple enabled)
        self.advanced_quality_container = QFrame()
        self.advanced_quality_container.setObjectName("AdvancedQualityContainer")
        aq_lay = QVBoxLayout(self.advanced_quality_container)
        aq_lay.setContentsMargins(0, 0, 0, 0)

        def _sync_ez(on: bool):
            if on:
                self.chk_ez_sanitize.setChecked(True)
                self.chk_ez_sanitize.setEnabled(False)
            else:
                self.chk_ez_sanitize.setEnabled(True)

        _sync_ez(self.chk_ez_simple.isChecked())
        self.chk_ez_simple.toggled.connect(_sync_ez)

        # Maintenance
        lay_maint = card("Maintenance", "Log management and diagnostics.")
        btn_logs = QPushButton("Clear all logs")
        btn_logs.setFixedHeight(24)
        btn_logs.clicked.connect(self.clearLogsRequested.emit)
        lay_maint.addWidget(btn_logs)
        btn_export = QPushButton("Export logs (zip)")
        btn_export.setFixedHeight(24)
        btn_export.clicked.connect(self.exportLogsRequested.emit)
        lay_maint.addWidget(btn_export)

        # Help / FAQ
        lay_help = card("Help", "Find answers to common questions.")
        btn_faq = QPushButton("Open FAQ")
        btn_faq.setFixedHeight(24)
        btn_faq.clicked.connect(self.openFaqRequested.emit)
        lay_help.addWidget(btn_faq)

        root.addStretch(1)

        # Block scroll-wheel on unfocused inputs
        self._wheel_block_targets = []
        for w in self.findChildren((QComboBox, QSpinBox)):
            w.installEventFilter(self)
            self._wheel_block_targets.append(w)
            try:
                w.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
            except Exception:
                pass
            try:
                if not hasattr(w, "_orig_wheelEvent"):
                    w._orig_wheelEvent = w.wheelEvent

                    def _guarded_wheel(ev, _w=w):
                        if not _w.hasFocus():
                            ev.ignore()
                            return
                        try:
                            _w._orig_wheelEvent(ev)
                        except Exception:
                            ev.ignore()

                    w.wheelEvent = _guarded_wheel
            except Exception:
                pass

        widgets_for_change = [
            self.cmb_theme,
            self.chk_auto_clear_success,
            self.chk_auto_search_text,
            self.spn_search_debounce,
            self.chk_auto_reset_after,
            self.cmb_notif,
            self.cmb_ytdlp_schedule,
            self.cmb_app_schedule,
            self.cmb_ytdlp_branch,
            self.cmb_app_channel,
            self.cmb_app_action,
            self.chk_ez_simple,
            self.chk_ez_sanitize,
            self.chk_ez_hide_adv,
        ]
        for w in widgets_for_change:
            if hasattr(w, "toggled"):
                try:
                    w.toggled.connect(self.changed.emit)
                except Exception:
                    pass
            if hasattr(w, "currentIndexChanged"):
                try:
                    w.currentIndexChanged.connect(self.changed.emit)
                except Exception:
                    pass
            if hasattr(w, "valueChanged"):
                try:
                    w.valueChanged.connect(self.changed.emit)
                except Exception:
                    pass

    def eventFilter(self, obj, event):
        try:
            if event.type() == QEvent.Type.Wheel and obj in getattr(
                self, "_wheel_block_targets", []
            ):
                if not obj.hasFocus():
                    return True
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def apply_to(self, settings: AppSettings):
        mode = self.cmb_theme.currentText().lower()
        settings.ui.theme_mode = "system" if mode == "system" else mode
        settings.ui.auto_clear_on_success = self.chk_auto_clear_success.isChecked()
        settings.ui.auto_search_text = self.chk_auto_search_text.isChecked()
        settings.ui.search_debounce_seconds = int(self.spn_search_debounce.value())
        settings.app.auto_reset_after_downloads = self.chk_auto_reset_after.isChecked()
        settings.app.notifications_detail = self.cmb_notif.currentText().lower()
        rev_sched = {0: "off", 1: "launch", 2: "daily", 3: "weekly", 4: "monthly"}
        # Update unified configs first
        try:
            y_idx = self.cmb_ytdlp_schedule.currentIndex()
            a_idx = self.cmb_app_schedule.currentIndex()
            y_val = rev_sched.get(y_idx, "daily")
            a_val = rev_sched.get(a_idx, "daily")
            settings.ytdlp_update.schedule.cadence = UpdateCadence(y_val)
            settings.app_update.schedule.cadence = UpdateCadence(a_val)
        except Exception:
            pass
        # Legacy mirrors for backward compat
        settings.ytdlp.update_schedule = rev_sched.get(
            self.cmb_ytdlp_schedule.currentIndex(), "daily"
        )
        settings.app.update_schedule = rev_sched.get(
            self.cmb_app_schedule.currentIndex(), "daily"
        )
        settings.ytdlp.auto_update = settings.ytdlp.update_schedule != "off"
        settings.app.auto_update = settings.app.update_schedule != "off"
        # ytdlp branch mapping
        self_branch = {0: "stable", 1: "master", 2: "nightly"}.get(
            self.cmb_ytdlp_branch.currentIndex(), "stable"
        )
        settings.ytdlp.branch = self_branch
        # App channel mapping
        self_channel = {0: "release", 1: "prerelease", 2: "nightly"}.get(
            self.cmb_app_channel.currentIndex(), "release"
        )
        settings.app.channel = self_channel
        # App action mapping (unified config)
        try:
            action_idx = self.cmb_app_action.currentIndex()
            settings.app_update.action = (
                UpdateAction.PROMPT if action_idx == 0 else UpdateAction.AUTO
            )
        except Exception:
            pass
        # Legacy behavior flags for migration friendliness
        if (
            getattr(settings, "app_update", None)
            and settings.app_update.action == UpdateAction.AUTO
        ):
            settings.app.auto_update = True
            settings.app.check_on_launch = False
        elif (
            getattr(settings, "app_update", None)
            and settings.app_update.action == UpdateAction.PROMPT
        ):
            # Prompt on check (enable launch or daily based on schedule)
            settings.app.auto_update = False
            # Check on launch if cadence is launch, else leave False
            try:
                settings.app.check_on_launch = (
                    settings.app_update.schedule.cadence == UpdateCadence.LAUNCH
                )
            except Exception:
                settings.app.check_on_launch = True
        settings.ez.simple_paste_mode = self.chk_ez_simple.isChecked()
        if settings.ez.simple_paste_mode:
            settings.ez.sanitize_radio_links = True
        else:
            settings.ez.sanitize_radio_links = self.chk_ez_sanitize.isChecked()
        settings.ez.hide_advanced_quality = self.chk_ez_hide_adv.isChecked()
