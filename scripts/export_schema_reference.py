"""Export a reviewable model contract. This is not a claim of live database verification."""

import argparse
import sys
from pathlib import Path

from sqlalchemy import CheckConstraint, Enum, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.db import models  # noqa: E402, F401
from app.db.base import Base  # noqa: E402


def render() -> str:
    dialect = postgresql.dialect()
    constraint_name = dialect.identifier_preparer.truncate_and_render_constraint_name
    lines = [
        "# Core schema reference",
        "",
        "Generated from SQLAlchemy models by scripts/export_schema_reference.py. "
        "Live verification results belong in PHASE_2_REPORT.md. "
        "All entity keys are UUIDs; timestamps use timestamptz. "
        "The acquired_at physical-copy field is a calendar date.",
        "",
        "## Enum types",
        "",
    ]
    enums = {
        c.type.name: c.type
        for t in Base.metadata.tables.values()
        for c in t.columns
        if isinstance(c.type, Enum)
    }
    for name, enum in sorted(enums.items()):
        lines.append(f"- **{name}**: {', '.join(enum.enums)}")
    for table in Base.metadata.sorted_tables:
        lines += [
            "",
            f"## {table.name}",
            "",
            "| Column | PostgreSQL type | Nullable | Default |",
            "|---|---|---|---|",
        ]
        for column in table.columns:
            default = (
                str(column.server_default.arg)
                if column.server_default is not None and hasattr(column.server_default, "arg")
                else ""
            )
            if column.computed is not None:
                default = "generated: " + str(column.computed.sqltext)
            lines.append(
                f"| {column.name} | {column.type.compile(dialect=dialect)} | "
                f"{'yes' if column.nullable else 'no'} | {default.replace('|', '&#124;')} |"
            )
        lines += [
            "",
            "Constraints:",
            "",
            f"- `{table.primary_key.name}`: PRIMARY KEY "
            f"({', '.join(table.primary_key.columns.keys())}).",
        ]
        for fk in sorted(table.foreign_key_constraints, key=lambda c: str(c.name)):
            lines.append(
                f"- `{constraint_name(fk.name, _alembic_quote=False)}`: "
                f"({', '.join(fk.columns.keys())}) → "
                f"({', '.join(e.target_fullname for e in fk.elements)}), DELETE {fk.ondelete}."
            )
        for constraint in sorted(table.constraints, key=lambda c: str(c.name)):
            if isinstance(constraint, UniqueConstraint):
                lines.append(
                    f"- `{constraint_name(constraint.name, _alembic_quote=False)}`: "
                    f"UNIQUE ({', '.join(constraint.columns.keys())})."
                )
            elif isinstance(constraint, CheckConstraint):
                lines.append(
                    f"- `{constraint_name(constraint.name, _alembic_quote=False)}`: "
                    f"CHECK `{constraint.sqltext}`."
                )
        if table.indexes:
            lines += [
                "",
                "Additional indexes (primary/unique constraint indexes are implicit):",
                "",
                "```sql",
            ]
            lines += [
                str(CreateIndex(index).compile(dialect=dialect)) + ";"
                for index in sorted(table.indexes, key=lambda i: str(i.name))
            ]
            lines += ["```"]
    return "\n".join(lines) + "\n"


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--check", action="store_true")
args = parser.parse_args()
target = ROOT / "docs/SCHEMA_REFERENCE.md"
result = render()
if args.check:
    if not target.exists() or target.read_text(encoding="utf-8") != result:
        raise SystemExit("Schema reference differs from model metadata; regenerate and review it")
    print("Schema reference matches model metadata.")
else:
    target.write_text(result, encoding="utf-8", newline="\n")
    print(f"Exported {len(Base.metadata.tables)} table definitions to docs/SCHEMA_REFERENCE.md")
