# src/tpane/parsers/pytest.py

"""
Pytest Output Parser

Parses pytest console output into TOPA format.
"""

import re
from collections import defaultdict
from typing import Optional

from ..core.schema import ParsedFileResult, ParsedTestData, ParsedTestResult
from .base import BaseParser


class PytestParser(BaseParser):
    """Parser for pytest console output."""

    def __init__(self) -> None:
        super().__init__()

        # Pytest output patterns
        self.test_line_pattern = re.compile(r"^([^\s:]+(?:\.py)?):?:?(\w+)?\s+(.*)$")

        self.failure_pattern = re.compile(
            r"^FAILED\s+([^:\s]+(?:\.py)?):?:?(\w+)?\s*-?\s*(.*)$"
        )

        self.error_pattern = re.compile(
            r"^ERROR\s+([^:\s]+(?:\.py)?):?:?(\w+)?\s*-?\s*(.*)$"
        )

        self.passed_pattern = re.compile(r"^PASSED\s+([^:\s]+(?:\.py)?):?:?(\w+)?")

        self.summary_pattern = re.compile(
            r"=+\s*(\d+)\s+failed(?:,\s*(\d+)\s+passed)?(?:,\s*(\d+)\s+error)?.*?in\s+([\d.]+s?)"
        )

        self.assertion_pattern = re.compile(
            r"assert\s+(.+?)\s*(?:==|!=|<|>|<=|>=|is|in)\s*(.+?)(?:\s*$|\s*#)",
            re.IGNORECASE,
        )

    def parse(self, content: str) -> ParsedTestData:
        """Parse pytest console output."""
        lines = content.split("\n")

        # Track test results by file
        file_tests = defaultdict(list)

        # Track summary info
        total_tests = 0
        failed_count = 0
        passed_count = 0
        error_count = 0
        elapsed_time = None

        # Parse mode

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Check for summary line first
            summary_match = self.summary_pattern.search(line)
            if summary_match:
                failed_count = int(summary_match.group(1))
                passed_count = int(summary_match.group(2) or 0)
                error_count = int(summary_match.group(3) or 0)
                total_tests = failed_count + passed_count + error_count
                elapsed_time = self._parse_time_string(summary_match.group(4))
                continue

            # Check for FAILED lines
            failure_match = self.failure_pattern.match(line)
            if failure_match:
                file_path = failure_match.group(1)
                test_name = failure_match.group(2) or "unknown"
                failure_reason = failure_match.group(3) or ""

                # Extract line number from failure reason if present
                line_num = self._extract_line_number(failure_reason)

                test_result = ParsedTestResult(
                    name=self._normalize_test_name(test_name),
                    line=line_num,
                    passed=False,
                )

                # Look ahead for assertion details
                assertion_details = self._extract_assertion_from_context(lines, i + 1)
                if assertion_details:
                    test_result.expected, test_result.actual = assertion_details
                elif failure_reason:
                    # Use failure reason as expected/actual if no assertion found
                    if self._is_error_message(failure_reason):
                        test_result.error_message = failure_reason
                    else:
                        test_result.expected = "assertion to pass"
                        test_result.actual = failure_reason

                file_tests[file_path].append(test_result)
                continue

            # Check for ERROR lines
            error_match = self.error_pattern.match(line)
            if error_match:
                file_path = error_match.group(1)
                test_name = error_match.group(2) or "unknown"
                error_reason = error_match.group(3) or "unknown error"

                line_num = self._extract_line_number(error_reason)

                test_result = ParsedTestResult(
                    name=self._normalize_test_name(test_name),
                    line=line_num,
                    passed=False,
                    error_message=error_reason,
                )

                file_tests[file_path].append(test_result)
                continue

            # Check for PASSED lines
            passed_match = self.passed_pattern.match(line)
            if passed_match:
                file_path = passed_match.group(1)
                test_name = passed_match.group(2) or "unknown"

                test_result = ParsedTestResult(
                    name=self._normalize_test_name(test_name), passed=True
                )

                file_tests[file_path].append(test_result)
                continue

            # Skip unmatched lines

        # If we couldn't parse summary, calculate from parsed tests
        if total_tests == 0:
            total_tests = sum(len(tests) for tests in file_tests.values())
            passed_count = sum(
                sum(1 for t in tests if t.passed) for tests in file_tests.values()
            )
            failed_count = sum(
                sum(1 for t in tests if not t.passed and not t.is_error)
                for tests in file_tests.values()
            )
            error_count = sum(
                sum(1 for t in tests if t.is_error) for tests in file_tests.values()
            )

        # Convert to file results
        file_results = []
        for file_path, tests in file_tests.items():
            # Clean up file path
            clean_path = self._clean_file_path(file_path)

            file_results.append(
                ParsedFileResult(file_path=clean_path, test_results=tests)
            )

        # Handle case where we have summary but no individual test results
        if total_tests > 0 and not file_results:
            # Create a generic file result
            generic_tests = []

            for i in range(failed_count):
                generic_tests.append(
                    ParsedTestResult(
                        name=f"failed test {i + 1}",
                        passed=False,
                        expected="test to pass",
                        actual="test failed",
                    )
                )

            for i in range(error_count):
                generic_tests.append(
                    ParsedTestResult(
                        name=f"error test {i + 1}",
                        passed=False,
                        error_message="test error occurred",
                    )
                )

            for i in range(passed_count):
                generic_tests.append(
                    ParsedTestResult(name=f"passed test {i + 1}", passed=True)
                )

            file_results.append(
                ParsedFileResult(file_path="pytest_output", test_results=generic_tests)
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

    def _extract_assertion_from_context(
        self, lines: list[str], start_index: int
    ) -> Optional[tuple]:
        """Look ahead in lines for assertion details."""
        # Look at next few lines for assertion info
        for i in range(start_index, min(start_index + 10, len(lines))):
            line = lines[i].strip()

            # Stop at next test result or empty lines
            if any(
                pattern.match(line)
                for pattern in [
                    self.failure_pattern,
                    self.error_pattern,
                    self.passed_pattern,
                ]
            ):
                break

            if not line:
                continue

            # Look for assertion patterns
            if "assert" in line.lower():
                expected, actual = self._extract_assertion_values(line)
                if expected and actual:
                    return expected, actual

            # Look for comparison indicators
            if any(op in line for op in ["==", "!=", "Expected:", "Actual:"]):
                expected, actual = self._extract_assertion_values(line)
                if expected and actual:
                    return expected, actual

        return None

    def _clean_file_path(self, file_path: str) -> str:
        """Clean up pytest file paths."""
        if not file_path:
            return "unknown"

        # Remove pytest-specific prefixes
        file_path = re.sub(r"^.*?::", "", file_path)

        # Ensure .py extension if it looks like a Python file
        if "/" in file_path or "_test" in file_path or "test_" in file_path:
            if not file_path.endswith(".py"):
                file_path += ".py"

        return file_path
