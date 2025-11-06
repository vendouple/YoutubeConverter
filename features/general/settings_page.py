from PyQt6.QtCore import pyqtSignal, Qt, QEvent, QPropertyAnimation, QEasingCurve
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
    QLineEdit,
    QScrollArea,
)

from core.settings import AppSettings
from core.models import UpdateCadence, UpdateAction


class CollapsibleSection(QWidget):
    """A collapsible section widget for organizing settings."""

    def __init__(self, title: str, description: str = "", parent=None):
        super().__init__(parent)
        self.is_collapsed = False

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header (clickable)
        self.header = QFrame()
        self.header.setObjectName("CollapsibleHeader")
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(18, 14, 18, 14)

        # Title and description
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-size:18px; font-weight:600;")
        text_layout.addWidget(self.title_label)

        if description:
            self.desc_label = QLabel(description)
            self.desc_label.setWordWrap(True)
            self.desc_label.setProperty("role", "caption")
            text_layout.addWidget(self.desc_label)

        header_layout.addLayout(text_layout, 1)

        # Collapse/expand icon
        self.toggle_icon = QLabel("▼")
        self.toggle_icon.setStyleSheet("font-size: 14px;")
        header_layout.addWidget(self.toggle_icon)

        main_layout.addWidget(self.header)

        # Content container
        self.content_frame = QFrame()
        self.content_frame.setObjectName("CategoryCard")
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(18, 14, 18, 14)
        self.content_layout.setSpacing(8)

        main_layout.addWidget(self.content_frame)

        # Enable mouse click on header
        self.header.mousePressEvent = lambda e: self.toggle_collapse()

    def toggle_collapse(self):
        """Toggle the collapsed state."""
        self.is_collapsed = not self.is_collapsed
        self.content_frame.setVisible(not self.is_collapsed)
        self.toggle_icon.setText("▶" if self.is_collapsed else "▼")

    def add_widget(self, widget: QWidget):
        """Add a widget to the content area."""
        self.content_layout.addWidget(widget)

    def add_layout(self, layout):
        """Add a layout to the content area."""
        self.content_layout.addLayout(layout)


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
        self._all_sections = []  # Track all sections for search/filter

        self.setStyleSheet("")

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # Search and filter bar
        search_layout = QHBoxLayout()

        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Search settings...")
        self.search_box.textChanged.connect(self._on_search_changed)
        self.search_box.setStyleSheet(
            """
            QLineEdit {
                padding: 8px 12px;
                border-radius: 8px;
                font-size: 13px;
            }
        """
        )
        search_layout.addWidget(self.search_box, 1)

        # Filter dropdown
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Settings", "YouTube Converter", "General"])
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        self.filter_combo.setStyleSheet("padding: 6px 12px; min-width: 120px;")
        search_layout.addWidget(self.filter_combo)

        main_layout.addLayout(search_layout)

        # Settings content area
        self.settings_content = QWidget()
        root = QVBoxLayout(self.settings_content)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(20)

        # Helper function to create collapsible sections
        def collapsible_section(
            title: str, desc: str, category: str = "General"
        ) -> CollapsibleSection:
            section = CollapsibleSection(title, desc)
            section.setProperty("category", category)
            section.setProperty("searchText", f"{title} {desc}".lower())
            self._all_sections.append(section)
            root.addWidget(section)
            return section

        # ===== GENERAL SETTINGS =====
        # Main category header
        general_header = QLabel("⚙️ General Settings")
        general_header.setStyleSheet(
            "font-size: 22px; font-weight: 700; margin-top: 8px; margin-bottom: 4px;"
        )
        general_header.setProperty("category", "General")
        self._all_sections.append(general_header)
        root.addWidget(general_header)

        # Appearance subcategory
        section_app = collapsible_section(
            "Appearance", "Theme, accent color and general UI behavior.", "General"
        )
        row_theme = QHBoxLayout()
        row_theme.addWidget(QLabel("Theme:"))
        self.cmb_theme = QComboBox()
        theme_options = ["Dark", "Light", "OLED"]
        self.cmb_theme.addItems(theme_options)
        cur_mode = getattr(settings.ui, "theme_mode", "dark").lower()
        mode_to_index = {name.lower(): idx for idx, name in enumerate(theme_options)}
        self.cmb_theme.setCurrentIndex(mode_to_index.get(cur_mode, 0))
        row_theme.addWidget(self.cmb_theme, 1)
        section_app.add_layout(row_theme)
        btn_accent = QPushButton("Pick accent color")
        btn_accent.setObjectName("CompactButton")
        btn_accent.clicked.connect(self.accentPickRequested.emit)
        section_app.add_widget(btn_accent)

        # Search & Input subcategory
        section_search = collapsible_section(
            "Search & Input", "Controls how text input triggers searches.", "General"
        )
        self.chk_auto_search_text = QCheckBox("Auto search while typing")
        self.chk_auto_search_text.setChecked(
            getattr(settings.ui, "auto_search_text", True)
        )
        section_search.add_widget(self.chk_auto_search_text)
        row_db = QHBoxLayout()
        row_db.addWidget(QLabel("Search debounce (s):"))
        self.spn_search_debounce = QSpinBox()
        self.spn_search_debounce.setRange(0, 10)
        self.spn_search_debounce.setValue(
            int(getattr(settings.ui, "search_debounce_seconds", 3))
        )
        row_db.addWidget(self.spn_search_debounce)
        section_search.add_layout(row_db)

        # Notifications subcategory
        section_notif = collapsible_section(
            "Notifications",
            "Toast notification verbosity level. (WIP, Doesnt work yet)",
            "General",
        )
        section_notif.add_widget(QLabel("Notification detail level:"))
        self.cmb_notif = QComboBox()
        self.cmb_notif.addItems(["Detailed", "Minimal", "None"])
        self.cmb_notif.setCurrentIndex(
            {"detailed": 0, "minimal": 1, "none": 2}.get(
                getattr(settings.app, "notifications_detail", "detailed").lower(), 0
            )
        )
        section_notif.add_widget(self.cmb_notif)

        # Updates subcategory (schedule-based)
        section_updates = collapsible_section(
            "Updates",
            "Control how the app and yt-dlp update: schedule, channels, and behavior.",
            "General",
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
        self.btn_check_ytdlp.setObjectName("CompactButton")
        self.btn_check_ytdlp.clicked.connect(self.checkYtDlpRequested.emit)
        row_y_btn.addWidget(self.btn_check_ytdlp)
        y_lay.addLayout(row_y_btn)

        section_updates.add_widget(y_section)

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
        self.btn_check_app.setObjectName("CompactButton")
        self.btn_check_app.clicked.connect(self.checkAppCheckOnlyRequested.emit)
        row_a_btn.addWidget(self.btn_check_app)
        a_lay.addLayout(row_a_btn)

        section_updates.add_widget(a_section)

        # Maintenance subcategory
        section_maint = collapsible_section(
            "Maintenance", "Log management and diagnostics.", "General"
        )
        btn_logs = QPushButton("Clear all logs")
        btn_logs.setObjectName("CompactButton")
        btn_logs.clicked.connect(self.clearLogsRequested.emit)
        section_maint.add_widget(btn_logs)
        btn_export = QPushButton("Export logs (zip)")
        btn_export.setObjectName("CompactButton")
        btn_export.clicked.connect(self.exportLogsRequested.emit)
        section_maint.add_widget(btn_export)

        # Help / FAQ
        section_help = collapsible_section(
            "Help", "Find answers to common questions.", "General"
        )
        btn_faq = QPushButton("Open FAQ")
        btn_faq.setObjectName("CompactButton")
        btn_faq.clicked.connect(self.openFaqRequested.emit)
        section_help.add_widget(btn_faq)

        # ===== YOUTUBE CONVERTER SETTINGS =====
        # Main category header
        youtube_header = QLabel("📺 YouTube Converter Settings")
        youtube_header.setStyleSheet(
            "font-size: 22px; font-weight: 700; margin-top: 16px; margin-bottom: 4px;"
        )
        youtube_header.setProperty("category", "YouTube Converter")
        self._all_sections.append(youtube_header)
        root.addWidget(youtube_header)

        # Downloads subcategory
        section_dl = collapsible_section(
            "Downloads",
            "Workflow preferences for post-completion behavior.",
            "YouTube Converter",
        )
        self.chk_auto_reset_after = QCheckBox("Reset wizard after all downloads")
        self.chk_auto_reset_after.setChecked(
            getattr(settings.app, "auto_reset_after_downloads", True)
        )
        section_dl.add_widget(self.chk_auto_reset_after)

        # Filename template
        lbl_filename = QLabel("Filename template:")
        lbl_filename.setStyleSheet("margin-top: 8px; font-weight: 600;")
        section_dl.add_widget(lbl_filename)

        filename_row = QHBoxLayout()
        self.txt_filename_template = QLineEdit()
        self.txt_filename_template.setText(
            getattr(settings.defaults, "filename_template", "{title}")
        )
        self.txt_filename_template.setPlaceholderText("{title}")
        filename_row.addWidget(self.txt_filename_template, 1)

        # Preview button
        self.btn_filename_preview = QPushButton("Preview")
        self.btn_filename_preview.setObjectName("CompactButton")
        self.btn_filename_preview.clicked.connect(self._show_filename_preview)
        filename_row.addWidget(self.btn_filename_preview)
        section_dl.add_layout(filename_row)

        # Available variables help text
        lbl_vars = QLabel(
            "📝 Available variables: {title}, {videoId}, {channelName}, "
            "{dateDownloaded}, {playlistName}, {index}, {format}, {resolution}"
        )
        lbl_vars.setWordWrap(True)
        lbl_vars.setStyleSheet("color: #888; font-size: 11px; margin-left: 4px;")
        section_dl.add_widget(lbl_vars)

        # Preview label (initially hidden)
        self.lbl_filename_preview = QLabel()
        self.lbl_filename_preview.setWordWrap(True)
        self.lbl_filename_preview.setStyleSheet(
            "background: #2a2b30; padding: 8px; border-radius: 4px; "
            "font-family: monospace; margin-top: 4px;"
        )
        self.lbl_filename_preview.hide()
        section_dl.add_widget(self.lbl_filename_preview)

        # Quality Settings subcategory
        section_quality = collapsible_section(
            "Quality & Format",
            "Default quality preferences and advanced options.",
            "YouTube Converter",
        )
        # EZ Mode settings (moved here as they relate to quality selection)
        self.chk_ez_simple = QCheckBox("Simple paste mode (EZ Mode)")
        self.chk_ez_simple.setChecked(settings.ez.simple_paste_mode)
        section_quality.add_widget(self.chk_ez_simple)
        self.chk_ez_sanitize = QCheckBox("Sanitize radio/mix links")
        self.chk_ez_sanitize.setChecked(settings.ez.sanitize_radio_links)
        section_quality.add_widget(self.chk_ez_sanitize)
        self.chk_ez_hide_adv = QCheckBox("Hide advanced quality options")
        self.chk_ez_hide_adv.setChecked(settings.ez.hide_advanced_quality)
        section_quality.add_widget(self.chk_ez_hide_adv)

        # Hide subtitle options (experimental)
        self.chk_hide_subtitles = QCheckBox(
            "Hide subtitle options (Experimental feature)"
        )
        self.chk_hide_subtitles.setChecked(
            getattr(settings.defaults, "hide_subtitle_options", True)
        )
        self.chk_hide_subtitles.setToolTip(
            "When enabled, subtitle options are hidden in the quality page. "
            "Uncheck to show subtitle configuration options."
        )
        section_quality.add_widget(self.chk_hide_subtitles)

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

        # SponsorBlock subcategory
        section_sponsorblock = collapsible_section(
            "SponsorBlock",
            "Skip sponsored segments automatically during downloads.",
            "YouTube Converter",
        )

        # Enable SponsorBlock checkbox
        self.chk_sponsorblock = QCheckBox("Enable SponsorBlock integration")
        self.chk_sponsorblock.setChecked(
            getattr(settings.defaults, "sponsorblock_enabled", False)
        )
        section_sponsorblock.add_widget(self.chk_sponsorblock)

        # Behavior mode selection
        lbl_behavior = QLabel("Settings behavior:")
        lbl_behavior.setStyleSheet("margin-top: 8px; font-weight: 600;")
        section_sponsorblock.add_widget(lbl_behavior)

        self.radio_sb_remember = QCheckBox(
            "Remember last used categories from quality menu"
        )
        self.radio_sb_remember.setChecked(
            getattr(settings.defaults, "sponsorblock_remember_last", False)
        )
        section_sponsorblock.add_widget(self.radio_sb_remember)

        self.radio_sb_default = QCheckBox("Always use default categories (below)")
        self.radio_sb_default.setChecked(
            not getattr(settings.defaults, "sponsorblock_remember_last", False)
        )
        section_sponsorblock.add_widget(self.radio_sb_default)

        # Make them mutually exclusive
        def _on_remember_toggled(checked):
            if checked:
                self.radio_sb_default.setChecked(False)
                # Hide category selection when remembering last
                self._toggle_sb_categories(False)
            else:
                self.radio_sb_default.setChecked(True)

        def _on_default_toggled(checked):
            if checked:
                self.radio_sb_remember.setChecked(False)
                # Show category selection when using defaults
                self._toggle_sb_categories(True)
            else:
                self.radio_sb_remember.setChecked(True)

        self.radio_sb_remember.toggled.connect(_on_remember_toggled)
        self.radio_sb_default.toggled.connect(_on_default_toggled)

        # Category selection container (shown only for "use defaults" mode)
        self.sb_categories_container = QWidget()
        sb_categories_layout = QVBoxLayout(self.sb_categories_container)
        sb_categories_layout.setContentsMargins(0, 0, 0, 0)
        sb_categories_layout.setSpacing(8)

        lbl_categories = QLabel("Default categories to skip:")
        lbl_categories.setStyleSheet("margin-top: 8px; font-weight: 600;")
        sb_categories_layout.addWidget(lbl_categories)

        # Preset dropdown
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Preset:"))
        self.cmb_sb_preset = QComboBox()
        self.cmb_sb_preset.addItems(
            [
                "Custom",
                "Strict (All segments)",
                "Balanced (Sponsor + Self-promo)",
                "Minimal (Sponsor only)",
            ]
        )
        self.cmb_sb_preset.setCurrentIndex(0)  # Default to Custom
        self.cmb_sb_preset.currentIndexChanged.connect(self._apply_sponsorblock_preset)
        preset_layout.addWidget(self.cmb_sb_preset, 1)
        sb_categories_layout.addLayout(preset_layout)

        # Individual category checkboxes
        current_cats = getattr(
            settings.defaults, "sponsorblock_categories", ["sponsor", "selfpromo"]
        )

        self.chk_sb_sponsor = QCheckBox("Sponsor - Paid promotion")
        self.chk_sb_sponsor.setChecked("sponsor" in current_cats)
        sb_categories_layout.addWidget(self.chk_sb_sponsor)

        self.chk_sb_selfpromo = QCheckBox("Self-promotion - Unpaid promotion")
        self.chk_sb_selfpromo.setChecked("selfpromo" in current_cats)
        sb_categories_layout.addWidget(self.chk_sb_selfpromo)

        self.chk_sb_interaction = QCheckBox("Interaction reminder - Like/Subscribe")
        self.chk_sb_interaction.setChecked("interaction" in current_cats)
        sb_categories_layout.addWidget(self.chk_sb_interaction)

        self.chk_sb_intro = QCheckBox("Intro - Intermission/Intro animation")
        self.chk_sb_intro.setChecked("intro" in current_cats)
        sb_categories_layout.addWidget(self.chk_sb_intro)

        self.chk_sb_outro = QCheckBox("Outro - Endcards/Credits")
        self.chk_sb_outro.setChecked("outro" in current_cats)
        sb_categories_layout.addWidget(self.chk_sb_outro)

        self.chk_sb_preview = QCheckBox("Preview - Recap of previous episodes")
        self.chk_sb_preview.setChecked("preview" in current_cats)
        sb_categories_layout.addWidget(self.chk_sb_preview)

        self.chk_sb_music_offtopic = QCheckBox(
            "Music/Off-topic - Non-music in music videos"
        )
        self.chk_sb_music_offtopic.setChecked("music_offtopic" in current_cats)
        sb_categories_layout.addWidget(self.chk_sb_music_offtopic)

        self.chk_sb_filler = QCheckBox("Filler - Filler tangent/jokes")
        self.chk_sb_filler.setChecked("filler" in current_cats)
        sb_categories_layout.addWidget(self.chk_sb_filler)

        # Connect checkboxes to update preset
        for chk in [
            self.chk_sb_sponsor,
            self.chk_sb_selfpromo,
            self.chk_sb_interaction,
            self.chk_sb_intro,
            self.chk_sb_outro,
            self.chk_sb_preview,
            self.chk_sb_music_offtopic,
            self.chk_sb_filler,
        ]:
            chk.toggled.connect(self._on_sb_category_changed)

        section_sponsorblock.add_widget(self.sb_categories_container)

        # Set initial visibility based on mode
        self._toggle_sb_categories(
            not getattr(settings.defaults, "sponsorblock_remember_last", False)
        )

        # Info label
        lbl_info = QLabel(
            "ℹ️ SponsorBlock segments will be automatically removed during video processing."
        )
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("color: #888; font-size: 12px; margin-top: 8px;")
        section_sponsorblock.add_widget(lbl_info)

        # Subtitles/Lyrics subcategory
        section_subtitles = collapsible_section(
            "Subtitles & Lyrics",
            "Download subtitles/lyrics files alongside your videos and audio",
        )
        root.addWidget(section_subtitles)

        # Enable subtitles checkbox
        self.chk_subtitles = QCheckBox("Download subtitles/lyrics")
        self.chk_subtitles.setChecked(
            getattr(settings.defaults, "download_subtitles", False)
        )
        section_subtitles.add_widget(self.chk_subtitles)

        # Language selection
        lang_row = QWidget()
        lang_layout = QHBoxLayout(lang_row)
        lang_layout.setContentsMargins(20, 0, 0, 0)
        lang_layout.setSpacing(8)
        lbl_lang = QLabel("Languages:")
        lbl_lang.setToolTip("Comma-separated language codes (e.g., en,es,fr)")
        self.txt_subtitle_langs = QLineEdit()
        self.txt_subtitle_langs.setPlaceholderText("en,es,fr")
        self.txt_subtitle_langs.setText(
            getattr(settings.defaults, "subtitle_languages", "en")
        )
        self.txt_subtitle_langs.setMaximumWidth(200)
        lang_layout.addWidget(lbl_lang)
        lang_layout.addWidget(self.txt_subtitle_langs)
        lang_layout.addStretch(1)
        section_subtitles.add_widget(lang_row)

        # Auto-generated subtitles checkbox
        self.chk_auto_subs = QCheckBox(
            "Download auto-generated if manual not available"
        )
        self.chk_auto_subs.setChecked(
            getattr(settings.defaults, "auto_generate_subs", False)
        )
        self.chk_auto_subs.setStyleSheet("margin-left: 20px;")
        section_subtitles.add_widget(self.chk_auto_subs)

        # Embed subtitles (video only)
        self.chk_embed_subs = QCheckBox("Embed subtitles in video files (video only)")
        self.chk_embed_subs.setChecked(
            getattr(settings.defaults, "embed_subtitles", False)
        )
        self.chk_embed_subs.setStyleSheet("margin-left: 20px;")
        self.chk_embed_subs.setToolTip(
            "Embed subtitles into video file. For audio downloads, subtitles are always saved as separate files."
        )
        section_subtitles.add_widget(self.chk_embed_subs)

        # Info label
        lbl_sub_info = QLabel(
            "ℹ️ Subtitles will be downloaded as .srt files. For videos, you can embed them into the file."
        )
        lbl_sub_info.setWordWrap(True)
        lbl_sub_info.setStyleSheet("color: #888; font-size: 12px; margin-top: 8px;")
        section_subtitles.add_widget(lbl_sub_info)

        root.addStretch(1)

        # Add scrollable content area to main layout
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.settings_content)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        main_layout.addWidget(scroll)

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
            self.chk_auto_search_text,
            self.spn_search_debounce,
            self.chk_auto_reset_after,
            self.txt_filename_template,
            self.cmb_notif,
            self.cmb_ytdlp_schedule,
            self.cmb_app_schedule,
            self.cmb_ytdlp_branch,
            self.cmb_app_channel,
            self.cmb_app_action,
            self.chk_ez_simple,
            self.chk_ez_sanitize,
            self.chk_ez_hide_adv,
            self.chk_sponsorblock,
            self.radio_sb_remember,
            self.radio_sb_default,
            self.cmb_sb_preset,
            self.chk_sb_sponsor,
            self.chk_sb_selfpromo,
            self.chk_sb_interaction,
            self.chk_sb_intro,
            self.chk_sb_outro,
            self.chk_sb_preview,
            self.chk_sb_music_offtopic,
            self.chk_sb_filler,
            self.chk_subtitles,
            self.txt_subtitle_langs,
            self.chk_auto_subs,
            self.chk_embed_subs,
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
            if hasattr(w, "textChanged"):
                try:
                    w.textChanged.connect(self.changed.emit)
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
        if mode not in {"light", "dark", "oled"}:
            mode = "dark"
        settings.ui.theme_mode = mode
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
        self_channel = {0: "release", 1: "nightly"}.get(
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

        # Hide subtitle options
        settings.defaults.hide_subtitle_options = self.chk_hide_subtitles.isChecked()

        # SponsorBlock settings
        settings.defaults.sponsorblock_enabled = self.chk_sponsorblock.isChecked()
        settings.defaults.sponsorblock_remember_last = (
            self.radio_sb_remember.isChecked()
        )

        # Only save categories if using default mode (not remember last)
        if not settings.defaults.sponsorblock_remember_last:
            # Collect enabled categories
            categories = []
            if self.chk_sb_sponsor.isChecked():
                categories.append("sponsor")
            if self.chk_sb_selfpromo.isChecked():
                categories.append("selfpromo")
            if self.chk_sb_interaction.isChecked():
                categories.append("interaction")
            if self.chk_sb_intro.isChecked():
                categories.append("intro")
            if self.chk_sb_outro.isChecked():
                categories.append("outro")
            if self.chk_sb_preview.isChecked():
                categories.append("preview")
            if self.chk_sb_music_offtopic.isChecked():
                categories.append("music_offtopic")
            if self.chk_sb_filler.isChecked():
                categories.append("filler")

            settings.defaults.sponsorblock_categories = categories

        # Filename template
        settings.defaults.filename_template = (
            self.txt_filename_template.text() or "{title}"
        )

        # Subtitle settings
        settings.defaults.download_subtitles = self.chk_subtitles.isChecked()
        settings.defaults.subtitle_languages = (
            self.txt_subtitle_langs.text().strip() or "en"
        )
        settings.defaults.auto_generate_subs = self.chk_auto_subs.isChecked()
        settings.defaults.embed_subtitles = self.chk_embed_subs.isChecked()

    def _on_search_changed(self, text: str):
        """Filter settings sections based on search text with highlighting."""
        search_text = text.lower().strip()

        for section in self._all_sections:
            # Handle header labels (category headers like "⚙️ General Settings")
            if isinstance(section, QLabel):
                original_text = section.property("originalText")
                if original_text is None:
                    # Store original text on first search
                    original_text = section.text()
                    section.setProperty("originalText", original_text)

                if not search_text:
                    # Clear highlighting
                    section.setText(original_text)
                    section.setVisible(True)
                else:
                    # Check if search matches (case insensitive)
                    if search_text in original_text.lower():
                        # Highlight matching text with yellow background
                        highlighted = self._highlight_text(original_text, search_text)
                        section.setText(highlighted)
                        section.setVisible(True)
                    else:
                        section.setText(original_text)
                        section.setVisible(False)
                continue

            # Handle CollapsibleSection widgets
            if isinstance(section, CollapsibleSection):
                section_text = section.property("searchText") or ""

                # Store original texts if not already stored
                if section.property("originalTitle") is None:
                    section.setProperty("originalTitle", section.title_label.text())
                if (
                    hasattr(section, "desc_label")
                    and section.property("originalDesc") is None
                ):
                    section.setProperty("originalDesc", section.desc_label.text())

                # Get originals
                original_title = section.property("originalTitle")
                original_desc = (
                    section.property("originalDesc")
                    if hasattr(section, "desc_label")
                    else None
                )

                # Show/hide based on search match
                if not search_text or search_text in section_text:
                    section.setVisible(True)

                    # Apply highlighting if search text exists
                    if search_text:
                        # Highlight title
                        if search_text in original_title.lower():
                            highlighted_title = self._highlight_text(
                                original_title, search_text
                            )
                            section.title_label.setText(highlighted_title)
                        else:
                            section.title_label.setText(original_title)

                        # Highlight description
                        if original_desc and search_text in original_desc.lower():
                            highlighted_desc = self._highlight_text(
                                original_desc, search_text
                            )
                            section.desc_label.setText(highlighted_desc)
                        elif original_desc:
                            section.desc_label.setText(original_desc)
                    else:
                        # Clear highlighting
                        section.title_label.setText(original_title)
                        if original_desc:
                            section.desc_label.setText(original_desc)
                else:
                    section.setVisible(False)
                    # Reset text even when hidden
                    section.title_label.setText(original_title)
                    if original_desc:
                        section.desc_label.setText(original_desc)

    def _highlight_text(self, text: str, search: str) -> str:
        """Highlight search term in text with yellow background (case insensitive)."""
        if not search or not text:
            return text

        # Find all occurrences (case insensitive)
        result = []
        text_lower = text.lower()
        search_lower = search.lower()
        last_idx = 0

        idx = text_lower.find(search_lower)
        while idx != -1:
            # Add text before match
            result.append(text[last_idx:idx])
            # Add highlighted match
            match_text = text[idx : idx + len(search)]
            result.append(
                f'<span style="background-color: #ffeb3b; color: #000000; padding: 2px 4px; border-radius: 3px;">{match_text}</span>'
            )
            last_idx = idx + len(search)
            idx = text_lower.find(search_lower, last_idx)

        # Add remaining text
        result.append(text[last_idx:])

        return "".join(result)

    def _on_filter_changed(self, filter_text: str):
        """Filter settings sections based on category."""
        if filter_text == "All Settings":
            # Show all sections
            for section in self._all_sections:
                section.setVisible(True)
        else:
            # Show only matching category (including headers)
            for section in self._all_sections:
                category = section.property("category")
                if category:
                    section.setVisible(category == filter_text)
                else:
                    # No category property means it's likely a header label
                    section.setVisible(False)

    def _apply_sponsorblock_preset(self, index: int):
        """Apply a SponsorBlock preset to the category checkboxes."""
        if index == 0:  # Custom - don't change anything
            return
        elif index == 1:  # Strict (All segments)
            self.chk_sb_sponsor.setChecked(True)
            self.chk_sb_selfpromo.setChecked(True)
            self.chk_sb_interaction.setChecked(True)
            self.chk_sb_intro.setChecked(True)
            self.chk_sb_outro.setChecked(True)
            self.chk_sb_preview.setChecked(True)
            self.chk_sb_music_offtopic.setChecked(True)
            self.chk_sb_filler.setChecked(True)
        elif index == 2:  # Balanced (Sponsor + Self-promo)
            self.chk_sb_sponsor.setChecked(True)
            self.chk_sb_selfpromo.setChecked(True)
            self.chk_sb_interaction.setChecked(False)
            self.chk_sb_intro.setChecked(False)
            self.chk_sb_outro.setChecked(False)
            self.chk_sb_preview.setChecked(False)
            self.chk_sb_music_offtopic.setChecked(False)
            self.chk_sb_filler.setChecked(False)
        elif index == 3:  # Minimal (Sponsor only)
            self.chk_sb_sponsor.setChecked(True)
            self.chk_sb_selfpromo.setChecked(False)
            self.chk_sb_interaction.setChecked(False)
            self.chk_sb_intro.setChecked(False)
            self.chk_sb_outro.setChecked(False)
            self.chk_sb_preview.setChecked(False)
            self.chk_sb_music_offtopic.setChecked(False)
            self.chk_sb_filler.setChecked(False)

    def _on_sb_category_changed(self):
        """Update preset dropdown to 'Custom' when user manually changes categories."""
        # Set to Custom when user manually changes checkboxes
        self.cmb_sb_preset.setCurrentIndex(0)

    def _toggle_sb_categories(self, show: bool):
        """Show or hide the category selection container."""
        self.sb_categories_container.setVisible(show)

    def _show_filename_preview(self):
        """Show a preview of the filename template with example data."""
        from datetime import datetime

        template = self.txt_filename_template.text() or "{title}"

        # Example data
        example_data = {
            "title": "Example Video Title",
            "videoId": "dQw4w9WgXcQ",
            "channelName": "Example Channel",
            "dateDownloaded": datetime.now().strftime("%Y-%m-%d"),
            "playlistName": "My Playlist",
            "index": "01",
            "format": "mp4",
            "resolution": "1080p",
        }

        # Apply template
        try:
            preview = template
            for key, value in example_data.items():
                preview = preview.replace(f"{{{key}}}", str(value))

            # Sanitize for filename
            safe_preview = "".join(
                c for c in preview if c.isalnum() or c in (" ", "-", "_", ".")
            ).strip()

            self.lbl_filename_preview.setText(f"Preview: {safe_preview}.mp4")
            self.lbl_filename_preview.setStyleSheet(
                "background: #2d5016; color: #90ee90; padding: 8px; "
                "border-radius: 4px; font-family: monospace; margin-top: 4px;"
            )
            self.lbl_filename_preview.show()
        except Exception as e:
            self.lbl_filename_preview.setText(f"❌ Invalid template: {str(e)}")
            self.lbl_filename_preview.setStyleSheet(
                "background: #5a1616; color: #ff9999; padding: 8px; "
                "border-radius: 4px; font-family: monospace; margin-top: 4px;"
            )
            self.lbl_filename_preview.show()
