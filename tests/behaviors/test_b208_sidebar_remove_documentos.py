"""RED test for behavior B-208 — Sidebar drops "Documentos" entry, keeps "Estratégia".

GOAL:
    Issue #208: a entrada "Documentos" deve ser removida da sidebar,
    mantendo apenas "Estratégia" (com seu ícone Target). A sala
    ``DocumentosRoom`` continua existindo internamente — apenas o link
    no ``NAV_ITEMS`` do ``Sidebar.tsx`` é suprimido.

BEHAVIOR:
    B-208 — Sidebar: remover entrada "Documentos", manter "Estratégia"
    O arquivo ``apps/blu_v3/src/components/shell/Sidebar.tsx`` deve
    satisfazer simultaneamente:

        1. AC1: nenhuma entrada de ``NAV_ITEMS`` com ``s: 'documentos'``
           e ``label: 'Documentos'``.
        2. AC2: continua existindo uma entrada de ``NAV_ITEMS`` com
           ``s: 'estrategia'`` e ``label: 'Estratégia'`` cujo ícone é
           ``<Target ... />``.

AC (Acceptance Criteria):
    AC1 — Sidebar não tem mais entrada "Documentos"
    AC2 — Entrada "Estratégia" permanece com ícone

DECISION:
    Estratégia: extend (alteração cirúrgica no ``Sidebar.tsx``)
    Arquivo alvo: apps/blu_v3/src/components/shell/Sidebar.tsx
    Seção alvo: array ``NAV_ITEMS``

Anti-Goals (must NOT be violated):
    1. NÃO remover a entrada de "Estratégia" — apenas "Documentos".
    2. NÃO alterar o ícone de "Estratégia" (deve permanecer ``Target``).
    3. NÃO remover a sala ``DocumentosRoom`` ou o tipo ``Screen =
       'documentos'`` — outros fluxos (rotinas, decision cards,
       spotlight) podem continuar referenciando a rota.
    4. NÃO mexer em ``FOOT_ITEMS`` (Atividade / Admin / AgentOps).

Estado atual: RED — a linha ``{ s: 'documentos', icon: <PencilSimpleLine
... />, label: 'Documentos' }`` ainda está presente em ``NAV_ITEMS``. O
teste faz parse do arquivo ``Sidebar.tsx``, extrai o array ``NAV_ITEMS``
e verifica as duas ACs acima, falhando com AssertionError até que a
feature seja implementada na fase GREEN.
"""

import re
from pathlib import Path

import pytest

# ── Path to the target source file ───────────────────────────────────────

SIDEBAR_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "apps"
    / "blu_v3"
    / "src"
    / "components"
    / "shell"
    / "Sidebar.tsx"
)


# ── Override root conftest cleanup (pure file-based test) ───────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test is pure file inspection, no DB."""
    yield


# ── Helpers: parse the TypeScript file ───────────────────────────────────


def _extract_nav_items(content: str) -> list[dict[str, str]]:
    """Return the parsed entries of the ``NAV_ITEMS`` array.

    Each entry is a dict with the keys ``s`` (screen slug), ``label`` and
    ``icon`` as they appear in the source.  Only simple, single-line
    object literals are matched — which is the format used by the real
    ``Sidebar.tsx`` (one object literal per ``NAV_ITEMS`` row).
    """
    items: list[dict[str, str]] = []
    # Match the body of `const NAV_ITEMS: NavItem[] = [ ... ];`
    array_match = re.search(
        r"const\s+NAV_ITEMS\s*:\s*NavItem\[\]\s*=\s*\[(?P<body>.*?)\];",
        content,
        re.DOTALL,
    )
    if not array_match:
        return items
    body = array_match.group("body")
    # Each entry: `{ s: 'xxx', icon: <...>, label: 'yyy' }`
    for obj_match in re.finditer(r"\{(?P<entry>[^}]*)\}", body):
        entry = obj_match.group("entry")
        s_match = re.search(r"s\s*:\s*['\"](?P<v>[^'\"]+)['\"]", entry)
        label_match = re.search(r"label\s*:\s*['\"](?P<v>[^'\"]+)['\"]", entry)
        icon_match = re.search(r"icon\s*:\s*<(?P<v>[A-Za-z0-9_]+)", entry)
        if s_match and label_match and icon_match:
            items.append(
                {
                    "s": s_match.group("v"),
                    "label": label_match.group("v"),
                    "icon": icon_match.group("v"),
                }
            )
    return items


# ── The single behavior under test ──────────────────────────────────────


def test_b208_sidebar_drops_documentos_keeps_estrategia_with_target():
    """Sidebar NAV_ITEMS must not contain 'Documentos' and must still
    contain 'Estratégia' with the Target icon.
    """
    # 1. The Sidebar source file must exist.
    assert SIDEBAR_PATH.exists(), (
        f"Sidebar source file not found: {SIDEBAR_PATH}"
    )

    content = SIDEBAR_PATH.read_text(encoding="utf-8")

    # 2. Extract the NAV_ITEMS array.
    nav_items = _extract_nav_items(content)
    assert nav_items, (
        "Could not parse any NAV_ITEMS entries from Sidebar.tsx. "
        "Expected a `const NAV_ITEMS: NavItem[] = [ { s: '...', icon: <...>, label: '...' }, ... ];` block."
    )

    # 3. AC1 — no entry with s='documentos' and label='Documentos'.
    documentos_entries = [
        n for n in nav_items
        if n["s"] == "documentos" and n["label"] == "Documentos"
    ]
    assert not documentos_entries, (
        "AC#1 violated: Sidebar still has a 'Documentos' entry in NAV_ITEMS. "
        "Behavior B-208 requires removing the row:\n"
        "    { s: 'documentos', icon: <PencilSimpleLine ... />, label: 'Documentos' }\n"
        f"Found {len(documentos_entries)} match(es):\n"
        + "\n".join(f"    {n}" for n in documentos_entries)
    )

    # 4. AC2 — 'Estratégia' must still be present, with the Target icon.
    estrategia_entries = [
        n for n in nav_items
        if n["s"] == "estrategia" and n["label"] == "Estratégia"
    ]
    assert estrategia_entries, (
        "AC#2 violated: Sidebar no longer has an 'Estratégia' entry. "
        "Behavior B-208 must KEEP 'Estratégia' (only 'Documentos' is removed). "
        "Expected a row like:\n"
        "    { s: 'estrategia', icon: <Target ... />, label: 'Estratégia' }"
    )
    estrategia = estrategia_entries[0]
    assert estrategia["icon"] == "Target", (
        "AC#2 violated: 'Estratégia' icon is not 'Target'. "
        f"Got icon={estrategia['icon']!r}. Behavior B-208 / anti-goal #2 "
        "requires keeping the original Target icon for 'Estratégia'."
    )

    # 5. Anti-goal #4 — FOOT_ITEMS must be untouched.  We sanity-check by
    #    making sure the canonical foot entries are still present.
    for foot_slug, foot_label in (
        ("atividade", "Atividade"),
        ("admin", "Admin"),
        ("blu_ops", "AgentOps"),
    ):
        assert any(
            n["s"] == foot_slug and n["label"] == foot_label for n in nav_items
        ), (
            f"Anti-goal #4 violated: FOOT_ITEMS entry for {foot_slug!r} "
            f"({foot_label!r}) is missing. B-208 must not touch FOOT_ITEMS."
        )
