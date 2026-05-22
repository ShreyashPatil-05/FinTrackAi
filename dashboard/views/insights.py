"""
AI Financial Insights View

Generates personalised financial insights using Google Gemini AI
based on the user's last 3 months of expense, income, budget and
savings data.
"""
import json
import logging
import calendar
import os
from datetime import date

from dateutil.relativedelta import relativedelta

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpRequest, HttpResponse, JsonResponse

from expenses.forms import get_category_choices
from ..models import Subscription, SavingsGoal, CategoryBudget
from ..utils import get_sum_amount, get_month_date_range
from ..services.expense_service import (
    get_period_expenses,
    get_total_spent,
    get_category_breakdown,
    get_anomalies,
)
from ..services.income_service import get_monthly_income
from ..services.subscription_service import get_total_monthly_cost, get_active_subscriptions
from ..services.savings_service import get_goals_with_progress

logger = logging.getLogger(__name__)


# ── Gemini helper ────────────────────────────────────────────────────────────

def _call_gemini(prompt: str) -> str | None:
    """Call Gemini API and return the text response, or None on failure."""
    api_key = os.environ.get('GEMINI_API_KEY', '')
    if not api_key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini API error: {e}", exc_info=True)
        return None


# ── Data gathering ───────────────────────────────────────────────────────────

def _gather_user_data(user) -> dict:
    """
    Collect the last 3 months of financial data using existing services.
    Returns a structured dict used both for the prompt and the template.
    """
    today = date.today()

    # ── 3-month window ──
    monthly_data = []
    for i in range(2, -1, -1):
        d = today - relativedelta(months=i)
        year, month = d.year, d.month
        start_dt, end_dt = get_month_date_range(year, month)

        income = get_monthly_income(user, month, year)
        total_spent = get_total_spent(user, start_dt, end_dt)
        top_cats = get_category_breakdown(user, start_dt, end_dt)[:5]

        monthly_data.append({
            'month': calendar.month_name[month],
            'year': year,
            'income': income,
            'spent': total_spent,
            'saved': round(income - total_spent, 2),
            'savings_rate': round((income - total_spent) / income * 100, 1) if income > 0 else 0,
            'top_categories': [
                {'category': cat, 'amount': amt} for cat, amt in top_cats
            ],
        })

    # ── Current month budget status ──
    cur_year, cur_month = today.year, today.month
    cur_start, cur_end = get_month_date_range(cur_year, cur_month)
    cur_expenses_qs = get_period_expenses(user, cur_start, cur_end)

    budgets = {
        b.category: float(b.limit)
        for b in CategoryBudget.objects.filter(user=user, month=cur_month, year=cur_year)
    }
    spent_by_cat = {
        row['category']: float(row['total'])
        for row in cur_expenses_qs.values('category').annotate(total=Sum('amount'))
    }
    budget_status = []
    for cat, limit in budgets.items():
        spent = spent_by_cat.get(cat, 0)
        pct = round(spent / limit * 100, 1) if limit > 0 else 0
        budget_status.append({
            'category': cat,
            'limit': limit,
            'spent': spent,
            'pct': pct,
            'status': 'over' if pct >= 100 else ('warning' if pct >= 80 else 'ok'),
        })

    # ── Subscriptions — reuse service ──
    active_subs_qs = get_active_subscriptions(user)
    active_subs = list(active_subs_qs.values('name', 'amount', 'cycle', 'next_billing'))
    total_monthly_subs = round(get_total_monthly_cost(user), 2)

    # ── Savings goals — reuse service ──
    goals = []
    for g in get_goals_with_progress(user):
        goals.append({
            'name': g.name,
            'target': float(g.target),
            'saved': g.saved,
            'pct': g.progress_pct,
            'remaining': g.remaining,
            'target_date': str(g.target_date) if g.target_date else None,
        })

    # ── Anomalies — reuse service ──
    anomalies = get_anomalies(user, days=30)[:5]

    return {
        'monthly_data': monthly_data,
        'budget_status': budget_status,
        'active_subs': active_subs,
        'total_monthly_subs': total_monthly_subs,
        'goals': goals,
        'anomalies': anomalies,
        'today': str(today),
        'current_month': calendar.month_name[cur_month],
        'current_year': cur_year,
    }


