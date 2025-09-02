from PyQt6.QtCore import Qt, pyqtSignal, QObject, QEvent
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGroupBox,
    QFormLayout,
    QCheckBox,
    QComboBox,
    QPushButton,
    QSpinBox,
    QLabel,
    QMessageBox,
    QHBoxLayout,
)
from core.settings import AppSettings


class SettingsPage(QWidget):
    changed = pyqtSignal()
    checkYtDlpRequested = pyqtSignal()
    checkAppCheckOnlyRequested = pyqtSignal()
    accentPickRequested = pyqtSignal()
    resetDefaultsRequested = pyqtSignal()
    clearLogsRequested = pyqtSignal()  # NEW

    def __init__(self, settings: AppSettings):
        super().__init__()
        self._settings = settings
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 16, 4, 16)

        grp_note = QGroupBox("Note")
        frm_note = QFormLayout(grp_note)
        frm_note.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        frm_note.addRow(
            QLabel(
                "If program is bricked to reset, delete settings.json in %APPDATA%/Roaming/YoutubeConverter/"
            )
        )
        lay.addWidget(grp_note)

        grp_general = QGroupBox("General")
        frm_general = QFormLayout(grp_general)
        frm_general.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.btn_accent = QPushButton("Pick accent color")
        self.btn_accent.clicked.connect(self.accentPickRequested.emit)
        frm_general.addRow(
            QLabel(
                "Accent colors such as loading bars need a program restart to be updated"
            )
        )
        frm_general.addRow("Accent color", self.btn_accent)
        lay.addWidget(grp_general)

        grp_search = QGroupBox("Search")
        frm_search = QFormLayout(grp_search)
        frm_search.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.chk_auto_search_text = QCheckBox()
        self.chk_auto_search_text.setChecked(settings.ui.auto_search_text)
        frm_search.addRow("Auto search text", self.chk_auto_search_text)
        self.chk_auto_clear_success = QCheckBox()
        self.chk_auto_clear_success.setChecked(
            bool(getattr(settings.ui, "auto_clear_on_success", False))
        )
        frm_search.addRow("Auto clear input on success", self.chk_auto_clear_success)
        self.spn_search_debounce = QSpinBox()
        self.spn_search_debounce.setRange(0, 10)
        self.spn_search_debounce.setValue(
            int(getattr(settings.ui, "search_debounce_seconds", 3))
        )
        frm_search.addRow("Search debounce (s)", self.spn_search_debounce)
        lay.addWidget(grp_search)

        grp_ytdlp = QGroupBox("yt-dlp")
        frm_ytdlp = QFormLayout(grp_ytdlp)
        frm_ytdlp.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.chk_ytdlp_auto = QCheckBox()
        self.chk_ytdlp_auto.setChecked(settings.ytdlp.auto_update)
        frm_ytdlp.addRow("Auto-update yt-dlp", self.chk_ytdlp_auto)
        self.cmb_ytdlp_branch = QComboBox()
        self.cmb_ytdlp_branch.addItems(["stable", "nightly", "master"])
        self.cmb_ytdlp_branch.setCurrentText(settings.ytdlp.branch)
        frm_ytdlp.addRow("yt-dlp branch", self.cmb_ytdlp_branch)
        self.btn_ytdlp_check = QPushButton("Check yt-dlp now")
        self.btn_ytdlp_check.clicked.connect(self.checkYtDlpRequested.emit)
        frm_ytdlp.addRow("", self.btn_ytdlp_check)
        lay.addWidget(grp_ytdlp)

        grp_app = QGroupBox("App updates")
        frm_app = QFormLayout(grp_app)
        frm_app.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.cmb_app_behavior = QComboBox()
        self.cmb_app_behavior.addItems(
            [
                "Do nothing on launch",
                "Check on launch (prompt)",
                "Auto-update on launch",
            ]
        )
        if settings.app.auto_update:
            self.cmb_app_behavior.setCurrentIndex(2)
        elif getattr(settings.app, "check_on_launch", False):
            self.cmb_app_behavior.setCurrentIndex(1)
        else:
            self.cmb_app_behavior.setCurrentIndex(0)
        frm_app.addRow("On launch behavior", self.cmb_app_behavior)
        self.cmb_app_channel = QComboBox()
        self.cmb_app_channel.addItems(
            ["release", "nightly"]
        )  # disabled prelease option for now , "prerelease"
        self.cmb_app_channel.setCurrentText(settings.app.channel)
        frm_app.addRow("Update channel", self.cmb_app_channel)
        self.btn_app_check = QPushButton("Check app update")
        self.btn_app_check.clicked.connect(self.checkAppCheckOnlyRequested.emit)
        frm_app.addRow("", self.btn_app_check)
        lay.addWidget(grp_app)
        lay.addStretch(1)

        class _NoWheelFilter(QObject):
            def eventFilter(self, obj, event):
                if event.type() == QEvent.Type.Wheel:
                    return True
                return super().eventFilter(obj, event)

        self._nowheel = _NoWheelFilter(self)
        for w in (
            self.spn_search_debounce,
            self.cmb_ytdlp_branch,
            self.cmb_app_channel,
            self.cmb_app_behavior,
        ):
            w.installEventFilter(self._nowheel)

        self.btn_reset_defaults = QPushButton("Reset to Default Settings")
        self.btn_reset_defaults.setObjectName("DangerButton")
        self.btn_reset_defaults.clicked.connect(self._confirm_reset_defaults)
        lay.addWidget(self.btn_reset_defaults, 0, Qt.AlignmentFlag.AlignRight)

        self.btn_clear_logs = QPushButton("Clear All Logs")  # NEW
        self.btn_clear_logs.clicked.connect(self._on_clear_logs)
        lay.addWidget(self.btn_clear_logs, 0, Qt.AlignmentFlag.AlignRight)

        for w in (
            self.chk_auto_search_text,
            self.chk_ytdlp_auto,
            self.chk_auto_clear_success,
        ):
            w.toggled.connect(self.changed.emit)
        self.spn_search_debounce.valueChanged.connect(self.changed.emit)
        self.cmb_ytdlp_branch.currentTextChanged.connect(self.changed.emit)
        self.cmb_app_channel.currentTextChanged.connect(self.changed.emit)
        self.cmb_app_behavior.currentIndexChanged.connect(self.changed.emit)

    def _confirm_reset_defaults(self):
        if (
            QMessageBox.question(
                self,
                "Reset Settings",
                "Reset all settings to their defaults?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.resetDefaultsRequested.emit()

    def _on_clear_logs(self):
        if (
            QMessageBox.question(
                self,
                "Clear logs",
                "Delete all logs?",
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.clearLogsRequested.emit()

    def apply_to(self, settings: AppSettings):
        # UI
        settings.ui.auto_search_text = self.chk_auto_search_text.isChecked()
        settings.ui.search_debounce_seconds = int(self.spn_search_debounce.value())
        settings.ui.auto_clear_on_success = self.chk_auto_clear_success.isChecked()

        # yt-dlp
        settings.ytdlp.auto_update = self.chk_ytdlp_auto.isChecked()
        settings.ytdlp.branch = self.cmb_ytdlp_branch.currentText()

        # App updates (mapped from behavior combo)
        behavior = self.cmb_app_behavior.currentIndex()
        settings.app.auto_update = behavior == 2
        settings.app.check_on_launch = behavior == 1
        settings.app.channel = self.cmb_app_channel.currentText()
