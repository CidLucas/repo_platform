"""RED test for behavior B-5 — Padronização do design system entre salas (BKL-031).

GOAL:
    F-2 (Consistência Visual e Navegação entre Salas) — As salas
    FinanceiroRoom, ComprasRoom, ClientesRoom, AgendaRoom e
    BibliotecaRoom devem compartilhar um design system padronizado
    via CSS global (global.css) em vez de inline styles divergentes.

    A global.css já define classes reutilizáveis:
      - .panel        → fundo glass, borda var(--gb), border-radius
                        var(--rl), backdrop-filter blur, box-shadow
                        consistente, transition hover
      - .ph / .pb     → header padding 13px 16px 11px / body scroll
      - .btn.bp       → botão primário com background var(--ac)
      - .btn.bs       → botão secundário com glass background
      - .dc-row:hover → hover em linhas de decisão

    O objetivo deste RED test é verificar que padding de estados
    de loading/empty, cor de botões primários e estrutura de painéis
    são consistentes entre as 5 salas.

BEHAVIOR:
    B-5 — Padronização do design system entre salas (BKL-031).
    Todas as 5 salas devem:

    1. Usar className="panel" no wrapper principal.
    2. Usar className="btn bp" para botões primários.
    3. Usar padding vertical "12px 0" para estados de loading/empty
       (mesmo padrão aceito pela maioria das salas).

    **Estado atual (RED):**
    - ClientesRoom.tsx  → padding: '16px 0' nos loading/empty ✗ (RED)
    - BibliotecaRoom.tsx → padding: '16px 0' nos loading/empty ✗ (RED)
    - FinanceiroRoom    → padding: '12px 0' ✓
    - ComprasRoom       → padding: '12px 0' ✓
    - AgendaRoom        → padding: '12px 0' ✓

    **Estado alvo (GREEN):**
    - Todas as 5 salas usam padding: '12px 0' para loading/empty.
    - Todas as 5 salas usam className="panel" no wrapper.
    - Todas as 5 salas usam className="btn bp" para botão primário.

AC (Acceptance Criteria):
    AC#1 — Nenhuma sala tem padding: '16px 0' em estados de
            loading/empty.  RED (ClientesRoom e BibliotecaRoom).
    AC#2 — FinanceiroRoom.tsx tem padding: '12px 0' em pelo menos
            um estado de loading/empty — GREEN (já conforme).
    AC#3 — ComprasRoom.tsx tem padding: '12px 0' em pelo menos
            um estado de loading/empty — GREEN (já conforme).
    AC#4 — ClientesRoom.tsx tem padding: '12px 0' em pelo menos
            um estado de loading/empty — RED (atualmente só tem
            "16px 0").
    AC#5 — BibliotecaRoom.tsx tem padding: '12px 0' em pelo menos
            um estado de loading/empty — RED (atualmente só tem
            "16px 0").
    AC#6 — Todas as 5 salas usam className="panel" no wrapper
            principal — GREEN (já conforme).
    AC#7 — Todas as 5 salas usam className="btn bp" (ou
            className={`btn ${cond ? 'bp' : 'bs'}`}) para o botão
            de ação principal — GREEN (já conforme).

DECISÃO:
    Estratégia: source_inspection (regex sobre o TSX).
    Arquivos alvo:
      - apps/blu_v3/src/pages/app/FinanceiroRoom.tsx
      - apps/blu_v3/src/pages/app/ComprasRoom.tsx
      - apps/blu_v3/src/pages/app/ClientesRoom.tsx
      - apps/blu_v3/src/pages/app/AgendaRoom.tsx
      - apps/blu_v3/src/pages/app/BibliotecaRoom.tsx

Anti-Goals (must NOT be violated):
    1. NAO modificar código de produção — o teste é puramente
       estático. A implementação da feature será feita na fase
       GREEN.
    2. NAO importar ou executar código TypeScript/React — o teste
       apenas lê os arquivos como texto e usa regex.
    3. NAO usar fixtures de DB ou rede — o teste é determinístico
       e roda sem rede.
    4. NAO exigir mudanças na global.css (já tem o design system
       correto). Apenas as salas precisam ser padronizadas.
"""

import re
from pathlib import Path

import pytest


# ── Constants: paths da interface pública sob teste ──────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

ROOM_DIR = REPO_ROOT / "apps" / "blu_v3" / "src" / "pages" / "app"