# ── Prompt builder ───────────────────────────────────────────────────────────

def _build_prompt(data: dict) -> str:
    monthly = data['monthly_data']
    goals   = data['goals']
    subs    = data['active_subs']
    budget  = data['budget_status']
    anomaly = data['anomalies']

    prompt = (
        f"You are a personal finance advisor for an Indian user of FinTrack.\n"
        f"Analyse the following financial data and generate exactly 5 concise, actionable insights.\n\n"
        f"Today: {data['today']}\n\n=== LAST 3 MONTHS ===\n"
    )
    for m in monthly:
        top_cats_str = ', '.join(
            f"{c['category']} ₹{c['amount']:,.0f}" for c in m['top_categories']
        )
        prompt += (
            f"\n{m['month']} {m['year']}:\n"
            f"  Income: ₹{m['income']:,.0f}\n"
            f"  Spent:  ₹{m['spent']:,.0f}\n"
            f"  Saved:  ₹{m['saved']:,.0f} ({m['savings_rate']}% savings rate)\n"
            f"  Top categories: {top_cats_str}\n"
        )

    if budget:
        prompt += "\n=== CURRENT MONTH BUDGET STATUS ===\n"
        for b in budget:
            prompt += f"  {b['category']}: spent ₹{b['spent']:,.0f} of ₹{b['limit']:,.0f} ({b['pct']}%) — {b['status']}\n"

    if subs:
        prompt += f"\n=== SUBSCRIPTIONS ===\nTotal monthly cost: ₹{data['total_monthly_subs']:,.0f}\n"
        for s in subs[:5]:
            prompt += f"  {s['name']}: ₹{s['amount']} ({s['cycle']})\n"

    if goals:
        prompt += "\n=== SAVINGS GOALS ===\n"
        for g in goals:
            prompt += f"  {g['name']}: {g['pct']}% complete (₹{g['saved']:,.0f} / ₹{g['target']:,.0f})"
            if g['target_date']:
                prompt += f", target date: {g['target_date']}"
            prompt += "\n"

    if anomaly:
        prompt += "\n=== UNUSUAL EXPENSES (last 30 days) ===\n"
        for a in anomaly:
            prompt += f"  {a['title']} ({a['category']}): ₹{a['amount']:,.0f} — {a['multiplier']}x usual spend\n"

    prompt += (
        "\n=== INSTRUCTIONS ===\n"
        "Return ONLY a valid JSON array with exactly 5 objects. No markdown, no explanation.\n"
        'Each object must have: "type" (positive/warning/danger/info), '
        '"icon" (Bootstrap Icons name), "title" (max 8 words), "insight" (max 25 words, use ₹).\n'
    )
    return prompt


# ── Parse Gemini response ────────────────────────────────────────────────────

def _parse_insights(raw: str) -> list:
    """Parse Gemini JSON response into a list of validated insight dicts."""
    if not raw:
        return []
    try:
        text = raw.strip()
        if text.startswith('```'):
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
        insights = json.loads(text.strip())
        if isinstance(insights, list):
            return [
                item for item in insights
                if all(k in item for k in ('type', 'icon', 'title', 'insight'))
            ][:6]
    except Exception as e:
        logger.error(f"Failed to parse Gemini response: {e}\nRaw: {raw[:200]}")
    return []


# ── Fallback rule-based insights ─────────────────────────────────────────────

