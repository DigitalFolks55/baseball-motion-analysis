"""Local media input, validation, metadata, and frame sampling boundaries."""

from baseball_motion_analysis.video.camera import CameraInputSource
from baseball_motion_analysis.video.image_sequence import load_image_sequence
from baseball_motion_analysis.video.models import (
    CameraStreamConfig,
    FrameData,
    FrameSamplingDiagnostics,
    FrameSamplingOptions,
    FrameSequence,
    FrameTimestampDiagnostics,
    ImageSequenceInputSource,
    LocalMediaStorageConfig,
    MediaSourceType,
    VideoInputSource,
    VideoMetadata,
)
from baseball_motion_analysis.video.service import MediaInputService
from baseball_motion_analysis.video.validators import MediaInputError, MediaValidationError
from baseball_motion_analysis.video.video_loader import (
    load_video_file,
    normalize_frame_timestamps,
    temporal_sample_positions,
)

__all__ = [
    "CameraInputSource",
    "CameraStreamConfig",
    "FrameData",
    "FrameSamplingDiagnostics",
    "FrameSamplingOptions",
    "FrameSequence",
    "FrameTimestampDiagnostics",
    "ImageSequenceInputSource",
    "LocalMediaStorageConfig",
    "MediaInputError",
    "MediaInputService",
    "MediaSourceType",
    "MediaValidationError",
    "VideoInputSource",
    "VideoMetadata",
    "load_image_sequence",
    "load_video_file",
    "normalize_frame_timestamps",
    "temporal_sample_positions",
]
