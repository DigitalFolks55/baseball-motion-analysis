"""Recorded local video loading and frame sampling."""

from __future__ import annotations

import math
from dataclasses import replace
from pathlib import Path
from typing import cast

import cv2

from baseball_motion_analysis.video.models import (
    FrameArray,
    FrameData,
    FrameSamplingDiagnostics,
    FrameSamplingOptions,
    FrameSequence,
    FrameTimestampDiagnostics,
    MediaSourceType,
    VideoMetadata,
)
from baseball_motion_analysis.video.validators import MediaValidationError, validate_video_file_path

_MIN_TIMESTAMP_STEP_SECONDS = 0.001


def load_video_file(
    path: Path | str,
    *,
    sampling: FrameSamplingOptions | None = None,
    source_identifier: str | None = None,
    internal_media_reference: str | None = None,
) -> FrameSequence:
    """Validate, open, and sample a recorded local video file."""
    video_path = validate_video_file_path(path)
    options = sampling or FrameSamplingOptions()

    capture = cv2.VideoCapture(str(video_path))
    try:
        if not capture.isOpened():
            msg = "video file could not be opened by OpenCV"
            raise MediaValidationError(msg)

        metadata = extract_video_metadata(capture)
        frames, sampling_diagnostics, timestamp_diagnostics = _sample_video_frames(
            capture,
            metadata,
            options,
        )
        metadata = replace(
            metadata,
            warnings=combine_warning_text(metadata.warnings, sampling_diagnostics.limitations),
            timestamp_diagnostics=timestamp_diagnostics,
            sampling_diagnostics=sampling_diagnostics,
        )
    finally:
        capture.release()

    return FrameSequence(
        source_type=MediaSourceType.RECORDED_VIDEO,
        source_identifier=source_identifier or video_path.name,
        metadata=metadata,
        frames=frames,
        warnings=metadata.warnings,
        internal_media_reference=internal_media_reference,
    )


def extract_video_metadata(capture: cv2.VideoCapture) -> VideoMetadata:
    """Extract basic metadata from an open OpenCV video capture."""
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    total_frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))

    warnings: list[str] = []
    normalized_fps: float | None = fps if fps > 0 else None
    if normalized_fps is None:
        warnings.append("video fps is unavailable")

    normalized_total_frame_count = total_frame_count if total_frame_count >= 0 else None
    duration_seconds = (
        normalized_total_frame_count / normalized_fps
        if normalized_total_frame_count is not None and normalized_fps is not None
        else None
    )

    return VideoMetadata(
        source_type=MediaSourceType.RECORDED_VIDEO,
        width=width,
        height=height,
        fps=normalized_fps,
        total_frame_count=normalized_total_frame_count,
        duration_seconds=duration_seconds,
        warnings=tuple(warnings),
    )


def normalize_frame_timestamps(
    raw_timestamps: tuple[float | None, ...],
    *,
    source_fps: float | None,
) -> tuple[tuple[float, ...], FrameTimestampDiagnostics]:
    """Return valid monotonic timestamps and provenance diagnostics."""
    if not raw_timestamps:
        return (), FrameTimestampDiagnostics(timestamp_source="missing")

    finite_decoder_timestamps = tuple(
        timestamp
        for timestamp in raw_timestamps
        if timestamp is not None and math.isfinite(timestamp) and timestamp >= 0.0
    )
    decoder_globally_valid = len(finite_decoder_timestamps) == len(
        raw_timestamps
    ) and _has_positive_temporal_span(finite_decoder_timestamps)
    if decoder_globally_valid:
        normalized: list[float] = []
        repair_count = 0
        previous = -math.inf
        cadence = _median_positive_delta(finite_decoder_timestamps)
        repair_step = max(_MIN_TIMESTAMP_STEP_SECONDS, min(cadence or 0.033333, 0.033333))
        for timestamp in finite_decoder_timestamps:
            value = float(timestamp)
            if value <= previous:
                value = previous + repair_step
                repair_count += 1
            normalized.append(value)
            previous = value
        if repair_count:
            return tuple(normalized), FrameTimestampDiagnostics(
                timestamp_source="repaired",
                timestamp_fallback_reason="invalid_decoder_timestamps",
                timestamp_repair_count=repair_count,
                limitations=(
                    "Decoder frame timestamps contained duplicate or decreasing values and were "
                    "repaired to preserve monotonic presentation time.",
                ),
            )
        return tuple(normalized), FrameTimestampDiagnostics(timestamp_source="opencv_pos_msec")

    if source_fps is not None and source_fps > 0.0:
        reason = (
            "missing_decoder_timestamps"
            if not finite_decoder_timestamps
            else "invalid_decoder_timestamps"
        )
        return tuple(index / source_fps for index in range(len(raw_timestamps))), (
            FrameTimestampDiagnostics(
                timestamp_source="constant_fps",
                timestamp_fallback_reason=reason,
                limitations=(
                    "Decoder presentation timestamps were unavailable or unreliable; "
                    "timestamps were synthesized from constant source FPS metadata.",
                ),
            )
        )

    if finite_decoder_timestamps:
        normalized = []
        repair_count = 0
        previous = -math.inf
        cadence = _median_positive_delta(finite_decoder_timestamps)
        repair_step = max(_MIN_TIMESTAMP_STEP_SECONDS, min(cadence or 0.033333, 0.033333))
        for raw_timestamp in raw_timestamps:
            if raw_timestamp is None or not math.isfinite(raw_timestamp) or raw_timestamp < 0.0:
                value = previous + repair_step if math.isfinite(previous) else 0.0
                repair_count += 1
            else:
                value = raw_timestamp
                if value <= previous:
                    value = previous + repair_step
                    repair_count += 1
            normalized.append(value)
            previous = value
        return tuple(normalized), FrameTimestampDiagnostics(
            timestamp_source="repaired",
            timestamp_fallback_reason="missing_fps",
            timestamp_repair_count=repair_count,
            limitations=(
                "Video FPS metadata was unavailable; decoder timestamps were repaired where "
                "needed and used as the presentation timeline.",
            ),
        )

    msg = "video timestamps are unavailable and fps metadata is invalid"
    raise MediaValidationError(msg)


