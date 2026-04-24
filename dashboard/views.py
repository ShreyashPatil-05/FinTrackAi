import csv
import io
import json
from datetime import datetime, date
from calendar import month_name

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.db.models import Sum
from django.http import JsonResponse, HttpResponseNotAllowed
from django.urls import reverse

from expenses.models import Expense, DEFAULT_CATEGORIES
from .models import CustomCategory, Income, Subscription, CategoryBudget, SavingsGoal, SavingsContribution


# ---------------------------
# Landing Page
# ---------------------------

def landing(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "landing.html")


# ---------------------------
# Dashboard
# ---------------------------

@login_required(login_url='login')
def dashboard_view(request):
    from .models import UserProfile
    profile_obj, _ = UserProfile.objects.get_or_create(user=request.user)

    # Advance overdue subscriptions on every dashboard load
    from datetime import date as _today_date
    _today = _today_date.today()
    for _sub in Subscription.objects.filter(
        user=request.user, status='active', next_billing__lt=_today
    ):
        try:
            _sub.advance_billing_date()
        except Exception:
            pass
    show_tour = not profile_obj.onboarding_complete

    now = datetime.now()

    # ── resolve active month/year (for month nav) ──
    try:
        view_month = int(request.GET.get('month', now.month))
        view_year  = int(request.GET.get('year',  now.year))
        if not (1 <= view_month <= 12):
            raise ValueError
    except (ValueError, TypeError):
        view_month, view_year = now.month, now.year

    # ── income: sum Income entries for the active month/year ──
    income = float(
        Income.objects.filter(user=request.user, date__month=view_month, date__year=view_year)
        .aggregate(Sum('amount'))['amount__sum'] or 0
    )

    # ── custom date-range filter ──
    start_str    = request.GET.get('start_date', '')
    end_str      = request.GET.get('end_date',   '')
    filter_cat   = request.GET.get('filter_cat', '')

    if start_str and end_str:
        try:
            start_dt = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_dt   = datetime.strptime(end_str,   '%Y-%m-%d').date()
            is_custom = True
            filter_label = f"{start_dt.strftime('%d %b')} – {end_dt.strftime('%d %b %Y')}"
        except ValueError:
            is_custom = False
            start_dt = date(view_year, view_month, 1)
            end_dt   = date(view_year, view_month, _last_day(view_year, view_month))
            filter_label = f"{month_name[view_month]} {view_year}"
    else:
        is_custom = False
        start_dt = date(view_year, view_month, 1)
        end_dt   = date(view_year, view_month, _last_day(view_year, view_month))
        filter_label = f"{month_name[view_month]} {view_year}"

    # for custom range, re-sum income over that date range
    if is_custom:
        income = float(
            Income.objects.filter(user=request.user, date__gte=start_dt, date__lte=end_dt)
            .aggregate(Sum('amount'))['amount__sum'] or 0
        )

    all_expenses    = Expense.objects.filter(user=request.user)
    period_expenses = all_expenses.filter(date__gte=start_dt, date__lte=end_dt)
    if filter_cat:
        period_expenses = period_expenses.filter(category=filter_cat)

    total   = float(period_expenses.aggregate(Sum('amount'))['amount__sum'] or 0)
    balance = income - total
    savings_rate = round((balance / income * 100), 1) if income > 0 else 0
    savings_rate = max(0, min(100, savings_rate))

    # ── financial health ──
    if savings_rate >= 30:
        health_label, health_color = 'Excellent', '#16a34a'
    elif savings_rate >= 15:
        health_label, health_color = 'Good', '#2563eb'
    elif savings_rate >= 0:
        health_label, health_color = 'Fair', '#d97706'
    else:
        health_label, health_color = 'Over Budget', '#dc2626'

    if savings_rate >= 30:
        health_tip = "Great work! You're saving more than usual."
    elif savings_rate >= 15:
        health_tip = "You're on track. Try to push savings above 30%."
    elif savings_rate >= 0:
        health_tip = "Spending is high. Review your top categories."
    else:
        health_tip = "You've exceeded your income budget this period."

    # ── prev month comparison ──
    if not is_custom:
        pm, py = (12, view_year - 1) if view_month == 1 else (view_month - 1, view_year)
        prev_total = float(
            all_expenses.filter(date__month=pm, date__year=py)
            .aggregate(Sum('amount'))['amount__sum'] or 0
        )
        prev_income = float(
            Income.objects.filter(user=request.user, date__month=pm, date__year=py)
            .aggregate(Sum('amount'))['amount__sum'] or 0
        )
        prev_savings_rate = max(0, round(((prev_income - prev_total) / prev_income * 100), 1)) if prev_income > 0 else 0
        savings_delta = round(savings_rate - prev_savings_rate, 1)
    else:
        savings_delta = None

    # ── prev / next month nav links ──
    if view_month == 1:
        prev_m, prev_y = 12, view_year - 1
    else:
        prev_m, prev_y = view_month - 1, view_year
    if view_month == 12:
        next_m, next_y = 1, view_year + 1
    else:
        next_m, next_y = view_month + 1, view_year

    # ── category breakdown ──
    cat_data    = period_expenses.values('category').annotate(total=Sum('amount')).order_by('-total')
    cat_labels  = [c['category'] for c in cat_data]
    cat_amounts = [float(c['total']) for c in cat_data]
    top_categories = list(zip(cat_labels, cat_amounts))[:5]

    # ── daily spending ──
    daily_raw     = period_expenses.values('date').annotate(total=Sum('amount')).order_by('date')
    daily_labels  = [str(d['date']) for d in daily_raw]
    daily_amounts = [float(d['total']) for d in daily_raw]

    # ── available years for dropdown ──
    year_dates = all_expenses.dates('date', 'year')
    years = sorted(set([d.year for d in year_dates] + [now.year]), reverse=True)

    # ── month names list (1-indexed) ──
    month_names = list(month_name)[1:]  # ['January', ..., 'December']

    # ── spending forecast (current month only) ──
    forecast = None
    if not is_custom and view_month == now.month and view_year == now.year:
        import calendar
        days_in_month = calendar.monthrange(view_year, view_month)[1]
        day_of_month  = now.day
        if day_of_month > 0 and total > 0:
            daily_avg        = total / day_of_month
            forecast_total   = round(daily_avg * days_in_month, 0)
            days_left        = days_in_month - day_of_month
            forecast_balance = round(income - forecast_total, 0)
            forecast_pct     = min(round(forecast_total / income * 100, 1), 999) if income > 0 else None
            if forecast_total <= income:
                forecast_status = 'good'
                forecast_msg    = f"On track — projected to spend ₹{forecast_total:,.0f} this month."
            elif forecast_total <= income * 1.1:
                forecast_status = 'warning'
                forecast_msg    = f"Slightly over — projected to spend ₹{forecast_total:,.0f}, just above your income."
            else:
                forecast_status = 'danger'
                forecast_msg    = f"Over budget — projected to spend ₹{forecast_total:,.0f} by month end."
            forecast = {
                'daily_avg':        round(daily_avg, 0),
                'forecast_total':   forecast_total,
                'forecast_balance': forecast_balance,
                'forecast_pct':     forecast_pct,
                'days_left':        days_left,
                'status':           forecast_status,
                'msg':              forecast_msg,
            }

    # ── categories for filter dropdown ──
    from expenses.forms import get_category_choices
    all_cats = [c for c, _ in get_category_choices(request.user)]

    # ── budget alerts (current month only, not custom range) ──
    budget_alerts = []
    if not is_custom and view_month == now.month and view_year == now.year:
        budgets_qs = CategoryBudget.objects.filter(
            user=request.user, month=view_month, year=view_year
        )
        spent_by_cat = {
            row['category']: float(row['total'])
            for row in period_expenses.values('category').annotate(total=Sum('amount'))
        }
        for b in budgets_qs:
            spent = spent_by_cat.get(b.category, 0.0)
            limit = float(b.limit)
            if limit > 0:
                pct = round(spent / limit * 100, 1)
                if pct >= 100:
                    budget_alerts.append({
                        'category': b.category,
                        'pct': pct,
                        'status': 'danger',
                        'msg': f"Over limit — spent ₹{spent:,.0f} of ₹{limit:,.0f}",
                    })
                elif pct >= 80:
                    budget_alerts.append({
                        'category': b.category,
                        'pct': pct,
                        'status': 'warning',
                        'msg': f"{pct}% used — ₹{limit - spent:,.0f} remaining",
                    })

    context = {
        'income': income,
        'total': total,
        'balance': balance,
        'savings_rate': savings_rate,
        'savings_delta': savings_delta,
        'health_label': health_label,
        'health_color': health_color,
        'health_tip': health_tip,
        'filter_label': filter_label,
        'is_custom': is_custom,
        'start_date': start_str,
        'end_date': end_str,
        'filter_cat': filter_cat,
        'view_month': view_month,
        'view_year': view_year,
        'prev_m': prev_m, 'prev_y': prev_y,
        'next_m': next_m, 'next_y': next_y,
        'years': years,
        'all_cats': all_cats,
        'month_names': month_names,
        'top_categories': top_categories,
        'top_cat_placeholders': range(5 - len(top_categories)),
        'cat_labels_json': json.dumps(cat_labels),
        'cat_amounts_json': json.dumps(cat_amounts),
        'daily_labels_json': json.dumps(daily_labels),
        'daily_amounts_json': json.dumps(daily_amounts),
        'count': period_expenses.count(),
        'show_tour': show_tour,
        'forecast': forecast,
        'budget_alerts': budget_alerts,
    }
    recent = list(period_expenses.order_by('-date')[:5])
    context['recent_expenses'] = recent
    context['recent_placeholders'] = range(max(0, 5 - len(recent)))
    return render(request, 'dashboard/dashboard.html', context)


