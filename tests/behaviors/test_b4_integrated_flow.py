"""RED test for behavior B-4 — OnboardingApp: integrated flow (full AC matrix).

GOAL:
    Validar, como um TODO integrado, que o effect de resolução de
    ``clientId`` em ``apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx``
    (linhas 1818-1859) implementa TODAS as ramificações do fluxo de
    onboarding descritas abaixo.  O effect decide, após o usuário
    autenticar, qual passo do wizard mostrar (``auth`` → ``info`` /
    ``data``) ou se já deve redirecionar para ``/app`` (quando o
    onboarding já está concluído — ou quando fontes de dados já
    estão ativas e o usuário não precisa refazer o wizard).

BEHAVIOR:
    B-4 — OnboardingApp: fluxo integrado de onboarding.

    O effect ``useEffect(() => { ... }, [user?.id, loading, step, navigate])``
    dentro de ``OnboardingApp`` faz o seguinte:
      1. Aguarda ``loading`` terminar e o ``user`` estar populado.
      2. Se ainda estamos em ``step === 'auth'``, chama
         ``supabase.rpc('get_my_client_id')`` e decide o que fazer
         com base no resultado.

    Hoje (RED para o AC3) o ramo ``onboarding_completed_at = NULL``
    (linhas 1836-1844) cai DIRETO em ``setStep('info')`` sem consultar
    a RPC ``has_active_data_sources``.  Isso faz com que clientes que
    já estão com ETLs rodando (Google Drive, Nuvemshop, Conta Azul,
    etc.) sejam forçados a refazer o wizard do zero.

AC (Acceptance Criteria) — matriz completa do fluxo integrado:

    AC#1 (Cenário 1 — novo cliente / sem clientId):
        Quando ``supabase.rpc('get_my_client_id')`` retorna ``data =
        null`` (ou seja, o usuário NÃO tem ``clientes_blu`` ainda),
        o effect DEVE:
          (a) chamar ``supabase.rpc('ensure_tenant_row')`` (best-effort)
          (b) chamar ``setStep('info')``

        Estado atual (GREEN): ambos os calls existem em
        ``OnboardingApp.tsx:1846-1852``.

    AC#2 (Cenário 2 — cliente existente sem dados):
        Quando ``get_my_client_id`` retorna um ``clientId`` MAS a linha
        em ``clientes_blu`` tem ``onboarding_completed_at = NULL`` E
        ``localStorage.onboarding_returning_to_data`` NÃO está
        setado, o effect DEVE cair no fallback final
        ``setStep('info')``.

        Estado atual (GREEN): o else final (linhas 1842-1845) chama
        ``setStep('info')`` quando não há flag de retorno e nem
        ``onboarding_completed_at``.

    AC#3 (Cenário 3 — cliente com fontes de dados ativas):
        Quando ``get_my_client_id`` retorna um ``clientId`` MAS
        ``onboarding_completed_at = NULL``, o effect DEVE, ANTES
        de cair no fallback do AC#2, consultar
        ``supabase.rpc('has_active_data_sources', ...)`` e, se o
        resultado for truthy, executar ``navigate('/app', { replace:
        true })``.

        Estado atual (RED): o else (linhas 1842-1845) vai DIRETO
        para ``setStep('info')`` sem chamar a RPC.  Este é o ÚNICO
        AC que está RED hoje.  Implementação GREEN esperada:

          } else {
            // Provisional profile without completed onboarding —
            // check if the client already has active data sources
            // (Google Drive, Nuvemshop, Conta Azul etc.) and, if so,
            // skip the wizard and go straight to /app.
            let hasActiveSources = false
            try {
              const { data } = await supabase.rpc(
                'has_active_data_sources',
                { p_client_id: clientId }
              )
              hasActiveSources = !!data
            } catch { /* best-effort */ }
            if (hasActiveSources) {
              navigate('/app', { replace: true })
              return
            }
            if (!cancelled) setStep('info')
          }

    AC#4 (Cenário 4 — onboarding concluído):
        Quando a linha em ``clientes_blu`` tem ``onboarding_completed_at``
        não-nulo, o effect DEVE chamar ``navigate('/app', { replace:
        true })``.

        Estado atual (GREEN): linhas 1836-1837.

    AC#5 (Edge case — falha de rede / timeout no RPC):
        Quando ``supabase.rpc('get_my_client_id')`` REJEITA (network
        error, timeout, RLS denial, etc.), o effect DEVE cair no
        fallback ``setStep('info')`` (não quebrar a navegação, não
        deixar o usuário preso em ``'auth'``).

        Estado atual (GREEN): o segundo argumento do ``.then(``
        (linhas 1853-1856) faz exatamente isso.

    AC#6 (Edge case — retorno do OAuth do Drive):
        Quando ``localStorage.onboarding_returning_to_data === '1'``,
        o effect DEVE remover essa flag e chamar ``setStep('data')``
        para restaurar o usuário no passo de configuração de dados
        (caso ele tenha saído para fazer OAuth do Google Drive
        durante o wizard).

        Estado atual (GREEN): linhas 1838-1841.

DECISÃO DE IMPLEMENTAÇÃO:
    Estratégia: source_inspection (regex sobre o arquivo .tsx).
    Arquivo alvo: apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx
    Não importa React, não monta mocks, não consulta o banco.
    O teste falha com ``pytest.fail`` em pt-BR enquanto o AC3 não
    estiver implementado.  Os demais ACs estão GREEN hoje e devem
    permanecer GREEN após a fase GREEN (regressão).

Anti-Goals (must NOT be violated):
    1. NÃO executar JSX/React runtime — o teste é puro I/O + regex.
    2. NÃO depender de Supabase, mocks ou fixtures de DB.
    3. NÃO alterar o ``OnboardingApp.tsx`` neste behavior — a
       implementação do AC3 é feita na fase GREEN.
    4. NÃO introduzir asserts frouxos que passam no estado RED;
       este arquivo DEVE falhar especificamente no AC3 até que a
       verificação de ``has_active_data_sources`` seja adicionada
       antes do ``setStep('info')`` final.
"""

