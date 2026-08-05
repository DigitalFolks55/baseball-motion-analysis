"""Swing analysis API adapter."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from baseball_motion_analysis.api.schemas import (
    ErrorDetail,
    ErrorResponse,
    PoseFramePayload,
    SwingAnalysisRequestPayload,
    SwingAnalysisResponse,
    SwingAnalysisResultResponse,
    SwingFeedbackResponse,
    SwingVideoAnalysisRequestPayload,
    SwingVideoAnalysisResponse,
)
from baseball_motion_analysis.app import (
    AnalyzeSwingRequest,
    AnalyzeSwingVideoRequest,
    SwingAnalysisApplicationService,
    SwingVideoAnalysisApplicationService,
    SwingVideoSamplingOptions,
)
from baseball_motion_analysis.app.media_services import (
    MediaApplicationError,
    VideoLibraryApplicationService,
    create_video_library_application_service,
)
from baseball_motion_analysis.app.swing_services import SwingVideoAnalysisError
from baseball_motion_analysis.motion import SwingHandedness, SwingPhase
from baseball_motion_analysis.pose import (
    MediaPipePoseEstimatorConfig,
    Point2D,
    PoseFrame,
    PoseKeypoint,
    PoseKeypointName,
)

router = APIRouter(prefix="/analysis/swing", tags=["analysis"])


class SwingApiRequestError(Exception):
    """Raised when a swing analysis request cannot be converted safely."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@router.post("", response_model=SwingAnalysisResponse, responses={400: {"model": ErrorResponse}})
def analyze_swing_from_pose_json(
    payload: Annotated[dict[str, Any], Body()],
) -> SwingAnalysisResponse | JSONResponse:
    """Analyze already-extracted pose keypoints through the app service."""
    try:
        request_payload = SwingAnalysisRequestPayload.model_validate(payload)
        app_request = _to_app_request(request_payload)
        response = SwingAnalysisApplicationService().analyze_pose_sequence(app_request)
    except ValidationError as exc:
        return _error_response(
            "invalid_swing_analysis_request",
            _validation_message(exc),
        )
    except (SwingApiRequestError, ValueError) as exc:
        return _error_response(
            getattr(exc, "code", "invalid_swing_analysis_request"),
            str(exc),
        )

    return SwingAnalysisResponse(
        analysis=SwingAnalysisResultResponse.from_result(response.analysis),
        feedback=SwingFeedbackResponse.from_report(response.feedback),
    )