def _last_day(year, month):
    import calendar
    return calendar.monthrange(year, month)[1]


# ---------------------------
# Tour — mark complete
# ---------------------------

@login_required(login_url='login')
def tour_complete(request):
    if request.method == 'POST':
        from .models import UserProfile
        profile_obj, _ = UserProfile.objects.get_or_create(user=request.user)
        profile_obj.onboarding_complete = True
        profile_obj.save(update_fields=['onboarding_complete'])
        return JsonResponse({'ok': True})
    return HttpResponseNotAllowed(['POST'])


# ---------------------------
# Export user data
# ---------------------------

@login_required(login_url='login')
def export_data(request):
    import csv
    from calendar import month_name
    from django.http import HttpResponse
    from expenses.forms import get_category_choices

    all_cats = [c for c, _ in get_category_choices(request.user)]
    today = date.today()
    months = [(i, month_name[i]) for i in range(1, 13)]
    years = list(range(today.year, today.year - 6, -1))

    if request.method == 'POST':
        # date range mode vs month/year mode
        filter_mode = request.POST.get('filter_mode', 'range')
        date_from = date_to = None

        if filter_mode == 'monthyear':
            try:
                sel_month = int(request.POST.get('sel_month', today.month))
                sel_year  = int(request.POST.get('sel_year', today.year))
                import calendar
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

