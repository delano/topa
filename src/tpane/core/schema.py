"""
TOPAZ Schema Definitions

Data structures representing the standardized TOPAZ format.
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Optional


class TestStatus(Enum):
    """Overall test run status."""

    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"


class TestType(Enum):
    """Individual test result type."""

    FAILURE = "failure"
    ERROR = "error"


class FocusMode(Enum):
    """TOPAZ v0.3 focus modes for progressive disclosure."""

    SUMMARY = "summary"
    CRITICAL = "critical"
    FAILURES = "failures"
    FIRST_FAILURE = "first-failure"
    ALL = "all"


class ProjectType(Enum):
    """Auto-detected project types."""

    RAILS = "rails"
    DJANGO = "django"
    NODE_PACKAGE = "node_package"
    PYTHON_PACKAGE = "python_package"
    JAVA_MAVEN = "java_maven"
    JAVA_GRADLE = "java_gradle"
    DOTNET = "dotnet"
    GO_MODULE = "go_module"
    RUST_CRATE = "rust_crate"
    GENERIC = "generic"


# Cross-language field normalization mappings from TOPAZ v0.3 spec
ENVIRONMENT_MAPPINGS: dict[str, list[str]] = {
    "CI": ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL", "TRAVIS", "CIRCLECI"],
    "ENV": ["RAILS_ENV", "NODE_ENV", "APP_ENV", "DJANGO_SETTINGS_MODULE", "FLASK_ENV"],
    "COV": ["COVERAGE", "SIMPLECOV", "PYTEST_COV", "NYC_CONFIG"],
    "SEED": ["SEED", "RANDOM_SEED", "TEST_SEED"],
}

FLAG_MAPPINGS: dict[str, list[str]] = {
    "verbose": ["-v", "--verbose", "-verbose"],
    "debug": ["-d", "--debug", "-debug", "DEBUG=1"],
    "parallel": ["-j", "--parallel", "-n", "-parallel"],
    "fails-only": ["-f", "--failed-only", "--failed", "-fails"],
    "strict": ["--strict", "-W error", "-strict"],
    "quiet": ["-q", "--quiet", "-quiet"],
    "traces": ["-s", "--tb=long", "--traceback", "-traces"],
}

PROJECT_DETECTION_PATTERNS: dict[ProjectType, list[str]] = {
    ProjectType.RAILS: ["config/application.rb", "Gemfile", "config/routes.rb"],
    ProjectType.DJANGO: ["manage.py", "settings.py", "wsgi.py"],
    ProjectType.NODE_PACKAGE: ["package.json", "node_modules"],
    ProjectType.PYTHON_PACKAGE: ["setup.py", "pyproject.toml", "requirements.txt"],
    ProjectType.JAVA_MAVEN: ["pom.xml"],
    ProjectType.JAVA_GRADLE: ["build.gradle", "build.gradle.kts"],
    ProjectType.DOTNET: ["*.csproj", "*.sln", "*.fsproj"],
    ProjectType.GO_MODULE: ["go.mod", "go.sum"],
    ProjectType.RUST_CRATE: ["Cargo.toml", "Cargo.lock"],
}


def normalize_environment_variables(env_dict: dict[str, str]) -> dict[str, str]:
    """Normalize environment variables to TOPAZ standard keys."""
    normalized = {}

    for topa_key, possible_keys in ENVIRONMENT_MAPPINGS.items():
        for env_key in possible_keys:
            if env_key in env_dict:
                # Use the first match found
                normalized[topa_key] = env_dict[env_key]
                break

    return normalized


def normalize_flags(flags: list[str]) -> list[str]:
    """Normalize command-line flags to TOPAZ standard terms."""
    normalized = set()

    for flag in flags:
        for topa_flag, possible_flags in FLAG_MAPPINGS.items():
            if flag in possible_flags:
                normalized.add(topa_flag)
                break

    return sorted(normalized)


@dataclass
class TestCounts:
    """Test execution statistics."""

    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass
class FileCounts:
    """File-level statistics."""

    total: int = 0
    with_failures: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass
class TestResult:
    """Individual test failure or error."""

    line: int
    name: str
    type: TestType
    expected: Optional[str] = None
    actual: Optional[str] = None
    error: Optional[str] = None
    diff: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result = {"line": self.line, "name": self.name, "type": self.type.value}

        if self.expected is not None:
            result["expected"] = self.expected
        if self.actual is not None:
            result["actual"] = self.actual
        if self.error is not None:
            result["error"] = self.error
        if self.diff is not None:
            result["diff"] = self.diff

        return result


@dataclass
class FileSummary:
    """File-level test results summary."""

    file: str
    tests: list[TestResult] = field(default_factory=list)
    truncated: Optional[int] = None  # Number of additional failures not shown

    def has_failures(self) -> bool:
        """Check if file has any failures or errors."""
        return len(self.tests) > 0

    def failure_count(self) -> int:
        """Count assertion failures."""
        return sum(1 for t in self.tests if t.type == TestType.FAILURE)

    def error_count(self) -> int:
        """Count errors/exceptions."""
        return sum(1 for t in self.tests if t.type == TestType.ERROR)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        result: dict[str, Any] = {
            "file": self.file,
            "tests": [test.to_dict() for test in self.tests],
        }

        if self.truncated is not None:
            result["truncated"] = self.truncated

        return result


@dataclass
class Summary:
    """High-level test run summary."""

    status: TestStatus
    tests: TestCounts
    files: FileCounts
    elapsed: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        result = {
            "status": self.status.value,
            "tests": self.tests.to_dict(),
            "files": self.files.to_dict(),
        }

        if self.elapsed is not None:
            result["elapsed"] = self.elapsed

        return result


@dataclass
class FileIssues:
    """Simple file-level issue count (for summary mode)."""

    file: str
    issues: int

    def to_dict(self) -> dict[str, Any]:
        return {"file": self.file, "issues": self.issues}


@dataclass
class ExecutionContext:
    """TOPAZ v0.3 execution context with compact field formats."""

    command: str
    pid: int
    pwd: str
    runtime: str  # "language version (platform)"
    test_framework: str  # "name (isolation_mode)"
    files_under_test: int
    protocol: str  # "TOPAZ v0.3 | focus: mode | limit: tokens"
    package_manager: Optional[str] = None  # "name version"
    vcs: Optional[str] = None  # "system branch@commit"
    environment: Optional[dict[str, str]] = None  # Non-default env vars only
    flags: Optional[list[str]] = None  # Normalized execution flags
    project_type: Optional[ProjectType] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to v0.3 compact format."""
        result: dict[str, Any] = {
            "command": self.command,
            "pid": f"{self.pid} | pwd: {self.pwd}",
            "runtime": self.runtime,
            "test_framework": self.test_framework,
            "protocol": self.protocol,
            "files_under_test": self.files_under_test,
        }

        if self.package_manager:
            result["package_manager"] = self.package_manager

        if self.vcs:
            result["vcs"] = self.vcs

        if self.environment:
            env_pairs = [f"{k}={v}" for k, v in self.environment.items()]
            result["environment"] = ", ".join(env_pairs)

        if self.flags:
            result["flags"] = ", ".join(self.flags)

        if self.project_type:
            result["project_type"] = self.project_type.value

        return result


