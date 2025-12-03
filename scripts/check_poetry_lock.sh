#!/usr/bin/env bash
set -euo pipefail

echo "Checking poetry.lock consistency across projects"

projects=$(git ls-files -- '**/pyproject.toml' | sed 's|/pyproject.toml||' | sort -u)
if [ -z "$projects" ]; then
  echo "No poetry projects found."
  exit 0
fi

echo "Found projects:"
  # Use Python's tomllib to parse pyproject.toml and poetry.lock reliably
echo "$projects"

fail=0

for p in $projects; do
  echo "\n=== Checking project: $p ==="
  pushd "$p" >/dev/null

  # Lightweight check: compare declared dependencies in pyproject.toml
  # with package names listed in poetry.lock. This avoids running
  # `poetry lock --no-update` or flags that may not exist in all versions.
  if [ ! -f pyproject.toml ]; then
    echo "WARNING: no pyproject.toml in $p"
    popd >/dev/null
    continue
  fi

  if [ ! -f poetry.lock ]; then
    echo "WARNING: no poetry.lock in $p"
    fail=1
    popd >/dev/null
    continue
  fi

  python3 - <<'PY'
import sys, tomllib, pathlib
p = pathlib.Path('.')
try:
    py = tomllib.loads(p.joinpath('pyproject.toml').read_text())
except Exception as e:
    print('ERROR: failed to parse pyproject.toml:', e)
    sys.exit(2)

deps = []
try:
    deps_dict = py.get('tool', {}).get('poetry', {}).get('dependencies', {}) or {}
    deps = [k for k in deps_dict.keys() if k != 'python']
except Exception:
    deps = []

try:
    lock = tomllib.loads(p.joinpath('poetry.lock').read_text())
    # poetry.lock uses table [[package]] with 'name' keys
    packages = [pkg.get('name') for pkg in lock.get('package', []) if 'name' in pkg]
except Exception:
    # fallback: parse lines containing name = "..."
    text = p.joinpath('poetry.lock').read_text()
    packages = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('name ='):
            try:
                name = line.split('=',1)[1].strip().strip('"').strip("'")
                packages.append(name)
            except Exception:
                pass

missing = []
for d in deps:
    if d not in packages:
        missing.append(d)

if missing:
    print('MISMATCH: dependencies declared in pyproject.toml not found in poetry.lock for project:', ', '.join(missing))
    sys.exit(1)
else:
    print('OK: all declared dependencies present in poetry.lock')
    sys.exit(0)
PY
  rc=$?
  if [ $rc -ne 0 ]; then
    fail=1
  else
    echo "OK: all declared dependencies present in poetry.lock for $p"
  fi

  popd >/dev/null
done

if [ "$fail" -ne 0 ]; then
  echo "::error::One or more poetry.lock files are inconsistent with pyproject.toml. Run 'poetry lock --no-update' locally and commit updated lockfile(s)."
  exit 1
fi

echo "All checked projects have consistent poetry.lock files."
