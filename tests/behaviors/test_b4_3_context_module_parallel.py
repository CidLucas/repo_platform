"""RED test for behavior B4.3 — Sequential counts in context_module.py.

GOAL:
    Corrigir 4 bottlenecks P1 no código de produção. Issue #121 — Performance.
    A funcao list_data_sources em context_module.py atualmente faz 4 chamadas
    `await _count(table)` sequencialmente para contar linhas de fato_transacoes,
    dim_clientes, dim_fornecedores, dim_inventory — cada count é um round-trip DB
    separado que soma latência.

BEHAVIOR:
    B4.3 — list_data_sources deve usar asyncio.gather() para executar os 4 counts
    em paralelo, em vez de sequencialmente.

    Hoje (RED) o código faz:
        counts = {
            "fato_transacoes": await _count("fato_transacoes"),
            "dim_clientes": await _count("dim_clientes"),
            "dim_fornecedores": await _count("dim_fornecedores"),
            "dim_inventory": await _count("dim_inventory"),
        }

    O contrato GREEN esperado é:
        table_names = ["fato_transacoes", "dim_clientes", "dim_fornecedores", "dim_inventory"]
        results = await asyncio.gather(
            *(_count(t) for t in table_names),
            return_exceptions=True
        )
        counts = dict(zip(table_names, results))

AC (Acceptance Criteria):
    AC#3 — list_data_sources executa 4 counts em paralelo (via asyncio.gather)

DECISION:
    Estratégia: extend (refatorar list_data_sources para usar asyncio.gather)
    Arquivo alvo: services/tool_pool_api/src/tool_pool_api/server/tool_modules/context_module.py
    Função alvo: list_data_sources (linha ~260)

Anti-Goals (must NOT be violated):
    1. NÃO alterar a assinatura de list_data_sources
    2. NÃO alterar o contrato de retorno (dict com row_counts + recent_ingestion_jobs + summary)
    3. NÃO introduzir dependência externa nova
    4. NÃO alterar as funções helpers ou outras funções não-alvo

Estado atual: RED — 4 awaits sequenciais ainda estão presentes no dict literal.
O teste source-level falha ao verificar que não há asyncio.gather no corpo.
"""

import ast
import re
from pathlib import Path

import pytest


# ── Path ──────────────────────────────────────────────────────────────────

FUNC_NAME = "_list_data_sources_logic"

CONTEXT_MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "services"
    / "tool_pool_api"
    / "src"
    / "tool_pool_api"
    / "server"
    / "tool_modules"
    / "context_module.py"
)


# ── Source-level guard helpers ────────────────────────────────────────────


def _get_function_source(func_name: str = FUNC_NAME) -> str:
    """Extract the source code of a function by name from context_module.py."""
    assert CONTEXT_MODULE_PATH.exists(), (
        f"Source file not found: {CONTEXT_MODULE_PATH}"
    )
    source = CONTEXT_MODULE_PATH.read_text(encoding="utf-8")

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == func_name:
            lines = source.splitlines()
            start = node.lineno - 1
            end = node.end_lineno
            return "\n".join(lines[start:end])

    # Fallback: regex
    marker = f"async def {func_name}("
    idx = source.find(marker)
    assert idx != -1, (
        f"Could not find async def {func_name} in {CONTEXT_MODULE_PATH}"
    )

    # Heuristic: grab until next top-level def
    remaining = source[idx:]
    lines = remaining.splitlines()
    result_lines = []
    for i, line in enumerate(lines):
        if i > 0 and (
            line.startswith("async def ") or line.startswith("def ")
            or line.startswith("@")
        ):
            if not line.startswith("    "):
                break
        result_lines.append(line)
    return "\n".join(result_lines)


def _has_asyncio_gather(source: str) -> bool:
    """Check if the function body contains asyncio.gather call."""
    return "asyncio.gather" in source


def _count_dict_await_patterns(source: str) -> int:
    """Count sequential await calls inside dict literal patterns.

    Detects patterns like:
        "key": await _count("table"),
    """
    # Count lines with `await _count(` after a colon
    pattern = r':\s*await\s+_count\('
    matches = re.findall(pattern, source)
    return len(matches)


# ── Tests ─────────────────────────────────────────────────────────────────


def test_b4_3_list_data_sources_uses_gather():
    """_list_data_sources_logic must use asyncio.gather, not 4 sequential counts.

    This test reads the source of `_list_data_sources_logic` and verifies:
    1. It does NOT have 4 sequential await _count() calls
    2. It DOES have asyncio.gather or equivalent parallel call
    """
    source = _get_function_source()

    dict_awaits = _count_dict_await_patterns(source)

    # Assert RED: asyncio.gather MUST be present for GREEN
    # Since the code is still RED (4 sequential counts), this assertion FAILS
    assert _has_asyncio_gather(source), (
        "RED — _list_data_sources_logic does NOT use asyncio.gather yet. "
        "Expected: 4 table counts (fato_transacoes, dim_clientes, dim_fornecedores, "
        "dim_inventory) executed in parallel via asyncio.gather. "
        f"Found: {dict_awaits} sequential await _count() call(s) instead of asyncio.gather. "
        "The Coder must refactor to use `results = await asyncio.gather(*(_count(t) for t in tables))`."
    )


def test_b4_3_source_file_exists():
    """Sanity check: the source file must exist."""
    assert CONTEXT_MODULE_PATH.exists(), (
        f"Source file not found: {CONTEXT_MODULE_PATH}"
    )
    source = CONTEXT_MODULE_PATH.read_text(encoding="utf-8")
    assert f"async def {FUNC_NAME}(" in source, (
        f"{FUNC_NAME} function not found in context_module.py"
    )
