"""RED test for ALL 10 ACs — StepInfo frontend adjustments.

GOAL:
    Validar todas as 10 Acceptance Criteria do behavior
    'Ajustes frontend StepInfo — layout, tags de confianca, remover Foco'
    em apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx.

BEHAVIOR:
    B-ALL — StepInfo layout final: website na row2, ordem dos campos,
    tags de confianca verde/amarela em CNPJ e telefone, Foco removido.

    O StepInfo (Step Empresa) no OnboardingApp.tsx deve:

    1. Website no row2 ao lado do nome
    2. Ordem dos campos: nome -> website -> empresa -> CNPJ -> setor -> porte
    3. Campo "Foco atual do negocio" (primaryFocus) removido do StepInfo
    4. saveDraft em handleNext nao envia primaryFocus
    5. CNPJ no scrape-grid com tag de confianca verde/amarela
    6. Telefone no scrape-grid com tag de confianca verde/amarela
    7. Cores: verde #16a34a/#dcfce7, amarelo #ca8a04/#fef9c3
    8. Tags ao lado do valor do campo em flex container com gap:6
    9. Todos os inputs do StepInfo tem onChange (campos editaveis)
    10. Step Dados segue funcionando (regressao zero)

AC (Acceptance Criteria):
    AC#1  — Website field moved to same line as nome (row2: nome + website)
    AC#2  — New field order: nome+website -> empresa -> CNPJ -> setor -> porte
    AC#3  — "Foco atual do negocio" (primaryFocus) removed from StepInfo
    AC#4  — saveDraft in handleNext has no primaryFocus
    AC#5  — CNPJ ScrapeField in scrape-grid with confidence tag
    AC#6  — Telefone ScrapeField in scrape-grid with confidence tag
    AC#7  — Tag colors: green #16a34a/#dcfce7, yellow #ca8a04/#fef9c3
    AC#8  — Tags in flex container with gap:6 alongside field values
    AC#9  — All input elements in StepInfo have onChange attribute
    AC#10 — function StepData({ still exists (no regression)

DECISION:
    Estrategia: source-inspection via pytest
    Arquivo alvo: apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx
    Secao alvo: StepInfo component

Anti-Goals (must NOT be violated):
    1. NAO quebrar o Step Dados (proximo step)
    2. NAO quebrar a logica de auto-preenchimento existente
    3. NAO remover onChange handlers (campos permanecem editaveis)
    4. NAO importar TypeScript (test puro de inspecao de texto)
    5. NAO mockar nada (test deterministico de string-matching)

Estado atual: RED — as seguintes features NAO existem no codigo:
    - row2 ainda tem 'Seu nome' + 'Website' parcialmente implementado
    - Ordem dos campos pode estar fora do spec
    - 'primaryFocus' e 'Foco atual' podem nao ter sido removidos completamente
    - Tags de confianca verde/amarela por campo podem nao estar visiveis
    - CNPJ/Telefone com tag inline ao lado podem nao estar com gap:6
"""

from pathlib import Path

import pytest

# ── Path resolution (repo root) ──────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

ONBOARDING_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "onboarding"
    / "OnboardingApp.tsx"
)


# ── Override root conftest cleanup (pure file-based test) ────────────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test is pure file inspection, no DB."""
    yield


# ── Helpers ──────────────────────────────────────────────────────────────────


def _read_onboarding() -> str:
    """Read the full OnboardingApp.tsx source as text."""
    assert ONBOARDING_PATH.exists(), (
        f"OnboardingApp.tsx not found at {ONBOARDING_PATH}"
    )
    return ONBOARDING_PATH.read_text(encoding="utf-8")


