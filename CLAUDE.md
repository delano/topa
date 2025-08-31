# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**tpane** is the reference implementation of TOPA (Test Output Protocol for AI) - a standardized format for optimizing test output for LLM consumption. The tool achieves 60-80% token reduction while maintaining semantic completeness for AI analysis.

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
# Basic usage
python src/tpane.py test_output.txt

# With specific format and mode
python src/tpane.py --format junit --mode failures test-results.xml

# From stdin
pytest | python src/tpane.py --format pytest --mode summary

# With token limit
python src/tpane.py --limit 1000 large_test_output.xml
```

## Architecture Overview

### Core Architecture Pattern
The project follows a **Parser-Encoder-Schema** pattern:

- **Parsers** (`src/tpane/parsers/`): Convert various test formats (JUnit, pytest, TAP, RSpec) into standardized internal representation
- **Core Engine** (`src/tpane/core/`): Handles token budgeting, TOPA encoding, and schema definitions
- **Schema** (`src/tpane/core/schema.py`): Defines the data structures for both parsed input and TOPA output

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
- `TOPAOutput` and related classes: Final TOPA format structure
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
├── __main__.py           # CLI interface and main orchestration
├── core/                 # Core engine components
│   ├── encoder.py        # TOPA format encoding
│   ├── schema.py         # Data structure definitions
│   └── token_budget.py   # Token management and optimization
└── parsers/              # Test format parsers
    ├── base.py          # Abstract base parser with utilities
    ├── junit.py         # JUnit XML parser
    ├── pytest.py        # pytest output parser
    ├── rspec.py         # RSpec JSON parser
    └── tap.py           # TAP format parser
```

### TOPA Standard Implementation
The tool implements the evolving TOPA specification (currently v0.3 proposal in `spec/`):
- **Token efficiency**: 60-80% reduction compared to raw test output
- **Focus modes**: summary, critical, failures, first-failure
- **Progressive disclosure**: Adjusts detail level based on token budget
- **Cross-language support**: Framework-agnostic design

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
- This repo is home for both thee tpane reference implementation and TOPA the sepcification itself.
