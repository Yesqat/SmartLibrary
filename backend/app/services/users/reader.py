"""Owned favorites, preferences and notification operations."""

from uuid import UUID

from sqlalchemy import Engine, delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.api.dependencies import Principal
from app.core.config import Settings
from app.core.errors import AppError
from app.core.permissions import Permission, authorize
from app.db.enums import InteractionSource, InteractionType
from app.db.models.catalog import Book, Category
from app.db.models.engagement import Favorite, Notification, UserCategoryPreference, UserInteraction
from app.repositories.reader import preferences
from app.schemas.reader import NotificationRead, Preferences
from app.services.audit.events import AuditContext
from app.services.auth.service import AuthService


class ReaderService:
    def __init__(
        self, engine: Engine, settings: Settings, context: AuditContext, principal: Principal
    ):
        self.engine, self.principal = engine, principal
        self.auth = AuthService(engine, settings, context)

    def authorize(self, db: Session) -> UUID:
        user = self.auth.require_live(db, self.principal.user.id, self.principal.family_id)
        authorize(user.role, Permission.READ_PERSONAL)
        return user.id

    def favorite(self, book_id: UUID, enabled: bool) -> None:
        with Session(self.engine) as db, db.begin():
            # Same lock order as circulation: title before user.
            book = db.scalar(select(Book).where(Book.id == book_id).with_for_update())
            user_id = self.authorize(db)
            if not book or (enabled and book.archived_at):
                raise AppError("BOOK_NOT_FOUND", "Кітап табылмады.", 404)
            if enabled:
                identity = db.scalar(
                    insert(Favorite)
                    .values(user_id=user_id, book_id=book_id)
                    .on_conflict_do_nothing(index_elements=["user_id", "book_id"])
                    .returning(Favorite.id)
                )
                if identity:
                    db.add(
                        UserInteraction(
                            user_id=user_id,
                            book_id=book_id,
                            interaction_type=InteractionType.FAVORITE,
                            source=InteractionSource.CATALOG,
                            event_key=f"favorite:{identity}",
                        )
                    )
            else:
                db.execute(
                    delete(Favorite).where(Favorite.user_id == user_id, Favorite.book_id == book_id)
                )

    def set_preferences(self, category_ids: list[UUID]) -> Preferences:
        with Session(self.engine) as db, db.begin():
            # Reference writers lock category then user; keep that order here too.
            categories = list(
                db.scalars(
                    select(Category)
                    .where(Category.id.in_(category_ids), Category.archived_at.is_(None))
                    .order_by(Category.id)
                    .with_for_update()
                )
            )
            user_id = self.authorize(db)
            if len(categories) != len(category_ids):
                raise AppError("CATEGORY_NOT_FOUND", "Санат табылмады.", 404)
            db.execute(
                delete(UserCategoryPreference).where(UserCategoryPreference.user_id == user_id)
            )
            db.add_all(
                [
                    UserCategoryPreference(user_id=user_id, category_id=row.id, weight=1)
                    for row in categories
                ]
            )
            db.flush()
            return preferences(db, user_id)

    def read_notification(self, identity: UUID) -> NotificationRead:
        with Session(self.engine) as db, db.begin():
            user_id = self.authorize(db)
            row = db.scalar(
                select(Notification)
                .where(Notification.id == identity, Notification.user_id == user_id)
                .with_for_update()
            )
            if not row:
                raise AppError("NOTIFICATION_NOT_FOUND", "Хабарлама табылмады.", 404)
            row.is_read = True
            db.flush()
            return NotificationRead.model_validate(row)

    def read_all(self) -> None:
        with Session(self.engine) as db, db.begin():
            user_id = self.authorize(db)
            db.execute(
                update(Notification)
                .where(Notification.user_id == user_id, Notification.is_read.is_(False))
                .values(is_read=True)
            )
