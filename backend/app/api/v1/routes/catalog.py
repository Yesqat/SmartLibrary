"""Public catalog reads and bearer-authenticated staff metadata operations."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import OptionalPrincipal, Principal, require_permission
from app.core.auth_http import audit_context, check_origin
from app.core.errors import AppError
from app.core.permissions import Permission, authorize
from app.core.rate_limit import consume
from app.repositories.catalog import get_book, list_books, list_copies
from app.schemas.auth import ErrorResponse
from app.schemas.catalog import (
    ArchiveInput,
    BookCreate,
    BookPatch,
    BookRead,
    BookViewInput,
    CopyCreate,
    CopyPatch,
    CopyRead,
    Page,
)
from app.services.catalog.service import CatalogService
from app.services.storage.images import MAX_IMAGE_BYTES, LocalImageStorage, validate_image

router = APIRouter(
    prefix="/api/v1",
    tags=["Catalog"],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 413, 422, 429, 503)},
)
Staff = Annotated[Principal, Depends(require_permission(Permission.MANAGE_CATALOG))]
Reader = Annotated[Principal, Depends(require_permission(Permission.READ_PERSONAL))]
PageNumber = Annotated[int, Query(ge=1, le=100000)]
PageSize = Annotated[int, Query(ge=1, le=100)]
SearchText = Annotated[str, Query(max_length=500)]


def mutation_origin(request: Request) -> None:
    check_origin(request)


mutations = [Depends(mutation_origin)]


def check_archived(include_archived: bool, principal: Principal | None) -> None:
    if include_archived:
        if not principal:
            raise AppError("UNAUTHORIZED", "Жүйеге кіріңіз.", 401)
        authorize(principal.user.role, Permission.MANAGE_CATALOG)


def service(request: Request, principal: Principal) -> CatalogService:
    return CatalogService(
        request.app.state.db, request.app.state.settings, audit_context(request), principal
    )


@router.get("/books", response_model=Page[BookRead])
def books(
    request: Request,
    principal: OptionalPrincipal,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    q: SearchText = "",
    include_archived: bool = False,
) -> Page[BookRead]:
    check_archived(include_archived, principal)
    with Session(request.app.state.db) as db:
        return list_books(db, page, page_size, q.strip(), include_archived)


@router.get("/books/{book_id}", response_model=BookRead)
def book(
    book_id: UUID, request: Request, principal: OptionalPrincipal, include_archived: bool = False
) -> BookRead:
    check_archived(include_archived, principal)
    with Session(request.app.state.db) as db:
        return get_book(db, book_id, include_archived)


@router.post("/books", response_model=BookRead, status_code=201, dependencies=mutations)
def create_book(data: BookCreate, request: Request, principal: Staff) -> BookRead:
    return service(request, principal).book_write(data)


@router.patch("/books/{book_id}", response_model=BookRead, dependencies=mutations)
def update_book(book_id: UUID, data: BookPatch, request: Request, principal: Staff) -> BookRead:
    return service(request, principal).book_write(data, book_id)


@router.patch("/books/{book_id}/archive", response_model=BookRead, dependencies=mutations)
def archive_book(book_id: UUID, data: ArchiveInput, request: Request, principal: Staff) -> BookRead:
    return service(request, principal).book_archive(book_id, data.archived)


@router.get("/books/{book_id}/copies", response_model=Page[CopyRead])
def copies(
    book_id: UUID,
    request: Request,
    principal: Staff,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    include_archived: bool = False,
) -> Page[CopyRead]:
    with Session(request.app.state.db) as db:
        return list_copies(db, book_id, page, page_size, include_archived)


@router.post(
    "/books/{book_id}/copies", response_model=CopyRead, status_code=201, dependencies=mutations
)
def create_copy(book_id: UUID, data: CopyCreate, request: Request, principal: Staff) -> CopyRead:
    return service(request, principal).copy_write(data, book_id=book_id)


@router.patch("/copies/{copy_id}", response_model=CopyRead, dependencies=mutations)
def update_copy(copy_id: UUID, data: CopyPatch, request: Request, principal: Staff) -> CopyRead:
    return service(request, principal).copy_write(data, identity=copy_id)


@router.patch("/copies/{copy_id}/archive", response_model=CopyRead, dependencies=mutations)
def archive_copy(copy_id: UUID, data: ArchiveInput, request: Request, principal: Staff) -> CopyRead:
    return service(request, principal).copy_write(
        CopyPatch(), identity=copy_id, archive=data.archived
    )


@router.post("/books/{book_id}/cover", response_model=BookRead, dependencies=mutations)
async def upload_cover(
    book_id: UUID, file: UploadFile, request: Request, principal: Staff
) -> BookRead:
    try:
        consume(request, "cover-upload", str(principal.user.id), 30, 60)
        content = await file.read(MAX_IMAGE_BYTES + 1)
        decoded = await run_in_threadpool(validate_image, content, file.content_type)
        return await run_in_threadpool(
            service(request, principal).cover_write,
            book_id,
            decoded,
            LocalImageStorage(request.app.state.settings.upload_directory),
        )
    finally:
        await file.close()


@router.delete("/books/{book_id}/cover", response_model=BookRead, dependencies=mutations)
def remove_cover(book_id: UUID, request: Request, principal: Staff) -> BookRead:
    return service(request, principal).cover_write(
        book_id, None, LocalImageStorage(request.app.state.settings.upload_directory)
    )


@router.get("/media/{filename}", response_class=Response)
def media(filename: str, request: Request) -> FileResponse:
    path = LocalImageStorage(request.app.state.settings.upload_directory).path(filename)
    if not path.is_file():
        raise AppError("NOT_FOUND", "Сурет табылмады.", 404)
    return FileResponse(
        path,
        media_type="image/webp",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.post("/books/{book_id}/views", status_code=204, dependencies=mutations)
def record_book_view(
    book_id: UUID, data: BookViewInput, request: Request, principal: Reader
) -> Response:
    service(request, principal).record_view(book_id, data.event_id)
    return Response(status_code=204)
