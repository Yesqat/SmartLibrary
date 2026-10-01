"""Compare generated and sequence defaults without executing volatile expressions."""

import re
import sys
from functools import cache
from typing import Any

from alembic.autogenerate.api import AutogenContext
from alembic.operations.ops import AlterColumnOp
from alembic.runtime.plugins import Plugin
from alembic.util import CommandError, DispatchPriority, PriorityDispatchResult
from sqlalchemy import Column, Computed, DefaultClause


def compare_special_defaults(
    context: AutogenContext,
    operation: AlterColumnOp,
    schema: str | None,
    table: str,
    column: str,
    inspected: Column[Any],
    metadata: Column[Any],
) -> PriorityDispatchResult:
    actual, expected = inspected.server_default, metadata.server_default
    if isinstance(actual, Computed) or isinstance(expected, Computed):
        # Fail explicitly: Alembic cannot automatically alter generated expressions.
        def expression(value: Computed) -> str:
            return re.sub(r"[\s()]", "", str(value.sqltext)).lower()

        if (
            not isinstance(actual, Computed)
            or not isinstance(expected, Computed)
            or expression(actual) != expression(expected)
            or actual.persisted != expected.persisted
        ):
            raise CommandError(f"Generated expression drift on {table}.{column}; review migration")
        return PriorityDispatchResult.STOP
    if (table, column) != ("reservations", "reservation_number"):
        return PriorityDispatchResult.CONTINUE

    def sequence_default(value: Any) -> str:
        expression = str(value.arg) if isinstance(value, DefaultClause) else ""
        return re.sub(r"[\s()]|::(?:text|regclass)", "", expression)

    operation.existing_server_default = actual
    if sequence_default(actual) != sequence_default(expected):
        operation.modify_server_default = expected
    return PriorityDispatchResult.STOP


def setup(plugin: Plugin) -> None:
    plugin.add_autogenerate_comparator(
        compare_special_defaults,
        "column",
        "server_default",
        priority=DispatchPriority.FIRST,
    )


@cache
def register() -> None:
    """Alembic may load env.py repeatedly in one operator process."""
    Plugin.setup_plugin_from_module(sys.modules[__name__], "smartlibrary.defaults")
