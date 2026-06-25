"""RED test for behavior — AnalyticsPanel migration to Compras, Financeiro and Clientes.

GOAL:
    Every room page that displays an analytics summary at the panel bottom
    (ComprasRoom, FinanceiroRoom, ClientesRoom) currently hand-rolls the
    `anl-card` / `anl-hd` / `anl-nums` / `anl-kpi` block and the
    `(['30d', '90d', '1y'] as const).map(...)` period selector inline. This
    test REDs the migration of those three rooms to a single shared
    component — `AnalyticsPanel` — that owns the title, the pinned KPIs
    shown in the collapsed header, the period selector, and the open /
    closed body.

    The shared `AnalyticsPanel` component (which does NOT exist yet) is
    expected to live at:
        apps/blu_v3/src/components/shared/AnalyticsPanel.tsx
    and to expose:
        export interface AnalyticsPanelProps {
            title: string
            kpis: Array<{ label: string; value: string | number; color?: string }>
            period: string
            onPeriodChange: (p: string) => void
            children?: React.ReactNode
            defaultOpen?: boolean
        }
        export default function AnalyticsPanel(props: AnalyticsPanelProps) { ... }

BEHAVIOR:
    For every room page that renders the bottom analytics block, the
    rendering code must:

        1. Import the default export of `AnalyticsPanel` from
           `../../components/shared/AnalyticsPanel`.
        2. Render `<AnalyticsPanel title={...} kpis={[...]} period={...}
           onPeriodChange={...}>` (with `children` for the expanded body
           and optional `defaultOpen` if needed) instead of the inline
           `anl-card` / `anl-hd` / `anl-nums` / `anl-kpi` / period-pill
           block.
        3. Pass the same `setAnalyticsPeriod` setter the inline block
           uses, so clicking a period pill reaches the room's query
           invalidation (the period selector becomes part of
           AnalyticsPanel, not duplicated inline).

AC (Acceptance Criteria):
    AC#1 — `AnalyticsPanel.tsx` exists at
           `apps/blu_v3/src/components/shared/AnalyticsPanel.tsx` and
           exports `default function AnalyticsPanel`.
    AC#2 — `AnalyticsPanel.tsx` exports an `AnalyticsPanelProps`
           interface with exactly the six props: `title`, `kpis`,
           `period`, `onPeriodChange`, `children?`, `defaultOpen?`.
    AC#3 — `ComprasRoom.tsx` imports the default `AnalyticsPanel` and
           renders `<AnalyticsPanel ... />` in place of the inline
           `anl-card` / `anl-hd` / `anl-nums` / `anl-kpi` block.
    AC#4 — `FinanceiroRoom.tsx` imports the default `AnalyticsPanel` and
           renders `<AnalyticsPanel ... />` in place of the inline
           `anl-hd` / `anl-nums` / `anl-kpi` block (Financeiro has no
           `anl-card` wrapper — only the header / nums / kpi triple).
    AC#5 — `ClientesRoom.tsx` imports the default `AnalyticsPanel` and
           renders `<AnalyticsPanel ... />` in place of the inline
           `anl-card` / `anl-hd` / `anl-nums` / `anl-kpi` block.
    AC#6 — The period selector (`30d` / `90d` / `1y`) is rendered
           uniformly by `AnalyticsPanel` in all three rooms; the rooms
           MUST NOT duplicate the
           `(['30d', '90d', '1y'] as const).map(p => <span ... pill ...>)`
           pattern inline.

DECISION:
    Estratégia: extend — a NEW shared component is introduced at
                `apps/blu_v3/src/components/shared/AnalyticsPanel.tsx`
                and the three room pages delegate to it. The rooms
                still own their data (`supply`, `fin`, `commercial`,
                `kpiQ`, `commercialQ`, `supplyQ`); `AnalyticsPanel`
                owns the chrome (title, header KPIs, period selector,
                open/close, body container).
    Arquivos alvo:
        - apps/blu_v3/src/components/shared/AnalyticsPanel.tsx (NEW)
        - apps/blu_v3/src/pages/app/ComprasRoom.tsx
        - apps/blu_v3/src/pages/app/FinanceiroRoom.tsx
        - apps/blu_v3/src/pages/app/ClientesRoom.tsx
    Função alvo:  the analytics block at the bottom of each room's
                 panel (the `anl-card` / `anl-hd` / `anl-nums` /
                 `anl-kpi` block plus the period pill bar plus the
                 `anl-body` expanded region).

Estado atual: RED — AC#1 fails because `AnalyticsPanel.tsx` does not
exist; AC#2 fails because the `AnalyticsPanelProps` interface does
not exist; AC#3, AC#4 and AC#5 fail because none of the three rooms
imports or renders `<AnalyticsPanel>`; AC#6 fails because the
`(['30d', '90d', '1y'] as const).map(p => ...)` period selector is
duplicated inline in every room. The Coder must (a) create the shared
`AnalyticsPanel` component with the documented `AnalyticsPanelProps`
contract, (b) replace the inline analytics block in all three rooms
with `<AnalyticsPanel ... />` and (c) delete the inline period
selector from every room — `AnalyticsPanel` is the single source of
truth for the 30d / 90d / 1y pill bar.

Anti-Goals (must NOT be violated):
    1. NÃO alterar os props de `AnalyticsPanelProps` (os 6 props
       documentados são contrato: `title`, `kpis`, `period`,
       `onPeriodChange`, `children?`, `defaultOpen?`).
    2. NÃO manter o bloco `anl-card` / `anl-hd` / `anl-nums` / `anl-kpi`
       inline nas salas após a migração (a migração SUBSTITUI o JSX,
       não o encapsula).
    3. NÃO duplicar o period selector 30d / 90d / 1y inline nas salas
       — `AnalyticsPanel` já o renderiza internamente.
    4. NÃO introduzir uma nova dependência — o componente vive em
       `apps/blu_v3/src/components/shared/AnalyticsPanel.tsx` (novo
       arquivo, mesmo diretório dos demais componentes compartilhados
       como `DecisionCard`, `CollapsiblePanel`, etc.).
    5. NÃO mover a query / fetch para dentro de `AnalyticsPanel` —
       as salas continuam responsáveis por buscar os indicadores
       (`getSupplyIndicators`, `getFinanceIndicators`,
       `getCommercialIndicators`, `getContextMetrics`).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# ── Paths ─────────────────────────────────────────────────────────────────


REPO_ROOT = Path(__file__).resolve().parent.parent.parent

ANALYTICS_PANEL_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "components"
    / "shared"
    / "AnalyticsPanel.tsx"
)

COMPRAS_ROOM_PATH = REPO_ROOT / "apps" / "blu_v3" / "src" / "pages" / "app" / "ComprasRoom.tsx"
FINANCEIRO_ROOM_PATH = REPO_ROOT / "apps" / "blu_v3" / "src" / "pages" / "app" / "FinanceiroRoom.tsx"
CLIENTES_ROOM_PATH = REPO_ROOT / "apps" / "blu_v3" / "src" / "pages" / "app" / "ClientesRoom.tsx"


# ── Source-level guard helpers ────────────────────────────────────────────


def _read_source(path: Path) -> str:
    assert path.exists(), f"Source file not found: {path}"
    return path.read_text(encoding="utf-8")


def _imports_analytics_panel_default(source: str) -> bool:
    """Detect the default import of AnalyticsPanel from
    `../../components/shared/AnalyticsPanel`.

    Accepts:
        import AnalyticsPanel from '../../components/shared/AnalyticsPanel'
        import AnalyticsPanel from "../../components/shared/AnalyticsPanel"
    """
    pattern = (
        r"import\s+AnalyticsPanel\b"
        r"\s*from\s*['\"]\.\.\/\.\.\/components\/shared\/AnalyticsPanel['\"]"
    )
    return re.search(pattern, source) is not None


def _uses_analytics_panel_jsx(source: str) -> bool:
    """Detect a JSX usage of `<AnalyticsPanel ...>` (with any props)."""
    return re.search(r"<\s*AnalyticsPanel\b", source) is not None


def _has_inline_anl_block_with_card(source: str) -> bool:
    """Detect the inline analytics block with the `anl-card` wrapper
    around the `anl-hd` / `anl-nums` / `anl-kpi` triple — i.e. an inline
    hand-rolled AnalyticsPanel that the migration must replace.

    Used for `ComprasRoom` and `ClientesRoom`, both of which render the
    block inside `<div className="anl-card"> ... </div>`. The simultaneous
    presence of all four classNames is a strong signal of the inline
    block. The Coder is expected to delete the whole block.
    """
    return (
        re.search(r'className\s*=\s*["\']anl-card["\']', source) is not None
        and re.search(r'className\s*=\s*["\']anl-hd["\']', source) is not None
        and re.search(r'className\s*=\s*["\']anl-nums["\']', source) is not None
        and re.search(r'className\s*=\s*["\']anl-kpi["\']', source) is not None
    )


def _has_inline_anl_block_no_card(source: str) -> bool:
    """Detect the inline analytics header WITHOUT the `anl-card` wrapper.

    Used for `FinanceiroRoom`, which renders `<div className="anl-hd">`
    directly (the surrounding card chrome is owned by the panel's own
    `<div className="card">` wrapper in that room). The simultaneous
    presence of `anl-hd` / `anl-nums` / `anl-kpi` is the strong signal
    of the inline block.
    """
    return (
        re.search(r'className\s*=\s*["\']anl-hd["\']', source) is not None
        and re.search(r'className\s*=\s*["\']anl-nums["\']', source) is not None
        and re.search(r'className\s*=\s*["\']anl-kpi["\']', source) is not None
    )


def _has_inline_period_selector(source: str) -> bool:
    """Detect the inline `(['30d', '90d', '1y'] as const).map(p => ...)`
    period selector.

    The pattern is repeated verbatim in all three rooms:
        {(['30d', '90d', '1y'] as const).map(p => (
          <span
            key={p}
            className={`pill${analyticsPeriod === p ? ' on' : ''}`}
            style={{ cursor: 'pointer' }}
            onClick={() => setAnalyticsPeriod(p)}
          >
            {p === '30d' ? '30d' : p === '90d' ? '90d' : '1 ano'}
          </span>
        ))}
    The Coder is expected to delete the whole block because
    `AnalyticsPanel` owns the period selector.
    """
    pattern = (
        r"\(\s*\[\s*['\"]30d['\"]\s*,\s*['\"]90d['\"]\s*,\s*['\"]1y['\"]\s*\]\s*"
        r"as\s+const\s*\)\s*\.\s*map\s*\("
    )
    return re.search(pattern, source) is not None


# ── AC#1: AnalyticsPanel component file exists with default export ───────


def test_analytics_panel_file_exists():
    """AC#1a — `apps/blu_v3/src/components/shared/AnalyticsPanel.tsx`
    must exist.

    The whole migration hinges on having a shared component to delegate
    to. If the file is missing, AC#2 / AC#3 / AC#4 / AC#5 / AC#6 are
    unreachable.
    """
    assert ANALYTICS_PANEL_PATH.exists(), (
        f"RED — AnalyticsPanel component file not found: "
        f"{ANALYTICS_PANEL_PATH}. Expected the new shared component to "
        f"live next to `DecisionCard`, `CollapsiblePanel` and "
        f"`RoutineConfigSection` so all three room pages can import it "
        f"via `../../components/shared/AnalyticsPanel`."
    )


def test_analytics_panel_default_export():
    """AC#1b — `AnalyticsPanel.tsx` must export the component as
    `export default function AnalyticsPanel`.

    The default-export shape matches the convention used by the other
    shared components (`DecisionCard`, `CollapsiblePanel`,
    `RoutineConfigSection`, etc.) so the rooms can import it with
    `import AnalyticsPanel from '../../components/shared/AnalyticsPanel'`.
    """
    assert ANALYTICS_PANEL_PATH.exists(), (
        f"RED — source file not found: {ANALYTICS_PANEL_PATH}"
    )
    source = _read_source(ANALYTICS_PANEL_PATH)

    pattern = r"export\s+default\s+function\s+AnalyticsPanel\b"
    assert re.search(pattern, source), (
        "RED — AnalyticsPanel.tsx does NOT have a `export default "
        "function AnalyticsPanel` declaration. Expected the default "
        "export shape `export default function AnalyticsPanel(props: "
        "AnalyticsPanelProps) { ... }` so the room pages can import it "
        "via `import AnalyticsPanel from "
        "'../../components/shared/AnalyticsPanel'` (the same import "
        "shape used by `DecisionCard`, `CollapsiblePanel`, etc.)."
    )


# ── AC#2: AnalyticsPanelProps interface contract ──────────────────────────


def test_analytics_panel_exposes_analytics_panel_props_interface():
    """AC#2a — `AnalyticsPanelProps` must be exported as a
    `export interface AnalyticsPanelProps { ... }` block.

    Without the exported interface, the rooms cannot reference the
    contract by name when wiring `<AnalyticsPanel ... />` and the type
    checker has nothing to verify the call site against.
    """
    assert ANALYTICS_PANEL_PATH.exists(), (
        f"RED — source file not found: {ANALYTICS_PANEL_PATH}"
    )
    source = _read_source(ANALYTICS_PANEL_PATH)

    iface = re.search(
        r"export\s+interface\s+AnalyticsPanelProps\s*\{",
        source,
    )
    assert iface, (
        "RED — AnalyticsPanel.tsx does NOT export an `interface "
        "AnalyticsPanelProps`. Expected: "
        "`export interface AnalyticsPanelProps { title: string; kpis: "
        "Array<{ label: string; value: string | number; color?: string "
        "}>; period: string; onPeriodChange: (p: string) => void; "
        "children?: React.ReactNode; defaultOpen?: boolean; }` so the "
        "migrated rooms can rely on the contract."
    )


def test_analytics_panel_props_has_title_string():
    """AC#2b — `AnalyticsPanelProps` must declare `title: string`.

    The title (e.g. `"📊 Analytics de Compras"`) is the topmost label
    of the panel; it must be a required string so the rooms pass a
    stable label that the component renders in the header.
    """
    assert ANALYTICS_PANEL_PATH.exists(), (
        f"RED — source file not found: {ANALYTICS_PANEL_PATH}"
    )
    source = _read_source(ANALYTICS_PANEL_PATH)

    iface = re.search(
        r"export\s+interface\s+AnalyticsPanelProps\s*\{([^}]*)\}",
        source,
        re.DOTALL,
    )
    assert iface, (
        "RED — `interface AnalyticsPanelProps` is not declared in "
        "AnalyticsPanel.tsx. Add it before evaluating the individual "
        "props."
    )

    body = iface.group(1)
    match = re.search(r"\btitle\s*:\s*string\b", body)
    assert match, (
        "RED — `AnalyticsPanelProps` is missing the `title: string` "
        "prop. The header label (e.g. `\"📊 Analytics de Compras\"`) is "
        "part of the contract; every migrated room passes it to "
        "`<AnalyticsPanel title={...} />`."
    )


def test_analytics_panel_props_has_kpis_array():
    """AC#2c — `AnalyticsPanelProps` must declare
    `kpis: Array<{ label: string; value: string | number; color?: string }>`.

    The `kpis` array is what the rooms currently render inside
    `<div className="anl-nums">` (the collapsed-header KPIs). After the
    migration the rooms hand the array to `<AnalyticsPanel kpis={...} />`
    and the component renders the `label` / `value` / `color` triple
    uniformly.
    """
    assert ANALYTICS_PANEL_PATH.exists(), (
        f"RED — source file not found: {ANALYTICS_PANEL_PATH}"
    )
    source = _read_source(ANALYTICS_PANEL_PATH)

    iface = re.search(
        r"export\s+interface\s+AnalyticsPanelProps\s*\{([^}]*)\}",
        source,
        re.DOTALL,
    )
    assert iface, (
        "RED — `interface AnalyticsPanelProps` is not declared in "
        "AnalyticsPanel.tsx. Add it before evaluating the individual "
        "props."
    )

    body = iface.group(1)

    has_kpis_prop = re.search(r"\bkpis\s*:\s*Array\s*<", body) is not None
    assert has_kpis_prop, (
        "RED — `AnalyticsPanelProps` is missing the `kpis: Array<...>` "
        "prop. Expected: `kpis: Array<{ label: string; value: string | "
        "number; color?: string }>` so each room passes the header "
        "KPIs as data instead of inlining the `anl-nums` / `anl-kpi` "
        "JSX."
    )

    has_label = re.search(r"\blabel\s*:\s*string\b", body) is not None
    has_value = re.search(
        r"\bvalue\s*:\s*(?:string\s*\|\s*number|number\s*\|\s*string)\b", body
    ) is not None
    has_color_optional = re.search(r"\bcolor\s*\?\s*:\s*string\b", body) is not None

    assert has_label, (
        "RED — `AnalyticsPanelProps.kpis[]` is missing the `label: "
        "string` field. The header KPI label is part of the contract."
    )
    assert has_value, (
        "RED — `AnalyticsPanelProps.kpis[]` is missing the "
        "`value: string | number` field (union order is irrelevant). "
        "Header KPIs are rendered as either a formatted number or a "
        "literal string (e.g. `'—'`)."
    )
    assert has_color_optional, (
        "RED — `AnalyticsPanelProps.kpis[]` is missing the optional "
        "`color?: string` field. Some rooms pass a per-KPI color "
        "(e.g. `var(--ok)` / `var(--urg)`) and the contract must allow "
        "it."
    )


def test_analytics_panel_props_has_period_and_on_period_change():
    """AC#2d — `AnalyticsPanelProps` must declare `period: string` and
    `onPeriodChange: (p: string) => void`.

    The `period` value is the current pill (`'30d' | '90d' | '1y'`)
    and `onPeriodChange` is the setter the room passes so the pill bar
    can drive the room's `setAnalyticsPeriod`. Both are required:
    `period` so the component knows which pill is active, and
    `onPeriodChange` so clicking a pill can change the period.
    """
    assert ANALYTICS_PANEL_PATH.exists(), (
        f"RED — source file not found: {ANALYTICS_PANEL_PATH}"
    )
    source = _read_source(ANALYTICS_PANEL_PATH)

    iface = re.search(
        r"export\s+interface\s+AnalyticsPanelProps\s*\{([^}]*)\}",
        source,
        re.DOTALL,
    )
    assert iface, (
        "RED — `interface AnalyticsPanelProps` is not declared in "
        "AnalyticsPanel.tsx. Add it before evaluating the individual "
        "props."
    )

    body = iface.group(1)

    has_period = re.search(r"\bperiod\s*:\s*string\b", body) is not None
    assert has_period, (
        "RED — `AnalyticsPanelProps` is missing `period: string`. The "
        "current pill value (`'30d' | '90d' | '1y'`) is the source of "
        "truth for which pill the period selector highlights."
    )

    has_on_period_change = re.search(
        r"\bonPeriodChange\s*:\s*\(\s*p\s*:\s*string\s*\)\s*=>\s*void\b",
        body,
    ) is not None
    assert has_on_period_change, (
        "RED — `AnalyticsPanelProps` is missing "
        "`onPeriodChange: (p: string) => void`. The room passes its "
        "`setAnalyticsPeriod` setter here so the pill bar inside "
        "`AnalyticsPanel` can drive the room's period state."
    )


def test_analytics_panel_props_has_optional_children_and_default_open():
    """AC#2e — `AnalyticsPanelProps` must declare
    `children?: React.ReactNode` and `defaultOpen?: boolean`.

    `children` is the expanded body (the kpi-grid + secondary metrics
    that all three rooms currently render inside `<div className=
    "anl-body">`); it is optional because a room might use
    `AnalyticsPanel` for the header KPIs only. `defaultOpen` controls
    whether the panel starts expanded; the current rooms start
    collapsed (`useState(false)`), so a sensible default is fine, but
    the prop must exist so a room can flip it.
    """
    assert ANALYTICS_PANEL_PATH.exists(), (
        f"RED — source file not found: {ANALYTICS_PANEL_PATH}"
    )
    source = _read_source(ANALYTICS_PANEL_PATH)

    iface = re.search(
        r"export\s+interface\s+AnalyticsPanelProps\s*\{([^}]*)\}",
        source,
        re.DOTALL,
    )
    assert iface, (
        "RED — `interface AnalyticsPanelProps` is not declared in "
        "AnalyticsPanel.tsx. Add it before evaluating the individual "
        "props."
    )

    body = iface.group(1)

    has_children = re.search(
        r"\bchildren\s*\?\s*:\s*React\.ReactNode\b", body
    ) is not None
    assert has_children, (
        "RED — `AnalyticsPanelProps` is missing "
        "`children?: React.ReactNode`. The expanded body (kpi-grid + "
        "secondary metrics) is passed as children so the component "
        "owns the open / close chrome but the room owns the content."
    )

    has_default_open = re.search(
        r"\bdefaultOpen\s*\?\s*:\s*boolean\b", body
    ) is not None
    assert has_default_open, (
        "RED — `AnalyticsPanelProps` is missing `defaultOpen?: boolean`. "
        "The current rooms start collapsed; a room that wants to start "
        "expanded must be able to flip this prop."
    )


# ── AC#3: ComprasRoom uses shared AnalyticsPanel ──────────────────────────


def test_compras_room_imports_analytics_panel():
    """AC#3a — `ComprasRoom.tsx` must import the default export of
    `AnalyticsPanel` from `../../components/shared/AnalyticsPanel`.

    Without the import, the JSX `<AnalyticsPanel ...>` would be a
    reference to an undeclared identifier and the build would fail.
    """
    assert COMPRAS_ROOM_PATH.exists(), (
        f"RED — source file not found: {COMPRAS_ROOM_PATH}"
    )
    source = _read_source(COMPRAS_ROOM_PATH)

    assert _imports_analytics_panel_default(source), (
        "RED — ComprasRoom.tsx does NOT import AnalyticsPanel from "
        "`../../components/shared/AnalyticsPanel`. Expected: "
        "`import AnalyticsPanel from "
        "'../../components/shared/AnalyticsPanel'` so the bottom "
        "analytics block can be rendered through the shared component "
        "instead of the inline `anl-card` / `anl-hd` / `anl-nums` / "
        "`anl-kpi` JSX plus the inline period selector."
    )


def test_compras_room_uses_analytics_panel_jsx():
    """AC#3b — `ComprasRoom.tsx` must render at least one
    `<AnalyticsPanel ... />` JSX element.

    Importing without using is dead code; the test guards against the
    half-migration where someone adds the import but forgets to wire
    it into the analytics block.
    """
    assert COMPRAS_ROOM_PATH.exists(), (
        f"RED — source file not found: {COMPRAS_ROOM_PATH}"
    )
    source = _read_source(COMPRAS_ROOM_PATH)

    assert _uses_analytics_panel_jsx(source), (
        "RED — ComprasRoom.tsx does NOT render <AnalyticsPanel ...>. "
        "Expected: a JSX usage such as "
        "`<AnalyticsPanel title=\"📊 Analytics de Compras\" kpis={[...]} "
        "period={analyticsPeriod} onPeriodChange={setAnalyticsPeriod}>"
        "...expanded body...</AnalyticsPanel>` in place of the inline "
        "`anl-card` / `anl-hd` / `anl-nums` / `anl-kpi` block."
    )


def test_compras_room_drops_inline_anl_block():
    """AC#3c — After the migration, `ComprasRoom` must no longer render
    the inline analytics block (the `anl-card` / `anl-hd` / `anl-nums` /
    `anl-kpi` className quadruple).

    The migration is a replacement, not an addition. Keeping the inline
    block alongside `<AnalyticsPanel>` would double-render the header
    KPIs.
    """
    assert COMPRAS_ROOM_PATH.exists(), (
        f"RED — source file not found: {COMPRAS_ROOM_PATH}"
    )
    source = _read_source(COMPRAS_ROOM_PATH)

    assert not _has_inline_anl_block_with_card(source), (
        "RED — ComprasRoom.tsx still contains the inline `anl-card` / "
        "`anl-hd` / `anl-nums` / `anl-kpi` analytics block. Expected: "
        "the inline block is REPLACED by `<AnalyticsPanel ... />`, not "
        "kept alongside it. Removing the inline block is the whole "
        "point of the migration."
    )


# ── AC#4: FinanceiroRoom uses shared AnalyticsPanel ───────────────────────


def test_financeiro_room_imports_analytics_panel():
    """AC#4a — `FinanceiroRoom.tsx` must import the default export of
    `AnalyticsPanel` from `../../components/shared/AnalyticsPanel`.
    """
    assert FINANCEIRO_ROOM_PATH.exists(), (
        f"RED — source file not found: {FINANCEIRO_ROOM_PATH}"
    )
    source = _read_source(FINANCEIRO_ROOM_PATH)

    assert _imports_analytics_panel_default(source), (
        "RED — FinanceiroRoom.tsx does NOT import AnalyticsPanel from "
        "`../../components/shared/AnalyticsPanel`. Expected: "
        "`import AnalyticsPanel from "
        "'../../components/shared/AnalyticsPanel'` so the analytics "
        "block at the bottom of the Financeiro tab can be rendered "
        "through the shared component instead of the inline "
        "`anl-hd` / `anl-nums` / `anl-kpi` JSX plus the inline period "
        "selector. (Note: Financeiro has no `anl-card` wrapper — the "
        "header sits directly inside the room's own `<div className="
        "\"card\">`.)"
    )


def test_financeiro_room_uses_analytics_panel_jsx():
    """AC#4b — `FinanceiroRoom.tsx` must render at least one
    `<AnalyticsPanel ... />` JSX element.

    Importing without using is dead code; the test guards against the
    half-migration where someone adds the import but forgets to wire
    it into the analytics header.
    """
    assert FINANCEIRO_ROOM_PATH.exists(), (
        f"RED — source file not found: {FINANCEIRO_ROOM_PATH}"
    )
    source = _read_source(FINANCEIRO_ROOM_PATH)

    assert _uses_analytics_panel_jsx(source), (
        "RED — FinanceiroRoom.tsx does NOT render <AnalyticsPanel ...>. "
        "Expected: a JSX usage such as "
        "`<AnalyticsPanel title=\"📊 Analytics\" kpis={[...]} "
        "period={analyticsPeriod} onPeriodChange={setAnalyticsPeriod}>"
        "...expanded body...</AnalyticsPanel>` in place of the inline "
        "`anl-hd` / `anl-nums` / `anl-kpi` block (note: no `anl-card` "
        "wrapper in Financeiro)."
    )


def test_financeiro_room_drops_inline_anl_block():
    """AC#4c — After the migration, `FinanceiroRoom` must no longer
    render the inline analytics header (the `anl-hd` / `anl-nums` /
    `anl-kpi` className triple).

    `FinanceiroRoom` does NOT have the `anl-card` wrapper (its header
    sits directly inside the room's own `<div className="card">`),
    so the strong signal of the inline block is the `anl-hd` /
    `anl-nums` / `anl-kpi` triple. The migration must remove it.
    """
    assert FINANCEIRO_ROOM_PATH.exists(), (
        f"RED — source file not found: {FINANCEIRO_ROOM_PATH}"
    )
    source = _read_source(FINANCEIRO_ROOM_PATH)

    assert not _has_inline_anl_block_no_card(source), (
        "RED — FinanceiroRoom.tsx still contains the inline `anl-hd` / "
        "`anl-nums` / `anl-kpi` analytics header. Expected: the inline "
        "block is REPLACED by `<AnalyticsPanel ... />`, not kept "
        "alongside it. (Financeiro does not have the `anl-card` "
        "wrapper — the header sits directly inside the room's own "
        "`<div className=\"card\">`.)"
    )


# ── AC#5: ClientesRoom uses shared AnalyticsPanel ─────────────────────────


def test_clientes_room_imports_analytics_panel():
    """AC#5a — `ClientesRoom.tsx` must import the default export of
    `AnalyticsPanel` from `../../components/shared/AnalyticsPanel`.
    """
    assert CLIENTES_ROOM_PATH.exists(), (
        f"RED — source file not found: {CLIENTES_ROOM_PATH}"
    )
    source = _read_source(CLIENTES_ROOM_PATH)

    assert _imports_analytics_panel_default(source), (
        "RED — ClientesRoom.tsx does NOT import AnalyticsPanel from "
        "`../../components/shared/AnalyticsPanel`. Expected: "
        "`import AnalyticsPanel from "
        "'../../components/shared/AnalyticsPanel'` so the bottom "
        "analytics block can be rendered through the shared component "
        "instead of the inline `anl-card` / `anl-hd` / `anl-nums` / "
        "`anl-kpi` JSX plus the inline period selector."
    )


def test_clientes_room_uses_analytics_panel_jsx():
    """AC#5b — `ClientesRoom.tsx` must render at least one
    `<AnalyticsPanel ... />` JSX element in place of the inline
    `anl-card` / `anl-hd` / `anl-nums` / `anl-kpi` block.
    """
    assert CLIENTES_ROOM_PATH.exists(), (
        f"RED — source file not found: {CLIENTES_ROOM_PATH}"
    )
    source = _read_source(CLIENTES_ROOM_PATH)

    assert _uses_analytics_panel_jsx(source), (
        "RED — ClientesRoom.tsx does NOT render <AnalyticsPanel ...>. "
        "Expected: a JSX usage such as "
        "`<AnalyticsPanel title=\"📊 Analytics Comercial\" kpis={[...]} "
        "period={analyticsPeriod} onPeriodChange={setAnalyticsPeriod}>"
        "...expanded body...</AnalyticsPanel>` in place of the inline "
        "`anl-card` / `anl-hd` / `anl-nums` / `anl-kpi` block."
    )


def test_clientes_room_drops_inline_anl_block():
    """AC#5c — After the migration, `ClientesRoom` must no longer
    render the inline analytics block (the `anl-card` / `anl-hd` /
    `anl-nums` / `anl-kpi` className quadruple).
    """
    assert CLIENTES_ROOM_PATH.exists(), (
        f"RED — source file not found: {CLIENTES_ROOM_PATH}"
    )
    source = _read_source(CLIENTES_ROOM_PATH)

    assert not _has_inline_anl_block_with_card(source), (
        "RED — ClientesRoom.tsx still contains the inline `anl-card` / "
        "`anl-hd` / `anl-nums` / `anl-kpi` analytics block. Expected: "
        "the inline block is REPLACED by `<AnalyticsPanel ... />`, not "
        "kept alongside it. Removing the inline block is the whole "
        "point of the migration."
    )


# ── AC#6: Period selector is owned by AnalyticsPanel, not duplicated ──────


@pytest.mark.parametrize(
    "room_page",
    [
        "ComprasRoom.tsx",
        "FinanceiroRoom.tsx",
        "ClientesRoom.tsx",
    ],
)
def test_room_does_not_duplicate_inline_period_selector(room_page: str):
    """AC#6 — The `30d` / `90d` / `1y` period selector must live inside
    `AnalyticsPanel`, NOT be re-implemented inline in every room.

    Today each room hand-rolls the pill bar as:
        {(['30d', '90d', '1y'] as const).map(p => (
          <span
            key={p}
            className={`pill${analyticsPeriod === p ? ' on' : ''}`}
            style={{ cursor: 'pointer' }}
            onClick={() => setAnalyticsPeriod(p)}
          >
            {p === '30d' ? '30d' : p === '90d' ? '90d' : '1 ano'}
          </span>
        ))}
    This pattern is the strong signal of the inline period selector.
    After the migration, the room passes `period={analyticsPeriod}`
    and `onPeriodChange={setAnalyticsPeriod}` to `<AnalyticsPanel>`,
    and the inline `.map(p => ...)` block is removed.
    """
    if room_page == "ComprasRoom.tsx":
        page_path = COMPRAS_ROOM_PATH
    elif room_page == "FinanceiroRoom.tsx":
        page_path = FINANCEIRO_ROOM_PATH
    elif room_page == "ClientesRoom.tsx":
        page_path = CLIENTES_ROOM_PATH
    else:
        raise AssertionError(f"Unhandled room_page in parametrize: {room_page}")

    assert page_path.exists(), (
        f"RED — source file not found: {page_path}"
    )
    source = _read_source(page_path)

    assert not _has_inline_period_selector(source), (
        f"RED — {room_page} still contains the inline period selector "
        "(`(['30d', '90d', '1y'] as const).map(p => ...)`). Expected: "
        "the period selector is owned by `AnalyticsPanel` and the room "
        "passes `period={analyticsPeriod}` + "
        "`onPeriodChange={setAnalyticsPeriod}` instead of rendering the "
        "pill bar inline. Removing the inline period selector is what "
        "makes AC#6 green."
    )