@never_cache
@login_required(login_url='login')
def profile(request):
    from .models import UserProfile
    user = request.user
    profile_obj, _ = UserProfile.objects.get_or_create(user=user)
    success = False

    if request.method == "POST":
        action = request.POST.get('action', 'profile')

        if action == 'avatar':
            if 'avatar' in request.FILES:
                avatar_file = request.FILES['avatar']

                if avatar_file.size > 2 * 1024 * 1024:
                    messages.error(request, 'Image too large. Maximum size is 2MB.')
                    return redirect('profile')

                header = avatar_file.read(12)
                avatar_file.seek(0)
                allowed_signatures = [
                    b'\xff\xd8\xff',
                    b'\x89PNG\r\n\x1a\n',
                    b'GIF87a', b'GIF89a',
                    b'RIFF',
                ]
                if not any(header.startswith(sig) for sig in allowed_signatures):
                    messages.error(request, 'Invalid file type. Only JPEG, PNG, GIF and WebP are allowed.')
                    return redirect('profile')

                # Delete old avatar safely (works for both local and S3)
                if profile_obj.avatar:
                    try:
                        profile_obj.avatar.delete(save=False)
                    except Exception:
                        pass
                profile_obj.avatar = avatar_file
                profile_obj.save(update_fields=['avatar'])
                success = True
        elif action == 'remove_avatar':
            if profile_obj.avatar:
                try:
                    profile_obj.avatar.delete(save=False)
                except Exception:
                    pass
                profile_obj.avatar = None
                profile_obj.save(update_fields=['avatar'])
                success = True
        else:
            new_username = request.POST.get("username", "").strip()
            if not new_username:
                messages.error(request, 'Username cannot be empty.')
                return redirect('profile')
            if User.objects.exclude(pk=user.pk).filter(username=new_username).exists():
                messages.error(request, f'Username "{new_username}" is already taken.')
                return redirect('profile')
            user.first_name = request.POST.get("first_name", "").strip()
            user.last_name  = request.POST.get("last_name", "").strip()
            user.username   = new_username
            user.email      = request.POST.get("email", "").strip()
            user.save()
            success = True

    return render(request, 'dashboard/profile.html', {
        'success': success,
        'profile_obj': profile_obj,
    })


