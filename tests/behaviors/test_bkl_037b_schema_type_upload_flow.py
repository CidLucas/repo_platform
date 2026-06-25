"""RED test for behavior BKL-037b — Schema_type dinâmico no upload flow.

GOAL:
    Issue #198 — E-1: Proteção contra classificação incorreta de CSV.
    Após confirmação do tipo de CSV no StepData (Behavior 1), o schema_type
    confirmado deve ser passado para:
    1. knowledgeBaseService.uploadCsvDataSource() — aceitar schemaType opcional
    2. StepLaunch — usar schema_type do usuário em vez de hardcoded 'invoices'

BEHAVIOR:
    BKL-037b — Schema_type dinâmico no upload flow.

    ``apps/blu_v3/src/services/knowledgeBaseService.ts`` defines
    ``uploadCsvDataSource()`` that currently:
        - Accepts only ``file: File, clientId: string`` (NO optional schemaType)
        - Hardcodes ``form.append('schema_type', 'invoices')`` at line 271

    ``apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx`` renders
    ``StepLaunch`` that currently:
        - Hardcodes ``form.append('schema_type', 'invoices')`` at line 1617

    After the fix:
        - ``uploadCsvDataSource()`` must accept an optional ``schemaType``
          parameter that defaults to ``'invoices'`` when omitted.
        - ``StepLaunch`` must receive and use a user-confirmed ``csvSchemaType``
          value instead of hardcoded ``'invoices'``.
        - The parent ``OnboardingApp`` must declare and pass ``csvSchemaType``
          state to ``StepLaunch``.

AC (Acceptance Criteria):
    AC4 — uploadCsvDataSource() recebe schema_type variável
    AC6 — Só chama EF após confirmação com tipo correto

Anti-Goals (must NOT be violated):
    1. NÃO alterar a assinatura do ``callMatchColumns()`` helper — seu
       ``schema_type: 'invoices'`` interno é independente do upload flow.
    2. NÃO introduzir dependências novas — usar TypeScript nativo.
    3. NÃO alterar a interface de retorno de ``uploadCsvDataSource()``.
    4. NÃO remover o fallback ``'invoices'``.

Estado atual: RED. O teste asserta o DESIRED behavior (que NÃO existe),
portanto FALHA. Cada teste verifica a PRESENÇA de uma feature que
deve ser adicionada na fase GREEN.
"""

import re
from pathlib import Path

import pytest


# ── Paths ────────────────────────────────────────────────────────────────

THIS_FILE = Path(__file__).resolve()
BEHAVIORS_DIR = THIS_FILE.parent
TESTS_DIR = BEHAVIORS_DIR.parent
REPO_ROOT = TESTS_DIR.parent

SERVICE_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "services"
    / "knowledgeBaseService.ts"
)

ONBOARDING_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "onboarding"
    / "OnboardingApp.tsx"
)


# ── Override root conftest cleanup (no real Supabase needed) ─────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test is pure source inspection, no DB teardown."""
    yield


# ── Helpers ──────────────────────────────────────────────────────────────


def _read_service_source() -> str:
    """Return the full text of ``knowledgeBaseService.ts``."""
    assert SERVICE_PATH.exists(), f"Source file not found: {SERVICE_PATH}"
    return SERVICE_PATH.read_text(encoding="utf-8")


def _read_onboarding_source() -> str:
    """Return the full text of ``OnboardingApp.tsx``."""
    assert ONBOARDING_PATH.exists(), f"Source file not found: {ONBOARDING_PATH}"
    return ONBOARDING_PATH.read_text(encoding="utf-8")


def _extract_function_body(source: str, fn_name: str, start_marker: str = "export async function") -> str:
    """Return the body of the named async function using brace counting.

    Searches for ``start_marker + fn_name`` then brace-counts to find the body.
    Returns the body text (content between outer braces).
    Raises ``AssertionError`` if not found.
    """
    pattern = re.escape(start_marker) + r"\s+" + re.escape(fn_name) + r"\s*\([^)]*\)\s*(?::\s*[^{]+)?\s*\{"
    match = re.search(pattern, source, re.DOTALL)
    assert match, (
        f"Não foi possível localizar o corpo da função `{fn_name}` em "
        f"{SERVICE_PATH if 'knowledge' in fn_name.lower() else ONBOARDING_PATH}. "
        f"Procurou-se: `{start_marker} {fn_name}(...)`."
    )

    body_start = match.end()
    depth = 1
    j = body_start
    in_string = None
    in_line_comment = False
    in_block_comment = False
    while j < len(source) and depth > 0:
        ch = source[j]
        nxt = source[j + 1] if j + 1 < len(source) else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            j += 1
            continue
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                j += 2
                continue
            j += 1
            continue
        if in_string is not None:
            if ch == "\\":
                j += 2
                continue
            if ch == in_string:
                in_string = None
                j += 1
                continue
            j += 1
            continue
        if ch == "/" and nxt == "/":
            in_line_comment = True
            j += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            j += 2
            continue
        if ch in ('"', "'", "`"):
            in_string = ch
            j += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        j += 1

    assert depth == 0, f"Falha ao parsear o corpo de `{fn_name}` — chaves desbalanceadas."
    return source[body_start : j - 1]


