"""Register all core mappings for Alembic and explicit application imports."""

from app.db.models.administration import AuditLog, SystemSetting
from app.db.models.ai import (
    AIConversation,
    AIMessage,
    AIMessageBook,
    BookEmbedding,
    CategoryPrediction,
    CategoryPredictionRun,
    CategoryPredictionSelection,
    EmbeddingModel,
)
from app.db.models.catalog import (
    Author,
    Book,
    BookAuthor,
    BookCategory,
    BookCopy,
    Category,
    Publisher,
)
from app.db.models.circulation import Borrowing, Reservation
from app.db.models.engagement import (
    Favorite,
    Notification,
    RecommendationImpression,
    SearchEvent,
    UserCategoryPreference,
    UserInteraction,
)
from app.db.models.users import RefreshSession, User

__all__ = [
    "AIConversation",
    "AIMessage",
    "AIMessageBook",
    "AuditLog",
    "Author",
    "Book",
    "BookAuthor",
    "BookCategory",
    "BookCopy",
    "BookEmbedding",
    "Borrowing",
    "Category",
    "CategoryPrediction",
    "CategoryPredictionRun",
    "CategoryPredictionSelection",
    "EmbeddingModel",
    "Favorite",
    "Notification",
    "Publisher",
    "RecommendationImpression",
    "RefreshSession",
    "Reservation",
    "SearchEvent",
    "SystemSetting",
    "User",
    "UserCategoryPreference",
    "UserInteraction",
]
