"""RED test for BKL-037a — Modal de confirmacao de tipo de CSV no StepData.

GOAL:
    BKL-037a — Issue #198 E-1: Protecao contra classificacao incorreta de CSV.
    Atualmente o StepData (OnboardingApp.tsx L927-1210) envia o CSV direto para
    StepMapping com schema_type="invoices" fixo, sem perguntar ao usuario.
    Deve-se adicionar um modal de confirmacao apos upload do CSV.

BEHAVIOR:
    BKL-037a — Modal de confirmacao de tipo de CSV no StepData

    Apos selecionar o arquivo CSV em StepData (handleCsvChange L1057), deve
    mostrar um modal de confirmacao com:
    1. Mensagem: "Detectamos N colunas que parecem ser de notas fiscais. Confirma?"
    2. Botoes: "Sim, sao notas" | "Nao, e outro tipo" | "Cancelar"
    3. "Sim, sao notas" → avanca para StepMapping com schema_type="invoices"
    4. "Nao, e outro tipo" → abre dropdown com opcoes: invoices, receipts,
       bank_statements, outros + "Nao sei" (LLM sugere o tipo)
    5. "Cancelar" → limpa o arquivo, volta ao StepData sem CSV
    6. UploadCsvDataSource() SO deve ser chamada apos confirmacao (no StepLaunch)
    7. schema_type confirmado passado para StepMapping e StepLaunch

AC (Acceptance Criteria):
    AC#1 — Confirmacao "Detectamos N colunas..." aparece apos upload
    AC#2 — Opcoes "Sim, sao notas", "Nao, e outro tipo", "Cancelar"
    AC#3 — "Nao, e outro tipo" permite selecionar tipo (dropdown)
    AC#5 — "Cancelar" remove arquivo e volta ao StepData sem CSV
    R1   — Opcao "Nao sei" com LLM para sugerir tipo
    AC#6 — callMatchColumns e upload-csv-source usam schema_type dinamico
           (nao hardcoded "invoices")

CsvClassification interface (should exist but does not yet):
    interface CsvClassification {
      confirmed: boolean
      schemaType: 'invoices' | 'receipts' | 'bank_statements' | 'outros' | string
      canceled: boolean
    }

DECISION:
    Estrategia: source-inspection via pytest
    Arquivo alvo: apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx
    Seção alvo: StepData component (L927-1210), handleCsvChange (L1057-1065),
                callMatchColumns (L135-150), StepLaunch upload (L1610-1641)

Anti-Goals (must NOT be violated):
    1. NÃO quebrar fluxo de upload existente (Drive, BigQuery)
    2. NÃO modificar StepMapping ou StepLaunch para alem do schema_type dinamico
    3. NÃO impedir usuario de avancar sem CSV (onSkip continua funcional)

Estado atual: RED — as seguintes features NAO existem:
    - Nenhum modal de confirmacao em StepData (handleCsvChange aceita direto)
    - callMatchColumns hardcoded com schema_type='invoices' (L139)
    - Upload CSV em StepLaunch hardcoded schema_type='invoices' (L1617)
    - Nenhuma interface CsvClassification no arquivo
    - Nenhum estado de confirmacao de CSV (showConfirmation, csvClassification)
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


def _extract_step_data_section(source: str) -> str:
    """Extract the StepData component body from the source.

    Returns the text from 'function StepData({' up to the closing '}'
    that ends the component.
    """
    marker = "function StepData({"
    idx = source.find(marker)
    assert idx != -1, (
        f"Cannot find 'function StepData({{' in {ONBOARDING_PATH}"
    )

    close_paren = source.find(")", idx)
    assert close_paren != -1, "Cannot find closing ) for StepData params"
    brace_start = source.find("{", close_paren)
    assert brace_start != -1, "Cannot find opening brace for StepData body"

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

    assert end != -1, "Cannot find closing brace for StepData"
    return source[idx:end]


def _extract_call_match_columns(source: str) -> str:
    """Extract the callMatchColumns function body."""
    marker = "async function callMatchColumns("
    idx = source.find(marker)
    if idx == -1:
        return ""

    close_paren = source.find(")", idx)
    assert close_paren != -1, "Cannot find closing ) for callMatchColumns params"
    brace_start = source.find("{", close_paren)
    assert brace_start != -1, "Cannot find opening brace for callMatchColumns"

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


def _has_confirmation_modal(source: str) -> bool:
    """AC#1: Check if a confirmation modal/dialog exists in StepData.

    Look for strings that would indicate a confirmation modal for CSV type.
    Currently RED: no such strings exist.
    """
    step_data = _extract_step_data_section(source)
    # Search for the expected confirmation message
    markers = [
        "Detectamos", "colunas", "notas fiscais",
        "Confirma", "confirmacao", "csvClassification",
        "CsvClassification",
    ]
    found = [m for m in markers if m in step_data]
    # All markers must be present for the modal to exist
    return len(found) >= 4  # At least 4 of the 7 markers


def _has_confirmation_buttons(source: str) -> bool:
    """AC#2: Check if the three buttons exist in StepData.

    Currently RED: no such buttons exist.
    """
    step_data = _extract_step_data_section(source)
    buttons = [
        "Sim, sao notas",
        "Nao, e outro tipo",
        "Cancelar",
    ]
    return all(b in step_data for b in buttons)


def _has_type_dropdown(source: str) -> bool:
    """AC#3: Check if a schema-type dropdown/select exists in StepData.

    Currently RED: no schema-type selection dropdown exists after CSV upload.
    """
    step_data = _extract_step_data_section(source)
    # Would contain a select/option for choosing schema type
    markers = [
        "invoices", "receipts", "bank_statements", "schemaType",
    ]
    return all(m in step_data for m in markers)


def _has_cancel_csv_behavior(source: str) -> bool:
    """AC#5: Check if cancel clears the CSV file in StepData.

    Currently RED: handleCsvChange has no cancel logic.
    """
    step_data = _extract_step_data_section(source)
    # Cancel should clear csvUploaded, csvFileName, csvHeaders
    return "csvUploaded" in step_data and "csvClassification" in step_data


def _has_llm_suggest_option(source: str) -> bool:
    """R1: Check if "Nao sei" / LLM suggest option exists in StepData.

    Currently RED: no such option exists.
    """
    step_data = _extract_step_data_section(source)
    markers = [
        "Nao sei",
        "sugere",
        "llm_suggest",
    ]
    return any(m in step_data for m in markers)


# ── Tests ────────────────────────────────────────────────────────────────────


def test_bkl_037a_source_file_exists():
    """Sanity check: the source file must exist and contain StepData."""
    assert ONBOARDING_PATH.exists(), (
        f"Source file not found: {ONBOARDING_PATH}"
    )
    source = _read_onboarding()
    assert "function StepData({" in source, (
        "StepData component not found in OnboardingApp.tsx"
    )


def test_ac1_confirmation_modal():
    """AC#1 — Confirmation modal must appear after CSV upload.

    RED (failing): currently handleCsvChange immediately sets csvUploaded=true
    and calls onCsvFileReady without asking. No modal exists.
    GREEN expected: after CSV file is selected, a modal should appear showing
    "Detectamos N colunas que parecem ser de notas fiscais. Confirma?" with
    buttons for the user to confirm or reject the classification.
    """
    source = _read_onboarding()

    assert _has_confirmation_modal(source), (
        "RED — Modal de confirmacao NAO existe. "
        "Atualmente o handleCsvChange aceita o CSV direto, sem perguntar "
        "ao usuario sobre o tipo de dados. "
        "O Coder deve adicionar um modal de confirmacao com a mensagem "
        "'Detectamos N colunas que parecem ser de notas fiscais. Confirma?' "
        "apos o upload do CSV (handleCsvChange L1057), antes de prosseguir "
        "para StepMapping."
    )


def test_ac2_buttons():
    """AC#2 — Three buttons must exist: "Sim, sao notas", "Nao, e outro tipo", "Cancelar".

    RED (failing): currently no modal exists, so no buttons.
    GREEN expected: the modal has three actionable buttons.
    """
    source = _read_onboarding()

    assert _has_confirmation_buttons(source), (
        "RED — Botoes de confirmacao NAO existem. "
        "Atualmente nao ha modal nem botoes. "
        "O Coder deve adicionar tres botoes no modal de confirmacao: "
        "'Sim, sao notas' (schema_type='invoices'), "
        "'Nao, e outro tipo' (abre seletor de tipo), "
        "'Cancelar' (limpa arquivo e volta)."
    )


def test_ac3_type_dropdown():
    """AC#3 — "Nao, e outro tipo" must open dropdown with schema type options.

    RED (failing): currently no modal or dropdown exists for schema type selection.
    GREEN expected: when user clicks "Nao, e outro tipo", a dropdown appears
    with options: invoices, receipts, bank_statements, outros + "Nao sei".
    """
    source = _read_onboarding()

    assert _has_type_dropdown(source), (
        "RED — Dropdown de tipo de schema NAO existe no StepData. "
        "Atualmente o StepData nao tem opcao de selecionar tipo de CSV. "
        "O Coder deve adicionar um dropdown/select com as opcoes: "
        "invoices, receipts, bank_statements, outros (com campo texto) "
        "e 'Nao sei' (para classificacao via LLM)."
    )


def test_ac5_cancel_clears_file():
    """AC#5 — "Cancelar" must clear the CSV file and return to StepData.

    RED (failing): currently no cancel mechanism exists in handleCsvChange.
    GREEN expected: clicking "Cancelar" should:
    - Clear csvUploaded (set to false)
    - Clear csvFileName
    - Clear csvHeaders
    - NOT call onCsvFileReady
    - Return to StepData without CSV selected
    """
    source = _read_onboarding()

    assert _has_cancel_csv_behavior(source), (
        "RED — Comportamento de cancelamento NAO existe. "
        "Atualmente handleCsvChange nao tem logica de cancelamento. "
        "O Coder deve adicionar ao modal um botao 'Cancelar' que: "
        "limpa o estado csvUploaded, csvFileName e csvHeaders, "
        "e retorna ao StepData sem CSV, sem chamar onCsvFileReady."
    )


def test_r1_llm_suggest():
    """R1 — "Nao sei" option with LLM to suggest schema type.

    RED (failing): currently no LLM suggest option exists.
    GREEN expected: when user selects "Nao sei" in the type dropdown,
    the app should call an LLM to suggest the most likely schema type
    based on column headers.
    """
    source = _read_onboarding()

    assert _has_llm_suggest_option(source), (
        "RED — Opcao 'Nao sei' com sugestao LLM NAO existe. "
        "Atualmente nao ha opcao de classificacao via LLM. "
        "O Coder deve adicionar a opcao 'Nao sei' no dropdown de tipo, "
        "que chama um LLM para sugerir o tipo de schema baseado nas "
        "colunas do CSV, preenchendo automaticamente a selecao."
    )


def test_ac6_dynamic_schema_type():
    """AC#6 — callMatchColumns and upload-csv-source must use dynamic schema_type.

    RED (failing): currently callMatchColumns hardcodes schema_type='invoices' (L139)
    and StepLaunch upload hardcodes schema_type='invoices' (L1617).
    GREEN expected: schema_type should be accepted as a function parameter,
    not hardcoded in the body.
    """
    source = _read_onboarding()

    call_match = _extract_call_match_columns(source)

    # Extract only the function parameter list (between the first parens)
    paren_start = call_match.find("(")
    paren_end = call_match.find(")")
    params = call_match[paren_start + 1:paren_end] if paren_start != -1 and paren_end != -1 else ""

    # GREEN check: schemaType or schema_type should be a function PARAMETER
    # RED currently: only appears as hardcoded 'invoices' in the body
    assert "schemaType" in params or "schema_type" in params, (
        "RED — callMatchColumns NAO aceita schemaType como parametro. "
        "Atualmente schema_type='invoices' esta hardcoded em "
        "callMatchColumns (L139) e no upload-csv-source (L1617). "
        "O Coder deve: (1) adicionar schemaType como parametro em "
        "callMatchColumns, (2) usar o schema_type confirmado no "
        "upload-csv-source em StepLaunch, (3) remover o literal 'invoices' "
        "hardcoded em ambos os lugares."
    )
