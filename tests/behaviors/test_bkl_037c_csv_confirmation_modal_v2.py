"""RED test for Behavior 1 — Modal de confirmacao de tipo de CSV no onboarding.

GOAL:
    BLU modal de confirmacao de tipo de CSV no onboarding. Quando o usuario faz
    upload de CSV/XLSX (ou conecta Google Drive) no StepData, o sistema deve
    exibir um modal de confirmacao com o tipo de schema detectado automaticamente,
    permitindo que o usuario confirme ou altere.

BEHAVIOR:
    Behavior 1 — Modal de confirmacao de tipo de CSV no onboarding.

    O usuario faz upload de CSV/XLSX (ou conecta Google Drive) no StepData do
    onboarding. Antes de prosseguir, o sistema deve exibir um modal de confirmacao
    com o tipo de schema detectado automaticamente, permitindo que o usuario
    confirme ou altere.

AC (Acceptance Criteria):
    AC#1 — Auto-detecao de schema type
        Ao receber os headers do CSV, o frontend chama match-columns com cada
        um dos 4 schema types (invoices, fato_transacoes, dim_clientes,
        dim_inventory) e escolhe o tipo com maior confidence media. Se empatar,
        invoices eh o default.

    AC#2 — Modal de confirmacao
        Apos auto-detectar, um modal eh exibido com:
        - Titulo: "Qual o tipo de dados desta planilha?"
        - Descricao do tipo detectado (ex: "Notas Fiscais / Faturamento",
          "Transacoes Financeiras", "Clientes", "Estoque / Produtos")
        - Opcao de selecionar outro tipo via radio buttons
        - Botoes "Confirmar" e "Alterar tipo"

    AC#3 — Sheet name heuristic preserved
        Se o arquivo for XLSX multi-sheet, a heuristica existente de
        scoreSheetName() continua valendo como parte da auto-detecao.
        O sheet mais provavel de ser o principal eh usado para extrair headers.

    AC#4 — Schema type persiste no fluxo
        O schema type selecionado pelo usuario (ou o auto-detectado) eh passado
        adiante no fluxo: callMatchColumns(schemaType) e upload-csv-source /
        upload-drive-source recebem o schemaType correto, nao o 'invoices'
        hardcoded.

    AC#5 — Modal nao bloqueia fluxo sem CSV
        Se o usuario nao fez upload de CSV (apenas sistemas), o modal nao
        aparece — o fluxo segue normal com o default 'invoices' para BigQuery.

Anti-Goals (must NOT be violated):
    1. Nao quebrar handleCsvChange existente (csvFileRef, setCsvFileName,
       parseSpreadsheetHeaders)
    2. Nao remover scoreSheetName() ou parseSpreadsheetHeaders()
    3. Nao quebrar callMatchColumns — sua assinatura ja aceita schemaType?
    4. Nao remover fallback 'invoices'
    5. Nao quebrar fluxo Drive/BigQuery

Estado atual: RED. O teste abaixo verifica features que NAO existem no codigo
atual (ou existem de forma diferente). Cada teste FALHA porque o comportamento
DESEJADO ainda nao foi implementado.

Diferencas entre o codigo atual e o desejado:
    - Codigo atual tem modal com "Detectamos N colunas..." (diferente de
      "Qual o tipo de dados desta planilha?")
    - Modal atual tem botoes "Sim, sao notas" / "Nao, e outro tipo" / "Cancelar"
      (diferente de "Confirmar" / "Alterar tipo")
    - Modal atual usa dropdown, nao radio buttons
    - Nao ha logica de auto-detecao que chama match-columns para todos os 4 tipos
    - upload-drive-source ainda hardcoded 'invoices'
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


# ── Check helpers (assert DESIRED behavior — all return False currently) ────


def _has_auto_detection_4_types(source: str) -> bool:
    """AC#1: Check if StepData auto-detects schema type across 4 types.

    Looks for logic that calls match-columns for invoices, fato_transacoes,
    dim_clientes, dim_inventory and picks the best confidence.
    """
    step_data = _extract_step_data_section(source)
    markers = [
        "fato_transacoes",
        "dim_clientes",
        "dim_inventory",
        "auto_detect",
        "confidence",
        "match-columns",
    ]
    return all(m in step_data for m in markers)


def _has_modal_with_correct_title(source: str) -> bool:
    """AC#2: Check if modal has title 'Qual o tipo de dados desta planilha?'."""
    step_data = _extract_step_data_section(source)
    return "Qual o tipo de dados desta planilha?" in step_data


