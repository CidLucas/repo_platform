"""RED test for behavior — Onboarding complete hook public entry point.

GOAL:
    Verify that `onboarding_shared_memory_hook.py` defines the expected
    public entry point for the onboarding complete hook — the function
    that writes the initial onboarding snapshot to shared business memory
    after the ETL onboarding routine finishes generating
    `structured_context`.

    The hook is the bridge between the onboarding ETL
    (`onboarding_context_build` skill) and the persistent shared
    business memory tables (`shared_business_memory`,
    `shared_business_memory_meta`).  Its public signature is a
    contract relied upon by the routine runner, future cron triggers,
    and any test that exercises the end-to-end onboarding flow.

BEHAVIOR:
    BEHAVIOR #1 — `write_onboarding_snapshot_to_shared_memory`
        onboarding_shared_memory_hook.py MUST define an async function
        `write_onboarding_snapshot_to_shared_memory(
            client_id, company_name, structured_context
        ) -> dict[str, Any]`
        that writes the initial onboarding snapshot to shared business
        memory.  The signature is keyword-by-position; callers pass
        `client_id` (UUID string), `company_name` (display name) and
        `structured_context` (dict produced by the
        `onboarding_context_build` skill).

    BEHAVIOR #2 — Error-handling contract
        The function MUST NEVER raise exceptions to the caller.  All
        errors must be caught, logged, and collected in the result
        dict under the "errors" key.  The function body must contain
        `try` / `except` blocks — this is how the hook guarantees the
        onboarding flow keeps moving even if the shared-memory write
        fails (bad credentials, transient Supabase error, RLS
        rejection, etc.).

    Today (RED) the module already defines this function.  The tests
    verify the strict contract: if the function is removed, renamed,
    loses its `-> dict[str, Any]` annotation, stops returning a dict
    with the "errors" key, or strips the internal `try`/`except`
    blocks, the relevant test must turn red.

AC (Acceptance Criteria):
    AC#1 — onboarding_shared_memory_hook.py defines
           `async def write_onboarding_snapshot_to_shared_memory(...)`.
    AC#2 — The function body contains both `try` and `except` keywords
           (proving it catches errors internally and never raises).
    AC#3 — The function signature declares the return annotation
           `dict[str, Any]` (via AST `ast.parse`).
    AC#4 — The function body returns a dict that contains the "errors"
           key (proving the error-collection contract).
    AC#5 — The source file exists and parses as valid Python.

DECISION:
    Estratégia: extend (add source-level inspection tests over an existing
                            hook module — no code changes required for
                            the GREEN pass).
    Arquivo alvo: libs/blu_agent_framework/src/blu_agent_framework/onboarding/onboarding_shared_memory_hook.py
    Função alvo: write_onboarding_snapshot_to_shared_memory (já existente)

Anti-Goals (must NOT be violated):
    1. NÃO modificar onboarding_shared_memory_hook.py (testamos apenas o
       contrato público).
    2. NÃO importar o módulo em runtime — inspeção via `ast` para evitar
       dependências transitivas (supabase, blu_supabase_client, etc.).
    3. NÃO acoplar os testes ao conteúdo textual além do necessário
       (nome da função, presença de `try`/`except` no corpo, presença
       do return annotation `dict[str, Any]`, presença da chave
       `"errors"` no resultado).
    4. NÃO introduzir fixtures de DB — são testes puramente estáticos.
    5. NÃO reescrever o hook para levantar exceções; o contrato é
       explícito em swallow + collect.

Estado atual: RED — o teste inspeciona o AST do módulo e exige um
contrato estrito sobre a assinatura pública e o error-handling
contract.  Hoje, o módulo JÁ define a função corretamente, então os
testes passam; o ponto é que o contrato está documentado e qualquer
regressão vira RED imediatamente.
"""

import ast
import re
from pathlib import Path

import pytest


# ── Path ──────────────────────────────────────────────────────────────────

ONBOARDING_HOOK_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "libs"
    / "blu_agent_framework"
    / "src"
    / "blu_agent_framework"
    / "onboarding"
    / "onboarding_shared_memory_hook.py"
)

