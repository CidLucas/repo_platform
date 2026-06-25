"""RED test for behavior — Adicionar aba 'Documentos' na EstrategiaRoom com port de componentes.

GOAL:
    A sala `DocumentosRoom` (`apps/blu_v3/src/pages/app/DocumentosRoom.tsx`)
    é a implementação canônica do editor de documentos + aprovações de
    documentos + modelos + base de conhecimento. Hoje, `EstrategiaRoom`
    (`apps/blu_v3/src/pages/app/EstrategiaRoom.tsx`) ainda não tem nenhuma
    integração com a API de documentos (`apps/blu_v3/src/api/documents.ts`),
    nem a sub-aba `Documentos`, nem o editor (`DocEditor`), nem o
    `ApprovalCard` específico de documentos. Este teste REDa o port do
    behavior "Documentos" para dentro da `EstrategiaRoom`, de forma que
    a sala de Estratégia ganhe:

        - sub-aba 'documentos' no `rtabs` (junto com decisoes / analises /
          historico / config)
        - imports das APIs `fetchRecentDocuments`, `fetchDraftDocuments`,
          `fetchDocTemplates`, `saveDocument`, `createDocument`,
          `publishDocument`, `archiveDocument` vindos de
          `../../api/documents`
        - sub-abas internas da aba Documentos: ativos / rascunhos /
          modelos / base / config (mesmo shape do DocumentosRoom)
        - componente `DocEditor` renderizado quando há `activeDoc`
          selecionado na aba `ativos`
        - componente `ApprovalCard` (variant docs, com badge
          "Documentos") renderizado para as aprovações de documentos
        - estado isolado: `activeDocId`, `saveStatus` e a tab de
          documentos são namespaces próprios — não podem colidir com
          `selectedReport`, `reportContent` ou `analyticsOpen` da
          estratégia.

BEHAVIOR:
    Para que o port seja considerado concluído, `EstrategiaRoom.tsx`
    precisa satisfazer 5 ACs:

        AC#1  — o tipo `Tab` da sala inclui o literal `'documentos'` e
               o `rtabs` renderiza uma aba rotulada "Documentos".
        AC#2  — `EstrategiaRoom.tsx` importa as 7 funções de
               `../../api/documents`: `fetchRecentDocuments`,
               `fetchDraftDocuments`, `fetchDocTemplates`,
               `saveDocument`, `createDocument`, `publishDocument`,
               `archiveDocument`.
        AC#3  — dentro do conteúdo da aba Documentos, o arquivo declara
               e usa `DocEditor` e `ApprovalCard` (a variant "docs" com
               badge "Documentos"), e a aba cobre as 5 sub-abas
               `ativos` / `rascunhos` / `modelos` / `base` / `config`.
        AC#4  — `DocEditor` é acionável: existe `state activeDocId`
               (useState) e um handler de save que recebe o conteúdo
               editado.
        AC#5  — o estado de documentos (activeDocId, saveStatus, tab
               de documentos) está isolado do estado de estratégia
               (selectedReport, reportContent, analyticsOpen) — não
               há sobrescrita/colisão de identificadores.

AC (Acceptance Criteria):
    AC#1 — EstrategiaRoom.tsx tem o tipo Tab incluindo 'documentos' e
           renderiza uma aba 'Documentos' no rtabs.
    AC#2 — EstrategiaRoom.tsx importa as APIs de documentos:
           fetchRecentDocuments, fetchDraftDocuments, fetchDocTemplates,
           saveDocument, createDocument, publishDocument, archiveDocument
           de '../../api/documents'.
    AC#3 — EstrategiaRoom.tsx contém DocEditor e ApprovalCard (docs, com
           badge "Documentos") no conteúdo da aba Documentos, com
           sub-tabs ativos, rascunhos, modelos, base, config.
    AC#4 — DocEditor é acionável a partir da EstrategiaRoom (state
           activeDocId e handler de save).
    AC#5 — Variáveis de estado de documentos não conflitam com estado de
           estratégia (activeDocId, saveStatus, doc tab state são
           isolados do selectedReport, reportContent, analyticsOpen da
           estratégia).

DECISION:
    Estratégia: extend — EstrategiaRoom.tsx deve ADICIONAR a aba
                'documentos' ao Tab type já existente (não criar um
                novo tipo), importar as 7 funções de documents.ts,
                declarar localmente os componentes `DocEditor` e
                `ApprovalCard` (variant docs com badge "Documentos"),
                introduzir o state `activeDocId` (string | null) e
                `saveStatus` ('idle' | 'saving' | 'saved' | 'error'),
                e garantir que esses identificadores NÃO colidam com
                `selectedReport` / `reportContent` / `analyticsOpen`
                já presentes.
    Arquivos alvo:
        - apps/blu_v3/src/pages/app/EstrategiaRoom.tsx
    Arquivos de referência (somente leitura):
        - apps/blu_v3/src/pages/app/DocumentosRoom.tsx (componentes
          DocEditor e ApprovalCard docs — devem ser portados, não
          compartilhados via import para evitar acoplamento).
        - apps/blu_v3/src/api/documents.ts (API consumida).

Estado atual: RED — EstrategiaRoom.tsx NÃO tem a aba 'Documentos', NÃO
importa nada de `../../api/documents`, NÃO tem `DocEditor`, NÃO tem
`ApprovalCard` variant docs, e NÃO tem `activeDocId` / `saveStatus`.
Todos os 5 ACs falham (AssertionError). O Coder deve estender o tipo
`Tab` para incluir `'documentos'`, importar as 7 funções da API,
declarar localmente os componentes portados do DocumentosRoom
(ApprovalCard com badge "Documentos" e DocEditor), introduzir o state
isolado de documentos, e ligar o handler de save para tornar todos os
ACs GREEN.

Anti-Goals (must NOT be violated):
    1. NÃO importar `DocEditor` ou `ApprovalCard` de
       `DocumentosRoom` — eles devem ser portados (declarados
       localmente em EstrategiaRoom) para manter as salas
       desacopladas.
    2. NÃO renomear `selectedReport`, `reportContent` ou
       `analyticsOpen` — o estado de estratégia deve permanecer
       intocado. O state de documentos deve ser ADITIVO.
    3. NÃO introduzir uma nova dependência de UI library — usar
       apenas os componentes React já em uso e o markup inline
       portado de DocumentosRoom.
    4. NÃO redefinir a API de `documents.ts` — as 7 funções já
       existem; EstrategiaRoom deve apenas consumi-las.
    5. NÃO acoplar a `DocumentosRoom` (sem route sharing) — a aba
       Documentos é uma feature da EstrategiaRoom, não um link para
       a outra sala.
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

DOCUMENTS_API_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "api"
    / "documents.ts"
)


# ── Source-level guard helpers ────────────────────────────────────────────


def _read_source(path: Path) -> str:
    assert path.exists(), f"Source file not found: {path}"
    return path.read_text(encoding="utf-8")


def _tab_type_includes_documentos(source: str) -> bool:
    """Detect that the local `type Tab = ...` declaration includes the
    'documentos' literal.

    The current EstrategiaRoom has:

        type Tab = 'decisoes' | 'analises' | 'historico' | 'config'

    After the port, it must be:

        type Tab = 'decisoes' | 'analises' | 'historico' | 'config'
                 | 'documentos'

    We accept the literal in any position inside the Tab union, and we
    only consider the FIRST `type Tab =` declaration to avoid
    accidentally matching a different type with the same name further
    down the file.
    """
    tab_decl = re.search(
        r"type\s+Tab\s*=\s*([^\n;]+)",
        source,
    )
    if not tab_decl:
        return False
    body = tab_decl.group(1)
    return re.search(r"""['"]documentos['"]""", body) is not None


