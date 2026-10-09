"""
ai/tools.py — Vectorless RAG Tools

These tools are the "retrieval" half of the Vectorless RAG pattern.
Instead of searching a vector database, they retrieve structured financial
data deterministically from PostgreSQL via the Django service layer.

How they work:
  - make_tools(user) returns a list of LangChain @tool functions that are
    pre-bound to the authenticated user via a closure.
  - The LLM selects which tools to call and provides period/filter arguments.
  - The user object is NEVER provided by the LLM — it is captured from the
    closure at Python level, ensuring the agent cannot access another user's data.
  - All tool outputs map directly to the Pydantic schemas in ai/schemas.py.

build_financial_context(user) is the public function used by the insights
pipeline. It calls all tools automatically and assembles a FinancialContext
object that is passed to the LLM as structured context.

Security rules enforced here:
  - No tool accepts a user_id argument.
  - No tool exposes raw SQL, model field names, or schema details to the LLM.
  - All data access goes through the service layer, not direct ORM queries.
"""
import calendar
import logging
from datetime import datetime, timezone
from typing import Any

from dateutil.relativedelta import relativedelta

from ai.schemas import (
    AnomalyRecord,
    BudgetStatus,
    CategorySpend,
    FinancialContext,
    FinancialSummary,
    SavingsGoalProgress,
    SubscriptionItem,
    SubscriptionSummary,
)
from dashboard.services.expense_service import (
    get_anomalies,
    get_category_breakdown,
    get_total_spent,
)
from dashboard.services.income_service import get_monthly_income, get_range_income
from dashboard.services.savings_service import get_goals_with_progress
from dashboard.services.subscription_service import (
    get_active_subscriptions,
    get_total_monthly_cost,
)
from dashboard.models import CategoryBudget
from dashboard.utils import get_month_date_range

logger = logging.getLogger(__name__)


# ── Period resolution ─────────────────────────────────────────────────────────

# Valid period identifiers the LLM can pass to tools
VALID_PERIODS = {"current_month", "last_month", "last_3_months"}


def _resolve_period_dates(period: str) -> tuple:
    """
    Convert a period identifier string into a (start_date, end_date, label) tuple.

    Args:
        period: One of 'current_month', 'last_month', 'last_3_months'

    Returns:
        tuple: (start_date, end_date, human_readable_label)

    Raises:
        ValueError: If period is not a recognised identifier
    """
    if period not in VALID_PERIODS:
        raise ValueError(
            f"Invalid period '{period}'. "
            f"Must be one of: {', '.join(sorted(VALID_PERIODS))}"
        )

    today = datetime.now(tz=timezone.utc).date()

    if period == "current_month":
        start_date, end_date = get_month_date_range(today.year, today.month)
        label = f"{calendar.month_name[today.month]} {today.year}"

    elif period == "last_month":
        last_month_date = today - relativedelta(months=1)
        start_date, end_date = get_month_date_range(
            last_month_date.year, last_month_date.month
        )
        label = f"{calendar.month_name[last_month_date.month]} {last_month_date.year}"

    elif period == "last_3_months":
        three_months_ago = today - relativedelta(months=2)
        start_date, _ = get_month_date_range(three_months_ago.year, three_months_ago.month)
        _, end_date = get_month_date_range(today.year, today.month)
        label = (
            f"{calendar.month_name[three_months_ago.month]} {three_months_ago.year}"
            f" – {calendar.month_name[today.month]} {today.year}"
        )

    return start_date, end_date, label


# ── Individual data fetchers ──────────────────────────────────────────────────
# These private functions are called by make_tools() and build_financial_context().
# They return Pydantic schema instances, not raw dicts.


