"""Recorded local video loading and frame sampling."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import cv2

from baseball_motion_analysis.video.models import (
    FrameArray,
    FrameData,
    FrameSamplingOptions,
    FrameSequence,
    MediaSourceType,
    VideoMetadata,
)
from baseball_motion_analysis.video.validators import MediaValidationError, validate_video_file_path


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
        sample_interval = _effective_sample_interval(metadata.fps, options)
        frames = _sample_video_frames(capture, metadata, sample_interval, options.max_frame_count)
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


def _effective_sample_interval(source_fps: float | None, options: FrameSamplingOptions) -> int:
    if options.target_fps is None or source_fps is None:
        return options.sample_every_n_frames
    target_interval = max(1, round(source_fps / options.target_fps))
    return max(options.sample_every_n_frames, target_interval)


def _sample_video_frames(
    capture: cv2.VideoCapture,
    metadata: VideoMetadata,
    sample_interval: int,
    max_frame_count: int | None,
) -> tuple[FrameData, ...]:
    sampled_frames: list[FrameData] = []
    frame_index = 0

    while True:
        success, frame = capture.read()
        if not success:
            break

        if frame_index % sample_interval == 0:
            timestamp_seconds = (
                frame_index / metadata.fps if metadata.fps is not None and metadata.fps > 0 else 0.0
            )
            sampled_frames.append(
                FrameData(
                    source_type=MediaSourceType.RECORDED_VIDEO,
                    frame_index=frame_index,
                    timestamp_seconds=timestamp_seconds,
                    width=int(frame.shape[1]),
                    height=int(frame.shape[0]),
                    image=cast(FrameArray, frame),
                )
            )
            if max_frame_count is not None and len(sampled_frames) >= max_frame_count:
                break

        frame_index += 1

    if not sampled_frames:
        msg = "video file did not yield any readable frames"
        raise MediaValidationError(msg)

    return tuple(sampled_frames)
