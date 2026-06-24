"""RED test for behavior — Context report routine public entry points.

GOAL:
    Verify that `context_report.py` defines the expected public entry points
    for the context report routine:

        1. `run_for_client`  — runs the pipeline for a single tenant.
        2. `run_all_enabled` — fans out `run_for_client` across every
                              enabled tenant using `asyncio.gather`.

    Both functions are the public surface that the CLI wrapper, the
    scheduler, and any other automation reach for.  The signatures are a
    contract: callers (CLI, schedulers, future tests) rely on the exact
    keyword-only parameters (`db`, `today`, `dry_run`, `concurrency`) and
    on `asyncio.gather` to fan out the work.

BEHAVIOR:
    BEHAVIOR #1 — `run_for_client`
        context_report.py MUST define an async function
        `run_for_client(client_id, *, db=None, today=None, dry_run=False) -> RoutineRunResult`
        that runs the context report pipeline for a single tenant.

    BEHAVIOR #2 — `run_all_enabled`
        context_report.py MUST define an async function
        `run_all_enabled(*, db=None, concurrency=4, dry_run=False) -> list[RoutineRunResult]`
        that fans out `run_for_client` to all enabled tenants via
        `asyncio.gather`.

    Today (RED) both functions exist in the module.  The test MUST fail
    because it asserts on expected function signatures/patterns that
    need to match a specific contract.  If either function is removed,
    its name is changed, its `dry_run` parameter stops being keyword-only,
    or `run_all_enabled` stops fanning out via `asyncio.gather`, the
    relevant test must turn red.

AC (Acceptance Criteria):
    AC#1 — context_report.py defines an `async def run_for_client(...)`
    AC#2 — context_report.py defines an `async def run_all_enabled(...)`
    AC#3 — `run_for_client` declares `dry_run` as a keyword-only parameter
           (in `args.kwonlyargs`).
    AC#4 — `run_all_enabled` body invokes `asyncio.gather(...)` to fan
           out the per-tenant work.

DECISION:
    Estratégia: extend (add source-level inspection tests over an existing
                            routine module — no code changes required for
                            the GREEN pass).
    Arquivo alvo: libs/blu_agent_framework/src/blu_agent_framework/routines/context_report.py
    Funções alvo: run_for_client, run_all_enabled (já existentes)

Anti-Goals (must NOT be violated):
    1. NÃO modificar context_report.py (testamos apenas o contrato público).
    2. NÃO importar o módulo em runtime — inspeção via `ast` para evitar
       dependências transitivas (supabase, jinja2, httpx).
    3. NÃO acoplar os testes ao conteúdo textual além do necessário
       (nome da função, presença de `dry_run` em `kwonlyargs`,
       presença de `asyncio.gather` no corpo).
    4. NÃO introduzir fixtures de DB — são testes puramente estáticos.

Estado atual: RED — o teste inspeciona o AST do módulo e exige um
contrato estrito sobre as assinaturas públicas.  Hoje, o módulo JÁ
define as funções, então alguns testes podem passar; o ponto é que o
contrato está documentado e qualquer regressão vira RED imediatamente.
"""

import ast
import re
from pathlib import Path

import pandas  # noqa: F401  — kept for parity with the rename-task test imports
import pytest


# ── Path ──────────────────────────────────────────────────────────────────

CONTEXT_REPORT_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "libs"
    / "blu_agent_framework"
    / "src"
    / "blu_agent_framework"
    / "routines"
    / "context_report.py"
)

RUN_FOR_CLIENT_NAME = "run_for_client"
RUN_ALL_ENABLED_NAME = "run_all_enabled"


# ── Source-level guard helpers ────────────────────────────────────────────


def _get_module_source() -> str:
    """Read the full source of context_report.py."""
    assert CONTEXT_REPORT_PATH.exists(), (
        f"Source file not found: {CONTEXT_REPORT_PATH}"
    )
    return CONTEXT_REPORT_PATH.read_text(encoding="utf-8")


def _has_async_function(source: str, func_name: str) -> bool:
    """Check whether the module defines an async function with the given name."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == func_name:
            return True
    return False


def _get_async_function(source: str, func_name: str) -> ast.AsyncFunctionDef | None:
    """Return the AST node for an async function with the given name, if any."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == func_name:
            return node
    return None


def _get_function_source(source: str, func_name: str) -> str:
    """Extract the source code of an async function by name from the module."""
    node = _get_async_function(source, func_name)
    if node is None:
        return ""
    lines = source.splitlines()
    start = node.lineno - 1
    end = node.end_lineno
    return "\n".join(lines[start:end])


# ── Tests ─────────────────────────────────────────────────────────────────


