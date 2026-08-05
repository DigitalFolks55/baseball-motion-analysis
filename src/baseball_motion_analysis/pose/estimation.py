"""Pose estimation interfaces and local implementations."""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, replace
from importlib import import_module
from pathlib import Path
from typing import Any, Literal, Protocol, cast

import cv2
import numpy as np

from baseball_motion_analysis.pose.models import Point2D, PoseFrame, PoseKeypoint, PoseKeypointName
from baseball_motion_analysis.video import FrameData

_REQUIRED_MEDIAPIPE_LANDMARKS = (
    PoseKeypointName.NOSE,
    PoseKeypointName.LEFT_SHOULDER,
    PoseKeypointName.RIGHT_SHOULDER,
    PoseKeypointName.LEFT_ELBOW,
    PoseKeypointName.RIGHT_ELBOW,
    PoseKeypointName.LEFT_WRIST,
    PoseKeypointName.RIGHT_WRIST,
    PoseKeypointName.LEFT_HIP,
    PoseKeypointName.RIGHT_HIP,
    PoseKeypointName.LEFT_KNEE,
    PoseKeypointName.RIGHT_KNEE,
    PoseKeypointName.LEFT_ANKLE,
    PoseKeypointName.RIGHT_ANKLE,
)

_MEDIAPIPE_LANDMARK_INDEXES = {
    PoseKeypointName.NOSE: 0,
    PoseKeypointName.LEFT_EAR: 7,
    PoseKeypointName.RIGHT_EAR: 8,
    PoseKeypointName.LEFT_SHOULDER: 11,
    PoseKeypointName.RIGHT_SHOULDER: 12,
    PoseKeypointName.LEFT_ELBOW: 13,
    PoseKeypointName.RIGHT_ELBOW: 14,
    PoseKeypointName.LEFT_WRIST: 15,
    PoseKeypointName.RIGHT_WRIST: 16,
    PoseKeypointName.LEFT_HIP: 23,
    PoseKeypointName.RIGHT_HIP: 24,
    PoseKeypointName.LEFT_KNEE: 25,
    PoseKeypointName.RIGHT_KNEE: 26,
    PoseKeypointName.LEFT_ANKLE: 27,
    PoseKeypointName.RIGHT_ANKLE: 28,
    PoseKeypointName.LEFT_HEEL: 29,
    PoseKeypointName.RIGHT_HEEL: 30,
    PoseKeypointName.LEFT_FOOT_INDEX: 31,
    PoseKeypointName.RIGHT_FOOT_INDEX: 32,
}


@dataclass(frozen=True)
class MediaPipePoseEstimatorConfig:
    """Tuning values for local MediaPipe pose estimation and stabilization."""

    num_poses: int = 1
    min_pose_detection_confidence: float = 0.5
    min_pose_presence_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    min_landmark_confidence: float = 0.3
    smoothing_window: int = 3
    max_interpolation_gap_frames: int = 2
    outlier_rejection_enabled: bool = True
    outlier_distance_ratio: float = 0.75
    high_velocity_smoothing_limit_ratio: float = 0.8
    stabilization_delta_warning_ratio: float = 0.35
    player_selection_strategy: Literal[
        "continuity_confidence_size",
        "confidence_size",
    ] = "continuity_confidence_size"
    processing_mode: Literal["normal", "notebook_parity"] = "normal"
    enable_segmentation_mask: bool = False
    runtime_delegate: Literal["cpu", "gpu"] = "cpu"

    def __post_init__(self) -> None:
        if self.num_poses < 1:
            msg = "num_poses must be greater than or equal to 1"
            raise ValueError(msg)
        for name in (
            "min_pose_detection_confidence",
            "min_pose_presence_confidence",
            "min_tracking_confidence",
            "min_landmark_confidence",
        ):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                msg = f"{name} must be between 0 and 1"
                raise ValueError(msg)
        if self.smoothing_window < 1:
            msg = "smoothing_window must be greater than or equal to 1"
            raise ValueError(msg)
        if self.max_interpolation_gap_frames < 0:
            msg = "max_interpolation_gap_frames must be greater than or equal to 0"
            raise ValueError(msg)
        if self.outlier_distance_ratio <= 0:
            msg = "outlier_distance_ratio must be greater than 0"
            raise ValueError(msg)
        if self.high_velocity_smoothing_limit_ratio <= 0:
            msg = "high_velocity_smoothing_limit_ratio must be greater than 0"
            raise ValueError(msg)
        if self.stabilization_delta_warning_ratio <= 0:
            msg = "stabilization_delta_warning_ratio must be greater than 0"
            raise ValueError(msg)

    @classmethod
    def notebook_parity(
        cls, base: MediaPipePoseEstimatorConfig | None = None
    ) -> MediaPipePoseEstimatorConfig:
        """Return a MediaPipe config that mirrors raw notebook-style single-frame output."""
        config = base or cls()
        return replace(
            config,
            num_poses=1,
            smoothing_window=1,
            max_interpolation_gap_frames=0,
            outlier_rejection_enabled=False,
            player_selection_strategy="confidence_size",
            processing_mode="notebook_parity",
        )


@dataclass(frozen=True)
class PoseQualityDiagnostics:
    """Aggregated quality signals for one pose-estimation run."""

    total_frame_count: int
    detected_pose_frame_count: int
    detected_pose_frame_ratio: float
    required_landmark_coverage: float
    mean_confidence: float | None
    min_confidence: float | None
    smoothed_frame_count: int
    interpolated_frame_count: int
    rejected_outlier_count: int
    out_of_frame_landmark_count: int


@dataclass(frozen=True)
class PoseDebugDiagnostics:
    """Debug signals that explain how raw detections became analysis poses."""

    running_mode: Literal["video", "image"]
    processing_mode: Literal["normal", "notebook_parity"]
    requested_num_poses: int
    player_selection_strategy: str
    selected_candidate_indexes: tuple[int, ...]
    mean_stabilization_delta_ratio: float | None = None
    max_stabilization_delta_ratio: float | None = None
    stabilization_changed_keypoint_count: int = 0


