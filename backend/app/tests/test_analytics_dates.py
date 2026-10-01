from datetime import date

import pytest

from app.core.errors import AppError
from app.schemas.analytics import AnalyticsDates
from app.services.analytics.definitions import percentage, period


@pytest.mark.parametrize("days,bucket", [(30, "day"), (120, "week"), (730, "month")])
def test_buckets_are_bounded_continuous_and_timezone_aware(days, bucket):
    from datetime import timedelta

    window = period(
        AnalyticsDates(
            date_from=date(2024, 1, 1), date_to=date(2024, 1, 1) + timedelta(days=days - 1)
        ),
        "Asia/Qyzylorda",
    )
    assert window.meta.bucket == bucket and len(window.buckets()) <= 121
    assert window.start.utcoffset().total_seconds() == 5 * 3600
    assert window.end.date() == window.meta.date_to + timedelta(days=1)
    assert len(set(window.buckets())) == len(window.buckets())


@pytest.mark.parametrize(
    "start,end",
    [
        (date(2025, 2, 1), date(2025, 1, 1)),
        (None, date.min),
        (None, date.max),
        (date(2000, 1, 1), date(2025, 1, 1)),
    ],
)
def test_invalid_or_overflowing_dates_are_safe(start, end):
    with pytest.raises(AppError) as error:
        period(AnalyticsDates(date_from=start, date_to=end), "UTC")
    assert error.value.status == 422


def test_empty_denominator_is_unknown_not_fabricated_zero():
    assert percentage(0, 0) is None and percentage(1, 4) == 25