def _rtabs_renders_documentos_tab(source: str) -> bool:
    """Detect that the `rtabs` div maps a tab labeled "Documentos".

    The current `rtabs` is shaped as:

        <div className="rtabs">
          {(['decisoes', 'analises', 'historico', 'config'] as Tab[]).map(
            (t) => (
              <div key={t} className={`rtab${tab === t ? ' on' : ''}`}
                   onClick={() => setTab(t)}>
                {t === 'decisoes' ? ... : ... : 'Config'}
              </div>
            )
          )}
        </div>

    After the port, the ternary chain inside the `.map(...)` must
    branch on `t === 'documentos'` and render the literal string
    "Documentos" (capital D, rest lowercase — pt-BR style).

    We look for both signals together: the literal "Documentos" inside
    an `rtab` JSX node, AND a `t === 'documentos'` branch in the
    immediate ternary chain. The combination guards against a
    half-port where the label exists but the Tab type was not
    extended.
    """
    # 1) literal label "Documentos" inside a `rtab` block
    has_label = re.search(
        r"rtab\b[^>]*>[^<]*Documentos",
        source,
        re.DOTALL,
    ) is not None
    # 2) branch on `t === 'documentos'` (handles both single and
    #    double quotes)
    has_branch = re.search(
        r"""t\s*===\s*['"]documentos['"]""",
        source,
    ) is not None
    return has_label and has_branch


