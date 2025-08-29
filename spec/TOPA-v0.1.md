# TOPA v0.1 - Test Output Protocol for AI

## Overview

TOPA (Test Output Protocol for AI) is a standardized test output format specifically designed for LLM consumption. It addresses the token efficiency, structured parsing, and cross-tool integration needs of AI-powered development workflows.

**Key Benefits:**
- 60-80% token reduction compared to raw test output
- Structured, predictable format for reliable parsing
- Language-agnostic design for cross-framework adoption
- Progressive disclosure based on context and budget

## Design Principles

1. **Token Efficiency**: Minimize tokens while preserving semantic completeness
2. **Structured Data**: Consistent schema for reliable programmatic access
3. **Semantic Clarity**: Clear causality (what failed and why) with actionable context
4. **Progressive Disclosure**: Multiple detail levels based on available budget
5. **Cross-Framework**: Language and tool agnostic design

## Core Schema

### Basic Structure

```yaml
version: "0.1"
summary:
  status: PASS|FAIL|ERROR
  tests:
    total: number
    passed: number
    failed: number
    errors: number
  files:
    total: number
    with_failures: number
  elapsed: "time_string"  # e.g., "1.2s", "350ms"

# Only present if failures/errors exist
failures:
  - file: "relative/path/to/test_file"
    tests:
      - line: line_number
        name: "test description"
        type: "failure" | "error"
        expected: "expected_value"  # For assertion failures
        actual: "actual_value"      # For assertion failures
        error: "error_message"      # For exceptions/errors
        diff: "diff_content"        # Optional, budget-aware
```

### Status Values

- **PASS**: All tests passed
- **FAIL**: Some tests failed (assertion failures)
- **ERROR**: Critical errors (exceptions, syntax errors, setup failures)

### File Path Normalization

- Use relative paths from project root
- Remove common prefixes to save tokens
- Fall back to basename if relative path is complex
- Example: `try/formatters/agent_formatter_try.rb` instead of full path

### Time Format

- Sub-millisecond: `"250¼s"`
- Milliseconds: `"1.2s"`, `"350ms"`
- Seconds: `"1.2s"`, `"45.6s"`

## Focus Modes

TOPA supports different levels of detail based on context needs:

### 1. Summary Mode
Shows only high-level statistics and file-level issue counts.

```yaml
version: "0.1"
summary:
  status: FAIL
  tests: {total: 15, passed: 12, failed: 2, errors: 1}
  files: {total: 3, with_failures: 2}
  elapsed: "1.2s"

files_with_issues:
  - file: "user_test.rb"
    issues: 2
  - file: "auth_test.rb"
    issues: 1
```

### 2. Critical Mode
Shows only errors (exceptions), skipping assertion failures.

```yaml
version: "0.1"
summary:
  status: ERROR
  tests: {total: 15, passed: 12, failed: 2, errors: 1}
  files: {total: 3, with_failures: 1}
  elapsed: "1.2s"

failures:
  - file: "auth_test.rb"
    tests:
      - line: 23
        name: "login with invalid credentials"
        type: error
        error: "NoMethodError: undefined method `authenticate' for nil"
```

### 3. Failures Mode
Shows all failures and errors with full detail.

```yaml
version: "0.1"
summary:
  status: FAIL
  tests: {total: 15, passed: 12, failed: 2, errors: 1}
  files: {total: 3, with_failures: 2}
  elapsed: "1.2s"

failures:
  - file: "user_test.rb"
    tests:
      - line: 45
        name: "validates email format"
        type: failure
        expected: "true"
        actual: "false"
      - line: 52
        name: "requires strong password"
        type: failure
        expected: "minimum 8 characters"
        actual: "got 6 characters"

  - file: "auth_test.rb"
    tests:
      - line: 23
        name: "login with invalid credentials"
        type: error
        error: "NoMethodError: undefined method `authenticate' for nil"