# ── AC4: uploadCsvDataSource() -- schema_type parameter ─────────────────


def test_bkl_037b_ac4_upload_csv_must_accept_schema_type_param():
    """AC4 — ``uploadCsvDataSource()`` DEVE aceitar ``schemaType`` opcional.

    Atualmente a assinatura é (linhas 264-266 de knowledgeBaseService.ts):

        export async function uploadCsvDataSource(
          file: File,
          clientId: string,
        ): Promise<CsvUploadResult>

    Após o fix, deve ser:

        export async function uploadCsvDataSource(
          file: File,
          clientId: string,
          schemaType?: string,
        ): Promise<CsvUploadResult>

    Esta asserção testa que ``schemaType?`` JÁ está na assinatura — como
    a feature ainda não existe, o teste FALHA (RED).
    """
    source = _read_service_source()

    sig_match = re.search(
        r"export\s+async\s+function\s+uploadCsvDataSource\s*\(([^)]*)\)",
        source,
        re.DOTALL,
    )
    assert sig_match, (
        f"Não foi possível encontrar a assinatura de `uploadCsvDataSource` em "
        f"{SERVICE_PATH}."
    )

    sig_body = sig_match.group(1)

    # Test for the DESIRED feature: schemaType? must be in the signature
    has_schema_type_param = "schemaType?" in sig_body or "schema_type?" in sig_body
    assert has_schema_type_param, (
        "AC4 violada — RED. A função `uploadCsvDataSource()` em "
        f"{SERVICE_PATH} NÃO aceita `schemaType` opcional. "
        f"Assinatura atual: `uploadCsvDataSource({sig_body.strip()})`. "
        "A implementação GREEN deve adicionar um parâmetro opcional "
        "`schemaType?: string` e propagá-lo para `form.append('schema_type', ...)` "
        "em vez do valor hardcoded 'invoices'."
    )


def test_bkl_037b_ac4_upload_csv_must_use_variable_schema_type():
    """AC4 — ``uploadCsvDataSource()`` DEVE usar variável em vez de 'invoices'.

    Atualmente linha 271 de knowledgeBaseService.ts:

        form.append('schema_type', 'invoices')

    Após o fix, o valor deve ser uma variável (ex.: ``schemaType || 'invoices'``)
    que possa ser controlada pelo parâmetro opcional ``schemaType``.

    Esta asserção testa que o valor passado NÃO é a string literal ``'invoices'``
    — como o código atual usa o literal, o teste FALHA (RED).
    """
    source = _read_service_source()
    fn_body = _extract_function_body(source, "uploadCsvDataSource")

    schema_type_append = re.search(
        r"""form\.append\s*\(\s*['"]schema_type['"]\s*,\s*([^)]+)\)""",
        fn_body,
    )
    assert schema_type_append is not None, (
        "AC4 violada: não encontrou `form.append('schema_type', ...)` "
        f"dentro de `uploadCsvDataSource()` em {SERVICE_PATH}."
    )

    value_part = schema_type_append.group(1).strip()

    # DESIRED behavior: value must be a VARIABLE, not a hardcoded literal
    is_variable = not bool(re.match(r"""^['"`][^'"`]+['"`]$""", value_part))
    assert is_variable, (
        "AC4 violada — RED. O valor passado para `form.append('schema_type', ...)` "
        f"em `uploadCsvDataSource()` é o hardcoded `{value_part}`. "
        "A implementação GREEN deve substituir o literal por uma variável "
        "que use o parâmetro opcional `schemaType`, ex.: "
        "`form.append('schema_type', schemaType || 'invoices')`."
    )


# ── AC6: StepLaunch usa schema_type do usuário ──────────────────────────


