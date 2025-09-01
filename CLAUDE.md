# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**tpane** is the reference implementation of TOPAZ (Test Output Protocol for AI) - a standardized format for optimizing test output for LLM consumption. The tool implements **TOPAZ v0.3** by default, achieving 66% token reduction (375 → 125 tokens) with compact EXECUTION_CONTEXT headers and smart defaults. This repo contains both the tpane universal adapter and the TOPAZ specification itself.

**Current Implementation Status**:
- ✅ **TOPAZ v0.3** with ExecutionContext class and compact format (66% token reduction)
- ✅ **Cross-language normalization** via environment/flag mappings
- ✅ **Environment detection** (runtime, VCS, package manager, project type)
- ✅ **Dual encoder support**: TOPAZV3Encoder (default) and TOPAZEncoder (legacy)
- ✅ **Enhanced CLI**: `--topaz-version v0.3|v0.2`, `--mode all` support
- ✅ **Updated defaults**: 5000 token limit, v0.3 format

**Architecture**:
- Based on tryouts Ruby library validation and real-world usage patterns
- Universal adapter serving as stopgap until frameworks support TOPAZ natively

## Development Commands

### Setup and Installation
```bash
# Install in development mode with all dependencies
pip install -e ".[dev]"

# Verify installation
python src/tpane.py --help
```

### Code Quality and Linting
```bash
# Lint and format code (primary command)
ruff check && ruff format && mypy src/

# Individual commands
ruff check                    # Check for linting issues
ruff check --fix             # Auto-fix issues where possible
ruff format                   # Format code
mypy src/                     # Type checking for source code
mypy tests/                   # Type checking for tests
```

### Testing
```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov

# Run tests with verbose output
pytest -v

# Run specific test file
pytest tests/test_parsers.py

# Run tests matching a pattern
pytest -k "test_pattern"
```

### Running the Tool
```bash
# Basic usage (TOPAZ v0.3 default)
python src/tpane.py test_output.txt

# With specific format and mode
python src/tpane.py --format junit --mode failures test-results.xml

# From stdin
pytest | python src/tpane.py --format pytest --mode summary

# With token limit (default: 5000)
python src/tpane.py --limit 1000 large_test_output.xml

# TOPAZ version control
python src/tpane.py --topaz-version v0.3 test_output.txt  # default
python src/tpane.py --topaz-version v0.2 test_output.txt  # legacy

# New focus modes
python src/tpane.py --mode all comprehensive_output.xml
```

## Architecture Overview

### Core Architecture Pattern
The project follows a **Parser-Encoder-Schema** pattern:

- **Parsers** (`src/tpane/parsers/`): Convert various test formats (JUnit, pytest, TAP, RSpec) into standardized internal representation
- **Core Engine** (`src/tpane/core/`): Handles token budgeting, TOPAZ encoding, and schema definitions
- **Schema** (`src/tpane/core/schema.py`): Defines the data structures for both parsed input and TOPAZ output

### Key Components

**Main Entry Point**: `src/tpane/__main__.py`
- Command-line interface and argument parsing
- Format auto-detection logic
- Orchestrates parsing and encoding pipeline

**Base Parser**: `src/tpane/parsers/base.py`
- Abstract base class for all format parsers
- Common utilities: line number extraction, test name normalization, time parsing
- Provides consistent interface for different test formats

**Schema System**: `src/tpane/core/schema.py`
- `ParsedTestData` and `ParsedFileResult`: Internal representation after parsing
- `TOPAZOutput` and related classes: Final TOPAZ format structure
- Enum types for test status and focus modes

### Parser Architecture
Each parser inherits from `BaseParser` and implements:
- `parse(content: str) -> ParsedTestData`: Main parsing logic
- Format-specific pattern matching and data extraction
- Utilizes base class utilities for common operations

