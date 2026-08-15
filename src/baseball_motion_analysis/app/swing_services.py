"""Application service for swing analysis workflows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from baseball_motion_analysis.analysis import (
    SwingAnalysisConfig,
    SwingAnalysisResult,
    analyze_swing,
)
from baseball_motion_analysis.app.media_services import (
    MediaApplicationError,
    VideoLibraryApplicationService,
)
from baseball_motion_analysis.feedback import SwingFeedbackReport, generate_swing_feedback
from baseball_motion_analysis.motion import (
    BodySide,
    NormalizedBodySides,
    SwingHandedness,
    SwingMetricName,
    SwingPhase,
    SwingPhaseFrames,
    detect_swing_phases,
    resolve_body_sides,
    side_keypoint,
)
from baseball_motion_analysis.pose import (
    MediaPipePoseEstimator,
    MediaPipePoseEstimatorConfig,
    Point2D,
    PoseDebugDiagnostics,
    PoseEstimationError,
    PoseEstimator,
    PoseFrame,
    PoseKeypoint,
    PoseKeypointName,
    PoseQualityDiagnostics,
    pose_quality_diagnostics,
)
from baseball_motion_analysis.video import (
    FrameData,
    FrameSamplingOptions,
    LocalMediaStorageConfig,
    MediaInputService,
)


class SwingVideoAnalysisError(Exception):
    """Raised when video-driven swing analysis cannot complete."""

    error_code = "swing_video_analysis_error"
    user_message = "Swing video analysis failed."

    def __init__(self, message: str | None = None, *, error_code: str | None = None) -> None:
        super().__init__(message or self.user_message)
        self.message = message or self.user_message
        if error_code is not None:
            self.error_code = error_code


class NoUsablePoseFramesError(SwingVideoAnalysisError):
    """Raised when pose estimation yields no usable frames."""

    error_code = "no_usable_pose_frames"
    user_message = "No usable pose frames were detected in the selected video."


@dataclass(frozen=True)
class AnalyzeSwingRequest:
    """Request to analyze an already-extracted pose sequence."""

    frames: Sequence[PoseFrame]
    handedness: SwingHandedness = SwingHandedness.UNKNOWN
    phase_frames: Mapping[SwingPhase, int] | None = None
    config: SwingAnalysisConfig | None = None
    frame_width: int | None = None
    frame_height: int | None = None


@dataclass(frozen=True)
class AnalyzeSwingResponse:
    """Application-service result for swing evaluation."""

    analysis: SwingAnalysisResult
    feedback: SwingFeedbackReport


@dataclass(frozen=True)
class SwingVideoSamplingOptions:
    """Sampling options for video-driven swing analysis."""

    quality_mode: Literal["faster", "balanced", "higher_accuracy"] = "higher_accuracy"
    target_fps: float | None = None
    max_frame_count: int | None = None
    full_frame_max_frame_count: int | None = None

    def __post_init__(self) -> None:
        if self.quality_mode not in {"faster", "balanced", "higher_accuracy"}:
            msg = "quality_mode must be faster, balanced, or higher_accuracy"
            raise ValueError(msg)
        if self.target_fps is not None and self.target_fps <= 0:
            msg = "target_fps must be greater than 0"
            raise ValueError(msg)
        if self.max_frame_count is not None and self.max_frame_count < 1:
            msg = "max_frame_count must be greater than or equal to 1"
            raise ValueError(msg)
        if self.full_frame_max_frame_count is not None and self.full_frame_max_frame_count < 1:
            msg = "full_frame_max_frame_count must be greater than or equal to 1"
            raise ValueError(msg)


@dataclass(frozen=True)
class SwingVideoSamplingDiagnostics:
    """Diagnostics for video-frame coverage used by analysis."""

    quality_mode: str
    source_fps: float | None
    target_fps: float | None
    effective_fps: float | None
    sampled_frame_count: int
    total_frame_count: int | None
    max_frame_count: int
    cap_applied: bool
    full_frame_sampling: bool


@dataclass(frozen=True)
class AnalyzeSwingVideoRequest:
    """Request to analyze a stored video."""

    media_id: str
    handedness: SwingHandedness = SwingHandedness.UNKNOWN
    sampling: SwingVideoSamplingOptions = field(default_factory=SwingVideoSamplingOptions)
    pose_mode: Literal["normal", "notebook_parity"] = "normal"
    overlay_source: Literal["stabilized", "raw"] = "stabilized"

    def __post_init__(self) -> None:
        if self.pose_mode not in {"normal", "notebook_parity"}:
            msg = "pose_mode must be normal or notebook_parity"
            raise ValueError(msg)
        if self.overlay_source not in {"stabilized", "raw"}:
            msg = "overlay_source must be stabilized or raw"
            raise ValueError(msg)


@dataclass(frozen=True)
class SwingEventWindow:
    """Detected swing event frame and surrounding window."""

    phase: SwingPhase
    frame_index: int
    start_frame_index: int
    end_frame_index: int
    confidence: float
    label: str
    detection_method: str


@dataclass(frozen=True)
class PoseOverlayKeypoint:
    """Browser overlay keypoint data."""

    name: str
    x: float
    y: float
    confidence: float
    category: str
    label: str | None = None
    interpolated: bool = False
    smoothed: bool = False
    out_of_frame: bool = False


@dataclass(frozen=True)
class PoseOverlayFrame:
    """Browser overlay pose data for one sampled frame."""

    frame_index: int
    timestamp_seconds: float | None
    keypoints: tuple[PoseOverlayKeypoint, ...]
    is_event_frame: bool
    source: Literal["stabilized", "raw"] = "stabilized"


@dataclass(frozen=True)
class EvaluationOverlayPoint:
    """Normalized browser-neutral point for an evaluation overlay line."""

    x: float
    y: float


@dataclass(frozen=True)
class EvaluationOverlayLine:
    """Browser-neutral swing evaluation line drawn over replay frames."""

    metric_name: str
    phase: str
    frame_index: int
    start_keypoint_name: str | None
    end_keypoint_name: str | None
    start: EvaluationOverlayPoint
    end: EvaluationOverlayPoint
    label: str
    severity: str
    confidence: float
    style: Literal["solid", "dashed", "reference"]
    color_role: Literal["good", "warning", "severe", "neutral", "low_confidence"]


@dataclass(frozen=True)
class CachedPoseEstimation:
    """Cached pose frames with original limitations."""

    frames: tuple[PoseFrame, ...]
    raw_frames: tuple[PoseFrame, ...]
    frame_width: int
    frame_height: int
    limitations: tuple[str, ...]
    pose_diagnostics: PoseQualityDiagnostics | None
    raw_pose_diagnostics: PoseQualityDiagnostics | None
    pose_debug_diagnostics: PoseDebugDiagnostics | None
    sampling_diagnostics: SwingVideoSamplingDiagnostics


@dataclass(frozen=True)
class SwingPoseEstimationBundle:
    """Pose-estimation output used by video swing analysis."""

    frames: tuple[PoseFrame, ...]
    raw_frames: tuple[PoseFrame, ...]
    frame_width: int
    frame_height: int
    limitations: tuple[str, ...]
    pose_diagnostics: PoseQualityDiagnostics | None
    raw_pose_diagnostics: PoseQualityDiagnostics | None
    pose_debug_diagnostics: PoseDebugDiagnostics | None
    sampling_diagnostics: SwingVideoSamplingDiagnostics


@dataclass(frozen=True)
class AnalyzeSwingVideoResponse:
    """Video-driven swing analysis result."""

    analysis: SwingAnalysisResult
    feedback: SwingFeedbackReport
    pose_frames: tuple[PoseFrame, ...]
    raw_pose_frames: tuple[PoseFrame, ...]
    events: tuple[SwingEventWindow, ...]
    overlay_frames: tuple[PoseOverlayFrame, ...]
    raw_overlay_frames: tuple[PoseOverlayFrame, ...]
    evaluation_overlay: tuple[EvaluationOverlayLine, ...]
    limitations: tuple[str, ...]
    pose_cache_hit: bool
    pose_diagnostics: PoseQualityDiagnostics | None
    raw_pose_diagnostics: PoseQualityDiagnostics | None
    pose_debug_diagnostics: PoseDebugDiagnostics | None
    sampling_diagnostics: SwingVideoSamplingDiagnostics


class SwingAnalysisApplicationService:
    """Application-service boundary for swing motion evaluation."""

    def analyze_pose_sequence(self, request: AnalyzeSwingRequest) -> AnalyzeSwingResponse:
        """Analyze pose observations and generate a feedback report."""
        analysis = analyze_swing(
            request.frames,
            handedness=request.handedness,
            phase_frames=request.phase_frames,
            config=request.config,
            frame_width=request.frame_width,
            frame_height=request.frame_height,
        )
        feedback = generate_swing_feedback(analysis)
        return AnalyzeSwingResponse(analysis=analysis, feedback=feedback)


class SwingVideoAnalysisApplicationService:
    """Application-service boundary for stored-video swing analysis."""

    def __init__(
        self,
        *,
        video_library_service: VideoLibraryApplicationService,
        pose_estimator: PoseEstimator | None = None,
        mediapipe_pose_model_path: Path | str | None = None,
        mediapipe_config: MediaPipePoseEstimatorConfig | None = None,
        media_input_service: MediaInputService | None = None,
        pose_cache: dict[
            tuple[str, SwingVideoSamplingOptions, str],
            CachedPoseEstimation,
        ]
        | None = None,
    ) -> None:
        self._video_library_service = video_library_service
        self._pose_estimator = pose_estimator
        self._mediapipe_pose_model_path = mediapipe_pose_model_path
        self._mediapipe_config = mediapipe_config or MediaPipePoseEstimatorConfig()
        self._media_input_service = media_input_service
        self._pose_cache = pose_cache if pose_cache is not None else {}
        self.cache_hits = 0

    def analyze_video(self, request: AnalyzeSwingVideoRequest) -> AnalyzeSwingVideoResponse:
        """Analyze a stored video by sampling frames and estimating pose."""
        pose_bundle, cache_hit = self._pose_frames_for_video(request)
        pose_frames = pose_bundle.frames
        if not pose_frames:
            raise NoUsablePoseFramesError()

        phases = detect_swing_phases(
            pose_frames,
            frame_width=pose_bundle.frame_width,
            frame_height=pose_bundle.frame_height,
        )
        phase_frames = {
            SwingPhase.SETUP: phases.setup,
            SwingPhase.STRIDE: phases.stride,
            SwingPhase.FOOT_STRIKE: phases.foot_strike,
            SwingPhase.IMPACT: phases.impact,
            SwingPhase.FOLLOW_THROUGH: phases.follow_through,
        }
        analysis_response = SwingAnalysisApplicationService().analyze_pose_sequence(
            AnalyzeSwingRequest(
                frames=pose_frames,
                handedness=request.handedness,
                phase_frames=phase_frames,
                frame_width=pose_bundle.frame_width,
                frame_height=pose_bundle.frame_height,
            )
        )
        events = _events_from_phases(phases)
        overlay_frames = _overlay_frames(pose_frames, events, source="stabilized")
        raw_overlay_frames = _overlay_frames(pose_bundle.raw_frames, events, source="raw")
        evaluation_overlay = build_evaluation_overlay_lines(
            pose_frames,
            analysis_response.analysis,
        )
        combined_limitations = tuple(
            dict.fromkeys(
                (
                    *pose_bundle.limitations,
                    *phases.limitations,
                    *analysis_response.analysis.limitations,
                )
            )
        )

        return AnalyzeSwingVideoResponse(
            analysis=analysis_response.analysis,
            feedback=analysis_response.feedback,
            pose_frames=pose_frames,
            raw_pose_frames=pose_bundle.raw_frames,
            events=events,
            overlay_frames=overlay_frames,
            raw_overlay_frames=raw_overlay_frames,
            evaluation_overlay=evaluation_overlay,
            limitations=combined_limitations,
            pose_cache_hit=cache_hit,
            pose_diagnostics=pose_bundle.pose_diagnostics,
            raw_pose_diagnostics=pose_bundle.raw_pose_diagnostics,
            pose_debug_diagnostics=pose_bundle.pose_debug_diagnostics,
            sampling_diagnostics=pose_bundle.sampling_diagnostics,
        )

    def _pose_frames_for_video(
        self, request: AnalyzeSwingVideoRequest
    ) -> tuple[SwingPoseEstimationBundle, bool]:
        cache_key = (request.media_id, request.sampling, request.pose_mode)
        cached = self._pose_cache.get(cache_key)
        if cached is not None:
            self.cache_hits += 1
            return (
                SwingPoseEstimationBundle(
                    frames=cached.frames,
                    raw_frames=cached.raw_frames,
                    frame_width=cached.frame_width,
                    frame_height=cached.frame_height,
                    limitations=(
                        *cached.limitations,
                        "Pose frames were reused from the in-memory cache.",
                    ),
                    pose_diagnostics=cached.pose_diagnostics,
                    raw_pose_diagnostics=cached.raw_pose_diagnostics,
                    pose_debug_diagnostics=cached.pose_debug_diagnostics,
                    sampling_diagnostics=cached.sampling_diagnostics,
                ),
                True,
            )

        try:
            record = self._video_library_service.get_video(request.media_id)
            location = self._video_library_service.get_video_content_location(request.media_id)
        except MediaApplicationError:
            raise

        media_input_service = self._media_input_service or MediaInputService(
            LocalMediaStorageConfig(media_root=location.path.parent)
        )
        frame_sampling, requested_target_fps, requested_max_count = _frame_sampling_options(
            request.sampling,
            total_frame_count=record.total_frame_count,
        )
        sequence = media_input_service.load_video_file(
            location.path,
            sampling=frame_sampling,
        )
        sampling_diagnostics = _sampling_diagnostics(
            request.sampling,
            sequence_frames=sequence.frames,
            source_fps=sequence.metadata.fps,
            total_frame_count=sequence.metadata.total_frame_count,
            requested_target_fps=requested_target_fps,
            requested_max_count=requested_max_count,
        )
        try:
            pose_result = self._pose_estimator_for_request(request).estimate(sequence.frames)
        except PoseEstimationError as exc:
            raise SwingVideoAnalysisError(exc.message, error_code=exc.error_code) from exc
        if not pose_result.frames:
            raise NoUsablePoseFramesError()
        raw_pose_frames = pose_result.raw_frames or pose_result.frames
        pose_diagnostics = pose_result.diagnostics or pose_quality_diagnostics(
            pose_result.frames,
            smoothed_frame_count=0,
            interpolated_frame_count=0,
            rejected_outlier_count=0,
        )
        raw_pose_diagnostics = pose_result.raw_diagnostics or pose_quality_diagnostics(
            raw_pose_frames,
            smoothed_frame_count=0,
            interpolated_frame_count=0,
            rejected_outlier_count=0,
        )
        pose_debug_diagnostics = pose_result.debug_diagnostics or _fallback_pose_debug_diagnostics(
            request,
        )
        sampling_limitations = _sampling_limitations(sampling_diagnostics)
        limitations = (*sampling_limitations, *pose_result.limitations)
        self._pose_cache[cache_key] = CachedPoseEstimation(
            frames=pose_result.frames,
            raw_frames=raw_pose_frames,
            frame_width=sequence.metadata.width,
            frame_height=sequence.metadata.height,
            limitations=limitations,
            pose_diagnostics=pose_diagnostics,
            raw_pose_diagnostics=raw_pose_diagnostics,
            pose_debug_diagnostics=pose_debug_diagnostics,
            sampling_diagnostics=sampling_diagnostics,
        )
        return (
            SwingPoseEstimationBundle(
                frames=pose_result.frames,
                raw_frames=raw_pose_frames,
                frame_width=sequence.metadata.width,
                frame_height=sequence.metadata.height,
                limitations=limitations,
                pose_diagnostics=pose_diagnostics,
                raw_pose_diagnostics=raw_pose_diagnostics,
                pose_debug_diagnostics=pose_debug_diagnostics,
                sampling_diagnostics=sampling_diagnostics,
            ),
            False,
        )

    def _pose_estimator_for_request(self, request: AnalyzeSwingVideoRequest) -> PoseEstimator:
        if self._pose_estimator is not None:
            return self._pose_estimator
        config = self._mediapipe_config
        if request.pose_mode == "notebook_parity":
            config = MediaPipePoseEstimatorConfig.notebook_parity(config)
        return MediaPipePoseEstimator(
            model_path=self._mediapipe_pose_model_path,
            config=config,
        )


def _events_from_phases(phases: SwingPhaseFrames) -> tuple[SwingEventWindow, ...]:
    phase_labels = {
        SwingPhase.SETUP: "Setup",
        SwingPhase.STRIDE: "Stride",
        SwingPhase.FOOT_STRIKE: "Foot Strike",
        SwingPhase.IMPACT: "Impact",
        SwingPhase.FOLLOW_THROUGH: "Follow-through",
    }
    return tuple(
        SwingEventWindow(
            phase=phase,
            frame_index=phases.frame_index_for(phase),
            start_frame_index=phases.frame_index_for(phase),
            end_frame_index=phases.frame_index_for(phase),
            confidence=phases.confidence_for(phase),
            label=phase_labels[phase],
            detection_method=phases.detection_method_for(phase),
        )
        for phase in SwingPhase
    )


def _frame_sampling_options(
    request: SwingVideoSamplingOptions,
    *,
    total_frame_count: int | None,
) -> tuple[FrameSamplingOptions, float | None, int]:
    defaults = _sampling_quality_defaults(request.quality_mode)
    target_fps = request.target_fps if request.target_fps is not None else defaults["target_fps"]
    max_frame_count = int(
        request.max_frame_count
        if request.max_frame_count is not None
        else defaults["max_frame_count"]
    )
    full_frame_cap = int(
        request.full_frame_max_frame_count
        if request.full_frame_max_frame_count is not None
        else defaults["full_frame_max_frame_count"]
    )
    use_full_frame_sampling = (
        total_frame_count is not None
        and total_frame_count <= full_frame_cap
        and request.target_fps is None
    )
    return (
        FrameSamplingOptions(
            target_fps=None if use_full_frame_sampling else target_fps,
            max_frame_count=max_frame_count,
            sample_every_n_frames=1,
        ),
        None if use_full_frame_sampling else target_fps,
        max_frame_count,
    )


def _sampling_quality_defaults(quality_mode: str) -> dict[str, float | int]:
    if quality_mode == "faster":
        return {"target_fps": 12.0, "max_frame_count": 60, "full_frame_max_frame_count": 90}
    if quality_mode == "balanced":
        return {"target_fps": 24.0, "max_frame_count": 120, "full_frame_max_frame_count": 150}
    return {"target_fps": 30.0, "max_frame_count": 180, "full_frame_max_frame_count": 180}


def _sampling_diagnostics(
    request: SwingVideoSamplingOptions,
    *,
    sequence_frames: Sequence[FrameData],
    source_fps: float | None,
    total_frame_count: int | None,
    requested_target_fps: float | None,
    requested_max_count: int,
) -> SwingVideoSamplingDiagnostics:
    sampled_count = len(sequence_frames)
    effective_fps = _effective_sampled_fps(sequence_frames, source_fps)
    cap_applied = total_frame_count is not None and sampled_count < total_frame_count
    full_frame_sampling = total_frame_count is not None and sampled_count >= total_frame_count
    return SwingVideoSamplingDiagnostics(
        quality_mode=request.quality_mode,
        source_fps=source_fps,
        target_fps=requested_target_fps,
        effective_fps=effective_fps,
        sampled_frame_count=sampled_count,
        total_frame_count=total_frame_count,
        max_frame_count=requested_max_count,
        cap_applied=cap_applied,
        full_frame_sampling=full_frame_sampling,
    )


def _effective_sampled_fps(
    sequence_frames: Sequence[FrameData],
    source_fps: float | None,
) -> float | None:
    if len(sequence_frames) < 2:
        return source_fps
    first = sequence_frames[0]
    last = sequence_frames[-1]
    first_timestamp = first.timestamp_seconds
    last_timestamp = last.timestamp_seconds
    if first_timestamp is None or last_timestamp is None or last_timestamp <= first_timestamp:
        return source_fps
    return round((len(sequence_frames) - 1) / (last_timestamp - first_timestamp), 3)


def _sampling_limitations(
    diagnostics: SwingVideoSamplingDiagnostics,
) -> tuple[str, ...]:
    limitations = [
        (
            f"Video pose analysis used {diagnostics.sampled_frame_count} sampled frame(s) "
            f"at about {_format_optional_float(diagnostics.effective_fps)} FPS; overlay "
            "points are aligned to sampled frames."
        )
    ]
    if diagnostics.cap_applied:
        limitations.append(
            "Sampling was reduced by the selected quality mode or frame cap; very fast "
            "swing events may be missed."
        )
    if diagnostics.quality_mode == "faster":
        limitations.append(
            "Faster analysis mode uses fewer frames and can reduce phase detection accuracy."
        )
    return tuple(limitations)


def _format_optional_float(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}"


def _fallback_pose_debug_diagnostics(
    request: AnalyzeSwingVideoRequest,
) -> PoseDebugDiagnostics:
    return PoseDebugDiagnostics(
        running_mode="video",
        processing_mode=request.pose_mode,
        requested_num_poses=1,
        player_selection_strategy="injected_pose_estimator",
        selected_candidate_indexes=(),
    )


def _overlay_frames(
    pose_frames: Sequence[PoseFrame],
    events: Sequence[SwingEventWindow],
    *,
    source: Literal["stabilized", "raw"],
) -> tuple[PoseOverlayFrame, ...]:
    event_indexes = {event.frame_index for event in events}
    return tuple(
        PoseOverlayFrame(
            frame_index=frame.frame_index,
            timestamp_seconds=frame.timestamp_seconds,
            keypoints=tuple(
                _overlay_keypoint(
                    name.value,
                    keypoint.confidence,
                    keypoint.point.x,
                    keypoint.point.y,
                    interpolated=keypoint.interpolated,
                    smoothed=keypoint.smoothed,
                    out_of_frame=keypoint.out_of_frame,
                )
                for name, keypoint in frame.keypoints.items()
            ),
            is_event_frame=frame.frame_index in event_indexes,
            source=source,
        )
        for frame in pose_frames
    )


def _overlay_keypoint(
    name: str,
    confidence: float,
    x: float,
    y: float,
    *,
    interpolated: bool,
    smoothed: bool,
    out_of_frame: bool,
) -> PoseOverlayKeypoint:
    label_names = {
        "nose": "Head",
        "left_wrist": "L Wrist",
        "right_wrist": "R Wrist",
        "bat_tip": "Bat",
        "bat_barrel": "Bat",
    }
    category = "bat" if name in {"bat_tip", "bat_barrel"} else "body"
    if confidence < 0.5:
        category = "low_confidence"
    return PoseOverlayKeypoint(
        name=name,
        x=x,
        y=y,
        confidence=confidence,
        category=category,
        label=label_names.get(name),
        interpolated=interpolated,
        smoothed=smoothed,
        out_of_frame=out_of_frame,
    )


def build_evaluation_overlay_lines(
    pose_frames: Sequence[PoseFrame],
    analysis: SwingAnalysisResult,
) -> tuple[EvaluationOverlayLine, ...]:
    """Build browser-neutral evaluation lines from v2 metric evidence and pose frames."""
    frame_by_index = {frame.frame_index: frame for frame in pose_frames}
    sides = resolve_body_sides(analysis.handedness)
    lines: list[EvaluationOverlayLine] = []
    for metric in analysis.metrics:
        if metric.value is None:
            continue
        if metric.name == SwingMetricName.NORMALIZED_STANCE_WIDTH:
            lines.extend(
                _stance_width_lines(
                    frame_by_index,
                    metric.evidence_frames,
                    metric.name.value,
                    metric.severity.value,
                    metric.confidence,
                )
            )
        elif metric.name == SwingMetricName.TORSO_FORWARD_TILT:
            lines.extend(
                _torso_lines(
                    frame_by_index,
                    metric.evidence_frames,
                    metric.name.value,
                    metric.severity.value,
                    metric.confidence,
                    label="Torso tilt",
                )
            )
        elif metric.name == SwingMetricName.TORSO_TILT_PRESERVATION:
            lines.extend(
                _torso_lines(
                    frame_by_index,
                    metric.evidence_frames,
                    metric.name.value,
                    metric.severity.value,
                    metric.confidence,
                    label="Tilt hold",
                    style="reference",
                )
            )
        elif metric.name == SwingMetricName.GRIP_LOADING_VECTOR:
            lines.extend(
                _grip_loading_lines(
                    frame_by_index,
                    metric.evidence_frames,
                    sides.rear,
                    metric.name.value,
                    metric.severity.value,
                    metric.confidence,
                )
            )
        elif metric.name == SwingMetricName.REAR_KNEE_SWAY:
            lines.extend(
                _rear_knee_sway_lines(
                    frame_by_index,
                    metric.evidence_frames,
                    sides,
                    metric.name.value,
                    metric.severity.value,
                    metric.confidence,
                )
            )
        elif metric.name == SwingMetricName.HEAD_TRANSLATION_RATIO:
            lines.extend(
                _head_translation_lines(
                    frame_by_index,
                    metric.evidence_frames,
                    metric.name.value,
                    metric.severity.value,
                    metric.confidence,
                )
            )
        elif metric.name == SwingMetricName.EARLY_CONNECTION_ANGLE:
            lines.extend(
                _early_connection_lines(
                    frame_by_index,
                    metric.evidence_frames,
                    sides.lead,
                    metric.name.value,
                    metric.severity.value,
                    metric.confidence,
                )
            )
        elif metric.name == SwingMetricName.LEAD_KNEE_BLOCKING_INDEX:
            lines.extend(
                _lead_knee_blocking_lines(
                    frame_by_index,
                    metric.evidence_frames,
                    sides.lead,
                    metric.name.value,
                    metric.severity.value,
                    metric.confidence,
                )
            )
        elif metric.name == SwingMetricName.HIP_SHOULDER_SEPARATION_TIMING:
            lines.extend(
                _hip_shoulder_lines(
                    frame_by_index,
                    metric.evidence_frames,
                    metric.name.value,
                    metric.severity.value,
                    metric.confidence,
                )
            )
        elif metric.name == SwingMetricName.ESTIMATED_ATTACK_ANGLE:
            lines.extend(
                _attack_angle_lines(
                    frame_by_index,
                    metric.evidence_frames,
                    metric.name.value,
                    metric.severity.value,
                    metric.confidence,
                    fallback=any(
                        "fallback" in limitation.lower() for limitation in metric.limitations
                    ),
                )
            )
        elif metric.name == SwingMetricName.FOLLOW_THROUGH_POSTURE_BALANCE:
            lines.extend(
                _follow_through_lines(
                    frame_by_index,
                    metric.evidence_frames,
                    metric.name.value,
                    metric.severity.value,
                    metric.confidence,
                )
            )
    return tuple(lines)


def _stance_width_lines(
    frame_by_index: Mapping[int, PoseFrame],
    evidence_frames: Sequence[int],
    metric_name: str,
    severity: str,
    confidence: float,
) -> tuple[EvaluationOverlayLine, ...]:
    lines: list[EvaluationOverlayLine] = []
    for frame_index in evidence_frames:
        frame = frame_by_index.get(frame_index)
        if frame is None:
            continue
        lines.extend(
            _line_from_keypoints(
                frame,
                PoseKeypointName.LEFT_ANKLE,
                PoseKeypointName.RIGHT_ANKLE,
                metric_name=metric_name,
                label="Stance width",
                severity=severity,
                confidence=confidence,
            )
        )
    return tuple(lines)


def _torso_lines(
    frame_by_index: Mapping[int, PoseFrame],
    evidence_frames: Sequence[int],
    metric_name: str,
    severity: str,
    confidence: float,
    *,
    label: str,
    style: Literal["solid", "dashed", "reference"] = "solid",
) -> tuple[EvaluationOverlayLine, ...]:
    lines: list[EvaluationOverlayLine] = []
    for frame_index in evidence_frames:
        frame = frame_by_index.get(frame_index)
        if frame is None:
            continue
        hip = _midpoint(frame, PoseKeypointName.LEFT_HIP, PoseKeypointName.RIGHT_HIP)
        shoulder = _midpoint(
            frame,
            PoseKeypointName.LEFT_SHOULDER,
            PoseKeypointName.RIGHT_SHOULDER,
        )
        if hip is None or shoulder is None:
            continue
        lines.append(
            _line(
                metric_name=metric_name,
                phase=_phase_for_frame(frame_index, metric_name),
                frame_index=frame_index,
                start=hip.point,
                end=shoulder.point,
                start_keypoint_name=None,
                end_keypoint_name=None,
                label=label,
                severity=severity,
                confidence=min(confidence, hip.confidence, shoulder.confidence),
                style=style,
            )
        )
    return tuple(lines)


def _grip_loading_lines(
    frame_by_index: Mapping[int, PoseFrame],
    evidence_frames: Sequence[int],
    rear_side: BodySide,
    metric_name: str,
    severity: str,
    confidence: float,
) -> tuple[EvaluationOverlayLine, ...]:
    lines: list[EvaluationOverlayLine] = []
    rear_ankle_name = side_keypoint(rear_side, "ankle")
    for frame_index in evidence_frames:
        frame = frame_by_index.get(frame_index)
        if frame is None:
            continue
        grip = _grip(frame)
        rear_ankle = frame.get(rear_ankle_name)
        if grip is None or rear_ankle is None:
            continue
        lines.append(
            _line(
                metric_name=metric_name,
                phase=SwingPhase.SETUP.value,
                frame_index=frame_index,
                start=rear_ankle.point,
                end=grip.point,
                start_keypoint_name=rear_ankle_name.value,
                end_keypoint_name=None,
                label="Grip load",
                severity=severity,
                confidence=min(confidence, grip.confidence, rear_ankle.confidence),
                style="dashed",
            )
        )
    return tuple(lines)


def _rear_knee_sway_lines(
    frame_by_index: Mapping[int, PoseFrame],
    evidence_frames: Sequence[int],
    sides: NormalizedBodySides,
    metric_name: str,
    severity: str,
    confidence: float,
) -> tuple[EvaluationOverlayLine, ...]:
    if len(evidence_frames) < 2:
        return ()
    setup = frame_by_index.get(evidence_frames[0])
    stride = frame_by_index.get(evidence_frames[-1])
    if setup is None or stride is None:
        return ()
    rear_ankle_name = side_keypoint(sides.rear, "ankle")
    rear_knee_name = side_keypoint(sides.rear, "knee")
    setup_rear_ankle = setup.get(rear_ankle_name)
    stride_rear_knee = stride.get(rear_knee_name)
    if setup_rear_ankle is None or stride_rear_knee is None:
        return ()
    return (
        _line(
            metric_name=metric_name,
            phase=SwingPhase.STRIDE.value,
            frame_index=stride.frame_index,
            start=setup_rear_ankle.point,
            end=stride_rear_knee.point,
            start_keypoint_name=rear_ankle_name.value,
            end_keypoint_name=rear_knee_name.value,
            label="Rear knee sway",
            severity=severity,
            confidence=min(confidence, setup_rear_ankle.confidence, stride_rear_knee.confidence),
            style="dashed",
        ),
    )


def _head_translation_lines(
    frame_by_index: Mapping[int, PoseFrame],
    evidence_frames: Sequence[int],
    metric_name: str,
    severity: str,
    confidence: float,
) -> tuple[EvaluationOverlayLine, ...]:
    if len(evidence_frames) < 2:
        return ()
    setup = frame_by_index.get(evidence_frames[0])
    impact = frame_by_index.get(evidence_frames[-1])
    if setup is None or impact is None:
        return ()
    setup_head = _head(setup)
    impact_head = _head(impact)
    if setup_head is None or impact_head is None:
        return ()
    return (
        _line(
            metric_name=metric_name,
            phase=SwingPhase.IMPACT.value,
            frame_index=impact.frame_index,
            start=setup_head.point,
            end=impact_head.point,
            start_keypoint_name=None,
            end_keypoint_name=None,
            label="Head drift",
            severity=severity,
            confidence=min(confidence, setup_head.confidence, impact_head.confidence),
            style="dashed",
        ),
    )


def _early_connection_lines(
    frame_by_index: Mapping[int, PoseFrame],
    evidence_frames: Sequence[int],
    lead_side: BodySide,
    metric_name: str,
    severity: str,
    confidence: float,
) -> tuple[EvaluationOverlayLine, ...]:
    lines: list[EvaluationOverlayLine] = []
    shoulder_name = side_keypoint(lead_side, "shoulder")
    wrist_name = side_keypoint(lead_side, "wrist")
    for frame_index in evidence_frames:
        frame = frame_by_index.get(frame_index)
        if frame is None:
            continue
        lines.extend(
            _line_from_keypoints(
                frame,
                shoulder_name,
                wrist_name,
                metric_name=metric_name,
                label="Connection",
                severity=severity,
                confidence=confidence,
            )
        )
    return tuple(lines)


def _lead_knee_blocking_lines(
    frame_by_index: Mapping[int, PoseFrame],
    evidence_frames: Sequence[int],
    lead_side: BodySide,
    metric_name: str,
    severity: str,
    confidence: float,
) -> tuple[EvaluationOverlayLine, ...]:
    lines: list[EvaluationOverlayLine] = []
    hip_name = side_keypoint(lead_side, "hip")
    knee_name = side_keypoint(lead_side, "knee")
    ankle_name = side_keypoint(lead_side, "ankle")
    for frame_index in evidence_frames:
        frame = frame_by_index.get(frame_index)
        if frame is None:
            continue
        lines.extend(
            _line_from_keypoints(
                frame,
                hip_name,
                knee_name,
                metric_name=metric_name,
                label="Lead block",
                severity=severity,
                confidence=confidence,
            )
        )
        lines.extend(
            _line_from_keypoints(
                frame,
                knee_name,
                ankle_name,
                metric_name=metric_name,
                label="Lead block",
                severity=severity,
                confidence=confidence,
            )
        )
    return tuple(lines)


def _hip_shoulder_lines(
    frame_by_index: Mapping[int, PoseFrame],
    evidence_frames: Sequence[int],
    metric_name: str,
    severity: str,
    confidence: float,
) -> tuple[EvaluationOverlayLine, ...]:
    lines: list[EvaluationOverlayLine] = []
    for frame_index in evidence_frames:
        frame = frame_by_index.get(frame_index)
        if frame is None:
            continue
        for start_name, end_name, label in (
            (PoseKeypointName.RIGHT_HIP, PoseKeypointName.LEFT_HIP, "Hip axis"),
            (
                PoseKeypointName.RIGHT_SHOULDER,
                PoseKeypointName.LEFT_SHOULDER,
                "Shoulder axis",
            ),
        ):
            lines.extend(
                _line_from_keypoints(
                    frame,
                    start_name,
                    end_name,
                    metric_name=metric_name,
                    label=label,
                    severity=severity,
                    confidence=confidence,
                    style="reference",
                )
            )
    return tuple(lines)


def _attack_angle_lines(
    frame_by_index: Mapping[int, PoseFrame],
    evidence_frames: Sequence[int],
    metric_name: str,
    severity: str,
    confidence: float,
    *,
    fallback: bool,
) -> tuple[EvaluationOverlayLine, ...]:
    if not evidence_frames:
        return ()
    impact = frame_by_index.get(evidence_frames[-1])
    if impact is None:
        return ()
    grip = _grip(impact)
    bat_name = PoseKeypointName.BAT_TIP
    bat = impact.get(bat_name)
    if bat is None:
        bat_name = PoseKeypointName.BAT_BARREL
        bat = impact.get(bat_name)
    if grip is not None and bat is not None:
        return (
            _line(
                metric_name=metric_name,
                phase=SwingPhase.IMPACT.value,
                frame_index=impact.frame_index,
                start=grip.point,
                end=bat.point,
                start_keypoint_name=None,
                end_keypoint_name=bat_name.value,
                label="Attack angle",
                severity=severity,
                confidence=min(confidence, grip.confidence, bat.confidence),
                style="solid",
            ),
        )
    if len(evidence_frames) < 2:
        return ()
    start_frame = frame_by_index.get(evidence_frames[0])
    if start_frame is None:
        return ()
    grip_start = _grip(start_frame)
    grip_end = _grip(impact)
    if grip_start is None or grip_end is None:
        return ()
    line_confidence = min(confidence, grip_start.confidence, grip_end.confidence, 0.45)
    return (
        _line(
            metric_name=metric_name,
            phase=SwingPhase.IMPACT.value,
            frame_index=impact.frame_index,
            start=grip_start.point,
            end=grip_end.point,
            start_keypoint_name=None,
            end_keypoint_name=None,
            label="Grip path",
            severity=severity,
            confidence=line_confidence,
            style="dashed" if fallback else "solid",
            color_role="low_confidence" if fallback or line_confidence < 0.5 else None,
        ),
    )


def _follow_through_lines(
    frame_by_index: Mapping[int, PoseFrame],
    evidence_frames: Sequence[int],
    metric_name: str,
    severity: str,
    confidence: float,
) -> tuple[EvaluationOverlayLine, ...]:
    if len(evidence_frames) < 2:
        return ()
    impact = frame_by_index.get(evidence_frames[0])
    follow = frame_by_index.get(evidence_frames[-1])
    if impact is None or follow is None:
        return ()
    lines: list[EvaluationOverlayLine] = []
    lines.extend(
        _torso_lines(
            frame_by_index,
            (follow.frame_index,),
            metric_name,
            severity,
            confidence,
            label="Finish posture",
            style="reference",
        )
    )
    impact_head = _head(impact)
    follow_head = _head(follow)
    if impact_head is not None and follow_head is not None:
        lines.append(
            _line(
                metric_name=metric_name,
                phase=SwingPhase.FOLLOW_THROUGH.value,
                frame_index=follow.frame_index,
                start=impact_head.point,
                end=follow_head.point,
                start_keypoint_name=None,
                end_keypoint_name=None,
                label="Finish balance",
                severity=severity,
                confidence=min(confidence, impact_head.confidence, follow_head.confidence),
                style="dashed",
            )
        )
    return tuple(lines)


def _line_from_keypoints(
    frame: PoseFrame,
    start_name: PoseKeypointName,
    end_name: PoseKeypointName,
    *,
    metric_name: str,
    label: str,
    severity: str,
    confidence: float,
    style: Literal["solid", "dashed", "reference"] = "solid",
) -> tuple[EvaluationOverlayLine, ...]:
    start = frame.get(start_name)
    end = frame.get(end_name)
    if start is None or end is None:
        return ()
    return (
        _line(
            metric_name=metric_name,
            phase=_phase_for_frame(frame.frame_index, metric_name),
            frame_index=frame.frame_index,
            start=start.point,
            end=end.point,
            start_keypoint_name=start_name.value,
            end_keypoint_name=end_name.value,
            label=label,
            severity=severity,
            confidence=min(confidence, start.confidence, end.confidence),
            style=style,
        ),
    )


def _line(
    *,
    metric_name: str,
    phase: str,
    frame_index: int,
    start: Point2D,
    end: Point2D,
    start_keypoint_name: str | None,
    end_keypoint_name: str | None,
    label: str,
    severity: str,
    confidence: float,
    style: Literal["solid", "dashed", "reference"],
    color_role: Literal["good", "warning", "severe", "neutral", "low_confidence"] | None = None,
) -> EvaluationOverlayLine:
    bounded_confidence = max(0.0, min(1.0, confidence))
    return EvaluationOverlayLine(
        metric_name=metric_name,
        phase=phase,
        frame_index=frame_index,
        start_keypoint_name=start_keypoint_name,
        end_keypoint_name=end_keypoint_name,
        start=EvaluationOverlayPoint(x=start.x, y=start.y),
        end=EvaluationOverlayPoint(x=end.x, y=end.y),
        label=label,
        severity=severity,
        confidence=round(bounded_confidence, 3),
        style=style,
        color_role=color_role or _color_role(severity, bounded_confidence),
    )


def _color_role(
    severity: str,
    confidence: float,
) -> Literal["good", "warning", "severe", "neutral", "low_confidence"]:
    if confidence < 0.5:
        return "low_confidence"
    if severity == "good":
        return "good"
    if severity == "warning":
        return "warning"
    if severity == "severe":
        return "severe"
    return "neutral"


def _phase_for_frame(frame_index: int, metric_name: str) -> str:
    if metric_name in {
        SwingMetricName.NORMALIZED_STANCE_WIDTH.value,
        SwingMetricName.TORSO_FORWARD_TILT.value,
        SwingMetricName.GRIP_LOADING_VECTOR.value,
    }:
        return SwingPhase.SETUP.value
    if metric_name in {
        SwingMetricName.REAR_KNEE_SWAY.value,
        SwingMetricName.HEAD_TRANSLATION_RATIO.value,
    }:
        return SwingPhase.STRIDE.value
    if metric_name in {
        SwingMetricName.EARLY_CONNECTION_ANGLE.value,
        SwingMetricName.HIP_SHOULDER_SEPARATION_TIMING.value,
    }:
        return SwingPhase.FOOT_STRIKE.value
    if metric_name in {
        SwingMetricName.TORSO_TILT_PRESERVATION.value,
        SwingMetricName.LEAD_KNEE_BLOCKING_INDEX.value,
        SwingMetricName.ESTIMATED_ATTACK_ANGLE.value,
    }:
        return SwingPhase.IMPACT.value
    if metric_name == SwingMetricName.FOLLOW_THROUGH_POSTURE_BALANCE.value:
        return SwingPhase.FOLLOW_THROUGH.value
    return str(frame_index)


def _midpoint(
    frame: PoseFrame,
    first_name: PoseKeypointName,
    second_name: PoseKeypointName,
) -> PoseKeypoint | None:
    first = frame.get(first_name)
    second = frame.get(second_name)
    if first is None or second is None:
        return None
    return PoseKeypoint(
        point=Point2D(
            x=(first.point.x + second.point.x) / 2.0,
            y=(first.point.y + second.point.y) / 2.0,
        ),
        confidence=min(first.confidence, second.confidence),
    )


def _head(frame: PoseFrame) -> PoseKeypoint | None:
    for name in (PoseKeypointName.NOSE, PoseKeypointName.LEFT_EAR, PoseKeypointName.RIGHT_EAR):
        keypoint = frame.get(name)
        if keypoint is not None:
            return keypoint
    return None


def _grip(frame: PoseFrame) -> PoseKeypoint | None:
    left = frame.get(PoseKeypointName.LEFT_WRIST)
    right = frame.get(PoseKeypointName.RIGHT_WRIST)
    if left is None or right is None:
        return left or right
    return PoseKeypoint(
        point=Point2D(
            x=(left.point.x + right.point.x) / 2.0,
            y=(left.point.y + right.point.y) / 2.0,
        ),
        confidence=min(left.confidence, right.confidence),
    )
