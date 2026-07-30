"""Persistent media library models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path


class MediaStatus(StrEnum):
    """Processing state for a stored media item."""

    IMPORTING = "importing"
    READY = "ready"
    FAILED = "failed"


@dataclass(frozen=True)
class MediaRecord:
    """Metadata record for one stored media item."""

    media_id: str
    source_type: str
    display_name: str
    stored_relative_path: Path
    file_extension: str
    file_size_bytes: int
    created_at: datetime
    width: int
    height: int
    fps: float | None
    total_frame_count: int | None
    duration_seconds: float | None
    status: MediaStatus
    error_code: str | None = None
    error_message: str | None = None

    def to_storage_dict(self) -> dict[str, object]:
        """Serialize the record into simple storage primitives."""
        data = asdict(self)
        data["stored_relative_path"] = self.stored_relative_path.as_posix()
        data["created_at"] = self.created_at.isoformat()
        data["status"] = self.status.value
        return data


@dataclass(frozen=True)
class VideoReplayManifest:
    """Browser replay metadata for one stored video."""

    media_id: str
    display_name: str
    content_url: str
    duration_seconds: float | None
    width: int
    height: int
    fps: float | None
    browser_playback_status: str
