"""Application services for browser video library workflows."""

from __future__ import annotations

import re
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from baseball_motion_analysis.core.config import AppSettings
from baseball_motion_analysis.storage.local_file_store import LocalMediaFileStore, StoragePathError
from baseball_motion_analysis.storage.models import MediaRecord, MediaStatus, VideoReplayManifest
from baseball_motion_analysis.storage.repository import MediaRepository
from baseball_motion_analysis.storage.sqlite_repository import SqliteMediaRepository
from baseball_motion_analysis.video import (
    FrameSamplingOptions,
    LocalMediaStorageConfig,
    MediaInputService,
)
from baseball_motion_analysis.video.replay import (
    classify_browser_playback_status,
    media_type_for_video_path,
)
from baseball_motion_analysis.video.validators import MediaValidationError

_SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._ -]+")


def create_video_library_application_service(
    settings: AppSettings,
) -> VideoLibraryApplicationService:
    """Create the default video library application service for runtime settings."""
    file_store = LocalMediaFileStore(settings.media_root)
    repository = SqliteMediaRepository(settings.database_path)
    return VideoLibraryApplicationService(repository=repository, file_store=file_store)


class MediaApplicationError(Exception):
    """Base class for user-facing media application errors."""

    error_code = "media_error"
    user_message = "Media operation failed."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.user_message)
        self.message = message or self.user_message


class InvalidMediaIdError(MediaApplicationError):
    """Raised when a media ID does not exist."""

    error_code = "invalid_media_id"
    user_message = "The requested video could not be found."


class MissingMediaFileError(MediaApplicationError):
    """Raised when metadata exists but the stored media file is missing."""

    error_code = "missing_stored_file"
    user_message = "The stored video file is missing."


class StorageWriteError(MediaApplicationError):
    """Raised when storage cannot complete a write or path operation."""

    error_code = "storage_write_failure"
    user_message = "The video could not be stored."


class RepositoryError(MediaApplicationError):
    """Raised when the metadata repository cannot complete an operation."""

    error_code = "metadata_repository_failure"
    user_message = "The media library could not be updated."


class UnreadableVideoError(MediaApplicationError):
    """Raised when the video validation or metadata extraction fails."""

    error_code = "unreadable_video"
    user_message = "The uploaded file could not be read as a supported video."


@dataclass(frozen=True)
class ImportVideoRequest:
    """Request to import a staged browser upload."""

    staging_path: Path
    display_name: str
    file_size_bytes: int


@dataclass(frozen=True)
class VideoContentLocation:
    """Resolved file location for one stored video."""

    path: Path
    file_size_bytes: int
    media_type: str


