"""RED test for behavior B2 — _auto_create_links function in memory_module.py.

GOAL:
    Implementar auto-linking de entidades nas páginas da shared memory.
    When a memory entry is written, entity references [label](entity_type:name)
    in its markdown value are automatically converted into semantic links.

BEHAVIOR:
    B2 — _auto_create_links function in memory_module.py
    Creates links with source=system, confidence=1.0 for each entity reference
    found via _extract_entity_references in the value string.

    Signature:
        async def _auto_create_links(
            client_id: str,
            entity_type: str,
            entity_name: str,
            value: str,
            metadata: dict | None = None,
        ) -> dict:

    Steps:
        1. Serializes value to string
        2. Calls _extract_entity_references(value) to find [label](type:name)
        3. For each reference, creates a link via _shared_memory_link_logic
           with source="system", confidence=1.0, link_type="references"
        4. Updates last_auto_link_at and auto_link_count on the source entity
        5. Ignores duplicates (uq_shared_memory_link) silently

AC (Acceptance Criteria):
    AC#2 — _auto_create_links() varre o value de um fato escrito e cria links
           source=system para cada referência encontrada via _extract_entity_references
    AC#5 — Duplicatas (uq_shared_memory_link) são ignoradas silenciosamente

DECISION:
    Estratégia: create_new
    Arquivo alvo: services/tool_pool_api/src/tool_pool_api/server/tool_modules/memory_module.py

Estado atual: RED — a função _auto_create_links ainda não existe; o teste busca a string
"def _auto_create_links" no source de memory_module.py e falha com AssertionError
até que a função seja implementada na fase GREEN.
"""

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


# ── Helper: check function exists in source ─────────────────────────────


def _function_exists_in_source(source: str, func_name: str) -> bool:
    """Check whether ``def <func_name>(`` appears in the source file."""
    marker = f"def {func_name}("
    return marker in source


# ── The single behavior under test ──────────────────────────────────────


def test_b2_auto_create_links_function_must_exist():
    """_auto_create_links() must be defined in memory_module.py.

    This test fails (RED) because the function has not been implemented yet.
    It validates:
    - The function will accept (client_id, entity_type, entity_name, value, metadata)
    - It will call _extract_entity_references(value) to scan for entity references
    - For each reference found, it will create a semantic link via
      _shared_memory_link_logic with source='system' and confidence=1.0
    - It will update last_auto_link_at and auto_link_count on the source entity
    - Duplicate-link exceptions (uq_shared_memory_link) will be caught silently
    """
    # 1. The source file must exist
    assert MEMORY_MODULE_PATH.exists(), (
        f"Source file not found: {MEMORY_MODULE_PATH}"
    )

    source = MEMORY_MODULE_PATH.read_text()

    # 2. The function _auto_create_links must be defined
    #    This assertion fails (RED) because the function does not exist yet.
    assert _function_exists_in_source(source, "_auto_create_links"), (
        "_auto_create_links() is not defined in memory_module.py. "
        "Behavior B2 requires an async function with signature:\n"
        "    async def _auto_create_links(\n"
        "        client_id: str,\n"
        "        entity_type: str,\n"
        "        entity_name: str,\n"
        "        value: str,\n"
        "        metadata: dict | None = None,\n"
        "    ) -> dict:\n"
        "\n"
        "Steps the function must implement:\n"
        "    1. Serialize value to string (if not already)\n"
        "    2. Call _extract_entity_references(value) to find [label](type:name)\n"
        "    3. For each reference, call _shared_memory_link_logic with\n"
        "       source='system', confidence=1.0, link_type='references'\n"
        "    4. Update last_auto_link_at=now() and auto_link_count+=1\n"
        "       on the source entity's row in shared_business_memory\n"
        "    5. Catch duplicate-key exceptions silently\n"
    )

    # 3. Verify the function is async (starts with 'async def')
    lines = source.split("\n")
    func_lines = [
        i for i, line in enumerate(lines)
        if f"async def _auto_create_links(" in line
    ]
    assert len(func_lines) == 1, (
        "_auto_create_links must be declared as an async function "
        "(exactly one 'async def _auto_create_links(' declaration expected, "
        f"found {len(func_lines)})."
    )
