# TOPA Integration Guide

This guide shows how to integrate TOPA into various development workflows and tools.

## CI/CD Integration

### GitHub Actions

```yaml
name: Test with TOPA Analysis
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run tests
        run: |
          pytest --junit-xml=test-results.xml
        continue-on-error: true

      - name: Convert to TOPA format
        run: |
          python topa/src/tpane.py --format junit --mode summary test-results.xml > test-summary.yaml

      - name: Upload TOPA output
        uses: actions/upload-artifact@v3
        with:
          name: test-analysis
          path: test-summary.yaml
```

### GitLab CI

```yaml
test:
  script:
    - pytest --junit-xml=test-results.xml || true
    - python topa/src/tpane.py --format junit test-results.xml > test-analysis.yaml
  artifacts:
    reports:
      junit: test-results.xml
    paths:
      - test-analysis.yaml
```

## Language-Specific Integration

### Python (pytest)

```bash
# Basic pytest integration
pytest tests/ | python tpane.py --format pytest --mode failures

# With JSON output
pytest --json-report --json-report-file=results.json
python tpane.py --format pytest results.json

# In CI with token limits
pytest | python tpane.py --mode summary --limit 1000
```

### Ruby (RSpec)

```bash
# JSON format (recommended)
bundle exec rspec --format json --out rspec.json
python tpane.py --format rspec rspec.json

# Direct pipe (text parsing)
bundle exec rspec | python tpane.py --format rspec

# Critical errors only
bundle exec rspec --format json | python tpane.py --mode critical
```

### Java (JUnit)

```bash
# Maven surefire reports
python tpane.py --format junit target/surefire-reports/TEST-*.xml

# Gradle test reports
python tpane.py --format junit build/test-results/test/TEST-*.xml

# Single file
python tpane.py --format junit build/test-results/test/TEST-MyTest.xml
```

### JavaScript (Jest)

```bash
# Jest with JUnit reporter
npm test -- --reporters=jest-junit
python tpane.py --format junit junit.xml

# Custom Jest integration (requires adapter)
npm test | python tpane.py --format jest  # (future enhancement)
```

## AI Tool Integration

### OpenAI API

```python
import openai
import subprocess
import yaml

# Run tests and get TOPA output
result = subprocess.run([
    'python', 'tpane.py', '--mode', 'failures', 'test-results.xml'
], capture_output=True, text=True)

topa_output = result.stdout

# Send to OpenAI with token-efficient prompt
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{
        "role": "user",
        "content": f"Analyze these test failures and suggest fixes:\n\n{topa_output}"
    }]
)

print(response.choices[0].message.content)
```

### Claude API

```python
import anthropic
import subprocess

# Get TOPA output with appropriate token limit for Claude
result = subprocess.run([
    'python', 'tpane.py', '--limit', '8000', '--mode', 'first-failure'
], capture_output=True, text=True)

client = anthropic.Anthropic(api_key="your-api-key")

response = client.messages.create(
    model="claude-3-sonnet-20240229",
    max_tokens=2000,
    messages=[{
        "role": "user",
        "content": f"Help me understand and fix these test failures:\n\n{result.stdout}"
    }]
)

print(response.content[0].text)
```

## IDE Integration

### VS Code Extension

```json
{
  "name": "TOPA Test Analysis",
  "version": "0.1.0",
  "contributes": {
    "commands": [
      {
        "command": "topa.analyzeTests",
        "title": "Analyze Test Results with TOPA"
      }
    ]
  }
}
```

### Vim/Neovim

```vim
" Add to .vimrc or init.vim
function! TOPAAnalyze()
    let test_output = system('pytest --tb=short 2>&1')
    let topa_output = system('echo "' . escape(test_output, '"') . '" | python ~/topa/src/tpane.py --mode critical')

    " Display in new buffer
    new
    setlocal buftype=nofile
    put =topa_output
endfunction

command! TOPAAnalyze call TOPAAnalyze()
```

## Custom Parser Development

### Adding New Input Format

1. **Create parser class**:

```python
# src/parsers/myformat.py
from .base import BaseParser
from ..core.schema import ParsedTestData

class MyFormatParser(BaseParser):
    def parse(self, content: str) -> ParsedTestData:
        # Implement parsing logic
        return self._build_test_data(
            total_tests=10,
            passed_tests=8,
            failed_tests=2,
            file_results=file_results
        )
```

2. **Register in main CLI**:

```python
# src/tpane.py
from .parsers.myformat import MyFormatParser

class InputFormat(Enum):
    # ... existing formats
    MYFORMAT = "myformat"

def get_parser(format_type: InputFormat) -> BaseParser:
    parsers = {
        # ... existing parsers
        InputFormat.MYFORMAT: MyFormatParser,
    }
```

3. **Add detection pattern**:

```python
def detect_format(content: str) -> InputFormat:
    # Add detection logic
    if content.startswith('MYFORMAT:'):
        return InputFormat.MYFORMAT
    # ... existing logic
```

## Performance Optimization

### Token Budget Tuning

```bash
# For different model contexts
python tpane.py --limit 2000   # GPT-3.5 friendly
python tpane.py --limit 8000   # GPT-4 standard
python tpane.py --limit 32000  # GPT-4 Turbo
python tpane.py --limit 100000 # Claude-3 Opus

# Focus modes for different needs
python tpane.py --mode summary      # Overview only (~200 tokens)
python tpane.py --mode critical     # Errors only (~500-1000 tokens)
python tpane.py --mode first-failure # One per file (~1000-2000 tokens)
python tpane.py --mode failures     # All failures (~2000-5000 tokens)
```

### Batching Multiple Test Runs

```bash
# Process multiple test result files
for file in test-results-*.xml; do
    echo "=== $file ==="
    python tpane.py --format junit --mode summary "$file"
done > combined-analysis.yaml
```

## Error Handling

### Common Issues

1. **Malformed Input**: TOPA includes fallback text parsing for most formats
2. **Large Files**: Use `--limit` to cap token usage
3. **Unsupported Formats**: Contribute a new parser or use generic text parsing
4. **Encoding Issues**: TOPA handles UTF-8 by default

### Debugging

```bash
# Verbose mode (if added)
python tpane.py --verbose test-results.xml

# Debug token usage
python tpane.py --limit 500 --mode failures test-results.xml
# Check if output is truncated, adjust limit accordingly
```

## Production Deployment

### Docker Integration

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY src/ /app/tpane/
RUN pip install pyyaml

# Usage: docker run tpane-image python tpane/tpane.py --format junit /data/results.xml
ENTRYPOINT ["python", "tpane/tpane.py"]
```

### Lambda Function

```python
import json
import boto3
from tpane import TOPAEncoder, PytestParser

def lambda_handler(event, context):
    # Parse test output from event
    test_output = event['test_output']
    format_type = event.get('format', 'pytest')

    # Process with TOPA
    parser = PytestParser()  # or get_parser(format_type)
    parsed_data = parser.parse(test_output)

    encoder = TOPAEncoder('summary')
    topa_output = encoder.encode(parsed_data)

    return {
        'statusCode': 200,
        'body': json.dumps(topa_output)
    }
```

## Community Integration

### Submit Parser to Test Frameworks

1. **Create PR** with native TOPA output support
2. **Reference implementation** available in this repo
3. **Specification** provides clear target format
4. **Benefits**: Reduced processing overhead, better AI integration

### Contribute Improvements

- **New parsers** for additional test frameworks
- **Enhanced format detection** algorithms
- **Token optimization** improvements
- **Integration examples** for popular tools

See the main [README.md](../README.md) for contribution guidelines.
