"""Repository protocols for media metadata persistence."""

from __future__ import annotations

from typing import Protocol

from baseball_motion_analysis.storage.models import MediaRecord


class MediaRepository(Protocol):
    """Persistence boundary for media records."""

    def save(self, record: MediaRecord) -> None:
        """Persist a media record transactionally."""

    def get(self, media_id: str) -> MediaRecord | None:
        """Return one media record by ID, if present."""

    def list_all(self) -> tuple[MediaRecord, ...]:
        """Return all media records in newest-first order."""

    def delete(self, media_id: str) -> None:
        """Delete one media record by ID."""
