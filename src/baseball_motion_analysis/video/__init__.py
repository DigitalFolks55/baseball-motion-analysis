"""Local media input, validation, metadata, and frame sampling boundaries."""

from baseball_motion_analysis.video.camera import CameraInputSource
from baseball_motion_analysis.video.image_sequence import load_image_sequence
from baseball_motion_analysis.video.models import (
    CameraStreamConfig,
    FrameData,
    FrameSamplingOptions,
    FrameSequence,
    ImageSequenceInputSource,
    LocalMediaStorageConfig,
    MediaSourceType,
    VideoInputSource,
    VideoMetadata,
)
from baseball_motion_analysis.video.service import MediaInputService
from baseball_motion_analysis.video.validators import MediaInputError, MediaValidationError
from baseball_motion_analysis.video.video_loader import load_video_file

__all__ = [
    "CameraInputSource",
    "CameraStreamConfig",
    "FrameData",
    "FrameSamplingOptions",
    "FrameSequence",
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
]
