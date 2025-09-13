"""Error normalization map (T033)

Provides friendly user-facing messages for categorized internal failure keys.
Extend keys as needed; consumer code should prefer safe fallbacks when key missing.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class NormalizedError:
    key: str
    title: str
    message: str
    suggestion: str | None = None


_ERROR_MAP: Dict[str, NormalizedError] = {
    "network": NormalizedError(
        key="network",
        title="Network Error",
        message="A network problem occurred while contacting the update server.",
        suggestion="Check your internet connection or try again later.",
    ),
    "permission": NormalizedError(
        key="permission",
        title="Permission Denied",
        message="The application lacked permission to write required files.",
        suggestion="Run as administrator or choose a different folder.",
    ),
    "disk": NormalizedError(
        key="disk",
        title="Disk Error",
        message="A disk I/O error occurred while saving files.",
        suggestion="Ensure sufficient free space and retry.",
    ),
    "ffmpeg_missing": NormalizedError(
        key="ffmpeg_missing",
        title="FFmpeg Not Ready",
        message="FFmpeg is not yet installed or accessible.",
        suggestion="Allow installation to finish or install FFmpeg manually.",
    ),
    "yt_dlp_missing": NormalizedError(
        key="yt_dlp_missing",
        title="yt-dlp Missing",
        message="The yt-dlp binary is missing and a download is required.",
        suggestion="Trigger a yt-dlp update or reinstall the application.",
    ),
}


def normalize_error(key: str) -> NormalizedError:
    return _ERROR_MAP.get(
        key,
        NormalizedError(
            key=key,
            title="Unexpected Error",
            message="An unexpected problem occurred.",
            suggestion="Please retry or check logs for details.",
        ),
    )


__all__ = ["normalize_error", "NormalizedError"]
