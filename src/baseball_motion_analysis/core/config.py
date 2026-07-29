"""Runtime configuration for local and server browser modes."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

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

    @field_validator("media_root", "database_path")
    @classmethod
    def expand_configured_path(cls, path: Path) -> Path:
        """Expand user-relative paths without forcing machine-specific absolute output."""
        return path.expanduser()

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