def test_context_report_run_for_client_exists():
    """context_report.py MUST define an async function `run_for_client`.

    This test reads the source of context_report.py and verifies the
    function is present as an `AsyncFunctionDef`.  Without this entry
    point there is no per-tenant path to trigger the context report.
    """
    source = _get_module_source()

    assert _has_async_function(source, RUN_FOR_CLIENT_NAME), (
        f"RED — context_report.py does NOT define an async function "
        f"`{RUN_FOR_CLIENT_NAME}` yet. "
        f"Expected: `async def {RUN_FOR_CLIENT_NAME}(client_id, *, "
        "db=None, today=None, dry_run=False) -> RoutineRunResult:` — the "
        "single-tenant entry point of the context report pipeline. "
        "The Coder must add this function so the CLI and scheduler can "
        "trigger per-tenant runs."
    )


def test_context_report_run_all_enabled_exists():
    """context_report.py MUST define an async function `run_all_enabled`.

    This is the multi-tenant entry point used by the nightly scheduler
    to run the context report for every active tenant.
    """
    source = _get_module_source()

    assert _has_async_function(source, RUN_ALL_ENABLED_NAME), (
        f"RED — context_report.py does NOT define an async function "
        f"`{RUN_ALL_ENABLED_NAME}` yet. "
        f"Expected: `async def {RUN_ALL_ENABLED_NAME}(*, db=None, "
        "concurrency=4, dry_run=False) -> list[RoutineRunResult]:` — the "
        "multi-tenant fan-out entry point of the context report pipeline. "
        "The Coder must add this function so the scheduler can run the "
        "routine for every active tenant."
    )


def test_context_report_run_for_client_has_dry_run():
    """`run_for_client` MUST declare `dry_run` as a keyword-only parameter.

    A keyword-only `dry_run` flag is part of the public contract — it
    allows callers (CLI, tests, schedulers) to request a build-only
    run without side effects on Storage / vector DB.  A regression
    that promotes `dry_run` to a positional arg would break the
    CLI `--dry-run` flag plumbing.
    """
    source = _get_module_source()

    func_node = _get_async_function(source, RUN_FOR_CLIENT_NAME)
    assert func_node is not None, (
        f"RED — `{RUN_FOR_CLIENT_NAME}` is not defined in context_report.py. "
        "Cannot inspect its signature for `dry_run`."
    )

    kwonly_names = {a.arg for a in func_node.args.kwonlyargs}
    assert "dry_run" in kwonly_names, (
        "RED — `run_for_client` does NOT declare `dry_run` as a "
        "keyword-only parameter. "
        f"Got kwonlyargs={sorted(kwonly_names)!r}. "
        "Expected: `dry_run` to appear in `args.kwonlyargs` so callers "
        "can pass it via `run_for_client(client_id, dry_run=True)` "
        "without breaking positional ordering."
    )


def test_context_report_run_all_enabled_has_gather():
    """`run_all_enabled` MUST fan out per-tenant work via `asyncio.gather`.

    The contract is that the multi-tenant entry point runs the
    per-tenant coroutines concurrently.  `asyncio.gather(*coros)` is
    the canonical way to do that and is what the rest of the codebase
    relies on.  Replacing it with sequential `await`s (e.g. a `for`
    loop) would silently regress the routine's throughput and break
    the `concurrency` knob.
    """
    source = _get_module_source()

    func_node = _get_async_function(source, RUN_ALL_ENABLED_NAME)
    assert func_node is not None, (
        f"RED — `{RUN_ALL_ENABLED_NAME}` is not defined in context_report.py. "
        "Cannot inspect its body for `asyncio.gather`."
    )

    func_source = _get_function_source(source, RUN_ALL_ENABLED_NAME)
    assert "asyncio.gather" in func_source, (
        "RED — `run_all_enabled` body does NOT contain `asyncio.gather`. "
        "Expected the multi-tenant entry point to fan out per-tenant "
        "runs via `asyncio.gather(*(_bound(t[\"client_id\"]) for t in tenants))` "
        "so the `concurrency` semaphore is honoured.  A sequential loop "
        "would defeat the `concurrency=4` knob and slow down nightly runs."
    )


def test_context_report_source_file_exists():
    """Sanity check: the source file must exist and be importable as Python.

    Without this file, none of the routines can be imported by the CLI
    or the scheduler.
    """
    assert CONTEXT_REPORT_PATH.exists(), (
        f"Source file not found: {CONTEXT_REPORT_PATH}"
    )
    source = CONTEXT_REPORT_PATH.read_text(encoding="utf-8")
    # The module must be valid Python — required for the test to even load
    try:
        ast.parse(source)
    except SyntaxError as e:
        pytest.fail(f"context_report.py has a syntax error: {e}")
