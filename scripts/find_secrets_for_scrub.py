#!/usr/bin/env python3
"""
Find likely secrets in the repository and print a scrub report.

This script intentionally does not modify files. It prints filename, line
number, matched snippet, and a suggested placeholder. Run it locally before
creating a scrub PR; after rotating keys you can apply replacements.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

patterns = [
    (re.compile(r"(?i)api[_-]?key\s*=\s*['\"]?([A-Za-z0-9\-_.=:/]+)['\"]?"), '<API_KEY>'),
    (re.compile(r"(?i)secret[_-]?key\s*=\s*['\"]?([A-Za-z0-9\-_.=:/]+)['\"]?"), '<SECRET_KEY>'),
    (re.compile(r"(?i)password\s*=\s*['\"]?([^'\"]+)['\"]?"), '<PASSWORD>'),
    (re.compile(r"(?i)SUPABASE_[A-Z_]+=.*"), '<SUPABASE_VALUE>'),
    (re.compile(r"sk-[A-Za-z0-9\-_.]+"), '<SK>'),
    (re.compile(r"pk-[A-Za-z0-9\-_.]+"), '<PK>'),
    (re.compile(r"eyJ[A-Za-z0-9_-]{10,}"), '<JWT-LIKE>'),
    (re.compile(r"https?://[^\s@/]+:[^\s@/]+@[^\s]+"), '<URL_WITH_CREDS>'),
    (re.compile(r"[A-Za-z0-9\-_]{32,}"), '<LONG_TOKEN>'),
]

def scan_file(path: Path):
    try:
        txt = path.read_text(encoding='utf-8')
    except Exception:
        return []
    findings = []
    for i, line in enumerate(txt.splitlines(), start=1):
        for pat, placeholder in patterns:
            if pat.search(line):
                findings.append((i, line.strip(), placeholder))
                break
    return findings


def main():
    files = [p for p in ROOT.rglob('*') if p.is_file() and p.suffix in ('.py', '.env', '.sh', '.yml', '.yaml', '.json', '.ini')]
    report = []
    for f in files:
        rel = f.relative_to(ROOT)
        found = scan_file(f)
        if found:
            for ln, snippet, placeholder in found:
                report.append((str(rel), ln, snippet, placeholder))

    if not report:
        print('No likely secrets found by heuristics.')
        return 0

    print('Potential secrets report (heuristic):')
    for path, ln, snippet, placeholder in report:
        print(f"- {path}:{ln} -> {snippet}\n    suggested replacement: {placeholder}\n")

    print('After rotating keys, use these suggestions to prepare a scrub PR.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
