import os
import sys
import subprocess
import requests
import zipfile
import time
import logging
from enum import Enum
from typing import Optional, Callable
from PyQt6.QtCore import QThread, pyqtSignal, QObject

try:
    from core.models import UpdateSchedule, UpdateCadence
except Exception:
    # Lightweight fallback definitions if models not yet imported (tests will still drive real path)
    from enum import Enum
    from dataclasses import dataclass
    from typing import Optional as _Opt

    class UpdateCadence(str, Enum):
        OFF = "off"
        LAUNCH = "launch"
        DAILY = "daily"
        WEEKLY = "weekly"
        MONTHLY = "monthly"

    @dataclass
    class UpdateSchedule:
        cadence: UpdateCadence = UpdateCadence.OFF
        last_check_ts: _Opt[float] = None


if getattr(sys, "frozen", False):
    ROOT_DIR = os.path.dirname(sys.executable)
else:
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YTDLP_DIR = os.path.join(ROOT_DIR, "yt-dlp-bin")
YTDLP_EXE = os.path.join(YTDLP_DIR, "yt-dlp.exe")
STAGING_DIR = os.path.join(ROOT_DIR, "_update_staging")


def get_latest_release_info(branch: str) -> dict:
    if branch == "nightly":
        repo = "yt-dlp/yt-dlp-nightly-builds"
        api = f"https://api.github.com/repos/{repo}/releases/latest"
        dl = "https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/latest/download/yt-dlp.exe"
    elif branch == "master":
        repo = "yt-dlp/yt-dlp-master-builds"
        api = f"https://api.github.com/repos/{repo}/releases/latest"
        dl = "https://github.com/yt-dlp/yt-dlp-master-builds/releases/latest/download/yt-dlp.exe"
    else:
        repo = "yt-dlp/yt-dlp"
        api = f"https://api.github.com/repos/{repo}/releases/latest"
        dl = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
    tag = ""
    try:
        r = requests.get(api, timeout=15)
        r.raise_for_status()
        rel = r.json()
        tag = rel.get("tag_name") or rel.get("name") or ""
    except Exception:
        pass
    return {"repo": repo, "api": api, "download_url": dl, "tag": tag}


def _hidden_subprocess_kwargs():
    kwargs = {}
    if os.name == "nt":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        kwargs["startupinfo"] = si
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return kwargs


def current_binary_version() -> str:
    if not os.path.exists(YTDLP_EXE):
        return ""
    try:
        kwargs = _hidden_subprocess_kwargs()
        out = subprocess.check_output([YTDLP_EXE, "--version"], timeout=10, **kwargs)
        return (out.decode(errors="ignore").strip().split()[0]) if out else ""
    except Exception:
        return ""


def ensure_ytdlp_dir():
    os.makedirs(YTDLP_DIR, exist_ok=True)


def clear_ytdlp_cache():
    try:
        if os.path.exists(YTDLP_EXE):
            kwargs = _hidden_subprocess_kwargs()
            subprocess.run([YTDLP_EXE, "--rm-cache-dir"], timeout=15, **kwargs)
    except Exception:
        pass


