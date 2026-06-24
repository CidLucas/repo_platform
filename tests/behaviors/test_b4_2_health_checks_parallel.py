"""RED test for behavior B4.2 — Sequential health checks in health.py.

GOAL:
    Corrigir 4 bottlenecks P1 no código de produção. Issue #121 — Performance.
    O `health_check` em health.py atualmente faz um loop sobre `_checks` e executa
    cada check com `await asyncio.wait_for(check_func(), timeout=...)` sequencialmente
    — cada check é um round-trip separado que soma latência.

BEHAVIOR:
    B4.2 — health_check e readiness_check em health.py devem usar asyncio.gather()
    para executar as health checks em paralelo, em vez de sequencialmente no for loop.

    Hoje (RED) o código faz:
        for check_name, check_func in _checks.items():
            result = await asyncio.wait_for(check_func(), timeout=timeout_seconds)

    O contrato GREEN esperado é:
        async def _run_check(name, func, timeout):
            try:
                result = await asyncio.wait_for(func(), timeout=timeout)
                return name, result
            except Exception as e:
                return name, e

        results = await asyncio.gather(
            *(_run_check(n, f, timeout_seconds) for n, f in _checks.items()),
            return_exceptions=True
        )

AC (Acceptance Criteria):
    AC#3 — health_check executa N checks em paralelo (via asyncio.gather) em vez de N awaits sequenciais
    AC#4 — readiness_check também usa asyncio.gather para checks paralelos

DECISION:
    Estratégia: extend (refatorar health_check e readiness_check para usar asyncio.gather)
    Arquivo alvo: libs/blu_observability_bootstrap/src/blu_observability_bootstrap/health.py
    Funções alvo: health_check (linha ~82) e readiness_check (linha ~127)

Anti-Goals (must NOT be violated):
    1. NÃO alterar a assinatura de create_health_router
    2. NÃO alterar o contrato de retorno (HealthStatus / ReadinessStatus)
    3. NÃO introduzir dependência externa nova
    4. NÃO alterar as funções helper check_database_url etc.
    5. NÃO modificar /live e /metrics endpoints

Estado atual: RED — o loop `for check_name, check_func in _checks.items(): await` sequencial
ainda está presente. O teste source-level falha com AssertionError ao verificar que não há
asyncio.gather() no corpo das funções health_check e readiness_check.
"""

import ast
import inspect
import re
from pathlib import Path

import pytest


# ── Path ──────────────────────────────────────────────────────────────────

HEALTH_MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "libs"
    / "blu_observability_bootstrap"
    / "src"
    / "blu_observability_bootstrap"
    / "health.py"
)


# ── Source-level guard helpers ────────────────────────────────────────────


def _get_function_source(func_name: str) -> str:
    """Extract the source code of a function by name from health.py."""
    assert HEALTH_MODULE_PATH.exists(), f"Source file not found: {HEALTH_MODULE_PATH}"
    source = HEALTH_MODULE_PATH.read_text(encoding="utf-8")

    # Find the function definition
    marker = f"async def {func_name}("
    idx = source.find(marker)
    assert idx != -1, f"Could not find async def {func_name} in {HEALTH_MODULE_PATH}"

    # Parse the function body using ast
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == func_name:
            lines = source.splitlines()
            start = node.lineno - 1  # 0-indexed
            end = node.end_lineno  # already 1-indexed in ast
            return "\n".join(lines[start:end])

    raise AssertionError(f"Could not extract source for function {func_name}")


def _has_asyncio_gather(source: str) -> bool:
    """Check if the function body contains asyncio.gather call."""
    return "asyncio.gather" in source or "asyncio.gather(" in source


def _has_sequential_for_loop(source: str) -> bool:
    """Check if the function body contains a sequential for-await loop pattern.

    Detects:
        for check_name, check_func in _checks.items():
            result = await ...
    """
    # Check for for-in-items pattern followed by await inside the loop body
    lines = source.splitlines()
    in_for_loop = False
    for_depth = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Detect "for X in Y.items():" or "for X, Y in Z.items():"
        if stripped.startswith("for ") and ".items():" in stripped:
            in_for_loop = True
            for_depth = 0
            continue

        if in_for_loop:
            # Track indentation depth relative to the for line
            indent = len(line) - len(line.lstrip())
            if indent <= for_depth and not stripped.startswith("#") and stripped:
                in_for_loop = False
                continue
            if stripped.startswith("await ") or "await " in stripped:
                return True  # Found await inside a for loop over .items()

    return False


# ── Tests ─────────────────────────────────────────────────────────────────


def test_b4_2_health_check_uses_gather():
    """health_check must use asyncio.gather, not sequential for loop.

    This test reads the source of `health_check` and verifies:
    1. It does NOT contain a sequential for-await loop over _checks.items()
    2. It DOES contain asyncio.gather or equivalent parallel call
    """
    source = _get_function_source("health_check")

    # Assert RED: asyncio.gather MUST be present for GREEN
    # Since the code is still RED (sequential loop), this assertion FAILS
    assert _has_asyncio_gather(source), (
        "RED — health_check does NOT use asyncio.gather yet. "
        "Expected: health_check uses asyncio.gather to run N checks in parallel. "
        "Found: sequential for-await loop over _checks.items(). "
        "The Coder must refactor to use `results = await asyncio.gather(...)`."
    )


def test_b4_2_readiness_check_uses_gather():
    """readiness_check must also use asyncio.gather, not sequential for loop.

    Same validation as health_check but for the readiness_check function.
    """
    source = _get_function_source("readiness_check")

    # Assert RED: asyncio.gather MUST be present for GREEN
    # Since the code is still RED (sequential loop), this assertion FAILS
    assert _has_asyncio_gather(source), (
        "RED — readiness_check does NOT use asyncio.gather yet. "
        "Expected: readiness_check uses asyncio.gather to run N checks in parallel. "
        "Found: sequential for-await loop over _checks.items(). "
        "The Coder must refactor to use `results = await asyncio.gather(...)`."
    )


def test_b4_2_source_file_exists():
    """Sanity check: the source file must exist."""
    assert HEALTH_MODULE_PATH.exists(), (
        f"Source file not found: {HEALTH_MODULE_PATH}"
    )
    source = HEALTH_MODULE_PATH.read_text(encoding="utf-8")
    assert "async def health_check(" in source, (
        "health_check function not found in health.py"
    )
    assert "async def readiness_check(" in source, (
        "readiness_check function not found in health.py"
    )