def _sample_video_frames(
    capture: cv2.VideoCapture,
    metadata: VideoMetadata,
    options: FrameSamplingOptions,
) -> tuple[tuple[FrameData, ...], FrameSamplingDiagnostics, FrameTimestampDiagnostics]:
    decoded_frames: list[tuple[int, FrameArray, int, int]] = []
    raw_timestamps: list[float | None] = []
    frame_index = 0

    while True:
        success, frame = capture.read()
        if not success:
            break
        timestamp_msec = float(capture.get(cv2.CAP_PROP_POS_MSEC))
        raw_timestamps.append(timestamp_msec / 1000.0 if timestamp_msec >= 0.0 else None)
        decoded_frames.append(
            (frame_index, cast(FrameArray, frame), int(frame.shape[1]), int(frame.shape[0]))
        )
        frame_index += 1

    if not decoded_frames:
        msg = "video file did not yield any readable frames"
        raise MediaValidationError(msg)

    timestamps, timestamp_diagnostics = normalize_frame_timestamps(
        tuple(raw_timestamps),
        source_fps=metadata.fps,
    )
    candidate_frames = tuple(
        FrameData(
            source_type=MediaSourceType.RECORDED_VIDEO,
            frame_index=decoded_frame[0],
            timestamp_seconds=timestamps[index],
            width=decoded_frame[2],
            height=decoded_frame[3],
            image=decoded_frame[1],
        )
        for index, decoded_frame in enumerate(decoded_frames)
    )
    selected_positions = temporal_sample_positions(
        tuple(frame.timestamp_seconds for frame in candidate_frames),
        source_fps=metadata.fps,
        options=options,
    )
    sampled_frames = tuple(candidate_frames[position] for position in selected_positions)
    diagnostics = _frame_sampling_diagnostics(
        candidate_frames,
        sampled_frames,
        metadata=metadata,
        options=options,
        timestamp_diagnostics=timestamp_diagnostics,
    )
    return sampled_frames, diagnostics, timestamp_diagnostics


