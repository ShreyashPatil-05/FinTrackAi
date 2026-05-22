"""
Dashboard Utility Functions

Shared helper functions for dashboard views to reduce code duplication
and improve maintainability.
"""
from datetime import date, datetime
from typing import Dict, List, Tuple
import calendar

from django.db.models import Sum


def get_sum_amount(queryset) -> float:
    """
    Return the total of the 'amount' field from a queryset.

    Centralises the repeated aggregate(Sum('amount')) pattern.

    Args:
        queryset: Any Django queryset that has an 'amount' field

    Returns:
        float: Sum of amount, or 0.0 if queryset is empty
    """
    return float(queryset.aggregate(Sum('amount'))['amount__sum'] or 0)


def get_month_date_range(year: int, month: int) -> Tuple[date, date]:
    """
    Return the first and last date of a given month.

    Args:
        year: Year (e.g., 2026)
        month: Month number (1-12)

    Returns:
        tuple: (start_date, end_date) as date objects
    """
    start_dt = date(year, month, 1)
    end_dt   = date(year, month, get_last_day_of_month(year, month))
    return start_dt, end_dt


def get_previous_month(month: int, year: int) -> Tuple[int, int]:
    """
    Return the previous month and year.

    Args:
        month: Current month (1-12)
        year: Current year

    Returns:
        tuple: (prev_month, prev_year)
    """
    if month == 1:
        return 12, year - 1
    return month - 1, year


def get_month_navigation(request, default_month=None, default_year=None) -> Dict[str, int]:
    """
    Parse month/year from request GET parameters and calculate prev/next navigation.
    
    Args:
        request: Django HttpRequest object
        default_month: Default month if not in request (defaults to current month)
        default_year: Default year if not in request (defaults to current year)
        
    Returns:
        dict: Navigation data with keys:
            - view_month: Selected month (1-12)
            - view_year: Selected year
            - view_month_name: Month name (e.g., "January")
            - prev_m: Previous month number
            - prev_y: Previous month year
            - next_m: Next month number
            - next_y: Next month year
            
    Example:
        >>> nav = get_month_navigation(request)
        >>> print(nav['view_month'], nav['view_year'])
        4 2026
    """
    today = date.today()
    
    try:
        view_month = int(request.GET.get('month', default_month or today.month))
        view_year = int(request.GET.get('year', default_year or today.year))
        if not (1 <= view_month <= 12):
            raise ValueError("Month must be between 1 and 12")
    except (ValueError, TypeError):
        view_month, view_year = today.month, today.year
    
    # Calculate previous month
    if view_month == 1:
        prev_m, prev_y = 12, view_year - 1
    else:
        prev_m, prev_y = view_month - 1, view_year
    
    # Calculate next month
    if view_month == 12:
        next_m, next_y = 1, view_year + 1
    else:
        next_m, next_y = view_month + 1, view_year
    
    return {
        'view_month': view_month,
        'view_year': view_year,
        'view_month_name': calendar.month_name[view_month],
        'prev_m': prev_m,
        'prev_y': prev_y,
        'next_m': next_m,
        'next_y': next_y,
    }


def get_last_day_of_month(year: int, month: int) -> int:
    """
    Get the last day number of a given month.
    
    Args:
        year: Year (e.g., 2026)
        month: Month number (1-12)
        
    Returns:
        int: Last day of the month (28-31)
        
    Example:
        >>> get_last_day_of_month(2026, 2)
        28
        >>> get_last_day_of_month(2026, 4)
        30
    """
    return calendar.monthrange(year, month)[1]


def format_currency(value: float) -> str:
    """
    Format currency with K/L suffixes for large amounts.
    
    Args:
        value: Amount to format
        
    Returns:
        str: Formatted currency string with ₹ symbol
        
    Examples:
        >>> format_currency(500)
        '₹500'
        >>> format_currency(1500)
        '₹1.5K'
        >>> format_currency(150000)
        '₹1.5L'
    """
    v = float(value)
    if v >= 100000:
        return f"₹{v/100000:.1f}L"
    elif v >= 1000:
        return f"₹{v/1000:.1f}K"
    return f"₹{v:.0f}"


def get_date_range(request, view_month: int, view_year: int) -> Dict:
    """
    Parse custom date range from request or use month boundaries.
    
    Args:
        request: Django HttpRequest object
        view_month: Default month to use if no custom range
        view_year: Default year to use if no custom range
        
    Returns:
        dict: Date range information with keys:
            - start_dt: Start date object
            - end_dt: End date object
            - is_custom: Boolean indicating if custom range was used
            - filter_label: Human-readable label for the range
            - start_str: Start date string (YYYY-MM-DD) or empty
            - end_str: End date string (YYYY-MM-DD) or empty
    """
    
    start_str = request.GET.get('start_date', '').strip()
    end_str = request.GET.get('end_date', '').strip()
    
    if start_str and end_str:
        try:
            start_dt = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_dt = datetime.strptime(end_str, '%Y-%m-%d').date()
            is_custom = True
            filter_label = f"{start_dt.strftime('%d %b')} – {end_dt.strftime('%d %b %Y')}"
        except ValueError:
            is_custom = False
            start_dt, end_dt = get_month_date_range(view_year, view_month)
            filter_label = f"{calendar.month_name[view_month]} {view_year}"
            start_str = end_str = ''
    else:
        is_custom = False
        start_dt, end_dt = get_month_date_range(view_year, view_month)
        filter_label = f"{calendar.month_name[view_month]} {view_year}"
    
    return {
        'start_dt': start_dt,
        'end_dt': end_dt,
        'is_custom': is_custom,
        'filter_label': filter_label,
        'start_str': start_str,
        'end_str': end_str,
    }


def calculate_savings_rate(income: float, expenses: float) -> Tuple[float, str, str, str]:
    """
    Calculate savings rate and financial health metrics.
    
    Args:
        income: Total income amount
        expenses: Total expense amount
        
    Returns:
        tuple: (savings_rate, health_label, health_color, health_tip)
            - savings_rate: Percentage saved (0-100, capped)
            - health_label: Text label (Excellent/Good/Fair/Over Budget)
            - health_color: Hex color code for UI
            - health_tip: Actionable advice text
    """
    balance = income - expenses
    savings_rate = round((balance / income * 100), 1) if income > 0 else 0
    savings_rate = max(0, min(100, savings_rate))
    
    if savings_rate >= 30:
        health_label = 'Excellent'
        health_color = '#16a34a'
        health_tip = "Great work! You're saving more than usual."
    elif savings_rate >= 15:
        health_label = 'Good'
        health_color = '#2563eb'
        health_tip = "You're on track. Try to push savings above 30%."
    elif savings_rate >= 0:
        health_label = 'Fair'
        health_color = '#d97706'
        health_tip = "Spending is high. Review your top categories."
    else:
        health_label = 'Over Budget'
        health_color = '#dc2626'
        health_tip = "You've exceeded your income budget this period."
    
    return savings_rate, health_label, health_color, health_tip


def get_available_years(user) -> list:
    """
    Get list of years that have expense data for a user.
    
    Args:
        user: Django User object
        
    Returns:
        list: Sorted list of years (newest first), always includes current year
    """
    from expenses.models import Expense
    
    today = date.today()
    
    year_dates = Expense.objects.filter(user=user).dates('date', 'year')
    years = sorted(set([d.year for d in year_dates] + [today.year]), reverse=True)
    
    return years
