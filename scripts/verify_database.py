"""Read-only live schema/integrity evidence. Run in the database operator container."""

import json
from collections import Counter
from dataclasses import asdict

from alembic.script import ScriptDirectory
from sqlalchemy import DateTime, Enum, Uuid, inspect, select, text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.manage import alembic_config, engine
from app.services.settings.policy import circulation_policy


def main() -> None:
    db = engine("migration")
    try:
        with db.connect() as connection:
            inspector = inspect(connection)
            tables = sorted(Base.metadata.tables)
            assert set(inspector.get_table_names()) == set(tables) | {"alembic_version"}
            head = connection.scalar(text("SELECT version_num FROM alembic_version"))
            assert head == ScriptDirectory.from_config(alembic_config()).get_current_head()
            extensions = dict(
                connection.execute(text("SELECT extname,extversion FROM pg_extension"))
                .tuples()
                .all()
            )
            assert {"vector", "pg_trgm"} <= extensions.keys()
            enums = {row["name"]: row["labels"] for row in inspector.get_enums()}
            assert enums == {
                c.type.name: c.type.enums
                for t in Base.metadata.tables.values()
                for c in t.columns
                if isinstance(c.type, Enum)
            }
            for name in tables:
                columns = {c["name"]: c for c in inspector.get_columns(name)}
                table = Base.metadata.tables[name]
                assert set(columns) == set(table.columns.keys())
                assert inspector.get_pk_constraint(name)["constrained_columns"] == ["id"]
                assert isinstance(columns["id"]["type"], Uuid)
                for column in table.columns:
                    assert columns[column.name]["nullable"] == column.nullable
                    if isinstance(column.type, DateTime):
                        assert columns[column.name]["type"].timezone
            constraints = connection.execute(
                text("""
                SELECT contype,convalidated FROM pg_constraint c
                JOIN pg_class t ON t.oid=c.conrelid JOIN pg_namespace n ON n.oid=t.relnamespace
                WHERE n.nspname='public' AND t.relname=ANY(:tables)
            """),
                {"tables": tables},
            ).all()
            assert all(row.convalidated for row in constraints)
            totals = dict(Counter(row.contype for row in constraints))
            assert totals == {"p": 27, "f": 48, "u": 31, "c": 60}
            indexes = connection.scalar(
                text("SELECT count(*) FROM pg_indexes WHERE schemaname='public'")
            )
            assert indexes == 144
            counts = {
                name: connection.scalar(select(text("count(*)")).select_from(table))
                for name, table in Base.metadata.tables.items()
            }
            assert (
                connection.scalar(
                    text("""
                SELECT count(*) FROM reservations r JOIN book_copies c ON c.id=r.book_copy_id
                WHERE r.book_id<>c.book_id
            """)
                )
                == 0
            )
            assert (
                connection.scalar(
                    text("""
                SELECT count(*) FROM borrowings b JOIN reservations r ON r.id=b.reservation_id
                WHERE b.user_id<>r.user_id OR b.book_copy_id<>r.book_copy_id
            """)
                )
                == 0
            )
            vectors = [
                dict(row)
                for row in connection.execute(
                    text("""
                SELECT m.model_name,m.revision,m.dimension,count(e.id) AS vectors,
                min(vector_dims(e.embedding)) AS minimum_dimension,
                max(vector_dims(e.embedding)) AS maximum_dimension
                FROM embedding_models m LEFT JOIN book_embeddings e ON e.model_id=m.id
                GROUP BY m.id
            """)
                ).mappings()
            ]
            for space in vectors:
                if space["vectors"]:
                    assert (
                        space["minimum_dimension"]
                        == space["maximum_dimension"]
                        == space["dimension"]
                    )
        with Session(db) as session:
            policy = asdict(circulation_policy(session))
    finally:
        db.dispose()
    runtime = engine("runtime")
    try:
        with runtime.connect() as connection:
            role = connection.execute(
                text("""
                SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls
                FROM pg_roles WHERE rolname=current_user
            """)
            ).one()
            assert not any(role)
            assert not connection.scalar(
                text("SELECT has_schema_privilege(current_user,'public','CREATE')")
            )
            for table in (
                "audit_logs",
                "borrowings",
                "reservations",
                "books",
                "book_copies",
                "users",
            ):
                assert not connection.scalar(
                    text("SELECT has_table_privilege(current_user,:t,'DELETE')"), {"t": table}
                )
    finally:
        runtime.dispose()
    print(
        json.dumps(
            {
                "verification": "actual live PostgreSQL",
                "head": head,
                "extensions": extensions,
                "tables": len(tables),
                "enums": len(enums),
                "constraints": totals,
                "indexes_including_alembic": indexes,
                "row_counts": counts,
                "vector_spaces": vectors,
                "policy": policy,
                "uuid_timestamps_relationships_runtime_privileges": "PASS",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
