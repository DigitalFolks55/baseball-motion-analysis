"""Runtime configuration for local and server browser modes."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeMode(StrEnum):
    """Supported browser UI runtime modes."""

    LOCAL = "local"
    SERVER = "server"


class AppSettings(BaseSettings):
    """Environment-driven application settings."""

    model_config = SettingsConfigDict(env_prefix="BMA_", env_file=".env", extra="ignore")

    runtime_mode: RuntimeMode = RuntimeMode.LOCAL
    media_root: Path = Path("data/media")
    database_path: Path = Path("data/media/library.sqlite3")
    max_upload_mb: int = Field(default=200, ge=1)
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    mediapipe_pose_model_path: Path | None = None
    mediapipe_num_poses: int = Field(default=1, ge=1)
    mediapipe_min_pose_detection_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    mediapipe_min_pose_presence_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    mediapipe_min_tracking_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    mediapipe_min_landmark_confidence: float = Field(default=0.3, ge=0.0, le=1.0)
    mediapipe_smoothing_window: int = Field(default=3, ge=1)
    mediapipe_max_interpolation_gap_frames: int = Field(default=2, ge=0)
    mediapipe_outlier_rejection_enabled: bool = True
    mediapipe_outlier_distance_ratio: float = Field(default=0.75, gt=0.0)
    mediapipe_high_velocity_smoothing_limit_ratio: float = Field(default=0.8, gt=0.0)
    mediapipe_stabilization_delta_warning_ratio: float = Field(default=0.35, gt=0.0)
    mediapipe_player_selection_strategy: Literal[
        "continuity_confidence_size",
        "confidence_size",
    ] = "continuity_confidence_size"
    mediapipe_enable_segmentation_mask: bool = False
    mediapipe_runtime_delegate: Literal["cpu", "gpu"] = "cpu"

    @field_validator("media_root", "database_path", "mediapipe_pose_model_path")
    @classmethod
    def expand_configured_path(cls, path: Path | None) -> Path | None:
        """Expand user-relative paths without forcing machine-specific absolute output."""
        return path.expanduser() if path is not None else None

    @property
    def max_upload_bytes(self) -> int:
        """Return the configured upload limit in bytes."""
        return self.max_upload_mb * 1024 * 1024

    @property
    def privacy_storage_label(self) -> str:
        """Return concise UI copy for where browser uploads are stored."""
        if self.runtime_mode is RuntimeMode.LOCAL:
            return "Files stay under the configured local media directory on this computer."
        return "Files are stored on the configured server-side media directory."


def load_settings() -> AppSettings:
    """Load application settings from the process environment."""
    return AppSettings()
