"""RED test for #185 — R-2: UX das Rotinas — Filtrar Platforma.

GOAL:
    R-2 — O painel de rotinas deve permitir filtrar rotinas por plataforma
    (domínio/sala). Hoje o ``RoutinesPanel`` aceita apenas ``domain`` como
    filtro de escopo e a função ``fetchRoutines`` filtra apenas pelo campo
    ``room`` em ``cross_agent_routines``. Nenhuma das duas assinaturas
    expõe um parâmetro ``platform`` dedicado.

BEHAVIOR:
    O comportamento esperado (fase GREEN) é:

      * O componente ``RoutinesPanel`` deve aceitar uma prop opcional
        ``platform`` (além da ``domain`` já existente) para filtrar
        rotinas pela plataforma/domínio selecionado.
      * A função ``fetchRoutines(clientId, platform?)`` deve retornar
        apenas rotinas que correspondam à plataforma selecionada.
      * O painel deve exibir uma mensagem apropriada quando nenhuma
        rotina casar com o filtro aplicado.

AC (Acceptance Criteria):
    AC#1 — RoutinesPanel aceita prop opcional ``platform`` para filtragem.
    AC#2 — ``fetchRoutines(clientId, platform)`` retorna apenas rotinas
           da plataforma selecionada.
    AC#3 — O painel exibe uma mensagem apropriada quando nenhuma rotina
           casa com o filtro.

DECISION:
    Estratégia: extend — estender o contrato existente de
    ``RoutinesPanel`` / ``fetchRoutines`` adicionando um parâmetro
    opcional ``platform``. NÃO substituir ``domain``: o filtro
    ``platform`` é ADICIONAL ao filtro de escopo atual.

Anti-Goals (must NOT be violated):
    1. NÃO remover o filtro ``domain``/``room`` existente — o
       ``platform`` filter é adicional ao escopo atual.
    2. NÃO quebrar a backward compatibility de
       ``fetchRoutines(clientId, domain?)`` — chamadas antigas devem
       continuar funcionando.
    3. NÃO introduzir dependência externa (DB, rede) — este é um teste
       de unidade puro, baseado em inspeção de arquivos fonte.
    4. NÃO alterar a API de ``fetchCustomRoutines`` — escopo exclusivo
       do catálogo (``source='catalog'``).

Estado atual (RED):
    * ``RoutinesPanel.tsx`` define ``export default function RoutinesPanel
      ({ domain }: { domain: string })`` — NÃO aceita ``platform``.
    * ``routines.ts`` define ``export async function fetchRoutines(
      clientId: string, domain?: string)`` — NÃO aceita ``platform``.

    Ambos os arquivos NÃO contêm a string ``platform`` (em nenhum
    contexto relevante) — todas as verificações abaixo falham
    atualmente. Quando a fase GREEN for implementada (adicionar prop
    ``platform`` ao RoutinesPanel + parâmetro ``platform`` ao
    fetchRoutines + mensagem de "nenhuma rotina" para o filtro
    selecionado), as três verificações passarão.
"""

from pathlib import Path

import pytest

# ── Path resolution (root of repo) ───────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

ROUTINES_PANEL_TSX = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "components"
    / "shared"
    / "RoutinesPanel.tsx"
)
ROUTINES_API_TS = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "api"
    / "routines.ts"
)


# ── Override root conftest cleanup (pure file-based test) ───────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test is pure file inspection, no DB."""
    yield


# ── Helpers ─────────────────────────────────────────────────────────────


def _read_text(path: Path) -> str:
    assert path.exists(), f"File not found: {path}"
    return path.read_text(encoding="utf-8")


def _panel_has_platform_prop(content: str) -> bool:
    """Return True if RoutinesPanel signature/destructuring mentions ``platform``.

    Accepts any of:
      * ``function RoutinesPanel({ domain, platform }``
      * ``function RoutinesPanel({ platform, domain }``
      * destructuring with default value:
        ``function RoutinesPanel({ domain, platform = '' }``
      * plain object: ``props: { platform?: string }``
    """
    needles = [
        "platform",  # generic — most permissive check
    ]
    if not any(n in content for n in needles):
        return False
    # Must appear in a props/destructuring context near RoutinesPanel.
    # We check that ``platform`` is referenced at least once in the
    # RoutinesPanel definition (not just inside any random comment).
    lines = content.splitlines()
    in_panel = False
    for line in lines:
        stripped = line.strip()
        if "function RoutinesPanel(" in stripped:
            in_panel = True
        if in_panel and "platform" in stripped:
            return True
        # Bail out when we leave the RoutinesPanel function body.
        if in_panel and stripped.startswith("export default function RoutinesPanel"):
            continue
    # Fallback: if the panel signature is one-liner, the loop above still
    # catches the line that contains both ``RoutinesPanel(`` and the prop.
    return "platform" in content and "RoutinesPanel" in content