class YtDlpUpdateWorker(QThread):
    status = pyqtSignal(str)

    def __init__(self, branch: str = "stable", check_only: bool = True):
        super().__init__()
        self.branch = branch
        self.check_only = check_only

    def run(self):
        try:
            ensure_ytdlp_dir()
            current = current_binary_version()
            rel = get_latest_release_info(self.branch)
            latest = rel.get("tag", "")
            dl_url = rel.get("download_url")
            if self.check_only:
                if latest and current:
                    if current == latest:
                        self.status.emit(f"yt-dlp binary up-to-date ({current})")
                    else:
                        self.status.emit(
                            f"yt-dlp binary current {current}; latest {latest}"
                        )
                elif current:
                    self.status.emit(f"yt-dlp binary current {current}; latest unknown")
                else:
                    self.status.emit("yt-dlp binary not installed")
                return
            if latest and current and current == latest and os.path.exists(YTDLP_EXE):
                self.status.emit("yt-dlp is up-to-date.")
                return
            if not dl_url:
                self.status.emit("Cannot resolve yt-dlp download URL")
                return
            self.status.emit("Downloading yt-dlp binary...")
            tmp_path = YTDLP_EXE + ".tmp"
            with requests.get(dl_url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(tmp_path, "wb") as f:
                    for chunk in r.iter_content(256 * 1024):
                        if chunk:
                            f.write(chunk)
            if os.path.exists(YTDLP_EXE):
                try:
                    os.remove(YTDLP_EXE)
                except Exception:
                    pass
            os.replace(tmp_path, YTDLP_EXE)
            try:
                os.chmod(YTDLP_EXE, 0o755)
            except Exception:
                pass
            self.status.emit("yt-dlp updated.")
            clear_ytdlp_cache()
        except Exception as e:
            self.status.emit(f"yt-dlp update failed: {e}")


class AppUpdateWorker(QThread):
    status = pyqtSignal(str)
    updated = pyqtSignal(bool)
    available = pyqtSignal(str, str)
    availableDetails = pyqtSignal(str, str, str)

    def __init__(self, repo: str, channel: str, current_version: str, do_update: bool):
        super().__init__()
        self.repo = repo
        self.channel = (channel or "release").lower()
        self.current_version = current_version
        self.do_update = do_update

    def _local_version(self) -> str:
        try:
            vp = os.path.join(ROOT_DIR, "version.txt")
            if os.path.exists(vp):
                with open(vp, "r", encoding="utf-8") as f:
                    return f.read().strip()
        except Exception:
            pass
        return self.current_version or ""

    def _get_release_json(self) -> Optional[dict]:
        base = f"https://api.github.com/repos/{self.repo}/releases"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "YoutubeConverter-Updater",
        }

        def _get(url: str):
            try:
                r = requests.get(url, headers=headers, timeout=20)
                if r.status_code == 403:
                    self.status.emit(f"GitHub API rate limited (403) for {url}")
                elif r.status_code == 404:
                    self.status.emit(f"Not found (404) for {url}")
                r.raise_for_status()
                return r.json()
            except requests.exceptions.RequestException as e:
                self.status.emit(f"GitHub API error: {e}")
                return None

        if self.channel == "nightly":
            rel = _get(f"{base}/tags/nightly")
            if rel:
                return rel
            tags = (
                _get(f"https://api.github.com/repos/{self.repo}/tags?per_page=100")
                or []
            )
            tag = next(
                (t for t in tags if (t.get("name") or "").lower() == "nightly"), None
            )
            if not tag:
                return None
            rel = _get(f"{base}/tags/{tag.get('name')}")
            return rel or {"tag_name": tag.get("name"), "assets": []}

        rels = _get(base) or []
        if rels:
            if self.channel == "release":
                rel = next((x for x in rels if not x.get("prerelease")), None)
                if rel:
                    return rel
            elif self.channel == "prerelease":
                rel = next(
                    (
                        x
                        for x in rels
                        if x.get("prerelease")
                        and (x.get("tag_name") or "").lower() != "nightly"
                    ),
                    None,
                ) or next((x for x in rels if x.get("prerelease")), None)
                if rel:
                    return rel
            else:
                return rels[0]

        tags = _get(f"https://api.github.com/repos/{self.repo}/tags?per_page=100") or []
        if not tags:
            return None
        if self.channel == "release":
            ver = next(
                (t for t in tags if (t.get("name") or "").lower().startswith("v")), None
            )
            chosen = ver or tags[0]
        elif self.channel == "prerelease":
            chosen = next(
                (t for t in tags if (t.get("name") or "").lower() != "nightly"), tags[0]
            )
        else:
            chosen = tags[0]
        rel = _get(f"{base}/tags/{chosen.get('name')}")
        return rel or {"tag_name": chosen.get("name"), "assets": []}

    def _pick_zip_asset(self, rel: dict) -> Optional[dict]:
        assets = rel.get("assets") or []
        for a in assets:
            n = (a.get("name") or "").lower()
            if n.startswith("youtubeconverter") and n.endswith(".zip"):
                return a
        for a in assets:
            n = (a.get("name") or "").lower()
            if n.endswith(".zip"):
                return a
        return None

    def _extract_zip_flat(self, zip_path: str, dest_dir: str):
        with zipfile.ZipFile(zip_path) as zf:
            for m in zf.infolist():
                name = m.filename.replace("\\", "/")
                parts = name.split("/")
                rel = "/".join(parts[1:]) if len(parts) > 1 else parts[0]
                if not rel or rel.endswith("/"):
                    continue
                out_path = os.path.join(dest_dir, rel)
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with zf.open(m) as src, open(out_path, "wb") as dst:
                    dst.write(src.read())

    @staticmethod
    def _normalize_version(v: str) -> str:
        if not v:
            return ""
        s = v.strip()
        if len(s) >= 2 and (s[0] in ("v", "V")) and s[1].isdigit():
            s = s[1:]
        return s.strip().lower()

    def run(self):
        try:
            self.status.emit(f"Checking app updates from {self.repo}...")
            rel = self._get_release_json()
            if not rel:
                self.status.emit(f"No releases found for {self.repo} [{self.channel}].")
                self.updated.emit(False)
                return
            if self.channel == "nightly":
                tag = rel.get("name") or rel.get("tag_name") or ""
            else:
                tag = rel.get("tag_name") or rel.get("name") or ""
            raw_remote_ver = (tag or "").strip()
            raw_local_ver = self._local_version()

            remote_ver = self._normalize_version(raw_remote_ver)
            local_ver = self._normalize_version(raw_local_ver)

            if remote_ver and local_ver and remote_ver == local_ver:
                self.status.emit(
                    f"App up-to-date ({raw_local_ver or local_ver}) [{self.channel}]"
                )
                self.updated.emit(False)
                return

            if not self.do_update:
                if remote_ver and local_ver and remote_ver != local_ver:
                    self.status.emit(
                        f"Update available {raw_local_ver or local_ver} -> {raw_remote_ver or remote_ver} [{self.channel}]"
                    )
                    body_md = rel.get("body") or ""
                    # Emit only one detailed signal to prevent duplicate prompts
                    self.availableDetails.emit(
                        raw_remote_ver or remote_ver,
                        raw_local_ver or local_ver,
                        body_md,
                    )
                else:
                    self.status.emit(f"Update check complete [{self.channel}]")
                self.updated.emit(False)
                return
            asset = self._pick_zip_asset(rel)
            if not asset:
                self.status.emit("No zip asset found in release.")
                self.updated.emit(False)
                return

            url = asset.get("browser_download_url")
            name = asset.get("name") or "update.zip"
            self.status.emit(f"Downloading {name}...")
            os.makedirs(STAGING_DIR, exist_ok=True)
            tmp_zip = os.path.join(STAGING_DIR, "_update_tmp.zip")
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(tmp_zip, "wb") as f:
                    for chunk in r.iter_content(256 * 1024):
                        if chunk:
                            f.write(chunk)

            self.status.emit("Preparing update...")
            for root, dirs, files in os.walk(STAGING_DIR):
                for fn in files:
                    if fn != "_update_tmp.zip":
                        try:
                            os.remove(os.path.join(root, fn))
                        except Exception:
                            pass
            self._extract_zip_flat(tmp_zip, STAGING_DIR)
            try:
                os.remove(tmp_zip)
            except Exception:
                pass
            try:
                with open(os.path.join(STAGING_DIR, ".pending"), "w") as f:
                    f.write(remote_ver or "")
            except Exception:
                pass
            self.status.emit("Update ready. It will be applied on restart.")
            self.updated.emit(True)
        except Exception as e:
            self.status.emit(f"App update failed: {e}")
            self.updated.emit(False)
            if not asset:
                self.status.emit("No zip asset found in release.")
                self.updated.emit(False)
                return

            url = asset.get("browser_download_url")
            name = asset.get("name") or "update.zip"
            self.status.emit(f"Downloading {name}...")
            os.makedirs(STAGING_DIR, exist_ok=True)
            tmp_zip = os.path.join(STAGING_DIR, "_update_tmp.zip")
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(tmp_zip, "wb") as f:
                    for chunk in r.iter_content(256 * 1024):
                        if chunk:
                            f.write(chunk)

            self.status.emit("Preparing update...")
            # Extract into staging (no in-place overwrite while running)
            for root, dirs, files in os.walk(STAGING_DIR):
                for fn in files:
                    if fn != "_update_tmp.zip":
                        try:
                            os.remove(os.path.join(root, fn))
                        except Exception:
                            pass
            self._extract_zip_flat(tmp_zip, STAGING_DIR)
            try:
                os.remove(tmp_zip)
            except Exception:
                pass
            try:
                with open(os.path.join(STAGING_DIR, ".pending"), "w") as f:
                    f.write(remote_ver or "")
            except Exception:
                pass
            self.status.emit("Update ready. It will be applied on restart.")
            self.updated.emit(True)
        except Exception as e:
            self.status.emit(f"App update failed: {e}")
            self.updated.emit(False)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("update_debugger")

