"""
Main Dashboard View

Displays financial overview, analytics, and spending insights.
"""
import json
import logging
from datetime import datetime, date
from calendar import month_name

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseNotAllowed, HttpRequest, HttpResponse

from expenses.forms import get_category_choices
from ..models import Subscription, UserProfile
from ..utils import (
    get_month_navigation,
    get_date_range,
    calculate_savings_rate,
    get_available_years,
    get_sum_amount,
    get_previous_month,
    get_month_date_range,
)
from ..services.expense_service import (
    get_period_expenses,
    get_total_spent,
    get_top_categories,
    get_daily_totals,
    get_spending_forecast,
    get_recent_expenses,
    get_category_breakdown,
)
from ..services.income_service import get_monthly_income, get_range_income
from ..services.budget_service import get_budget_alerts

logger = logging.getLogger(__name__)


def _advance_overdue_subscriptions(user) -> None:
    """
    Advance billing dates for all overdue subscriptions.

    Args:
        user: Django User object
    """
    _today = date.today()
    for _sub in Subscription.objects.filter(
        user=user, status='active', next_billing__lt=_today
    ):
        try:
            _sub.advance_billing_date()
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to advance subscription {_sub.pk}: {e}")


@login_required(login_url='login')
def dashboard_view(request: HttpRequest) -> HttpResponse:
    """
    Main dashboard view showing financial overview and analytics.

    Features:
        - Month/year navigation with custom date ranges
        - Income vs expenses tracking
        - Savings rate calculation with financial health indicator
        - Category breakdown (top 5)
        - Daily spending chart
        - Spending forecast for current month
        - Budget alerts for overspending
        - Recent expenses list
        - Interactive onboarding tour

    Args:
        request: Django HttpRequest object

    Returns:
        HttpResponse: Rendered dashboard template
    """
    profile_obj, _ = UserProfile.objects.get_or_create(user=request.user)

    # Advance overdue subscriptions on every dashboard load
    _advance_overdue_subscriptions(request.user)

    show_tour = not profile_obj.onboarding_complete

    now = datetime.now()

    # ── resolve active month/year (for month nav) ──
    nav = get_month_navigation(request)
    view_month = nav['view_month']
    view_year = nav['view_year']

    # ── income: sum Income entries for the active month/year ──
    income = get_monthly_income(request.user, view_month, view_year)

    # ── custom date-range filter ──
    filter_cat = request.GET.get('filter_cat', '')
    date_range_info = get_date_range(request, view_month, view_year)

    start_dt = date_range_info['start_dt']
    end_dt = date_range_info['end_dt']
    is_custom = date_range_info['is_custom']
    filter_label = date_range_info['filter_label']
    start_str = date_range_info['start_str']
    end_str = date_range_info['end_str']

    # for custom range, re-sum income over that date range
    if is_custom:
        income = get_range_income(request.user, start_dt, end_dt)

    period_expenses = get_period_expenses(request.user, start_dt, end_dt, category=filter_cat or None)
    total = get_sum_amount(period_expenses)
    balance = income - total

    # Calculate savings rate and financial health
    savings_rate, health_label, health_color, health_tip = calculate_savings_rate(income, total)

    # ── prev month comparison ──
    if not is_custom:
        prev_m, prev_y = get_previous_month(view_month, view_year)
        prev_start, prev_end = get_month_date_range(prev_y, prev_m)
        prev_total = get_total_spent(request.user, prev_start, prev_end)
        prev_income = get_monthly_income(request.user, prev_m, prev_y)
        prev_savings_rate = max(0, round(((prev_income - prev_total) / prev_income * 100), 1)) if prev_income > 0 else 0
        savings_delta = round(savings_rate - prev_savings_rate, 1)
    else:
        savings_delta = None

    # ── available years for dropdown ──
    years = get_available_years(request.user)

    # ── category breakdown ──
    top_categories = get_top_categories(request.user, start_dt, end_dt, n=5)
    cat_labels = [c for c, _ in top_categories]
    cat_amounts = [a for _, a in top_categories]

    # Full breakdown for chart (all categories)
    full_breakdown = get_category_breakdown(request.user, start_dt, end_dt)
    all_cat_labels = [c for c, _ in full_breakdown]
    all_cat_amounts = [a for _, a in full_breakdown]

    # ── daily spending ──
    daily_data = get_daily_totals(request.user, start_dt, end_dt)
    daily_labels = [d['date'] for d in daily_data]
    daily_amounts = [d['total'] for d in daily_data]

    # ── month names list (1-indexed) ──
    month_names = list(month_name)[1:]  # ['January', ..., 'December']

    # ── spending forecast (current month only) ──
    forecast = get_spending_forecast(request.user, view_month, view_year, income) if not is_custom else None

    # ── categories for filter dropdown ──
    all_cats = [c for c, _ in get_category_choices(request.user)]

    # ── budget alerts (current month only, not custom range) ──
    budget_alerts = []
    if not is_custom and view_month == now.month and view_year == now.year:
        budget_alerts = get_budget_alerts(request.user, view_month, view_year, period_expenses)

    context = {
        'income': income,
        'total': total,
        'balance': balance,
        'savings_rate': savings_rate,
        'savings_delta': savings_delta,
        'health_label': health_label,
        'health_color': health_color,
        'health_tip': health_tip,
        'filter_label': filter_label,
        'is_custom': is_custom,
        'start_date': start_str,
        'end_date': end_str,
        'filter_cat': filter_cat,
        'view_month': view_month,
        'view_year': view_year,
        'prev_m': nav['prev_m'],
        'prev_y': nav['prev_y'],
        'next_m': nav['next_m'],
        'next_y': nav['next_y'],
        'years': years,
        'all_cats': all_cats,
        'month_names': month_names,
        'top_categories': top_categories,
        'top_cat_placeholders': range(5 - len(top_categories)),
        'cat_labels_json': json.dumps(all_cat_labels),
        'cat_amounts_json': json.dumps(all_cat_amounts),
        'daily_labels_json': json.dumps(daily_labels),
        'daily_amounts_json': json.dumps(daily_amounts),
        'count': period_expenses.count(),
        'show_tour': show_tour,
        'forecast': forecast,
        'budget_alerts': budget_alerts,
    }
    recent = get_recent_expenses(request.user, start_dt, end_dt, limit=5)
    context['recent_expenses'] = recent
    context['recent_placeholders'] = range(max(0, 5 - len(recent)))
    return render(request, 'dashboard/dashboard.html', context)


@login_required(login_url='login')
def tour_complete(request: HttpRequest) -> JsonResponse:
    """
    Mark the onboarding tour as complete for the current user.

    Args:
        request: Django HttpRequest object

    Returns:
        JsonResponse: Success status or 405 if not POST
    """
    if request.method == 'POST':
        profile_obj, _ = UserProfile.objects.get_or_create(user=request.user)
        profile_obj.onboarding_complete = True
        profile_obj.save(update_fields=['onboarding_complete'])
        return JsonResponse({'ok': True})
    return HttpResponseNotAllowed(['POST'])
