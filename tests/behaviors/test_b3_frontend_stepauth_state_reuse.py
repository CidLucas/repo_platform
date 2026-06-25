"""RED test for behavior B3 — Frontend StepAuth state reuse entre signups.

GOAL:
    Verificar via source-inspection que ``OnboardingApp.tsx`` (e o hook
    ``useOnboardingDraft``) NAO reusa estado entre signups de usuarios
    diferentes. Quando ``user.id`` muda (novo signup com email
    diferente), dois estados problematicos podem contaminar o fluxo:

      (a) o ref ``clientIdChecked`` (linha 1817) e' ``useRef(false)``
          sem nenhum reset no efeito da linha 1818-1859. Esse efeito
          roda com dep ``[user?.id, loading, step, navigate]`` e tem
          guarda ``if (clientIdChecked.current) return``. Resultado:
          no SEGUNDO signup, o efeito re-dispara (pois user.id mudou),
          MAS o ref ainda vale ``true`` do signup ANTERIOR, e a guarda
          early-return bloqueia o fetch de ``get_my_client_id`` para o
          novo usuario. O novo signup fica preso no step ``auth`` ou
          redireciona errado (redireciona para /app se o usuario
          anterior tinha onboarding_completed_at, OU fica sem
          provisionar tenant se o usuario anterior nao tinha).

      (b) o hook ``useOnboardingDraft(user?.email ?? '')`` (linha
          1790) inicializa o estado via ``useState(() => ...)``
          lendo o localStorage, MAS nao tem nenhum ``useEffect``
          que observe a mudanca de ``userEmail`` para re-ler
          localStorage ou resetar o estado em memoria. Resultado: o
          draft do usuario ANTERIOR (nome, empresa, cnpj, vertical,
          systems, etc.) continua exibido nos campos do StepInfo/
          StepData do NOVO usuario, ate que ``saveDraft`` seja
          chamado — o que nao acontece no step ``auth``.

    O bug e' de CONTAMINACAO DE SESSAO: o segundo signup herda o
    estado React/localStorage do primeiro. Em modos de uso real
    (logout, troca de conta, devtools) isso e' facil de reproduzir.

BEHAVIOR:
    B3 — Frontend StepAuth state reuse entre signups.
    Issue: o step de auth nao limpa refs e draft locais quando
    ``user.id`` muda, fazendo com que um novo signup herde o estado
    do signup anterior.

    Cadeia investigada:
        OnboardingApp.tsx
            ├─> useRef clientIdChecked                    [linha 1817]
            ├─> useEffect com dep [user?.id, ...]         [linha 1818]
            └─> useOnboardingDraft(user?.email ?? '')     [linha 1790]
                └─> useState(() => readLocalStorage)      [hook L68-75]
                    └─> useState SEM useEffect de reset    [hook L68-110]

AC (Acceptance Criteria):
    AC#1 — O ref ``clientIdChecked`` em ``OnboardingApp.tsx`` deve
           ser resetado (``clientIdChecked.current = false``) sempre
           que ``user?.id`` mudar. Hoje o ref e' declarado uma vez
           e nunca resetado; o efeito da linha 1818-1859 fica preso
           na guarda early-return ``if (clientIdChecked.current)
           return`` para qualquer usuario subsequente.

    AC#2 — O hook ``useOnboardingDraft`` deve detectar a mudanca de
           ``userEmail`` e resetar/reler o estado do draft
           (chamar ``setDraft(initialDraft(userEmail))`` ou reler
           o localStorage com a nova chave ``DRAFT_KEY(userEmail)``).
           Hoje o hook so le localStorage uma vez no initializer de
           ``useState``; trocas de usuario nao re-inicializam nada.

DECISAO:
    Estrategia: source_inspection (teste le arquivos .tsx/.ts como
    texto). Arquivos alvo:
        - apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx
        - apps/blu_v3/src/hooks/useOnboardingDraft.ts

Estado atual: RED — o teste falha porque o ref e' declarado uma unica
vez (sem reset por user.id) e o hook nao re-inicializa quando
``userEmail`` muda. Estes testes documentam as duas propriedades de
isolamento de estado entre signups e sinalizam o estado RED ate que
uma fase GREEN corrija os dois pontos.
"""

from __future__ import annotations

from pathlib import Path

import pytest


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

