"""Reader self-service: no caller-controlled owner IDs."""

from uuid import UUID

from fastapi import APIRouter, Request, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import Authenticated, Principal
from app.api.v1.routes.catalog import PageNumber, PageSize, Reader, mutations
from app.core.auth_http import audit_context
from app.core.rate_limit import consume
from app.db.models.engagement import Favorite
from app.repositories import reader as repository
from app.schemas.auth import ErrorResponse, UserResponse
from app.schemas.catalog import BookRead, Page
from app.schemas.reader import (
    FavoriteState,
    NotificationRead,
    PreferenceInput,
    Preferences,
    ProfileInput,
    ReaderSummary,
)
from app.services.storage.images import MAX_IMAGE_BYTES, LocalImageStorage, validate_image
from app.services.users.profile import ProfileService
from app.services.users.reader import ReaderService

router = APIRouter(
    prefix="/api/v1",
    tags=["Reader and profile"],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 404, 413, 422, 429)},
)


def service(request: Request, principal: Principal) -> ReaderService:
    consume(request, "reader-write", str(principal.user.id), 120, 60)
    return ReaderService(
        request.app.state.db, request.app.state.settings, audit_context(request), principal
    )


def profile_service(request: Request, principal: Principal) -> ProfileService:
    consume(request, "profile-write", str(principal.user.id), 30, 60)
    return ProfileService(
        request.app.state.db, request.app.state.settings, audit_context(request), principal
    )


@router.get("/favorites", response_model=Page[BookRead])
def favorites(
    request: Request, principal: Reader, page: PageNumber = 1, page_size: PageSize = 20
) -> Page[BookRead]:
    with Session(request.app.state.db) as db:
        return repository.favorite_page(db, principal.user.id, page, page_size)


@router.get("/favorites/{book_id}", response_model=FavoriteState)
def favorite_state(book_id: UUID, request: Request, principal: Reader) -> FavoriteState:
    with Session(request.app.state.db) as db:
        return FavoriteState(
            is_favorite=db.scalar(
                select(Favorite.id).where(
                    Favorite.user_id == principal.user.id, Favorite.book_id == book_id
                )
            )
            is not None
        )


@router.post("/favorites/{book_id}", status_code=204, dependencies=mutations)
def favorite(book_id: UUID, request: Request, principal: Reader) -> Response:
    service(request, principal).favorite(book_id, True)
    return Response(status_code=204)


@router.delete("/favorites/{book_id}", status_code=204, dependencies=mutations)
def unfavorite(book_id: UUID, request: Request, principal: Reader) -> Response:
    service(request, principal).favorite(book_id, False)
    return Response(status_code=204)


@router.get("/notifications", response_model=Page[NotificationRead])
def notifications(
    request: Request,
    principal: Reader,
    page: PageNumber = 1,
    page_size: PageSize = 20,
    unread: bool = False,
) -> Page[NotificationRead]:
    with Session(request.app.state.db) as db:
        return repository.notification_page(db, principal.user.id, page, page_size, unread)


@router.patch(
    "/notifications/{identity}/read", response_model=NotificationRead, dependencies=mutations
)
def read_notification(identity: UUID, request: Request, principal: Reader) -> NotificationRead:
    return service(request, principal).read_notification(identity)


@router.post("/notifications/read-all", status_code=204, dependencies=mutations)
def read_all(request: Request, principal: Reader) -> Response:
    service(request, principal).read_all()
    return Response(status_code=204)


@router.get("/reader/summary", response_model=ReaderSummary)
def summary(request: Request, principal: Reader) -> ReaderSummary:
    with Session(request.app.state.db) as db:
        return repository.summary(db, principal.user.id)


@router.get("/users/me", response_model=UserResponse)
def profile(principal: Authenticated) -> UserResponse:
    return UserResponse.model_validate(principal.user)


@router.patch("/users/me", response_model=UserResponse, dependencies=mutations)
def update_profile(data: ProfileInput, request: Request, principal: Authenticated) -> UserResponse:
    return profile_service(request, principal).update(data)


@router.get("/users/me/preferences", response_model=Preferences)
def preferences(request: Request, principal: Reader) -> Preferences:
    with Session(request.app.state.db) as db:
        return repository.preferences(db, principal.user.id)


@router.patch("/users/me/preferences", response_model=Preferences, dependencies=mutations)
def update_preferences(data: PreferenceInput, request: Request, principal: Reader) -> Preferences:
    return service(request, principal).set_preferences(data.category_ids)


@router.post("/users/me/avatar", response_model=UserResponse, dependencies=mutations)
async def avatar(file: UploadFile, request: Request, principal: Authenticated) -> UserResponse:
    operation = profile_service(request, principal)
    try:
        content = await file.read(MAX_IMAGE_BYTES + 1)
        decoded = await run_in_threadpool(validate_image, content, file.content_type)
        return await run_in_threadpool(
            operation.avatar,
            decoded,
            LocalImageStorage(request.app.state.settings.upload_directory),
        )
    finally:
        await file.close()


@router.delete("/users/me/avatar", response_model=UserResponse, dependencies=mutations)
def remove_avatar(request: Request, principal: Authenticated) -> UserResponse:
    return profile_service(request, principal).avatar(
        None, LocalImageStorage(request.app.state.settings.upload_directory)
    )
