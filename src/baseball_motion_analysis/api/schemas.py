"""API schemas for browser-safe API adapters."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from baseball_motion_analysis.analysis import SwingAnalysisResult
from baseball_motion_analysis.app.swing_services import (
    AnalyzeSwingVideoResponse,
    PoseOverlayFrame,
    SwingEventWindow,
    SwingVideoSamplingDiagnostics,
)
from baseball_motion_analysis.feedback import SwingFeedbackReport
from baseball_motion_analysis.motion import SwingPhase, SwingPhaseFrames
from baseball_motion_analysis.pose import PoseDebugDiagnostics, PoseFrame, PoseQualityDiagnostics
from baseball_motion_analysis.storage.models import MediaRecord, VideoReplayManifest


class ErrorDetail(BaseModel):
    """Structured browser-safe error details."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Structured browser-safe error response."""

    error: ErrorDetail


class DeleteMediaResponse(BaseModel):
    """Response returned after deleting one uploaded media item."""

    media_id: str
    deleted: bool


class MediaRecordResponse(BaseModel):
    """Public media record response without internal storage paths."""

    model_config = ConfigDict(from_attributes=True)

    media_id: str
    source_type: str
    display_name: str
    file_extension: str
    file_size_bytes: int
    created_at: datetime
    width: int
    height: int
    fps: float | None
    total_frame_count: int | None
    duration_seconds: float | None
    status: str
    error_code: str | None
    error_message: str | None

    @classmethod
    def from_record(cls, record: MediaRecord) -> MediaRecordResponse:
        """Create a public response from a storage record."""
        return cls(
            media_id=record.media_id,
            source_type=record.source_type,
            display_name=record.display_name,
            file_extension=record.file_extension,
            file_size_bytes=record.file_size_bytes,
            created_at=record.created_at,
            width=record.width,
            height=record.height,
            fps=record.fps,
            total_frame_count=record.total_frame_count,
            duration_seconds=record.duration_seconds,
            status=record.status.value,
            error_code=record.error_code,
            error_message=record.error_message,
        )


class VideoReplayManifestResponse(BaseModel):
    """Public replay manifest response."""

    media_id: str
    display_name: str
    content_url: str
    duration_seconds: float | None
    width: int
    height: int
    fps: float | None
    browser_playback_status: Literal[
        "supported",
        "possibly_unsupported",
        "unsupported",
        "missing",
    ]

    @classmethod
    def from_manifest(cls, manifest: VideoReplayManifest) -> VideoReplayManifestResponse:
        """Create a public response from a replay manifest."""
        return cls(
            media_id=manifest.media_id,
            display_name=manifest.display_name,
            content_url=manifest.content_url,
            duration_seconds=manifest.duration_seconds,
            width=manifest.width,
            height=manifest.height,
            fps=manifest.fps,
            browser_playback_status=manifest.browser_playback_status,  # type: ignore[arg-type]
        )


class PoseKeypointPayload(BaseModel):
    """Public pose keypoint payload accepted by analysis adapters."""

    x: float
    y: float
    confidence: float = 1.0
    interpolated: bool = False
    smoothed: bool = False
    out_of_frame: bool = False


class PoseFramePayload(BaseModel):
    """Public pose frame payload accepted by analysis adapters."""

    frame_index: int
    keypoints: dict[str, PoseKeypointPayload]
    timestamp_seconds: float | None = None


class SwingAnalysisRequestPayload(BaseModel):
    """Public swing analysis request payload."""

    frames: list[PoseFramePayload]
    handedness: str = "unknown"
    phase_frames: dict[str, int] | None = None


class SwingPhaseFramesResponse(BaseModel):
    """Swing phase frame indexes returned to browser clients."""

    setup: int
    stride: int
    foot_strike: int
    impact: int
    follow_through: int
    confidence: float
    limitations: tuple[str, ...]
    phase_confidences: dict[str, float]
    detection_methods: dict[str, str]

    @classmethod
    def from_phases(cls, phases: SwingPhaseFrames) -> SwingPhaseFramesResponse:
        """Create a response from swing phase frames."""
        return cls(
            setup=phases.setup,
            stride=phases.stride,
            foot_strike=phases.foot_strike,
            impact=phases.impact,
            follow_through=phases.follow_through,
            confidence=phases.confidence,
            limitations=phases.limitations,
            phase_confidences={phase.value: phases.confidence_for(phase) for phase in SwingPhase},
            detection_methods={
                phase.value: phases.detection_method_for(phase) for phase in SwingPhase
            },
        )


