"""Local media file validation helpers."""

from __future__ import annotations

from pathlib import Path

SUPPORTED_VIDEO_EXTENSIONS = frozenset({".mp4", ".mov", ".avi", ".mkv", ".webm"})
SUPPORTED_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp"})


class MediaInputError(ValueError):
    """Base error for local media input failures."""


class MediaValidationError(MediaInputError):
    """Raised when a local media path is invalid."""


def normalize_path(path: Path | str) -> Path:
    """Convert path-like input to a Path without resolving user-specific directories."""
    return Path(path).expanduser()


def validate_existing_file(path: Path | str, *, media_kind: str) -> Path:
    """Validate that a path points to an existing local file."""
    candidate = normalize_path(path)
    if not candidate.exists():
        msg = f"{media_kind} file does not exist"
        raise MediaValidationError(msg)
    if not candidate.is_file():
        msg = f"{media_kind} path is not a file"
        raise MediaValidationError(msg)
    return candidate


def validate_video_file_path(path: Path | str) -> Path:
    """Validate a recorded video path by existence and extension."""
    candidate = validate_existing_file(path, media_kind="video")
    if candidate.suffix.lower() not in SUPPORTED_VIDEO_EXTENSIONS:
        msg = f"unsupported video extension: {candidate.suffix.lower() or '<none>'}"
        raise MediaValidationError(msg)
    return candidate


def validate_image_file_path(path: Path | str) -> Path:
    """Validate an image path by existence and extension."""
    candidate = validate_existing_file(path, media_kind="image")
    if candidate.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        msg = f"unsupported image extension: {candidate.suffix.lower() or '<none>'}"
        raise MediaValidationError(msg)
    return candidate


def validate_image_sequence_paths(paths: list[Path] | tuple[Path, ...]) -> tuple[Path, ...]:
    """Validate that a sequence contains at least one supported image file."""
    if not paths:
        msg = "image sequence must contain at least one image"
        raise MediaValidationError(msg)
    return tuple(validate_image_file_path(path) for path in paths)
