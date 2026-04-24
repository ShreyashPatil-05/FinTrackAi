"""
Main Dashboard View

Displays financial overview, analytics, and spending insights.
"""
import json
import logging
import calendar
from datetime import datetime, date
from calendar import month_name
from decimal import Decimal

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseNotAllowed, HttpRequest, HttpResponse
from django.db.models import Sum

from expenses.models import Expense
from expenses.forms import get_category_choices
from ..models import Income, Subscription, CategoryBudget, UserProfile
from ..utils import (
    get_month_navigation,
    get_date_range,
    calculate_savings_rate,
    get_available_years,
)

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
    income = float(
        Income.objects.filter(user=request.user, date__month=view_month, date__year=view_year)
        .aggregate(Sum('amount'))['amount__sum'] or 0
    )

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
        income = float(
            Income.objects.filter(user=request.user, date__gte=start_dt, date__lte=end_dt)
            .aggregate(Sum('amount'))['amount__sum'] or 0
        )

    all_expenses    = Expense.objects.filter(user=request.user)
    period_expenses = all_expenses.filter(date__gte=start_dt, date__lte=end_dt)
    if filter_cat:
        period_expenses = period_expenses.filter(category=filter_cat)

    total   = float(period_expenses.aggregate(Sum('amount'))['amount__sum'] or 0)
    balance = income - total
    
    # Calculate savings rate and financial health
    savings_rate, health_label, health_color, health_tip = calculate_savings_rate(income, total)

    # ── prev month comparison ──
    if not is_custom:
        pm, py = (12, view_year - 1) if view_month == 1 else (view_month - 1, view_year)
        prev_total = float(
            all_expenses.filter(date__month=pm, date__year=py)
            .aggregate(Sum('amount'))['amount__sum'] or 0
        )
        prev_income = float(
            Income.objects.filter(user=request.user, date__month=pm, date__year=py)
            .aggregate(Sum('amount'))['amount__sum'] or 0
        )
        prev_savings_rate = max(0, round(((prev_income - prev_total) / prev_income * 100), 1)) if prev_income > 0 else 0
        savings_delta = round(savings_rate - prev_savings_rate, 1)
    else:
        savings_delta = None

    # ── available years for dropdown ──
    years = get_available_years(request.user)

    # ── category breakdown ──
    cat_data    = period_expenses.values('category').annotate(total=Sum('amount')).order_by('-total')
    cat_labels  = [c['category'] for c in cat_data]
    cat_amounts = [float(c['total']) for c in cat_data]
    top_categories = list(zip(cat_labels, cat_amounts))[:5]

    # ── daily spending ──
    daily_raw     = period_expenses.values('date').annotate(total=Sum('amount')).order_by('date')
    daily_labels  = [str(d['date']) for d in daily_raw]
    daily_amounts = [float(d['total']) for d in daily_raw]

    # ── month names list (1-indexed) ──
    month_names = list(month_name)[1:]  # ['January', ..., 'December']

    # ── spending forecast (current month only) ──
    forecast = None
    if not is_custom and view_month == now.month and view_year == now.year:
        days_in_month = calendar.monthrange(view_year, view_month)[1]
        day_of_month  = now.day
        if day_of_month > 0 and total > 0:
            daily_avg        = total / day_of_month
            forecast_total   = round(daily_avg * days_in_month, 0)
            days_left        = days_in_month - day_of_month
            forecast_balance = round(income - forecast_total, 0)
            forecast_pct     = min(round(forecast_total / income * 100, 1), 999) if income > 0 else None
            if forecast_total <= income:
                forecast_status = 'good'
                forecast_msg    = f"On track — projected to spend ₹{forecast_total:,.0f} this month."
            elif forecast_total <= income * 1.1:
                forecast_status = 'warning'
                forecast_msg    = f"Slightly over — projected to spend ₹{forecast_total:,.0f}, just above your income."
            else:
                forecast_status = 'danger'
                forecast_msg    = f"Over budget — projected to spend ₹{forecast_total:,.0f} by month end."
            forecast = {
                'daily_avg':        round(daily_avg, 0),
                'forecast_total':   forecast_total,
                'forecast_balance': forecast_balance,
                'forecast_pct':     forecast_pct,
                'days_left':        days_left,
                'status':           forecast_status,
                'msg':              forecast_msg,
            }

    # ── categories for filter dropdown ──
    all_cats = [c for c, _ in get_category_choices(request.user)]

    # ── budget alerts (current month only, not custom range) ──
    budget_alerts = []
    if not is_custom and view_month == now.month and view_year == now.year:
        budgets_qs = CategoryBudget.objects.filter(
            user=request.user, month=view_month, year=view_year
        )
        spent_by_cat = {
            row['category']: float(row['total'])
            for row in period_expenses.values('category').annotate(total=Sum('amount'))
        }
        for b in budgets_qs:
            spent = spent_by_cat.get(b.category, 0.0)
            limit = float(b.limit)
            if limit > 0:
                pct = round(spent / limit * 100, 1)
                if pct >= 100:
                    budget_alerts.append({
                        'category': b.category,
                        'pct': pct,
                        'status': 'danger',
                        'msg': f"Over limit — spent ₹{spent:,.0f} of ₹{limit:,.0f}",
                    })
                elif pct >= 80:
                    budget_alerts.append({
                        'category': b.category,
                        'pct': pct,
                        'status': 'warning',
                        'msg': f"{pct}% used — ₹{limit - spent:,.0f} remaining",
                    })

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
        'cat_labels_json': json.dumps(cat_labels),
        'cat_amounts_json': json.dumps(cat_amounts),
        'daily_labels_json': json.dumps(daily_labels),
        'daily_amounts_json': json.dumps(daily_amounts),
        'count': period_expenses.count(),
        'show_tour': show_tour,
        'forecast': forecast,
        'budget_alerts': budget_alerts,
    }
    recent = list(period_expenses.order_by('-date')[:5])
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
