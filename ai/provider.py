"""
ai/provider.py — LLM Provider Adapter

Wraps the LangChain ChatGoogleGenerativeAI client so the rest of the
ai/ module never imports LangChain directly. If the LLM provider needs
to change in the future (e.g. OpenAI, Anthropic), only this file changes.

Key responsibilities:
  - Read GEMINI_API_KEY from the environment (never hardcoded)
  - Return a lazily-initialised ChatGoogleGenerativeAI instance
  - Bind a Pydantic schema to the LLM via .with_structured_output()
    so the LLM is forced to return valid schema instances instead of
    raw strings that need manual JSON parsing

Usage:
    from ai.provider import get_llm, get_structured_llm
    from ai.schemas import InsightCollection

    # Plain LLM — returns a string
    llm = get_llm()

    # Schema-bound LLM — returns an InsightCollection instance
    structured_llm = get_structured_llm(InsightCollection)
    result: InsightCollection = structured_llm.invoke([...messages...])

Raises:
    LLMNotConfiguredError if GEMINI_API_KEY is missing
    LLMPackageNotInstalledError if langchain-google-genai is not installed
"""
import logging
import os

logger = logging.getLogger(__name__)


# Cached LLM instance — initialised once on first call to get_llm()
_cached_llm_instance = None


class LLMNotConfiguredError(Exception):
    """Raised when GEMINI_API_KEY is not set in the environment."""


class LLMPackageNotInstalledError(Exception):
    """Raised when the langchain-google-genai package is not installed."""


def get_llm(temperature: float = 0.3):
    """
    Return a lazily-initialised ChatGoogleGenerativeAI instance.

    The client is created once and reused for all subsequent calls.
    Temperature 0.3 is used by default — low enough to keep financial
    figures stable, high enough to produce varied insight phrasing.

    Args:
        temperature: LLM sampling temperature (0.0 = deterministic, 1.0 = creative)

    Returns:
        ChatGoogleGenerativeAI instance

    Raises:
        LLMNotConfiguredError:       if GEMINI_API_KEY is not set
        LLMPackageNotInstalledError: if langchain-google-genai is not installed
    """
    global _cached_llm_instance

    if _cached_llm_instance is not None:
        return _cached_llm_instance

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise LLMNotConfiguredError(
            "GEMINI_API_KEY is not set. "
            "Add it to your .env file to enable AI features."
        )

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError as error:
        raise LLMPackageNotInstalledError(
            "langchain-google-genai is not installed. "
            "Run: pip install langchain-google-genai==2.1.5"
        ) from error

    _cached_llm_instance = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=temperature,
    )

    logger.info("LLM provider initialised: gemini-2.5-flash (temperature=%.1f)", temperature)
    return _cached_llm_instance


def get_structured_llm(output_schema):
    """
    Return a ChatGoogleGenerativeAI instance bound to a Pydantic output schema.

    LangChain's .with_structured_output() instructs the LLM to return a
    valid instance of `output_schema` rather than a raw string. This
    replaces the fragile split('```') + json.loads() pattern used previously.

    If the LLM cannot produce a valid schema instance, LangChain raises a
    ValidationError which the LangGraph guardrail node catches and routes
    to the rule-based fallback.

    Args:
        output_schema: A Pydantic BaseModel class (e.g. InsightCollection)

    Returns:
        A runnable LangChain chain that accepts messages and returns an
        instance of output_schema

    Raises:
        LLMNotConfiguredError:       if GEMINI_API_KEY is not set
        LLMPackageNotInstalledError: if langchain-google-genai is not installed
    """
    llm = get_llm()
    return llm.with_structured_output(output_schema)


def is_llm_available() -> bool:
    """
    Return True if the LLM can be initialised without errors.

    Used for health checks and to determine whether to attempt an
    AI call or fall back to rule-based insights immediately.

    Returns:
        bool: True if GEMINI_API_KEY is set and the package is installed
    """
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return False

    try:
        import langchain_google_genai  # noqa: F401 — checking availability only
        return True
    except ImportError:
        return False


def reset_cached_llm() -> None:
    """
    Clear the cached LLM instance.

    Intended for use in tests only — forces a fresh client to be created
    on the next call to get_llm(). Not needed in production.
    """
    global _cached_llm_instance
    _cached_llm_instance = None
