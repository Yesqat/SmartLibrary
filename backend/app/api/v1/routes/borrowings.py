from fastapi import APIRouter, Request
from sqlalchemy.orm import Session

from app.api.v1.routes.catalog import PageNumber, PageSize, Reader
from app.repositories.borrowings import borrowing_page
from app.schemas.auth import ErrorResponse
from app.schemas.catalog import Page
from app.schemas.circulation import BorrowingView

router = APIRouter(
    prefix="/api/v1/borrowings",
    tags=["My borrowings"],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 422)},
)


@router.get("/me/active", response_model=Page[BorrowingView])
def active(
    request: Request, principal: Reader, page: PageNumber = 1, page_size: PageSize = 20
) -> Page[BorrowingView]:
    with Session(request.app.state.db) as db:
        return borrowing_page(db, page, page_size, user_id=principal.user.id, active=True)


@router.get("/me/history", response_model=Page[BorrowingView])
def history(
    request: Request, principal: Reader, page: PageNumber = 1, page_size: PageSize = 20
) -> Page[BorrowingView]:
    with Session(request.app.state.db) as db:
        return borrowing_page(db, page, page_size, user_id=principal.user.id, active=False)
