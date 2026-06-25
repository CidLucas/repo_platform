"""RED test for behavior B-4: Fallback de RPC — Evitar loading eterno.

GOAL:
    B-4 — callDimensionRpc deve retornar estrutura com zeros+period em vez de
    throw/error quando RPC não existe, evitando loading eterno no frontend.

BEHAVIOR:
    Hoje, em ``apps/blu_v3/src/api/analytics.ts``, a função ``callDimensionRpc``
    (linha 131) lança ``throw new Error`` quando o RPC retorna erro. Isso faz
    com que qualquer função que use ``callDimensionRpc`` sem try/catch —
    como ``getSupplyIndicators``, ``getInventoryIndicators``,
    ``getMarketingIndicators``, ``getAdminIndicators`` e
    ``getCommercialTopClients`` — propague o erro para o React Query,
    resultando em ``isError: true`` e loading eterno no frontend.

    A GREEN phase deve:
    - Modificar ``callDimensionRpc`` para capturar erro e retornar estrutura
      padrão com ``{ period }`` (sem throw)
    - OU adicionar try/catch em cada função vulnerável

AC (Acceptance Criteria):
    AC-3: getSupplyIndicators() nunca deixa front em loading eterno —
          retorna estrutura válida mesmo sem RPC.

    Desdobramento em ACs de teste:
    AC #1 — callDimensionRpc contém ``throw new Error`` (RED: deveria
            capturar erro e retornar { period } em vez de throw)
    AC #2 — getSupplyIndicators NÃO tem try/catch (RED: deveria ter
            proteção contra falha de RPC)
    AC #3 — getCommercialTopClients NÃO tem try/catch (RED: deveria ter
            proteção contra falha de RPC)
    AC #4 — getInventoryIndicators NÃO tem try/catch (RED: deveria ter
            proteção contra falha de RPC)
    AC #5 — getMarketingIndicators NÃO tem try/catch (RED: deveria ter
            proteção contra falha de RPC)
    AC #6 — getAdminIndicators NÃO tem try/catch (RED: deveria ter
            proteção contra falha de RPC)

Anti-Goals (must NOT be violated):
    1. NÃO alterar interface pública das funções (assinaturas, tipos de retorno)
    2. NÃO alterar funções já protegidas (getFinanceIndicators, getCommercialIndicators)
    3. NÃO modificar código de produção
    4. NÃO usar mocks ou Supabase real — pura source-inspection
    5. NÃO testar SQL/baseline

Estado atual: RED. Cada teste verifica que o comportamento DESIRED NÃO EXISTE
hoje. A leitura é puramente source-inspection (texto de .ts), sem Supabase
real e sem mocks.
"""

import re
from pathlib import Path

import pytest


# ── Paths ────────────────────────────────────────────────────────────────

THIS_FILE = Path(__file__).resolve()
BEHAVIORS_DIR = THIS_FILE.parent
TESTS_DIR = BEHAVIORS_DIR.parent
REPO_ROOT = TESTS_DIR.parent
ANALYTICS_TS_PATH = REPO_ROOT / "apps" / "blu_v3" / "src" / "api" / "analytics.ts"


# ── Override root conftest cleanup (no real Supabase needed) ─────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — pure source inspection, no DB teardown."""
    yield


# ── Helpers ──────────────────────────────────────────────────────────────


def _analytics_ts() -> str:
    assert ANALYTICS_TS_PATH.exists(), f"File not found: {ANALYTICS_TS_PATH}"
    return ANALYTICS_TS_PATH.read_text(encoding="utf-8")


def _extract_function_body(source: str, fn_name: str) -> str:
    """Extract the body of an async arrow function by name.

    Handles:
        export const fnName = async (params): ReturnType => {
    """
    pattern = (
        re.escape("export const ")
        + re.escape(fn_name)
        + r"\s*=\s*async\s*\([^)]*\)\s*(?::\s*[^{]+)?\s*=>\s*\{"
    )
    match = re.search(pattern, source, re.DOTALL)
    if not match:
        return ""

    body_start = match.end()
    depth = 1
    j = body_start
    in_str = None
    in_lc = False
    in_bc = False

    while j < len(source) and depth > 0:
        ch = source[j]
        nxt = source[j + 1] if j + 1 < len(source) else ""

        if in_lc:
            if ch == "\n":
                in_lc = False
            j += 1
            continue
        if in_bc:
            if ch == "*" and nxt == "/":
                in_bc = False
                j += 2
                continue
            j += 1
            continue
        if in_str is not None:
            if ch == "\\":
                j += 2
                continue
            if ch == in_str:
                in_str = None
                j += 1
                continue
            j += 1
            continue
        if ch == "/" and nxt == "/":
            in_lc = True
            j += 2
            continue
        if ch == "/" and nxt == "*":
            in_bc = True
            j += 2
            continue
        if ch in ('"', "'", "`"):
            in_str = ch
            j += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        j += 1

    if depth != 0:
        return ""
    return source[body_start : j - 1]


def _extract_function_body_decl(source: str, fn_name: str) -> str:
    """Extract the body of an async function declaration by name.

    Handles:
        async function callDimensionRpc<T>(rpc: string, period: string): Promise<T> {
    """
    pattern = (
        re.escape("async function ")
        + re.escape(fn_name)
        + r"<[^>]*>\s*\([^)]*\)\s*:\s*Promise<[^>]+>\s*\{"
    )
    match = re.search(pattern, source, re.DOTALL)
    if not match:
        return ""

    body_start = match.end()
    depth = 1
    j = body_start
    in_str = None
    in_lc = False
    in_bc = False

    while j < len(source) and depth > 0:
        ch = source[j]
        nxt = source[j + 1] if j + 1 < len(source) else ""

        if in_lc:
            if ch == "\n":
                in_lc = False
            j += 1
            continue
        if in_bc:
            if ch == "*" and nxt == "/":
                in_bc = False
                j += 2
                continue
            j += 1
            continue
        if in_str is not None:
            if ch == "\\":
                j += 2
                continue
            if ch == in_str:
                in_str = None
                j += 1
                continue
            j += 1
            continue
        if ch == "/" and nxt == "/":
            in_lc = True
            j += 2
            continue
        if ch == "/" and nxt == "*":
            in_bc = True
            j += 2
            continue
        if ch in ('"', "'", "`"):
            in_str = ch
            j += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        j += 1

    if depth != 0:
        return ""
    return source[body_start : j - 1]