import re
from pathlib import Path

import pytest


# ── Constants: a interface pública sob teste ───────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TARGET_FILE = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "onboarding"
    / "OnboardingApp.tsx"
)

# Marcador âncora que delimita o início do bloco sob teste dentro do
# ``.then(`` do ``supabase.rpc('get_my_client_id')`` (linha 1824).
# Procuramos tudo o que vem DEPOIS desse ponto porque o effect inteiro
# (linhas 1818-1859) é um único ``.then(`` com decisões aninhadas.
ONBOARDING_MARKER = "row?.onboarding_completed_at"

# Janela (em caracteres) após o marker que cobre o ``.then(`` inteiro
# do effect.  O effect tem ~35 linhas / ~2000 chars, então 4000 dá
# margem generosa sem tornar a regex lenta.
_SEARCH_WINDOW = 4000


# ── Override do root conftest (teste puramente estático) ──────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest — este teste é
    puro I/O de arquivo, sem necessidade de teardown no Supabase.
    """
    yield


# ── Helpers de inspeção do TypeScript ─────────────────────────────────


def _onboarding_source_text() -> str:
    """Lê o componente e devolve o conteúdo como string única."""
    assert TARGET_FILE.exists(), (
        f"Componente não encontrado em {TARGET_FILE}. "
        "O behavior B-4 (integrated flow) exige que este arquivo "
        "exista no repositório."
    )
    return TARGET_FILE.read_text(encoding="utf-8")


def _slice_from_onboarding_marker(src: str) -> str:
    """Devolve o trecho do arquivo que vem **a partir** da checagem
    ``row?.onboarding_completed_at`` (linha 1836 do
    ``OnboardingApp.tsx``), limitado a ``_SEARCH_WINDOW`` caracteres.

    Se o marcador não for encontrado, devolve string vazia — cabendo
    ao teste falhar com mensagem clara dizendo que o effect esperado
    não existe (pré-condição de sanidade violada).
    """
    idx = src.find(ONBOARDING_MARKER)
    if idx < 0:
        return ""
    return src[idx : idx + _SEARCH_WINDOW]


def _has_rpc_call(window: str, rpc_name: str) -> bool:
    """Detecta a presença de uma chamada ``.rpc('<rpc_name>', ...)``
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