@login_required(login_url='login')
def delete_account(request):
    if request.method == 'POST':
        password = request.POST.get('confirm_password', '')
        if not request.user.check_password(password):
            messages.error(request, 'Incorrect password. Account not deleted.')
            return redirect('profile')
        user = request.user
        from django.contrib.auth import logout
        logout(request)
        user.delete()
        messages.success(request, 'Your account has been deleted.')
        return redirect('landing')
    return redirect('profile')


# ---------------------------
# Settings — dispatcher
# ---------------------------

@login_required(login_url='login')
def settings(request):
    return redirect('settings_income')


# ---------------------------
# Settings — Income
# ---------------------------

@login_required(login_url='login')
def settings_income(request):
    from calendar import month_name as _month_name
    import calendar as _cal
    from datetime import date as _date

    today = _date.today()

    # Month/year navigation
    try:
        view_month = int(request.GET.get('month', today.month))
        view_year  = int(request.GET.get('year',  today.year))
        if not (1 <= view_month <= 12):
            raise ValueError
    except (ValueError, TypeError):
        view_month, view_year = today.month, today.year

    # Prev/next month nav
    if view_month == 1:
        prev_m, prev_y = 12, view_year - 1
    else:
        prev_m, prev_y = view_month - 1, view_year
    if view_month == 12:
        next_m, next_y = 1, view_year + 1
    else:
        next_m, next_y = view_month + 1, view_year

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
        'view_month_name': _month_name[view_month],
        'prev_m': prev_m, 'prev_y': prev_y,
        'next_m': next_m, 'next_y': next_y,
        'default_date': default_date,
    })


@login_required(login_url='login')
def income_add(request):
    if request.method == 'POST':
        try:
            from decimal import Decimal, InvalidOperation
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
            from datetime import datetime
            d = datetime.strptime(inc_date, '%Y-%m-%d')
            return redirect(f"/settings/income/?month={d.month}&year={d.year}")
        except (InvalidOperation, KeyError):
            messages.error(request, 'Failed to add income. Check the amount entered.')
    return redirect('settings_income')



@never_cache
@login_required(login_url='login')
def income_edit(request, pk):
    income = get_object_or_404(Income, pk=pk, user=request.user)
    if request.method == 'POST':
        try:
            from decimal import Decimal, InvalidOperation
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
def income_delete(request, pk):
    Income.objects.filter(pk=pk, user=request.user).delete()
    messages.success(request, 'Income entry deleted.')
    return redirect('settings_income')


# ---------------------------
# Settings — Categories
# ---------------------------