def _has_try_catch(body: str) -> bool:
    """Check if function body contains try/catch."""
    return bool(re.search(r"\btry\s*\{", body)) and bool(
        re.search(r"\bcatch\s*[({]", body)
    )


def _has_throw(body: str) -> bool:
    """Check if function body contains throw new Error."""
    return bool(re.search(r"\bthrow\s+new\s+Error\b", body))


# ── RED Tests ────────────────────────────────────────────────────────────


def test_b4_rpc_fallback_ac1_call_dimension_rpc_has_throw():
    """AC #1: callDimensionRpc contém throw new Error (RED — deveria capturar e retornar {period})."""
    source = _analytics_ts()
    body = _extract_function_body_decl(source, "callDimensionRpc")
    assert body, pytest.fail(
        "RED AC#1: Não foi possível extrair o corpo de callDimensionRpc"
    )
    assert _has_throw(body), pytest.fail(
        "callDimensionRpc currently does NOT throw — GREEN already?"
    )
    # TRUE RED: throw existe — comportamento DESIRED (não throw) não está presente
    pytest.fail(
        "RED AC#1: callDimensionRpc contém throw new Error. "
        "Deveria capturar erro e retornar { period } em vez de throw."
    )


def test_b4_rpc_fallback_ac2_supply_indicators_no_try_catch():
    """AC #2: getSupplyIndicators NÃO tem try/catch (RED — deveria ter proteção)."""
    source = _analytics_ts()
    body = _extract_function_body(source, "getSupplyIndicators")
    assert body, pytest.fail(
        "RED AC#2: Não foi possível extrair o corpo de getSupplyIndicators"
    )
    if _has_try_catch(body):
        pytest.fail(
            "RED AC#2: getSupplyIndicators já tem try/catch — GREEN já implementada?"
        )
    # TRUE RED: sem try/catch — vulnerável a loading eterno
    pytest.fail(
        "RED AC#2: getSupplyIndicators NÃO tem try/catch. "
        "Quando callDimensionRpc lançar erro, o front fica em loading eterno."
    )


def test_b4_rpc_fallback_ac3_commercial_top_clients_no_try_catch():
    """AC #3: getCommercialTopClients NÃO tem try/catch (RED — deveria ter proteção)."""
    source = _analytics_ts()
    body = _extract_function_body(source, "getCommercialTopClients")
    assert body, pytest.fail(
        "RED AC#3: Não foi possível extrair o corpo de getCommercialTopClients"
    )
    if _has_try_catch(body):
        pytest.fail(
            "RED AC#3: getCommercialTopClients já tem try/catch — GREEN já implementada?"
        )
    # TRUE RED: sem try/catch
    pytest.fail(
        "RED AC#3: getCommercialTopClients NÃO tem try/catch. "
        "Quando RPC falhar, o front fica em loading eterno."
    )


def test_b4_rpc_fallback_ac4_inventory_indicators_no_try_catch():
    """AC #4: getInventoryIndicators NÃO tem try/catch (RED — deveria ter proteção)."""
    source = _analytics_ts()
    body = _extract_function_body(source, "getInventoryIndicators")
    assert body, pytest.fail(
        "RED AC#4: Não foi possível extrair o corpo de getInventoryIndicators"
    )
    if _has_try_catch(body):
        pytest.fail(
            "RED AC#4: getInventoryIndicators já tem try/catch — GREEN já implementada?"
        )
    pytest.fail(
        "RED AC#4: getInventoryIndicators NÃO tem try/catch. "
        "Quando RPC falhar, o front fica em loading eterno."
    )


def test_b4_rpc_fallback_ac5_marketing_indicators_no_try_catch():
    """AC #5: getMarketingIndicators NÃO tem try/catch (RED — deveria ter proteção)."""
    source = _analytics_ts()
    body = _extract_function_body(source, "getMarketingIndicators")
    assert body, pytest.fail(
        "RED AC#5: Não foi possível extrair o corpo de getMarketingIndicators"
    )
    if _has_try_catch(body):
        pytest.fail(
            "RED AC#5: getMarketingIndicators já tem try/catch — GREEN já implementada?"
        )
    pytest.fail(
        "RED AC#5: getMarketingIndicators NÃO tem try/catch. "
        "Quando RPC falhar, o front fica em loading eterno."
    )


def test_b4_rpc_fallback_ac6_admin_indicators_no_try_catch():
    """AC #6: getAdminIndicators NÃO tem try/catch (RED — deveria ter proteção)."""
    source = _analytics_ts()
    body = _extract_function_body(source, "getAdminIndicators")
    assert body, pytest.fail(
        "RED AC#6: Não foi possível extrair o corpo de getAdminIndicators"
    )
    if _has_try_catch(body):
        pytest.fail(
            "RED AC#6: getAdminIndicators já tem try/catch — GREEN já implementada?"
        )
    pytest.fail(
        "RED AC#6: getAdminIndicators NÃO tem try/catch. "
        "Quando RPC falhar, o front fica em loading eterno."
    )
