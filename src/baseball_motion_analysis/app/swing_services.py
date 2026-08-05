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
    SwingHandedness,
    SwingPhase,
    SwingPhaseFrames,
    detect_swing_phases,
)
from baseball_motion_analysis.pose import (
    MediaPipePoseEstimator,
    MediaPipePoseEstimatorConfig,
    PoseDebugDiagnostics,
    PoseEstimationError,
    PoseEstimator,
    PoseFrame,
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
class CachedPoseEstimation:
    """Cached pose frames with original limitations."""

    frames: tuple[PoseFrame, ...]
    raw_frames: tuple[PoseFrame, ...]
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

        phases = detect_swing_phases(pose_frames)
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
            )
        )
        events = _events_from_phases(phases)
        overlay_frames = _overlay_frames(pose_frames, events, source="stabilized")
        raw_overlay_frames = _overlay_frames(pose_bundle.raw_frames, events, source="raw")
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
