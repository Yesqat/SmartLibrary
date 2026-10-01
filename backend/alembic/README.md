# Alembic migrations

Schema changes are explicit operator actions. Application startup never calls
`create_all` or runs migrations. See [database operations](../../docs/DATABASE.md)
for the Compose commands and [verification status](../../docs/PHASE_2_REPORT.md)
before treating the schema as deployed.

| Revision | Contents |
|---|---|
| `0001_extensions` | Install `vector` and `pg_trgm` using operator privileges. |
| `0002_core_schema` | 27 tables, 16 native enums, constraints, indexes and the reservation number sequence. |
| `0003_defaults_and_guards` | Six system settings, update timestamps and immutable audit/model provenance guards. |

Revision files contain frozen DDL; they do not import current application models.
Alembic's environment imports all models for schema comparison. It requires an
explicit operator connection or `MIGRATION_DATABASE_URL`; runtime credentials
are never implicitly used for migrations.

For a future schema change, set the migration DSN privately and run from `backend`:

```powershell
alembic revision --autogenerate -m "Describe the schema change"
alembic upgrade head
alembic check
```

Review generated changes, including enums, checks, indexes, extensions and data
transitions. Run the documented `app.db.manage upgrade` afterward to refresh
runtime grants. Never include credentials in revision files or shell arguments.
`alembic upgrade head --sql` renders the complete upgrade without connecting.
The reservation-number default comparator avoids evaluating `nextval` while
checking drift, so a check does not consume sequence values.

`app/db/migration_comparison.py` uses Alembic's public
[autogenerate plugin API](https://alembic.sqlalchemy.org/en/latest/api/plugins.html)
(minimum Alembic 1.18). It compares the generated notification reference before
ordinary default handling, which cannot read a `Computed` expression as a
`DefaultClause`. A changed generated expression fails with an explicit review
error. Normal default and nullability comparison remains enabled. Registration
is cached because the operator loads Alembic repeatedly in one process. Five
real PostgreSQL regression cases cover these comparisons and sequence safety.

The test runner checks upgrade/downgrade/upgrade only on its newly created,
randomly named disposable database. Downgrading this initial schema destroys
domain data; an operational rollback needs a reviewed backup/restore plan.
Extension downgrade deliberately leaves installed extensions intact because
other database objects may depend on them.