ROOM_FILES: dict[str, Path] = {
    "FinanceiroRoom": ROOM_DIR / "FinanceiroRoom.tsx",
    "ComprasRoom": ROOM_DIR / "ComprasRoom.tsx",
    "ClientesRoom": ROOM_DIR / "ClientesRoom.tsx",
    "AgendaRoom": ROOM_DIR / "AgendaRoom.tsx",
    "BibliotecaRoom": ROOM_DIR / "BibliotecaRoom.tsx",
}


# ── Override do root conftest (teste puramente estático) ────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest cleanup — pure unit tests, no DB needed."""
    yield


# ── Helpers ─────────────────────────────────────────────────────────


def _read_text(path: Path) -> str:
    """Lê o conteúdo de um arquivo como texto."""
    return path.read_text(encoding="utf-8")


def _get_room_content(name: str) -> tuple[str, Path]:
    """Retorna (conteudo, path) para uma sala."""
    path = ROOM_FILES[name]
    return _read_text(path), path


# ── Tests ────────────────────────────────────────────────────────────


class TestDesignSystemPadronizacao:
    """B-5 (BKL-031): Padronização do design system entre salas."""

    def test_ac1_no_inconsistent_16px_padding(self):
        """AC#1 — NENHUMA sala deve ter padding: '16px 0' em loading/empty."""
        problems: list[str] = []
        for name, path in ROOM_FILES.items():
            content = _read_text(path)
            # Procura por padding: '16px 0' ou padding: "16px 0" em contextos
            # de loading/empty (perto de Carregando, Nenhum, etc.)
            # Usa lookahead para encontrar padding em linhas que tambem
            # mencionam Carregando, Nenhum ou texto similar
            for m in re.finditer(
                r"""padding\s*:\s*['"]16px\s+0['"]""",
                content,
            ):
                # Pega o contexto ao redor (5 linhas para cada lado) para verificar
                # se é de fato um estado de loading/empty
                start = max(0, m.start() - 300)
                end = min(len(content), m.end() + 300)
                ctx = content[start:end]

                # Só reporta se for realmente loading/empty state
                # (contem Carregando, Nenhum, or similar)
                if re.search(
                    r"Carregando|Nenhum|Sem\s|vazio|empty|loading",
                    ctx,
                    re.IGNORECASE,
                ):
                    problems.append(
                        f"{name} ({path.relative_to(REPO_ROOT)}): "
                        f"padding: '16px 0' em estado de loading/empty"
                    )

        if problems:
            msg = (
                "AC#1 violada.  As seguintes salas usam padding: '16px 0'\n"
                "em estados de loading/empty, enquanto o padrao esperado\n"
                "e padding: '12px 0' (consistente com FinanceiroRoom,\n"
                "ComprasRoom e AgendaRoom):\n\n"
            )
            msg += "\n".join(f"  - {p}" for p in problems)
            msg += (
                "\n\nTodas as salas devem usar o mesmo padding vertical\n"
                "para consistencia visual.\n\n"
                "GREEN deve alterar as linhas offending de:\n"
                "  padding: '16px 0'\n"
                "para:\n"
                "  padding: '12px 0'"
            )
            pytest.fail(msg)

    def test_ac2_financeiro_has_12px_padding(self):
        """AC#2 — FinanceiroRoom tem padding: '12px 0'."""
        content, path = _get_room_content("FinanceiroRoom")
        padding_match = re.search(
            r"""padding\s*:\s*['"]12px\s+0['"]""",
            content,
        )
        if not padding_match:
            pytest.fail(
                "AC#2 violada.  O componente ``FinanceiroRoom`` em "
                f"{path.relative_to(REPO_ROOT)} NAO contem\n"
                "nenhum ``padding: '12px 0'`` para estado de loading/empty.\n\n"
                "Todas as salas devem ter pelo menos um estado de\n"
                "loading/empty com ``padding: '12px 0'``.\n\n"
                "GREEN deve garantir que exista:\n"
                '  <div style={{ padding: "12px 0", ... }}>Carregando...</div>'
            )

    def test_ac3_compras_has_12px_padding(self):
        """AC#3 — ComprasRoom tem padding: '12px 0'."""
        content, path = _get_room_content("ComprasRoom")
        padding_match = re.search(
            r"""padding\s*:\s*['"]12px\s+0['"]""",
            content,
        )
        if not padding_match:
            pytest.fail(
                "AC#3 violada.  O componente ``ComprasRoom`` em "
                f"{path.relative_to(REPO_ROOT)} NAO contem\n"
                "nenhum ``padding: '12px 0'`` para estado de loading/empty.\n\n"
                "Todas as salas devem ter pelo menos um estado de\n"
                "loading/empty com ``padding: '12px 0'``.\n\n"
                "GREEN deve garantir que exista:\n"
                '  <div style={{ padding: "12px 0", ... }}>Carregando...</div>'
            )

    def test_ac4_clientes_has_12px_padding(self):
        """AC#4 — ClientesRoom DEVE ter padding: '12px 0' (RED — atualmente
        so tem '16px 0')."""
        content, path = _get_room_content("ClientesRoom")
        padding_match = re.search(
            r"""padding\s*:\s*['"]12px\s+0['"]""",
            content,
        )
        if not padding_match:
            pytest.fail(
                "AC#4 violada.  O componente ``ClientesRoom`` em "
                f"{path.relative_to(REPO_ROOT)} NAO contem\n"
                "nenhum ``padding: '12px 0'`` para estado de loading/empty.\n"
                "Atualmente usa ``padding: '16px 0'`` (inconsistente\n"
                "com as demais salas que usam '12px 0').\n\n"
                "Todas as salas devem usar o mesmo padding vertical\n"
                "para consistencia visual.\n\n"
                "GREEN deve alterar a(s) linha(s) offending de:\n"
                "  padding: '16px 0'\n"
                "para:\n"
                "  padding: '12px 0'"
            )

    def test_ac5_biblioteca_has_12px_padding(self):
        """AC#5 — BibliotecaRoom DEVE ter padding: '12px 0' (RED — atualmente
        so tem '16px 0')."""
        content, path = _get_room_content("BibliotecaRoom")
        padding_match = re.search(
            r"""padding\s*:\s*['"]12px\s+0['"]""",
            content,
        )
        if not padding_match:
            pytest.fail(
                "AC#5 violada.  O componente ``BibliotecaRoom`` em "
                f"{path.relative_to(REPO_ROOT)} NAO contem\n"
                "nenhum ``padding: '12px 0'`` para estado de loading/empty.\n"
                "Atualmente usa ``padding: '16px 0'`` (inconsistente\n"
                "com as demais salas que usam '12px 0').\n\n"
                "Todas as salas devem usar o mesmo padding vertical\n"
                "para consistencia visual.\n\n"
                "GREEN deve alterar a(s) linha(s) offending de:\n"
                "  padding: '16px 0'\n"
                "para:\n"
                "  padding: '12px 0'"
            )

    def test_ac6_all_rooms_have_panel_class(self) -> None:
        """AC#6 — Todas as 5 salas usam className='panel'."""
        for name, path in ROOM_FILES.items():
            content = _read_text(path)
            if not re.search(
                r"""className\s*=\s*["']panel["']""",
                content,
            ):
                pytest.fail(
                    f"AC#6 violada.  O componente ``{name}`` em "
                    f"{path.relative_to(REPO_ROOT)}\n"
                    "NAO contem um ``className=\"panel\"`` no wrapper "
                    "principal.\n\n"
                    "Todas as salas devem usar a classe ``.panel`` da "
                    "global.css\ncomo container principal.\n\n"
                    "GREEN deve adicionar:\n"
                    '  <div className="panel" '
                    'style={{gridColumn:1,gridRow:1}}>\n'
                    "    ...conteudo...\n"
                    "  </div>"
                )

    def test_ac7_all_rooms_have_bp_button(self) -> None:
        """AC#7 — Todas as 5 salas usam className='btn bp'."""
        for name, path in ROOM_FILES.items():
            content = _read_text(path)
            # Procura por className contendo "bp" (ex: 'btn bp' ou
            # `btn ${cond ? 'bp' : 'bs'}`)
            if not re.search(
                r"""className\s*=\s*(?:["'`][^"'`]*["'`]|\{[^}]+\})""",
                content,
            ):
                continue  # nao achou pattern, vai pro fail

            if not re.search(
                r"""className\s*=\s*(?:
                    ["'](?:[^"']*\s)?bp(?:[^"']*\s)?["']|
                    \{[\s\S]*?['"`]bp['"`][\s\S]*?\}
                )""",
                content,
                re.VERBOSE,
            ):
                pytest.fail(
                    f"AC#7 violada.  O componente ``{name}`` em "
                    f"{path.relative_to(REPO_ROOT)}\n"
                    "NAO contem um ``className=\"btn bp\"`` para o botão\n"
                    "de acao principal.\n\n"
                    "A classe ``.bp`` ja define:\n"
                    "  - background: var(--ac) → cor consistente\n"
                    "  - color: #fff\n"
                    "  - hover: background: #7A4FC9\n\n"
                    "GREEN deve garantir que o botao primario use:\n"
                    '  <button className="btn bp" onClick={...}>...</button>'
                )
