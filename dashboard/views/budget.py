"""
Budget Management Views

Category budgets, spending tracking, and custom categories.
"""
from datetime import date

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.db.models import Sum
from django.urls import reverse
from django.http import HttpRequest, HttpResponse

from expenses.models import Expense, DEFAULT_CATEGORIES
from expenses.forms import get_category_choices
from ..models import CustomCategory, CategoryBudget
from ..utils import get_month_navigation, format_currency


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
    custom_categories  = CustomCategory.objects.filter(user=request.user)
    success = False
    error   = None

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
    
    today = date.today()

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

    # Load budgets for this month
    budgets = {
        b.category: b
        for b in CategoryBudget.objects.filter(
            user=request.user, month=view_month, year=view_year
        )
    }

    # Spending for this month
    month_expenses = (
        Expense.objects.filter(user=request.user, date__month=view_month, date__year=view_year)
        .values('category').annotate(spent=Sum('amount'))
    )
    spent_map = {row['category']: float(row['spent']) for row in month_expenses}
    total_spent = sum(spent_map.values())

    # Total budget goal = sum of all saved category limits (auto-computed, no manual entry)
    total_goal = sum(float(b.limit) for b in budgets.values()) or None
    if total_goal:
        total_pct = min(round(total_spent / total_goal * 100, 1), 9999)
        total_over = total_spent - total_goal
        total_status = 'danger' if total_pct >= 100 else ('warning' if total_pct >= 80 else 'ok')
    else:
        total_pct = total_over = None
        total_status = 'none'

    budget_rows = []
    for cat in categories:
        budget = budgets.get(cat)
        limit  = float(budget.limit) if budget else None
        spent  = spent_map.get(cat, 0.0)
        if limit:
            pct = min(round(spent / limit * 100, 1), 9999)
            remaining = limit - spent
            if pct >= 100:
                status = 'danger'
            elif pct >= 80:
                status = 'warning'
            else:
                status = 'ok'
        else:
            pct, remaining, status = None, None, 'none'
        budget_rows.append({
            'category': cat,
            'limit': limit,
            'spent': spent,
            'remaining': remaining,
            'pct': pct,
            'status': status,
        })

    # Use utility function for formatting
    def fmt_amount(v):
        return format_currency(v)

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
        'total_spent_fmt': fmt_amount(total_spent),
        'total_goal_fmt': fmt_amount(total_goal) if total_goal else None,
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
            year  = int(request.POST['year'])
        except (KeyError, ValueError):
            messages.error(request, 'Invalid month/year.')
            return redirect('settings_budget')

        prev_m, prev_y = (12, year - 1) if month == 1 else (month - 1, year)

        prev_budgets = CategoryBudget.objects.filter(
            user=request.user, month=prev_m, year=prev_y
        )
        if not prev_budgets.exists():
            messages.error(request, 'No budget limits found for the previous month.')
            return redirect(f"{reverse('settings_budget')}?month={month}&year={year}")

        copied = 0
        for b in prev_budgets:
            _, created = CategoryBudget.objects.update_or_create(
                user=request.user, category=b.category, month=month, year=year,
                defaults={'limit': b.limit}
            )
            copied += 1

        messages.success(request, f'Copied {copied} budget limit{"s" if copied != 1 else ""} from last month.')
    return redirect(f"{reverse('settings_budget')}?month={month}&year={year}")
