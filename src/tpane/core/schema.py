"""
TOPA Schema Definitions

Data structures representing the standardized TOPA format.
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
class TOPAOutput:
    """Complete TOPA format output."""

    version: str
    summary: Summary
    failures: Optional[list[FileSummary]] = None
    files_with_issues: Optional[list[FileIssues]] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format for serialization."""
        result: dict[str, Any] = {"version": self.version, "summary": self.summary.to_dict()}

        if self.failures is not None:
            result["failures"] = [f.to_dict() for f in self.failures]

        if self.files_with_issues is not None:
            result["files_with_issues"] = [f.to_dict() for f in self.files_with_issues]

        return result


# Parsed test data from input (before TOPA encoding)
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
