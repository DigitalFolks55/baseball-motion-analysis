"""API schemas for media upload and replay."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from baseball_motion_analysis.storage.models import MediaRecord, VideoReplayManifest


class ErrorDetail(BaseModel):
    """Structured browser-safe error details."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Structured browser-safe error response."""

    error: ErrorDetail


class DeleteMediaResponse(BaseModel):
    """Response returned after deleting one uploaded media item."""

    media_id: str
    deleted: bool


class MediaRecordResponse(BaseModel):
    """Public media record response without internal storage paths."""

    model_config = ConfigDict(from_attributes=True)

    media_id: str
    source_type: str
    display_name: str
    file_extension: str
    file_size_bytes: int
    created_at: datetime
    width: int
    height: int
    fps: float | None
    total_frame_count: int | None
    duration_seconds: float | None
    status: str
    error_code: str | None
    error_message: str | None

    @classmethod
    def from_record(cls, record: MediaRecord) -> MediaRecordResponse:
        """Create a public response from a storage record."""
        return cls(
            media_id=record.media_id,
            source_type=record.source_type,
            display_name=record.display_name,
            file_extension=record.file_extension,
            file_size_bytes=record.file_size_bytes,
            created_at=record.created_at,
            width=record.width,
            height=record.height,
            fps=record.fps,
            total_frame_count=record.total_frame_count,
            duration_seconds=record.duration_seconds,
            status=record.status.value,
            error_code=record.error_code,
            error_message=record.error_message,
        )


class VideoReplayManifestResponse(BaseModel):
    """Public replay manifest response."""

    media_id: str
    display_name: str
    content_url: str
    duration_seconds: float | None
    width: int
    height: int
    fps: float | None
    browser_playback_status: Literal[
        "supported",
        "possibly_unsupported",
        "unsupported",
        "missing",
    ]

    @classmethod
    def from_manifest(cls, manifest: VideoReplayManifest) -> VideoReplayManifestResponse:
        """Create a public response from a replay manifest."""
        return cls(
            media_id=manifest.media_id,
            display_name=manifest.display_name,
            content_url=manifest.content_url,
            duration_seconds=manifest.duration_seconds,
            width=manifest.width,
            height=manifest.height,
            fps=manifest.fps,
            browser_playback_status=manifest.browser_playback_status,  # type: ignore[arg-type]
        )
