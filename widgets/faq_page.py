from __future__ import annotations
from dataclasses import dataclass
from typing import List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QComboBox,
)


@dataclass
class FaqEntry:
    category: str
    question: str
    answer: str


class FaqPage(QWidget):
    """Simple searchable FAQ page with category filter and results list."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: List[FaqEntry] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(8)

        header = QLabel("Help & FAQ")
        header.setStyleSheet("font-size: 20px; font-weight: 600;")
        root.addWidget(header)

        controls = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search questions…")
        self.cmb_category = QComboBox()
        self.cmb_category.addItem("All Categories")
        controls.addWidget(QLabel("Filter:"))
        controls.addWidget(self.cmb_category)
        controls.addStretch(1)
        controls.addWidget(self.txt_search, 2)
        root.addLayout(controls)

        self.list_results = QListWidget()
        self.list_results.setMinimumHeight(160)
        self.txt_answer = QTextEdit()
        self.txt_answer.setReadOnly(True)
        self.txt_answer.setMinimumHeight(220)
        root.addWidget(self.list_results, 1)
        root.addWidget(self.txt_answer, 2)

        # Wire events
        self.txt_search.textChanged.connect(self._refresh)
        self.cmb_category.currentIndexChanged.connect(self._refresh)
        self.list_results.currentItemChanged.connect(self._show_selected)

        # Load defaults
        self._load_default_entries()
        self._refresh()

    def _load_default_entries(self):
        self._entries = [
            FaqEntry(
                "Downloads",
                "Can the app resume partial downloads?",
                ("Yes it can, try it out! " "It may be buggy still."),
            ),
            FaqEntry(
                "Downloads",
                "How do I choose audio quality (e.g., 160k)?",
                (
                    "In Step 3 (Quality), pick a target like 'best' or an approximate bitrate (e.g., 160k). "
                    "The app selects the closest available stream."
                ),
            ),
            FaqEntry(
                "Downloads",
                "Downloads are very slow or keep failing",
                (
                    "This can be caused by:\n"
                    "• Network congestion or unstable connection\n"
                    "• YouTube rate limiting (try waiting and retrying)\n"
                    "• Antivirus blocking the download\n"
                    "• Disk space running low\n"
                    "• Proxy/VPN interfering with connection\n\n"
                    "Try changing your network, disabling VPN temporarily, or clearing browser cache."
                ),
            ),
            FaqEntry(
                "Downloads",
                "Video/audio is out of sync after download",
                (
                    "This can happen with certain video formats. Try:\n"
                    "• Selecting a different quality option\n"
                    "• Using 'best' quality instead of specific resolution\n"
                    "• For audio-only, choose a direct audio format\n"
                    "• Check if the original video has sync issues"
                ),
            ),
            FaqEntry(
                "Downloads",
                "Getting 'Video unavailable' or 'Private video' errors",
                (
                    "This occurs when:\n"
                    "• Video is private, unlisted, or deleted\n"
                    "• Video is geo-blocked in your region\n"
                    "• Age-restricted content requiring sign-in\n"
                    "• Copyright takedown\n\n"
                    "Try accessing the video in your browser first to confirm availability."
                ),
            ),
            FaqEntry(
                "Updates",
                "What do the update schedules mean?",
                (
                    "Off disables checks. Every Launch checks on startup. Daily/Weekly/Monthly check based on the last successful check time."
                ),
            ),
            FaqEntry(
                "Updates",
                "What is the difference between App updates and yt-dlp updates?",
                (
                    "App updates refresh this application. yt-dlp updates refresh the bundled downloader binary. They can be scheduled independently."
                ),
            ),
            FaqEntry(
                "Updates",
                "Update failed or app won't restart after update",
                (
                    "Try these steps:\n"
                    "• Close the app completely and restart manually\n"
                    "• Check if antivirus is blocking the update\n"
                    "• Run as administrator if on Windows\n"
                    "• Download fresh copy from official source\n"
                    "• Export logs before updating for troubleshooting"
                ),
            ),
            FaqEntry(
                "SponsorBlock",
                "How does SponsorBlock removal work?",
                (
                    "When enabled, segments (e.g., sponsor/intro/outro) are removed using the community-maintained database. "
                    "You can choose which categories to remove."
                ),
            ),
            FaqEntry(
                "SponsorBlock",
                "SponsorBlock isn't removing segments",
                (
                    "This can happen if:\n"
                    "• Video is too new (segments not yet submitted)\n"
                    "• No community submissions for this video\n"
                    "• Network issues accessing SponsorBlock API\n"
                    "• Selected categories don't match available segments\n\n"
                    "SponsorBlock relies on community contributions, so newer or less popular videos may not have segments."
                ),
            ),
            FaqEntry(
                "Troubleshooting",
                "I get a network or permission error—what should I try?",
                (
                    "Check your connection, try again, or export logs from Settings → Maintenance and share the zip for support."
                ),
            ),
            FaqEntry(
                "Troubleshooting",
                "Where are the exported log files saved?",
                (
                    "Log zip files are saved to:\n"
                    "Windows: %APPDATA%\\YoutubeConverter\\logs\\logs-YYYYMMDD-HHMMSS.zip\n"
                    "Example: C:\\Users\\YourName\\AppData\\Roaming\\YoutubeConverter\\logs\\logs-20250913-143022.zip\n\n"
                    "You can find this folder by:\n"
                    "• Pressing Win+R, typing %APPDATA%\\YoutubeConverter\\logs and hitting Enter\n"
                    "• The app shows the filename in a success toast after export"
                ),
            ),
            FaqEntry(
                "Troubleshooting",
                "App crashes on startup or won't open",
                (
                    "Try these solutions:\n"
                    "• Update graphics drivers\n"
                    "• Run as administrator\n"
                    "• Check Windows Event Viewer for error details\n"
                    "• Disable antivirus temporarily\n"
                    "• Clear app settings: Delete %APPDATA%\\YoutubeConverter folder\n"
                    "• Reinstall Microsoft Visual C++ Redistributables"
                ),
            ),
            FaqEntry(
                "Troubleshooting",
                "FFmpeg errors or 'Conversion failed'",
                (
                    "FFmpeg issues can occur due to:\n"
                    "• Corrupted or missing FFmpeg binary\n"
                    "• Unsupported video/audio codec\n"
                    "• File path with special characters\n"
                    "• Insufficient disk space\n"
                    "• Antivirus quarantining FFmpeg\n\n"
                    "Try reinstalling the app or adding FFmpeg folder to antivirus exclusions."
                ),
            ),
            FaqEntry(
                "Troubleshooting",
                "High CPU/memory usage during downloads",
                (
                    "This is normal for video processing, but can be reduced by:\n"
                    "• Downloading fewer concurrent streams\n"
                    "• Choosing lower quality options\n"
                    "• Closing other applications\n"
                    "• Using audio-only format for music\n"
                    "• Avoiding video conversion when possible"
                ),
            ),
            FaqEntry(
                "Troubleshooting",
                "App interface appears corrupted or unreadable",
                (
                    "Display issues can be fixed by:\n"
                    "• Changing theme in Settings → Appearance\n"
                    "• Adjusting Windows display scaling (100%, 125%, 150%)\n"
                    "• Updating graphics drivers\n"
                    "• Try different color theme (Dark/Light/OLED)\n"
                    "• Reset app settings if problem persists"
                ),
            ),
            FaqEntry(
                "File Management",
                "Where are downloaded files saved?",
                (
                    "By default, files are saved to your Downloads folder. You can change the destination in Settings or during the download process. "
                    "The app remembers your last used location."
                ),
            ),
            FaqEntry(
                "File Management",
                "How to organize downloads by playlist/channel?",
                (
                    "The app can create subfolders based on:\n"
                    "• Playlist name\n"
                    "• Channel name\n"
                    "• Upload date\n\n"
                    "Configure this in Settings → Downloads → Folder structure options."
                ),
            ),
            FaqEntry(
                "File Management",
                "Downloaded file has wrong extension or won't play",
                (
                    "This can happen if:\n"
                    "• Codec not supported by your media player\n"
                    "• File corrupted during download\n"
                    "• Wrong format selected\n\n"
                    "Try:\n"
                    "• Using VLC media player (supports most formats)\n"
                    "• Re-downloading with different quality\n"
                    "• Converting to MP4/MP3 format"
                ),
            ),
            FaqEntry(
                "Performance",
                "How to speed up downloads?",
                (
                    "To optimize download speed:\n"
                    "• Use wired internet connection\n"
                    "• Close bandwidth-heavy applications\n"
                    "• Select appropriate quality (higher = slower)\n"
                    "• Download during off-peak hours\n"
                    "• Ensure sufficient free disk space\n"
                    "• Consider downloading audio-only for music"
                ),
            ),
            FaqEntry(
                "Accessibility",
                "Is there a high-contrast theme?",
                (
                    "Yes. Choose 'Dark' or 'OLED' themes in Settings → Appearance. The UI aims for improved contrast and readable controls."
                ),
            ),
            FaqEntry(
                "Accessibility",
                "Keyboard shortcuts and navigation",
                (
                    "The app supports:\n"
                    "• Tab navigation through interface elements\n"
                    "• Enter to activate buttons\n"
                    "• Escape to close dialogs\n"
                    "• Ctrl+V to paste URLs\n"
                    "• Standard Windows accessibility features"
                ),
            ),
        ]

        # Populate categories
        cats = sorted({e.category for e in self._entries})
        for c in cats:
            self.cmb_category.addItem(c)

    def _refresh(self):
        term = (self.txt_search.text() or "").strip().lower()
        cat_idx = self.cmb_category.currentIndex()
        cat = None if cat_idx <= 0 else self.cmb_category.currentText()
        self.list_results.clear()
        for e in self._entries:
            if cat and e.category != cat:
                continue
            if (
                term
                and (term not in e.question.lower())
                and (term not in e.answer.lower())
            ):
                continue
            it = QListWidgetItem(f"[{e.category}] {e.question}")
            it.setData(Qt.ItemDataRole.UserRole, e)
            self.list_results.addItem(it)
        if self.list_results.count() > 0:
            self.list_results.setCurrentRow(0)
        else:
            self.txt_answer.setPlainText("No results.")

    def _show_selected(
        self, current: QListWidgetItem | None, _prev: QListWidgetItem | None = None
    ):
        if not current:
            self.txt_answer.clear()
            return
        e = current.data(Qt.ItemDataRole.UserRole)
        if isinstance(e, FaqEntry):
            self.txt_answer.setPlainText(e.answer)
