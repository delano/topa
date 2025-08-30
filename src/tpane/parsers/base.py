# src/tpane/parsers/base.py

"""
Base Parser Interface

Abstract base class for all input format parsers.
"""

import re
from abc import ABC, abstractmethod
from typing import Optional, Tuple

try:
    from ..core.schema import ParsedTestData
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.schema import ParsedTestData


class BaseParser(ABC):
    """Abstract base class for test output parsers."""

    def __init__(self):
        self.line_number_pattern = re.compile(
            r"(?:line|:)?\s*(\d+)", re.IGNORECASE
        )

    @abstractmethod
    def parse(self, content: str) -> ParsedTestData:
        """Parse test output content into structured data."""
        pass

    def _extract_line_number(self, text: str) -> Optional[int]:
        """Extract line number from text if present."""
        match = self.line_number_pattern.search(text)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
        return None

    def _normalize_test_name(self, name: str) -> str:
        """Normalize test name for consistency."""
        if not name:
            return "unnamed test"

        # Remove common prefixes/suffixes
        name = re.sub(r"^(test_?|it_?)", "", name, flags=re.IGNORECASE)
        name = re.sub(r"_test$", "", name, flags=re.IGNORECASE)

        # Convert underscores to spaces for readability
        name = name.replace("_", " ")

        # Clean up whitespace
        name = " ".join(name.split())

        return name or "unnamed test"

    def _parse_time_string(self, time_str: str) -> Optional[str]:
        """Parse various time formats into normalized string."""
        if not time_str:
            return None

        # Remove extra whitespace and convert to lowercase
        time_str = time_str.strip().lower()

        # Look for time patterns
        patterns = [
            (r"(\d+(?:\.\d+)?)\s*s(?:ec(?:onds?)?)?", "s"),  # seconds
            (r"(\d+(?:\.\d+)?)\s*ms(?:ec(?:onds?)?)?", "ms"),  # milliseconds
            (r"(\d+(?:\.\d+)?)\s*μs", "μs"),  # microseconds
            (r"(\d+(?:\.\d+)?)\s*us", "μs"),  # microseconds (alt)
        ]

        for pattern, unit in patterns:
            match = re.search(pattern, time_str)
            if match:
                value = float(match.group(1))

                # Normalize to appropriate unit
                if unit == "s":
                    if value < 1:
                        return f"{int(value * 1000)}ms"
                    else:
                        return f"{value:.1f}s"
                elif unit == "ms":
                    if value < 1:
                        return f"{int(value * 1000)}μs"
                    else:
                        return f"{int(value)}ms"
                else:  # microseconds
                    return f"{int(value)}μs"

        return time_str  # Return as-is if no patterns match

    def _extract_file_path(self, text: str) -> Optional[str]:
        """Extract file path from text."""
        # Look for common file path patterns
        patterns = [
            r"([a-zA-Z0-9_./\\-]+\.(?:rb|py|js|ts|java|php|go|rs|cpp|c|h))(?:\s|:|\[)",  # File extensions
            r"([a-zA-Z0-9_./\\-]+/[a-zA-Z0-9_./\\-]+)",  # Path-like strings
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return None

    def _is_error_message(self, text: str) -> bool:
        """Check if text looks like an error message."""
        error_indicators = [
            "error",
            "exception",
            "traceback",
            "stack trace",
            "undefined method",
            "no method",
            "null pointer",
            "syntax error",
            "runtime error",
            "fatal",
        ]

        text_lower = text.lower()
        return any(indicator in text_lower for indicator in error_indicators)

    def _extract_assertion_values(
        self, text: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """Extract expected and actual values from assertion failure text."""
        patterns = [
            # RSpec style: expected: X, got: Y
            r"expected:\s*([^,\n]+).*?(?:got|actual):\s*([^,\n]+)",
            # pytest style: assert X == Y
            r"assert\s+([^=\n]+)\s*==\s*([^,\n]+)",
            # Generic: Expected X but was/got Y
            r"expected\s+([^,\n]+).*?(?:but\s+(?:was|got)|actual)\s+([^,\n]+)",
        ]

        for i, pattern in enumerate(patterns):
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                if i == 1:  # pytest style: assert actual == expected
                    # For pytest assertions, the first value is actual, second is expected
                    actual = match.group(1).strip()
                    expected = match.group(2).strip()
                    return expected, actual
                else:
                    # For other patterns, group 1 is expected, group 2 is actual
                    expected = match.group(1).strip()
                    actual = match.group(2).strip()
                    return expected, actual

        return None, None

    def _build_test_data(self, **kwargs) -> ParsedTestData:
        """Helper to build ParsedTestData with calculated totals."""
        data = ParsedTestData(**kwargs)

        # Calculate totals from file results if not provided
        if not data.total_tests and data.file_results:
            data.total_tests = sum(
                len(f.test_results) for f in data.file_results
            )
            data.passed_tests = sum(
                sum(1 for t in f.test_results if t.passed)
                for f in data.file_results
            )
            data.failed_tests = sum(
                sum(
                    1 for t in f.test_results if not t.passed and not t.is_error
                )
                for f in data.file_results
            )
            data.error_tests = sum(
                sum(1 for t in f.test_results if t.is_error)
                for f in data.file_results
            )
            data.total_files = len(data.file_results)

        return data
