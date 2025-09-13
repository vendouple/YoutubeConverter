import logging
import os
import zipfile
import time
from typing import Optional, List

# Simple logging facade used by tests (set_level and logger instance expected)

_LOG_LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}

# Determine log directory (AppData on Windows) for future expansion
APPDATA = os.getenv("APPDATA") or os.path.expanduser("~")
LOG_DIR = os.path.join(APPDATA, "YoutubeConverter", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, "app.log")

_logger = logging.getLogger("YoutubeConverter")
if not _logger.handlers:
    _logger.setLevel(logging.INFO)
    fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    fh.setFormatter(fmt)
    _logger.addHandler(fh)
    # Also console (debug convenience) – safe if running tests
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    _logger.addHandler(ch)

# Public alias expected by tests
logger = _logger


def set_level(name: str):
    """Dynamically adjust root application logger level.

    Accepts case-insensitive names (e.g., 'error', 'DEBUG'). No exception on invalid input.
    """
    if not name:
        return
    lvl = _LOG_LEVELS.get(str(name).upper())
    if lvl is None:
        return
    logger.setLevel(lvl)
    for h in logger.handlers:
        try:
            h.setLevel(lvl)
        except Exception:
            pass


__all__ = ["logger", "set_level", "LOG_PATH", "LOG_DIR"]


def list_log_files(max_files: int = 10) -> List[str]:
    try:
        files = [
            os.path.join(LOG_DIR, f)
            for f in os.listdir(LOG_DIR)
            if f.lower().endswith(".log")
        ]
        files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return files[:max_files]
    except Exception:
        return []


def export_logs(dest_zip: str | None = None, max_files: int = 10) -> str:
    """Zip recent log files for support/export (T034).

    Returns path to created zip (or empty string on failure).
    """
    try:
        files = list_log_files(max_files)
        if not files:
            return ""
        if dest_zip is None:
            stamp = time.strftime("%Y%m%d-%H%M%S")
            dest_zip = os.path.join(LOG_DIR, f"logs-{stamp}.zip")
        with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in files:
                try:
                    zf.write(f, os.path.basename(f))
                except Exception:
                    pass
        return dest_zip
    except Exception:
        return ""


__all__.extend(["export_logs", "list_log_files"])
