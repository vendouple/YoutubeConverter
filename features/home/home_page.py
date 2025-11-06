"""Home page with feature shortcuts and future functionality placeholders."""

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QGridLayout,
    QScrollArea,
)


class FlowLayout(QVBoxLayout):
    """A custom layout that arranges items in a responsive grid."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards = []
        self._grid = None
        self._min_card_width = 220
        self._max_card_width = 350

    def add_card(self, card):
        """Add a card to the flow layout."""
        self._cards.append(card)
        self._reflow()

    def _reflow(self):
        """Rearrange cards based on available width."""
        if not self._cards:
            return

        # Remove existing grid if any
        if self._grid is not None:
            while self._grid.count():
                item = self._grid.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)
            # Remove the grid layout
            self.removeItem(self._grid)
            self._grid.deleteLater()

        # Create new grid
        self._grid = QGridLayout()
        self._grid.setSpacing(16)
        self.addLayout(self._grid)

        # Calculate columns based on parent width
        parent = self.parentWidget()
        if parent:
            available_width = parent.width() - 80  # Account for margins
            cols = max(1, min(4, available_width // (self._min_card_width + 16)))
        else:
            cols = 2

        # Add cards to grid
        for i, card in enumerate(self._cards):
            row = i // cols
            col = i % cols
            self._grid.addWidget(card, row, col)


class FeatureCard(QFrame):
    """A card representing a feature shortcut."""

    clicked = pyqtSignal(str)  # Emits feature name when clicked

    def __init__(
        self,
        icon: str,
        title: str,
        description: str,
        feature_id: str,
        enabled: bool = True,
    ):
        super().__init__()
        self.feature_id = feature_id
        self.enabled = enabled

        self.setObjectName("FeatureCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(
            Qt.CursorShape.PointingHandCursor
            if enabled
            else Qt.CursorShape.ForbiddenCursor
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Coming soon badge for disabled features (top-right corner)
        if not enabled:
            badge_container = QWidget()
            badge_container.setStyleSheet("background: transparent;")
            badge_layout = QHBoxLayout(badge_container)
            badge_layout.setContentsMargins(0, 0, 0, 0)
            badge_layout.setSpacing(0)

            badge_layout.addStretch()

            badge = QLabel("Coming Soon")
            badge.setObjectName("ComingSoonBadge")
            badge.setStyleSheet(
                """
                QLabel#ComingSoonBadge {
                    background: #6b7280;
                    color: #e5e7eb;
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-size: 10px;
                    font-weight: 600;
                    letter-spacing: 0.5px;
                }
            """
            )
            badge_layout.addWidget(badge)
            layout.addWidget(badge_container)

        # Icon
        icon_label = QLabel(icon)
        icon_label.setObjectName("CardIcon")
        icon_label.setStyleSheet("font-size: 48px; background: transparent;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # Title
        title_label = QLabel(title)
        title_label.setObjectName("CardTitle")
        title_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; background: transparent;"
        )
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        # Description
        desc_label = QLabel(description)
        desc_label.setObjectName("CardDescription")
        desc_label.setStyleSheet(
            "font-size: 12px; color: #888; background: transparent;"
        )
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        layout.addStretch()

        # Gray out disabled cards
        if not enabled:
            self.setEnabled(False)

    def mousePressEvent(self, event):
        if self.enabled and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.feature_id)
        super().mousePressEvent(event)


class HomePage(QWidget):
    """Home page with feature shortcuts."""

    youtubeRequested = pyqtSignal()

    def __init__(self):
        super().__init__()

        # Main scroll area for responsiveness
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_widget = QWidget()
        scroll.setWidget(scroll_widget)

        layout = QVBoxLayout(scroll_widget)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(32)

        # Welcome section - no frame, just labels
        welcome_layout = QVBoxLayout()
        welcome_layout.setSpacing(8)

        title = QLabel("Welcome to YouTube Converter")
        title.setObjectName("WelcomeTitle")
        title.setStyleSheet(
            "font-size: 28px; font-weight: bold; background: transparent;"
        )
        welcome_layout.addWidget(title)

        subtitle = QLabel("Choose a feature to get started")
        subtitle.setObjectName("WelcomeSubtitle")
        subtitle.setStyleSheet("font-size: 14px; color: #888; background: transparent;")
        welcome_layout.addWidget(subtitle)

        layout.addLayout(welcome_layout)

        # Features section header
        features_label = QLabel("Features")
        features_label.setObjectName("FeaturesHeader")
        features_label.setStyleSheet(
            "font-size: 20px; font-weight: 600; background: transparent;"
        )
        layout.addWidget(features_label)

        # Flow layout for responsive cards
        self.flow_layout = FlowLayout()
        layout.addLayout(self.flow_layout)

        # Create feature cards
        # YouTube Download (enabled)
        youtube_card = FeatureCard(
            "🎵",
            "YouTube Downloader",
            "Download videos and audio from YouTube",
            "youtube",
            enabled=True,
        )
        youtube_card.clicked.connect(lambda: self.youtubeRequested.emit())
        self.flow_layout.add_card(youtube_card)

        # Trimming & Editing (disabled - future)
        trim_card = FeatureCard(
            "✂️",
            "Trimming & Editing",
            "Cut and edit your media files",
            "trimming",
            enabled=False,
        )
        self.flow_layout.add_card(trim_card)

        # File Converter (disabled - future)
        converter_card = FeatureCard(
            "🔄",
            "File Converter",
            "Convert between audio and video formats",
            "converter",
            enabled=False,
        )
        self.flow_layout.add_card(converter_card)

        # Movie Downloader (disabled - future)
        movie_card = FeatureCard(
            "🎬",
            "Movie Downloader",
            "Download movies from supported sources",
            "movies",
            enabled=False,
        )
        self.flow_layout.add_card(movie_card)

        layout.addStretch()

        # Set scroll area as main widget
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def resizeEvent(self, event):
        """Handle resize to reflow cards."""
        super().resizeEvent(event)
        if hasattr(self, "flow_layout"):
            self.flow_layout._reflow()