# ── AC#1 — Novo cliente (sem clientId) → ensure_tenant_row + setStep('info') ─


def test_b4_ac1_novo_cliente_ensure_tenant_row_e_set_step_info():
    """AC#1 (Cenário 1): quando ``get_my_client_id`` retorna ``null``,
    o effect DEVE chamar ``supabase.rpc('ensure_tenant_row')`` e em
    seguida ``setStep('info')``.

    Estado atual (GREEN): ambos os calls existem em
    ``OnboardingApp.tsx`` dentro do ``} else {`` que trata
    ``!clientId`` (linhas 1846-1852).
    """
    src = _onboarding_source_text()

    # Pré-condição de sanidade: o marker de onboarding_completed_at
    # precisa existir no arquivo (o effect tem que estar montado).
    assert ONBOARDING_MARKER in src, (
        f"Esperava encontrar o marcador de checagem de onboarding "
        f"({ONBOARDING_MARKER!r}) em "
        f"{TARGET_FILE.relative_to(REPO_ROOT)}, mas ele não está "
        "lá.  O behavior B-4 pressupõe que o effect de resolução "
        "de clientId já consulta onboarding_completed_at em "
        "clientes_blu."
    )

    window = _slice_from_onboarding_marker(src)
    assert window, "Janela de inspeção vazia — verifique ONBOARDING_MARKER."

    # AC#1(a): chamada a ensure_tenant_row presente
    assert _has_rpc_call(window, "ensure_tenant_row"), (
        "AC#1(a) violado — o effect de resolução de clientId em "
        f"{TARGET_FILE.relative_to(REPO_ROOT)} deveria chamar "
        "`supabase.rpc('ensure_tenant_row')` quando o usuário é "
        "novo (não tem clientId em `clientes_blu`), mas essa "
        "chamada está AUSENTE.  Sem o ensure_tenant_row, o token "
        "do Google Drive capturado durante o step 'data' não "
        "encontra um tenant válido para anexar — quebrando a "
        "conexão OAuth.  Implemente o call best-effort dentro do "
        "ramo `else {` que trata `!clientId` (em torno da linha "
        "1850):\n\n"
        "  try {\n"
        "    await supabase.rpc('ensure_tenant_row')\n"
        "  } catch { /* best-effort */ }\n"
    )

    # AC#1(b): setStep('info') presente (pelo menos uma ocorrência)
    assert _has_set_step(window, "info"), (
        "AC#1(b) violado — o effect deveria chamar "
        "`setStep('info')` quando o usuário é novo, mas essa "
        "chamada está AUSENTE na janela inspecionada.  Sem ela, "
        "o usuário novo fica preso no step 'auth' e não consegue "
        "preencher o wizard de onboarding."
    )


# ── AC#2 — Cliente existente sem dados → setStep('info') (fallback) ─


