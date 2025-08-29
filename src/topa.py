#!/usr/bin/env python3
"""
TOPA - Test Output Protocol for AI
A standardized test output format designed for LLM consumption.

Usage:
  topa [OPTIONS] [INPUT_FILE]
  cat test_output.xml | topa --format junit --mode failures

Options:
  --format FORMAT    Input format: junit, tap, pytest, rspec, auto [default: auto]
  --mode MODE        Focus mode: summary, critical, failures, first-failure [default: failures]
  --limit TOKENS     Token budget limit [default: 2000]
  --version          Show version information
  --help             Show this help message

Examples:
  # Convert JUnit XML to TOPA format
  topa --format junit test-results.xml

  # Process pytest output with summary mode
  pytest | topa --format pytest --mode summary

  # First failure only with token limit
  topa --format rspec --mode first-failure --limit 1000 rspec.json
"""

import argparse
import json
import sys
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml

# Import core modules (to be created)
try:
    # from .core.schema import FileSummary, TestResult, TOPAOutput
    from .core.encoder import TOPAEncoder
    from .core.token_budget import TokenBudget
    from .parsers.base import BaseParser
    from .parsers.junit import JUnitParser
    from .parsers.pytest import PytestParser
    from .parsers.rspec import RSpecParser
    from .parsers.tap import TAPParser
except ImportError:
    # Fallback for development/standalone usage
    sys.path.insert(0, str(Path(__file__).parent))
    from core.encoder import TOPAEncoder
    from core.token_budget import TokenBudget
    from parsers.base import BaseParser
    from parsers.junit import JUnitParser
    from parsers.pytest import PytestParser
    from parsers.rspec import RSpecParser
    from parsers.tap import TAPParser

VERSION = "0.1.0"


class FocusMode(Enum):
    SUMMARY = "summary"
    CRITICAL = "critical"
    FAILURES = "failures"
    FIRST_FAILURE = "first-failure"


class InputFormat(Enum):
    AUTO = "auto"
    JUNIT = "junit"
    TAP = "tap"
    PYTEST = "pytest"
    RSPEC = "rspec"


def detect_format(content: str) -> InputFormat:
    """Auto-detect input format based on content patterns."""
    content_lower = content.lower().strip()

    # JUnit XML detection
    if content_lower.startswith("<?xml") and "<testsuite" in content_lower:
        return InputFormat.JUNIT

    # TAP detection
    if content_lower.startswith(("1..", "tap version")):
        return InputFormat.TAP

    # RSpec JSON detection
    try:
        data = json.loads(content)
        if isinstance(data, dict) and "examples" in data and "summary" in data:
            return InputFormat.RSPEC
    except json.JSONDecodeError:
        pass

    # pytest detection (common patterns)
    pytest_patterns = [
        "failed",
        "passed",
        "::test_",
        "collected",
        "assertions",
        "traceback",
        "assert ",
    ]
    if any(pattern in content_lower for pattern in pytest_patterns):
        return InputFormat.PYTEST

    # Default to pytest as most flexible fallback
    return InputFormat.PYTEST


def get_parser(format_type: InputFormat) -> BaseParser:
    """Get appropriate parser for input format."""
    parsers = {
        InputFormat.JUNIT: JUnitParser,
        InputFormat.TAP: TAPParser,
        InputFormat.PYTEST: PytestParser,
        InputFormat.RSPEC: RSpecParser,
    }

    parser_class = parsers.get(format_type, PytestParser)
    return parser_class()


def read_input(input_file: Optional[str]) -> str:
    """Read from file or stdin."""
    if input_file and input_file != "-":
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            print(f"Error: File '{input_file}' not found", file=sys.stderr)
            sys.exit(1)
        except UnicodeDecodeError:
            print(
                f"Error: Cannot decode '{input_file}' as UTF-8", file=sys.stderr
            )
            sys.exit(1)
    else:
        # Read from stdin
        return sys.stdin.read()


def main():
    parser = argparse.ArgumentParser(
        description="TOPA - Test Output Protocol for AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  topa test-results.xml                    # Auto-detect format
  pytest | topa --mode summary             # Process pytest output
  topa --format junit --mode critical results.xml
  topa --format rspec --limit 1000 rspec.json
        """,
    )

    parser.add_argument(
        "input_file",
        nargs="?",
        default="-",
        help='Input file (use "-" or omit for stdin)',
    )

    parser.add_argument(
        "--format",
        type=str,
        choices=[f.value for f in InputFormat],
        default="auto",
        help="Input format (default: auto-detect)",
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=[m.value for m in FocusMode],
        default="failures",
        help="Focus mode (default: failures)",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=2000,
        help="Token budget limit (default: 2000)",
    )

    parser.add_argument(
        "--version", action="version", version=f"TOPA {VERSION}"
    )

    args = parser.parse_args()

    try:
        # Read input
        content = read_input(args.input_file)

        if not content.strip():
            print("Error: No input provided", file=sys.stderr)
            sys.exit(1)

        # Detect format if auto
        input_format = InputFormat(args.format)
        if input_format == InputFormat.AUTO:
            input_format = detect_format(content)

        # Get appropriate parser
        test_parser = get_parser(input_format)

        # Parse test results
        try:
            parsed_results = test_parser.parse(content)
        except Exception as e:
            print(
                f"Error parsing {input_format.value} format: {e}",
                file=sys.stderr,
            )
            sys.exit(1)

        # Create encoder with specified parameters
        focus_mode = FocusMode(args.mode)
        token_budget = TokenBudget(args.limit)
        encoder = TOPAEncoder(focus_mode, token_budget)

        # Generate TOPA output
        try:
            topa_output = encoder.encode(parsed_results)

            # Output as YAML (more readable than JSON for this use case)
            yaml_output = yaml.dump(
                topa_output,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )

            print(yaml_output)

        except Exception as e:
            print(f"Error encoding TOPA output: {e}", file=sys.stderr)
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
