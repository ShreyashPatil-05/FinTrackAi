"""
dashboard/services/plan_service.py

Single source of truth for all SaaS plan enforcement.
Provides limit checks, feature gating, and usage tracking.

Free plan limits
    - 50 expenses per month
    - 20 income entries per month
    - 2 savings goals (total, not per month)
    - 3 subscriptions (total)
    - 3 budget categories (total)

Pro-only locked features
    - CSV import
    - Data export
    - Bank webhook
    - AI Insights (Gemini)
"""
from django.utils import timezone


# Free tier numeric limits, keyed by resource name used in check_limit()
FREE_TIER_LIMITS = {
    "expenses_per_month": 50,
    "income_per_month": 20,
    "savings_goals": 2,
    "subscriptions": 3,
    "budget_categories": 3,
}

# Features that are completely locked on the free plan
PRO_ONLY_FEATURES = {"csv_import", "export", "webhook", "ai_insights"}

# Human-readable names for Pro-only features (used in error messages)
PRO_FEATURE_DISPLAY_NAMES = {
    "csv_import": "CSV import",
    "export": "Data export",
    "webhook": "Bank webhook",
    "ai_insights": "AI Insights",
}


def is_pro(user) -> bool:
    """
    Return True if the user currently has an active Pro plan.

    Checks both the plan type and the expiry date via UserProfile.is_pro().
    Returns False safely if the profile does not exist yet.

    Args:
        user: Django User instance

    Returns:
        bool
    """
    try:
        return user.profile.is_pro()
    except Exception:
        return False


def check_limit(user, resource: str) -> tuple:
    """
    Check whether the user is allowed to perform a resource-creating action.

    Pro users always pass. Free users are checked against FREE_TIER_LIMITS
    for countable resources, and blocked entirely for PRO_ONLY_FEATURES.

    Args:
        user:     Django User instance
        resource: Resource identifier. Valid values:
                  'expense', 'income', 'savings_goal', 'subscription',
                  'budget_category', 'csv_import', 'export', 'webhook',
                  'ai_insights'

    Returns:
        tuple[bool, str]:
            (True, '')                    — action is allowed
            (False, human_readable_msg)   — action is blocked; message explains why
    """
    if is_pro(user):
        return True, ""

    current_time = timezone.now()

    if resource == "expense":
        return _check_monthly_limit(
            user=user,
            resource_name="expense",
            current_month=current_time.month,
            current_year=current_time.year,
            limit=FREE_TIER_LIMITS["expenses_per_month"],
            limit_description="expenses this month",
        )

    if resource == "income":
        return _check_monthly_limit(
            user=user,
            resource_name="income",
            current_month=current_time.month,
            current_year=current_time.year,
            limit=FREE_TIER_LIMITS["income_per_month"],
            limit_description="income entries this month",
        )

    if resource == "savings_goal":
        return _check_total_limit(
            user=user,
            resource_name="savings_goal",
            limit=FREE_TIER_LIMITS["savings_goals"],
            limit_description="savings goals",
        )

    if resource == "subscription":
        return _check_total_limit(
            user=user,
            resource_name="subscription",
            limit=FREE_TIER_LIMITS["subscriptions"],
            limit_description="subscriptions",
        )

    if resource == "budget_category":
        return _check_total_limit(
            user=user,
            resource_name="budget_category",
            limit=FREE_TIER_LIMITS["budget_categories"],
            limit_description="budget categories",
        )

    if resource in PRO_ONLY_FEATURES:
        feature_name = PRO_FEATURE_DISPLAY_NAMES.get(resource, resource)
        return False, f"{feature_name} is a Pro feature. Upgrade to unlock it."

    # Unknown resource — allow by default (fail open, not closed)
    return True, ""


def get_usage(user) -> dict:
    """
    Return current usage counts and limits for the user.

    Used to render usage meters on the pricing page and in the UI,
    e.g. "12 / 50 expenses this month".

    Args:
        user: Django User instance

    Returns:
        dict with keys:
            is_pro         (bool)
            expenses       (int)   — count for current month
            income         (int)   — count for current month
            savings_goals  (int)   — total count
            subscriptions  (int)   — total count
            budget_cats    (int)   — total count
            limits         (dict)  — FREE_TIER_LIMITS reference
    """
    from expenses.models import Expense
    from dashboard.models import Income, SavingsGoal, Subscription, CategoryBudget

    current_time = timezone.now()

    return {
        "is_pro": is_pro(user),
        "expenses": Expense.objects.filter(
            user=user,
            date__month=current_time.month,
            date__year=current_time.year,
        ).count(),
        "income": Income.objects.filter(
            user=user,
            date__month=current_time.month,
            date__year=current_time.year,
        ).count(),
        "savings_goals": SavingsGoal.objects.filter(user=user).count(),
        "subscriptions": Subscription.objects.filter(user=user).count(),
        "budget_cats": CategoryBudget.objects.filter(user=user).count(),
        "limits": FREE_TIER_LIMITS,
    }


# Private helpers — not part of the public API of this module

def _check_monthly_limit(user, resource_name, current_month, current_year, limit, limit_description) -> tuple:
    """Check a per-month resource count against a free tier limit."""
    from expenses.models import Expense
    from dashboard.models import Income

    if resource_name == "expense":
        current_count = Expense.objects.filter(
            user=user,
            date__month=current_month,
            date__year=current_year,
        ).count()
    else:
        current_count = Income.objects.filter(
            user=user,
            date__month=current_month,
            date__year=current_year,
        ).count()

    if current_count >= limit:
        return False, (
            f"You've reached the free plan limit of {limit} {limit_description}. "
            f"Upgrade to Pro for unlimited access."
        )
    return True, ""


def _check_total_limit(user, resource_name, limit, limit_description) -> tuple:
    """Check a total resource count against a free tier limit."""
    from dashboard.models import SavingsGoal, Subscription, CategoryBudget

    model_map = {
        "savings_goal": SavingsGoal,
        "subscription": Subscription,
        "budget_category": CategoryBudget,
    }

    model = model_map.get(resource_name)
    if model is None:
        return True, ""

    current_count = model.objects.filter(user=user).count()
    if current_count >= limit:
        return False, (
            f"Free plan allows {limit} {limit_description}. "
            f"Upgrade to Pro for unlimited access."
        )
    return True, ""