@dataclass(frozen=True)
class PoseEstimationResult:
    """Pose estimation output for sampled frames."""

    frames: tuple[PoseFrame, ...]
    limitations: tuple[str, ...] = ()
    diagnostics: PoseQualityDiagnostics | None = None
    raw_frames: tuple[PoseFrame, ...] = ()
    raw_diagnostics: PoseQualityDiagnostics | None = None
    debug_diagnostics: PoseDebugDiagnostics | None = None


class PoseEstimator(Protocol):
    """Interface for converting decoded frames into pose observations."""

    def estimate(self, frames: Sequence[FrameData]) -> PoseEstimationResult:
        """Estimate pose for decoded video frames."""


class PoseEstimationError(Exception):
    """Base class for pose-estimation failures."""

    error_code = "pose_estimation_error"
    user_message = "Pose estimation failed."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.user_message)
        self.message = message or self.user_message


class MediaPipeDependencyMissingError(PoseEstimationError):
    """Raised when MediaPipe is required but unavailable."""

    error_code = "missing_mediapipe_dependency"
    user_message = "MediaPipe is not installed in the current environment."


class MediaPipePoseModelMissingError(PoseEstimationError):
    """Raised when the MediaPipe pose model asset is not configured or missing."""

    error_code = "missing_mediapipe_pose_model"
    user_message = (
        "MediaPipe pose analysis requires BMA_MEDIAPIPE_POSE_MODEL_PATH to point to a "
        "local Pose Landmarker .task model."
    )


class MediaPipePoseTrackingError(PoseEstimationError):
    """Raised when MediaPipe pose tracking fails at runtime."""

    error_code = "mediapipe_pose_tracking_failed"
    user_message = "MediaPipe pose tracking failed for the selected video."


class NoDetectedPlayerPoseError(PoseEstimationError):
    """Raised when no player body pose is detected in sampled frames."""

    error_code = "no_detectable_player_pose"
    user_message = "MediaPipe did not detect a usable player body pose in the selected video."


class MediaPipePoseEstimator:
    """Pose estimator backed by MediaPipe Pose Landmarker video-mode tracking."""

    def __init__(
        self,
        *,
        model_path: Path | str | None = None,
        config: MediaPipePoseEstimatorConfig | None = None,
        min_landmark_confidence: float | None = None,
        landmarker_factory: Any | None = None,
        image_factory: Callable[[FrameData], Any] | None = None,
    ) -> None:
        resolved_config = config or MediaPipePoseEstimatorConfig()
        if min_landmark_confidence is not None:
            resolved_config = replace(
                resolved_config,
                min_landmark_confidence=min_landmark_confidence,
            )
        self._model_path = Path(model_path).expanduser() if model_path is not None else None
        self._config = resolved_config
        self._landmarker_factory = landmarker_factory
        self._image_factory = image_factory or _mediapipe_image_from_frame

    def estimate(self, frames: Sequence[FrameData]) -> PoseEstimationResult:
        """Return MediaPipe-derived pose observations for every sampled frame."""
        if not frames:
            return PoseEstimationResult(
                frames=(),
                limitations=("No sampled video frames were available for pose estimation.",),
            )

        landmarker = self._create_landmarker()
        raw_pose_frames: list[PoseFrame] = []
        limitations: list[str] = [
            "MediaPipe Pose tracks player body landmarks only; bat tip, bat barrel, and "
            "ball position are not detected."
        ]
        detected_frame_count = 0
        previous_timestamp_ms = -1
        previous_pose_frame: PoseFrame | None = None
        selected_candidate_indexes: list[int] = []

        try:
            for sequence_index, frame in enumerate(frames):
                timestamp_ms = _monotonic_timestamp_ms(frame, sequence_index, previous_timestamp_ms)
                previous_timestamp_ms = timestamp_ms
                result = landmarker.detect_for_video(
                    self._image_factory(frame),
                    timestamp_ms,
                )
                pose_frame, frame_limitations, detected, selection = (
                    _pose_frame_from_mediapipe_result_with_selection(
                        result,
                        frame_index=frame.frame_index,
                        timestamp_seconds=frame.timestamp_seconds,
                        min_landmark_confidence=self._config.min_landmark_confidence,
                        previous_frame=previous_pose_frame,
                        config=self._config,
                    )
                )
                if selection.index >= 0:
                    selected_candidate_indexes.append(selection.index)
                raw_pose_frames.append(pose_frame)
                limitations.extend(frame_limitations)
                if detected:
                    detected_frame_count += 1
                    previous_pose_frame = pose_frame
        except PoseEstimationError:
            raise
        except Exception as exc:
            raise MediaPipePoseTrackingError() from exc
        finally:
            close = getattr(landmarker, "close", None)
            if callable(close):
                close()

        if detected_frame_count == 0:
            raise NoDetectedPlayerPoseError()

        pose_frames, postprocess_limitations, diagnostics = stabilize_pose_frames(
            raw_pose_frames,
            self._config,
        )
        raw_diagnostics = pose_quality_diagnostics(
            raw_pose_frames,
            smoothed_frame_count=0,
            interpolated_frame_count=0,
            rejected_outlier_count=0,
        )
        stabilization_debug = stabilization_delta_diagnostics(raw_pose_frames, pose_frames)
        debug_diagnostics = PoseDebugDiagnostics(
            running_mode="video",
            processing_mode=self._config.processing_mode,
            requested_num_poses=self._config.num_poses,
            player_selection_strategy=self._config.player_selection_strategy,
            selected_candidate_indexes=tuple(selected_candidate_indexes),
            mean_stabilization_delta_ratio=stabilization_debug.mean_delta_ratio,
            max_stabilization_delta_ratio=stabilization_debug.max_delta_ratio,
            stabilization_changed_keypoint_count=stabilization_debug.changed_keypoint_count,
        )
        limitations.extend(postprocess_limitations)
        if (
            stabilization_debug.max_delta_ratio is not None
            and stabilization_debug.max_delta_ratio > self._config.stabilization_delta_warning_ratio
        ):
            limitations.append(
                "Pose stabilization changed at least one landmark by a large body-scale "
                "relative distance; compare the raw overlay in debug mode."
            )
        if self._config.processing_mode == "notebook_parity":
            limitations.append(
                "Notebook-parity pose mode returns raw single-pose MediaPipe landmarks "
                "without temporal stabilization; use it for diagnostics, not final "
                "coached evaluation."
            )
        limitations.append(
            f"MediaPipe detected a usable body pose in {detected_frame_count} of "
            f"{len(frames)} sampled frame(s)."
        )
        return PoseEstimationResult(
            frames=tuple(pose_frames),
            limitations=tuple(dict.fromkeys(limitations)),
            diagnostics=diagnostics,
            raw_frames=tuple(raw_pose_frames),
            raw_diagnostics=raw_diagnostics,
            debug_diagnostics=debug_diagnostics,
        )

    def _create_landmarker(self) -> Any:
        if self._landmarker_factory is not None:
            return self._landmarker_factory()

        model_path = self._model_path
        if model_path is None or not model_path.exists():
            raise MediaPipePoseModelMissingError()

        try:
            mediapipe = import_module("mediapipe")
        except ImportError as exc:
            raise MediaPipeDependencyMissingError() from exc

        try:
            options = mediapipe.tasks.vision.PoseLandmarkerOptions(
                base_options=_mediapipe_base_options(
                    mediapipe,
                    model_path=model_path,
                    runtime_delegate=self._config.runtime_delegate,
                ),
                running_mode=mediapipe.tasks.vision.RunningMode.VIDEO,
                num_poses=self._config.num_poses,
                min_pose_detection_confidence=self._config.min_pose_detection_confidence,
                min_pose_presence_confidence=self._config.min_pose_presence_confidence,
                min_tracking_confidence=self._config.min_tracking_confidence,
                output_segmentation_masks=self._config.enable_segmentation_mask,
            )
            return mediapipe.tasks.vision.PoseLandmarker.create_from_options(options)
        except Exception as exc:
            raise MediaPipePoseModelMissingError() from exc


