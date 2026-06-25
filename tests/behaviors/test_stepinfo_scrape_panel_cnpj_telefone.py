"""
RED test for StepInfo scrape panel — CNPJ, Telefone, confidence tags in scrape grid.

GOAL:
    Ajustes no StepInfo (Step Empresa) no OnboardingApp.tsx para refletir
    as mudanças de layout e UX do Step Empresa.

BEHAVIOR:
    B4 — Scrape panel: exibir CNPJ e telefone com tags de confiança

    O scrape-panel no StepInfo deve exibir:
    1. CNPJ com tag de confiança (verde se confidence >= 0.7, amarela se >= 0.3)
    2. Telefone com tag de confiança (verde/amarela)
    3. handleWebsiteBlur deve auto-preenche telefone quando ctx.telefone presente
    4. SiteContext interface deve incluir telefone
    5. handleNext deve enviar telefone no saveDraft
    6. siteContext sem cnpj/telefone continua funcionando como antes

AC (Acceptance Criteria):
    AC#5 — CNPJ exibido no scrape panel quando siteContext.cnpj presente, com tag de confiança
    AC#6 — Telefone exibido no scrape panel quando siteContext.telefone presente, com tag de confiança
    AC#9 — Scrape panel atualizado para mostrar CNPJ e telefone ao lado dos campos existentes
    AC#8 — Step Dados funciona sem alterações (regressão zero)

DECISION:
    Estratégia: source-inspection via pytest
    Arquivo alvo: apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx
    Seções alvo: SiteContext interface, scrape-grid, handleWebsiteBlur, handleNext

Anti-Goals (must NOT be violated):
    1. NÃO quebrar auto-preenchimento existente (nome empresa, CNPJ, vertical)
    2. NÃO remover onChange handlers (campos permanecem editáveis)
    3. NÃO quebrar Step Dados — novos campos no draft não devem causar erro de schema
    4. NÃO remover tags de confiança existentes no header do scrape-panel

Estado atual: RED — as seguintes features NÃO existem no código:
    - SiteContext interface NÃO tem campo `telefone`
    - Scrape-grid NÃO renderiza CNPJ como ScrapeField
    - Scrape-grid NÃO renderiza telefone como ScrapeField
    - handleWebsiteBlur NÃO auto-preenche telefone
    - handleNext NÃO envia telefone no saveDraft
    - Não há tags de confiança individuais por campo (CNPJ, telefone)
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


def _extract_interface_section(source: str, interface_name: str) -> str:
    """Extract a TypeScript interface block from the source by name.

    Returns the full text of `interface <name> { ... }`.
    """
    marker = f"interface {interface_name} "
    idx = source.find(marker)
    if idx == -1:
        return ""

    # Find the opening { — could be on same line or next
    brace_start = source.find("{", idx)
    if brace_start == -1:
        return ""

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

    if end == -1:
        return ""

    return source[idx:end]


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

    close_paren = source.find(")", idx)
    assert close_paren != -1, "Cannot find closing ) for StepInfo params"
    brace_start = source.find("{", close_paren)
    assert brace_start != -1, "Cannot find opening brace for StepInfo body"

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


def _extract_handle_website_blur(source: str) -> str:
    """Extract the body of `handleWebsiteBlur` from the source.

    Returns the text from 'async function handleWebsiteBlur(' up to the
    next top-level function declaration or '}' that closes the function.
    """
    marker = "async function handleWebsiteBlur("
    idx = source.find(marker)
    assert idx != -1, (
        f"Could not find '{marker}' in {ONBOARDING_PATH}"
    )

    brace_start = source.find("{", idx)
    assert brace_start != -1, "Could not find opening brace for handleWebsiteBlur"

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

    assert end != -1, "Could not find closing brace for handleWebsiteBlur"
    return source[idx:end]


def _extract_handle_next(source: str) -> str:
    """Extract the body of `handleNext` from the source."""
    marker = "async function handleNext()"
    idx = source.find(marker)
    assert idx != -1, (
        f"Could not find 'async function handleNext()' in {ONBOARDING_PATH}"
    )

    brace_start = source.find("{", idx)
    assert brace_start != -1, "Could not find opening brace for handleNext"

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

    assert end != -1, "Could not find closing brace for handleNext"
    return source[idx:end]


def _extract_scrape_grid_section(source: str) -> str:
    """Extract the scrape-grid div content from the JSX.

    Returns text from 'className=\"scrape-grid\"' to the closing </div>
    at the same depth.
    """
    step_info = _extract_step_info_section(source)
    marker = 'className="scrape-grid"'
    idx = step_info.find(marker)
    if idx == -1:
        return ""

    # Find the opening >
    content_start = step_info.find(">", idx) + 1

    # Find matching </div> for this scrape-grid div
    # Since JSX doesn't have explicit closing for the grid div itself,
    # we look for the next closing </div> that ends the grid
    # The scrape-grid is typically: <div className="scrape-grid">{children}</div>
    # Find the actual opening div tag's closing >
    div_end = step_info.find("</div>", content_start)
    if div_end == -1:
        return step_info[idx:]

    return step_info[idx:div_end + 6]


def _extract_scrape_panel_section(source: str) -> str:
    """Extract the scrape-panel section from the JSX.

    Finds the scrape-panel div and returns its content.
    """
    marker = 'className="scrape-panel"'
    idx = source.find(marker)
    assert idx != -1, (
        f"Could not find 'scrape-panel' in {ONBOARDING_PATH}"
    )

    # Walk JSX tag depth from the scrape-panel div to the closing </div>
    lines = source[idx:].splitlines()

    result_lines: list[str] = []
    div_depth = 1  # we start inside the scrape-panel div
    for line in lines:
        if not result_lines and line.strip() == "":
            continue
        result_lines.append(line)

        # Count net opening/closing divs
        # Opening <div (but not </div or self-closing)
        opens = line.count("<div") - line.count("</div>")
        if opens > 0:
            div_depth += opens
        closes = line.count("</div>")
        if closes > 0:
            div_depth -= closes
            if div_depth <= 0:
                break

    return "\n".join(result_lines)


def _has_scrape_field(source: str, label: str) -> bool:
    """Check if a ScrapeField with the given label exists in the source."""
    # Look for: <ScrapeField label="<label>" ...
    pattern = f'label="{label}"'
    return pattern in source


def _has_confidence_tag_near_field(source: str, field_label: str) -> bool:
    """Check if there is a confidence tag (green or yellow) near a field.

    Looks for the field label followed by a confidence badge in the same
    general section.
    """
    lines = source.splitlines()

    field_line_idx = -1
    for i, line in enumerate(lines):
        if field_label in line:
            field_line_idx = i
            break

    if field_line_idx == -1:
        return False

    # Check nearby lines (within 10 lines after the field label)
    for i in range(field_line_idx, min(field_line_idx + 10, len(lines))):
        line = lines[i]
        if "Confiança alta" in line or "Confiança média" in line:
            return True
        if "confiança alta" in line.lower() or "confiança média" in line.lower():
            return True

    return False


def _has_telefone_auto_fill(source: str) -> bool:
    """Check if handleWebsiteBlur auto-fills telefone from ctx.telefone."""
    handle_body = _extract_handle_website_blur(source)
    return "ctx.telefone" in handle_body or "telefone" in handle_body


def _has_telefone_in_handle_next(source: str) -> bool:
    """Check if handleNext sends telefone in saveDraft."""
    handle_next = _extract_handle_next(source)
    return "telefone" in handle_next


# ── Tests ────────────────────────────────────────────────────────────────────


def test_b4_source_file_exists():
    """Sanity check: the source file must exist and contain key sections."""
    assert ONBOARDING_PATH.exists(), (
        f"Source file not found: {ONBOARDING_PATH}"
    )
    source = _read_onboarding()
    assert "SiteContext" in source, (
        "SiteContext interface not found in OnboardingApp.tsx"
    )
    assert 'className="scrape-grid"' in source, (
        "scrape-grid section not found in OnboardingApp.tsx"
    )


def test_ac5_cnpj_in_scrape_panel():
    """AC#5 — CNPJ must be displayed in the scrape panel when siteContext.cnpj is present.

    RED: The scrape-grid currently shows company_name, vertical, and suggested_agents
    but does NOT render CNPJ as a ScrapeField with label="CNPJ".
    GREEN expected: When siteContext.cnpj exists, the scrape-grid should contain
    a ScrapeField with label="CNPJ" and value formatted with formatCnpj.

    The CNPJ field should appear alongside existing fields in the scrape-grid.
    """
    source = _read_onboarding()
    scrape_grid = _extract_scrape_grid_section(source)

    assert _has_scrape_field(scrape_grid, "CNPJ"), (
        "RED — No ScrapeField with label='CNPJ' found in the scrape-grid section. "
        "Expected: when siteContext.cnpj is present, render a ScrapeField showing "
        "the formatted CNPJ value in the scrape-grid. "
        "The Coder must add 'siteContext.cnpj && ( <ScrapeField label=\"CNPJ\" ... /> )' "
        "to the scrape-grid div, with value formatted via formatCnpj(ctx.cnpj) "
        "and a delay of 250ms."
    )


def test_ac5_cnpj_confidence_tag():
    """AC#5 — CNPJ field should have a confidence tag next to it.

    RED: Currently there is no confidence tag near any CNPJ field in the scrape panel.
    GREEN expected: When siteContext.cnpj is present, next to the CNPJ ScrapeField
    there should be a green 'Confiança alta' tag if confidence >= 0.7,
    or a yellow 'Confiança média' tag if 0.3 <= confidence < 0.7.
    """
    source = _read_onboarding()
    scrape_section = _extract_scrape_panel_section(source)

    # Check for CNPJ field first
    has_cnpj = _has_scrape_field(scrape_section, "CNPJ")
    if not has_cnpj:
        pytest.fail(
            "RED — CNPJ ScrapeField not yet present in scrape panel, "
            "so confidence tag cannot be found either. "
            "AC#5 requires both the CNPJ field display AND confidence tag."
        )

    assert _has_confidence_tag_near_field(scrape_section, "CNPJ"), (
        "RED — No individual confidence tag found near the CNPJ field. "
        "Expected: a green 'Confiança alta' or yellow 'Confiança média' badge "
        "rendered next to the CNPJ value, conditional on siteContext.confidence. "
        "The Coder must add a confidence tag span next to the CNPJ ScrapeField "
        "similar to the existing pattern in the scrape-panel header."
    )


def test_ac6_telefone_in_site_context():
    """AC#6 — SiteContext interface must include a 'telefone' field.

    RED: The current SiteContext interface has company_name, cnpj, vertical,
    confidence, suggested_agents but does NOT have a telefone field.
    GREEN expected: SiteContext should include 'telefone?: string' so that
    the edge function can return telefone data.
    """
    source = _read_onboarding()
    interface = _extract_interface_section(source, "SiteContext")

    assert "telefone" in interface, (
        "RED — The SiteContext interface does NOT yet include a 'telefone' field. "
        "Expected: 'telefone?: string' added to the SiteContext interface. "
        "The Coder must add telefone to the interface so the scrape panel "
        "and auto-fill can consume it from the website-intel edge function."
    )


def test_ac6_telefone_in_scrape_panel():
    """AC#6 — Telefone must be displayed in the scrape panel with confidence tag.

    RED: The scrape-grid currently does NOT render telefone as a ScrapeField.
    GREEN expected: When siteContext.telefone is present, the scrape-grid should
    contain a ScrapeField with label="Telefone" and a confidence tag.
    """
    source = _read_onboarding()
    scrape_grid = _extract_scrape_grid_section(source)

    # Step 1: check if the field exists
    has_telefone_field = _has_scrape_field(scrape_grid, "Telefone")

    assert has_telefone_field, (
        "RED — No ScrapeField with label='Telefone' found in the scrape-grid. "
        "Expected: when siteContext.telefone is present, render a ScrapeField "
        "showing the telefone value. "
        "The Coder must add 'siteContext.telefone && ( <ScrapeField label=\"Telefone\" ... /> )' "
        "to the scrape-grid div, with a delay of 500ms."
    )


def test_ac6_telefone_confidence_tag():
    """AC#6 — Telefone field should have a confidence tag next to it.

    RED: Currently there is no confidence tag near any telefone field in scrape panel.
    GREEN expected: A confidence tag (green/yellow) next to the Telefone ScrapeField.
    """
    source = _read_onboarding()
    scrape_grid = _extract_scrape_grid_section(source)

    has_telefone = _has_scrape_field(scrape_grid, "Telefone")
    if not has_telefone:
        pytest.fail(
            "RED — Telefone ScrapeField not yet present in scrape grid, "
            "so confidence tag cannot be found. "
            "AC#6 requires both telefone display AND confidence tag next to it."
        )

    assert _has_confidence_tag_near_field(scrape_grid, "Telefone"), (
        "RED — No individual confidence tag found near the Telefone field. "
        "Expected: a green 'Confiança alta' or yellow 'Confiança média' badge "
        "next to the Telefone ScrapeField value. "
        "The Coder must add a confidence tag span next to the Telefone ScrapeField."
    )


def test_ac6_telefone_auto_fill():
    """AC#6 — Telefone must be auto-filled when website-intel returns telefone.

    RED: handleWebsiteBlur does NOT currently auto-fill telefone from ctx.telefone.
    GREEN expected: handleWebsiteBlur should contain logic similar to the CNPJ
    auto-fill: 'if (ctx.telefone && !telefone.trim()) setTelefone(ctx.telefone)'.
    """
    source = _read_onboarding()

    assert _has_telefone_auto_fill(source), (
        "RED — handleWebsiteBlur does NOT auto-fill telefone from ctx.telefone. "
        "Expected: after the CNPJ auto-fill block, add similar logic for telefone: "
        "if (ctx.telefone && !telefone.trim()) setTelefone(ctx.telefone). "
        "The Coder must add telefone state, setTelefone, and auto-fill in handleWebsiteBlur."
    )


def test_ac8_step_dados_no_site_context():
    """AC#8 — siteContext without cnpj/telefone must still work as before.

    RED tests that the regression path exists: when siteContext is present
    but without cnpj/telefone, the scrape panel should still show the
    company_name and vertical fields.

    This test should PASS (GREEN) even in RED state because the existing
    company_name and vertical rendering already works.
    """
    source = _read_onboarding()
    scrape_grid = _extract_scrape_grid_section(source)

    # Current grid should still show company_name and vertical
    has_company = "company_name" in scrape_grid
    has_vertical = "vertical" in scrape_grid

    assert has_company, (
        "REGRESSION — company_name field missing from scrape-grid. "
        "Should still be present regardless of new cnpj/telefone fields."
    )
    assert has_vertical, (
        "REGRESSION — vertical field missing from scrape-grid. "
        "Should still be present regardless of new cnpj/telefone fields."
    )


def test_ac8_step_dados_site_context_condition():
    """AC#8 — siteContext must show even when only cnpj/telefone are present.

    The condition for showing the scrape panel currently requires
    'ctx.vertical || ctx.company_name' (line 500). After adding cnpj/telefone,
    it should also show when only cnpj or telefone are present.

    RED: The condition on line 500 only checks vertical || company_name.
    GREEN expected: The condition should also include cnpj and telefone so
    that the scrape panel shows when only those are returned.
    """
    source = _read_onboarding()
    handle_body = _extract_handle_website_blur(source)

    # Check the condition that triggers setSiteContext
    # Currently: if (ctx.vertical || ctx.company_name) setSiteContext(ctx)
    # Should be: if (ctx.vertical || ctx.company_name || ctx.cnpj || ctx.telefone) setSiteContext(ctx)
    set_site_context_line = None
    for line in handle_body.splitlines():
        if "setSiteContext" in line:
            set_site_context_line = line
            break

    assert set_site_context_line is not None, (
        "setSiteContext call not found in handleWebsiteBlur"
    )

    has_cnpj_in_condition = "ctx.cnpj" in set_site_context_line
    has_telefone_in_condition = (
        "ctx.telefone" in set_site_context_line
        or "telefone" in set_site_context_line
    )

    assert has_cnpj_in_condition and has_telefone_in_condition, (
        "RED — The condition to show the scrape panel does not include cnpj/telefone. "
        "Expected: 'if (ctx.vertical || ctx.company_name || ctx.cnpj || ctx.telefone) setSiteContext(ctx)' "
        "so the panel shows even when only CNPJ/telefone are returned by the edge function. "
        f"Current condition line: {set_site_context_line}"
    )


def test_ac8_handle_next_no_primary_focus():
    """AC#8 — handleNext must work without primaryFocus.

    Regression: after removing primaryFocus from StepInfo, handleNext should
    NOT reference primaryFocus in its saveDraft call. This ensures the
    fluxo continues working.

    This test should PASS (GREEN) because primaryFocus was already removed
    from StepInfo in a previous GREEN commit (a3c1daaa).
    """
    source = _read_onboarding()
    step_info = _extract_step_info_section(source)

    assert "primaryFocus" not in step_info, (
        "REGRESSION — primaryFocus is still referenced in StepInfo. "
        "It should have been removed when PRIMARY_FOCUS was taken out of StepInfo."
    )
