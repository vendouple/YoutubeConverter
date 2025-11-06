## 🧩 **Chapter-Aware Downloading**

Enable smarter handling of videos with chapters (e.g., music mixes, segmented content):

- **Chapter Detection**: Auto-detect chapters from YouTube metadata.
- **Chapter Selector UI**:
  - Checkbox list of chapters with title + timestamp.
  - Option to select/deselect chapters.
- **Download Modes**:
  - **Split Mode**: Download each chapter as a separate file.
  - **Combine Mode**: Download selected chapters as one merged file.
- **Chapter Naming Rules**:
  - `{chapterTitle}`, `{chapterIndex}`, `{videoTitle} - {chapterTitle}`

---

## 📝 **Filename Customization**

Let users define filename templates globally or per download:

- **Supported Parameters**:
  - `{title}`, `{videoId}`, `{channelName}`, `{dateDownloaded}`, `{playlistName}`, `{index}`, `{format}`, `{resolution}`
- **Settings UI**:
  - Live preview of filename output.
  - Preset templates (e.g., “{channelName} - {title}”, “{index} - {title}”)
- **Sanitization Rules**:
  - Strip illegal characters, truncate long names, optional slugify.

---

## 🖼️ **Thumbnail & Image Embedding**

Enhance audio file presentation and metadata:

- **Embed Thumbnail into Audio**:
  - MP3, M4A, FLAC support.
  - Option to use YouTube thumbnail or custom image.
- **Download Thumbnail Separately**:
  - Choose resolution (default, maxres, etc.)
  - Save as `.jpg` or `.png`

---

## 🧠 **Metadata Control**

Expose metadata editing and automation:

- **Auto-Fill Tags**:
  - Title, Artist, Album, Genre, Year
- **Manual Override**:
  - Editable fields before download
- **Metadata Templates**:
  - Use filename parameters to auto-fill tags

---

## 📥 **Download Queue Enhancements**

Improve control and visibility of downloads:

- **Per-Item Format/Quality Override**
- **Drag to Reorder Queue**
- **Pause/Resume Individual Downloads**
- **Retry Failed Downloads**
- **Concurrent Download Limit** (e.g., 3 at a time)
- **Speed Limiter** (optional throttle)

---

## 🧰 **Advanced Options**

For power users who want deeper control:

- **SponsorBlock Timeline Preview**:
  - Visual overlay of skipped segments
- **Post-Download Actions**:
  - Auto-convert to another format
  - Auto-run script (e.g., move, tag, notify)
- **Folder Profiles**:
  - Save multiple output paths with presets
- **Session Restore**:
  - Reload queue and settings on startup
