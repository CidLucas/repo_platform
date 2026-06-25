"""RED test — B-3 (BATCH #215): OnboardingApp.tsx redirect usar nova RPC
``is_onboarded_client()``.

GOAL:
    Substituir o ``useEffect`` de redirect em
    ``apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx`` (~L1815-1859)
    para usar ``supabase.rpc("is_onboarded_client")`` como entry point
    único, em vez do combo atual ``get_my_client_id`` + query manual
    em ``clientes_blu``.

BEHAVIOR:
    "B-3 — useEffect de redirect do OnboardingApp chama
    supabase.rpc('is_onboarded_client') como entry point único,
    navega para /app quando onboarded, restaura step='data' se
    onboarding_returning_to_data, senão get_my_client_id +
    ensure_tenant_row + setStep('info'). Error handler com fallback
    para query direta de onboarding_completed_at."

    O useEffect de redirect deve:
        1. Chamar ``supabase.rpc("is_onboarded_client")`` como entry
           point único.
        2. Se ``onboarded === true``: ``navigate("/app", { replace: true })``.
        3. Se ``onboarding_returning_to_data`` no localStorage: restaurar
           ``step="data"`` e ``localStorage.removeItem``.
        4. Senão: ``get_my_client_id`` + ``ensure_tenant_row`` se sem
           client_id, depois ``setStep("info")``.
        5. Error handler: fallback para query direta de
           ``onboarding_completed_at`` via ``supabase.from("clientes_blu")``.
        6. ``clientIdChecked`` guard via ``useRef`` continua funcionando.
        7. Cleanup de ``cancelled`` continua funcionando.

    Estado atual (BEFORE — RED):
        O useEffect em OnboardingApp.tsx L1815-1859 ainda usa
        ``supabase.rpc("get_my_client_id")`` como entry point e
        NÃO chama ``is_onboarded_client``.

    Estado esperado (AFTER — GREEN):
        O useEffect de redirect usa ``supabase.rpc("is_onboarded_client")``
        como entry point único, com fallback no error handler e
        restore do step data via localStorage.

AC (Acceptance Criteria):
    AC#1 - ``supabase.rpc("is_onboarded_client")`` chamado no useEffect
           de redirect.
    AC#2 - Se ``onboarded === true``, ``navigate("/app", { replace: true })``.
    AC#3 - ``onboarding_returning_to_data`` restaura ``step="data"`` com
           ``localStorage.removeItem``.
    AC#4 - ``get_my_client_id`` + ``ensure_tenant_row`` em else branch
           (após ``is_onboarded_client=false``).
    AC#5 - Error handler com fallback: query ``onboarding_completed_at``
           via ``supabase.from("clientes_blu")``.
    AC#6 - ``clientIdChecked`` guard continua (``useRef`` + early return).
    AC#7 - ``cancelled`` cleanup continua (``return () => { cancelled = true }``).

Anti-Goals:
    1. NÃO modificar código de produção (OnboardingApp.tsx).
    2. NÃO executar/parsear TypeScript — somente inspeção textual com regex.
    3. NÃO usar mocks, Supabase ou banco de dados.
    4. NÃO quebrar funcionalidade existente.
    5. NÃO relaxar o teste para que ele passe — precisa ser TRUE RED agora.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Paths ──────────────────────────────────────────────────────────────

THIS_FILE = Path(__file__).resolve()
BEHAVIORS_DIR = THIS_FILE.parent
TESTS_DIR = BEHAVIORS_DIR.parent
REPO_ROOT = TESTS_DIR.parent

SOURCE = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "onboarding"
    / "OnboardingApp.tsx"
)


# ── Override do root conftest (teste puramente estático) ──────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest — este teste é
    pura inspeção textual do arquivo TSX, sem teardown no Supabase, sem
    rede, sem parser TypeScript, sem execução de código React.
    """
    yield


# ── Helpers de inspeção textual ───────────────────────────────────────


def _read_source(path: Path) -> str:
    """Lê o arquivo TSX como texto puro (sem parser)."""
    assert path.is_file(), (
        f"Source file not found: {path}.  "
        "O behavior B-3 (BATCH #215) exige que o arquivo "
        "apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx exista no repo."
    )
    return path.read_text(encoding="utf-8")


# ── Teste principal (RED) — cobre todos os ACs de B-3 ────────────────


