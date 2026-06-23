"""RED test for behavior B5 — TOOL_INVENTORY.md documents shared_memory_write.

GOAL:
    Implementar auto-linking de entidades nas páginas da shared memory.
    A documentação canônica de tools (TOOL_INVENTORY.md) deve refletir
    a nova tool ``shared_memory_write`` com a flag ``auto_link`` e a
    referência ao item T3.4 do plano de Entity Linking.

BEHAVIOR:
    B5 — Update TOOL_INVENTORY.md with shared_memory_write entry
    A seção 1.1 BUILTIN_TOOLS de ``docs/system_reference/TOOL_INVENTORY.md``
    deve listar a tool ``shared_memory_write`` com:

        | `shared_memory_write` | CUSTOM | SME | memoria/compartilhada | memory_module.py — auto_link: bool = True (T3.4) |

    Em outras palavras, a linha deve:
        1. Conter o slug ``shared_memory_write``.
        2. Mencionar o flag ``auto_link`` (ex: ``auto_link: bool = True``
           ou ``auto_link=True``).
        3. Referenciar o item T3.4 (ex: ``T3.4`` ou ``auto-linking``).
        4. Indicar o módulo de origem (``memory_module.py``).

    Esta é a única fonte de verdade documental para o time; a flag
    ``auto_link`` precisa estar visível em TOOL_INVENTORY.md para que
    engenheiros e agentes saibam que a tool habilita auto-linking por
    padrão.

AC (Acceptance Criteria):
    AC#7 — TOOL_INVENTORY.md lista shared_memory_write com nota de auto_link
           e referência ao T3.4

DECISION:
    Estratégia: extend
    Arquivo alvo: docs/system_reference/TOOL_INVENTORY.md
    Seção alvo: 1.1 BUILTIN_TOOLS (entre os cabeçalhos ``### 1.1 BUILTIN_TOOLS``
                 e ``### 1.2``)

Anti-Goals (must NOT be violated):
    1. NÃO adicionar ``shared_memory_upsert`` à seção 1.1 do
       TOOL_INVENTORY.md. Conforme decisão D5 e ant-goal #3 do B3, a
       tool ``shared_memory_upsert`` continua fora do inventário público
       e não deve ganhar entrada nova como efeito colateral deste B5.
    2. NÃO remover entradas existentes em 1.1.
    3. NÃO modificar seções 1.2 GOOGLE_TOOLS ou 1.3 DOCKER_MCP_TOOLS.
    4. NÃO duplicar a entrada de ``shared_memory_write``.

Estado atual: RED — ``shared_memory_write`` ainda não aparece em
``docs/system_reference/TOOL_INVENTORY.md`` seção 1.1. O teste abre o
arquivo markdown, extrai a seção 1.1 e verifica a presença do slug, da
menção a ``auto_link`` e da referência a ``T3.4``, falhando com
AssertionError até que a feature seja implementada na fase GREEN.
"""

import re
from pathlib import Path

import pytest

# ── Path to the target documentation file ───────────────────────────────

TOOL_INVENTORY_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "docs"
    / "system_reference"
    / "TOOL_INVENTORY.md"
)


# ── Override root conftest cleanup (pure file-based test) ───────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test is pure file inspection, no DB."""
    yield


# ── Helpers: parse the markdown file ────────────────────────────────────


def _extract_section_1_1(content: str) -> str:
    """Return the body of section 1.1 BUILTIN_TOOLS.

    The body is the text between the line ``### 1.1 BUILTIN_TOOLS``
    (inclusive of the section header) and the line that starts with
    ``### 1.2`` (exclusive).  Returns an empty string if either
    boundary is missing.
    """
    header_match = re.search(
        r"^### 1\.1\s+BUILTIN_TOOLS[^\n]*\n", content, re.MULTILINE
    )
    if not header_match:
        return ""
    next_section_match = re.search(
        r"^### 1\.2\s", content[header_match.end() :], re.MULTILINE
    )
    if not next_section_match:
        return ""
    end = header_match.end() + next_section_match.start()
    return content[header_match.start() : end]


def _table_rows(section_body: str) -> list[str]:
    """Return the markdown table rows of section 1.1 (one row per line,
    only lines that look like ``| ... |``).  Header and separator rows
    (``|---|---|``) are filtered out.
    """
    rows: list[str] = []
    for line in section_body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if not stripped.endswith("|"):
            continue
        # Filter out the separator row (e.g. "|------|------|")
        if re.match(r"^\|[\s\-:|]+\|\s*$", stripped):
            continue
        rows.append(stripped)
    return rows


