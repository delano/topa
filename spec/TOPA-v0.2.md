# TOPA v0.2 - Test Output Protocol for AI

## Overview

TOPA (Test Output Protocol for AI) is a standardized test output format specifically designed for LLM consumption. It addresses the token efficiency, structured parsing, and cross-tool integration needs of AI-powered development workflows.

**Key Benefits:**
- 60-80% token reduction compared to raw test output
- Structured, predictable format for reliable parsing
- Language-agnostic design for cross-framework adoption
- Progressive disclosure based on context and budget
- **NEW**: Comprehensive parser warning system integration
- **NEW**: Strict/non-strict mode support for validation workflows

## Design Principles

1. **Token Efficiency**: Minimize tokens while preserving semantic completeness
2. **Structured Data**: Consistent schema for reliable programmatic access
3. **Semantic Clarity**: Clear causality (what failed and why) with actionable context
4. **Progressive Disclosure**: Multiple detail levels based on available budget
5. **Cross-Framework**: Language and tool agnostic design
6. ****NEW** Validation Integration**: Unified handling of test failures and parser warnings

## Core Schema v0.2

### Basic Structure

```yaml
version: "0.2"
execution_details:
  framework: "direct" | "rspec" | "minitest" | string
  context_mode: "shared" | "isolated" | string
  parser: "enhanced" | "legacy" | string
  agent_mode: "focus=failures, limit=5000 tokens" | string
  strict_mode: true | false  # NEW: validation strictness

summary:
  status: PASS|FAIL|ERROR|WARNINGS
  tests:
    total: number
    passed: number
    failed: number
    errors: number
  files:
    total: number
    with_failures: number
    with_warnings: number  # NEW: warning tracking
  elapsed: "time_string"  # e.g., "1.2s", "350ms"

# NEW: Parser validation section
parser_warnings:  # Present when parser warnings exist
  - file: "relative/path/to/test_file"
    line: line_number
    type: "missing_description" | "syntax_warning" | "format_warning"
    message: "descriptive warning message"
    suggestion: "actionable fix suggestion"  # Optional

parser_errors:  # Present when validation fails in strict mode
  - file: "relative/path/to/test_file"
    line: line_number
    type: "validation_failure" | "syntax_error" | "format_error"
    message: "descriptive error message"
    suggestion: "actionable fix suggestion"  # Optional

# Present if test failures/errors exist
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

- **PASS**: All tests passed, no warnings or in non-strict mode
- **FAIL**: Some tests failed (assertion failures)
- **ERROR**: Critical errors (exceptions, syntax errors, setup failures)
- **WARNINGS**: **NEW** - Tests passed but parser warnings exist (strict mode)

### **NEW** Validation Integration

TOPA v0.2 introduces comprehensive validation support:

#### Strict Mode Operation
```yaml
version: "0.2"
execution_details:
  framework: "direct"
  context_mode: "shared"
  parser: "enhanced"
  agent_mode: "focus=failures, limit=5000 tokens"
  strict_mode: true

summary:
  status: ERROR  # Warnings become errors in strict mode
  tests: {total: 0, passed: 0, failed: 0, errors: 0}
  files: {total: 1, with_failures: 0, with_warnings: 0}
  elapsed: "45ms"

parser_errors:
  - file: "agent_friendly_warnings.try.rb"
    line: 8
    type: "missing_description"
    message: "Test case without explicit description"
    suggestion: "Add a test description using '## Description' prefix"
  - file: "agent_friendly_warnings.try.rb"
    line: 15
    type: "missing_description"
    message: "Test case without explicit description"
    suggestion: "Add a test description using '## Description' prefix"
```

#### Non-Strict Mode Operation
```yaml
version: "0.2"
execution_details:
  framework: "direct"
  context_mode: "shared"
  parser: "enhanced"
  agent_mode: "focus=failures, limit=5000 tokens"
  strict_mode: false

summary:
  status: WARNINGS
  tests: {total: 4, passed: 4, failed: 0, errors: 0}
  files: {total: 1, with_failures: 0, with_warnings: 1}
  elapsed: "78ms"

parser_warnings:
  - file: "agent_friendly_warnings.try.rb"
    line: 8
    type: "missing_description"
    message: "Test case without explicit description"
    suggestion: "Add a test description using '## Description' prefix"
  - file: "agent_friendly_warnings.try.rb"
    line: 15
    type: "missing_description"
    message: "Test case without explicit description"
    suggestion: "Add a test description using '## Description' prefix"
```

## Focus Modes

TOPA v0.2 maintains all v0.1 focus modes with validation enhancements:

### 1. Summary Mode
Shows only high-level statistics including validation status.

```yaml
version: "0.2"
execution_details:
  strict_mode: false
summary:
  status: WARNINGS
  tests: {total: 15, passed: 12, failed: 2, errors: 1}
  files: {total: 3, with_failures: 2, with_warnings: 1}
  elapsed: "1.2s"

files_with_issues:
  - file: "user_test.rb"
    test_issues: 2
  - file: "auth_test.rb"
    test_issues: 1
  - file: "validation_test.rb"
    parser_warnings: 3  # NEW: separate warning counts
```

### 2. Critical Mode
Shows only errors (exceptions) and parser errors, skipping assertion failures and warnings.

```yaml
version: "0.2"
execution_details:
  strict_mode: true
summary:
  status: ERROR
  tests: {total: 15, passed: 12, failed: 2, errors: 1}
  files: {total: 3, with_failures: 1, with_warnings: 0}
  elapsed: "1.2s"

