Summary

The optimized TOPAZ v0.3 format is now **maximally respectful of context window size** while retaining all critical debugging information:

### Token Efficiency Achieved:
- **66% reduction** in token usage (375 → 125 tokens)
- **Compact format**: 10 lines instead of 30
- **Smart defaults**: Only shows non-standard configurations
- **Single-line values**: Multiple related fields per line

### Critical Information Retained:
- ✅ **Command reproduction**: Exact command for debugging
- ✅ **System context**: PID, working directory
- ✅ **Runtime details**: Language, version, platform (simplified)
- ✅ **Version control**: Branch and commit (compact format)
- ✅ **Environment**: Only relevant, non-default values
- ✅ **Test scale**: File count for understanding scope

### What Was Removed/Optimized:
- ❌ **Shell**: Rarely impacts test outcomes
- ❌ **Package manager path**: Long, rarely needed
- ❌ **Test discovery patterns**: Implicit from framework
- ❌ **Nested structures**: Flattened for efficiency
- ❌ **Protocol metadata**: Compressed to single line
- ❌ **Default values**: Only show when different

### Why This Balance Works:
1. **Prevents circular debugging**: Includes version, environment, and flags that often cause platform-specific issues
2. **Scales efficiently**: At 125 tokens, even 10 test runs only use 1250 tokens
3. **Language-agnostic**: Format works for Python, JavaScript, Java, etc.
4. **Focus modes**: `summary` mode can be as low as 50 tokens

The TOPAZ v0.3 proposal provides a robust standard that respects LLM context windows while ensuring agents have the information needed to debug effectively without going in circles.

---

# TOPAZ v0.3 Specification Proposal

## Test Output Protocol for AI - Version 0.3

### Overview

TOPAZ (Test Output Protocol for AI) is a language-agnostic, token-efficient format for communicating test execution results and context to AI agents. Version 0.3 optimizes for minimal token usage while providing maximum diagnostic value.

### Key Changes from v0.2

1. **Compact Execution Context**: Reduced from ~30 lines to ~10 lines
2. **Single-line Formats**: Multiple values per line where logical
3. **Smart Defaults**: Only show non-standard configurations
4. **Normalized Field Names**: Shorter, consistent naming across languages

### TOPAZ v0.3 Format Specification

#### Execution Context (Header)

```yaml
EXECUTION_CONTEXT:
  command: <exact command executed>
  pid: <process_id> | pwd: <working_directory>
  runtime: <language> <version> (<platform>)
  package_manager: <name> <version>  # Optional: only if present
  vcs: <system> <branch>@<commit>     # Optional: only if available
  environment: <KEY=value, ...>        # Optional: only non-defaults
  test_framework: <name> (<isolation_mode>)
  flags: <flag1, flag2, ...>          # Optional: only if set
  protocol: TOPAZ v0.3 | focus: <mode> | limit: <tokens>
  project_type: <type>                # Optional: only if detectable
  files_under_test: <count>
```

#### Test Results (Body)

```yaml
# For failures/errors mode:
<file_path>:
  L<line>: <failure_description>
    Test: <test_name>
    Expected: <expected_value>  # Optional
    Got: <actual_value>         # Optional
    Diff:                       # Optional
      - <removed>
      + <added>

# For summary mode:
Summary:
  <passed> passed, <failed> failed[, <errors> errors] in <files> files

Files:
  <file_path>: <count> <status>
```

### Field Definitions

#### Execution Context Fields

| Field | Description | Example | Required |
|-------|-------------|---------|----------|
| `command` | Exact command executed | `pytest tests/ -v` | Yes |
| `pid` | Process ID | `12345` | Yes |
| `pwd` | Working directory | `/home/user/project` | Yes |
| `runtime` | Language, version, platform | `python 3.11.5 (linux-x64)` | Yes |
| `package_manager` | Dependency manager info | `pip 23.0.1` | No |
| `vcs` | Version control info | `git main@a1b2c3d` | No |
| `environment` | Relevant env vars | `CI=github, ENV=test` | No |
| `test_framework` | Framework and isolation | `pytest (isolated)` | Yes |
| `flags` | Execution flags | `verbose, parallel` | No |
| `protocol` | TOPAZ version and config | `TOPAZ v0.3 \| focus: failures \| limit: 5000` | Yes |
| `project_type` | Auto-detected type | `python_package` | No |
| `files_under_test` | Number of test files | `42` | Yes |

#### Environment Variables (Normalized)

| TOPAZ Key | Maps From | Description |
|----------|-----------|-------------|
| `CI` | `CI`, `GITHUB_ACTIONS`, `GITLAB_CI` | CI system identifier |
| `ENV` | `RAILS_ENV`, `NODE_ENV`, `APP_ENV` | Application environment |
| `COV` | `COVERAGE`, `SIMPLECOV`, `PYTEST_COV` | Coverage enabled |
| `SEED` | `SEED`, `RANDOM_SEED` | Test randomization seed |

