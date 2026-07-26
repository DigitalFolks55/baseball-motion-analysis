from pathlib import Path

import pytest

from baseball_motion_analysis.video.validators import (
    MediaValidationError,
    validate_image_file_path,
    validate_image_sequence_paths,
    validate_video_file_path,
)


def test_existing_valid_video_extension_passes(tmp_path: Path) -> None:
    video_path = tmp_path / "sample.mp4"
    video_path.write_bytes(b"not decoded in extension validation")

    assert validate_video_file_path(video_path) == video_path


def test_unsupported_video_extension_fails(tmp_path: Path) -> None:
    video_path = tmp_path / "sample.txt"
    video_path.write_text("not a video")

    with pytest.raises(MediaValidationError, match="unsupported video extension"):
        validate_video_file_path(video_path)


def test_missing_video_file_fails(tmp_path: Path) -> None:
    with pytest.raises(MediaValidationError, match="video file does not exist"):
        validate_video_file_path(tmp_path / "missing.mp4")


def test_existing_valid_image_extension_passes(tmp_path: Path) -> None:
    image_path = tmp_path / "frame.png"
    image_path.write_bytes(b"not decoded in extension validation")

    assert validate_image_file_path(image_path) == image_path


def test_unsupported_image_extension_fails(tmp_path: Path) -> None:
    image_path = tmp_path / "frame.bmp"
    image_path.write_bytes(b"not supported")

    with pytest.raises(MediaValidationError, match="unsupported image extension"):
        validate_image_file_path(image_path)


def test_missing_image_file_fails(tmp_path: Path) -> None:
    with pytest.raises(MediaValidationError, match="image file does not exist"):
        validate_image_file_path(tmp_path / "missing.png")


def test_empty_image_sequence_fails() -> None:
    with pytest.raises(MediaValidationError, match="at least one image"):
        validate_image_sequence_paths([])