### Supported Formats
- **JUnit XML**: `<testsuite>` and `<testcase>` elements
- **pytest**: Text output with assertion failures and tracebacks
- **TAP (Test Anything Protocol)**: `1..N` format with ok/not ok results
- **RSpec JSON**: JSON format with examples and summary

## Development Standards

### Code Quality Requirements
- **Line length**: 88 characters (configured in pyproject.toml)
- **Type hints**: Required for all public functions using Python 3.9+ syntax
- **Testing**: Aim for >80% coverage, use pytest framework
- **Linting**: Must pass `ruff check && ruff format && mypy src/`

### Project Structure
```
src/tpane/
├── __init__.py           # Package initialization and exports
├── __main__.py           # CLI interface with v0.3 support
├── core/                 # Core engine components
│   ├── encoder.py        # Legacy TOPAZ v0.2 encoder
│   ├── encoder_v3.py     # TOPAZ v0.3 encoder with execution context
│   ├── schema.py         # Data structures for both v0.2 and v0.3
│   └── token_budget.py   # Token management and optimization
└── parsers/              # Test format parsers
    ├── base.py          # Abstract base parser with utilities
    ├── junit.py         # JUnit XML parser
    ├── pytest.py        # pytest output parser
    ├── rspec.py         # RSpec JSON parser
    └── tap.py           # TAP format parser
```

### TOPAZ Standard Implementation
The tool implements TOPAZ v0.3 specification with tryouts-inspired design:
- **Token efficiency**: 66% reduction (375 → 125 tokens) with compact format
- **Execution context**: Environment details for debugging (command, runtime, VCS, etc.)
- **Focus modes**: summary, critical, failures, first-failure, all
- **Cross-language normalization**: Consistent fields across Python, Ruby, JavaScript, Java
- **Smart defaults**: Only shows non-standard configurations
- **Progressive disclosure**: Scales from 50 tokens (summary) to 500+ (comprehensive)

## Testing Strategy

Tests are located in `tests/test_parsers.py` and cover:
- Parser functionality for each supported format
- Edge cases and malformed input handling
- Token budgeting and encoding logic
- CLI interface and argument parsing

### Running Specific Tests
```bash
# Test specific parser
pytest tests/test_parsers.py::TestJUnitParser

# Test with verbose output for debugging
pytest -v tests/test_parsers.py::TestJUnitParser::test_parse_simple_xml
```

## Contributing Workflow

Before submitting changes:

1. **Code quality**: `ruff check && ruff format && mypy src/`
2. **Tests**: `pytest --cov` (maintain >80% coverage)
3. **Functionality**: Test with various input formats from `examples/`

The project enforces strict typing with mypy and comprehensive linting with ruff to maintain code quality.

## TOPAZ v0.3 Philosophy and Implementation Notes

### Design Philosophy
TOPAZ v0.3 represents "codified best practices" for AI-optimized test output based on real-world usage in the Ruby tryouts library. Key principles:

- **What to exclude matters**: Some data (like timestamps) can confuse LLM interpretation when test suites simulate time
- **Upfront context prevents circular debugging**: Include environment, versions, and flags that commonly cause issues
- **Token efficiency enables scale**: At 125 tokens per test run, even 10 runs only use 1250 tokens
- **Progressive disclosure**: Focus modes scale from 50 tokens (summary) to 500+ (comprehensive)

### Real-World Validation
The v0.3 format is validated by the tryouts Ruby library's `--agent` mode, which provides:
- Compact EXECUTION_CONTEXT with essential debugging info
- 66% token reduction while preserving semantic completeness
- Cross-language applicability (Ruby \u2192 Python \u2192 JavaScript \u2192 Java)

### Implementation Strategy
- **Universal Adapter**: tpane serves as stopgap until test frameworks support TOPAZ natively
- **Dual Version Support**: v0.3 default with v0.2 backward compatibility
- **Environment Detection**: Automatic runtime, VCS, package manager detection
- **Cross-Language Normalization**: Consistent field names across frameworks
- This repo is home for both thee tpane reference implementation and TOPAZ the sepcification itself.