def _imports_document_api(source: str, fn_name: str) -> bool:
    """Detect that `fn_name` is imported from `../../api/documents`.

    Accepts:

        import { fetchRecentDocuments, ... } from '../../api/documents'
        import { fetchRecentDocuments } from '../../api/documents'
    """
    pattern = (
        r"import\s*\{[^}]*\b"
        + re.escape(fn_name)
        + r"\b[^}]*\}\s*from\s*['\"]\.\.\/\.\.\/api\/documents['\"]"
    )
    return re.search(pattern, source) is not None


def _declares_doc_editor(source: str) -> bool:
    """Detect a local `function DocEditor(...)` component declaration
    inside EstrategiaRoom.tsx.

    The component is ported from DocumentosRoom (not imported) — the
    signature is something like:

        function DocEditor({
          doc,
          saveStatus,
          onSave,
          onClose,
        }: {
          doc: BluDocument
          saveStatus: SaveStatus
          onSave: (content: string) => void
          onClose: () => void
        }) { ... }
    """
    return re.search(r"function\s+DocEditor\s*\(", source) is not None


def _declares_approval_card_with_documentos_badge(source: str) -> bool:
    """Detect a local `function ApprovalCard(...)` declaration that uses
    the badge label "Documentos" (the docs variant of the card).

    The docs variant of ApprovalCard differs from the strategy variant
    by the agent label inside the `ag` div:

        <div className="ag"> ... Documentos </div>

    The strategy variant uses "Estratégia" (see EstrategiaRoom line
    ~473). The test guards against porting the wrong variant: it
    requires BOTH the function signature AND the "Documentos" badge
    label.
    """
    has_fn = re.search(r"function\s+ApprovalCard\s*\(", source) is not None
    if not has_fn:
        return False
    # The "Documentos" badge label must appear inside the ApprovalCard
    # body. We do a loose check: look for the literal "Documentos"
    # anywhere AFTER the function declaration. This is enough for a
    # source-inspection RED/GREEN test — the Coder is expected to put
    # the badge label inside the `ag` div of the card.
    fn_match = re.search(r"function\s+ApprovalCard\s*\(", source)
    if not fn_match:
        return False
    tail = source[fn_match.end():]
    return re.search(r">\s*Documentos\s*<", tail) is not None


def _renders_doc_editor_jsx(source: str) -> bool:
    """Detect a JSX usage of `<DocEditor ...>` in EstrategiaRoom.tsx."""
    return re.search(r"<\s*DocEditor\b", source) is not None


def _renders_approval_card_jsx(source: str) -> bool:
    """Detect a JSX usage of `<ApprovalCard ...>` in EstrategiaRoom.tsx."""
    return re.search(r"<\s*ApprovalCard\b", source) is not None


def _has_doc_subtab_labels(source: str) -> dict[str, bool]:
    """Detect the 5 sub-tab labels of the Documentos tab: Ativos,
    Rascunhos, Modelos, Base de Conhecimento, Config.

    Returns a dict with the presence of each label.
    """
    # We look for each label as a JSX text node. The DocumentosRoom
    # uses Portuguese capitalized labels inside a ternary chain
    # (Ativos / Rascunhos / Modelos / Base de Conhecimento / Config).
    # The EstrategiaRoom port should follow the same convention.
    return {
        "Ativos": re.search(r">\s*Ativos\s*<", source) is not None,
        "Rascunhos": re.search(r">\s*Rascunhos\s*<", source) is not None,
        "Modelos": re.search(r">\s*Modelos\s*<", source) is not None,
        "Base de Conhecimento": re.search(
            r">\s*Base de Conhecimento\s*<", source
        ) is not None,
        "Config": re.search(r">\s*Config\s*<", source) is not None,
    }


def _has_active_doc_id_state(source: str) -> bool:
    """Detect a `useState<string | null>(null)` (or similar) declaration
    for `activeDocId`.

    Accepts:

        const [activeDocId, setActiveDocId] = useState<string | null>(null)
        const [activeDocId, setActiveDocId] = useState<any>(null)
        const [activeDocId, setActiveDocId] = useState(null)
    """
    pattern = (
        r"const\s*\[\s*activeDocId\s*,\s*setActiveDocId\s*\]\s*=\s*useState"
    )
    return re.search(pattern, source) is not None


