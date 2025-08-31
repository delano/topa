"""
TOPA v0.3 Encoder

Converts parsed test data into TOPA v0.3 format with execution context and
optimized token usage following the v0.3 specification.
"""

import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from .schema import (
    PROJECT_DETECTION_PATTERNS,
    ExecutionContext,
    FocusMode,
    ParsedTestData,
    ProjectType,
    TOPAV3Output,
    V3FailureResult,
    normalize_environment_variables,
    normalize_flags,
)
from .token_budget import TokenBudget


class TOPAV3Encoder:
    """Encodes parsed test data into TOPA v0.3 format with execution context."""

    VERSION = "0.3"

    def __init__(
        self,
        focus_mode: str = FocusMode.FAILURES.value,
        token_budget: Optional[TokenBudget] = None,
        command: Optional[str] = None,
    ):
        self.focus_mode = FocusMode(focus_mode)
        self.budget = token_budget or TokenBudget(5000)  # v0.3 default
        self.command = command or self._detect_command()

    def encode(self, parsed_data: ParsedTestData) -> dict[str, Any]:
        """Convert parsed test data to TOPA v0.3 format."""

        # Build execution context
        execution_context = self._build_execution_context(parsed_data)

        # Create v0.3 output
        v3_output = TOPAV3Output(
            execution_context=execution_context, focus_mode=self.focus_mode
        )

        # Add content based on focus mode
        if self.focus_mode == FocusMode.SUMMARY:
            v3_output.summary_line = self._build_summary_line(parsed_data)
            v3_output.file_issues = self._build_file_issues(parsed_data)
        else:
            # failures, critical, first-failure, all modes
            v3_output.failures = self._build_failures(parsed_data)

        return v3_output.to_dict()

    def _build_execution_context(self, parsed_data: ParsedTestData) -> ExecutionContext:
        """Build the TOPA v0.3 execution context."""

        # Required fields
        pid = os.getpid()
        pwd = str(Path.cwd())
        runtime = self._detect_runtime()
        test_framework = self._detect_test_framework()
        protocol = f"TOPA v{self.VERSION} | focus: {self.focus_mode.value} | limit: {self.budget.limit}"

        # Optional fields
        package_manager = self._detect_package_manager()
        vcs_info = self._detect_vcs_info()
        environment = self._detect_environment()
        flags = self._detect_flags()
        project_type = self._detect_project_type()

        return ExecutionContext(
            command=self.command,
            pid=pid,
            pwd=pwd,
            runtime=runtime,
            test_framework=test_framework,
            files_under_test=parsed_data.total_files,
            protocol=protocol,
            package_manager=package_manager,
            vcs=vcs_info,
            environment=environment,
            flags=flags,
            project_type=project_type,
        )

    def _build_summary_line(self, parsed_data: ParsedTestData) -> str:
        """Build the compact summary line for summary mode."""
        passed = parsed_data.passed_tests
        failed = parsed_data.failed_tests
        errors = parsed_data.error_tests
        files = parsed_data.total_files

        parts = [f"{passed} passed"]
        if failed > 0:
            parts.append(f"{failed} failed")
        if errors > 0:
            parts.append(f"{errors} errors")

        result = ", ".join(parts)
        result += f" in {files} files"

        return result

    def _build_file_issues(self, parsed_data: ParsedTestData) -> dict[str, str]:
        """Build file-level issue counts for summary mode."""
        file_issues = {}

        for file_result in parsed_data.file_results:
            if file_result.has_issues():
                failed = file_result.failure_count()
                errors = file_result.error_count()

                issue_parts = []
                if failed > 0:
                    issue_parts.append(f"{failed} failed")
                if errors > 0:
                    issue_parts.append(f"{errors} errors")

                issue_str = ", ".join(issue_parts)
                normalized_path = self._normalize_path(file_result.file_path)
                file_issues[normalized_path] = issue_str

                # Token budget check
                if not self.budget.has_budget():
                    break

        return file_issues

    def _build_failures(
        self, parsed_data: ParsedTestData
    ) -> dict[str, list[V3FailureResult]]:
        """Build failure details for non-summary modes."""
        failures = {}

        for file_result in parsed_data.file_results:
            failed_tests = [t for t in file_result.test_results if not t.passed]

            if not failed_tests:
                continue

            # Filter based on focus mode
            if self.focus_mode == FocusMode.CRITICAL:
                # Only errors/exceptions
                failed_tests = [t for t in failed_tests if t.is_error]
            elif self.focus_mode == FocusMode.FIRST_FAILURE:
                # Only first failure per file
                failed_tests = failed_tests[:1]

            if not failed_tests:
                continue

            v3_failures = []
            for test in failed_tests:
                # Extract failure description
                if test.is_error:
                    description = "error occurred"
                else:
                    description = "test failed"

                v3_failure = V3FailureResult(
                    line=test.line or 0,
                    description=description,
                    test_name=test.name,
                    expected=test.expected,
                    actual=test.actual,
                )

                v3_failures.append(v3_failure)

                # Token budget check
                if not self.budget.has_budget():
                    break

            if v3_failures:
                normalized_path = self._normalize_path(file_result.file_path)
                failures[normalized_path] = v3_failures

            # Token budget check
            if not self.budget.has_budget():
                break

        return failures

    def _detect_command(self) -> str:
        """Detect the command that was executed."""
        # Try to get from command line args
        if len(sys.argv) > 0:
            return " ".join(sys.argv)
        return "unknown"

    def _detect_runtime(self) -> str:
        """Detect runtime information: language version (platform)."""
        # Python version and platform
        version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        system = platform.system().lower()
        machine = platform.machine().lower()

        # Normalize platform names
        if system == "darwin":
            platform_name = f"darwin-{machine}"
        elif system == "windows":
            platform_name = "win64" if machine == "amd64" else "win32"
        else:
            platform_name = f"{system}-{machine}"

        return f"python {version} ({platform_name})"

    def _detect_test_framework(self) -> str:
        """Detect test framework and isolation mode."""
        # For tpane, we're processing output from various frameworks
        # Default to framework agnostic since we're a universal adapter
        return "tpane (isolated)"

    def _detect_package_manager(self) -> Optional[str]:
        """Detect package manager and version."""
        try:
            # Try pip first (most common for Python)
            result = subprocess.run(
                ["pip", "--version"], capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                # Parse "pip 23.0.1 from ..."
                version_line = result.stdout.strip()
                if "pip" in version_line:
                    parts = version_line.split()
                    if len(parts) >= 2:
                        return f"pip {parts[1]}"
        except (
            subprocess.TimeoutExpired,
            subprocess.SubprocessError,
            FileNotFoundError,
        ):
            pass

        # Could add conda, poetry, pipenv detection here
        return None

    def _detect_vcs_info(self) -> Optional[str]:
        """Detect version control system info."""
        try:
            # Try git
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=2,
            )

            if branch_result.returncode == 0:
                branch = branch_result.stdout.strip()

                # Get short commit hash
                commit_result = subprocess.run(
                    ["git", "rev-parse", "--short", "HEAD"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )

                if commit_result.returncode == 0:
                    commit = commit_result.stdout.strip()
                    return f"git {branch}@{commit}"
                else:
                    return f"git {branch}"

        except (
            subprocess.TimeoutExpired,
            subprocess.SubprocessError,
            FileNotFoundError,
        ):
            pass

        return None

    def _detect_environment(self) -> Optional[dict[str, str]]:
        """Detect relevant environment variables."""
        env_vars = dict(os.environ)
        normalized = normalize_environment_variables(env_vars)

        # Only return if we found something
        return normalized if normalized else None

    def _detect_flags(self) -> Optional[list[str]]:
        """Detect and normalize command-line flags."""
        # Extract flags from command
        if not self.command:
            return None

        # Simple flag detection - look for - and -- patterns
        words = self.command.split()
        raw_flags = [word for word in words if word.startswith("-")]

        if not raw_flags:
            return None

        normalized = normalize_flags(raw_flags)
        return normalized if normalized else None

    def _detect_project_type(self) -> Optional[ProjectType]:
        """Detect project type based on file patterns."""
        current_dir = Path.cwd()

        # Check each pattern
        for project_type, patterns in PROJECT_DETECTION_PATTERNS.items():
            for pattern in patterns:
                if "*" in pattern:
                    # Glob pattern
                    if list(current_dir.glob(pattern)):
                        return project_type
                else:
                    # Direct file check
                    if (current_dir / pattern).exists():
                        return project_type

        return ProjectType.GENERIC

    def _normalize_path(self, file_path: str) -> str:
        """Normalize file path for token efficiency."""
        if not file_path:
            return "unknown"

        try:
            path = Path(file_path)

            # Security check for malicious paths
            path_str = str(path)
            suspicious_patterns = [
                "../",
                "..\\",
                "/etc/",
                "/proc/",
                "/sys/",
                "C:\\Windows",
                "C:\\System32",
            ]

            if any(pattern in path_str for pattern in suspicious_patterns):
                return path.name or "unknown"

            # Prefer relative paths if shorter
            if not path.is_absolute() and len(path_str) < 50:
                return path_str

            # Try to make relative to current directory
            try:
                rel_path = path.relative_to(Path.cwd())
                if len(str(rel_path)) < len(file_path):
                    return str(rel_path)
            except ValueError:
                pass

            # If still long, use last few meaningful parts
            parts = path.parts
            if len(parts) > 3:
                return "/".join(parts[-2:])

            # Truncate if too long
            if len(str(path)) > 60:
                return path.name

            return str(path)

        except Exception:
            try:
                return Path(file_path).name
            except Exception:
                return "unknown"
