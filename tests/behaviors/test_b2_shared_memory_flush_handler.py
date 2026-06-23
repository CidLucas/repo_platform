"""RED test for behavior B2 — shared_memory_flush tool registration sem copypaste.

GOAL:
    Implementar exportação de memórias como JSON (com tenant isolation) e
    soft-delete/flush de memórias na shared business memory.

BEHAVIOR:
    B2 — Corrigir shared_memory_flush tool registration: remover copypaste de
    meta_list/export.

    The ``shared_memory_flush`` handler currently contains copypasted blocks
    from ``_shared_memory_meta_list_logic`` (wrong log prefix, premature return)
    and ``_shared_memory_export_logic`` (wrong error messages).  This behavior
    removes both blocks and leaves only the correct call to
    ``_shared_memory_flush_logic``.

    Behavior contract (after fix):
        1. shared_memory_flush handler calls ``_shared_memory_flush_logic``
           (NOT ``_shared_memory_meta_list_logic`` or
           ``_shared_memory_export_logic``).
        2. The log message uses the prefix ``[memory_module] shared_memory_flush``
           (not ``meta_list``).
        3. The error handler logs ``[memory_module] shared_memory_flush failed``
           and raises ``ToolError("Failed to flush shared memory: ...")``.
        4. The ``_shared_memory_flush_logic`` call passes ``client_id``,
           ``entity_type``, ``entity_name`` and ``key``.

AC (Acceptance Criteria):
    AC#8 — Tool registration de flush não tem copypaste de meta_list/export.

DECISION:
    fix_and_extend
    Arquivo alvo: services/tool_pool_api/src/tool_pool_api/server/tool_modules/memory_module.py

Anti-Goals (must NOT be violated):
    1. NÃO alterar _shared_memory_flush_logic (é o behavior B1)
    2. NÃO alterar shared_memory_meta_list ou shared_memory_export tools

Estado atual: RED — o handler shared_memory_flush contém copypaste de
meta_list (chama _shared_memory_meta_list_logic) e export
(chama _shared_memory_export_logic).  O teste falha até que o
copypaste seja removido e reste apenas a chamada a
_shared_memory_flush_logic.
"""

import re
from pathlib import Path

import pytest

# ── Path to the target source file ──────────────────────────────────────

MEMORY_MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "services"
    / "tool_pool_api"
    / "src"
    / "tool_pool_api"
    / "server"
    / "tool_modules"
    / "memory_module.py"
)


# ── Override root conftest cleanup (no real Supabase needed) ───────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test is pure unit, no DB teardown."""
    yield


# ── Helpers: parse the source file ──────────────────────────────────────


def _extract_function_body(source: str, func_name: str) -> str:
    """Return the body text of the first ``async def <func_name>(...)`` found.

    The body is the text after the signature's terminating ':' up to the
    next top-level ``def`` / ``async def`` declaration.  Used to scope
    assertions (e.g. forbidden ``_meta_list_logic`` calls) to the
    correct function in the file.
    """
    pattern = rf"(?:async\s+)?def\s+{re.escape(func_name)}\s*\("
    match = re.search(pattern, source)
    if not match:
        return ""
    # Walk past the matching ')' to find the ':' that closes the header.
    start = match.end()
    depth = 1
    i = start
    while i < len(source) and depth > 0:
        char = source[i]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        i += 1
    # Skip the optional return annotation until the next ':'
    j = i
    while j < len(source) and source[j] != ":":
        j += 1
    body_start = j + 1
    # Body ends at the next 'def' / 'async def' at indentation level 0..4
    next_def = re.search(
        r"^[\s]{0,8}(?:async\s+)?def\s+",
        source[body_start:],
        re.MULTILINE,
    )
    if next_def:
        return source[body_start : body_start + next_def.start()]
    return source[body_start:]


# ── The single behavior under test ──────────────────────────────────────


