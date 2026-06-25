"""
RED test for Behavior B-5 — Error Handling & Rate Limiting no OnboardingApp.tsx.

GOAL:
    O async handleCnpjBlur do StepInfo em
    apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx (declarado em B-2)
    deve tratar erros da Edge Function `onboarding-cnpj-enrich` de forma
    silenciosa e mostrar mensagem sutil quando o backend sinalizar
    rate limit, sem nunca bloquear o usuário com alert/modal/setError
    intrusivo.

BEHAVIOR:
    B-5 — Error Handling & Rate Limiting

    1. Antes de chamar supabase.functions.invoke, handleCnpjBlur valida
       que o CNPJ tem 14 dígitos (cnpj.length !== 14) e não chama a
       Edge Function para CNPJs inválidos.
    2. Falhas da API (timeout, 404, 429, erro de rede) são engolidas
       silenciosamente num catch — sem setError, sem alert, sem modal.
       O formulário permanece editável.
    3. O finally sempre desliga o loading via setEnrichingCnpj(false).
    4. Quando a Edge Function retorna { error: "rate_limit" }, o
       componente exibe o texto "Servico temporariamente indisponivel.
       Tente novamente em alguns instantes." abaixo do campo CNPJ como
       mensagem sutil (sem interromper o fluxo).

AC (Acceptance Criteria):
    AC-1 — CNPJ inválido (< 14 dígitos) NÃO chama a Edge Function
    AC-2 — Erro silencioso: try/catch/finally sem setError, com
           setEnrichingCnpj(false) no finally
    AC-3 — Rate limit: data?.error === "rate_limit" exibe texto sutil
           "Servico temporariamente indisponivel. Tente novamente em
           alguns instantes." abaixo do campo CNPJ

DECISION:
    Estratégia: source-inspection via pytest
    Arquivo alvo: apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx
    Padrões procurados:
        - cnpj.length !== 14 (guard pré-invoke)
        - try/catch/finally com setEnrichingCnpj(false) no finally
        - data?.error === "rate_limit" (detecção de rate limit)
        - string literal "Servico temporariamente indisponivel"

Anti-Goals (must NOT be violated):
    1. NÃO usar alert(), confirm() ou modal de erro para falhas de API
    2. NÃO chamar setError para erros da Edge Function (silencioso)
    3. NÃO bloquear o input CNPJ com disabled durante o enriquecimento
    4. NÃO importar libs/React no teste — pytest + pathlib apenas

Estado atual: RED — nenhuma das features B-5 existe no código:
    - NÃO existe validação `cnpj.length !== 14` (handleCnpjBlur não existe)
    - NÃO existe try/catch/finally em handleCnpjBlur
    - NÃO existe padrão `data?.error === "rate_limit"`
    - NÃO existe string literal "Servico temporariamente indisponivel"
    - NÃO existe setEnrichingCnpj(false) no finally
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


def test_b5_error_handling_rate_limiting():
    """B-5 — handleCnpjBlur deve tratar erros e rate limit de forma silenciosa.

    Verifica 5 propriedades RED do source OnboardingApp.tsx:

        a) AC-1: pattern `cnpj.length !== 14` existe no source
                 (CNPJ inválido não chama a Edge Function)
        b) AC-2: existe `setEnrichingCnpj(false)` no source
                 (garante reset do loading no finally)
        c) AC-2: existe pattern `} catch (` no source (tratamento de erro)
        d) AC-3: pattern `data?.error === "rate_limit"` existe no source
                 (detecção de rate limit da Edge Function)
        e) AC-3: string literal "Servico temporariamente indisponivel"
                 existe no source (mensagem sutil ao usuário)

    Estado atual: TODOS os 5 asserts são RED porque handleCnpjBlur
    ainda não foi implementado (B-2) e nenhum dos padrões de B-5
    existe no código.

    GREEN esperado: o Coder implementa handleCnpjBlur com guard
    `if (cnpj.length !== 14) return;` antes do invoke, envolve o
    invoke em try { ... } catch { /* silencioso */ } finally {
    setEnrichingCnpj(false); } e checa `if (data?.error === "rate_limit")`
    para exibir o texto "Servico temporariamente indisponivel. Tente
    novamente em alguns instantes." abaixo do campo CNPJ.
    """
    source = _read_onboarding()

    # ── (a) AC-1: cnpj.length !== 14 (guard de validação) ───────────────────
    assert "cnpj.length !== 14" in source, (
        "RED — AC-1: NÃO existe validação `cnpj.length !== 14` em "
        "OnboardingApp.tsx. "
        "Esperado: dentro de handleCnpjBlur, antes de chamar "
        "supabase.functions.invoke, validar `if (cnpj.length !== 14) return;` "
        "(ou equivalente) para garantir que apenas CNPJs com exatamente "
        "14 dígitos disparam a Edge Function. CNPJs parciais (em digitação) "
        "não devem gerar chamadas de API."
    )

    # ── (b) AC-2: setEnrichingCnpj(false) (reset de loading no finally) ──────
    assert "setEnrichingCnpj(false)" in source, (
        "RED — AC-2: NÃO existe `setEnrichingCnpj(false)` em OnboardingApp.tsx. "
        "Esperado: dentro de handleCnpjBlur, em um bloco finally, chamar "
        "setEnrichingCnpj(false) para garantir que o loading é desligado "
        "mesmo se a Edge Function falhar (timeout, 404, 429, erro de rede). "
        "Sem isso, o campo CNPJ ficaria preso em estado de loading."
    )

    # ── (c) AC-2: } catch ( tratamento de erro silencioso ────────────────────
    assert "} catch (" in source, (
        "RED — AC-2: NÃO existe bloco `} catch (` em handleCnpjBlur no "
        "OnboardingApp.tsx. "
        "Esperado: envolver a chamada supabase.functions.invoke em "
        "try { ... } catch (err) { /* silencioso */ } finally { ... } "
        "para que qualquer falha de API (timeout, 404, 429, erro de rede) "
        "seja engolida sem exibir alert, modal ou setError intrusivo. "
        "O formulário deve permanecer editável após a falha."
    )

    # ── (d) AC-3: data?.error === "rate_limit" (detecção de rate limit) ────
    assert 'data?.error === "rate_limit"' in source, (
        "RED — AC-3: NÃO existe pattern `data?.error === \"rate_limit\"` em "
        "OnboardingApp.tsx. "
        "Esperado: após o await supabase.functions.invoke(...), checar "
        "`if (data?.error === \"rate_limit\")` para detectar quando a "
        "Edge Function sinaliza rate limit (HTTP 429 traduzido), e nesse "
        "caso exibir a mensagem sutil ao usuário."
    )

    # ── (e) AC-3: string literal "Servico temporariamente indisponivel" ──────
    assert "Servico temporariamente indisponivel" in source, (
        "RED — AC-3: NÃO existe a string literal \"Servico temporariamente "
        "indisponivel\" em OnboardingApp.tsx. "
        "Esperado: quando data?.error === \"rate_limit\", renderizar o texto "
        "\"Servico temporariamente indisponivel. Tente novamente em alguns "
        "instantes.\" abaixo do campo CNPJ como texto sutil (ex: text-xs "
        "text-muted-foreground), sem interromper o fluxo do formulário."
    )