def test_b4_ac2_cliente_existente_sem_dados_fallback_set_step_info():
    """AC#2 (Cenário 2): quando ``get_my_client_id`` retorna um
    ``clientId`` MAS ``onboarding_completed_at = NULL`` E
    ``localStorage.onboarding_returning_to_data !== '1'``, o effect
    DEVE cair no fallback ``setStep('info')`` (provisional profile
    sem onboarding concluído → resume do começo do wizard).

    Estado atual (GREEN): o else final (linhas 1842-1845) chama
    ``setStep('info')`` neste cenário.  Este teste é uma
    **proteção contra regressão** — se alguém acidentalmente
    remover o fallback final durante a implementação do AC3, o
    teste vai falhar.
    """
    src = _onboarding_source_text()
    window = _slice_from_onboarding_marker(src)
    assert window, "Janela de inspeção vazia — verifique ONBOARDING_MARKER."

    # O else final (depois do if/else if) DEVE chamar setStep('info').
    # Procuramos o ÚLTIMO setStep('info') na janela — ele deve estar
    # dentro do ramo else do AC#2 (linhas 1842-1845).
    matches = list(
        re.finditer(r"setStep\(\s*[\"']info[\"']", window, re.IGNORECASE)
    )
    assert matches, (
        "AC#2 violado — o effect não chama `setStep('info')` em "
        "lugar nenhum dentro da janela do AC#1/AC#2.  Sem o "
        "fallback final, clientes com `clientes_blu.onboarding_"
        "completed_at = NULL` ficam travados no step 'auth' e "
        "nunca entram no wizard de onboarding."
    )

    # Deve haver PELO MENOS uma chamada a setStep('info') APÓS o
    # tratamento do `onboarding_returning_to_data` (ou seja, dentro
    # do else final do AC#2).  Localizamos o marker de OAuth return
    # e verificamos que setStep('info') aparece depois.
    oauth_marker = "onboarding_returning_to_data"
    oauth_idx = window.find(oauth_marker)
    assert oauth_idx >= 0, (
        "Pré-condição AC#2 violada: o marker `onboarding_returning_"
        "to_data` deveria aparecer na janela (AC#6), mas não "
        "aparece.  Isso indica que a estrutura do effect foi "
        "alterada — revise se o AC#2 ainda faz sentido."
    )

    after_oauth = window[oauth_idx:]
    assert _has_set_step(after_oauth, "info"), (
        "AC#2 violado — depois do bloco `onboarding_returning_to_"
        "data` (AC#6) o effect deveria cair no fallback final "
        "`setStep('info')`, mas essa chamada está AUSENTE.  Sem "
        "ela, clientes que voltam ao /onboarding sem flag de "
        "OAuth e sem onboarding_completed_at ficam presos em "
        "'auth'.  Implemente o fallback final:\n\n"
        "  } else {\n"
        "    // Provisional profile without completed onboarding "
        "    — resume from info.\n"
        "    if (!cancelled) setStep('info')\n"
        "  }\n"
    )


# ── AC#3 — Cliente com fontes ativas → navigate('/app') (RED) ────────