def _row_mentions_slug(row: str, slug: str) -> bool:
    """True if the given markdown table row mentions ``slug`` in its
    first cell (the slug column).  Matches ``| `slug` ... |`` as well
    as any other formatting variant with the slug token adjacent to
    backticks.
    """
    cells = [c.strip() for c in row.strip("|").split("|")]
    if not cells:
        return False
    first_cell = cells[0]
    return bool(re.search(rf"`{re.escape(slug)}`", first_cell)) or (
        first_cell.strip("`") == slug
    )


# ── The single behavior under test ──────────────────────────────────────


def test_b5_tool_inventory_lists_shared_memory_write_with_auto_link_and_t34():
    """TOOL_INVENTORY.md section 1.1 must list ``shared_memory_write`` with
    a note mentioning ``auto_link`` and a reference to ``T3.4``, while
    leaving ``shared_memory_upsert`` out of section 1.1 (anti-goal #1).
    """
    # 1. The documentation file must exist.
    assert TOOL_INVENTORY_PATH.exists(), (
        f"Documentation file not found: {TOOL_INVENTORY_PATH}"
    )

    content = TOOL_INVENTORY_PATH.read_text(encoding="utf-8")

    # 2. Extract section 1.1 BUILTIN_TOOLS.
    section_1_1 = _extract_section_1_1(content)
    assert section_1_1, (
        "Could not locate section 1.1 BUILTIN_TOOLS in TOOL_INVENTORY.md. "
        "Expected a `### 1.1 BUILTIN_TOOLS` header followed by a "
        "`### 1.2` header."
    )

    rows = _table_rows(section_1_1)
    assert rows, "Section 1.1 has no markdown table rows."

    # 3. AC#7 — shared_memory_write must be listed in section 1.1.
    write_rows = [r for r in rows if _row_mentions_slug(r, "shared_memory_write")]
    assert write_rows, (
        "shared_memory_write is missing from section 1.1 BUILTIN_TOOLS of "
        "TOOL_INVENTORY.md. Behavior B5 / AC#7 requires a new table row such "
        "as:\n"
        "    | `shared_memory_write` | CUSTOM | SME | memoria/compartilhada | "
        "memory_module.py — auto_link: bool = True (T3.4) |\n"
    )
    # Sanity: must not be duplicated.
    assert len(write_rows) == 1, (
        f"shared_memory_write appears {len(write_rows)} times in section 1.1. "
        "Behavior B5 / anti-goal #4: do not duplicate the entry."
    )
    write_row = write_rows[0]

    # 4. AC#7 — the row's notes must mention the auto_link flag.
    assert re.search(r"auto_link", write_row), (
        "shared_memory_write row in TOOL_INVENTORY.md section 1.1 must "
        "mention the `auto_link` flag. Expected a note such as "
        "`auto_link: bool = True` or `auto_link=True`. Got row:\n"
        f"    {write_row}"
    )
    # The canonical signature fragment: `auto_link: bool = True`
    # is the same wording the codebase uses for the parameter.
    assert re.search(r"auto_link\s*[:=]\s*bool\s*=\s*True", write_row) or re.search(
        r"auto_link\s*=\s*True", write_row
    ), (
        "shared_memory_write row in TOOL_INVENTORY.md must specify that "
        "auto_link defaults to True (e.g. `auto_link: bool = True` or "
        "`auto_link=True`). Got row:\n"
        f"    {write_row}"
    )

    # 5. AC#7 — the row must reference the T3.4 plan item.
    assert (
        "T3.4" in write_row or "auto-linking" in write_row.lower()
    ), (
        "shared_memory_write row in TOOL_INVENTORY.md must reference the "
        "T3.4 plan item (or use the term `auto-linking`). Got row:\n"
        f"    {write_row}"
    )

    # 6. AC#7 (provenance) — the row must point to memory_module.py so
    #    readers can locate the implementation.  This is a soft
    #    constraint matching the convention of other entries.
    assert "memory_module.py" in write_row, (
        "shared_memory_write row in TOOL_INVENTORY.md must mention the "
        "source module `memory_module.py` (consistent with the other "
        "shared_memory_* entries). Got row:\n"
        f"    {write_row}"
    )

    # 7. Anti-goal #1 — shared_memory_upsert must NOT be added to
    #    section 1.1.  D5 keeps shared_memory_upsert outside the public
    #    inventory; B3's anti-goal #3 forbade the auto_link flag on it;
    #    B5 must not introduce a brand-new row for it either.
    upsert_rows = [r for r in rows if _row_mentions_slug(r, "shared_memory_upsert")]
    assert not upsert_rows, (
        "Anti-goal #1 violated: shared_memory_upsert must NOT be added to "
        "section 1.1 of TOOL_INVENTORY.md. B5 only documents "
        "shared_memory_write. Found row(s):\n"
        + "\n".join(f"    {r}" for r in upsert_rows)
    )
