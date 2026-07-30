# ruff: noqa: I001
from datetime import UTC, datetime
from pathlib import Path

import pytest

from baseball_motion_analysis.app.media_services import (
    ImportVideoRequest,
    MissingMediaFileError,
    UnreadableVideoError,
    VideoLibraryApplicationService,
    generate_media_id,
    sanitize_display_filename,
)
from baseball_motion_analysis.storage import (
    LocalMediaFileStore,
    MediaRecord,
    MediaStatus,
    SqliteMediaRepository,
    StoragePathError,
)
from baseball_motion_analysis.video.replay import classify_browser_playback_status


def test_media_id_generation_is_stable_opaque_shape() -> None:
    media_id = generate_media_id()

    assert media_id.startswith("vid_")
    assert len(media_id) == 36
    assert "/" not in media_id
    assert ".." not in media_id


def test_display_filename_sanitization_removes_path_and_unsafe_characters() -> None:
    assert sanitize_display_filename("../Private Player/session<>01.mp4") == "session_01.mp4"
    assert sanitize_display_filename("") == "uploaded-video"


def test_media_record_storage_serialization_uses_relative_path() -> None:
    record = _record(stored_relative_path=Path("videos/vid_sample.mp4"))

    data = record.to_storage_dict()

    assert data["stored_relative_path"] == "videos/vid_sample.mp4"
    assert data["created_at"] == "2026-07-29T00:00:00+00:00"
    assert data["status"] == "ready"


def test_sqlite_repository_save_get_and_list(tmp_path: Path) -> None:
    repository = SqliteMediaRepository(tmp_path / "library.sqlite3")
    first = _record(media_id="vid_first", display_name="first.mp4")
    second = _record(media_id="vid_second", display_name="second.mp4")

    repository.save(first)
    repository.save(second)

    assert repository.get("vid_first") == first
    assert [record.media_id for record in repository.list_all()] == ["vid_second", "vid_first"]


def test_sqlite_repository_delete_removes_record(tmp_path: Path) -> None:
    repository = SqliteMediaRepository(tmp_path / "library.sqlite3")
    record = _record()
    repository.save(record)

    repository.delete(record.media_id)

    assert repository.get(record.media_id) is None
    assert repository.list_all() == ()


def test_local_file_store_commits_video_to_relative_generated_path(tmp_path: Path) -> None:
    store = LocalMediaFileStore(tmp_path / "media")
    staging_path = store.create_staging_file(".mp4")
    staging_path.write_bytes(b"video bytes")

    relative_path = store.commit_video(staging_path, "vid_sample")

    assert relative_path == Path("videos/vid_sample.mp4")
    assert not staging_path.exists()
    assert store.resolve_relative_path(relative_path).read_bytes() == b"video bytes"


def test_local_file_store_deletes_committed_file(tmp_path: Path) -> None:
    store = LocalMediaFileStore(tmp_path / "media")
    staging_path = store.create_staging_file(".mp4")
    staging_path.write_bytes(b"video bytes")
    relative_path = store.commit_video(staging_path, "vid_sample")

    store.delete_committed_file(relative_path)

    with pytest.raises(StoragePathError, match="missing"):
        store.resolve_relative_path(relative_path)


def test_local_file_store_rejects_path_traversal(tmp_path: Path) -> None:
    store = LocalMediaFileStore(tmp_path / "media")

    with pytest.raises(StoragePathError, match="safe relative path"):
        store.resolve_relative_path(Path("../private.mp4"))


def test_playback_status_classification() -> None:
    assert classify_browser_playback_status(".mp4") == "supported"
    assert classify_browser_playback_status(".webm") == "supported"
    assert classify_browser_playback_status(".avi") == "possibly_unsupported"
    assert classify_browser_playback_status(".mp4", file_exists=False) == "missing"


def test_missing_stored_file_is_reported_for_content(tmp_path: Path) -> None:
    repository = SqliteMediaRepository(tmp_path / "library.sqlite3")
    store = LocalMediaFileStore(tmp_path / "media")
    record = _record(stored_relative_path=Path("videos/missing.mp4"))
    repository.save(record)
    service = VideoLibraryApplicationService(repository=repository, file_store=store)

    manifest = service.get_replay_manifest(record.media_id)

    assert manifest.browser_playback_status == "missing"
    with pytest.raises(MissingMediaFileError):
        service.get_video_content_location(record.media_id)


def test_service_deletes_stored_file_and_metadata(tmp_path: Path) -> None:
    repository = SqliteMediaRepository(tmp_path / "library.sqlite3")
    store = LocalMediaFileStore(tmp_path / "media")
    staging_path = store.create_staging_file(".mp4")
    staging_path.write_bytes(b"video bytes")
    relative_path = store.commit_video(staging_path, "vid_sample")
    record = _record(stored_relative_path=relative_path)
    repository.save(record)
    service = VideoLibraryApplicationService(repository=repository, file_store=store)

    service.delete_video(record.media_id)

    assert repository.get(record.media_id) is None
    with pytest.raises(StoragePathError, match="missing"):
        store.resolve_relative_path(relative_path)


def test_service_deletes_metadata_when_stored_file_is_already_missing(tmp_path: Path) -> None:
    repository = SqliteMediaRepository(tmp_path / "library.sqlite3")
    store = LocalMediaFileStore(tmp_path / "media")
    record = _record(stored_relative_path=Path("videos/missing.mp4"))
    repository.save(record)
    service = VideoLibraryApplicationService(repository=repository, file_store=store)

    service.delete_video(record.media_id)

    assert repository.get(record.media_id) is None


def test_failed_import_cleans_staging_file(tmp_path: Path) -> None:
    repository = SqliteMediaRepository(tmp_path / "library.sqlite3")
    store = LocalMediaFileStore(tmp_path / "media")
    service = VideoLibraryApplicationService(repository=repository, file_store=store)
    staging_path = store.create_staging_file(".mp4")
    staging_path.write_bytes(b"not a real video")

    with pytest.raises(UnreadableVideoError):
        service.import_video(
            ImportVideoRequest(
                staging_path=staging_path,
                display_name="broken.mp4",
                file_size_bytes=staging_path.stat().st_size,
            )
        )

    assert not staging_path.exists()
    assert repository.list_all() == ()


def _record(
    *,
    media_id: str = "vid_sample",
    display_name: str = "sample.mp4",
    stored_relative_path: Path = Path("videos/vid_sample.mp4"),
) -> MediaRecord:
    return MediaRecord(
        media_id=media_id,
        source_type="recorded_video",
        display_name=display_name,
        stored_relative_path=stored_relative_path,
        file_extension=".mp4",
        file_size_bytes=120,
        created_at=datetime(2026, 7, 29, tzinfo=UTC),
        width=32,
        height=24,
        fps=10.0,
        total_frame_count=2,
        duration_seconds=0.2,
        status=MediaStatus.READY,
    )
