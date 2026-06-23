"""RED test for behavior B4 — Document auto-linking in SHARED_MEMORY_DESIGN.md §7.

GOAL:
    Documentar na seção 7 do SHARED_MEMORY_DESIGN.md todo o mecanismo de
    auto-linking de entidades: tracking columns, parâmetro ``auto_link``,
    fluxo de funções, convenção de ``source``/``confidence`` e tratamento
    de duplicatas. A documentação atual da seção 7 é apenas conceitual e
    não cobre os detalhes de implementação introduzidos pelas Behaviors
    B1, B2 e B3.

BEHAVIOR:
    B4 — Document auto-linking in SHARED_MEMORY_DESIGN.md section 7
    (Issue #28, Fase 3). A seção "## 7. Entity Linking" deve documentar,
    de forma executável e verificável, todos os componentes do pipeline
    de auto-linking:

        1. Tracking columns adicionadas à ``shared_business_memory``:
               last_auto_link_at  TIMESTAMPTZ  (nullable)
               auto_link_count    INTEGER      DEFAULT 0
        2. Parâmetro ``auto_link: bool = True`` em ``shared_memory_write``
        3. Fluxo completo:
               shared_memory_write
                   → _auto_create_links
                   → _extract_entity_references
                   → _shared_memory_link_logic
        4. Convenção ``source="system"`` e ``confidence=1.0`` para links
           criados automaticamente
        5. Tratamento silencioso de duplicatas via
           ``uq_shared_memory_link``
        6. ``auto_link=False`` desativa a criação automática de links
           sem quebrar o write

AC (Acceptance Criteria):
    AC#6 — SHARED_MEMORY_DESIGN.md seção 7 documenta colunas tracking,
           parâmetro auto_link e fluxo _auto_create_links. Cada item
           acima deve ser verificável por inspeção textual da seção 7
           (substring/regex match).

DECISÃO:
    Estratégia: extend
    Arquivo alvo: docs/llm_wiki/SHARED_MEMORY_DESIGN.md
    Seção alvo:  ## 7. Entity Linking
    Não criar novo arquivo: o cabeçalho "## 7. Entity Linking" já
    existe (linha 794) com 4 sub-seções (7.1–7.4). Esta behavior EXTENDE
    a documentação existente adicionando sub-seções / parágrafos que
    cubram os 6 itens do BEHAVIOR. Pode-se também atualizar a sub-seção
    7.2 (Mecanismo Proposto) para citar o nome real das funções e o
    parâmetro, e atualizar 7.3 / 7.4 para citar source=system e
    confidence=1.0.

Anti-Goals (must NOT be violated):
    1. NÃO renomear a seção "## 7. Entity Linking" — o índice em
       "## Índice" e os anchors referenciam exatamente este título.
    2. NÃO mover a documentação para outra seção — a AC#6 é
       explícita sobre a seção 7.
    3. NÃO remover o conteúdo conceitual existente (7.1–7.4); apenas
       estender com os 6 itens.

Estado atual: RED — a seção 7 atual NÃO contém:
    - Nome das funções ``_auto_create_links``, ``_extract_entity_references``
      e ``_shared_memory_link_logic``.
    - Documentação das colunas ``last_auto_link_at`` e ``auto_link_count``.
    - Assinatura literal ``auto_link: bool = True``.
    - Convenção ``source="system"`` com ``confidence=1.0``.
    - Declaração explícita de que ``auto_link=False`` desativa o fluxo.
O teste falha com AssertionError até que a documentação seja estendida
na fase GREEN.
"""

import re
from pathlib import Path

import pytest


# ── Constants: the public interface under test ──────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DESIGN_PATH = REPO_ROOT / "docs" / "llm_wiki" / "SHARED_MEMORY_DESIGN.md"

# Regex que delimita o início da seção 7 (## 7. ...) até o início da
# seção 8 (## 8. ...). Aceita espaços/quebras de linha entre o "##" e o
# número; exige o título "Entity Linking" para garantir que estamos
# lendo a seção correta (não outra que porventura também comece com 7).
SECTION_7_START = re.compile(
    r"^##\s+7\.\s+Entity\s+Linking\s*$",
    re.MULTILINE | re.IGNORECASE,
)
SECTION_8_START = re.compile(
    r"^##\s+8\.\s+",
    re.MULTILINE,
)


