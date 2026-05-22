"""
Savings Service

Business logic for savings goals, contributions, and completion predictions.
"""
import math
from datetime import date
from dateutil.relativedelta import relativedelta

from django.db import transaction

from expenses.models import Expense
from ..models import SavingsGoal, SavingsContribution


def get_goals_with_progress(user):
    """
    Return all savings goals for a user with prefetched contributions.

    Args:
        user: Django User object

    Returns:
        QuerySet: SavingsGoal queryset with prefetched contributions
    """
    return SavingsGoal.objects.filter(user=user).prefetch_related('contributions')


def get_total_saved(user):
    """
    Return the total amount saved across all goals for a user.

    Args:
        user: Django User object

    Returns:
        float: Total saved amount
    """
    goals = get_goals_with_progress(user)
    return sum(float(g.saved) for g in goals)


def add_contribution(user, goal_pk, amount, contribution_date):
    """
    Add a contribution to a savings goal and create a matching expense.

    Raises ValueError if amount <= 0 or exceeds remaining target.

    Args:
        user: Django User object
        goal_pk: Primary key of the SavingsGoal
        amount: Contribution amount (float)
        contribution_date: Date of contribution (str or date)

    Returns:
        SavingsGoal: The updated goal instance

    Raises:
        ValueError: If amount is invalid or exceeds remaining target
        SavingsGoal.DoesNotExist: If goal not found for user
    """
    goal = SavingsGoal.objects.get(pk=goal_pk, user=user)

    if amount <= 0:
        raise ValueError('Amount must be greater than zero.')

    remaining = float(goal.target) - float(goal.saved)
    if amount > remaining:
        raise ValueError(
            f'Amount exceeds remaining target. You only need ₹{remaining:,.0f} more.'
        )

    fund_date = str(contribution_date) if not isinstance(contribution_date, str) else contribution_date

    with transaction.atomic():
        SavingsContribution.objects.create(goal=goal, amount=amount, date=fund_date)
        Expense.objects.create(
            user=user,
            title=f"Savings — {goal.name}",
            category='Savings',
            amount=amount,
            date=fund_date,
        )

    return goal


def predict_completion_date(goal):
    """
    Predict when a savings goal will be completed based on average monthly contributions.

    Args:
        goal: SavingsGoal instance (contributions should be prefetched or accessible)

    Returns:
        date or None: Predicted completion date, or None if not enough data
    """
    contributions = list(goal.contributions.order_by('date'))
    if len(contributions) < 2:
        return None

    # Group contributions by month to get monthly totals
    monthly_totals = {}
    for c in contributions:
        key = (c.date.year, c.date.month)
        monthly_totals[key] = monthly_totals.get(key, 0) + float(c.amount)

    if not monthly_totals:
        return None

    avg_monthly = sum(monthly_totals.values()) / len(monthly_totals)
    if avg_monthly <= 0:
        return None

    remaining = goal.remaining
    if remaining <= 0:
        return date.today()

    months_needed = remaining / avg_monthly
    months_needed = math.ceil(months_needed)
    return date.today() + relativedelta(months=months_needed)