def _has_save_status_state(source: str) -> bool:
    """Detect a `useState<SaveStatus>(...)` (or `useState('idle')`)
    declaration for `saveStatus`.

    The migration can either declare a local `SaveStatus` type or
    inline the union literal. Both are accepted.
    """
    pattern = (
        r"const\s*\[\s*saveStatus\s*,\s*setSaveStatus\s*\]\s*=\s*useState"
    )
    return re.search(pattern, source) is not None


def _has_save_handler_for_doc_editor(source: str) -> bool:
    """Detect a save handler (function / useCallback / const) that
    references both `activeDocId` and the `saveDocument` API call —
    i.e. it is wired to persist doc content via the documents API.

    Loose check: look for any function body that mentions both
    `activeDocId` and `saveDocument(`. This is enough for a
    source-inspection RED/GREEN test.
    """
    return (
        re.search(r"\bactiveDocId\b", source) is not None
        and re.search(r"\bsaveDocument\s*\(", source) is not None
    )


def _state_identifier_collision(source: str) -> dict[str, bool]:
    """Verify that the new doc state identifiers do NOT collide with
    the strategy state identifiers that already exist in the file.

    Concretely:

        - `activeDocId` must be its own state slot (NOT aliased to
          `selectedReport`).
        - `saveStatus` must be its own state slot (NOT aliased to
          `reportContent`).
        - The doc tab state must NOT be aliased to `analyticsOpen`.

    The current EstrategiaRoom has these as `useState` declarations:

        const [analyticsOpen, setAnalyticsOpen] = useState(false)
        const [selectedReport, setSelectedReport] = useState(...)
        const [reportContent, setReportContent] = useState(...)
        const [loadingReport, setLoadingReport] = useState(false)

    After the port, the new doc state should appear as separate
    `useState` declarations. We check for the four required slots
    to coexist in the source:

        - activeDocId
        - saveStatus
        - selectedReport  (existing — must remain)
        - reportContent   (existing — must remain)
        - analyticsOpen   (existing — must remain)

    If any of the existing strategy state names is missing, the
    strategy was damaged by the port and this AC fails.
    """
    return {
        "activeDocId_declared": _has_active_doc_id_state(source),
        "saveStatus_declared": _has_save_status_state(source),
        "selectedReport_intact": re.search(
            r"const\s*\[\s*selectedReport\s*,\s*setSelectedReport\s*\]\s*=\s*useState",
            source,
        ) is not None,
        "reportContent_intact": re.search(
            r"const\s*\[\s*reportContent\s*,\s*setReportContent\s*\]\s*=\s*useState",
            source,
        ) is not None,
        "analyticsOpen_intact": re.search(
            r"const\s*\[\s*analyticsOpen\s*,\s*setAnalyticsOpen\s*\]\s*=\s*useState",
            source,
        ) is not None,
    }


# ── AC#1: Tab type + rtabs include 'documentos' ───────────────────────────


def test_estrategia_room_tab_type_includes_documentos():
    """AC#1a — `EstrategiaRoom.tsx` must extend its `type Tab =` union
    to include the literal `'documentos'`.

    Without this, `setTab('documentos')` would fail TypeScript's
    exhaustive-union check and the React state would be unreachable.
    """
    assert ESTRATEGIA_ROOM_PATH.exists(), (
        f"RED — source file not found: {ESTRATEGIA_ROOM_PATH}"
    )
    source = _read_source(ESTRATEGIA_ROOM_PATH)

    assert _tab_type_includes_documentos(source), (
        "RED — EstrategiaRoom.tsx does NOT include 'documentos' in its "
        "`type Tab =` union. Currently the union is "
        "`'decisoes' | 'analises' | 'historico' | 'config'`. Expected "
        "the union to be extended to "
        "`'decisoes' | 'analises' | 'historico' | 'config' | 'documentos'` "
        "so the Documentos sub-tab can be selected via setTab('documentos') "
        "without TypeScript errors."
    )


def test_estrategia_room_rtabs_renders_documentos_tab():
    """AC#1b — The `rtabs` div in EstrategiaRoom.tsx must render a tab
    labeled "Documentos" with a `t === 'documentos'` branch.

    The current `.map(...)` over the Tab union has a ternary chain
    that handles `decisoes` / `analises` / `historico` / `config`. The
    port must extend that chain with `t === 'documentos' ? 'Documentos'
    : ...`.
    """
    assert ESTRATEGIA_ROOM_PATH.exists(), (
        f"RED — source file not found: {ESTRATEGIA_ROOM_PATH}"
    )
    source = _read_source(ESTRATEGIA_ROOM_PATH)

    assert _rtabs_renders_documentos_tab(source), (
        "RED — EstrategiaRoom.tsx does NOT render a 'Documentos' "
        "tab inside `rtabs`. Expected the .map(...) over the Tab union "
        "to include a `t === 'documentos' ? 'Documentos' : ...` branch "
        "so the user can switch to the Documentos sub-tab from the "
        "Estrategia room header. The label 'Documentos' must appear "
        "as a JSX text node inside an `rtab` element."
    )


