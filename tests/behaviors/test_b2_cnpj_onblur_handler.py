"""
RED test for Behavior B-2 — CNPJ onBlur Handler no OnboardingApp.tsx.

GOAL:
    O input de CPF/CNPJ da empresa (Step Empresa) em
    apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx (~L585-592)
    deve disparar uma Edge Function `onboarding-cnpj-enrich` quando o
    usuário sai do campo (onBlur), desde que o valor tenha 14 dígitos
    (CNPJ puro, sem máscara).

BEHAVIOR:
    B-2 — CNPJ onBlur Handler

    1. O <input> do CPF/CNPJ deve ter `onBlur={handleCnpjBlur}`.
    2. Deve existir `async function handleCnpjBlur(` no componente.
    3. Dentro de handleCnpjBlur, deve haver chamada
       `supabase.functions.invoke('onboarding-cnpj-enrich', ...)`.
    4. A string literal `'onboarding-cnpj-enrich'` deve existir no source.
    5. Deve existir state `enrichedForCnpj` (para evitar re-disparos).
    6. Deve existir state `setEnrichingCnpj` (loading flag).

AC (Acceptance Criteria):
    AC-B2.1 — onBlur ligado ao input do CNPJ (~L585-592)
    AC-B2.2 — handleCnpjBlur é async function e chama onboarding-cnpj-enrich
    AC-B2.3 — Não dispara se cnpj.length !== 14 (validação prévia)
    AC-B2.4 — Idempotência: enrichedForCnpj evita re-fetch do mesmo CNPJ
    AC-B2.5 — Loading: setEnrichingCnpj(true)/(false) controla UI

DECISION:
    Estratégia: source-inspection via pytest
    Arquivo alvo: apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx
    Seções alvo: <input> CPF/CNPJ (~L585-592), top-level async function
                 handleCnpjBlur, supabase.functions.invoke, states

Anti-Goals (must NOT be violated):
    1. NÃO quebrar onChange existente (campo permanece editável)
    2. NÃO trocar placeholder "00.000.000/0001-00" — é o marcador de extração
    3. NÃO remover formatCnpj() aplicado no value
    4. NÃO importar libs/React no teste — pytest + pathlib apenas

Estado atual: RED — as seguintes features NÃO existem no código:
    - <input> do CNPJ NÃO tem onBlur
    - NÃO existe `handleCnpjBlur` no source
    - NÃO existe chamada a `supabase.functions.invoke('onboarding-cnpj-enrich', ...)`
    - NÃO existe string literal `onboarding-cnpj-enrich`
    - NÃO existe state `enrichedForCnpj`
    - NÃO existe state `setEnrichingCnpj`
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
        f"OnboardingApp.tsx não encontrado em {ONBOARDING_PATH}"
    )
    return ONBOARDING_PATH.read_text(encoding="utf-8")


def _extract_input_section(source: str) -> str:
    """Extrai o bloco do <input> do CPF/CNPJ a partir do placeholder.

    Estratégia: localiza a string do placeholder `00.000.000/0001-00` e
    retorna do `<input` mais próximo antes dela até o `/>` que fecha a
    tag. Isso isola o JSX do campo CNPJ dos inputs vizinhos (Nome da
    empresa, etc.).

    Returns "" se não encontrar (tratado pelo assert como RED).
    """
    marker = '"00.000.000/0001-00"'
    idx = source.find(marker)
    if idx == -1:
        return ""

    # Encontrar o "<input" imediatamente anterior ao placeholder
    input_start = source.rfind("<input", 0, idx)
    if input_start == -1:
        return ""

    # Encontrar o ">" de fechamento da tag <input ... /> — pode ser
    # self-closing (/>) ou tag aberta (>), mas o padrão do projeto é
    # self-closing para inputs.
    end = source.find("/>", input_start)
    if end == -1:
        # Fallback: tentar ">" simples
        end = source.find(">", input_start)
        if end == -1:
            return ""
        end += 1
    else:
        end += 2

    return source[input_start:end]


# ── Tests ────────────────────────────────────────────────────────────────────


def test_b2_cnpj_onblur_handler():
    """B-2 — CNPJ input deve ter onBlur handler que chama onboarding-cnpj-enrich.

    Verifica 6 propriedades RED do source OnboardingApp.tsx:

        a) <input> do CNPJ tem `onBlur={handleCnpjBlur}`
        b) Existe `async function handleCnpjBlur(` no source
        c) Existe `supabase.functions.invoke('onboarding-cnpj-enrich'` no source
        d) Existe a string literal `onboarding-cnpj-enrich` no source
        e) Existe state `enrichedForCnpj` (idempotência)
        f) Existe setter `setEnrichingCnpj` (loading flag)

    Estado atual: TODOS os 6 asserts são RED porque o input só tem
    onChange e não há handler / edge-function / states no código.

    GREEN esperado: o Coder adiciona handleCnpjBlur (async) que valida
    cnpj.length === 14, evita duplicar com enrichedForCnpj, dispara
    supabase.functions.invoke('onboarding-cnpj-enrich', { body: { cnpj } })
    e controla loading via setEnrichingCnpj.
    """
    source = _read_onboarding()
    input_section = _extract_input_section(source)

    # ── Sanity: o input do CNPJ precisa existir no source ────────────────────
    assert input_section, (
        "RED — Não foi possível localizar o bloco do <input> do CNPJ "
        "(placeholder '00.000.000/0001-00') em OnboardingApp.tsx. "
        "Esperado: o input existe (~L585-592), mas o teste não conseguiu "
        "extrair o bloco para verificar o onBlur. "
        "Verifique se o placeholder foi alterado."
    )

    # ── (a) onBlur={handleCnpjBlur} no <input> do CNPJ ──────────────────────
    assert "onBlur={handleCnpjBlur}" in input_section, (
        "RED — O <input> do CPF/CNPJ (~L585-592) NÃO tem onBlur={handleCnpjBlur}. "
        "Estado atual: tem apenas onChange, sem disparar nada ao sair do campo. "
        "Esperado: adicionar onBlur={handleCnpjBlur} ao <input> do CNPJ para "
        "acionar a Edge Function de enriquecimento quando o usuário sair do campo."
    )

    # ── (b) async function handleCnpjBlur( no source ────────────────────────
    assert "async function handleCnpjBlur(" in source, (
        "RED — Não existe `async function handleCnpjBlur(` em OnboardingApp.tsx. "
        "Esperado: declarar uma função assíncrona handleCnpjBlur que valida "
        "cnpj.length === 14, checa enrichedForCnpj !== cnpj para evitar "
        "re-fetch, e chama a Edge Function."
    )

    # ── (c) supabase.functions.invoke('onboarding-cnpj-enrich' no source ────
    assert "supabase.functions.invoke('onboarding-cnpj-enrich'" in source, (
        "RED — handleCnpjBlur não chama supabase.functions.invoke. "
        "Esperado: dentro de handleCnpjBlur, após validar CNPJ de 14 dígitos "
        "e checar enrichedForCnpj !== cnpj, chamar "
        "supabase.functions.invoke('onboarding-cnpj-enrich', { body: { cnpj } })."
    )

    # ── (d) string literal 'onboarding-cnpj-enrich' no source ──────────────
    assert "onboarding-cnpj-enrich" in source, (
        "RED — A string literal 'onboarding-cnpj-enrich' NÃO aparece em "
        "OnboardingApp.tsx. Esperado: o nome da Edge Function deve estar "
        "literalmente no source (tipicamente como primeiro argumento de "
        "supabase.functions.invoke)."
    )

    # ── (e) state enrichedForCnpj (idempotência) ────────────────────────────
    assert "enrichedForCnpj" in source, (
        "RED — Não existe o state `enrichedForCnpj` em OnboardingApp.tsx. "
        "Esperado: declarar useState para guardar o último CNPJ já enviado "
        "à Edge Function, e pular o invoke se `cnpj === enrichedForCnpj` "
        "(evita chamadas duplicadas quando o usuário re-edita o mesmo CNPJ)."
    )

    # ── (f) setter setEnrichingCnpj (loading flag) ──────────────────────────
    assert "setEnrichingCnpj" in source, (
        "RED — Não existe o setter `setEnrichingCnpj` em OnboardingApp.tsx. "
        "Esperado: declarar useState<boolean> para indicar loading do "
        "enriquecimento (ex: 'Buscando dados da empresa…'), e togglar "
        "setEnrichingCnpj(true) antes do invoke e setEnrichingCnpj(false) "
        "no finally (try/catch/finally)."
    )
