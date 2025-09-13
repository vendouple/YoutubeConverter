import json
import os
from dataclasses import dataclass, asdict, field
from typing import List, Optional

# Reuse model layer schedule/action enums for unified update config
try:
    from core.models import (
        UpdateSchedule,
        UpdateCadence,
        UpdateAction,
        AppUpdateConfig,
        YTDLPUpdateConfig,
    )
except Exception:
    # Fallback lightweight stand-ins (should not persist long term)
    from enum import Enum
    from dataclasses import dataclass as _dc, field as _field

    class UpdateCadence(str, Enum):
        OFF = "off"
        LAUNCH = "launch"
        DAILY = "daily"
        WEEKLY = "weekly"
        MONTHLY = "monthly"

    class UpdateAction(str, Enum):
        NO_CHECK = "no_check"
        PROMPT = "prompt"
        AUTO = "auto"

    @_dc
    class UpdateSchedule:
        cadence: UpdateCadence = UpdateCadence.OFF
        last_check_ts: Optional[float] = None

    @_dc
    class AppUpdateConfig:
        schedule: UpdateSchedule = _field(default_factory=UpdateSchedule)
        action: UpdateAction = UpdateAction.PROMPT

    @_dc
    class YTDLPUpdateConfig:
        enabled: bool = True
        schedule: UpdateSchedule = _field(
            default_factory=lambda: UpdateSchedule(UpdateCadence.DAILY)
        )


