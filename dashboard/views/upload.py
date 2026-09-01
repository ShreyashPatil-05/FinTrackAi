"""
CSV Upload View

Import expenses from CSV files.
"""
import csv
import io
from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse

from expenses.models import Expense, DEFAULT_CATEGORIES
from ..models import CustomCategory
from ..decorators import plan_required


@login_required(login_url='login')
@plan_required('csv_import')
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
    csv_data  = ''     # CSV content passed back via hidden form field
    imported  = 0
    skipped   = []
    error     = None
    success   = False

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "preview" and request.FILES.get("csv_file"):
            csv_file = request.FILES["csv_file"]
            # ── Size limit: 1MB ──
            if csv_file.size > 1 * 1024 * 1024:
                error = "CSV too large. Maximum file size is 1MB."
            else:
                try:
                    decoded = csv_file.read().decode("utf-8")
                    reader  = csv.DictReader(io.StringIO(decoded))
                    rows = list(reader)
                    # validate required columns
                    required = {'title', 'category', 'amount', 'date'}
                    if not required.issubset({h.lower().strip() for h in reader.fieldnames or []}):
                        error = "CSV must have columns: title, category, amount, date"
                    elif len(rows) > 5000:
                        error = "Too many rows. Maximum 5,000 rows per import."
                    else:
                        preview = rows[:5]
                        csv_data = decoded   # passed to template; returned via hidden field
                except Exception as e:
                    error = f"Could not read file: {e}"

        elif action == "import":
            decoded = request.POST.get('csv_data', '').strip()
            if decoded:
                reader = csv.DictReader(io.StringIO(decoded))
                custom_cats = list(CustomCategory.objects.filter(
                    user=request.user).values_list('name', flat=True))
                valid_cats = DEFAULT_CATEGORIES + [c for c in custom_cats if c not in DEFAULT_CATEGORIES]

                skipped = []
                expenses_to_create = []
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
                        amount = Decimal(amount_s)
                        if amount <= 0:
                            raise InvalidOperation
                    except (InvalidOperation, ValueError, TypeError):
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

                    expenses_to_create.append(Expense(
                        user=request.user,
                        title=title,
                        category=cat,
                        amount=amount,
                        date=date_s,
                    ))

                if expenses_to_create:
                    Expense.objects.bulk_create(expenses_to_create, batch_size=500)
                imported = len(expenses_to_create)
                success = True

    return render(request, 'dashboard/settings.html', {
        'section': 'upload',
        'preview': preview,
        'csv_data': csv_data,
        'imported': imported,
        'skipped': skipped,
        'error': error,
        'success': success,
    })