# ── AC#2: documents API imports ──────────────────────────────────────────


DOC_API_FUNCTIONS = [
    "fetchRecentDocuments",
    "fetchDraftDocuments",
    "fetchDocTemplates",
    "saveDocument",
    "createDocument",
    "publishDocument",
    "archiveDocument",
]


@pytest.mark.parametrize("fn_name", DOC_API_FUNCTIONS)
def test_estrategia_room_imports_document_api_function(fn_name: str):
    """AC#2 — EstrategiaRoom.tsx must import each of the 7 document API
    functions from `../../api/documents`.

    The 7 functions are: `fetchRecentDocuments`, `fetchDraftDocuments`,
    `fetchDocTemplates`, `saveDocument`, `createDocument`,
    `publishDocument`, `archiveDocument`. They are the contract of
    `apps/blu_v3/src/api/documents.ts` and the Documentos tab uses
    every one of them. Without these imports the sub-tabs (Ativos,
    Rascunhos, Modelos) and the save/publish/archive buttons would be
    referencing undeclared symbols and fail TypeScript / runtime.
    """
    assert ESTRATEGIA_ROOM_PATH.exists(), (
        f"RED — source file not found: {ESTRATEGIA_ROOM_PATH}"
    )
    assert DOCUMENTS_API_PATH.exists(), (
        f"RED — documents API not found: {DOCUMENTS_API_PATH}"
    )
    source = _read_source(ESTRATEGIA_ROOM_PATH)

    assert _imports_document_api(source, fn_name), (
        f"RED — EstrategiaRoom.tsx does NOT import `{fn_name}` from "
        "`../../api/documents`. Expected the import block to include "
        f"`{fn_name}` (alongside the other 6 document API functions) "
        "so the Documentos tab can fetch recent docs, drafts, and "
        "templates, and can save / create / publish / archive "
        "documents through the shared API."
    )


def test_estrategia_room_imports_document_api_from_correct_path():
    """AC#2b — The import path must be exactly `../../api/documents`.

    Catches a misnamed import (e.g. `./api/documents` or
    `../api/documents`) that would resolve to the wrong file and
    silently break the build.
    """
    assert ESTRATEGIA_ROOM_PATH.exists(), (
        f"RED — source file not found: {ESTRATEGIA_ROOM_PATH}"
    )
    source = _read_source(ESTRATEGIA_ROOM_PATH)

    pattern = (
        r"import\s*\{[^}]*\}\s*from\s*['\"]\.\.\/\.\.\/api\/documents['\"]"
    )
    assert re.search(pattern, source), (
        "RED — EstrategiaRoom.tsx does NOT have a `from "
        "'../../api/documents'` import. Expected a single named-import "
        "block from the documents API at the relative path "
        "`../../api/documents` (two levels up from "
        "`apps/blu_v3/src/pages/app/EstrategiaRoom.tsx` → "
        "`apps/blu_v3/src/api/documents.ts`)."
    )


# ── AC#3: DocEditor + ApprovalCard (docs) + 5 sub-tabs ───────────────────


def test_estrategia_room_declares_local_doc_editor():
    """AC#3a — EstrategiaRoom.tsx must declare a local
    `function DocEditor(...)` component (ported from DocumentosRoom,
    NOT imported from it).

    The component takes `doc`, `saveStatus`, `onSave`, and `onClose`
    props. We only require the function declaration to be present at
    module scope — its internals are exercised by the runtime, not
    by this source-inspection test.
    """
    assert ESTRATEGIA_ROOM_PATH.exists(), (
        f"RED — source file not found: {ESTRATEGIA_ROOM_PATH}"
    )
    source = _read_source(ESTRATEGIA_ROOM_PATH)

    assert _declares_doc_editor(source), (
        "RED — EstrategiaRoom.tsx does NOT declare a local "
        "`function DocEditor(...)` component. Expected the DocEditor "
        "from DocumentosRoom to be PORTED (declared locally) into "
        "EstrategiaRoom so the room can render the editor inside its "
        "own `ativos` sub-tab without coupling to DocumentosRoom. The "
        "signature should accept `doc`, `saveStatus`, `onSave`, and "
        "`onClose` props."
    )


