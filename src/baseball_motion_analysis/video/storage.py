"""Optional local media copy behavior for selected files."""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from baseball_motion_analysis.video.models import LocalMediaCopyResult, LocalMediaStorageConfig


def copy_video_to_media_root(path: Path, config: LocalMediaStorageConfig) -> LocalMediaCopyResult:
    """Copy one video file into the local media root."""
    copied_path, reference = _copy_file(path, config.media_root / "recorded_videos")
    return LocalMediaCopyResult(paths=(copied_path,), internal_media_reference=reference)


def copy_images_to_media_root(
    paths: tuple[Path, ...], config: LocalMediaStorageConfig
) -> LocalMediaCopyResult:
    """Copy an image sequence into a collision-safe local directory."""
    sequence_id = uuid4().hex
    target_dir = config.media_root / "image_sequences" / sequence_id
    target_dir.mkdir(parents=True, exist_ok=True)

    copied_paths: list[Path] = []
    for index, path in enumerate(paths):
        target_name = f"{index:06d}_{uuid4().hex}{path.suffix.lower()}"
        target_path = target_dir / target_name
        shutil.copy2(path, target_path)
        copied_paths.append(target_path)

    reference = str(Path("image_sequences") / sequence_id)
    return LocalMediaCopyResult(paths=tuple(copied_paths), internal_media_reference=reference)


def _copy_file(path: Path, target_dir: Path) -> tuple[Path, str]:
    target_dir.mkdir(parents=True, exist_ok=True)
    target_name = f"{uuid4().hex}{path.suffix.lower()}"
    target_path = target_dir / target_name
    shutil.copy2(path, target_path)
    reference = str(Path(target_dir.name) / target_name)
    return target_path, reference