def _extract_step_info_section(source: str) -> str:
    """Extract the StepInfo component body from the source.

    Returns the text from 'function StepInfo({' up to the closing '}'
    that ends the component.
    """
    marker = "function StepInfo({"
    idx = source.find(marker)
    assert idx != -1, (
        f"Cannot find 'function StepInfo({{' in {ONBOARDING_PATH}"
    )

    # Find the closing ) of the destructured params
    close_paren = source.find(")", idx)
    assert close_paren != -1, "Cannot find closing ) for StepInfo params"
    brace_start = source.find("{", close_paren)
    assert brace_start != -1, "Cannot find opening brace for StepInfo body"

    # Walk brace depth to find matching closing brace
    depth = 0
    end = -1
    for i in range(brace_start, len(source)):
        ch = source[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    assert end != -1, "Cannot find closing brace for StepInfo"
    return source[idx:end]


def _extract_row2_content(source: str) -> str:
    """Extract content of the <div className='row2'> inside StepInfo.

    Returns the text content between the row2 opening tag and its matching
    closing </div> at the same depth.
    """
    step_info = _extract_step_info_section(source)
    marker = 'className="row2"'
    idx = step_info.find(marker)
    assert idx != -1, "row2 div not found in StepInfo"

    # Find the > that closes the opening tag
    content_start = step_info.find(">", idx) + 1

    # Walk to find matching </div> at the same nesting level.
    # We start at depth 1 (inside the row2 div). We need to find when
    # the depth returns to 0.
    depth = 1
    i = content_start
    while i < len(step_info):
        if step_info[i:i + 5] == "<div " or step_info[i:i + 5] == "<div>":
            depth += 1
            i += 5
        elif step_info[i:i + 6] == "</div>":
            depth -= 1
            if depth == 0:
                return step_info[content_start:i]
            i += 6
        else:
            i += 1

    return step_info[content_start:]


def _extract_step_info_jsx(source: str) -> str:
    """Extract the JSX return section of StepInfo (everything after 'return (').

    This avoids matching labels that appear in the function signature
    (e.g. 'initialWebsite' contains 'Website' as a substring).
    """
    step_info = _extract_step_info_section(source)
    return_idx = step_info.find("return (")
    assert return_idx != -1, "return ( not found in StepInfo"
    return step_info[return_idx:]


def _extract_handle_next(source: str) -> str:
    """Extract the body of `async function handleNext()` from StepInfo.

    Returns the text from the function signature up to the matching '}'
    that closes the function body.
    """
    step_info = _extract_step_info_section(source)
    marker = "async function handleNext()"
    idx = step_info.find(marker)
    assert idx != -1, "async function handleNext() not found in StepInfo"

    brace_start = step_info.find("{", idx)
    assert brace_start != -1, "Cannot find opening brace for handleNext"

    depth = 0
    end = -1
    for i in range(brace_start, len(step_info)):
        ch = step_info[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    assert end != -1, "Cannot find closing brace for handleNext"
    return step_info[idx:end]


def _extract_scrape_grid_section(source: str) -> str:
    """Extract the scrape-grid div content from StepInfo.

    Walks JSX tag depth from the scrape-grid <div> opening to the matching
    </div> at the same depth, returning all the children inside.
    """
    step_info = _extract_step_info_section(source)
    marker = 'className="scrape-grid"'
    idx = step_info.find(marker)
    assert idx != -1, "scrape-grid div not found in StepInfo"

    # Find the > that closes the opening tag
    gt_idx = step_info.find(">", idx)
    assert gt_idx != -1, "Cannot find '>' after scrape-grid marker"

    content_start = gt_idx + 1

    # Walk JSX tag depth
    depth = 1
    i = content_start
    while i < len(step_info):
        # Check for opening <div (not </div>, not self-closing in unusual ways)
        if step_info[i:i + 5] == "<div " or step_info[i:i + 5] == "<div>":
            depth += 1
            i += 5
        elif step_info[i:i + 6] == "</div>":
            depth -= 1
            if depth == 0:
                return step_info[content_start:i]
            i += 6
        else:
            i += 1

    return step_info[content_start:]


def _extract_inputs_in_step_info(source: str) -> list[str]:
    """Extract all <input ...> opening tag texts in StepInfo.

    Returns the raw text of each input tag (e.g. "<input type=\"text\" ... />").
    """
    import re

    step_info = _extract_step_info_section(source)
    # Match <input followed by any attrs and ending in /> or > (not </input)
    # Use a non-greedy regex that handles multi-line
    pattern = re.compile(r"<input\b[^>]*/?>", re.DOTALL)
    matches = pattern.findall(step_info)
    return matches


# ── Tests ────────────────────────────────────────────────────────────────────


def test_source_file_exists():
    """Sanity check: the source file must exist and contain StepInfo.

    This test should always pass as long as the file is in place.
    """
    assert ONBOARDING_PATH.exists(), (
        f"Source file not found: {ONBOARDING_PATH}"
    )
    source = _read_onboarding()
    assert "function StepInfo({" in source, (
        "StepInfo component not found in OnboardingApp.tsx"
    )


def test_ac1_website_in_row2():
    """AC#1 — Website field must be in the row2 div alongside 'Seu nome'.

    RED expected: row2 currently has 'Seu nome' but 'Website' is in a
    separate field div, NOT inside row2.
    GREEN expected: The row2 div contains BOTH 'Seu nome' AND 'Website'
    labels/inputs.
    """
    source = _read_onboarding()
    row2_content = _extract_row2_content(source)

    has_seu_nome = "Seu nome" in row2_content
    has_website = "Website" in row2_content

    assert has_seu_nome and has_website, (
        "RED — Website is NOT in the same row2 div as 'Seu nome'. "
        f"row2 content: {row2_content[:400]!r}. "
        "Expected: both 'Seu nome' and 'Website' fields inside the "
        "<div className='row2'> block, side by side. "
        "The Coder must move the website field into the row2 div alongside "
        "the nome field, keeping the website onBlur handleWebsiteBlur intact."
    )


def test_ac2_field_order():
    """AC#2 — Fields must appear in correct order in StepInfo.

    RED expected: order is currently row2(nome+empresa) -> CNPJ -> website
    -> scrape-panel -> setor -> porte.
    GREEN expected order: 'Seu nome' < 'Website' < 'Nome da empresa' <
    'CPF / CNPJ' < 'Setor' < 'Tamanho da equipe'.
    """
    source = _read_onboarding()
    step_jsx = _extract_step_info_jsx(source)

    # Find each key label substring and compare positions WITHIN the JSX
    # (not the function signature) to avoid matching 'initialWebsite' etc.
    pos_seu_nome = step_jsx.find("Seu nome")
    pos_website = step_jsx.find("Website")
    pos_nome_empresa = step_jsx.find("Nome da empresa")
    pos_cnpj = step_jsx.find("CPF / CNPJ")
    pos_setor = step_jsx.find("Setor *")
    pos_porte = step_jsx.find("Tamanho da equipe")

    # All must be found
    missing = []
    if pos_seu_nome == -1:
        missing.append("Seu nome")
    if pos_website == -1:
        missing.append("Website")
    if pos_nome_empresa == -1:
        missing.append("Nome da empresa")
    if pos_cnpj == -1:
        missing.append("CPF / CNPJ")
    if pos_setor == -1:
        missing.append("Setor *")
    if pos_porte == -1:
        missing.append("Tamanho da equipe")

    assert not missing, (
        f"RED — Could not find labels in StepInfo JSX: {missing}. "
        f"StepInfo JSX length: {len(step_jsx)} chars."
    )

    assert pos_seu_nome < pos_website, (
        f"RED — 'Seu nome' (pos={pos_seu_nome}) must come before "
        f"'Website' (pos={pos_website})"
    )
    assert pos_website < pos_nome_empresa, (
        f"RED — 'Website' (pos={pos_website}) must come before "
        f"'Nome da empresa' (pos={pos_nome_empresa})"
    )
    assert pos_nome_empresa < pos_cnpj, (
        f"RED — 'Nome da empresa' (pos={pos_nome_empresa}) must come before "
        f"'CPF / CNPJ' (pos={pos_cnpj})"
    )
    assert pos_cnpj < pos_setor, (
        f"RED — 'CPF / CNPJ' (pos={pos_cnpj}) must come before "
        f"'Setor *' (pos={pos_setor})"
    )
    assert pos_setor < pos_porte, (
        f"RED — 'Setor *' (pos={pos_setor}) must come before "
        f"'Tamanho da equipe' (pos={pos_porte})"
    )


def test_ac3_primary_focus_removed():
    """AC#3 — 'primaryFocus' and 'Foco atual' must NOT appear in StepInfo.

    RED expected: 'primaryFocus' variable and 'Foco atual do negocio' label
    are still present in the StepInfo component.
    GREEN expected: neither 'primaryFocus' nor 'Foco atual' appears anywhere
    in the StepInfo section.
    """
    source = _read_onboarding()
    step_info = _extract_step_info_section(source)

    assert "primaryFocus" not in step_info, (
        "RED — The variable 'primaryFocus' is still present in StepInfo. "
        "The Coder must remove it (state, setPrimaryFocus, onClick handlers, "
        "and the saveDraft field) along with the PRIMARY_FOCUS radio-pills "
        "section in the scrape-panel."
    )

    assert "Foco atual" not in step_info, (
        "RED — The label 'Foco atual' is still present in StepInfo. "
        "The Coder must remove the 'Foco atual do negocio' radio-pills "
        "section from the scrape-panel in StepInfo (contextual questions "
        "should contain only 'Principal produto ou servico')."
    )


def test_ac4_savedraft_no_primary_focus():
    """AC#4 — saveDraft in handleNext must not reference primaryFocus.

    RED expected: saveDraft call inside handleNext includes a
    primaryFocus: ... key in the patch object.
    GREEN expected: the saveDraft call has no primaryFocus field.
    """
    source = _read_onboarding()
    handle_next = _extract_handle_next(source)

    # Look for saveDraft call and check if it contains primaryFocus
    assert "saveDraft" in handle_next, (
        "saveDraft call not found in handleNext"
    )

    assert "primaryFocus" not in handle_next, (
        "RED — The saveDraft call in handleNext still references 'primaryFocus'. "
        "After removing primaryFocus from StepInfo, the saveDraft patch in "
        "handleNext should NOT include primaryFocus. "
        f"handleNext body: {handle_next}"
    )


def test_ac5_cnpj_confidence_tag():
    """AC#5 — scrape-grid must contain a CNPJ ScrapeField with confidence tag.

    RED expected: no CNPJ ScrapeField with label='CNPJ' in the scrape-grid,
    OR no confidence tag span next to it.
    GREEN expected: A <ScrapeField label='CNPJ' ... /> is rendered in the
    scrape-grid div when siteContext.cnpj is present, AND a confidence tag
    span (Confianca alta or Confianca media) is rendered next to it.
    """
    source = _read_onboarding()
    scrape_grid = _extract_scrape_grid_section(source)

    has_cnpj_field = 'label="CNPJ"' in scrape_grid
    has_confianca_alta = "Confiança alta" in scrape_grid or "Confianca alta" in scrape_grid
    has_confianca_media = "Confiança média" in scrape_grid or "Confianca media" in scrape_grid

    assert has_cnpj_field, (
        "RED — No ScrapeField with label='CNPJ' found in scrape-grid. "
        "Expected: a CNPJ ScrapeField rendered when siteContext.cnpj is present."
    )

    assert has_confianca_alta or has_confianca_media, (
        "RED — No confidence tag ('Confianca alta' or 'Confianca media') "
        "found next to the CNPJ ScrapeField in the scrape-grid. "
        "Expected: a green 'Confianca alta' tag for confidence >= 0.7, "
        "or a yellow 'Confianca media' tag for 0.3 <= confidence < 0.7, "
        "rendered in a flex container alongside the CNPJ value."
    )


def test_ac6_telefone_confidence_tag():
    """AC#6 — scrape-grid must contain a Telefone ScrapeField with confidence tag.

    RED expected: no Telefone ScrapeField with label='Telefone' in the
    scrape-grid, OR no confidence tag span next to it.
    GREEN expected: A <ScrapeField label='Telefone' ... /> is rendered in the
    scrape-grid div when siteContext.telefone is present, AND a confidence
    tag span is rendered next to it.
    """
    source = _read_onboarding()
    scrape_grid = _extract_scrape_grid_section(source)

    has_telefone_field = 'label="Telefone"' in scrape_grid
    has_confianca_alta = "Confiança alta" in scrape_grid or "Confianca alta" in scrape_grid
    has_confianca_media = "Confiança média" in scrape_grid or "Confianca media" in scrape_grid

    assert has_telefone_field, (
        "RED — No ScrapeField with label='Telefone' found in scrape-grid. "
        "Expected: a Telefone ScrapeField rendered when siteContext.telefone "
        "is present, with a delay of 500ms."
    )

    assert has_confianca_alta or has_confianca_media, (
        "RED — No confidence tag ('Confianca alta' or 'Confianca media') "
        "found next to the Telefone ScrapeField in the scrape-grid. "
        "Expected: a confidence tag span rendered alongside the Telefone "
        "value in a flex container with gap:6."
    )


def test_ac7_tag_colors():
    """AC#7 — Tag colors must use specific hex codes.

    RED expected: tag spans use 'var(--green)' or 'var(--amber)' instead of
    the specific hex codes #16a34a / #dcfce7 (green) or #ca8a04 / #fef9c3
    (yellow).
    GREEN expected: Confidence tag spans in the scrape-grid use the exact
    hex colors: green text on #dcfce7 background, yellow text on #fef9c3
    background.
    """
    source = _read_onboarding()
    scrape_grid = _extract_scrape_grid_section(source)

    # Green tag: color #16a34a, background #dcfce7
    has_green_color = "#16a34a" in scrape_grid
    has_green_bg = "#dcfce7" in scrape_grid

    # Yellow tag: color #ca8a04, background #fef9c3
    has_yellow_color = "#ca8a04" in scrape_grid
    has_yellow_bg = "#fef9c3" in scrape_grid

    assert has_green_color, (
        "RED — Green tag color #16a34a not found in scrape-grid. "
        "Expected: 'color: #16a34a' in the green confidence tag span."
    )
    assert has_green_bg, (
        "RED — Green tag background #dcfce7 not found in scrape-grid. "
        "Expected: 'background: #dcfce7' in the green confidence tag span."
    )
    assert has_yellow_color, (
        "RED — Yellow tag color #ca8a04 not found in scrape-grid. "
        "Expected: 'color: #ca8a04' in the yellow confidence tag span."
    )
    assert has_yellow_bg, (
        "RED — Yellow tag background #fef9c3 not found in scrape-grid. "
        "Expected: 'background: #fef9c3' in the yellow confidence tag span."
    )


def test_ac8_tags_alongside():
    """AC#8 — Confidence tags must be in a flex container with gap:6 next to the field.

    RED expected: the ScrapeField and confidence tag span are rendered as
    separate siblings, OR the flex container uses a different gap value.
    GREEN expected: A <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
    wraps the ScrapeField and the confidence tag span, so they render
    side-by-side with 6px spacing.
    """
    source = _read_onboarding()
    scrape_grid = _extract_scrape_grid_section(source)

    # Look for the flex container with gap:6 wrapping CNPJ and Telefone fields
    has_flex_gap_6 = "display: 'flex'" in scrape_grid and "gap: 6" in scrape_grid

    assert has_flex_gap_6, (
        "RED — No flex container with 'display: flex' and 'gap: 6' found in "
        "the scrape-grid. Expected: a <div style={{ display: 'flex', "
        "alignItems: 'center', gap: 6 }}> wrapping the CNPJ/Telefone "
        "ScrapeField and its confidence tag span, so they appear side-by-side "
        "with 6px spacing."
    )


def test_ac9_fields_editable():
    """AC#9 — All <input> elements in StepInfo must have an onChange attribute.

    RED expected: at least one <input> tag in StepInfo is missing the
    onChange handler (e.g. type='submit', type='hidden', or a static input).
    GREEN expected: every <input> tag rendered inside StepInfo has an
    onChange={...} attribute, so the user can edit the field.
    """
    source = _read_onboarding()
    inputs = _extract_inputs_in_step_info(source)

    assert len(inputs) > 0, (
        "RED — No <input> elements found in StepInfo. "
        "Expected at least: nome, website, empresa, cnpj, produtoServico."
    )

    inputs_without_onchange = [
        inp for inp in inputs if "onChange" not in inp
    ]

    assert not inputs_without_onchange, (
        f"RED — Found {len(inputs_without_onchange)} <input> element(s) in "
        f"StepInfo WITHOUT an onChange handler: {inputs_without_onchange}. "
        f"All inputs (total {len(inputs)}) must be editable: {inputs}."
    )


def test_ac10_step_dados_no_regression():
    """AC#10 — function StepData({ must still exist (regression check).

    This is a no-regression test. The Step Dados step is the next step
    after Step Empresa. If anyone accidentally removes or renames the
    StepData function, this test will fail.
    """
    source = _read_onboarding()

    assert "function StepData({" in source, (
        "REGRESSION — function StepData({ not found in OnboardingApp.tsx. "
        "The Step Dados component must remain in place for the onboarding "
        "flow to continue from Step Empresa to the data sources step."
    )
