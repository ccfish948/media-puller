"""Core download orchestration — pulls media via yt-dlp and feeds into open_music."""

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

from media_puller.output import openmusic as om

log = logging.getLogger("puller")

# ── Supported platforms for user-facing display ──

PLATFORM_LABELS: dict[str, str] = {
    "youtube":   "YouTube",
    "bilibili":  "Bilibili",
    "douyin":    "抖音/ TikTok",
    "soundcloud": "SoundCloud",
    "twitch":    "Twitch",
    "vimeo":     "Vimeo",
    "generic":   "其他 (yt-dlp)",
}

# ── Config keys ──

DEFAULT_CONFIG: dict[str, Any] = {
    "format":           "mp3",
    "quality":          "192",
    "output_dir":       str(Path.home() / "Music" / "media-puller"),
    "embed_thumbnail":  True,
    "keep_original":    False,
    "max_downloads":    None,          # None = unlimited
    "yt_dlp_extra":     [],            # extra yt-dlp flags
}

# ── Download result ──

class DownloadResult:
    """Holds the result of a single download."""

    def __init__(
        self,
        url: str,
        platform: str,
        title: str,
        artist: str | None,
        duration: int | None,
        file_path: Path,
        thumbnail_path: Path | None,
        description: str | None,
        tags: list[str] | None,
        success: bool,
        error: str | None = None,
    ):
        self.url = url
        self.platform = platform
        self.title = title
        self.artist = artist
        self.duration = duration
        self.file_path = file_path
        self.thumbnail_path = thumbnail_path
        self.description = description
        self.tags = tags or []
        self.success = success
        self.error = error

    def to_song_metadata(self) -> dict[str, Any]:
        """Return a dict compatible with open_music's Song JSON."""
        credits = {}
        if self.artist:
            credits[self.artist] = {"name": self.artist, "description": None}
        return {
            "title": self.title,
            "credits": credits if credits else None,
            "duration": self.duration,
            "source": str(self.file_path),
            "description": self.description,
            "hashtags": self.tags if self.tags else None,
            "album": {"title": self.platform, "cover": None},
        }


# ── URL platform detection ──

PLATFORM_PATTERNS: dict[str, str] = {
    "youtube":    r"(youtube\.com|youtu\.be)",
    "bilibili":   r"(bilibili\.com|b23\.tv)",
    "douyin":     r"(douyin\.com|tiktok\.com)",
    "soundcloud": r"soundcloud\.com",
    "twitch":     r"twitch\.tv",
    "vimeo":      r"vimeo\.com",
}

def detect_platform(url: str) -> str:
    import re
    for platform, pattern in PLATFORM_PATTERNS.items():
        if re.search(pattern, url, re.IGNORECASE):
            return platform
    return "generic"


# ── yt-dlp JSON extraction ──

def extract_info(url: str, yt_dlp_extra: list[str] | None = None) -> dict[str, Any] | None:
    """Run yt-dlp --dump-json and return parsed metadata."""
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--dump-json",
        "--no-warnings",
        "--flat-playlist",
        * (yt_dlp_extra or []),
        url,
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120, check=False,
        )
    except subprocess.TimeoutExpired:
        log.error("yt-dlp timed out for %s", url)
        return None
    except FileNotFoundError:
        log.error("yt-dlp not found — install it: pip install yt-dlp")
        return None

    if result.returncode != 0:
        stderr = result.stderr.strip()
        # filter known noise
        lines = [l for l in stderr.split("\n") if "WARNING" not in l and "[youtube]" not in l]
        if lines:
            log.warning("yt-dlp stderr: %s", " | ".join(lines[:3]))
        if not result.stdout.strip():
            return None

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


# ── Download single URL ──

def download_url(
    url: str,
    config: dict[str, Any] | None = None,
) -> DownloadResult:
    """Download a single URL and return the result."""
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    platform = detect_platform(url)
    platform_label = PLATFORM_LABELS.get(platform, platform)
    log.info("🌐 %s  →  %s", url, platform_label)

    out_dir = Path(cfg["output_dir"]).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    audio_format = cfg["format"]
    quality = cfg["quality"]

    # ── Extract metadata first ──
    info = extract_info(url, cfg.get("yt_dlp_extra"))

    title = (info or {}).get("title") or Path(url).name
    artist = (info or {}).get("uploader") or (info or {}).get("artist") or (info or {}).get("channel")
    duration = (info or {}).get("duration")
    description = (info or {}).get("description")
    tags = (info or {}).get("tags") or (info or {}).get("categories")

    # ── Download audio ──
    sanitized = _sanitize(title)
    output_template = str(out_dir / f"{sanitized}.%(ext)s")

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-x",
        "--audio-format", audio_format,
        "--audio-quality", quality,
        "--output", output_template,
        "--no-playlist",
        "--no-warnings",
        * (cfg.get("yt_dlp_extra") or []),
        url,
    ]

    if cfg["embed_thumbnail"]:
        cmd += ["--embed-thumbnail"]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600, check=False,
        )
    except subprocess.TimeoutExpired:
        return DownloadResult(url, platform, title, artist, duration,
                              out_dir / f"{sanitized}.{audio_format}",
                              None, description, tags, False,
                              error="Download timed out (10 min)")

    if result.returncode != 0:
        err = result.stderr.strip() or "unknown error"
        return DownloadResult(url, platform, title, artist, duration,
                              out_dir / f"{sanitized}.{audio_format}",
                              None, description, tags, False, error=err)

    # Find the actual output file — yt-dlp converts webm → mp3 via -x flag
    file_path = out_dir / f"{sanitized}.{audio_format}"
    if not file_path.exists():
        found = list(out_dir.glob(f"{sanitized}.*"))
        if found:
            file_path = found[0]

    log.info("✅ 已下載: %s", file_path)

    # ── Thumbnail ──
    thumbnail_path = None
    if info and info.get("thumbnail"):
        thumb_url = info["thumbnail"]
        import urllib.request
        try:
            thumb_path = file_path.with_suffix(".jpg")
            urllib.request.urlretrieve(thumb_url, thumb_path)
            thumbnail_path = thumb_path
        except Exception as e:
            log.warning("thumbnail download failed: %s", e)

    return DownloadResult(
        url=url,
        platform=platform,
        title=title,
        artist=artist,
        duration=duration,
        file_path=file_path if file_path.exists() else Path(str(file_path)),
        thumbnail_path=thumbnail_path,
        description=description,
        tags=tags,
        success=True,
    )


def _sanitize(name: str) -> str:
    """Remove characters that are problematic in file names."""
    import re
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    return name.strip().strip(".") or "untitled"


# ── Batch download ──

def download_batch(
    urls: list[str],
    config: dict[str, Any] | None = None,
    open_music_export: bool = False,
) -> list[DownloadResult]:
    """Download multiple URLs and optionally generate open_music JSON."""
    results: list[DownloadResult] = []
    for i, url in enumerate(urls):
        log.info("[%d/%d] 正在下載: %s", i + 1, len(urls), url)
        result = download_url(url, config)
        results.append(result)
        if not result.success:
            log.error("❌ 下載失敗 [%s]: %s", url, result.error)

    if open_music_export and results:
        cfg = {**DEFAULT_CONFIG, **(config or {})}
        out_dir = Path(cfg["output_dir"]).expanduser().resolve()
        om.export_library_json(results, out_dir)

    return results
