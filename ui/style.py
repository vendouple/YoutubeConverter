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

/* Segmented buttons (Audio/Video) */
QPushButton#SegmentButton {{
    background: #232428;
    border: 1px solid #34353b;
    border-radius: 8px;
    padding: 6px 10px;
}}
QPushButton#SegmentButton:hover {{ border-color: {ac}; }}
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

/* Win11-like CheckBox (check mark box) */
QCheckBox {{
    spacing: 6px; /* space between box and label */
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

/* Stepper */
#StepperLabel {{
    background: #24252a; border: 1px solid #34353b; border-radius: 16px; padding: 6px 12px;
}}
#StepperLabel[current="true"] {{ border-color: {ac}; color: {ac}; }}
"""
