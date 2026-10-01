"""Metadata maintenance cannot perform circulation transitions."""

from app.core.errors import AppError
from app.db.enums import CopyCondition, CopyStatus

MAINTENANCE_TRANSITIONS = {
    CopyStatus.AVAILABLE: {CopyStatus.DAMAGED, CopyStatus.LOST, CopyStatus.MAINTENANCE},
    CopyStatus.DAMAGED: {CopyStatus.MAINTENANCE},
    CopyStatus.MAINTENANCE: {CopyStatus.AVAILABLE, CopyStatus.DAMAGED, CopyStatus.LOST},
    CopyStatus.LOST: set(),
    CopyStatus.RESERVED: set(),
    CopyStatus.BORROWED: set(),
}


def validate_maintenance(old: CopyStatus, new: CopyStatus, condition: CopyCondition) -> None:
    if new != old and new not in MAINTENANCE_TRANSITIONS[old]:
        raise AppError(
            "INVALID_COPY_TRANSITION", "Дана күйін осы әрекетпен өзгертуге болмайды.", 409
        )
    if condition == CopyCondition.DAMAGED and new not in {
        CopyStatus.DAMAGED,
        CopyStatus.MAINTENANCE,
        CopyStatus.LOST,
    }:
        raise AppError("COPY_DAMAGED", "Зақымдалған дана қолжетімді бола алмайды.", 409)
    if new == CopyStatus.DAMAGED and condition != CopyCondition.DAMAGED:
        raise AppError("INVALID_COPY_TRANSITION", "Зақымдалған дананың жағдайын көрсетіңіз.", 409)