def estimate_pose_frame_with_mediapipe_image_mode(
    frame: FrameData,
    *,
    model_path: Path | str | None = None,
    config: MediaPipePoseEstimatorConfig | None = None,
    landmarker_factory: Any | None = None,
    image_factory: Callable[[FrameData], Any] | None = None,
) -> PoseEstimationResult:
    """Run MediaPipe image mode on one decoded frame for notebook-parity diagnostics."""
    parity_config = MediaPipePoseEstimatorConfig.notebook_parity(config)
    landmarker = (
        landmarker_factory()
        if landmarker_factory is not None
        else _create_image_landmarker(
            model_path=model_path,
            config=parity_config,
        )
    )
    resolved_image_factory = image_factory or _mediapipe_image_from_frame
    try:
        result = landmarker.detect(resolved_image_factory(frame))
        pose_frame, limitations, detected, selection = (
            _pose_frame_from_mediapipe_result_with_selection(
                result,
                frame_index=frame.frame_index,
                timestamp_seconds=frame.timestamp_seconds,
                min_landmark_confidence=parity_config.min_landmark_confidence,
                previous_frame=None,
                config=parity_config,
            )
        )
    except PoseEstimationError:
        raise
    except Exception as exc:
        raise MediaPipePoseTrackingError() from exc
    finally:
        close = getattr(landmarker, "close", None)
        if callable(close):
            close()

    if not detected:
        raise NoDetectedPlayerPoseError()

    diagnostics = pose_quality_diagnostics(
        (pose_frame,),
        smoothed_frame_count=0,
        interpolated_frame_count=0,
        rejected_outlier_count=0,
    )
    return PoseEstimationResult(
        frames=(pose_frame,),
        limitations=(
            *limitations,
            "MediaPipe image-mode notebook-parity diagnostics ran on one decoded frame.",
        ),
        diagnostics=diagnostics,
        raw_frames=(pose_frame,),
        raw_diagnostics=diagnostics,
        debug_diagnostics=PoseDebugDiagnostics(
            running_mode="image",
            processing_mode="notebook_parity",
            requested_num_poses=parity_config.num_poses,
            player_selection_strategy=parity_config.player_selection_strategy,
            selected_candidate_indexes=(selection.index,) if selection.index >= 0 else (),
            mean_stabilization_delta_ratio=None,
            max_stabilization_delta_ratio=None,
            stabilization_changed_keypoint_count=0,
        ),
    )


def _create_image_landmarker(
    *,
    model_path: Path | str | None,
    config: MediaPipePoseEstimatorConfig,
) -> Any:
    resolved_model_path = Path(model_path).expanduser() if model_path is not None else None
    if resolved_model_path is None or not resolved_model_path.exists():
        raise MediaPipePoseModelMissingError()

    try:
        mediapipe = import_module("mediapipe")
    except ImportError as exc:
        raise MediaPipeDependencyMissingError() from exc

    try:
        options = mediapipe.tasks.vision.PoseLandmarkerOptions(
            base_options=_mediapipe_base_options(
                mediapipe,
                model_path=resolved_model_path,
                runtime_delegate=config.runtime_delegate,
            ),
            running_mode=mediapipe.tasks.vision.RunningMode.IMAGE,
            num_poses=config.num_poses,
            min_pose_detection_confidence=config.min_pose_detection_confidence,
            min_pose_presence_confidence=config.min_pose_presence_confidence,
            min_tracking_confidence=config.min_tracking_confidence,
            output_segmentation_masks=config.enable_segmentation_mask,
        )
        return mediapipe.tasks.vision.PoseLandmarker.create_from_options(options)
    except Exception as exc:
        raise MediaPipePoseModelMissingError() from exc


