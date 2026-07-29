"""SQLite implementation of the local media metadata index."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from baseball_motion_analysis.storage.models import MediaRecord, MediaStatus
from baseball_motion_analysis.storage.repository import MediaRepository


class SqliteMediaRepository(MediaRepository):
    """Persist media records in a small local SQLite database."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def save(self, record: MediaRecord) -> None:
        """Persist a media record using a transaction."""
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO media_records (
                    media_id,
                    source_type,
                    display_name,
                    stored_relative_path,
                    file_extension,
                    file_size_bytes,
                    created_at,
                    width,
                    height,
                    fps,
                    total_frame_count,
                    duration_seconds,
                    status,
                    error_code,
                    error_message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(media_id) DO UPDATE SET
                    source_type = excluded.source_type,
                    display_name = excluded.display_name,
                    stored_relative_path = excluded.stored_relative_path,
                    file_extension = excluded.file_extension,
                    file_size_bytes = excluded.file_size_bytes,
                    created_at = excluded.created_at,
                    width = excluded.width,
                    height = excluded.height,
                    fps = excluded.fps,
                    total_frame_count = excluded.total_frame_count,
                    duration_seconds = excluded.duration_seconds,
                    status = excluded.status,
                    error_code = excluded.error_code,
                    error_message = excluded.error_message
                """,
                _record_to_row(record),
            )

    def get(self, media_id: str) -> MediaRecord | None:
        """Return one media record by ID, if present."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM media_records WHERE media_id = ?",
                (media_id,),
            ).fetchone()
        return _row_to_record(row) if row is not None else None

    def list_all(self) -> tuple[MediaRecord, ...]:
        """Return all media records in newest-first order."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM media_records ORDER BY created_at DESC, media_id DESC"
            ).fetchall()
        return tuple(_row_to_record(row) for row in rows)

    def delete(self, media_id: str) -> None:
        """Delete one media record by ID using a transaction."""
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM media_records WHERE media_id = ?",
                (media_id,),
            )

    def _initialize_schema(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS media_records (
                    media_id TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    stored_relative_path TEXT NOT NULL,
                    file_extension TEXT NOT NULL,
                    file_size_bytes INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    width INTEGER NOT NULL,
                    height INTEGER NOT NULL,
                    fps REAL,
                    total_frame_count INTEGER,
                    duration_seconds REAL,
                    status TEXT NOT NULL,
                    error_code TEXT,
                    error_message TEXT
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        return connection


def _record_to_row(record: MediaRecord) -> tuple[object, ...]:
    return (
        record.media_id,
        record.source_type,
        record.display_name,
        record.stored_relative_path.as_posix(),
        record.file_extension,
        record.file_size_bytes,
        record.created_at.isoformat(),
        record.width,
        record.height,
        record.fps,
        record.total_frame_count,
        record.duration_seconds,
        record.status.value,
        record.error_code,
        record.error_message,
    )


def _row_to_record(row: sqlite3.Row) -> MediaRecord:
    values: dict[str, Any] = dict(row)
    return MediaRecord(
        media_id=str(values["media_id"]),
        source_type=str(values["source_type"]),
        display_name=str(values["display_name"]),
        stored_relative_path=Path(str(values["stored_relative_path"])),
        file_extension=str(values["file_extension"]),
        file_size_bytes=int(values["file_size_bytes"]),
        created_at=datetime.fromisoformat(str(values["created_at"])),
        width=int(values["width"]),
        height=int(values["height"]),
        fps=float(values["fps"]) if values["fps"] is not None else None,
        total_frame_count=(
            int(values["total_frame_count"]) if values["total_frame_count"] is not None else None
        ),
        duration_seconds=(
            float(values["duration_seconds"]) if values["duration_seconds"] is not None else None
        ),
        status=MediaStatus(str(values["status"])),
        error_code=str(values["error_code"]) if values["error_code"] is not None else None,
        error_message=str(values["error_message"]) if values["error_message"] is not None else None,
    )
