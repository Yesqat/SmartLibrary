"""Explicit capability map; ADMIN is not an implicit bypass for circulation or ownership."""

from enum import StrEnum
from uuid import UUID

from app.core.errors import AppError
from app.db.enums import UserRole


class Permission(StrEnum):
    READ_PERSONAL = "read_personal"
    RESERVE = "reserve"
    MANAGE_CATALOG = "manage_catalog"
    CIRCULATE = "circulate"
    VIEW_READERS = "view_readers"
    MANAGE_USERS = "manage_users"
    MANAGE_SETTINGS = "manage_settings"
    VIEW_ANALYTICS = "view_analytics"
    VIEW_AUDIT = "view_audit"


ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.READER: frozenset({Permission.READ_PERSONAL, Permission.RESERVE}),
    UserRole.LIBRARIAN: frozenset(
        {
            Permission.MANAGE_CATALOG,
            Permission.CIRCULATE,
            Permission.VIEW_READERS,
        }
    ),
    UserRole.ADMIN: frozenset(
        {
            Permission.MANAGE_CATALOG,
            Permission.MANAGE_USERS,
            Permission.MANAGE_SETTINGS,
            Permission.VIEW_ANALYTICS,
            Permission.VIEW_AUDIT,
        }
    ),
}


def authorize(role: UserRole, permission: Permission) -> None:
    if permission not in ROLE_PERMISSIONS[role]:
        raise AppError("FORBIDDEN", "Бұл әрекетке рұқсат жоқ.", 403)


def authorize_owner(user_id: UUID, owner_id: UUID) -> None:
    if user_id != owner_id:
        # Deliberately hide whether another user's private object exists.
        raise AppError("NOT_FOUND", "Жазба табылмады.", 404)
