"""RED test for behavior B-4 — Design system consistente entre salas (NAO implementado).

GOAL:
    Garantir que todas as 5 salas (FinanceiroRoom, ComprasRoom, ClientesRoom,
    AgendaRoom, BibliotecaRoom) usem CSS :hover para efeitos de hover em
    cards/rows, SEM usar estado JavaScript (useState + onMouseEnter/onMouseLeave).

    O uso de JS state para hover e INCONSISTENTE com o design system das
    demais salas e deve ser substituido por CSS :hover.

BEHAVIOR:
    B-4 — Design system consistente entre salas:
    Todas as 5 salas devem usar o mesmo padrao de hover: CSS :hover via
    classes/selectors, nao useState para hover.

AC (Acceptance Criteria):
    AC-4 — Todas as 5 salas (FinanceiroRoom, ComprasRoom, ClientesRoom,
            AgendaRoom, BibliotecaRoom) implementam hover em elementos de
            card/row via CSS :hover, SEM usar useState de hover.

Estado atual (RED):
    - FinanceiroRoom.tsx: usa classe CSS `.dc-row:hover` — OK (CSS)
    - ComprasRoom.tsx: usa `.sup-row:hover` e `.dc-row:hover` — OK (CSS)
    - ClientesRoom.tsx: usa `.dc-row:hover` — OK (CSS)
    - AgendaRoom.tsx: usa `.dc-row:hover` e `.pl-item:hover` — OK (CSS)
    - BibliotecaRoom.tsx: DocCard usa `const [hover, setHover] = useState(false)`
      com `onMouseEnter`/`onMouseLeave` — INCONSISTENTE (JS state)

Estado alvo (GREEN):
    BibliotecaRoom.tsx deve refatorar DocCard para usar CSS :hover
    (ex: .doc-card:hover { background: ... }) em vez de estado JS.
    Todas as 5 salas devem usar exclusivamente CSS para hover.

Anti-Goals:
    1. NAO modificar codigo de producao (so testes estaticos com regex).
    2. NAO usar mocks, DB, browser testing, jsdom.
    3. NAO quebrar hover existente nas salas que ja usam CSS (nas 4 salas via
       classes CSS, o hover deve ser PRESERVADO).
    4. NAO relaxar o teste para passar no estado atual — TRUE RED.
    5. NAO modificar o conftest.py existente em tests/behaviors/conftest.py.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Paths ──────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

ROOM_FILES: dict[str, Path] = {
    "FinanceiroRoom": REPO_ROOT / "apps" / "blu_v3" / "src" / "pages" / "app" / "FinanceiroRoom.tsx",
    "ComprasRoom":    REPO_ROOT / "apps" / "blu_v3" / "src" / "pages" / "app" / "ComprasRoom.tsx",
    "ClientesRoom":   REPO_ROOT / "apps" / "blu_v3" / "src" / "pages" / "app" / "ClientesRoom.tsx",
    "AgendaRoom":     REPO_ROOT / "apps" / "blu_v3" / "src" / "pages" / "app" / "AgendaRoom.tsx",
    "BibliotecaRoom": REPO_ROOT / "apps" / "blu_v3" / "src" / "pages" / "app" / "BibliotecaRoom.tsx",
}


# ── Source helpers ─────────────────────────────────────────────────────────


def _read_source(path: Path) -> str:
    """Le o codigo-fonte TSX como texto puro."""
    assert path.exists(), f"Source file not found: {path}"
    return path.read_text(encoding="utf-8")


def _has_js_hover(source: str) -> bool:
    """Verifica se o codigo-fonte contem padrao de hover JavaScript.

    Detecta:
      - const [hover, setHover] = useState(...)
      - onMouseEnter={() => setHover(true)}
      - onMouseLeave={() => setHover(false)}

    Retorna True se pelo menos um destes padroes for encontrado.
    """
    # Padrao 1: useState com hover
    if re.search(r'useState\s*<[^>]*>\s*\(\s*false\s*\)', source) or \
       re.search(r'useState\s*\(\s*false\s*\)', source):
        # Verifica se essa variavel se chama 'hover'
        if re.search(r'\bconst\s+\[\s*hover\s*,\s*setHover\s*\]\s*=\s*useState', source):
            return True

    # Padrao 2: onMouseEnter / onMouseLeave com setHover
    if re.search(r'onMouseEnter\s*=\s*\(\s*\)\s*=>\s*setHover\s*\(\s*true\s*\)', source) and \
       re.search(r'onMouseLeave\s*=\s*\(\s*\)\s*=>\s*setHover\s*\(\s*false\s*\)', source):
        return True

    return False


# ── Test ───────────────────────────────────────────────────────────────────


def test_b4_ac4_hover_consistente_css_nao_js() -> None:
    """AC-4 — Todas as 5 salas usam CSS :hover para hover, NAO useState JS.

    Verifica que NENHUMA das 5 salas contem o padrao de hover JavaScript
    (useState com setHover + onMouseEnter/onMouseLeave). Se qualquer sala
    usar JS hover, o teste falha (RED).
    """
    salas_com_js_hover: list[str] = []

    for nome_sala, path in ROOM_FILES.items():
        source = _read_source(path)
        if _has_js_hover(source):
            salas_com_js_hover.append(nome_sala)

    if salas_com_js_hover:
        detalhes = "\n".join(
            f"  - {nome}: usa useState/setHover com onMouseEnter/onMouseLeave para hover\n"
            f"    (inconsistente com as demais salas que usam CSS :hover)"
            for nome in salas_com_js_hover
        )
        msg = (
            "RED — AC-4: As seguintes sala(s) usam JavaScript state para hover\n"
            "em vez de CSS :hover, quebrando a consistencia do design system:\n\n"
            f"{detalhes}\n\n"
            "Esperado: todas as 5 salas devem usar CSS :hover (pseudo-classe)\n"
            "para efeitos de hover em cards/rows.\n\n"
            "Exemplo de como deve ficar (GREEN):\n"
            "  - Remover: const [hover, setHover] = useState(false)\n"
            "  - Remover: onMouseEnter/onMouseLeave\n"
            "  - Substituir o estilo inline `background: hover ? ... : ...`\n"
            "    por uma classe CSS, por exemplo:\n"
            "      .doc-card { background: ... }\n"
            "      .doc-card:hover { background: ... }\n"
            "    Ou usar um seletor CSS, sem depender de estado React.\n\n"
            "O Coder deve refatorar o(s) componente(s) afetado(s) para usar\n"
            "apenas CSS :hover, mantendo o mesmo efeito visual."
        )
        pytest.fail(msg)
