"""Dialog for handling file conflicts during downloads."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QFrame,
)


class FileConflictDialog(QDialog):
    """Dialog shown when files already exist in the download directory."""

    def __init__(self, conflicts: list, parent=None):
        """
        Initialize the file conflict dialog.

        Args:
            conflicts: List of dicts with 'title' and 'path' keys for conflicting files
            parent: Parent widget
        """
        super().__init__(parent)
        self.conflicts = conflicts
        self.action = None  # Will be 'replace', 'skip', 'replace_all', 'skip_all'

        self.setWindowTitle("Files Already Exist")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Title
        title = QLabel("File Conflicts Detected")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # Description
        desc = QLabel(
            f"{len(conflicts)} file(s) already exist in the download location. "
            "How would you like to proceed?"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # List of conflicting files
        list_label = QLabel("Conflicting files:")
        list_label.setStyleSheet("font-weight: 600; margin-top: 8px;")
        layout.addWidget(list_label)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.list_widget.setStyleSheet(
            """
            QListWidget {
                background: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin: 2px;
            }
        """
        )

        for conflict in conflicts:
            title = conflict.get("title", "Unknown")
            path = conflict.get("path", "")
            item = QListWidgetItem(f"📄 {title}")
            if path:
                item.setToolTip(f"Path: {path}")
            self.list_widget.addItem(item)

        layout.addWidget(self.list_widget, 1)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        # Action buttons
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)

        # Single file actions
        single_row = QHBoxLayout()
        single_row.setSpacing(8)

        btn_replace = QPushButton("Replace")
        btn_replace.setToolTip("Replace this file with the new download")
        btn_replace.clicked.connect(lambda: self._set_action("replace"))
        btn_replace.setStyleSheet(
            """
            QPushButton {
                padding: 10px 20px;
                font-size: 13px;
                border-radius: 6px;
                background: #2196F3;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background: #1976D2;
            }
        """
        )
        single_row.addWidget(btn_replace)

        btn_skip = QPushButton("Skip")
        btn_skip.setToolTip("Skip downloading this file")
        btn_skip.clicked.connect(lambda: self._set_action("skip"))
        btn_skip.setStyleSheet(
            """
            QPushButton {
                padding: 10px 20px;
                font-size: 13px;
                border-radius: 6px;
                background: #757575;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background: #616161;
            }
        """
        )
        single_row.addWidget(btn_skip)

        btn_layout.addLayout(single_row)

        # Batch actions (only show if multiple conflicts)
        if len(conflicts) > 1:
            batch_row = QHBoxLayout()
            batch_row.setSpacing(8)

            btn_replace_all = QPushButton("Replace All")
            btn_replace_all.setToolTip("Replace all conflicting files")
            btn_replace_all.clicked.connect(lambda: self._set_action("replace_all"))
            btn_replace_all.setStyleSheet(
                """
                QPushButton {
                    padding: 10px 20px;
                    font-size: 13px;
                    border-radius: 6px;
                    background: #4CAF50;
                    color: white;
                    border: none;
                }
                QPushButton:hover {
                    background: #388E3C;
                }
            """
            )
            batch_row.addWidget(btn_replace_all)

            btn_skip_all = QPushButton("Skip All")
            btn_skip_all.setToolTip("Skip all conflicting files")
            btn_skip_all.clicked.connect(lambda: self._set_action("skip_all"))
            btn_skip_all.setStyleSheet(
                """
                QPushButton {
                    padding: 10px 20px;
                    font-size: 13px;
                    border-radius: 6px;
                    background: #9E9E9E;
                    color: white;
                    border: none;
                }
                QPushButton:hover {
                    background: #757575;
                }
            """
            )
            batch_row.addWidget(btn_skip_all)

            btn_layout.addLayout(batch_row)

        layout.addLayout(btn_layout)

    def _set_action(self, action: str):
        """Set the chosen action and close the dialog."""
        self.action = action
        self.accept()

    def get_action(self) -> str:
        """Return the action chosen by the user."""
        return self.action