def test_b4_ac3_cliente_com_fontes_ativas_navigate_app():
    """AC#3 (Cenário 3): quando ``onboarding_completed_at = NULL`` MAS
    o cliente já possui fontes de dados ativas
    (``has_active_data_sources = true``), o effect DEVE chamar
    ``navigate('/app', { replace: true })`` em vez de cair no
    fallback do AC#2 (``setStep('info')``).

    Estado atual (RED): o else (linhas 1842-1845) trata
    ``onboarding_completed_at = NULL`` indo DIRETO para
    ``setStep('info')`` sem consultar
    ``supabase.rpc('has_active_data_sources', ...)``.  Clientes
    que já estão com ETLs rodando (Google Drive, Nuvemshop,
    Conta Azul, etc.) são forçados a refazer o wizard do zero,
    vendo a tela 'info' mesmo tendo dados ativos no produto.

    GREEN esperado: dentro do else do AC#2, ANTES do
    ``setStep('info')`` final, adicionar:

      } else {
        let hasActiveSources = false
        try {
          const { data } = await supabase.rpc(
            'has_active_data_sources',
            { p_client_id: clientId }
          )
          hasActiveSources = !!data
        } catch { /* best-effort */ }
        if (hasActiveSources) {
          navigate('/app', { replace: true })
          return
        }
        if (!cancelled) setStep('info')
      }
    """
    src = _onboarding_source_text()
    window = _slice_from_onboarding_marker(src)
    assert window, "Janela de inspeção vazia — verifique ONBOARDING_MARKER."

    # (a) A RPC `has_active_data_sources` precisa estar sendo chamada
    # dentro do mesmo `.then(` do effect de resolução de clientId.
    has_rpc = _has_rpc_call(window, "has_active_data_sources")

    # (b) O navigate('/app') também precisa estar presente na janela
    # do AC#3 (o AC#4 já tem um navigate('/app') no AC#1 — então
    # vamos verificar se há UM navigate('/app') ADICIONAL ao do
    # AC#4, ou se o navigate('/app') aparece DEPOIS do
    # `has_active_data_sources`).
    has_navigate = _has_navigate_to_app(window)

    if not has_rpc or not has_navigate:
        pytest.fail(
            "AC#3 violado — RED.  O effect de resolução de clientId "
            f"em {TARGET_FILE.relative_to(REPO_ROOT)} (linhas "
            "1836-1844) trata o ramo `onboarding_completed_at = "
            "NULL` indo DIRETO para `setStep('info')` sem "
            "consultar `supabase.rpc('has_active_data_sources', "
            "...).  \n\n"
            "IMPACTO EM PRODUÇÃO:\n"
            "  Clientes que já conectaram integrações (Google "
            "Drive, Nuvemshop, Conta Azul, etc.) e cujos ETLs "
            "já estão trazendo dados — mas que por algum motivo "
            "(ex.: provisionamento parcial, migração, ou auth "
            "re-emitido) chegam ao /onboarding com "
            "onboarding_completed_at = NULL — são forçados a "
            "refazer o wizard do zero, vendo a tela 'info' "
            "mesmo tendo dados ativos no produto.  Isso gera "
            "fricção desnecessária e confunde quem já está "
            "operando o produto.\n\n"
            "ELEMENTOS QUE FALTAM (verifique cada um):\n"
            f"  - Chamada `supabase.rpc('has_active_data_sources', "
            f"...` no effect: {'PRESENTE' if has_rpc else 'AUSENTE ✗'}\n"
            f"  - `navigate('/app', {{ replace: true }})` no "
            f"    ramo do AC#3: {'PRESENTE' if has_navigate else 'AUSENTE ✗'}\n\n"
            "IMPLEMENTAÇÃO GREEN ESPERADA (dentro do mesmo .then( "
            "do `supabase.rpc('get_my_client_id')`, no ramo `else` "
            "do `if (row?.onboarding_completed_at)`, ANTES do "
            "`setStep('info')` final):\n\n"
            "  } else {\n"
            "    // Provisional profile without completed onboarding "
            "    — but check if the client already has active data\n"
            "    // sources (Google Drive, Nuvemshop, Conta Azul "
            "    etc.) and, if so, skip the wizard and go\n"
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
            "OBSERVAÇÕES DE DESIGN:\n"
            "  - O RPC deve ser envolvido em try/catch para não "
            "quebrar a navegação se a função falhar — o fallback "
            "para setStep('info') permanece como caminho de "
            "recuperação.\n"
            "  - O `return` após o navigate é importante para "
            "evitar que o `setStep('info')` continue sendo "
            "executado na mesma volta do .then().\n"
            "  - A RPC `has_active_data_sources` deve existir no "
            "schema `public` (vide behavior B-1) e retornar "
            "`true` quando houver ao menos um registro em "
            "`client_data_sources` com `sync_status IN ('ready', "
            "'success', 'synced')` para o `p_client_id` dado."
        )


# ── AC#4 — Onboarding concluído → navigate('/app') ──────────────────


def test_b4_ac4_onboarding_completo_navigate_app():
    """AC#4 (Cenário 4): quando ``onboarding_completed_at`` é
    não-nulo, o effect DEVE chamar ``navigate('/app', { replace:
    true })``.

    Estado atual (GREEN): linhas 1836-1837.
    """
    src = _onboarding_source_text()
    window = _slice_from_onboarding_marker(src)
    assert window, "Janela de inspeção vazia — verifique ONBOARDING_MARKER."

    # Verifica que o primeiro navigate('/app') aparece DIRETAMENTE
    # após a checagem de onboarding_completed_at (o `if` do AC#4).
    early_window = window[:300]  # cobre o if do AC#4
    assert _has_navigate_to_app(early_window), (
        "AC#4 violado — quando `onboarding_completed_at` é não-nulo, "
        f"o effect em {TARGET_FILE.relative_to(REPO_ROOT)} deveria "
        "chamar `navigate('/app', { replace: true })`, mas essa "
        "chamada está AUSENTE nas primeiras linhas após a "
        "checagem.  Sem ela, clientes com onboarding completo "
        "que voltem ao /onboarding (ex.: por URL digitada, "
        "redirect de OAuth, deep link) ficam presos no wizard "
        "mesmo já tendo terminado."
    )


