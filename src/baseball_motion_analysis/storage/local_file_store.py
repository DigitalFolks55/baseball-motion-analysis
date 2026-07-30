"""Local filesystem storage for staged and committed browser uploads."""

from __future__ import annotations

import shutil
import tempfile
from os import close
from pathlib import Path


class StoragePathError(ValueError):
    """Raised when storage path input is unsafe or invalid."""


class LocalMediaFileStore:
    """Owns local filesystem placement for uploaded media content."""

    def __init__(self, media_root: Path) -> None:
        self._media_root = media_root.expanduser()
        self._staging_dir = self._media_root / "staging"
        self._video_dir = self._media_root / "videos"
        self._staging_dir.mkdir(parents=True, exist_ok=True)
        self._video_dir.mkdir(parents=True, exist_ok=True)

    @property
    def media_root(self) -> Path:
        """Return the configured media root."""
        return self._media_root

    def create_staging_file(self, suffix: str) -> Path:
        """Create an empty controlled staging file and return its path."""
        normalized_suffix = _safe_suffix(suffix)
        descriptor, path = tempfile.mkstemp(
            suffix=normalized_suffix,
            prefix="upload_",
            dir=self._staging_dir,
        )
        close(descriptor)
        return Path(path)

    def commit_video(self, staging_path: Path, media_id: str) -> Path:
        """Move a staged upload into permanent video storage."""
        if not staging_path.is_file():
            msg = "staging file is missing"
            raise StoragePathError(msg)
        _validate_media_id(media_id)
        _ensure_descendant(staging_path, self._staging_dir)

        target_relative_path = Path("videos") / f"{media_id}{staging_path.suffix.lower()}"
        target_path = self.resolve_relative_path(target_relative_path, must_exist=False)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staging_path), target_path)
        return target_relative_path

    def delete_staging_file(self, path: Path) -> None:
        """Remove a controlled staging file if it still exists."""
        _ensure_descendant(path, self._staging_dir)
        if path.exists() and path.is_file():
            path.unlink()

    def delete_committed_file(self, relative_path: Path) -> None:
        """Remove a committed stored media file by safe relative path."""
        resolved_path = self.resolve_relative_path(relative_path, must_exist=False)
        if resolved_path.exists():
            if not resolved_path.is_file():
                msg = "stored media path is not a file"
                raise StoragePathError(msg)
            resolved_path.unlink()

    def resolve_relative_path(self, relative_path: Path, *, must_exist: bool = True) -> Path:
        """Resolve a stored relative path under the media root."""
        if relative_path.is_absolute() or ".." in relative_path.parts:
            msg = "stored media path is not a safe relative path"
            raise StoragePathError(msg)
        resolved = self._media_root / relative_path
        _ensure_descendant(resolved, self._media_root)
        if must_exist and not resolved.is_file():
            msg = "stored media file is missing"
            raise StoragePathError(msg)
        return resolved


def _safe_suffix(suffix: str) -> str:
    normalized = suffix.lower().strip()
    if not normalized:
        return ".upload"
    if not normalized.startswith("."):
        normalized = f".{normalized}"
    if "/" in normalized or "\\" in normalized or ".." in normalized:
        return ".upload"
    return normalized


def _validate_media_id(media_id: str) -> None:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
    if not media_id or any(character not in allowed for character in media_id):
        msg = "media ID contains unsupported characters"
        raise StoragePathError(msg)


def _ensure_descendant(path: Path, root: Path) -> None:
    resolved_path = path.resolve(strict=False)
    resolved_root = root.resolve(strict=False)
    if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
        msg = "path is outside the configured media root"
        raise StoragePathError(msg)
