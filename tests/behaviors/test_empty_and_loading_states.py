"""RED test for behavior — shared `EmptyState` component.

GOAL:
    Every room page in `apps/blu_v3` (Compras, Financeiro, Clientes,
    Documentos, Estoque, Estratégia, Agenda, …) needs to render an
    "empty / no data" state. Today each page rolls its own ad-hoc
    empty state — a `<div className="empty">…</div>` block with a
    hand-typed icon string, a hand-typed title, a hand-typed
    description, and (sometimes) a call-to-action button. That
    duplication has already produced visual drift (different icons,
    different copy, sometimes no action button at all) and is the
    reason the rooms feel inconsistent when the user lands on a tab
    with zero records.

    The fix is a single shared component at
    `apps/blu_v3/src/components/shared/EmptyState.tsx` with a
    minimal, fully-typed prop surface. Once the shared component
    exists, the rooms migrate their hand-rolled empty blocks to it
    one PR at a time.

BEHAVIOR:
    The shared `EmptyState` component must:

        1. Live at `apps/blu_v3/src/components/shared/EmptyState.tsx`.
        2. Export a TypeScript `interface EmptyStateProps` with:
               icon:        string
               title:       string
               description: string
               action?:     { label: string; onClick: () => void }
           — i.e. `icon`, `title`, `description` are required, and
           `action` is OPTIONAL (the `?` modifier) and, when
           provided, must be a small object literal with a `label`
           string and an `onClick` zero-arg callback returning
           `void`.
        3. Be the default export of the file, named `EmptyState`,
           and accept `EmptyStateProps` as the type annotation on
           its parameter list. The required props (`icon`,
           `title`, `description`) must be reachable as named
           locals inside the function body — i.e. the function
           must destructure them out of the props argument (so a
           consumer can write `<EmptyState icon="…" title="…"
           description="…" />` without having to dig into
           `props.icon`).

AC (Acceptance Criteria):
    AC#1 — `apps/blu_v3/src/components/shared/EmptyState.tsx` exists
           on disk (the canonical location for the shared component).
    AC#2 — The file exports `interface EmptyStateProps` so other
           files can `import type { EmptyStateProps } from
           '../../components/shared/EmptyState'`.
    AC#3 — `EmptyStateProps` declares `icon: string`, `title: string`,
           and `description: string` as required string props.
    AC#4 — `EmptyStateProps` declares `action` as OPTIONAL (`action?:`)
           and, when present, the type is the object literal
           `{ label: string; onClick: () => void }`.
    AC#5 — The file has a `export default function EmptyState(...):
           EmptyStateProps` signature — the component is the
           default export and is typed against the contract.
    AC#6 — The default-export function destructures the three
           required props (`icon`, `title`, `description`) out of
           its props argument, so the JSX body can reference them
           as bare identifiers.

DECISION:
    Estratégia: create — a brand-new shared component, no
                pre-existing `EmptyState` to migrate from. The
                shared component is the source of truth for
                empty-state markup; rooms will adopt it in
                follow-up PRs.
    Arquivo alvo: apps/blu_v3/src/components/shared/EmptyState.tsx
    Função alvo:  `export default function EmptyState(props:
                 EmptyStateProps) { … }` plus the
                 `EmptyStateProps` interface.

Estado atual: RED — `EmptyState.tsx` does NOT exist on disk. Every
AC fails on the file-exists check (AC#1) and the source-inspection
checks (AC#2 → AC#6) cannot run. The Coder must create the file
with the exact prop contract above to turn all 6 ACs GREEN.

Anti-Goals (must NOT be violated):
    1. NÃO renomear nenhum dos 4 props — `icon`, `title`,
       `description`, `action` são contrato.
    2. NÃO tornar `action` obrigatório — ele é OPTIONAL (`?`) e
       um consumidor que não quer CTA deve poder omiti-lo
       inteiramente.
    3. NÃO alterar o tipo do `action` — ele é exatamente
       `{ label: string; onClick: () => void }`. Não aceitar
       `onClick: (e: MouseEvent) => void`, não aceitar
       `onClick: () => Promise<void>`, não aceitar `onClick?:`.
    4. NÃO tipar `icon` como `ReactNode` / `JSX.Element` — ele é
       `string` (o componente decide como renderizar a string:
       emoji, classe, lookup em um mapa, etc.).
    5. NÃO exportar o componente como named export — ele deve ser
       o DEFAULT export para casar com o padrão de
       `import EmptyState from '../../components/shared/EmptyState'`
       já usado pelos outros componentes shared (`DecisionCard`,
       `ErrorFallback`, …).
    6. NÃO colocar o componente em outro diretório
       (`components/common/`, `components/ui/`, etc.) — ele é
       `components/shared/EmptyState.tsx` por contrato.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Paths ─────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

EMPTY_STATE_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "components"
    / "shared"
    / "EmptyState.tsx"
)


# ── Source-level guard helpers ────────────────────────────────────────────


def _read_source(path: Path) -> str:
    assert path.exists(), f"Source file not found: {path}"
    return path.read_text(encoding="utf-8")


def _has_empty_state_props_interface(source: str) -> bool:
    """Detect an `export interface EmptyStateProps { … }` declaration.

    We match the opening `export interface EmptyStateProps {` and the
    closing `}`. The body is allowed to contain at most one level of
    nested braces (which is exactly what `action?: { label: string;
    onClick: () => void }` needs).
    """
    pattern = (
        r"export\s+interface\s+EmptyStateProps\s*\{"
        r"((?:[^{}]|\{[^{}]*\})*)"
        r"\}"
    )
    return re.search(pattern, source, re.DOTALL) is not None


def _empty_state_props_body(source: str) -> str | None:
    """Return the body of the `EmptyStateProps` interface, or None if
    the interface is not declared.

    The body is the substring between the opening `{` and the matching
    closing `}`, with one level of nested-brace support so that
    `action?: { label: string; onClick: () => void }` does not break
    the extraction.
    """
    pattern = (
        r"export\s+interface\s+EmptyStateProps\s*\{"
        r"((?:[^{}]|\{[^{}]*\})*)"
        r"\}"
    )
    m = re.search(pattern, source, re.DOTALL)
    return m.group(1) if m else None


def _declares_required_string_prop(source: str, prop: str) -> bool:
    """Detect `<prop>: string` declared as a required prop.

    We look for `<prop>` followed by `:` (NOT `?:`) and the literal
    `string` type. This rejects optional props (`icon?:`) and
    rejected type variants (`icon?: ReactNode`).
    """
    pattern = rf"\b{prop}\s*:\s*string\b"
    return re.search(pattern, source) is not None


def _declares_optional_action_prop(source: str) -> bool:
    """Detect `action?:` — i.e. `action` is declared as an OPTIONAL prop.

    We look for `action` followed by `?:` (the question mark making
    it optional) and NOT `action:` (which would be required).
    """
    return re.search(r"\baction\s*\?\s*:\s*", source) is not None


def _action_type_shape(source: str) -> dict[str, bool]:
    """Inspect the type of the `action` prop and return which contract
    fields are present.

    We grab the substring that follows `action?:` up to the matching
    closing `}` (with one level of nested-brace support, so an
    object-literal type with a function-type field still parses),
    and check for:
        - label:    string
        - onClick:  () => void
    """
    # Match `action?:` followed by `{ … }` with one level of nesting.
    pattern = (
        r"\baction\s*\?\s*:\s*\{"
        r"((?:[^{}]|\{[^{}]*\})*)"
        r"\}"
    )
    m = re.search(pattern, source, re.DOTALL)
    if not m:
        return {"label": False, "onClick": False, "shape": False}
    body = m.group(1)
    has_label = re.search(r"\blabel\s*:\s*string\b", body) is not None
    has_onclick = re.search(
        r"\bonClick\s*:\s*\(\s*\)\s*=>\s*void\b", body
    ) is not None
    return {
        "label": has_label,
        "onClick": has_onclick,
        "shape": has_label and has_onclick,
    }


def _has_default_export_function(source: str) -> bool:
    """Detect `export default function EmptyState(...) { … }`.

    We are permissive about the parameter list: both the destructure
    form (`({ … }: EmptyStateProps)`) and the bare form
    (`(props: EmptyStateProps)`) must pass. The function name MUST
    be `EmptyState` (the default export of the file).
    """
    pattern = (
        r"export\s+default\s+function\s+EmptyState\s*\("
        r"[^)]*\)"
        r"\s*:\s*EmptyStateProps"
    )
    return re.search(pattern, source, re.DOTALL) is not None


def _destructure_has_required_props(source: str) -> dict[str, bool]:
    """Detect the destructure form of the default-export parameter list
    and return which required props are reachable as bare names.

    We only check the three required props (`icon`, `title`,
    `description`); `action` is optional and may or may not be
    destructured. A prop is "present" if its identifier appears
    inside the `{ … }` destructure of the default-export function.
    """
    sig = re.search(
        r"export\s+default\s+function\s+EmptyState\s*\(\s*\{([^}]*)\}\s*:\s*EmptyStateProps",
        source,
    )
    if not sig:
        # If the function uses the bare `props: EmptyStateProps`
        # form, the destructure is not present. We surface the three
        # required props as "not detected" — the dedicated signature
        # test is the one that enforces typing.
        return {"icon": False, "title": False, "description": False}
    body = sig.group(1)
    return {
        "icon": re.search(r"\bicon\b", body) is not None,
        "title": re.search(r"\btitle\b", body) is not None,
        "description": re.search(r"\bdescription\b", body) is not None,
    }


# ── AC#1: file exists at the canonical path ──────────────────────────────


def test_empty_state_file_exists():
    """AC#1 — `apps/blu_v3/src/components/shared/EmptyState.tsx` must
    exist on disk.

    This is the source-of-truth guard for the entire migration: until
    the file exists, every other AC#2..AC#6 is unreachable. The
    rooms will import the shared component from this exact path, so
    placing the file elsewhere (e.g. `components/ui/EmptyState.tsx`)
    is a hard contract violation.
    """
    assert EMPTY_STATE_PATH.exists(), (
        f"RED — source file not found: {EMPTY_STATE_PATH}. "
        "Expected: a new `EmptyState.tsx` under "
        "`apps/blu_v3/src/components/shared/` exporting the shared "
        "empty-state component used by every room page. Without it, "
        "each room keeps rolling its own ad-hoc empty block, and the "
        "visual drift across rooms (different icons, different copy, "
        "sometimes no action button) continues."
    )


# ── AC#2: interface is exported ──────────────────────────────────────────


def test_empty_state_exports_empty_state_props_interface():
    """AC#2 — The file must export `interface EmptyStateProps { … }`.

    Other modules will import the type as
    `import type { EmptyStateProps } from
    '../../components/shared/EmptyState'`, which requires the
    `export` keyword on the interface declaration. We also require
    the body to be well-formed (one level of nested-brace support,
    so `action?: { … }` is captured correctly).
    """
    assert EMPTY_STATE_PATH.exists(), (
        f"RED — source file not found: {EMPTY_STATE_PATH}"
    )
    source = _read_source(EMPTY_STATE_PATH)

    assert _has_empty_state_props_interface(source), (
        "RED — EmptyState.tsx does NOT export `interface EmptyStateProps "
        "{ … }`. Expected: `export interface EmptyStateProps { icon: "
        "string; title: string; description: string; action?: { label: "
        "string; onClick: () => void } }` so consumers can `import type "
        "{ EmptyStateProps }` and rely on the prop contract."
    )


# ── AC#3: required props are typed as `string` ───────────────────────────


@pytest.mark.parametrize("prop", ["icon", "title", "description"])
def test_empty_state_required_prop_is_string_typed(prop: str):
    """AC#3 — Each required prop (`icon`, `title`, `description`) must
    be typed as `string` (REQUIRED, not optional, not `ReactNode`,
    not `JSX.Element`).

    The shared component decides how to render `icon` (emoji,
    className lookup, inline SVG, etc.), so the prop must be a
    raw `string` — that is the contract. An optional `?:` would
    mean a room can render an empty state with no icon, which is
    allowed, but the prop itself stays required; if a room needs
    no icon it should pass an empty string.
    """
    assert EMPTY_STATE_PATH.exists(), (
        f"RED — source file not found: {EMPTY_STATE_PATH}"
    )
    source = _read_source(EMPTY_STATE_PATH)

    # The interface must be present first — otherwise the prop
    # declaration is meaningless. We re-use the body extraction
    # so we are checking the prop in its declared context, not
    # picking up stray `title="…"` JSX attributes.
    body = _empty_state_props_body(source)
    assert body is not None, (
        "RED — EmptyState.tsx does NOT export `interface "
        "EmptyStateProps`. AC#3 cannot be evaluated until the "
        "interface exists; declare it first (see AC#2)."
    )

    required_re = rf"\b{prop}\s*:\s*string\b"
    assert re.search(required_re, body), (
        f"RED — EmptyStateProps is missing the required prop "
        f"`{prop}: string`. Expected the interface to declare "
        f"`{prop}: string` (REQUIRED, not optional) so consumers "
        f"can pass an icon/title/description string and have it "
        f"rendered by the shared component."
    )


# ── AC#4: `action` is optional and shaped correctly ───────────────────────


def test_empty_state_action_is_optional():
    """AC#4a — The `action` prop must be OPTIONAL (`action?:`).

    A room page that has no call-to-action (e.g. a read-only
    document list) must be able to write
    `<EmptyState icon="📄" title="…" description="…" />` without
    supplying an `action`. The `?` modifier on the prop is the
    whole point: it makes the prop optional at the type level.
    """
    assert EMPTY_STATE_PATH.exists(), (
        f"RED — source file not found: {EMPTY_STATE_PATH}"
    )
    source = _read_source(EMPTY_STATE_PATH)

    assert _declares_optional_action_prop(source), (
        "RED — EmptyState.tsx does NOT declare `action` as an "
        "OPTIONAL prop. Expected `action?:` (with the `?` "
        "modifier) so consumers that don't need a call-to-action "
        "can omit the `action` prop entirely. A required `action` "
        "would force every empty state to render a button, which "
        "is wrong for read-only rooms (e.g. a 'no documents yet' "
        "state in DocumentosRoom)."
    )


def test_empty_state_action_shape_is_object_literal():
    """AC#4b — When `action` is supplied, its type must be the object
    literal `{ label: string; onClick: () => void }`.

    The shared component renders a single button when `action` is
    provided, and that button needs (a) the visible label and (b)
    a click handler. The contract pins both — no optional
    `onClick?:`, no MouseEvent parameter, no Promise return type.
    """
    assert EMPTY_STATE_PATH.exists(), (
        f"RED — source file not found: {EMPTY_STATE_PATH}"
    )
    source = _read_source(EMPTY_STATE_PATH)

    shape = _action_type_shape(source)
    assert shape["shape"], (
        "RED — EmptyState.tsx declares `action?:` but the type is "
        "not `{ label: string; onClick: () => void }`. "
        f"Detected: label={shape['label']}, onClick={shape['onClick']}. "
        "Expected: `action?: { label: string; onClick: () => void }` "
        "so the shared component can render a `<button>` with a "
        "fixed label and a zero-arg, void-returning click handler. "
        "Any other shape (optional onClick, MouseEvent parameter, "
        "Promise return) is out of contract."
    )


# ── AC#5: default-export function is typed against the contract ─────────


def test_empty_state_default_export_function_uses_props():
    """AC#5 — The file must have
    `export default function EmptyState(...): EmptyStateProps`.

    Two things are pinned at once:
        (a) the component is the DEFAULT export of the file (rooms
            will write `import EmptyState from
            '../../components/shared/EmptyState'`), and
        (b) its parameter list is typed against the `EmptyStateProps`
            interface, so TypeScript will catch any consumer that
            passes the wrong prop shape at compile time.
    """
    assert EMPTY_STATE_PATH.exists(), (
        f"RED — source file not found: {EMPTY_STATE_PATH}"
    )
    source = _read_source(EMPTY_STATE_PATH)

    assert _has_default_export_function(source), (
        "RED — EmptyState.tsx does NOT have the expected default-"
        "export signature `export default function EmptyState(...): "
        "EmptyStateProps`. The component MUST be the default export "
        "(matching the convention of other shared components like "
        "`DecisionCard` and `ErrorFallback`) and MUST be typed "
        "against `EmptyStateProps` so the prop contract is enforced "
        "at compile time for every room that adopts it."
    )


# ── AC#6: required props are destructured into bare names ────────────────


@pytest.mark.parametrize("prop", ["icon", "title", "description"])
def test_empty_state_function_destructures_required_prop(prop: str):
    """AC#6 — The default-export function must destructure each
    required prop (`icon`, `title`, `description`) out of its props
    argument, so the JSX body can reference them as bare identifiers
    (`{title}`, `{description}`, `{icon}`) without going through
    `props.title`, `props.icon`, etc.

    `action` is intentionally NOT checked here because it is
    optional — it may or may not be destructured (the component
    is free to use `props.action` for an optional callback).
    """
    assert EMPTY_STATE_PATH.exists(), (
        f"RED — source file not found: {EMPTY_STATE_PATH}"
    )
    source = _read_source(EMPTY_STATE_PATH)

    destructure = _destructure_has_required_props(source)
    assert destructure[prop], (
        f"RED — the default-export `EmptyState` function does not "
        f"destructure the required prop `{prop}`. Expected the "
        f"signature to be "
        f"`export default function EmptyState({{ icon, title, "
        f"description, action? }}: EmptyStateProps) {{ … }}` "
        f"so the JSX body can reference `{{{prop}}}` directly. "
        f"Detected destructure: icon={destructure['icon']}, "
        f"title={destructure['title']}, "
        f"description={destructure['description']}."
    )


# ═══════════════════════════════════════════════════════════════════════════
# AC#2 — shared `LoadingState` component
# ═══════════════════════════════════════════════════════════════════════════
#
# GOAL:
#     Every room page in `apps/blu_v3` (Compras, Financeiro, Clientes,
#     Documentos, Estoque, Estratégia, Agenda, …) also needs a shared
#     "loading" state — the spinner/skeleton block rendered while the
#     page is fetching its data. Today each page rolls its own ad-hoc
#     loading block: a `<div className="loading">…</div>` with a
#     hand-typed spinner, sometimes a hand-typed "Carregando…" string,
#     and no shared `data-testid` or `role` for tests to anchor on.
#
#     The fix is a single shared component at
#     `apps/blu_v3/src/components/shared/LoadingState.tsx` with a
#     minimal, fully-typed prop surface. The prop surface here is even
#     narrower than `EmptyState` — a single optional `message` string
#     (e.g. "Carregando compras…") so rooms can override the default
#     copy but otherwise get a polished spinner for free.
#
# BEHAVIOR:
#     The shared `LoadingState` component must:
#
#         1. Live at `apps/blu_v3/src/components/shared/LoadingState.tsx`.
#         2. Export a TypeScript `interface LoadingStateProps` with:
#                message?: string
#           — i.e. `message` is OPTIONAL (the `?` modifier) and, when
#           provided, is a plain `string` (the component decides how to
#           render the message: a `<span>`, a `<p>`, a `aria-label`,
#           etc.).
#         3. Be the default export of the file, named `LoadingState`,
#            and accept `LoadingStateProps` as the type annotation on
#            its parameter list. The optional prop (`message`) must be
#            reachable as a named local inside the function body —
#            i.e. the function must destructure it out of the props
#            argument (so a consumer can write `<LoadingState />` for
#            the default copy, or `<LoadingState message="…" />` to
#            override it, without having to dig into `props.message`).
#
# AC (Acceptance Criteria):
#     AC#1 — `apps/blu_v3/src/components/shared/LoadingState.tsx`
#            exists on disk (the canonical location for the shared
#            component).
#     AC#2 — The file exports `interface LoadingStateProps` so other
#            files can `import type { LoadingStateProps } from
#            '../../components/shared/LoadingState'`.
#     AC#3 — `LoadingStateProps` declares `message?:` — i.e. the
#            `message` prop is OPTIONAL (the `?` modifier) and, when
#            present, is typed as `string`. NOT `message: string`
#            (would force every caller to pass a string), NOT
#            `message?: ReactNode` (the prop is a raw string — the
#            component decides how to render it).
#     AC#4 — The file has a `export default function
#            LoadingState(...): LoadingStateProps` signature — the
#            component is the default export and is typed against
#            the contract.
#     AC#5 — The default-export function destructures `message` out
#            of its props argument, so the JSX body can reference it
#            as a bare identifier (`{message ?? 'Carregando…'}`)
#            without going through `props.message`.
#
# DECISION:
#     Estratégia: create — a brand-new shared component, no
#                 pre-existing `LoadingState` to migrate from. The
#                 shared component is the source of truth for
#                 loading-state markup; rooms will adopt it in
#                 follow-up PRs.
#     Arquivo alvo: apps/blu_v3/src/components/shared/LoadingState.tsx
#     Função alvo:  `export default function LoadingState(props:
#                  LoadingStateProps) { … }` plus the
#                  `LoadingStateProps` interface.
#
# Estado atual: RED — `LoadingState.tsx` does NOT exist on disk.
# Every AC fails on the file-exists check (AC#1) and the source-
# inspection checks (AC#2 → AC#5) cannot run. The Coder must create
# the file with the exact prop contract above to turn all 5 ACs
# GREEN.
#
# Anti-Goals (must NOT be violated):
#     1. NÃO renomear o prop `message` — ele é contrato.
#     2. NÃO tornar `message` obrigatório — ele é OPTIONAL (`?`) e
#        um consumidor que não quer customizar a copy deve poder
#        escrever `<LoadingState />` sem erro de tipo.
#     3. NÃO alterar o tipo de `message` — ele é exatamente
#        `string`. Não aceitar `message?: ReactNode`, não aceitar
#        `message?: JSX.Element`, não aceitar `message?: string | null`.
#     4. NÃO exportar o componente como named export — ele deve ser
#        o DEFAULT export para casar com o padrão de
#        `import LoadingState from '../../components/shared/LoadingState'`
#        já usado pelos outros componentes shared (`DecisionCard`,
#        `ErrorFallback`, `EmptyState`, …).
#     5. NÃO colocar o componente em outro diretório
#        (`components/common/`, `components/ui/`, etc.) — ele é
#        `components/shared/LoadingState.tsx` por contrato.


# ── Paths ─────────────────────────────────────────────────────────────────


LOADING_STATE_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "components"
    / "shared"
    / "LoadingState.tsx"
)


# ── Source-level guard helpers (LoadingState) ─────────────────────────────


def _has_loading_state_props_interface(source: str) -> bool:
    """Detect an `export interface LoadingStateProps { … }` declaration.

    We match the opening `export interface LoadingStateProps {` and
    the closing `}`. The body is allowed to contain at most one level
    of nested braces (the prop surface is a single optional `message`
    string, so no nested braces are actually needed — but the regex
    is symmetric with the `EmptyStateProps` helper for readability).
    """
    pattern = (
        r"export\s+interface\s+LoadingStateProps\s*\{"
        r"((?:[^{}]|\{[^{}]*\})*)"
        r"\}"
    )
    return re.search(pattern, source, re.DOTALL) is not None


def _loading_state_props_body(source: str) -> str | None:
    """Return the body of the `LoadingStateProps` interface, or None
    if the interface is not declared.

    The body is the substring between the opening `{` and the
    matching closing `}`, with one level of nested-brace support.
    """
    pattern = (
        r"export\s+interface\s+LoadingStateProps\s*\{"
        r"((?:[^{}]|\{[^{}]*\})*)"
        r"\}"
    )
    m = re.search(pattern, source, re.DOTALL)
    return m.group(1) if m else None


def _declares_optional_message_prop(source: str) -> bool:
    """Detect `message?:` — i.e. `message` is declared as an OPTIONAL
    prop, typed against the contract.

    We look for `message` followed by `?:` (the question mark making
    it optional) and the literal `string` type. This rejects:
        - `message: string` (required — wrong)
        - `message?: ReactNode` (wrong type)
        - `message?: JSX.Element` (wrong type)
    """
    pattern = r"\bmessage\s*\?\s*:\s*string\b"
    return re.search(pattern, source) is not None


def _has_loading_state_default_export_function(source: str) -> bool:
    """Detect `export default function LoadingState(...) { … }`.

    We are permissive about the parameter list: both the destructure
    form (`({ … }: LoadingStateProps)`) and the bare form
    (`(props: LoadingStateProps)`) must pass. The function name MUST
    be `LoadingState` (the default export of the file).
    """
    pattern = (
        r"export\s+default\s+function\s+LoadingState\s*\("
        r"[^)]*\)"
        r"\s*:\s*LoadingStateProps"
    )
    return re.search(pattern, source, re.DOTALL) is not None


def _loading_state_destructures_message(source: str) -> bool:
    """Detect the destructure form of the default-export parameter
    list and check that `message` is reachable as a bare name.

    We only check the `message` prop (the entire prop surface). A
    prop is "present" if its identifier appears inside the `{ … }`
    destructure of the default-export function.
    """
    sig = re.search(
        r"export\s+default\s+function\s+LoadingState\s*\(\s*\{([^}]*)\}\s*:\s*LoadingStateProps",
        source,
    )
    if not sig:
        # If the function uses the bare `props: LoadingStateProps`
        # form, the destructure is not present. We surface `message`
        # as "not detected" — the dedicated signature test is the
        # one that enforces typing.
        return False
    body = sig.group(1)
    return re.search(r"\bmessage\b", body) is not None


# ── AC#1: file exists at the canonical path ──────────────────────────────


class TestLoadingState:
    """AC#2 — shared `LoadingState` component.

    Validates that a shared loading-state component exists at
    `apps/blu_v3/src/components/shared/LoadingState.tsx` with a
    minimal, fully-typed prop surface: a single OPTIONAL `message`
    string. The shared component is the single source of truth for
    loading-state markup across all room pages.
    """

    def test_loading_state_file_exists(self):
        """AC#1 — `apps/blu_v3/src/components/shared/LoadingState.tsx`
        must exist on disk.

        This is the source-of-truth guard for the entire migration:
        until the file exists, every other AC#2..AC#5 is unreachable.
        The rooms will import the shared component from this exact
        path, so placing the file elsewhere (e.g.
        `components/ui/LoadingState.tsx`) is a hard contract
        violation.
        """
        assert LOADING_STATE_PATH.exists(), (
            f"RED — source file not found: {LOADING_STATE_PATH}. "
            "Expected: a new `LoadingState.tsx` under "
            "`apps/blu_v3/src/components/shared/` exporting the "
            "shared loading-state component used by every room "
            "page. Without it, each room keeps rolling its own "
            "ad-hoc loading block (different spinners, different "
            "copy, no shared `role`/`data-testid` for tests to "
            "anchor on), and the visual drift across rooms "
            "continues."
        )

    def test_loading_state_exports_loading_state_props_interface(self):
        """AC#2 — The file must export
        `interface LoadingStateProps { … }`.

        Other modules will import the type as
        `import type { LoadingStateProps } from
        '../../components/shared/LoadingState'`, which requires the
        `export` keyword on the interface declaration. We also
        require the body to be well-formed (one level of
        nested-brace support, symmetric with the `EmptyStateProps`
        helper).
        """
        assert LOADING_STATE_PATH.exists(), (
            f"RED — source file not found: {LOADING_STATE_PATH}"
        )
        source = _read_source(LOADING_STATE_PATH)

        assert _has_loading_state_props_interface(source), (
            "RED — LoadingState.tsx does NOT export `interface "
            "LoadingStateProps { … }`. Expected: "
            "`export interface LoadingStateProps { message?: string }` "
            "so consumers can `import type { LoadingStateProps }` "
            "and rely on the prop contract."
        )

    def test_loading_state_message_is_optional_string(self):
        """AC#3 — The `message` prop must be OPTIONAL
        (`message?:`) AND typed as `string`.

        Two contracts pinned at once:
            (a) `message` MUST be optional — a consumer that wants
                the default copy must be able to write
                `<LoadingState />` without supplying a `message`,
                and TypeScript must accept it.
            (b) When `message` IS supplied, it MUST be a raw
                `string` (NOT `ReactNode`, NOT `JSX.Element`).
                The shared component decides how to render the
                string: a `<span>`, a `<p>`, an `aria-label`,
                etc. A `ReactNode` type would invite consumers
                to pass a `<Spinner />` element, which belongs
                in the component body, not in the prop.
        """
        assert LOADING_STATE_PATH.exists(), (
            f"RED — source file not found: {LOADING_STATE_PATH}"
        )
        source = _read_source(LOADING_STATE_PATH)

        body = _loading_state_props_body(source)
        assert body is not None, (
            "RED — LoadingState.tsx does NOT export `interface "
            "LoadingStateProps`. AC#3 cannot be evaluated until "
            "the interface exists; declare it first (see AC#2)."
        )

        assert _declares_optional_message_prop(source), (
            "RED — LoadingState.tsx does NOT declare `message` as "
            "an OPTIONAL string prop. Expected `message?: string` "
            "(with the `?` modifier) so consumers that don't need "
            "to override the default copy can write `<LoadingState />` "
            "without a TypeScript error. A required `message: string` "
            "would force every caller to pass a string, which is "
            "wrong — the default copy is a sensible fallback."
        )

    def test_loading_state_default_export_function_uses_props(self):
        """AC#4 — The file must have
        `export default function LoadingState(...): LoadingStateProps`.

        Two things are pinned at once:
            (a) the component is the DEFAULT export of the file
                (rooms will write
                `import LoadingState from
                '../../components/shared/LoadingState'`), and
            (b) its parameter list is typed against the
                `LoadingStateProps` interface, so TypeScript will
                catch any consumer that passes the wrong prop
                shape at compile time.
        """
        assert LOADING_STATE_PATH.exists(), (
            f"RED — source file not found: {LOADING_STATE_PATH}"
        )
        source = _read_source(LOADING_STATE_PATH)

        assert _has_loading_state_default_export_function(source), (
            "RED — LoadingState.tsx does NOT have the expected "
            "default-export signature "
            "`export default function LoadingState(...): LoadingStateProps`. "
            "The component MUST be the default export (matching the "
            "convention of other shared components like "
            "`DecisionCard`, `ErrorFallback`, and `EmptyState`) "
            "and MUST be typed against `LoadingStateProps` so the "
            "prop contract is enforced at compile time for every "
            "room that adopts it."
        )

    def test_loading_state_function_destructures_message(self):
        """AC#5 — The default-export function must destructure
        `message` out of its props argument, so the JSX body can
        reference it as a bare identifier
        (`{message ?? 'Carregando…'}`) without going through
        `props.message`.
        """
        assert LOADING_STATE_PATH.exists(), (
            f"RED — source file not found: {LOADING_STATE_PATH}"
        )
        source = _read_source(LOADING_STATE_PATH)

        assert _loading_state_destructures_message(source), (
            "RED — the default-export `LoadingState` function does "
            "not destructure the `message` prop. Expected the "
            "signature to be "
            "`export default function LoadingState({ message }: "
            "LoadingStateProps) { … }` so the JSX body can "
            "reference `{message}` directly (and fall back to a "
            "default like `'Carregando…'` when the prop is "
            "omitted). Going through `props.message` is "
            "functionally equivalent but is out of contract for "
            "this shared component."
        )