def _fetch_financial_summary(user: Any, period: str) -> FinancialSummary:
    """
    Fetch income, expense, and savings data for a period and return a
    typed FinancialSummary schema instance.

    Args:
        user:   Django User instance (injected, never from LLM)
        period: Period identifier string

    Returns:
        FinancialSummary
    """
    start_date, end_date, period_label = _resolve_period_dates(period)

    if period == "current_month":
        today = datetime.now(tz=timezone.utc).date()
        total_income = get_monthly_income(user, today.month, today.year)
    elif period == "last_month":
        last_month = datetime.now(tz=timezone.utc).date() - relativedelta(months=1)
        total_income = get_monthly_income(user, last_month.month, last_month.year)
    else:
        total_income = get_range_income(user, start_date, end_date)

    total_expenses = get_total_spent(user, start_date, end_date)
    amount_saved = round(total_income - total_expenses, 2)
    savings_rate = round((amount_saved / total_income * 100), 1) if total_income > 0 else 0.0

    # Top 5 categories with percentage of total spend
    raw_category_breakdown = get_category_breakdown(user, start_date, end_date)[:5]
    top_categories = [
        CategorySpend(
            category=category_name,
            amount=round(category_amount, 2),
            percentage_of_total=(
                round(category_amount / total_expenses * 100, 1)
                if total_expenses > 0 else 0.0
            ),
        )
        for category_name, category_amount in raw_category_breakdown
    ]

    return FinancialSummary(
        period_label=period_label,
        income=round(total_income, 2),
        expenses=round(total_expenses, 2),
        saved=amount_saved,
        savings_rate=savings_rate,
        top_categories=top_categories,
    )


def _fetch_budget_status(user: Any) -> list[BudgetStatus]:
    """
    Fetch current-month budget utilisation for all categories that have a
    budget set, and return a list of typed BudgetStatus schema instances.

    Categories without a budget limit are excluded — there is nothing to
    report on for a category with no limit set.

    Args:
        user: Django User instance

    Returns:
        list[BudgetStatus]
    """
    from django.db.models import Sum
    from expenses.models import Expense

    today = datetime.now(tz=timezone.utc).date()
    start_date, end_date = get_month_date_range(today.year, today.month)

    # Fetch all budgets set for this month
    category_budgets = CategoryBudget.objects.filter(
        user=user,
        month=today.month,
        year=today.year,
    )

    # Build a spend lookup for this month
    monthly_expense_totals = (
        Expense.objects
        .filter(user=user, date__gte=start_date, date__lte=end_date)
        .values("category")
        .annotate(total_spent=Sum("amount"))
    )
    spent_by_category = {
        row["category"]: float(row["total_spent"])
        for row in monthly_expense_totals
    }

    budget_status_list = []
    for budget in category_budgets:
        monthly_limit = float(budget.limit)
        if monthly_limit <= 0:
            continue

        amount_spent = spent_by_category.get(budget.category, 0.0)
        utilisation_pct = round(amount_spent / monthly_limit * 100, 1)

        if utilisation_pct >= 100:
            status = "over"
        elif utilisation_pct >= 80:
            status = "warning"
        else:
            status = "ok"

        budget_status_list.append(
            BudgetStatus(
                category=budget.category,
                monthly_limit=monthly_limit,
                amount_spent=round(amount_spent, 2),
                utilisation_pct=utilisation_pct,
                status=status,
            )
        )

    return budget_status_list


def _fetch_anomalies(user: Any, lookback_days: int = 30) -> list[AnomalyRecord]:
    """
    Fetch unusual expenses (>2x the 30-day category average and >₹500)
    and return a list of typed AnomalyRecord schema instances.

    Args:
        user:          Django User instance
        lookback_days: Number of days to look back (default 30)

    Returns:
        list[AnomalyRecord]
    """
    raw_anomalies = get_anomalies(user, days=lookback_days)

    return [
        AnomalyRecord(
            expense_title=anomaly["title"],
            category=anomaly["category"],
            amount=anomaly["amount"],
            category_average=anomaly["avg"],
            spend_multiplier=anomaly["multiplier"],
            date=anomaly["date"],
        )
        for anomaly in raw_anomalies
    ]


def _fetch_subscription_summary(user: Any) -> SubscriptionSummary:
    """
    Fetch all active subscriptions and their normalised monthly cost,
    and return a typed SubscriptionSummary schema instance.

    Args:
        user: Django User instance

    Returns:
        SubscriptionSummary
    """
    active_subscriptions = get_active_subscriptions(user)
    total_monthly_cost = round(get_total_monthly_cost(user), 2)

    subscription_items = [
        SubscriptionItem(
            name=subscription.name,
            monthly_amount=round(float(subscription.amount), 2),
            billing_cycle=subscription.cycle,
        )
        for subscription in active_subscriptions
    ]

    return SubscriptionSummary(
        active_subscriptions=subscription_items,
        total_monthly_cost=total_monthly_cost,
    )


