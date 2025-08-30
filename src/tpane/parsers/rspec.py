"""
RSpec JSON Parser

Parses RSpec JSON output into TOPA format.
"""

import json
from typing import Any, Dict

try:
    from ..core.schema import ParsedFileResult, ParsedTestData, ParsedTestResult
    from .base import BaseParser
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent))
    from base import BaseParser

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.schema import ParsedFileResult, ParsedTestData, ParsedTestResult


class RSpecParser(BaseParser):
    """Parser for RSpec JSON format."""

    def parse(self, content: str) -> ParsedTestData:
        """Parse RSpec JSON content."""
        try:
            data = json.loads(content)

            # Validate expected structure
            if not isinstance(data, dict):
                raise ValueError("Expected JSON object at root")

            if "examples" not in data:
                raise ValueError("Missing 'examples' in RSpec JSON")

            return self._parse_rspec_json(data)

        except json.JSONDecodeError as e:
            # Fall back to text parsing
            return self._parse_as_text(content, f"JSON Parse Error: {e}")

    def _parse_rspec_json(self, data: Dict[str, Any]) -> ParsedTestData:
        """Parse RSpec JSON structure."""
        # Extract summary information
        summary = data.get("summary", {})
        total_tests = summary.get("example_count", 0)
        failed_count = summary.get("failure_count", 0)
        error_count = summary.get("error_count", 0)  # RSpec might have errors
        pending_count = summary.get("pending_count", 0)
        duration = summary.get("duration")

        # Passed tests = total - failed - errors - pending
        # (Pending tests are usually counted as passed for TOPA purposes)
        passed_count = total_tests - failed_count - error_count

        # Parse elapsed time
        elapsed_time = None
        if duration is not None:
            elapsed_time = self._parse_time_string(f"{duration}s")

        # Parse individual examples (tests)
        examples = data.get("examples", [])
        file_tests = {}  # Group by file

        for example in examples:
            test_result = self._parse_example(example)
            file_path = example.get("file_path", "unknown_spec.rb")

            # Clean up file path
            file_path = self._clean_rspec_file_path(file_path)

            if file_path not in file_tests:
                file_tests[file_path] = []
            file_tests[file_path].append(test_result)

        # Convert to file results
        file_results = []
        for file_path, tests in file_tests.items():
            file_results.append(
                ParsedFileResult(file_path=file_path, test_results=tests)
            )

        return ParsedTestData(
            total_tests=total_tests,
            passed_tests=passed_count,
            failed_tests=failed_count,
            error_tests=error_count,
            total_files=len(file_results),
            elapsed_time=elapsed_time,
            file_results=file_results,
        )

    def _parse_example(self, example: Dict[str, Any]) -> ParsedTestResult:
        """Parse individual RSpec example."""
        # Basic info
        description = example.get("description", "unnamed example")
        full_description = example.get("full_description", description)
        status = example.get("status", "unknown")
        line_number = example.get("line_number")

        # Determine if passed
        passed = status in ["passed", "pending"]

        # Create test result
        test_result = ParsedTestResult(
            name=self._normalize_rspec_description(
                full_description or description
            ),
            line=line_number,
            passed=passed,
        )

        # Handle failures and errors
        if not passed:
            exception = example.get("exception")

            if exception:
                exception_class = exception.get("class", "")
                exception_message = exception.get("message", "")

                # Determine if this is an error (exception) or failure (assertion)
                if self._is_rspec_error(exception_class):
                    # This is an error/exception
                    test_result.error_message = (
                        f"{exception_class}: {exception_message}".strip(": ")
                    )
                else:
                    # This is an assertion failure
                    # Try to extract expected/actual from message
                    expected, actual = self._extract_assertion_values(
                        exception_message
                    )

                    if expected and actual:
                        test_result.expected = expected
                        test_result.actual = actual
                    else:
                        # Use full exception info
                        test_result.expected = "assertion to pass"
                        test_result.actual = (
                            f"{exception_class}: {exception_message}".strip(
                                ": "
                            )
                        )

        return test_result

    def _normalize_rspec_description(self, description: str) -> str:
        """Normalize RSpec test descriptions."""
        if not description:
            return "unnamed example"

        # RSpec descriptions are usually already well formatted
        # Just clean up extra whitespace
        return " ".join(description.split())

    def _is_rspec_error(self, exception_class: str) -> bool:
        """Determine if exception class represents an error vs assertion failure."""
        # RSpec assertion failures typically use specific exception types
        failure_exceptions = [
            "RSpec::Expectations::ExpectationNotMetError",
            "ExpectationNotMetError",
            "Failure",
        ]

        # Anything else is likely a real error/exception
        return exception_class not in failure_exceptions

    def _clean_rspec_file_path(self, file_path: str) -> str:
        """Clean up RSpec file paths."""
        if not file_path:
            return "unknown_spec.rb"

        # RSpec file paths are usually already clean
        # Just ensure they have .rb extension if they look like Ruby files
        if "spec" in file_path.lower() and not file_path.endswith(".rb"):
            file_path += ".rb"

        return file_path

    def _parse_as_text(
        self, content: str, error_context: str
    ) -> ParsedTestData:
        """Fallback text parsing for malformed JSON."""
        lines = content.split("\n")

        test_results = []

        # Look for common RSpec text patterns
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for failure/example patterns
            if any(
                pattern in line.lower()
                for pattern in ["example", "spec", "failure", "error"]
            ):
                test_name = line

                # Determine status
                passed = (
                    "failure" not in line.lower()
                    and "error" not in line.lower()
                )
                is_error = "error" in line.lower()

                test_result = ParsedTestResult(
                    name=self._normalize_test_name(test_name),
                    passed=passed,
                    error_message=line if is_error else None,
                    expected="valid JSON"
                    if not passed and not is_error
                    else None,
                    actual=error_context
                    if not passed and not is_error
                    else None,
                )
                test_results.append(test_result)

        # Create single file result
        file_results = [
            ParsedFileResult(
                file_path="rspec_parse_error.json", test_results=test_results
            )
        ]

        return self._build_test_data(file_results=file_results)