class HeuristicPoseEstimator:
    """Deterministic local pose estimator for tests and explicit fallback injection."""

    limitation = (
        "Pose was estimated by a deterministic local heuristic; use a calibrated pose "
        "model for production-quality body tracking."
    )

    def estimate(self, frames: Sequence[FrameData]) -> PoseEstimationResult:
        """Return deterministic side-view pose observations for sampled frames."""
        if not frames:
            return PoseEstimationResult(
                frames=(),
                limitations=("No sampled video frames were available for pose estimation.",),
                diagnostics=PoseQualityDiagnostics(
                    total_frame_count=0,
                    detected_pose_frame_count=0,
                    detected_pose_frame_ratio=0.0,
                    required_landmark_coverage=0.0,
                    mean_confidence=None,
                    min_confidence=None,
                    smoothed_frame_count=0,
                    interpolated_frame_count=0,
                    rejected_outlier_count=0,
                    out_of_frame_landmark_count=0,
                ),
            )

        total = max(1, len(frames) - 1)
        pose_frames = tuple(
            PoseFrame(
                frame_index=frame.frame_index,
                timestamp_seconds=frame.timestamp_seconds,
                keypoints=_swing_like_keypoints(index / total),
            )
            for index, frame in enumerate(frames)
        )
        return PoseEstimationResult(
            frames=pose_frames,
            limitations=(self.limitation,),
            diagnostics=pose_quality_diagnostics(
                pose_frames,
                smoothed_frame_count=0,
                interpolated_frame_count=0,
                rejected_outlier_count=0,
            ),
        )


def _swing_like_keypoints(progress: float) -> dict[PoseKeypointName, PoseKeypoint]:
    """Create a deterministic right-handed side-view pose for one swing progress value."""
    shoulder_y = -0.08 if progress >= 0.45 else 0.0
    lead_hip_y = 0.45 if progress >= 0.25 else 0.6
    nose_x = 0.5 + max(0.0, progress - 0.75) * 0.1
    lead_wrist_x = 0.5 + max(0.0, progress - 0.45) * 1.25
    rear_wrist_x = 0.3 + max(0.0, progress - 0.45) * 1.25
    wrist_y = 0.0 + max(0.0, progress - 0.45) * 0.35
    bat_tip_x = ((lead_wrist_x + rear_wrist_x) / 2.0) + 0.85
    bat_tip_y = wrist_y - 0.17

    return {
        PoseKeypointName.NOSE: _kp(nose_x, -0.35),
        PoseKeypointName.LEFT_SHOULDER: _kp(1.0, shoulder_y),
        PoseKeypointName.RIGHT_SHOULDER: _kp(0.0, 0.0),
        PoseKeypointName.LEFT_ELBOW: _kp(0.8, 0.25),
        PoseKeypointName.RIGHT_ELBOW: _kp(0.2, 0.25),
        PoseKeypointName.LEFT_WRIST: _kp(lead_wrist_x, wrist_y),
        PoseKeypointName.RIGHT_WRIST: _kp(rear_wrist_x, wrist_y),
        PoseKeypointName.LEFT_HIP: _kp(1.0, lead_hip_y),
        PoseKeypointName.RIGHT_HIP: _kp(0.0, 0.6),
        PoseKeypointName.LEFT_KNEE: _kp(1.0, 1.2),
        PoseKeypointName.RIGHT_KNEE: _kp(0.0, 1.2),
        PoseKeypointName.LEFT_ANKLE: _kp(1.0, 2.0),
        PoseKeypointName.RIGHT_ANKLE: _kp(0.0, 2.0),
        PoseKeypointName.BAT_TIP: _kp(bat_tip_x, bat_tip_y, confidence=0.65),
    }


def _kp(x: float, y: float, *, confidence: float = 0.9) -> PoseKeypoint:
    return PoseKeypoint(point=Point2D(x=x, y=y), confidence=confidence)


def pose_frame_from_mediapipe_result(
    result: Any,
    *,
    frame_index: int,
    timestamp_seconds: float | None,
    min_landmark_confidence: float = 0.3,
    previous_frame: PoseFrame | None = None,
    config: MediaPipePoseEstimatorConfig | None = None,
) -> tuple[PoseFrame, tuple[str, ...], bool]:
    """Convert one MediaPipe result object into the internal pose-frame model."""
    frame, limitations, detected, _selection = _pose_frame_from_mediapipe_result_with_selection(
        result,
        frame_index=frame_index,
        timestamp_seconds=timestamp_seconds,
        min_landmark_confidence=min_landmark_confidence,
        previous_frame=previous_frame,
        config=config,
    )
    return frame, limitations, detected


def pose_frame_from_mediapipe_image_result(
    result: Any,
    *,
    frame_index: int,
    timestamp_seconds: float | None,
    min_landmark_confidence: float = 0.3,
    config: MediaPipePoseEstimatorConfig | None = None,
) -> tuple[PoseFrame, tuple[str, ...], bool]:
    """Convert one MediaPipe image-mode result into the internal pose-frame model."""
    return pose_frame_from_mediapipe_result(
        result,
        frame_index=frame_index,
        timestamp_seconds=timestamp_seconds,
        min_landmark_confidence=min_landmark_confidence,
        previous_frame=None,
        config=MediaPipePoseEstimatorConfig.notebook_parity(config),
    )


@dataclass(frozen=True)
class PoseCandidateSelection:
    """Selected MediaPipe candidate and its diagnostic selection score."""

    landmarks: Sequence[Any]
    index: int
    score: float