parser_errors:  # NEW: critical parser issues
  - file: "malformed_test.rb"
    line: 1
    type: "syntax_error"
    message: "Invalid test file structure"

failures:
  - file: "auth_test.rb"
    tests:
      - line: 23
        name: "login with invalid credentials"
        type: error
        error: "NoMethodError: undefined method `authenticate' for nil"
```

### 3. Failures Mode
Shows all failures, errors, and validation issues with full detail.

### 4. First-Failure Mode
Shows only the first failure/error per file plus all parser warnings to minimize tokens.

### **NEW** 5. Validation Mode
**New focus mode** specifically for validation workflows:

```yaml
version: "0.2"
execution_details:
  framework: "direct"
  parser: "enhanced"
  agent_mode: "focus=validation, limit=3000 tokens"
  strict_mode: true

summary:
  status: WARNINGS
  validation_summary:
    parser_warnings: 5
    parser_errors: 0
    suggestions_available: 5

parser_warnings:
  - file: "test_suite.rb"
    line: 12
    type: "missing_description"
    message: "Test case without explicit description"
    suggestion: "Add a test description using '## Description' prefix"
  - file: "test_suite.rb"
    line: 28
    type: "format_warning"
    message: "Inconsistent expectation syntax"
    suggestion: "Use '#=> expected_value' format consistently"

# Test results omitted in validation focus mode
```

## **NEW** Parser Warning Types

TOPA v0.2 standardizes common parser warning categories:

### Structural Warnings
- `missing_description`: Test cases without explicit descriptions
- `empty_test_case`: Test cases with no executable code
- `incomplete_expectation`: Expectations without corresponding code

### Format Warnings
- `inconsistent_syntax`: Mixed expectation syntax patterns
- `whitespace_issues`: Formatting inconsistencies
- `comment_structure`: Malformed comment patterns

### Content Warnings
- `duplicate_test`: Duplicate test case definitions
- `unreachable_code`: Code after return statements
- `unused_variables`: Defined but unused test variables

## Token Optimization Strategies v0.2

### 1. Validation-Aware Truncation
- Parser warnings have higher priority than test failures for critical workflows
- Suggestion text is truncated intelligently while preserving actionability
- File/line references are consolidated to avoid repetition

### 2. **NEW** Smart Warning Deduplication
```yaml
# Instead of repeating identical warnings:
parser_warnings:
  - files: ["test_a.rb", "test_b.rb", "test_c.rb"]
    lines: [8, 15, 23]
    type: "missing_description"
    message: "Test case without explicit description"
    suggestion: "Add a test description using '## Description' prefix"
    count: 6  # Total occurrences across files
```

### 3. **NEW** Contextual Message Compression
```yaml
# Full format (budget permitting):
parser_warnings:
  - file: "user_validation_test.rb"
    line: 42
    type: "missing_description" 
    message: "Test case without explicit description"
    suggestion: "Add a test description using '## Description' prefix"

# Compressed format (budget constrained):
parser_warnings:
  - file: "user_validation_test.rb"
    line: 42
    type: "missing_description"
    fix: "Add ## Description prefix"
```

## Implementation Enhancements v0.2

### **NEW** Validation Pipeline Integration
```ruby
# Pseudocode for v0.2 implementation
class TOPAFormatter
  def format(test_results, parser_warnings: [], strict_mode: false)
    output = base_structure
    
    # Determine status considering validation
    output[:summary][:status] = determine_status(
      test_results, parser_warnings, strict_mode
    )
    
    # Add validation sections
    if parser_warnings.any?
      if strict_mode && warnings_block_execution?
        output[:parser_errors] = format_as_errors(parser_warnings)
      else
        output[:parser_warnings] = format_warnings(parser_warnings)
      end
    end
    
    # Apply focus mode logic with validation awareness
    apply_focus_mode(output, focus_mode)
  end
end
```

### **NEW** Strict Mode Behavior
- **Strict Mode**: Parser warnings become errors, block test execution
- **Non-Strict Mode**: Parser warnings are informational, tests execute normally
- **Exit Codes**: Strict mode uses non-zero exit codes for warnings

### **NEW** Enhanced Agent Integration
- Agent mode automatically adjusts token limits based on validation needs
- Parser warnings are given priority in token allocation
- Suggestion text is optimized for LLM consumption

## Validation Requirements v0.2

A valid TOPA v0.2 implementation must:

1. **Support Dual Validation Modes**: Both strict and non-strict operation
2. **Preserve Warning Semantics**: All parser warnings must be actionable
3. **Maintain Backward Compatibility**: v0.1 parsers should handle v0.2 gracefully
4. **Implement Smart Deduplication**: Identical warnings should be consolidated
5. **Provide Contextual Suggestions**: All warnings should include fix guidance
6. **Handle Mixed Scenarios**: Combined test failures and parser warnings

## Migration from v0.1

### Breaking Changes
- `version` field updated to `"0.2"`
- New `execution_details` section with validation context
- `status` field adds `WARNINGS` value
- `files` summary adds `with_warnings` count

### Backward Compatibility
- v0.1 consumers can ignore new validation fields
- Core test failure structure remains unchanged
- Focus modes maintain same basic behavior

## Version History

- **v0.1** (2024): Core schema, focus modes, token optimization strategies
- **v0.2** (2024): Parser warning integration, strict mode support, validation workflows

## References

- Tryouts Agent Mode Implementation: Production implementation achieving 60-80% token reduction
- Tryouts Parser Warning System: Comprehensive validation with actionable suggestions
- Language Server Protocol: Model for cross-tool standardization
- Test Anything Protocol (TAP): Precedent for test output standardization