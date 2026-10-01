from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import MessageRole
from app.schemas.catalog import BookRead, Page


class ConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str | None = Field(default=None, min_length=1, max_length=100)


class MessageInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    content: str = Field(min_length=1, max_length=2000)
    request_id: UUID


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime


class MessageRead(BaseModel):
    id: UUID
    role: MessageRole
    content: str
    created_at: datetime
    error_code: str | None
    books: list[BookRead]


class ConversationDetail(BaseModel):
    conversation: ConversationRead
    messages: Page[MessageRead]
