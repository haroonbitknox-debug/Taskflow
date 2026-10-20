from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user, require_csrf
from app.db.session import get_db
from app.models import User
from app.schemas.files import FileMetadata, FilePage, FileSearchPage
from app.services.file_service import (
    FileServiceError,
    delete_file,
    download_path,
    get_file_metadata,
    list_files,
    retry_indexing,
    search_files,
    upload_file,
)

router = APIRouter(prefix="/files", tags=["files"])


def _raise_service_error(error: FileServiceError) -> None:
    raise HTTPException(status_code=error.status_code, detail=str(error)) from error


@router.post(
    "/upload",
    response_model=FileMetadata,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def upload_spreadsheet(
    upload: UploadFile = File(...),
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> FileMetadata:
    try:
        return await upload_file(db, user, upload)
    except FileServiceError as exc:
        _raise_service_error(exc)
    finally:
        await upload.close()


@router.get("/search", response_model=FileSearchPage)
def search_spreadsheets(
    q: str = Query(min_length=1, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    file_id: int | None = Query(default=None, gt=0),
    extension: str | None = Query(default=None, pattern=r"^\.(xlsx|xls|csv)$"),
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> FileSearchPage:
    if not q.strip():
        raise HTTPException(status_code=422, detail="Search query cannot be blank.")
    return search_files(db, user.id, q, page, page_size, file_id, extension)


@router.get("", response_model=FilePage)
def get_files(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    extension: str | None = Query(default=None, pattern=r"^\.(xlsx|xls|csv)$"),
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> FilePage:
    return list_files(db, user.id, page, page_size, extension)


@router.get("/{file_id}/status", response_model=FileMetadata)
def get_processing_status(
    file_id: int,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> FileMetadata:
    try:
        return get_file_metadata(db, file_id, user.id)
    except FileServiceError as exc:
        _raise_service_error(exc)


@router.post(
    "/{file_id}/retry",
    response_model=FileMetadata,
    dependencies=[Depends(require_csrf)],
)
def retry_file_indexing(
    file_id: int,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> FileMetadata:
    try:
        return retry_indexing(db, file_id, user.id)
    except FileServiceError as exc:
        _raise_service_error(exc)


@router.get("/{file_id}/download")
def download_spreadsheet(
    file_id: int,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    try:
        path, file = download_path(db, file_id, user.id)
    except FileServiceError as exc:
        _raise_service_error(exc)
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=file.original_filename,
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; sandbox",
        },
    )


@router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
def remove_spreadsheet(
    file_id: int,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Response:
    try:
        delete_file(db, file_id, user.id)
    except FileServiceError as exc:
        _raise_service_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{file_id}", response_model=FileMetadata)
def file_details(
    file_id: int,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> FileMetadata:
    try:
        return get_file_metadata(db, file_id, user.id)
    except FileServiceError as exc:
        _raise_service_error(exc)
