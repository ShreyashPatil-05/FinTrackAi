"""
ai/schemas.py — Pydantic Schemas for the AI Layer

Three groups of schemas are defined here:

  1. FINANCIAL DATA SCHEMAS
     Ground-truth data built from the Django service layer (PostgreSQL).
     These are never populated by the LLM — only by Python service calls.

  2. LLM OUTPUT SCHEMAS
     What Gemini must return, enforced by LangChain's .with_structured_output().
     Replaces the current fragile split('```') + json.loads() parsing.

  3. LANGGRAPH AGENT STATE
     The state dict that flows between nodes in the LangGraph state machine.

Security rule:
  No schema contains a user_id field.
  The authenticated Django User object is injected at the view layer in Python
  and passed directly to tool functions — the LLM never sees or provides it.
"""
from __future__ import annotations

from typing import Any, Literal, Optional, Union
from typing_extensions import TypedDict

from pydantic import BaseModel, Field


# ── Exports ───────────────────────────────────────────────────────────────────

__all__ = [
    # Financial data schemas
    "CategorySpend",
    "FinancialSummary",
    "BudgetStatus",
    "AnomalyRecord",
    "SubscriptionItem",
    "SubscriptionSummary",
    "SavingsGoalProgress",
    "FinancialContext",
    # LLM output schemas
    "InsightCard",
    "InsightCollection",
    "CopilotResponse",
    # LangGraph state
    "AgentState",
]


# =============================================================================
# GROUP 1 — FINANCIAL DATA SCHEMAS
# Ground-truth data from PostgreSQL via the Django service layer.
# The LLM never populates these — it only reads them as context.
# =============================================================================


class CategorySpend(BaseModel):
    """
    Spending total for one expense category within a period.

    Amounts are float because that is what the expense_service
    category breakdown functions return.
    """

    category: str
    amount: float
    percentage_of_total: float = Field(default=0.0, ge=0, le=100)


class FinancialSummary(BaseModel):
    """
    High-level income, expense, and savings summary for one time period.

    Used for both single-month summaries and rolling 3-month summaries.
    The period_label is a human-readable string passed directly to the LLM
    as context (e.g. "September 2026", "Last 3 months").
    """

    period_label: str
    income: float
    expenses: float
    saved: float
    savings_rate: float
    top_categories: list[CategorySpend] = Field(default_factory=list)


class BudgetStatus(BaseModel):
    """
    Budget utilisation for one expense category in the current month.

    status is derived from utilisation_pct:
      ok      → below 80%
      warning → 80-99%
      over    → 100% or above
    """

    category: str
    monthly_limit: float
    amount_spent: float
    utilisation_pct: float
    status: Literal["ok", "warning", "over"]


class AnomalyRecord(BaseModel):
    """
    A single expense that was flagged as unusually high.

    An expense is anomalous when it exceeds twice the 30-day
    category average and is above ₹500.

    category_average is the 30-day rolling average for that category.
    spend_multiplier shows how many times above average this expense was.
    """

    expense_title: str
    category: str
    amount: float
    category_average: float
    spend_multiplier: float
    date: str


class SubscriptionItem(BaseModel):
    """One active recurring subscription."""

    name: str
    monthly_amount: float
    billing_cycle: str


class SubscriptionSummary(BaseModel):
    """
    All active subscriptions for the user, with the normalised monthly cost.

    total_monthly_cost normalises all cycles (weekly, monthly, yearly)
    to a per-month figure so the LLM can reason about recurring spend.
    """

    active_subscriptions: list[SubscriptionItem] = Field(default_factory=list)
    total_monthly_cost: float


class SavingsGoalProgress(BaseModel):
    """Progress toward one savings goal."""

    goal_name: str
    target_amount: float
    amount_saved: float
    progress_pct: float
    remaining_amount: float
    target_date: Optional[str] = None