def test_bkl_037b_ac6_step_launch_must_accept_csv_schema_type_prop():
    """AC6 — ``StepLaunch`` DEVE aceitar ``csvSchemaType`` como prop.

    Atualmente StepLaunch recebe (linhas 1493-1501):

        { bootstrap, pendingCredentials, onDone, website, csvFile,
          csvSheetName, driveFileId, confirmedColumnMapping }

    Após o fix, deve incluir ``csvSchemaType?: string``.

    Esta asserção testa que a prop JÁ existe — como não existe, FALHA (RED).
    """
    source = _read_onboarding_source()

    # StepLaunch type annotation spans multiple lines with destructured props
    # Pattern: function StepLaunch({ ... }: { ... }) {
    # Use DOTALL to match across newlines
    props_match = re.search(
        r"function\s+StepLaunch\s*\(\s*\{([^}]+)\}\s*:",
        source,
        re.DOTALL,
    )
    assert props_match, (
        f"Não foi possível encontrar a definição de `StepLaunch` em "
        f"{ONBOARDING_PATH}."
    )

    props_str = props_match.group(1)

    # DESIRED: csvSchemaType MUST be in the destructured props
    has_csv_schema_type = "csvSchemaType" in props_str
    assert has_csv_schema_type, (
        f"AC6 violada — RED. `StepLaunch` em {ONBOARDING_PATH} NÃO possui "
        f"a prop `csvSchemaType` em sua definição. "
        f"A implementação GREEN deve adicionar `csvSchemaType?: string` "
        f"às props de `StepLaunch` e usá-lo no lugar de 'invoices' hardcoded."
    )


def test_bkl_037b_ac6_step_launch_must_use_variable_schema_type():
    """AC6 — ``StepLaunch`` DEVE usar variável em vez de 'invoices'.

    Atualmente linha 1617:

        form.append('schema_type', 'invoices')

    Após o fix, o valor deve vir de uma prop/estado variável (ex.: csvSchemaType).

    Esta asserção testa que o valor NÃO é mais hardcoded — como é, FALHA (RED).
    """
    source = _read_onboarding_source()

    # Find all form.append('schema_type', ...) in the entire file
    all_appends = list(re.finditer(
        r"""form\.append\s*\(\s*['"]schema_type['"]\s*,\s*([^)]+)\)""",
        source,
    ))
    assert len(all_appends) > 0, (
        "AC6 violada: não encontrou `form.append('schema_type', ...)` "
        f"em {ONBOARDING_PATH}."
    )

    # Find the append that uses a hardcoded literal
    hardcoded_found = False
    value_part = ""
    for match in all_appends:
        value_part = match.group(1).strip()
        if re.match(r"""^['"`][^'"`]+['"`]$""", value_part):
            hardcoded_found = True
            break

    # DESIRED: there should be NO hardcoded 'invoices' in any form.append('schema_type', ...)
    assert not hardcoded_found, (
        f"AC6 violada — RED. `StepLaunch` em {ONBOARDING_PATH} ainda usa valor "
        f"hardcoded `{value_part}` em `form.append('schema_type', ...)`. "
        f"A implementação GREEN deve substituir o valor hardcoded `'invoices'` "
        f"por uma variável oriunda da prop `csvSchemaType`, ex.: "
        f"`form.append('schema_type', csvSchemaType || 'invoices')`."
    )


def test_bkl_037b_ac6_onboarding_app_must_have_csv_schema_type_state():
    """AC6 — ``OnboardingApp`` DEVE ter estado ``csvSchemaType``.

    Atualmente OnboardingApp declara (linhas 1768-1776):

        const [csvFile, setCsvFile] = useState<File | null>(null)
        const [csvSheetName, setCsvSheetName] = useState<string>('')
        const [csvSourceId, setCsvSourceId] = useState<string | null>(null)

    Após o fix, deve ter também:

        const [csvSchemaType, setCsvSchemaType] = useState<string>('invoices')

    Esta asserção testa que o estado JÁ existe — como não existe, FALHA (RED).
    """
    source = _read_onboarding_source()

    # DESIRED: csvSchemaType state must exist in OnboardingApp
    has_csv_schema_type_state = "csvSchemaType" in source
    assert has_csv_schema_type_state, (
        f"AC6 violada — RED. `OnboardingApp` em {ONBOARDING_PATH} NÃO declara "
        f"o estado `csvSchemaType`. "
        f"A implementação GREEN deve adicionar "
        f"`const [csvSchemaType, setCsvSchemaType] = useState<string>('invoices')` "
        f"em `OnboardingApp`, passar `csvSchemaType` como prop para `StepLaunch`, "
        f"e propagar o callback `onCsvSchemaType` para `StepData` para que o "
        f"tipo de CSV confirmado pelo usuário seja salvo no estado."
    )
