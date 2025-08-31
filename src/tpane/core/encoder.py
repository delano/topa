"""
TOPA Encoder

Converts parsed test data into standardized TOPA format with token optimization.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from .schema import (
        FileCounts,
        FileIssues,
        FileSummary,
        ParsedTestData,
        ParsedTestResult,
        Summary,
        TestCounts,
        TestResult,
        TestType,
        TOPAOutput,
    )
    from .token_budget import TokenBudget
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent))
    from schema import (
        FileCounts,
        FileIssues,
        FileSummary,
        ParsedTestData,
        ParsedTestResult,
        Summary,
        TestCounts,
        TestResult,
        TestType,
        TOPAOutput,
    )
    from token_budget import TokenBudget


class FocusMode:
    """Focus mode constants."""

    SUMMARY = "summary"
    CRITICAL = "critical"
    FAILURES = "failures"
    FIRST_FAILURE = "first-failure"


class TOPAEncoder:
    """Encodes parsed test data into TOPA format with token optimization."""

    VERSION = "0.1"

    def __init__(
        self,
        focus_mode: str = FocusMode.FAILURES,
        token_budget: Optional[TokenBudget] = None,
    ):
        self.focus_mode = focus_mode
        self.budget = token_budget or TokenBudget(2000)

    def encode(self, parsed_data: ParsedTestData) -> Dict[str, Any]:
        """Convert parsed test data to TOPA format."""

        # Build summary
        summary = self._build_summary(parsed_data)

        # Create base TOPA output
        topa_output = TOPAOutput(version=self.VERSION, summary=summary)

        # Add details based on focus mode
        if self.focus_mode == FocusMode.SUMMARY:
            topa_output.files_with_issues = self._build_files_with_issues(parsed_data)

        elif self.focus_mode == FocusMode.CRITICAL:
            topa_output.failures = self._build_critical_failures(parsed_data)

        elif self.focus_mode == FocusMode.FIRST_FAILURE:
            topa_output.failures = self._build_first_failure_details(parsed_data)

        else:  # FAILURES mode (default)
            topa_output.failures = self._build_all_failure_details(parsed_data)

        return topa_output.to_dict()

    def _build_summary(self, parsed_data: ParsedTestData) -> Summary:
        """Build the summary section."""
        test_counts = TestCounts(
            total=parsed_data.total_tests,
            passed=parsed_data.passed_tests,
            failed=parsed_data.failed_tests,
            errors=parsed_data.error_tests,
        )

        file_counts = FileCounts(
            total=parsed_data.total_files,
            with_failures=parsed_data.files_with_failures,
        )

        return Summary(
            status=parsed_data.overall_status,
            tests=test_counts,
            files=file_counts,
            elapsed=parsed_data.elapsed_time,
        )

    def _build_files_with_issues(self, parsed_data: ParsedTestData) -> List[FileIssues]:
        """Build file-level issue counts for summary mode."""
        files_with_issues = []

        for file_result in parsed_data.file_results:
            if file_result.has_issues():
                issue_count = file_result.failure_count() + file_result.error_count()

                files_with_issues.append(
                    FileIssues(
                        file=self._normalize_path(file_result.file_path),
                        issues=issue_count,
                    )
                )

                # Budget check
                if not self.budget.has_budget():
                    break

        return files_with_issues

    def _build_critical_failures(
        self, parsed_data: ParsedTestData
    ) -> List[FileSummary]:
        """Build failure details for critical mode (errors only)."""
        failures = []

        for file_result in parsed_data.file_results:
            error_tests = [t for t in file_result.test_results if t.is_error]

            if error_tests:
                test_results = []

                for test in error_tests:
                    test_result = TestResult(
                        line=test.line or 0,
                        name=test.name,
                        type=TestType.ERROR,
                        error=self.budget.smart_truncate(
                            test.error_message or "unknown error", 50
                        ),
                    )
                    test_results.append(test_result)

                    # Budget check
                    if not self.budget.has_budget():
                        break

                if test_results:
                    failures.append(
                        FileSummary(
                            file=self._normalize_path(file_result.file_path),
                            tests=test_results,
                        )
                    )

                # Budget check
                if not self.budget.has_budget():
                    break

        return failures

    def _build_first_failure_details(
        self, parsed_data: ParsedTestData
    ) -> List[FileSummary]:
        """Build failure details for first-failure mode."""
        failures = []

        for file_result in parsed_data.file_results:
            failed_tests = [t for t in file_result.test_results if not t.passed]

            if failed_tests:
                # Take first failure/error only
                first_test = failed_tests[0]
                test_result = self._build_test_result(first_test)

                # Count additional failures
                truncated_count = (
                    len(failed_tests) - 1 if len(failed_tests) > 1 else None
                )

                failures.append(
                    FileSummary(
                        file=self._normalize_path(file_result.file_path),
                        tests=[test_result],
                        truncated=truncated_count,
                    )
                )

                # Budget check
                if not self.budget.has_budget():
                    break

        return failures

    def _build_all_failure_details(
        self, parsed_data: ParsedTestData
    ) -> List[FileSummary]:
        """Build complete failure details for failures mode."""
        failures = []

        for file_result in parsed_data.file_results:
            failed_tests = [t for t in file_result.test_results if not t.passed]

            if failed_tests:
                test_results = []

                # Process errors first (higher priority)
                error_tests = [t for t in failed_tests if t.is_error]
                failure_tests = [t for t in failed_tests if t.is_failure]

                for test in error_tests + failure_tests:
                    test_result = self._build_test_result(test)
                    test_results.append(test_result)

                    # Budget check - leave room for at least one more file
                    if self.budget.used_percentage > 80:
                        break

                if test_results:
                    failures.append(
                        FileSummary(
                            file=self._normalize_path(file_result.file_path),
                            tests=test_results,
                        )
                    )

                # Budget check
                if not self.budget.has_budget():
                    break

        return failures

    def _build_test_result(self, test: ParsedTestResult) -> TestResult:
        """Build a single test result with budget awareness."""
        if test.is_error:
            return TestResult(
                line=test.line or 0,
                name=self.budget.smart_truncate(test.name, 30),
                type=TestType.ERROR,
                error=self.budget.smart_truncate(
                    test.error_message or "unknown error", 50
                ),
            )
        else:
            result = TestResult(
                line=test.line or 0,
                name=self.budget.smart_truncate(test.name, 30),
                type=TestType.FAILURE,
            )

            # Add expected/actual if available
            if test.expected is not None:
                result.expected = self.budget.smart_truncate(str(test.expected), 25)
            if test.actual is not None:
                result.actual = self.budget.smart_truncate(str(test.actual), 25)

            # Add diff if budget allows and values are strings
            if (
                self.budget.remaining > 100
                and test.expected
                and test.actual
                and isinstance(test.expected, str)
                and isinstance(test.actual, str)
            ):
                result.diff = self._generate_simple_diff(test.expected, test.actual)

            return result

    def _generate_simple_diff(self, expected: str, actual: str) -> Optional[str]:
        """Generate a simple diff if budget allows."""
        if not self.budget.has_budget(50):  # Need reasonable space for diff
            return None

        # Simple line-by-line diff
        exp_lines = expected.split("\n")
        act_lines = actual.split("\n")

        diff_lines = []
        diff_lines.append(f"- {act_lines[0] if act_lines else '(empty)'}")
        diff_lines.append(f"+ {exp_lines[0] if exp_lines else '(empty)'}")

        diff_text = "\n".join(diff_lines)

        # Only return if it fits in budget
        if not self.budget.would_exceed(diff_text):
            return diff_text

        return None

    def _normalize_path(self, file_path: str) -> str:
        """Normalize file path for token efficiency."""
        if not file_path:
            return "unknown"

        try:
            # Convert to Path object for easier manipulation
            path = Path(file_path)

            # Check for potentially malicious path patterns
            path_str = str(path)
            if any(
                suspicious in path_str
                for suspicious in [
                    "../",
                    "..\\",
                    "/etc/",
                    "/proc/",
                    "/sys/",
                    "C:\\Windows",
                    "C:\\System32",
                ]
            ):
                # For potentially suspicious paths, use only the filename
                return path.name or "unknown"

            # If it's already relative and reasonable length, use as-is
            if not path.is_absolute() and len(path_str) < 50:
                return path_str

            # Try to make relative to current directory
            try:
                rel_path = path.relative_to(Path.cwd())
                if len(str(rel_path)) < len(file_path):
                    return str(rel_path)
            except ValueError:
                pass  # Not relative to cwd

            # If path is still long, try to use just the meaningful part
            parts = path.parts
            if len(parts) > 3:
                # Keep last 2-3 parts if it makes sense
                # Use joinpath to handle Windows drive letters properly
                meaningful_parts = parts[-2:]
                try:
                    return "/".join(
                        meaningful_parts
                    )  # Force forward slashes for consistency
                except (TypeError, ValueError, AttributeError) as e:
                    # Log the specific error for debugging
                    # TypeError: if meaningful_parts contains non-string elements
                    # ValueError: if join operation fails due to invalid characters
                    # AttributeError: if meaningful_parts is not iterable
                    import logging

                    logging.debug(
                        f"Path normalization failed for {meaningful_parts}: {e}"
                    )
                    return path.name

            # Fall back to basename if nothing else works
            if len(str(path)) > 60:
                return path.name

            return str(path)

        except (OSError, TypeError, ValueError, AttributeError) as e:
            # If any path processing fails, fall back to basename
            # OSError: File system issues (permissions, invalid paths)
            # TypeError: Invalid argument types
            # ValueError: Invalid path values
            # AttributeError: Missing attributes on path objects
            import logging

            logging.debug(
                f"Path normalization completely failed for '{file_path}': {e}"
            )
            try:
                return Path(file_path).name
            except (OSError, TypeError, ValueError):
                return "unknown"
