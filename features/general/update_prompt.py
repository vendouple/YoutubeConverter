from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QCheckBox,
    QHBoxLayout,
    QPushButton,
)
from PyQt6.QtCore import Qt


class UpdatePromptDialog(QDialog):
    """Pre-UAC explanatory dialog capturing user consent for update flow.

    Returns accepted() True on proceed. Exposes property skip_future for 'don't ask again'.
    """

    def __init__(self, parent=None, *, has_update: bool = False):
        super().__init__(parent)
        self.setWindowTitle("Application Update")
        self.setModal(True)
        self.resize(420, 240)
        lay = QVBoxLayout(self)
        msg = (
            (
                "An update is available. The application will download and prepare files.\n\n"
                "You may be prompted by Windows (UAC) during the restart phase."
            )
            if has_update
            else (
                "The application will check for updates now. If a newer version is found, "
                "it will be downloaded and applied. It will automatically restart afterward.\n\n"
            )
        )
        lbl = QLabel(msg)
        lbl.setWordWrap(True)
        lay.addWidget(lbl)

        self.chk_skip = QCheckBox("Don't show this again")
        lay.addWidget(self.chk_skip)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_ok = QPushButton("Proceed")
        self.btn_ok.setDefault(True)
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_ok)
        lay.addLayout(btn_row)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(self.accept)

    @property
    def skip_future(self) -> bool:
        return self.chk_skip.isChecked()