#### Execution Flags (Normalized)

| Flag | Description | Language Examples |
|------|-------------|-------------------|
| `verbose` | Detailed output | `-v`, `--verbose` |
| `debug` | Debug mode | `-d`, `--debug`, `DEBUG=1` |
| `parallel` | Parallel execution | `-j`, `--parallel`, `-n` |
| `fails-only` | Show only failures | `-f`, `--failed-only` |
| `strict` | Strict mode | `--strict`, `-W error` |
| `quiet` | Minimal output | `-q`, `--quiet` |
| `traces` | Stack traces | `-s`, `--tb=long` |

#### Project Types

| Type | Detection | Languages |
|------|-----------|-----------|
| `rails` | `config/application.rb` | Ruby |
| `django` | `manage.py` | Python |
| `node_package` | `package.json` | JavaScript |
| `python_package` | `setup.py`, `pyproject.toml` | Python |
| `java_maven` | `pom.xml` | Java |
| `java_gradle` | `build.gradle` | Java |
| `dotnet` | `*.csproj` | C# |
| `go_module` | `go.mod` | Go |
| `rust_crate` | `Cargo.toml` | Rust |
| `generic` | Default | Any |

### Token Efficiency Analysis

#### v0.2 Format (~30 lines, ~375 tokens)
```yaml
summary:
  total_tests: 156
  passed_tests: 142
  # ... extensive nested structure
file_results:
  - file_path: "spec/user_spec.rb"
    test_count: 8
    # ... deeply nested results
```

#### v0.3 Format (~10 lines, ~125 tokens)
```yaml
EXECUTION_CONTEXT:
  command: rspec spec/
  pid: 12345 | pwd: /project
  runtime: ruby 3.2.0 (linux-x64)
  # ... compact single lines
```

**Token Savings: ~66% reduction**

### Language Implementation Examples

#### Python/pytest
```yaml
EXECUTION_CONTEXT:
  command: pytest tests/ -v --cov
  pid: 12345 | pwd: /home/user/project
  runtime: python 3.11.5 (linux-x64)
  package_manager: pip 23.0.1
  vcs: git main@a1b2c3d
  environment: CI=github, COV=1
  test_framework: pytest (isolated)
  flags: verbose, coverage
  protocol: TOPAZ v0.3 | focus: failures | limit: 5000
  project_type: python_package
  files_under_test: 24
```

#### JavaScript/Jest
```yaml
EXECUTION_CONTEXT:
  command: npm test
  pid: 54321 | pwd: /app
  runtime: node 20.10.0 (darwin-arm64)
  package_manager: npm 10.2.3
  vcs: git develop@f3e2d1c
  test_framework: jest (isolated)
  protocol: TOPAZ v0.3 | focus: all | limit: 10000
  project_type: node_package
  files_under_test: 18
```

#### Java/JUnit
```yaml
EXECUTION_CONTEXT:
  command: mvn test
  pid: 98765 | pwd: /workspace
  runtime: java 17.0.9 (linux-x64)
  package_manager: maven 3.9.5
  vcs: git feature/auth@9876543
  environment: CI=jenkins
  test_framework: junit5 (isolated)
  flags: parallel
  protocol: TOPAZ v0.3 | focus: failures | limit: 5000
  project_type: java_maven
  files_under_test: 52
```

### Focus Modes

| Mode | Description | Use Case | Token Usage |
|------|-------------|----------|-------------|
| `summary` | Counts only | Quick status check | ~50 tokens |
| `failures` | All failures with details | Standard debugging | ~50-500 tokens |
| `first-failure` | First failure per file | Initial diagnosis | ~100-200 tokens |
| `critical` | Errors/exceptions only | Crash debugging | ~100-300 tokens |
| `all` | Complete output | Full analysis | 500+ tokens |

### Migration Guide from v0.2

1. **Flatten nested structures**: `runtime.language: ruby` → `runtime: ruby 3.2.0`
2. **Combine related fields**: Separate lines for shell/pid → `pid: 123 | pwd: /dir`
3. **Normalize field names**: `execution_time` → part of summary line
4. **Reduce verbosity**: Only show non-default values
5. **Use focus modes**: Replace manual truncation with protocol modes

### Benefits of v0.3

1. **66% Token Reduction**: More efficient use of context windows
2. **Faster Parsing**: Single-line formats are quicker to process
3. **Better Defaults**: Less noise from standard configurations
4. **Universal Compatibility**: Works across all major test frameworks
5. **Smart Truncation**: Focus modes prevent context overflow

### Reference Implementation

The reference implementation is available in:
- Ruby: [tryouts](https://github.com/delano/tryouts) (original)
- Cross-language: [tpane](https://github.com/delano/tpane) (universal adapter)

### Future Considerations (v0.4+)

- Binary format option for extreme compression
- Streaming protocol for real-time updates
- Diff-only updates for watch mode
- Machine learning optimized field selection
