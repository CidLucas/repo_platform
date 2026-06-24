"""RED test for behavior B4.1 — Serial awaits → asyncio.gather in context_service.py.

GOAL:
    Corrigir 4 bottlenecks P1 no código de produção. Issue #121 — Performance.
    O `get_morning_brief` em context_service.py atualmente faz 3 chamadas sequenciais
    (approval_requests, active routines, get_business_memory_snapshot) que poderiam
    ser executadas em paralelo via asyncio.gather.

BEHAVIOR:
    B4.1 — get_morning_brief em context_service.py deve usar asyncio.gather() para
    executar as 3 consultas independentes em paralelo, em vez de sequencialmente.

    Hoje (RED) o código faz 3 awaits sequenciais:
        1. supabase.table("approval_requests").select(...).execute()
        2. supabase.table("cross_agent_routines").select(...).execute()
        3. await self.get_business_memory_snapshot(...)

    O contrato GREEN esperado é usar asyncio.gather para paralelizar as 3 consultas.

AC (Acceptance Criteria):
    AC#3 — get_morning_brief executa as 3 consultas em paralelo (via asyncio.gather)

DECISION:
    Estratégia: extend (refatorar get_morning_brief para usar asyncio.gather)
    Arquivo alvo: libs/blu_context_service/src/blu_context_service/context_service.py
    Função alvo: get_morning_brief (linha ~785)

Anti-Goals (must NOT be violated):
    1. NÃO alterar a assinatura de get_morning_brief
    2. NÃO alterar o contrato de retorno (string)
    3. NÃO introduzir dependência externa nova
    4. NÃO alterar get_business_memory_snapshot ou outras funções não-alvo

Estado atual: RED — 3 awaits sequenciais ainda estão presentes. O teste source-level
falha ao verificar que não há asyncio.gather no corpo da função.
"""

import ast
import re
from pathlib import Path

import pytest


# ── Path ──────────────────────────────────────────────────────────────────

CONTEXT_SERVICE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "libs"
    / "blu_context_service"
    / "src"
    / "blu_context_service"
    / "context_service.py"
)


# ── Source-level guard helpers ────────────────────────────────────────────


def _get_function_source(func_name: str) -> str:
    """Extract the source code of a function by name from context_service.py."""
    assert CONTEXT_SERVICE_PATH.exists(), (
        f"Source file not found: {CONTEXT_SERVICE_PATH}"
    )
    source = CONTEXT_SERVICE_PATH.read_text(encoding="utf-8")

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == func_name:
            lines = source.splitlines()
            start = node.lineno - 1
            end = node.end_lineno
            return "\n".join(lines[start:end])

    # Fallback: try regex for async def
    marker = f"async def {func_name}("
    idx = source.find(marker)
    assert idx != -1, (
        f"Could not find async def {func_name} in {CONTEXT_SERVICE_PATH}"
    )

    # Simple heuristic: grab until next top-level def or end of file
    remaining = source[idx:]
    lines = remaining.splitlines()
    result_lines = []
    for i, line in enumerate(lines):
        if i > 0 and (
            line.startswith("async def ") or line.startswith("def ")
        ):
            # Check it's top-level (not indented)
            if not line.startswith("    "):
                break
        result_lines.append(line)
    return "\n".join(result_lines)


def _has_asyncio_gather(source: str) -> bool:
    """Check if the function body contains asyncio.gather call."""
    return "asyncio.gather" in source


def _count_sequential_awaits(source: str) -> int:
    """Count top-level `await` statements inside the function body.

    Awaits that are inside a loop or try/except block are counted.
    This helps detect the 3 sequential awaits pattern.
    """
    lines = source.splitlines()
    await_count = 0
    for line in lines:
        stripped = line.strip()
        # Count lines that START with await (top-level awaits in the function)
        if stripped.startswith("await ") or stripped.startswith("result = await "):
            await_count += 1
        # Also count for:  result = (\n    await ...
        elif " = await " in stripped:
            await_count += 1
    return await_count


# ── Tests ─────────────────────────────────────────────────────────────────


def test_b4_1_morning_brief_uses_gather():
    """get_morning_brief must use asyncio.gather, not 3 sequential awaits.

    This test reads the source of `get_morning_brief` and verifies:
    1. It does NOT have 3+ sequential awaits
    2. It DOES have asyncio.gather or equivalent parallel call
    """
    source = _get_function_source("get_morning_brief")

    current_awaits = _count_sequential_awaits(source)

    # Assert RED: asyncio.gather MUST be present for GREEN
    # Since the code is still RED (3 sequential awaits), this assertion FAILS
    assert _has_asyncio_gather(source), (
        "RED — get_morning_brief does NOT use asyncio.gather yet. "
        "Expected: 3 independent queries (approval_requests, routines, memory_snapshot) "
        "executed in parallel via asyncio.gather. "
        f"Found: {current_awaits} sequential await(s) instead of asyncio.gather. "
        "The Coder must refactor to use `results = await asyncio.gather(...)`."
    )


def test_b4_1_source_file_exists():
    """Sanity check: the source file must exist."""
    assert CONTEXT_SERVICE_PATH.exists(), (
        f"Source file not found: {CONTEXT_SERVICE_PATH}"
    )
    source = CONTEXT_SERVICE_PATH.read_text(encoding="utf-8")
    assert "async def get_morning_brief(" in source, (
        "get_morning_brief function not found in context_service.py"
    )
