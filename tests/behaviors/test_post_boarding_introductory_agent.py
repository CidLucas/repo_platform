"""RED behavior test for Post-boarding — Introductory Agent.

GOAL:
    After the user dismisses the ``FirstRunOverlay`` (onboarding complete)
    but BEFORE the blu agent has introduced itself, the HomePage must show
    an "introductory agent" — a chat-style card that presents the agent
    (its name, role, and a quick list of capabilities) so the user knows
    *who* is "watching over" the office and *what* the agent can do on
    their behalf.

    This is the natural companion of ``PostBoardingEmptyState`` (covered by
    ``test_post_boarding_empty_home.py``): the empty-state focuses on
    prompting the user to add a data connection; the introductory agent
    focuses on establishing the agent's identity and trust.

BEHAVIOR:
    A user who just finished boarding and has not yet acknowledged the
    agent's introduction must see, on the home page, a friendly
    self-presentation card containing:

        (1) The agent's name — ``"Agente blu"`` (or any of the
            equivalent self-introductions: ``"sou o blu"``,
            ``"sou seu agente"``, ``"meu nome é blu"``).
        (2) A short role / capability description that mentions one
            of the verbs the agent can do — e.g. ``"Posso te ajudar"``,
            ``"Posso monitorar"``, or ``"Posso cuidar"``.
        (3) A dismiss control (a ``<button>`` element) so the user can
            hide the card and return to the regular HomePage.

    The card must be rendered conditionally: only while the user has not
    yet acknowledged the introduction.  Once dismissed, the regular
    HomePage renders instead.

AC (Acceptance Criteria):
    AC#1 — A component file ``PostBoardingIntroductoryAgent.tsx`` exists
           at
           ``apps/blu_v3/src/components/onboarding/PostBoardingIntroductoryAgent.tsx``
           with a default-exported function named
           ``PostBoardingIntroductoryAgent``.
    AC#2 — The component source contains the agent's name — any of:
           ``"Agente blu"``, ``"sou o blu"``, ``"sou seu agente"``,
           ``"meu nome é blu"`` (or ``"meu nome e blu"``).
    AC#3 — The component source contains a capability / role
           description that uses one of the verbs the agent performs:
           ``"Posso te ajudar"``, ``"Posso monitorar"``, or
           ``"Posso cuidar"``.
    AC#4 — The component renders a dismiss control — i.e. the source
           contains a ``<button`` element so the user has a way to
           close the card.
    AC#5 — ``HomePage.tsx`` imports ``PostBoardingIntroductoryAgent``
           AND renders it conditionally via a guard such as
           ``if (hasNoAgentIntro) return (<PostBoardingIntroductoryAgent ... />)``.

DECISION:
    Estratégia: create (new chat-style component + integrate into
                       HomePage with a conditional guard).
    Alvo: apps/blu_v3/src/components/onboarding/PostBoardingIntroductoryAgent.tsx
    Render: HomePage.tsx (com guard `hasNoAgentIntro` / `showIntroAgent` /
            equivalente)

Estado atual (RED — component does not exist yet):
    * ``PostBoardingIntroductoryAgent.tsx`` NÃO existe — AC#1, AC#2,
      AC#3, AC#4 falham.
    * ``HomePage.tsx`` NÃO importa ``PostBoardingIntroductoryAgent``
      — AC#5 falha.
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
    / "onboarding"
    / "PostBoardingIntroductoryAgent.tsx"
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


def _has_any_literal(source: str, literals: tuple[str, ...]) -> str | None:
    """Return the first literal from ``literals`` that appears in ``source``.

    Returns ``None`` if none of them appear.  The literal is matched as a
    plain substring (case-sensitive) — TSX/JSX text is rendered verbatim
    from the source, so a substring match is sufficient.
    """
    for lit in literals:
        if lit in source:
            return lit
    return None


# ── Single behavior test ──────────────────────────────────────────────────


def test_post_boarding_introductory_agent_behavior():
    """Validate the post-boarding introductory agent card.

    When the user has just finished the FirstRunOverlay and has not yet
    seen the agent's self-presentation, the HomePage must render an
    introductory card that:

        * names the agent (``Agente blu`` / ``sou o blu`` / etc.);
        * states a capability (``Posso te ajudar`` / ``Posso monitorar`` /
          ``Posso cuidar``);
        * exposes a dismiss button;
        * is gated by a conditional guard so the regular HomePage
          replaces it once the introduction is acknowledged.

    This single test aggregates all five ACs to prevent silent
    regressions in the post-boarding introduction experience.
    """
    failures: list[str] = []

    # ── AC#1: Component file exists with default export ──────────────
    if not COMPONENT_PATH.exists():
        failures.append(
            "AC#1 — RED: PostBoardingIntroductoryAgent.tsx not found at "
            f"{COMPONENT_PATH}. Expected: a new TSX component with "
            "`export default function PostBoardingIntroductoryAgent(...)`."
        )
    else:
        source = _read_text(COMPONENT_PATH)

        if not _has_default_export_function(source, "PostBoardingIntroductoryAgent"):
            failures.append(
                "AC#1 — RED: PostBoardingIntroductoryAgent.tsx exists but does NOT "
                "export a default function named `PostBoardingIntroductoryAgent`. "
                f"File: {COMPONENT_PATH}"
            )

        # ── AC#2: Agent name self-introduction ─────────────────────
        name_match = _has_any_literal(
            source,
            (
                "Agente blu",
                "sou o blu",
                "sou seu agente",
                "meu nome é blu",
                "meu nome e blu",
            ),
        )
        if name_match is None:
            failures.append(
                "AC#2 — RED: PostBoardingIntroductoryAgent.tsx does NOT contain "
                "the agent's name. Expected one of the literals: 'Agente blu', "
                "'sou o blu', 'sou seu agente', 'meu nome é blu' (or "
                "'meu nome e blu'). The user must know who is greeting them "
                "after boarding."
            )

        # ── AC#3: Capability / role description ────────────────────
        capability_match = _has_any_literal(
            source,
            (
                "Posso te ajudar",
                "Posso monitorar",
                "Posso cuidar",
            ),
        )
        if capability_match is None:
            failures.append(
                "AC#3 — RED: PostBoardingIntroductoryAgent.tsx does NOT contain "
                "a capability / role description. Expected one of: "
                "'Posso te ajudar', 'Posso monitorar', or 'Posso cuidar' — "
                "a short statement of what the agent can do for the user so "
                "they trust the system to act on their behalf."
            )

        # ── AC#4: Dismiss control (a <button> element) ──────────────
        has_button = bool(re.search(r"<\s*button\b", source))
        if not has_button:
            failures.append(
                "AC#4 — RED: PostBoardingIntroductoryAgent.tsx does NOT render a "
                "dismiss control. Expected: a `<button>...</button>` element "
                "that lets the user hide the introductory card and return "
                "to the regular HomePage. Without a dismiss affordance the "
                "user is stuck on the post-boarding screen."
            )

    # ── AC#5: HomePage imports AND conditionally renders the component ─
    if not HOME_PAGE_PATH.exists():
        failures.append(
            "AC#5 — RED: HomePage.tsx not found at expected path: "
            f"{HOME_PAGE_PATH}."
        )
    else:
        hp_source = _read_text(HOME_PAGE_PATH)

        # Check import: default or named import referencing PostBoardingIntroductoryAgent
        has_import = bool(
            re.search(
                r"import\s+(?:PostBoardingIntroductoryAgent|\{[^}]*\bPostBoardingIntroductoryAgent\b[^}]*\})"
                r"\s*from\s*['\"][^'\"]*PostBoardingIntroductoryAgent['\"]",
                hp_source,
            )
        )
        if not has_import:
            failures.append(
                "AC#5 — RED: HomePage.tsx does NOT `import PostBoardingIntroductoryAgent` "
                "from `../../components/onboarding/PostBoardingIntroductoryAgent`. "
                "The component is dead code without this import."
            )

        # Check conditional render: the component must be behind a
        # guard (e.g. `hasNoAgentIntro`, `showIntroAgent`, `!hasSeenAgentIntro`).
        # We accept any guard variable whose name mentions "intro" so the
        # implementation has freedom in naming.
        has_guard = bool(
            re.search(
                r"if\s*\(\s*!?\s*\w*[Ii]ntro\w*\s*\)",
                hp_source,
            )
        ) or bool(
            re.search(
                r"if\s*\(\s*!?\s*\w*[Ii]ntrodu\w*\s*\)",
                hp_source,
            )
        )
        has_render = bool(
            re.search(
                r"<\s*PostBoardingIntroductoryAgent\b",
                hp_source,
            )
        )
        if not (has_guard and has_render):
            missing: list[str] = []
            if not has_guard:
                missing.append(
                    "no `if (<introGuard>)` guard (variable name must contain "
                    "'intro' / 'introduc')"
                )
            if not has_render:
                missing.append(
                    "no `<PostBoardingIntroductoryAgent .../>` render"
                )
            failures.append(
                "AC#5 — RED: HomePage.tsx does NOT render "
                "<PostBoardingIntroductoryAgent> conditionally. "
                f"Missing: {'; '.join(missing)}. "
                "Expected a pattern such as "
                "`if (hasNoAgentIntro) return (<PostBoardingIntroductoryAgent ... />)` "
                "so the introductory card is only shown while the user has "
                "not yet acknowledged the agent's introduction."
            )

    assert not failures, (
        "RED — Post-boarding introductory agent behavior not implemented. "
        f"{len(failures)} acceptance criteria violated:\n\n  - "
        + "\n  - ".join(failures)
    )
