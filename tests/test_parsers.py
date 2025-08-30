#!/usr/bin/env python3
"""
Test suite for TOPA parsers
"""

import sys
import unittest
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parsers.junit import JUnitParser
from parsers.pytest import PytestParser
from parsers.rspec import RSpecParser
from parsers.tap import TAPParser


class TestJUnitParser(unittest.TestCase):
    """Test JUnit XML parser."""

    def setUp(self):
        self.parser = JUnitParser()

    def test_parse_simple_xml(self):
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="TestSuite" tests="2" failures="1" errors="0" time="1.0">
  <testcase name="test_pass" classname="TestClass" time="0.5"/>
  <testcase name="test_fail" classname="TestClass" time="0.5">
    <failure message="Expected true but was false">Assertion failed</failure>
  </testcase>
</testsuite>"""

        result = self.parser.parse(xml_content)

        self.assertEqual(result.total_tests, 2)
        self.assertEqual(result.passed_tests, 1)
        self.assertEqual(result.failed_tests, 1)
        self.assertEqual(result.error_tests, 0)
        self.assertEqual(len(result.file_results), 1)

        file_result = result.file_results[0]
        self.assertEqual(len(file_result.test_results), 2)

        # Check failed test
        failed_test = file_result.test_results[1]
        self.assertFalse(failed_test.passed)
        self.assertEqual(failed_test.name, "fail")

    def test_parse_with_errors(self):
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="TestSuite" tests="1" failures="0" errors="1" time="1.0">
  <testcase name="test_error" classname="TestClass" time="0.5">
    <error message="NullPointerException">Error occurred</error>
  </testcase>
</testsuite>"""

        result = self.parser.parse(xml_content)

        self.assertEqual(result.total_tests, 1)
        self.assertEqual(result.error_tests, 1)

        error_test = result.file_results[0].test_results[0]
        self.assertFalse(error_test.passed)
        self.assertTrue(error_test.is_error)
        self.assertIn("NullPointerException", error_test.error_message)


class TestPytestParser(unittest.TestCase):
    """Test pytest output parser."""

    def setUp(self):
        self.parser = PytestParser()

    def test_parse_pytest_output(self):
        pytest_output = """
FAILED test_user.py::test_validation - assert False == True
PASSED test_user.py::test_creation
ERROR test_auth.py::test_login - NameError: name 'AuthService' is not defined
===== 1 failed, 1 passed, 1 error in 1.23s =====
"""

        result = self.parser.parse(pytest_output)

        # Should extract from summary line or individual results
        self.assertGreater(result.total_tests, 0)
        self.assertGreater(len(result.file_results), 0)

    def test_extract_assertion_values(self):
        # Test the base parser method
        expected, actual = self.parser._extract_assertion_values(
            "assert False == True"
        )
        self.assertEqual(expected, "False")
        self.assertEqual(actual, "True")


class TestRSpecParser(unittest.TestCase):
    """Test RSpec JSON parser."""

    def setUp(self):
        self.parser = RSpecParser()

    def test_parse_rspec_json(self):
        json_content = """{
  "summary": {
    "duration": 1.23,
    "example_count": 2,
    "failure_count": 1,
    "error_count": 0
  },
  "examples": [
    {
      "description": "passes validation",
      "status": "passed",
      "file_path": "./spec/user_spec.rb",
      "line_number": 10
    },
    {
      "description": "fails validation",
      "status": "failed",
      "file_path": "./spec/user_spec.rb",
      "line_number": 15,
      "exception": {
        "class": "RSpec::Expectations::ExpectationNotMetError",
        "message": "Expected true but got false"
      }
    }
  ]
}"""

        result = self.parser.parse(json_content)

        self.assertEqual(result.total_tests, 2)
        self.assertEqual(result.passed_tests, 1)
        self.assertEqual(result.failed_tests, 1)
        self.assertEqual(result.elapsed_time, "1.23s")

        file_result = result.file_results[0]
        failed_test = next(t for t in file_result.test_results if not t.passed)
        self.assertIsNotNone(failed_test.expected)
        self.assertIsNotNone(failed_test.actual)


class TestTAPParser(unittest.TestCase):
    """Test TAP parser."""

    def setUp(self):
        self.parser = TAPParser()

    def test_parse_tap_output(self):
        tap_content = """1..3
ok 1 - test passes
not ok 2 - test fails
# Expected: true
# Actual: false
ok 3 - another test passes"""

        result = self.parser.parse(tap_content)

        self.assertEqual(result.total_tests, 3)
        self.assertEqual(result.passed_tests, 2)
        self.assertEqual(result.failed_tests, 1)

        file_result = result.file_results[0]
        self.assertEqual(len(file_result.test_results), 3)

        # Check failed test has diagnostic info
        failed_test = file_result.test_results[1]
        self.assertFalse(failed_test.passed)
        self.assertEqual(failed_test.name, "test fails")