def _user_config_dir() -> str:
    base = os.getenv("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "YoutubeConverter")


APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(APP_DIR)
# Old location (legacy)
LEGACY_SETTINGS_PATH = os.path.join(ROOT_DIR, "settings.json")
# Per-user location
SETTINGS_DIR = _user_config_dir()
SETTINGS_PATH = os.path.join(SETTINGS_DIR, "settings.json")


@dataclass
class UISettings:
    auto_advance: bool = True
    reset_after_downloads: bool = True
    accent_color_hex: str = "#F28C28"
    auto_fetch_urls: bool = True
    auto_search_text: bool = True
    live_search: bool = True
    search_debounce_seconds: int = 3
    fast_paste_enabled: bool = True
    quality_refetch_seconds: int = 1
    background_metadata_enabled: bool = True
    auto_clear_on_success: bool = True
    # Theme persistence
    theme_mode: str = "system"  # system|light|dark|oled


# Hidden (For first start only)
@dataclass
class DefaultsSettings:
    kind: str = "audio"
    format: str = "mp3"
    # SponsorBlock defaults (remember last config)
    sponsorblock_enabled: bool = False
    sponsorblock_categories: List[str] = field(
        default_factory=lambda: ["sponsor", "selfpromo"]
    )
    sponsorblock_api_key: str = ""


@dataclass
class YtDlpSettings:
    auto_update: bool = True
    branch: str = "stable"


@dataclass
class AppUpdateSettings:
    auto_update: bool = True
    channel: str = "release"
    check_on_launch: bool = (
        False  # Prompt on launch (mutually exclusive with auto_update)
    )


@dataclass
class EZModeSettings:
    sanitize_radio_links: bool = True
    simple_paste_mode: bool = False
    hide_advanced_quality: bool = False


@dataclass
class AppSettings:
    last_download_dir: str = field(
        default_factory=lambda: os.path.expanduser("~/Downloads")
    )
    ui: UISettings = field(default_factory=UISettings)
    defaults: DefaultsSettings = field(default_factory=DefaultsSettings)
    # Legacy raw sections (kept for minimal backward compat during migration window)
    ytdlp: YtDlpSettings = field(default_factory=YtDlpSettings)
    app: AppUpdateSettings = field(default_factory=AppUpdateSettings)
    # EZ Mode
    ez: EZModeSettings = field(default_factory=EZModeSettings)
    # Unified update configs (distinct) – preferred going forward
    app_update: AppUpdateConfig = field(default_factory=AppUpdateConfig)
    ytdlp_update: YTDLPUpdateConfig = field(default_factory=YTDLPUpdateConfig)


class SettingsManager:
    def load(self) -> AppSettings:
        if not os.path.exists(SETTINGS_PATH) and os.path.exists(LEGACY_SETTINGS_PATH):
            try:
                os.makedirs(SETTINGS_DIR, exist_ok=True)
                with open(LEGACY_SETTINGS_PATH, "r", encoding="utf-8") as f:
                    legacy = f.read()
                with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                    f.write(legacy)
            except Exception:
                pass

        if not os.path.exists(SETTINGS_PATH):
            return AppSettings()
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Migrate/merge (sanitize deprecated fields)
            ui_raw = (data.get("ui") or {}).copy()
            if (
                "auto_clear_on_success" not in ui_raw
                and "clear_input_after_fetch" in ui_raw
            ):
                ui_raw["auto_clear_on_success"] = bool(
                    ui_raw.get("clear_input_after_fetch")
                )
            ui_raw.pop("clear_input_after_fetch", None)  # drop deprecated

            ui = UISettings(**ui_raw)
            defaults = DefaultsSettings(**data.get("defaults", {}))
            ytdlp = YtDlpSettings(**data.get("ytdlp", {}))
            app = AppUpdateSettings(**data.get("app", {}))
            ez = EZModeSettings(**(data.get("ez", {}) or {}))

            # Migration: create distinct update configs if not present
            if "app_update" in data:
                raw_app_upd = data.get("app_update") or {}
                try:
                    # schedule.cadence stored as string; map to enum if possible
                    sc = raw_app_upd.get("schedule", {}) or {}
                    cadence_val = sc.get("cadence", UpdateCadence.OFF)
                    try:
                        cadence_val = UpdateCadence(cadence_val)
                    except Exception:
                        cadence_val = UpdateCadence.OFF
                    app_update_cfg = AppUpdateConfig(
                        schedule=UpdateSchedule(
                            cadence=cadence_val, last_check_ts=sc.get("last_check_ts")
                        ),
                        action=UpdateAction(
                            raw_app_upd.get("action", UpdateAction.PROMPT)
                        ),
                    )
                except Exception:
                    app_update_cfg = AppUpdateConfig()
            else:
                # Derive from legacy 'app'
                # Heuristic: if auto_update True => AUTO; elif check_on_launch True => PROMPT else NO_CHECK
                if getattr(app, "auto_update", False):
                    # Default to PROMPT (less intrusive) instead of AUTO for migration
                    action = UpdateAction.PROMPT
                    cadence = UpdateCadence.DAILY
                elif getattr(app, "check_on_launch", False):
                    action = UpdateAction.PROMPT
                    cadence = UpdateCadence.LAUNCH
                else:
                    action = UpdateAction.NO_CHECK
                    cadence = UpdateCadence.OFF
                app_update_cfg = AppUpdateConfig(
                    schedule=UpdateSchedule(cadence=cadence, last_check_ts=None),
                    action=action,
                )

            if "ytdlp_update" in data:
                raw_yt_upd = data.get("ytdlp_update") or {}
                try:
                    sc = raw_yt_upd.get("schedule", {}) or {}
                    cadence_val = sc.get("cadence", UpdateCadence.DAILY)
                    try:
                        cadence_val = UpdateCadence(cadence_val)
                    except Exception:
                        cadence_val = UpdateCadence.DAILY
                    ytdlp_update_cfg = YTDLPUpdateConfig(
                        enabled=raw_yt_upd.get("enabled", True),
                        schedule=UpdateSchedule(
                            cadence=cadence_val, last_check_ts=sc.get("last_check_ts")
                        ),
                    )
                except Exception:
                    ytdlp_update_cfg = YTDLPUpdateConfig()
            else:
                # Derive from legacy ytdlp
                ytdlp_update_cfg = YTDLPUpdateConfig(
                    enabled=getattr(ytdlp, "auto_update", True),
                    schedule=UpdateSchedule(
                        cadence=(
                            UpdateCadence.DAILY
                            if getattr(ytdlp, "auto_update", True)
                            else UpdateCadence.OFF
                        )
                    ),
                )

            return AppSettings(
                last_download_dir=data.get(
                    "last_download_dir", AppSettings().last_download_dir
                ),
                ui=ui,
                defaults=defaults,
                ytdlp=ytdlp,
                app=app,
                ez=ez,
                app_update=(
                    AppUpdateConfig(
                        schedule=app_update_cfg.schedule,
                        action=(
                            UpdateAction.PROMPT
                            if getattr(app_update_cfg, "action", None)
                            == UpdateAction.AUTO
                            else app_update_cfg.action
                        ),
                    )
                ),
                ytdlp_update=ytdlp_update_cfg,
            )
        except Exception:
            return AppSettings()

    def save(self, settings: AppSettings):
        data = asdict(settings)
        os.makedirs(SETTINGS_DIR, exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
