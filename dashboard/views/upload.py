"""
CSV Upload View

Import expenses from CSV files.
"""
import csv
import io

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse

from expenses.models import Expense, DEFAULT_CATEGORIES
from ..models import CustomCategory


@login_required(login_url='login')
def settings_upload(request: HttpRequest) -> HttpResponse:
    """
    Upload and import expenses from CSV file.
    
    Features:
        - Preview first 5 rows before import
        - Validate required columns (title, category, amount, date)
        - Auto-sanitize categories (fallback to 'Other')
        - Detailed error reporting for skipped rows
        
    Args:
        request: Django HttpRequest object
        
    Returns:
        HttpResponse: Upload settings page
    """
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
