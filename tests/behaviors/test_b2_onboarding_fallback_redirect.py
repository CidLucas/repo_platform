"""RED test for behavior B-2 — OnboardingApp: Fallback redirect.

GOAL:
    Garantir que ``apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx``
    possua um **fallback** no effect que resolve o ``clientId``: quando
    ``onboarding_completed_at`` é ``NULL`` mas o cliente **já tem
    fontes de dados ativas** (``has_active_data_sources = true``), o
    componente deve redirecionar para ``/app`` em vez de prosseguir
    para o passo ``info`` do wizard de onboarding.

BEHAVIOR:
    B-2 — OnboardingApp fallback redirect.

    Atualmente, o effect em ``OnboardingApp.tsx`` (linhas 1836-1844)
    trata o ramo ``onboarding_completed_at = NULL`` indo direto para
    ``setStep('info')``, sem verificar se o cliente já conectou
    integrações (Google Drive, Nuvemshop, Conta Azul, etc.).  Quando
    o cliente já tem dados chegando via ETL/integração, mandá-lo
    refazer o wizard de onboarding é fricção desnecessária e confunde
    quem já estava operando o produto.

AC (Acceptance Criteria):
    AC#1 — Quando ``onboarding_completed_at`` é ``NULL`` e o
    ``localStorage.onboarding_returning_to_data`` não está setado,
    o código deve chamar ``supabase.rpc('has_active_data_sources',
    ...)`` (ou forma equivalente) e, se o resultado for truthy,
    executar ``navigate('/app', { replace: true })`` em vez de
    ``setStep('info')``.

DECISÃO:
    Estratégia: source_inspection (regex sobre o arquivo .tsx)
    Arquivo alvo: apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx

Anti-Goals (must NOT be violated):
    1. NÃO alterar o arquivo ``OnboardingApp.tsx`` neste behavior —
       o teste é puramente estático.  A implementação do fallback
       será feita na fase GREEN.
    2. NÃO exigir execução do React, JSX ou qualquer runtime de
       frontend — este behavior valida apenas a presença do
       ``.rpc('has_active_data_sources', ...)`` no código-fonte.
    3. NÃO depender de fixtures de banco de dados — o teste é
       determinístico e roda sem rede.

Estado atual: RED — ``OnboardingApp.tsx`` (linhas 1836-1844) trata
o ramo ``onboarding_completed_at = NULL`` indo direto para
``setStep('info')`` sem chamar ``supabase.rpc('has_active_data_sources',
...)``.  O teste falha com ``pytest.fail`` em pt-BR até que o
fallback seja adicionado (fase GREEN).
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

TARGET_RPC = "has_active_data_sources"

# Marcador que delimita o início do bloco de checagem de
# onboarding_completed_at no effect de resolução do clientId.
# Procuramos o fallback APÓS este ponto, dentro da mesma função
# assíncrona do ``.then(`` (linhas 1830-1852 do OnboardingApp.tsx).
# Usamos a substring ``onboarding_completed_at`` combinada com o
# ``navigate('/app', { replace: true })`` (já existente) para reduzir
# falsos positivos vindos de outros arquivos.
ONBOARDING_CHECK_MARKER = "row?.onboarding_completed_at"

# Janela (em caracteres) examinada após o ``ONBOARDING_CHECK_MARKER``
# para detectar a chamada ``.rpc(`` com a função alvo.  4000 chars é
# folga generosa para cobrir o ``.then(`` inteiro (o effect tem ~30
# linhas, ~1500 chars), mantendo o teste rápido.
_RPC_SEARCH_WINDOW = 4000


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
        "O behavior B-2 exige que este arquivo exista no repositório."
    )
    return TARGET_FILE.read_text()


def _slice_after_onboarding_check(src: str) -> str:
    """Devolve o trecho do arquivo que vem **depois** da checagem
    ``row?.onboarding_completed_at`` (linha 1836 do
    ``OnboardingApp.tsx``), limitado a ``_RPC_SEARCH_WINDOW``
    caracteres.

    Se o marcador não for encontrado, devolve string vazia — cabendo
    ao teste falhar com mensagem clara.
    """
    idx = src.find(ONBOARDING_CHECK_MARKER)
    if idx < 0:
        return ""
    return src[idx : idx + _RPC_SEARCH_WINDOW]


def _has_fallback_rpc(window: str) -> bool:
    """Detecta a presença de uma chamada
    ``supabase.rpc('has_active_data_sources', ...)`` (ou variantes
    equivalentes com aspas duplas, ``.rpc(`` com whitespace) dentro
    da ``window``.

    Aceita tanto ``supabase.rpc(...)`` quanto qualquer
    ``.rpc('has_active_data_sources', ...)`` desde que o **primeiro
    argumento** da chamada seja o nome da função alvo, entre aspas
    simples ou duplas.
    """
    pattern = re.compile(
        r"\.rpc\(\s*[\"']" + re.escape(TARGET_RPC) + r"[\"']",
        re.IGNORECASE | re.DOTALL,
    )
    return bool(pattern.search(window))


# ── O behavior sob teste ──────────────────────────────────────────────


def test_b2_ac1_fallback_redirect_has_active_data_sources():
    """AC#1: ``OnboardingApp.tsx`` deve implementar um fallback
    que, quando ``onboarding_completed_at`` é ``NULL`` e o cliente
    JÁ possui fontes de dados ativas (``has_active_data_sources =
    true``), redireciona para ``/app`` em vez de levar o usuário
    de volta ao passo ``info`` do wizard de onboarding.

    Falha (RED) enquanto o effect de resolução de ``clientId``
    (linhas 1836-1844) tratar o ramo ``onboarding_completed_at =
    NULL`` indo direto para ``setStep('info')`` sem consultar
    ``has_active_data_sources``.
    """
    src = _onboarding_source_text()

    # Pré-condição de sanidade: a checagem ``onboarding_completed_at``
    # precisa existir no arquivo, caso contrário este teste não
    # faria sentido (a AC é "APÓS essa checagem").
    assert ONBOARDING_CHECK_MARKER in src, (
        f"Esperava encontrar o marcador de checagem de onboarding "
        f"({ONBOARDING_CHECK_MARKER!r}) em "
        f"{TARGET_FILE.relative_to(REPO_ROOT)}, mas ele não está "
        "lá.  O behavior B-2 pressupõe que o effect de resolução "
        "de clientId já consulta onboarding_completed_at em "
        "clientes_blu."
    )

    after_check = _slice_after_onboarding_check(src)
    assert after_check, (
        "Não foi possível fatiar o arquivo após a checagem de "
        "onboarding_completed_at; verifique a constante "
        "ONBOARDING_CHECK_MARKER no teste."
    )

    if not _has_fallback_rpc(after_check):
        pytest.fail(
            "AC#1 violado: o componente "
            f"{TARGET_FILE.relative_to(REPO_ROOT)} "
            "verifica onboarding_completed_at em clientes_blu "
            "(linhas 1836-1844) e trata o ramo NULL indo "
            "diretamente para setStep('info'), mas NÃO consulta "
            "supabase.rpc('has_active_data_sources', ...) como "
            "fallback.  Clientes que já conectaram integrações "
            "(Google Drive, Nuvemshop, Conta Azul, etc.) e cujos "
            "ETLs já estão trazendo dados — mas que por algum "
            "motivo (ex.: provisionamento parcial, migração, ou "
            "auth re-emitido) chegam ao /onboarding com "
            "onboarding_completed_at = NULL — são forçados a "
            "refazer o wizard do zero, vendo a tela 'info' mesmo "
            "tendo dados ativos no produto.  Implemente o "
            "fallback adicionando — dentro do mesmo .then( do "
            "supabase.rpc('get_my_client_id') e após o bloco "
            "if (row?.onboarding_completed_at) — uma chamada "
            "equivalente a:\n\n"
            "  const { data: hasSources } = await supabase.rpc(\n"
            "    'has_active_data_sources',\n"
            "    { p_client_id: clientId }\n"
            "  )\n"
            "  if (hasSources) {\n"
            "    navigate('/app', { replace: true })\n"
            "    return\n"
            "  }\n\n"
            "antes do ramo final que chama setStep('info') no "
            "linha 1844.  Envolva o RPC em try/catch para não "
            "quebrar a navegação se a RPC falhar — o fallback "
            "para setStep('info') permanece como caminho de "
            "recuperação."
        )
