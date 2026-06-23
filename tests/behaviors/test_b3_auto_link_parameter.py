"""RED test for behavior B3 — auto_link parameter on shared_memory_write.

GOAL:
    Implementar auto-linking de entidades nas páginas da shared memory.
    When a memory entry is written via shared_memory_write, entity references
    [label](entity_type:name) in its value should be automatically converted
    into semantic links via _auto_create_links, controlled by an auto_link
    parameter (default True).

BEHAVIOR:
    B3 — Add auto_link parameter to shared_memory_write
    The tool ``shared_memory_write`` and its underlying logic function
    ``_shared_memory_write_logic`` must both expose a new keyword-only-style
    parameter::

        auto_link: bool = True

    Behavior contract:
        1. shared_memory_write tool accepts auto_link: bool = True
        2. _shared_memory_write_logic accepts auto_link: bool = True
        3. shared_memory_write passes auto_link through to the logic call
        4. After a successful write, shared_memory_write invokes
           _auto_create_links(client_id, entity_type, entity_name, value)
           to create semantic links from entity references.
        5. auto_link=False disables the call without breaking the write.

AC (Acceptance Criteria):
    AC#3 — shared_memory_write aceita parâmetro auto_link: bool = True e chama
           _auto_create_links após write bem-sucedido
    AC#4 — auto_link=False desativa a criação automática de links sem quebrar
           o write

DECISION:
    Estratégia: extend
    Arquivo alvo: services/tool_pool_api/src/tool_pool_api/server/tool_modules/memory_module.py
    Estender: _shared_memory_write_logic e a tool shared_memory_write (dentro
    do bloco register_module) com auto_link: bool = True.

Anti-Goals (must NOT be violated):
    1. NÃO modificar a constraint uq_shared_memory_link
    2. NÃO alterar o schema da tabela shared_memory_links
    3. NÃO modificar shared_memory_upsert ou outras tools de escrita
       (anti-goal #3: shared_memory_upsert must NOT get auto_link param)
    4. NÃO implementar confirmação humana

Estado atual: RED — nem shared_memory_write nem _shared_memory_write_logic
possuem o parâmetro auto_link. O teste busca auto_link: bool = True nas
respectivas assinaturas e valida a chamada de _auto_create_links dentro do
corpo da tool shared_memory_write, falhando com AssertionError até que a
feature seja implementada na fase GREEN.
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


def _extract_params(source: str, func_name: str) -> str:
    """Return the raw parameter-list text of ``def <func_name>(...)``.

    Returns an empty string if the function is not found. The returned
    substring is the text between the opening ``(`` and the matching
    closing ``)`` of the function header (multi-line signatures supported).
    """
    pattern = rf"\bdef\s+{re.escape(func_name)}\s*\("
    match = re.search(pattern, source)
    if not match:
        return ""
    start = match.end()  # position right after the opening '('
    depth = 1
    i = start
    while i < len(source) and depth > 0:
        char = source[i]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        i += 1
    return source[start : i - 1]


def _extract_function_body(source: str, func_name: str) -> str:
    """Return the body text of the first ``def <func_name>(...)`` found.

    The body is the text after the signature's terminating ':' up to the
    next top-level ``def`` / ``async def`` declaration.  Used to scope
    assertions (e.g. ``_auto_create_links(...)`` invocation) to the
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


