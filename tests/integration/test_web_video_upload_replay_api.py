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
    assert 'id="languageSelect"' in page.text
    assert "English" in page.text
    assert "日本語" in page.text
    assert 'data-i18n="language.label"' in page.text
    assert 'data-i18n="upload.title"' in page.text
    assert 'data-i18n="result.feedback"' in page.text
    assert "Local" in page.text
    assert "Upload Video" in page.text
    assert "Video Library" in page.text
    assert "Motion Analysis" in page.text
    assert "Swing Analysis" in page.text
    assert "Throwing" in page.text
    assert "Pitching" in page.text
    assert "Fielding" in page.text
    assert "Video-driven" in page.text
    assert "Detected locally from sampled video frames" in page.text
    assert "selected automatically" in page.text
    assert "Right-handed" in page.text
    assert "Quality Mode" in page.text
    assert "Higher accuracy" in page.text
    assert "Advanced Pose Debug" in page.text
    assert "Single pose" in page.text
    assert "Notebook parity" not in page.text
    assert (
        '<option value="notebook_parity" data-i18n="pose_mode.single_pose">Single pose</option>'
        in page.text
    )
    assert "Overlay Source" in page.text
    assert "Score Confidence" in page.text
    assert "Methodology" in page.text
    assert 'data-i18n="table.unit">Unit</th>' in page.text
    assert "Poses" in page.text
    assert "Evaluation Lines" in page.text
    assert "Metric" in page.text
    assert 'id="evaluationMetricControl"' in page.text
    assert 'id="evaluationMetricToggle"' in page.text
    assert 'aria-haspopup="true"' in page.text
    assert 'aria-expanded="false"' in page.text
    assert 'id="evaluationMetricMenu"' in page.text
    assert "multiple size=" not in page.text
    assert page.text.index("poseOverlayToggle") < page.text.index("evaluationLinesToggle")
    assert page.text.index("evaluationLinesToggle") < page.text.index("evaluationMetricControl")
    assert page.text.index("evaluationMetricControl") < page.text.index("playbackRate")
    assert 'aria-pressed="false"' in page.text
    assert "Diagnostics" in page.text
    assert "Pose Quality" in page.text
    assert '<details id="analysisDiagnostics"' in page.text
    assert page.text.index("Diagnostics") > page.text.index("Detected Faults")
    assert page.text.index("Limitations") > page.text.index("Diagnostics")
    assert page.text.index("Pose Quality") > page.text.index("Limitations")
    assert "Run Swing Analysis" in page.text
    assert "Clear Analysis" in page.text
    assert "poseOverlayCanvas" in page.text
    assert "Replay" in page.text
    assert "Use Default Swing Pose" not in page.text
    assert "Pose JSON" not in page.text
    assert "Phase Frame Indexes" not in page.text
    assert script.status_code == 200
    assert "/api/v1/analysis/swing/video" in script.text
    assert "quality_mode" in script.text
    assert "pose_mode" in script.text
    assert "pose_mode: swingPoseMode.value" in script.text
    assert "overlay_source" in script.text
    assert "analysisRawOverlayFrames" in script.text
    assert "analysisEvaluationOverlay" in script.text
    assert "evaluation_overlay" in script.text
    assert "poseOverlayToggle" in script.text
    assert "evaluationMetricToggle" in script.text
    assert "evaluationMetricMenu" in script.text
    assert "poseOverlayEnabled = !poseOverlayEnabled" in script.text
    assert "updatePoseOverlayToggle" in script.text
    assert "updateEvaluationLinesToggle" in script.text
    assert "updateEvaluationMetricSelect" in script.text
    assert "syncEvaluationMetricSelectSelection" in script.text
    assert "selectedEvaluationMetrics" in script.text
    assert "drawEvaluationOverlayLines" in script.text
    assert "evaluationLinesForFrame" in script.text
    assert "evaluationLinesEnabled = !evaluationLinesEnabled" in script.text
    assert "drawSkeletonLines(context, keypoints, contentRect)" in script.text
    assert "drawKeypoint(context, keypoint, contentRect, frame.is_event_frame)" in script.text
    assert "drawKeypointLabel" not in script.text
    assert "videoPlayer.playbackRate = Number(playbackRate.value)" in script.text
    assert '"overlay.active": "Overlay active: {modes} aligned to replay."' in script.text
    assert '"overlay.offset": ", offset {offsetMs} ms"' in script.text
    assert "Single Pose" in script.text
    assert "Event confidence" in script.text
    assert "languageStorageKey" in script.text
    assert "currentLanguage" in script.text
    assert "applyLanguage()" in script.text
    assert "lastSwingAnalysisResult" in script.text
    assert "localizedSwingSummary" in script.text
    assert "localizedImprovementPoints" in script.text
    assert "localStorage.setItem(languageStorageKey, currentLanguage)" in script.text
    assert "renderPoseQuality" in script.text
    assert "videoContentRect" in script.text
    assert "renderSwingVideoAnalysis" in script.text
    assert "swingMethodology" in script.text
    assert "clearAnalysis({ status" in script.text
    assert "drawPoseOverlay" in script.text
    assert 'videoPlayer.addEventListener("timeupdate"' in script.text
    assert 'motionType.addEventListener("change"' in script.text
    assert "stepFrame(direction)" in script.text
    assert styles.status_code == 200
    assert "review-layout" in page.text
    assert "upload-panel review-column" in page.text
    assert "library-panel review-column" in page.text
    assert "replay-panel review-column" in page.text
    assert "analysis-panel review-column" in page.text
    assert "grid-template-areas" in styles.text
    assert '"upload replay"' in styles.text
    assert '"library replay"' in styles.text
    assert '"analysis analysis"' in styles.text
    assert "lower-workspace" not in page.text
    assert "pose-overlay" in styles.text
    assert "replay-toolbar" in styles.text
    assert "pose-overlay-toggle" in styles.text
    assert "evaluation-lines-toggle" in styles.text
    assert "toolbar-field" in styles.text
    assert "metric-control" in styles.text
    assert "metric-dropdown-toggle" in styles.text
    assert "metric-dropdown-menu" in styles.text
    assert "metric-dropdown-item" in styles.text
    assert "language-control" in styles.text
    assert "min-height: 2.25rem" in styles.text
    assert "evidence-cell" in styles.text
    assert "table-cell-content" in styles.text
    assert "metrics-table" in styles.text
    assert "metrics-evidence-column" in styles.text
    assert "width: 7.5rem" in styles.text
    assert "max-height: 4.75rem" in styles.text
    assert "fault-evidence" in styles.text
    assert "metrics-evidence" in styles.text
    assert "max-height: min(42vh, 32rem)" in styles.text
    assert "overflow-y: auto" in styles.text
    assert "overflow-x: hidden" in styles.text