@login_required(login_url='login')
def settings_categories(request):
    default_categories = DEFAULT_CATEGORIES
    custom_categories  = CustomCategory.objects.filter(user=request.user)
    success = False
    error   = None

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add":
            name = request.POST.get("name", "").strip().title()
            if not name:
                error = "Category name cannot be empty."
            elif name in default_categories:
                error = f'"{name}" already exists as a default category.'
            elif CustomCategory.objects.filter(user=request.user, name=name).exists():
                error = f'"{name}" already exists.'
            else:
                CustomCategory.objects.create(user=request.user, name=name)
                success = True

        elif action == "delete":
            cat_id = request.POST.get("cat_id")
            CustomCategory.objects.filter(pk=cat_id, user=request.user).delete()
            return redirect('settings_categories')

    return render(request, 'dashboard/settings.html', {
        'section': 'categories',
        'default_categories': default_categories,
        'custom_categories': custom_categories,
        'success': success,
        'error': error,
    })


# ---------------------------
# Settings — Budget
# ---------------------------

@never_cache
@login_required(login_url='login')
def settings_budget(request):
    from expenses.forms import get_category_choices
    from expenses.models import Expense
    from datetime import date as _date
    import calendar as _cal

    today = _date.today()

    # Month/year navigation
    try:
        view_month = int(request.GET.get('month', today.month))
        view_year  = int(request.GET.get('year',  today.year))
        if not (1 <= view_month <= 12):
            raise ValueError
    except (ValueError, TypeError):
        view_month, view_year = today.month, today.year

    categories = [c for c, _ in get_category_choices(request.user)]

    if request.method == 'POST':
        for cat in categories:
            key = f"limit_{cat}"
            val = request.POST.get(key, '').strip()
            if val:
                try:
                    CategoryBudget.objects.update_or_create(
                        user=request.user, category=cat,
                        month=view_month, year=view_year,
                        defaults={'limit': float(val)}
                    )
                except ValueError:
                    pass
            else:
                CategoryBudget.objects.filter(
                    user=request.user, category=cat,
                    month=view_month, year=view_year
                ).delete()
        messages.success(request, 'Budgets saved.')
        return redirect(f"{request.path}?month={view_month}&year={view_year}")

    # Load budgets for this month
    budgets = {
        b.category: b
        for b in CategoryBudget.objects.filter(
            user=request.user, month=view_month, year=view_year
        )
    }

    # Spending for this month
    month_expenses = (
        Expense.objects.filter(user=request.user, date__month=view_month, date__year=view_year)
        .values('category').annotate(spent=Sum('amount'))
    )
    spent_map = {row['category']: float(row['spent']) for row in month_expenses}
    total_spent = sum(spent_map.values())

    # Total budget goal = sum of all saved category limits (auto-computed, no manual entry)
    total_goal = sum(float(b.limit) for b in budgets.values()) or None
    if total_goal:
        total_pct = min(round(total_spent / total_goal * 100, 1), 9999)
        total_over = total_spent - total_goal
        total_status = 'danger' if total_pct >= 100 else ('warning' if total_pct >= 80 else 'ok')
    else:
        total_pct = total_over = None
        total_status = 'none'

    budget_rows = []
    for cat in categories:
        budget = budgets.get(cat)
        limit  = float(budget.limit) if budget else None
        spent  = spent_map.get(cat, 0.0)
        if limit:
            pct = min(round(spent / limit * 100, 1), 9999)
            remaining = limit - spent
            if pct >= 100:
                status = 'danger'
            elif pct >= 80:
                status = 'warning'
            else:
                status = 'ok'
        else:
            pct, remaining, status = None, None, 'none'
        budget_rows.append({
            'category': cat,
            'limit': limit,
            'spent': spent,
            'remaining': remaining,
            'pct': pct,
            'status': status,
        })

    # Month nav
    if view_month == 1:
        prev_m, prev_y = 12, view_year - 1
    else:
        prev_m, prev_y = view_month - 1, view_year
    if view_month == 12:
        next_m, next_y = 1, view_year + 1
    else:
        next_m, next_y = view_month + 1, view_year

    def fmt_amount(v):
        if v >= 100000:
            return f"₹{v/100000:.1f}L"
        elif v >= 1000:
            return f"₹{v/1000:.1f}K"
        return f"₹{v:.0f}"

    return render(request, 'dashboard/settings.html', {
        'section': 'budget',
        'budget_rows': budget_rows,
        'view_month': view_month,
        'view_year': view_year,
        'view_month_name': _cal.month_name[view_month],
        'prev_m': prev_m, 'prev_y': prev_y,
        'next_m': next_m, 'next_y': next_y,
        'total_goal': total_goal,
        'total_spent': total_spent,
        'total_pct': total_pct,
        'total_over': total_over,
        'total_status': total_status,
        'total_spent_fmt': fmt_amount(total_spent),
        'total_goal_fmt': fmt_amount(total_goal) if total_goal else None,
    })


