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
                "SponsorBlock",
                "How does SponsorBlock removal work?",
                (
                    "When enabled, segments (e.g., sponsor/intro/outro) are removed using the community-maintained database. "
                    "You can choose which categories to remove."
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
                "Accessibility",
                "Is there a high-contrast theme?",
                (
                    "Yes. Choose 'Dark' or 'OLED' themes in Settings → Appearance. The UI aims for improved contrast and readable controls."
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
