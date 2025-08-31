# Development Guide

This guide covers setting up the development environment, running tests, and contributing to tpane.

## Prerequisites

- Python 3.7 or higher
- pip package manager

## Development Setup

### 1. Clone and Install

```bash
# Clone the repository
git clone https://github.com/delano/tpane.git
cd tpane

# Install in development mode with all dependencies
pip install -e ".[dev]"
```

### 2. Verify Installation

```bash
# Check that development tools are available
ruff --version
mypy --version
pytest --version

# Run the tool to verify it works
python src/tpane.py --help
```

## Development Workflow

### Code Quality Tools

The project uses modern Python tooling for code quality:

```bash
# Lint and format code with ruff
ruff check                    # Check for linting issues
ruff check --fix             # Auto-fix issues where possible
ruff format                   # Format code

# Type checking with mypy
mypy src/                     # Check source code types
mypy tests/                   # Check test code types

# Run all quality checks
ruff check && ruff format && mypy src/
```

### Testing

```bash
# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run tests with coverage report
pytest --cov

# Run tests for a specific file
pytest tests/test_specific.py

# Run tests matching a pattern
pytest -k "test_pattern"
```

### Project Structure

```
tpane/
├── src/
│   └── tpane.py          # Main implementation
├── tests/                # Test suite
├── docs/                 # Documentation
├── examples/             # Usage examples
├── pyproject.toml        # Project configuration
├── README.md             # User documentation
├── DEVELOPMENT.md        # This file
└── DEPLOYMENT.md         # Deployment guide
```

## Code Standards

### Formatting and Style

- **Line length**: 88 characters (configured in pyproject.toml)
- **Quote style**: Double quotes
- **Import sorting**: Managed by ruff (isort replacement)
- **Code formatting**: Handled by ruff format

### Type Hints

- All public functions must have type hints
- Use `typing` module for Python 3.7 compatibility
- mypy configuration enforces strict typing

### Testing

- Use pytest for all tests
- Aim for >80% test coverage
- Test files should match `test_*.py` pattern
- Place tests in the `tests/` directory

## Contributing

### Before Submitting

1. **Code Quality**: Ensure all quality checks pass
   ```bash
   ruff check && ruff format && mypy src/
   ```

2. **Tests**: Ensure all tests pass and coverage is maintained
   ```bash
   pytest --cov
   ```

3. **Documentation**: Update relevant documentation for your changes

### Pull Request Process

1. Create a feature branch from `main`
2. Make your changes following the code standards
3. Add or update tests as needed
4. Update documentation if required
5. Ensure all quality checks pass
6. Submit a pull request with a clear description

## Debugging

### Common Issues

**Import errors**: Ensure you've installed in development mode with `pip install -e ".[dev]"`

**Ruff not found**: Install development dependencies or install ruff directly with `pip install ruff`

**Type errors**: Check that you're using Python 3.7+ compatible syntax and type hints

### Development Tips

- Use `python src/tpane.py` to run the tool during development
- Test with various input formats in the `examples/` directory
- Use `pytest -v` for detailed test output during debugging
- Run `ruff check --fix` before committing to auto-fix style issues

## Performance Considerations

- The tool processes large test files efficiently
- Default token budget is 2000, configurable via `--limit`
- Memory usage scales with input size, default max is 50MB
- Consider performance impact when adding new features

## Release Process

See [DEPLOYMENT.md](DEPLOYMENT.md) for information about releasing new versions to PyPI.
