#!/usr/bin/env bash
set -euo pipefail

# Validate pyproject.toml files using poetry. Requires 'poetry' available in PATH.
echo "Checking pyproject.toml files with 'poetry check'"

found=0
for f in $(find . -name pyproject.toml); do
  dir=$(dirname "$f")
  echo "--- Checking $dir ---"
  (cd "$dir" && poetry check) || { echo "poetry check failed in $dir"; exit 2; }
  found=1
done

if [ "$found" -eq 0 ]; then
  echo "No pyproject.toml files found."
fi

echo "pyproject.toml validation completed"
