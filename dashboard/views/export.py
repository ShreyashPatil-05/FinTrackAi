"""
Data Export View

Export user financial data to CSV format.
"""
import csv
import calendar
from datetime import date
from calendar import month_name

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse

from expenses.forms import get_category_choices
from expenses.models import Expense
from ..models import Income, Subscription, SavingsGoal
from ..utils import get_available_years


@login_required(login_url='login')
def export_data(request: HttpRequest) -> HttpResponse:
    """
    Export user's financial data to CSV format.
    
    Features:
        - Filter by date range (custom or month/year)
        - Filter by categories
        - Select data types (expenses, income, savings, subscriptions)
        - UTF-8 BOM for Excel compatibility
        
    Args:
        request: Django HttpRequest object
        
    Returns:
        HttpResponse: CSV file download or export form
    """
    all_cats = [c for c, _ in get_category_choices(request.user)]
    today = date.today()
    months = [(i, month_name[i]) for i in range(1, 13)]
    years = get_available_years(request.user)

    if request.method == 'POST':
        # date range mode vs month/year mode
        filter_mode = request.POST.get('filter_mode', 'range')
        date_from = date_to = None

        if filter_mode == 'monthyear':
            try:
                sel_month = int(request.POST.get('sel_month', today.month))
                sel_year  = int(request.POST.get('sel_year', today.year))
                last_day = calendar.monthrange(sel_year, sel_month)[1]
                date_from = f'{sel_year}-{sel_month:02d}-01'
                date_to   = f'{sel_year}-{sel_month:02d}-{last_day:02d}'
            except (ValueError, TypeError):
                pass
        elif filter_mode == 'year':
            try:
                sel_year = int(request.POST.get('sel_fullyear', today.year))
                date_from = f'{sel_year}-01-01'
                date_to   = f'{sel_year}-12-31'
            except (ValueError, TypeError):
                pass
        else:
            date_from = request.POST.get('date_from', '').strip() or None
            date_to   = request.POST.get('date_to',   '').strip() or None
        categories = request.POST.getlist('categories')
        data_types = request.POST.getlist('data_types')

        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="my_fintrack_data.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)

        if not data_types or 'expenses' in data_types:
            qs = Expense.objects.filter(user=request.user).order_by('-date')
            if date_from: qs = qs.filter(date__gte=date_from)
            if date_to:   qs = qs.filter(date__lte=date_to)
            if categories: qs = qs.filter(category__in=categories)
            writer.writerow(['=== EXPENSES ==='])
            writer.writerow(['date', 'title', 'category', 'amount'])
            for e in qs:
                writer.writerow([e.date, e.title, e.category, e.amount])
            writer.writerow([])

        if not data_types or 'income' in data_types:
            qs = Income.objects.filter(user=request.user).order_by('-date')
            if date_from: qs = qs.filter(date__gte=date_from)
            if date_to:   qs = qs.filter(date__lte=date_to)
            writer.writerow(['=== INCOME ==='])
            writer.writerow(['date', 'source', 'amount', 'description'])
            for i in qs:
                writer.writerow([i.date, i.source, i.amount, i.description])
            writer.writerow([])

        if not data_types or 'savings' in data_types:
            writer.writerow(['=== SAVINGS GOALS ==='])
            writer.writerow(['name', 'target', 'saved', 'target_date'])
            qs = SavingsGoal.objects.filter(user=request.user)
            for g in qs:
                writer.writerow([g.name, g.target, g.saved, g.target_date or ''])
            writer.writerow([])

        if not data_types or 'subscriptions' in data_types:
            writer.writerow(['=== SUBSCRIPTIONS ==='])
            writer.writerow(['name', 'amount', 'cycle', 'status', 'next_billing'])
            qs = Subscription.objects.filter(user=request.user)
            if date_from: qs = qs.filter(next_billing__gte=date_from)
            if date_to:   qs = qs.filter(next_billing__lte=date_to)
            for s in qs:
                writer.writerow([s.name, s.amount, s.cycle, s.status, s.next_billing])

        return response

    return render(request, 'dashboard/export.html', {
        'all_cats': all_cats,
        'months': months,
        'years': years,
        'today': today,
    })
