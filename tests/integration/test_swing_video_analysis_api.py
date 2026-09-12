from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from baseball_motion_analysis.app.main import create_app
from baseball_motion_analysis.app.swing_services import SwingVideoAnalysisApplicationService
from baseball_motion_analysis.core.config import AppSettings
from baseball_motion_analysis.motion import SwingMetricName
from baseball_motion_analysis.pose import (
    PoseDebugDiagnostics,
    PoseEstimationResult,
    PoseFrame,
    PoseKeypointName,
    pose_quality_diagnostics,
)
from baseball_motion_analysis.video import FrameData
from unit.swing_test_helpers import good_swing_frames


def test_swing_video_analysis_endpoint_returns_events_overlay_and_cached_pose(
    tmp_path: Path,
) -> None:
    app = _create_test_app(tmp_path)
    client = TestClient(app)
    video_path = _create_tiny_video(tmp_path / "swing-session.avi", frame_count=8, fps=10.0)
    upload_response = client.post(
        "/api/v1/media/videos",
        files={"file": ("swing-session.avi", video_path.read_bytes(), "video/x-msvideo")},
    )
    media_id = upload_response.json()["media_id"]
    app.state.swing_video_analysis_service = SwingVideoAnalysisApplicationService(
        video_library_service=app.state.video_library_service,
        pose_estimator=BodyOnlyPoseEstimator(),
    )

    first_response = client.post(
        "/api/v1/analysis/swing/video",
        json={"media_id": media_id, "handedness": "right_handed"},
    )
    second_response = client.post(
        "/api/v1/analysis/swing/video",
        json={"media_id": media_id, "handedness": "right_handed"},
    )

    assert first_response.status_code == 200
    first_payload = first_response.json()
    assert first_payload["analysis"]["overall_score"] >= 0.0
    assert first_payload["analysis"]["methodology_version"] == "swing_evaluation_v2"
    assert {
        "metric_deduction",
        "fault_deduction",
    }.issubset(first_payload["analysis"]["phase_scores"][0])
    assert any(
        metric["name"] == "normalized_stance_width"
        for metric in first_payload["analysis"]["metrics"]
    )
    assert first_payload["feedback"]["summary"]
    assert first_payload["pose"]
    assert first_payload["raw_pose"]
    assert all("bat_tip" not in frame["keypoints"] for frame in first_payload["pose"])
    assert len(first_payload["events"]) == 5
    assert all(event["detection_method"] for event in first_payload["events"])
    assert {event["phase"] for event in first_payload["events"]} == {
        "setup",
        "stride",
        "foot_strike",
        "impact",
        "follow_through",
    }
    assert first_payload["analysis"]["phases"]["phase_confidences"]["impact"] > 0
    assert first_payload["analysis"]["phases"]["detection_methods"]["impact"]
    assert first_payload["analysis"]["phases"]["event_statuses"]["impact"] == "estimated"
    assert (
        next(event for event in first_payload["events"] if event["phase"] == "impact")["status"]
        == "estimated"
    )
    assert all(event["is_visible"] for event in first_payload["events"])
    assert all(event["is_overlay_event"] for event in first_payload["events"])
    assert first_payload["pose_diagnostics"]["detected_pose_frame_ratio"] == 1.0
    assert first_payload["raw_pose_diagnostics"]["detected_pose_frame_ratio"] == 1.0
    assert first_payload["pose_debug_diagnostics"]["running_mode"] == "video"
    assert first_payload["pose_debug_diagnostics"]["requested_num_poses"] == 1
    assert first_payload["pose_debug_diagnostics"]["selected_candidate_indexes"] == [0]
    assert first_payload["pose_debug_diagnostics"]["candidate_switch_count"] == 0
    assert first_payload["pose_debug_diagnostics"]["candidate_ambiguity_count"] == 0
    assert first_payload["frame_quality_diagnostics"]["total_frame_count"] == 8
    assert first_payload["frame_quality_diagnostics"]["usable_frame_count"] >= 1
    assert first_payload["active_window_diagnostics"]["peak_motion_frame_index"] >= 0
    assert "affected_metrics" in first_payload["scoring_evidence_diagnostics"]
    assert first_payload["sampling_diagnostics"]["quality_mode"] == "higher_accuracy"
    assert first_payload["sampling_diagnostics"]["sampled_frame_count"] == 8
    assert first_payload["sampling_diagnostics"]["full_frame_sampling"] is True
    assert first_payload["overlay"]
    assert first_payload["raw_overlay"]
    assert first_payload["evaluation_overlay"]
    assert {line["metric_name"] for line in first_payload["evaluation_overlay"]} == {
        metric_name.value for metric_name in SwingMetricName
    }
    evaluation_line = first_payload["evaluation_overlay"][0]
    assert {
        "metric_name",
        "phase",
        "frame_index",
        "start",
        "end",
        "severity",
        "confidence",
        "style",
        "color_role",
    }.issubset(evaluation_line)
    assert isinstance(evaluation_line["start"]["x"], float)
    assert isinstance(evaluation_line["end"]["y"], float)
    assert first_payload["overlay"][0]["source"] == "stabilized"
    assert first_payload["raw_overlay"][0]["source"] == "raw"
    assert "interpolated" in first_payload["overlay"][0]["keypoints"][0]
    assert "smoothed" in first_payload["overlay"][0]["keypoints"][0]
    assert "out_of_frame" in first_payload["overlay"][0]["keypoints"][0]
    assert any(frame["is_event_frame"] for frame in first_payload["overlay"])
    assert any(
        keypoint["label"] for frame in first_payload["overlay"] for keypoint in frame["keypoints"]
    )
    assert first_payload["limitations"]
    assert any("bat tip" in limitation for limitation in first_payload["limitations"])
    assert first_payload["pose_cache_hit"] is False
    assert str(tmp_path) not in first_response.text

    assert second_response.status_code == 200
    assert second_response.json()["pose_cache_hit"] is True


