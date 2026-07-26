"""Local camera stream interface for future real-time analysis."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Protocol, cast

import cv2
import numpy as np

from baseball_motion_analysis.video.models import (
    CameraStreamConfig,
    FrameArray,
    FrameData,
    MediaSourceType,
)
from baseball_motion_analysis.video.validators import MediaInputError


class CameraCapture(Protocol):
    """Protocol for OpenCV-like camera capture objects."""

    def isOpened(self) -> bool: ...  # noqa: N802 - OpenCV compatibility method.

    def read(self) -> tuple[bool, object]: ...

    def release(self) -> None: ...

    def set(self, prop_id: int, value: float) -> bool: ...


class CameraInputSource:
    """Minimal local camera stream wrapper.

    TODO: Add real-time pose-estimation and motion-analysis integration after the
    local input contract is validated.
    """

    def __init__(
        self,
        config: CameraStreamConfig | None = None,
        *,
        capture_factory: Callable[[int], CameraCapture] | None = None,
    ) -> None:
        self.config = config or CameraStreamConfig()
        self._capture_factory = capture_factory or cv2.VideoCapture
        self._capture: CameraCapture | None = None
        self._frame_index = 0
        self._opened_at: float | None = None

    def open(self) -> None:
        """Open the configured local camera device."""
        capture = self._capture_factory(self.config.device_index)
        if self.config.requested_fps is not None:
            capture.set(cv2.CAP_PROP_FPS, self.config.requested_fps)
        if self.config.width is not None:
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, float(self.config.width))
        if self.config.height is not None:
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, float(self.config.height))
        if not capture.isOpened():
            msg = "camera device could not be opened"
            raise MediaInputError(msg)

        self._capture = capture
        self._opened_at = time.monotonic()
        self._frame_index = 0

    def read_frame(self) -> FrameData:
        """Read one camera frame from an opened camera device."""
        if self._capture is None or self._opened_at is None:
            msg = "camera stream is not open"
            raise MediaInputError(msg)

        success, frame = self._capture.read()
        if not success:
            msg = "camera frame could not be read"
            raise MediaInputError(msg)
        if not isinstance(frame, np.ndarray):
            msg = "camera frame is not image-like"
            raise MediaInputError(msg)

        timestamp_seconds = time.monotonic() - self._opened_at
        frame_data = FrameData(
            source_type=MediaSourceType.CAMERA_STREAM,
            frame_index=self._frame_index,
            timestamp_seconds=timestamp_seconds,
            width=int(frame.shape[1]),
            height=int(frame.shape[0]),
            image=cast(FrameArray, frame.astype(np.uint8, copy=False)),
        )
        self._frame_index += 1
        return frame_data

    def close(self) -> None:
        """Release the current camera device if open."""
        if self._capture is not None:
            self._capture.release()
        self._capture = None
        self._opened_at = None

    def __enter__(self) -> CameraInputSource:
        self.open()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