def _has_schema_type_descriptions(source: str) -> bool:
    """AC#2: Check if modal has schema type descriptions."""
    step_data = _extract_step_data_section(source)
    descriptions = [
        "Notas Fiscais / Faturamento",
        "Transacoes Financeiras",
        "Clientes",
        "Estoque / Produtos",
    ]
    return any(d in step_data for d in descriptions)


def _has_radio_buttons(source: str) -> bool:
    """AC#2: Check if modal uses radio buttons for type selection."""
    step_data = _extract_step_data_section(source)
    return 'type="radio"' in step_data or "radio" in step_data.lower()


def _has_confirm_and_alterar_buttons(source: str) -> bool:
    """AC#2: Check if modal has 'Confirmar' and 'Alterar tipo' buttons."""
    step_data = _extract_step_data_section(source)
    return "Confirmar" in step_data and "Alterar tipo" in step_data


def _has_score_sheet_name_preserved(source: str) -> bool:
    """AC#3: Check that scoreSheetName() still exists in the file."""
    return "function scoreSheetName(" in source


def _has_schema_type_in_upload_drive_source(source: str) -> bool:
    """AC#4: Check that upload-drive-source uses variable schema_type.

    Currently line 1755 hardcodes 'invoices'. After fix it should use a
    variable (e.g., csvSchemaType).
    """
    # Find upload-drive-source invocation
    idx = source.find("upload-drive-source")
    if idx == -1:
        return False
    # Look at the surrounding body (within function scope)
    snippet = source[idx:].split("\n")[:30]
    snippet_text = "\n".join(snippet)
    # Check if schema_type is a variable (not hardcoded literal)
    import re
    append_match = re.search(
        r"""schema_type['"]\s*[:,=]\s*([^,;\n)}]+)""",
        snippet_text,
    )
    if not append_match:
        return False
    value = append_match.group(1).strip()
    # DESIRED: value is NOT a string literal
    return not bool(re.match(r"""^['"`][^'"`]+['"`]$""", value))


def _has_no_modal_without_csv(source: str) -> bool:
    """AC#5: Check that modal logic is gated by CSV upload.

    The modal should only show when a CSV file has been uploaded.
    Check that showClassificationModal is gated on csvUploaded or similar.
    """
    step_data = _extract_step_data_section(source)
    # The modal should be guarded by csvUploaded or csvHeaders length
    guards = [
        "csvUploaded && showClassificationModal",
        "csvHeaders.length > 0 && showClassificationModal",
        "csvHeaders?.length > 0 &&",
    ]
    return any(g in step_data for g in guards)


# ── Tests ────────────────────────────────────────────────────────────────────


def test_bkl_037c_source_file_exists():
    """Sanity check: the source file must exist and contain StepData."""
    assert ONBOARDING_PATH.exists(), (
        f"Source file not found: {ONBOARDING_PATH}"
    )
    source = _read_onboarding()
    assert "function StepData({" in source, (
        "StepData component not found in OnboardingApp.tsx"
    )


def test_bkl_037c_ac1_auto_detection_4_types():
    """AC#1 — Auto-detection across 4 schema types.

    RED (failing): currently there is NO logic to auto-detect schema type by
    calling match-columns with 4 types. The current modal assumes 'invoices'.
    GREEN expected: handleCsvChange (or a new handler) should call match-columns
    with all 4 types (invoices, fato_transacoes, dim_clientes, dim_inventory),
    pick the one with highest average confidence, and use it as default.
    """
    source = _read_onboarding()

    assert _has_auto_detection_4_types(source), (
        "RED — Auto-detecao com 4 tipos NAO existe. "
        "O codigo atual nao chama match-columns com todos os 4 schema types "
        "(invoices, fato_transacoes, dim_clientes, dim_inventory) para "
        "auto-detectar o tipo. "
        "O Coder deve adicionar logica que: "
        "1. Chama match-columns com cada um dos 4 tipos "
        "2. Compara confidence media de cada um "
        "3. Escolhe o maior (invoices como default em caso de empate) "
        "4. Preenche o modal com o tipo detectado"
    )


def test_bkl_037c_ac2_modal_title():
    """AC#2a — Modal must have title 'Qual o tipo de dados desta planilha?'.

    RED (failing): current modal has different text.
    GREEN expected: the modal should have the exact title string.
    """
    source = _read_onboarding()

    assert _has_modal_with_correct_title(source), (
        "RED — Titulo do modal NAO esta correto. "
        "O codigo atual tem um modal com texto diferente. "
        "O Coder deve alterar o modal para exibir o titulo "
        "'Qual o tipo de dados desta planilha?' "
        "com a descricao do tipo detectado."
    )


