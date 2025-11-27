<p align="center">
<img src="YTConverterIcon.png" width="300" alt="Logo">
</p>
<div align="center">

![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/vendouple/YoutubeConverter/.github%2Fworkflows%2Fbuilder.yml)
![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/vendouple/YoutubeConverter/total)

</div>

# YouTube Converter
> [!NOTE]  
> Youtube Converter bug fixes and feature updates will be implemented very slowly. On a future note, I will be migrating this app away from PyQt6 to a faster framework like C for the backend and html for easy sytling in the frontend.
> Features like Cutting, Bulk Converting. Will not be implemented with this framework. So expect v3 to come out in a very long time.


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

- Theme: Light/Dark/OLED (applies immediately and persists across restarts)
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