def test_swing_video_analysis_endpoint_can_skip_impact_without_ball_contact(
    tmp_path: Path,
) -> None:
    app = _create_test_app(tmp_path)
    client = TestClient(app)
    video_path = _create_tiny_video(tmp_path / "skip-impact-session.avi", frame_count=8, fps=10.0)
    upload_response = client.post(
        "/api/v1/media/videos",
        files={
            "file": (
                "skip-impact-session.avi",
                video_path.read_bytes(),
                "video/x-msvideo",
            )
        },
    )
    app.state.swing_video_analysis_service = SwingVideoAnalysisApplicationService(
        video_library_service=app.state.video_library_service,
        pose_estimator=BodyOnlyPoseEstimator(),
    )

    response = client.post(
        "/api/v1/analysis/swing/video",
        json={
            "media_id": upload_response.json()["media_id"],
            "handedness": "right_handed",
            "impact_detection_policy": "skip_without_ball",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis"]["phases"]["event_statuses"]["impact"] == "skipped"
    impact_event = next(event for event in payload["events"] if event["phase"] == "impact")
    assert impact_event["status"] == "skipped"
    assert impact_event["is_visible"] is False
    assert impact_event["is_overlay_event"] is False
    assert not any(
        frame["frame_index"] == impact_event["frame_index"] and frame["is_event_frame"]
        for frame in payload["overlay"]
    )
    attack_metric = next(
        metric
        for metric in payload["analysis"]["metrics"]
        if metric["name"] == "estimated_attack_angle"
    )
    head_metric = next(
        metric
        for metric in payload["analysis"]["metrics"]
        if metric["name"] == "head_translation_ratio"
    )
    follow_metric = next(
        metric
        for metric in payload["analysis"]["metrics"]
        if metric["name"] == "follow_through_posture_balance"
    )
    assert attack_metric["severity"] == "not_evaluated"
    assert attack_metric["value"] is None
    assert head_metric["severity"] != "not_evaluated"
    assert follow_metric["severity"] != "not_evaluated"
    assert any("no-ball fallback anchor" in limitation for limitation in head_metric["limitations"])
    assert any(
        "no-ball fallback anchor" in limitation for limitation in follow_metric["limitations"]
    )


def test_swing_video_analysis_endpoint_rejects_invalid_media_id(tmp_path: Path) -> None:
    client = TestClient(_create_test_app(tmp_path))

    response = client.post(
        "/api/v1/analysis/swing/video",
        json={"media_id": "vid_missing", "handedness": "right_handed"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "invalid_media_id"


def test_swing_video_analysis_endpoint_requires_configured_mediapipe_model(
    tmp_path: Path,
) -> None:
    client = TestClient(_create_test_app(tmp_path))
    video_path = _create_tiny_video(tmp_path / "needs-model.avi", frame_count=3, fps=10.0)
    upload_response = client.post(
        "/api/v1/media/videos",
        files={"file": ("needs-model.avi", video_path.read_bytes(), "video/x-msvideo")},
    )

    response = client.post(
        "/api/v1/analysis/swing/video",
        json={"media_id": upload_response.json()["media_id"], "handedness": "right_handed"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "missing_mediapipe_pose_model"


def test_swing_video_analysis_endpoint_rejects_invalid_sampling(tmp_path: Path) -> None:
    client = TestClient(_create_test_app(tmp_path))

    response = client.post(
        "/api/v1/analysis/swing/video",
        json={
            "media_id": "vid_missing",
            "handedness": "right_handed",
            "sampling": {"target_fps": 0, "max_frame_count": 0},
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_swing_video_analysis"


def test_swing_video_analysis_endpoint_accepts_notebook_parity_debug_mode(
    tmp_path: Path,
) -> None:
    app = _create_test_app(tmp_path)
    client = TestClient(app)
    video_path = _create_tiny_video(tmp_path / "parity-session.avi", frame_count=4, fps=10.0)
    upload_response = client.post(
        "/api/v1/media/videos",
        files={"file": ("parity-session.avi", video_path.read_bytes(), "video/x-msvideo")},
    )
    app.state.swing_video_analysis_service = SwingVideoAnalysisApplicationService(
        video_library_service=app.state.video_library_service,
        pose_estimator=BodyOnlyPoseEstimator(processing_mode="notebook_parity"),
    )

    response = client.post(
        "/api/v1/analysis/swing/video",
        json={
            "media_id": upload_response.json()["media_id"],
            "handedness": "right_handed",
            "pose_mode": "notebook_parity",
            "overlay_source": "raw",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["pose_debug_diagnostics"]["processing_mode"] == "notebook_parity"
    assert payload["raw_overlay"]


def _create_test_app(tmp_path: Path) -> object:
    settings = AppSettings(
        media_root=tmp_path / "media",
        database_path=tmp_path / "library.sqlite3",
        max_upload_mb=10,
        mediapipe_pose_model_path=None,
    )
    return create_app(settings=settings)


class BodyOnlyPoseEstimator:
    def __init__(self, *, processing_mode: str = "normal") -> None:
        self.processing_mode = processing_mode

    def estimate(self, frames: tuple[FrameData, ...]) -> PoseEstimationResult:
        source_frames = good_swing_frames()
        pose_frames: list[PoseFrame] = []
        for index, frame in enumerate(frames):
            source = source_frames[min(index, len(source_frames) - 1)]
            pose_frames.append(
                PoseFrame(
                    frame_index=frame.frame_index,
                    timestamp_seconds=frame.timestamp_seconds,
                    keypoints={
                        name: keypoint
                        for name, keypoint in source.keypoints.items()
                        if name not in {PoseKeypointName.BAT_TIP, PoseKeypointName.BAT_BARREL}
                    },
                )
            )
        raw_pose_frames = tuple(pose_frames)
        return PoseEstimationResult(
            frames=tuple(pose_frames),
            limitations=(
                "MediaPipe Pose tracks player body landmarks only; bat tip, bat barrel, "
                "and ball position are not detected.",
            ),
            raw_frames=raw_pose_frames,
            raw_diagnostics=pose_quality_diagnostics(
                raw_pose_frames,
                smoothed_frame_count=0,
                interpolated_frame_count=0,
                rejected_outlier_count=0,
            ),
            debug_diagnostics=PoseDebugDiagnostics(
                running_mode="video",
                processing_mode=self.processing_mode,  # type: ignore[arg-type]
                requested_num_poses=1,
                player_selection_strategy="fake_candidate_selection",
                selected_candidate_indexes=(0,),
                mean_stabilization_delta_ratio=0.0,
                max_stabilization_delta_ratio=0.0,
                stabilization_changed_keypoint_count=0,
            ),
        )


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
            frame = np.full((24, 32, 3), index * 20, dtype=np.uint8)
            writer.write(frame)
    finally:
        writer.release()

    return path
