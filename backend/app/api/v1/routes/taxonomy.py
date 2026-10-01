"""Typed taxonomy endpoints share the same lifecycle service."""

from uuid import UUID

from fastapi import APIRouter, Request
from sqlalchemy.orm import Session

from app.api.dependencies import OptionalPrincipal
from app.api.v1.routes.catalog import (
    PageNumber,
    PageSize,
    SearchText,
    Staff,
    check_archived,
    mutations,
    service,
)
from app.core.errors import AppError
from app.db.models.catalog import Author, Category, Publisher
from app.schemas.auth import ErrorResponse
from app.schemas.catalog import (
    ArchiveInput,
    AuthorCreate,
    AuthorPatch,
    AuthorRead,
    CategoryCreate,
    CategoryPatch,
    CategoryRead,
    Page,
    PublisherCreate,
    PublisherPatch,
    PublisherRead,
)
from app.services.catalog.service import taxonomy_page

router = APIRouter(
    prefix="/api/v1",
    tags=["Catalog references"],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 422)},
)


@router.get("/authors/{identity}", response_model=AuthorRead)
def get_authors(
    identity: UUID, request: Request, principal: OptionalPrincipal, include_archived: bool = False
) -> AuthorRead:
    check_archived(include_archived, principal)
    with Session(request.app.state.db) as db:
        row = db.get(Author, identity)
        if row is None or (row.archived_at and not include_archived):
            raise AppError("AUTHOR_NOT_FOUND", "Жазба табылмады.", 404)
        return AuthorRead.model_validate(row)


@router.get("/categories/{identity}", response_model=CategoryRead)
def get_categories(
    identity: UUID, request: Request, principal: OptionalPrincipal, include_archived: bool = False
) -> CategoryRead:
    check_archived(include_archived, principal)
    with Session(request.app.state.db) as db:
        row = db.get(Category, identity)
        if row is None or (row.archived_at and not include_archived):
            raise AppError("CATEGORY_NOT_FOUND", "Жазба табылмады.", 404)
        return CategoryRead.model_validate(row)


@router.get("/publishers/{identity}", response_model=PublisherRead)
def get_publishers(
    identity: UUID, request: Request, principal: OptionalPrincipal, include_archived: bool = False
) -> PublisherRead:
    check_archived(include_archived, principal)
    with Session(request.app.state.db) as db:
        row = db.get(Publisher, identity)
        if row is None or (row.archived_at and not include_archived):
            raise AppError("PUBLISHER_NOT_FOUND", "Жазба табылмады.", 404)
        return PublisherRead.model_validate(row)


@router.get("/authors", response_model=Page[AuthorRead])
def list_authors(
    request: Request,
    principal: OptionalPrincipal,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    q: SearchText = "",
    include_archived: bool = False,
) -> Page[AuthorRead]:
    check_archived(include_archived, principal)
    with Session(request.app.state.db) as db:
        return taxonomy_page(
            db, "authors", AuthorRead, page, page_size, q.strip(), include_archived
        )


@router.post("/authors", response_model=AuthorRead, status_code=201, dependencies=mutations)
def create_authors(data: AuthorCreate, request: Request, principal: Staff) -> AuthorRead:
    return AuthorRead.model_validate(service(request, principal).taxonomy_write("authors", data))


@router.patch("/authors/{identity}", response_model=AuthorRead, dependencies=mutations)
def update_authors(
    identity: UUID, data: AuthorPatch, request: Request, principal: Staff
) -> AuthorRead:
    return AuthorRead.model_validate(
        service(request, principal).taxonomy_write("authors", data, identity)
    )


@router.patch("/authors/{identity}/archive", response_model=AuthorRead, dependencies=mutations)
def archive_authors(
    identity: UUID, data: ArchiveInput, request: Request, principal: Staff
) -> AuthorRead:
    return AuthorRead.model_validate(
        service(request, principal).taxonomy_write("authors", data, identity, data.archived)
    )


@router.get("/categories", response_model=Page[CategoryRead])
def list_categories(
    request: Request,
    principal: OptionalPrincipal,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    q: SearchText = "",
    include_archived: bool = False,
) -> Page[CategoryRead]:
    check_archived(include_archived, principal)
    with Session(request.app.state.db) as db:
        return taxonomy_page(
            db, "categories", CategoryRead, page, page_size, q.strip(), include_archived
        )


@router.post("/categories", response_model=CategoryRead, status_code=201, dependencies=mutations)
def create_categories(data: CategoryCreate, request: Request, principal: Staff) -> CategoryRead:
    return CategoryRead.model_validate(
        service(request, principal).taxonomy_write("categories", data)
    )


@router.patch("/categories/{identity}", response_model=CategoryRead, dependencies=mutations)
def update_categories(
    identity: UUID, data: CategoryPatch, request: Request, principal: Staff
) -> CategoryRead:
    return CategoryRead.model_validate(
        service(request, principal).taxonomy_write("categories", data, identity)
    )


@router.patch("/categories/{identity}/archive", response_model=CategoryRead, dependencies=mutations)
def archive_categories(
    identity: UUID, data: ArchiveInput, request: Request, principal: Staff
) -> CategoryRead:
    return CategoryRead.model_validate(
        service(request, principal).taxonomy_write("categories", data, identity, data.archived)
    )


@router.get("/publishers", response_model=Page[PublisherRead])
def list_publishers(
    request: Request,
    principal: OptionalPrincipal,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    q: SearchText = "",
    include_archived: bool = False,
) -> Page[PublisherRead]:
    check_archived(include_archived, principal)
    with Session(request.app.state.db) as db:
        return taxonomy_page(
            db, "publishers", PublisherRead, page, page_size, q.strip(), include_archived
        )


@router.post("/publishers", response_model=PublisherRead, status_code=201, dependencies=mutations)
def create_publishers(data: PublisherCreate, request: Request, principal: Staff) -> PublisherRead:
    return PublisherRead.model_validate(
        service(request, principal).taxonomy_write("publishers", data)
    )


@router.patch("/publishers/{identity}", response_model=PublisherRead, dependencies=mutations)
def update_publishers(
    identity: UUID, data: PublisherPatch, request: Request, principal: Staff
) -> PublisherRead:
    return PublisherRead.model_validate(
        service(request, principal).taxonomy_write("publishers", data, identity)
    )


@router.patch(
    "/publishers/{identity}/archive", response_model=PublisherRead, dependencies=mutations
)
def archive_publishers(
    identity: UUID, data: ArchiveInput, request: Request, principal: Staff
) -> PublisherRead:
    return PublisherRead.model_validate(
        service(request, principal).taxonomy_write("publishers", data, identity, data.archived)
    )