def _pose_frame_from_mediapipe_result_with_selection(
    result: Any,
    *,
    frame_index: int,
    timestamp_seconds: float | None,
    min_landmark_confidence: float = 0.3,
    previous_frame: PoseFrame | None = None,
    config: MediaPipePoseEstimatorConfig | None = None,
) -> tuple[PoseFrame, tuple[str, ...], bool, PoseCandidateSelection]:
    """Convert one MediaPipe result and retain candidate-selection diagnostics."""
    pose_landmarks = getattr(result, "pose_landmarks", None) or []
    if not pose_landmarks:
        return (
            PoseFrame(frame_index=frame_index, timestamp_seconds=timestamp_seconds, keypoints={}),
            (f"Frame {frame_index}: MediaPipe did not detect a player body pose.",),
            False,
            PoseCandidateSelection(landmarks=(), index=-1, score=0.0),
        )

    selection_config = config or MediaPipePoseEstimatorConfig(
        min_landmark_confidence=min_landmark_confidence
    )
    selection = select_best_pose_landmarks_with_diagnostics(
        pose_landmarks,
        previous_frame=previous_frame,
        config=selection_config,
    )
    landmarks = selection.landmarks
    keypoints: dict[PoseKeypointName, PoseKeypoint] = {}
    low_confidence_names: list[str] = []
    out_of_frame_names: list[str] = []
    for keypoint_name, landmark_index in _MEDIAPIPE_LANDMARK_INDEXES.items():
        if landmark_index >= len(landmarks):
            continue
        landmark = landmarks[landmark_index]
        confidence = _landmark_confidence(landmark)
        if confidence < min_landmark_confidence:
            low_confidence_names.append(keypoint_name.value)
            continue
        x = float(getattr(landmark, "x", 0.0))
        y = float(getattr(landmark, "y", 0.0))
        out_of_frame = not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0)
        if out_of_frame:
            out_of_frame_names.append(keypoint_name.value)
        keypoints[keypoint_name] = PoseKeypoint(
            point=Point2D(x=x, y=y),
            confidence=confidence,
            out_of_frame=out_of_frame,
        )

    limitations: list[str] = []
    missing_required = [
        keypoint.value for keypoint in _REQUIRED_MEDIAPIPE_LANDMARKS if keypoint not in keypoints
    ]
    if missing_required:
        limitations.append(
            f"Frame {frame_index}: missing required body landmarks: {', '.join(missing_required)}."
        )
    if low_confidence_names:
        limitations.append(
            f"Frame {frame_index}: low-confidence MediaPipe landmarks were ignored: "
            f"{', '.join(low_confidence_names)}."
        )
    if out_of_frame_names:
        limitations.append(
            f"Frame {frame_index}: MediaPipe landmarks outside the visible frame were "
            f"preserved for analysis diagnostics: {', '.join(out_of_frame_names)}."
        )

    return (
        PoseFrame(
            frame_index=frame_index,
            timestamp_seconds=timestamp_seconds,
            keypoints=keypoints,
        ),
        tuple(limitations),
        bool(keypoints),
        selection,
    )


def select_best_pose_landmarks(
    pose_landmarks: Sequence[Sequence[Any]],
    *,
    previous_frame: PoseFrame | None = None,
    config: MediaPipePoseEstimatorConfig | None = None,
) -> Sequence[Any]:
    """Select the most likely player from MediaPipe pose candidates."""
    return select_best_pose_landmarks_with_diagnostics(
        pose_landmarks,
        previous_frame=previous_frame,
        config=config,
    ).landmarks


def select_best_pose_landmarks_with_diagnostics(
    pose_landmarks: Sequence[Sequence[Any]],
    *,
    previous_frame: PoseFrame | None = None,
    config: MediaPipePoseEstimatorConfig | None = None,
) -> PoseCandidateSelection:
    """Select the most likely player and keep the selected candidate index."""
    if not pose_landmarks:
        return PoseCandidateSelection(landmarks=(), index=-1, score=0.0)
    selection_config = config or MediaPipePoseEstimatorConfig()
    scored = tuple(
        (
            index,
            landmarks,
            _pose_selection_score(
                landmarks,
                previous_frame=previous_frame,
                config=selection_config,
            ),
        )
        for index, landmarks in enumerate(pose_landmarks)
    )
    index, landmarks, score = max(scored, key=lambda item: item[2])
    return PoseCandidateSelection(landmarks=landmarks, index=index, score=score)


def _pose_selection_score(
    landmarks: Sequence[Any],
    *,
    previous_frame: PoseFrame | None,
    config: MediaPipePoseEstimatorConfig,
) -> float:
    confidence_score = _mean_landmark_confidence(landmarks)
    size_score = min(1.0, _pose_bbox_area(landmarks) * 4.0)
    center_score = _pose_center_preference_score(landmarks)
    in_frame_score = 1.0 - _pose_out_of_frame_ratio(landmarks)
    if (
        previous_frame is None
        or config.player_selection_strategy == "confidence_size"
        or not previous_frame.keypoints
    ):
        return (
            confidence_score * 0.35 + size_score * 0.3 + center_score * 0.25 + in_frame_score * 0.1
        )

    continuity = _pose_continuity_score(landmarks, previous_frame)
    return continuity * 0.5 + confidence_score * 0.3 + size_score * 0.15 + in_frame_score * 0.05


def _pose_visibility_score(landmarks: Sequence[Any]) -> float:
    if not landmarks:
        return 0.0
    return _pose_bbox_area(landmarks) * _mean_landmark_confidence(landmarks)


def _pose_bbox_area(landmarks: Sequence[Any]) -> float:
    if not landmarks:
        return 0.0
    xs = [float(getattr(landmark, "x", 0.0)) for landmark in landmarks]
    ys = [float(getattr(landmark, "y", 0.0)) for landmark in landmarks]
    return max(0.01, (max(xs) - min(xs)) * (max(ys) - min(ys)))


def _pose_center_preference_score(landmarks: Sequence[Any]) -> float:
    if not landmarks:
        return 0.0
    xs = [float(getattr(landmark, "x", 0.0)) for landmark in landmarks]
    ys = [float(getattr(landmark, "y", 0.0)) for landmark in landmarks]
    center_x = (min(xs) + max(xs)) / 2.0
    center_y = (min(ys) + max(ys)) / 2.0
    distance = math.dist((center_x, center_y), (0.5, 0.55))
    return max(0.0, 1.0 - distance / 0.75)