class TestTokenBudget(unittest.TestCase):
    """Test token budget management."""

    def setUp(self):
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        from core.token_budget import TokenBudget

        self.TokenBudget = TokenBudget

    def test_token_estimation(self):
        budget = self.TokenBudget(1000)

        # Test basic estimation
        tokens = budget.estimate_tokens("hello world")
        self.assertGreater(tokens, 0)
        self.assertLess(tokens, 10)  # Should be reasonable

    def test_budget_consumption(self):
        budget = self.TokenBudget(100)

        # Consume some tokens
        consumed = budget.consume("test text")
        self.assertGreater(consumed, 0)
        self.assertLess(budget.remaining, 100)

    def test_smart_truncation(self):
        budget = self.TokenBudget(50)

        long_text = "This is a very long text that should be truncated " * 10
        truncated = budget.smart_truncate(long_text, max_tokens=10)

        self.assertLess(len(truncated), len(long_text))
        self.assertTrue(
            truncated.endswith("...") or len(truncated) < len(long_text)
        )

class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""
    
    def test_empty_input(self):
        """Test parsers handle empty input gracefully."""
        parsers = [JUnitParser(), PytestParser(), RSpecParser(), TAPParser()]
        
        for parser in parsers:
            with self.subTest(parser=parser.__class__.__name__):
                result = parser.parse("")
                self.assertIsInstance(result, type(parser.parse("")))
                self.assertEqual(result.total_tests, 0)
    
    def test_malformed_xml(self):
        """Test JUnit parser handles malformed XML."""
        parser = JUnitParser()
        
        malformed_xml = "<testsuite><testcase name='test' unclosed>"
        result = parser.parse(malformed_xml)
        
        # Should fallback to text parsing and not crash
        self.assertIsInstance(result, type(parser.parse("")))
    
    def test_unicode_handling(self):
        """Test parsers handle Unicode content."""
        parser = JUnitParser()
        
        unicode_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="UnicodeTest" tests="1" failures="1">
  <testcase name="test_unicode" classname="TestClass">
    <failure message="Unicode test: 你好世界 🚀 ñáñá">Unicode failure: émojis 🎉</failure>
  </testcase>
</testsuite>'''
        
        result = parser.parse(unicode_xml)
        self.assertEqual(result.total_tests, 1)
        self.assertEqual(result.failed_tests, 1)
    
    def test_large_numbers(self):
        """Test parsers handle large test counts."""
        parser = TAPParser()
        
        # TAP with large plan number
        large_tap = "1..999999\nok 1 - test passes"
        result = parser.parse(large_tap)
        
        # Should handle gracefully (may add error for plan mismatch)
        self.assertGreaterEqual(result.total_tests, 1)
    
    def test_path_normalization_edge_cases(self):
        """Test path normalization with various edge cases."""
        sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
        from core.encoder import TOPAEncoder
        from core.token_budget import TokenBudget
        
        encoder = TOPAEncoder('failures', TokenBudget(1000))
        
        # Test various path formats
        test_paths = [
            "",  # Empty path
            "simple.rb",  # Simple filename
            "/very/long/path/to/some/deeply/nested/test/file.rb",  # Long path
            "C:\\Windows\\Path\\test.rb",  # Windows path
            "path/with spaces/test.rb",  # Path with spaces
            "файл.rb",  # Unicode filename
        ]
        
        for path in test_paths:
            with self.subTest(path=path):
                normalized = encoder._normalize_path(path)
                self.assertIsInstance(normalized, str)
                self.assertGreater(len(normalized), 0)  # Should never return empty
    
    def test_token_budget_edge_cases(self):
        """Test token budget with edge cases."""
        sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
        from core.token_budget import TokenBudget
        
        # Zero budget
        zero_budget = TokenBudget(0)
        self.assertFalse(zero_budget.has_budget())
        self.assertEqual(zero_budget.smart_truncate("test"), "")
        
        # Very small budget
        small_budget = TokenBudget(10)
        long_text = "This is a very long text" * 100
        truncated = small_budget.smart_truncate(long_text)
        self.assertLessEqual(len(truncated), 50)  # Should be much shorter
        
        # Extremely large budget
        large_budget = TokenBudget(1_000_000)
        self.assertTrue(large_budget.has_budget())


if __name__ == "__main__":
    # Run tests
    unittest.main(verbosity=2)
