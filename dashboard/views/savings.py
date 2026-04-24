"""
Savings Goals Management Views

Track savings goals and contributions.
"""
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.db import transaction
from django.http import HttpRequest, HttpResponse

from expenses.models import Expense
from ..models import SavingsGoal, SavingsContribution


def _fmt_amount(v):
    """Format amount with K/L suffix for large numbers."""
    v = float(v)
    if v >= 100000:
        return f"₹{v/100000:.1f}L"
    elif v >= 1000:
        return f"₹{v/1000:.1f}K"
    return f"₹{v:.0f}"


@login_required(login_url='login')
def savings_goals(request: HttpRequest) -> HttpResponse:
    """
    List all savings goals with progress tracking.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        HttpResponse: Savings goals page
    """
    goals = SavingsGoal.objects.filter(user=request.user).prefetch_related('contributions')
    total_saved = sum(float(g.saved) for g in goals)
    return render(request, 'dashboard/savings_goals.html', {
        'goals': goals,
        'total_saved_fmt': _fmt_amount(total_saved),
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
                name=request.POST['name'].strip(),
                target=float(request.POST['target']),
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
            goal.name        = request.POST['name'].strip()
            goal.target      = float(request.POST['target'])
            goal.target_date = request.POST.get('target_date') or None
            goal.icon        = request.POST.get('icon', goal.icon)
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
    goal = get_object_or_404(SavingsGoal, pk=pk, user=request.user)
    if request.method == 'POST':
        try:
            
            amount = float(request.POST['amount'])
            if amount <= 0:
                messages.error(request, 'Amount must be greater than zero.')
            else:
                remaining = float(goal.target) - float(goal.saved)
                if amount > remaining:
                    messages.error(request, f'Amount exceeds remaining target. You only need ₹{remaining:,.0f} more.')
                else:
                    fund_date = request.POST.get('date', '').strip() or str(date.today())
                    with transaction.atomic():
                        SavingsContribution.objects.create(goal=goal, amount=amount, date=fund_date)
                        Expense.objects.create(
                            user=request.user,
                            title=f"Savings — {goal.name}",
                            category='Savings',
                            amount=amount,
                            date=fund_date,
                        )
                    messages.success(request, f'₹{amount:,.0f} added to "{goal.name}".')
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