# ── Override root conftest cleanup (no real Supabase needed) ───────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test is pure file I/O, no DB teardown."""
    yield


# ── Helpers: extract section 7 from the design doc ──────────────────────


def _extract_section_7(markdown: str) -> str:
    """Return the text of section 7 (``## 7. Entity Linking``) up to
    the start of section 8.  Returns an empty string if the section
    cannot be located.
    """
    m_start = SECTION_7_START.search(markdown)
    if not m_start:
        return ""
    m_end = SECTION_8_START.search(markdown, m_start.end())
    if not m_end:
        # Section 7 is the last section; take everything until EOF.
        return markdown[m_start.start():]
    return markdown[m_start.start() : m_end.start()]


# ── The single behavior under test ──────────────────────────────────────


def test_b4_section_7_documents_auto_linking_pipeline():
    """Section 7 of SHARED_MEMORY_DESIGN.md must document the full
    auto-linking pipeline introduced by behaviors B1, B2 and B3.

    Concretely the section must contain, in any wording but matching
    the required concepts:

        1. Tracking columns:
               last_auto_link_at   TIMESTAMPTZ  (nullable)
               auto_link_count     INTEGER      DEFAULT 0
        2. The parameter ``auto_link: bool = True`` on
           ``shared_memory_write``.
        3. The function flow:
               _auto_create_links
                   → _extract_entity_references
                   → _shared_memory_link_logic
        4. The convention ``source="system"`` with ``confidence=1.0``
           for auto-created links.
        5. Silent duplicate handling via ``uq_shared_memory_link``.
        6. ``auto_link=False`` disables the call without breaking
           the write.
    """
    # 1. The design doc must exist at the canonical path.
    assert DESIGN_PATH.exists(), (
        f"Design doc not found at {DESIGN_PATH}. "
        "Behavior B4 requires docs/llm_wiki/SHARED_MEMORY_DESIGN.md to exist."
    )

    markdown = DESIGN_PATH.read_text()

    # 2. Section 7 must be locatable in the file.
    section7 = _extract_section_7(markdown)
    assert section7, (
        "Could not locate section '## 7. Entity Linking' in "
        f"{DESIGN_PATH}. Behavior B4 requires this exact section header."
    )

    # ── Item 1: tracking columns ────────────────────────────────────────
    # ``last_auto_link_at`` documented as TIMESTAMPTZ, nullable, on
    # shared_business_memory.
    assert re.search(
        r"last_auto_link_at\s+TIMESTAMPTZ",
        section7,
        re.IGNORECASE,
    ), (
        "Section 7 is missing the `last_auto_link_at TIMESTAMPTZ` "
        "tracking column. Behavior B4 / AC#6 requires documentation of "
        "the new column added by behavior B1's migration:\n"
        "    last_auto_link_at  TIMESTAMPTZ  (nullable)\n"
        "on public.shared_business_memory."
    )

    # The column must be flagged as nullable (NULL / nullable / "opcional").
    nullable_window = section7[
        max(0, (section7.lower().find("last_auto_link_at") - 80))
        : section7.lower().find("last_auto_link_at") + 200
    ] if "last_auto_link_at" in section7.lower() else ""
    assert re.search(
        r"\b(nullable|null|opcional|optional)\b",
        nullable_window,
        re.IGNORECASE,
    ), (
        "Section 7 documents `last_auto_link_at` but does not flag it as "
        "nullable. Behavior B4 / AC#6 requires `last_auto_link_at` to be "
        "documented as TIMESTAMPTZ NULLABLE."
    )

    # ``auto_link_count`` documented as INTEGER DEFAULT 0.
    assert re.search(
        r"auto_link_count\s+INTEGER\s+DEFAULT\s+0",
        section7,
        re.IGNORECASE,
    ), (
        "Section 7 is missing the `auto_link_count INTEGER DEFAULT 0` "
        "tracking column. Behavior B4 / AC#6 requires documentation of "
        "the second column added by behavior B1's migration:\n"
        "    auto_link_count  INTEGER  DEFAULT 0\n"
        "on public.shared_business_memory."
    )

    # Both columns must be associated with the shared_business_memory table
    # inside section 7 (or section 2 referenced from section 7).
    assert re.search(
        r"shared_business_memory",
        section7,
        re.IGNORECASE,
    ), (
        "Section 7 does not mention `shared_business_memory`. "
        "Behavior B4 / AC#6 requires the tracking columns to be "
        "documented as additions to public.shared_business_memory."
    )

    # ── Item 2: auto_link parameter on shared_memory_write ─────────────
    assert re.search(
        r"auto_link\s*:\s*bool\s*=\s*True",
        section7,
        re.IGNORECASE,
    ), (
        "Section 7 is missing the canonical `auto_link: bool = True` "
        "parameter signature. Behavior B4 / AC#6 requires the section to "
        "document the parameter exactly as it appears in "
        "_shared_memory_write_logic and the shared_memory_write tool."
    )

    # The parameter must be tied to shared_memory_write (or its
    # underlying logic).  The mention may be on the section 5 tool
    # inventory or directly in section 7 — the docstring permits either.
    # Here we only check section 7 because AC#6 names that section
    # explicitly; if cross-referenced, section 7 must at least name
    # the tool.
    assert re.search(
        r"shared_memory_write",
        section7,
        re.IGNORECASE,
    ), (
        "Section 7 does not mention `shared_memory_write`. "
        "Behavior B4 / AC#6 requires the `auto_link` parameter to be "
        "documented in the context of shared_memory_write."
    )

    # ── Item 3: complete function flow ────────────────────────────────
    # Each helper function name must appear in section 7 so the flow
    # write → _auto_create_links → _extract_entity_references →
    # _shared_memory_link_logic is traceable from the docs.
    for helper in (
        r"_auto_create_links",
        r"_extract_entity_references",
        r"_shared_memory_link_logic",
    ):
        assert re.search(helper, section7), (
            f"Section 7 is missing the helper function `{helper}`. "
            "Behavior B4 / AC#6 requires the documentation of the full "
            "auto-link flow:\n"
            "    shared_memory_write\n"
            "        → _auto_create_links\n"
            "        → _extract_entity_references\n"
            "        → _shared_memory_link_logic"
        )

    # The flow must be presented in a traceable order.  We check that
    # the first helper mentioned in the flow is _auto_create_links and
    # that _extract_entity_references precedes _shared_memory_link_logic
    # (the canonical order from B2 / B3).
    auto_create_idx = section7.find("_auto_create_links")
    extract_idx = section7.find("_extract_entity_references")
    link_logic_idx = section7.find("_shared_memory_link_logic")

    assert auto_create_idx < extract_idx < link_logic_idx, (
        "Section 7 mentions the helper functions but does not present "
        "them in the canonical order of the auto-link flow. "
        "Behavior B4 / AC#6 requires the documented order to be:\n"
        "    1. _auto_create_links          (entry point)\n"
        "    2. _extract_entity_references  (scan value)\n"
        "    3. _shared_memory_link_logic   (persist link)\n"
        f"Got positions: _auto_create_links={auto_create_idx}, "
        f"_extract_entity_references={extract_idx}, "
        f"_shared_memory_link_logic={link_logic_idx}."
    )

    # ── Item 4: source=system with confidence=1.0 convention ──────────
    # The convention must appear in the form `source="system"` (or
    # `source=system` / `source: system`) coupled with
    # `confidence=1.0` (or `confidence: 1.0`).
    assert re.search(
        r'source\s*=\s*["\']?system["\']?',
        section7,
        re.IGNORECASE,
    ), (
        "Section 7 is missing the `source=system` convention. "
        "Behavior B4 / AC#6 requires section 7 to document that all "
        "auto-created links have `source=\"system\"`."
    )

    assert re.search(
        r"confidence\s*=\s*1\.0",
        section7,
        re.IGNORECASE,
    ), (
        "Section 7 is missing the `confidence=1.0` convention. "
        "Behavior B4 / AC#6 requires section 7 to document that all "
        "auto-created links are created with `confidence=1.0`."
    )

    # The two must be co-located in the same sentence / clause so the
    # reader can see they go together.  Check they appear within 200
    # chars of each other (twice the typical "source=system,
    # confidence=1.0" sentence length).
    src_match = re.search(
        r'source\s*=\s*["\']?system["\']?',
        section7,
        re.IGNORECASE,
    )
    conf_match = re.search(
        r"confidence\s*=\s*1\.0",
        section7,
        re.IGNORECASE,
    )
    assert src_match and conf_match, "internal: regex match assertions above."
    distance = abs(src_match.start() - conf_match.start())
    assert distance <= 200, (
        f"Section 7 mentions `source=system` and `confidence=1.0` but "
        f"they are {distance} characters apart. Behavior B4 / AC#6 "
        "requires them to be co-located (within ~200 chars) so the "
        "reader sees them as a single convention for auto-created links."
    )

    # ── Item 5: silent duplicate handling via uq_shared_memory_link ───
    assert re.search(
        r"uq_shared_memory_link",
        section7,
        re.IGNORECASE,
    ), (
        "Section 7 is missing the `uq_shared_memory_link` reference. "
        "Behavior B4 / AC#6 requires the section to document that the "
        "unique constraint `uq_shared_memory_link` enforces idempotency "
        "of auto-created links."
    )

    # Must be coupled with a "silent" / "ignored" / "idempotent" phrase.
    assert re.search(
        r"(silenciosamente|silent|silently|ignorad[oa]s?|idempotent|on\s+conflict\s+do\s+nothing|except\s+UniqueViolation)",
        section7,
        re.IGNORECASE,
    ), (
        "Section 7 mentions `uq_shared_memory_link` but does not describe "
        "the silent / idempotent handling. Behavior B4 / AC#6 requires "
        "section 7 to state that duplicate-link errors are caught "
        "silently (no exception bubbles up to the write call)."
    )

    # ── Item 6: auto_link=False disables the call ─────────────────────
    # Look for an explicit statement that auto_link=False disables
    # the call.  Acceptable phrasings:
    #   - "auto_link=False desativa..."
    #   - "auto_link=False desabilita..."
    #   - "quando auto_link=False, _auto_create_links não é chamado"
    #   - "if auto_link is False, skip _auto_create_links"
    assert re.search(
        r"auto_link\s*=\s*False[^.\n]{0,120}"
        r"(desativ|desabilit|na[çc]o\s+(?:é|ser[aá]|invocad|chamad)|skip|omit|disabled?)",
        section7,
        re.IGNORECASE,
    ) or re.search(
        r"(desativ|desabilit|skip|omit|disabled?)"
        r"[^.\n]{0,80}auto_link\s*=\s*False",
        section7,
        re.IGNORECASE,
    ) or re.search(
        r"quando\s+auto_link\s*=\s*False",
        section7,
        re.IGNORECASE,
    ) or re.search(
        r"if\s+not\s+auto_link[^.\n]{0,80}(skip|return|pass)",
        section7,
        re.IGNORECASE,
    ), (
        "Section 7 does not explicitly state that `auto_link=False` "
        "disables the call to _auto_create_links. Behavior B4 / AC#6 "
        "requires section 7 to document that `auto_link=False` "
        "desativa a criação automática de links (the write still "
        "succeeds, but no semantic links are produced)."
    )

    # Also verify that the disabling clause is paired with the
    # reassurance that the write itself is not broken.
    assert re.search(
        r"auto_link\s*=\s*False[^.\n]{0,200}(write|não\s+quebra|not\s+break|without\s+break|sem\s+quebrar)",
        section7,
        re.IGNORECASE,
    ) or re.search(
        r"(write|não\s+quebra|not\s+break|without\s+break|sem\s+quebrar)"
        r"[^.\n]{0,200}auto_link\s*=\s*False",
        section7,
        re.IGNORECASE,
    ), (
        "Section 7 states that `auto_link=False` disables link creation, "
        "but does not clarify that the write itself is not broken. "
        "Behavior B4 / AC#6 requires the doc to make explicit that the "
        "shared_memory_write call still succeeds when auto_link=False."
    )