@router.post(
    "/video",
    response_model=SwingVideoAnalysisResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def analyze_swing_from_video(
    request: Request,
    payload: Annotated[dict[str, Any], Body()],
) -> SwingVideoAnalysisResponse | JSONResponse:
    """Analyze a stored video by sampling frames and estimating pose locally."""
    try:
        request_payload = SwingVideoAnalysisRequestPayload.model_validate(payload)
        app_request = AnalyzeSwingVideoRequest(
            media_id=request_payload.media_id,
            handedness=_to_handedness(request_payload.handedness),
            sampling=_to_sampling_options(request_payload),
            pose_mode=request_payload.pose_mode,
            overlay_source=request_payload.overlay_source,
        )
        response = _swing_video_service(request).analyze_video(app_request)
    except ValidationError as exc:
        return _error_response("invalid_swing_video_analysis_request", _validation_message(exc))
    except MediaApplicationError as exc:
        status_code = 404 if exc.error_code in {"invalid_media_id", "missing_stored_file"} else 400
        return _error_response(exc.error_code, exc.message, status_code=status_code)
    except (SwingApiRequestError, SwingVideoAnalysisError, ValueError) as exc:
        return _error_response(
            getattr(exc, "error_code", getattr(exc, "code", "invalid_swing_video_analysis")),
            getattr(exc, "message", str(exc)),
        )

    return SwingVideoAnalysisResponse.from_response(response)


def _to_app_request(payload: SwingAnalysisRequestPayload) -> AnalyzeSwingRequest:
    if not payload.frames:
        raise SwingApiRequestError(
            "empty_pose_frame_list",
            "Provide at least one pose frame for swing analysis.",
        )

    return AnalyzeSwingRequest(
        frames=tuple(_to_pose_frame(frame) for frame in payload.frames),
        handedness=_to_handedness(payload.handedness),
        phase_frames=_to_phase_frames(payload.phase_frames),
    )


def _to_pose_frame(payload: PoseFramePayload) -> PoseFrame:
    if not payload.keypoints:
        raise SwingApiRequestError(
            "empty_pose_keypoints",
            f"Frame {payload.frame_index} must include at least one keypoint.",
        )

    keypoints: dict[PoseKeypointName, PoseKeypoint] = {}
    for raw_name, raw_keypoint in payload.keypoints.items():
        try:
            keypoint_name = PoseKeypointName(raw_name)
        except ValueError as exc:
            raise SwingApiRequestError(
                "unknown_pose_keypoint",
                f"Unknown pose keypoint name: {raw_name}.",
            ) from exc
        keypoints[keypoint_name] = PoseKeypoint(
            point=Point2D(x=raw_keypoint.x, y=raw_keypoint.y),
            confidence=raw_keypoint.confidence,
        )

    return PoseFrame(
        frame_index=payload.frame_index,
        keypoints=keypoints,
        timestamp_seconds=payload.timestamp_seconds,
    )


def _to_handedness(value: str) -> SwingHandedness:
    try:
        return SwingHandedness(value)
    except ValueError as exc:
        allowed = ", ".join(handedness.value for handedness in SwingHandedness)
        raise SwingApiRequestError(
            "invalid_swing_handedness",
            f"Swing handedness must be one of: {allowed}.",
        ) from exc


def _to_phase_frames(values: dict[str, int] | None) -> dict[SwingPhase, int] | None:
    if values is None:
        return None

    phase_frames: dict[SwingPhase, int] = {}
    for raw_phase, frame_index in values.items():
        try:
            phase = SwingPhase(raw_phase)
        except ValueError as exc:
            allowed = ", ".join(phase.value for phase in SwingPhase)
            raise SwingApiRequestError(
                "invalid_swing_phase",
                f"Swing phase must be one of: {allowed}.",
            ) from exc
        phase_frames[phase] = frame_index
    return phase_frames


def _to_sampling_options(payload: SwingVideoAnalysisRequestPayload) -> SwingVideoSamplingOptions:
    if payload.sampling is None:
        return SwingVideoSamplingOptions()
    default_sampling = SwingVideoSamplingOptions()
    return SwingVideoSamplingOptions(
        quality_mode=payload.sampling.quality_mode,
        target_fps=payload.sampling.target_fps,
        max_frame_count=(
            payload.sampling.max_frame_count
            if payload.sampling.max_frame_count is not None
            else default_sampling.max_frame_count
        ),
        full_frame_max_frame_count=(
            payload.sampling.full_frame_max_frame_count
            if payload.sampling.full_frame_max_frame_count is not None
            else default_sampling.full_frame_max_frame_count
        ),
    )


def _swing_video_service(request: Request) -> SwingVideoAnalysisApplicationService:
    service = getattr(request.app.state, "swing_video_analysis_service", None)
    if isinstance(service, SwingVideoAnalysisApplicationService):
        return service

    media_service = getattr(request.app.state, "video_library_service", None)
    if media_service is None:
        media_service = create_video_library_application_service(request.app.state.settings)
        request.app.state.video_library_service = media_service
    if not isinstance(media_service, VideoLibraryApplicationService):
        msg = "media service is not configured"
        raise SwingApiRequestError("media_service_unavailable", msg)

    service = SwingVideoAnalysisApplicationService(
        video_library_service=media_service,
        mediapipe_pose_model_path=request.app.state.settings.mediapipe_pose_model_path,
        mediapipe_config=_mediapipe_config_from_settings(request.app.state.settings),
    )
    request.app.state.swing_video_analysis_service = service
    return service


def _mediapipe_config_from_settings(settings: Any) -> MediaPipePoseEstimatorConfig:
    return MediaPipePoseEstimatorConfig(
        num_poses=settings.mediapipe_num_poses,
        min_pose_detection_confidence=settings.mediapipe_min_pose_detection_confidence,
        min_pose_presence_confidence=settings.mediapipe_min_pose_presence_confidence,
        min_tracking_confidence=settings.mediapipe_min_tracking_confidence,
        min_landmark_confidence=settings.mediapipe_min_landmark_confidence,
        smoothing_window=settings.mediapipe_smoothing_window,
        max_interpolation_gap_frames=settings.mediapipe_max_interpolation_gap_frames,
        outlier_rejection_enabled=settings.mediapipe_outlier_rejection_enabled,
        outlier_distance_ratio=settings.mediapipe_outlier_distance_ratio,
        high_velocity_smoothing_limit_ratio=(
            settings.mediapipe_high_velocity_smoothing_limit_ratio
        ),
        stabilization_delta_warning_ratio=settings.mediapipe_stabilization_delta_warning_ratio,
        player_selection_strategy=settings.mediapipe_player_selection_strategy,
        enable_segmentation_mask=settings.mediapipe_enable_segmentation_mask,
        runtime_delegate=settings.mediapipe_runtime_delegate,
    )


def _validation_message(error: ValidationError) -> str:
    first = error.errors()[0]
    field = ".".join(str(part) for part in first["loc"])
    return f"Invalid swing analysis request field '{field}': {first['msg']}."


def _error_response(code: str, message: str, *, status_code: int = 400) -> JSONResponse:
    payload = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(status_code=status_code, content=payload.model_dump())