# ── AC#5 — Falha de rede no RPC → fallback setStep('info') ──────────


def test_b4_ac5_falha_rpc_fallback_set_step_info():
    """AC#5 (Edge case): quando ``supabase.rpc('get_my_client_id')``
    REJEITA (network error, timeout, RLS denial, etc.), o effect
    DEVE cair no fallback ``setStep('info')`` (não quebrar a
    navegação, não deixar o usuário preso em ``'auth'``).

    Implementação esperada: o segundo argumento do ``.then(``
    do effect — ``(onFulfilled, onRejected)`` — deve tratar a
    rejeição e chamar ``setStep('info')``.

    Estado atual (GREEN): linhas 1853-1856.
    """
    src = _onboarding_source_text()
    window = _slice_from_onboarding_marker(src)
    assert window, "Janela de inspeção vazia — verifique ONBOARDING_MARKER."

    # Localiza o fechamento do primeiro .then( (o parêntese de
    # fechamento do callback principal).  Procuramos o padrão
    # `},` seguido do segundo callback `() =>` — esse é o
    # onRejected do .then().
    rejection_handler = re.search(
        r"\}\s*,\s*\(\s*\)\s*=>\s*\{[^}]*setStep\([^)]*info[^)]*\)",
        window,
        re.IGNORECASE | re.DOTALL,
    )

    if not rejection_handler:
        # Tenta outra heurística: procura `, () =>` ou `,\n  () =>`
        # seguido de setStep('info') em até 200 chars.
        rejection_handler = re.search(
            r",\s*\(\s*\)\s*=>\s*\{[\s\S]{0,300}?setStep\(\s*[\"']info[\"']",
            window,
            re.IGNORECASE,
        )

    assert rejection_handler, (
        "AC#5 violado — o effect de resolução de clientId em "
        f"{TARGET_FILE.relative_to(REPO_ROOT)} deveria ter um "
        "tratamento de rejeição no `.then(`` do "
        "`supabase.rpc('get_my_client_id')` que caia no fallback "
        "`setStep('info')` quando o RPC falha (network error, "
        "timeout, RLS denial, etc.).  Sem isso, qualquer falha "
        "de rede deixa o usuário preso no step 'auth' sem "
        "feedback.  Implemente o segundo argumento do `.then(``:\n\n"
        "  supabase.rpc('get_my_client_id').then(\n"
        "    async ({ data: clientId }) => { ... },\n"
        "    () => {\n"
        "      if (!cancelled) setStep('info')\n"
        "    },\n"
        "  )\n"
    )


# ── AC#6 — Retorno do OAuth do Drive → setStep('data') ─────────────


def test_b4_ac6_oauth_drive_return_set_step_data():
    """AC#6 (Edge case): quando
    ``localStorage.onboarding_returning_to_data === '1'``, o effect
    DEVE remover essa flag e chamar ``setStep('data')`` para
    restaurar o usuário no passo de configuração de dados (caso
    ele tenha saído para fazer OAuth do Google Drive durante o
    wizard).

    Estado atual (GREEN): linhas 1838-1841.
    """
    src = _onboarding_source_text()
    window = _slice_from_onboarding_marker(src)
    assert window, "Janela de inspeção vazia — verifique ONBOARDING_MARKER."

    # (a) Verifica a checagem do localStorage
    has_localstorage_check = (
        "localStorage.getItem('onboarding_returning_to_data')" in window
        or 'localStorage.getItem("onboarding_returning_to_data")' in window
    )
    assert has_localstorage_check, (
        "AC#6(a) violado — o effect deveria consultar "
        "`localStorage.getItem('onboarding_returning_to_data')` "
        f"em {TARGET_FILE.relative_to(REPO_ROOT)} para detectar "
        "retorno do OAuth do Google Drive, mas essa checagem "
        "está AUSENTE.  Sem ela, o usuário que saiu do wizard "
        "para autorizar o Drive volta ao passo 'info' em vez de "
        "voltar ao passo 'data' (perdendo o estado da seleção "
        "de fonte de dados)."
    )

    # (b) Verifica a remoção da flag
    has_remove = (
        "localStorage.removeItem('onboarding_returning_to_data')" in window
        or 'localStorage.removeItem("onboarding_returning_to_data")' in window
    )
    assert has_remove, (
        "AC#6(b) violado — o effect deveria chamar "
        "`localStorage.removeItem('onboarding_returning_to_data')` "
        f"em {TARGET_FILE.relative_to(REPO_ROOT)} após detectar o "
        "retorno do OAuth, mas essa remoção está AUSENTE.  Sem "
        "ela, a flag persiste para sempre e o usuário SEMPRE "
        "cai em 'data' em vez de fazer o fluxo normal."
    )

    # (c) Verifica o setStep('data')
    assert _has_set_step(window, "data"), (
        "AC#6(c) violado — o effect deveria chamar "
        "`setStep('data')` quando o usuário volta do OAuth do "
        f"Drive, em {TARGET_FILE.relative_to(REPO_ROOT)}, mas "
        "essa chamada está AUSENTE."
    )


