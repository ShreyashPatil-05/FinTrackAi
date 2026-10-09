"""
dashboard/services/subscription_service.py

Business logic for subscription queries, cost calculations, and billing alerts.
All functions are read-only — no subscription records are created here.
"""
from datetime import date, timedelta

from ..models import Subscription


def get_active_subscriptions(user):
    """
    Return a queryset of all active subscriptions for a user.

    Args:
        user: Django User instance

    Returns:
        QuerySet: Subscription queryset filtered to status='active'
    """
    return Subscription.objects.filter(user=user, status="active")


def get_total_monthly_cost(user) -> float:
    """
    Return the total normalised monthly cost of all active subscriptions.

    Each subscription's cost is normalised to a monthly figure regardless
    of whether its billing cycle is weekly, monthly, or yearly.
    This uses the Subscription.monthly_cost property defined on the model.

    Args:
        user: Django User instance

    Returns:
        float: Sum of all monthly-equivalent subscription costs
    """
    active_subscriptions = get_active_subscriptions(user)
    return sum(subscription.monthly_cost for subscription in active_subscriptions)


def get_total_yearly_cost(user) -> float:
    """
    Return the total normalised yearly cost of all active subscriptions.

    Calculated as total_monthly_cost × 12.

    Args:
        user: Django User instance

    Returns:
        float: Annualised subscription cost
    """
    return get_total_monthly_cost(user) * 12


def get_subscriptions_due_soon(user, days_ahead: int = 7) -> set:
    """
    Return the primary keys of active subscriptions with a billing date
    within the next N days (inclusive of today).

    Args:
        user:       Django User instance
        days_ahead: Number of days to look ahead (default 7)

    Returns:
        set: Set of Subscription primary keys
    """
    today = date.today()
    cutoff_date = today + timedelta(days=days_ahead)

    upcoming_subscription_pks = (
        get_active_subscriptions(user)
        .filter(next_billing__gte=today, next_billing__lte=cutoff_date)
        .values_list("pk", flat=True)
    )
    return set(upcoming_subscription_pks)


def get_subscriptions_due_today(user) -> set:
    """
    Return the primary keys of active subscriptions with a billing date of today.

    Args:
        user: Django User instance

    Returns:
        set: Set of Subscription primary keys
    """
    today = date.today()
    due_today_pks = (
        get_active_subscriptions(user)
        .filter(next_billing=today)
        .values_list("pk", flat=True)
    )
    return set(due_today_pks)


def get_upcoming_subscription_count(user, days_ahead: int = 7) -> int:
    """
    Return the count of active subscriptions due within the next N days.

    Args:
        user:       Django User instance
        days_ahead: Number of days to look ahead (default 7)

    Returns:
        int: Number of upcoming subscriptions
    """
    return len(get_subscriptions_due_soon(user, days_ahead=days_ahead))
