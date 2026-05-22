"""
Mock Bank Webhook Handler

Receives simulated bank transactions and creates Expense entries.
"""
import json
from datetime import date, datetime

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.cache import cache

from .models import Expense, DEFAULT_CATEGORIES
from dashboard.models import WebhookToken


@csrf_exempt
@require_POST
def bank_webhook(request):
    """Handle incoming bank transaction webhooks."""
    # ── Rate limit: 60 requests per minute per IP ──
    ip = request.META.get('REMOTE_ADDR', '')
    rate_key = f'webhook_rate_{ip}'
    hits = cache.get(rate_key, 0)
    if hits >= 60:
        return JsonResponse({'error': 'Rate limit exceeded'}, status=429)
    cache.set(rate_key, hits + 1, timeout=60)

    # ── Authenticate token ──
    token = request.headers.get('X-Bank-Token', '')
    token_obj = WebhookToken.verify(token)
    if token_obj is None:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    user = token_obj.user

    # ── Parse payload ──
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    # ── Validate required fields ──
    for field in ['merchant', 'amount', 'category']:
        if field not in data:
            return JsonResponse({'error': f'Missing field: {field}'}, status=400)

    # ── Validate merchant ──
    merchant = str(data['merchant']).strip()
    if not merchant or len(merchant) > 200:
        return JsonResponse({'error': 'Invalid merchant name (1-200 chars)'}, status=400)

    # ── Validate amount ──
    try:
        amount = float(data['amount'])
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid amount'}, status=400)

    # ── Validate date ──
    date_str = data.get('date', str(date.today()))
    try:
        txn_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        if txn_date > date.today():
            return JsonResponse({'error': 'Date cannot be in the future'}, status=400)
    except ValueError:
        return JsonResponse({'error': 'Invalid date format, use YYYY-MM-DD'}, status=400)

    # ── Sanitize category ──
    category = str(data['category']).strip().title()
    if category not in DEFAULT_CATEGORIES + ['Subscription']:
        category = 'Other'

    expense = Expense.objects.create(
        user=user,
        title=merchant,
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
