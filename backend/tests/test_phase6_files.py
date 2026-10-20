from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import FileIndexEntry, UploadedFile, User, UserRole
from app.services import file_service
from app.utils.passwords import hash_password
from app.utils.tokens import create_access_token
from tests.test_phase4 import USER_PASSWORD, create_account, csrf


@pytest.fixture()
def file_storage_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(file_service, "UPLOADS_BASE", tmp_path)
    return tmp_path / "uploads" / "user-files"


def make_xlsx() -> bytes:
    workbook = Workbook()
    first = workbook.active
    first.title = "Invoices"
    first.append(["Invoice", "Customer", "Amount"])
    first.append(["1045", "Northwind", 250])
    first.append(["1046", "Contoso", 400])
    second = workbook.create_sheet("Notes")
    second.append(["Topic", "Comment"])
    second.append(["Payment", "Invoice 1045 is due"])
    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def test_csv_upload_is_indexed_and_search_returns_cell_references(
    client: TestClient,
    file_storage_root: Path,
) -> None:
    create_account(client, "File Owner", "file.owner@example.test")
    response = client.post(
        "/api/files/upload",
        files={"upload": ("invoices.csv", "Invoice,Customer\n1045,Northwind\n", "text/csv")},
        headers=csrf(client),
    )
    assert response.status_code == 201, response.text
    metadata = response.json()
    assert metadata["original_filename"] == "invoices.csv"
    assert metadata["processing_status"] == "ready"
    assert metadata["indexed_entry_count"] == 2
    assert "relative_path" not in metadata and str(file_storage_root) not in response.text

    results = client.get("/api/files/search?q=invoice%201045")
    assert results.status_code == 200
    hit = next(item for item in results.json()["items"] if item["row_number"] == 2)
    assert hit["original_filename"] == "invoices.csv"
    assert hit["worksheet_name"] == "CSV"
    assert hit["column_name"] == "Invoice"
    assert "1045" in hit["excerpt"]
    assert client.get("/api/files/search?q=no-such-value").json()["total"] == 0
    assert client.get("/api/files/search?q=%25").json()["total"] == 0
    assert client.get("/api/files/search?q=%20").status_code == 422


