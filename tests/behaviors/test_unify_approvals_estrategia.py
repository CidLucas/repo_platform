"""RED test for behavior — Unify approval queries for documentos + estrategia in EstrategiaRoom.

GOAL:
    A sala unificada de Estratégia (`apps/blu_v3/src/pages/app/EstrategiaRoom.tsx`)
    deve exibir na aba `Decisões` as aprovações pendentes vindas de
    **ambos** os domínios — `documentos` e `estrategia`. Hoje, ela só
    consome `fetchApprovalsByAgent('estrategia', ...)` e renderiza um
    único variant do `ApprovalCard` (com badge "Estratégia" e botões
    "Aprovar / Depois / Ignorar"). A unificação requer:

        1. Acrescentar uma query `fetchApprovalsByAgent('documentos', ...)`
           ao `useQueries` (sem remover a query de estrategia).
        2. Mesclar as duas listas na aba `Decisões` para que o usuário
           veja aprovações de documentos e estrategia lado a lado.
        3. Renderizar variants distintos do `ApprovalCard`:
              - Documentos → badge "Documentos" + botão "Assinar"
              - Estrategia → badge "Estratégia" + botões "Aprovar / Ignorar"
        4. Atualizar o badge de contagem no `rtabs` para refletir a soma
           dos dois domínios (não só estrategia).
        5. Preservar os `staleTime` existentes: `approvals 30s`,
           `insights 60s`. A nova query de documentos deve usar `30_000`.

BEHAVIOR:
    Atualmente, `EstrategiaRoom.tsx` (apps/blu_v3/src/pages/app/EstrategiaRoom.tsx):
        - importa `fetchApprovalsByAgent` de `../../api/approvals` ✓
        - `approvalsQ` → `fetchApprovalsByAgent('estrategia', clientId!)`
          com `staleTime: 30_000` ✓
        - `insightsQ` → `fetchInsights(10, 'estrategia')` com
          `staleTime: 60_000` ✓
        - `ApprovalCard` local renderiza badge "Estratégia" e botões
          "Aprovar / Depois / Ignorar" ✓
        - Badge count no `rtabs` mostra `approvals.length` (só estrategia) ✓
        - **NÃO** tem `approvalsDocsQ` para documentos ✗
        - **NÃO** mescla as duas listas na aba Decisões ✗
        - **NÃO** tem variant do `ApprovalCard` com badge "Documentos"
          e botão "Assinar" ✗
        - **NÃO** atualiza o badge count para refletir documentos + estrategia ✗

    A sala de referência para o variant docs é
    `apps/blu_v3/src/pages/app/DocumentosRoom.tsx` (que tem
    `fetchApprovalsByAgent('documentos', ...)` e o `ApprovalCard` com
    badge "Documentos" + botão "Assinar"). Esse arquivo NÃO deve ser
    modificado — a unificação é aditiva na `EstrategiaRoom`.

ACs (Acceptance Criteria):
    AC#1 — EstrategiaRoom.tsx executa `fetchApprovalsByAgent('documentos', ...)`
           **junto** com `fetchApprovalsByAgent('estrategia', ...)` no
           `useQueries`. A query de estrategia deve continuar existindo
           (preservação).
    AC#2 — A aba `Decisões` mostra aprovações de **ambos** os domínios
           (merged array ou maps concatenados dentro do mesmo painel).
    AC#3 — `ApprovalCard` renderiza distintamente:
              - Documentos → badge "Documentos" + botão "Assinar"
              - Estrategia → badge "Estratégia" + botão "Aprovar"
                            + botão "Ignorar"
    AC#4 — Badge de contagem no `rtabs` reflete o total de
           `documentos + estrategia` pending (não só estrategia).
    AC#5 — Labels nos badges dos `ApprovalCard`s: "Documentos" e
           "Estratégia" (cada um no seu variant).
    AC#6 — Insights já estão unificados/cobertos
           (`fetchInsights(10, 'estrategia')` já filtra server-side).
           AC de sanidade — não requer mudança de código.
    AC#7 — `staleTime` preservados: `approvals 30_000` (incluindo a
           nova query de documentos) e `insights 60_000`.

DECISION:
    Estratégia: extend — `EstrategiaRoom.tsx` deve ADICIONAR a query
                `fetchApprovalsByAgent('documentos', ...)` ao
                `useQueries` (sem remover a de estrategia), declarar
                um novo variant do `ApprovalCard` (docs) com badge
                "Documentos" e botão "Assinar" (portado do
                `DocumentosRoom`, **não** importado — para manter as
                salas desacopladas), mesclar as duas listas na aba
                Decisões (ex.: `const allApprovals = [...approvalsDocs,
                ...approvals]`), e atualizar o badge count no `rtabs`
                para refletir o total merged.
    Arquivos alvo:
        - apps/blu_v3/src/pages/app/EstrategiaRoom.tsx
    Arquivos de referência (somente leitura):
        - apps/blu_v3/src/pages/app/DocumentosRoom.tsx (variant docs
          do ApprovalCard — "Documentos" badge + "Assinar" botão).
        - apps/blu_v3/src/api/approvals.ts (API consumida).

Estado atual: RED — `EstrategiaRoom.tsx` NÃO tem a query de
`fetchApprovalsByAgent('documentos', ...)`, NÃO mescla aprovações na
aba Decisões, NÃO tem variant do `ApprovalCard` com badge "Documentos"
e botão "Assinar", e o badge count no `rtabs` reflete apenas
`approvals.length` (estrategia). Todos os 6 testes RED cobrem os
gaps acima.

Anti-Goals (must NOT be violated):
    1. NÃO modificar `DocumentosRoom.tsx` — ele é a referência
       canônica do variant docs do `ApprovalCard`. A unificação é
       aditiva na `EstrategiaRoom`.
    2. NÃO criar mocks de Supabase — os testes são source-inspection
       apenas (sem DB, sem runtime, sem React).
    3. NÃO modificar produção — este arquivo só REDuz o gap. A
       implementação GREEN vem em um commit separado.
    4. NÃO quebrar o estado de estrategia existente
       (`selectedReport`, `reportContent`, `analyticsOpen`, `tab`,
       etc.) — a unificação é aditiva.
    5. NÃO importar `ApprovalCard` de `DocumentosRoom` — o variant
       docs deve ser portado (declarado localmente) para manter as
       salas desacopladas, da mesma forma que o variant estrategia
       já é local.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Paths ─────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

ESTRATEGIA_ROOM_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "EstrategiaRoom.tsx"
)

DOCUMENTOS_ROOM_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "DocumentosRoom.tsx"
)

APPROVALS_API_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "api"
    / "approvals.ts"
)


# ── Source-level guard helpers ────────────────────────────────────────────


def _read_source(path: Path) -> str:
    assert path.exists(), f"Source file not found: {path}"
    return path.read_text(encoding="utf-8")


def _has_approvals_documentos_query(source: str) -> bool:
    """Detect that `useQueries` has a query with
    `queryKey: ['approvals', 'documentos', ...]` and `queryFn` calling
    `fetchApprovalsByAgent('documentos', ...)`.

    The current EstrategiaRoom has only the estrategia query — this
    helper returns False until the documentos query is added.
    """
    has_key = re.search(
        r"queryKey:\s*\[\s*['\"]approvals['\"]\s*,\s*['\"]documentos['\"]",
        source,
    ) is not None
    has_fn = re.search(
        r"""fetchApprovalsByAgent\s*\(\s*['"]documentos['"]""",
        source,
    ) is not None
    return has_key and has_fn


def _has_approvals_estrategia_query(source: str) -> bool:
    """Detect that `useQueries` still has the estrategia approvals
    query (AC#7 preservation — must NOT be removed by the migration).

    The current EstrategiaRoom has this query — this helper returns
    True today and must keep returning True after the migration.
    """
    has_key = re.search(
        r"queryKey:\s*\[\s*['\"]approvals['\"]\s*,\s*['\"]estrategia['\"]",
        source,
    ) is not None
    has_fn = re.search(
        r"""fetchApprovalsByAgent\s*\(\s*['"]estrategia['"]""",
        source,
    ) is not None
    return has_key and has_fn


def _has_merged_approvals_in_decisoes(source: str) -> bool:
    """Detect that the `Decisões` tab content references approvals
    from BOTH the documentos and estrategia domains.

    The current code only references `approvals` (estrategia) inside
    the `tab === 'decisoes'` panel. After the migration, the panel
    must reference BOTH — either via a merged array variable (e.g.
    `allApprovals`, `mergedApprovals`) or via separate maps of
    `approvalsDocs` and `approvals`.

    We accept any of the following evidence inside the Decisões tab
    window (from `tab === 'decisoes'` to the next `tab === 'analises'`):

        1. A new variable name (e.g. `allApprovals`, `mergedApprovals`,
           `decisoesApprovals`, `allDecisions`) is referenced — the
           Coder is expected to build this variable from BOTH lists.
        2. The literal identifier `approvalsDocs` (or `docsApprovals`)
           is referenced — meaning the docs list is being iterated
           inside Decisões.
        3. A spread expression that combines both lists, e.g.
           `[...approvalsDocs, ...approvals]`.
    """
    decisoes_match = re.search(
        r"""tab\s*===\s*['"]decisoes['"]""",
        source,
    )
    if not decisoes_match:
        return False
    start = decisoes_match.start()
    # Window: from decisoes marker to the next 'analises' marker
    # (or end of file as a safe fallback).
    rest = source[start + 1:]
    next_tab_match = re.search(
        r"""tab\s*===\s*['"]analises['"]""",
        rest,
    )
    end = start + 1 + next_tab_match.start() if next_tab_match else len(source)
    window = source[start:end]

    # 1) A merged variable is referenced in the Decisões tab.
    has_merged_var = re.search(
        r"\b(allApprovals|mergedApprovals|decisoesApprovals|allDecisions)\b",
        window,
    ) is not None
    # 2) The docs identifier is referenced in the Decisões tab.
    has_docs_ref = (
        re.search(r"\bapprovalsDocs\b", window) is not None
        or re.search(r"\bdocsApprovals\b", window) is not None
    )
    return has_merged_var or has_docs_ref


def _has_assinar_button(source: str) -> bool:
    """Detect that an `Assinar` (sign) button label is present in the
    source — this is the docs variant of the approval action.

    The current EstrategiaRoom has no `Assinar` button (it uses
    `Aprovar` / `Depois` / `Ignorar`). The docs variant must add it.
    """
    return re.search(r"\bAssinar\b", source) is not None


def _has_aprovar_button(source: str) -> bool:
    """Detect that an `Aprovar` (approve) button label is present in
    the source — the estrategia variant of the approval action.

    The current EstrategiaRoom has this label inside its local
    `ApprovalCard`. This is a preservation guard.
    """
    return re.search(r"\bAprovar\b", source) is not None


def _has_ignorar_button(source: str) -> bool:
    """Detect that an `Ignorar` (ignore/reject) button label is present
    in the source — the estrategia variant of the reject action.

    The current EstrategiaRoom has this label. Preservation guard.
    """
    return re.search(r"\bIgnorar\b", source) is not None


def _has_documentos_badge_in_approval_card(source: str) -> bool:
    """Detect that the literal `Documentos` badge label appears inside
    an `ApprovalCard` function (or a clearly named docs-variant like
    `ApprovalCardDocs` / `DocsApprovalCard`).

    The current EstrategiaRoom has only ONE `ApprovalCard` function
    with the badge "Estratégia" — no `Documentos` badge anywhere. The
    docs variant must add it.
    """
    # Find all approval-card function declarations (named ApprovalCard
    # or a clear docs variant). For each, check if the function body
    # contains a JSX text node ">Documentos<".
    fn_pattern = (
        r"function\s+(?:ApprovalCard|ApprovalCardDocs|DocsApprovalCard)\s*\("
    )
    fn_matches = list(re.finditer(fn_pattern, source))
    for fn_match in fn_matches:
        # Find the end of this function body (next top-level `function `
        # or end of file).
        tail = source[fn_match.end():]
        next_fn = re.search(r"^function\s+", tail, re.MULTILINE)
        end = next_fn.start() if next_fn else len(tail)
        body = tail[:end]
        if re.search(r">\s*Documentos\s*<", body):
            return True
    return False


def _has_estrategia_badge_in_approval_card(source: str) -> bool:
    """Detect that the literal `Estratégia` (or `Estrategia`) badge
    label appears inside an `ApprovalCard` function. Preservation
    guard for the estrategia variant.
    """
    fn_pattern = (
        r"function\s+(?:ApprovalCard|ApprovalCardEstrategia|EstrategiaApprovalCard)\s*\("
    )
    fn_matches = list(re.finditer(fn_pattern, source))
    for fn_match in fn_matches:
        tail = source[fn_match.end():]
        next_fn = re.search(r"^function\s+", tail, re.MULTILINE)
        end = next_fn.start() if next_fn else len(tail)
        body = tail[:end]
        # Accept both "Estratégia" (with acute) and "Estrategia" (without).
        if re.search(r">\s*Estrat[eé]gia\s*<", body):
            return True
    return False


def _approval_badge_count_merged(source: str) -> bool:
    """Detect that the badge count inside the `rtabs` (the small
    pill rendered next to "Decisões") reflects BOTH the documentos
    and estrategia approvals — not just estrategia.

    The current code renders:
        <span className="tbdg">{approvals.length}</span>

    After the migration, the expression inside `{...}` must reference
    BOTH the docs and estrategia identifiers — either as separate
    `approvalsDocs.length + approvals.length` or as a merged variable
    like `allApprovals.length`.
    """
    # Find the rtabs tbdg span. We accept a liberal pattern: any
    # `className="tbdg"` (or `className='tbdg'`) followed by a
    # `{...}` expression.
    tbdg_match = re.search(
        r"""className\s*=\s*["']tbdg["'][^{]*\{([^}]+)\}""",
        source,
        re.DOTALL,
    )
    if not tbdg_match:
        return False
    expr = tbdg_match.group(1)
    # The expression must reference BOTH the docs and estrategia
    # approval lists (or a merged variable that contains both).
    has_docs_ref = (
        re.search(r"\bapprovalsDocs\b", expr) is not None
        or re.search(r"\bdocsApprovals\b", expr) is not None
    )
    has_estrategia_ref = re.search(r"\bapprovals\b", expr) is not None
    has_merged_var = re.search(
        r"\b(allApprovals|mergedApprovals|decisoesApprovals|allDecisions)\b",
        expr,
    ) is not None
    return (has_docs_ref and has_estrategia_ref) or has_merged_var


def _stale_time_preserved(
    source: str,
    query_key_part: str,
    expected_ms: int,
) -> bool:
    """Check that a query whose `queryKey` includes `query_key_part`
    has `staleTime: <expected_ms>` (in milliseconds) in the SAME
    query object.

    The pattern we look for is:
        queryKey: [...'query_key_part'...]
        ... (up to ~500 chars of query object body) ...
        staleTime: <digits with optional underscores>

    The `expected_ms` is compared as an integer (underscores in the
    source are stripped, e.g. `30_000` → `30000`).
    """
    # Build a pattern that matches the queryKey line, then up to
    # 500 chars of body, then the staleTime line.
    pattern = (
        r"queryKey:\s*\[[^\]]*['\"]"
        + re.escape(query_key_part)
        + r"['\"][^\]]*\][\s\S]{0,500}?staleTime:\s*(\d[\d_]*)"
    )
    match = re.search(pattern, source)
    if not match:
        return False
    stale_time_str = match.group(1).replace("_", "")
    try:
        return int(stale_time_str) == expected_ms
    except ValueError:
        return False


def _has_insights_query_with_estrategia_filter(source: str) -> bool:
    """Detect that the `insights` query uses the `fetchInsights(..., 'estrategia')`
    signature — server-side filter for the estrategia room.

    AC#6 sanity check — the current code already does this.
    """
    return re.search(
        r"""fetchInsights\s*\(\s*[^)]*['"]estrategia['"]""",
        source,
    ) is not None


# ── AC#1: useQueries has BOTH documentos and estrategia approvals ─────────


def test_estrategia_room_has_both_approvals_queries():
    """AC#1 — `EstrategiaRoom.tsx` must execute
    `fetchApprovalsByAgent('documentos', ...)` **junto** com
    `fetchApprovalsByAgent('estrategia', ...)` inside `useQueries`.

    Concretely, the file must contain:
        - a `queryKey: ['approvals', 'documentos', ...]` entry
          with a `queryFn` calling `fetchApprovalsByAgent('documentos', ...)`
        - a `queryKey: ['approvals', 'estrategia', ...]` entry
          with a `queryFn` calling `fetchApprovalsByAgent('estrategia', ...)`

    The estrategia query must be PRESERVED (AC#7 invariant — the
    migration is additive, not destructive). The current code has
    only the estrategia query, so this combined assertion fails RED:
    the documentos query is missing.
    """
    assert ESTRATEGIA_ROOM_PATH.exists(), (
        f"RED — source file not found: {ESTRATEGIA_ROOM_PATH}"
    )
    source = _read_source(ESTRATEGIA_ROOM_PATH)

    problemas: list[str] = []
    if not _has_approvals_documentos_query(source):
        problemas.append(
            "the `documentos` approvals query is MISSING — `useQueries` "
            "does NOT have a `queryKey: ['approvals', 'documentos', ...]` "
            "entry, nor a `queryFn` calling "
            "`fetchApprovalsByAgent('documentos', ...)`. The Estrategia "
            "room needs to fetch document approvals in parallel with "
            "estrategia approvals so the Decisões tab can show both."
        )
    if not _has_approvals_estrategia_query(source):
        problemas.append(
            "the `estrategia` approvals query was REMOVED — the "
            "migration must be ADDITIVE. `useQueries` must still have "
            "`queryKey: ['approvals', 'estrategia', ...]` with "
            "`queryFn: () => fetchApprovalsByAgent('estrategia', clientId!)`."
        )

    assert not problemas, (
        "RED — EstrategiaRoom.tsx `useQueries` does not have BOTH the "
        "documentos and estrategia approvals queries.\n"
        + "\n".join(f"  - {p}" for p in problemas)
    )


# ── AC#2: Decisões tab shows merged approvals from both domains ──────────


def test_estrategia_room_decisoes_renders_merged_approvals():
    """AC#2 — The `Decisões` tab content must render approvals from
    BOTH the documentos and estrategia domains.

    Currently the `tab === 'decisoes'` panel only references
    `approvals` (the estrategia list) — it has no awareness of
    document approvals. After the migration, the panel must
    reference the docs list (via a merged variable like
    `allApprovals` / `mergedApprovals`, or via a direct
    `approvalsDocs` reference).
    """
    assert ESTRATEGIA_ROOM_PATH.exists(), (
        f"RED — source file not found: {ESTRATEGIA_ROOM_PATH}"
    )
    source = _read_source(ESTRATEGIA_ROOM_PATH)

    assert _has_merged_approvals_in_decisoes(source), (
        "RED — EstrategiaRoom.tsx `Decisões` tab does NOT render "
        "approvals from both domains. Currently the `tab === 'decisoes'` "
        "panel only iterates `approvals` (the estrategia list) and is "
        "completely unaware of document approvals. Expected the panel "
        "to render a merged list (e.g. "
        "`const allApprovals = [...approvalsDocs, ...approvals]; "
        "{allApprovals.map((ap) => <ApprovalCard ... />)}`) or to "
        "iterate BOTH `approvalsDocs` and `approvals` inside the "
        "Decisões tab content, so document and estrategia approvals "
        "appear together in the unified Decisões view."
    )


# ── AC#3: ApprovalCard renders distinctly: docs (Assinar) vs estrategia ──


def test_estrategia_room_renders_approval_cards_for_both_domains():
    """AC#3 — `ApprovalCard` (or a clearly named docs variant) must
    render BOTH action button sets:
        - Documentos → button "Assinar" (matching DocumentosRoom line ~461)
        - Estrategia → button "Aprovar" (matching EstrategiaRoom line ~488)
                      + button "Ignorar" (matching EstrategiaRoom line ~490)

    The current EstrategiaRoom has only the estrategia variant
    (Aprovar / Depois / Ignorar) — no `Assinar` button anywhere. The
    docs variant must add the `Assinar` button to render document
    approvals in the Decisões tab.

    Both action sets must be present so the user can sign a document
    OR approve / ignore an estrategia analysis from the same view.
    """
    assert ESTRATEGIA_ROOM_PATH.exists(), (
        f"RED — source file not found: {ESTRATEGIA_ROOM_PATH}"
    )
    source = _read_source(ESTRATEGIA_ROOM_PATH)

    problemas: list[str] = []
    if not _has_assinar_button(source):
        problemas.append(
            "the `Assinar` button is MISSING — the docs variant of "
            "ApprovalCard must render a button labeled `Assinar` (or "
            "`✍️ Assinar` with the emoji) to sign document approvals. "
            "See DocumentosRoom.tsx line ~461 for the reference pattern. "
            "Without this button, document approvals in the Decisões "
            "tab cannot be signed by the user."
        )
    if not _has_aprovar_button(source):
        problemas.append(
            "the `Aprovar` button is MISSING — the estrategia variant "
            "of ApprovalCard must keep rendering a button labeled "
            "`Aprovar` (or `👍 Aprovar`) to approve estrategia "
            "analyses. See EstrategiaRoom.tsx line ~488 for the "
            "reference pattern. The migration must NOT remove the "
            "estrategia action set."
        )
    if not _has_ignorar_button(source):
        problemas.append(
            "the `Ignorar` button is MISSING — the estrategia variant "
            "of ApprovalCard must keep rendering a button labeled "
            "`Ignorar` to reject estrategia analyses. See "
            "EstrategiaRoom.tsx line ~490 for the reference pattern."
        )

    assert not problemas, (
        "RED — EstrategiaRoom.tsx ApprovalCard does not render the "
        "required button sets for BOTH domains.\n"
        + "\n".join(f"  - {p}" for p in problemas)
    )


# ── AC#4: Badge count in rtabs reflects documentos + estrategia ──────────


def test_estrategia_room_rtabs_badge_count_includes_documentos():
    """AC#4 — The badge count rendered next to the "Decisões" tab in
    `rtabs` (the `<span className="tbdg">` pill) must reflect the
    TOTAL of documentos + estrategia pending approvals — not just
    estrategia.

    Currently the badge is `{approvals.length}` (estrategia only).
    After the migration, the expression must reference BOTH domains
    — e.g. `{allApprovals.length}` (where `allApprovals` is the
    merged array) or `{approvalsDocs.length + approvals.length}`.
    """
    assert ESTRATEGIA_ROOM_PATH.exists(), (
        f"RED — source file not found: {ESTRATEGIA_ROOM_PATH}"
    )
    source = _read_source(ESTRATEGIA_ROOM_PATH)

    assert _approval_badge_count_merged(source), (
        "RED — EstrategiaRoom.tsx `rtabs` badge count is NOT merged. "
        "Currently the `<span className=\"tbdg\">` pill next to "
        "'Decisões' renders `{approvals.length}` — that only counts "
        "estrategia approvals. Expected the expression inside the "
        "`{...}` to reflect the total of BOTH domains, e.g. "
        "`{allApprovals.length}` (using a merged variable built "
        "from `[...approvalsDocs, ...approvals]`) or "
        "`{approvalsDocs.length + approvals.length}`. Without this, "
        "the tab badge undercounts pending approvals and the user "
        "cannot tell at a glance how many decisions need attention."
    )


# ── AC#5: Badge labels: 'Documentos' and 'Estrategia' ────────────────────


def test_estrategia_room_approval_cards_have_both_badges():
    """AC#5 — The `ApprovalCard` variants must use the badge labels
    "Documentos" (docs variant) and "Estratégia" / "Estrategia"
    (estrategia variant).

    Currently the file has only ONE `ApprovalCard` function with
    the badge "Estratégia" (line ~473) — no "Documentos" badge
    anywhere. The docs variant must add the "Documentos" badge so
    the user can visually distinguish document approvals from
    estrategia approvals in the unified Decisões tab.
    """
    assert ESTRATEGIA_ROOM_PATH.exists(), (
        f"RED — source file not found: {ESTRATEGIA_ROOM_PATH}"
    )
    source = _read_source(ESTRATEGIA_ROOM_PATH)

    problemas: list[str] = []
    if not _has_documentos_badge_in_approval_card(source):
        problemas.append(
            "the `Documentos` badge label is MISSING inside an "
            "ApprovalCard function. The docs variant must render the "
            "literal `Documentos` text inside its `ag` div (matching "
            "DocumentosRoom.tsx line ~449). Currently the only "
            "ApprovalCard in EstrategiaRoom uses the badge "
            "`Estratégia` (line ~473) — there is no docs variant."
        )
    if not _has_estrategia_badge_in_approval_card(source):
        problemas.append(
            "the `Estratégia` (or `Estrategia`) badge label is "
            "MISSING inside an ApprovalCard function. The estrategia "
            "variant must keep rendering the `Estratégia` badge "
            "(line ~473) so estrategia approvals stay visually "
            "distinct from document approvals. The migration must "
            "NOT remove the estrategia badge."
        )

    assert not problemas, (
        "RED — EstrategiaRoom.tsx ApprovalCard variants do not have "
        "BOTH badge labels.\n"
        + "\n".join(f"  - {p}" for p in problemas)
    )


# ── AC#6: Insights already filtered by estrategia (sanity, GREEN today) ──


def test_estrategia_room_insights_query_uses_estrategia_filter():
    """AC#6 — Insights are already unified / covered. The `insights`
    query in `useQueries` must call
    `fetchInsights(N, 'estrategia')` — the `p_room='estrategia'`
    filter is applied server-side.

    This is a SANITY check. The current code already does this
    (EstrategiaRoom.tsx line ~144: `queryFn: () => fetchInsights(10, 'estrategia')`),
    so this test passes GREEN today and must keep passing GREEN
    after the migration.

    NOTE: This test is intentionally GREEN — AC#6 explicitly says
    "Insights já estão unificados ou cobertos". It is included as a
    guard against the migration accidentally changing the filter.
    """
    assert ESTRATEGIA_ROOM_PATH.exists(), (
        f"RED — source file not found: {ESTRATEGIA_ROOM_PATH}"
    )
    source = _read_source(ESTRATEGIA_ROOM_PATH)

    assert _has_insights_query_with_estrategia_filter(source), (
        "RED — EstrategiaRoom.tsx `insights` query is NOT using the "
        "`'estrategia'` server-side filter. Expected the queryFn to "
        "call `fetchInsights(N, 'estrategia')` so the estrategia room "
        "only shows insights tagged for the estrategia domain. "
        "Without the filter, the room would show insights from other "
        "domains (e.g. financeiro, agenda) polluting the unified view."
    )


# ── AC#7: staleTime preserved for approvals (30s) and insights (60s) ─────


def test_estrategia_room_queries_have_correct_stale_times():
    """AC#7 — `staleTime` invariants:
        - The `approvals` queries (BOTH `documentos` AND `estrategia`)
          must use `staleTime: 30_000` (30 seconds).
        - The `insights` query must use `staleTime: 60_000` (60 seconds).

    The current code has the estrategia approvals query at 30_000
    and the insights query at 60_000. After the migration, the NEW
    documentos approvals query must ALSO be at 30_000 (matching the
    DocumentosRoom.tsx pattern at line ~67). The insights query
    must stay at 60_000.

    This test combines all three staleTime checks into one assertion
    so the missing documentos query (which causes the
    `_stale_time_preserved('documentos', 30_000)` check to fail)
    makes the test fail RED.
    """
    assert ESTRATEGIA_ROOM_PATH.exists(), (
        f"RED — source file not found: {ESTRATEGIA_ROOM_PATH}"
    )
    source = _read_source(ESTRATEGIA_ROOM_PATH)

    problemas: list[str] = []
    if not _stale_time_preserved(source, "documentos", 30_000):
        problemas.append(
            "the `documentos` approvals query is MISSING or has the "
            "wrong `staleTime`. Expected `useQueries` to contain a "
            "query with `queryKey: ['approvals', 'documentos', ...]` "
            "and `staleTime: 30_000` (matching DocumentosRoom.tsx "
            "line ~67 and the estrategia approvals pattern at "
            "EstrategiaRoom.tsx line ~140)."
        )
    if not _stale_time_preserved(source, "estrategia", 30_000):
        problemas.append(
            "the `estrategia` approvals query has the wrong "
            "`staleTime` (or was removed). Expected `staleTime: 30_000` "
            "on the estrategia approvals query — see EstrategiaRoom.tsx "
            "line ~140 for the current value. The migration must "
            "PRESERVE this staleTime."
        )
    if not _stale_time_preserved(source, "insights", 60_000):
        problemas.append(
            "the `insights` query has the wrong `staleTime` (or was "
            "removed). Expected `staleTime: 60_000` on the insights "
            "query — see EstrategiaRoom.tsx line ~146 for the current "
            "value. The migration must PRESERVE this staleTime."
        )

    assert not problemas, (
        "RED — EstrategiaRoom.tsx queries do not have the correct "
        "`staleTime` values.\n"
        + "\n".join(f"  - {p}" for p in problemas)
    )
