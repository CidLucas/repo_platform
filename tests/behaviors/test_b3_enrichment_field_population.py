"""
RED test for Behavior B-3 — Enrichment Field Population no OnboardingApp.tsx.

GOAL:
    Quando o Step Empresa (StepInfo) recebe dados enriquecidos da Receita
    Federal via Edge Function `onboarding-cnpj-enrich` (acionada pelo
    onBlur de B-2), o componente deve:
        1. Persistir os dados em um state `cnpjEnrichData`.
        2. Derivar a vertical (setor) a partir do CNAE retornado pela
           Receita, usando uma função utilitária `deriveVerticalFromCnae`.
        3. Exibir uma seção "Dados da Receita Federal" com os campos
           retornados (razao_social, cnpj, cnae, etc.).
        4. Auto-preencher o campo "Nome da empresa" (state `empresa`) com
           `data.razao_social`.

    Arquivo alvo: apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx

BEHAVIOR:
    B-3 — Enrichment Field Population

    1. O componente StepInfo deve armazenar a resposta da Edge Function
       em `cnpjEnrichData` (useState tipado).
    2. Deve existir `function deriveVerticalFromCnae(` (ou arrow
       `const deriveVerticalFromCnae = `) que recebe um CNAE e devolve
       a chave de vertical (`food` | `retail` | ...).
    3. Deve existir no JSX uma seção rotulada "Dados da Receita Federal"
       que renderiza os campos enriquecidos (razao_social, cnpj formatado,
       cnae_descricao, etc.).
    4. Quando `cnpjEnrichData` chega, o nome da empresa deve ser
       auto-preenchido: `setEmpresa(data.razao_social)` (somente se
       `empresa.trim()` estiver vazio, para não sobrescrever o usuário).

AC (Acceptance Criteria):
    AC-B3.1 — String literal 'razao_social' existe no source
              (campo retornado pela Edge Function / usado para auto-fill)
    AC-B3.2 — Função `deriveVerticalFromCnae(` declarada no source
              (utilitário de classificação de CNAE → vertical)
    AC-B3.3 — State `cnpjEnrichData` (ou setter `setCnpjEnrichData`)
              existe no source (persistência da resposta)
    AC-B3.4 — String literal 'Dados da Receita Federal' existe no source
              (rótulo da seção de exibição dos dados enriquecidos)
    AC-B3.5 — `setEmpresa(data.razao_social)` (ou `setEmpresa(cnpjEnrichData.razao_social)`)
              existe no source (auto-preenchimento do nome da empresa)

DECISION:
    Estratégia: source-inspection via pytest
    Arquivo alvo: apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx
    Sem React, sem DOM, sem mocks, sem DB — apenas pathlib + pytest.

Anti-Goals (must NOT be violated):
    1. NÃO quebrar o onChange existente do input CNPJ (campo continua editável)
    2. NÃO remover `formatCnpj()` aplicado no `value` do input CNPJ
    3. NÃO importar libs externas (React, supabase, etc.) no teste
    4. NÃO usar mocks ou fixtures de DB — puro file inspection

Estado atual: RED — as seguintes features NÃO existem no código:
    - State `cnpjEnrichData` / setter `setCnpjEnrichData` não existem
    - Função `deriveVerticalFromCnae(` não existe
    - Seção "Dados da Receita Federal" não existe
    - Auto-preenchimento via `setEmpresa(data.razao_social)` não existe
    - O source hoje referencia `setEmpresa` apenas para `empresa` simples
      e para o auto-fill do website-intel (handleWebsiteBlur).
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


def test_b3_enrichment_field_population():
    """B-3 — StepInfo deve popular campos com dados da Receita Federal.

    Verifica 5 propriedades RED do source OnboardingApp.tsx:

        a) String literal 'razao_social' existe no source
           (campo retornado pela Edge Function `onboarding-cnpj-enrich`
           e usado no auto-fill do nome da empresa).
        b) Função `deriveVerticalFromCnae(` declarada no source
           (utilitário que converte CNAE numérico em chave de vertical).
        c) State `cnpjEnrichData` (ou setter `setCnpjEnrichData`)
           existe no source (persistência da resposta de enriquecimento).
        d) String literal 'Dados da Receita Federal' existe no source
           (rótulo da seção de exibição dos dados enriquecidos).
        e) `setEmpresa(data.razao_social)` existe no source
           (auto-preenchimento do campo "Nome da empresa" com a
           razão social retornada pela Receita Federal).

    Estado atual: TODOS os 5 asserts são RED porque o componente
    StepInfo não tem state de enriquecimento, não tem utilitário de
    CNAE, não tem seção de exibição dos dados da Receita e não faz
    auto-preenchimento a partir do payload da Edge Function.

    GREEN esperado: o Coder adiciona:
      - `const [cnpjEnrichData, setCnpjEnrichData] = useState<...>(null)`
        (AC-B3.3);
      - `function deriveVerticalFromCnae(cnae: string): string` (ou arrow)
        (AC-B3.2);
      - handler em `handleCnpjBlur` que faz
        `setCnpjEnrichData(data); if (!empresa.trim()) setEmpresa(data.razao_social)`
        (AC-B3.1 e AC-B3.5);
      - bloco JSX `<div>Dados da Receita Federal ...</div>` que renderiza
        razao_social, cnpj (formatado), cnae, etc. (AC-B3.4).
    """
    source = _read_onboarding()

    # ── Sanity: o arquivo precisa ter conteúdo ───────────────────────────────
    assert source, (
        "RED — OnboardingApp.tsx está vazio. "
        "Esperado: o arquivo existe e tem StepInfo com handler de CNPJ."
    )

    # ── (a) String literal 'razao_social' no source ──────────────────────────
    assert "razao_social" in source, (
        "RED — A string literal 'razao_social' NÃO aparece em OnboardingApp.tsx. "
        "Esperado: o campo razao_social retornado pela Edge Function "
        "`onboarding-cnpj-enrich` deve ser referenciado no source — "
        "tipicamente em `setEmpresa(data.razao_social)` para auto-preencher "
        "o nome da empresa, e/ou no JSX da seção 'Dados da Receita Federal' "
        "para exibir o valor."
    )

    # ── (b) Função deriveVerticalFromCnae( no source ────────────────────────
    assert "deriveVerticalFromCnae(" in source, (
        "RED — Não existe `deriveVerticalFromCnae(` em OnboardingApp.tsx. "
        "Esperado: declarar uma função (declaration ou arrow) com a "
        "assinatura `deriveVerticalFromCnae(cnae: string): string` que "
        "mapeia o CNAE numérico da Receita Federal para a chave de "
        "vertical do blu (ex: 'food' | 'retail' | 'services' | ...). "
        "Pode ser declarada no top-level do módulo ou dentro do StepInfo."
    )

    # ── (c) State cnpjEnrichData / setter setCnpjEnrichData ─────────────────
    assert "cnpjEnrichData" in source or "setCnpjEnrichData" in source, (
        "RED — Não existe o state `cnpjEnrichData` (nem o setter "
        "`setCnpjEnrichData`) em OnboardingApp.tsx. "
        "Esperado: declarar `const [cnpjEnrichData, setCnpjEnrichData] = "
        "useState<CnpjEnrichData | null>(null)` dentro de StepInfo, "
        "tipado com os campos retornados pela Edge Function "
        "(razao_social, cnpj, cnae, cnae_descricao, situacao, uf, etc.). "
        "O setter deve ser chamado dentro de `handleCnpjBlur` quando a "
        "Edge Function retorna dados."
    )

    # ── (d) String literal 'Dados da Receita Federal' no source ─────────────
    assert "Dados da Receita Federal" in source, (
        "RED — A string literal 'Dados da Receita Federal' NÃO aparece em "
        "OnboardingApp.tsx. Esperado: o JSX de StepInfo deve conter uma "
        "seção/bloco rotulado 'Dados da Receita Federal' (em um <h3>, "
        "<div className=...>, label, etc.) que exibe os campos retornados "
        "pela Edge Function (razao_social, cnpj formatado, cnae, "
        "situacao cadastral, etc.) para o usuário conferir antes de "
        "prosseguir."
    )

    # ── (e) setEmpresa(data.razao_social) — auto-preenchimento ──────────────
    assert "setEmpresa(data.razao_social)" in source, (
        "RED — Não existe `setEmpresa(data.razao_social)` em "
        "OnboardingApp.tsx. Esperado: após o invoke de "
        "`onboarding-cnpj-enrich` retornar dados, o handler deve "
        "auto-preencher o campo 'Nome da empresa' SOMENTE se ele ainda "
        "estiver vazio (`if (!empresa.trim()) setEmpresa(data.razao_social)`) "
        "— nunca sobrescrever o valor que o usuário já digitou. "
        "Observação: o source JÁ tem `setEmpresa(ctx.company_name)` no "
        "handler handleWebsiteBlur (auto-fill via website-intel), mas "
        "este AC exige explicitamente o auto-fill via razao_social da "
        "Receita Federal (outro caminho de enriquecimento)."
    )