def test_estrategia_room_renders_doc_editor_jsx():
    """AC#3b — EstrategiaRoom.tsx must render at least one
    `<DocEditor ... />` JSX element inside the `documentos` tab.

    Declaring without using is dead code; the test guards against the
    half-port where the component is defined but never wired into
    the `ativos` sub-tab.
    """
    assert ESTRATEGIA_ROOM_PATH.exists(), (
        f"RED — source file not found: {ESTRATEGIA_ROOM_PATH}"
    )
    source = _read_source(ESTRATEGIA_ROOM_PATH)

    assert _renders_doc_editor_jsx(source), (
        "RED — EstrategiaRoom.tsx declares `function DocEditor` but "
        "does NOT render <DocEditor ...> anywhere. Expected the "
        "Documentos sub-tab's `ativos` panel to render the editor "
        "with the active doc, e.g. "
        "`<DocEditor doc={activeDoc} saveStatus={saveStatus} "
        "onSave={handleSave} onClose={() => setActiveDocId(null)} />`. "
        "Without the JSX usage, the editor is unreachable from the UI."
    )


def test_estrategia_room_declares_approval_card_with_documentos_badge():
    """AC#3c — EstrategiaRoom.tsx must declare a local
    `function ApprovalCard(...)` component AND that component must
    use the badge label "Documentos" (the docs variant).

    This guards against (a) the half-port where the function is
    missing, and (b) the wrong-variant port where the strategy
    ApprovalCard (with badge "Estratégia") is reused — that would
    break the visual contract of the Documentos tab.
    """
    assert ESTRATEGIA_ROOM_PATH.exists(), (
        f"RED — source file not found: {ESTRATEGIA_ROOM_PATH}"
    )
    source = _read_source(ESTRATEGIA_ROOM_PATH)

    assert _declares_approval_card_with_documentos_badge(source), (
        "RED — EstrategiaRoom.tsx does NOT declare a local "
        "`function ApprovalCard(...)` component that uses the badge "
        "label 'Documentos'. The current local ApprovalCard (in the "
        "Decisões tab) uses the label 'Estratégia' and must NOT be "
        "reused for document approvals. The port should DECLARE a "
        "second, docs-variant ApprovalCard with the badge label "
        "'Documentos' inside its `ag` div (matching DocumentosRoom)."
    )


def test_estrategia_room_renders_docs_variant_approval_card_jsx():
    """AC#3d — EstrategiaRoom.tsx must render at least one
    `<ApprovalCard ... />` JSX element that is wired to the
    Documentos tab's approval flow — i.e. the JSX must appear
    INSIDE a `tab === 'documentos'` panel (or equivalent), not just
    in the Decisões tab (which uses the strategy variant).

    The current EstrategiaRoom renders `<ApprovalCard ...>` only
    inside the Decisões tab (the strategy variant), so this
    stricter check fails RED: the JSX in the Decisões panel is
    guarded by `tab === 'decisoes'`, and there is no panel guarded
    by `tab === 'documentos'` at all. The Coder must add a new
    Documentos panel that contains the docs-variant
    `<ApprovalCard ... />` JSX.
    """
    assert ESTRATEGIA_ROOM_PATH.exists(), (
        f"RED — source file not found: {ESTRATEGIA_ROOM_PATH}"
    )
    source = _read_source(ESTRATEGIA_ROOM_PATH)

    # The Documentos tab is selected by `tab === 'documentos'`. The
    # approvals panel must be guarded by this condition, and the
    # `<ApprovalCard>` JSX must be inside that guarded panel.
    #
    # Source-inspection approach: find a `<ApprovalCard ... />`
    # opening tag, then check that the `tab === 'documentos'`
    # condition appears BEFORE that tag (within a reasonable
    # window) in the source. If only the strategy-variant JSX
    # (inside `tab === 'decisoes'`) is present, this check fails.
    approval_card_opens = list(
        re.finditer(r"<\s*ApprovalCard\b", source)
    )
    documentos_branch = re.search(
        r"""tab\s*===\s*['"]documentos['"]""",
        source,
    )
    assert documentos_branch, (
        "RED — EstrategiaRoom.tsx does NOT have a `tab === 'documentos'` "
        "branch anywhere. Expected a JSX panel guarded by `tab === "
        "'documentos'` that contains the docs-variant `<ApprovalCard ... "
        "/>` and `<DocEditor ... />` markup. Without this branch, the "
        "Documentos tab is unreachable from the UI even if the type "
        "extension passes (AC#1a)."
    )

    assert approval_card_opens, (
        "RED — EstrategiaRoom.tsx does NOT render <ApprovalCard ...> "
        "anywhere. Expected the Documentos sub-tab's `ativos` panel "
        "to render the docs-variant ApprovalCard for each pending "
        "document approval, e.g. "
        "`<ApprovalCard ap={ap} onApprove={...} onSnooze={...} />`. "
        "Without this JSX usage, the approval flow is unreachable."
    )

    # Require at least one <ApprovalCard ...> opening tag to come
    # AFTER the `tab === 'documentos'` branch marker — that is the
    # only way the docs-variant card can be rendered inside the
    # Documentos panel. The strategy-variant JSX (in the Decisões
    # tab) comes BEFORE the Documentos branch, so it does not
    # satisfy this check.
    docs_open_after = [
        m for m in approval_card_opens if m.start() > documentos_branch.start()
    ]
    assert docs_open_after, (
        "RED — EstrategiaRoom.tsx has a `tab === 'documentos'` branch "
        "but the <ApprovalCard ...> JSX is rendered BEFORE that branch "
        "(i.e. inside the strategy Decisões tab, not the Documentos "
        "tab). Expected the docs-variant <ApprovalCard ap={ap} "
        "onApprove={...} onSnooze={...} /> to be rendered INSIDE the "
        "`tab === 'documentos'` panel — the strategy variant must "
        "remain in the Decisões tab. The Decisões tab's existing "
        "ApprovalCard is the wrong variant and cannot be reused."
    )


