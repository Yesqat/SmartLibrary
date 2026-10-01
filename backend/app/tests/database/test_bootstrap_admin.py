"""Operator-only initial Admin creation on an empty real PostgreSQL database."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from psycopg import sql
from sqlalchemy import func, select

from app.core.security import PASSWORD_HASHER, verify_password
from app.db.bootstrap_admin import create_initial_admin
from app.db.manage import engine, upgrade
from app.db.models import AuditLog, User
from app.schemas.auth import RegisterInput


def test_initial_admin_is_validated_audited_and_concurrent_safe(test_database_name):
    name = "smartlibrary_test_" + uuid4().hex
    owner = engine("admin", "postgres")
    created = False
    try:
        with owner.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.connection.driver_connection.execute(
                sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name))
            )
            created = True
        upgrade(name)
        db = engine("migration", name)
        try:
            existing = RegisterInput.model_validate(
                {
                    "email": "reader@example.com",
                    "first_name": "Аян",
                    "last_name": "Омар",
                    "password": "Existing Reader password 721!",
                }
            )
            with db.begin() as connection:
                connection.execute(
                    User.__table__.insert().values(
                        email=str(existing.email),
                        first_name=existing.first_name,
                        last_name=existing.last_name,
                        password_hash=PASSWORD_HASHER.hash(existing.password.get_secret_value()),
                    )
                )
            with pytest.raises(ValueError, match="never promotes"):
                create_initial_admin(db, existing)
            with pytest.raises(ValueError):
                RegisterInput(
                    email="operator@example.com",
                    first_name="Аян",
                    last_name="Омар",
                    password="short",
                )
            data = RegisterInput(
                email="operator@example.com",
                first_name="Аян",
                last_name="Омар",
                password="Private operator password 982!",
            )

            def attempt():
                try:
                    create_initial_admin(db, data)
                    return True
                except ValueError:
                    return False

            with ThreadPoolExecutor(max_workers=2) as executor:
                assert sorted(executor.map(lambda _: attempt(), range(2))) == [False, True]
            with db.connect() as connection:
                assert connection.scalar(select(func.count()).select_from(User)) == 2
                assert (
                    connection.scalar(
                        select(User.role).where(User.email == str(existing.email))
                    ).value
                    == "READER"
                )
                row = connection.execute(
                    select(User.password_hash, User.role, User.status).where(
                        User.email == str(data.email)
                    )
                ).one()
                assert row.role.value == "ADMIN" and row.status.value == "ACTIVE"
                assert verify_password(row.password_hash, data.password.get_secret_value())
                assert (
                    connection.scalar(
                        select(func.count())
                        .select_from(AuditLog)
                        .where(AuditLog.action == "ADMIN_BOOTSTRAP")
                    )
                    == 1
                )
            with pytest.raises(ValueError, match="already exists"):
                create_initial_admin(db, data)
        finally:
            db.dispose()
    finally:
        if created:
            with owner.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
                connection.connection.driver_connection.execute(
                    sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
                )
        owner.dispose()