USE_DRAFT_HOOK_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "hooks"
    / "useOnboardingDraft.ts"
)


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest cleanup — pure source-inspection tests, no DB teardown."""
    yield


# ══════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════


def _extract_lines(source: str, start_marker: str, max_lines: int = 80) -> str:
    """Retorna ate ``max_lines`` linhas a partir da primeira ocorrencia
    de ``start_marker`` no source. Usado para inspecionar trechos
    curtos (refs, useEffects, declaracoes de hook) com contexto
    suficiente para a mensagem de pytest.fail.
    """
    idx = source.find(start_marker)
    if idx == -1:
        return ""
    lines = source[idx:].split("\n")[:max_lines]
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════
# AC#1 — clientIdChecked ref must be RESET when user.id changes
# ══════════════════════════════════════════════════════════════════════════


def test_b3_ac1_client_id_checked_resetado_quando_user_muda():
    """AC#1: o ref ``clientIdChecked`` declarado em
    ``OnboardingApp.tsx`` (linha 1817) deve ter seu ``.current``
    resetado para ``false`` sempre que ``user?.id`` mudar (novo
    signup). Hoje o ref e' um ``useRef(false)`` simples, declarado
    UMA vez e nunca mais tocado fora da atribuicao
    ``clientIdChecked.current = true`` da linha 1822 (dentro do
    proprio useEffect que ele guarda).

    O useEffect da linha 1818-1859 declara deps
    ``[user?.id, loading, step, navigate]``, entao ele RE-DISPARA
    quando ``user.id`` muda. Porem, na PRIMEIRA linha do corpo ha
    a guarda:

        if (clientIdChecked.current) return

    Como o ref vale ``true`` desde o primeiro signup, o segundo
    signup faz o efeito re-disparar, bater na guarda, e ABANDONAR
    o trabalho de consultar ``get_my_client_id`` para o novo
    usuario. O resultado: o novo signup ou (i) e' redirecionado
    para ``/app`` se o cliente anterior tinha
    ``onboarding_completed_at`` (mesmo sendo outro user) ou (ii)
    fica preso em ``step === 'auth'`` porque o efeito nunca chama
    ``setStep('info')`` para o novo usuario.

    Fix esperado (GREEN):
        - Trocar ``useRef(false)`` por algo re-keyed em user.id
          (ex.: ``useRef<Record<string, boolean>>({})`` + check
          ``clientIdChecked.current[user.id]``), OU
        - Adicionar um ``useEffect(() => { clientIdChecked.current
          = false }, [user?.id])`` separado, OU
        - Mover a guarda para dentro do callback
          (``get_my_client_id``) usando uma flag LOCAL ao
          callback (e nao um ref persistente).
    """
    assert ONBOARDING_APP_PATH.exists(), (
        f"Source file not found: {ONBOARDING_APP_PATH}. "
        "AC#1 requires inspecting OnboardingApp.tsx."
    )

    source = ONBOARDING_APP_PATH.read_text()

    assert "const clientIdChecked = useRef(false)" in source, (
        "AC#1 sanity violated: could not find "
        "`const clientIdChecked = useRef(false)` in OnboardingApp.tsx. "
        "AC#1 requires the ref to exist so we can verify the reset "
        "behavior."
    )

    ref_block = _extract_lines(source, "const clientIdChecked = useRef", max_lines=3)
    effect_block = _extract_lines(
        source, "clientIdChecked.current = true", max_lines=60
    )

    has_reset = (
        "clientIdChecked.current = false" in source
        and "clientIdChecked.current = true" in source
    )

    if has_reset:
        reset_idx = source.find("clientIdChecked.current = false")
        reset_line_no = source[:reset_idx].count("\n") + 1
        deps_idx = source.find("[user?.id, loading, step, navigate]")
        deps_line_no = source[:deps_idx].count("\n") + 1 if deps_idx != -1 else -1

        ctx_start = max(0, reset_idx - 200)
        ctx_end = min(len(source), reset_idx + 200)
        reset_context = source[ctx_start:ctx_end]
        is_in_user_id_effect = (
            "user?.id" in reset_context
            and ("useEffect" in reset_context or "useLayoutEffect" in reset_context)
        )

        if is_in_user_id_effect and reset_line_no > 0:
            return
        if reset_line_no > 0 and deps_line_no > 0 and reset_line_no < deps_line_no:
            return

    pytest.fail(
        "AC#1 RED: o ref clientIdChecked em OnboardingApp.tsx NAO e' "
        "resetado quando user.id muda.\n\n"
        "Causa raiz investigada: a declaracao na linha 1817 e'\n"
        "  const clientIdChecked = useRef(false)\n"
        "e' um useRef simples, criado UMA unica vez no mount do "
        "componente e nunca mais resetado. O useEffect da linha "
        "1818-1859, que depende de [user?.id, loading, step, "
        "navigate], abre com a guarda:\n"
        "  if (clientIdChecked.current) return\n\n"
        "Cenario problematico: o Usuario A faz signup, o efeito "
        "roda uma vez, clientIdChecked.current vira true. Em "
        "seguida, o Usuario B faz signup (signOut + signUp, troca "
        "de conta em devtools, etc.). O efeito RE-DISPARA porque "
        "user.id mudou, MAS a guarda early-return bloqueia tudo:\n"
        "  - se A tinha onboarding_completed_at: o Usuario B e' "
        "redirecionado para /app mesmo sendo conta nova\n"
        "  - caso contrario: o Usuario B fica preso em step === "
        "'auth' porque setStep('info') nunca e' chamado para ele\n\n"
        "Fix esperado (GREEN): resetar o ref sempre que user.id "
        "mudar. Opcoes validas:\n"
        "  1. Adicionar um useEffect dedicado:\n"
        "       useEffect(() => {\n"
        "         clientIdChecked.current = false\n"
        "       }, [user?.id])\n"
        "  2. Re-keyar o ref por user.id (Map<userId, boolean>)\n"
        "  3. Mover a flag para escopo LOCAL do callback "
        "supabase.rpc.\n\n"
        f"Trecho atual do ref (linha 1817):\n```\n{ref_block}\n```\n\n"
        f"Trecho atual do useEffect com a guarda (linhas 1818-):\n"
        f"```\n{effect_block}\n```\n"
    )


# ══════════════════════════════════════════════════════════════════════════
# AC#1 — Sanity check: clientIdChecked ref exists in OnboardingApp.tsx
# ══════════════════════════════════════════════════════════════════════════


def test_b3_ac1_sanity():
    """Sanity: confirma que ``OnboardingApp.tsx`` existe e contem a
    declaracao ``const clientIdChecked = useRef(false)``. Sem isso, o
    teste de AC#1 nao faria sentido (inspecionaria um arquivo sem o
    ref que estamos auditando).
    """
    assert ONBOARDING_APP_PATH.exists(), (
        f"Source file not found: {ONBOARDING_APP_PATH}. "
        "AC#1 sanity requires OnboardingApp.tsx to exist."
    )
    text = ONBOARDING_APP_PATH.read_text()
    assert "const clientIdChecked = useRef" in text, (
        "AC#1 sanity violated: OnboardingApp.tsx does not contain "
        "`const clientIdChecked = useRef`. Expected the ref to be "
        "declared as part of the step='auth' routing effect."
    )


# ══════════════════════════════════════════════════════════════════════════
# AC#2 — useOnboardingDraft must clear/reset draft when userEmail changes
# ══════════════════════════════════════════════════════════════════════════


def test_b3_ac2_use_draft_hook_reseta_quando_user_muda():
    """AC#2: o hook ``useOnboardingDraft(userEmail)`` em
    ``apps/blu_v3/src/hooks/useOnboardingDraft.ts`` deve detectar a
    mudanca de ``userEmail`` e resetar/reler o draft (estado React
    + localStorage com a nova chave ``DRAFT_KEY(userEmail)``).

    Hoje o hook (linhas 68-110) faz:
        const [draft, setDraft] = useState(() => {
            try {
                const raw = localStorage.getItem(DRAFT_KEY(userEmail))
                if (raw) return { ...initialDraft(userEmail), ...JSON.parse(raw) }
            } catch {}
            return initialDraft(userEmail)
        })

    O initializer de ``useState`` roda APENAS no primeiro mount do
    componente. Nao ha nenhum ``useEffect`` que dependa de
    ``userEmail`` para re-inicializar o draft ou limpar o estado
    anterior. Resultado: o draft do Usuario A continua em memoria
    (e em localStorage) mesmo apos o Usuario B fazer signUp. Os
    componentes StepInfo, StepData, StepMapping etc. continuam
    exibindo nome, empresa, cnpj, vertical, porte, systems e
    routines do Usuario A para o Usuario B ate que ``saveDraft``
    seja chamado de fato (o que nao acontece durante o step
    ``auth``).

    Alem disso, o hook retorna o draft IN-MEMORY diretamente, sem
    detectar a troca de usuario. Mesmo se o caller fizesse
    ``saveDraft({ email: novoEmail })``, o proximo render ainda
    mostraria o draft antigo ate o setState completar.

    Fix esperado (GREEN):
        - Adicionar um useEffect que observa userEmail e chama
          ``setDraft(initialDraft(newEmail))`` (ou re-le
          localStorage) sempre que userEmail muda. Alternativa:
          re-keyar o componente no caller (ex.: ``<OnboardingApp
          key={user?.id} />``) — mas isso e' workaround fora do
          hook.
        - Opcionalmente, limpar o localStorage do email ANTERIOR
          (anti-contaminacao entre sessoes, mesma logica de B-1).
    """
    assert USE_DRAFT_HOOK_PATH.exists(), (
        f"Source file not found: {USE_DRAFT_HOOK_PATH}. "
        "AC#2 requires inspecting useOnboardingDraft.ts."
    )

    source = USE_DRAFT_HOOK_PATH.read_text()

    assert "export function useOnboardingDraft" in source, (
        "AC#2 sanity violated: could not find "
        "`export function useOnboardingDraft` in useOnboardingDraft.ts. "
        "AC#2 requires the hook to exist as an exported function."
    )
    assert "DRAFT_KEY" in source, (
        "AC#2 sanity violated: useOnboardingDraft.ts does not contain "
        "`DRAFT_KEY`. Expected the hook to key localStorage by user "
        "email so we can detect cross-user contamination."
    )

    has_useremail_effect = (
        ("useEffect" in source or "useLayoutEffect" in source)
        and "userEmail" in source
        and ("setDraft" in source or "initialDraft" in source)
    )

    if has_useremail_effect:
        effect_idx = source.find("useEffect")
        if effect_idx == -1:
            effect_idx = source.find("useLayoutEffect")
        effect_block = source[effect_idx:effect_idx + 600]
        if "userEmail" in effect_block and "setDraft" in effect_block:
            return

    has_remount_pattern = (
        "key={user?.id}" in ONBOARDING_APP_PATH.read_text()
        or 'key={user?.id}' in ONBOARDING_APP_PATH.read_text()
        or 'key={user?.email}' in ONBOARDING_APP_PATH.read_text()
    )
    if has_remount_pattern:
        return

    init_block = _extract_lines(
        source, "export function useOnboardingDraft", max_lines=50
    )
    caller_block = _extract_lines(
        ONBOARDING_APP_PATH.read_text(),
        "const { draft, saveDraft, bootstrap } = useOnboardingDraft",
        max_lines=5,
    )

    pytest.fail(
        "AC#2 RED: o hook useOnboardingDraft NAO reseta o draft "
        "quando userEmail muda.\n\n"
        "Causa raiz investigada: o hook em "
        "apps/blu_v3/src/hooks/useOnboardingDraft.ts (linhas "
        "68-110) usa APENAS o initializer de useState para ler "
        "localStorage:\n"
        "  const [draft, setDraft] = useState(() => {\n"
        "    const raw = localStorage.getItem(DRAFT_KEY(userEmail))\n"
        "    ...\n"
        "  })\n\n"
        "Esse initializer roda UMA vez no mount do componente. "
        "Quando o caller em OnboardingApp.tsx (linha 1790) passa "
        "um userEmail diferente (ex.: Usuario B faz signUp apos "
        "Usuario A), o hook NAO detecta a troca: o draft do "
        "Usuario A continua em memoria e em localStorage.\n\n"
        "Sintoma: o StepInfo, StepData, StepMapping do Usuario B "
        "exibem nome, empresa, cnpj, vertical, porte, systems, "
        "routines e agents do Usuario A ate que saveDraft seja "
        "chamado (o que NAO acontece durante o step 'auth').\n\n"
        "Fix esperado (GREEN):\n"
        "  1. Adicionar useEffect que observa userEmail:\n"
        "       useEffect(() => {\n"
        "         setDraft(initialDraft(userEmail))\n"
        "       }, [userEmail])\n"
        "  OU re-keyar o componente pelo caller (OnboardingApp) "
        "com <OnboardingApp key={user?.id} /> — workaround "
        "externo ao hook.\n\n"
        f"Trecho atual do hook (linha 68-):\n```\n{init_block}\n"
        f"```\n\n"
        f"Trecho atual da chamada no caller (linha 1790):\n"
        f"```\n{caller_block}\n```\n"
    )


# ══════════════════════════════════════════════════════════════════════════
# AC#2 — Sanity check: hook file exists with the expected exports
# ══════════════════════════════════════════════════════════════════════════


def test_b3_ac2_sanity():
    """Sanity: confirma que ``useOnboardingDraft.ts`` existe e expoe
    a funcao ``useOnboardingDraft`` e a constante ``DRAFT_KEY``
    (diretamente ou via o body do hook). Sem isso, o teste de AC#2
    nao faria sentido (inspecionaria um arquivo sem o hook).
    """
    assert USE_DRAFT_HOOK_PATH.exists(), (
        f"Source file not found: {USE_DRAFT_HOOK_PATH}. "
        "AC#2 sanity requires useOnboardingDraft.ts to exist."
    )
    text = USE_DRAFT_HOOK_PATH.read_text()
    assert "useOnboardingDraft" in text, (
        "AC#2 sanity violated: useOnboardingDraft.ts does not "
        "contain `useOnboardingDraft`. Expected the hook to be "
        "defined and exported from this file."
    )
    assert "userEmail" in text, (
        "AC#2 sanity violated: useOnboardingDraft.ts does not "
        "reference `userEmail` anywhere. Expected the hook to "
        "accept userEmail as its parameter so we can audit the "
        "reset behavior on user change."
    )
    assert "localStorage" in text, (
        "AC#2 sanity violated: useOnboardingDraft.ts does not "
        "reference `localStorage`. Expected the hook to persist "
        "the draft to localStorage so cross-user contamination "
        "can be detected and cleaned up."
    )