def _pose_out_of_frame_ratio(landmarks: Sequence[Any]) -> float:
    if not landmarks:
        return 1.0
    out_of_frame = sum(
        1
        for landmark in landmarks
        if not (
            0.0 <= float(getattr(landmark, "x", 0.0)) <= 1.0
            and 0.0 <= float(getattr(landmark, "y", 0.0)) <= 1.0
        )
    )
    return out_of_frame / len(landmarks)


def _mean_landmark_confidence(landmarks: Sequence[Any]) -> float:
    if not landmarks:
        return 0.0
    return sum(_landmark_confidence(landmark) for landmark in landmarks) / len(landmarks)


def _pose_continuity_score(landmarks: Sequence[Any], previous_frame: PoseFrame) -> float:
    distances: list[float] = []
    for name, landmark_index in _MEDIAPIPE_LANDMARK_INDEXES.items():
        previous = previous_frame.keypoints.get(name)
        if previous is None or landmark_index >= len(landmarks):
            continue
        landmark = landmarks[landmark_index]
        distance = math.dist(
            (previous.point.x, previous.point.y),
            (float(getattr(landmark, "x", 0.0)), float(getattr(landmark, "y", 0.0))),
        )
        distances.append(distance)
    if not distances:
        return 0.0
    scale = _pose_frame_body_scale(previous_frame) or 0.25
    mean_distance = sum(distances) / len(distances)
    return max(0.0, 1.0 - mean_distance / max(scale, 0.01))


def stabilize_pose_frames(
    frames: Sequence[PoseFrame],
    config: MediaPipePoseEstimatorConfig | None = None,
) -> tuple[tuple[PoseFrame, ...], tuple[str, ...], PoseQualityDiagnostics]:
    """Reject jumps, interpolate short gaps, smooth landmarks, and return diagnostics."""
    stabilization_config = config or MediaPipePoseEstimatorConfig()
    if stabilization_config.outlier_rejection_enabled:
        outlier_rejected, rejected_count = _reject_outlier_jumps(frames, stabilization_config)
    else:
        outlier_rejected, rejected_count = tuple(frames), 0
    interpolated, interpolated_frame_indexes = _interpolate_short_gaps(
        outlier_rejected,
        stabilization_config,
    )
    smoothed, smoothed_frame_indexes = _smooth_pose_frames(interpolated, stabilization_config)
    diagnostics = pose_quality_diagnostics(
        smoothed,
        smoothed_frame_count=len(smoothed_frame_indexes),
        interpolated_frame_count=len(interpolated_frame_indexes),
        rejected_outlier_count=rejected_count,
    )
    limitations = _postprocess_limitations(
        diagnostics,
        smoothed_frame_indexes=smoothed_frame_indexes,
        interpolated_frame_indexes=interpolated_frame_indexes,
    )
    return smoothed, limitations, diagnostics


@dataclass(frozen=True)
class StabilizationDeltaDiagnostics:
    """Distance summary between raw and stabilized landmarks."""

    mean_delta_ratio: float | None
    max_delta_ratio: float | None
    changed_keypoint_count: int


def stabilization_delta_diagnostics(
    raw_frames: Sequence[PoseFrame],
    stabilized_frames: Sequence[PoseFrame],
) -> StabilizationDeltaDiagnostics:
    """Measure stabilization movement relative to each frame's body scale."""
    ratios: list[float] = []
    raw_by_frame = {frame.frame_index: frame for frame in raw_frames}
    for stabilized in stabilized_frames:
        raw = raw_by_frame.get(stabilized.frame_index)
        if raw is None:
            continue
        scale = _pose_frame_body_scale(raw) or _pose_frame_body_scale(stabilized) or 0.25
        for name, stabilized_keypoint in stabilized.keypoints.items():
            raw_keypoint = raw.keypoints.get(name)
            if raw_keypoint is None:
                continue
            distance = _keypoint_distance(raw_keypoint, stabilized_keypoint)
            if math.isclose(distance, 0.0, abs_tol=1e-9):
                continue
            ratios.append(distance / max(scale, 0.01))
    if not ratios:
        return StabilizationDeltaDiagnostics(
            mean_delta_ratio=None,
            max_delta_ratio=None,
            changed_keypoint_count=0,
        )
    return StabilizationDeltaDiagnostics(
        mean_delta_ratio=round(sum(ratios) / len(ratios), 3),
        max_delta_ratio=round(max(ratios), 3),
        changed_keypoint_count=len(ratios),
    )


def pose_quality_diagnostics(
    frames: Sequence[PoseFrame],
    *,
    smoothed_frame_count: int,
    interpolated_frame_count: int,
    rejected_outlier_count: int,
) -> PoseQualityDiagnostics:
    """Aggregate pose quality from internal pose frames."""
    if not frames:
        return PoseQualityDiagnostics(
            total_frame_count=0,
            detected_pose_frame_count=0,
            detected_pose_frame_ratio=0.0,
            required_landmark_coverage=0.0,
            mean_confidence=None,
            min_confidence=None,
            smoothed_frame_count=smoothed_frame_count,
            interpolated_frame_count=interpolated_frame_count,
            rejected_outlier_count=rejected_outlier_count,
            out_of_frame_landmark_count=0,
        )

    required_slots = len(frames) * len(_REQUIRED_MEDIAPIPE_LANDMARKS)
    required_present = sum(
        1 for frame in frames for name in _REQUIRED_MEDIAPIPE_LANDMARKS if name in frame.keypoints
    )
    confidences = [keypoint.confidence for frame in frames for keypoint in frame.keypoints.values()]
    detected_frames = sum(1 for frame in frames if frame.keypoints)
    out_of_frame_count = sum(
        1 for frame in frames for keypoint in frame.keypoints.values() if keypoint.out_of_frame
    )
    return PoseQualityDiagnostics(
        total_frame_count=len(frames),
        detected_pose_frame_count=detected_frames,
        detected_pose_frame_ratio=round(detected_frames / len(frames), 3),
        required_landmark_coverage=round(required_present / required_slots, 3)
        if required_slots
        else 0.0,
        mean_confidence=round(sum(confidences) / len(confidences), 3) if confidences else None,
        min_confidence=round(min(confidences), 3) if confidences else None,
        smoothed_frame_count=smoothed_frame_count,
        interpolated_frame_count=interpolated_frame_count,
        rejected_outlier_count=rejected_outlier_count,
        out_of_frame_landmark_count=out_of_frame_count,
    )


