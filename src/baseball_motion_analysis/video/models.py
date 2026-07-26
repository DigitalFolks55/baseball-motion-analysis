"""Shared local media input models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import numpy as np
import numpy.typing as npt

FrameArray = npt.NDArray[np.uint8]


class MediaSourceType(StrEnum):
    """Supported local media input source types."""

    RECORDED_VIDEO = "recorded_video"
    IMAGE_SEQUENCE = "image_sequence"
    CAMERA_STREAM = "camera_stream"


@dataclass(frozen=True)
class FrameSamplingOptions:
    """Options for sampling frames from a recorded video."""

    sample_every_n_frames: int = 1
    target_fps: float | None = None
    max_frame_count: int | None = None

    def __post_init__(self) -> None:
        if self.sample_every_n_frames < 1:
            msg = "sample_every_n_frames must be greater than or equal to 1"
            raise ValueError(msg)
        if self.target_fps is not None and self.target_fps <= 0:
            msg = "target_fps must be greater than 0"
            raise ValueError(msg)
        if self.max_frame_count is not None and self.max_frame_count < 1:
            msg = "max_frame_count must be greater than or equal to 1"
            raise ValueError(msg)


@dataclass(frozen=True)
class VideoMetadata:
    """Metadata shared by recorded videos, image sequences, and camera streams."""

    source_type: MediaSourceType
    width: int
    height: int
    fps: float | None
    total_frame_count: int | None
    duration_seconds: float | None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class FrameData:
    """One decoded frame with timing metadata."""

    source_type: MediaSourceType
    frame_index: int
    timestamp_seconds: float
    width: int
    height: int
    image: FrameArray


@dataclass(frozen=True)
class FrameSequence:
    """A normalized decoded frame sequence for future pose and replay modules."""

    source_type: MediaSourceType
    source_identifier: str
    metadata: VideoMetadata
    frames: tuple[FrameData, ...]
    warnings: tuple[str, ...] = ()
    internal_media_reference: str | None = None

    @property
    def frame_count(self) -> int | None:
        """Return the original frame count when known."""
        return self.metadata.total_frame_count

    @property
    def sampled_frame_count(self) -> int:
        """Return the number of frames present in this sequence."""
        return len(self.frames)


@dataclass(frozen=True)
class VideoInputSource:
    """Recorded local video input descriptor."""

    path: Path
    source_identifier: str
    internal_media_reference: str | None = None


@dataclass(frozen=True)
class ImageSequenceInputSource:
    """Local image-sequence input descriptor."""

    paths: tuple[Path, ...]
    source_identifier: str
    internal_media_reference: str | None = None


@dataclass(frozen=True)
class LocalMediaStorageConfig:
    """Configuration for optional local media copy behavior."""

    media_root: Path = Path("video")


@dataclass(frozen=True)
class LocalMediaCopyResult:
    """Result of copying local media into the configured media root."""

    paths: tuple[Path, ...]
    internal_media_reference: str


@dataclass(frozen=True)
class CameraStreamConfig:
    """Configuration for a local camera stream input."""

    device_index: int = 0
    requested_fps: float | None = None
    width: int | None = None
    height: int | None = None

    def __post_init__(self) -> None:
        if self.device_index < 0:
            msg = "device_index must be greater than or equal to 0"
            raise ValueError(msg)
        if self.requested_fps is not None and self.requested_fps <= 0:
            msg = "requested_fps must be greater than 0"
            raise ValueError(msg)
        if self.width is not None and self.width < 1:
            msg = "width must be greater than or equal to 1"
            raise ValueError(msg)
        if self.height is not None and self.height < 1:
            msg = "height must be greater than or equal to 1"
            raise ValueError(msg)


def combine_warnings(*warning_groups: tuple[str, ...]) -> tuple[str, ...]:
    """Combine warning tuples while preserving order."""
    combined: list[str] = []
    for warnings in warning_groups:
        combined.extend(warnings)
    return tuple(combined)
