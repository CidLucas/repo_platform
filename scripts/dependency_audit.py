#!/usr/bin/env python3
"""
Heuristic dependency audit.

For each top-level package directory (services/* and libs/*), the script
collects imported top-level module names and compares them to the
`pyproject.toml` [tool.poetry.dependencies] (if present) to find:
 - Potentially missing dependencies (used but not declared)
 - Potentially unused dependencies (declared but not imported)

This is heuristic and will have false positives/negatives (namespace packages,
standard library vs third-party mapping). Use as a guide, not an absolute.
"""
from pathlib import Path
import ast
import tomllib
import sys

ROOT = Path(__file__).resolve().parent.parent


def collect_imports(path: Path):
    imports = set()
    for p in path.rglob('*.py'):
        try:
            tree = ast.parse(p.read_text(encoding='utf-8'))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    imports.add(n.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
    return imports


def read_pyproject_deps(pyproject_path: Path):
    try:
        data = tomllib.loads(pyproject_path.read_text(encoding='utf-8'))
        deps = data.get('tool', {}).get('poetry', {}).get('dependencies', {})
        # remove python spec
        deps = {k for k in deps.keys() if k.lower() != 'python'}
        return deps
    except Exception:
        return set()


def analyze_project(dirpath: Path):
    pyproject = dirpath / 'pyproject.toml'
    imports = collect_imports(dirpath)
    deps = read_pyproject_deps(pyproject) if pyproject.exists() else set()

    # Heuristic: filter out stdlib modules by a small builtin list
    stdlib_like = {
        'os', 'sys', 're', 'json', 'time', 'typing', 'pathlib', 'itertools',
        'collections', 'dataclasses', 'asyncio', 'logging', 'datetime', 'math'
    }

    third_party_imports = {i for i in imports if i not in stdlib_like}

    missing = sorted([i for i in third_party_imports if i not in deps])
    unused = sorted([d for d in deps if d not in imports])

    return {
        'imports_count': len(imports),
        'declared_deps': sorted(deps),
        'missing': missing,
        'unused': unused,
    }


def main():
    projects = []
    for d in ROOT.iterdir():
        if d.is_dir() and d.name in ('services', 'libs'):
            for child in d.iterdir():
                if child.is_dir():
                    projects.append(child)

    any_issues = False
    for proj in projects:
        res = analyze_project(proj)
        if res['missing'] or res['unused']:
            any_issues = True
            print(f"\nProject: {proj}")
            if res['missing']:
                print("  Potential MISSING dependencies (imports found but not declared):")
                for m in res['missing']:
                    print(f"   - {m}")
            if res['unused']:
                print("  Potential UNUSED declared dependencies (declared but not imported):")
                for u in res['unused']:
                    print(f"   - {u}")

    if not any_issues:
        print("No obvious dependency mismatches found (heuristic)")
        return 0
    return 1


if __name__ == '__main__':
    sys.exit(main())
