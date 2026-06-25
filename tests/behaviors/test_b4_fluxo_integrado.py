"""RED test integrado B-4 — fluxo de login/onboarding (4 cenarios).

GOAL:
    Validar de forma integrada que o effect de resolucao de ``clientId``
    em ``apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx`` (linhas
    1818-1859) implementa os 4 cenarios canonicos de login/onboarding
    previstos no card B-4 do plano de correcoes estruturais.

    Os 4 cenarios sob teste sao:

      Cenario 1 — Cliente novo (sem cadastro):
        ``get_my_client_id`` retorna ``{ data: null }`` → o effect DEVE
        chamar ``supabase.rpc('ensure_tenant_row')`` e em seguida
        ``setStep('info')``.

      Cenario 2 — Cliente existente, onboarding incompleto, sem dados:
        ``get_my_client_id`` retorna ``clientId`` →
        ``clientes_blu.onboarding_completed_at = NULL`` →
        ``localStorage.onboarding_returning_to_data`` NAO setado →
        ``setStep('info')`` (fallback final).

      Cenario 3 — Cliente existente COM dados ativos (O BUG):
        ``get_my_client_id`` retorna ``clientId`` →
        ``onboarding_completed_at = NULL`` → sem
        ``onboarding_returning_to_data``.
        O effect DEVERIA consultar ``has_active_data_sources`` via RPC
        e, se a fonte for ativa, navegar para ``/app`` em vez de cair
        no fallback do Cenario 2.

      Cenario 4 — Cliente completo (onboarding finalizado):
        ``get_my_client_id`` retorna ``clientId`` →
        ``onboarding_completed_at IS NOT NULL`` →
        ``navigate('/app', { replace: true })``.

BEHAVIOR:
    B-4 — fluxo integrado de login/onboarding (card B-4 do plano).

    Hoje (RED para o Cenario 3) o ramo ``onboarding_completed_at = NULL``
    (linhas 1842-1844 do OnboardingApp.tsx) cai DIRETO em
    ``setStep('info')`` sem consultar a RPC
    ``has_active_data_sources``.  Clientes que ja' estao com ETLs
    rodando (Google Drive, Nuvemshop, Conta Azul, etc.) sao forcados
    a refazer o wizard do zero, vendo a tela 'info' mesmo tendo
    dados ativos no produto.

AC (Acceptance Criteria) — 4 cenarios do card B-4:

    AC#1 (Cenario 1 — novo cliente / sem clientId):
        Quando ``supabase.rpc('get_my_client_id')`` retorna ``data =
        null``, o effect DEVE:
          (a) chamar ``supabase.rpc('ensure_tenant_row')`` (best-effort)
          (b) chamar ``setStep('info')``
        Estado atual: GREEN (linhas 1846-1852).

    AC#2 (Cenario 2 — cliente existente sem dados):
        Quando ``get_my_client_id`` retorna ``clientId`` MAS
        ``onboarding_completed_at = NULL`` E
        ``localStorage.onboarding_returning_to_data`` NAO esta'
        setado, o effect DEVE cair no fallback final
        ``setStep('info')``.
        Estado atual: GREEN (linhas 1842-1845).

    AC#3 (Cenario 3 — cliente com fontes de dados ativas — O BUG):
        Quando ``get_my_client_id`` retorna ``clientId`` MAS
        ``onboarding_completed_at = NULL``, o effect DEVE, ANTES
        de cair no fallback do AC#2, consultar
        ``supabase.rpc('has_active_data_sources', ...)`` e, se o
        resultado for truthy, executar
        ``navigate('/app', { replace: true })``.
        Estado atual: RED — o else (linhas 1842-1845) vai DIRETO
        para ``setStep('info')`` sem chamar a RPC.  Este e' o UNICO
        AC que esta' RED hoje.

    AC#4 (Cenario 4 — onboarding concluido):
        Quando ``onboarding_completed_at`` e' nao-nulo, o effect
        DEVE chamar ``navigate('/app', { replace: true })``.
        Estado atual: GREEN (linhas 1836-1837).

DECISAO DE IMPLEMENTACAO:
    Estrategia: source_inspection (regex sobre o arquivo .tsx).
    Arquivo alvo: apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx
    Nao importa React, nao monta mocks, nao consulta o banco.
    O teste falha com ``pytest.fail()`` em pt-BR enquanto o AC#3
    (Cenario 3) nao estiver implementado.  Os demais ACs (1, 2 e 4)
    estao GREEN hoje e devem permanecer GREEN apos a fase GREEN
    (regressao).

Anti-Goals (must NOT be violated):
    1. NAO executar JSX/React runtime — o teste e' puro I/O + regex.
    2. NAO depender de Supabase, mocks ou fixtures de DB.
    3. NAO alterar o ``OnboardingApp.tsx`` neste behavior — a
       implementacao do AC#3 e' feita na fase GREEN.
    4. NAO introduzir asserts frouxos que passam no estado RED;
       este arquivo DEVE falhar especificamente no Cenario 3
       (AC#3) ate' que a verificacao de ``has_active_data_sources``
       seja adicionada antes do ``setStep('info')`` final.

Estado atual: RED — Cenarios 1, 2 e 4 estao GREEN (regressao).
Cenario 3 (AC#3) e' o UNICO que falha — este teste serve como
gate integrado: a implementacao do card B-4 so' sera' considerada
GREEN quando TODOS os 4 cenarios passarem.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Constants: paths e marcadores do source sob teste ───────────────────


REPO_ROOT = Path(__file__).resolve().parent.parent.parent

ONBOARDING_APP_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "onboarding"
    / "OnboardingApp.tsx"
)

# Marcadores que delimitam o effect de resolucao de clientId dentro
# do ``.then(`` do ``supabase.rpc('get_my_client_id')`` (linhas
# 1824-1856 do OnboardingApp.tsx).  Usamos o marker
# ``row?.onboarding_completed_at`` (linha 1836) como ancora porque
# ele marca o inicio do bloco de decisao de routing que cobre os
# 4 cenarios do card B-4.
ONBOARDING_MARKER = "row?.onboarding_completed_at"

# Janela (em caracteres) apos o marker que cobre o ``.then(`` inteiro
# do effect.  O effect tem ~30 linhas / ~2000 chars, entao 5000 da'
# margem generosa sem tornar a regex lenta.
_SEARCH_WINDOW = 5000


# ── Override do root conftest (teste puramente estatico) ──────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest — este teste e'
    puro I/O de arquivo, sem necessidade de teardown no Supabase.
    """
    yield


