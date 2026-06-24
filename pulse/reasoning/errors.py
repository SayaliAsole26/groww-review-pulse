"""Reasoning pipeline exceptions."""


class ReasoningError(Exception):
    """Base error for clustering and LLM reasoning."""


class ClusteringError(ReasoningError):
    """Failed to produce valid clusters."""


class LlmError(ReasoningError):
    """LLM provider call failed."""


class TokenBudgetExceededError(LlmError):
    """Run exceeded configured token budget."""

    def __init__(self, used: int, limit: int) -> None:
        self.used = used
        self.limit = limit
        super().__init__(f"Token budget exceeded: used {used}, limit {limit}.")


class QuoteValidationError(ReasoningError):
    """No valid themes remain after quote validation."""
