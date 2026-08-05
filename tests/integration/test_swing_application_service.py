from pathlib import Path

import cv2
import numpy as np
import pytest

from baseball_motion_analysis.app import AnalyzeSwingRequest, SwingAnalysisApplicationService
from baseball_motion_analysis.app.media_services import (
    ImportVideoRequest,
    VideoLibraryApplicationService,
)
from baseball_motion_analysis.app.swing_services import (
    AnalyzeSwingVideoRequest,
    SwingVideoAnalysisApplicationService,
    SwingVideoAnalysisError,
)
from baseball_motion_analysis.motion import SwingHandedness
from baseball_motion_analysis.pose import (
    PoseDebugDiagnostics,
    PoseEstimationResult,
    PoseFrame,
    PoseKeypointName,
    pose_quality_diagnostics,
)
from baseball_motion_analysis.storage import LocalMediaFileStore, SqliteMediaRepository
from baseball_motion_analysis.video import FrameData
from unit.swing_test_helpers import GOOD_PHASES, good_swing_frames


def test_swing_analysis_application_service_returns_analysis_and_feedback() -> None:
    service = SwingAnalysisApplicationService()

    response = service.analyze_pose_sequence(
        AnalyzeSwingRequest(
            frames=good_swing_frames(),
            handedness=SwingHandedness.RIGHT_HANDED,
            phase_frames=GOOD_PHASES,
        )
    )

    assert response.analysis.overall_score > 90.0
    assert response.feedback.summary
    assert response.feedback.good_points
    assert response.feedback.confidence == response.analysis.confidence


def test_swing_video_analysis_application_service_estimates_pose_and_reuses_cache(
    tmp_path: Path,
) -> None:
    library_service = _video_library_service(tmp_path)
    video_path = _create_tiny_video(tmp_path / "service-swing.avi", frame_count=7, fps=10.0)
    staging_path = library_service.create_staging_file(".avi")
    staging_path.write_bytes(video_path.read_bytes())
    record = library_service.import_video(
        ImportVideoRequest(
            staging_path=staging_path,
            display_name="service-swing.avi",
            file_size_bytes=staging_path.stat().st_size,
        )
    )
    pose_estimator = RecordingBodyPoseEstimator()
    service = SwingVideoAnalysisApplicationService(
        video_library_service=library_service,
        pose_estimator=pose_estimator,
    )

    first_response = service.analyze_video(
        AnalyzeSwingVideoRequest(
            media_id=record.media_id,
            handedness=SwingHandedness.RIGHT_HANDED,
        )
    )
    second_response = service.analyze_video(
        AnalyzeSwingVideoRequest(
            media_id=record.media_id,
            handedness=SwingHandedness.RIGHT_HANDED,
        )
    )

    assert first_response.analysis.overall_score >= 0.0
    assert len(first_response.pose_frames) == 7
    assert len(first_response.events) == 5
    assert first_response.overlay_frames
    assert first_response.raw_overlay_frames
    assert all(frame.source == "stabilized" for frame in first_response.overlay_frames)
    assert all(frame.source == "raw" for frame in first_response.raw_overlay_frames)
    assert first_response.pose_cache_hit is False
    assert first_response.pose_diagnostics is not None
    assert first_response.raw_pose_diagnostics is not None
    assert first_response.pose_debug_diagnostics is not None
    assert first_response.pose_diagnostics.detected_pose_frame_ratio == 1.0
    assert first_response.pose_debug_diagnostics.selected_candidate_indexes == (0,)
    assert first_response.sampling_diagnostics.quality_mode == "higher_accuracy"
    assert first_response.sampling_diagnostics.full_frame_sampling is True
    assert first_response.sampling_diagnostics.sampled_frame_count == 7
    assert all(event.detection_method for event in first_response.events)
    assert second_response.pose_cache_hit is True
    assert pose_estimator.calls == 1
    assert all(
        PoseKeypointName.BAT_TIP not in frame.keypoints for frame in first_response.pose_frames
    )


def test_swing_video_analysis_default_estimator_requires_mediapipe_model_path(
    tmp_path: Path,
) -> None:
    library_service = _video_library_service(tmp_path)
    video_path = _create_tiny_video(tmp_path / "service-swing-default.avi", frame_count=3, fps=10.0)
    staging_path = library_service.create_staging_file(".avi")
    staging_path.write_bytes(video_path.read_bytes())
    record = library_service.import_video(
        ImportVideoRequest(
            staging_path=staging_path,
            display_name="service-swing-default.avi",
            file_size_bytes=staging_path.stat().st_size,
        )
    )
    service = SwingVideoAnalysisApplicationService(video_library_service=library_service)

    with pytest.raises(SwingVideoAnalysisError) as exc_info:
        service.analyze_video(AnalyzeSwingVideoRequest(media_id=record.media_id))

    assert exc_info.value.error_code == "missing_mediapipe_pose_model"


class RecordingBodyPoseEstimator:
    def __init__(self) -> None:
        self.calls = 0

    def estimate(self, frames: tuple[FrameData, ...]) -> PoseEstimationResult:
        self.calls += 1
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
                processing_mode="normal",
                requested_num_poses=1,
                player_selection_strategy="fake_candidate_selection",
                selected_candidate_indexes=(0,),
                mean_stabilization_delta_ratio=0.0,
                max_stabilization_delta_ratio=0.0,
                stabilization_changed_keypoint_count=0,
            ),
        )


def _video_library_service(tmp_path: Path) -> VideoLibraryApplicationService:
    return VideoLibraryApplicationService(
        repository=SqliteMediaRepository(tmp_path / "library.sqlite3"),
        file_store=LocalMediaFileStore(tmp_path / "media"),
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
