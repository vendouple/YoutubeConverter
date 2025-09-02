import json
import os
from dataclasses import dataclass, asdict, field
from typing import List  # ADDED


def _user_config_dir() -> str:
    base = os.getenv("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "YoutubeConverter")


APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(APP_DIR)
# Old location (legacy)
LEGACY_SETTINGS_PATH = os.path.join(ROOT_DIR, "settings.json")
# New per-user location
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
        False  # NEW: prompt on launch (mutually exclusive with auto_update)
    )


@dataclass
class AppSettings:
    last_download_dir: str = field(
        default_factory=lambda: os.path.expanduser("~/Downloads")
    )
    ui: UISettings = field(default_factory=UISettings)
    defaults: DefaultsSettings = field(default_factory=DefaultsSettings)
    ytdlp: YtDlpSettings = field(default_factory=YtDlpSettings)
    app: AppUpdateSettings = field(default_factory=AppUpdateSettings)


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
            return AppSettings(
                last_download_dir=data.get(
                    "last_download_dir", AppSettings().last_download_dir
                ),
                ui=ui,
                defaults=defaults,
                ytdlp=ytdlp,
                app=app,
            )
        except Exception:
            return AppSettings()

    def save(self, settings: AppSettings):
        data = asdict(settings)
        os.makedirs(SETTINGS_DIR, exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
