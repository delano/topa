#!/bin/bash

# TOPA Examples - Convert sample inputs to TOPA format
# Run from the project root directory

echo "=== TOPA Sample Conversions ==="
echo

echo "1. JUnit XML to TOPA (failures mode):"
python src/topa.py --format junit examples/sample_junit.xml
echo

echo "2. pytest output to TOPA (summary mode):"
python src/topa.py --format pytest --mode summary examples/sample_pytest.txt
echo

echo "3. RSpec JSON to TOPA (critical mode):"
python src/topa.py --format rspec --mode critical examples/sample_rspec.json
echo

echo "4. TAP output to TOPA (first-failure mode):"
python src/topa.py --format tap --mode first-failure examples/sample_tap.txt
echo

echo "5. Auto-detect format (pytest):"
python src/topa.py examples/sample_pytest.txt
echo