class SwingPhaseScoreResponse(BaseModel):
    """Browser-safe phase score response."""

    phase: str
    score: float
    weight: float
    confidence: float


class SwingMetricResultResponse(BaseModel):
    """Browser-safe swing metric response."""

    name: str
    value: float | None
    target_min: float | None
    target_max: float | None
    severity: str
    confidence: float
    evidence_frames: tuple[int, ...]
    deduction: float
    message: str
    limitations: tuple[str, ...]


class SwingFaultResultResponse(BaseModel):
    """Browser-safe swing fault response."""

    fault_type: str
    phase: str
    severity: str
    confidence: float
    evidence: str
    evidence_frames: tuple[int, ...]


class SwingAnalysisResultResponse(BaseModel):
    """Browser-safe swing analysis response."""

    overall_score: float
    phase_scores: tuple[SwingPhaseScoreResponse, ...]
    metrics: tuple[SwingMetricResultResponse, ...]
    detected_faults: tuple[SwingFaultResultResponse, ...]
    good_points: tuple[str, ...]
    improvement_priorities: tuple[str, ...]
    confidence: float
    limitations: tuple[str, ...]
    phases: SwingPhaseFramesResponse
    handedness: str

    @classmethod
    def from_result(cls, result: SwingAnalysisResult) -> SwingAnalysisResultResponse:
        """Create a public response from an analysis result."""
        return cls(
            overall_score=result.overall_score,
            phase_scores=tuple(
                SwingPhaseScoreResponse(
                    phase=score.phase.value,
                    score=score.score,
                    weight=score.weight,
                    confidence=score.confidence,
                )
                for score in result.phase_scores
            ),
            metrics=tuple(
                SwingMetricResultResponse(
                    name=metric.name.value,
                    value=metric.value,
                    target_min=metric.target_min,
                    target_max=metric.target_max,
                    severity=metric.severity.value,
                    confidence=metric.confidence,
                    evidence_frames=metric.evidence_frames,
                    deduction=metric.deduction,
                    message=metric.message,
                    limitations=metric.limitations,
                )
                for metric in result.metrics
            ),
            detected_faults=tuple(
                SwingFaultResultResponse(
                    fault_type=fault.fault_type.value,
                    phase=fault.phase.value,
                    severity=fault.severity.value,
                    confidence=fault.confidence,
                    evidence=fault.evidence,
                    evidence_frames=fault.evidence_frames,
                )
                for fault in result.detected_faults
            ),
            good_points=result.good_points,
            improvement_priorities=result.improvement_priorities,
            confidence=result.confidence,
            limitations=result.limitations,
            phases=SwingPhaseFramesResponse.from_phases(result.phases),
            handedness=result.handedness.value,
        )


class SwingFeedbackResponse(BaseModel):
    """Browser-safe swing feedback response."""

    summary: str
    good_points: tuple[str, ...]
    improvement_points: tuple[str, ...]
    drills_or_suggestions: tuple[str, ...]
    confidence: float
    limitations: tuple[str, ...]

    @classmethod
    def from_report(cls, report: SwingFeedbackReport) -> SwingFeedbackResponse:
        """Create a public response from a feedback report."""
        return cls(
            summary=report.summary,
            good_points=report.good_points,
            improvement_points=report.improvement_points,
            drills_or_suggestions=report.drills_or_suggestions,
            confidence=report.confidence,
            limitations=report.limitations,
        )


class SwingAnalysisResponse(BaseModel):
    """Public swing analysis API response."""

    analysis: SwingAnalysisResultResponse
    feedback: SwingFeedbackResponse


class SwingVideoSamplingRequest(BaseModel):
    """Optional browser sampling request for video analysis."""

    quality_mode: Literal["faster", "balanced", "higher_accuracy"] = "higher_accuracy"
    target_fps: float | None = None
    max_frame_count: int | None = None
    full_frame_max_frame_count: int | None = None


class SwingVideoAnalysisRequestPayload(BaseModel):
    """Video-driven swing analysis request."""

    media_id: str
    handedness: str = "unknown"
    sampling: SwingVideoSamplingRequest | None = None
    pose_mode: Literal["normal", "notebook_parity"] = "normal"
    overlay_source: Literal["stabilized", "raw"] = "stabilized"


