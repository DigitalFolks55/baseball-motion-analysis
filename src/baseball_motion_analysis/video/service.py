"""Application-service contract for local media input."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from baseball_motion_analysis.video.camera import CameraInputSource
from baseball_motion_analysis.video.image_sequence import ImageSortMode, load_image_sequence
from baseball_motion_analysis.video.models import (
    CameraStreamConfig,
    FrameSamplingOptions,
    FrameSequence,
    ImageSequenceInputSource,
    LocalMediaStorageConfig,
    VideoInputSource,
)
from baseball_motion_analysis.video.storage import (
    copy_images_to_media_root,
    copy_video_to_media_root,
)
from baseball_motion_analysis.video.validators import (
    validate_image_sequence_paths,
    validate_video_file_path,
)
from baseball_motion_analysis.video.video_loader import load_video_file

ImageSortModeName = Literal["request_order", "filename", "modified_time"]


class MediaInputService:
    """Coordinates local video, image-sequence, and camera input workflows."""

    def __init__(self, storage_config: LocalMediaStorageConfig | None = None) -> None:
        self._storage_config = storage_config or LocalMediaStorageConfig()

    def load_video_file(
        self,
        path: Path,
        *,
        sampling: FrameSamplingOptions | None = None,
        copy_to_media_root: bool = False,
    ) -> FrameSequence:
        """Load a recorded video file into a normalized frame sequence."""
        validated_path = validate_video_file_path(path)
        source = VideoInputSource(path=validated_path, source_identifier=validated_path.name)

        if copy_to_media_root:
            copy_result = copy_video_to_media_root(validated_path, self._storage_config)
            source = VideoInputSource(
                path=copy_result.paths[0],
                source_identifier=validated_path.name,
                internal_media_reference=copy_result.internal_media_reference,
            )

        return load_video_file(
            source.path,
            sampling=sampling,
            source_identifier=source.source_identifier,
            internal_media_reference=source.internal_media_reference,
        )

    def load_image_sequence(
        self,
        paths: Sequence[Path],
        *,
        assumed_fps: float | None = None,
        sort_mode: ImageSortModeName = "request_order",
        copy_to_media_root: bool = False,
    ) -> FrameSequence:
        """Load local images into a normalized frame sequence."""
        validated_paths = validate_image_sequence_paths(tuple(paths))
        source = ImageSequenceInputSource(
            paths=validated_paths,
            source_identifier="image_sequence",
        )

        if copy_to_media_root:
            copy_result = copy_images_to_media_root(validated_paths, self._storage_config)
            source = ImageSequenceInputSource(
                paths=copy_result.paths,
                source_identifier="image_sequence",
                internal_media_reference=copy_result.internal_media_reference,
            )

        return load_image_sequence(
            source.paths,
            assumed_fps=assumed_fps,
            sort_mode=sort_mode,
            source_identifier=source.source_identifier,
            internal_media_reference=source.internal_media_reference,
        )

    def open_camera_stream(
        self,
        device_index: int = 0,
        *,
        requested_fps: float | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> CameraInputSource:
        """Create a local camera input source without opening hardware immediately."""
        config = CameraStreamConfig(
            device_index=device_index,
            requested_fps=requested_fps,
            width=width,
            height=height,
        )
        return CameraInputSource(config=config)


def normalize_sort_mode(sort_mode: ImageSortModeName) -> ImageSortMode:
    """Return a validated image sort mode for callers that need the concrete type."""
    return sort_mode
