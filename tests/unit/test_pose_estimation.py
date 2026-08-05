import numpy as np

from baseball_motion_analysis.pose import (
    HeuristicPoseEstimator,
    MediaPipePoseEstimator,
    MediaPipePoseEstimatorConfig,
    PoseKeypointName,
    estimate_pose_frame_with_mediapipe_image_mode,
    pose_frame_from_mediapipe_image_result,
    pose_frame_from_mediapipe_result,
    select_best_pose_landmarks,
    select_best_pose_landmarks_with_diagnostics,
    stabilize_pose_frames,
)
from baseball_motion_analysis.pose.models import Point2D, PoseFrame, PoseKeypoint
from baseball_motion_analysis.video import FrameData, MediaSourceType


def test_heuristic_pose_estimator_returns_pose_for_every_sampled_frame() -> None:
    frames = tuple(_frame(index) for index in range(4))
    estimator = HeuristicPoseEstimator()

    result = estimator.estimate(frames)

    assert [frame.frame_index for frame in result.frames] == [0, 1, 2, 3]
    assert result.limitations
    assert all(PoseKeypointName.NOSE in frame.keypoints for frame in result.frames)
    assert all(PoseKeypointName.BAT_TIP in frame.keypoints for frame in result.frames)
    assert result.frames[-1].keypoints[PoseKeypointName.BAT_TIP].confidence < 1.0


def test_heuristic_pose_estimator_reports_empty_input_limitation() -> None:
    result = HeuristicPoseEstimator().estimate(())

    assert result.frames == ()
    assert result.limitations == ("No sampled video frames were available for pose estimation.",)


def test_mediapipe_result_mapping_returns_internal_pose_frame() -> None:
    result = FakeMediaPipeResult(
        [_landmarks(confidence=0.8)],
    )

    frame, limitations, detected = pose_frame_from_mediapipe_result(
        result,
        frame_index=12,
        timestamp_seconds=0.4,
    )

    assert detected is True
    assert limitations == ()
    assert frame.frame_index == 12
    assert frame.timestamp_seconds == 0.4
    assert frame.keypoints[PoseKeypointName.NOSE].point.x == 0.5
    assert frame.keypoints[PoseKeypointName.LEFT_SHOULDER].confidence == 0.8
    assert PoseKeypointName.BAT_TIP not in frame.keypoints
    assert PoseKeypointName.LEFT_FOOT_INDEX in frame.keypoints


def test_mediapipe_default_and_notebook_parity_configs_are_single_pose_raw_modes() -> None:
    default_config = MediaPipePoseEstimatorConfig()
    parity_config = MediaPipePoseEstimatorConfig.notebook_parity(
        MediaPipePoseEstimatorConfig(num_poses=3)
    )

    assert default_config.num_poses == 1
    assert parity_config.num_poses == 1
    assert parity_config.processing_mode == "notebook_parity"
    assert parity_config.smoothing_window == 1
    assert parity_config.max_interpolation_gap_frames == 0
    assert parity_config.outlier_rejection_enabled is False


def test_mediapipe_image_mode_and_video_mode_mapping_match_with_fake_result() -> None:
    result = FakeMediaPipeResult([_landmarks(confidence=0.8)])

    video_frame, video_limitations, video_detected = pose_frame_from_mediapipe_result(
        result,
        frame_index=4,
        timestamp_seconds=0.2,
    )
    image_frame, image_limitations, image_detected = pose_frame_from_mediapipe_image_result(
        result,
        frame_index=4,
        timestamp_seconds=0.2,
    )

    assert image_detected is video_detected is True
    assert image_limitations == video_limitations
    assert image_frame == video_frame


def test_mediapipe_result_mapping_preserves_out_of_frame_landmarks_without_clamping() -> None:
    landmarks = _landmarks(confidence=0.9)
    landmarks[0] = FakeLandmark(1.2, -0.1, visibility=0.9, presence=0.9)
    result = FakeMediaPipeResult([landmarks])

    frame, limitations, detected = pose_frame_from_mediapipe_result(
        result,
        frame_index=6,
        timestamp_seconds=0.2,
    )

    nose = frame.keypoints[PoseKeypointName.NOSE]
    assert detected is True
    assert nose.point.x == 1.2
    assert nose.point.y == -0.1
    assert nose.out_of_frame is True
    assert any("outside the visible frame" in limitation for limitation in limitations)


