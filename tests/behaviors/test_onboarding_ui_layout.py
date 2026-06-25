"""RED test for UI Layout — website ao lado do nome, campo "Foco" removido, reordenar campos.

GOAL:
    Ajustar o StepInfo (Step Empresa) no OnboardingApp.tsx para:
    website ao lado do nome, nova ordem de campos, remover "Foco",
    tags verde/amarela por confidence, CNPJ e telefone auto-preenchidos.

BEHAVIOR:
    B2 — UI layout: website ao lado do nome, remover foco, reordenar

    O StepInfo em apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx
    deve reorganizar os campos no formulário de dados da empresa para:

    1. Website na mesma linha do nome (row2: nome + website)
    2. Nova ordem: nome + website → empresa → CNPJ → setor → porte
    3. Campo "Foco atual do negócio" (primaryFocus) removido do Step Empresa

AC (Acceptance Criteria):
    AC#1 — Website field moved to same line as nome (row2: nome + website)
    AC#2 — New field order: nome+website → empresa → CNPJ → setor → porte
    AC#3 — "Foco atual do negócio" (primaryFocus) removed from Step Empresa

DECISION:
    Estratégia: source-inspection via pytest
    Arquivo alvo: apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx
    Seção alvo: StepInfo component (~linha 456-695)

Anti-Goals (must NOT be violated):
    1. NÃO quebrar o Step Dados (próximo step)
    2. NÃO quebrar a lógica de auto-preenchimento existente
    3. NÃO remover onChange handlers (campos permanecem editáveis)

Estado atual: RED — as seguintes features NÃO existem:
    - Website está em field próprio (L575-583), NÃO no row2 com nome
    - row2 tem nome + empresa (L551-560), deveria ser nome + website
    - "Foco atual do negócio" (primaryFocus) AINDA presente no scrape-panel (L648-658)
    - Order atual: row2 → CNPJ → website → scrape-panel → setor → porte
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

    # Find the enclosing braces for the function — there are two levels:
    # the function body { } and potentially JSX inside. We need the outer
    # function body, which is the first { after the destructuring params.
    # The function signature is: function StepInfo({...props}) {
    # So we find the first { after the closing ) of the destructured params.
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


def _row2_contains_website(source: str) -> bool:
    """AC#1: Check if the row2 div contains both nome AND website fields.

    The row2 div should have two child field divs: one for nome and one for
    website. Currently (RED) it has nome + empresa, not website.
    """
    # Find the row2 div content
    row2_marker = 'className="row2"'
    idx = source.find(row2_marker)
    if idx == -1:
        return False

    # Find the closing of the row2 div — we need to find the matching </div>
    # Walk tag depth
    tag_depth = 1
    search_start = source.find(">", idx) + 1
    for i in range(search_start, min(search_start + 400, len(source))):
        if source[i:i+4] == "<div" and not source[i:i+5] == "</div":
            tag_depth += 1
        elif source[i:i+6] == "</div>":
            tag_depth -= 1
            if tag_depth == 0:
                row2_content = source[search_start:i]
                break
    else:
        row2_content = source[search_start:search_start + 400]

    # Check: row2 should have BOTH nome AND website-related content
    has_nome = "nome" in row2_content.lower()
    has_website = "website" in row2_content.lower()
    return has_nome and has_website


def _get_field_order(source: str) -> list[str]:
    """AC#2: Extract the field/label order from the JSX structure.

    Returns a list of field label texts in order, as they appear in the
    rendered component JSX, excluding the scrape-panel section.
    """
    step_info = _extract_step_info_section(source)

    # Find field labels by looking for <label> tags
    labels: list[str] = []
    label_marker = "<label"
    search_pos = 0

    while True:
        label_idx = step_info.find(label_marker, search_pos)
        if label_idx == -1:
            break

        # Find the end of the label content (before the next tag)
        content_start = step_info.find(">", label_idx) + 1
        content_end = step_info.find("</label>", content_start)
        if content_end == -1:
            break

        label_content = step_info[content_start:content_end].strip()
        # Clean up any JSX expressions inside (like {' '})
        if "{" in label_content:
            label_content = label_content.split("{")[0].strip()

        if label_content and len(label_content) > 2:
            labels.append(label_content)

        search_pos = content_end + 7  # len("</label>")

    return labels


def _has_primary_focus_in_step_info(source: str) -> bool:
    """AC#3: Check if primaryFocus / 'Foco atual' is still present in StepInfo.

    RED: the string 'primaryFocus' and 'Foco atual do negócio' should BOTH be
    present in the file currently. GREEN: they should NOT appear in StepInfo.
    """
    step_info = _extract_step_info_section(source)
    has_primary_focus_var = "primaryFocus" in step_info
    has_foco_label = "Foco atual do negócio" in step_info
    return has_primary_focus_var or has_foco_label


# ── Tests ────────────────────────────────────────────────────────────────────


def test_b2_source_file_exists():
    """Sanity check: the source file must exist and contain StepInfo."""
    assert ONBOARDING_PATH.exists(), (
        f"Source file not found: {ONBOARDING_PATH}"
    )
    source = _read_onboarding()
    assert "function StepInfo({" in source, (
        "StepInfo component not found in OnboardingApp.tsx"
    )


def test_ac1_website_in_row2():
    """AC#1 — Website must be on the same line as nome (row2).

    RED: currently the row2 div has nome + empresa. Website is on its own
    line as a separate <div className="field">.
    GREEN expected: row2 should contain both nome input AND website input
    side by side.
    """
    source = _read_onboarding()

    assert _row2_contains_website(source), (
        "RED — Website não está no row2 com o nome. "
        "Atualmente o row2 contém nome + empresa, mas o website está em "
        "um field próprio separado. "
        "O Coder deve mover o campo website para dentro do row2, ao lado "
        "do campo nome, mantendo o placeholder de website e o onBlur "
        "handleWebsiteBlur intactos."
    )


def test_ac2_field_order():
    """AC#2 — Fields must appear in correct order.

    RED: current order is row2(nome+empresa) → CNPJ → website → scrape-panel
    → setor → porte.
    GREEN expected order: row2(nome+website) → empresa → CNPJ → setor → porte.

    We check by looking at the label texts in order within StepInfo.
    The expected sequence after adjustments:
    - 'Seu nome' (nome field in row2)
    - 'Website' (or 'Website ' with JSX space — website field in row2)
    - 'Nome da empresa *' (empresa field)
    - 'CPF / CNPJ da empresa' (CNPJ field)
    - 'Setor *' (setor field with detection badge)
    - 'Tamanho da equipe *' (porte field)
    """
    source = _read_onboarding()
    labels = _get_field_order(source)

    # Find key fields
    try:
        nome_idx = next(i for i, l in enumerate(labels) if "Seu nome" in l)
        empresa_idx = next(i for i, l in enumerate(labels) if "Nome da empresa" in l and "*" in l)
        cnpj_idx = next(i for i, l in enumerate(labels) if "CPF" in l or "CNPJ" in l)
        setor_idx = next(i for i, l in enumerate(labels) if "Setor" in l and "*" in l)
        porte_idx = next(i for i, l in enumerate(labels) if ("Tamanho" in l or "equipe" in l or "porte" in l) and "*" in l)
    except StopIteration as e:
        pytest.fail(f"RED — Could not find all required fields in StepInfo: {e}")

    # Check relative order: nome → empresa → CNPJ → setor → porte
    assert nome_idx < empresa_idx, (
        f"RED — 'nome' (idx={nome_idx}) deve vir antes de 'empresa' (idx={empresa_idx}). "
        f"Order atual: {labels}"
    )
    assert empresa_idx < cnpj_idx, (
        f"RED — 'empresa' (idx={empresa_idx}) deve vir antes de 'CNPJ' (idx={cnpj_idx}). "
        f"Order atual: {labels}"
    )
    assert cnpj_idx < setor_idx, (
        f"RED — 'CNPJ' (idx={cnpj_idx}) deve vir antes de 'Setor' (idx={setor_idx}). "
        f"Order atual: {labels}"
    )
    assert setor_idx < porte_idx, (
        f"RED — 'Setor' (idx={setor_idx}) deve vir antes de 'porte' (idx={porte_idx}). "
        f"Order atual: {labels}"
    )


def test_ac3_primary_focus_removed():
    """AC#3 — 'Foco atual do negócio' (primaryFocus) must be removed.

    RED: currently 'primaryFocus' variable and 'Foco atual do negócio' label
    are present in the StepInfo component (scrape-panel section, L648-658).
    GREEN expected: these strings should NOT appear anywhere in StepInfo.
    The variable primaryFocus, the state setPrimaryFocus, and the JSX with
    "Foco atual do negócio" should all be removed from Step Empresa.
    """
    source = _read_onboarding()
    step_info = _extract_step_info_section(source)

    assert "Foco atual do negócio" not in step_info, (
        "RED — O label 'Foco atual do negócio' ainda está presente no StepInfo. "
        "Deve ser removido do Step Empresa conforme AC#3. "
        "O Coder deve remover a seção de radio-pills PRIMARY_FOCUS do "
        "scrape-panel no StepInfo (as perguntas contextuais devem conter "
        "apenas 'Principal produto ou serviço')."
    )

    assert "primaryFocus" not in step_info, (
        "RED — A variável 'primaryFocus' ainda está presente no StepInfo. "
        "Deve ser removida junto com seu estado e onChange handlers."
    )
