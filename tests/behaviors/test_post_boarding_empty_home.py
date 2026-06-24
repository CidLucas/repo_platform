"""RED test for behavior — Post-boarding empty home page.

GOAL:
    After completing the onboarding flow (``FirstRunOverlay`` dismissed) but
    BEFORE the user has connected any data sources, the HomePage must show
    a friendly empty state — a welcome message plus a prominent CTA inviting
    the user to add their first connection. Today the HomePage renders the
    full panel grid even when ``hasNoData`` is true, so the user lands on
    an empty/broken-looking dashboard with no guidance.

BEHAVIOR:
    A user who just finished boarding and has no connected data must see an
    empty home page showing:

      (1) a friendly welcome message such as "Bem-vindo! Vamos começar"
      (2) a prominent button labeled "Adicionar primeira conexão" or
          "Conectar primeiro sistema" inviting them to add their first
          data connection.

AC (Acceptance Criteria):
    AC#1 — A component file ``PostBoardingEmptyState.tsx`` exists at
           ``apps/blu_v3/src/components/shared/PostBoardingEmptyState.tsx``
           with a default-exported function named ``PostBoardingEmptyState``.
    AC#2 — The component renders a welcome message containing the text
           ``"Bem-vindo"`` (so the user feels greeted after boarding).
    AC#3 — The component renders a button/link containing
           ``"Adicionar primeira conexão"`` OR ``"Conectar primeiro sistema"``
           (so the user has a clear next step to add their first source).
    AC#4 — ``HomePage.tsx`` imports ``PostBoardingEmptyState`` from the new
           component path AND renders it via JSX (e.g.
           ``<PostBoardingEmptyState ... />``) so the post-boarding empty
           state is actually wired into the home page.

DECISION:
    Estratégia: create new component + integrate into HomePage.
    Arquivo alvo: apps/blu_v3/src/components/shared/PostBoardingEmptyState.tsx
    Função alvo:  PostBoardingEmptyState (default export)

Anti-Goals (must NOT be violated):
    1. NÃO alterar o fluxo de onboarding existente (FirstRunOverlay,
       OnboardingApp) — o gate ``firstRun && hasNoData`` no AppShell
       permanece intocado.
    2. NÃO introduzir dependência de rede/DB/mock — este é um teste
       puro de inspeção de arquivos fonte.
    3. NÃO quebrar a renderização normal do HomePage para usuários COM
       dados — a renderização do empty state deve ser condicional
       (early-return / ternary guard), nunca substituir a UI atual
       incondicionalmente.

Estado atual (RED):
    * ``PostBoardingEmptyState.tsx`` NÃO existe em
      ``apps/blu_v3/src/components/shared/`` — AC#1 e AC#2 e AC#3 falham.
    * ``HomePage.tsx`` NÃO importa ``PostBoardingEmptyState`` e não
      renderiza ``<PostBoardingEmptyState>`` em lugar nenhum — AC#4
      falha.

    Quando a fase GREEN for implementada (criar o componente com
    default export + texto "Bem-vindo" + botão "Adicionar primeira
    conexão" + integrá-lo no HomePage com guard de "no data"), as
    quatro verificações passam.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Path resolution (root of repo) ───────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

COMPONENT_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "components"
    / "shared"
    / "PostBoardingEmptyState.tsx"
)

HOME_PAGE_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "HomePage.tsx"
)


# ── Override root conftest cleanup (pure file-based test) ────────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test is pure file inspection, no DB."""
    yield


# ── Source-level guard helpers ───────────────────────────────────────────


def _read_text(path: Path) -> str:
    assert path.exists(), f"File not found: {path}"
    return path.read_text(encoding="utf-8")


def _has_default_export_function(source: str, name: str) -> bool:
    """Detect ``export default function <name>(`` in a TSX source.

    Accepts either ``export default function Name(...)`` or
    ``export default function (...)`` (anonymous default function).
    The check requires the default-exported function to actually be
    named ``<name>`` (case-sensitive) so we don't accept unrelated
    default exports from the file.
    """
    pattern = rf"export\s+default\s+function\s+{re.escape(name)}\b"
    return re.search(pattern, source) is not None


# ── Tests (one per AC) ───────────────────────────────────────────────────


def test_ac1_post_boarding_empty_state_file_exists_with_default_export():
    """AC#1 — ``PostBoardingEmptyState.tsx`` must exist on disk at
    ``apps/blu_v3/src/components/shared/PostBoardingEmptyState.tsx`` and
    export a default function named ``PostBoardingEmptyState``.

    Without the file + default export, HomePage cannot import the
    component and the post-boarding empty state cannot be rendered.
    """
    if not COMPONENT_PATH.exists():
        # Surface the file-not-found as the dominant failure for AC#1.
        assert False, (
            "RED — AC#1 violated: source file not found: "
            f"{COMPONENT_PATH}. Expected: a new TSX component at "
            "`apps/blu_v3/src/components/shared/PostBoardingEmptyState.tsx` "
            "with `export default function PostBoardingEmptyState(...)` so "
            "HomePage can import it via "
            "`import PostBoardingEmptyState from "
            "'../../components/shared/PostBoardingEmptyState'`."
        )

    source = _read_text(COMPONENT_PATH)

    assert _has_default_export_function(source, "PostBoardingEmptyState"), (
        "RED — AC#1 violated: PostBoardingEmptyState.tsx exists but does NOT "
        "export a default function named `PostBoardingEmptyState`. Expected: "
        "`export default function PostBoardingEmptyState(...)` so HomePage "
        "can `import PostBoardingEmptyState from "
        "'../../components/shared/PostBoardingEmptyState'`. "
        f"File: {COMPONENT_PATH}"
    )