# ---- Schedule helpers (contract tests expect these) ----

_CADENCE_SECONDS = {
    UpdateCadence.DAILY: 60 * 60 * 24,
    UpdateCadence.WEEKLY: 60 * 60 * 24 * 7,
    UpdateCadence.MONTHLY: 60 * 60 * 24 * 30,  # Simplified month length
}


def next_schedule_due(
    s: UpdateSchedule, now: Optional[float] = None
) -> Optional[float]:
    """Return epoch seconds when the schedule will next be due or None if never.

    LAUNCH cadence is treated as always due (returned now) to simplify call sites.
    OFF cadence returns None.
    """
    import time as _time

    now = now or _time.time()
    if not s or s.cadence == UpdateCadence.OFF:
        return None
    if s.cadence == UpdateCadence.LAUNCH:
        return now
    base = s.last_check_ts or 0.0
    interval = _CADENCE_SECONDS.get(s.cadence)
    if not interval:
        return None
    return base + interval


def is_schedule_due(s: UpdateSchedule, now: Optional[float] = None) -> bool:
    """Return True if schedule indicates a check should run at 'now'."""
    import time as _time

    now = now or _time.time()
    if not s:
        return False
    if s.cadence == UpdateCadence.OFF:
        return False
    if s.cadence == UpdateCadence.LAUNCH:
        return True
    target = next_schedule_due(s, now)
    if target is None:
        return False
    return now >= target - 1e-6  # tolerate float rounding


