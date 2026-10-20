from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class FileMetadata(BaseModel):
    id: int
    original_filename: str
    extension: str
    mime_type: str
    file_size: int
    created_at: datetime
    processing_status: str
    indexing_status: str
    indexed_entry_count: int
    processing_error: str | None = None


class FilePage(BaseModel):
    items: list[FileMetadata]
    total: int
    page: int
    page_size: int


class FileSearchHit(BaseModel):
    file_id: int
    original_filename: str
    extension: str
    worksheet_name: str | None = None
    row_number: int | None = None
    column_name: str | None = None
    match_type: Literal["filename", "worksheet", "content"]
    excerpt: str
    created_at: datetime


class FileSearchPage(BaseModel):
    items: list[FileSearchHit]
    total: int
    page: int
    page_size: int
