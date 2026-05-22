"""
Subscription Management Views

Track recurring subscriptions and billing dates.
"""
import logging
from datetime import date, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.http import HttpRequest, HttpResponse

from ..models import Subscription
from ..services.subscription_service import (
    get_active_subscriptions,
    get_total_monthly_cost,
    get_total_yearly_cost,
    get_due_soon_pks,
    get_due_today_pks,
    get_upcoming_count,
)

logger = logging.getLogger(__name__)


@login_required(login_url='login')
def subscriptions(request: HttpRequest) -> HttpResponse:
    """
    List and manage subscriptions.

    Features:
        - View all subscriptions (active/paused/cancelled)
        - Total monthly and yearly costs
        - Upcoming billing alerts (next 7 days)
        - Auto-advance overdue billing dates

    Args:
        request: Django HttpRequest object

    Returns:
        HttpResponse: Subscriptions page
    """
    today = date.today()
    week_ahead = today + timedelta(days=7)

    # Auto-advance any overdue billing dates
    active_subs = get_active_subscriptions(request.user)
    for sub in active_subs.filter(next_billing__lt=today):
        sub.advance_billing_date()

    # Re-query after updates
    subs = Subscription.objects.filter(user=request.user)

    total_monthly = get_total_monthly_cost(request.user)
    total_yearly = get_total_yearly_cost(request.user)
    active_count = get_active_subscriptions(request.user).count()
    upcoming = get_upcoming_count(request.user, days=7)
    due_soon_pks = get_due_soon_pks(request.user, days=7)
    due_today_pks = get_due_today_pks(request.user)

    return render(request, 'dashboard/subscriptions.html', {
        'subs': subs,
        'total_monthly': total_monthly,
        'total_yearly': total_yearly,
        'active_count': active_count,
        'upcoming': upcoming,
        'due_soon_pks': due_soon_pks,
        'due_today_pks': due_today_pks,
        'cycle_choices': Subscription.CYCLE_CHOICES,
        'category_choices': Subscription.CATEGORY_CHOICES,
        'status_choices': Subscription.STATUS_CHOICES,
        'today': today,
        'week_ahead': week_ahead,
    })


@login_required(login_url='login')
def subscription_add(request: HttpRequest) -> HttpResponse:
    """
    Add a new subscription.

    Args:
        request: Django HttpRequest object

    Returns:
        HttpResponse: Redirect to subscriptions page
    """
    if request.method == 'POST':
        try:
            billing_date = request.POST.get('next_billing', '').strip()
            sub = Subscription.objects.create(
                user=request.user,
                name=request.POST.get('name', '').strip(),
                amount=float(request.POST.get('amount', 0)),
                cycle=request.POST.get('cycle', 'monthly'),
                category=request.POST.get('category', 'Other'),
                next_billing=billing_date,
                status=request.POST.get('status', 'active'),
            )
            messages.success(request, f'"{sub.name}" subscription added.')
        except Exception:
            messages.error(request, 'Could not add subscription.')
            return redirect('subscriptions')
        try:
            if sub.status == 'active':
                sub.advance_billing_date()
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to advance billing for subscription {sub.pk}: {e}")
    return redirect('subscriptions')


@never_cache
@login_required(login_url='login')
def subscription_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Edit an existing subscription.

    Args:
        request: Django HttpRequest object
        pk: Primary key of subscription

    Returns:
        HttpResponse: Redirect to subscriptions page
    """
    sub = get_object_or_404(Subscription, pk=pk, user=request.user)
    if request.method == 'POST':
        try:
            sub.name = request.POST.get('name', '').strip()
            sub.amount = float(request.POST.get('amount', sub.amount))
            sub.cycle = request.POST.get('cycle', sub.cycle)
            sub.category = request.POST.get('category', sub.category)
            sub.next_billing = request.POST.get('next_billing', sub.next_billing)
            sub.status = request.POST.get('status', sub.status)
            sub.save()
            messages.success(request, f'"{sub.name}" updated.')
        except Exception:
            messages.error(request, 'Could not update subscription.')
    return redirect('subscriptions')


@login_required(login_url='login')
def subscription_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Delete a subscription.

    Args:
        request: Django HttpRequest object
        pk: Primary key of subscription

    Returns:
        HttpResponse: Redirect to subscriptions page
    """
    sub = get_object_or_404(Subscription, pk=pk, user=request.user)
    name = sub.name
    sub.delete()
    messages.success(request, f'"{name}" deleted.')
    return redirect('subscriptions')