@pytest.mark.behaviors
def test_b3_onboardingapp_rpc_redirect_red() -> None:
    """B-3 (BATCH #215) — RED.  Falha enquanto o ``useEffect`` de
    redirect do ``OnboardingApp.tsx`` ainda usar
    ``supabase.rpc("get_my_client_id")`` como entry point em vez de
    ``supabase.rpc("is_onboarded_client")``.

    Esta função agrega a verificação de TODOS os ACs em uma única
    asserção: coleta todas as deficiências e dispara ``pytest.fail``
    com mensagem consolidada em pt-BR listando o que falta para GREEN.
    """
    source = _read_source(SOURCE)

    # Extrai o bloco do useEffect de redirect (L1815-1859 hoje).
    # Usamos uma heurística que captura o useEffect inteiro a partir do
    # comment "When user is authenticated at the auth step" até o
    # `}, [user?.id, loading, step, navigate])` final.
    redirect_block_match = re.search(
        r"// When user is authenticated at the auth step.*?}, \[user\?\.id, loading, step, navigate\]\)",
        source,
        re.DOTALL,
    )
    assert redirect_block_match is not None, (
        "[RED] B-3 (BATCH #215) — nao foi possivel localizar o useEffect "
        "de redirect do OnboardingApp.tsx (bloco entre o comment "
        "'When user is authenticated at the auth step' e a dependencia "
        "[user?.id, loading, step, navigate]).  O coder precisa preservar "
        "esta estrutura ao refatorar o useEffect."
    )
    redirect_block = redirect_block_match.group(0)

    problemas: list[str] = []

    # ── AC#1 — supabase.rpc("is_onboarded_client") chamado no useEffect ──
    has_is_onboarded_rpc = bool(
        re.search(
            r'supabase\.rpc\(\s*[\'"]is_onboarded_client[\'"]\s*\)',
            redirect_block,
        )
    )

    if not has_is_onboarded_rpc:
        problemas.append(
            "AC#1 — `supabase.rpc(\"is_onboarded_client\")` NAO "
            "chamado como entry point unico no useEffect de redirect.  "
            "O coder precisa substituir o entry point `get_my_client_id` "
            "pela nova RPC `is_onboarded_client()` que agrega os 3 sinais "
            "de onboarding (onboarding_completed_at, data_sources ativos, "
            "enabled_agents + conta > 1h)."
        )

    # ── AC#2 — Se onboarded === true, navigate("/app", { replace: true }) ──
    has_navigate_app = bool(
        re.search(
            r'navigate\(\s*[\'"]/app[\'"]\s*,\s*\{\s*replace:\s*true\s*\}\s*\)',
            redirect_block,
        )
    )

    if not has_navigate_app:
        problemas.append(
            "AC#2 — `navigate(\"/app\", { replace: true })` NAO presente "
            "no useEffect de redirect.  Quando `is_onboarded_client` "
            "retornar `true`, o usuario deve ser redirecionado para /app "
            "com `replace: true` para nao poluir o history."
        )

    # ── AC#3 — onboarding_returning_to_data restaura step="data" com localStorage.removeItem ──
    has_returning_to_data = bool(
        re.search(
            r"onboarding_returning_to_data",
            redirect_block,
        )
    )
    has_set_step_data = bool(
        re.search(
            r"setStep\(\s*[\'\"]data[\'\"]\s*\)",
            redirect_block,
        )
    )
    has_localstorage_remove = bool(
        re.search(
            r"localStorage\.removeItem\(\s*[\'\"]onboarding_returning_to_data[\'\"]\s*\)",
            redirect_block,
        )
    )

    if not (has_returning_to_data and has_set_step_data and has_localstorage_remove):
        missing: list[str] = []
        if not has_returning_to_data:
            missing.append("leitura de `onboarding_returning_to_data` no localStorage")
        if not has_set_step_data:
            missing.append("`setStep(\"data\")` para restaurar o step")
        if not has_localstorage_remove:
            missing.append("`localStorage.removeItem(\"onboarding_returning_to_data\")` para limpar o flag")
        problemas.append(
            "AC#3 — fluxo de retorno de OAuth NAO esta completo no "
            f"useEffect de redirect. Faltando: {', '.join(missing)}.  "
            "Quando o usuario volta do Drive OAuth, o step deve ser "
            "restaurado para 'data' e o flag removido do localStorage."
        )

    # ── AC#4 — get_my_client_id + ensure_tenant_row em else branch ──
    #    (após is_onboarded_client=false)
    has_get_my_client_id = bool(
        re.search(
            r"get_my_client_id",
            redirect_block,
        )
    )
    has_ensure_tenant_row = bool(
        re.search(
            r"ensure_tenant_row",
            redirect_block,
        )
    )

    if not (has_get_my_client_id and has_ensure_tenant_row):
        missing: list[str] = []
        if not has_get_my_client_id:
            missing.append("`get_my_client_id` para novo usuario sem client_id")
        if not has_ensure_tenant_row:
            missing.append("`ensure_tenant_row` para provisionar tenant row")
        problemas.append(
            "AC#4 — `get_my_client_id` + `ensure_tenant_row` NAO estao "
            f"presentes no else branch.  Faltando: {', '.join(missing)}.  "
            "Quando `is_onboarded_client` retornar `false` e nao houver "
            "client_id, o codigo precisa provisionar a tenant row "
            "imediatamente para que o token capture do Drive encontre "
            "um tenant valido durante o step data."
        )

    # ── AC#5 — Error handler com fallback: query onboarding_completed_at via supabase.from("clientes_blu") ──
    has_error_fallback = bool(
        re.search(
            r"clientes_blu",
            redirect_block,
        )
    )
    has_onboarding_completed_at = bool(
        re.search(
            r"onboarding_completed_at",
            redirect_block,
        )
    )

    if not (has_error_fallback and has_onboarding_completed_at):
        missing: list[str] = []
        if not has_error_fallback:
            missing.append("`supabase.from(\"clientes_blu\")` no error handler")
        if not has_onboarding_completed_at:
            missing.append("`onboarding_completed_at` no fallback")
        problemas.append(
            "AC#5 — error handler SEM fallback para query direta de "
            f"`onboarding_completed_at`.  Faltando: {', '.join(missing)}.  "
            "Quando a RPC `is_onboarded_client` falhar, o codigo precisa "
            "ter um fallback que consulta `onboarding_completed_at` "
            "diretamente em `clientes_blu` para nao quebrar o fluxo de "
            "redirect de clientes existentes."
        )

    # ── AC#6 — clientIdChecked guard continua (useRef + if clientIdChecked.current return) ──
    has_clientIdChecked_ref = bool(
        re.search(
            r"clientIdChecked\s*=\s*useRef\(false\)",
            redirect_block,
        )
    )
    has_clientIdChecked_guard = bool(
        re.search(
            r"if\s*\(\s*clientIdChecked\.current\s*\)\s*return",
            redirect_block,
        )
    )
    has_clientIdChecked_set = bool(
        re.search(
            r"clientIdChecked\.current\s*=\s*true",
            redirect_block,
        )
    )

    if not (has_clientIdChecked_ref and has_clientIdChecked_guard and has_clientIdChecked_set):
        missing: list[str] = []
        if not has_clientIdChecked_ref:
            missing.append("`clientIdChecked = useRef(false)`")
        if not has_clientIdChecked_guard:
            missing.append("`if (clientIdChecked.current) return`")
        if not has_clientIdChecked_set:
            missing.append("`clientIdChecked.current = true`")
        problemas.append(
            "AC#6 — `clientIdChecked` guard NAO esta completo.  "
            f"Faltando: {', '.join(missing)}.  O guard contra multiplas "
            "execucoes do useEffect (causadas por multiplos eventos de "
            "auth state do OAuth) precisa ser preservado na refatoracao."
        )

    # ── AC#7 — cancelled cleanup continua (return () => { cancelled = true }) ──
    has_cancelled_decl = bool(
        re.search(
            r"let\s+cancelled\s*=\s*false",
            redirect_block,
        )
    )
    has_cancelled_cleanup = bool(
        re.search(
            r"return\s*\(\s*\)\s*=>\s*\{\s*cancelled\s*=\s*true\s*\}",
            redirect_block,
        )
    )

    if not (has_cancelled_decl and has_cancelled_cleanup):
        missing: list[str] = []
        if not has_cancelled_decl:
            missing.append("`let cancelled = false` no inicio do effect")
        if not has_cancelled_cleanup:
            missing.append("`return () => { cancelled = true }` no cleanup")
        problemas.append(
            "AC#7 — `cancelled` cleanup NAO esta completo.  "
            f"Faltando: {', '.join(missing)}.  O cleanup do useEffect "
            "precisa marcar `cancelled = true` para evitar updates de "
            "estado apos unmount (memory leak / React warning)."
        )

    # ── Agrega todas as deficiências ─────────────────────────────────
    if problemas:
        cabecalho = (
            "[RED] B-3 (BATCH #215) — OnboardingApp.tsx redirect usando "
            f"RPC `is_onboarded_client` — {len(problemas)} AC(s) "
            "violado(s):\n"
        )
        detalhes = "\n".join(f"  - {p}" for p in problemas)
        pytest.fail(cabecalho + detalhes)
