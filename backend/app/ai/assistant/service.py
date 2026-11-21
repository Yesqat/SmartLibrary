"""Owned durable turns; short DB transactions surround bounded provider work."""

import json
import logging
from datetime import timedelta
from math import ceil
from time import perf_counter
from typing import Any
from uuid import UUID, uuid5

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.ai.assistant import provider
from app.ai.assistant.contracts import unavailable
from app.ai.assistant.orchestration import Answer, respond
from app.ai.assistant.tools import ToolContext
from app.api.dependencies import Principal
from app.core.config import Settings
from app.core.errors import AppError
from app.core.permissions import Permission, authorize
from app.core.security import now
from app.db.enums import MessageRole
from app.db.models import AIConversation, AIMessage, AIMessageBook, Book
from app.repositories.catalog import book_query, serialize
from app.schemas.assistant import ConversationDetail, ConversationRead, MessageInput, MessageRead
from app.schemas.catalog import Page
from app.services.audit.events import AuditContext
from app.services.auth.service import AuthService


def owned(db: Session, identity: UUID, user_id: UUID, lock: bool = False) -> AIConversation:
    query = select(AIConversation).where(
        AIConversation.id == identity, AIConversation.user_id == user_id
    )
    row = db.scalar(query.with_for_update() if lock else query)
    if row is None:
        raise AppError("NOT_FOUND", "Әңгіме табылмады.", 404)
    return row


def message_views(db: Session, messages: list[AIMessage]) -> list[MessageRead]:
    refs: dict[UUID, list[UUID]] = {}
    for message_id, book_id in db.execute(
        select(AIMessageBook.message_id, AIMessageBook.book_id)
        .where(AIMessageBook.message_id.in_([m.id for m in messages]))
        .order_by(AIMessageBook.position)
    ):
        refs.setdefault(message_id, []).append(book_id)
    identities = {b for values in refs.values() for b in values}
    books = (
        {
            row[0].id: serialize(*row)
            for row in db.execute(
                book_query().where(Book.id.in_(identities), Book.archived_at.is_(None))
            )
        }
        if identities
        else {}
    )
    return [
        MessageRead(
            id=m.id,
            role=m.role,
            content=m.content,
            created_at=m.created_at,
            error_code=m.error_code,
            books=[books[b] for b in refs.get(m.id, []) if b in books],
        )
        for m in messages
    ]