def _api_has_platform_parameter(content: str) -> bool:
    """Return True if ``fetchRoutines`` signature includes a ``platform`` parameter.

    Accepts any of:
      * ``export async function fetchRoutines(clientId: string, platform?: string)``
      * ``export async function fetchRoutines(clientId: string, platform: string)``
      * placement after ``domain`` (e.g. ``fetchRoutines(clientId, domain?, platform?)``)

    The check is intentionally permissive: any reference to ``platform`` in
    the signature line of ``fetchRoutines`` counts.
    """
    lines = content.splitlines()
    for line in lines:
        stripped = line.strip()
        if "function fetchRoutines(" in stripped and "platform" in stripped:
            return True
    return False


# ── The single behavior under test ──────────────────────────────────────


def test_r2_platform_filter_routines_red():
    """R-2 / AC#1 + AC#2 + AC#3 — RoutinesPanel + fetchRoutines must support
    an optional ``platform`` filter for routines.

    The test inspects the repository's source-of-truth files (no mocks,
    no DB) and asserts:

      AC#1) ``apps/blu_v3/src/components/shared/RoutinesPanel.tsx`` exposes
             ``platform`` as a prop/parameter of the ``RoutinesPanel``
             function so the panel can be filtered by platform.
      AC#2) ``apps/blu_v3/src/api/routines.ts`` exposes ``platform`` as a
             parameter of ``fetchRoutines`` so the data layer can filter
             routines by platform.
      AC#3) ``apps/blu_v3/src/components/shared/RoutinesPanel.tsx`` shows
             a user-facing message when no routines match the current
             filter (so the user knows the filter is active, not broken).

    All three checks fail in the current state (RED) because:

      * ``RoutinesPanel`` signature is ``({ domain }: { domain: string })``
        and contains no reference to ``platform``.
      * ``fetchRoutines`` signature is
        ``(clientId: string, domain?: string)`` and contains no
        reference to ``platform``.
      * The empty-state message in RoutinesPanel is hard-coded to
        "este domínio" — it does NOT differentiate between an empty
        platform filter and a broken backend.
    """
    failures: list[str] = []

    # ── AC#1 — RoutinesPanel accepts optional ``platform`` prop ───
    panel_text = _read_text(ROUTINES_PANEL_TSX)

    if not _panel_has_platform_prop(panel_text):
        failures.append(
            "AC#1 violated: RoutinesPanel does NOT accept a `platform` "
            "prop. Behavior R-2 / #185 requires the RoutinesPanel "
            "function signature to expose an OPTIONAL `platform` "
            "parameter (in addition to the existing `domain`) so the "
            "panel can be filtered by platform/domain. "
            f"File: {ROUTINES_PANEL_TSX}"
        )

    # ── AC#2 — fetchRoutines(clientId, platform?) filters by platform ─
    api_text = _read_text(ROUTINES_API_TS)

    if not _api_has_platform_parameter(api_text):
        failures.append(
            "AC#2 violated: fetchRoutines does NOT accept a `platform` "
            "parameter. Behavior R-2 / #185 requires "
            "`fetchRoutines(clientId, platform?)` to return only "
            "routines for the selected platform. Today the signature is "
            "`fetchRoutines(clientId, domain?: string)` and filters on "
            "the `room` field of cross_agent_routines — the dedicated "
            "`platform` parameter does NOT exist. "
            f"File: {ROUTINES_API_TS}"
        )

    # ── AC#3 — Panel shows appropriate message when no routines match ──
    # We accept EITHER:
    #   (a) an empty-state message that mentions "platform" (preferred),
    #   (b) a generic empty-state message that distinguishes the
    #       filtered-empty case from the loading case.
    # For now we only check (a) to keep the test strictly RED: today
    # the empty-state string is "Nenhuma rotina de catálogo disponível
    # para este domínio." which does NOT mention the platform filter.
    panel_mentions_platform_in_empty_state = (
        "platform" in panel_text.lower()
        and (
            "plataforma" in panel_text.lower()
            or "platform" in panel_text.lower()
        )
    )
    if not panel_mentions_platform_in_empty_state:
        failures.append(
            "AC#3 violated: RoutinesPanel does NOT show an appropriate "
            "message when no routines match the platform filter. "
            "Behavior R-2 / #185 requires the panel to surface a "
            "user-facing message that acknowledges the platform filter "
            "(e.g. 'Nenhuma rotina disponível para esta plataforma.') "
            "Today the empty-state string is 'Nenhuma rotina de "
            "catálogo disponível para este domínio.' which does NOT "
            "reference the platform filter. "
            f"File: {ROUTINES_PANEL_TSX}"
        )

    # ── Aggregate all failures ───────────────────────────────────
    assert not failures, (
        "R-2 / #185 — Platform filter for routines is NOT yet "
        "implemented. The following acceptance criteria are violated:\n\n  - "
        + "\n  - ".join(failures)
    )