class SwingEventResponse(BaseModel):
    """Detected swing event response."""

    phase: str
    frame_index: int
    start_frame_index: int
    end_frame_index: int
    confidence: float
    label: str
    detection_method: str

    @classmethod
    def from_event(cls, event: SwingEventWindow) -> SwingEventResponse:
        """Create a public response from a swing event."""
        return cls(
            phase=event.phase.value,
            frame_index=event.frame_index,
            start_frame_index=event.start_frame_index,
            end_frame_index=event.end_frame_index,
            confidence=event.confidence,
            label=event.label,
            detection_method=event.detection_method,
        )


class PoseQualityDiagnosticsResponse(BaseModel):
    """Browser-safe pose-quality diagnostics."""

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

    @classmethod
    def from_diagnostics(
        cls,
        diagnostics: PoseQualityDiagnostics,
    ) -> PoseQualityDiagnosticsResponse:
        """Create a public response from pose-quality diagnostics."""
        return cls(
            total_frame_count=diagnostics.total_frame_count,
            detected_pose_frame_count=diagnostics.detected_pose_frame_count,
            detected_pose_frame_ratio=diagnostics.detected_pose_frame_ratio,
            required_landmark_coverage=diagnostics.required_landmark_coverage,
            mean_confidence=diagnostics.mean_confidence,
            min_confidence=diagnostics.min_confidence,
            smoothed_frame_count=diagnostics.smoothed_frame_count,
            interpolated_frame_count=diagnostics.interpolated_frame_count,
            rejected_outlier_count=diagnostics.rejected_outlier_count,
            out_of_frame_landmark_count=diagnostics.out_of_frame_landmark_count,
        )


class SwingVideoSamplingDiagnosticsResponse(BaseModel):
    """Browser-safe sampling diagnostics."""

    quality_mode: str
    source_fps: float | None
    target_fps: float | None
    effective_fps: float | None
    sampled_frame_count: int
    total_frame_count: int | None
    max_frame_count: int
    cap_applied: bool
    full_frame_sampling: bool

    @classmethod
    def from_diagnostics(
        cls,
        diagnostics: SwingVideoSamplingDiagnostics,
    ) -> SwingVideoSamplingDiagnosticsResponse:
        """Create a public response from sampling diagnostics."""
        return cls(
            quality_mode=diagnostics.quality_mode,
            source_fps=diagnostics.source_fps,
            target_fps=diagnostics.target_fps,
            effective_fps=diagnostics.effective_fps,
            sampled_frame_count=diagnostics.sampled_frame_count,
            total_frame_count=diagnostics.total_frame_count,
            max_frame_count=diagnostics.max_frame_count,
            cap_applied=diagnostics.cap_applied,
            full_frame_sampling=diagnostics.full_frame_sampling,
        )


class PoseFrameResponse(BaseModel):
    """Browser-safe pose frame response."""

    frame_index: int
    timestamp_seconds: float | None
    keypoints: dict[str, PoseKeypointPayload]

    @classmethod
    def from_pose_frame(cls, frame: PoseFrame) -> PoseFrameResponse:
        """Create a public response from a pose frame."""
        return cls(
            frame_index=frame.frame_index,
            timestamp_seconds=frame.timestamp_seconds,
            keypoints={
                name.value: PoseKeypointPayload(
                    x=keypoint.point.x,
                    y=keypoint.point.y,
                    confidence=keypoint.confidence,
                    interpolated=keypoint.interpolated,
                    smoothed=keypoint.smoothed,
                    out_of_frame=keypoint.out_of_frame,
                )
                for name, keypoint in frame.keypoints.items()
            },
        )


class PoseOverlayKeypointResponse(BaseModel):
    """Browser-safe overlay keypoint response."""

    name: str
    x: float
    y: float
    confidence: float
    category: str
    label: str | None
    interpolated: bool
    smoothed: bool
    out_of_frame: bool


class PoseOverlayFrameResponse(BaseModel):
    """Browser-safe overlay frame response."""

    frame_index: int
    timestamp_seconds: float | None
    keypoints: tuple[PoseOverlayKeypointResponse, ...]
    is_event_frame: bool
    source: Literal["stabilized", "raw"]

    @classmethod
    def from_overlay_frame(cls, frame: PoseOverlayFrame) -> PoseOverlayFrameResponse:
        """Create a public response from overlay frame data."""
        return cls(
            frame_index=frame.frame_index,
            timestamp_seconds=frame.timestamp_seconds,
            keypoints=tuple(
                PoseOverlayKeypointResponse(
                    name=keypoint.name,
                    x=keypoint.x,
                    y=keypoint.y,
                    confidence=keypoint.confidence,
                    category=keypoint.category,
                    label=keypoint.label,
                    interpolated=keypoint.interpolated,
                    smoothed=keypoint.smoothed,
                    out_of_frame=keypoint.out_of_frame,
                )
                for keypoint in frame.keypoints
            ),
            is_event_frame=frame.is_event_frame,
            source=frame.source,
        )


