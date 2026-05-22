"""
Budget Management Views

Category budgets, spending tracking, and custom categories.
"""
from datetime import date

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.urls import reverse
from django.http import HttpRequest, HttpResponse

from expenses.models import DEFAULT_CATEGORIES
from expenses.forms import get_category_choices
from ..models import CustomCategory, CategoryBudget
from ..utils import get_month_navigation, format_currency, get_previous_month
from ..services.budget_service import (
    get_budget_rows,
    get_total_budget_summary,
    copy_budgets_from_last_month,
)


@login_required(login_url='login')
def settings_categories(request: HttpRequest) -> HttpResponse:
    """
    Manage custom expense categories.

    Features:
        - View default categories (read-only)
        - Add custom categories
        - Delete custom categories
        - Duplicate prevention

    Args:
        request: Django HttpRequest object

    Returns:
        HttpResponse: Categories settings page
    """
    default_categories = DEFAULT_CATEGORIES
    custom_categories = CustomCategory.objects.filter(user=request.user)
    success = False
    error = None

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add":
            name = request.POST.get("name", "").strip().title()
            if not name:
                error = "Category name cannot be empty."
            elif name in default_categories:
                error = f'"{name}" already exists as a default category.'
            elif CustomCategory.objects.filter(user=request.user, name=name).exists():
                error = f'"{name}" already exists.'
            else:
                CustomCategory.objects.create(user=request.user, name=name)
                success = True

        elif action == "delete":
            cat_id = request.POST.get("cat_id")
            CustomCategory.objects.filter(pk=cat_id, user=request.user).delete()
            return redirect('settings_categories')

    return render(request, 'dashboard/settings.html', {
        'section': 'categories',
        'default_categories': default_categories,
        'custom_categories': custom_categories,
        'success': success,
        'error': error,
    })


@never_cache
@login_required(login_url='login')
def settings_budget(request: HttpRequest) -> HttpResponse:
    """
    Monthly budget management with spending tracking.

    Features:
        - Set budget limits per category per month
        - View spending vs budget with progress bars
        - Color-coded status (ok/warning/danger)
        - Total budget and spending summary
        - Month/year navigation

    Args:
        request: Django HttpRequest object

    Returns:
        HttpResponse: Budget settings page
    """
    # Month/year navigation using utility
    nav = get_month_navigation(request)
    view_month = nav['view_month']
    view_year = nav['view_year']

    categories = [c for c, _ in get_category_choices(request.user)]

    if request.method == 'POST':
        for cat in categories:
            key = f"limit_{cat}"
            val = request.POST.get(key, '').strip()
            if val:
                try:
                    CategoryBudget.objects.update_or_create(
                        user=request.user, category=cat,
                        month=view_month, year=view_year,
                        defaults={'limit': float(val)}
                    )
                except ValueError:
                    pass
            else:
                CategoryBudget.objects.filter(
                    user=request.user, category=cat,
                    month=view_month, year=view_year
                ).delete()
        messages.success(request, 'Budgets saved.')
        return redirect(f"{request.path}?month={view_month}&year={view_year}")

    budget_rows = get_budget_rows(request.user, view_month, view_year)
    summary = get_total_budget_summary(request.user, view_month, view_year)

    total_goal = summary['total_goal']
    total_spent = summary['total_spent']
    total_pct = summary['pct']
    total_status = summary['status']
    total_over = (total_spent - total_goal) if total_goal else None

    return render(request, 'dashboard/settings.html', {
        'section': 'budget',
        'budget_rows': budget_rows,
        'view_month': view_month,
        'view_year': view_year,
        'view_month_name': nav['view_month_name'],
        'prev_m': nav['prev_m'],
        'prev_y': nav['prev_y'],
        'next_m': nav['next_m'],
        'next_y': nav['next_y'],
        'total_goal': total_goal,
        'total_spent': total_spent,
        'total_pct': total_pct,
        'total_over': total_over,
        'total_status': total_status,
        'total_spent_fmt': format_currency(total_spent),
        'total_goal_fmt': format_currency(total_goal) if total_goal else None,
    })


@login_required(login_url='login')
def budget_copy_last_month(request):
    """
    Copy budget limits from previous month to current month.

    Args:
        request: Django HttpRequest object

    Returns:
        HttpResponse: Redirect to budget settings
    """
    if request.method == 'POST':
        try:
            month = int(request.POST['month'])
            year = int(request.POST['year'])
        except (KeyError, ValueError):
            messages.error(request, 'Invalid month/year.')
            return redirect('settings_budget')

        prev_m, prev_y = get_previous_month(month, year)
        prev_exists = CategoryBudget.objects.filter(
            user=request.user, month=prev_m, year=prev_y
        ).exists()

        if not prev_exists:
            messages.error(request, 'No budget limits found for the previous month.')
            return redirect(f"{reverse('settings_budget')}?month={month}&year={year}")

        copied = copy_budgets_from_last_month(request.user, month, year)
        messages.success(request, f'Copied {copied} budget limit{"s" if copied != 1 else ""} from last month.')
    return redirect(f"{reverse('settings_budget')}?month={month}&year={year}")
