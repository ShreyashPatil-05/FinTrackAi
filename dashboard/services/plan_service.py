"""
Plan Service

Single source of truth for all SaaS plan enforcement.
Provides limit checks, feature gating, and usage tracking.

Free tier limits:
    - 50 expenses / month
    - 20 income entries / month
    - 2 savings goals (total)
    - 3 subscriptions (total)
    - 3 budget categories (total)

Locked features (Pro only):
    - CSV import
    - Data export
    - Bank webhook
    - AI Insights (Gemini)
"""
from django.utils import timezone

# ── Free tier limits ──────────────────────────────────────────────────────────

FREE_LIMITS = {
    'expenses_per_month':   50,
    'income_per_month':     20,
    'savings_goals':         2,
    'subscriptions':         3,
    'budget_categories':     3,
}

LOCKED_FEATURES = {'csv_import', 'export', 'webhook', 'ai_insights'}

_FEATURE_NAMES = {
    'csv_import':  'CSV import',
    'export':      'Data export',
    'webhook':     'Bank webhook',
    'ai_insights': 'AI Insights',
}


# ── Core helpers ──────────────────────────────────────────────────────────────

def is_pro(user) -> bool:
    """
    Return True if the user has an active Pro plan.
    Safe to call even if UserProfile doesn't exist yet.
    """
    try:
        return user.profile.is_pro()
    except Exception:
        return False


def check_limit(user, resource: str) -> tuple[bool, str]:
    """
    Check whether the user is allowed to perform a resource-creating action.

    Returns (True, '') if allowed.
    Returns (False, error_message) if the free-tier limit has been reached
    or the feature is Pro-only.

    Args:
        user:     Django User instance
        resource: One of 'expense', 'income', 'savings_goal', 'subscription',
                  'budget_category', 'csv_import', 'export', 'webhook', 'ai_insights'
    """
    if is_pro(user):
        return True, ''

    now = timezone.now()

    # ── Per-month counters ────────────────────────────────────────────────────
    if resource == 'expense':
        from expenses.models import Expense
        count = Expense.objects.filter(
            user=user,
            date__month=now.month,
            date__year=now.year,
        ).count()
        limit = FREE_LIMITS['expenses_per_month']
        if count >= limit:
            return False, (
                f"You've reached the free plan limit of {limit} expenses this month. "
                f"Upgrade to Pro for unlimited expenses."
            )

    elif resource == 'income':
        from dashboard.models import Income
        count = Income.objects.filter(
            user=user,
            date__month=now.month,
            date__year=now.year,
        ).count()
        limit = FREE_LIMITS['income_per_month']
        if count >= limit:
            return False, (
                f"You've reached the free plan limit of {limit} income entries this month. "
                f"Upgrade to Pro for unlimited income entries."
            )

    # ── Total-count limits ────────────────────────────────────────────────────
    elif resource == 'savings_goal':
        from dashboard.models import SavingsGoal
        count = SavingsGoal.objects.filter(user=user).count()
        limit = FREE_LIMITS['savings_goals']
        if count >= limit:
            return False, (
                f"Free plan allows {limit} savings goals. "
                f"Upgrade to Pro for unlimited goals."
            )

    elif resource == 'subscription':
        from dashboard.models import Subscription
        count = Subscription.objects.filter(user=user).count()
        limit = FREE_LIMITS['subscriptions']
        if count >= limit:
            return False, (
                f"Free plan allows {limit} subscriptions. "
                f"Upgrade to Pro for unlimited subscriptions."
            )

    elif resource == 'budget_category':
        from dashboard.models import CategoryBudget
        count = CategoryBudget.objects.filter(user=user).count()
        limit = FREE_LIMITS['budget_categories']
        if count >= limit:
            return False, (
                f"Free plan allows {limit} budget categories. "
                f"Upgrade to Pro for unlimited budgets."
            )

    # ── Pro-only locked features ──────────────────────────────────────────────
    elif resource in LOCKED_FEATURES:
        name = _FEATURE_NAMES.get(resource, resource)
        return False, f"{name} is a Pro feature. Upgrade to unlock it."

    return True, ''


def get_usage(user) -> dict:
    """
    Return current usage counts and limits for the user.

    Used to render usage meters in the UI (e.g. "12 / 50 expenses this month").

    Returns a dict:
        {
            'is_pro': bool,
            'expenses':       int,   # this month
            'income':         int,   # this month
            'savings_goals':  int,   # total
            'subscriptions':  int,   # total
            'budget_cats':    int,   # total
            'limits':         dict,  # FREE_LIMITS
        }
    """
    from expenses.models import Expense
    from dashboard.models import Income, SavingsGoal, Subscription, CategoryBudget

    now = timezone.now()
    return {
        'is_pro':        is_pro(user),
        'expenses':      Expense.objects.filter(
                            user=user,
                            date__month=now.month,
                            date__year=now.year,
                         ).count(),
        'income':        Income.objects.filter(
                            user=user,
                            date__month=now.month,
                            date__year=now.year,
                         ).count(),
        'savings_goals': SavingsGoal.objects.filter(user=user).count(),
        'subscriptions': Subscription.objects.filter(user=user).count(),
        'budget_cats':   CategoryBudget.objects.filter(user=user).count(),
        'limits':        FREE_LIMITS,
    }