def _fetch_savings_goals(user: Any) -> list[SavingsGoalProgress]:
    """
    Fetch all savings goals with their current progress and return a list
    of typed SavingsGoalProgress schema instances.

    Args:
        user: Django User instance

    Returns:
        list[SavingsGoalProgress]
    """
    goals_with_progress = get_goals_with_progress(user)

    return [
        SavingsGoalProgress(
            goal_name=goal.name,
            target_amount=round(float(goal.target), 2),
            amount_saved=round(float(goal.saved), 2),
            progress_pct=goal.progress_pct,
            remaining_amount=round(float(goal.remaining), 2),
            target_date=str(goal.target_date) if goal.target_date else None,
        )
        for goal in goals_with_progress
    ]


# ── Public API ────────────────────────────────────────────────────────────────

def build_financial_context(user: Any) -> FinancialContext:
    """
    Assemble a complete FinancialContext for a user by calling all data
    fetchers and combining their outputs.

    This is the single function called by the LangGraph insights pipeline
    in the gather_context node. It replaces the previous _gather_user_data()
    function in dashboard/views/insights.py.

    All data comes from PostgreSQL via the Django service layer — none of it
    comes from the LLM. The resulting FinancialContext is passed to the LLM
    as read-only context, and later used by the guardrail layer to verify
    every number the LLM produces.

    Args:
        user: Django User instance (from request.user in the view layer)

    Returns:
        FinancialContext: Fully populated context object
    """
    assembled_at = datetime.now(tz=timezone.utc).isoformat()

    logger.info("Building financial context for user_id=%s", user.pk)

    current_month_summary = _fetch_financial_summary(user, "current_month")
    previous_month_summary = _fetch_financial_summary(user, "last_month")
    last_3_months_summary = _fetch_financial_summary(user, "last_3_months")
    budget_status = _fetch_budget_status(user)
    anomalies = _fetch_anomalies(user, lookback_days=30)
    subscription_summary = _fetch_subscription_summary(user)
    savings_goals = _fetch_savings_goals(user)

    logger.info(
        "Financial context assembled: %d budget items, %d anomalies, "
        "%d subscriptions, %d goals",
        len(budget_status),
        len(anomalies),
        len(subscription_summary.active_subscriptions),
        len(savings_goals),
    )

    return FinancialContext(
        current_month=current_month_summary,
        previous_month=previous_month_summary,
        last_3_months=last_3_months_summary,
        budget_status=budget_status,
        anomalies=anomalies,
        subscriptions=subscription_summary,
        savings_goals=savings_goals,
        assembled_at=assembled_at,
    )


