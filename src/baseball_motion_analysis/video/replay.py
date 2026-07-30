"""Browser replay helpers for stored videos."""

from __future__ import annotations

from pathlib import Path

SUPPORTED_BROWSER_VIDEO_EXTENSIONS = frozenset({".mp4", ".webm"})
POSSIBLY_UNSUPPORTED_BROWSER_VIDEO_EXTENSIONS = frozenset({".mov", ".avi", ".mkv"})


def classify_browser_playback_status(file_extension: str, *, file_exists: bool = True) -> str:
    """Classify whether a stored video is likely playable by a normal browser."""
    if not file_exists:
        return "missing"
    normalized = file_extension.lower()
    if normalized in SUPPORTED_BROWSER_VIDEO_EXTENSIONS:
        return "supported"
    if normalized in POSSIBLY_UNSUPPORTED_BROWSER_VIDEO_EXTENSIONS:
        return "possibly_unsupported"
    return "unsupported"


def media_type_for_video_path(path: Path) -> str:
    """Return a suitable response media type for a stored video path."""
    match path.suffix.lower():
        case ".mp4":
            return "video/mp4"
        case ".webm":
            return "video/webm"
        case ".mov":
            return "video/quicktime"
        case ".avi":
            return "video/x-msvideo"
        case ".mkv":
            return "video/x-matroska"
        case _:
            return "application/octet-stream"