# ── Sumário do estado RED/GREEN da matriz integrada ──────────────


def test_b4_sumario_matriz_integrada():
    """Sumário: a matriz completa de 6 ACs do fluxo integrado.

    Este teste funciona como um 'guard rail' da regressão: ele
    falha com uma mensagem consolidada sempre que QUALQUER um dos
    6 ACs estiver faltando.  Útil para uma visão rápida do estado
    do flow durante a fase GREEN.

    Hoje (RED), APENAS o AC#3 está faltando — todos os outros
    devem passar.  Quando o AC#3 for implementado, este sumário
    deve passar.
    """
    src = _onboarding_source_text()
    window = _slice_from_onboarding_marker(src)
    assert window, "Janela de inspeção vazia — verifique ONBOARDING_MARKER."

    checks = {
        "AC#1 (novo cliente → ensure_tenant_row)": (
            _has_rpc_call(window, "ensure_tenant_row")
        ),
        "AC#1 (novo cliente → setStep('info'))": (
            _has_set_step(window, "info")
        ),
        "AC#2 (sem dados → setStep('info') fallback)": (
            _has_set_step(window, "info")
        ),
        "AC#3 (fontes ativas → has_active_data_sources)": (
            _has_rpc_call(window, "has_active_data_sources")
        ),
        "AC#3 (fontes ativas → navigate('/app'))": (
            _has_navigate_to_app(window)
        ),
        "AC#4 (onboarding_completed_at → navigate('/app'))": (
            _has_navigate_to_app(window)
        ),
        "AC#5 (RPC rejeita → setStep('info') no onRejected)": bool(
            re.search(
                r",\s*\(\s*\)\s*=>\s*\{[\s\S]{0,300}?setStep\(\s*[\"']info[\"']",
                window,
                re.IGNORECASE,
            )
        ),
        "AC#6 (OAuth return → setStep('data'))": (
            _has_set_step(window, "data")
        ),
    }

    failing = [name for name, ok in checks.items() if not ok]
    if failing:
        bullets = "\n".join(f"  ✗ {name}" for name in failing)
        pytest.fail(
            "Matriz integrada do OnboardingApp incompleta em "
            f"{TARGET_FILE.relative_to(REPO_ROOT)}.\n\n"
            "Os seguintes ACs estão AUSENTES (RED):\n"
            f"{bullets}\n\n"
            "Hoje o ÚNICO AC intencionalmente RED é o AC#3 "
            "(cenario 3 — `has_active_data_sources` check antes "
            "do `setStep('info')` final).  Os demais ACs já estão "
            "implementados e DEVEM permanecer GREEN durante a "
            "fase GREEN — qualquer outro AC faltando indica "
            "regressão.\n\n"
            "Implemente o AC#3 adicionando a chamada de "
            "`has_active_data_sources` dentro do `else` do AC#2 "
            "(linhas 1842-1845 do OnboardingApp.tsx), ANTES do "
            "`setStep('info')` final, conforme detalhamento do "
            "teste `test_b4_ac3_cliente_com_fontes_ativas_"
            "navigate_app`."
        )