def _reject_outlier_jumps(
    frames: Sequence[PoseFrame],
    config: MediaPipePoseEstimatorConfig,
) -> tuple[tuple[PoseFrame, ...], int]:
    if len(frames) < 3:
        return tuple(frames), 0

    rejected_count = 0
    output: list[PoseFrame] = [frames[0]]
    for index in range(1, len(frames) - 1):
        previous_frame = output[-1]
        current_frame = frames[index]
        next_frame = frames[index + 1]
        scale = (
            _pose_frame_body_scale(previous_frame)
            or _pose_frame_body_scale(current_frame)
            or _pose_frame_body_scale(next_frame)
            or 0.25
        )
        threshold = max(0.01, scale * config.outlier_distance_ratio)
        keypoints: dict[PoseKeypointName, PoseKeypoint] = {}
        for name, keypoint in current_frame.keypoints.items():
            previous = previous_frame.keypoints.get(name)
            next_keypoint = next_frame.keypoints.get(name)
            if previous is None or next_keypoint is None:
                keypoints[name] = keypoint
                continue
            previous_distance = _keypoint_distance(previous, keypoint)
            next_distance = _keypoint_distance(next_keypoint, keypoint)
            surrounding_distance = _keypoint_distance(previous, next_keypoint)
            if (
                previous_distance > threshold
                and next_distance > threshold
                and surrounding_distance <= threshold
            ):
                rejected_count += 1
                continue
            keypoints[name] = keypoint
        output.append(
            PoseFrame(
                frame_index=current_frame.frame_index,
                timestamp_seconds=current_frame.timestamp_seconds,
                keypoints=keypoints,
            )
        )
    output.append(frames[-1])
    return tuple(output), rejected_count


def _interpolate_short_gaps(
    frames: Sequence[PoseFrame],
    config: MediaPipePoseEstimatorConfig,
) -> tuple[tuple[PoseFrame, ...], frozenset[int]]:
    if config.max_interpolation_gap_frames == 0 or len(frames) < 3:
        return tuple(frames), frozenset()

    keypoints_by_frame = [dict(frame.keypoints) for frame in frames]
    interpolated_frame_indexes: set[int] = set()
    for name in _all_keypoint_names(frames):
        index = 0
        while index < len(frames):
            if name in keypoints_by_frame[index]:
                index += 1
                continue
            gap_start = index
            while index < len(frames) and name not in keypoints_by_frame[index]:
                index += 1
            gap_end = index - 1
            gap_length = gap_end - gap_start + 1
            before_index = gap_start - 1
            after_index = index
            if (
                before_index < 0
                or after_index >= len(frames)
                or gap_length > config.max_interpolation_gap_frames
            ):
                continue
            before = keypoints_by_frame[before_index][name]
            after = keypoints_by_frame[after_index][name]
            for position in range(gap_start, gap_end + 1):
                ratio = (position - before_index) / (after_index - before_index)
                interpolated = PoseKeypoint(
                    point=Point2D(
                        x=before.point.x + (after.point.x - before.point.x) * ratio,
                        y=before.point.y + (after.point.y - before.point.y) * ratio,
                    ),
                    confidence=min(before.confidence, after.confidence) * 0.65,
                    interpolated=True,
                    out_of_frame=before.out_of_frame or after.out_of_frame,
                )
                keypoints_by_frame[position][name] = interpolated
                interpolated_frame_indexes.add(frames[position].frame_index)

    return (
        tuple(
            PoseFrame(
                frame_index=frame.frame_index,
                timestamp_seconds=frame.timestamp_seconds,
                keypoints=keypoints_by_frame[index],
            )
            for index, frame in enumerate(frames)
        ),
        frozenset(interpolated_frame_indexes),
    )


def _smooth_pose_frames(
    frames: Sequence[PoseFrame],
    config: MediaPipePoseEstimatorConfig,
) -> tuple[tuple[PoseFrame, ...], frozenset[int]]:
    if config.smoothing_window <= 1 or len(frames) < 3:
        return tuple(frames), frozenset()

    radius = config.smoothing_window // 2
    smoothed_frame_indexes: set[int] = set()
    output: list[PoseFrame] = []
    for index, frame in enumerate(frames):
        keypoints: dict[PoseKeypointName, PoseKeypoint] = {}
        for name, keypoint in frame.keypoints.items():
            neighbors = [
                neighbor.keypoints[name]
                for neighbor in frames[max(0, index - radius) : index + radius + 1]
                if name in neighbor.keypoints
            ]
            if len(neighbors) < 2:
                keypoints[name] = keypoint
                continue
            if _should_skip_smoothing_for_fast_keypoint(name, frames, index, config):
                keypoints[name] = keypoint
                continue
            average_x = sum(neighbor.point.x for neighbor in neighbors) / len(neighbors)
            average_y = sum(neighbor.point.y for neighbor in neighbors) / len(neighbors)
            if not math.isclose(average_x, keypoint.point.x) or not math.isclose(
                average_y,
                keypoint.point.y,
            ):
                smoothed_frame_indexes.add(frame.frame_index)
            keypoints[name] = PoseKeypoint(
                point=Point2D(x=average_x, y=average_y),
                confidence=keypoint.confidence,
                interpolated=keypoint.interpolated,
                smoothed=True,
                out_of_frame=keypoint.out_of_frame,
            )
        output.append(
            PoseFrame(
                frame_index=frame.frame_index,
                timestamp_seconds=frame.timestamp_seconds,
                keypoints=keypoints,
            )
        )
    return tuple(output), frozenset(smoothed_frame_indexes)


