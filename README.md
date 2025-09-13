<p align="center">
<img src="YTConverterIcon.png" width="300" alt="Logo">
</p>

# YouTube Converter

Convert YouTube videos to audio or video on Windows with a simple, modern UI. Built with PyQt6 + yt-dlp + ffmpeg.

## Features

- EZ Mode (fast paste → sanitize radio links → one-click download)
- Advanced Mode (quality selection, multiple queued items)
- URL normalization (radio/playlist → single watch URL when desired)
- Theme modes: System, Light, Dark, OLED (true black)
- Notifications with tuned durations:
  - Info ≈ 30s
  - Success ≈ 10s
  - Fail ≥ 60s or sticky until dismissed, with FAQ link

## Settings and updates

- Theme: System/Light/Dark/OLED (applies immediately and persists across restarts)
- EZ Mode: hides advanced controls, sanitizes radio links to single videos
- Updates (Settings → Updates):
  - App updates: schedule + action (No Check, Prompt, Auto)
  - yt-dlp updates: enable/disable + cadence

## Notifications

- Info and Success auto-dismiss; Fail stays longer or until dismissed
- Fail notifications link to the in-app FAQ

## Logs and troubleshooting

- Logs are written under %AppData%/YoutubeConverter/logs
- Use Settings → Export Logs to zip recent logs for sharing

## FAQ

- In-app: Help → FAQ (common errors and decisions like resume behavior)
