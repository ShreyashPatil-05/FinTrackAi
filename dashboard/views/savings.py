"""
Savings Goals Management Views

Track savings goals and contributions.
"""
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.http import HttpRequest, HttpResponse

from ..models import SavingsGoal
from ..utils import format_currency
from ..services.savings_service import (
    get_goals_with_progress,
    get_total_saved,
    add_contribution,
)


@login_required(login_url='login')
def savings_goals(request: HttpRequest) -> HttpResponse:
    """
    List all savings goals with progress tracking.

    Args:
        request: Django HttpRequest object

    Returns:
        HttpResponse: Savings goals page
    """
    goals = get_goals_with_progress(request.user)
    total_saved = get_total_saved(request.user)
    return render(request, 'dashboard/savings_goals.html', {
        'goals': goals,
        'total_saved_fmt': format_currency(total_saved),
        'icon_choices': SavingsGoal.ICON_CHOICES,
    })


@login_required(login_url='login')
def savings_goal_add(request: HttpRequest) -> HttpResponse:
    """
    Create a new savings goal.

    Args:
        request: Django HttpRequest object

    Returns:
        HttpResponse: Redirect to savings goals page
    """
    if request.method == 'POST':
        try:
            goal = SavingsGoal.objects.create(
                user=request.user,
                name=request.POST.get('name', '').strip(),
                target=float(request.POST.get('target', 0)),
                target_date=request.POST.get('target_date') or None,
                icon=request.POST.get('icon', 'piggy-bank'),
            )
            messages.success(request, f'Goal "{goal.name}" created.')
        except Exception:
            messages.error(request, 'Could not create goal.')
    return redirect('savings_goals')


@never_cache
@login_required(login_url='login')
def savings_goal_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Edit an existing savings goal.

    Args:
        request: Django HttpRequest object
        pk: Primary key of savings goal

    Returns:
        HttpResponse: Redirect to savings goals page
    """
    goal = get_object_or_404(SavingsGoal, pk=pk, user=request.user)
    if request.method == 'POST':
        try:
            goal.name = request.POST.get('name', '').strip()
            goal.target = float(request.POST.get('target', goal.target))
            goal.target_date = request.POST.get('target_date') or None
            goal.icon = request.POST.get('icon', goal.icon)
            goal.save()
            messages.success(request, f'Goal "{goal.name}" updated.')
        except Exception:
            messages.error(request, 'Could not update goal.')
    return redirect('savings_goals')


@login_required(login_url='login')
def savings_goal_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """
    View savings goal details and contribution history.

    Args:
        request: Django HttpRequest object
        pk: Primary key of savings goal

    Returns:
        HttpResponse: Savings goal detail page
    """
    goal = get_object_or_404(SavingsGoal, pk=pk, user=request.user)
    all_contributions = goal.contributions.order_by('-date')
    contributions = all_contributions[:3]
    total_contributions = all_contributions.count()
    return render(request, 'dashboard/savings_goal_detail.html', {
        'goal': goal,
        'contributions': contributions,
        'total_contributions': total_contributions,
    })


@login_required(login_url='login')
def savings_goal_add_funds(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Add funds to a savings goal.

    Creates both a savings contribution and an expense entry.

    Args:
        request: Django HttpRequest object
        pk: Primary key of savings goal

    Returns:
        HttpResponse: Redirect to savings goal detail page
    """
    if request.method == 'POST':
        try:
            amount = float(request.POST.get('amount', 0))
            fund_date = request.POST.get('date', '').strip()
            add_contribution(request.user, pk, amount, fund_date or str(date.today()))
            messages.success(request, f'₹{amount:,.0f} added to goal.')
        except ValueError as e:
            messages.error(request, str(e))
        except SavingsGoal.DoesNotExist:
            messages.error(request, 'Goal not found.')
        except Exception:
            messages.error(request, 'Could not deposit funds. Please try again.')
    return redirect('savings_goal_detail', pk=pk)


@login_required(login_url='login')
def savings_goal_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Delete a savings goal.

    Args:
        request: Django HttpRequest object
        pk: Primary key of savings goal

    Returns:
        HttpResponse: Redirect to savings goals page
    """
    goal = get_object_or_404(SavingsGoal, pk=pk, user=request.user)
    name = goal.name
    goal.delete()
    messages.success(request, f'Goal "{name}" deleted.')
    return redirect('savings_goals')
