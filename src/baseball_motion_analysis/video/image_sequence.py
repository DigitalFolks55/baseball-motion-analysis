"""Local image-sequence loading."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Literal, cast

import cv2

from baseball_motion_analysis.video.models import (
    FrameArray,
    FrameData,
    FrameSequence,
    MediaSourceType,
    VideoMetadata,
)
from baseball_motion_analysis.video.validators import (
    MediaValidationError,
    validate_image_sequence_paths,
)

ImageSortMode = Literal["request_order", "filename", "modified_time"]


def load_image_sequence(
    paths: Sequence[Path | str],
    *,
    assumed_fps: float | None = None,
    sort_mode: ImageSortMode = "request_order",
    source_identifier: str = "image_sequence",
    internal_media_reference: str | None = None,
) -> FrameSequence:
    """Validate and load local images into a normalized frame sequence."""
    if assumed_fps is not None and assumed_fps <= 0:
        msg = "assumed_fps must be greater than 0"
        raise MediaValidationError(msg)

    validated_paths = validate_image_sequence_paths(tuple(Path(path) for path in paths))
    sorted_paths = sort_image_paths(validated_paths, sort_mode=sort_mode)
    frames = _load_frames(sorted_paths, assumed_fps=assumed_fps)

    first_frame = frames[0]
    duration_seconds = len(frames) / assumed_fps if assumed_fps is not None else None
    metadata = VideoMetadata(
        source_type=MediaSourceType.IMAGE_SEQUENCE,
        width=first_frame.width,
        height=first_frame.height,
        fps=assumed_fps,
        total_frame_count=len(frames),
        duration_seconds=duration_seconds,
    )

    return FrameSequence(
        source_type=MediaSourceType.IMAGE_SEQUENCE,
        source_identifier=source_identifier,
        metadata=metadata,
        frames=tuple(frames),
        warnings=metadata.warnings,
        internal_media_reference=internal_media_reference,
    )


def sort_image_paths(paths: tuple[Path, ...], *, sort_mode: ImageSortMode) -> tuple[Path, ...]:
    """Sort image sequence paths for deterministic frame order."""
    if sort_mode == "request_order":
        return paths
    if sort_mode == "filename":
        return tuple(sorted(paths, key=lambda path: path.name))
    if sort_mode == "modified_time":
        return tuple(sorted(paths, key=lambda path: path.stat().st_mtime))

    msg = f"unsupported image sequence sort mode: {sort_mode}"
    raise MediaValidationError(msg)


def _load_frames(paths: tuple[Path, ...], *, assumed_fps: float | None) -> list[FrameData]:
    frames: list[FrameData] = []
    expected_dimensions: tuple[int, int] | None = None

    for frame_index, path in enumerate(paths):
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            msg = "image file could not be read by OpenCV"
            raise MediaValidationError(msg)

        width = int(image.shape[1])
        height = int(image.shape[0])
        dimensions = (width, height)
        if expected_dimensions is None:
            expected_dimensions = dimensions
        elif dimensions != expected_dimensions:
            msg = "image sequence contains mismatched dimensions"
            raise MediaValidationError(msg)

        frames.append(
            FrameData(
                source_type=MediaSourceType.IMAGE_SEQUENCE,
                frame_index=frame_index,
                timestamp_seconds=frame_index / assumed_fps if assumed_fps is not None else 0.0,
                width=width,
                height=height,
                image=cast(FrameArray, image),
            )
        )

    return frames
