"""RED test for behavior — Post-boarding empty home screen.

GOAL:
    After the user completes the onboarding flow (FirstRunOverlay dismissed)
    but BEFORE they have connected any data sources or interacted with any
    agent introductions, the HomePage must display an empty state — a friendly
    welcome message plus a prominent call-to-action — instead of the regular
    (empty/broken) dashboard.

BEHAVIOR:
    A user who just finished boarding and has no connections and no agent
    introductions must see an empty home page showing:

        (1) A welcome message such as "Bem-vindo! Vamos começar"
        (2) A prominent button labeled "Adicionar primeira conexão" that
            invites the user to add their first data connection.

    The empty state must be rendered conditionally: only when ``hasNoData``
    evaluates to true (no ``blu_has_data`` localStorage key is set for the
    current client). Once the user adds a connection, ``hasNoData`` flips to
    false and the regular HomePage renders instead.

AC (Acceptance Criteria):
    AC#1 — A component file ``PostBoardingEmptyState.tsx`` exists at
           ``apps/blu_v3/src/components/shared/PostBoardingEmptyState.tsx``
           with a default-exported function named ``PostBoardingEmptyState``.
    AC#2 — The component source contains a welcome message with the text
           ``"Bem-vindo"`` (any literal — e.g. ``Bem-vindo! Vamos começar``).
    AC#3 — The component source contains a CTA label with
           ``"Adicionar primeira conexão"`` so the user has a clear next step.
    AC#4 — ``HomePage.tsx`` imports ``PostBoardingEmptyState`` AND renders it
           conditionally via a guard such as
           ``if (hasNoData) return (<PostBoardingEmptyState ... />)``.

DECISION:
    Create a new component + integrate into HomePage with a conditional guard.
    Alvo: apps/blu_v3/src/components/shared/PostBoardingEmptyState.tsx

Estado atual (RED — component does not exist yet):
    * ``PostBoardingEmptyState.tsx`` NÃO existe — AC#1, AC#2, AC#3 falham.
    * ``HomePage.tsx`` NÃO importa ``PostBoardingEmptyState`` — AC#4 falha.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Path resolution (repo root) ───────────────────────────────────────────

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


# ── Override root conftest cleanup (pure file-based test) ─────────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — pure file inspection, no DB needed."""
    yield


# ── Source-level guard helpers ────────────────────────────────────────────


def _read_text(path: Path) -> str:
    assert path.exists(), f"File not found: {path}"
    return path.read_text(encoding="utf-8")


def _has_default_export_function(source: str, name: str) -> bool:
    """Detect ``export default function <name>(`` in TSX source."""
    pattern = rf"export\s+default\s+function\s+{re.escape(name)}\b"
    return re.search(pattern, source) is not None


# ── Single behavior test ──────────────────────────────────────────────────


def test_post_boarding_empty_home_behavior():
    """Validate the post-boarding empty home screen.

    When no connections or agent introductions are present, the HomePage
    must display an empty state with a welcome message and a CTA to add
    the first connection. This single test checks all four ACs to prevent
    silent regressions in the post-boarding experience.
    """
    failures: list[str] = []

    # ── AC#1: Component file exists with default export ──────────────
    if not COMPONENT_PATH.exists():
        failures.append(
            "AC#1 — RED: PostBoardingEmptyState.tsx not found at "
            f"{COMPONENT_PATH}. Expected: a new TSX component with "
            "`export default function PostBoardingEmptyState(...)`."
        )
    else:
        source = _read_text(COMPONENT_PATH)

        if not _has_default_export_function(source, "PostBoardingEmptyState"):
            failures.append(
                "AC#1 — RED: PostBoardingEmptyState.tsx exists but does NOT "
                "export a default function named `PostBoardingEmptyState`. "
                f"File: {COMPONENT_PATH}"
            )

        # ── AC#2: Welcome message ────────────────────────────────────
        if "Bem-vindo" not in source:
            failures.append(
                "AC#2 — RED: PostBoardingEmptyState.tsx does NOT contain "
                "the welcome message 'Bem-vindo'. Expected: a JSX string "
                "such as `Bem-vindo! Vamos começar` so the user feels "
                "greeted after boarding."
            )

        # ── AC#3: CTA label ──────────────────────────────────────────
        if "Adicionar primeira conexão" not in source:
            failures.append(
                "AC#3 — RED: PostBoardingEmptyState.tsx does NOT contain "
                "the CTA label 'Adicionar primeira conexão'. Expected: a "
                "button/link rendered by PostBoardingEmptyState whose "
                "visible label invites the user to add their first source."
            )

    # ── AC#4: HomePage imports AND conditionally renders the component ─
    if not HOME_PAGE_PATH.exists():
        failures.append(
            "AC#4 — RED: HomePage.tsx not found at expected path: "
            f"{HOME_PAGE_PATH}."
        )
    else:
        hp_source = _read_text(HOME_PAGE_PATH)

        # Check import: default or named import referencing PostBoardingEmptyState
        has_import = bool(
            re.search(
                r"import\s+(?:PostBoardingEmptyState|\{[^}]*\bPostBoardingEmptyState\b[^}]*\})"
                r"\s*from\s*['\"][^'\"]*PostBoardingEmptyState['\"]",
                hp_source,
            )
        )
        if not has_import:
            failures.append(
                "AC#4 — RED: HomePage.tsx does NOT `import PostBoardingEmptyState` "
                "from `../../components/shared/PostBoardingEmptyState`. "
                "The component is dead code without this import."
            )

        # Check conditional render: the component must be behind a hasNoData guard.
        # Expected pattern: `if (hasNoData) return ( ... <PostBoardingEmptyState ... )`
        has_conditional_render = bool(
            re.search(
                r"if\s*\(\s*hasNoData\s*\)",
                hp_source,
            )
        ) and bool(
            re.search(
                r"<\s*PostBoardingEmptyState\b",
                hp_source,
            )
        )
        if not has_conditional_render:
            failures.append(
                "AC#4 — RED: HomePage.tsx does NOT render "
                "<PostBoardingEmptyState> conditionally behind a "
                "`hasNoData` guard. Expected: "
                "`if (hasNoData) return (<PostBoardingEmptyState ... />)` "
                "so the empty state is only shown when the user has no "
                "connected data sources."
            )

    assert not failures, (
        "RED — Post-boarding empty home behavior not implemented. "
        f"{len(failures)} acceptance criteria violated:\n\n  - "
        + "\n  - ".join(failures)
    )
