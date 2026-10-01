from typing import Literal

from app.schemas.analytics import AnalyticsDates


class ReportInput(AnalyticsDates):
    report_type: Literal["inventory", "borrowings", "overdue", "reservations"]
    format: Literal["pdf", "xlsx"]
