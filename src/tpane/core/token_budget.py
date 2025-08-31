"""
Token Budget Management

Handles token counting and budget-aware truncation for TOPA output.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TokenBudget:
    """Manages token allocation and consumption for TOPA output."""

    limit: int
    consumed: int = 0

    # Token estimation coefficients (rough approximations)
    # Based on typical tokenization patterns for common LLMs
    CHARS_PER_TOKEN = 4  # Conservative estimate
    YAML_OVERHEAD = 50  # Base YAML structure overhead

    def __post_init__(self):
        """Reserve tokens for base structure."""
        self.consumed = self.YAML_OVERHEAD

    @property
    def remaining(self) -> int:
        """Tokens remaining in budget."""
        return max(0, self.limit - self.consumed)

    @property
    def used_percentage(self) -> float:
        """Percentage of budget consumed."""
        return (self.consumed / self.limit) * 100 if self.limit > 0 else 0

    def has_budget(self, tokens: Optional[int] = None) -> bool:
        """Check if budget allows for additional tokens."""
        if tokens is None:
            return self.remaining > 0
        return self.remaining >= tokens

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        if not text:
            return 0

        # Count significant characters (ignore pure whitespace)
        char_count = len(text.strip())

        # Adjust for YAML structure (colons, dashes, indentation)
        yaml_chars = text.count(":") + text.count("-") + text.count("\n")
        adjusted_chars = char_count + (
            yaml_chars * 0.5
        )  # YAML tokens are often shorter

        return max(1, int(adjusted_chars / self.CHARS_PER_TOKEN))

    def would_exceed(self, text: str) -> bool:
        """Check if adding text would exceed budget."""
        estimated_tokens = self.estimate_tokens(text)
        return (self.consumed + estimated_tokens) > self.limit

    def consume(self, text: str) -> int:
        """Consume tokens for text and return amount consumed."""
        tokens = self.estimate_tokens(text)
        self.consumed += tokens
        return tokens

    def force_consume(self, text: str) -> int:
        """Consume tokens regardless of budget (for mandatory content)."""
        return self.consume(text)

    def smart_truncate(self, text: str, max_tokens: Optional[int] = None) -> str:
        """Truncate text intelligently to fit within token budget."""
        if not text:
            return text

        # Use provided limit or remaining budget
        token_limit = max_tokens if max_tokens is not None else self.remaining

        if token_limit <= 0:
            return ""

        estimated_tokens = self.estimate_tokens(text)

        # If text fits, return as-is
        if estimated_tokens <= token_limit:
            return text

        # Calculate target character count
        target_chars = int(
            token_limit * self.CHARS_PER_TOKEN * 0.8
        )  # Leave some buffer

        if target_chars < 10:  # Too small to be meaningful
            return ""

        # Intelligent truncation strategies
        return self._truncate_intelligently(text, target_chars)

    def _truncate_intelligently(self, text: str, target_chars: int) -> str:
        """Apply intelligent truncation preserving meaningful content."""
        if len(text) <= target_chars:
            return text

        # For very short limits, just truncate with ellipsis
        if target_chars < 20:
            return text[: max(0, target_chars - 3)] + "..."

        # Try to preserve meaningful content
        truncated = text[: target_chars - 3]

        # Try to break at word boundaries
        last_space = truncated.rfind(" ")
        if last_space > target_chars // 2:  # Only if we don't lose too much
            truncated = truncated[:last_space]

        # Try to break at sentence boundaries
        last_period = truncated.rfind(".")
        if last_period > target_chars // 2:
            truncated = truncated[: last_period + 1]
            return truncated  # Don't add ellipsis after period

        return truncated + "..."

    def fit_text(self, text: str, preserve_suffix: Optional[str] = None) -> str:
        """Fit text within remaining budget, optionally preserving a suffix."""
        if not self.has_budget():
            return ""

        if not self.would_exceed(text):
            return text

        # Calculate available space
        available_tokens = self.remaining
        suffix_tokens = self.estimate_tokens(preserve_suffix) if preserve_suffix else 0
        content_tokens = available_tokens - suffix_tokens - 1  # Buffer for "..."

        if content_tokens <= 0:
            return preserve_suffix or ""

        # Truncate main content
        truncated_content = self.smart_truncate(text, content_tokens)

        if preserve_suffix:
            return truncated_content + preserve_suffix
        else:
            return truncated_content

    def reserve(self, tokens: int) -> bool:
        """Reserve tokens for future use. Returns True if successful."""
        if self.remaining >= tokens:
            self.consumed += tokens
            return True
        return False

    def status_report(self) -> str:
        """Generate budget status report."""
        return f"Tokens: {self.consumed}/{self.limit} ({self.used_percentage:.1f}%)"

    def copy(self) -> "TokenBudget":
        """Create a copy of the current budget state."""
        return TokenBudget(limit=self.limit, consumed=self.consumed)
