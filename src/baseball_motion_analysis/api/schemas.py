"""API schemas for browser-safe API adapters."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from baseball_motion_analysis.analysis import SwingAnalysisResult
from baseball_motion_analysis.app.swing_services import (
    AnalyzeSwingVideoResponse,
    EvaluationOverlayLine,
    PoseOverlayFrame,
    SwingEventWindow,
    SwingScoringEvidenceDiagnostics,
    SwingScoringEvidenceIssue,
    SwingVideoSamplingDiagnostics,
)
from baseball_motion_analysis.feedback import SwingFeedbackReport
from baseball_motion_analysis.motion import (
    SwingActiveWindowDiagnostics,
    SwingFrameQualityDiagnostics,
    SwingPhase,
    SwingPhaseFrames,
)
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
    impact_detection_policy: Literal[
        "body_pose_estimated",
        "require_ball_contact",
        "skip_without_ball",
    ] = "body_pose_estimated"
    frame_width: int | None = None
    frame_height: int | None = None


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
    fallback_reasons: dict[str, str | None]
    event_statuses: dict[str, str]

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
            fallback_reasons={
                phase.value: phases.fallback_reason_for(phase) for phase in SwingPhase
            },
            event_statuses={phase.value: phases.status_for(phase).value for phase in SwingPhase},
        )


class SwingPhaseScoreResponse(BaseModel):
    """Browser-safe phase score response."""

    phase: str
    score: float
    weight: float
    confidence: float
    metric_deduction: float
    fault_deduction: float


class SwingMetricResultResponse(BaseModel):
    """Browser-safe swing metric response."""

    name: str
    value: float | None
    target_min: float | None
    target_max: float | None
    unit: str
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
    deduction: float
    linked_metrics: tuple[str, ...]
    evidence: str
    evidence_frames: tuple[int, ...]


class SwingAnalysisResultResponse(BaseModel):
    """Browser-safe swing analysis response."""

    methodology_version: str
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
            methodology_version=result.methodology_version,
            overall_score=result.overall_score,
            phase_scores=tuple(
                SwingPhaseScoreResponse(
                    phase=score.phase.value,
                    score=score.score,
                    weight=score.weight,
                    confidence=score.confidence,
                    metric_deduction=score.metric_deduction,
                    fault_deduction=score.fault_deduction,
                )
                for score in result.phase_scores
            ),
            metrics=tuple(
                SwingMetricResultResponse(
                    name=metric.name.value,
                    value=metric.value,
                    target_min=metric.target_min,
                    target_max=metric.target_max,
                    unit=metric.unit,
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
                    deduction=fault.deduction,
                    linked_metrics=tuple(metric.value for metric in fault.linked_metrics),
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
    impact_detection_policy: Literal[
        "body_pose_estimated",
        "require_ball_contact",
        "skip_without_ball",
    ] = "body_pose_estimated"


class SwingEventResponse(BaseModel):
    """Detected swing event response."""

    phase: str
    frame_index: int
    start_frame_index: int
    end_frame_index: int
    confidence: float
    label: str
    detection_method: str
    status: str
    fallback_reason: str | None = None
    is_visible: bool = True
    is_overlay_event: bool = True

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
            status=event.status.value,
            fallback_reason=event.fallback_reason,
            is_visible=event.is_visible,
            is_overlay_event=event.is_overlay_event,
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
    source_duration_seconds: float | None
    analyzed_start_seconds: float | None
    analyzed_end_seconds: float | None
    analyzed_duration_seconds: float | None
    max_frame_count: int
    cap_applied: bool
    full_frame_sampling: bool
    temporal_coverage_complete: bool
    timestamp_source: str
    timestamp_fallback_reason: str | None = None
    timestamp_repair_count: int
    limitations: tuple[str, ...]

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
            source_duration_seconds=diagnostics.source_duration_seconds,
            analyzed_start_seconds=diagnostics.analyzed_start_seconds,
            analyzed_end_seconds=diagnostics.analyzed_end_seconds,
            analyzed_duration_seconds=diagnostics.analyzed_duration_seconds,
            max_frame_count=diagnostics.max_frame_count,
            cap_applied=diagnostics.cap_applied,
            full_frame_sampling=diagnostics.full_frame_sampling,
            temporal_coverage_complete=diagnostics.temporal_coverage_complete,
            timestamp_source=diagnostics.timestamp_source,
            timestamp_fallback_reason=diagnostics.timestamp_fallback_reason,
            timestamp_repair_count=diagnostics.timestamp_repair_count,
            limitations=diagnostics.limitations,
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


class EvaluationOverlayPointResponse(BaseModel):
    """Browser-safe normalized point for an evaluation overlay line."""

    x: float
    y: float


class EvaluationOverlayLineResponse(BaseModel):
    """Browser-safe swing evaluation overlay line response."""

    metric_name: str
    phase: str
    frame_index: int
    start_keypoint_name: str | None
    end_keypoint_name: str | None
    start: EvaluationOverlayPointResponse
    end: EvaluationOverlayPointResponse
    label: str
    severity: str
    confidence: float
    style: Literal["solid", "dashed", "reference"]
    color_role: Literal["good", "warning", "severe", "neutral", "low_confidence"]

    @classmethod
    def from_overlay_line(
        cls,
        line: EvaluationOverlayLine,
    ) -> EvaluationOverlayLineResponse:
        """Create a public response from evaluation overlay line data."""
        return cls(
            metric_name=line.metric_name,
            phase=line.phase,
            frame_index=line.frame_index,
            start_keypoint_name=line.start_keypoint_name,
            end_keypoint_name=line.end_keypoint_name,
            start=EvaluationOverlayPointResponse(x=line.start.x, y=line.start.y),
            end=EvaluationOverlayPointResponse(x=line.end.x, y=line.end.y),
            label=line.label,
            severity=line.severity,
            confidence=line.confidence,
            style=line.style,
            color_role=line.color_role,
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
    candidate_switch_count: int
    candidate_ambiguity_count: int

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
            candidate_switch_count=diagnostics.candidate_switch_count,
            candidate_ambiguity_count=diagnostics.candidate_ambiguity_count,
        )


class SwingFrameQualityDiagnosticsResponse(BaseModel):
    """Browser-safe swing frame-quality diagnostics."""

    total_frame_count: int
    usable_frame_count: int
    weak_frame_count: int
    rejected_frame_count: int
    weak_frame_indexes: tuple[int, ...]
    rejected_frame_indexes: tuple[int, ...]
    reasons_by_frame: dict[int, tuple[str, ...]]

    @classmethod
    def from_diagnostics(
        cls,
        diagnostics: SwingFrameQualityDiagnostics,
    ) -> SwingFrameQualityDiagnosticsResponse:
        """Create a public response from frame-quality diagnostics."""
        return cls(
            total_frame_count=diagnostics.total_frame_count,
            usable_frame_count=diagnostics.usable_frame_count,
            weak_frame_count=diagnostics.weak_frame_count,
            rejected_frame_count=diagnostics.rejected_frame_count,
            weak_frame_indexes=diagnostics.weak_frame_indexes,
            rejected_frame_indexes=diagnostics.rejected_frame_indexes,
            reasons_by_frame=dict(diagnostics.reasons_by_frame),
        )


class SwingActiveWindowDiagnosticsResponse(BaseModel):
    """Browser-safe active swing window diagnostics."""

    start_frame_index: int
    end_frame_index: int
    peak_motion_frame_index: int
    confidence: float
    fallback_reason: str | None

    @classmethod
    def from_diagnostics(
        cls,
        diagnostics: SwingActiveWindowDiagnostics,
    ) -> SwingActiveWindowDiagnosticsResponse:
        """Create a public response from active swing window diagnostics."""
        return cls(
            start_frame_index=diagnostics.start_frame_index,
            end_frame_index=diagnostics.end_frame_index,
            peak_motion_frame_index=diagnostics.peak_motion_frame_index,
            confidence=diagnostics.confidence,
            fallback_reason=diagnostics.fallback_reason,
        )


class SwingScoringEvidenceIssueResponse(BaseModel):
    """Browser-safe scoring evidence issue."""

    metric_name: str
    evidence_frames: tuple[int, ...]
    reasons: tuple[str, ...]

    @classmethod
    def from_issue(
        cls,
        issue: SwingScoringEvidenceIssue,
    ) -> SwingScoringEvidenceIssueResponse:
        """Create a public response from one scoring evidence issue."""
        return cls(
            metric_name=issue.metric_name,
            evidence_frames=issue.evidence_frames,
            reasons=issue.reasons,
        )


class SwingScoringEvidenceDiagnosticsResponse(BaseModel):
    """Browser-safe scoring evidence diagnostics."""

    affected_metrics: tuple[SwingScoringEvidenceIssueResponse, ...]

    @classmethod
    def from_diagnostics(
        cls,
        diagnostics: SwingScoringEvidenceDiagnostics,
    ) -> SwingScoringEvidenceDiagnosticsResponse:
        """Create a public response from scoring evidence diagnostics."""
        return cls(
            affected_metrics=tuple(
                SwingScoringEvidenceIssueResponse.from_issue(issue)
                for issue in diagnostics.affected_metrics
            )
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
    evaluation_overlay: tuple[EvaluationOverlayLineResponse, ...]
    limitations: tuple[str, ...]
    pose_cache_hit: bool
    pose_diagnostics: PoseQualityDiagnosticsResponse | None
    raw_pose_diagnostics: PoseQualityDiagnosticsResponse | None
    pose_debug_diagnostics: PoseDebugDiagnosticsResponse | None
    sampling_diagnostics: SwingVideoSamplingDiagnosticsResponse
    frame_quality_diagnostics: SwingFrameQualityDiagnosticsResponse | None
    active_window_diagnostics: SwingActiveWindowDiagnosticsResponse | None
    scoring_evidence_diagnostics: SwingScoringEvidenceDiagnosticsResponse

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
            evaluation_overlay=tuple(
                EvaluationOverlayLineResponse.from_overlay_line(line)
                for line in response.evaluation_overlay
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
            frame_quality_diagnostics=(
                SwingFrameQualityDiagnosticsResponse.from_diagnostics(
                    response.frame_quality_diagnostics
                )
                if response.frame_quality_diagnostics is not None
                else None
            ),
            active_window_diagnostics=(
                SwingActiveWindowDiagnosticsResponse.from_diagnostics(
                    response.active_window_diagnostics
                )
                if response.active_window_diagnostics is not None
                else None
            ),
            scoring_evidence_diagnostics=(
                SwingScoringEvidenceDiagnosticsResponse.from_diagnostics(
                    response.scoring_evidence_diagnostics
                )
            ),
        )