def test_web_ui_evaluation_metric_filter_static_behavior(tmp_path: Path) -> None:
    client = TestClient(_create_test_app(tmp_path))

    page = client.get("/")
    script = client.get("/static/app.js")

    assert page.status_code == 200
    assert script.status_code == 200
    assert page.text.index("poseOverlayToggle") < page.text.index("evaluationLinesToggle")
    assert page.text.index("evaluationLinesToggle") < page.text.index("evaluationMetricControl")
    assert page.text.index("evaluationMetricControl") < page.text.index("playbackRate")

    assert 'const allEvaluationMetricsValue = "__all__";' in script.text
    assert "const selectedEvaluationMetrics = new Set();" in script.text
    assert 'label: t("overlay.all_metrics")' in script.text
    assert "localizedLabels" in script.text
    assert 'normalized_stance_width: "Stance width"' in script.text
    assert 'normalized_stance_width: "スタンス幅"' in script.text
    assert 'torso_tilt_preservation: "Tilt hold"' in script.text
    assert 'hip_shoulder_separation_timing: "Hip/shoulder timing"' in script.text
    assert 'follow_through_posture_balance: "Follow-through"' in script.text
    assert "evaluationMetricNames()" in script.text
    assert "seenMetricNames.has(line.metric_name)" in script.text
    assert "value: metricName" in script.text
    assert "label: formatEvaluationMetricLabel(metricName)" in script.text
    assert "evaluationMetricToggle.disabled = metricNames.length === 0" in script.text
    assert "selectedEvaluationMetrics.clear()" in script.text
    assert "syncEvaluationMetricSelectSelection()" in script.text
    assert "evaluationMetricMenuItem" in script.text
    assert 'checkbox.type = "checkbox"' in script.text

    assert "return selectedEvaluationLines().filter(" in script.text
    all_metric_branch = "if (selectedEvaluationMetrics.size === 0) return analysisEvaluationOverlay"
    assert all_metric_branch in script.text
    assert "selectedEvaluationMetrics.has(line.metric_name)" in script.text
    assert "if (evaluationLinesEnabled) {" in script.text
    assert "drawEvaluationOverlayLines(context, frame, contentRect)" in script.text
    assert (
        'return t("overlay.metric_groups_mode", { count: selectedEvaluationMetrics.size });'
        in script.text
    )

    listener_start = script.text.index('evaluationMetricMenu.addEventListener("change"')
    listener_body = script.text[listener_start : listener_start + 260]
    assert "syncSelectedEvaluationMetricsFromMenu(event.target);" in listener_body
    assert "drawPoseOverlay();" in listener_body
    sync_function = "function syncSelectedEvaluationMetricsFromMenu(changedCheckbox)"
    sync_start = script.text.index(sync_function)
    sync_body = script.text[sync_start : sync_start + 520]
    assert "changedCheckbox.value === allEvaluationMetricsValue" in sync_body
    assert "selectedEvaluationMetrics.add(changedCheckbox.value)" in sync_body
    assert "selectedEvaluationMetrics.delete(changedCheckbox.value)" in sync_body
    assert "syncEvaluationMetricSelectSelection();" in sync_body
    assert "fetch(" not in listener_body
    assert "playbackRate" not in listener_body
    assert "clearAnalysis" not in listener_body
    assert 'evaluationMetricToggle.addEventListener("click"' in script.text
    assert 'document.addEventListener("keydown"' in script.text