class FinancialContext(BaseModel):
    """
    The complete Vectorless RAG payload for one user.

    This object is assembled entirely from PostgreSQL data via the Django
    service layer before any LLM call is made. It is then passed to the
    LLM as structured context.

    The guardrail layer uses all_numeric_values() to build a set of
    ground-truth numbers that it cross-checks against every ₹ amount
    and percentage the LLM produces in its response.

    Assembly happens in ai/tools.py via build_financial_context(user).
    """

    current_month: FinancialSummary
    previous_month: Optional[FinancialSummary] = None
    last_3_months: Optional[FinancialSummary] = None
    budget_status: list[BudgetStatus] = Field(default_factory=list)
    anomalies: list[AnomalyRecord] = Field(default_factory=list)
    subscriptions: SubscriptionSummary
    savings_goals: list[SavingsGoalProgress] = Field(default_factory=list)
    assembled_at: str

    def all_numeric_values(self) -> set[float]:
        """
        Return a flat set of every numeric value in this context.

        Used by the numeric grounding guardrail to verify that every
        ₹ amount and percentage the LLM mentions can be traced back
        to a real number from the database.
        """
        numeric_values: set[float] = set()

        # Add values from all period summaries
        period_summaries = [self.current_month, self.previous_month, self.last_3_months]
        for summary in period_summaries:
            if summary is None:
                continue
            numeric_values.update([
                summary.income,
                summary.expenses,
                summary.saved,
                summary.savings_rate,
            ])
            for category in summary.top_categories:
                numeric_values.update([category.amount, category.percentage_of_total])

        # Add budget utilisation values
        for budget_item in self.budget_status:
            numeric_values.update([
                budget_item.monthly_limit,
                budget_item.amount_spent,
                budget_item.utilisation_pct,
            ])

        # Add anomaly values
        for anomaly in self.anomalies:
            numeric_values.update([
                anomaly.amount,
                anomaly.category_average,
                anomaly.spend_multiplier,
            ])

        # Add subscription values
        for subscription in self.subscriptions.active_subscriptions:
            numeric_values.add(subscription.monthly_amount)
        numeric_values.add(self.subscriptions.total_monthly_cost)

        # Add savings goal values
        for goal in self.savings_goals:
            numeric_values.update([
                goal.target_amount,
                goal.amount_saved,
                goal.progress_pct,
                goal.remaining_amount,
            ])

        return numeric_values


# =============================================================================
# GROUP 2 — LLM OUTPUT SCHEMAS
# What Gemini must return, validated by LangChain .with_structured_output().
# These replace the current fragile JSON parsing in dashboard/views/insights.py.
# =============================================================================


class InsightCard(BaseModel):
    """
    One AI-generated financial insight card shown on the insights page.

    The data_reference field must contain the exact number(s) this insight
    is based on (e.g. "expenses: ₹45,000 | savings_rate: 23.4%").
    The guardrail layer checks every value in data_reference against
    FinancialContext.all_numeric_values() before the card is shown to the user.
    """

    card_type: Literal["positive", "warning", "danger", "info"] = Field(alias="type")
    icon: str
    title: str = Field(max_length=60)
    insight: str = Field(max_length=200)
    data_reference: str = Field(
        default="",
        description=(
            "The specific numeric value(s) this insight is based on. "
            "Example: 'expenses: ₹45,000 | savings_rate: 23.4%'"
        ),
    )

    model_config = {"populate_by_name": True}


class InsightCollection(BaseModel):
    """
    The final output of the LangGraph insights pipeline.

    Contains 3–6 InsightCard objects. The minimum of 3 ensures there is
    always enough content for a meaningful insights page.
    ai_used is set to False when the pipeline falls back to rule-based insights.
    """

    cards: list[InsightCard] = Field(min_length=3, max_length=6)
    ai_used: bool = True


class CopilotResponse(BaseModel):
    """
    The final output of the LangGraph copilot agent for one user question.

    tools_called lists the names of tools that were invoked to answer the question.
    has_disclaimer is True when the response touches affordability or planning,
    where a financial advice disclaimer must be shown alongside the answer.
    """

    answer: str
    tools_called: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "medium"
    has_disclaimer: bool = False


# =============================================================================
# GROUP 3 — LANGGRAPH AGENT STATE
# The state dict that flows between nodes in the LangGraph state machine.
# TypedDict is required by LangGraph — do not change to BaseModel.
# =============================================================================


class AgentState(TypedDict):
    """
    Shared state passed between every node in the LangGraph state machine.

    Security rule:
      `user` is a Django User object injected by the Django view before the
      graph is invoked. The LLM never receives, reads, or provides a user_id.
      Every tool function receives `user` directly from this state — not from
      any LLM output.

    Flow:
      Insights pipeline  → question is an empty string
      Copilot pipeline   → question contains the user's question

    retry_count tracks how many times generate_insights_node has been called.
    The guardrail node routes to fallback once retry_count reaches 1.
    """

    user: Any
    question: str
    context: Optional[FinancialContext]
    tool_outputs: dict
    raw_llm_response: Optional[str]
    parsed_response: Optional[Union[InsightCollection, CopilotResponse]]
    guardrail_passed: Optional[bool]
    guardrail_failures: list[str]
    retry_count: int
    error: Optional[str]