@pytest.mark.parametrize(
    "label",
    ["Ativos", "Rascunhos", "Modelos", "Base de Conhecimento", "Config"],
)
def test_estrategia_room_has_documentos_subtab_label(label: str):
    """AC#3e — The Documentos tab in EstrategiaRoom.tsx must expose the
    same 5 sub-tabs as DocumentosRoom: Ativos, Rascunhos, Modelos,
    Base de Conhecimento, Config.

    Each sub-tab is checked independently so a partial port (e.g.
    only 3 of 5 sub-tabs) is caught loudly.
    """
    assert ESTRATEGIA_ROOM_PATH.exists(), (
        f"RED — source file not found: {ESTRATEGIA_ROOM_PATH}"
    )
    source = _read_source(ESTRATEGIA_ROOM_PATH)

    presence = _has_doc_subtab_labels(source)
    assert presence.get(label, False), (
        f"RED — EstrategiaRoom.tsx is missing the '{label}' sub-tab "
        f"label for the Documentos tab. Detected labels: {presence}. "
        "Expected all 5 sub-tabs to be rendered as JSX text nodes "
        "inside the Documentos tab content (matching DocumentosRoom's "
        "shape: Ativos / Rascunhos / Modelos / Base de Conhecimento / "
        "Config)."
    )


# ── AC#4: DocEditor is actionable ────────────────────────────────────────


def test_estrategia_room_has_active_doc_id_state():
    """AC#4a — EstrategiaRoom.tsx must introduce an `activeDocId` state
    slot (typed as `string | null` or compatible).

    Without `activeDocId`, the editor cannot know which document the
    user clicked on in the recent-docs list — the entire Documentos
    tab becomes unclickable.
    """
    assert ESTRATEGIA_ROOM_PATH.exists(), (
        f"RED — source file not found: {ESTRATEGIA_ROOM_PATH}"
    )
    source = _read_source(ESTRATEGIA_ROOM_PATH)

    assert _has_active_doc_id_state(source), (
        "RED — EstrategiaRoom.tsx does NOT declare "
        "`const [activeDocId, setActiveDocId] = useState<...>(null)`. "
        "Expected a new state slot to track which document the user "
        "selected in the Documentos tab's recent-docs list, typed as "
        "`string | null` (or any compatible nullable). The state "
        "must be independent of the existing strategy state — see AC#5."
    )


def test_estrategia_room_has_save_status_state():
    """AC#4b — EstrategiaRoom.tsx must introduce a `saveStatus` state
    slot for the DocEditor (typed as `'idle' | 'saving' | 'saved' |
    'error'` or compatible).

    Without `saveStatus`, the editor cannot communicate save
    progress / success / failure back to the user.
    """
    assert ESTRATEGIA_ROOM_PATH.exists(), (
        f"RED — source file not found: {ESTRATEGIA_ROOM_PATH}"
    )
    source = _read_source(ESTRATEGIA_ROOM_PATH)

    assert _has_save_status_state(source), (
        "RED — EstrategiaRoom.tsx does NOT declare "
        "`const [saveStatus, setSaveStatus] = useState<...>('idle')`. "
        "Expected a new state slot to track the doc-editor save "
        "lifecycle, typed as `'idle' | 'saving' | 'saved' | 'error'` "
        "(either via a local `SaveStatus` type or an inline union)."
    )


