"""
Expenses Views

Handles CRUD operations for expense tracking with filtering,
pagination, and bulk operations.
"""
import json
from typing import Optional

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from datetime import date
from calendar import month_name

from .models import Expense, DEFAULT_CATEGORIES
from .forms import ExpenseForm, get_category_choices
from dashboard.utils import get_month_navigation, get_available_years, get_sum_amount, get_date_range
from dashboard.services.plan_service import check_limit


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
    Uses the same get_date_range() pattern as the dashboard —
    month/year nav and custom date range are mutually exclusive,
    resolved in one place in the view.
    """
    # ── Month / year nav (same util as dashboard) ──────────────────────────
    nav = get_month_navigation(request)
    view_month = nav['view_month']
    view_year  = nav['view_year']

    # ── Date range (resolves month vs custom range conflict) ───────────────
    date_range  = get_date_range(request, view_month, view_year)
    start_dt    = date_range['start_dt']
    end_dt      = date_range['end_dt']
    is_custom   = date_range['is_custom']
    filter_label = date_range['filter_label']
    start_str   = date_range['start_str']
    end_str     = date_range['end_str']

    # ── Filters ────────────────────────────────────────────────────────────
    search      = request.GET.get('search', '').strip()
    filter_cat  = request.GET.get('filter_cat', '').strip()

    expenses = Expense.objects.filter(
        user=request.user,
        date__gte=start_dt,
        date__lte=end_dt,
    ).order_by('-date', '-id')

    if search:
        expenses = expenses.filter(title__icontains=search)
    if filter_cat:
        expenses = expenses.filter(category=filter_cat)

    total = get_sum_amount(expenses)
    count = expenses.count()

    # ── Pagination ─────────────────────────────────────────────────────────
    try:
        per_page = int(request.GET.get('per_page', 10))
        if per_page not in (10, 20, 50):
            per_page = 10
    except (ValueError, TypeError):
        per_page = 10

    paginator   = Paginator(expenses, per_page)
    page_obj    = paginator.get_page(request.GET.get('page', 1))
    all_years   = get_available_years(request.user)
    all_cats    = [c for c, _ in get_category_choices(request.user)]

    context = {
        'expenses':      page_obj,
        'page_obj':      page_obj,
        'category_list': all_cats,
        'filter_cat':    filter_cat,
        'search':        search,
        'total':         total,
        'count':         count,
        'per_page':      per_page,
        'view_month':    view_month,
        'view_year':     view_year,
        'view_month_name': nav['view_month_name'],
        'filter_label':  filter_label,
        'prev_m':        nav['prev_m'],
        'prev_y':        nav['prev_y'],
        'next_m':        nav['next_m'],
        'next_y':        nav['next_y'],
        'all_years':     all_years,
        'month_names':   list(month_name)[1:],
        'is_custom':     is_custom,
        'start_date':    start_str,
        'end_date':      end_str,
    }

    # ── AJAX — return fragment only ─────────────────────────────────────────
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string(
            'expenses/partials/expense_list_partial.html',
            context,
            request=request,
        )
        return JsonResponse({'html': html})

    return render(request, 'expenses/expense_list.html', context)


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
            # ── Plan limit check ──────────────────────────────────────────────
            allowed, msg = check_limit(request.user, 'expense')
            if not allowed:
                messages.error(request, msg)
                return redirect('pricing')
            # ─────────────────────────────────────────────────────────────────
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
