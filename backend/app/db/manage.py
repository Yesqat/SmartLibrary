"""Explicit operator database tooling. No schema mutation occurs at application startup."""

import argparse
import os
from pathlib import Path
from uuid import uuid4

import psycopg
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from psycopg import sql
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine

ROOT = Path(__file__).resolve().parents[2]


def env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise ValueError(f"Configure {name} for the database operator command")
    return value


def url(kind: str, database: str | None = None) -> URL:
    prefix = {"admin": "POSTGRES", "migration": "MIGRATION_DB", "runtime": "APP_DB"}[kind]
    return URL.create(
        "postgresql+psycopg",
        username=env(f"{prefix}_USER"),
        password=env(f"{prefix}_PASSWORD"),
        host=env("POSTGRES_HOST"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=database or env("POSTGRES_DB"),
    )


def engine(kind: str, database: str | None = None) -> Engine:
    return create_engine(
        url(kind, database), hide_parameters=True, connect_args={"connect_timeout": 5}
    )


def alembic_config() -> Config:
    return Config(str(ROOT / "alembic.ini"))


def bootstrap(database: str | None = None) -> None:
    """Install extensions as operator, then give schema ownership to a non-superuser migrator."""
    admin = engine("admin", database)
    migrator = env("MIGRATION_DB_USER")
    runtime = env("APP_DB_USER")
    if len({migrator, runtime, env("POSTGRES_USER")}) != 3:
        raise ValueError("Admin, migration and runtime database roles must be distinct")
    with admin.begin() as connection:
        raw = connection.connection.driver_connection
        if not isinstance(raw, psycopg.Connection):
            raise TypeError("PostgreSQL psycopg connection required")
        for role, password in (
            (migrator, env("MIGRATION_DB_PASSWORD")),
            (runtime, env("APP_DB_PASSWORD")),
        ):
            if len(password) < 32:
                raise ValueError("Operator-managed database passwords require 32+ characters")
            exists = raw.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone()
            if not exists:
                raw.execute(sql.SQL("CREATE ROLE {} LOGIN").format(sql.Identifier(role)))
            raw.execute(
                sql.SQL(
                    "ALTER ROLE {} WITH NOSUPERUSER NOCREATEDB NOCREATEROLE "
                    "NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD {}"
                ).format(sql.Identifier(role), sql.Literal(password))
            )
        actual_db = connection.scalar(text("SELECT current_database()"))
        raw.execute(
            sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(sql.Identifier(actual_db))
        )
        for role in (migrator, runtime):
            raw.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    sql.Identifier(actual_db), sql.Identifier(role)
                )
            )
        raw.execute("REVOKE ALL ON SCHEMA public FROM PUBLIC")
        raw.execute(sql.SQL("ALTER SCHEMA public OWNER TO {}").format(sql.Identifier(migrator)))
        raw.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(runtime)))
        current = MigrationContext.configure(connection).get_current_revision()
        if current is None:
            cfg = alembic_config()
            cfg.attributes["connection"] = connection
            command.upgrade(cfg, "0001_extensions")
        raw.execute(
            sql.SQL("ALTER TABLE public.alembic_version OWNER TO {}").format(
                sql.Identifier(migrator)
            )
        )
    admin.dispose()


def grants(database: str | None = None) -> None:
    """Explicit table privileges: no runtime DDL, audit mutation or history deletion."""
    migration = engine("migration", database)
    runtime = env("APP_DB_USER")
    with migration.begin() as connection:
        raw = connection.connection.driver_connection
        if not isinstance(raw, psycopg.Connection):
            raise TypeError("PostgreSQL psycopg connection required")
        raw.execute(
            sql.SQL("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {}").format(
                sql.Identifier(runtime)
            )
        )
        raw.execute(
            sql.SQL("GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO {}").format(
                sql.Identifier(runtime)
            )
        )
        raw.execute(
            sql.SQL("GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {}").format(
                sql.Identifier(runtime)
            )
        )
        deletable = (
            "favorites",
            "user_category_preferences",
            "book_authors",
            "book_categories",
            "book_embeddings",
            "ai_messages",
            "ai_conversations",
            "notifications",
        )
        for table in deletable:
            raw.execute(
                sql.SQL("GRANT DELETE ON {} TO {}").format(
                    sql.Identifier(table), sql.Identifier(runtime)
                )
            )
        for table in (
            "audit_logs",
            "user_interactions",
            "search_events",
            "recommendation_impressions",
        ):
            raw.execute(
                sql.SQL("REVOKE UPDATE ON {} FROM {}").format(
                    sql.Identifier(table), sql.Identifier(runtime)
                )
            )
        raw.execute(
            sql.SQL("REVOKE INSERT, UPDATE ON system_settings FROM {}").format(
                sql.Identifier(runtime)
            )
        )
        raw.execute(
            sql.SQL("GRANT UPDATE (value, updated_by, updated_at) ON system_settings TO {}").format(
                sql.Identifier(runtime)
            )
        )
        raw.execute(
            sql.SQL("REVOKE ALL ON alembic_version FROM {}").format(sql.Identifier(runtime))
        )
        # Vector-space provenance cannot be altered underneath stored vectors.
        raw.execute(
            sql.SQL("REVOKE UPDATE ON embedding_models FROM {}").format(sql.Identifier(runtime))
        )
    migration.dispose()


def upgrade(database: str | None = None) -> None:
    bootstrap(database)
    migration = engine("migration", database)
    with migration.begin() as connection:
        cfg = alembic_config()
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, "head")
    migration.dispose()
    grants(database)
    print("Migrations applied; restricted runtime grants applied.")


def check(database: str | None = None) -> None:
    migration = engine("migration", database)
    with migration.connect() as connection:
        cfg = alembic_config()
        cfg.attributes["connection"] = connection
        command.current(cfg)
        command.check(cfg)
    migration.dispose()


def test_database() -> int:
    """Create and destroy only this run's random, isolated PostgreSQL test database."""
    import subprocess

    database = "smartlibrary_test_" + uuid4().hex
    admin = engine("admin", "postgres")
    created = False
    try:
        with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            raw = connection.connection.driver_connection
            if not isinstance(raw, psycopg.Connection):
                raise TypeError("PostgreSQL psycopg connection required")
            raw.execute(
                sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(database))
            )
            created = True
        upgrade(database)
        check(database)
        migration = engine("migration", database)
        with migration.begin() as connection:
            cfg = alembic_config()
            cfg.attributes["connection"] = connection
            command.downgrade(cfg, "base")
            command.upgrade(cfg, "head")
        migration.dispose()
        grants(database)
        check(database)
        print("Empty test database upgrade/downgrade/upgrade and drift checks passed.")
        test_env = dict(os.environ)
        test_env["PHASE2_TEST_DATABASE"] = database
        test_env["APP_ENV"] = "test"
        result = subprocess.run(["pytest", "-q"], cwd=ROOT, env=test_env, check=False)
        return result.returncode
    finally:
        if created:
            with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
                raw = connection.connection.driver_connection
                if not isinstance(raw, psycopg.Connection):
                    raise TypeError("PostgreSQL psycopg connection required")
                raw.execute(
                    sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database))
                )
            print("Removed this run's isolated test database.")
        admin.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["upgrade", "check", "seed", "test"])
    args = parser.parse_args()
    if args.command == "upgrade":
        upgrade()
    elif args.command == "check":
        check()
    elif args.command == "seed":
        from app.db.seed import seed_development

        seed_development()
    elif args.command == "test":
        raise SystemExit(test_database())


if __name__ == "__main__":
    main()
