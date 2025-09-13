from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QHBoxLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal


class UpdateProgressDialog(QDialog):
    cancelRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Updating Application")
        self.setModal(True)
        self.resize(460, 160)
        lay = QVBoxLayout(self)
        self.lbl = QLabel("Checking for updates…")
        self.lbl.setWordWrap(True)
        self.bar = QProgressBar()
        self.bar.setRange(0, 0)  # indeterminate initial
        lay.addWidget(self.lbl)
        lay.addWidget(self.bar)
        row = QHBoxLayout()
        row.addStretch(1)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.cancelRequested.emit)
        row.addWidget(self.btn_cancel)
        lay.addLayout(row)

    def update_state(self, state: str, message: str):
        self.lbl.setText(message or state)
        low = (state or "").lower()
        if low in ("downloading", "verifying", "applying"):
            # keep indeterminate but could add percentage later
            self.bar.setRange(0, 0)
        elif low in ("restart_needed", "error", "canceled"):
            self.bar.setRange(0, 1)
            self.bar.setValue(1)
            self.btn_cancel.setEnabled(False)
