# tpane

**The reference implementation of the TOPA (Test Output Protocol for AI) standard**

## Why "tpane"?

The name has a dual meaning that perfectly captures the tool's purpose:

**1. T-Pain Auto-tune Analogy**
Just like T-Pain's auto-tune transforms raw vocals into polished audio, `tpane` transforms verbose test outputs into clean, structured formats optimized for AI analysis.

**2. Test Output for Context Window**
`tpane` creates a clear "window pane" into your test results - but more importantly, it optimizes them to fit within AI context windows. No more truncated logs or overwhelming verbosity when analyzing test failures.

## Key Benefits

- **60-80% token reduction** compared to raw test output
- **Structured, predictable format** for reliable AI parsing
- **Language-agnostic design** for cross-framework adoption
- **Progressive disclosure** based on context and budget constraints

## Quick Start

```bash
# Install dependencies (requires Python 3.7+)
pip install pyyaml

# Convert JUnit XML to TOPA format
python src/tpane.py --format junit test-results.xml

# Process pytest output with summary mode
pytest | python src/tpane.py --format pytest --mode summary

# Auto-detect format and use failures mode (default)
python src/tpane.py test_output.txt
```

## Usage Examples

### Basic Usage
```bash
# Auto-detect format and show failures (default mode)
tpane test_output.txt

# Specify format explicitly
tpane --format junit test-results.xml
tpane --format pytest pytest_output.txt
tpane --format rspec rspec_results.json
tpane --format tap tap_output.txt

# Process from stdin
pytest | tpane --format pytest
npm test | tpane --format tap
```

### Focus Modes
```bash
# Show summary only (minimal token usage)
tpane --mode summary test_output.txt

# Show critical failures only (errors and key failures)
tpane --mode critical test_output.txt

# Show all failures (default)
tpane --mode failures test_output.txt

# Show only the first failure (for quick debugging)
tpane --mode first-failure test_output.txt
```

### Token Management
```bash
# Set custom token budget (default: 2000)
tpane --limit 1000 large_test_output.xml
tpane --limit 5000 comprehensive_results.json

# Handle large files (default max: 50MB)
tpane --max-input-size 100 very_large_results.xml
```

## About TOPA

TOPA (Test Output Protocol for AI) is a standardized test output format designed specifically for LLM consumption. It addresses the token efficiency, structured parsing, and cross-tool integration needs of AI-powered development workflows.

**TOPA Design Principles:**
1. **Token Efficiency**: Minimize tokens while preserving semantic completeness
2. **Structured Data**: Consistent schema for reliable programmatic access
3. **Semantic Clarity**: Clear causality (what failed and why) with actionable context
4. **Progressive Disclosure**: Multiple detail levels based on available budget
5. **Cross-Framework**: Language and tool agnostic design

## TOPA Output Format

The `tpane` tool outputs YAML-formatted TOPA data that includes:

- **Test Summary**: Total, passed, failed, error counts and execution time
- **File Results**: Organized by test file with path normalization
- **Test Details**: Individual test results with failure context
- **Token Metadata**: Budget usage and truncation indicators
- **Semantic Enhancement**: Extracted assertions, expected/actual values

### Example Output
```yaml
summary:
  total_tests: 156
  passed_tests: 142
  failed_tests: 12
  error_tests: 2
  execution_time: "23.45s"
  
file_results:
  - file_path: "spec/user_validation_spec.rb"
    test_count: 8
    failed_count: 2
    test_results:
      - name: "validates email format"
        passed: false
        expected: "valid email"
        actual: "invalid@"
        error_message: "Email format validation failed"
        location: "spec/user_validation_spec.rb:42"
        
token_metadata:
  estimated_tokens: 1847
  budget_limit: 2000
  truncated: false
  focus_mode: "failures"
```

## Installation & Development

```bash
# Clone the repository
git clone https://github.com/delano/tpane.git
cd tpane

# Install dependencies
pip install pyyaml

# Run tests
python -m pytest tests/ -v

# Run the tool directly
python src/tpane.py --help
```

## Supported Test Formats

| Format | Auto-Detection | Status |
|--------|----------------|---------|
| **JUnit XML** | ✅ `<?xml` + `<testsuite` | Full support |
| **pytest** | ✅ Common patterns | Full support |
| **TAP** | ✅ `1..` or `TAP version` | Full support |
| **RSpec JSON** | ✅ `examples` + `summary` keys | Full support |

## Integration Examples

### GitHub Actions
```yaml
- name: Run tests and generate TOPA output
  run: |
    pytest --junitxml=results.xml
    python src/tpane.py --format junit results.xml > topa_output.yaml
    
- name: Analyze failures with AI
  uses: your-ai-analysis-action@v1
  with:
    test_results: topa_output.yaml
```

### CI/CD Pipeline
```bash
#!/bin/bash
# Run tests and process with tpane
npm test > test_output.txt 2>&1
python src/tpane.py --format tap test_output.txt > topa_results.yaml

# Send to AI analysis service
curl -X POST https://your-ai-service/analyze \
  -H "Content-Type: text/yaml" \
  --data-binary @topa_results.yaml
```

## Technical Implementation

`tpane` implements the TOPA standard through:

- **Smart Format Detection**: Automatic identification of input test format
- **Modular Parsers**: Extensible parser architecture for new test frameworks
- **Token Budget Management**: Intelligent truncation and prioritization
- **Path Normalization**: Consistent file path handling across platforms
- **Error Recovery**: Graceful handling of malformed or incomplete test output

## Contributing

We welcome contributions to both the TOPA standard and the `tpane` reference implementation:

- **Standard Evolution**: Propose enhancements to the TOPA specification
- **Parser Extensions**: Add support for new test frameworks
- **Performance Optimization**: Improve token efficiency and processing speed
- **Integration Examples**: Share real-world usage patterns

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

**tpane** - Because your test output deserves the auto-tune treatment! 🎤✨