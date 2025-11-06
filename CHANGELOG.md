# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-11-06

### Added
- **Home Page with Feature Cards**: New home page with responsive layout and feature shortcuts for improved navigation
- **Collapsible Settings Sections**: Settings page now uses collapsible sections for better organization and easier navigation
- **Search and Filter in Settings**: Added dynamic search functionality to show/hide settings sections based on user input
- **File Conflict Handling**: New file conflict dialog that manages file conflicts during downloads, allowing users to choose actions when files already exist
- **Subtitle Support**: Comprehensive subtitle functionality with the following features:
  - Global and per-item subtitle settings in Step 3 Quality Widget
  - Subtitle language selection
  - Support for auto-generated and embedded subtitles
  - Helper buttons for applying settings to all or selected videos
  - Subtitle availability validation with warnings for each video
  - UI elements for managing subtitle options
- **Enhanced Download Management**: 
  - UI lock/unlock signals during download processes
  - File existence checks before starting downloads
  - Improved progress tracking and status updates
- **Future Features Documentation**: Created comprehensive document outlining potential enhancements including chapter-aware downloading, filename customization, thumbnail embedding, metadata control, and more

### Changed
- **Major Refactor**: Reorganized project structure for future feature implementation:
  - Moved widgets to feature-based folders (`features/general`, `features/home`, `features/youtube_converter`)
  - Better separation of concerns and modularity
- **Theme System Improvements**:
  - Set dark theme as the default
  - Enhanced theme handling and options in settings
  - Improved theme styles for better visual consistency
  - Better styling for disabled buttons across different themes
- **Download Logic Enhancement**: Updated download logic in Step 4 Downloads Widget to handle subtitle settings and file conflicts
- **UI/UX Improvements**:
  - Enhanced UI elements for better user experience and accessibility
  - Improved progress dialog with correct indeterminate state
  - Clearer update prompt messages explaining the update process and restart behavior
- **Settings Organization**: Refactored settings page to utilize collapsible sections for various settings categories

### Fixed
- **Theme and Styles**: Multiple fixes to theming system and visual styles for consistency
- **Download Navigation**: Fixed issue where download page wouldn't go back after finishing
- **Duplicate Settings**: Removed duplicate subtitle settings entries
- **Update Progress Dialog**: Corrected indeterminate state maintenance

### Removed
- Removed obsolete subtitle calls in settings that were causing conflicts

### Known Issues
- **Subtitle Embedding**: Note that embedding subtitles does not currently work and is being addressed in future updates

### Technical Changes
- Added FFmpeg to `.gitignore` to prevent accidental commits
- Enhanced `core/yt_manager.py` with improved download handling
- Updated `MainWindow` to include subtitle settings in download metadata
- Improved error handling and validation throughout the application

---

## [1.2.0] - Previous Release

Initial stable release with core YouTube conversion functionality.
