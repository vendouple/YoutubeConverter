# Youtube Converter

Convert yt videos to audio or video again easily!

### SponsorBlock (automatic trimming)

- Enable in Quality step → Advanced → "Remove segments with SponsorBlock".
- Categories include sponsor, intro/outro, interaction, music_offtopic (aka non_music).
- The app first tries fast, lossless trimming. If that can’t be applied for the current format, it automatically re-encodes using ffmpeg filters to remove segments.

### FAQ

- The app seems like it hasn't been updated in a while, will it still work?
  - The app should work 90%, unless ytdlp or ffmpeg changes significantly it will fetch from the repo itself and auto update! So it should still work nonetheless.
- Help! The app has a bug!
  - Report it! Go to the issues tab

...more to come