def _rule_based_insights(data: dict) -> list:
    """Generate basic insights without AI when Gemini is unavailable."""
    insights = []
    monthly = data['monthly_data']

    if len(monthly) >= 2:
        curr, prev = monthly[-1], monthly[-2]

        if curr['savings_rate'] > prev['savings_rate']:
            diff = round(curr['savings_rate'] - prev['savings_rate'], 1)
            insights.append({
                'type': 'positive', 'icon': 'graph-up-arrow',
                'title': 'Savings rate improving',
                'insight': f"Your savings rate rose by {diff}% vs last month — great progress!",
            })
        elif curr['savings_rate'] < prev['savings_rate']:
            diff = round(prev['savings_rate'] - curr['savings_rate'], 1)
            insights.append({
                'type': 'warning', 'icon': 'exclamation-triangle',
                'title': 'Savings rate dropped',
                'insight': f"Savings rate fell by {diff}% this month. Review your top spending categories.",
            })

        if prev['spent'] > 0:
            pct_change = round((curr['spent'] - prev['spent']) / prev['spent'] * 100, 1)
            if pct_change > 20:
                insights.append({
                    'type': 'danger', 'icon': 'arrow-up-circle',
                    'title': 'Spending spike detected',
                    'insight': f"Total spending is up {pct_change}% vs last month — ₹{curr['spent']:,.0f} vs ₹{prev['spent']:,.0f}.",
                })

    over_budget = [b for b in data['budget_status'] if b['status'] == 'over']
    if over_budget:
        cats = ', '.join(b['category'] for b in over_budget[:2])
        insights.append({
            'type': 'danger', 'icon': 'wallet2',
            'title': 'Budget limit exceeded',
            'insight': f"You've exceeded your budget for {cats} this month.",
        })

    if data['total_monthly_subs'] > 0:
        insights.append({
            'type': 'info', 'icon': 'arrow-repeat',
            'title': 'Subscription cost overview',
            'insight': f"Your {len(data['active_subs'])} active subscriptions cost ₹{data['total_monthly_subs']:,.0f}/month.",
        })

    close_goals = [g for g in data['goals'] if 80 <= g['pct'] < 100]
    if close_goals:
        g = close_goals[0]
        insights.append({
            'type': 'positive', 'icon': 'piggy-bank',
            'title': 'Almost there!',
            'insight': f"Your '{g['name']}' goal is {g['pct']}% complete — just ₹{g['remaining']:,.0f} to go!",
        })

    if data['anomalies']:
        a = data['anomalies'][0]
        insights.append({
            'type': 'warning', 'icon': 'lightning-charge',
            'title': 'Unusual expense detected',
            'insight': f"'{a['title']}' (₹{a['amount']:,.0f}) is {a['multiplier']}x your usual {a['category']} spend.",
        })

    return insights[:6] or [{
        'type': 'info', 'icon': 'bar-chart-line',
        'title': 'Start tracking to get insights',
        'insight': 'Add your income and expenses to unlock personalised AI financial insights.',
    }]


# ── Main view ────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def insights_view(request: HttpRequest) -> HttpResponse:
    """AI Financial Insights page — powered by Gemini with rule-based fallback."""
    data = _gather_user_data(request.user)
    api_key_set = bool(os.environ.get('GEMINI_API_KEY', ''))

    insights = []
    ai_used = False

    if api_key_set:
        raw = _call_gemini(_build_prompt(data))
        insights = _parse_insights(raw)
        if insights:
            ai_used = True

    if not insights:
        insights = _rule_based_insights(data)

    # Month-over-month comparison
    monthly = data['monthly_data']
    mom = None
    if len(monthly) >= 2:
        curr, prev = monthly[-1], monthly[-2]
        mom = {
            'curr_month': curr['month'],
            'prev_month': prev['month'],
            'income_curr': curr['income'],
            'income_prev': prev['income'],
            'spent_curr': curr['spent'],
            'spent_prev': prev['spent'],
            'saved_curr': curr['saved'],
            'saved_prev': prev['saved'],
            'income_delta': round(curr['income'] - prev['income'], 0),
            'spent_delta': round(curr['spent'] - prev['spent'], 0),
            'saved_delta': round(curr['saved'] - prev['saved'], 0),
            'rate_curr': curr['savings_rate'],
            'rate_prev': prev['savings_rate'],
        }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'insights': insights, 'ai_used': ai_used})

    return render(request, 'dashboard/insights.html', {
        'insights': insights,
        'ai_used': ai_used,
        'api_key_set': api_key_set,
        'monthly_data': data['monthly_data'],
        'budget_status': data['budget_status'],
        'anomalies': data['anomalies'],
        'goals': data['goals'],
        'active_subs': data['active_subs'],
        'total_monthly_subs': data['total_monthly_subs'],
        'mom': mom,
        'current_month': data['current_month'],
        'current_year': data['current_year'],
    })
