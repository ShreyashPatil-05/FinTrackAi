"""
Budget Service

Business logic for category budgets, alerts, and summaries.
"""
from django.db.models import Sum

from expenses.models import Expense
from expenses.forms import get_category_choices
from ..models import CategoryBudget
from ..utils import get_sum_amount, get_previous_month


def _budget_status(pct) -> str:
    """Return status string based on percentage used."""
    if pct >= 100:
        return 'danger'
    if pct >= 80:
        return 'warning'
    return 'ok'


def get_budget_rows(user, month, year) -> list:
    """Return a list of budget row dicts for all categories in a given month."""
    categories = [c for c, _ in get_category_choices(user)]
    budgets = {
        b.category: b
        for b in CategoryBudget.objects.filter(user=user, month=month, year=year)
    }
    month_expenses = (
        Expense.objects.filter(user=user, date__month=month, date__year=year)
        .values('category').annotate(spent=Sum('amount'))
    )
    spent_map = {row['category']: float(row['spent']) for row in month_expenses}

    rows = []
    for cat in categories:
        budget = budgets.get(cat)
        limit = float(budget.limit) if budget else None
        spent = spent_map.get(cat, 0.0)
        if limit:
            pct = min(round(spent / limit * 100, 1), 9999)
            remaining = limit - spent
            status = _budget_status(pct)
        else:
            pct = remaining = None
            status = 'none'
        rows.append({
            'category': cat,
            'limit': limit,
            'spent': spent,
            'remaining': remaining,
            'pct': pct,
            'status': status,
        })
    return rows


def get_budget_alerts(user, month, year, period_expenses_qs) -> list:
    """Return budget alert dicts for categories at or near their limit."""
    budgets_qs = CategoryBudget.objects.filter(user=user, month=month, year=year)
    spent_by_cat = {
        row['category']: float(row['total'])
        for row in period_expenses_qs.values('category').annotate(total=Sum('amount'))
    }

    alerts = []
    for b in budgets_qs:
        spent = spent_by_cat.get(b.category, 0.0)
        limit = float(b.limit)
        if limit <= 0:
            continue
        pct = round(spent / limit * 100, 1)
        if pct >= 100:
            alerts.append({
                'category': b.category,
                'pct': pct,
                'status': 'danger',
                'msg': f"Over limit — spent ₹{spent:,.0f} of ₹{limit:,.0f}",
            })
        elif pct >= 80:
            alerts.append({
                'category': b.category,
                'pct': pct,
                'status': 'warning',
                'msg': f"{pct}% used — ₹{limit - spent:,.0f} remaining",
            })
    return alerts


def get_total_budget_summary(user, month, year) -> dict:
    """Return a summary dict for total budget vs spending."""
    budgets = list(CategoryBudget.objects.filter(user=user, month=month, year=year))
    total_goal = sum(float(b.limit) for b in budgets) or None
    total_spent = get_sum_amount(
        Expense.objects.filter(user=user, date__month=month, date__year=year)
    )

    if total_goal:
        pct = min(round(total_spent / total_goal * 100, 1), 9999)
        status = _budget_status(pct)
    else:
        pct = None
        status = 'none'

    return {
        'total_goal': total_goal,
        'total_spent': total_spent,
        'pct': pct,
        'status': status,
    }


def copy_budgets_from_last_month(user, month, year) -> int:
    """Copy budget limits from the previous month. Returns count of copied budgets."""
    prev_month, prev_year = get_previous_month(month, year)
    prev_budgets = CategoryBudget.objects.filter(user=user, month=prev_month, year=prev_year)

    copied = 0
    for b in prev_budgets:
        CategoryBudget.objects.update_or_create(
            user=user, category=b.category, month=month, year=year,
            defaults={'limit': b.limit}
        )
        copied += 1
    return copied