```

### 4. First-Failure Mode
Shows only the first failure/error per file to minimize tokens.

```yaml
version: "0.1"
summary:
  status: FAIL
  tests: {total: 15, passed: 12, failed: 2, errors: 1}
  files: {total: 3, with_failures: 2}
  elapsed: "1.2s"

failures:
  - file: "user_test.rb"
    tests:
      - line: 45
        name: "validates email format"
        type: failure
        expected: "true"
        actual: "false"
    truncated: 1  # Additional failures not shown

  - file: "auth_test.rb"
    tests:
      - line: 23
        name: "login with invalid credentials"
        type: error
        error: "NoMethodError: undefined method `authenticate' for nil"
```

## Token Optimization Strategies

### 1. Hierarchical Organization
- Group failures by file to avoid repeating file paths
- Use consistent indentation and structure
- Eliminate redundant information

### 2. Smart Truncation
- Truncate long values while preserving key information
- Show meaningful prefixes/suffixes
- Indicate truncation clearly: `"very long string..."  "very long st..."`

### 3. Relative Path Optimization
```ruby
# Instead of: /Users/dev/project/spec/models/user_spec.rb
# Use:        spec/models/user_spec.rb
# Or:         user_spec.rb (if deeply nested)
```

### 4. Diff Generation (Budget Permitting)
Only include diffs when token budget allows:

```yaml
- line: 34
  name: "calculates total"
  type: failure
  expected: "42"
  actual: "24"
  diff: |
    - 24
    + 42
```

### 5. Progressive Disclosure Levels

**Level 1 (Minimal)**: Status + counts only
**Level 2 (Summary)**: + File-level issue counts
**Level 3 (Critical)**: + Error details only
**Level 4 (Standard)**: + All failure details
**Level 5 (Verbose)**: + Diffs and extended context

## Source Format Support

TOPA parsers should support these common test output formats:

### JUnit XML
```xml
<testsuite tests="3" failures="1" errors="0">
  <testcase classname="UserTest" name="validates email"/>
  <testcase classname="UserTest" name="requires password">
    <failure message="Expected true but was false"/>
  </testcase>
</testsuite>
```

### TAP (Test Anything Protocol)
```
1..3
ok 1 validates email
not ok 2 requires password
# Expected: true
# Actual: false
ok 3 saves user
```

### pytest Output
```
FAILED test_user.py::test_password - assert False
FAILED test_auth.py::test_login - AttributeError: 'NoneType'
```

### RSpec JSON
```json
{
  "summary": {"example_count": 3, "failure_count": 1},
  "examples": [
    {
      "description": "validates email",
      "status": "passed"
    },
    {
      "description": "requires password",
      "status": "failed",
      "exception": {"message": "Expected true but was false"}
    }
  ]
}
```

## Implementation Notes

### Token Budget Management
- Implement configurable token limits (default: 2000 tokens)
- Priority order: Summary  Errors  First failures  All failures  Diffs
- Use exponential backoff for truncation decisions

### Error Handling
- Gracefully handle malformed input
- Provide meaningful error messages
- Fall back to basic text parsing when structured parsing fails

### Performance Requirements
- Sub-second processing for typical test suites (<1000 tests)
- Memory efficient streaming for large test outputs
- Minimal dependencies for easy integration

## Validation Requirements

A valid TOPA implementation must:

1. **Preserve Semantic Completeness**: All failure information from source must be representable
2. **Achieve Token Efficiency**: 60-80% reduction vs. raw output for typical test suites
3. **Maintain Consistency**: Same input should produce identical output across runs
4. **Handle Edge Cases**: Empty results, malformed input, very large outputs
5. **Support Progressive Disclosure**: All focus modes must be implemented

## Version History

- **v0.1** (Initial): Core schema, focus modes, token optimization strategies

## References

- Tryouts Agent Mode Implementation: Proof of concept achieving 60-80% token reduction
- Language Server Protocol: Model for cross-tool standardization
- Test Anything Protocol (TAP): Precedent for test output standardization
