"""
Income Service

Business logic for income queries and summaries.
"""
from ..models import Income
from ..utils import get_sum_amount


def get_monthly_income(user, month, year) -> float:
    """Return total income for a specific month and year."""
    return get_sum_amount(
        Income.objects.filter(user=user, date__month=month, date__year=year)
    )


def get_range_income(user, start_dt, end_dt) -> float:
    """Return total income within a date range."""
    return get_sum_amount(
        Income.objects.filter(user=user, date__gte=start_dt, date__lte=end_dt)
    )


def get_income_entries(user, month, year, source_q=''):
    """
    Return income entries for a month, with optional source filter.

    Args:
        user: Django User object
        month: Month number (1-12)
        year: Year
        source_q: Optional source string to filter by (case-insensitive contains)

    Returns:
        QuerySet: Filtered Income queryset
    """
    qs = Income.objects.filter(user=user, date__month=month, date__year=year)
    if source_q:
        qs = qs.filter(source__icontains=source_q)
    return qs


def get_income_summary(user, month, year) -> dict:
    """
    Return a summary dict for income in a given month.

    Returns:
        dict: With keys total_records (int) and total_amount (float)
    """
    qs = Income.objects.filter(user=user, date__month=month, date__year=year)
    return {
        'total_records': qs.count(),
        'total_amount': get_sum_amount(qs),
    }