def test_ac2_post_boarding_empty_state_renders_welcome_message():
    """AC#2 — The component source must contain the literal text
    ``"Bem-vindo"`` so the user feels greeted after boarding.

    The check is intentionally permissive about the surrounding copy
    (any string literal containing the substring ``Bem-vindo`` counts,
    so "Bem-vindo!", "Bem-vindo de volta", "Bem-vindo(a) ao Blu" all
    pass) — but the word MUST be present in the rendered text.
    """
    if not COMPONENT_PATH.exists():
        assert False, (
            "RED — AC#2 violated: cannot verify welcome message because the "
            f"component file does not exist: {COMPONENT_PATH}. "
            "Expected: a JSX string literal such as "
            "`Bem-vindo! Vamos começar` rendered by "
            "PostBoardingEmptyState so the user feels greeted after boarding."
        )

    source = _read_text(COMPONENT_PATH)

    # Accept any of the common ways to spell the welcome word in a
    # JSX string literal — case-sensitive substring match against the
    # raw source. We require the substring `Bem-vindo` (with hyphen)
    # to be present; this is the PT-BR greeting expected in the spec.
    assert "Bem-vindo" in source, (
        "RED — AC#2 violated: PostBoardingEmptyState.tsx does NOT contain "
        "the welcome message 'Bem-vindo'. Expected: a JSX-rendered string "
        "such as `<h1>Bem-vindo! Vamos começar</h1>` or similar so the "
        "user feels greeted after completing the boarding flow. "
        f"File: {COMPONENT_PATH}"
    )


def test_ac3_post_boarding_empty_state_renders_add_connection_cta():
    """AC#3 — The component source must contain a button/link label with
    one of:

      * ``"Adicionar primeira conexão"`` (preferred)
      * ``"Conectar primeiro sistema"`` (alternate wording)

    so the user has a clear next step to add their first data source.
    """
    if not COMPONENT_PATH.exists():
        assert False, (
            "RED — AC#3 violated: cannot verify CTA because the component "
            f"file does not exist: {COMPONENT_PATH}. Expected: a "
            "button/link rendered by PostBoardingEmptyState whose visible "
            "label is `Adicionar primeira conexão` (or `Conectar primeiro "
            "sistema` as alternate wording) so the user can add their first "
            "data source from the post-boarding empty state."
        )

    source = _read_text(COMPONENT_PATH)

    has_add_label = "Adicionar primeira conexão" in source
    has_connect_label = "Conectar primeiro sistema" in source

    assert has_add_label or has_connect_label, (
        "RED — AC#3 violated: PostBoardingEmptyState.tsx does NOT render a "
        "call-to-action inviting the user to add their first data source. "
        "Expected: a button/link with one of the following labels — "
        "`Adicionar primeira conexão` (preferred) or `Conectar primeiro "
        "sistema` (alternate). The post-boarding empty state MUST surface "
        "this CTA prominently so the user knows the next step. "
        f"File: {COMPONENT_PATH}"
    )


def test_ac4_home_page_imports_and_renders_post_boarding_empty_state():
    """AC#4 — ``HomePage.tsx`` must import ``PostBoardingEmptyState`` from
    the new component path AND render it via JSX.

    Without the import + JSX usage, the new component is dead code:
    the post-boarding empty state is not shown to users, so the
    onboarding flow ends on the regular HomePage (which currently
    renders an empty/broken-looking dashboard with no guidance).
    """
    assert HOME_PAGE_PATH.exists(), (
        f"RED — HomePage not found at expected path: {HOME_PAGE_PATH}. "
        "Cannot verify AC#4 without the home page source."
    )

    source = _read_text(HOME_PAGE_PATH)

    # ── Import check ─────────────────────────────────────────────
    # Accept either a default import (the most idiomatic for a
    # default-exported component) or a named import — but the symbol
    # name must be `PostBoardingEmptyState` and the import path must
    # reference the new component file.
    default_import = re.search(
        r"import\s+PostBoardingEmptyState\b"
        r"[^;]*from\s*['\"][^'\"]*PostBoardingEmptyState[^'\"]*['\"]",
        source,
    )
    named_import = re.search(
        r"import\s*\{[^}]*\bPostBoardingEmptyState\b[^}]*\}"
        r"\s*from\s*['\"][^'\"]*PostBoardingEmptyState[^'\"]*['\"]",
        source,
    )
    has_import = default_import is not None or named_import is not None

    # ── JSX usage check ───────────────────────────────────────────
    jsx_usage = re.search(r"<\s*PostBoardingEmptyState\b", source)
    has_usage = jsx_usage is not None

    failures: list[str] = []
    if not has_import:
        failures.append(
            "HomePage.tsx does NOT `import PostBoardingEmptyState` from "
            "`../../components/shared/PostBoardingEmptyState`. Expected: "
            "`import PostBoardingEmptyState from "
            "'../../components/shared/PostBoardingEmptyState'` (or equivalent "
            "named import from the same module)."
        )
    if not has_usage:
        failures.append(
            "HomePage.tsx does NOT render `<PostBoardingEmptyState ... />` "
            "anywhere in its JSX. Expected: a JSX usage such as "
            "`<PostBoardingEmptyState onAddConnection={...} />` gated by a "
            "`hasNoData` / `data.length === 0` condition so the post-boarding "
            "empty state replaces (or overlays) the regular HomePage when "
            "the user has no connected data sources."
        )

    assert not failures, (
        "RED — AC#4 violated: HomePage.tsx does not integrate "
        "PostBoardingEmptyState. The component is dead code without the "
        "import + JSX usage. Details:\n\n  - "
        + "\n  - ".join(failures)
        + f"\n\nFile: {HOME_PAGE_PATH}"
    )