def test_web_ui_japanese_localization_static_behavior(tmp_path: Path) -> None:
    client = TestClient(_create_test_app(tmp_path))

    page = client.get("/")
    script = client.get("/static/app.js")

    assert page.status_code == 200
    assert script.status_code == 200
    assert '<select id="languageSelect" autocomplete="off">' in page.text
    assert '<option value="en" selected>English</option>' in page.text
    assert '<option value="ja">日本語</option>' in page.text
    assert "野球動作ビデオレビュー" in script.text
    assert "動画アップロード" in script.text
    assert "スイング分析を実行" in script.text
    assert "表示フレームに基づく v2 少年野球ベースライン評価" in script.text
    assert "良い点" in script.text
    assert "改善ポイント" in script.text
    assert "スタンス幅" in script.text
    assert "構え" in script.text
    assert "ドアスイング / キャスティング" in script.text
    assert "胸の前で腕を組む回転ドリル" in script.text
    assert 'languageSelect?.addEventListener("change"' in script.text
    assert "renderSwingVideoAnalysis(lastSwingAnalysisResult)" in script.text
    assert "localizedLabels[currentLanguage]" in script.text

    listener_start = script.text.index('languageSelect?.addEventListener("change"')
    listener_body = script.text[listener_start : listener_start + 260]
    assert "localStorage.setItem(languageStorageKey, currentLanguage)" in listener_body
    assert "applyLanguage();" in listener_body
    assert "fetch(" not in listener_body
    assert "runSwingAnalysisButton" not in listener_body


def test_web_ui_evidence_cells_are_bounded_and_scrollable(tmp_path: Path) -> None:
    client = TestClient(_create_test_app(tmp_path))

    script = client.get("/static/app.js")
    styles = client.get("/static/styles.css")

    assert script.status_code == 200
    assert styles.status_code == 200
    assert "metrics-evidence-column" in script.text
    metrics_evidence_call = (
        'appendScrollableCell(\n      row,\n      (metric.evidence_frames ?? []).join(", ")'
    )
    assert metrics_evidence_call in script.text
    evidence_class_assignment = (
        "content.className = `table-cell-content evidence-cell ${contentClassName}`;"
    )
    assert evidence_class_assignment in script.text
    assert 'content.className = "table-cell-content";' in script.text
    assert "if (String(value).length > 32) content.tabIndex = 0" in script.text
    assert "content.tabIndex = 0" in script.text
    assert 'evidence.className = "evidence-cell fault-evidence"' in script.text
    assert "evidence.tabIndex = 0" in script.text
    assert ".evidence-cell" in styles.text
    assert ".table-cell-content" in styles.text
    assert ".metrics-table" in styles.text
    assert ".metrics-evidence-column" in styles.text
    assert "width: 7.5rem" in styles.text
    assert "max-width: 6.75rem" in styles.text
    assert "max-height: 4.75rem" in styles.text
    assert "overflow-y: auto" in styles.text
    assert "overflow-x: hidden" in styles.text
    assert "overflow-wrap: anywhere" in styles.text
    assert "overscroll-behavior: contain" in styles.text


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