@dataclass
class V3FailureResult:
    """TOPAZ v0.3 compact failure result."""

    line: int
    description: str
    test_name: str
    expected: Optional[str] = None
    actual: Optional[str] = None
    diff_removed: Optional[str] = None
    diff_added: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to v0.3 format."""
        result: dict[str, Any] = {
            f"L{self.line}": self.description,
            "Test": self.test_name,
        }

        if self.expected is not None:
            result["Expected"] = self.expected
        if self.actual is not None:
            result["Got"] = self.actual
        if self.diff_removed or self.diff_added:
            diff_lines = []
            if self.diff_removed:
                diff_lines.append(f"- {self.diff_removed}")
            if self.diff_added:
                diff_lines.append(f"+ {self.diff_added}")
            result["Diff"] = diff_lines

        return result


@dataclass
class TOPAZOutput:
    """Complete TOPAZ format output."""

    version: str
    summary: Summary
    failures: Optional[list[FileSummary]] = None
    files_with_issues: Optional[list[FileIssues]] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format for serialization."""
        result: dict[str, Any] = {
            "version": self.version,
            "summary": self.summary.to_dict(),
        }

        if self.failures is not None:
            result["failures"] = [f.to_dict() for f in self.failures]

        if self.files_with_issues is not None:
            result["files_with_issues"] = [f.to_dict() for f in self.files_with_issues]

        return result


@dataclass
class TOPAZV3Output:
    """TOPAZ v0.3 format output with execution context."""

    execution_context: ExecutionContext
    focus_mode: FocusMode
    # For summary mode
    summary_line: Optional[str] = None  # "X passed, Y failed in Z files"
    file_issues: Optional[dict[str, str]] = None  # {"file.py": "2 failed"}

    # For failures/critical modes
    failures: Optional[dict[str, list[V3FailureResult]]] = (
        None  # {"file.py": [failures]}
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to v0.3 format for serialization."""
        result: dict[str, Any] = {"EXECUTION_CONTEXT": self.execution_context.to_dict()}

        if self.focus_mode == FocusMode.SUMMARY:
            if self.summary_line:
                result["Summary"] = self.summary_line
            if self.file_issues:
                result["Files"] = self.file_issues
        else:
            # failures, critical, first-failure, all modes
            if self.failures:
                for file_path, file_failures in self.failures.items():
                    result[file_path] = [f.to_dict() for f in file_failures]

        return result


# Parsed test data from input (before TOPAZ encoding)
@dataclass
class ParsedTestData:
    """Raw test data parsed from various input formats."""

    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    error_tests: int = 0
    total_files: int = 0
    elapsed_time: Optional[str] = None
    file_results: list["ParsedFileResult"] = field(default_factory=list)

    @property
    def overall_status(self) -> TestStatus:
        """Determine overall status based on results."""
        if self.error_tests > 0:
            return TestStatus.ERROR
        elif self.failed_tests > 0:
            return TestStatus.FAIL
        else:
            return TestStatus.PASS

    @property
    def files_with_failures(self) -> int:
        """Count files that have failures or errors."""
        return sum(1 for f in self.file_results if f.has_issues())


@dataclass
class ParsedFileResult:
    """File-level results from parsed input."""

    file_path: str
    test_results: list["ParsedTestResult"] = field(default_factory=list)

    def has_issues(self) -> bool:
        """Check if file has any failures or errors."""
        return any(not r.passed for r in self.test_results)

    def failure_count(self) -> int:
        """Count assertion failures (not errors)."""
        return sum(
            1 for r in self.test_results if not r.passed and r.error_message is None
        )

    def error_count(self) -> int:
        """Count errors/exceptions."""
        return sum(1 for r in self.test_results if r.error_message is not None)


@dataclass
class ParsedTestResult:
    """Individual test result from parsed input."""

    name: str
    line: Optional[int] = None
    passed: bool = True
    expected: Optional[str] = None
    actual: Optional[str] = None
    error_message: Optional[str] = None

    @property
    def is_error(self) -> bool:
        """Check if this is an error (exception) rather than assertion failure."""
        return not self.passed and self.error_message is not None

    @property
    def is_failure(self) -> bool:
        """Check if this is an assertion failure."""
        return not self.passed and self.error_message is None
