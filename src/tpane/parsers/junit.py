# src/tpane/parsers/junit.py

"""
JUnit XML Parser

Parses JUnit XML test results into TOPA format.
"""

import re
from typing import TYPE_CHECKING

try:
    # Use defusedxml for security if available
    import defusedxml.ElementTree as ET
except ImportError:
    # Fall back to standard library
    import xml.etree.ElementTree as ET  # type: ignore[no-redef]

# For type hints, always use the standard library types
if TYPE_CHECKING:
    import xml.etree.ElementTree as ET_types

    Element = ET_types.Element
else:
    # Handle both defusedxml and standard library Element types
    try:
        Element = ET.Element
    except AttributeError:
        # defusedxml doesn't expose Element directly, import from standard library
        import xml.etree.ElementTree as _stdlib_ET

        Element = _stdlib_ET.Element

from ..core.schema import ParsedFileResult, ParsedTestData, ParsedTestResult
from .base import BaseParser


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
        except Exception as e:
            # Handle security exceptions from defusedxml and other XML issues
            if "EntitiesForbidden" in str(
                type(e)
            ) or "ExternalReferenceForbidden" in str(type(e)):
                return self._parse_as_text(
                    content, "XML Security Error: Entity processing forbidden"
                )
            else:
                # Fall back for any other XML processing issues
                return self._parse_as_text(content, f"XML Processing Error: {e}")

    def _clean_xml(self, content: str) -> str:
        """Clean up common XML formatting issues."""
        # Remove BOM if present
        if content.startswith("\ufeff"):
            content = content[1:]

        # Only do minimal XML cleaning - don't escape structure tags
        # Fix double-encoded entities (e.g., "&amp;amp;" → "&amp;")
        # Pattern explanation: "&amp;" followed by valid XML entity names
        # Examples: "&amp;amp;" → "&amp;", "&amp;lt;" → "&lt;"
        content = re.sub(r"&amp;(amp|lt|gt|quot|apos);", r"&\1;", content)

        # Fix unescaped ampersands that aren't part of valid XML entities
        # Negative lookahead pattern explanation:
        # - &(?!...): Match & not followed by the lookahead pattern
        # - (?:amp|lt|gt|quot|apos): Standard XML entities
        # - #\d+: Decimal character references (e.g., &#39;)
        # - #x[0-9a-fA-F]+: Hexadecimal character references (e.g., &#x27;)
        # Examples: "Tom & Jerry" → "Tom &amp; Jerry", but "&amp;" stays "&amp;"
        content = re.sub(
            r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)",
            "&amp;",
            content,
        )

        return content.strip()

    def _parse_testsuites(self, testsuites: list[Element]) -> ParsedTestData:
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
            file_path = self._extract_file_path_from_suite(testsuite, suite_name)
            file_results.append(
                ParsedFileResult(file_path=file_path, test_results=test_results)
            )

        # Calculate passed tests
        total_passed = total_tests - total_failures - total_errors

        # Format time
        elapsed_time = (
            self._parse_time_string(f"{total_time}s") if total_time > 0 else None
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

    def _parse_testcase(self, testcase: Element) -> ParsedTestResult:
        """Parse individual test case."""
        name = testcase.get("name", "unnamed test")

        # Normalize test name - just use the base name without classname prefix
        test_name = self._normalize_test_name(name)

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

    def _extract_file_path_from_suite(self, testsuite: Element, suite_name: str) -> str:
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

    def _parse_as_text(self, content: str, error_context: str) -> ParsedTestData:
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
                passed = "failure" not in line.lower() and "error" not in line.lower()
                is_error = "error" in line.lower()

                test_result = ParsedTestResult(
                    name=self._normalize_test_name(test_name),
                    passed=passed,
                    error_message=line if is_error else None,
                    expected="parse error" if not passed and not is_error else None,
                    actual=error_context if not passed and not is_error else None,
                )
                test_results.append(test_result)

        # Create single file result
        file_results = [
            ParsedFileResult(
                file_path="junit_parse_error.xml", test_results=test_results
            )
        ]

        return self._build_test_data(file_results=file_results)