# ── Helpers de inspecao do TypeScript ─────────────────────────────────


def _onboarding_source_text() -> str:
    """Le o componente e devolve o conteudo como string unica."""
    assert ONBOARDING_APP_PATH.exists(), (
        f"Componente nao encontrado em {ONBOARDING_APP_PATH}. "
        "O behavior B-4 (fluxo integrado) exige que este arquivo "
        "exista no repositorio."
    )
    return ONBOARDING_APP_PATH.read_text(encoding="utf-8")


def _slice_from_onboarding_marker(src: str) -> str:
    """Devolve o trecho do arquivo que vem **a partir** da checagem
    ``row?.onboarding_completed_at`` (linha 1836 do
    ``OnboardingApp.tsx``), limitado a ``_SEARCH_WINDOW`` caracteres.

    Se o marcador nao for encontrado, devolve string vazia — cabendo
    ao teste falhar com mensagem clara dizendo que o effect esperado
    nao existe (pre-condicao de sanidade violada).
    """
    idx = src.find(ONBOARDING_MARKER)
    if idx < 0:
        return ""
    return src[idx : idx + _SEARCH_WINDOW]


def _has_rpc_call(window: str, rpc_name: str) -> bool:
    """Detecta a presenca de uma chamada ``.rpc('<rpc_name>', ...)``
    (ou variantes com aspas duplas, whitespace extra) dentro de
    ``window``.
    """
    pattern = re.compile(
        r"\.rpc\(\s*[\"']" + re.escape(rpc_name) + r"[\"']",
        re.IGNORECASE | re.DOTALL,
    )
    return bool(pattern.search(window))


