"""
Expense Service

Business logic for expense queries, aggregations, forecasting, and anomaly detection.
"""
import calendar
from datetime import date, timedelta, datetime

from django.db.models import Avg

from expenses.models import Expense
from ..utils import get_sum_amount, get_month_date_range


def get_period_expenses(user, start_dt, end_dt, category=None):
    """Return a filtered queryset of expenses for a user within a date range."""
    qs = Expense.objects.filter(user=user, date__gte=start_dt, date__lte=end_dt)
    if category:
        qs = qs.filter(category=category)
    return qs


def get_total_spent(user, start_dt, end_dt, category=None) -> float:
    """Return the total amount spent in a date range."""
    return get_sum_amount(get_period_expenses(user, start_dt, end_dt, category))


def get_category_breakdown(user, start_dt, end_dt) -> list:
    """Return a list of (category, amount) tuples ordered by amount descending."""
    from django.db.models import Sum
    qs = get_period_expenses(user, start_dt, end_dt)
    cat_data = qs.values('category').annotate(total=Sum('amount')).order_by('-total')
    return [(row['category'], float(row['total'])) for row in cat_data]


def get_top_categories(user, start_dt, end_dt, n=5) -> list:
    """Return the top N categories by spending amount."""
    return get_category_breakdown(user, start_dt, end_dt)[:n]


def get_daily_totals(user, start_dt, end_dt) -> list:
    """Return daily spending totals as a list of dicts with 'date' and 'total' keys."""
    from django.db.models import Sum
    qs = get_period_expenses(user, start_dt, end_dt)
    daily_raw = qs.values('date').annotate(total=Sum('amount')).order_by('date')
    return [{'date': str(row['date']), 'total': float(row['total'])} for row in daily_raw]


def get_spending_forecast(user, month, year, income) -> dict | None:
    """
    Forecast end-of-month spending based on daily average so far.
    Only meaningful for the current month. Returns None if not enough data.
    """
    now = datetime.now()
    if month != now.month or year != now.year:
        return None

    days_in_month = calendar.monthrange(year, month)[1]
    day_of_month = now.day
    start_dt, end_dt = get_month_date_range(year, month)

    total = get_total_spent(user, start_dt, end_dt)
    if day_of_month <= 0 or total <= 0:
        return None

    daily_avg = total / day_of_month
    forecast_total = round(daily_avg * days_in_month, 0)
    days_left = days_in_month - day_of_month
    forecast_balance = round(income - forecast_total, 0)
    forecast_pct = min(round(forecast_total / income * 100, 1), 999) if income > 0 else None

    if forecast_total <= income:
        status = 'good'
        msg = f"On track — projected to spend ₹{forecast_total:,.0f} this month."
    elif forecast_total <= income * 1.1:
        status = 'warning'
        msg = f"Slightly over — projected to spend ₹{forecast_total:,.0f}, just above your income."
    else:
        status = 'danger'
        msg = f"Over budget — projected to spend ₹{forecast_total:,.0f} by month end."

    return {
        'daily_avg': round(daily_avg, 0),
        'forecast_total': forecast_total,
        'forecast_balance': forecast_balance,
        'forecast_pct': forecast_pct,
        'days_left': days_left,
        'status': status,
        'msg': msg,
    }


def get_anomalies(user, days=30) -> list:
    """Return a list of unusual expenses (> 2x category average and > ₹500)."""
    today = date.today()
    all_expenses = Expense.objects.filter(user=user)
    cat_avgs = {
        row['category']: float(row['avg'])
        for row in all_expenses.values('category').annotate(avg=Avg('amount'))
    }
    recent = all_expenses.filter(date__gte=today - timedelta(days=days)).order_by('-amount')[:50]

    anomalies = []
    for exp in recent:
        avg = cat_avgs.get(exp.category, 0)
        if avg > 0 and float(exp.amount) > avg * 2 and float(exp.amount) > 500:
            anomalies.append({
                'title': exp.title,
                'category': exp.category,
                'amount': float(exp.amount),
                'avg': round(avg, 0),
                'date': str(exp.date),
                'multiplier': round(float(exp.amount) / avg, 1),
            })
    return anomalies


def get_recent_expenses(user, start_dt, end_dt, limit=5) -> list:
    """Return the most recent expenses in a date range."""
    return list(get_period_expenses(user, start_dt, end_dt).order_by('-date')[:limit])