def temporal_sample_positions(
    timestamps: tuple[float, ...],
    *,
    source_fps: float | None,
    options: FrameSamplingOptions,
) -> tuple[int, ...]:
    """Select deterministic positions by time across the full usable range."""
    if not timestamps:
        return ()
    eligible_positions = tuple(range(0, len(timestamps), options.sample_every_n_frames))
    if not eligible_positions:
        return (0,)
    eligible_timestamps = tuple(timestamps[position] for position in eligible_positions)
    target_count = len(eligible_positions)
    if (
        options.target_fps is not None
        and source_fps is not None
        and source_fps > options.target_fps
    ):
        duration = max(0.0, eligible_timestamps[-1] - eligible_timestamps[0])
        cadence_count = max(1, math.floor(duration * options.target_fps) + 1)
        target_count = min(target_count, cadence_count)
    if options.max_frame_count is not None:
        target_count = min(target_count, options.max_frame_count)
    if target_count >= len(eligible_positions):
        return eligible_positions
    if target_count <= 1:
        return (eligible_positions[0],)

    start = eligible_timestamps[0]
    end = eligible_timestamps[-1]
    desired_times = tuple(
        start + (end - start) * index / (target_count - 1) for index in range(target_count)
    )
    selected: list[int] = []
    cursor = 0
    for desired_time in desired_times:
        best_offset = min(
            range(cursor, len(eligible_positions)),
            key=lambda offset: (abs(eligible_timestamps[offset] - desired_time), offset),
        )
        position = eligible_positions[best_offset]
        if selected and position <= selected[-1]:
            continue
        selected.append(position)
        cursor = best_offset + 1
        if cursor >= len(eligible_positions):
            break
    return tuple(selected)


def _frame_sampling_diagnostics(
    source_frames: tuple[FrameData, ...],
    sampled_frames: tuple[FrameData, ...],
    *,
    metadata: VideoMetadata,
    options: FrameSamplingOptions,
    timestamp_diagnostics: FrameTimestampDiagnostics,
) -> FrameSamplingDiagnostics:
    source_duration = metadata.duration_seconds or _time_span_seconds(source_frames)
    analyzed_start = sampled_frames[0].timestamp_seconds if sampled_frames else None
    analyzed_end = sampled_frames[-1].timestamp_seconds if sampled_frames else None
    analyzed_duration = (
        analyzed_end - analyzed_start
        if analyzed_start is not None
        and analyzed_end is not None
        and analyzed_end >= analyzed_start
        else None
    )
    achieved_fps = (
        round((len(sampled_frames) - 1) / analyzed_duration, 3)
        if analyzed_duration is not None and analyzed_duration > 0.0 and len(sampled_frames) > 1
        else metadata.fps
    )
    cap_applied = len(sampled_frames) < len(source_frames)
    full_frame_sampling = len(sampled_frames) == len(source_frames)
    temporal_coverage_complete = (
        bool(sampled_frames)
        and sampled_frames[0].frame_index == source_frames[0].frame_index
        and sampled_frames[-1].frame_index == source_frames[-1].frame_index
    )
    limitations = list(timestamp_diagnostics.limitations)
    if cap_applied:
        limitations.append(
            "Frame sampling was reduced by target cadence or frame-count cap across the full "
            "clip duration."
        )
    if not temporal_coverage_complete:
        limitations.append(
            "The selected frames do not cover both the first and final usable source frame."
        )
    return FrameSamplingDiagnostics(
        source_fps=metadata.fps,
        requested_fps=options.target_fps,
        achieved_fps=achieved_fps,
        sampled_frame_count=len(sampled_frames),
        total_frame_count=metadata.total_frame_count,
        source_duration_seconds=source_duration,
        analyzed_start_seconds=analyzed_start,
        analyzed_end_seconds=analyzed_end,
        analyzed_duration_seconds=analyzed_duration,
        max_frame_count=options.max_frame_count,
        cap_applied=cap_applied,
        full_frame_sampling=full_frame_sampling,
        temporal_coverage_complete=temporal_coverage_complete,
        timestamp_source=timestamp_diagnostics.timestamp_source,
        timestamp_fallback_reason=timestamp_diagnostics.timestamp_fallback_reason,
        timestamp_repair_count=timestamp_diagnostics.timestamp_repair_count,
        limitations=tuple(limitations),
    )


def _has_positive_temporal_span(timestamps: tuple[float, ...]) -> bool:
    return len(timestamps) <= 1 or timestamps[-1] > timestamps[0]


def _median_positive_delta(timestamps: tuple[float, ...]) -> float | None:
    deltas = sorted(
        current - previous
        for previous, current in zip(timestamps, timestamps[1:], strict=False)
        if current > previous
    )
    if not deltas:
        return None
    middle = len(deltas) // 2
    if len(deltas) % 2:
        return deltas[middle]
    return (deltas[middle - 1] + deltas[middle]) / 2.0


def _time_span_seconds(frames: tuple[FrameData, ...]) -> float | None:
    if len(frames) < 2:
        return None
    return max(0.0, frames[-1].timestamp_seconds - frames[0].timestamp_seconds)


def combine_warning_text(
    existing: tuple[str, ...],
    additional: tuple[str, ...],
) -> tuple[str, ...]:
    """Combine warning strings while preserving order and uniqueness."""
    return tuple(dict.fromkeys((*existing, *additional)))
