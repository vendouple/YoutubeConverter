class StyleManager:
    def __init__(self, accent_hex: str):
        self._accent = accent_hex

    # NEW: color helpers
    def _rgb_tuple(self, hex_color: str):
        try:
            s = hex_color.lstrip("#")
            return tuple(int(s[i : i + 2], 16) for i in (0, 2, 4))
        except Exception:
            return (242, 140, 40)  # fallback

    def _lighter(self, hex_color: str, factor: float = 1.15):
        r, g, b = self._rgb_tuple(hex_color)
        f = max(1.0, float(factor))
        to = lambda x: max(0, min(255, int(x * f)))
        return f"#{to(r):02x}{to(g):02x}{to(b):02x}"

    def _rgba(self, hex_color: str, alpha: float = 0.25):
        r, g, b = self._rgb_tuple(hex_color)
        a = max(0.0, min(1.0, float(alpha)))
        return f"rgba({r},{g},{b},{a})"

    def with_accent(self, hex_color: str):
        self._accent = hex_color
        return self.qss()

    def qss(self) -> str:
        """Default/base QSS (dark-friendly). Used as a foundation for all themes."""
        ac = self._accent
        ac_hover = self._lighter(ac, 1.2)  # slightly lighter than accent
        ac_bg_on = self._rgba(ac, 0.25)  # subtle on background
        ac_bg_hover = self._rgba(ac_hover, 0.35)  # stronger on hover
        return f"""
/* Base */
QWidget {{
    background: #1c1d20; /* slightly darker for contrast */
    color: #f0f0f0;      /* lighter text for improved contrast */
    font-size: 13px;
}}
QLabel {{
    background: transparent;
}}
QFrame#Sidebar {{
    background: #202125;
    border-right: 1px solid #2e2f33;
}}

/* Accent vertical separator */
QFrame#AccentVLine {{
    background-color: {ac};
    min-width: 1px;
    max-width: 1px;
    margin: 0 6px;
}}

/* Lists: frameless, full-row hover/selection */
QListView, QListWidget, QTreeView {{
    border: none;
    background: #1e1f22;
    outline: 0;
}}
QListView::item, QListWidget::item {{
    margin: 2px;            /* CHANGED: tighter gaps */
    padding: 8px;           /* CHANGED: tighter padding */
    border-radius: 10px;
    border: 1px solid transparent;
}}
/* Light accent on hover, darker on selected */
QListView::item:hover, QListWidget::item:hover {{
    background: #24252a;
    border-color: {ac};
}}
QListView::item:selected, QListWidget::item:selected {{
    background: {ac};
    color: #ffffff;
    border-color: {ac};
}}
/* Ensure selection fills full row width */
QListView::icon, QListWidget::icon {{
    padding-right: 8px;
}}

/* Buttons */
QPushButton {{
    background: #2c2d32;
    border: 1px solid #40424a;
    border-radius: 8px;
    padding: 8px 12px;
}}
QPushButton:hover {{ border-color: {ac}; }}
QPushButton:pressed {{ background: #25262a; }}
QPushButton:disabled {{
    background: #1a1b1e;
    border: 1px solid #2a2b30;
    color: #555555;
    opacity: 0.5;
}}
QPushButton:checked {{
    border-color: {ac};
    background: #2d2e33;
}}
QPushButton#IconButton {{ font-size: 18px; padding: 0; }}

/* Primary/Danger buttons */
QPushButton#PrimaryButton {{
    background: {ac};
    color: #ffffff;
    border: 1px solid {ac};
}}
QPushButton#PrimaryButton:hover {{ filter: brightness(1.1); }}
QPushButton#PrimaryButton:pressed {{ filter: brightness(0.95); }}

QPushButton#DangerButton {{
    background: #c53030;
    color: #ffffff;
    border: 1px solid #a82b2b;
}}
QPushButton#DangerButton:hover {{ background: #d13a3a; }}
QPushButton#DangerButton:pressed {{ background: #b22a2a; }}

/* Segmented buttons (Audio/Video) - Balanced 50/50 menu style */
QPushButton#SegmentButton {{
    background: #232428;
    border: 1px solid #34353b;
    border-radius: 6px;
    padding: 6px 12px;
    min-width: 70px;
    max-width: 100px;
    min-height: 28px;
    font-weight: 500;
    text-align: center;
}}
QPushButton#SegmentButton:hover {{ 
    border-color: {ac}; 
    background: #2a2b30;
}}
QPushButton#SegmentButton:checked {{
    border-color: {ac};
    color: {ac};
    background: #24252a;
}}

/* Inputs */
QPushButton:focus, QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QCheckBox:focus, QRadioButton:focus {{
    outline: 0; border: 1px solid #34353b;
}}
QLineEdit, QComboBox, QTextEdit {{
    background: #212226; border: 1px solid #3d3f45; border-radius: 8px; padding: 6px 8px;
}}

/* Modern ComboBox dropdown arrows */
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left-width: 1px;
    border-left-color: #3d3f45;
    border-left-style: solid;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
    background: #2c2d32;
}}
QComboBox::down-arrow {{
    image: none;
    border: 2px solid #8a8b90;
    width: 0px;
    height: 0px;
    border-top: 4px solid #8a8b90;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: none;
}}
QComboBox::down-arrow:hover {{
    border-top-color: {ac};
}}
QComboBox QAbstractItemView {{
    background: #212226;
    border: 1px solid #3d3f45;
    border-radius: 8px;
    outline: none;
    selection-background-color: {ac};
    selection-color: #ffffff;
    padding: 2px;
}}

/* SpinBox arrows */
QSpinBox::up-button, QSpinBox::down-button {{
    background: #2c2d32;
    border: 1px solid #3d3f45;
    width: 20px;
}}
QSpinBox::up-button {{
    border-top-right-radius: 8px;
}}
QSpinBox::down-button {{
    border-bottom-right-radius: 8px;
}}
QSpinBox::up-arrow, QSpinBox::down-arrow {{
    width: 0px;
    height: 0px;
    border: 3px solid transparent;
}}
QSpinBox::up-arrow {{
    border-bottom: 4px solid #8a8b90;
}}
QSpinBox::down-arrow {{
    border-top: 4px solid #8a8b90;
}}
QSpinBox::up-arrow:hover {{
    border-bottom-color: {ac};
}}
QSpinBox::down-arrow:hover {{
    border-top-color: {ac};
}}

/* Win11-like CheckBox (check mark box) */
QCheckBox {{
    spacing: 6px; /* space between box and label */
    background: transparent;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;                 /* rounded square */
    background: #1f2024;                /* off background */
    border: 2px solid #cfd0d4;          /* off border (light gray) */
    margin-right: 6px;
}}
QCheckBox::indicator:hover {{
    border-color: {ac_hover};           /* hover: distinct from accent */
}}
QCheckBox::indicator:checked {{
    border-color: {ac};                 /* on border: accent */
    background: {ac_bg_on};             /* on background: subtle tint */
}}
QCheckBox::indicator:checked:hover {{
    border-color: {ac_hover};           /* on+hover border: distinct hover accent */
    background: {ac_bg_hover};          /* on+hover background: stronger tint */
}}
QCheckBox:checked {{
    color: {ac};                        /* label accent when ON */
}}
QCheckBox:hover {{
    color: {ac_hover};                  /* label hover color */
}}
QCheckBox::indicator:disabled {{
    border-color: #57585e;
    background: #2a2b30;
}}
QCheckBox:disabled {{
    color: #8a8b90;
}}

/* Button-like checkbox ('Add multiple') - keep existing look, hide indicator */
QCheckBox#ButtonLike {{
    background: #2a2b30;
    border: 1px solid #33343a;
    border-radius: 8px;
    padding: 8px 12px;
}}
QCheckBox#ButtonLike:hover {{ border-color: {ac}; }}
QCheckBox#ButtonLike:checked {{
    border-color: {ac};
    background: #2d2e33;
}}
QCheckBox#ButtonLike::indicator {{ width: 0px; height: 0px; }}

/* ProgressBar (default) */
QProgressBar {{
    border: 1px solid #34353b; border-radius: 8px; background: #24252a; text-align: center;
}}
QProgressBar::chunk {{ background-color: {ac}; border-radius: 8px; }}

/* Download progress bars: transparent background so row highlight shows through */
QProgressBar#DlProgress {{
    background: transparent;           /* CHANGED: transparent */
    border: 1px solid #34353b;
    border-radius: 8px;
}}
QProgressBar#DlProgress::chunk {{ background-color: {ac}; border-radius: 8px; }}

/* Scrollbars (Win11-like) */
QScrollBar:vertical {{
    background: transparent; width: 12px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #3a3b41; min-height: 24px; border-radius: 6px; margin: 2px;
}}
QScrollBar::handle:vertical:hover {{ background: {ac}; }}
QScrollBar::handle:vertical:pressed {{ background: {ac}; filter: brightness(0.9); }}

QScrollBar:horizontal {{
    background: transparent; height: 12px; margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: #3a3b41; min-width: 24px; border-radius: 6px; margin: 2px;
}}
QScrollBar::handle:horizontal:hover {{ background: {ac}; }}
QScrollBar::handle:horizontal:pressed {{ background: {ac}; filter: brightness(0.9); }}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0; height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
}}
QScrollBar::corner {{ background: transparent; }}

/* Tabs */
QTabWidget::pane {{
    border: 1px solid #34353b; border-radius: 10px; padding: 6px; top: -1px; background: #1f2024;
}}
QTabWidget::tab-bar {{ alignment: left; }}
QTabBar::tab {{
    background: #2a2b30; color: #e6e6e6; border: 1px solid transparent; border-bottom: none;
    padding: 8px 14px; margin-right: 6px; margin-top: 4px; border-top-left-radius: 8px; border-top-right-radius: 8px;
}}
QTabBar::tab:selected {{ background: #24252a; color: {ac}; border-color: #34353b; margin-top: 0; }}
QTabBar::tab:hover {{ color: {ac}; }}
QTabBar::tear {{ width: 0; height: 0; }}

/* Group boxes (Settings/sections) */
QGroupBox {{
    border: 1px solid #34353b; border-radius: 10px; margin-top: 10px;
}}
QGroupBox::title {{
    subcontrol-origin: margin; subcontrol-position: top left;
    padding: 4px 8px; color: {ac}; font-weight: 600;
    background: transparent;
}}

/* Stepper - Pill shaped with shorter height */
#StepperLabel {{
    background: #24252a; 
    border: 1px solid #34353b; 
    border-radius: 16px; 
    padding: 4px 16px;
    min-width: 80px;
    min-height: 28px;
    font-weight: 500;
    color: #e1e3e8;
}}
#StepperLabel[current="true"] {{ 
    border-color: {ac}; 
    color: {ac}; 
    font-weight: 600;
}}

/* Home Page Cards */
QFrame#FeatureCard {{
    background: #24252a;
    border: 1px solid #34353b;
    border-radius: 12px;
    padding: 20px;
    min-width: 220px;
    max-width: 350px;
    min-height: 220px;
}}
QFrame#FeatureCard:hover {{
    border-color: {ac};
    background: #2a2b30;
}}
QFrame#FeatureCard:disabled {{
    opacity: 0.5;
    border: 2px solid #3a3b41;
    background: #1a1b1e;
}}
QLabel#CardIcon, QLabel#CardTitle, QLabel#CardDescription {{
    background: transparent;
}}
QLabel#WelcomeTitle, QLabel#WelcomeSubtitle, QLabel#FeaturesHeader {{
    background: transparent;
}}

/* Update prompt components */
QTextBrowser#ChangelogBrowser {{
    background: #1e1f22; border: 1px solid #34353b; border-radius: 8px; padding: 8px;
}}
QPushButton#SecondaryButton {{
    background: #2a2b30; border: 1px solid #33343a; border-radius: 8px; padding: 6px 12px;
}}
QPushButton#SecondaryButton:hover {{ border-color: {ac}; }}

/* Compact settings buttons */
QPushButton#CompactButton {{
    background: #2a2b30; border: 1px solid #33343a; border-radius: 6px; padding: 4px 10px; 
    min-height: 20px; font-size: 12px;
}}
QPushButton#CompactButton:hover {{ border-color: {ac}; background: #2c2d32; }}

/* Collapsible Section Header */
QFrame#CollapsibleHeader {{
    background: #24252a;
    border: 1px solid #34353b;
    border-radius: 8px;
    margin-bottom: 4px;
}}
QFrame#CollapsibleHeader:hover {{
    background: #2a2b30;
    border-color: {ac};
}}
"""

    def theme_qss(self, mode: str) -> str:
        """Compose full application QSS for the given theme mode.
        mode: 'light' | 'dark' | 'oled'
        """
        base = self.qss()
        ac = self._accent
        if mode == "light":
            extra = f"""
            /* Light theme - Clean Windows 11 style */
            QWidget {{ background: #f7f8fa; color: #212529; }}
            QLabel {{ background: transparent; }}
            QFrame#Sidebar {{ background: #eef0f3; border-right: 1px solid #d6dbe1; }}
            /* Flat Cards - No neuromorphic effects */
            QFrame#CategoryCard, .CategoryCard {{ 
                background: #ffffff; 
                border: 1px solid #e5e7eb; 
                border-radius: 8px; 
                padding: 12px;
            }}
            QGroupBox {{ 
                border: 1px solid #e5e7eb; 
                border-radius: 10px; 
                background: #ffffff;
            }}
            QGroupBox::title {{ color: {ac}; }}
            /* Buttons */
            QPushButton {{ 
                background: #ffffff; 
                color: #212529; 
                border: 1px solid #d6dbe1; 
                border-radius: 8px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{ 
                border-color: {ac}; 
                background: #f3f4f6; 
            }}
            QPushButton:pressed {{ background: #e5e7eb; }}
            QPushButton:disabled {{
                background: #f3f4f6;
                border: 1px solid #e5e7eb;
                color: #9ca3af;
                opacity: 0.5;
            }}
            
            /* Light Segment Buttons (Video/Audio) - Balanced 50/50 menu style */
            QPushButton#SegmentButton {{
                background: #f3f4f6;
                color: #6b7280;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                padding: 6px 12px;
                min-width: 70px;
                max-width: 100px;
                min-height: 28px;
                font-weight: 500;
                text-align: center;
            }}
            QPushButton#SegmentButton:hover {{ 
                border-color: {ac}; 
                background: #e5e7eb;
                color: #374151;
            }}
            QPushButton#SegmentButton:checked {{
                border-color: {ac};
                color: {ac};
                background: #ffffff;
                font-weight: 600;
            }}
            
            /* Inputs - ensure dropdowns are properly styled */
            QLineEdit, QComboBox, QTextEdit {{ 
                background: #ffffff; 
                color: #212529; 
                border: 1px solid #d6dbe1; 
                border-radius: 8px; 
                padding: 6px 12px;
            }}
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{ border: 2px solid {ac}; }}
            /* ComboBox dropdown styling */
            QComboBox::drop-down {{ 
                background: #f3f4f6; 
                border: none;
                border-left: 1px solid #d6dbe1; 
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
                width: 20px;
            }}
            QComboBox::down-arrow {{ 
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #6b7280;
                width: 0px;
                height: 0px;
            }}
            QComboBox::down-arrow:hover {{ border-top-color: {ac}; }}
            QComboBox QAbstractItemView {{ 
                background: #ffffff; 
                border: 1px solid #d6dbe1; 
                border-radius: 8px; 
                selection-background-color: {ac}; 
                selection-color: #ffffff;
                color: #212529;
            }}
            QComboBox QAbstractItemView::item {{ 
                background: #ffffff;
                color: #212529;
                padding: 8px 12px;
                border: none;
            }}
            QComboBox QAbstractItemView::item:hover {{ 
                background: #f3f4f6;
                color: #212529;
            }}
            QComboBox QAbstractItemView::item:selected {{ 
                background: {ac};
                color: #ffffff;
            }}
            /* Checkboxes */
            QCheckBox {{ 
                color: #212529;
                background: transparent;
            }}
            QCheckBox::indicator {{ 
                background: #ffffff; 
                border: 2px solid #d6dbe1; 
                border-radius: 4px;
                width: 16px;
                height: 16px;
            }}
            QCheckBox::indicator:hover {{ border-color: {ac}; }}
            QCheckBox::indicator:checked {{ 
                border-color: {ac}; 
                background: {ac};
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEzLjUgNEw2IDExLjVMMi41IDgiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPgo=);
            }}
            /* Lists */
            QListView, QListWidget {{ 
                background: #ffffff; 
                border: 1px solid #e5e7eb; 
                border-radius: 8px; 
            }}
            QListView::item, QListWidget::item {{ 
                color: #374151; 
                padding: 8px 12px;
                border: none;
            }}
            QListView::item:hover, QListWidget::item:hover {{ 
                background: #f3f4f6; 
            }}
            QListView::item:selected, QListWidget::item:selected {{ 
                background: {ac}; 
                color: #ffffff; 
            }}
            /* Tabs */
            QTabWidget::pane {{ 
                background: #ffffff; 
                border: 1px solid #e5e7eb; 
                border-radius: 8px;
            }}
            /* Light Theme Tabs - Reduced height */
            QTabBar::tab {{ 
                background: #f9fafb; 
                color: #6b7280; 
                border: 1px solid #e5e7eb; 
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 6px 12px;
                margin-right: 2px;
                min-height: 24px;
                font-weight: 500;
            }}
            QTabBar::tab:selected {{ 
                background: #ffffff; 
                color: {ac}; 
                border-bottom-color: #ffffff;
                font-weight: 600;
            }}
            QTabBar::tab:hover {{ 
                background: #ffffff; 
                color: {ac}; 
            }}
            /* Scrollbars */
            QScrollBar:vertical {{ 
                background: #f3f4f6; 
                width: 12px; 
                border-radius: 6px; 
            }}
            QScrollBar::handle:vertical {{ 
                background: #cbd5e1; 
                border-radius: 6px; 
                min-height: 20px; 
            }}
            QScrollBar::handle:vertical:hover {{ background: {ac}; }}
            QScrollBar:horizontal {{ 
                background: #f3f4f6; 
                height: 12px; 
                border-radius: 6px; 
            }}
            QScrollBar::handle:horizontal {{ 
                background: #cbd5e1; 
                border-radius: 6px; 
                min-width: 20px; 
            }}
            QScrollBar::handle:horizontal:hover {{ background: {ac}; }}
            QScrollBar::add-line, QScrollBar::sub-line {{ border: none; background: none; }}
            /* Thumbnails */
            QLabel#ThumbnailLabel {{ 
                background: #f3f4f6; 
                border: 1px solid #e5e7eb; 
                border-radius: 6px; 
            }}
            /* SponsorBlock ComboBox */
            QComboBox#SponsorBlockComboBox {{ 
                background: #ffffff; 
                border: 1px solid #d6dbe1; 
                border-radius: 8px; 
                padding: 6px 12px; 
                min-height: 28px; 
                color: #212529;
            }}
            QComboBox#SponsorBlockComboBox:hover {{ border-color: {ac}; }}
            QComboBox#SponsorBlockComboBox:focus {{ border: 2px solid {ac}; }}
            QComboBox#SponsorBlockComboBox QAbstractItemView {{ 
                background: #ffffff; 
                border: 1px solid #d6dbe1; 
                border-radius: 8px; 
                selection-background-color: {ac}; 
                selection-color: #ffffff;
                color: #212529;
            }}
            QComboBox#SponsorBlockComboBox QAbstractItemView::item {{ 
                background: #ffffff;
                color: #212529;
                padding: 8px 12px;
                border: none;
            }}
            QComboBox#SponsorBlockComboBox QAbstractItemView::item:hover {{ 
                background: #f3f4f6;
                color: #212529;
            }}
            QComboBox#SponsorBlockComboBox QAbstractItemView::item:selected {{ 
                background: {ac};
                color: #ffffff;
            }}
            /* Drop-down arrows & spin buttons */
            QSpinBox::up-button, QSpinBox::down-button {{ 
                background: #f3f4f6; 
                border-color: #d6dbe1; 
            }}
            QSpinBox::up-arrow {{ border-bottom-color: #6b7280; }}
            QSpinBox::down-arrow {{ border-top-color: #6b7280; }}
            /* Light Stepper - Pill shaped with shorter height */
            #StepperLabel {{ 
                background: #ffffff; 
                border: 1px solid #e5e7eb; 
                border-radius: 16px; 
                color: #6b7280; 
                padding: 4px 16px;
                min-width: 80px;
                min-height: 28px;
                font-weight: 500;
            }}
            #StepperLabel[current="true"] {{ 
                border-color: {ac}; 
                color: {ac}; 
                background: {self._rgba(ac, 0.05)};
                font-weight: 600;
            }}
            /* Update prompt */
            QTextBrowser#ChangelogBrowser {{ background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 8px; color: #374151; }}
            QPushButton#SecondaryButton {{ background: #f3f4f6; border: 1px solid #d6dbe1; border-radius: 8px; padding: 6px 12px; color: #374151; }}
            QPushButton#SecondaryButton:hover {{ border-color: {ac}; background: #eef0f3; }}
            /* Add multiple button */
            QCheckBox#ButtonLike {{ background: #f3f4f6; border: 1px solid #d6dbe1; border-radius: 8px; padding: 8px 12px; color: #374151; }}
            QCheckBox#ButtonLike:hover {{ border-color: {ac}; background: #eef0f3; }}
            QCheckBox#ButtonLike:checked {{ border-color: {ac}; background: {self._rgba(ac, 0.1)}; color: {ac}; }}
            /* Compact buttons */
            QPushButton#CompactButton {{ background: #f3f4f6; border: 1px solid #d6dbe1; border-radius: 6px; padding: 4px 10px; min-height: 20px; font-size: 12px; color: #374151; }}
            QPushButton#CompactButton:hover {{ border-color: {ac}; background: #eef0f3; }}
            
            /* Collapsible Section Header - Light */
            QFrame#CollapsibleHeader {{
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                margin-bottom: 4px;
            }}
            QFrame#CollapsibleHeader:hover {{
                background: #f9fafb;
                border-color: {ac};
            }}
            
            /* Home Page Cards - Light */
            QFrame#FeatureCard {{
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
                padding: 20px;
                min-width: 220px;
                max-width: 350px;
                min-height: 220px;
            }}
            QFrame#FeatureCard:hover {{
                border-color: {ac};
                background: #f9fafb;
            }}
            QFrame#FeatureCard:disabled {{
                opacity: 0.5;
                border: 2px solid #d1d5db;
                background: #f3f4f6;
            }}
            QLabel#CardIcon, QLabel#CardTitle, QLabel#CardDescription {{
                background: transparent;
            }}
            QLabel#WelcomeTitle, QLabel#WelcomeSubtitle, QLabel#FeaturesHeader {{
                background: transparent;
            }}
            """
        elif mode == "oled":
            extra = f"""
            /* OLED theme - pure black */
            QWidget {{ background: #000000; color: #f8f9fa; }}
            QLabel {{ background: transparent; }}
            QCheckBox {{ background: transparent; }}
            QFrame#Sidebar {{ background: #000000; border-right: 1px solid #212529; }}
            /* Flat OLED Cards */
            QFrame#CategoryCard, .CategoryCard {{ 
                background: #0a0a0a; 
                border: 1px solid #212529; 
                border-radius: 8px; 
                padding: 12px;
            }}
            QPushButton {{ background: #111111; border: 1px solid #343a40; color: #f8f9fa; }}
            QPushButton:hover {{ background: #1a1a1a; border-color: {ac}; }}
            QPushButton:disabled {{
                background: #0a0a0a;
                border: 1px solid #1a1a1a;
                color: #444444;
                opacity: 0.5;
            }}
            
            /* OLED Segment Buttons (Video/Audio) - Balanced 50/50 menu style */
            QPushButton#SegmentButton {{
                background: #0a0a0a;
                color: #adb5bd;
                border: 1px solid #2a2a2a;
                border-radius: 6px;
                padding: 6px 12px;
                min-width: 70px;
                max-width: 100px;
                min-height: 28px;
                font-weight: 500;
                text-align: center;
            }}
            QPushButton#SegmentButton:hover {{ 
                border-color: {ac}; 
                background: #1a1a1a;
                color: #ffffff;
            }}
            QPushButton#SegmentButton:checked {{
                border-color: {ac};
                color: {ac};
                background: #111111;
                font-weight: 600;
            }}
            QLineEdit, QComboBox, QTextEdit {{ background: #111111; border: 1px solid #343a40; color: #f8f9fa; }}
            QListView, QListWidget {{ background: #0a0a0a; border: 1px solid #212529; border-radius: 8px; }}
            QListView::item:hover, QListWidget::item:hover {{ background: #111111; border: 1px solid #343a40; }}
            QLabel#ThumbnailLabel {{ background: #111111; border: 1px solid #343a40; border-radius: 6px; }}
            /* SponsorBlock ComboBox */
            QComboBox#SponsorBlockComboBox {{ background: #111111; border: 1px solid #343a40; border-radius: 8px; padding: 6px 12px; min-height: 28px; }}
            QComboBox#SponsorBlockComboBox:hover {{ border-color: {ac}; }}
            QComboBox#SponsorBlockComboBox:focus {{ border: 2px solid {ac}; }}
            QComboBox#SponsorBlockComboBox QAbstractItemView {{ background: #111111; border: 1px solid #343a40; border-radius: 8px; selection-background-color: {ac}; selection-color: #ffffff; }}
            /* Drop-down arrows & spin buttons */
            QComboBox::drop-down {{ background: #1a1a1a; border-left-color: #343a40; }}
            QComboBox::down-arrow {{ border-top-color: #adb5bd; }}
            QComboBox::down-arrow:hover {{ border-top-color: {ac}; }}
            QSpinBox::up-button, QSpinBox::down-button {{ background: #1a1a1a; border-color: #343a40; }}
            QSpinBox::up-arrow {{ border-bottom-color: #adb5bd; }}
            QSpinBox::down-arrow {{ border-top-color: #adb5bd; }}
            /* OLED Stepper - Pill shaped with shorter height */
            #StepperLabel {{ 
                background: #0a0a0a; 
                border: 1px solid #2a2a2a; 
                border-radius: 16px; 
                color: #e2e8f0; 
                padding: 4px 16px;
                min-width: 80px;
                min-height: 28px;
                font-weight: 500;
            }}
            #StepperLabel[current="true"] {{ 
                border-color: {ac}; 
                color: {ac}; 
                font-weight: 600;
            }}
            /* Update prompt */
            QTextBrowser#ChangelogBrowser {{ background: #0a0a0a; border: 1px solid #212529; border-radius: 8px; padding: 8px; color: #f8f9fa; }}
            QPushButton#SecondaryButton {{ background: #111111; border: 1px solid #343a40; border-radius: 8px; padding: 6px 12px; color: #f8f9fa; }}
            QPushButton#SecondaryButton:hover {{ border-color: {ac}; background: #1a1a1a; }}
            /* Add multiple button */
            QCheckBox#ButtonLike {{ background: #111111; border: 1px solid #343a40; border-radius: 8px; padding: 8px 12px; color: #f8f9fa; }}
            QCheckBox#ButtonLike:hover {{ border-color: {ac}; background: #1a1a1a; }}
            QCheckBox#ButtonLike:checked {{ border-color: {ac}; background: #2a2a2a; color: {ac}; }}
            /* Compact buttons */
            QPushButton#CompactButton {{ background: #111111; border: 1px solid #343a40; border-radius: 6px; padding: 4px 10px; min-height: 20px; font-size: 12px; color: #f8f9fa; }}
            QPushButton#CompactButton:hover {{ border-color: {ac}; background: #1a1a1a; }}
            """
        else:
            # Default dark theme (also used as fallback)
            extra = f"""
            /* Dark theme */
            QWidget {{ background: #1c1d20; color: #f0f0f0; }}
            QFrame#Sidebar {{ background: #202125; border-right: 1px solid #2e2f33; }}
            /* Flat Dark Cards */
            QFrame#CategoryCard, .CategoryCard {{ 
                background: #1e1f22; 
                border: 1px solid #2d2f33; 
                border-radius: 8px; 
                padding: 12px;
            }}
            
            /* Dark Segment Buttons (Video/Audio) - Balanced 50/50 menu style */
            QPushButton#SegmentButton {{
                background: rgba(255,255,255,0.05);
                color: #b0b2b8;
                border: 1px solid #3a3b40;
                border-radius: 6px;
                padding: 6px 12px;
                min-width: 70px;
                max-width: 100px;
                min-height: 28px;
                font-weight: 500;
                text-align: center;
            }}
            QPushButton#SegmentButton:hover {{ 
                border-color: {ac}; 
                background: rgba(255,255,255,0.08);
                color: #e1e3e8;
            }}
            QPushButton#SegmentButton:checked {{
                border-color: {ac};
                color: {ac};
                background: rgba(255,255,255,0.1);
                font-weight: 600;
            }}
            
            QLabel#ThumbnailLabel {{ background: #111111; border: 1px solid #333333; border-radius: 6px; }}
            /* SponsorBlock ComboBox */
            QComboBox#SponsorBlockComboBox {{ background: #1f1f23; border: 1px solid #3a3b40; border-radius: 8px; padding: 6px 12px; min-height: 28px; }}
            QComboBox#SponsorBlockComboBox:hover {{ border-color: {ac}; }}
            QComboBox#SponsorBlockComboBox:focus {{ border: 2px solid {ac}; }}
            QComboBox#SponsorBlockComboBox QAbstractItemView {{ background: #1f1f23; border: 1px solid #3a3b40; border-radius: 8px; selection-background-color: {ac}; selection-color: #ffffff; }}
            /* Drop-down arrows & spin buttons */
            QComboBox::drop-down {{ background: #2a2b30; border-left-color: #3a3b40; }}
            QComboBox::down-arrow {{ border-top-color: #b0b2b8; }}
            QComboBox::down-arrow:hover {{ border-top-color: {ac}; }}
            QSpinBox::up-button, QSpinBox::down-button {{ background: rgba(255,255,255,0.08); border-color: #3a3b40; }}
            QSpinBox::up-arrow {{ border-bottom-color: #b0b2b8; }}
            QSpinBox::down-arrow {{ border-top-color: #b0b2b8; }}
            /* Dark Stepper - Pill shaped with shorter height */
            #StepperLabel {{ 
                background: rgba(255,255,255,0.06); 
                border: 1px solid #3a3b40; 
                border-radius: 16px; 
                color: #e1e3e8; 
                padding: 4px 16px;
                min-width: 80px;
                min-height: 28px;
                font-weight: 500;
            }}
            #StepperLabel[current="true"] {{ 
                border-color: {ac}; 
                color: {ac}; 
                background: {self._rgba(ac, 0.1)};
                font-weight: 600;
            }}
            /* Update prompt */
            QTextBrowser#ChangelogBrowser {{ background: #1e1f22; border: 1px solid #2d2f33; border-radius: 8px; padding: 8px; color: #e1e3e8; }}
            QPushButton#SecondaryButton {{ background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.15); border-radius: 8px; padding: 6px 12px; color: #e1e3e8; }}
            QPushButton#SecondaryButton:hover {{ border-color: {ac}; background: rgba(255,255,255,0.12); }}
            /* Add multiple button */
            QCheckBox#ButtonLike {{ background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.15); border-radius: 8px; padding: 8px 12px; color: #e1e3e8; }}
            QCheckBox#ButtonLike:hover {{ border-color: {ac}; background: rgba(255,255,255,0.12); }}
            QCheckBox#ButtonLike:checked {{ border-color: {ac}; background: rgba(255,255,255,0.1); color: {ac}; }}
            /* Compact buttons */
            QPushButton#CompactButton {{ background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.15); border-radius: 6px; padding: 4px 10px; min-height: 20px; font-size: 12px; color: #e1e3e8; }}
            QPushButton#CompactButton:hover {{ border-color: {ac}; background: rgba(255,255,255,0.12); }}
            
            /* Collapsible Section Header - OLED */
            QFrame#CollapsibleHeader {{
                background: #0a0a0a;
                border: 1px solid #212529;
                border-radius: 8px;
                margin-bottom: 4px;
            }}
            QFrame#CollapsibleHeader:hover {{
                background: #111111;
                border-color: {ac};
            }}
            
            /* Home Page Cards - OLED */
            QFrame#FeatureCard {{
                background: #0a0a0a;
                border: 1px solid #212529;
                border-radius: 12px;
                padding: 20px;
                min-width: 220px;
                max-width: 350px;
                min-height: 220px;
            }}
            QFrame#FeatureCard:hover {{
                border-color: {ac};
                background: #111111;
            }}
            QFrame#FeatureCard:disabled {{
                opacity: 0.5;
                border: 2px solid #2a2a2a;
                background: #050505;
            }}
            QLabel#CardIcon, QLabel#CardTitle, QLabel#CardDescription {{
                background: transparent;
            }}
            QLabel#WelcomeTitle, QLabel#WelcomeSubtitle, QLabel#FeaturesHeader {{
                background: transparent;
            }}
            
            /* Lists */
            QListView, QListWidget {{ background: #1e1f22; border: 1px solid #2d2f33; border-radius: 8px; }}
            QListView::item:hover, QListWidget::item:hover {{ background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.15); }}
            QListView::item:selected, QListWidget::item:selected {{ background: {ac}; color: #ffffff; border: 1px solid {ac}; }}
            """

        return base + "\n" + extra
