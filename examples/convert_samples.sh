#!/bin/bash

# tpane Examples - Convert sample inputs to TOPAZ format
# Run from the project root directory

echo "=== tpane Sample Conversions =="
echo

echo "1. JUnit XML to TOPAZ (failures mode):"
python src/tpane.py --format junit examples/sample_junit.xml
echo

echo "2. pytest output to TOPAZ (summary mode):"
python src/tpane.py --format pytest --mode summary examples/sample_pytest.txt
echo

echo "3. RSpec JSON to TOPAZ (critical mode):"
python src/tpane.py --format rspec --mode critical examples/sample_rspec.json
echo

echo "4. TAP output to TOPAZ (first-failure mode):"
python src/tpane.py --format tap --mode first-failure examples/sample_tap.txt
echo

echo "5. Auto-detect format (pytest):"
python src/tpane.py examples/sample_pytest.txt
echo
