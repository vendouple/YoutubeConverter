import os
import json
import subprocess
from datetime import datetime
from typing import Callable, List, Optional
from urllib.parse import urlparse, parse_qs

import requests


_VALID_SB_CATEGORIES = {
    "sponsor",
    "selfpromo",
    "interaction",
    "intro",
    "outro",
    "preview",
    "filler",
    "music_offtopic",
    "exclusive_access",
    "chapter",
}


def sb_log_dir() -> str:
    try:
        appdata = os.getenv("APPDATA") or os.path.expanduser("~")
        d = os.path.join(appdata, "YoutubeConverter", "logs")
        os.makedirs(d, exist_ok=True)
        return d
    except Exception:
        return os.getcwd()


def sb_log(msg: str):
    try:
        path = os.path.join(sb_log_dir(), "sponsorblock.log")
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


def normalize_sb_categories(cats: List[str] | None) -> List[str]:
    out: List[str] = []
    seen = set()
    alias = {"non_music": "music_offtopic"}
    raw = list(cats or [])
    for c in raw:
        k = alias.get(c, c)
        if k in _VALID_SB_CATEGORIES and k not in seen:
            out.append(k)
            seen.add(k)
    invalid = [c for c in raw if alias.get(c, c) not in _VALID_SB_CATEGORIES]
    if invalid:
        sb_log(f"Filtered invalid SB categories: {invalid} -> kept {out}")
    return out


def extract_video_id(url: str, it: dict | None) -> str | None:
    try:
        if it and it.get("id"):
            return str(it.get("id"))
        u = urlparse(url or "")
        if u.netloc == "youtu.be":
            vid = (u.path or "").strip("/").split("/")[0]
            return vid or None
        if u.path.startswith("/shorts/"):
            vid = (u.path.split("/")[-1] or "").strip()
            return vid or None
        if u.path == "/watch":
            q = parse_qs(u.query or "")
            v = (q.get("v") or [None])[0]
            return v
    except Exception:
        return None
    return None


def _merge_ranges(ranges: List[tuple[float, float]]) -> List[tuple[float, float]]:
    if not ranges:
        return []
    rs = sorted([(float(a), float(b)) for a, b in ranges if b > a], key=lambda x: x[0])
    out = [rs[0]]
    for s, e in rs[1:]:
        ls, le = out[-1]
        if s <= le + 1e-3:
            out[-1] = (ls, max(le, e))
        else:
            out.append((s, e))
    return out


def fetch_segments(video_id: str, cats: List[str]) -> List[tuple[float, float]]:
    try:
        params = {
            "videoID": video_id,
            "categories": json.dumps(cats),
            "service": "YouTube",
        }
        r = requests.get(
            "https://sponsor.ajay.app/api/skipSegments", params=params, timeout=12
        )
        if r.status_code != 200:
            sb_log(f"[SB] API {r.status_code}: {r.text[:200]}")
            return []
        data = r.json() or []
        segs = []
        for obj in data:
            seg = obj.get("segment") or []
            if isinstance(seg, list) and len(seg) == 2 and seg[1] > seg[0]:
                segs.append((float(seg[0]), float(seg[1])))
        return segs
    except Exception as e:
        sb_log(f"[SB] API error: {e!r}")
        return []


def apply_sponsorblock_to_file(
    src: str,
    video_url: str,
    info: dict,
    cats: List[str],
    status_cb: Optional[Callable[[str], None]] = None,
    kind: str = "video",
    fmt: str = "mp4",
) -> bool:
    """
    Apply SponsorBlock filtering to remove segments from the video/audio file.

    Args:
        src: Source file path
        video_url: YouTube URL
        info: Video info dictionary
        cats: List of SponsorBlock categories to remove
        status_cb: Callback for status updates
        kind: "audio" or "video"
        fmt: Output format

    Returns:
        True if successful, False otherwise
    """
    try:
        # Safety check: ensure file exists and is readable
        if not src or not os.path.exists(src):
            sb_log(f"[SB] No file to process or path missing: {src}")
            return False

        # Extract video ID
        vid = extract_video_id(video_url, info)
        if not vid:
            sb_log("[SB] Could not extract videoID; skipping SB")
            return False

        # Fetch segments from API
        segs = fetch_segments(vid, cats)
        if not segs:
            sb_log("[SB] No segments returned; skipping SB")
            return False

        # Merge overlapping segments
        segments_to_remove = _merge_ranges(segs)
        sb_log(f"[SB] Segments to remove: {segments_to_remove}")

        # Update status
        if status_cb:
            status_cb("removing")

        # Build filter expression: not(between(t,s0,e0)+between(t,s1,e1)+...)
        parts = [f"between(t,{s:.3f},{e:.3f})" for (s, e) in segments_to_remove]
        expr = f"not({'+'.join(parts)})"

        base, ext = os.path.splitext(src)
        # Use a different temp filename to avoid conflicts
        dst = f"{base}.sbfiltered{ext}"

        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", src]

        if kind == "video":
            vf = f"select='{expr}',setpts=PTS-STARTPTS"
            af = f"aselect='{expr}',asetpts=N/SR/TB"
            cmd += ["-vf", vf, "-af", af]
            f = (fmt or ext.lstrip(".")).lower()
            if f == "webm":
                cmd += [
                    "-c:v",
                    "libvpx-vp9",
                    "-b:v",
                    "0",
                    "-crf",
                    "30",
                    "-c:a",
                    "libopus",
                    "-b:a",
                    "128k",
                ]
            else:
                cmd += [
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "22",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                ]
                if f == "mp4":
                    cmd += ["-movflags", "+faststart"]
        else:  # audio
            af = f"aselect='{expr}',asetpts=N/SR/TB"
            cmd += ["-af", af]
            f = (fmt or ext.lstrip(".")).lower()
            if f == "mp3":
                cmd += ["-c:a", "libmp3lame", "-q:a", "2"]
            elif f in ("m4a", "aac"):
                cmd += ["-c:a", "aac", "-b:a", "192k"]
            elif f == "flac":
                cmd += ["-c:a", "flac"]
            elif f == "wav":
                cmd += ["-c:a", "pcm_s16le"]
            elif f == "opus":
                cmd += ["-c:a", "libopus", "-b:a", "128k"]
            else:
                cmd += ["-c:a", "aac", "-b:a", "192k"]

        cmd += [dst]
        sb_log(f"[SB] Re-encode command: {' '.join(cmd)}")
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0:
            sb_log(f"[SB] Re-encode failed: {p.stderr.strip()[:500]}")
            return False

        if not os.path.exists(dst) or os.path.getsize(dst) < 100:
            sb_log(f"[SB] Output file missing or empty: {dst}")
            return False

        # Replace the original file with the filtered one
        os.replace(dst, src)
        return True
    except Exception as e:
        sb_log(f"[SB] Error during processing: {e}")
        return False
