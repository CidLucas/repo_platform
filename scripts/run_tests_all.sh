#!/usr/bin/env bash
set -euo pipefail

# Run pytest across the repo and enforce coverage minimum via pytest-cov.
# Usage: COVERAGE_MIN=80 ./scripts/run_tests_all.sh

COVERAGE_MIN=${COVERAGE_MIN:-80}

echo "Running tests across repository (coverage minimum: ${COVERAGE_MIN}%)"

# Install test deps
python -m pip install --upgrade pip
pip install -r requirements-dev.txt 2>/dev/null || true
pip install pytest pytest-cov -q

pytest --cov=. --cov-fail-under=${COVERAGE_MIN} -q

echo "All tests passed with coverage >= ${COVERAGE_MIN}%"