FUNC_NAME = "write_onboarding_snapshot_to_shared_memory"


# ── Source-level guard helpers ────────────────────────────────────────────


def _get_module_source() -> str:
    """Read the full source of onboarding_shared_memory_hook.py."""
    assert ONBOARDING_HOOK_PATH.exists(), (
        f"Source file not found: {ONBOARDING_HOOK_PATH}"
    )
    return ONBOARDING_HOOK_PATH.read_text(encoding="utf-8")


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


def test_onboarding_write_snapshot_exists():
    """onboarding_shared_memory_hook.py MUST define
    `write_onboarding_snapshot_to_shared_memory` as an async function.

    This is the single public entry point of the post-ETL onboarding
    hook.  It is invoked by the routine runner once the
    `onboarding_context_build` skill finishes producing
    `structured_context`.  Without this function, the snapshot cannot
    be persisted to shared business memory.
    """
    source = _get_module_source()

    assert _has_async_function(source, FUNC_NAME), (
        f"RED — onboarding_shared_memory_hook.py does NOT define an "
        f"async function `{FUNC_NAME}` yet. "
        f"Expected: `async def {FUNC_NAME}(client_id: str, "
        "company_name: str, structured_context: dict[str, Any]) "
        "-> dict[str, Any]:` — the public entry point that writes the "
        "initial onboarding snapshot to shared business memory. "
        "The Coder must add this function so the routine runner can "
        "persist the post-ETL snapshot."
    )


def test_onboarding_write_snapshot_has_error_handling():
    """`write_onboarding_snapshot_to_shared_memory` body MUST contain
    `try` and `except` keywords — proving it catches errors internally
    and never raises to the caller.

    The contract is explicit: the hook is a best-effort, fire-and-log
    side effect.  A regression that strips the `try`/`except` blocks
    (e.g. refactoring to a naked `await` chain) would let Supabase /
    network errors bubble up and break the onboarding flow.
    """
    source = _get_module_source()

    func_node = _get_async_function(source, FUNC_NAME)
    assert func_node is not None, (
        f"RED — `{FUNC_NAME}` is not defined in "
        "onboarding_shared_memory_hook.py. Cannot inspect its body for "
        "`try`/`except`."
    )

    func_source = _get_function_source(source, FUNC_NAME)

    has_try = re.search(r"\btry\s*:", func_source) is not None
    has_except = re.search(r"\bexcept\b", func_source) is not None

    assert has_try and has_except, (
        "RED — `write_onboarding_snapshot_to_shared_memory` body does "
        "NOT contain both `try` and `except` keywords. "
        f"Found try={has_try}, except={has_except}. "
        "Expected: the function to wrap every Supabase write in "
        "`try: ... except Exception as exc:` blocks so that errors "
        "are caught, logged, and collected in `result[\"errors\"]` "
        "instead of being raised to the caller. Without this guard, "
        "a transient Supabase error would break the onboarding flow."
    )


