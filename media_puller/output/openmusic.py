"""open_music output formatter — exports downloaded songs as an open_music-compatible library.json."""

import json
from pathlib import Path

PLATFORM_DISPLAY: dict[str, str] = {
    "youtube":   "YouTube",
    "bilibili":  "Bilibili",
    "douyin":    "抖音/TikTok",
    "soundcloud": "SoundCloud",
    "twitch":    "Twitch",
    "vimeo":     "Vimeo",
    "generic":   "其他來源",
}


def export_library_json(
    results: list["DownloadResult"],
    output_dir: Path,
) -> Path:
    """Generate a library.json that open_music can import."""
    from media_puller.core import DownloadResult

    songs = []
    playlists = []

    for r in results:
        if not r.success:
            continue
        songs.append(r.to_song_metadata())

    # Create a playlist per platform
    platforms_seen: dict[str, list[int]] = {}
    for i, r in enumerate(results):
        if not r.success:
            continue
        platforms_seen.setdefault(r.platform, []).append(i)

    for platform, indices in platforms_seen.items():
        platform_songs = [results[i].to_song_metadata() for i in indices]
        playlists.append({
            "name": f"📥 {PLATFORM_DISPLAY.get(platform, platform)}",
            "description": f"從 {PLATFORM_DISPLAY.get(platform, platform)} 下載",
            "playlist": platform_songs,
        })

    library = {
        "songs": songs,
        "playlists": playlists,
    }

    path = output_dir / "library.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(library, f, ensure_ascii=False, indent=2)

    return path
