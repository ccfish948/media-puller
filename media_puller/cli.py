"""CLI entry point for media-puller."""

import argparse
import json
import logging
import sys
from pathlib import Path

from media_puller import __version__
from media_puller.core import download_batch, DEFAULT_CONFIG, PLATFORM_LABELS
from media_puller.output import openmusic as om


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="media-puller",
        description="🎵 從 YouTube、Bilibili、抖音等平台下載音訊，匯入 open_music",
        epilog="範例: media-puller https://youtu.be/xxxx https://www.bilibili.com/video/xxxx",
    )

    parser.add_argument("urls", nargs="*", metavar="URL", help="要下載的影片/音訊網址")
    parser.add_argument("-f", "--format", default=DEFAULT_CONFIG["format"],
                        choices=["mp3", "flac", "opus", "m4a", "wav"],
                        help="音訊格式 (預設: mp3)")
    parser.add_argument("-q", "--quality", default=DEFAULT_CONFIG["quality"],
                        help="音訊品質 (預設: 192)")
    parser.add_argument("-o", "--output-dir", default=DEFAULT_CONFIG["output_dir"],
                        help=f"輸出目錄 (預設: {DEFAULT_CONFIG['output_dir']})")
    parser.add_argument("--no-thumbnail", action="store_true",
                        help="不嵌入縮圖")
    parser.add_argument("--open-music", action="store_true",
                        help="同時產生 open_music 可匯入的 library.json")
    parser.add_argument("--keep-original", action="store_true",
                        help="保留原始下載檔案")
    parser.add_argument("--max-downloads", type=int, default=None,
                        help="最多下載數量")
    parser.add_argument("--extra-ytdlp", nargs="*", default=[],
                        help="額外 yt-dlp 參數 (例如: --extra-ytdlp --cookies-from-browser chrome)")
    parser.add_argument("--list-platforms", action="store_true",
                        help="列出支援的平台")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="詳細輸出")
    parser.add_argument("--version", action="version",
                        version=f"media-puller {__version__}")

    args = parser.parse_args()

    # ── Logging ──
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        stream=sys.stderr,
    )
    log = logging.getLogger("puller")

    # ── List platforms ──
    if args.list_platforms:
        print("🌐 media-puller 支援的平台 (透過 yt-dlp):")
        for key, label in sorted(PLATFORM_LABELS.items()):
            print(f"  • {label}")
        print(f"\n  以及 1000+ 其他網站 (yt-dlp 自動偵測)")
        return

    # ── Build config ──
    config = {
        "format": args.format,
        "quality": args.quality,
        "output_dir": args.output_dir,
        "embed_thumbnail": not args.no_thumbnail,
        "keep_original": args.keep_original,
        "max_downloads": args.max_downloads,
        "yt_dlp_extra": args.extra_ytdlp,
    }

    urls = args.urls
    if not urls and not args.list_platforms:
        parser.print_help()
        sys.exit(1)
    if args.max_downloads:
        urls = urls[: args.max_downloads]

    log.info("🎵 media-puller v%s", __version__)
    log.info("📥 準備下載 %d 個網址 → %s", len(urls), config["format"])
    log.info("")

    results = download_batch(urls, config, open_music_export=args.open_music)

    # ── Summary ──
    success = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    log.info("")
    log.info("=" * 50)
    log.info("📊 下載完成: %d 成功, %d 失敗", len(success), len(failed))

    if failed:
        for r in failed:
            log.warning("  ❌ %s — %s", r.url, r.error)

    if args.open_music and success:
        out_dir = Path(config["output_dir"]).expanduser().resolve()
        log.info("📦 open_music library.json 已產生: %s/library.json", out_dir)
        log.info("   在 open_music 中使用 import %s 匯入", out_dir)

    sys.exit(1 if failed and not success else 0)


if __name__ == "__main__":
    main()
