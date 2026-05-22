"""
Subscription Service

Business logic for subscription queries, cost calculations, and billing alerts.
"""
from datetime import date, timedelta

from ..models import Subscription


def get_active_subscriptions(user):
    """
    Return a queryset of active subscriptions for a user.

    Args:
        user: Django User object

    Returns:
        QuerySet: Active Subscription queryset
    """
    return Subscription.objects.filter(user=user, status='active')


def get_total_monthly_cost(user):
    """
    Return the total equivalent monthly cost of all active subscriptions.

    Args:
        user: Django User object

    Returns:
        float: Total monthly cost
    """
    return sum(s.monthly_cost for s in get_active_subscriptions(user))


def get_total_yearly_cost(user):
    """
    Return the total equivalent yearly cost of all active subscriptions.

    Args:
        user: Django User object

    Returns:
        float: Total yearly cost
    """
    return get_total_monthly_cost(user) * 12


def get_due_soon_pks(user, days=7):
    """
    Return a set of PKs for active subscriptions due within the next N days.

    Args:
        user: Django User object
        days: Number of days to look ahead (default 7)

    Returns:
        set: Set of subscription PKs
    """
    today = date.today()
    week_ahead = today + timedelta(days=days)
    qs = get_active_subscriptions(user).filter(
        next_billing__gte=today, next_billing__lte=week_ahead
    )
    return set(qs.values_list('pk', flat=True))


def get_due_today_pks(user):
    """
    Return a set of PKs for active subscriptions due today.

    Args:
        user: Django User object

    Returns:
        set: Set of subscription PKs
    """
    today = date.today()
    return set(
        get_active_subscriptions(user)
        .filter(next_billing=today)
        .values_list('pk', flat=True)
    )


def get_upcoming_count(user, days=7):
    """
    Return the count of active subscriptions due within the next N days.

    Args:
        user: Django User object
        days: Number of days to look ahead (default 7)

    Returns:
        int: Count of upcoming subscriptions
    """
    return len(get_due_soon_pks(user, days=days))