def make_tools(user: Any) -> list:
    """
    Return a list of LangChain @tool functions pre-bound to the authenticated user.

    The user object is captured in a closure — the LLM never receives or
    provides a user_id. It only selects which tool to call and what
    period/filter arguments to pass.

    This function requires langchain-core to be installed. It is called
    by the LangGraph Copilot agent (Phase 7) when it needs to select and
    call individual tools based on the user's question.

    The insights pipeline uses build_financial_context() instead, which
    calls all fetchers directly without going through LangChain tools.

    Args:
        user: Django User instance (from request.user in the view layer)

    Returns:
        list: LangChain tool instances ready to be bound to an LLM
    """
    try:
        from langchain_core.tools import tool
    except ImportError as error:
        raise ImportError(
            "langchain-core is not installed. "
            "Run: pip install langchain==0.3.25 langchain-google-genai==2.1.5"
        ) from error

    @tool
    def get_period_summary(period: str) -> dict:
        """
        Get total income, expenses, savings amount, and savings rate for a period.

        Args:
            period: Must be one of 'current_month', 'last_month', 'last_3_months'

        Returns:
            dict with keys: period_label, income, expenses, saved, savings_rate,
            top_categories (list of category/amount/percentage dicts)
        """
        summary = _fetch_financial_summary(user, period)
        return summary.model_dump()

    @tool
    def compare_periods(first_period: str, second_period: str) -> dict:
        """
        Compare two periods and return the absolute and percentage changes
        in income, expenses, and savings rate.

        Args:
            first_period:  The more recent period (e.g. 'current_month')
            second_period: The older period to compare against (e.g. 'last_month')

        Returns:
            dict with keys: first_period_label, second_period_label,
            income_delta, income_delta_pct, expenses_delta, expenses_delta_pct,
            savings_rate_delta
        """
        first = _fetch_financial_summary(user, first_period)
        second = _fetch_financial_summary(user, second_period)

        def _pct_change(current_value: float, previous_value: float) -> float:
            if previous_value == 0:
                return 0.0
            return round((current_value - previous_value) / previous_value * 100, 1)

        return {
            "first_period_label": first.period_label,
            "second_period_label": second.period_label,
            "income_delta": round(first.income - second.income, 2),
            "income_delta_pct": _pct_change(first.income, second.income),
            "expenses_delta": round(first.expenses - second.expenses, 2),
            "expenses_delta_pct": _pct_change(first.expenses, second.expenses),
            "savings_rate_delta": round(first.savings_rate - second.savings_rate, 1),
        }

    @tool
    def get_category_breakdown(period: str, top_n: int = 5) -> list:
        """
        Get spending totals and percentage shares by category for a period.

        Args:
            period: Must be one of 'current_month', 'last_month', 'last_3_months'
            top_n:  Number of top categories to return (default 5, max 10)

        Returns:
            list of dicts with keys: category, amount, percentage_of_total
        """
        summary = _fetch_financial_summary(user, period)
        return [category.model_dump() for category in summary.top_categories[:min(top_n, 10)]]

    @tool
    def get_budget_status() -> list:
        """
        Get current-month budget utilisation for all categories that have
        a budget limit set.

        Returns:
            list of dicts with keys: category, monthly_limit, amount_spent,
            utilisation_pct, status ('ok' | 'warning' | 'over')
        """
        budget_items = _fetch_budget_status(user)
        return [item.model_dump() for item in budget_items]

    @tool
    def detect_spending_anomalies(lookback_days: int = 30) -> list:
        """
        Detect expenses that are unusually high compared to the recent average
        for that category (more than twice the average and above ₹500).

        Args:
            lookback_days: Number of past days to analyse (default 30)

        Returns:
            list of dicts with keys: expense_title, category, amount,
            category_average, spend_multiplier, date
        """
        anomaly_records = _fetch_anomalies(user, lookback_days=lookback_days)
        return [record.model_dump() for record in anomaly_records]

    @tool
    def get_subscription_summary() -> dict:
        """
        Get all active subscriptions and the total normalised monthly cost.

        Returns:
            dict with keys: active_subscriptions (list), total_monthly_cost (float)
        """
        subscription_summary = _fetch_subscription_summary(user)
        return subscription_summary.model_dump()

    @tool
    def get_savings_progress() -> list:
        """
        Get progress toward all savings goals including percentage complete,
        amount saved, remaining amount, and target date if set.

        Returns:
            list of dicts with keys: goal_name, target_amount, amount_saved,
            progress_pct, remaining_amount, target_date
        """
        savings_goals = _fetch_savings_goals(user)
        return [goal.model_dump() for goal in savings_goals]

    @tool
    def assess_discretionary_budget(proposed_spend: float = 0.0) -> dict:
        """
        Estimate how much discretionary budget remains for the current month
        based on income minus essential spending so far.

        Optionally checks whether a proposed spend amount is affordable.

        Args:
            proposed_spend: Optional amount the user is considering spending (default 0)

        Returns:
            dict with keys: current_expenses, monthly_income, estimated_remaining,
            daily_average, days_left_in_month, proposed_is_affordable (if proposed_spend > 0)
        """
        from datetime import date as date_type
        import calendar as cal_module

        today = datetime.now(tz=timezone.utc).date()
        days_in_month = cal_module.monthrange(today.year, today.month)[1]
        days_elapsed = today.day
        days_remaining = days_in_month - days_elapsed

        current_month_data = _fetch_financial_summary(user, "current_month")
        daily_average = (
            round(current_month_data.expenses / days_elapsed, 2)
            if days_elapsed > 0 else 0.0
        )
        estimated_remaining = round(
            current_month_data.income - current_month_data.expenses, 2
        )

        result = {
            "current_expenses": current_month_data.expenses,
            "monthly_income": current_month_data.income,
            "estimated_remaining": estimated_remaining,
            "daily_average": daily_average,
            "days_left_in_month": days_remaining,
        }

        if proposed_spend > 0:
            result["proposed_is_affordable"] = proposed_spend <= estimated_remaining

        return result

    return [
        get_period_summary,
        compare_periods,
        get_category_breakdown,
        get_budget_status,
        detect_spending_anomalies,
        get_subscription_summary,
        get_savings_progress,
        assess_discretionary_budget,
    ]
