from datetime import UTC, datetime, timedelta
from io import BytesIO
from uuid import UUID, uuid4

import pytest
from openpyxl import load_workbook
from pypdf import PdfReader
from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session

from app.core.security import now
from app.db.enums import UserRole
from app.db.models import AuditLog, BookCopy, Borrowing
from app.tests.database.domain.test_catalog import BASE, create_book, create_copy
from app.tests.database.domain.test_reservations import reserve

pytestmark = pytest.mark.integration
URL = BASE + "/admin/reports"


@pytest.mark.parametrize("kind", ["inventory", "borrowings", "overdue", "reservations"])
@pytest.mark.parametrize("format", ["pdf", "xlsx"])
def test_real_report_files_match_persisted_rows(client, actor, domain_db, kind, format):
    staff, token = actor(UserRole.LIBRARIAN)
    title = "Қазақша Әлем Өнер Ғылым " + str(uuid4())[:8]
    book = create_book(client, title=title)
    copy = create_copy(client, book)
    reader, _ = actor(UserRole.READER)
    if kind == "reservations":
        reserve(client, book)
    if kind in {"borrowings", "overdue"}:
        client.headers["Authorization"] = "Bearer " + token
        response = client.post(
            BASE + "/librarian/borrowings",
            json={
                "book_copy_id": copy["id"],
                "user_id": reader["id"],
                "idempotency_key": str(uuid4()),
            },
        )
        assert response.status_code == 200, response.text
        with Session(domain_db) as db, db.begin():
            db.execute(
                update(Borrowing)
                .where(Borrowing.id == UUID(response.json()["id"]))
                .values(borrowed_at=now() - timedelta(days=2), due_at=now() - timedelta(days=1))
            )
    admin, _ = actor(UserRole.ADMIN)
    result = client.post(URL, json={"report_type": kind, "format": format})
    assert result.status_code == 200, result.text[:150] if not result.is_success else ""
    assert result.headers["cache-control"] == "no-store"
    assert f"smartlibrary_{kind}_" in result.headers["content-disposition"]
    assert int(result.headers["x-report-rows"]) >= 1
    if format == "pdf":
        document = PdfReader(BytesIO(result.content))
        content = "\n".join(page.extract_text() for page in document.pages)
        assert title in content.replace("\n", " ")
        assert "Бет 1" in content
    else:
        workbook = load_workbook(BytesIO(result.content), data_only=False)
        rows = list(workbook["Жазбалар"].values)
        assert any(title in row for row in rows)
        assert len(rows) - 1 == int(result.headers["x-report-rows"])
        if kind == "overdue":
            assert all(row[-1] == "Мерзімі өткен" for row in rows[1:])
        assert all(cell.data_type != "f" for sheet in workbook for row in sheet for cell in row)
    with Session(domain_db) as db:
        assert db.scalar(
            select(AuditLog.id).where(
                AuditLog.user_id == UUID(admin["id"]), AuditLog.action == "REPORT_GENERATED"
            )
        )


def test_reports_rbac_validation_and_empty_output(client, actor):
    for role in [UserRole.READER, UserRole.LIBRARIAN]:
        actor(role)
        assert (
            client.post(URL, json={"report_type": "inventory", "format": "pdf"}).status_code == 403
        )
    actor(UserRole.ADMIN)
    for data in [
        {"report_type": "secrets", "format": "pdf"},
        {"report_type": "inventory", "format": "exe"},
        {
            "report_type": "borrowings",
            "format": "pdf",
            "date_from": "2025-02-01",
            "date_to": "2025-01-01",
        },
        {"report_type": "inventory", "format": "xlsx", "user_id": str(uuid4())},
    ]:
        assert client.post(URL, json=data).status_code == 422
    response = client.post(
        URL,
        json={
            "report_type": "borrowings",
            "format": "pdf",
            "date_from": "2080-01-01",
            "date_to": "2080-01-02",
        },
    )
    assert response.status_code == 200 and response.headers["x-report-rows"] == "0"
    assert "жазба жоқ" in PdfReader(BytesIO(response.content)).pages[0].extract_text()


def test_report_limit_rejects_without_silent_truncation(client, actor, domain_db):
    actor(UserRole.LIBRARIAN)
    book = create_book(client)
    prefix = str(uuid4())
    with Session(domain_db) as db, db.begin():
        db.execute(
            insert(BookCopy),
            [
                {
                    "book_id": UUID(book["id"]),
                    "inventory_number": f"{prefix}-{i}",
                    "created_at": datetime(2021, 1, 1, tzinfo=UTC),
                }
                for i in range(5001)
            ],
        )
    actor(UserRole.ADMIN)
    response = client.post(
        URL,
        json={
            "report_type": "inventory",
            "format": "xlsx",
            "date_from": "2020-12-31",
            "date_to": "2021-01-02",
        },
    )
    assert response.status_code == 422 and response.json()["error"]["code"] == "REPORT_TOO_LARGE"