# ---------------------------
# Settings — Upload Data
# ---------------------------

@login_required(login_url='login')
def settings_upload(request):
    preview   = None
    imported  = 0
    skipped   = []
    error     = None
    success   = False

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "preview" and request.FILES.get("csv_file"):
            csv_file = request.FILES["csv_file"]
            try:
                decoded = csv_file.read().decode("utf-8")
                reader  = csv.DictReader(io.StringIO(decoded))
                rows = list(reader)
                # validate required columns
                required = {'title', 'category', 'amount', 'date'}
                if not required.issubset({h.lower().strip() for h in reader.fieldnames or []}):
                    error = "CSV must have columns: title, category, amount, date"
                else:
                    preview = rows[:5]
                    request.session['csv_data'] = decoded
            except Exception as e:
                error = f"Could not read file: {e}"

        elif action == "import":
            decoded = request.session.pop('csv_data', None)
            if decoded:
                reader = csv.DictReader(io.StringIO(decoded))
                custom_cats = list(CustomCategory.objects.filter(
                    user=request.user).values_list('name', flat=True))
                valid_cats = DEFAULT_CATEGORIES + [c for c in custom_cats if c not in DEFAULT_CATEGORIES]

                skipped = []
                for row_num, row in enumerate(reader, start=2):  # start=2 (row 1 is header)
                    title    = row.get('title', '').strip()
                    amount_s = row.get('amount', '').strip()
                    date_s   = row.get('date', '').strip()
                    cat      = row.get('category', '').strip().title()

                    # Validate title
                    if not title:
                        skipped.append(f"Row {row_num}: missing title")
                        continue

                    # Validate amount
                    try:
                        amount = float(amount_s)
                        if amount <= 0:
                            raise ValueError
                    except (ValueError, TypeError):
                        skipped.append(f"Row {row_num} ({title}): invalid amount \"{amount_s}\"")
                        continue

                    # Validate date
                    try:
                        from datetime import datetime as _dt
                        _dt.strptime(date_s, '%Y-%m-%d')
                    except ValueError:
                        skipped.append(f"Row {row_num} ({title}): invalid date \"{date_s}\" — use YYYY-MM-DD")
                        continue

                    # Sanitize category
                    if cat not in valid_cats:
                        cat = 'Other'

                    Expense.objects.create(
                        user=request.user,
                        title=title,
                        category=cat,
                        amount=amount,
                        date=date_s,
                    )
                    imported += 1

                success = True

    return render(request, 'dashboard/settings.html', {
        'section': 'upload',
        'preview': preview,
        'imported': imported,
        'skipped': skipped,
        'error': error,
        'success': success,
    })

# ---------------------------
# Subscriptions
# ---------------------------