def conversation_list(db: Session, user_id: UUID, page: int, size: int) -> Page[ConversationRead]:
    query = select(AIConversation).where(AIConversation.user_id == user_id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(AIConversation.updated_at.desc(), AIConversation.id)
        .offset((page - 1) * size)
        .limit(size)
    )
    return Page(
        items=[ConversationRead.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=size,
        pages=ceil(total / size),
    )


def detail(db: Session, identity: UUID, user_id: UUID, page: int, size: int) -> ConversationDetail:
    conversation = owned(db, identity, user_id)
    query = select(AIMessage).where(AIMessage.conversation_id == identity)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = list(
        db.scalars(
            query.order_by(AIMessage.created_at.desc(), AIMessage.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
    )
    return ConversationDetail(
        conversation=ConversationRead.model_validate(conversation),
        messages=Page(
            items=message_views(db, list(reversed(rows))),
            total=total,
            page=page,
            page_size=size,
            pages=ceil(total / size),
        ),
    )


def context_history(db: Session, identity: UUID) -> list[dict[str, Any]]:
    rows = list(
        db.scalars(
            select(AIMessage)
            .where(AIMessage.conversation_id == identity)
            .order_by(AIMessage.created_at.desc(), AIMessage.id.desc())
            .limit(20)
        )
    )
    referenced_books: dict[UUID, list[dict[str, str]]] = {}
    for message_id, book_id, title in db.execute(
        select(AIMessageBook.message_id, Book.id, Book.title)
        .join(Book, Book.id == AIMessageBook.book_id)
        .where(AIMessageBook.message_id.in_([row.id for row in rows]), Book.archived_at.is_(None))
        .order_by(AIMessageBook.position)
    ):
        referenced_books.setdefault(message_id, []).append(
            {"book_id": str(book_id), "title": title}
        )
    history: list[dict[str, Any]] = []
    remaining = 16000
    for row in rows:
        # Carry book identities across turns. Availability and personal facts must be read again.
        text = (
            row.content
            if row.role == MessageRole.USER
            else json.dumps(
                {
                    "previous_intent": row.tool_metadata.get("kind", "unavailable"),
                    "books_previously_shown_in_order": referenced_books.get(row.id, []),
                },
                ensure_ascii=False,
            )
        )
        if len(text) > remaining:
            break
        remaining -= len(text)
        history.append({"role": row.role.value.lower(), "content": text})
    return list(reversed(history))


class AssistantService:
    def __init__(
        self, engine: Engine, settings: Settings, principal: Principal, context: AuditContext
    ):
        self.engine, self.settings, self.principal, self.context = (
            engine,
            settings,
            principal,
            context,
        )
        self.auth = AuthService(engine, settings, context)

    def authorize(self, db: Session) -> UUID:
        user = self.auth.require_live(db, self.principal.user.id, self.principal.family_id)
        authorize(user.role, Permission.READ_PERSONAL)
        return user.id

    def create(self, title: str | None) -> ConversationRead:
        with Session(self.engine) as db, db.begin():
            user_id = self.authorize(db)
            count = (
                db.scalar(
                    select(func.count())
                    .select_from(AIConversation)
                    .where(AIConversation.user_id == user_id)
                )
                or 0
            )
            if count >= 500:
                raise AppError("AI_LIMIT_REACHED", "Әңгіме санының шегіне жеттіңіз.", 409)
            row = AIConversation(user_id=user_id, title=title)
            db.add(row)
            db.flush()
            return ConversationRead.model_validate(row)

    def send(self, identity: UUID, data: MessageInput) -> MessageRead:
        user_message_id = uuid5(identity, "user:" + str(data.request_id))
        answer_id = uuid5(identity, "assistant:" + str(data.request_id))
        with Session(self.engine) as db, db.begin():
            user_id = self.authorize(db)
            conversation = owned(db, identity, user_id, True)
            prior = db.get(AIMessage, user_message_id)
            if prior and prior.content != data.content:
                raise AppError("IDEMPOTENCY_CONFLICT", "Сұраныс қайталануы сәйкес емес.", 409)
            if answer := db.get(AIMessage, answer_id):
                if answer.error_code:
                    raise unavailable()
                return message_views(db, [answer])[0]
            pending = list(
                db.scalars(
                    select(AIMessage).where(
                        AIMessage.conversation_id == identity,
                        AIMessage.role == MessageRole.USER,
                        AIMessage.tool_metadata["state"].astext == "pending",
                    )
                )
            )
            for pending_row in pending:
                if pending_row.created_at > now() - timedelta(seconds=120):
                    raise AppError("AI_TURN_IN_PROGRESS", "Алдыңғы жауап дайындалып жатыр.", 409)
                pending_row.tool_metadata = {"state": "interrupted"}
            if prior:
                raise AppError("AI_TURN_INTERRUPTED", "Сұранысты қайта жіберіңіз.", 409)
            count = (
                db.scalar(
                    select(func.count())
                    .select_from(AIMessage)
                    .where(AIMessage.conversation_id == identity)
                )
                or 0
            )
            if count >= 400:
                raise AppError("AI_LIMIT_REACHED", "Жаңа әңгіме бастаңыз.", 409)
            db.add(
                AIMessage(
                    id=user_message_id,
                    conversation_id=identity,
                    role=MessageRole.USER,
                    content=data.content,
                    tool_metadata={"state": "pending"},
                )
            )
            conversation.updated_at = now()
            if not conversation.title:
                conversation.title = data.content[:100]
            db.flush()
            history = context_history(db, identity)
        start = perf_counter()
        tools = ToolContext(self.engine, self.settings, self.principal, self.context)
        result: Answer | None = None
        failure: AppError | None = None
        try:
            result = respond(provider.provider(self.settings), tools, history)
        except AppError as error:
            failure = error if error.status in (401, 403) else unavailable()
        except Exception as error:
            logging.getLogger("smartlibrary").warning(
                "assistant_failed", extra={"error_type": type(error).__name__}
            )
            failure = unavailable()
        with Session(self.engine) as db, db.begin():
            user_id = self.authorize(db)
            conversation = owned(db, identity, user_id, True)
            row = db.get(AIMessage, user_message_id)
            if row is None or row.tool_metadata.get("state") != "pending":
                raise AppError("AI_TURN_INTERRUPTED", "Сұранысты қайта жіберіңіз.", 409)
            row.tool_metadata = {"state": "failed" if failure else "completed"}
            response = AIMessage(
                id=answer_id,
                conversation_id=identity,
                role=MessageRole.ASSISTANT,
                content=result.content if result else unavailable().message,
                tool_metadata={
                    "tools": tools.trace,
                    "kind": result.kind if result else "unavailable",
                    "book_ids": [str(book.id) for book in result.books] if result else [],
                    "provider": self.settings.assistant_provider or "unconfigured",
                },
                model_name=self.settings.assistant_model[:250] or None,
                latency_ms=int((perf_counter() - start) * 1000),
                input_tokens=result.input_tokens if result else None,
                output_tokens=result.output_tokens if result else None,
                error_code=failure.code if failure else None,
            )
            db.add(response)
            db.flush()
            if result:
                for position, book in enumerate(result.books, 1):
                    db.add(
                        AIMessageBook(message_id=response.id, book_id=book.id, position=position)
                    )
            conversation.updated_at = now()
            db.flush()
            output = message_views(db, [response])[0]
        if failure:
            raise failure
        return output
