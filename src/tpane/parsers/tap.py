# src/tpane/parsers/tap.py

"""
TAP (Test Anything Protocol) Parser

Parses TAP format test output into TOPA format.
"""

import re

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


class TAPParser(BaseParser):
    """Parser for TAP (Test Anything Protocol) format."""

    def __init__(self):
        super().__init__()

        # TAP format patterns
        self.plan_pattern = re.compile(r"^1\.\.(\d+)(?:\s*#\s*(.*))?$")
        self.test_pattern = re.compile(
            r"^(ok|not ok)(?:\s+(\d+))?(?:\s*-?\s*(.*))?$", re.IGNORECASE
        )
        self.directive_pattern = re.compile(
            r"#\s*(SKIP|TODO|FIXME)(?:\s+(.*))?$", re.IGNORECASE
        )
        self.diagnostic_pattern = re.compile(r"^#\s*(.*)$")

    def parse(self, content: str) -> ParsedTestData:
        """Parse TAP format content."""
        lines = content.split("\n")

        test_results = []
        planned_tests = 0
        current_file = "tap_output"
        pending_diagnostics = []

        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Check for plan line (1..N)
            plan_match = self.plan_pattern.match(line)
            if plan_match:
                planned_tests = int(plan_match.group(1))
                if plan_match.group(2):
                    # Plan has description, might include file info
                    plan_desc = plan_match.group(2)
                    file_path = self._extract_file_path(plan_desc)
                    if file_path:
                        current_file = file_path
                continue

            # Check for test result line
            test_match = self.test_pattern.match(line)
            if test_match:
                status = test_match.group(1).lower()
                test_number = (
                    int(test_match.group(2))
                    if test_match.group(2)
                    else len(test_results) + 1
                )
                description = test_match.group(3) or f"test {test_number}"

                # Check for directives (SKIP, TODO, etc.)
                directive_match = self.directive_pattern.search(description)
                directive = None
                if directive_match:
                    directive = directive_match.group(1).upper()
                    directive_reason = directive_match.group(2)
                    # Remove directive from description
                    description = description[: directive_match.start()].strip()

                # Determine if test passed
                passed = status == "ok"

                # Handle TODO/SKIP directives - these are special cases in TAP
                if directive == "TODO":
                    # TODO directive semantics (per TAP specification):
                    # - TODO tests are expected to fail (work in progress)
                    # - A TODO test that fails is treated as a success (expected failure)
                    # - A TODO test that passes is treated as a failure (unexpected success)
                    # This allows developers to mark known-failing tests without breaking builds
                    if passed:
                        passed = (
                            False  # Unexpected pass - TODO should have failed
                        )
                        pending_diagnostics.append(
                            "Unexpected pass - TODO item succeeded"
                        )
                    else:
                        # TODO tests that fail are expected - treat as passed
                        # This is counterintuitive but follows TAP standard behavior
                        passed = True

                elif directive == "SKIP":
                    # Skipped tests are treated as passed
                    passed = True

                # Create test result
                test_result = ParsedTestResult(
                    name=self._normalize_test_name(description),
                    line=line_num + 1,  # TAP line number
                    passed=passed,
                )

                # Add diagnostic info if test failed and we have pending diagnostics
                if not passed and pending_diagnostics:
                    # Use diagnostics to populate error/expected/actual
                    diagnostic_text = " ".join(pending_diagnostics)

                    if self._is_error_message(diagnostic_text):
                        test_result.error_message = diagnostic_text
                    else:
                        # Try to extract expected/actual from diagnostics
                        expected, actual = self._extract_assertion_values(
                            diagnostic_text
                        )
                        if expected and actual:
                            test_result.expected = expected
                            test_result.actual = actual
                        else:
                            test_result.expected = "test to pass"
                            test_result.actual = diagnostic_text

                    pending_diagnostics = []  # Clear used diagnostics

                test_results.append(test_result)
                continue

            # Check for diagnostic line (comments)
            diagnostic_match = self.diagnostic_pattern.match(line)
            if diagnostic_match:
                diagnostic = diagnostic_match.group(1).strip()

                # Skip empty diagnostics and directives we've already handled
                if not diagnostic or diagnostic.upper().startswith(
                    ("SKIP", "TODO", "FIXME")
                ):
                    continue

                # Look for file information in diagnostics
                file_path = self._extract_file_path(diagnostic)
                if file_path:
                    current_file = file_path
                    continue

                # Collect diagnostic for next test
                pending_diagnostics.append(diagnostic)
                continue

        # Calculate statistics
        total_tests = len(test_results)
        passed_tests = sum(1 for t in test_results if t.passed)
        failed_tests = sum(
            1 for t in test_results if not t.passed and not t.is_error
        )
        error_tests = sum(1 for t in test_results if t.is_error)

        # Check if we have the expected number of tests
        if planned_tests > 0 and total_tests != planned_tests:
            # Add a diagnostic test result for the mismatch
            test_results.append(
                ParsedTestResult(
                    name="test plan mismatch",
                    passed=False,
                    error_message=f"Planned {planned_tests} tests but got {total_tests}",
                )
            )
            error_tests += 1
            total_tests += 1

        # Create file result
        file_results = [
            ParsedFileResult(file_path=current_file, test_results=test_results)
        ]

        return ParsedTestData(
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            error_tests=error_tests,
            total_files=1,
            file_results=file_results,
        )
