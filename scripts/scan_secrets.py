#!/usr/bin/env python3
"""
Basic heuristic secrets scanner.

Searches repository files (text) for patterns that commonly indicate secrets
and API keys. Excludes `.env` by default to allow local dev files.

This is intentionally heuristic and should be complemented by a robust
secrets-scanning tool in CI (detect-secrets, trufflehog, etc.).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXCLUDE = {".git", "venv", "env", "node_modules", ".venv", ".env"}

# Patterns to scan for
PATTERNS = [
    (re.compile(r"\b(?:sb_secret_[A-Za-z0-9_-]{10,}|OPENAI_API_KEY|LANGFUSE_SECRET_KEY|OLLAMA_CLOUD_API_KEY)\b", re.I), "known-token"),
    (re.compile(r"sk-[A-Za-z0-9-]{20,}"), "openai/sk- token pattern"),
    (re.compile(r"eyJ[A-Za-z0-9_\-\.]{10,}"), "jwt/base64-like token"),
    (re.compile(r"[A-Za-z0-9/_\-+]{32,}"), "long base64-like string"),
    (re.compile(r"password\s*=\s*['\"]?.{4,}['\"]?", re.I), "password assignment"),
]


def scan_file(path: Path):
    try:
        text = path.read_text(errors="ignore")
    except Exception:
        return []

    findings = []
    for pat, name in PATTERNS:
        for m in pat.finditer(text):
            # Skip very short matches
            val = m.group(0).strip()
            if len(val) < 8:
                continue
            findings.append((name, val[:200], m.start()))
    return findings


def main():
    matches = {}
    for path in ROOT.rglob("*"):
        if any(p in path.parts for p in EXCLUDE):
            continue
        if path.is_file() and path.suffix in {".py", ".yaml", ".yml", ".env", ".json", ".sh", ".md"}:
            results = scan_file(path)
            if results:
                matches[str(path)] = results

    if not matches:
        print("No suspicious secrets found (heuristic scan)")
        return 0

    print("Potential secrets found (heuristic):")
    for fname, items in matches.items():
        print(f"\nFile: {fname}")
        for name, snippet, pos in items:
            print(f" - {name} @ {pos}: {snippet}")

    # Return non-zero to fail CI if desired
    return 1


if __name__ == '__main__':
    sys.exit(main())
