"""
Income Management Views

CRUD operations for income tracking.
"""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.db.models import Sum
from django.http import HttpRequest, HttpResponse

from ..models import Income
from ..utils import get_month_navigation


@login_required(login_url='login')
def settings_income(request: HttpRequest) -> HttpResponse:
    """
    Income management page with month/year navigation.
    
    Features:
        - List income entries for selected month
        - Filter by source type
        - Month/year navigation
        - Total amount and record count
        
    Args:
        request: Django HttpRequest object
        
    Returns:
        HttpResponse: Income settings page
    """
    
    today = date.today()

    # Month/year navigation using utility
    nav = get_month_navigation(request)
    view_month = nav['view_month']
    view_year = nav['view_year']

    # Base queryset for selected month
    qs = Income.objects.filter(user=request.user, date__month=view_month, date__year=view_year)

    # Optional filters for browsing
    source_q = request.GET.get('source', '')
    if source_q:
        qs = qs.filter(source__icontains=source_q)

    total_amount  = float(qs.aggregate(Sum('amount'))['amount__sum'] or 0)
    total_records = qs.count()

    # Default date = today if on current month, else 1st of selected month
    if view_month == today.month and view_year == today.year:
        default_date = today.strftime('%Y-%m-%d')
    else:
        default_date = f'{view_year}-{view_month:02d}-01'

    return render(request, 'dashboard/settings.html', {
        'section': 'income',
        'incomes': qs,
        'total_amount': total_amount,
        'total_records': total_records,
        'source_q': source_q,
        'source_choices': Income.SOURCE_CHOICES,
        'view_month': view_month,
        'view_year': view_year,
        'view_month_name': nav['view_month_name'],
        'prev_m': nav['prev_m'],
        'prev_y': nav['prev_y'],
        'next_m': nav['next_m'],
        'next_y': nav['next_y'],
        'default_date': default_date,
    })


@login_required(login_url='login')
def income_add(request: HttpRequest) -> HttpResponse:
    """
    Add a new income entry.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        HttpResponse: Redirect to income settings
    """
    if request.method == 'POST':
        try:
            inc_date = request.POST['date']
            amount = Decimal(request.POST['amount'])
            if amount <= 0:
                messages.error(request, 'Amount must be greater than zero.')
                return redirect('settings_income')
            Income.objects.create(
                user=request.user,
                date=inc_date,
                source=request.POST.get('source', 'Other'),
                description=request.POST.get('description', '').strip(),
                amount=amount,
            )
            messages.success(request, 'Income added.')
            d = datetime.strptime(inc_date, '%Y-%m-%d')
            return redirect(f"/settings/income/?month={d.month}&year={d.year}")
        except (InvalidOperation, KeyError):
            messages.error(request, 'Failed to add income. Check the amount entered.')
    return redirect('settings_income')


@never_cache
@login_required(login_url='login')
def income_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Edit an existing income entry.
    
    Args:
        request: Django HttpRequest object
        pk: Primary key of income entry
        
    Returns:
        HttpResponse: Redirect to income settings
    """
    income = get_object_or_404(Income, pk=pk, user=request.user)
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST['amount'])
            if amount <= 0:
                messages.error(request, 'Amount must be greater than zero.')
                return redirect('settings_income')
            income.date        = request.POST['date']
            income.source      = request.POST.get('source', income.source)
            income.description = request.POST.get('description', '').strip()
            income.amount      = amount
            income.save()
            messages.success(request, 'Income updated.')
        except (InvalidOperation, KeyError):
            messages.error(request, 'Could not update income. Check the amount entered.')
    return redirect('settings_income')


@login_required(login_url='login')
def income_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Delete an income entry.
    
    Args:
        request: Django HttpRequest object
        pk: Primary key of income entry
        
    Returns:
        HttpResponse: Redirect to income settings
    """
    Income.objects.filter(pk=pk, user=request.user).delete()
    messages.success(request, 'Income entry deleted.')
    return redirect('settings_income')
