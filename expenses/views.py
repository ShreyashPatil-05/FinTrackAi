"""
Expenses Views

Handles CRUD operations for expense tracking with filtering,
pagination, and bulk operations.
"""
from typing import Optional

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.db.models import Sum
from django.http import HttpRequest, HttpResponse
from django.core.paginator import Paginator
from datetime import date
from calendar import month_name

from .models import Expense, DEFAULT_CATEGORIES
from .forms import ExpenseForm, get_category_choices
from dashboard.utils import get_month_navigation, get_available_years


def _all_categories(user):
    """
    Get all available categories for a user (default + custom).
    
    Args:
        user: Django User object
        
    Returns:
        list: Category names as strings
    """
    return [c for c, _ in get_category_choices(user)]


@login_required(login_url='login')
def expense_list(request: HttpRequest) -> HttpResponse:
    """
    Display paginated list of expenses with filtering and search.
    
    Features:
        - Month/year navigation
        - Custom date range filtering
        - Category filtering (multi-select)
        - Text search on expense title
        - User-selectable page size (10/20/50)
        - Total amount and count display
        
    Args:
        request: Django HttpRequest object
        
    Returns:
        HttpResponse: Rendered expense list template
    """
    today = date.today()

    # Month/year nav using utility
    nav = get_month_navigation(request)
    view_month = nav['view_month']
    view_year = nav['view_year']

    # Filters
    search              = request.GET.get('search', '')
    selected_categories = request.GET.getlist('category')
    start_date          = request.GET.get('start_date', '')
    end_date            = request.GET.get('end_date', '')
    is_custom = bool(start_date and end_date)

    expenses = Expense.objects.filter(user=request.user).order_by('-date', '-id')

    if is_custom:
        expenses = expenses.filter(date__gte=start_date, date__lte=end_date)
    else:
        expenses = expenses.filter(date__month=view_month, date__year=view_year)

    if search:
        expenses = expenses.filter(title__icontains=search)
    if selected_categories:
        expenses = expenses.filter(category__in=selected_categories)

    total = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    count = expenses.count()

    # Pagination — user-selectable page size
    try:
        per_page = int(request.GET.get('per_page', 10))
        if per_page not in (10, 20, 50):
            per_page = 10
    except (ValueError, TypeError):
        per_page = 10
    paginator = Paginator(expenses, per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Available years using utility
    all_years = get_available_years(request.user)

    return render(request, 'expenses/expense_list.html', {
        'expenses': page_obj,
        'page_obj': page_obj,
        'category_list': _all_categories(request.user),
        'selected_categories': selected_categories,
        'total': total,
        'count': count,
        'per_page': per_page,
        'view_month': view_month,
        'view_year': view_year,
        'view_month_name': nav['view_month_name'],
        'prev_m': nav['prev_m'],
        'prev_y': nav['prev_y'],
        'next_m': nav['next_m'],
        'next_y': nav['next_y'],
        'all_years': all_years,
        'month_names': list(month_name)[1:],
        'is_custom': is_custom,
        'search': search,
        'start_date': start_date,
        'end_date': end_date,
    })


@login_required(login_url='login')
def add_expense(request):
    """
    Create a new expense entry.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        HttpResponse: Expense form or redirect to list on success
    """
    if request.method == 'POST':
        form = ExpenseForm(request.POST, user=request.user)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            expense.save()
            messages.success(request, f'Expense "{expense.title}" added.')
            return redirect('expense_list')
    else:
        form = ExpenseForm(user=request.user)
    return render(request, 'expenses/expense_form.html', {'form': form, 'action': 'Add'})



@never_cache
@login_required(login_url='login')
def edit_expense(request, pk):
    """
    Edit an existing expense entry.
    
    Args:
        request: Django HttpRequest object
        pk: Primary key of expense to edit
        
    Returns:
        HttpResponse: Expense form or redirect to list on success
        
    Raises:
        Http404: If expense doesn't exist or doesn't belong to user
    """
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'"{expense.title}" updated.')
            return redirect('expense_list')
    else:
        form = ExpenseForm(instance=expense, user=request.user)
    return render(request, 'expenses/expense_form.html', {'form': form, 'action': 'Edit'})


@login_required(login_url='login')
def delete_expense(request, pk):
    """
    Delete a single expense entry with confirmation.
    
    Args:
        request: Django HttpRequest object
        pk: Primary key of expense to delete
        
    Returns:
        HttpResponse: Confirmation page (GET) or redirect to list (POST)
        
    Raises:
        Http404: If expense doesn't exist or doesn't belong to user
    """
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == 'POST':
        title = expense.title
        expense.delete()
        messages.success(request, f'"{title}" deleted.')
        return redirect('expense_list')
    return render(request, 'expenses/expense_confirm_delete.html', {'expense': expense})


@login_required(login_url='login')
def bulk_delete_expenses(request):
    """
    Delete multiple expenses at once (bulk operation).
    
    Expects POST data with 'selected_ids' list of expense primary keys.
    Only deletes expenses belonging to the current user.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        HttpResponse: Redirect to expense list with success message
    """
    if request.method == 'POST':
        ids = request.POST.getlist('selected_ids')
        count = Expense.objects.filter(pk__in=ids, user=request.user).count()
        Expense.objects.filter(pk__in=ids, user=request.user).delete()
        messages.success(request, f'{count} expense{"s" if count != 1 else ""} deleted.')
    return redirect('expense_list')