def test_bkl_037c_ac2_schema_type_descriptions():
    """AC#2b — Modal must show schema type descriptions.

    RED (failing): current modal has no descriptions for schema types.
    GREEN expected: descriptions like "Notas Fiscais / Faturamento",
    "Transacoes Financeiras", "Clientes", "Estoque / Produtos".
    """
    source = _read_onboarding()

    assert _has_schema_type_descriptions(source), (
        "RED — Descricoes dos tipos de schema NAO existem no modal. "
        "O Coder deve adicionar descricoes amigaveis para cada schema type: "
        "'Notas Fiscais / Faturamento' (invoices), "
        "'Transacoes Financeiras' (fato_transacoes), "
        "'Clientes' (dim_clientes), "
        "'Estoque / Produtos' (dim_inventory)."
    )


def test_bkl_037c_ac2_radio_buttons():
    """AC#2c — Modal must use radio buttons for type selection.

    RED (failing): current modal uses a dropdown (<select>), not radio buttons.
    GREEN expected: the type selection should use radio buttons
    (<input type="radio">).
    """
    source = _read_onboarding()

    assert _has_radio_buttons(source), (
        "RED — Modal NAO usa radio buttons para selecao de tipo. "
        "O codigo atual usa um dropdown <select>. "
        "O Coder deve substituir o dropdown por radio buttons "
        "(<input type='radio'>) para cada tipo de schema, "
        "com o tipo detectado pre-selecionado."
    )


def test_bkl_037c_ac2_confirm_and_alterar_buttons():
    """AC#2d — Modal must have 'Confirmar' and 'Alterar tipo' buttons.

    RED (failing): current modal has different buttons.
    GREEN expected: "Confirmar" (confirms detected type) and
    "Alterar tipo" (opens radio button selection if not already shown).
    """
    source = _read_onboarding()

    assert _has_confirm_and_alterar_buttons(source), (
        "RED — Modal NAO tem botoes 'Confirmar' e 'Alterar tipo'. "
        "O codigo atual tem 'Sim, sao notas', 'Nao, e outro tipo', 'Cancelar'. "
        "O Coder deve substituir por: "
        "'Confirmar' (confirma o tipo detectado) e "
        "'Alterar tipo' (permite selecionar outro tipo via radio buttons)."
    )


def test_bkl_037c_ac3_sheet_name_heuristic_preserved():
    """AC#3 — scoreSheetName() heuristic must be preserved.

    GREEN already: scoreSheetName() already exists and is used in
    parseSpreadsheetHeaders. This test should PASS immediately,
    confirming the heuristic is NOT removed during refactoring.
    """
    source = _read_onboarding()

    assert _has_score_sheet_name_preserved(source), (
        "RED — scoreSheetName() NAO existe mais! "
        "A funcao scoreSheetName() foi removida. "
        "O Coder deve preservar scoreSheetName() para a heuristica de "
        "selecao de sheet principal em arquivos XLSX multi-sheet."
    )


def test_bkl_037c_ac4_upload_drive_source_variable_schema_type():
    """AC#4 — upload-drive-source must use variable schema_type.

    RED (failing): currently line 1755 hardcodes 'invoices'.
    GREEN expected: should use a variable like csvSchemaType || 'invoices'.
    """
    source = _read_onboarding()

    assert _has_schema_type_in_upload_drive_source(source), (
        "RED — upload-drive-source ainda usa 'invoices' hardcoded. "
        "Linha 1755: body: { ..., schema_type: 'invoices' }. "
        "O Coder deve substituir 'invoices' por uma variavel, ex.: "
        "schema_type: csvSchemaType || 'invoices'."
    )


def test_bkl_037c_ac5_modal_gated_by_csv():
    """AC#5 — Modal must not appear without CSV upload.

    RED (failing): current modal logic may not be properly gated.
    GREEN expected: showClassificationModal should only be true when
    a CSV/XLSX file has been uploaded (not for Drive-only or system-only flows).
    """
    source = _read_onboarding()

    assert _has_no_modal_without_csv(source), (
        "RED — Modal de CSV NAO esta protegido contra exibicao sem CSV. "
        "O modal de confirmacao de tipo de CSV so deve aparecer quando "
        "o usuario fez upload de um arquivo CSV/XLSX. "
        "Para fluxos apenas com sistemas (BigQuery) ou Google Drive, "
        "o modal nao deve aparecer e o fluxo segue com 'invoices' como default. "
        "O Coder deve garantir que showClassificationModal seja false "
        "quando nao ha CSV."
    )