def _has_set_step(window: str, step_name: str) -> bool:
    """Detecta ``setStep('<step_name>')`` (ou aspas duplas) dentro de
    ``window``.
    """
    pattern = re.compile(
        r"setStep\(\s*[\"']" + re.escape(step_name) + r"[\"']",
        re.IGNORECASE,
    )
    return bool(pattern.search(window))


def _has_navigate_to_app(window: str) -> bool:
    """Detecta ``navigate('/app', { replace: true })`` (ou aspas
    duplas) dentro de ``window``.
    """
    pattern = re.compile(
        r"navigate\(\s*[\"']/app[\"']",
        re.IGNORECASE,
    )
    return bool(pattern.search(window))


# ════════════════════════════════════════════════════════════════════════
# TESTE INTEGRADO — os 4 cenarios do card B-4
# ════════════════════════════════════════════════════════════════════════


def test_b4_cenarios_1_a_4_fluxo_integrado():
    """Teste integrado do fluxo de login/onboarding (card B-4).

    Este teste valida os 4 cenarios canonicos de login/onboarding
    que o effect de resolucao de ``clientId`` no
    ``OnboardingApp.tsx`` (linhas 1818-1859) deve tratar:

      - AC#1 (Cenario 1 — novo cliente / sem clientId):
          ``get_my_client_id`` retorna ``null`` → ``ensure_tenant_row``
          + ``setStep('info')``.  DEVE PASSAR (GREEN) hoje.

      - AC#2 (Cenario 2 — cliente existente sem dados):
          ``get_my_client_id`` retorna ``clientId``,
          ``onboarding_completed_at = NULL`` e sem
          ``onboarding_returning_to_data`` → fallback
          ``setStep('info')``.  DEVE PASSAR (GREEN) hoje.

      - AC#3 (Cenario 3 — cliente com fontes de dados ativas — O BUG):
          ``get_my_client_id`` retorna ``clientId``,
          ``onboarding_completed_at = NULL`` e sem
          ``onboarding_returning_to_data`` → DEVERIA consultar
          ``has_active_data_sources`` e navegar para ``/app`` se
          ativo, mas cai em ``setStep('info')``.  DEVE FALHAR (RED)
          ate' implementacao na fase GREEN.

      - AC#4 (Cenario 4 — onboarding concluido):
          ``onboarding_completed_at`` nao-nulo →
          ``navigate('/app', { replace: true })``.  DEVE PASSAR
          (GREEN) hoje.

    Estado atual: RED — apenas o AC#3 falha.  A mensagem de erro
    detalha em pt-BR o que precisa ser implementado no Cenario 3
    para que o card B-4 vire GREEN.

    Estrategia: source_inspection (regex sobre o arquivo .tsx).
    Sem React runtime, sem Supabase client, sem mocks, sem DB.
    """
    src = _onboarding_source_text()

    # ── Pre-condicao de sanidade: o marker de onboarding_completed_at
    # precisa existir no arquivo (o effect tem que estar montado). ──
    assert ONBOARDING_MARKER in src, (
        f"Esperava encontrar o marcador de checagem de onboarding "
        f"({ONBOARDING_MARKER!r}) em "
        f"{ONBOARDING_APP_PATH.relative_to(REPO_ROOT)}, mas ele nao "
        "esta' la'.  O behavior B-4 (fluxo integrado) pressupoe que "
        "o effect de resolucao de clientId ja' consulta "
        "onboarding_completed_at em clientes_blu."
    )

    window = _slice_from_onboarding_marker(src)
    assert window, (
        "Janela de inspecao vazia — verifique ONBOARDING_MARKER "
        f"em {ONBOARDING_APP_PATH.relative_to(REPO_ROOT)}."
    )

    # ── AC#1 (Cenario 1 — novo cliente / sem clientId) — GREEN ──────
    has_ensure_tenant = _has_rpc_call(window, "ensure_tenant_row")
    has_set_step_info_ac1 = _has_set_step(window, "info")
    assert has_ensure_tenant, (
        "AC#1 (Cenario 1) violado — o effect de resolucao de "
        f"clientId em {ONBOARDING_APP_PATH.relative_to(REPO_ROOT)} "
        "deveria chamar `supabase.rpc('ensure_tenant_row')` quando "
        "o usuario e' novo (sem clientId em `clientes_blu`), mas "
        "essa chamada esta' AUSENTE.  Sem o ensure_tenant_row, o "
        "tenant (clientes_blu) NAO e' criado para o novo usuario, e "
        "o bootstrap falha.  Implemente o call best-effort dentro "
        "do ramo `else {` que trata `!clientId` (em torno da linha "
        "1850)."
    )
    assert has_set_step_info_ac1, (
        "AC#1 (Cenario 1) violado — o effect deveria chamar "
        "`setStep('info')` quando o usuario e' novo, mas essa "
        "chamada esta' AUSENTE na janela inspecionada.  Sem ela, "
        "o usuario novo fica preso no step 'auth' e nao consegue "
        "preencher o wizard de onboarding."
    )

    # ── AC#2 (Cenario 2 — cliente existente sem dados) — GREEN ─────
    # O else final (depois do if/else if) DEVE chamar setStep('info').
    # Verificamos que ha' PELO MENOS uma chamada a setStep('info')
    # APOS o tratamento do `onboarding_returning_to_data` (ou seja,
    # dentro do else final do Cenario 2).  Localizamos o marker de
    # OAuth return e verificamos que setStep('info') aparece depois.
    oauth_marker = "onboarding_returning_to_data"
    oauth_idx = window.find(oauth_marker)
    assert oauth_idx >= 0, (
        "Pre-condicao AC#2 violada: o marker "
        f"`{oauth_marker}` deveria aparecer na janela (Cenario 2), "
        "mas nao aparece.  Isso indica que a estrutura do effect "
        "foi alterada — revise se o Cenario 2 ainda faz sentido."
    )
    after_oauth = window[oauth_idx:]
    assert _has_set_step(after_oauth, "info"), (
        "AC#2 (Cenario 2) violado — depois do bloco "
        "`onboarding_returning_to_data` o effect deveria cair no "
        "fallback final `setStep('info')` quando NAO ha' a flag de "
        "OAuth, mas essa chamada esta' AUSENTE.  Sem ela, clientes "
        "que voltam ao /onboarding sem flag de OAuth e sem "
        "onboarding_completed_at ficam presos em 'auth'.  "
        "Implemente o fallback final:\n\n"
        "  } else {\n"
        "    // Provisional profile without completed onboarding\n"
        "    // — resume from info.\n"
        "    if (!cancelled) setStep('info')\n"
        "  }\n"
    )

    # ── AC#4 (Cenario 4 — onboarding concluido) — GREEN ─────────────
    # O if (row?.onboarding_completed_at) deve chamar
    # navigate('/app', { replace: true }).  Verificamos que o
    # navigate('/app') aparece DIRETAMENTE apos a checagem de
    # onboarding_completed_at (o `if` do Cenario 4).
    early_window = window[:300]
    assert _has_navigate_to_app(early_window), (
        "AC#4 (Cenario 4) violado — quando `onboarding_completed_at` "
        "e' nao-nulo, o effect em "
        f"{ONBOARDING_APP_PATH.relative_to(REPO_ROOT)} deveria "
        "chamar `navigate('/app', { replace: true })`, mas essa "
        "chamada esta' AUSENTE nas primeiras linhas apos a "
        "checagem.  Sem ela, clientes com onboarding completo que "
        "voltem ao /onboarding (ex.: por URL digitada, redirect de "
        "OAuth, deep link) ficam presos no wizard mesmo ja' tendo "
        "terminado."
    )

    # ── AC#3 (Cenario 3 — cliente com fontes de dados ativas) — RED ─
    # (a) A RPC `has_active_data_sources` precisa estar sendo chamada
    # dentro do mesmo `.then(` do effect de resolucao de clientId.
    has_active_sources_rpc = _has_rpc_call(window, "has_active_data_sources")

    # (b) O navigate('/app') tambem precisa estar presente no ramo
    # do AC#3 — mas como o AC#4 ja' tem um navigate('/app') na
    # janela inteira, precisamos confirmar que a chamada acontece
    # DEPOIS de `has_active_data_sources` (ou seja, que a checagem
    # da RPC e' a origem do redirect para /app no Cenario 3).
    has_active_sources_navigate = False
    if has_active_sources_rpc:
        rpc_idx = re.search(
            r"\.rpc\(\s*[\"']has_active_data_sources[\"']",
            window,
            re.IGNORECASE,
        )
        if rpc_idx:
            after_rpc = window[rpc_idx.start():]
            has_active_sources_navigate = _has_navigate_to_app(
                after_rpc[:1500]
            )

    if not has_active_sources_rpc or not has_active_sources_navigate:
        pytest.fail(
            "AC#3 (Cenario 3) violado — RED.  O effect de resolucao "
            f"de clientId em "
            f"{ONBOARDING_APP_PATH.relative_to(REPO_ROOT)} "
            "(linhas 1836-1844) trata o ramo "
            "`onboarding_completed_at = NULL` indo DIRETO para "
            "`setStep('info')` sem consultar "
            "`supabase.rpc('has_active_data_sources', ...)`.\n\n"
            "ELEMENTOS QUE FALTAM (verifique cada um):\n"
            f"  - Chamada `supabase.rpc('has_active_data_sources', "
            f"...` no effect: "
            f"{'PRESENTE' if has_active_sources_rpc else 'AUSENTE ✗'}\n"
            f"  - `navigate('/app', {{ replace: true }})` no ramo "
            f"do Cenario 3 (apos a checagem da RPC): "
            f"{'PRESENTE' if has_active_sources_navigate else 'AUSENTE ✗'}\n\n"
            "IMPACTO EM PRODUCAO:\n"
            "  Clientes que ja' conectaram integracoes (Google "
            "Drive, Nuvemshop, Conta Azul, etc.) e cujos ETLs ja' "
            "estao trazendo dados — mas que por algum motivo "
            "(ex.: provisionamento parcial, migracao, ou auth "
            "re-emitido) chegam ao /onboarding com "
            "onboarding_completed_at = NULL — sao forcados a "
            "refazer o wizard do zero, vendo a tela 'info' mesmo "
            "tendo dados ativos no produto.  Isso gera friccao "
            "desnecessaria e confunde quem ja' esta' operando o "
            "produto.\n\n"
            "IMPLEMENTACAO GREEN ESPERADA (dentro do mesmo .then( "
            "do `supabase.rpc('get_my_client_id')`, no ramo `else` "
            "do `if (row?.onboarding_completed_at)`, ANTES do "
            "`setStep('info')` final):\n\n"
            "  } else {\n"
            "    // Provisional profile without completed onboarding\n"
            "    // — but check if the client already has active\n"
            "    // data sources (Google Drive, Nuvemshop, Conta\n"
            "    // Azul etc.) and, if so, skip the wizard and go\n"
            "    // straight to /app.\n"
            "    let hasActiveSources = false\n"
            "    try {\n"
            "      const { data } = await supabase.rpc(\n"
            "        'has_active_data_sources',\n"
            "        { p_client_id: clientId }\n"
            "      )\n"
            "      hasActiveSources = !!data\n"
            "    } catch { /* best-effort */ }\n"
            "    if (hasActiveSources) {\n"
            "      navigate('/app', { replace: true })\n"
            "      return\n"
            "    }\n"
            "    if (!cancelled) setStep('info')\n"
            "  }\n\n"
            "OBSERVACOES DE DESIGN:\n"
            "  - O RPC deve ser envolvido em try/catch para nao "
            "quebrar a navegacao se a funcao falhar — o fallback "
            "para setStep('info') permanece como caminho de "
            "recuperacao.\n"
            "  - O `return` apos o navigate e' importante para "
            "evitar que o `setStep('info')` continue sendo "
            "executado na mesma volta do .then().\n"
            "  - A RPC `has_active_data_sources` deve existir no "
            "schema `public` (vide behavior B-1) e retornar "
            "`true` quando houver ao menos um registro em "
            "`client_data_sources` com `sync_status IN ('ready', "
            "'success', 'synced')` para o `p_client_id` dado.\n\n"
            "REFERENCIAS:\n"
            "  - Card B-4 do plano de correcoes estruturais.\n"
            "  - B-1: definicao da RPC `has_active_data_sources` "
            "no baseline SQL.\n"
            "  - B-2: teste de fallback redirect (mesma "
            "implementacao, foco mais restrito)."
        )