def test_xlsx_multiple_worksheets_and_headers_are_indexed(
    client: TestClient,
) -> None:
    create_account(client, "Workbook Owner", "workbook.owner@example.test")
    uploaded = client.post(
        "/api/files/upload",
        files={"upload": ("workbook.xlsx", make_xlsx(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=csrf(client),
    )
    assert uploaded.status_code == 201, uploaded.text
    assert uploaded.json()["indexed_entry_count"] == 8

    results = client.get("/api/files/search?q=1045")
    assert results.status_code == 200
    hits = results.json()["items"]
    assert any(
        hit["worksheet_name"] == "Invoices"
        and hit["row_number"] == 2
        and hit["column_name"] == "Invoice"
        for hit in hits
    )
    notes = client.get("/api/files/search?q=invoice&extension=.xlsx")
    assert any(hit["worksheet_name"] == "Notes" for hit in notes.json()["items"])


@pytest.mark.parametrize(
    ("filename", "content", "mime", "message"),
    [
        ("report.exe", b"not a spreadsheet", "application/octet-stream", "Only .xlsx"),
        ("broken.xlsx", b"not a workbook", "application/octet-stream", "valid XLSX"),
        ("broken.xls", b"not an XLS workbook", "application/vnd.ms-excel", "legacy XLS"),
        ("wrong.csv", b"name,value\nx,1\n", "application/pdf", "content type"),
        ("invalid.csv", b"name,value\n\xff,1\n", "text/csv", "UTF-8"),
        ("binary.csv", b"name\nvalue\x00\n", "text/csv", "null bytes"),
    ],
)
def test_rejects_unsupported_mime_or_malformed_files(
    client: TestClient,
    filename: str,
    content: bytes,
    mime: str,
    message: str,
) -> None:
    create_account(client, "Validation Owner", f"{filename.replace('.', '-') }@example.test")
    response = client.post(
        "/api/files/upload",
        files={"upload": (filename, content, mime)},
        headers=csrf(client),
    )
    assert response.status_code == 422
    assert message.casefold() in response.json()["detail"].casefold()


def test_upload_size_and_spreadsheet_limits(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_account(client, "Limit Owner", "limit.owner@example.test")
    monkeypatch.setattr(settings, "file_max_size_bytes", 16)
    oversized = client.post(
        "/api/files/upload",
        files={"upload": ("large.csv", b"header\n" + b"x" * 40, "text/csv")},
        headers=csrf(client),
    )
    assert oversized.status_code == 422
    monkeypatch.setattr(settings, "file_max_size_bytes", 10 * 1024 * 1024)
    monkeypatch.setattr(settings, "file_max_rows", 1)
    too_many_rows = client.post(
        "/api/files/upload",
        files={"upload": ("rows.csv", "name\none\ntwo\n", "text/csv")},
        headers=csrf(client),
    )
    assert too_many_rows.status_code == 422
    assert "row limit" in too_many_rows.json()["detail"]
    monkeypatch.setattr(settings, "file_max_worksheets", 1)
    too_many_sheets = client.post(
        "/api/files/upload",
        files={"upload": ("sheets.xlsx", make_xlsx(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=csrf(client),
    )
    assert too_many_sheets.status_code == 422
    assert "worksheet limit" in too_many_sheets.json()["detail"]


def test_path_traversal_filename_is_reduced_to_a_basename(
    client: TestClient,
) -> None:
    create_account(client, "Path Owner", "path.owner@example.test")
    response = client.post(
        "/api/files/upload",
        files={"upload": ("..\\outside.csv", "name\nvalue\n", "text/csv")},
        headers=csrf(client),
    )
    assert response.status_code == 201, response.text
    assert response.json()["original_filename"] == "outside.csv"
    assert ".." not in response.json()["original_filename"]


def test_ownership_download_delete_and_cascade(
    client: TestClient,
    db_session: Session,
    file_storage_root: Path,
) -> None:
    owner_data = create_account(client, "Private Owner", "private.owner@example.test")
    uploaded = client.post(
        "/api/files/upload",
        files={"upload": ("private.csv", "name\nsecret\n", "text/csv")},
        headers=csrf(client),
    )
    file_id = uploaded.json()["id"]
    stored_file = next(file_storage_root.rglob("*.csv"))

    intruder = User(
        full_name="Another User",
        email="another.file.user@example.test",
        password_hash=hash_password(USER_PASSWORD),
    )
    db_session.add(intruder)
    db_session.commit()
    other_client = TestClient(client.app)
    other_client.cookies.set("taskflow_access", create_access_token(str(intruder.id)))
    csrf(other_client)

    assert other_client.get(f"/api/files/{file_id}").status_code == 404
    assert other_client.get(f"/api/files/{file_id}/download").status_code == 404
    assert other_client.get(f"/api/files/search?q=secret").json()["total"] == 0
    assert other_client.delete(f"/api/files/{file_id}", headers=csrf(other_client)).status_code == 404

    admin = User(
        full_name="File Privacy Admin",
        email="file.privacy.admin@example.test",
        password_hash=hash_password(USER_PASSWORD),
        role=UserRole.ADMIN,
    )
    db_session.add(admin)
    db_session.commit()
    admin_client = TestClient(client.app)
    admin_client.cookies.set("taskflow_access", create_access_token(str(admin.id)))
    csrf(admin_client)
    assert admin_client.get(f"/api/files/{file_id}").status_code == 404
    assert admin_client.get("/api/files/search?q=secret").json()["total"] == 0

    download = client.get(f"/api/files/{file_id}/download")
    assert download.status_code == 200
    assert download.headers["content-disposition"].endswith('filename="private.csv"')
    assert download.headers["x-content-type-options"] == "nosniff"
    assert client.delete(f"/api/files/{file_id}", headers=csrf(client)).status_code == 204
    assert not stored_file.exists()
    assert db_session.scalar(select(func.count(FileIndexEntry.id)).where(FileIndexEntry.uploaded_file_id == file_id)) == 0
    assert db_session.get(UploadedFile, file_id) is None
    assert owner_data["id"] != intruder.id


def test_file_endpoints_require_authentication(client: TestClient) -> None:
    unauthenticated = TestClient(client.app)
    assert unauthenticated.get("/api/files").status_code == 401
    assert unauthenticated.get("/api/files/search?q=private").status_code == 401
    assert unauthenticated.get("/api/files/1/download").status_code == 401


def test_indexing_failure_can_be_retried_safely(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_account(client, "Retry Owner", "retry.owner@example.test")
    original_reader = file_service._cell_rows

    def fail_processing(path, extension):
        raise RuntimeError("private internal exception detail")
        yield

    monkeypatch.setattr(file_service, "_cell_rows", fail_processing)
    uploaded = client.post(
        "/api/files/upload",
        files={"upload": ("retry.csv", "name\nvalue\n", "text/csv")},
        headers=csrf(client),
    )
    assert uploaded.status_code == 201
    assert uploaded.json()["processing_status"] == "failed"
    assert "private internal" not in str(uploaded.json())
    monkeypatch.setattr(file_service, "_cell_rows", original_reader)

    retried = client.post(
        f"/api/files/{uploaded.json()['id']}/retry",
        headers=csrf(client),
    )
    assert retried.status_code == 200
    assert retried.json()["processing_status"] == "ready"
    assert retried.json()["indexed_entry_count"] == 1
