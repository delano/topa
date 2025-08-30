# Deployment Guide

## PyPI Tokens Setup

### Required GitHub Secrets

| Secret | Source | Purpose | Triggers |
|--------|--------|---------|----------|
| `TEST_PYPI_API_TOKEN` | https://test.pypi.org/ | Testing uploads | Push to `main` |
| `PYPI_API_TOKEN` | https://pypi.org/ | Production releases | Version tags (`v*`) |

### Getting Tokens

**Test PyPI:**
1. Register at https://test.pypi.org/
2. Account Settings → API tokens → Generate token
3. Scope: Project or account-wide

**PyPI:**
1. Register at https://pypi.org/
2. Account Settings → API tokens → Generate token  
3. Scope: Project or account-wide

### GitHub Setup

Repository Settings → Secrets and variables → Actions → New repository secret

- Name: `TEST_PYPI_API_TOKEN`
- Value: `pypi-...` (from test.pypi.org)

- Name: `PYPI_API_TOKEN` 
- Value: `pypi-...` (from pypi.org)

## Workflow

```bash
# Development testing
git push origin main              # → Publishes to Test PyPI

# Official release
git tag v1.0.0                   # → Publishes to PyPI
git push origin v1.0.0
```

## Package Installation

```bash
# From Test PyPI
pip install -i https://test.pypi.org/simple/ tpane.tpane

# From PyPI
pip install tpane.tpane
```