def test_mediapipe_result_mapping_reports_missing_and_low_confidence_landmarks() -> None:
    landmarks = _landmarks(confidence=0.9)
    landmarks[11] = FakeLandmark(0.4, 0.4, visibility=0.1, presence=0.1)
    result = FakeMediaPipeResult([landmarks])

    frame, limitations, detected = pose_frame_from_mediapipe_result(
        result,
        frame_index=3,
        timestamp_seconds=0.1,
        min_landmark_confidence=0.3,
    )

    assert detected is True
    assert PoseKeypointName.LEFT_SHOULDER not in frame.keypoints
    assert any("missing required body landmarks" in limitation for limitation in limitations)
    assert any("low-confidence MediaPipe landmarks" in limitation for limitation in limitations)


def test_best_pose_selection_prefers_track_continuity_over_background_pose() -> None:
    previous = PoseFrame(
        frame_index=0,
        timestamp_seconds=0.0,
        keypoints={
            PoseKeypointName.NOSE: PoseKeypoint(Point2D(0.5, 0.2), confidence=0.9),
            PoseKeypointName.LEFT_SHOULDER: PoseKeypoint(Point2D(0.4, 0.4), confidence=0.9),
            PoseKeypointName.RIGHT_SHOULDER: PoseKeypoint(Point2D(0.6, 0.4), confidence=0.9),
        },
    )
    background = _landmarks(confidence=0.99)
    for landmark in background:
        landmark.x += 0.35
    tracked_player = _landmarks(confidence=0.7)

    selected = select_best_pose_landmarks(
        [background, tracked_player],
        previous_frame=previous,
        config=MediaPipePoseEstimatorConfig(),
    )

    assert selected is tracked_player


def test_first_frame_pose_selection_prefers_centered_plausible_player_over_edge_clutter() -> None:
    clutter = _landmarks(confidence=0.99)
    for landmark in clutter:
        landmark.x -= 0.45
    tracked_player = _landmarks(confidence=0.7)

    selection = select_best_pose_landmarks_with_diagnostics(
        [clutter, tracked_player],
        config=MediaPipePoseEstimatorConfig(),
    )

    assert selection.index == 1
    assert selection.landmarks is tracked_player


def test_stabilize_pose_frames_rejects_outlier_interpolates_gap_and_reports_diagnostics() -> None:
    frames = (
        _pose_frame_with_left_wrist(0, 0.4),
        _pose_frame_with_left_wrist(1, 8.0),
        _pose_frame_with_left_wrist(2, 0.5),
    )

    stabilized, limitations, diagnostics = stabilize_pose_frames(
        frames,
        MediaPipePoseEstimatorConfig(
            smoothing_window=1,
            max_interpolation_gap_frames=1,
            outlier_distance_ratio=0.5,
        ),
    )

    assert diagnostics.rejected_outlier_count == 1
    assert diagnostics.interpolated_frame_count == 1
    assert stabilized[1].keypoints[PoseKeypointName.LEFT_WRIST].interpolated is True
    assert stabilized[1].keypoints[PoseKeypointName.LEFT_WRIST].confidence < 0.9
    assert any("interpolated" in limitation for limitation in limitations)


def test_smoothing_does_not_over_smooth_high_velocity_wrist_motion() -> None:
    frames = (
        _pose_frame_with_left_wrist(0, 0.4),
        _pose_frame_with_left_wrist(1, 0.8),
        _pose_frame_with_left_wrist(2, 1.2),
    )

    stabilized, _limitations, diagnostics = stabilize_pose_frames(
        frames,
        MediaPipePoseEstimatorConfig(
            smoothing_window=3,
            max_interpolation_gap_frames=0,
            outlier_rejection_enabled=False,
            high_velocity_smoothing_limit_ratio=0.5,
        ),
    )

    middle_wrist = stabilized[1].keypoints[PoseKeypointName.LEFT_WRIST]
    assert middle_wrist.point.x == 0.8
    assert middle_wrist.smoothed is False
    assert diagnostics.interpolated_frame_count == 0


