"""Database states shared by models and future validated services."""

from enum import StrEnum


class UserRole(StrEnum):
    READER = "READER"
    LIBRARIAN = "LIBRARIAN"
    ADMIN = "ADMIN"


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    INACTIVE = "INACTIVE"


class CopyStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    BORROWED = "BORROWED"
    DAMAGED = "DAMAGED"
    LOST = "LOST"
    MAINTENANCE = "MAINTENANCE"


class CopyCondition(StrEnum):
    NEW = "NEW"
    GOOD = "GOOD"
    FAIR = "FAIR"
    POOR = "POOR"
    DAMAGED = "DAMAGED"


class ReservationStatus(StrEnum):
    WAITING = "WAITING"
    READY = "READY"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class BorrowingStatus(StrEnum):
    BORROWED = "BORROWED"
    RETURNED = "RETURNED"
    OVERDUE = "OVERDUE"
    LOST = "LOST"


class InteractionType(StrEnum):
    VIEW = "VIEW"
    SEARCH_CLICK = "SEARCH_CLICK"
    FAVORITE = "FAVORITE"
    RESERVE = "RESERVE"
    BORROW = "BORROW"
    RECOMMENDATION_CLICK = "RECOMMENDATION_CLICK"


class InteractionSource(StrEnum):
    CATALOG = "CATALOG"
    STANDARD_SEARCH = "STANDARD_SEARCH"
    SEMANTIC_SEARCH = "SEMANTIC_SEARCH"
    HYBRID_SEARCH = "HYBRID_SEARCH"
    RECOMMENDATION = "RECOMMENDATION"
    AI_ASSISTANT = "AI_ASSISTANT"
    SIMILAR_BOOKS = "SIMILAR_BOOKS"
    POPULAR_BOOKS = "POPULAR_BOOKS"


class SearchType(StrEnum):
    STANDARD = "STANDARD"
    SEMANTIC = "SEMANTIC"
    HYBRID = "HYBRID"


class NotificationType(StrEnum):
    RESERVATION_READY = "RESERVATION_READY"
    RESERVATION_EXPIRING = "RESERVATION_EXPIRING"
    RESERVATION_EXPIRED = "RESERVATION_EXPIRED"
    DUE_SOON = "DUE_SOON"
    OVERDUE = "OVERDUE"


class RelatedEntity(StrEnum):
    RESERVATION = "RESERVATION"
    BORROWING = "BORROWING"
    BOOK = "BOOK"


class RecommendationType(StrEnum):
    PERSONALIZED = "PERSONALIZED"
    SIMILAR_BOOK = "SIMILAR_BOOK"
    POPULAR = "POPULAR"


class MessageRole(StrEnum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"


class PredictionReview(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    MODIFIED = "MODIFIED"
    REJECTED = "REJECTED"


class ScoreKind(StrEnum):
    PROBABILITY = "PROBABILITY"
    COSINE_SIMILARITY = "COSINE_SIMILARITY"
    DECISION_FUNCTION = "DECISION_FUNCTION"


class SettingType(StrEnum):
    INTEGER = "INTEGER"
    BOOLEAN = "BOOLEAN"
    STRING = "STRING"
    JSON = "JSON"
