"""Application services used by API endpoints."""


class ApplicationStatusService:
    """Reports application status without reaching into domain modules."""

    def health(self) -> dict[str, str]:
        """Return a minimal health payload."""
        return {"status": "ok"}