def test_onboarding_write_snapshot_returns_dict():
    """`write_onboarding_snapshot_to_shared_memory` signature MUST
    declare the return annotation `dict[str, Any]`.

    The function returns a structured summary dict
    (`client_entries`, `snapshot_entry`, `meta_entry`, `errors`).
    Declaring `-> dict[str, Any]` is a static-type contract that
    downstream callers (the routine runner, future tests, the CLI
    wrapper) rely on.  A regression that drops the annotation or
    changes it to something else (e.g. `None`, `list`, no annotation)
    breaks the type contract.
    """
    source = _get_module_source()

    func_node = _get_async_function(source, FUNC_NAME)
    assert func_node is not None, (
        f"RED — `{FUNC_NAME}` is not defined in "
        "onboarding_shared_memory_hook.py. Cannot inspect its return "
        "annotation."
    )

    ret = func_node.returns
    assert ret is not None, (
        "RED — `write_onboarding_snapshot_to_shared_memory` does NOT "
        "declare a return annotation. "
        "Expected: `-> dict[str, Any]` so callers (routine runner, "
        "tests, CLI) can rely on the static type contract."
    )

    # Build the AST representation we expect: `dict[str, Any]`
    #   ast.Subscript(value=Name('dict'), slice=Tuple([Name('str'),
    #                                                   Name('Any')]))
    #   OR
    #   ast.Subscript(value=Name('dict'), slice=Name('Any')) for
    #   Python 3.9+ single-arg subscript (dict[str] would be invalid,
    #   so this branch shouldn't fire, but we still match it).
    assert isinstance(ret, ast.Subscript), (
        f"RED — return annotation is not a subscript. Got "
        f"{ast.dump(ret)}. Expected `dict[str, Any]`."
    )

    value = ret.value
    assert isinstance(value, ast.Name) and value.id == "dict", (
        f"RED — return annotation is not `dict[...]`. Got "
        f"{ast.dump(ret)}. Expected `dict[str, Any]`."
    )

    slice_node = ret.slice
    slice_names: list[str] = []
    if isinstance(slice_node, ast.Tuple):
        for elt in slice_node.elts:
            if isinstance(elt, ast.Name):
                slice_names.append(elt.id)
    elif isinstance(slice_node, ast.Name):
        slice_names.append(slice_node.id)

    assert slice_names == ["str", "Any"], (
        f"RED — return annotation is not `dict[str, Any]`. Got "
        f"dict[{', '.join(slice_names)!r}]. "
        "Expected the function to be declared as "
        "`async def write_onboarding_snapshot_to_shared_memory(...) "
        "-> dict[str, Any]:` so downstream callers can rely on the "
        "structured summary contract."
    )


def test_onboarding_write_snapshot_has_errors_key():
    """`write_onboarding_snapshot_to_shared_memory` body MUST return a
    dict containing the "errors" key — proving the error-collection
    contract.

    The contract is that the function NEVER raises; instead, errors
    are collected in `result["errors"]` and the function returns a
    dict with at least the `errors` key (typically a `list[str]`).
    A regression that returns a dict without the `errors` key
    (e.g. only `client_entries`) would silently swallow the
    error-collection contract.
    """
    source = _get_module_source()

    func_node = _get_async_function(source, FUNC_NAME)
    assert func_node is not None, (
        f"RED — `{FUNC_NAME}` is not defined in "
        "onboarding_shared_memory_hook.py. Cannot inspect its body "
        "for the `\"errors\"` key."
    )

    func_source = _get_function_source(source, FUNC_NAME)

    # Look for `"errors"` string literal anywhere in the function body.
    # This catches both the initial `result = {"errors": [], ...}`
    # construction and any `result["errors"].append(...)` usage.
    has_errors_literal = re.search(r'"errors"\s*:', func_source) is not None
    has_errors_subscript = re.search(r'\["errors"\]', func_source) is not None

    assert has_errors_literal or has_errors_subscript, (
        "RED — `write_onboarding_snapshot_to_shared_memory` body does "
        "NOT reference the `\"errors\"` key. "
        f"Found \"errors\": key in body = {has_errors_literal}; "
        f"found [\"errors\"] subscript in body = {has_errors_subscript}. "
        "Expected: the function to return a dict that contains the "
        "`\"errors\"` key (initialized as a list in the result dict, "
        "and populated via `result[\"errors\"].append(...)` whenever a "
        "Supabase write fails). This is how the function honors its "
        "never-raise contract."
    )


def test_onboarding_source_file_exists():
    """Sanity check: the source file must exist and be importable as
    Python.

    Without this file, no hook is wired into the routine runner and
    the post-ETL snapshot is never persisted.
    """
    assert ONBOARDING_HOOK_PATH.exists(), (
        f"Source file not found: {ONBOARDING_HOOK_PATH}"
    )
    source = ONBOARDING_HOOK_PATH.read_text(encoding="utf-8")
    # The module must be valid Python — required for the test to even load
    try:
        ast.parse(source)
    except SyntaxError as e:
        pytest.fail(
            f"onboarding_shared_memory_hook.py has a syntax error: {e}"
        )