def _should_skip_smoothing_for_fast_keypoint(
    name: PoseKeypointName,
    frames: Sequence[PoseFrame],
    index: int,
    config: MediaPipePoseEstimatorConfig,
) -> bool:
    fast_keypoints = {
        PoseKeypointName.LEFT_WRIST,
        PoseKeypointName.RIGHT_WRIST,
        PoseKeypointName.LEFT_ANKLE,
        PoseKeypointName.RIGHT_ANKLE,
    }
    if name not in fast_keypoints or index <= 0 or index >= len(frames) - 1:
        return False
    previous = frames[index - 1].keypoints.get(name)
    current = frames[index].keypoints.get(name)
    next_keypoint = frames[index + 1].keypoints.get(name)
    if previous is None or current is None or next_keypoint is None:
        return False
    scale = (
        _pose_frame_body_scale(frames[index - 1])
        or _pose_frame_body_scale(frames[index])
        or _pose_frame_body_scale(frames[index + 1])
        or 0.25
    )
    threshold = max(0.01, scale * config.high_velocity_smoothing_limit_ratio)
    return (
        _keypoint_distance(previous, current) > threshold
        or _keypoint_distance(current, next_keypoint) > threshold
    )


def _postprocess_limitations(
    diagnostics: PoseQualityDiagnostics,
    *,
    smoothed_frame_indexes: Iterable[int],
    interpolated_frame_indexes: Iterable[int],
) -> tuple[str, ...]:
    limitations: list[str] = []
    if diagnostics.smoothed_frame_count:
        limitations.append(
            f"Pose landmarks were smoothed on {diagnostics.smoothed_frame_count} frame(s)."
        )
    if diagnostics.interpolated_frame_count:
        frames = ", ".join(str(index) for index in sorted(interpolated_frame_indexes))
        limitations.append(f"Short missing-landmark gaps were interpolated on frame(s): {frames}.")
    if diagnostics.rejected_outlier_count:
        limitations.append(
            f"{diagnostics.rejected_outlier_count} obvious landmark jump(s) were rejected."
        )
    if diagnostics.out_of_frame_landmark_count:
        limitations.append(
            f"{diagnostics.out_of_frame_landmark_count} landmark(s) were outside the "
            "visible frame; overlay drawing clamps them to the video content rectangle."
        )
    if diagnostics.detected_pose_frame_ratio < 0.8:
        limitations.append("Pose detection covered fewer than 80% of sampled frames.")
    if diagnostics.required_landmark_coverage < 0.85:
        limitations.append("Required body landmark coverage was low for swing evaluation.")
    return tuple(limitations)


def _all_keypoint_names(frames: Sequence[PoseFrame]) -> tuple[PoseKeypointName, ...]:
    return tuple(dict.fromkeys(name for frame in frames for name in frame.keypoints))


def _keypoint_distance(first: PoseKeypoint, second: PoseKeypoint) -> float:
    return math.dist((first.point.x, first.point.y), (second.point.x, second.point.y))


def _pose_frame_body_scale(frame: PoseFrame) -> float | None:
    left_shoulder = frame.keypoints.get(PoseKeypointName.LEFT_SHOULDER)
    right_shoulder = frame.keypoints.get(PoseKeypointName.RIGHT_SHOULDER)
    left_hip = frame.keypoints.get(PoseKeypointName.LEFT_HIP)
    right_hip = frame.keypoints.get(PoseKeypointName.RIGHT_HIP)
    if left_shoulder and right_shoulder:
        shoulder_width = _keypoint_distance(left_shoulder, right_shoulder)
        if shoulder_width > 0:
            return shoulder_width
    if left_shoulder and left_hip:
        torso = _keypoint_distance(left_shoulder, left_hip)
        if torso > 0:
            return torso
    if right_shoulder and right_hip:
        torso = _keypoint_distance(right_shoulder, right_hip)
        if torso > 0:
            return torso
    return None


def _landmark_confidence(landmark: Any) -> float:
    values = [
        float(value)
        for value in (
            getattr(landmark, "visibility", None),
            getattr(landmark, "presence", None),
        )
        if value is not None
    ]
    if not values:
        return 1.0
    return _clamp_float(min(values))


def _monotonic_timestamp_ms(
    frame: FrameData,
    sequence_index: int,
    previous_timestamp_ms: int,
) -> int:
    timestamp_ms = round(frame.timestamp_seconds * 1000)
    if timestamp_ms <= previous_timestamp_ms:
        timestamp_ms = previous_timestamp_ms + 1
    if timestamp_ms < 0:
        timestamp_ms = sequence_index
    return timestamp_ms


def _mediapipe_image_from_frame(frame: FrameData) -> Any:
    try:
        mediapipe = import_module("mediapipe")
    except ImportError as exc:
        raise MediaPipeDependencyMissingError() from exc

    rgb_image = cv2.cvtColor(frame.image, cv2.COLOR_BGR2RGB)
    contiguous_image = np.ascontiguousarray(rgb_image)
    return mediapipe.Image(
        image_format=mediapipe.ImageFormat.SRGB,
        data=cast(Any, contiguous_image),
    )


def _mediapipe_base_options(
    mediapipe: Any,
    *,
    model_path: Path,
    runtime_delegate: Literal["cpu", "gpu"],
) -> Any:
    base_options = mediapipe.tasks.BaseOptions
    delegate_enum = getattr(base_options, "Delegate", None)
    if delegate_enum is None:
        return base_options(model_asset_path=str(model_path))

    delegate_name = "GPU" if runtime_delegate == "gpu" else "CPU"
    delegate = getattr(delegate_enum, delegate_name, None)
    if delegate is None:
        return base_options(model_asset_path=str(model_path))
    return base_options(model_asset_path=str(model_path), delegate=delegate)


def _clamp_float(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    if not np.isfinite(value):
        return minimum
    return min(maximum, max(minimum, float(value)))
