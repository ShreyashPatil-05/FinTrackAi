"""
dashboard/services/income_service.py

Business logic for income queries and monthly summaries.
All functions are read-only — no income records are created here.
"""
from ..models import Income
from ..utils import get_sum_amount


def get_monthly_income(user, month: int, year: int) -> float:
    """
    Return the total income amount for a specific month and year.

    Args:
        user:  Django User instance
        month: Calendar month number (1–12)
        year:  Four-digit year

    Returns:
        float: Sum of all income entries for that month. Returns 0.0 if none.
    """
    income_entries = Income.objects.filter(
        user=user,
        date__month=month,
        date__year=year,
    )
    return get_sum_amount(income_entries)


def get_range_income(user, start_date, end_date) -> float:
    """
    Return the total income amount within an inclusive date range.

    Args:
        user:       Django User instance
        start_date: Start of the range (date or datetime)
        end_date:   End of the range (date or datetime)

    Returns:
        float: Sum of all income entries in the range. Returns 0.0 if none.
    """
    income_entries = Income.objects.filter(
        user=user,
        date__gte=start_date,
        date__lte=end_date,
    )
    return get_sum_amount(income_entries)


def get_income_entries(user, month: int, year: int, source_filter: str = ""):
    """
    Return income entries for a given month, with an optional source filter.

    Args:
        user:          Django User instance
        month:         Calendar month number (1–12)
        year:          Four-digit year
        source_filter: Optional string to filter by income source (case-insensitive)

    Returns:
        QuerySet: Income queryset, ordered by date descending by default.
    """
    queryset = Income.objects.filter(user=user, date__month=month, date__year=year)
    if source_filter:
        queryset = queryset.filter(source__icontains=source_filter)
    return queryset


def get_income_summary(user, month: int, year: int) -> dict:
    """
    Return a summary of income entries for a given month.

    Args:
        user:  Django User instance
        month: Calendar month number (1–12)
        year:  Four-digit year

    Returns:
        dict with keys:
            total_records (int)   — number of income entries
            total_amount  (float) — sum of all amounts
    """
    income_entries = Income.objects.filter(user=user, date__month=month, date__year=year)
    return {
        "total_records": income_entries.count(),
        "total_amount": get_sum_amount(income_entries),
    }
