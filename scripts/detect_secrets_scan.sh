#!/usr/bin/env bash
set -euo pipefail

# Install detect-secrets and run a JSON scan. This script intentionally
# does not cause CI to fail; it writes the findings to `artifacts/detect-secrets.json`
# so maintainers can review and create a baseline after rotating secrets.

TMP_DIR=$(mktemp -d)
OUT_DIR="artifacts"
mkdir -p "$OUT_DIR"

python -m pip install --upgrade pip >/dev/null
python -m pip install detect-secrets >/dev/null

echo "Running detect-secrets scan..."
detect-secrets scan --json > "$OUT_DIR/detect-secrets.json" || true

echo "Summary of findings:"
python - <<'PY'
import json,sys
f='artifacts/detect-secrets.json'
try:
    data=json.load(open(f))
except Exception as e:
    print('No results file found or parse error:', e)
    sys.exit(0)

secrets = data.get('results', {})
count = sum(len(v) for v in secrets.values())
print(f"  Total findings: {count}")
for filename, issues in list(secrets.items())[:10]:
    print(f"  {filename}: {len(issues)}")
    for it in issues[:3]:
        print('    -', it.get('type'), 'line', it.get('line_number'))

PY

echo "Detect-secrets scan complete; results in $OUT_DIR/detect-secrets.json"
