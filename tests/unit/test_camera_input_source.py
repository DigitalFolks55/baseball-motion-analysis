import numpy as np
import pytest

from baseball_motion_analysis.video.camera import CameraInputSource
from baseball_motion_analysis.video.models import CameraStreamConfig, MediaSourceType
from baseball_motion_analysis.video.validators import MediaInputError


def test_camera_object_can_open_read_frame_and_close_with_mock() -> None:
    fake_capture = FakeCapture()

    def create_capture(device_index: int) -> FakeCapture:
        fake_capture.device_index = device_index
        return fake_capture

    source = CameraInputSource(
        CameraStreamConfig(device_index=0, requested_fps=30.0, width=8, height=6),
        capture_factory=create_capture,
    )

    source.open()
    frame = source.read_frame()
    source.close()

    assert fake_capture.device_was_released
    assert fake_capture.device_index == 0
    assert frame.source_type == MediaSourceType.CAMERA_STREAM
    assert frame.frame_index == 0
    assert frame.width == 8
    assert frame.height == 6


def test_camera_context_manager_releases_mock_capture() -> None:
    fake_capture = FakeCapture()

    with CameraInputSource(capture_factory=lambda device_index: fake_capture) as source:
        frame = source.read_frame()

    assert frame.frame_index == 0
    assert fake_capture.device_was_released


def test_camera_read_before_open_fails() -> None:
    source = CameraInputSource(capture_factory=lambda device_index: FakeCapture())

    with pytest.raises(MediaInputError, match="not open"):
        source.read_frame()


class FakeCapture:
    def __init__(self) -> None:
        self.device_index: int | None = None
        self.device_was_released = False

    def isOpened(self) -> bool:  # noqa: N802 - OpenCV compatibility method.
        return True

    def read(self) -> tuple[bool, object]:
        return True, np.zeros((6, 8, 3), dtype=np.uint8)

    def release(self) -> None:
        self.device_was_released = True

    def set(self, prop_id: int, value: float) -> bool:
        return True