class VideoLibraryApplicationService:
    """Application-service boundary for uploaded video library workflows."""

    def __init__(
        self,
        *,
        repository: MediaRepository,
        file_store: LocalMediaFileStore,
        media_input_service: MediaInputService | None = None,
    ) -> None:
        self._repository = repository
        self._file_store = file_store
        self._media_input_service = media_input_service or MediaInputService(
            LocalMediaStorageConfig(media_root=file_store.media_root)
        )

    def create_staging_file(self, suffix: str) -> Path:
        """Create a controlled staging path for a browser upload."""
        try:
            return self._file_store.create_staging_file(suffix)
        except StoragePathError as exc:
            raise StorageWriteError() from exc

    def delete_staging_file(self, path: Path) -> None:
        """Delete a controlled staging path after a failed upload."""
        try:
            self._file_store.delete_staging_file(path)
        except StoragePathError as exc:
            raise StorageWriteError() from exc

    def import_video(self, request: ImportVideoRequest) -> MediaRecord:
        """Validate, store, and index a staged uploaded video."""
        media_id = generate_media_id()
        display_name = sanitize_display_filename(request.display_name)

        try:
            sequence = self._media_input_service.load_video_file(
                request.staging_path,
                sampling=FrameSamplingOptions(max_frame_count=1),
            )
            stored_relative_path = self._file_store.commit_video(request.staging_path, media_id)
            record = MediaRecord(
                media_id=media_id,
                source_type=sequence.source_type.value,
                display_name=display_name,
                stored_relative_path=stored_relative_path,
                file_extension=request.staging_path.suffix.lower(),
                file_size_bytes=request.file_size_bytes,
                created_at=datetime.now(UTC),
                width=sequence.metadata.width,
                height=sequence.metadata.height,
                fps=sequence.metadata.fps,
                total_frame_count=sequence.metadata.total_frame_count,
                duration_seconds=sequence.metadata.duration_seconds,
                status=MediaStatus.READY,
            )
            self._repository.save(record)
        except MediaValidationError as exc:
            self._delete_failed_staging_file(request.staging_path)
            raise UnreadableVideoError() from exc
        except StoragePathError as exc:
            self._delete_failed_staging_file(request.staging_path)
            raise StorageWriteError() from exc
        except OSError as exc:
            self._delete_failed_staging_file(request.staging_path)
            raise StorageWriteError() from exc
        except Exception as exc:
            self._delete_failed_staging_file(request.staging_path)
            raise RepositoryError() from exc

        return record

    def list_videos(self) -> tuple[MediaRecord, ...]:
        """Return stored video records."""
        try:
            return self._repository.list_all()
        except Exception as exc:
            raise RepositoryError() from exc

    def get_video(self, media_id: str) -> MediaRecord:
        """Return one stored video record."""
        try:
            record = self._repository.get(media_id)
        except Exception as exc:
            raise RepositoryError() from exc
        if record is None:
            raise InvalidMediaIdError()
        return record

    def get_replay_manifest(self, media_id: str) -> VideoReplayManifest:
        """Build a browser replay manifest for one stored video."""
        record = self.get_video(media_id)
        file_exists = self._stored_file_exists(record)
        return VideoReplayManifest(
            media_id=record.media_id,
            display_name=record.display_name,
            content_url=f"/api/v1/media/videos/{record.media_id}/content",
            duration_seconds=record.duration_seconds,
            width=record.width,
            height=record.height,
            fps=record.fps,
            browser_playback_status=classify_browser_playback_status(
                record.file_extension,
                file_exists=file_exists,
            ),
        )

    def get_video_content_location(self, media_id: str) -> VideoContentLocation:
        """Resolve a stored video file for media-ID-based content serving."""
        record = self.get_video(media_id)
        try:
            path = self._file_store.resolve_relative_path(record.stored_relative_path)
        except StoragePathError as exc:
            raise MissingMediaFileError() from exc
        return VideoContentLocation(
            path=path,
            file_size_bytes=path.stat().st_size,
            media_type=_media_type_for_extension(record.file_extension),
        )

    def delete_video(self, media_id: str) -> None:
        """Delete one uploaded video's stored file and metadata record."""
        record = self.get_video(media_id)
        try:
            self._file_store.delete_committed_file(record.stored_relative_path)
            self._repository.delete(media_id)
        except StoragePathError as exc:
            raise StorageWriteError("The stored video could not be deleted.") from exc
        except OSError as exc:
            raise StorageWriteError("The stored video could not be deleted.") from exc
        except Exception as exc:
            raise RepositoryError("The media library record could not be deleted.") from exc

    def _stored_file_exists(self, record: MediaRecord) -> bool:
        try:
            self._file_store.resolve_relative_path(record.stored_relative_path)
        except StoragePathError:
            return False
        return True

    def _delete_failed_staging_file(self, staging_path: Path) -> None:
        with suppress(StoragePathError):
            self._file_store.delete_staging_file(staging_path)


def generate_media_id() -> str:
    """Generate a stable opaque media ID."""
    return f"vid_{uuid4().hex}"


def sanitize_display_filename(filename: str) -> str:
    """Return safe display metadata without trusting browser path input."""
    name = Path(filename or "uploaded-video").name.strip()
    name = _SAFE_FILENAME_PATTERN.sub("_", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name or "uploaded-video"


def _media_type_for_extension(file_extension: str) -> str:
    extension_path = Path(f"video{file_extension.lower()}")
    return media_type_for_video_path(extension_path)
