from typing import List, Dict
from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
    QSize,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
    QAbstractAnimation,
    QEvent,
    QObject,
)
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QPushButton,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QButtonGroup,
    QFrame,
    QGraphicsOpacityEffect,
    QCheckBox,
    QToolButton,
    QSizePolicy,
)
from PyQt6.QtGui import QIcon, QPixmap, QStandardItemModel, QStandardItem  #

from core.settings import AppSettings, SettingsManager
from core.yt_manager import InfoFetcher


class Step3QualityWidget(QWidget):
    qualityConfirmed = pyqtSignal(dict)
    backRequested = pyqtSignal()

    def __init__(self, settings: AppSettings):
        super().__init__()
        self.settings = settings
        self.items: List[Dict] = []
        self._meta_fetchers: List[InfoFetcher] = []
        self._url_index: Dict[str, int] = {}

        # ADDED: selection state
        self._apply_all = True
        self._global_sel = {
            "kind": self.settings.defaults.kind,
            "format": self.settings.defaults.format,
            "quality": "best",
        }
        self._per_item_sel: Dict[int, Dict[str, str]] = {}

        # SponsorBlock presets
        self._sb_presets = [
            ("Sponsor only", ["sponsor"]),
            ("Sponsor + selfpromo", ["sponsor", "selfpromo"]),
            (
                "Common (sponsor,selfpromo,interaction)",
                ["sponsor", "selfpromo", "interaction"],
            ),
            (
                "Everything",
                [
                    "sponsor",
                    "intro",
                    "outro",
                    "selfpromo",
                    "interaction",
                    "music_offtopic",
                    "preview",
                    "filler",
                ],
            ),
        ]

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # Header
        self.header = QLabel("Converter options")
        self.header.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        font = self.header.font()
        font.setPointSize(font.pointSize() + 1)
        font.setBold(True)
        self.header.setFont(font)
        root.addWidget(self.header)

        # Content: preview (left) + options (right)
        content = QHBoxLayout()
        content.setSpacing(10)
        root.addLayout(content, 1)

        # Left: preview
        self.preview = QListWidget()
        self.preview.setIconSize(QSize(96, 54))
        self.preview.setAlternatingRowColors(False)
        self.preview.setFrameShape(QFrame.Shape.NoFrame)
        self.preview.setSpacing(4)
        self.preview.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        content.addWidget(self.preview, 2)

        # Accent vertical separator between list and options
        vsep = QFrame()
        vsep.setObjectName("AccentVLine")
        vsep.setFrameShape(QFrame.Shape.VLine)
        vsep.setLineWidth(1)
        vsep.setFixedWidth(1)
        content.addWidget(vsep)

        # Right: options panel
        right = QVBoxLayout()
        right.setSpacing(8)
        content.addLayout(right, 1)

        # ADDED: apply-to-all toggle
        self.chk_apply_all = QCheckBox("Apply to all")
        self.chk_apply_all.setChecked(True)
        right.addWidget(self.chk_apply_all)

        # Segmented kind selector
        seg_row = QHBoxLayout()
        seg_row.setSpacing(6)
        self.btn_audio = QPushButton("Audio")
        self.btn_audio.setCheckable(True)
        self.btn_audio.setObjectName("SegmentButton")
        self.btn_video = QPushButton("Video")
        self.btn_video.setCheckable(True)
        self.btn_video.setObjectName("SegmentButton")
        self.kind_group = QButtonGroup(self)
        self.kind_group.setExclusive(True)
        self.kind_group.addButton(self.btn_audio)
        self.kind_group.addButton(self.btn_video)
        if self.settings.defaults.kind == "audio":
            self.btn_audio.setChecked(True)
        else:
            self.btn_video.setChecked(True)
        seg_row.addWidget(self.btn_audio)
        seg_row.addWidget(self.btn_video)
        seg_row.addStretch(1)
        right.addLayout(seg_row)

        # Format
        self.cmb_format = QComboBox()
        self.cmb_format.setEditable(False)
        right.addWidget(self._labeled("Format:", self.cmb_format))

        # Quality
        self.cmb_quality = QComboBox()
        right.addWidget(self._labeled("Quality:", self.cmb_quality))

        adv_toggle_row = QHBoxLayout()
        adv_toggle_row.setContentsMargins(0, 0, 0, 0)
        self.btn_adv = QToolButton()
        self.btn_adv.setText("Advanced")
        self.btn_adv.setCheckable(True)
        self.btn_adv.setChecked(False)
        self.btn_adv.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_adv.setArrowType(Qt.ArrowType.RightArrow)
        self.btn_adv.toggled.connect(
            lambda on: self.btn_adv.setArrowType(
                Qt.ArrowType.DownArrow if on else Qt.ArrowType.RightArrow
            )
        )
        adv_toggle_row.addWidget(self.btn_adv, 0, Qt.AlignmentFlag.AlignLeft)
        right.addLayout(adv_toggle_row)

        self.adv_panel = QFrame()
        self.adv_panel.setFrameShape(QFrame.Shape.NoFrame)
        self.adv_panel.setVisible(False)
        adv_lay = QVBoxLayout(self.adv_panel)
        adv_lay.setContentsMargins(0, 0, 0, 0)
        adv_lay.setSpacing(8)
        self.btn_adv.toggled.connect(self.adv_panel.setVisible)
        right.addWidget(self.adv_panel)
        self.adv_panel.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )

        # SponsorBlock inside Advanced
        self.chk_sb = QCheckBox("Remove segments with SponsorBlock")
        self.chk_sb.setChecked(
            bool(getattr(self.settings.defaults, "sponsorblock_enabled", False))
        )
        adv_lay.addWidget(self.chk_sb)

        self.cmb_sb_categories = QComboBox()
        self.cmb_sb_categories.setEditable(False)
        self.cmb_sb_categories.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.cmb_sb_categories.setToolTip(
            "Select categories to cut from the output using SponsorBlock.\n"
            "Warning: 'filler' is very aggressive; avoid enabling by default."
        )
        accent = getattr(self.settings.ui, "accent_color_hex", "#F28C28") or "#F28C28"
        self.cmb_sb_categories.setMinimumWidth(0)
        self.cmb_sb_categories.setMinimumContentsLength(12)
        self.cmb_sb_categories.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.cmb_sb_categories.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
        )
        self.cmb_sb_categories.setStyleSheet(
            f"""
            QComboBox {{
                background: #1f1f23;
                border: 1px solid #3a3b40;
                border-radius: 8px;
                padding: 6px 12px;
                min-height: 28px;
            }}
            QComboBox:hover {{
                border-color: {accent};
            }}
            QComboBox:focus {{
                border: 2px solid {accent};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 28px;
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background: #1f1f23;
                border: 1px solid #3a3b40;
                border-radius: 8px;
                outline: none;
                selection-background-color: #2b2c31;
                padding: 4px;
            }}
            """
        )

        m = QStandardItemModel(self.cmb_sb_categories)
        self.cmb_sb_categories.setModel(m)
        self._sb_options = [
            ("sponsor", "sponsor"),
            ("selfpromo", "selfpromo"),
            ("interaction", "interaction"),
            ("intro", "intro"),
            ("outro", "outro"),
            ("preview", "preview"),
            ("filler", "filler"),
            (
                "non_music",
                "music_offtopic",
            ),
        ]
        for label, _key in self._sb_options:
            it = QStandardItem(label)
            it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            it.setData(Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
            m.appendRow(it)

        def _update_sb_display():
            sel = self._get_sb_categories()
            if not sel:
                self.cmb_sb_categories.setCurrentText("None (click to choose)")
            else:
                labels = [lbl for (lbl, key) in self._sb_options if key in sel]
                self.cmb_sb_categories.setCurrentText(", ".join(labels))

        # Add debug output
        def _toggle_item(idx):
            it = self.cmb_sb_categories.model().item(idx)
            st = it.checkState()
            it.setCheckState(
                Qt.CheckState.Unchecked
                if st == Qt.CheckState.Checked
                else Qt.CheckState.Checked
            )
            _update_sb_display()
            self._persist_sb_settings()
            # Debug output of categories
            print(f"SponsorBlock categories selected: {self._get_sb_categories()}")

        self.cmb_sb_categories.view().pressed.connect(lambda mi: _toggle_item(mi.row()))
        _update_sb_display()
        adv_lay.addWidget(self._labeled("Segments to remove:", self.cmb_sb_categories))

        # Enable/disable SB controls per toggle
        def _set_sb_enabled(on: bool):
            self.cmb_sb_categories.setEnabled(on)

        _set_sb_enabled(self.chk_sb.isChecked())
        self.chk_sb.toggled.connect(_set_sb_enabled)

        right.addStretch(1)

        # Footer bar with Back (left) and Next (right) - consistent across steps
        footer = QHBoxLayout()
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        root.addWidget(sep)
        self.btn_back = QPushButton("Back")
        self.btn_next = QPushButton("Next")
        self.btn_next.setObjectName("PrimaryButton")
        footer.addWidget(self.btn_back)
        footer.addStretch(1)
        footer.addWidget(self.btn_next)
        root.addLayout(footer)

        # Defaults
        self._apply_kind_defaults()

        # Signals
        self.btn_back.clicked.connect(self.backRequested.emit)
        self.btn_next.clicked.connect(self._confirm)
        self.btn_audio.toggled.connect(self._on_kind_toggled)
        self.btn_video.toggled.connect(self._on_kind_toggled)
        self.cmb_format.currentTextChanged.connect(self._on_controls_changed)
        self.cmb_quality.currentTextChanged.connect(self._on_controls_changed)
        self.chk_apply_all.toggled.connect(self._apply_all_toggled)
        self.preview.currentRowChanged.connect(self._on_preview_row_changed)
        self.chk_sb.toggled.connect(self._persist_sb_settings)

        # Timer (kept but unused for background refetch)
        self._refetch_timer = QTimer(self)
        self._refetch_timer.setSingleShot(True)
        self._refetch_timer.timeout.connect(self._start_refetch_missing)

        # Block mouse wheel on comboboxes to avoid accidental changes
        class _NoWheelFilter(QObject):
            def eventFilter(self, obj, event):
                if event.type() == QEvent.Type.Wheel:
                    return True
                return super().eventFilter(obj, event)

        self._nowheel = _NoWheelFilter(self)
        for w in (self.cmb_format, self.cmb_quality):
            w.installEventFilter(self._nowheel)
        # Apply EZ Mode tweaks on construction
        try:
            self.apply_ez_mode(self.settings)
        except Exception:
            pass

    # Valid formats by kind
    def _formats_for_kind(self, kind: str) -> List[str]:
        return (
            ["mp3", "m4a", "flac", "wav", "opus"]
            if kind == "audio"
            else ["mp4", "mkv", "webm"]
        )

    # Default format by kind
    def _default_format_for_kind(self, kind: str) -> str:
        return "mp3" if kind == "audio" else "mp4"

    # Get current selection context (global or current item)
    def _current_context_sel(self) -> Dict[str, str]:
        if self._apply_all or self.preview.currentRow() < 0:
            return dict(self._global_sel)
        idx = self.preview.currentRow()
        return dict(self._per_item_sel.get(idx, self._global_sel))

    # Repopulate formats for current kind and pick a valid selection
    def _apply_kind_defaults(self):
        kind = "audio" if self.btn_audio.isChecked() else "video"
        formats = self._formats_for_kind(kind)
        self.cmb_format.blockSignals(True)
        try:
            self.cmb_format.clear()
            self.cmb_format.addItems(formats)
            ctx = self._current_context_sel()
            # Prefer previously chosen format if valid for this kind; else fallback default
            target_fmt = ctx.get("format")
            if target_fmt not in formats:
                # If settings default matches this kind and is valid, use that; else per-kind default
                def_fmt = getattr(self.settings.defaults, "format", "") or ""
                target_fmt = (
                    def_fmt
                    if def_fmt in formats
                    else self._default_format_for_kind(kind)
                )
            self.cmb_format.setCurrentText(target_fmt)
        finally:
            self.cmb_format.blockSignals(False)
        # Also refresh quality options for the new kind
        self._populate_quality_options()

    def _on_kind_toggled(self, checked: bool):
        if not checked:
            return
        kind = "audio" if self.btn_audio.isChecked() else "video"
        formats = self._formats_for_kind(kind)
        ctx = self._current_context_sel()
        # Adjust format if no longer valid
        fmt = ctx.get("format")
        if fmt not in formats:
            fmt = self._default_format_for_kind(kind)
        # Push into selection (global or per-item)
        if self._apply_all or self.preview.currentRow() < 0:
            self._global_sel.update({"kind": kind, "format": fmt})
        else:
            idx = self.preview.currentRow()
            sel = self._per_item_sel.get(idx, dict(self._global_sel))
            sel.update({"kind": kind, "format": fmt})
            self._per_item_sel[idx] = sel
        # Repopulate UI for this kind and set values
        self._apply_kind_defaults()
        self.cmb_format.setCurrentText(fmt)
        # Ensure quality list matches kind; keep current quality if present else "best"
        q = self.cmb_quality.currentText().strip() or "best"
        if self.cmb_quality.findText(q) < 0:
            self.cmb_quality.setCurrentText("best")
        # Propagate to warnings and selection
        self._on_controls_changed()
        self._update_warnings()

    def set_items(self, items: List[Dict]):
        self.items = items
        self._url_index = {}
        for i, it in enumerate(items):
            u = it.get("webpage_url") or it.get("url")
            if u:
                self._url_index[u] = i

        # Reset overrides when new items set
        self._per_item_sel.clear()
        self.chk_apply_all.setChecked(True)
        self._apply_all = True
        self.chk_apply_all.setVisible(len(items) > 1)

        self.header.setText(
            f"Selected {len(items)} item(s). Choose output format and quality."
        )
        self.preview.clear()
        for it in items:
            title = it.get("title") or "Untitled"
            lw = QListWidgetItem(title)
            pix = self._load_thumb(it)
            if pix:
                lw.setIcon(QIcon(pix))
            self.preview.addItem(lw)

        # Fade-in transition for a clean update
        eff = QGraphicsOpacityEffect(self.preview)
        self.preview.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity", self)
        anim.setDuration(200)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
        self._populate_quality_options()
        self._cleanup_fetchers()
        if hasattr(self, "_refetch_timer"):
            self._refetch_timer.stop()

        # Initialize warnings and load controls for context
        self._update_warnings()
        self._load_controls_from_context()

        try:
            self._set_sb_categories(
                list(getattr(self.settings.defaults, "sponsorblock_categories", []))
            )
        except Exception:
            pass

    def _load_thumb(self, it: Dict):
        url = it.get("thumbnail") or (it.get("thumbnails") or [{}])[-1].get("url")
        if not url:
            return None
        try:
            import requests, time

            for _ in range(3):
                try:
                    r = requests.get(url, timeout=6)
                    if r.ok:
                        pix = QPixmap()
                        if pix.loadFromData(r.content):
                            return pix
                except Exception:
                    pass
                time.sleep(0.2)
        except Exception:
            return None
        return None

    # Helpers for multi-select SB categories
    def _set_sb_categories(self, cats: List[str]):
        try:
            m: QStandardItemModel = self.cmb_sb_categories.model()
            by_key = {k for k in (cats or [])}
            for row in range(m.rowCount()):
                it: QStandardItem = m.item(row)
                label = it.text()
                key = next((k for (lbl, k) in self._sb_options if lbl == label), None)
                it.setCheckState(
                    Qt.CheckState.Checked if key in by_key else Qt.CheckState.Unchecked
                )
            # refresh display text
            labels = [lbl for (lbl, key) in self._sb_options if key in by_key]
            self.cmb_sb_categories.setCurrentText(
                ", ".join(labels) if labels else "None"
            )
        except Exception:
            pass

    def _get_sb_categories(self) -> List[str]:
        try:
            m: QStandardItemModel = self.cmb_sb_categories.model()
            res = []
            for row in range(m.rowCount()):
                it: QStandardItem = m.item(row)
                if it.checkState() == Qt.CheckState.Checked:
                    lbl = it.text()
                    key = next((k for (l, k) in self._sb_options if l == lbl), None)
                    if key:
                        res.append(key)
            # Debug print current categories when fetched
            print(f"SponsorBlock categories being used: {res}")
            return res
        except Exception as e:
            print(f"Error getting SponsorBlock categories: {e}")
            return []

    def _apply_all_toggled(self, checked: bool):
        self._apply_all = bool(checked)
        self._load_controls_from_context()
        self._update_warnings()

    def _on_preview_row_changed(self, row: int):
        self._load_controls_from_context()

    def _on_controls_changed(self, *_):
        kind = "audio" if self.btn_audio.isChecked() else "video"
        fmt = self.cmb_format.currentText().strip()
        q = self.cmb_quality.currentText().strip() or "best"
        if self._apply_all or self.preview.currentRow() < 0:
            self._global_sel = {"kind": kind, "format": fmt, "quality": q}
        else:
            idx = self.preview.currentRow()
            self._per_item_sel[idx] = {"kind": kind, "format": fmt, "quality": q}
        self._update_warnings()

    # ADDED: reflect context (apply-all or selected item) into controls
    def _load_controls_from_context(self):
        if self._apply_all or self.preview.currentRow() < 0:
            sel = self._global_sel
        else:
            idx = self.preview.currentRow()
            sel = self._per_item_sel.get(idx, self._global_sel)
        # Apply kind buttons
        if sel["kind"] == "audio":
            self.btn_audio.setChecked(True)
        else:
            self.btn_video.setChecked(True)
        # Repopulate format list for this kind, then set value
        self._apply_kind_defaults()
        self.cmb_format.setCurrentText(sel["format"])
        # Set quality
        if self.cmb_quality.findText(sel["quality"]) < 0:
            self.cmb_quality.addItem(sel["quality"])
        self.cmb_quality.setCurrentText(sel["quality"])
        enable = True if (self._apply_all or self.preview.currentRow() >= 0) else False
        for w in (self.btn_audio, self.btn_video, self.cmb_format, self.cmb_quality):
            w.setEnabled(enable)

    def _update_warnings(self):
        default_label = f"{self._global_sel['kind'].capitalize()}-{self._global_sel['format']}-{self._global_sel['quality']}"
        per_item_mode = not self._apply_all
        for i in range(self.preview.count()):
            it = self.preview.item(i)
            base_text = it.text().split(" ⚠")[0]
            if per_item_mode and i not in self._per_item_sel:
                it.setText(base_text + " ⚠")
                it.setToolTip(f"Will use default: {default_label}")
            else:
                it.setText(base_text)
                it.setToolTip("")

    def _populate_quality_options(self):
        self.cmb_quality.clear()
        default_v = ["best", "2160p", "1440p", "1080p", "720p", "480p", "360p"]
        default_a = ["best", "320k", "256k", "192k", "160k", "128k"]

        if not self.items:
            self.cmb_quality.addItems(
                default_a if self.btn_audio.isChecked() else default_v
            )
            return

        # Single-item special handling
        if len(self.items) == 1 and not self._has_formats(self.items[0]):
            self.cmb_quality.addItems(["best", "worse"])
            return

        fmts_lists = [
            it.get("formats") or [] for it in self.items if self._has_formats(it)
        ]
        if self.btn_audio.isChecked():
            abrs = sorted(
                {
                    int(f.get("abr"))
                    for fmts in fmts_lists
                    for f in fmts
                    if f.get("abr") and f.get("acodec") != "none"
                },
                reverse=True,
            )
            opts = ["best"] + [f"{a}k" for a in abrs] if abrs else default_a
            self.cmb_quality.addItems(opts)
        else:
            heights = sorted(
                {
                    int(f.get("height"))
                    for fmts in fmts_lists
                    for f in fmts
                    if f.get("height") and f.get("vcodec") != "none"
                },
                reverse=True,
            )
            opts = ["best"] + [f"{h}p" for h in heights] if heights else default_v
            self.cmb_quality.addItems(opts)

    def _start_refetch_missing(self):
        self._cleanup_fetchers()
        return

    def _cleanup_fetchers(self):
        for f in self._meta_fetchers:
            try:
                f.finished_ok.disconnect()
            except Exception:
                pass
            try:
                f.finished_fail.disconnect()
            except Exception:
                pass
        self._meta_fetchers.clear()

    # Optimized helper to check formats
    def _has_formats(self, it: Dict) -> bool:
        try:
            fmts = it.get("formats")
            return bool(fmts and isinstance(fmts, list) and len(fmts) > 0)
        except Exception:
            return False

    # Optimized persist method (no API key)
    def _persist_sb_settings(self, *_):
        try:
            self.settings.defaults.sponsorblock_enabled = bool(self.chk_sb.isChecked())
            self.settings.defaults.sponsorblock_categories = list(
                self._get_sb_categories()
            )
            SettingsManager().save(self.settings)
        except Exception:
            pass

    def _confirm(self):
        if hasattr(self, "_refetch_timer"):
            self._refetch_timer.stop()
        self._cleanup_fetchers()
        kind = "audio" if self.btn_audio.isChecked() else "video"
        fmt = self.cmb_format.currentText().strip()
        quality = self.cmb_quality.currentText().strip() or "best"
        self._global_sel = {"kind": kind, "format": fmt, "quality": quality}

        # Gather SponsorBlock prefs (global)
        sb_enabled = bool(self.chk_sb.isChecked())
        sb_cats = self._get_sb_categories()

        # Log SponsorBlock settings for debugging
        print(f"SponsorBlock enabled: {sb_enabled}")
        print(f"SponsorBlock categories: {sb_cats}")

        items_aug: List[Dict] = []
        for i, it in enumerate(self.items):
            d = dict(it)
            if i in self._per_item_sel:
                sel = self._per_item_sel[i]
                d["desired_kind"] = sel["kind"]
                d["desired_format"] = sel["format"]
                d["desired_quality"] = sel["quality"]
            d["sb_enabled"] = sb_enabled
            d["sb_categories"] = sb_cats
            items_aug.append(d)

        # Persist last chosen kind/format and SB defaults
        self.settings.defaults.kind = self._global_sel["kind"]
        self.settings.defaults.format = self._global_sel["format"]
        self._persist_sb_settings()

        self.qualityConfirmed.emit(
            {
                "items": items_aug,
                "kind": self._global_sel["kind"],
                "format": self._global_sel["format"],
                "quality": self._global_sel["quality"],
            }
        )

    # Minor copy tweaks
    def _labeled(self, text: str, w: QWidget) -> QWidget:
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lab = QLabel(text)
        lay.addWidget(lab)
        lay.addWidget(w, 1)
        return row

    def apply_ez_mode(self, settings: AppSettings | None = None):
        try:
            if settings is not None:
                self.settings = settings
            ez = getattr(self.settings, "ez", None)
            hide_adv = (
                bool(getattr(ez, "hide_advanced_quality", False)) if ez else False
            )
            # Hide the Advanced toggle and panel entirely if requested
            self.btn_adv.setVisible(not hide_adv)
            self.adv_panel.setVisible(False if hide_adv else self.btn_adv.isChecked())
        except Exception:
            pass
