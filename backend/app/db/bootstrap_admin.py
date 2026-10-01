"""One-time operator command. Public registration never invokes this capability."""

from getpass import getpass

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.security import PASSWORD_HASHER
from app.db.enums import UserRole, UserStatus
from app.db.models import User
from app.schemas.auth import RegisterInput
from app.services.administration.service import ADMIN_MEMBERSHIP_LOCK
from app.services.audit.events import AuditContext, record


def create_initial_admin(engine: Engine, data: RegisterInput) -> None:
    with Session(engine) as db, db.begin():
        # Same lock as Admin role/status changes; no race can create two initial Admins.
        db.execute(select(func.pg_advisory_xact_lock(ADMIN_MEMBERSHIP_LOCK)))
        if db.scalar(select(User.id).where(User.role == UserRole.ADMIN).limit(1)):
            raise ValueError("An Admin already exists; use authenticated Admin management")
        if db.scalar(select(User.id).where(User.email == str(data.email)).limit(1)):
            raise ValueError("This account already exists; operator bootstrap never promotes users")
        user = User(
            first_name=data.first_name,
            last_name=data.last_name,
            email=str(data.email),
            phone=data.phone,
            password_hash=PASSWORD_HASHER.hash(data.password.get_secret_value()),
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        db.flush()
        record(db, "ADMIN_BOOTSTRAP", AuditContext(), user.id, user.id, entity_type="USER")


def main() -> None:
    from pydantic import ValidationError

    from app.db.manage import engine

    password = getpass("New Admin password (12–128 characters): ")
    if password != getpass("Confirm password: "):
        raise SystemExit("Passwords did not match")
    try:
        data = RegisterInput.model_validate(
            {
                "email": input("Admin email: "),
                "first_name": input("First name: "),
                "last_name": input("Last name: "),
                "password": password,
            }
        )
    except ValidationError:
        raise SystemExit("Invalid account fields or password; no account created") from None
    db = engine("migration")
    try:
        create_initial_admin(db, data)
    except ValueError as error:
        raise SystemExit(str(error)) from None
    finally:
        db.dispose()
    print("Initial Admin created and audited. No development accounts were seeded.")


if __name__ == "__main__":
    main()