def test_b2_shared_memory_flush_handler_calls_flush_logic_not_meta_list_or_export():
    """shared_memory_flush handler must call _shared_memory_flush_logic and
    must NOT contain copypasted calls to _shared_memory_meta_list_logic or
    _shared_memory_export_logic.

    AC#8 — Tool registration de flush não tem copypaste de meta_list/export.
    """
    # 1. The source file must exist.
    assert MEMORY_MODULE_PATH.exists(), (
        f"Source file not found: {MEMORY_MODULE_PATH}"
    )

    source = MEMORY_MODULE_PATH.read_text()

    # 2. The handler function must exist.
    handler_body = _extract_function_body(source, "shared_memory_flush")
    assert handler_body, (
        "shared_memory_flush handler is not defined in memory_module.py.\n"
        "Expected:\n"
        "    async def shared_memory_flush(\n"
        "        ctx: Context,\n"
        "        entity_type: str | None = None,\n"
        "        ...\n"
        "    ) -> dict:\n"
    )

    # 3. AC#8 — The handler must call _shared_memory_flush_logic.
    flush_call = re.search(
        r"await\s+_shared_memory_flush_logic\s*\(",
        handler_body,
    )
    assert flush_call, (
        "shared_memory_flush handler body does not call\n"
        "    await _shared_memory_flush_logic(...)\n"
        "AC#8 requires the handler to delegate to the flush logic function.\n"
        "Current body starts with:\n"
        f"    {handler_body[:300].strip()}"
    )

    # 4. AC#8 — The handler must NOT call _shared_memory_meta_list_logic
    #    (copypaste from meta_list tool).
    has_meta_list_call = re.search(
        r"_shared_memory_meta_list_logic",
        handler_body,
    )
    assert not has_meta_list_call, (
        "AC#8 violated: shared_memory_flush handler still contains "
        "a reference to ``_shared_memory_meta_list_logic``.\n"
        "This is copypaste from shared_memory_meta_list.  Remove it so "
        "the handler only calls _shared_memory_flush_logic.\n"
        "Found at:\n"
        f"  ...{handler_body[max(0, has_meta_list_call.start()-60):has_meta_list_call.end()+60]}..."
    )

    # 5. AC#8 — The handler must NOT call _shared_memory_export_logic
    #    (copypaste from export tool).
    has_export_call = re.search(
        r"_shared_memory_export_logic",
        handler_body,
    )
    assert not has_export_call, (
        "AC#8 violated: shared_memory_flush handler still contains "
        "a reference to ``_shared_memory_export_logic``.\n"
        "This is copypaste from shared_memory_export.  Remove it so "
        "the handler only calls _shared_memory_flush_logic.\n"
        "Found at:\n"
        f"  ...{handler_body[max(0, has_export_call.start()-60):has_export_call.end()+60]}..."
    )

    # 6. AC#8 — The log message must use the correct prefix
    #    "[memory_module] shared_memory_flush" (not "meta_list").
    log_matches = re.findall(
        r'logger\.info\([^)]*"\[memory_module\]\s+shared_memory_(\w+)',
        handler_body,
    )
    wrong_prefix = [p for p in log_matches if p.startswith("meta_list")]
    assert not wrong_prefix, (
        "AC#8 violated: shared_memory_flush handler uses log prefix "
        f"'shared_memory_meta_list' (found: {wrong_prefix}).\n"
        "This is copypaste from the meta_list tool.  Use "
        "'[memory_module] shared_memory_flush' instead."
    )
    # At least one log line must reference 'flush' explicitly.
    flush_log = re.search(
        r'logger\.info\([^)]*"\[memory_module\]\s+shared_memory_flush\b',
        handler_body,
    )
    assert flush_log, (
        "AC#8 violated: shared_memory_flush handler does not have a log "
        "message with prefix '[memory_module] shared_memory_flush'.\n"
        "The handler must log its own activity, not copy the meta_list or "
        "export log message."
    )

    # 7. The handler must have proper error handling that catches
    #    ValueError and Exception, with a flush-specific error message.
    has_value_error_handler = re.search(
        r"except\s+ValueError\s+as\s+exc:\s*\n\s*raise\s+ToolError\(",
        handler_body,
    )
    assert has_value_error_handler, (
        "shared_memory_flush handler must catch ``ValueError as exc`` and "
        "re-raise as ``ToolError(str(exc))``.\n"
        "Expected pattern:\n"
        "    except ValueError as exc:\n"
        "        raise ToolError(str(exc))\n"
        "Current handler body:\n"
        f"    {handler_body[:400]}"
    )

    # 8. The handler must NOT contain copypasted error messages
    #    from export or meta_list.
    has_forbidden_export_error = re.search(
        r"Failed to export shared memory", handler_body
    )
    assert not has_forbidden_export_error, (
        "AC#8 violated: shared_memory_flush handler still contains "
        "the export error message 'Failed to export shared memory'.\n"
        "This is copypaste from shared_memory_export.  Remove it and use "
        "'Failed to flush shared memory' instead."
    )
    has_forbidden_list_error = re.search(
        r"Failed to list shared-memory-meta", handler_body
    )
    assert not has_forbidden_list_error, (
        "AC#8 violated: shared_memory_flush handler still contains "
        "the meta_list error message 'Failed to list shared-memory-meta'.\n"
        "This is copypaste from shared_memory_meta_list.  Remove it and use "
        "'Failed to flush shared memory' instead."
    )

    # 9. The handler must have a flush-specific Exception handler.
    has_exception_handler = re.search(
        r'except\s+Exception\s+as\s+exc:.*?'
        r'logger\.error\([^)]*"\[memory_module\]\s+shared_memory_flush\b',
        handler_body,
        re.DOTALL,
    )
    assert has_exception_handler, (
        "shared_memory_flush handler must catch ``Exception as exc``, log\n"
        "    [memory_module] shared_memory_flush failed: ...\n"
        "and raise\n"
        "    ToolError(\"Failed to flush shared memory: {exc}\")\n"
        "Current handler body:\n"
        f"    {handler_body[:500]}"
    )

    # 10. The call to _shared_memory_flush_logic must forward the four
    #     required keyword arguments.
    call_site_match = re.search(
        r"await\s+_shared_memory_flush_logic\s*\(",
        handler_body,
    )
    assert call_site_match, (
        "Could not isolate the _shared_memory_flush_logic call site."
    )
    # Extract the arguments from the opening ( to the matching closing )
    start = call_site_match.end()
    depth = 1
    i = start
    while i < len(handler_body) and depth > 0:
        char = handler_body[i]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        i += 1
    call_site = handler_body[start : i - 1]
    for arg in ("client_id", "entity_type", "entity_name", "key"):
        assert re.search(
            rf"\b{re.escape(arg)}\s*=", call_site
        ), (
            f"_shared_memory_flush_logic() call inside shared_memory_flush "
            f"must forward `{arg}=`. Got call site:\n    ({call_site})"
        )