def test_mediapipe_pose_estimator_tracks_each_sampled_frame_with_injected_landmarker() -> None:
    frames = tuple(_frame(index) for index in range(3))
    landmarker = FakeLandmarker()
    estimator = MediaPipePoseEstimator(
        landmarker_factory=lambda: landmarker,
        image_factory=lambda frame: frame.image,
    )

    result = estimator.estimate(frames)

    assert [frame.frame_index for frame in result.frames] == [0, 1, 2]
    assert landmarker.timestamps == [0, 100, 200]
    assert PoseKeypointName.BAT_TIP not in result.frames[0].keypoints
    assert any("bat tip" in limitation for limitation in result.limitations)
    assert any("3 of 3 sampled frame" in limitation for limitation in result.limitations)
    assert result.diagnostics is not None
    assert result.diagnostics.detected_pose_frame_ratio == 1.0
    assert result.raw_frames
    assert result.raw_diagnostics is not None
    assert result.debug_diagnostics is not None
    assert result.debug_diagnostics.requested_num_poses == 1
    assert result.debug_diagnostics.selected_candidate_indexes == (0, 0, 0)


def test_mediapipe_image_mode_diagnostic_uses_fake_landmarker() -> None:
    landmarker = FakeImageLandmarker()

    result = estimate_pose_frame_with_mediapipe_image_mode(
        _frame(5),
        landmarker_factory=lambda: landmarker,
        image_factory=lambda frame: frame.image,
    )

    assert [frame.frame_index for frame in result.frames] == [5]
    assert landmarker.detect_calls == 1
    assert landmarker.closed is True
    assert result.debug_diagnostics is not None
    assert result.debug_diagnostics.running_mode == "image"
    assert result.debug_diagnostics.processing_mode == "notebook_parity"
    assert result.debug_diagnostics.selected_candidate_indexes == (0,)


def test_mediapipe_pose_estimator_reports_no_detected_player() -> None:
    estimator = MediaPipePoseEstimator(
        landmarker_factory=lambda: FakeLandmarker(detect_pose=False),
        image_factory=lambda frame: frame.image,
    )

    try:
        estimator.estimate((_frame(0),))
    except Exception as exc:
        assert getattr(exc, "error_code", "") == "no_detectable_player_pose"
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("expected no_detectable_player_pose")


def _frame(index: int) -> FrameData:
    return FrameData(
        source_type=MediaSourceType.RECORDED_VIDEO,
        frame_index=index,
        timestamp_seconds=index / 10,
        width=32,
        height=24,
        image=np.zeros((24, 32, 3), dtype=np.uint8),
    )


class FakeLandmark:
    def __init__(
        self,
        x: float,
        y: float,
        *,
        visibility: float = 0.9,
        presence: float = 0.9,
    ) -> None:
        self.x = x
        self.y = y
        self.visibility = visibility
        self.presence = presence


class FakeMediaPipeResult:
    def __init__(self, pose_landmarks: list[list[FakeLandmark]]) -> None:
        self.pose_landmarks = pose_landmarks


class FakeLandmarker:
    def __init__(self, *, detect_pose: bool = True) -> None:
        self.detect_pose = detect_pose
        self.timestamps: list[int] = []
        self.closed = False

    def detect_for_video(self, image: object, timestamp_ms: int) -> FakeMediaPipeResult:
        self.timestamps.append(timestamp_ms)
        if not self.detect_pose:
            return FakeMediaPipeResult([])
        return FakeMediaPipeResult([_landmarks(confidence=0.8)])

    def close(self) -> None:
        self.closed = True


class FakeImageLandmarker:
    def __init__(self) -> None:
        self.detect_calls = 0
        self.closed = False

    def detect(self, image: object) -> FakeMediaPipeResult:
        self.detect_calls += 1
        return FakeMediaPipeResult([_landmarks(confidence=0.8)])

    def close(self) -> None:
        self.closed = True


