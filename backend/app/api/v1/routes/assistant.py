from uuid import UUID

from fastapi import APIRouter, Request
from sqlalchemy.orm import Session

from app.ai.assistant.service import AssistantService, conversation_list, detail
from app.api.v1.routes.catalog import PageNumber, PageSize, Reader, mutations
from app.core.auth_http import audit_context, client_ip
from app.core.errors import AppError
from app.core.rate_limit import consume
from app.schemas.assistant import (
    ConversationCreate,
    ConversationDetail,
    ConversationRead,
    MessageInput,
    MessageRead,
)
from app.schemas.auth import ErrorResponse
from app.schemas.catalog import Page

router = APIRouter(
    prefix="/api/v1/ai/conversations",
    tags=["AI assistant"],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 422, 429, 503)},
)


def service(request: Request, principal: Reader) -> AssistantService:
    return AssistantService(
        request.app.state.db, request.app.state.settings, principal, audit_context(request)
    )


def limit(request: Request, principal: Reader, action: str) -> None:
    try:
        consume(
            request, "ai-" + action, str(principal.user.id), 10 if action == "message" else 30, 60
        )
        if action == "message":
            consume(request, "ai-ip", client_ip(request), 30, 60)
            consume(request, "ai-daily", str(principal.user.id), 200, 86400)
    except AppError as error:
        if error.code == "AUTH_SERVICE_UNAVAILABLE":
            raise AppError(
                "AI_SERVICE_UNAVAILABLE", "AI көмекшісі уақытша қолжетімсіз.", 503
            ) from None
        raise


@router.post("", response_model=ConversationRead, status_code=201, dependencies=mutations)
def create(data: ConversationCreate, request: Request, principal: Reader) -> ConversationRead:
    limit(request, principal, "create")
    return service(request, principal).create(data.title)


@router.get("", response_model=Page[ConversationRead])
def listing(
    request: Request, principal: Reader, page: PageNumber = 1, page_size: PageSize = 20
) -> Page[ConversationRead]:
    with Session(request.app.state.db) as db:
        return conversation_list(db, principal.user.id, page, page_size)


@router.get("/{identity}", response_model=ConversationDetail)
def conversation(
    identity: UUID,
    request: Request,
    principal: Reader,
    page: PageNumber = 1,
    page_size: PageSize = 20,
) -> ConversationDetail:
    with Session(request.app.state.db) as db:
        return detail(db, identity, principal.user.id, page, page_size)


@router.post("/{identity}/messages", response_model=MessageRead, dependencies=mutations)
def send(identity: UUID, data: MessageInput, request: Request, principal: Reader) -> MessageRead:
    limit(request, principal, "message")
    return service(request, principal).send(identity, data)
