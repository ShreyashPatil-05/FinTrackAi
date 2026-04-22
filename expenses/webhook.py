"""
Mock Bank Webhook — receives simulated bank transactions and creates Expenses.
The webhook token is bound to a specific user — no cross-user posting possible.
"""
import json
from datetime import date

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Expense, DEFAULT_CATEGORIES
from dashboard.models import WebhookToken


@csrf_exempt
@require_POST
def bank_webhook(request):
    # Validate token and resolve the bound user
    token = request.headers.get('X-Bank-Token', '')
    token_obj = WebhookToken.verify(token)
    if token_obj is None:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    user = token_obj.user

    # Parse payload
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    # Validate required fields
    for field in ['merchant', 'amount', 'category']:
        if field not in data:
            return JsonResponse({'error': f'Missing field: {field}'}, status=400)

    try:
        amount = float(data['amount'])
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid amount'}, status=400)

    # Sanitize category
    category = str(data['category']).strip().title()
    if category not in DEFAULT_CATEGORIES + ['Subscription']:
        category = 'Other'

    txn_date = data.get('date', str(date.today()))

    expense = Expense.objects.create(
        user=user,
        title=str(data['merchant']).strip(),
        category=category,
        amount=amount,
        date=txn_date,
        source='bank',
    )

    return JsonResponse({
        'status': 'created',
        'expense_id': expense.pk,
        'title': expense.title,
        'amount': str(expense.amount),
        'category': expense.category,
        'date': str(expense.date),
    }, status=201)