def _landmarks(*, confidence: float) -> list[FakeLandmark]:
    landmarks = [
        FakeLandmark(0.5, 0.5, visibility=confidence, presence=confidence) for _ in range(33)
    ]
    landmarks[0] = FakeLandmark(0.5, 0.2, visibility=confidence, presence=confidence)
    landmarks[11] = FakeLandmark(0.4, 0.35, visibility=confidence, presence=confidence)
    landmarks[12] = FakeLandmark(0.6, 0.35, visibility=confidence, presence=confidence)
    landmarks[13] = FakeLandmark(0.35, 0.5, visibility=confidence, presence=confidence)
    landmarks[14] = FakeLandmark(0.65, 0.5, visibility=confidence, presence=confidence)
    landmarks[15] = FakeLandmark(0.32, 0.65, visibility=confidence, presence=confidence)
    landmarks[16] = FakeLandmark(0.68, 0.65, visibility=confidence, presence=confidence)
    landmarks[23] = FakeLandmark(0.43, 0.65, visibility=confidence, presence=confidence)
    landmarks[24] = FakeLandmark(0.57, 0.65, visibility=confidence, presence=confidence)
    landmarks[25] = FakeLandmark(0.42, 0.82, visibility=confidence, presence=confidence)
    landmarks[26] = FakeLandmark(0.58, 0.82, visibility=confidence, presence=confidence)
    landmarks[27] = FakeLandmark(0.41, 0.96, visibility=confidence, presence=confidence)
    landmarks[28] = FakeLandmark(0.59, 0.96, visibility=confidence, presence=confidence)
    landmarks[29] = FakeLandmark(0.39, 0.98, visibility=confidence, presence=confidence)
    landmarks[30] = FakeLandmark(0.61, 0.98, visibility=confidence, presence=confidence)
    landmarks[31] = FakeLandmark(0.36, 0.99, visibility=confidence, presence=confidence)
    landmarks[32] = FakeLandmark(0.64, 0.99, visibility=confidence, presence=confidence)
    return landmarks


def _pose_frame_with_left_wrist(frame_index: int, wrist_x: float) -> PoseFrame:
    base = {
        PoseKeypointName.NOSE: PoseKeypoint(Point2D(0.5, 0.2), confidence=0.9),
        PoseKeypointName.LEFT_SHOULDER: PoseKeypoint(Point2D(0.4, 0.35), confidence=0.9),
        PoseKeypointName.RIGHT_SHOULDER: PoseKeypoint(Point2D(0.6, 0.35), confidence=0.9),
        PoseKeypointName.LEFT_ELBOW: PoseKeypoint(Point2D(0.35, 0.5), confidence=0.9),
        PoseKeypointName.RIGHT_ELBOW: PoseKeypoint(Point2D(0.65, 0.5), confidence=0.9),
        PoseKeypointName.LEFT_WRIST: PoseKeypoint(Point2D(wrist_x, 0.65), confidence=0.9),
        PoseKeypointName.RIGHT_WRIST: PoseKeypoint(Point2D(0.68, 0.65), confidence=0.9),
        PoseKeypointName.LEFT_HIP: PoseKeypoint(Point2D(0.43, 0.65), confidence=0.9),
        PoseKeypointName.RIGHT_HIP: PoseKeypoint(Point2D(0.57, 0.65), confidence=0.9),
        PoseKeypointName.LEFT_KNEE: PoseKeypoint(Point2D(0.42, 0.82), confidence=0.9),
        PoseKeypointName.RIGHT_KNEE: PoseKeypoint(Point2D(0.58, 0.82), confidence=0.9),
        PoseKeypointName.LEFT_ANKLE: PoseKeypoint(Point2D(0.41, 0.96), confidence=0.9),
        PoseKeypointName.RIGHT_ANKLE: PoseKeypoint(Point2D(0.59, 0.96), confidence=0.9),
    }
    return PoseFrame(
        frame_index=frame_index,
        timestamp_seconds=frame_index / 30.0,
        keypoints=base,
    )
