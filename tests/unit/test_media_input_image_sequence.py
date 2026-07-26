from pathlib import Path

import cv2
import numpy as np
import pytest

from baseball_motion_analysis.video import (
    LocalMediaStorageConfig,
    MediaInputService,
    MediaSourceType,
)
from baseball_motion_analysis.video.validators import MediaValidationError


def test_image_sequence_uses_request_order_by_default(tmp_path: Path) -> None:
    second = _write_image(tmp_path / "b.png", width=8, height=6, value=20)
    first = _write_image(tmp_path / "a.png", width=8, height=6, value=10)

    sequence = MediaInputService().load_image_sequence([second, first], assumed_fps=10.0)

    assert sequence.source_type == MediaSourceType.IMAGE_SEQUENCE
    assert sequence.metadata.total_frame_count == 2
    assert sequence.metadata.width == 8
    assert sequence.metadata.height == 6
    assert sequence.metadata.fps == pytest.approx(10.0)
    assert sequence.metadata.duration_seconds == pytest.approx(0.2)
    assert [frame.frame_index for frame in sequence.frames] == [0, 1]
    assert [frame.timestamp_seconds for frame in sequence.frames] == pytest.approx([0.0, 0.1])
    assert int(sequence.frames[0].image[0, 0, 0]) == 20
    assert int(sequence.frames[1].image[0, 0, 0]) == 10


def test_image_sequence_can_sort_by_filename(tmp_path: Path) -> None:
    second = _write_image(tmp_path / "b.png", width=8, height=6, value=20)
    first = _write_image(tmp_path / "a.png", width=8, height=6, value=10)

    sequence = MediaInputService().load_image_sequence(
        [second, first],
        assumed_fps=10.0,
        sort_mode="filename",
    )

    assert int(sequence.frames[0].image[0, 0, 0]) == 10
    assert int(sequence.frames[1].image[0, 0, 0]) == 20


def test_image_sequence_rejects_mismatched_dimensions(tmp_path: Path) -> None:
    first = _write_image(tmp_path / "a.png", width=8, height=6, value=10)
    second = _write_image(tmp_path / "b.png", width=9, height=6, value=20)

    with pytest.raises(MediaValidationError, match="mismatched dimensions"):
        MediaInputService().load_image_sequence([first, second])


def test_image_sequence_copy_to_media_root_preserves_extensions(tmp_path: Path) -> None:
    first = _write_image(tmp_path / "a.png", width=8, height=6, value=10)
    second = _write_image(tmp_path / "b.jpg", width=8, height=6, value=20)
    media_root = tmp_path / "media"

    service = MediaInputService(LocalMediaStorageConfig(media_root=media_root))
    sequence = service.load_image_sequence(
        [first, second],
        assumed_fps=5.0,
        copy_to_media_root=True,
    )
    copied_png_files = list(media_root.rglob("*.png"))
    copied_jpg_files = list(media_root.rglob("*.jpg"))

    assert sequence.internal_media_reference is not None
    assert sequence.internal_media_reference.startswith("image_sequences/")
    assert str(tmp_path) not in sequence.internal_media_reference
    assert len(copied_png_files) == 1
    assert len(copied_jpg_files) == 1


def _write_image(path: Path, *, width: int, height: int, value: int) -> Path:
    image = np.full((height, width, 3), value, dtype=np.uint8)
    success = cv2.imwrite(str(path), image)
    if not success:
        pytest.skip(f"OpenCV could not create image fixture {path.suffix}")
    return path
