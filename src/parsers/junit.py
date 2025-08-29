"""
JUnit XML Parser

Parses JUnit XML test results into TOPA format.
"""

import re
import xml.etree.ElementTree as ET
from typing import List

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


class JUnitParser(BaseParser):
    """Parser for JUnit XML format."""

    def parse(self, content: str) -> ParsedTestData:
        """Parse JUnit XML content."""
        try:
            # Clean up common XML issues
            content = self._clean_xml(content)
            root = ET.fromstring(content)

            # Handle both single testsuite and testsuites root elements
            if root.tag == "testsuites":
                testsuites = root.findall("testsuite")
            elif root.tag == "testsuite":
                testsuites = [root]
            else:
                raise ValueError(f"Unexpected root element: {root.tag}")

            return self._parse_testsuites(testsuites)

        except ET.ParseError as e:
            # Fall back to text-based parsing for malformed XML
            return self._parse_as_text(content, f"XML Parse Error: {e}")

    def _clean_xml(self, content: str) -> str:
        """Clean up common XML formatting issues."""
        # Remove BOM if present
        if content.startswith("\ufeff"):
            content = content[1:]

        # Fix common encoding issues
        content = content.replace("&", "&amp;")
        content = re.sub(
            r"&amp;(amp|lt|gt|quot|apos);", r"&\1;", content
        )  # Don't double-encode

        return content.strip()

    def _parse_testsuites(self, testsuites: List[ET.Element]) -> ParsedTestData:
        """Parse multiple test suites."""
        file_results = []
        total_tests = 0
        total_failures = 0
        total_errors = 0
        total_time = 0.0

        for testsuite in testsuites:
            # Parse testsuite attributes
            suite_name = testsuite.get("name", "unknown")
            suite_tests = int(testsuite.get("tests", "0"))
            suite_failures = int(testsuite.get("failures", "0"))
            suite_errors = int(testsuite.get("errors", "0"))
            suite_time = float(testsuite.get("time", "0"))

            # Accumulate totals
            total_tests += suite_tests
            total_failures += suite_failures
            total_errors += suite_errors
            total_time += suite_time

            # Parse individual test cases
            testcases = testsuite.findall("testcase")
            test_results = []

            for testcase in testcases:
                test_result = self._parse_testcase(testcase)
                test_results.append(test_result)

            # Create file result (use suite name as file path)
            file_path = self._extract_file_path_from_suite(
                testsuite, suite_name
            )
            file_results.append(
                ParsedFileResult(file_path=file_path, test_results=test_results)
            )

        # Calculate passed tests
        total_passed = total_tests - total_failures - total_errors

        # Format time
        elapsed_time = (
            self._parse_time_string(f"{total_time}s")
            if total_time > 0
            else None
        )

        return ParsedTestData(
            total_tests=total_tests,
            passed_tests=total_passed,
            failed_tests=total_failures,
            error_tests=total_errors,
            total_files=len(file_results),
            elapsed_time=elapsed_time,
            file_results=file_results,
        )

    def _parse_testcase(self, testcase: ET.Element) -> ParsedTestResult:
        """Parse individual test case."""
        name = testcase.get("name", "unnamed test")
        classname = testcase.get("classname", "")

        # Normalize test name
        test_name = self._normalize_test_name(name)
        if classname and classname not in test_name:
            test_name = f"{classname}: {test_name}"

        # Extract line number if present
        line = None
        line_attr = testcase.get("line")
        if line_attr:
            try:
                line = int(line_attr)
            except ValueError:
                pass

        # Check for failures and errors
        failure = testcase.find("failure")
        error = testcase.find("error")

        if error is not None:
            # This is an error (exception)
            error_message = error.get("message", "")
            error_text = error.text or ""

            # Combine message and text
            full_error = f"{error_message}: {error_text}".strip(": ")

            return ParsedTestResult(
                name=test_name,
                line=line,
                passed=False,
                error_message=full_error,
            )

        elif failure is not None:
            # This is an assertion failure
            failure_message = failure.get("message", "")
            failure_text = failure.text or ""

            # Try to extract expected/actual values
            full_failure = f"{failure_message} {failure_text}".strip()
            expected, actual = self._extract_assertion_values(full_failure)

            return ParsedTestResult(
                name=test_name,
                line=line,
                passed=False,
                expected=expected,
                actual=actual,
            )

        else:
            # Passed test
            return ParsedTestResult(name=test_name, line=line, passed=True)

    def _extract_file_path_from_suite(
        self, testsuite: ET.Element, suite_name: str
    ) -> str:
        """Extract file path from testsuite element."""
        # Look for file-related attributes
        file_attrs = ["file", "filename", "source"]
        for attr in file_attrs:
            file_path = testsuite.get(attr)
            if file_path:
                return file_path

        # Try to extract from suite name
        if "/" in suite_name or "\\" in suite_name or "." in suite_name:
            # Looks like a file path
            return suite_name

        # Check for package-style naming (com.example.Test -> com/example/Test)
        if "." in suite_name:
            parts = suite_name.split(".")
            if len(parts) > 1:
                # Assume last part is class name, others are package
                return "/".join(parts[:-1]) + "/" + parts[-1] + ".java"

        # Fall back to suite name with common extension
        return suite_name + ".java"

    def _parse_as_text(
        self, content: str, error_context: str
    ) -> ParsedTestData:
        """Fallback text-based parsing for malformed XML."""
        lines = content.split("\n")

        # Try to extract basic information from text
        test_results = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for test-like patterns
            if (
                "test" in line.lower()
                or "failure" in line.lower()
                or "error" in line.lower()
            ):
                # Extract test name if possible
                test_name = line

                # Determine if it's a failure/error
                passed = (
                    "failure" not in line.lower()
                    and "error" not in line.lower()
                )
                is_error = "error" in line.lower()

                test_result = ParsedTestResult(
                    name=self._normalize_test_name(test_name),
                    passed=passed,
                    error_message=line if is_error else None,
                    expected="parse error"
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
                file_path="junit_parse_error.xml", test_results=test_results
            )
        ]

        return self._build_test_data(file_results=file_results)