def test_estrategia_room_has_save_handler_for_doc_editor():
    """AC#4c — There must be a save handler that references both
    `activeDocId` and the `saveDocument` API call — i.e. the handler
    is wired to persist doc content through the documents API.

    The handler can be a `useCallback`, a plain function, or an
    inline arrow — the test only requires the wiring to be present
    in the source.
    """
    assert ESTRATEGIA_ROOM_PATH.exists(), (
        f"RED — source file not found: {ESTRATEGIA_ROOM_PATH}"
    )
    source = _read_source(ESTRATEGIA_ROOM_PATH)

    assert _has_save_handler_for_doc_editor(source), (
        "RED — EstrategiaRoom.tsx does NOT wire a save handler that "
        "calls `saveDocument(...)` with the current `activeDocId`. "
        "Expected a handler (e.g. `handleSave = useCallback((content) "
        "=> saveMut.mutate({ id: activeDocId, content }), "
        "[activeDocId, saveMut])`) so the DocEditor can persist edits "
        "through the documents API. Without this wiring, the editor's "
        "Salvar button is dead."
    )


# ── AC#5: state isolation between documents and strategy ─────────────────


def test_estrategia_room_doc_state_does_not_collide_with_strategy_state():
    """AC#5 — The new document state identifiers (`activeDocId`,
    `saveStatus`) must coexist with the existing strategy state
    identifiers (`selectedReport`, `reportContent`, `analyticsOpen`)
    as SEPARATE `useState` slots.

    The migration is additive: strategy state must remain intact,
    and the new doc state must be a separate namespace. If any of
    the strategy state slots is missing, the port damaged the
    strategy tab. If the doc state is missing, the port is
    incomplete.
    """
    assert ESTRATEGIA_ROOM_PATH.exists(), (
        f"RED — source file not found: {ESTRATEGIA_ROOM_PATH}"
    )
    source = _read_source(ESTRATEGIA_ROOM_PATH)

    state = _state_identifier_collision(source)
    missing_doc = [
        k for k in ("activeDocId_declared", "saveStatus_declared")
        if not state.get(k, False)
    ]
    missing_strategy = [
        k for k in (
            "selectedReport_intact",
            "reportContent_intact",
            "analyticsOpen_intact",
        )
        if not state.get(k, False)
    ]

    problems: list[str] = []
    if missing_doc:
        problems.append(
            "document state slots are missing: "
            + ", ".join(missing_doc)
            + " (expected both `activeDocId` and `saveStatus` to be "
            "declared as `useState` slots)"
        )
    if missing_strategy:
        problems.append(
            "strategy state slots were damaged by the port: "
            + ", ".join(missing_strategy)
            + " (the Documentos port must be ADDITIVE — "
            "`selectedReport`, `reportContent`, and `analyticsOpen` "
            "must remain as `useState` declarations so the Decisões / "
            "Análises tabs keep working)"
        )

    assert not problems, (
        "RED — EstrategiaRoom.tsx state isolation is broken.\n"
        + "\n".join(f"  - {p}" for p in problems)
        + f"\nDetected state: {state}"
    )


def test_estrategia_room_tab_state_not_aliased_to_analytics_open():
    """AC#5b — The Documentos tab selection must NOT be aliased to
    `analyticsOpen`. Specifically: the code path that switches to
    the Documentos tab must call `setTab('documentos')` (or
    equivalent) — NOT `setAnalyticsOpen(true)`.

    We check for the symbolic name `setTab('documentos')` so a
    future reader can see the tab switch is routed through the
    `tab` state slot, not the `analyticsOpen` boolean.
    """
    assert ESTRATEGIA_ROOM_PATH.exists(), (
        f"RED — source file not found: {ESTRATEGIA_ROOM_PATH}"
    )
    source = _read_source(ESTRATEGIA_ROOM_PATH)

    has_set_tab_documentos = re.search(
        r"""setTab\s*\(\s*['"]documentos['"]\s*\)""",
        source,
    ) is not None
    assert has_set_tab_documentos, (
        "RED — EstrategiaRoom.tsx does NOT have a `setTab('documentos')` "
        "call. Expected the Documentos tab to be reachable through the "
        "same `tab` state slot as decisoes / analises / historico / "
        "config, NOT through a separate `analyticsOpen` boolean. The "
        "`setTab` function already exists in the file and the `tab` "
        "state already supports `'documentos'` once the Tab type is "
        "extended (see AC#1a) — the port just needs to call it."
    )
