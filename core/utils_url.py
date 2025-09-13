from __future__ import annotations
import re
from urllib.parse import urlparse, parse_qs

_YT_HOSTS = {
    "www.youtube.com",
    "youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
}
_WATCH_BASE = "https://www.youtube.com/watch?v={vid}"

_RADIO_PARAMS = {"start_radio", "rv", "list", "index"}

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def _extract_video_id(url: str) -> str | None:
    try:
        if "youtu.be/" in url:
            vid = url.rstrip("/").split("/")[-1].split("?")[0]
            return vid if _VIDEO_ID_RE.match(vid) else None
        p = urlparse(url)
        if p.netloc not in _YT_HOSTS:
            return None
        if p.path == "/watch":
            q = parse_qs(p.query)
            v = q.get("v", [None])[0]
            if v and _VIDEO_ID_RE.match(v):
                return v
        # Shorts or embed paths
        parts = [seg for seg in p.path.split("/") if seg]
        if parts:
            cand = parts[-1]
            if _VIDEO_ID_RE.match(cand):
                return cand
    except Exception:
        return None
    return None


def normalize_youtube_url(url: str) -> tuple[str, bool]:
    """Return (normalized_url, was_radio_like).

    Radio / playlist style single video links (with list=RD*, start_radio, rv, index) are simplified
    to canonical watch URL with only the primary video id.
    """
    vid = _extract_video_id(url)
    if not vid:
        return url, False
    p = urlparse(url)
    q = parse_qs(p.query)
    radio_like = any(k in q for k in _RADIO_PARAMS)
    # Always reduce to canonical form when radio-like or extraneous params present
    if radio_like:
        return _WATCH_BASE.format(vid=vid), True
    # If original already minimal keep it
    if p.path == "/watch" and set(q.keys()) <= {"v"}:
        return url, False
    return _WATCH_BASE.format(vid=vid), False
