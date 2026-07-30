from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from baseball_motion_analysis.app.main import create_app
from baseball_motion_analysis.core.config import AppSettings, RuntimeMode


def test_web_ui_and_static_assets_are_available(tmp_path: Path) -> None:
    client = TestClient(_create_test_app(tmp_path))

    page = client.get("/")
    script = client.get("/static/app.js")
    styles = client.get("/static/styles.css")

    assert page.status_code == 200
    assert "Baseball Motion Video Review" in page.text
    assert "Local" in page.text
    assert script.status_code == 200
    assert styles.status_code == 200


def test_upload_library_replay_manifest_and_content_range(tmp_path: Path) -> None:
    client = TestClient(_create_test_app(tmp_path))
    video_path = _create_tiny_video(tmp_path / "pitching-session.avi", frame_count=4, fps=10.0)

    upload_response = client.post(
        "/api/v1/media/videos",
        files={"file": ("pitching-session.avi", video_path.read_bytes(), "video/x-msvideo")},
    )

    assert upload_response.status_code == 200
    uploaded = upload_response.json()
    media_id = uploaded["media_id"]
    assert media_id.startswith("vid_")
    assert uploaded["display_name"] == "pitching-session.avi"
    assert uploaded["width"] == 32
    assert uploaded["height"] == 24
    assert "stored_relative_path" not in uploaded
    assert str(tmp_path) not in upload_response.text

    library_response = client.get("/api/v1/media/videos")
    assert library_response.status_code == 200
    assert [record["media_id"] for record in library_response.json()] == [media_id]

    manifest_response = client.get(f"/api/v1/media/videos/{media_id}/replay")
    assert manifest_response.status_code == 200
    manifest = manifest_response.json()
    assert manifest["media_id"] == media_id
    assert manifest["content_url"] == f"/api/v1/media/videos/{media_id}/content"
    assert manifest["browser_playback_status"] == "possibly_unsupported"
    assert str(tmp_path) not in manifest_response.text

    content_response = client.get(manifest["content_url"])
    assert content_response.status_code == 200
    assert content_response.headers["accept-ranges"] == "bytes"
    file_size = int(content_response.headers["content-length"])

    range_response = client.get(manifest["content_url"], headers={"Range": "bytes=0-9"})
    assert range_response.status_code == 206
    assert range_response.headers["accept-ranges"] == "bytes"
    assert range_response.headers["content-range"] == f"bytes 0-9/{file_size}"
    assert range_response.content == content_response.content[:10]

    invalid_range_response = client.get(
        manifest["content_url"], headers={"Range": f"bytes={file_size}-{file_size}"}
    )
    assert invalid_range_response.status_code == 416
    assert invalid_range_response.headers["content-range"] == f"bytes */{file_size}"
    assert invalid_range_response.json()["error"]["code"] == "invalid_http_byte_range"


def test_delete_uploaded_video_removes_file_and_library_record(tmp_path: Path) -> None:
    client = TestClient(_create_test_app(tmp_path))
    video_path = _create_tiny_video(tmp_path / "delete-session.avi", frame_count=3, fps=10.0)
    upload_response = client.post(
        "/api/v1/media/videos",
        files={"file": ("delete-session.avi", video_path.read_bytes(), "video/x-msvideo")},
    )
    media_id = upload_response.json()["media_id"]
    stored_files = list((tmp_path / "media" / "videos").iterdir())

    delete_response = client.delete(f"/api/v1/media/videos/{media_id}")

    assert delete_response.status_code == 200
    assert delete_response.json() == {"media_id": media_id, "deleted": True}
    assert list((tmp_path / "media" / "videos").iterdir()) == []
    assert all(not path.exists() for path in stored_files)

    library_response = client.get("/api/v1/media/videos")
    assert library_response.status_code == 200
    assert library_response.json() == []

    content_response = client.get(f"/api/v1/media/videos/{media_id}/content")
    assert content_response.status_code == 404
    assert content_response.json()["error"]["code"] == "invalid_media_id"
    assert str(tmp_path) not in delete_response.text


def test_delete_invalid_media_id_returns_structured_error(tmp_path: Path) -> None:
    client = TestClient(_create_test_app(tmp_path))

    response = client.delete("/api/v1/media/videos/vid_missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "invalid_media_id"


def test_invalid_empty_oversized_and_unreadable_uploads_are_rejected(tmp_path: Path) -> None:
    client = TestClient(_create_test_app(tmp_path, max_upload_mb=1))

    missing_response = client.post("/api/v1/media/videos")
    empty_response = client.post(
        "/api/v1/media/videos",
        files={"file": ("empty.mp4", b"", "video/mp4")},
    )
    oversized_response = client.post(
        "/api/v1/media/videos",
        files={"file": ("large.mp4", b"0" * (1024 * 1024 + 1), "video/mp4")},
    )
    invalid_extension_response = client.post(
        "/api/v1/media/videos",
        files={"file": ("notes.txt", b"not a video", "text/plain")},
    )
    unreadable_response = client.post(
        "/api/v1/media/videos",
        files={"file": ("broken.mp4", b"not a real video", "video/mp4")},
    )

    assert missing_response.status_code == 400
    assert missing_response.json()["error"]["code"] == "invalid_upload"
    assert empty_response.status_code == 400
    assert empty_response.json()["error"]["code"] == "empty_upload"
    assert oversized_response.status_code == 413
    assert oversized_response.json()["error"]["code"] == "file_too_large"
    assert invalid_extension_response.status_code == 422
    assert invalid_extension_response.json()["error"]["code"] == "unreadable_video"
    assert unreadable_response.status_code == 422
    assert unreadable_response.json()["error"]["code"] == "unreadable_video"
    assert _staging_files(tmp_path) == []


def test_server_mode_configuration_is_reflected_in_ui(tmp_path: Path) -> None:
    app = _create_test_app(tmp_path, runtime_mode=RuntimeMode.SERVER)
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "Server" in response.text
    assert "does not include authentication" in response.text


def test_existing_health_endpoint_still_works(tmp_path: Path) -> None:
    client = TestClient(_create_test_app(tmp_path))

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def _create_test_app(
    tmp_path: Path,
    *,
    runtime_mode: RuntimeMode = RuntimeMode.LOCAL,
    max_upload_mb: int = 10,
) -> object:
    settings = AppSettings(
        runtime_mode=runtime_mode,
        media_root=tmp_path / "media",
        database_path=tmp_path / "library.sqlite3",
        max_upload_mb=max_upload_mb,
    )
    return create_app(settings=settings)


def _staging_files(tmp_path: Path) -> list[Path]:
    staging_dir = tmp_path / "media" / "staging"
    return list(staging_dir.iterdir()) if staging_dir.exists() else []


def _create_tiny_video(path: Path, *, frame_count: int, fps: float) -> Path:
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        fps,
        (32, 24),
    )
    if not writer.isOpened():
        pytest.skip("OpenCV could not create the tiny video fixture")

    try:
        for index in range(frame_count):
            frame = np.full((24, 32, 3), index * 25, dtype=np.uint8)
            writer.write(frame)
    finally:
        writer.release()

    return path
