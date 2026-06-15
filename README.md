# media-puller

🎵 **從 YouTube、Bilibili、抖音/TikTok 等超過 1000 個平台下載音訊，直接匯入 open_music**

透過 yt-dlp 作為後端，支援幾乎所有主流影音平台，自動提取 metadata（歌名、藝人、時長、縮圖、hash tag），輸出為 open_music 可直接匯入的格式。

---

## 安裝

```bash
pip install yt-dlp
# 或: pip install -e .
```

## 使用

```bash
# 下載單個影片音訊
media-puller https://youtu.be/dQw4w9WgXcQ

# 下載多個網址
media-puller https://youtu.be/xxx https://www.bilibili.com/video/BV1xx

# 指定格式與品質
media-puller -f flac -q 320 https://youtu.be/xxx

# 匯入 open_music（同時產生 library.json）
media-puller --open-music https://youtu.be/xxx

# 指定輸出目錄
media-puller -o ~/Music/my-library https://youtu.be/xxx

# 查看更多選項
media-puller --help
```

## 與 open_music 整合

```bash
# 1. 下載音訊並產生 library.json
media-puller --open-music https://youtu.be/xxx https://www.bilibili.com/video/BV1xx

# 2. 在 open_music 中匯入
#    open_music > import ~/Music/media-puller
```

## 支援的平台 (透過 yt-dlp)

- YouTube / YouTube Music
- Bilibili (嗶哩嗶哩)
- 抖音 / TikTok
- SoundCloud
- Twitch
- Vimeo
- 以及 1000+ 其他網站

## 設定檔

`~/.config/media-puller/config.json`

```json
{
  "format": "mp3",
  "quality": "192",
  "output_dir": "~/Music/media-puller",
  "embed_thumbnail": true
}
```

## License

MIT
