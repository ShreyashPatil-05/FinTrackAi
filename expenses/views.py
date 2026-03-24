from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from datetime import date
from calendar import month_name

from .models import Expense, DEFAULT_CATEGORIES
from .forms import ExpenseForm, get_category_choices


def _all_categories(user):
    return [c for c, _ in get_category_choices(user)]


@login_required(login_url='login')
def expense_list(request):
    today = date.today()

    # Month/year nav
    try:
        view_month = int(request.GET.get('month', today.month))
        view_year  = int(request.GET.get('year',  today.year))
        if not (1 <= view_month <= 12):
            raise ValueError
    except (ValueError, TypeError):
        view_month, view_year = today.month, today.year

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

    # Month nav
    if view_month == 1:
        prev_m, prev_y = 12, view_year - 1
    else:
        prev_m, prev_y = view_month - 1, view_year
    if view_month == 12:
        next_m, next_y = 1, view_year + 1
    else:
        next_m, next_y = view_month + 1, view_year

    # Available years
    all_years = sorted(
        set(Expense.objects.filter(user=request.user).dates('date', 'year').values_list('date__year', flat=True)) | {today.year},
        reverse=True
    )

    return render(request, 'expenses/expense_list.html', {
        'expenses': expenses,
        'category_list': _all_categories(request.user),
        'selected_categories': selected_categories,
        'total': total,
        'count': expenses.count(),
        'view_month': view_month,
        'view_year': view_year,
        'view_month_name': month_name[view_month],
        'prev_m': prev_m, 'prev_y': prev_y,
        'next_m': next_m, 'next_y': next_y,
        'all_years': all_years,
        'month_names': list(month_name)[1:],
        'is_custom': is_custom,
        'search': search,
        'start_date': start_date,
        'end_date': end_date,
    })


@login_required(login_url='login')
def add_expense(request):
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



@login_required(login_url='login')
def edit_expense(request, pk):
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
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == 'POST':
        title = expense.title
        expense.delete()
        messages.success(request, f'"{title}" deleted.')
        return redirect('expense_list')
    return render(request, 'expenses/expense_confirm_delete.html', {'expense': expense})


@login_required(login_url='login')
def bulk_delete_expenses(request):
    if request.method == 'POST':
        ids = request.POST.getlist('selected_ids')
        count = Expense.objects.filter(pk__in=ids, user=request.user).count()
        Expense.objects.filter(pk__in=ids, user=request.user).delete()
        messages.success(request, f'{count} expense{"s" if count != 1 else ""} deleted.')
    return redirect('expense_list')
