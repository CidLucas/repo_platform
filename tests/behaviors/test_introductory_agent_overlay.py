"""RED test for behavior — Introductory agent (FirstRunOverlay) public contract.

GOAL:
    Validate the public contract of the three source files that make up
    the introductory onboarding agent so the guided first-run flow stays
    wired into the app shell:

        * ``apps/blu_v3/src/components/onboarding/FirstRunOverlay.tsx``
              — the chat-card overlay that greets the user, asks a few
                short questions, and lets the user open the connections
                modal mid-flow.
        * ``apps/blu_v3/src/store/appStore.ts``
              — the Zustand store slice that holds the ``firstRun`` flag
                plus the ``initFirstRun`` / ``dismissFirstRun`` actions.
        * ``apps/blu_v3/src/components/shell/AppShell.tsx``
              — the shell that reads the store flag, gates the overlay
                on the ``firstRun && hasNoData`` condition, and feeds the
                ``onOpenConnections`` callback that re-opens the existing
                ``ConnectionsModal``.

    The introductory agent is the FIRST thing a brand-new user sees after
    sign-up. If any of these three files loses its public contract, the
    onboarding flow silently regresses to "screen behind a transparent
    backdrop" or to "no greeting at all". This test pins the contract
    by source-level inspection (no JSX rendered, no DB touched).

BEHAVIOR:
    When a user lands on the shell for the first time (no data ingested
    yet) the store's ``firstRun`` flag is ``true`` and ``AppShell``
    mounts the ``FirstRunOverlay``. The overlay greets the user, walks
    them through 3-4 short questions (solo/sócio/equipe, which area to
    monitor, connect now or later) and, on the "connect now" pill,
    triggers the ``onOpenConnections`` callback so ``AppShell`` re-opens
    the existing ``ConnectionsModal``. When the user reaches the final
    "ready" step or clicks the close button, the overlay calls
    ``dismissFirstRun(clientId)`` which (a) sets the localStorage marker
    ``blu_first_run_done:<clientId> = '1'`` and (b) flips the store flag
    to ``false``, hiding the overlay on subsequent visits.

AC (Acceptance Criteria):
    AC#1 — ``FirstRunOverlay.tsx`` exists on disk at
            ``apps/blu_v3/src/components/onboarding/FirstRunOverlay.tsx``.
    AC#2 — ``FirstRunOverlay.tsx`` has a default-exported function named
            ``FirstRunOverlay`` (so AppShell can
            ``import FirstRunOverlay from '../onboarding/FirstRunOverlay'``).
    AC#3 — ``FirstRunOverlay.tsx`` reads the store via
            ``useAppStore`` (specifically the ``dismissFirstRun`` action).
    AC#4 — ``FirstRunOverlay.tsx`` declares the
            ``onOpenConnections`` callback prop (so it can hand the
            "connect now" pill back to AppShell).
    AC#5 — ``appStore.ts`` declares a ``firstRun`` boolean in the
            ``AppState`` interface and initializes it to a truthy value.
    AC#6 — ``appStore.ts`` implements an ``initFirstRun(clientId)``
            action that reads the ``blu_first_run_done:<clientId>``
            localStorage marker.
    AC#7 — ``appStore.ts`` implements a ``dismissFirstRun(clientId)``
            action that writes the ``blu_first_run_done:<clientId>``
            localStorage marker and flips ``firstRun`` to ``false``.
    AC#8 — ``AppShell.tsx`` imports ``FirstRunOverlay`` from
            ``../onboarding/FirstRunOverlay`` AND imports the store via
            ``useAppStore``.
    AC#9 — ``AppShell.tsx`` reads the store's ``firstRun`` flag and the
            ``initFirstRun`` action.
    AC#10 — ``AppShell.tsx`` renders ``<FirstRunOverlay ... />`` in its
            JSX with an ``onOpenConnections`` handler that opens the
            connections modal (or, at minimum, the existing
            ``ConnectionsModal`` is mounted alongside it).

DECISION:
    Estratégia: extend (validate the existing public contract of three
                 files — no code changes required for the GREEN pass).
    Arquivos alvo:
        - apps/blu_v3/src/components/onboarding/FirstRunOverlay.tsx
        - apps/blu_v3/src/store/appStore.ts
        - apps/blu_v3/src/components/shell/AppShell.tsx

Anti-Goals (must NOT be violated):
    1. NÃO alterar a UX do overlay (chat card, pills, spotlight) — o
       teste valida o contrato público, não a copy ou a animação.
    2. NÃO renomear ``firstRun`` / ``initFirstRun`` / ``dismissFirstRun``
       — eles são referenciados por AppShell, FirstRunOverlay e
       ConnectionsModal; trocar o nome quebra o fluxo inteiro.
    3. NÃO mudar a chave de localStorage ``blu_first_run_done:<clientId>``
       — outros fluxos (post-boarding empty state, onboarding ETL)
       dependem dela.
    4. NÃO importar componentes em runtime — este é um teste puro de
       inspeção de arquivos fonte (.tsx/.ts), mesmo padrão de
       ``test_config_tab_ux.py`` e ``test_post_boarding_empty_home.py``.
    5. NÃO introduzir dependência de DB / Supabase / mock — o teste
       nunca toca rede, usa só ``pathlib`` + ``re``.

Estado atual: GREEN — os três arquivos já implementam o contrato
esperado. Este teste serve de guard: se algum refactor futuro renomear
o componente, trocar a action da store, remover o gate de renderização
no AppShell ou trocar a chave de localStorage, o teste vira RED
imediatamente.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Paths ─────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

OVERLAY_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "components"
    / "onboarding"
    / "FirstRunOverlay.tsx"
)

STORE_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "store"
    / "appStore.ts"
)

APP_SHELL_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "components"
    / "shell"
    / "AppShell.tsx"
)


# ── Source-level guard helpers ────────────────────────────────────────────


def _read_source(path: Path) -> str:
    assert path.exists(), f"Source file not found: {path}"
    return path.read_text(encoding="utf-8")


def _has_default_export_function_named(source: str, name: str) -> bool:
    """Detect `export default function <name>(` in a TSX/TS source.

    Accepts only the named variant (`export default function FirstRunOverlay`)
    so we don't accept unrelated default exports (e.g. an internal helper
    accidentally hoisted to default).
    """
    pattern = rf"export\s+default\s+function\s+{re.escape(name)}\b"
    return re.search(pattern, source) is not None


def _declares_interface_member(source: str, member_name: str) -> bool:
    """Detect a member declaration inside the AppState interface in appStore.

    Accepts:
        firstRun: boolean
        firstRun:    boolean
        firstRun?: boolean
        firstRun : boolean
    on a single line (the interface is small enough that we don't need
    multi-line matching).
    """
    pattern = rf"^\s*{re.escape(member_name)}\s*\??\s*:\s*\w"
    return re.search(pattern, source, re.MULTILINE) is not None


def _action_call_pattern(action_name: str) -> re.Pattern[str]:
    """Build a regex that matches a call to a store action.

    Looks for ``actionName(`` preceded by either ``.`` (method call on
    a selector result) or whitespace/start-of-line (bare call). This is
    permissive enough to catch both styles commonly used in the codebase:

        store.dismissFirstRun(clientId)
        dismissFirstRun(clientId)
    """
    return re.compile(rf"(?:\.|\s){re.escape(action_name)}\s*\(")


def _interface_member_with_type(source: str, member_name: str) -> bool:
    """Like `_declares_interface_member` but also accepts `firstRun: any`
    (the store uses `boolean`; tests stay loose in case someone widens
    the type).
    """
    return _declares_interface_member(source, member_name)


# ── AC#1 — File exists ────────────────────────────────────────────────────


def test_ac1_first_run_overlay_file_exists():
    """AC#1 — ``FirstRunOverlay.tsx`` must exist on disk at
    ``apps/blu_v3/src/components/onboarding/FirstRunOverlay.tsx``.

    Without the file, AppShell cannot import the overlay and the
    introductory agent is gone (no greeting, no pills, no flow).
    """
    assert OVERLAY_PATH.exists(), (
        "RED — AC#1 violated: source file not found: "
        f"{OVERLAY_PATH}. Expected: a TSX component at "
        "`apps/blu_v3/src/components/onboarding/FirstRunOverlay.tsx` "
        "so AppShell can `import FirstRunOverlay from "
        "'../onboarding/FirstRunOverlay'`."
    )


# ── AC#2 — Default export of `FirstRunOverlay` ────────────────────────────


def test_ac2_first_run_overlay_has_default_export():
    """AC#2 — ``FirstRunOverlay.tsx`` must have a default-exported
    function named ``FirstRunOverlay``.

    The default export is the contract that AppShell relies on
    (`import FirstRunOverlay from '../onboarding/FirstRunOverlay'`).
    A regression to a named export breaks the import silently.
    """
    assert OVERLAY_PATH.exists(), (
        f"RED — AC#2 violated: source file not found: {OVERLAY_PATH}. "
        "Cannot verify the default export."
    )
    source = _read_source(OVERLAY_PATH)

    assert _has_default_export_function_named(source, "FirstRunOverlay"), (
        "RED — AC#2 violated: FirstRunOverlay.tsx does NOT export a "
        "default function named `FirstRunOverlay`. Expected: "
        "`export default function FirstRunOverlay(...)` so AppShell "
        "can `import FirstRunOverlay from "
        "'../onboarding/FirstRunOverlay'`. Without a default export, "
        "the overlay never mounts and the introductory agent flow is "
        "broken. "
        f"File: {OVERLAY_PATH}"
    )


# ── AC#3 — Overlay reads the store ───────────────────────────────────────


def test_ac3_first_run_overlay_reads_store():
    """AC#3 — The overlay source must import ``useAppStore`` from the
    store and call ``dismissFirstRun`` to close the flow.

    The store import is what allows the overlay to flip the
    ``firstRun`` flag (and persist the localStorage marker) when the
    user reaches the final step or clicks the close button.
    """
    assert OVERLAY_PATH.exists(), (
        f"RED — AC#3 violated: source file not found: {OVERLAY_PATH}."
    )
    source = _read_source(OVERLAY_PATH)

    imports_use_app_store = re.search(
        r"import\s*\{[^}]*\buseAppStore\b[^}]*\}\s*from\s*['\"][^'\"]*store/appStore[^'\"]*['\"]",
        source,
    )
    # Accept both styles:
    #   * `s.dismissFirstRun(...)` — method call straight on the selector
    #   * `dismissFirstRun(...)`   — bare call after destructuring via
    #                               `const dismissFirstRun = useAppStore(s => s.dismissFirstRun)`
    # The trailing `(` disambiguates the bare call from the selector
    # `useAppStore(s => s.dismissFirstRun)` (where the function name is
    # followed by `)`, not `(`).
    calls_dismiss = re.search(
        r"(?:\.|\s)\bdismissFirstRun\s*\(",
        source,
    ) or re.search(
        r"\bdismissFirstRun\s*\(",
        source,
    )

    failures: list[str] = []
    if imports_use_app_store is None:
        failures.append(
            "FirstRunOverlay.tsx does NOT import `useAppStore` from the "
            "store (`../../store/appStore` or `../../store/appStore.ts`). "
            "Expected: `import { useAppStore } from '../../store/appStore'` "
            "so the overlay can read the `firstRun` flag and call the "
            "`dismissFirstRun` action."
        )
    if calls_dismiss is None:
        failures.append(
            "FirstRunOverlay.tsx does NOT call `.dismissFirstRun(`. "
            "Expected: a `dismissFirstRun(clientId)` call wired to the "
            "overlay's close button / final-step CTA so the store flips "
            "`firstRun` to `false` and persists the "
            "`blu_first_run_done:<clientId>` localStorage marker."
        )

    assert not failures, (
        "RED — AC#3 violated: the overlay is not wired to the store. "
        "Details:\n\n  - " + "\n  - ".join(failures) + f"\n\nFile: {OVERLAY_PATH}"
    )


# ── AC#4 — Overlay declares `onOpenConnections` callback prop ─────────────


def test_ac4_first_run_overlay_declares_on_open_connections_prop():
    """AC#4 — The overlay must declare the ``onOpenConnections`` callback
    prop in its `Props` interface and call it from inside a handler.

    The "connect now" pill in the overlay hands control back to AppShell
    via this prop, so AppShell can re-open the existing ConnectionsModal
    without duplicating it.
    """
    assert OVERLAY_PATH.exists(), (
        f"RED — AC#4 violated: source file not found: {OVERLAY_PATH}."
    )
    source = _read_source(OVERLAY_PATH)

    declares_prop = re.search(
        r"onOpenConnections\??\s*:\s*\(",
        source,
    )
    invokes_prop = re.search(
        r"onOpenConnections\s*\??\.\?\.?\s*\(",
        source,
    ) or re.search(
        r"onOpenConnections\?\?\(\)\s*=>",
        source,
    ) or re.search(
        r"\bonOpenConnections\b\s*\?\.\s*\(",
        source,
    )

    failures: list[str] = []
    if declares_prop is None:
        failures.append(
            "FirstRunOverlay.tsx does NOT declare `onOpenConnections` "
            "in its Props interface. Expected: a `onOpenConnections?: () => void` "
            "(or non-optional) prop so AppShell can re-open the "
            "ConnectionsModal when the user picks the "
            "'Sim, conectar agora' pill."
        )
    if invokes_prop is None:
        failures.append(
            "FirstRunOverlay.tsx declares `onOpenConnections` but does "
            "NOT actually invoke it. Expected: a call such as "
            "`onOpenConnections?.()` inside the pill handler for the "
            "connect-now step, so the click propagates back to AppShell."
        )

    assert not failures, (
        "RED — AC#4 violated: the overlay cannot hand the user back to "
        "AppShell. Details:\n\n  - "
        + "\n  - ".join(failures)
        + f"\n\nFile: {OVERLAY_PATH}"
    )


# ── AC#5 — `firstRun` is in the store's AppState ──────────────────────────


def test_ac5_appstore_declares_first_run_state():
    """AC#5 — ``appStore.ts`` must declare a ``firstRun`` member in the
    AppState interface AND initialize it in the store factory to a
    truthy value (so the overlay shows up before initFirstRun runs).

    The default ``firstRun: true`` is what guarantees a brand-new
    clientId gets greeted on the very first render, even before the
    scoped localStorage marker is read.
    """
    assert STORE_PATH.exists(), (
        f"RED — AC#5 violated: source file not found: {STORE_PATH}."
    )
    source = _read_source(STORE_PATH)

    has_interface_member = _interface_member_with_type(source, "firstRun")
    has_initializer = re.search(
        r"firstRun\s*:\s*true\b",
        source,
    )

    failures: list[str] = []
    if not has_interface_member:
        failures.append(
            "appStore.ts does NOT declare a `firstRun` member in the "
            "AppState interface. Expected: `firstRun: boolean` inside "
            "`export interface AppState { ... }` so subscribers can read "
            "the flag via `useAppStore(s => s.firstRun)`."
        )
    if has_initializer is None:
        failures.append(
            "appStore.ts declares `firstRun` in the interface but does "
            "NOT initialize it to `true` in the store factory. Expected: "
            "`firstRun: true` in the initial state object so the "
            "introductory agent appears on the very first render of a "
            "brand-new client."
        )

    assert not failures, (
        "RED — AC#5 violated: the store's firstRun state is incomplete. "
        "Details:\n\n  - "
        + "\n  - ".join(failures)
        + f"\n\nFile: {STORE_PATH}"
    )


# ── AC#6 — `initFirstRun` action reads the localStorage marker ────────────


def test_ac6_appstore_implements_init_first_run():
    """AC#6 — ``appStore.ts`` must define an ``initFirstRun(clientId)``
    action that reads the ``blu_first_run_done:<clientId>`` localStorage
    marker and flips the ``firstRun`` flag accordingly.

    Without this action, a returning user would be re-greeted on every
    visit; without the localStorage read, the per-client "have we
    already onboarded this client?" check is broken.
    """
    assert STORE_PATH.exists(), (
        f"RED — AC#6 violated: source file not found: {STORE_PATH}."
    )
    source = _read_source(STORE_PATH)

    declares_init = re.search(
        r"\binitFirstRun\s*\(\s*clientId\s*:\s*string\s*\)",
        source,
    )
    reads_marker = re.search(
        r"blu_first_run_done\s*:",
        source,
    )

    failures: list[str] = []
    if declares_init is None:
        failures.append(
            "appStore.ts does NOT declare an `initFirstRun(clientId: "
            "string)` action. Expected: "
            "`initFirstRun(clientId: string) { ... }` in the store "
            "factory body so AppShell can call it once clientId is "
            "known and the scoped localStorage marker can be checked."
        )
    if reads_marker is None:
        failures.append(
            "appStore.ts declares `initFirstRun` but does NOT read the "
            "`blu_first_run_done:<clientId>` localStorage marker. "
            "Expected: `localStorage.getItem(`blu_first_run_done:${clientId}`)` "
            "inside the action so returning users skip the overlay."
        )

    assert not failures, (
        "RED — AC#6 violated: the initFirstRun action is incomplete. "
        "Details:\n\n  - "
        + "\n  - ".join(failures)
        + f"\n\nFile: {STORE_PATH}"
    )


# ── AC#7 — `dismissFirstRun` writes the marker and flips the flag ────────


def test_ac7_appstore_implements_dismiss_first_run():
    """AC#7 — ``appStore.ts`` must define a ``dismissFirstRun(clientId)``
    action that BOTH writes the ``blu_first_run_done:<clientId>``
    localStorage marker AND sets ``firstRun`` to ``false``.

    The action is the only way the overlay can signal "I'm done" back
    to the store; the localStorage write is the durable part, the
    `firstRun: false` set is the in-memory part.
    """
    assert STORE_PATH.exists(), (
        f"RED — AC#7 violated: source file not found: {STORE_PATH}."
    )
    source = _read_source(STORE_PATH)

    declares_dismiss = re.search(
        r"\bdismissFirstRun\s*\(\s*clientId\s*:\s*string\s*\)",
        source,
    )
    writes_marker = re.search(
        r"localStorage\.setItem\s*\(\s*[`'\"]blu_first_run_done\s*:\s*\$\{?clientId\}?[`'\"]",
        source,
    ) or re.search(
        r"localStorage\.setItem\s*\(\s*`blu_first_run_done:\${clientId}`",
        source,
    )
    flips_flag = re.search(
        r"firstRun\s*:\s*false\b",
        source,
    )

    failures: list[str] = []
    if declares_dismiss is None:
        failures.append(
            "appStore.ts does NOT declare a `dismissFirstRun(clientId: "
            "string)` action. Expected: "
            "`dismissFirstRun(clientId: string) { ... }` in the store "
            "factory body so the overlay can call it from its close "
            "button / final-step CTA."
        )
    if writes_marker is None:
        failures.append(
            "appStore.ts declares `dismissFirstRun` but does NOT write the "
            "`blu_first_run_done:<clientId>` localStorage marker. Expected: "
            "`localStorage.setItem(`blu_first_run_done:${clientId}`, '1')` "
            "inside the action so the dismissal persists across sessions."
        )
    if flips_flag is None:
        failures.append(
            "appStore.ts declares `dismissFirstRun` but does NOT set "
            "`firstRun` to `false` in the store state. Expected: "
            "`set({ firstRun: false })` (or `state.firstRun = false`) "
            "inside the action so the overlay is removed immediately."
        )

    assert not failures, (
        "RED — AC#7 violated: the dismissFirstRun action is incomplete. "
        "Details:\n\n  - "
        + "\n  - ".join(failures)
        + f"\n\nFile: {STORE_PATH}"
    )


# ── AC#8 — AppShell imports FirstRunOverlay + useAppStore ──────────────────


def test_ac8_appshell_imports_overlay_and_store():
    """AC#8 — ``AppShell.tsx`` must import ``FirstRunOverlay`` from the
    onboarding directory AND import the store via ``useAppStore``.

    Without the overlay import, AppShell cannot mount the introductory
    agent. Without the store import, it cannot read the ``firstRun``
    flag to know whether to show it.
    """
    assert APP_SHELL_PATH.exists(), (
        f"RED — AC#8 violated: source file not found: {APP_SHELL_PATH}."
    )
    source = _read_source(APP_SHELL_PATH)

    imports_overlay = re.search(
        r"import\s+FirstRunOverlay\b[^;]*from\s*['\"][^'\"]*onboarding/FirstRunOverlay[^'\"]*['\"]",
        source,
    )
    imports_store = re.search(
        r"import\s*\{[^}]*\buseAppStore\b[^}]*\}\s*from",
        source,
    )

    failures: list[str] = []
    if imports_overlay is None:
        failures.append(
            "AppShell.tsx does NOT import `FirstRunOverlay` from the "
            "onboarding directory. Expected: "
            "`import FirstRunOverlay from '../onboarding/FirstRunOverlay'` "
            "so the introductory agent can be mounted."
        )
    if imports_store is None:
        failures.append(
            "AppShell.tsx does NOT import `useAppStore` from the store. "
            "Expected: `import { useAppStore } from '../../store/appStore'` "
            "so the shell can read the `firstRun` flag."
        )

    assert not failures, (
        "RED — AC#8 violated: AppShell is missing the required imports. "
        "Details:\n\n  - "
        + "\n  - ".join(failures)
        + f"\n\nFile: {APP_SHELL_PATH}"
    )


# ── AC#9 — AppShell reads firstRun + calls initFirstRun ────────────────────


def test_ac9_appshell_reads_first_run_and_inits():
    """AC#9 — ``AppShell.tsx`` must read the store's ``firstRun`` flag
    via ``useAppStore`` AND call ``initFirstRun``.

    Reading `firstRun` gates the overlay; calling `initFirstRun` is what
    checks the per-client localStorage marker to skip the overlay for
    returning users.
    """
    assert APP_SHELL_PATH.exists(), (
        f"RED — AC#9 violated: source file not found: {APP_SHELL_PATH}."
    )
    source = _read_source(APP_SHELL_PATH)

    reads_first_run = re.search(
        r"\bfirstRun\b",
        source,
    )
    calls_init = re.search(
        r"\binitFirstRun\s*\(",
        source,
    )

    failures: list[str] = []
    if reads_first_run is None:
        failures.append(
            "AppShell.tsx does NOT reference `firstRun`. Expected: "
            "`const firstRun = useAppStore(s => s.firstRun)` or "
            "`const { firstRun } = useAppStore()` (or desugared equivalent) "
            "so the shell knows whether to show the introductory agent."
        )
    if calls_init is None:
        failures.append(
            "AppShell.tsx does NOT call `initFirstRun(clientId)`. Expected: "
            "a call to `initFirstRun(clientId)` (or `store.initFirstRun(clientId)`) "
            "inside a `useEffect` or similar initializer so the per-client "
            "localStorage marker is checked on mount."
        )

    assert not failures, (
        "RED — AC#9 violated: AppShell does not interact with firstRun state. "
        "Details:\n\n  - "
        + "\n  - ".join(failures)
        + f"\n\nFile: {APP_SHELL_PATH}"
    )


# ── AC#10 — AppShell renders <FirstRunOverlay> with onOpenConnections ───────


def test_ac10_appshell_renders_overlay_with_on_open_connections():
    """AC#10 — ``AppShell.tsx`` must render ``<FirstRunOverlay ... />``
    in its JSX with an ``onOpenConnections`` handler that opens the
    connections modal (or the ``ConnectionsModal`` is mounted alongside
    it in the same conditional block).

    The overlay needs the handler so the "connect now" pill works;
    without it the user can't add connections during the introductory
    flow.
    """
    assert APP_SHELL_PATH.exists(), (
        f"RED — AC#10 violated: source file not found: {APP_SHELL_PATH}."
    )
    source = _read_source(APP_SHELL_PATH)

    renders_overlay = re.search(
        r"<\s*FirstRunOverlay\b",
        source,
    )
    has_on_open = re.search(
        r"onOpenConnections",
        source,
    )
    renders_modal = re.search(
        r"<\s*ConnectionsModal\b",
        source,
    )

    failures: list[str] = []
    if renders_overlay is None:
        failures.append(
            "AppShell.tsx does NOT render `<FirstRunOverlay ... />` in its "
            "JSX. Expected: a JSX usage such as "
            "`<FirstRunOverlay onOpenConnections={...} />` gated by the "
            "`firstRun && hasNoData` condition."
        )
    if has_on_open is None:
        failures.append(
            "AppShell.tsx renders `<FirstRunOverlay ... />` but does NOT "
            "pass a `onOpenConnections` handler. Expected: "
            "`<FirstRunOverlay onOpenConnections={() => setConnectionsOpen(true)} />` "
            "so the overlay can re-open the ConnectionsModal from the "
            "'connect now' pill."
        )
    if renders_modal is None and has_on_open is None:
        failures.append(
            "AppShell.tsx has neither an `onOpenConnections` handler on the "
            "overlay nor a `<ConnectionsModal>` mount — the user cannot "
            "open the connections flow from the introductory agent."
        )

    assert not failures, (
        "RED — AC#10 violated: the overlay is not wired to the connections flow. "
        "Details:\n\n  - "
        + "\n  - ".join(failures)
        + f"\n\nFile: {APP_SHELL_PATH}"
    )