class PoseDebugDiagnosticsResponse(BaseModel):
    """Browser-safe pose debug diagnostics."""

    running_mode: str
    processing_mode: str
    requested_num_poses: int
    player_selection_strategy: str
    selected_candidate_indexes: tuple[int, ...]
    mean_stabilization_delta_ratio: float | None
    max_stabilization_delta_ratio: float | None
    stabilization_changed_keypoint_count: int

    @classmethod
    def from_diagnostics(cls, diagnostics: PoseDebugDiagnostics) -> PoseDebugDiagnosticsResponse:
        """Create a public response from pose debug diagnostics."""
        return cls(
            running_mode=diagnostics.running_mode,
            processing_mode=diagnostics.processing_mode,
            requested_num_poses=diagnostics.requested_num_poses,
            player_selection_strategy=diagnostics.player_selection_strategy,
            selected_candidate_indexes=diagnostics.selected_candidate_indexes,
            mean_stabilization_delta_ratio=diagnostics.mean_stabilization_delta_ratio,
            max_stabilization_delta_ratio=diagnostics.max_stabilization_delta_ratio,
            stabilization_changed_keypoint_count=diagnostics.stabilization_changed_keypoint_count,
        )


class SwingVideoAnalysisResponse(BaseModel):
    """Public video-driven swing analysis response."""

    analysis: SwingAnalysisResultResponse
    feedback: SwingFeedbackResponse
    pose: tuple[PoseFrameResponse, ...]
    raw_pose: tuple[PoseFrameResponse, ...]
    events: tuple[SwingEventResponse, ...]
    overlay: tuple[PoseOverlayFrameResponse, ...]
    raw_overlay: tuple[PoseOverlayFrameResponse, ...]
    limitations: tuple[str, ...]
    pose_cache_hit: bool
    pose_diagnostics: PoseQualityDiagnosticsResponse | None
    raw_pose_diagnostics: PoseQualityDiagnosticsResponse | None
    pose_debug_diagnostics: PoseDebugDiagnosticsResponse | None
    sampling_diagnostics: SwingVideoSamplingDiagnosticsResponse

    @classmethod
    def from_response(cls, response: AnalyzeSwingVideoResponse) -> SwingVideoAnalysisResponse:
        """Create a public response from video-driven app-service output."""
        return cls(
            analysis=SwingAnalysisResultResponse.from_result(response.analysis),
            feedback=SwingFeedbackResponse.from_report(response.feedback),
            pose=tuple(PoseFrameResponse.from_pose_frame(frame) for frame in response.pose_frames),
            raw_pose=tuple(
                PoseFrameResponse.from_pose_frame(frame) for frame in response.raw_pose_frames
            ),
            events=tuple(SwingEventResponse.from_event(event) for event in response.events),
            overlay=tuple(
                PoseOverlayFrameResponse.from_overlay_frame(frame)
                for frame in response.overlay_frames
            ),
            raw_overlay=tuple(
                PoseOverlayFrameResponse.from_overlay_frame(frame)
                for frame in response.raw_overlay_frames
            ),
            limitations=response.limitations,
            pose_cache_hit=response.pose_cache_hit,
            pose_diagnostics=(
                PoseQualityDiagnosticsResponse.from_diagnostics(response.pose_diagnostics)
                if response.pose_diagnostics is not None
                else None
            ),
            raw_pose_diagnostics=(
                PoseQualityDiagnosticsResponse.from_diagnostics(response.raw_pose_diagnostics)
                if response.raw_pose_diagnostics is not None
                else None
            ),
            pose_debug_diagnostics=(
                PoseDebugDiagnosticsResponse.from_diagnostics(response.pose_debug_diagnostics)
                if response.pose_debug_diagnostics is not None
                else None
            ),
            sampling_diagnostics=SwingVideoSamplingDiagnosticsResponse.from_diagnostics(
                response.sampling_diagnostics
            ),
        )