def test_b3_shared_memory_write_must_accept_auto_link_parameter():
    """shared_memory_write tool + _shared_memory_write_logic must expose
    ``auto_link: bool = True`` and call _auto_create_links after a
    successful write, while leaving shared_memory_upsert and
    shared_memory_meta_upsert untouched (anti-goal #3).
    """
    # 1. The source file must exist.
    assert MEMORY_MODULE_PATH.exists(), (
        f"Source file not found: {MEMORY_MODULE_PATH}"
    )

    source = MEMORY_MODULE_PATH.read_text()

    # 2. AC#3 — _shared_memory_write_logic must declare auto_link: bool = True.
    logic_params = _extract_params(source, "_shared_memory_write_logic")
    assert logic_params, (
        "_shared_memory_write_logic is not defined in memory_module.py."
    )
    assert "auto_link" in logic_params, (
        "_shared_memory_write_logic is missing the `auto_link` parameter. "
        "Behavior B3 requires:\n"
        "    async def _shared_memory_write_logic(\n"
        "        ...\n"
        "        ttl_tier: str | None = None,\n"
        "        auto_link: bool = True,        # ← add this\n"
        "    ) -> dict:\n"
    )
    # Match the canonical signature fragment: `auto_link: bool = True`
    assert re.search(
        r"auto_link\s*:\s*bool\s*=\s*True", logic_params
    ), (
        "_shared_memory_write_logic declares `auto_link` but its annotation "
        "or default does not match `auto_link: bool = True`."
    )

    # 3. AC#3 — shared_memory_write tool must declare auto_link: bool = True.
    tool_params = _extract_params(source, "shared_memory_write")
    assert tool_params, (
        "shared_memory_write tool function is not defined in memory_module.py."
    )
    assert "auto_link" in tool_params, (
        "shared_memory_write tool is missing the `auto_link` parameter. "
        "Behavior B3 requires the tool to expose:\n"
        "    async def shared_memory_write(\n"
        "        ...\n"
        "        client_id: str | None = None,\n"
        "        auto_link: bool = True,        # ← add this\n"
        "    ) -> dict:\n"
    )
    assert re.search(
        r"auto_link\s*:\s*bool\s*=\s*True", tool_params
    ), (
        "shared_memory_write tool declares `auto_link` but its annotation "
        "or default does not match `auto_link: bool = True`."
    )

    # 4. AC#3 — The tool must invoke _auto_create_links after a successful
    #    write, passing (client_id, entity_type, entity_name, value).
    tool_body = _extract_function_body(source, "shared_memory_write")
    assert tool_body, "Could not extract body of shared_memory_write tool."

    auto_link_call = re.search(
        r"await\s+_auto_create_links\s*\(",
        tool_body,
    )
    assert auto_link_call, (
        "shared_memory_write tool body does not call `await "
        "_auto_create_links(...)`. Behavior B3 / AC#3 requires the tool "
        "to invoke _auto_create_links after a successful write to create "
        "semantic links from entity references found in `value`."
    )

    # The call site must forward the four required arguments.
    call_window = tool_body[auto_link_call.start() : auto_link_call.start() + 600]
    call_window = call_window.split(")", 1)[0] + ")"
    for arg in ("client_id", "entity_type", "entity_name", "value"):
        assert re.search(
            rf"{re.escape(arg)}\s*=", call_window
        ), (
            f"_auto_create_links() call inside shared_memory_write must "
            f"forward `{arg}=` to the helper. Got call site:\n{call_window}"
        )

    # 5. AC#3 — The tool must pass auto_link through to the logic function.
    #    Verify the call to _shared_memory_write_logic inside the tool body
    #    includes `auto_link=auto_link` so the default propagates.
    logic_call = re.search(
        r"await\s+_shared_memory_write_logic\s*\(",
        tool_body,
    )
    assert logic_call, (
        "shared_memory_write tool body does not call "
        "_shared_memory_write_logic()."
    )
    logic_call_window = tool_body[
        logic_call.start() : logic_call.start() + 1200
    ]
    logic_call_window = logic_call_window.split(")", 1)[0] + ")"
    assert re.search(
        r"auto_link\s*=\s*auto_link", logic_call_window
    ), (
        "shared_memory_write tool must pass `auto_link=auto_link` to "
        "_shared_memory_write_logic() so the parameter is propagated. "
        f"Got call site:\n{logic_call_window}"
    )

    # 6. Anti-goal #3 — shared_memory_upsert must NOT gain auto_link.
    upsert_params = _extract_params(source, "shared_memory_upsert")
    assert upsert_params, (
        "shared_memory_upsert tool is not defined in memory_module.py."
    )
    assert "auto_link" not in upsert_params, (
        "Anti-goal #3 violated: shared_memory_upsert must NOT receive the "
        "`auto_link` parameter. Behavior B3 only extends shared_memory_write."
    )

    # 7. Anti-goal #3 — shared_memory_meta_upsert must NOT gain auto_link.
    meta_upsert_params = _extract_params(source, "shared_memory_meta_upsert")
    assert meta_upsert_params, (
        "shared_memory_meta_upsert tool is not defined in memory_module.py."
    )
    assert "auto_link" not in meta_upsert_params, (
        "Anti-goal #3 violated: shared_memory_meta_upsert must NOT receive "
        "the `auto_link` parameter. Behavior B3 only extends "
        "shared_memory_write."
    )
