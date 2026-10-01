"""Profile mutations cannot assign role/status/email or bypass live-session checks."""

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.api.dependencies import Principal
from app.core.config import Settings
from app.db.models.catalog import Book
from app.db.models.users import User
from app.schemas.auth import UserResponse
from app.schemas.reader import ProfileInput
from app.services.audit.events import AuditContext, record
from app.services.auth.service import AuthService
from app.services.storage.images import ImageStorage


class ProfileService:
    def __init__(
        self, engine: Engine, settings: Settings, context: AuditContext, principal: Principal
    ):
        self.engine, self.context, self.principal = engine, context, principal
        self.auth = AuthService(engine, settings, context)

    def update(self, data: ProfileInput) -> UserResponse:
        with Session(self.engine) as db, db.begin():
            user = self.auth.require_live(db, self.principal.user.id, self.principal.family_id)
            for field, value in data.model_dump().items():
                setattr(user, field, value)
            record(db, "PROFILE_UPDATED", self.context, user.id, user.id, entity_type="USER")
            db.flush()
            return UserResponse.model_validate(user)

    def avatar(self, content: bytes | None, storage: ImageStorage) -> UserResponse:
        saved = previous = None
        try:
            with Session(self.engine) as db, db.begin():
                user = self.auth.require_live(db, self.principal.user.id, self.principal.family_id)
                if content is not None:
                    saved = storage.save(content)
                previous, user.avatar_url = user.avatar_url, saved
                record(db, "AVATAR_UPDATED", self.context, user.id, user.id, entity_type="USER")
                db.flush()
                result = UserResponse.model_validate(user)
        except Exception:
            storage.delete(saved)
            raise
        if previous:
            with Session(self.engine) as db:
                shared = db.scalar(
                    select(User.id).where(User.avatar_url == previous).limit(1)
                ) or db.scalar(select(Book.id).where(Book.cover_url == previous).limit(1))
            if not shared:
                storage.delete(previous)
        return result
