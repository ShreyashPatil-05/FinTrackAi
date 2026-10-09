"""
dashboard/services/budget_service.py

Business logic for category budgets, spending alerts, and budget summaries.
All functions are read-only except copy_budgets_from_last_month.
"""
from django.db.models import Sum

from expenses.models import Expense
from expenses.forms import get_category_choices
from ..models import CategoryBudget
from ..utils import get_sum_amount, get_previous_month


# Budget status thresholds
BUDGET_WARNING_THRESHOLD = 80   # percentage — show warning
BUDGET_DANGER_THRESHOLD = 100   # percentage — over limit


def _get_budget_status(utilisation_pct: float) -> str:
    """
    Derive a budget status label from the utilisation percentage.

    Returns:
        'danger'  if at or above 100%
        'warning' if at or above 80%
        'ok'      otherwise
    """
    if utilisation_pct >= BUDGET_DANGER_THRESHOLD:
        return "danger"
    if utilisation_pct >= BUDGET_WARNING_THRESHOLD:
        return "warning"
    return "ok"


def get_budget_rows(user, month: int, year: int) -> list:
    """
    Return a list of budget row dicts for every expense category the user has.

    Each row contains the category name, its optional budget limit, the amount
    spent this month, the remaining budget, and a status label.

    Categories without a budget limit still appear in the list (limit=None,
    status='none') so the UI can display actual spend alongside unbudgeted items.

    Args:
        user:  Django User instance
        month: Calendar month number (1–12)
        year:  Four-digit year

    Returns:
        list of dicts, one per category:
            category  (str)
            limit     (float | None)
            spent     (float)
            remaining (float | None)
            pct       (float | None)
            status    (str: 'ok' | 'warning' | 'danger' | 'none')
    """
    all_categories = [category for category, _ in get_category_choices(user)]

    # Build a lookup of CategoryBudget objects for this month
    budget_by_category = {
        budget.category: budget
        for budget in CategoryBudget.objects.filter(user=user, month=month, year=year)
    }

    # Build a lookup of actual spend per category this month
    monthly_expenses = (
        Expense.objects
        .filter(user=user, date__month=month, date__year=year)
        .values("category")
        .annotate(total_spent=Sum("amount"))
    )
    spent_by_category = {
        row["category"]: float(row["total_spent"])
        for row in monthly_expenses
    }

    budget_rows = []
    for category in all_categories:
        budget = budget_by_category.get(category)
        monthly_limit = float(budget.limit) if budget else None
        amount_spent = spent_by_category.get(category, 0.0)

        if monthly_limit:
            utilisation_pct = min(round(amount_spent / monthly_limit * 100, 1), 9999)
            remaining_budget = monthly_limit - amount_spent
            status = _get_budget_status(utilisation_pct)
        else:
            utilisation_pct = None
            remaining_budget = None
            status = "none"

        budget_rows.append({
            "category": category,
            "limit": monthly_limit,
            "spent": amount_spent,
            "remaining": remaining_budget,
            "pct": utilisation_pct,
            "status": status,
        })

    return budget_rows


def get_budget_alerts(user, month: int, year: int, period_expenses_qs) -> list:
    """
    Return a list of budget alert dicts for categories at or near their limit.

    Only categories with a budget set are checked. Categories with no budget
    are silently skipped — there is nothing to alert on.

    Args:
        user:                 Django User instance
        month:                Calendar month number (1–12)
        year:                 Four-digit year
        period_expenses_qs:   Pre-filtered Expense queryset for the period

    Returns:
        list of dicts for categories that need an alert:
            category (str)
            pct      (float)
            status   (str: 'warning' | 'danger')
            msg      (str)  human-readable alert message
    """
    category_budgets = CategoryBudget.objects.filter(user=user, month=month, year=year)

    # Build actual spend per category from the provided queryset
    spent_by_category = {
        row["category"]: float(row["total"])
        for row in period_expenses_qs.values("category").annotate(total=Sum("amount"))
    }

    alerts = []
    for budget in category_budgets:
        amount_spent = spent_by_category.get(budget.category, 0.0)
        monthly_limit = float(budget.limit)

        if monthly_limit <= 0:
            continue

        utilisation_pct = round(amount_spent / monthly_limit * 100, 1)

        if utilisation_pct >= BUDGET_DANGER_THRESHOLD:
            alerts.append({
                "category": budget.category,
                "pct": utilisation_pct,
                "status": "danger",
                "msg": f"Over limit — spent ₹{amount_spent:,.0f} of ₹{monthly_limit:,.0f}",
            })
        elif utilisation_pct >= BUDGET_WARNING_THRESHOLD:
            remaining = monthly_limit - amount_spent
            alerts.append({
                "category": budget.category,
                "pct": utilisation_pct,
                "status": "warning",
                "msg": f"{utilisation_pct}% used — ₹{remaining:,.0f} remaining",
            })

    return alerts


def get_total_budget_summary(user, month: int, year: int) -> dict:
    """
    Return an overall budget vs spending summary for the month.

    Args:
        user:  Django User instance
        month: Calendar month number (1–12)
        year:  Four-digit year

    Returns:
        dict with keys:
            total_goal  (float | None) — sum of all budget limits, None if no budgets set
            total_spent (float)        — total expenses for the month
            pct         (float | None) — utilisation percentage, None if no budgets set
            status      (str)          — 'ok' | 'warning' | 'danger' | 'none'
    """
    category_budgets = list(CategoryBudget.objects.filter(user=user, month=month, year=year))
    total_budget_limit = sum(float(budget.limit) for budget in category_budgets) or None

    total_amount_spent = get_sum_amount(
        Expense.objects.filter(user=user, date__month=month, date__year=year)
    )

    if total_budget_limit:
        utilisation_pct = min(round(total_amount_spent / total_budget_limit * 100, 1), 9999)
        status = _get_budget_status(utilisation_pct)
    else:
        utilisation_pct = None
        status = "none"

    return {
        "total_goal": total_budget_limit,
        "total_spent": total_amount_spent,
        "pct": utilisation_pct,
        "status": status,
    }


def copy_budgets_from_last_month(user, month: int, year: int) -> int:
    """
    Copy all budget limits from the previous month into the given month.

    Existing budgets for the target month are updated; missing ones are created.
    Categories that had no budget last month are not created.

    Args:
        user:  Django User instance
        month: Target month (1–12)
        year:  Target year

    Returns:
        int: Number of budget rows created or updated
    """
    previous_month, previous_year = get_previous_month(month, year)
    previous_budgets = CategoryBudget.objects.filter(
        user=user,
        month=previous_month,
        year=previous_year,
    )

    copied_count = 0
    for previous_budget in previous_budgets:
        CategoryBudget.objects.update_or_create(
            user=user,
            category=previous_budget.category,
            month=month,
            year=year,
            defaults={"limit": previous_budget.limit},
        )
        copied_count += 1

    return copied_count
