"""Browser media API adapter."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from baseball_motion_analysis.api.schemas import (
    DeleteMediaResponse,
    ErrorDetail,
    ErrorResponse,
    MediaRecordResponse,
    VideoReplayManifestResponse,
)
from baseball_motion_analysis.app.media_services import (
    ImportVideoRequest,
    InvalidMediaIdError,
    MediaApplicationError,
    MissingMediaFileError,
    StorageWriteError,
    UnreadableVideoError,
    VideoContentLocation,
    VideoLibraryApplicationService,
    create_video_library_application_service,
)

router = APIRouter(prefix="/media/videos", tags=["media"])

_UPLOAD_CHUNK_SIZE = 1024 * 1024
_CONTENT_CHUNK_SIZE = 1024 * 1024
_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    413: {"model": ErrorResponse},
    416: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}


class UploadRequestError(MediaApplicationError):
    """Raised when multipart upload input is invalid."""

    error_code = "invalid_upload"
    user_message = "The upload request is invalid."


class EmptyUploadError(UploadRequestError):
    """Raised when no video bytes were uploaded."""

    error_code = "empty_upload"
    user_message = "Choose a non-empty video file."


class FileTooLargeError(UploadRequestError):
    """Raised when an upload exceeds the configured size limit."""

    error_code = "file_too_large"
    user_message = "The selected video is larger than the configured upload limit."


class InvalidRangeError(MediaApplicationError):
    """Raised when an HTTP byte range is malformed or unsatisfiable."""

    error_code = "invalid_http_byte_range"
    user_message = "The requested video byte range is invalid."


@dataclass(frozen=True)
class ByteRange:
    """Resolved inclusive byte range."""

    start: int
    end: int

    @property
    def length(self) -> int:
        """Return the number of bytes in the range."""
        return self.end - self.start + 1


@router.post("", response_model=MediaRecordResponse, responses=_ERROR_RESPONSES)
async def upload_video(
    request: Request,
    file: Annotated[UploadFile | None, File(description="Video file upload")] = None,
) -> MediaRecordResponse | JSONResponse:
    """Stream a browser-uploaded video into staging, then import through app services."""
    service = _media_service(request)
    if file is None or not file.filename:
        return _error_response(UploadRequestError("Choose a video file."), status_code=400)

    staging_path = service.create_staging_file(Path(file.filename).suffix)
    bytes_written = 0
    try:
        with staging_path.open("wb") as staged_file:
            while chunk := await file.read(_UPLOAD_CHUNK_SIZE):
                bytes_written += len(chunk)
                if bytes_written > request.app.state.settings.max_upload_bytes:
                    raise FileTooLargeError()
                staged_file.write(chunk)
        if bytes_written == 0:
            raise EmptyUploadError()

        record = service.import_video(
            ImportVideoRequest(
                staging_path=staging_path,
                display_name=file.filename,
                file_size_bytes=bytes_written,
            )
        )
    except MediaApplicationError as exc:
        with suppress(MediaApplicationError):
            service.delete_staging_file(staging_path)
        return _error_response(exc, status_code=_status_code_for_error(exc))
    finally:
        await file.close()

    return MediaRecordResponse.from_record(record)


@router.get("", response_model=tuple[MediaRecordResponse, ...], responses=_ERROR_RESPONSES)
def list_videos(request: Request) -> tuple[MediaRecordResponse, ...] | JSONResponse:
    """Return stored videos for the browser library."""
    service = _media_service(request)
    try:
        records = service.list_videos()
    except MediaApplicationError as exc:
        return _error_response(exc, status_code=_status_code_for_error(exc))
    return tuple(MediaRecordResponse.from_record(record) for record in records)


@router.get("/{media_id}", response_model=MediaRecordResponse, responses=_ERROR_RESPONSES)
def get_video(request: Request, media_id: str) -> MediaRecordResponse | JSONResponse:
    """Return one stored video record."""
    try:
        record = _media_service(request).get_video(media_id)
    except MediaApplicationError as exc:
        return _error_response(exc, status_code=_status_code_for_error(exc))
    return MediaRecordResponse.from_record(record)


@router.delete("/{media_id}", response_model=DeleteMediaResponse, responses=_ERROR_RESPONSES)
def delete_video(request: Request, media_id: str) -> DeleteMediaResponse | JSONResponse:
    """Delete one uploaded video through the application service."""
    try:
        _media_service(request).delete_video(media_id)
    except MediaApplicationError as exc:
        return _error_response(exc, status_code=_status_code_for_error(exc))
    return DeleteMediaResponse(media_id=media_id, deleted=True)


@router.get(
    "/{media_id}/replay",
    response_model=VideoReplayManifestResponse,
    responses=_ERROR_RESPONSES,
)
def get_replay_manifest(
    request: Request, media_id: str
) -> VideoReplayManifestResponse | JSONResponse:
    """Return a media-ID-based replay manifest for the browser."""
    try:
        manifest = _media_service(request).get_replay_manifest(media_id)
    except MediaApplicationError as exc:
        return _error_response(exc, status_code=_status_code_for_error(exc))
    return VideoReplayManifestResponse.from_manifest(manifest)


@router.get("/{media_id}/content", response_model=None, responses=_ERROR_RESPONSES)
def get_video_content(
    request: Request,
    media_id: str,
    range_header: Annotated[str | None, Header(alias="Range")] = None,
) -> FileResponse | StreamingResponse | JSONResponse:
    """Serve stored video content with explicit HTTP byte-range support."""
    service = _media_service(request)
    try:
        location = service.get_video_content_location(media_id)
        if range_header is None:
            return FileResponse(
                location.path,
                media_type=location.media_type,
                headers={"Accept-Ranges": "bytes"},
            )

        byte_range = parse_range_header(range_header, location.file_size_bytes)
    except InvalidRangeError as exc:
        return _range_error_response(exc, file_size=_file_size_if_available(request, media_id))
    except MediaApplicationError as exc:
        return _error_response(exc, status_code=_status_code_for_error(exc))

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Range": (f"bytes {byte_range.start}-{byte_range.end}/{location.file_size_bytes}"),
        "Content-Length": str(byte_range.length),
    }
    return StreamingResponse(
        _iter_file_range(location, byte_range),
        status_code=206,
        media_type=location.media_type,
        headers=headers,
    )


def parse_range_header(range_header: str, file_size: int) -> ByteRange:
    """Parse one HTTP byte range into an inclusive start/end pair."""
    if file_size < 1 or not range_header.startswith("bytes=") or "," in range_header:
        raise InvalidRangeError()

    spec = range_header.removeprefix("bytes=").strip()
    start_text, separator, end_text = spec.partition("-")
    if separator != "-":
        raise InvalidRangeError()

    if start_text == "":
        suffix_length = _parse_non_negative_int(end_text)
        if suffix_length < 1:
            raise InvalidRangeError()
        if suffix_length >= file_size:
            return ByteRange(start=0, end=file_size - 1)
        return ByteRange(start=file_size - suffix_length, end=file_size - 1)

    start = _parse_non_negative_int(start_text)
    end = file_size - 1 if end_text == "" else _parse_non_negative_int(end_text)
    if start >= file_size or end >= file_size or start > end:
        raise InvalidRangeError()
    return ByteRange(start=start, end=end)


def _parse_non_negative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise InvalidRangeError() from exc
    if parsed < 0:
        raise InvalidRangeError()
    return parsed


def _iter_file_range(location: VideoContentLocation, byte_range: ByteRange) -> Iterator[bytes]:
    remaining = byte_range.length
    with location.path.open("rb") as file:
        file.seek(byte_range.start)
        while remaining > 0:
            chunk = file.read(min(_CONTENT_CHUNK_SIZE, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


def _media_service(request: Request) -> VideoLibraryApplicationService:
    service = request.app.state.video_library_service
    if service is None:
        service = create_video_library_application_service(request.app.state.settings)
        request.app.state.video_library_service = service
    if not isinstance(service, VideoLibraryApplicationService):
        msg = "media service is not configured"
        raise HTTPException(status_code=500, detail=msg)
    return service


def _error_response(error: MediaApplicationError, *, status_code: int) -> JSONResponse:
    payload = ErrorResponse(error=ErrorDetail(code=error.error_code, message=error.message))
    return JSONResponse(status_code=status_code, content=payload.model_dump())


def _range_error_response(error: InvalidRangeError, *, file_size: int | None) -> JSONResponse:
    headers = {"Accept-Ranges": "bytes"}
    if file_size is not None:
        headers["Content-Range"] = f"bytes */{file_size}"
    payload = ErrorResponse(error=ErrorDetail(code=error.error_code, message=error.message))
    return JSONResponse(status_code=416, content=payload.model_dump(), headers=headers)


def _status_code_for_error(error: MediaApplicationError) -> int:
    if isinstance(error, InvalidMediaIdError):
        return 404
    if isinstance(error, MissingMediaFileError):
        return 404
    if isinstance(error, FileTooLargeError):
        return 413
    if isinstance(error, EmptyUploadError):
        return 400
    if isinstance(error, UploadRequestError):
        return 400
    if isinstance(error, UnreadableVideoError):
        return 422
    if isinstance(error, StorageWriteError):
        return 507
    return 500


def _file_size_if_available(request: Request, media_id: str) -> int | None:
    try:
        return _media_service(request).get_video_content_location(media_id).file_size_bytes
    except MediaApplicationError:
        return None
