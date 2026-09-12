from pathlib import Path

import cv2
import numpy as np
import pytest

from baseball_motion_analysis.video import (
    FrameSamplingOptions,
    LocalMediaStorageConfig,
    MediaInputService,
    MediaSourceType,
    normalize_frame_timestamps,
    temporal_sample_positions,
)
from baseball_motion_analysis.video.validators import MediaValidationError


def test_video_metadata_and_sample_every_n_frames(tmp_path: Path) -> None:
    video_path = _create_tiny_video(tmp_path / "sample.avi", frame_count=6, fps=10.0)

    sequence = MediaInputService().load_video_file(
        video_path,
        sampling=FrameSamplingOptions(sample_every_n_frames=2),
    )

    assert sequence.source_type == MediaSourceType.RECORDED_VIDEO
    assert sequence.source_identifier == "sample.avi"
    assert sequence.metadata.width == 32
    assert sequence.metadata.height == 24
    assert sequence.metadata.fps == pytest.approx(10.0)
    assert sequence.metadata.total_frame_count == 6
    assert sequence.metadata.duration_seconds == pytest.approx(0.6)
    assert [frame.frame_index for frame in sequence.frames] == [0, 2, 4]
    assert [frame.timestamp_seconds for frame in sequence.frames] == pytest.approx([0.0, 0.2, 0.4])


def test_video_target_fps_sampling(tmp_path: Path) -> None:
    video_path = _create_tiny_video(tmp_path / "sample.avi", frame_count=6, fps=10.0)

    sequence = MediaInputService().load_video_file(
        video_path,
        sampling=FrameSamplingOptions(target_fps=5.0),
    )

    assert [frame.frame_index for frame in sequence.frames] == [0, 2, 5]
    assert sequence.metadata.sampling_diagnostics is not None
    assert sequence.metadata.sampling_diagnostics.achieved_fps <= 5.0
    assert sequence.metadata.sampling_diagnostics.temporal_coverage_complete is True


def test_video_max_frame_count(tmp_path: Path) -> None:
    video_path = _create_tiny_video(tmp_path / "sample.avi", frame_count=6, fps=10.0)

    sequence = MediaInputService().load_video_file(
        video_path,
        sampling=FrameSamplingOptions(max_frame_count=2),
    )

    assert sequence.sampled_frame_count == 2
    assert [frame.frame_index for frame in sequence.frames] == [0, 5]
    assert sequence.metadata.sampling_diagnostics is not None
    assert sequence.metadata.sampling_diagnostics.cap_applied is True
    assert sequence.metadata.sampling_diagnostics.temporal_coverage_complete is True


@pytest.mark.parametrize(
    ("source_fps", "expected_max_count"),
    [
        (24.0, 24),
        (30.0, 30),
        (40.0, 30),
        (50.0, 30),
        (60.0, 30),
        (120.0, 30),
    ],
)
def test_temporal_sampling_does_not_exceed_requested_cadence(
    source_fps: float,
    expected_max_count: int,
) -> None:
    timestamps = tuple(index / source_fps for index in range(int(source_fps)))

    positions = temporal_sample_positions(
        timestamps,
        source_fps=source_fps,
        options=FrameSamplingOptions(target_fps=30.0),
    )

    assert len(positions) <= expected_max_count
    assert positions[0] == 0
    assert positions[-1] == len(timestamps) - 1
    assert list(positions) == sorted(set(positions))


def test_temporal_sampling_cap_represents_full_duration() -> None:
    timestamps = tuple(index / 60.0 for index in range(120))

    positions = temporal_sample_positions(
        timestamps,
        source_fps=60.0,
        options=FrameSamplingOptions(target_fps=30.0, max_frame_count=10),
    )

    assert len(positions) == 10
    assert positions[0] == 0
    assert positions[-1] == 119
    assert positions != tuple(range(10))


def test_normalize_frame_timestamps_reports_constant_fps_fallback() -> None:
    timestamps, diagnostics = normalize_frame_timestamps(
        (None, None, None, None),
        source_fps=24.0,
    )

    assert timestamps == pytest.approx((0.0, 1 / 24.0, 2 / 24.0, 3 / 24.0))
    assert diagnostics.timestamp_source == "constant_fps"
    assert diagnostics.timestamp_fallback_reason == "missing_decoder_timestamps"
    assert diagnostics.limitations


def test_normalize_frame_timestamps_repairs_irregular_decoder_timestamps() -> None:
    timestamps, diagnostics = normalize_frame_timestamps(
        (0.0, 0.033, 0.033, 0.020, 0.099),
        source_fps=None,
    )

    assert timestamps == tuple(sorted(timestamps))
    assert len(set(timestamps)) == len(timestamps)
    assert diagnostics.timestamp_source == "repaired"
    assert diagnostics.timestamp_repair_count == 3
    assert diagnostics.limitations


def test_unreadable_video_file_fails(tmp_path: Path) -> None:
    video_path = tmp_path / "broken.mp4"
    video_path.write_bytes(b"not a real video")

    with pytest.raises(MediaValidationError, match="could not be opened"):
        MediaInputService().load_video_file(video_path)


def test_video_copy_hides_absolute_path(tmp_path: Path) -> None:
    video_path = _create_tiny_video(tmp_path / "sample.avi", frame_count=2, fps=10.0)
    media_root = tmp_path / "media"

    sequence = MediaInputService(LocalMediaStorageConfig(media_root=media_root)).load_video_file(
        video_path,
        copy_to_media_root=True,
    )
    copied_files = list(media_root.rglob("*.avi"))

    assert sequence.internal_media_reference is not None
    assert sequence.internal_media_reference.endswith(".avi")
    assert str(tmp_path) not in sequence.internal_media_reference
    assert len(copied_files) == 1


def _create_tiny_video(path: Path, *, frame_count: int, fps: float) -> Path:
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        fps,
        (32, 24),
    )
    if not writer.isOpened():
        pytest.skip("OpenCV could not create the tiny video fixture")

    try:
        for index in range(frame_count):
            frame = np.full((24, 32, 3), index * 20, dtype=np.uint8)
            writer.write(frame)
    finally:
        writer.release()

    return path
