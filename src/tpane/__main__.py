#!/usr/bin/env python3

# src/tpane/__main__.py

"""
tpane - Reference implementation of TOPA (Test Output Protocol for AI)
A standardized test output format designed for LLM consumption.

Usage:
  tpane [OPTIONS] [INPUT_FILE]
  cat test_output.xml | tpane --format junit --mode failures

Options:
  --format FORMAT    Input format: junit, tap, pytest, rspec, auto [default: auto]
  --mode MODE        Focus mode: summary, critical, failures, first-failure, all [default: failures]
  --limit TOKENS     Token budget limit [default: 5000]
  --topa-version VER TOPA version: v0.2, v0.3 [default: v0.3]
  --version          Show version information
  --help             Show this help message

Examples:
  # Convert JUnit XML to TOPA format
  tpane --format junit test-results.xml

  # Process pytest output with summary mode
  pytest | tpane --format pytest --mode summary

  # First failure only with token limit
  tpane --format rspec --mode first-failure --limit 1000 rspec.json
"""

import argparse
import json
import sys
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml

# Import core modules
from .core.encoder import TOPAEncoder
from .core.encoder_v3 import TOPAV3Encoder
from .core.schema import FocusMode as V3FocusMode
from .core.token_budget import TokenBudget
from .parsers.base import BaseParser
from .parsers.junit import JUnitParser
from .parsers.pytest import PytestParser
from .parsers.rspec import RSpecParser
from .parsers.tap import TAPParser

VERSION = "0.3.0"


class FocusMode(Enum):
    SUMMARY = "summary"
    CRITICAL = "critical"
    FAILURES = "failures"
    FIRST_FAILURE = "first-failure"
    ALL = "all"  # v0.3 addition


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
    parsers: dict[InputFormat, type[BaseParser]] = {
        InputFormat.JUNIT: JUnitParser,
        InputFormat.TAP: TAPParser,
        InputFormat.PYTEST: PytestParser,
        InputFormat.RSPEC: RSpecParser,
    }

    parser_class = parsers.get(format_type, PytestParser)
    return parser_class()


def read_input(input_file: Optional[str], max_size_mb: int = 50) -> str:
    """Read from file or stdin with size validation.

    Args:
        input_file: File path or "-" for stdin
        max_size_mb: Maximum input size in megabytes
    """
    MAX_INPUT_SIZE = max_size_mb * 1024 * 1024

    if input_file and input_file != "-":
        try:
            # Check file size before reading
            file_size = Path(input_file).stat().st_size
            if file_size > MAX_INPUT_SIZE:
                print(
                    f"Error: File '{input_file}' is too large ({file_size / (1024 * 1024):.1f}MB). "
                    f"Maximum size is {max_size_mb}MB",
                    file=sys.stderr,
                )
                sys.exit(1)

            with open(input_file, encoding="utf-8") as f:
                content = f.read()
                if len(content) > MAX_INPUT_SIZE:
                    print(
                        f"Error: File content is too large. Maximum size is {max_size_mb}MB",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                return content
        except FileNotFoundError:
            print(f"Error: File '{input_file}' not found", file=sys.stderr)
            sys.exit(1)
        except UnicodeDecodeError:
            print(f"Error: Cannot decode '{input_file}' as UTF-8", file=sys.stderr)
            sys.exit(1)
        except OSError as e:
            print(f"Error: Cannot read file '{input_file}': {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Read from stdin with size limit
        try:
            content = sys.stdin.read(MAX_INPUT_SIZE + 1)
            if len(content) > MAX_INPUT_SIZE:
                print(
                    f"Error: Input is too large. Maximum size is {max_size_mb}MB",
                    file=sys.stderr,
                )
                sys.exit(1)
            return content
        except MemoryError:
            print("Error: Input is too large to process", file=sys.stderr)
            sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="tpane - Reference implementation of TOPA (Test Output Protocol for AI)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  tpane test-results.xml                    # Auto-detect format
  pytest | tpane --mode summary             # Process pytest output
  tpane --format junit --mode critical results.xml
  tpane --format rspec --limit 1000 rspec.json
  tpane --max-input-size 100 large-file.xml  # Allow 100MB input
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
        "--topa-version",
        type=str,
        choices=["v0.2", "v0.3"],
        default="v0.3",
        help="TOPA version to output (default: v0.3)",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=5000,
        help="Token budget limit (default: 5000)",
    )

    parser.add_argument(
        "--max-input-size",
        type=int,
        default=50,
        help="Maximum input file size in MB (default: 50)",
    )

    parser.add_argument(
        "--version", action="version", version=f"tpane {VERSION} (TOPA format)"
    )

    args = parser.parse_args()

    try:
        # Read input
        content = read_input(args.input_file, args.max_input_size)

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
        
        # Choose encoder version
        if args.topa_version == "v0.3":
            # Get command from args for v0.3 context
            command = " ".join(sys.argv)
            encoder = TOPAV3Encoder(focus_mode.value, token_budget, command)
        else:
            # Legacy v0.2 encoder
            encoder = TOPAEncoder(focus_mode.value, token_budget)

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