@login_required(login_url='login')
def subscriptions(request):
    from datetime import date, timedelta
    today = date.today()
    week_ahead = today + timedelta(days=7)

    subs = Subscription.objects.filter(user=request.user)
    active_subs = subs.filter(status='active')

    # Auto-advance any overdue billing dates
    for sub in active_subs.filter(next_billing__lt=today):
        sub.advance_billing_date()
    # Re-query after updates
    subs = Subscription.objects.filter(user=request.user)
    active_subs = subs.filter(status='active')

    total_monthly = sum(s.monthly_cost for s in active_subs)
    total_yearly  = total_monthly * 12
    active_count  = active_subs.count()
    upcoming_qs   = active_subs.filter(next_billing__gte=today, next_billing__lte=week_ahead)
    upcoming      = upcoming_qs.count()
    due_soon_pks  = set(upcoming_qs.values_list('pk', flat=True))
    due_today_pks = set(active_subs.filter(next_billing=today).values_list('pk', flat=True))

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
def subscription_add(request):
    if request.method == 'POST':
        try:
            billing_date = request.POST['next_billing']
            sub = Subscription.objects.create(
                user=request.user,
                name=request.POST['name'].strip(),
                amount=float(request.POST['amount']),
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
        except Exception:
            pass  # billing advance failure shouldn't affect the success message
    return redirect('subscriptions')


@login_required(login_url='login')
def subscription_edit(request, pk):
    sub = get_object_or_404(Subscription, pk=pk, user=request.user)
    if request.method == 'POST':
        try:
            sub.name         = request.POST['name'].strip()
            sub.amount       = float(request.POST['amount'])
            sub.cycle        = request.POST.get('cycle', sub.cycle)
            sub.category     = request.POST.get('category', sub.category)
            sub.next_billing = request.POST['next_billing']
            sub.status       = request.POST.get('status', sub.status)
            sub.save()
            messages.success(request, f'"{sub.name}" updated.')
        except Exception:
            messages.error(request, 'Could not update subscription.')
    return redirect('subscriptions')


@login_required(login_url='login')
def subscription_delete(request, pk):
    sub = get_object_or_404(Subscription, pk=pk, user=request.user)
    name = sub.name
    sub.delete()
    messages.success(request, f'"{name}" deleted.')
    return redirect('subscriptions')


# ---------------------------
# Savings Goals
# ---------------------------

def _fmt_amount(v):
    v = float(v)
    if v >= 100000:
        return f"₹{v/100000:.1f}L"
    elif v >= 1000:
        return f"₹{v/1000:.1f}K"
    return f"₹{v:.0f}"


@login_required(login_url='login')
def savings_goals(request):
    goals = SavingsGoal.objects.filter(user=request.user).prefetch_related('contributions')
    total_saved = sum(float(g.saved) for g in goals)
    return render(request, 'dashboard/savings_goals.html', {
        'goals': goals,
        'total_saved_fmt': _fmt_amount(total_saved),
        'icon_choices': SavingsGoal.ICON_CHOICES,
    })


@login_required(login_url='login')
def savings_goal_add(request):
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
def savings_goal_edit(request, pk):
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
def savings_goal_detail(request, pk):
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
def savings_goal_add_funds(request, pk):
    goal = get_object_or_404(SavingsGoal, pk=pk, user=request.user)
    if request.method == 'POST':
        try:
            from datetime import date
            from django.db import transaction
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
def savings_goal_delete(request, pk):
    goal = get_object_or_404(SavingsGoal, pk=pk, user=request.user)
    name = goal.name
    goal.delete()
    messages.success(request, f'Goal "{name}" deleted.')
    return redirect('savings_goals')

# ---------------------------
# Settings — Copy Budget from Last Month
# ---------------------------

@login_required(login_url='login')
def budget_copy_last_month(request):
    if request.method == 'POST':
        try:
            month = int(request.POST['month'])
            year  = int(request.POST['year'])
        except (KeyError, ValueError):
            messages.error(request, 'Invalid month/year.')
            return redirect('settings_budget')

        prev_m, prev_y = (12, year - 1) if month == 1 else (month - 1, year)

        prev_budgets = CategoryBudget.objects.filter(
            user=request.user, month=prev_m, year=prev_y
        )
        if not prev_budgets.exists():
            messages.error(request, 'No budget limits found for the previous month.')
            return redirect(f"{reverse('settings_budget')}?month={month}&year={year}")

        copied = 0
        for b in prev_budgets:
            _, created = CategoryBudget.objects.update_or_create(
                user=request.user, category=b.category, month=month, year=year,
                defaults={'limit': b.limit}
            )
            copied += 1

        messages.success(request, f'Copied {copied} budget limit{"s" if copied != 1 else ""} from last month.')
    return redirect(f"{reverse('settings_budget')}?month={month}&year={year}")
