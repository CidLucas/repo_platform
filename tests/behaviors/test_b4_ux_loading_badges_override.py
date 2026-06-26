"""
RED test for Behavior B-4 — UX Loading States, Badges & Override no OnboardingApp.tsx.

GOAL:
    Quando o Step Empresa (StepInfo) faz lookup do CNPJ via Edge Function
    `onboarding-cnpj-enrich` (B-2) e persiste os dados em `cnpjEnrichData`
    (B-3), o componente deve oferecer feedback visual de UX:

        1. Durante o lookup (request em flight), mostrar texto de loading
           "Consultando Receita Federal..." (AC-B4.1).
        2. Quando a Edge Function retorna sucesso, mostrar badge de
           confirmação "Confirmado pela Receita" (AC-B4.2).
        3. Permitir ao usuário descartar/limpar os dados enriquecidos via
           um botão "Limpar dados da Receita" (AC-B4.3) — para que o
           usuário possa sobrescrever (override) caso a Receita retorne
           dados desatualizados/errados.
        4. Exibir a seção rotulada "Dados da Receita Federal" que mostra
           os campos enriquecidos (razao_social, cnpj formatado, cnae,
           etc.) para o usuário revisar antes de prosseguir (AC-B4.4).

    Arquivo alvo: apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx

BEHAVIOR:
    B-4 — UX Loading States, Badges & Override do CNPJ Enrich

    1. StepInfo deve renderizar um estado de loading textual
       "Consultando Receita Federal..." enquanto a Edge Function
       `onboarding-cnpj-enrich` está em flight (entre o `onBlur` do
       CNPJ e a resolução da Promise).
    2. Após o retorno bem-sucedido, o componente deve renderizar um
       badge/label "Confirmado pela Receita" próximo ao(s) campo(s)
       enriquecido(s) — sinalizando ao usuário que a origem dos dados
       é a Receita Federal.
    3. Deve existir um botão/handler de override com label
       "Limpar dados da Receita" que:
         - faz `setCnpjEnrichData(null)` (zera o state de enriquecimento);
         - opcionalmente também limpa o auto-fill do nome da empresa
           (`setEmpresa('')`), desde que o nome veio do auto-fill
           (i.e., o usuário não digitou manualmente).
    4. A seção que exibe os dados da Receita deve ser rotulada
       "Dados da Receita Federal" (também coberto por B-3, mas aqui
       validados como parte do contrato de UX).

AC (Acceptance Criteria):
    AC-B4.1 — String literal 'Consultando Receita Federal' existe no source
              (texto de loading durante lookup do CNPJ)
    AC-B4.2 — String literal 'Confirmado pela Receita' existe no source
              (badge de confirmação de origem dos dados)
    AC-B4.3 — String literal 'Limpar dados da Receita' existe no source
              (label do botão de override que zera cnpjEnrichData)
    AC-B4.4 — String literal 'Dados da Receita Federal' existe no source
              (rótulo da seção de exibição dos dados enriquecidos)

DECISION:
    Estratégia: source-inspection via pytest
    Arquivo alvo: apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx
    Sem React, sem DOM, sem mocks, sem DB — apenas pathlib + pytest.

Anti-Goals (must NOT be violated):
    1. NÃO bloquear o input CNPJ (campo continua editável; o loading
       é apenas um indicador visual, não um disabled).
    2. NÃO remover o onBlur handler de B-2 (`handleCnpjBlur`) que
       invoca a Edge Function.
    3. NÃO importar libs externas (React, supabase, etc.) no teste
    4. NÃO usar mocks ou fixtures de DB — puro file inspection
    5. NÃO fazer o botão "Limpar dados da Receita" remover a
       formatação do CNPJ no input (apenas zera o state de
       enriquecimento; o valor digitado do CNPJ permanece).

Estado atual: RED — as seguintes features NÃO existem no código:
    - Texto de loading 'Consultando Receita Federal' não existe
    - Badge 'Confirmado pela Receita' não existe
    - Botão/handler 'Limpar dados da Receita' não existe
    - (A seção 'Dados da Receita Federal' já é cobrada por B-3; aqui
      é reafirmada como parte do contrato de UX de B-4 — o source
      atual não tem nenhuma das 4 strings.)
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


# ── Tests ────────────────────────────────────────────────────────────────────


def test_b4_ux_loading_badges_override():
    """B-4 — StepInfo deve ter loading textual, badge de confirmação,
    botão de override e seção rotulada da Receita Federal.

    Verifica 4 propriedades RED do source OnboardingApp.tsx:

        a) String literal 'Consultando Receita Federal' existe no source
           (texto exibido enquanto `handleCnpjBlur` aguarda a resposta
           da Edge Function `onboarding-cnpj-enrich` — UX de loading).
        b) String literal 'Confirmado pela Receita' existe no source
           (badge/label exibido após o retorno bem-sucedido da Edge
           Function, sinalizando a origem dos dados exibidos).
        c) String literal 'Limpar dados da Receita' existe no source
           (label do botão/handler de override que zera `cnpjEnrichData`,
           permitindo ao usuário descartar os dados da Receita e
           sobrescrever manualmente os campos do formulário).
        d) String literal 'Dados da Receita Federal' existe no source
           (rótulo da seção que renderiza os campos enriquecidos —
           razao_social, cnpj formatado, cnae, situacao, etc.).

    Estado atual: TODOS os 4 asserts são RED porque o componente
    StepInfo não tem nenhum dos elementos de UX acima — o source
    atual trata o enrichment de forma silenciosa (sem loading, sem
    badge, sem override e sem seção rotulada).

    GREEN esperado: o Coder adiciona:
      - Um bloco condicional do tipo
        `{loadingCnpj && <span>Consultando Receita Federal...</span>}`
        (ou equivalente) dentro de StepInfo, com um state
        `loadingCnpj` que vira true no início de `handleCnpjBlur`
        e false no finally (AC-B4.1);
      - Um badge/span condicional do tipo
        `{cnpjEnrichData && <span>Confirmado pela Receita</span>}`
        próximo ao input CNPJ ou à seção de dados (AC-B4.2);
      - Um botão `<button>Limpar dados da Receita</button>` com
        handler que faz `setCnpjEnrichData(null)` e zera o
        auto-fill do nome da empresa (se veio do enrichment)
        (AC-B4.3);
      - A seção `<div>Dados da Receita Federal ...</div>` que
        renderiza os campos enriquecidos (AC-B4.4).
    """
    source = _read_onboarding()

    # ── Sanity: o arquivo precisa ter conteúdo ───────────────────────────────
    assert source, (
        "RED — OnboardingApp.tsx está vazio. "
        "Esperado: o arquivo existe e tem StepInfo com handler de CNPJ."
    )

    # ── (a) String literal 'Consultando Receita Federal' no source ───────────
    assert "Consultando Receita Federal" in source, (
        "RED — A string literal 'Consultando Receita Federal' NÃO aparece em "
        "OnboardingApp.tsx. Esperado: o StepInfo deve exibir um texto de "
        "loading (ex: 'Consultando Receita Federal...') enquanto a Edge "
        "Function `onboarding-cnpj-enrich` está em flight — tipicamente "
        "dentro de um bloco `{loadingCnpj && <span>Consultando Receita "
        "Federal...</span>}` controlado por um state `loadingCnpj` que "
        "vira true no início de `handleCnpjBlur` e false no `finally`."
    )

    # ── (b) String literal 'Confirmado pela Receita' no source ───────────────
    assert "Confirmado pela Receita" in source, (
        "RED — A string literal 'Confirmado pela Receita' NÃO aparece em "
        "OnboardingApp.tsx. Esperado: o StepInfo deve renderizar um badge/"
        "label (ex: <span>Confirmado pela Receita</span>) próximo ao(s) "
        "campo(s) enriquecido(s) ou no header da seção de dados, "
        "visível somente quando `cnpjEnrichData` está populado — "
        "sinalizando ao usuário que a origem dos dados é a Receita "
        "Federal e dando confiança para prosseguir."
    )

    # ── (c) String literal 'Limpar dados da Receita' no source ───────────────
    assert "Limpar dados da Receita" in source, (
        "RED — A string literal 'Limpar dados da Receita' NÃO aparece em "
        "OnboardingApp.tsx. Esperado: o StepInfo deve ter um botão ou link "
        "rotulado 'Limpar dados da Receita' (ex: <button>Limpar dados da "
        "Receita</button>) com um handler onClick que faz "
        "`setCnpjEnrichData(null)` (e opcionalmente `setEmpresa('')` se o "
        "nome veio do auto-fill). Isso permite ao usuário descartar os "
        "dados retornados pela Receita e sobrescrever (override) "
        "manualmente caso estejam desatualizados ou errados."
    )

    # ── (d) String literal 'Dados da Receita Federal' no source ──────────────
    assert "Dados da Receita Federal" in source, (
        "RED — A string literal 'Dados da Receita Federal' NÃO aparece em "
        "OnboardingApp.tsx. Esperado: o JSX de StepInfo deve conter uma "
        "seção/bloco rotulado 'Dados da Receita Federal' (em um <h3>, "
        "<div className=...>, label, etc.) que exibe os campos retornados "
        "pela Edge Function (razao_social, cnpj formatado, cnae, "
        "cnae_descricao, situacao cadastral, uf, etc.) para o usuário "
        "conferir antes de prosseguir. Observação: este mesmo rótulo já é "
        "exigido por B-3 (AC-B3.4) — aqui ele é reafirmado como parte do "
        "contrato de UX de B-4."
    )
