"""
ai/guardrails.py — Guardrail Validators

Three independent validators that run after every LLM response before
any output is shown to the user.

  1. NumericGroundingGuardrail
     Extracts every ₹ amount and percentage from the LLM response text
     and cross-checks each one against the ground-truth FinancialContext
     assembled from PostgreSQL. Any unverifiable number triggers a failure.

  2. PolicyGuardrail
     Blocks questions or responses that touch regulated financial topics
     (investments, stocks, loans, crypto, insurance). FinTrack is a budget
     tracker, not a financial advisor.

  3. InjectionGuardrail
     Detects common prompt injection patterns in user input and rejects
     them before they reach the LLM. Logged for monitoring.

Each validator returns a GuardrailResult dataclass so the LangGraph node
can handle pass/fail uniformly without inspecting raw booleans and lists.

Usage (in LangGraph nodes):
    from ai.guardrails import (
        NumericGroundingGuardrail,
        PolicyGuardrail,
        InjectionGuardrail,
    )

    result = NumericGroundingGuardrail.check(llm_response_text, financial_context)
    if not result.passed:
        # route to fallback or retry
        ...
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ── Shared result type ────────────────────────────────────────────────────────


@dataclass
class GuardrailResult:
    """
    The outcome of a single guardrail check.

    Attributes:
        passed:           True if the check passed; False if it failed.
        failure_reasons:  List of human-readable descriptions of what failed.
                          Empty when passed=True.
        blocked_pattern:  The specific pattern that triggered a block
                          (used by PolicyGuardrail and InjectionGuardrail).
    """

    passed: bool
    failure_reasons: list = field(default_factory=list)
    blocked_pattern: Optional[str] = None

    def __bool__(self) -> bool:
        return self.passed


# =============================================================================
# GUARDRAIL 1 — Numeric Grounding
# =============================================================================


class NumericGroundingGuardrail:
    """
    Verifies that every ₹ amount and percentage in the LLM response can be
    traced back to a value that actually exists in the FinancialContext
    assembled from the database.

    Why this matters:
        LLMs can hallucinate financial figures. A personal finance app that
        shows incorrect rupee amounts destroys user trust immediately.

    How it works:
        1. Extract all ₹ amounts (e.g. "₹45,000") and percentages (e.g. "23.4%")
           from the LLM response text using regex.
        2. Build a set of all real numeric values from FinancialContext.
        3. For each extracted value, check whether it exists in the ground-truth
           set within a ±TOLERANCE_PCT tolerance (to allow for rounding).
        4. If any value cannot be matched, the check fails.

    Tolerance:
        2% by default — covers rounding differences between raw DB values
        and values the LLM may have rounded for display (e.g. ₹45,231 → ₹45,000).
    """

    TOLERANCE_PCT = 0.02  # 2% tolerance for rounding differences

    # Matches ₹ amounts like ₹45,000 or ₹1,23,456 or ₹500
    RUPEE_AMOUNT_PATTERN = re.compile(r"₹\s*[\d,]+(?:\.\d+)?")

    # Matches standalone percentages like 23.4% or 100%
    PERCENTAGE_PATTERN = re.compile(r"\b(\d+(?:\.\d+)?)\s*%")

    @classmethod
    def extract_claimed_values(cls, llm_response_text: str) -> list[float]:
        """
        Extract all numeric values the LLM claimed in its response.

        Handles both rupee amounts (strips ₹ and commas) and percentages.

        Args:
            llm_response_text: The raw text output from the LLM

        Returns:
            list[float]: All numeric values found in the response
        """
        extracted_values = []

        # Extract ₹ amounts
        for rupee_match in cls.RUPEE_AMOUNT_PATTERN.finditer(llm_response_text):
            raw_value = rupee_match.group().replace("₹", "").replace(",", "").strip()
            try:
                extracted_values.append(float(raw_value))
            except ValueError:
                pass

        # Extract percentages
        for pct_match in cls.PERCENTAGE_PATTERN.finditer(llm_response_text):
            try:
                extracted_values.append(float(pct_match.group(1)))
            except ValueError:
                pass

        return extracted_values

    @classmethod
    def _is_value_grounded(cls, claimed_value: float, ground_truth_values: set[float]) -> bool:
        """
        Return True if claimed_value is within TOLERANCE_PCT of any ground-truth value.

        Args:
            claimed_value:       The value extracted from the LLM response
            ground_truth_values: All real values from FinancialContext

        Returns:
            bool
        """
        for true_value in ground_truth_values:
            denominator = max(abs(true_value), 1.0)  # avoid division by zero
            relative_difference = abs(claimed_value - true_value) / denominator
            if relative_difference <= cls.TOLERANCE_PCT:
                return True
        return False

    @classmethod
    def check(cls, llm_response_text: str, financial_context) -> GuardrailResult:
        """
        Run the numeric grounding check.

        Args:
            llm_response_text: The full text of the LLM response
            financial_context: FinancialContext instance built from the database

        Returns:
            GuardrailResult
        """
        claimed_values = cls.extract_claimed_values(llm_response_text)

        # If the response contains no numeric claims, it passes by default
        if not claimed_values:
            return GuardrailResult(passed=True)

        ground_truth_values = financial_context.all_numeric_values()
        failure_reasons = []

        for claimed_value in claimed_values:
            if not cls._is_value_grounded(claimed_value, ground_truth_values):
                failure_reasons.append(
                    f"Unverifiable claim: {claimed_value} "
                    f"(not found in financial context within {cls.TOLERANCE_PCT * 100:.0f}% tolerance)"
                )

        if failure_reasons:
            logger.warning(
                "Numeric grounding check failed — %d unverifiable claim(s): %s",
                len(failure_reasons),
                "; ".join(failure_reasons),
            )
            return GuardrailResult(passed=False, failure_reasons=failure_reasons)

        return GuardrailResult(passed=True)


# =============================================================================
# GUARDRAIL 2 — Policy
# =============================================================================


class PolicyGuardrail:
    """
    Blocks questions and responses that touch regulated financial topics.

    FinTrack is a personal budget and expense tracker, not a financial advisor.
    Responding to investment, stock, crypto, loan, or insurance queries would
    create regulatory and reputational risk.

    When a query is blocked, a fixed disclaimer is returned instead of
    routing the question to the LLM.
    """

    DISCLAIMER_RESPONSE = (
        "FinTrack helps you understand your personal spending and budgets, "
        "but is not a registered financial advisor. "
        "For investment, loan, or insurance decisions, "
        "please consult a qualified professional."
    )

    # Topic keywords that trigger the policy block.
    # Checked as case-insensitive substring matches against the full input.
    BLOCKED_TOPICS = [
        # Investments and markets
        "stock", "share market", "equity", "nifty", "sensex", "bse", "nse",
        "mutual fund", "index fund", "etf", "sip", "elss", "portfolio",
        # Crypto
        "crypto", "bitcoin", "ethereum", "nft", "web3", "defi", "altcoin",
        # Loans and credit
        "loan", "emi", "mortgage", "home loan", "personal loan", "credit score",
        # Insurance
        "insurance", "life insurance", "term plan", "ulip",
        # Generic investment advice
        "invest my", "where to invest", "should i buy", "financial advice",
        "retire at", "fire number",
    ]

    @classmethod
    def check(cls, user_input: str) -> GuardrailResult:
        """
        Check whether the user's question touches a blocked topic.

        Args:
            user_input: The raw question from the user

        Returns:
            GuardrailResult:
                passed=True  — question is within scope, proceed to LLM
                passed=False — question is out of scope, return DISCLAIMER_RESPONSE
        """
        normalised_input = user_input.lower().strip()

        for blocked_topic in cls.BLOCKED_TOPICS:
            if blocked_topic in normalised_input:
                logger.info(
                    "PolicyGuardrail blocked query — matched topic: '%s'",
                    blocked_topic,
                )
                return GuardrailResult(
                    passed=False,
                    failure_reasons=[f"Query touches blocked topic: '{blocked_topic}'"],
                    blocked_pattern=blocked_topic,
                )

        return GuardrailResult(passed=True)


# =============================================================================
# GUARDRAIL 3 — Prompt Injection
# =============================================================================


class InjectionGuardrail:
    """
    Detects and rejects common prompt injection patterns in user input.

    Prompt injection attempts to override the LLM's system prompt or persona.
    These are blocked before the input reaches the LLM to prevent:
      - System prompt leakage
      - Persona hijacking
      - Jailbreak attempts
      - Attempts to extract API keys or internal configuration

    All detected injection attempts are logged for monitoring.
    """

    SAFE_RESPONSE = (
        "I can only help you understand your personal spending and budgets. "
        "Please ask a question about your finances."
    )

    # Patterns checked as case-insensitive substring matches
    INJECTION_PATTERNS = [
        "ignore previous instructions",
        "ignore all instructions",
        "ignore the above",
        "disregard the above",
        "forget everything",
        "you are now",
        "act as",
        "pretend you are",
        "new persona",
        "jailbreak",
        "dan mode",
        "developer mode",
        "system prompt",
        "print your instructions",
        "reveal your prompt",
        "what is your system",
        "show me the prompt",
        "api key",
        "gemini key",
        "secret key",
    ]

    @classmethod
    def check(cls, user_input: str) -> GuardrailResult:
        """
        Check whether the user's input contains a prompt injection attempt.

        Args:
            user_input: The raw question from the user

        Returns:
            GuardrailResult:
                passed=True  — input is safe, proceed
                passed=False — injection detected, return SAFE_RESPONSE
        """
        normalised_input = user_input.lower().strip()

        for injection_pattern in cls.INJECTION_PATTERNS:
            if injection_pattern in normalised_input:
                logger.warning(
                    "InjectionGuardrail blocked input — matched pattern: '%s' "
                    "(input length: %d chars)",
                    injection_pattern,
                    len(user_input),
                )
                return GuardrailResult(
                    passed=False,
                    failure_reasons=[f"Injection pattern detected: '{injection_pattern}'"],
                    blocked_pattern=injection_pattern,
                )

        return GuardrailResult(passed=True)


# =============================================================================
# CONVENIENCE: Run all input guardrails in sequence
# =============================================================================


def validate_user_input(user_input: str) -> GuardrailResult:
    """
    Run all input-side guardrails (injection + policy) against a user question.

    Injection check runs first — a blocked injection never reaches the
    policy check, which would be a waste of a comparison.

    Args:
        user_input: The raw question from the user

    Returns:
        GuardrailResult: First failure encountered, or a passing result if all pass.
    """
    injection_result = InjectionGuardrail.check(user_input)
    if not injection_result.passed:
        return injection_result

    policy_result = PolicyGuardrail.check(user_input)
    if not policy_result.passed:
        return policy_result

    return GuardrailResult(passed=True)