# ---------------- Update Flow State Machine (T030) -----------------


class UpdateState(str, Enum):
    PRE_PROMPT = "pre_prompt"
    CHECKING = "checking"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    APPLYING = "applying"
    RESTART_NEEDED = "restart_needed"
    ERROR = "error"
    CANCELED = "canceled"


class UpdateFlowManager(QObject):
    """High-level orchestrator wrapping AppUpdateWorker with coarse states.

    Future expansion: integrate code-sign verification & differential updates.
    """

    stateChanged = pyqtSignal(str)
    message = pyqtSignal(str)
    error = pyqtSignal(str)
    restartRequired = pyqtSignal()

    def __init__(self, repo: str, channel: str, current_version: str):
        super().__init__()
        self.repo = repo
        self.channel = channel
        self.current_version = current_version
        self._state: UpdateState = UpdateState.PRE_PROMPT
        self._worker: Optional[AppUpdateWorker] = None
        self._canceled = False

    # ---- State helpers ----
    def _set_state(self, s: UpdateState):
        if s != self._state:
            self._state = s
            self.stateChanged.emit(s.value)

    def state(self) -> UpdateState:
        return self._state

    # ---- Public API ----
    def start(self, do_update: bool):
        if self._worker and self._worker.isRunning():
            return
        self._canceled = False
        self._set_state(UpdateState.CHECKING)
        self._worker = AppUpdateWorker(
            self.repo, self.channel, self.current_version, do_update
        )
        self._worker.status.connect(self._on_status)
        self._worker.updated.connect(self._on_updated)
        self._worker.availableDetails.connect(self._on_available)
        self._worker.start()

    def cancel(self):
        if self._worker and self._worker.isRunning():
            try:
                self._canceled = True
                # QThread has no cooperative cancel path here; terminate as last resort
                self._worker.terminate()
            except Exception:
                pass
        self._set_state(UpdateState.CANCELED)

    # ---- Internal signal handlers ----
    def _on_status(self, text: str):
        if self._canceled:
            return
        low = (text or "").lower()
        if "downloading" in low and self._state == UpdateState.CHECKING:
            self._set_state(UpdateState.DOWNLOADING)
        elif "preparing" in low and self._state in (
            UpdateState.DOWNLOADING,
            UpdateState.CHECKING,
        ):
            self._set_state(UpdateState.VERIFYING)
        elif "update ready" in low:
            self._set_state(UpdateState.RESTART_NEEDED)
            self.restartRequired.emit()
        elif "failed" in low or "error" in low:
            self._set_state(UpdateState.ERROR)
            self.error.emit(text)
        self.message.emit(text)

    def _on_updated(self, changed: bool):
        if self._canceled:
            return
        if changed and self._state not in (
            UpdateState.RESTART_NEEDED,
            UpdateState.ERROR,
        ):
            self._set_state(UpdateState.RESTART_NEEDED)
            self.restartRequired.emit()
        elif not changed and self._state == UpdateState.CHECKING:
            # No update available -> remain or finalize
            self._set_state(UpdateState.CHECKING)

    def _on_available(self, remote_ver: str, local_ver: str, body_md: str):
        # Provide informational message hook; do not change state
        self.message.emit(
            f"Update available {local_ver or '?'} -> {remote_ver or '?'}".strip()
        )

    # Convenience: run a single-step check without download
    def check_only(self):
        self.start(do_update=False)

    # Convenience: run auto update (download/apply)
    def auto_update(self):
        self.start(do_update=True)
